// Índice de símbolos del proyecto.
//
// El índice es la base de todo lo que el LSP responde: hover, definición,
// referencias, renombrado y autocompletado. Se construye a partir de la
// información que ya calcula el checker (módulos, tipos y locales), sin
// volver a analizar nada.

import type { Span, Source } from "../util/span.ts";
import { function_type_of } from "./module_info.ts";
import type { ModuleInfo, FunctionInfo } from "./module_info.ts";
import type { PenguType } from "./types.ts";
import { type_display } from "./types.ts";
import { docs_before } from "./docs.ts";

export type SymbolKind =
  | "function"
  | "const"
  | "variable"
  | "parameter"
  | "field"
  | "method"
  | "constructor"
  | "rune"
  | "omen"
  | "variant"
  | "echo"
  | "seal"
  | "realm"
  | "module";

export interface Symbol {
  readonly id: string;
  readonly name: string;
  readonly kind: SymbolKind;
  readonly type: PenguType | undefined;
  readonly signature: string | undefined;
  readonly docs: string | undefined;
  readonly file: string;
  /** Declaración: lo que muestran el hover y la definición. */
  readonly span: Span;
  /** Ámbito donde el símbolo es visible; `undefined` si es de módulo. */
  readonly scope: Span | undefined;
  readonly container: string | undefined;
  readonly mutable: boolean;
  /** Realm al que pertenece (para `std` y módulos importados). */
  readonly realm: string;
}

export interface SymbolIndex {
  readonly symbols: readonly Symbol[];
  readonly by_name: ReadonlyMap<string, readonly Symbol[]>;
  readonly by_file: ReadonlyMap<string, readonly Symbol[]>;
}

export interface LocalSymbol {
  readonly name: string;
  readonly type: PenguType;
  readonly mutable: boolean;
  readonly kind: "parameter" | "variable";
  readonly span: Span;
  readonly scope: Span;
}

export function make_symbol_index(symbols: readonly Symbol[]): SymbolIndex {
  const by_name = new Map<string, Symbol[]>();
  const by_file = new Map<string, Symbol[]>();
  for (const symbol of symbols) {
    const named = by_name.get(symbol.name);
    if (named === undefined) by_name.set(symbol.name, [symbol]);
    else named.push(symbol);
    const filed = by_file.get(symbol.file);
    if (filed === undefined) by_file.set(symbol.file, [symbol]);
    else filed.push(symbol);
  }
  return { symbols, by_name, by_file };
}

// Firma legible: `nombre = (a: int, b: string = "x") -> bool`.
export function render_function_signature(fn: FunctionInfo): string {
  const params = fn.params.map((param) => {
    const name = `${param.mutable ? "mut " : ""}${param.variadic ? "..." : ""}${param.name}`;
    const typed = param.type === undefined ? name : `${name}: ${type_display(param.type)}`;
    return param.has_default ? `${typed} = …` : typed;
  });
  return `${fn.name} = (${params.join(", ")}) -> ${type_display(fn.result)}`;
}

export function render_method_signature(name: string, params: readonly PenguType[], result: PenguType, mutable: boolean, variadic = false): string {
  const rendered = params.map((param, index) => {
    const prefix = variadic && index === params.length - 1 ? "..." : "";
    return `${prefix}valor${index}: ${type_display(param)}`;
  });
  return `${mutable ? "mut " : ""}${name} = (${rendered.join(", ")}) -> ${type_display(result)}`;
}

// Símbolos de un módulo ya recolectado. `source` es opcional: si no está,
// el símbolo no lleva documentación (caso de módulos importados).
export function module_symbols(file: string, module: ModuleInfo, source?: Source): Symbol[] {
  const symbols: Symbol[] = [];
  const realm = module.realm;
  const docs_at = (span: Span): string | undefined => (source === undefined ? undefined : docs_before(source, span.start.offset));

  symbols.push({
    id: `module:${file}:realm`,
    name: realm,
    kind: "realm",
    type: undefined,
    signature: `realm ${realm}`,
    docs: undefined,
    file,
    span: first_span(module),
    scope: undefined,
    container: undefined,
    mutable: false,
    realm,
  });

  for (const [name, fn] of module.functions) {
    symbols.push({
      id: `module:${file}:function:${name}`,
      name,
      kind: "function",
      type: function_type_of(fn),
      signature: render_function_signature(fn),
      docs: docs_at(fn.span),
      file,
      span: fn.span,
      scope: undefined,
      container: `realm ${realm}`,
      mutable: false,
      realm,
    });
  }

  for (const [name, constant] of module.consts) {
    symbols.push({
      id: `module:${file}:const:${name}`,
      name,
      kind: "const",
      type: constant.type,
      signature: `${constant.mutable ? "static mut " : "const "}${name}: ${type_display(constant.type)}`,
      docs: docs_at(constant.span),
      file,
      span: constant.span,
      scope: undefined,
      container: `realm ${realm}`,
      mutable: constant.mutable,
      realm,
    });
  }

  for (const [name, rune] of module.env.runes) {
    symbols.push({
      id: `module:${file}:rune:${name}`,
      name,
      kind: "rune",
      type: undefined,
      signature: `rune ${name}${sigil_suffix(rune.sigils)}`,
      docs: docs_at(rune.span),
      file,
      span: rune.span,
      scope: undefined,
      container: `realm ${realm}`,
      mutable: false,
      realm,
    });
    for (const [field, info] of rune.fields) {
      symbols.push({
        id: `module:${file}:field:${name}.${field}`,
        name: field,
        kind: "field",
        type: info.type,
        signature: `${field}: ${type_display(info.type)}`,
        docs: docs_at(info.span),
        file,
        span: info.span,
        scope: undefined,
        container: `rune ${name}`,
        mutable: false,
        realm,
      });
    }
    for (const [method, info] of rune.methods) {
      symbols.push({
        id: `module:${file}:method:${name}.${method}`,
        name: method,
        kind: "method",
        type: undefined,
        signature: render_method_signature(info.operator ?? method, info.params, info.result, info.mutable, info.variadic),
        docs: docs_at(info.span),
        file,
        span: info.span,
        scope: undefined,
        container: `rune ${name}`,
        mutable: info.mutable,
        realm,
      });
    }
    if (rune.constructor !== undefined) {
      symbols.push({
        id: `module:${file}:constructor:${name}`,
        name: "constructor",
        kind: "constructor",
        type: undefined,
        signature: `constructor(${rune.constructor.params.map((param) => type_display(param)).join(", ")})`,
        docs: docs_at(rune.constructor.span),
        file,
        span: rune.constructor.span,
        scope: undefined,
        container: `rune ${name}`,
        mutable: false,
        realm,
      });
    }
  }

  for (const [name, omen] of module.env.omens) {
    symbols.push({
      id: `module:${file}:omen:${name}`,
      name,
      kind: "omen",
      type: undefined,
      signature: `${omen.is_flags ? "flags omen" : "omen"} ${name}${sigil_suffix(omen.sigils)}`,
      docs: docs_at(omen.span),
      file,
      span: omen.span,
      scope: undefined,
      container: `realm ${realm}`,
      mutable: false,
      realm,
    });
    for (const [variant, info] of omen.variants) {
      symbols.push({
        id: `module:${file}:variant:${name}.${variant}`,
        name: variant,
        kind: "variant",
        type: info.payload.length === 0 ? undefined : info.payload[0],
        signature: info.payload.length === 0 ? `${name}::${variant}` : `${name}::${variant}(${info.payload.map((p) => type_display(p)).join(", ")})`,
        docs: docs_at(info.span),
        file,
        span: info.span,
        scope: undefined,
        container: `omen ${name}`,
        mutable: false,
        realm,
      });
    }
  }

  for (const [name, alias] of module.env.aliases) {
    symbols.push({
      id: `module:${file}:${alias.seal ? "seal" : "echo"}:${name}`,
      name,
      kind: alias.seal ? "seal" : "echo",
      type: alias.target,
      signature: `${alias.seal ? "seal" : "echo"} ${name} = ${type_display(alias.target)}`,
      docs: docs_at(alias.span),
      file,
      span: alias.span,
      scope: undefined,
      container: `realm ${realm}`,
      mutable: false,
      realm,
    });
  }

  return symbols;
}

export function local_symbols(file: string, locals: readonly LocalSymbol[], realm: string): Symbol[] {
  return locals.map((local) => ({
    id: `local:${file}:${local.span.start.offset}`,
    name: local.name,
    kind: local.kind,
    type: local.type,
    signature: `${local.mutable ? "mut " : ""}${local.name}: ${type_display(local.type)}`,
    docs: undefined,
    file,
    span: local.span,
    scope: local.scope,
    container: undefined,
    mutable: local.mutable,
    realm,
  }));
}

function sigil_suffix(sigils: readonly string[]): string {
  return sigils.length === 0 ? "" : `<${sigils.join(", ")}>`;
}

function first_span(module: ModuleInfo): Span {
  for (const fn of module.functions.values()) return fn.span;
  for (const constant of module.consts.values()) return constant.span;
  return { file: "", start: { line: 1, column: 1, offset: 0 }, end: { line: 1, column: 1, offset: 0 } };
}

// Símbolo cuya declaración contiene `offset` (el más pequeño).
export function symbol_at(index: SymbolIndex, offset: number): Symbol | undefined {
  let best: Symbol | undefined;
  for (const symbol of index.symbols) {
    if (offset < symbol.span.start.offset || offset > symbol.span.end.offset) continue;
    if (best === undefined || span_length(symbol.span) < span_length(best.span)) best = symbol;
  }
  return best;
}

// Símbolos visibles en `offset`: locales y parámetros del ámbito actual,
// después los del módulo. Sombreado: gana el ámbito más interno.
export function visible_at(index: SymbolIndex, offset: number): Symbol[] {
  const chosen = new Map<string, Symbol>();
  for (const symbol of index.symbols) {
    if (!is_visible(symbol, offset)) continue;
    const previous = chosen.get(symbol.name);
    if (previous === undefined || scope_length(symbol) < scope_length(previous)) chosen.set(symbol.name, symbol);
  }
  const locals: Symbol[] = [];
  const globals: Symbol[] = [];
  for (const symbol of chosen.values()) {
    if (symbol.scope === undefined) globals.push(symbol);
    else locals.push(symbol);
  }
  locals.sort((left, right) => left.name.localeCompare(right.name));
  globals.sort(compare_globals);
  return [...locals, ...globals];
}

function is_visible(symbol: Symbol, offset: number): boolean {
  if (symbol.scope === undefined) return true;
  if (symbol.span.start.offset > offset) return false;
  return offset >= symbol.scope.start.offset && offset <= symbol.scope.end.offset;
}

function scope_length(symbol: Symbol): number {
  return symbol.scope === undefined ? Number.POSITIVE_INFINITY : span_length(symbol.scope);
}

function span_length(span: Span): number {
  return span.end.offset - span.start.offset;
}

const KIND_ORDER: ReadonlyMap<SymbolKind, number> = new Map([
  ["rune", 0],
  ["omen", 1],
  ["seal", 2],
  ["echo", 3],
  ["function", 4],
  ["const", 5],
  ["variant", 6],
  ["field", 7],
  ["method", 8],
  ["constructor", 9],
  ["module", 10],
  ["realm", 11],
  ["variable", 12],
  ["parameter", 13],
]);

function compare_globals(left: Symbol, right: Symbol): number {
  const by_kind = (KIND_ORDER.get(left.kind) ?? 99) - (KIND_ORDER.get(right.kind) ?? 99);
  if (by_kind !== 0) return by_kind;
  return left.name.localeCompare(right.name);
}
