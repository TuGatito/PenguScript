// Finalización: ámbito actual, módulos importados, `std`, miembros de
// runes y métodos enhechizados.

import type { PenguType } from "../semantic/types.ts";
import { type_display } from "../semantic/types.ts";
import { builtin_member_names, member_of_builtin } from "../semantic/builtin_members.ts";
import { receiver_shape } from "../semantic/checker_enchants.ts";
import { PRIMITIVE_TYPES, STRING_TYPES } from "../frontend/ast_type.ts";
import { find_rune_field, find_rune_method } from "../semantic/type_env.ts";
import type { Symbol } from "../semantic/symbols.ts";
import { visible_at } from "../semantic/symbols.ts";
import type { FileAnalysis, ProjectState } from "./project.ts";
import { receiver_before, signature_of, type_before, visible_symbols } from "./features.ts";
import { COMPLETION_KIND } from "./protocol.ts";

export interface CompletionItem {
  readonly label: string;
  readonly kind: number;
  readonly detail?: string;
  readonly documentation?: string;
  readonly insertText?: string;
  readonly sortText?: string;
}

export function completions_at(project: ProjectState, file: FileAnalysis, offset: number): CompletionItem[] {
  const receiver = receiver_before(file.source.text, offset);
  if (receiver !== undefined) {
    if (receiver.separator === ".") {
      const members = member_completions(file, receiver.offset);
      if (members.length > 0) return members;
    } else {
      const paths = path_completions(project, file, receiver.name);
      if (paths.length > 0) return paths;
    }
  }
  if (type_context(file.source.text, offset)) return type_completions(project, file);

  return scope_completions(project, file, offset);
}

// `x: `, `-> `, `ref<`, `optional<`… piden un tipo, no un valor.
function type_context(text: string, offset: number): boolean {
  const before = text.slice(0, offset);
  return /(:\s*|->\s*|<\s*|,\s*)$/.test(before) && !/[=(,]\s*$/.test(before.replace(/:\s*$/, ""));
}

function type_completions(project: ProjectState, file: FileAnalysis): CompletionItem[] {
  const items: CompletionItem[] = [];
  const push = (label: string, detail: string | undefined, insertText?: string): void => {
    if (items.some((item) => item.label === label)) return;
    items.push({ label, kind: COMPLETION_KIND.type, detail, insertText, sortText: `0${label}` });
  };
  for (const name of PRIMITIVE_TYPE_NAMES) push(name, "primitivo");
  for (const name of file.module.env.runes.keys()) push(name, "rune");
  for (const name of file.module.env.omens.keys()) push(name, "omen");
  for (const name of file.module.env.aliases.keys()) push(name, "alias");
  push("vector<T>", "contenedor", "vector<${1:int}>");
  push("map<K, V>", "mapa", "map<${1:string}, ${2:int}>");
  push("set<T>", "conjunto", "set<${1:int}>");
  push("optional<T>", "opcional", "optional<${1:int}>");
  push("T?", "azúcar de optional");
  return items;
}

function scope_completions(project: ProjectState, file: FileAnalysis, offset: number): CompletionItem[] {
  const items: CompletionItem[] = [];
  const own_file = file.file;
  const own_realm = file.module.realm;

  for (const symbol of visible_symbols(project, file, offset)) {
    const is_local = symbol.scope !== undefined;
    const is_own = symbol.file === own_file;
    items.push({
      label: symbol.name,
      kind: completion_kind(symbol),
      detail: signature_of(symbol),
      documentation: symbol.docs,
      insertText: symbol.kind === "function" ? `${symbol.name}(` : undefined,
      sortText: is_local ? `0${symbol.name}` : is_own || symbol.realm === own_realm ? `1${symbol.name}` : `2${symbol.name}`,
    });
  }

  for (const keyword of KEYWORDS_FOR_COMPLETION) {
    if (items.some((item) => item.label === keyword)) continue;
    items.push({ label: keyword, kind: COMPLETION_KIND.keyword, sortText: `8${keyword}` });
  }

  for (const alias of file.analysis.imports.keys()) {
    if (items.some((item) => item.label === alias)) continue;
    items.push({ label: alias, kind: COMPLETION_KIND.module, sortText: `3${alias}` });
  }

  return items;
}

function completion_kind(symbol: Symbol): number {
  switch (symbol.kind) {
    case "function":
      return COMPLETION_KIND.function;
    case "rune":
    case "omen":
    case "seal":
    case "echo":
      return COMPLETION_KIND.class;
    case "variant":
      return COMPLETION_KIND.enum_member;
    case "field":
    case "method":
      return COMPLETION_KIND.method;
    default:
      return COMPLETION_KIND.variable;
  }
}

function member_completions(file: FileAnalysis, receiver_offset: number): CompletionItem[] {
  const type = type_before(file, receiver_offset);
  if (type === undefined) return [];
  const items: CompletionItem[] = [];
  const push = (label: string, detail: string | undefined, documentation: string | undefined): void => {
    if (items.some((item) => item.label === label)) return;
    items.push({ label, kind: COMPLETION_KIND.method, detail, documentation, sortText: `0${label}` });
  };

  // Primero lo que aporta el propio código (enhechizamientos y runes),
  // después los miembros incorporados del tipo.
  const shape = receiver_shape(type);
  const key = shape === undefined ? undefined : `${shape.base}/${shape.arity}`;
  const enchanted_sets = key === undefined
    ? []
    : [file.module.env.enchants.get(key), file.analysis.enchants.get(key)];
  for (const enchanted of enchanted_sets) {
    if (enchanted === undefined) continue;
    for (const [name, methods] of enchanted.methods) {
      const method = methods[0];
      if (method === undefined) continue;
      const params = method.info.params.map((param) => type_display(param)).join(", ");
      push(name, `(${params}) -> ${type_display(method.info.result)}`, `realm ${method.realm}`);
    }
  }

  if (type.kind === "named") {
    const rune = file.module.env.runes.get(type.name);
    if (rune !== undefined) add_rune_members(file, rune.name, push);
  }

  for (const name of builtin_member_names(type)) {
    const member = member_of_builtin(type, name);
    push(name, member === undefined ? undefined : type_display(member), undefined);
  }

  return items;
}

function add_rune_members(
  file: FileAnalysis,
  rune_name: string,
  push: (label: string, detail: string | undefined, documentation: string | undefined) => void,
): void {
  const rune = file.module.env.runes.get(rune_name);
  if (rune === undefined) return;
  for (const [name, field] of rune.fields) push(name, type_display(field.type), undefined);
  for (const [name, method] of rune.methods) {
    const params = method.params.map((param) => type_display(param)).join(", ");
    push(method.operator ?? name, `(${params}) -> ${type_display(method.result)}`, method.mutable ? "mut" : undefined);
  }
  const parent = rune.parent;
  if (parent !== undefined) add_rune_members(file, parent, push);
}

function path_completions(project: ProjectState, file: FileAnalysis, name: string): CompletionItem[] {
  const omen = file.module.env.omens.get(name);
  if (omen !== undefined) {
    const items: CompletionItem[] = [];
    for (const [variant, info] of omen.variants) {
      const detail = info.payload.length === 0 ? undefined : `(${info.payload.map((param) => type_display(param)).join(", ")})`;
      items.push({ label: variant, kind: COMPLETION_KIND.enum_member, detail, sortText: `0${variant}` });
    }
    return items;
  }

  const alias = file.module.env.aliases.get(name);
  if (alias !== undefined) {
    return project.index.by_name.size === 0 ? [] : alias_methods(alias, project, file);
  }

  const imported = file.analysis.imports.get(name);
  if (imported !== undefined) {
    return module_members(project, imported.module.file);
  }

  const realm_symbols = project.index.symbols.filter((symbol) => symbol.realm === name && symbol.scope === undefined);
  return realm_symbols.map((symbol) => ({
    label: symbol.name,
    kind: completion_kind(symbol),
    detail: signature_of(symbol),
    documentation: symbol.docs,
    sortText: `0${symbol.name}`,
  }));
}

function alias_methods(alias: { readonly methods: ReadonlyMap<string, { readonly params: readonly PenguType[]; readonly result: PenguType }> }, project: ProjectState, file: FileAnalysis): CompletionItem[] {
  void project;
  void file;
  const items: CompletionItem[] = [];
  for (const [name, method] of alias.methods) {
    const params = method.params.map((param) => type_display(param)).join(", ");
    items.push({ label: name, kind: COMPLETION_KIND.method, detail: `(${params}) -> ${type_display(method.result)}` });
  }
  return items;
}

function module_members(project: ProjectState, module_file: string): CompletionItem[] {
  const items: CompletionItem[] = [];
  for (const symbol of project.index.by_file.get(module_file) ?? []) {
    if (symbol.scope !== undefined || symbol.kind === "realm" || symbol.kind === "constructor") continue;
    items.push({
      label: symbol.name,
      kind: completion_kind(symbol),
      detail: signature_of(symbol),
      documentation: symbol.docs,
      sortText: `0${symbol.name}`,
    });
  }
  return items;
}

const PRIMITIVE_TYPE_NAMES: readonly string[] = [...PRIMITIVE_TYPES, ...STRING_TYPES].filter((name) => name !== "void");

const KEYWORDS_FOR_COMPLETION: readonly string[] = [
  "realm", "invoke", "from", "as", "rune", "omen", "flags", "echo", "seal", "enchanting",
  "heir", "constructor", "destructor", "parent", "declare", "extern", "unsafe", "mut", "const",
  "static", "needs", "operator", "if", "unless", "else", "then", "switch", "when", "match",
  "do", "while", "until", "repeat", "for", "in", "break", "continue", "return", "pass",
  "true", "false", "none", "nullptr", "and", "or", "not", "async", "await",
];

// Para el resaltado de miembros se reutilizan los símbolos visibles del
// propio archivo cuando el receptor no tiene tipo anotado.
export function fallback_member_items(project: ProjectState, file: FileAnalysis, offset: number): CompletionItem[] {
  return visible_at(project.index, offset)
    .filter((symbol) => symbol.file === file.file)
    .map((symbol) => ({ label: symbol.name, kind: completion_kind(symbol), detail: signature_of(symbol) }));
}
