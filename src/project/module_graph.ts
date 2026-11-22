// Carga del grafo de módulos a partir de `invoke`.
//
// Parsea cada archivo alcanzable, detecta ciclos y deja los módulos
// en orden de dependencias. Los diagnósticos se acumulan para que el
// driver los muestre una sola vez.

import { readFileSync } from "node:fs";
import { dirname } from "node:path";
import { make_source } from "../util/span.ts";
import type { Diagnostic } from "../diagnostics/diagnostic.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import { CODES } from "../diagnostics/codes.ts";
import { make_sink } from "../diagnostics/sink.ts";
import { parse_text } from "../frontend/parser.ts";
import type { Program } from "../frontend/ast.ts";
import type { DeclNode } from "../frontend/ast_decl.ts";
import type { Span } from "../util/span.ts";
import { collect_module, same_method_signature } from "../semantic/module_info.ts";
import type { ModuleInfo } from "../semantic/module_info.ts";
import { symbol_type_of } from "../semantic/external.ts";
import { find_project_root, resolve_module_file } from "./paths.ts";

export interface SelectiveImport {
  readonly module: LoadedModule;
  readonly name: string;
}

export interface LoadedModule {
  readonly file: string;
  readonly program: Program;
  readonly info: ModuleInfo;
  readonly imports: Map<string, LoadedModule>;
  readonly selective: Map<string, SelectiveImport>;
}

export interface ModuleGraph {
  readonly entry: LoadedModule | undefined;
  readonly order: readonly LoadedModule[];
  readonly diagnostics: readonly Diagnostic[];
  // Diagnósticos por archivo: el LSP los publica documento a documento.
  readonly by_file: ReadonlyMap<string, readonly Diagnostic[]>;
}

export interface LoadOptions {
  // El LSP lee primero los buffers abiertos, después el disco.
  readonly read_file?: (path: string) => string | undefined;
}

interface LoadState {
  readonly loaded: Map<string, LoadedModule>;
  readonly visiting: Set<string>;
  readonly order: LoadedModule[];
  readonly diagnostics: Diagnostic[];
  readonly by_file: Map<string, Diagnostic[]>;
  readonly root: string;
  readonly read_file: ((path: string) => string | undefined) | undefined;
}

// Un diagnóstico se guarda en la lista global y en la de su archivo.
function report(state: LoadState, diagnostic: Diagnostic): void {
  state.diagnostics.push(diagnostic);
  const list = state.by_file.get(diagnostic.span.file);
  if (list === undefined) state.by_file.set(diagnostic.span.file, [diagnostic]);
  else list.push(diagnostic);
}

// Un realm puede reabrirse en varios archivos, pero un mismo nombre de
// tipo no puede declararse dos veces: en C++ sería una redefinición.
function check_realm_collisions(state: LoadState): void {
  const by_realm = new Map<string, Map<string, { file: string; span: Span }>>();
  for (const module of state.order) {
    const realm = module.info.realm;
    let names = by_realm.get(realm);
    if (names === undefined) {
      names = new Map();
      by_realm.set(realm, names);
    }
    for (const decl of module.program.decls) {
      if (!is_type_declaration(decl)) continue;
      const previous = names.get(decl.name);
      if (previous !== undefined && previous.file !== module.file) {
        report(
          state,
          make_error(
            CODES.realm_duplicate,
            `«${decl.name}» ya está declarado en el realm «${realm}» por «${previous.file}»`,
            decl.span,
            `un realm puede reabrirse, pero cada tipo se declara una sola vez`,
          ),
        );
        continue;
      }
      names.set(decl.name, { file: module.file, span: decl.span });
    }
  }
}

// Reabrir un realm en varios archivos comparte sus símbolos: todos los
// archivos del mismo realm ven los tipos y funciones de los demás.
function merge_realm_envs(state: LoadState): void {
  const groups = new Map<string, LoadedModule[]>();
  for (const module of state.order) {
    const list = groups.get(module.info.realm);
    if (list === undefined) groups.set(module.info.realm, [module]);
    else list.push(module);
  }

  for (const modules of groups.values()) {
    if (modules.length < 2) continue;
    for (const target of modules) {
      for (const source of modules) {
        if (source === target) continue;
        for (const [name, rune] of source.info.env.runes) {
          if (!target.info.env.runes.has(name)) target.info.env.runes.set(name, rune);
        }
        for (const [name, omen] of source.info.env.omens) {
          if (!target.info.env.omens.has(name)) target.info.env.omens.set(name, omen);
        }
        for (const [name, alias] of source.info.env.aliases) {
          if (!target.info.env.aliases.has(name)) target.info.env.aliases.set(name, alias);
        }
        for (const [name, fn] of source.info.functions) {
          if (!target.info.functions.has(name)) target.info.functions.set(name, fn);
        }
        for (const [name, constant] of source.info.consts) {
          if (!target.info.consts.has(name)) target.info.consts.set(name, constant);
        }
        // Los enhechizamientos de tipos incorporados se comparten igual:
        // `std/string.pengu` puede repartirse en varios archivos del realm.
        for (const [key, entry] of source.info.env.enchants) {
          const existing = target.info.env.enchants.get(key);
          if (existing === undefined) {
            target.info.env.enchants.set(key, entry);
            continue;
          }
          for (const [name, methods] of entry.methods) {
            const list = existing.methods.get(name);
            if (list === undefined) {
              existing.methods.set(name, [...methods]);
              continue;
            }
            for (const method of methods) {
              if (!list.some((other) => same_method_signature(other.info, method.info))) list.push(method);
            }
          }
        }
      }
    }
  }
}

function is_type_declaration(decl: DeclNode): decl is DeclNode & { readonly name: string; readonly span: Span } {
  switch (decl.kind) {
    case "rune_decl":
    case "omen_decl":
    case "echo_decl":
    case "seal_decl":
      return true;
    default:
      return false;
  }
}

function load_one(state: LoadState, file: string): LoadedModule | undefined {
  const cached = state.loaded.get(file);
  if (cached !== undefined) return cached;

  if (state.visiting.has(file)) {
    report(
      state,
      make_error(CODES.import_cycle, `ciclo de importaciones en «${file}»`, {
        file,
        start: { line: 1, column: 1, offset: 0 },
        end: { line: 1, column: 1, offset: 0 },
      }),
    );
    return undefined;
  }

  let text: string;
  const overlaid = state.read_file?.(file);
  try {
    text = overlaid ?? readFileSync(file, "utf8");
  } catch {
    report(
      state,
      make_error(CODES.module_not_found, `no se puede leer «${file}»`, {
        file,
        start: { line: 1, column: 1, offset: 0 },
        end: { line: 1, column: 1, offset: 0 },
      }),
    );
    return undefined;
  }

  const source = make_source(file, text);
  const parse = parse_text(file, text);
  for (const diagnostic of parse.diagnostics) report(state, diagnostic);

  const sink = make_sink({ max: 200 });
  const info = collect_module(file, parse.program, sink);
  for (const diagnostic of sink.diagnostics) report(state, diagnostic);

  state.visiting.add(file);

  const imports = new Map<string, LoadedModule>();
  const imports_by_alias = new Map<string, LoadedModule>();
  for (const [alias, imported] of info.imports) {
    const resolved = resolve_module_file(file, imported.path, state.root);
    if (resolved === undefined && imported.path.startsWith("std/")) {
      // Sin archivo .d.pengu: la firma la aporta el checker (intrínseca).
      continue;
    }
    if (resolved === undefined) {
      report(
        state,
        make_error(
          CODES.module_not_found,
          `no se encuentra el módulo «${imported.path}»`,
          imported.span,
          `se buscó «${imported.path}.pengu», «${imported.path}.d.pengu» y «${imported.path}/index.pengu»`,
        ),
      );
      continue;
    }
    const child = load_one(state, resolved);
    if (child === undefined) continue;
    imports_by_alias.set(alias, child);
    // Sin `as`, el módulo se importa con el nombre de su realm.
    imports.set(imported.explicit ? alias : child.info.realm, child);
  }

  const selective = new Map<string, SelectiveImport>();
  for (const [alias, imported] of info.imports) {
    if (imported.items === undefined) continue;
    const child = imports_by_alias.get(alias);
    if (child === undefined) continue;
    for (const name of imported.items) {
      if (symbol_type_of(child.info, name) === undefined && !child.info.env.runes.has(name) && !child.info.env.omens.has(name) && !child.info.env.aliases.has(name)) {
        report(
          state,
          make_error(CODES.unknown_identifier, `el módulo «${alias}» no exporta «${name}»`, imported.span),
        );
        continue;
      }
      selective.set(name, { module: child, name });
    }
  }

  state.visiting.delete(file);

  const module: LoadedModule = { file, program: parse.program, info, imports, selective };
  state.loaded.set(file, module);
  state.order.push(module);
  void source;
  return module;
}

export function load_graph(entry_file: string, options: LoadOptions = {}): ModuleGraph {
  const root = find_project_root(dirname(entry_file));
  const state: LoadState = {
    loaded: new Map(),
    visiting: new Set(),
    order: [],
    diagnostics: [],
    by_file: new Map(),
    root,
    read_file: options.read_file,
  };
  const entry = load_one(state, entry_file);
  check_realm_collisions(state);
  merge_realm_envs(state);
  return {
    entry,
    order: state.order,
    diagnostics: state.diagnostics,
    by_file: state.by_file,
  };
}
