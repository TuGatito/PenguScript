// Utilidades compartidas por las funciones del LSP: conversión de
// posiciones, receptor de un `.`/`::`, símbolos visibles y docs.

import type { Span, Source } from "../util/span.ts";
import { position_at, span_of } from "../util/span.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import type { PenguType } from "../semantic/types.ts";
import { type_display } from "../semantic/types.ts";
import type { Symbol } from "../semantic/symbols.ts";
import { symbol_at, visible_at } from "../semantic/symbols.ts";
import type { ModuleInfo } from "../semantic/module_info.ts";
import { find_node_at } from "./query.ts";
import type { FileAnalysis, ProjectState } from "./project.ts";

export interface LspRange {
  readonly start: { readonly line: number; readonly character: number };
  readonly end: { readonly line: number; readonly character: number };
}

export function to_lsp_range(source: Source, span: Span): LspRange {
  const start = position_at(source, span.start.offset);
  const end = position_at(source, span.end.offset);
  return {
    start: { line: start.line - 1, character: start.column - 1 },
    end: { line: end.line - 1, character: end.column - 1 },
  };
}

export function to_offset(source: Source, line: number, character: number): number {
  const base = source.line_starts[line] ?? 0;
  return Math.min(base + character, source.text.length);
}

// Identificador bajo el cursor (o el que termina justo antes).
export function ident_at(text: string, offset: number): { readonly name: string; readonly span: Span } | undefined {
  let start = offset;
  let end = offset;
  while (start > 0 && /[A-Za-z0-9_]/.test(text[start - 1] ?? "")) start -= 1;
  while (end < text.length && /[A-Za-z0-9_]/.test(text[end] ?? "")) end += 1;
  if (start === end) return undefined;
  return { name: text.slice(start, end), span: offset_span(start, end) };
}

export function offset_span(start: number, end: number): Span {
  return { file: "", start: { line: 1, column: start + 1, offset: start }, end: { line: 1, column: end + 1, offset: end } };
}

export function span_to_source(source: Source, start: number, end: number): Span {
  return span_of(source, start, end);
}

export interface Receiver {
  readonly kind: "member" | "path";
  readonly name: string;
  /** Offset del nombre del receptor (para resolver su tipo). */
  readonly offset: number;
  /** Lo que hay entre el receptor y el cursor (`.` o `::`). */
  readonly separator: "." | "::";
}

// `xs.`, `Color::`, `realm::` justo antes del cursor (con prefijo a medio
// escribir: `a.co` cuenta como `a.`).
export function receiver_before(text: string, offset: number): Receiver | undefined {
  const before = text.slice(0, offset);
  const double = before.lastIndexOf("::");
  const single = before.lastIndexOf(".");
  if (single < 0 && double < 0) return undefined;
  const separator_end = double > single ? double + 2 : single + 1;
  if (separator_end > before.length) return undefined;
  const tail = before.slice(separator_end);
  if (!/^[A-Za-z0-9_]*$/.test(tail)) return undefined;
  let name_end = separator_end - (double > single ? 2 : 1);
  while (name_end > 0 && /\s/.test(before[name_end - 1] ?? "")) name_end -= 1;
  let name_start = name_end;
  while (name_start > 0 && /[A-Za-z0-9_]/.test(before[name_start - 1] ?? "")) name_start -= 1;
  if (name_start === name_end) return undefined;
  const name = before.slice(name_start, name_end);
  if (!/^[A-Za-z_]/.test(name)) return undefined;
  return {
    kind: double > single ? "path" : "member",
    name,
    offset: name_start,
    separator: double > single ? "::" : ".",
  };
}

export function type_of_node(file: FileAnalysis, node: { readonly kind: string }): PenguType | undefined {
  return file.analysis.types.get(node as ExprNode);
}

// Tipo de la expresión que termina en `offset` (antes del `.` o `::`).
export function type_before(file: FileAnalysis, offset: number): PenguType | undefined {
  const node = find_node_at(file.program, offset);
  if (node === undefined) return undefined;
  return type_of_node(file, node);
}

// Símbolo global del proyecto por nombre dentro de un módulo/realm.
export function symbols_of_realm(project: ProjectState, realm: string): Symbol[] {
  const symbols: Symbol[] = [];
  for (const file of project.files.values()) {
    if (file.module.realm !== realm) continue;
    for (const symbol of project.index.by_file.get(file.file) ?? []) {
      if (symbol.scope === undefined) symbols.push(symbol);
    }
  }
  return symbols;
}

export function symbol_named(project: ProjectState, file: FileAnalysis, name: string, offset: number): Symbol | undefined {
  for (const symbol of visible_symbols(project, file, offset)) {
    if (symbol.name === name) return symbol;
  }
  for (const symbol of project.index.by_name.get(name) ?? []) {
    if (symbol.scope === undefined) return symbol;
  }
  return undefined;
}

export function existing_symbol(project: ProjectState, file: FileAnalysis, offset: number): Symbol | undefined {
  const ident = ident_at(file.source.text, offset);
  if (ident !== undefined) {
    const named = symbol_named(project, file, ident.name, offset);
    if (named !== undefined) return named;
  }
  const local = symbol_at(project.index, offset);
  return local !== undefined && local.file === file.file ? local : undefined;
}

// Símbolos que el programador puede escribir en `offset`: locales del
// ámbito, el módulo propio, los módulos importados y los selectivos.
export function visible_symbols(project: ProjectState, file: FileAnalysis, offset: number): Symbol[] {
  const result: Symbol[] = [];
  const seen = new Set<string>();
  const push = (symbol: Symbol): void => {
    if (seen.has(symbol.name)) return;
    seen.add(symbol.name);
    result.push(symbol);
  };

  for (const symbol of visible_at(project.index, offset)) {
    if (symbol.file !== file.file) continue;
    push(symbol);
  }

  for (const symbol of project.index.by_file.get(file.file) ?? []) {
    if (symbol.scope === undefined && symbol.kind !== "realm" && symbol.kind !== "constructor") push(symbol);
  }

  for (const imported of file.analysis.imports.values()) {
    add_imported(project, imported.module, push);
  }
  for (const [name, symbol] of file.analysis.selective) {
    for (const candidate of project.index.by_file.get(symbol.module.file) ?? []) {
      if (candidate.name === name && candidate.scope === undefined) push(candidate);
    }
  }
  return result;
}

function add_imported(project: ProjectState, module: ModuleInfo, push: (symbol: Symbol) => void): void {
  for (const candidate of project.index.by_file.get(module.file) ?? []) {
    if (candidate.scope === undefined && candidate.kind !== "realm" && candidate.kind !== "constructor") push(candidate);
  }
}

export function signature_of(symbol: Symbol): string {
  if (symbol.signature !== undefined) return symbol.signature;
  if (symbol.type !== undefined) return `${symbol.name}: ${type_display(symbol.type)}`;
  return symbol.name;
}
