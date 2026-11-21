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
import { collect_module } from "../semantic/module_info.ts";
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
}

interface LoadState {
  readonly loaded: Map<string, LoadedModule>;
  readonly visiting: Set<string>;
  readonly order: LoadedModule[];
  readonly diagnostics: Diagnostic[];
  readonly root: string;
}

function load_one(state: LoadState, file: string): LoadedModule | undefined {
  const cached = state.loaded.get(file);
  if (cached !== undefined) return cached;

  if (state.visiting.has(file)) {
    state.diagnostics.push(
      make_error(CODES.import_cycle, `ciclo de importaciones en «${file}»`, {
        file,
        start: { line: 1, column: 1, offset: 0 },
        end: { line: 1, column: 1, offset: 0 },
      }),
    );
    return undefined;
  }

  let text: string;
  try {
    text = readFileSync(file, "utf8");
  } catch {
    state.diagnostics.push(
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
  state.diagnostics.push(...parse.diagnostics);

  const sink = make_sink({ max: 200 });
  const info = collect_module(file, parse.program, sink);
  state.diagnostics.push(...sink.diagnostics);

  state.visiting.add(file);

  const imports = new Map<string, LoadedModule>();
  for (const [alias, imported] of info.imports) {
    const resolved = resolve_module_file(file, imported.path, state.root);
    if (resolved === undefined && imported.path.startsWith("std/")) {
      // Sin archivo .d.pengu: la firma la aporta el checker (intrínseca).
      continue;
    }
    if (resolved === undefined) {
      state.diagnostics.push(
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
    if (child !== undefined) imports.set(alias, child);
  }

  const selective = new Map<string, SelectiveImport>();
  for (const [alias, imported] of info.imports) {
    if (imported.items === undefined) continue;
    const child = imports.get(alias);
    if (child === undefined) continue;
    for (const name of imported.items) {
      if (symbol_type_of(child.info, name) === undefined && !child.info.env.runes.has(name) && !child.info.env.omens.has(name) && !child.info.env.aliases.has(name)) {
        state.diagnostics.push(
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

export function load_graph(entry_file: string): ModuleGraph {
  const root = find_project_root(dirname(entry_file));
  const state: LoadState = {
    loaded: new Map(),
    visiting: new Set(),
    order: [],
    diagnostics: [],
    root,
  };
  const entry = load_one(state, entry_file);
  return {
    entry,
    order: state.order,
    diagnostics: state.diagnostics,
  };
}
