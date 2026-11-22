// Inlay hints, tokens semánticos y regiones plegables.

import { lex_text } from "../frontend/lexer.ts";
import type { StmtNode } from "../frontend/ast_stmt.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import type { PenguType } from "../semantic/types.ts";
import { type_display } from "../semantic/types.ts";
import { is_builtin_type_name } from "../frontend/ast_type.ts";
import { INT } from "../semantic/types.ts";
import type { FileAnalysis } from "./project.ts";
import { span_to_source, to_lsp_range } from "./features.ts";

const INT_TYPE = INT;

export interface InlayHint {
  readonly position: { readonly line: number; readonly character: number };
  readonly label: string;
  readonly kind: number;
  readonly paddingLeft?: boolean;
}

const HINT_TYPE = 1;

// Tipos inferidos que no se escribieron: `x = 5` muestra `x: int`.
export function inlay_hints(file: FileAnalysis): InlayHint[] {
  const hints: InlayHint[] = [];
  const visit = (value: unknown): void => {
    if (Array.isArray(value)) {
      for (const item of value) visit(item);
      return;
    }
    if (typeof value !== "object" || value === null) return;
    const node = value as { readonly kind?: string };
    if (node.kind === "assign") {
      add_assignment_hint(file, node as StmtNode & { readonly kind: "assign" }, hints);
    } else if (node.kind === "const_stmt") {
      add_const_hint(file, node as StmtNode & { readonly kind: "const_stmt" }, hints);
    } else if (node.kind === "for_numeric" || node.kind === "for_iter") {
      add_for_hint(file, node as ExprNode, hints);
    }
    for (const key of Object.keys(node)) visit((node as Record<string, unknown>)[key]);
  };
  visit(file.program);
  return hints;
}

function add_assignment_hint(file: FileAnalysis, node: { readonly declared_type?: unknown; readonly targets: readonly ExprNode[]; readonly span: { readonly file: string; readonly start: { readonly offset: number }; readonly end: { readonly offset: number } } }, hints: InlayHint[]): void {
  if (node.declared_type !== undefined) return;
  const target = node.targets[0];
  if (target === undefined || target.kind !== "ident" || node.targets.length !== 1) return;
  const type = file.analysis.types.get(target);
  if (type === undefined) return;
  hints.push(hint_at(file, target.span.end.offset, type));
}

function add_const_hint(file: FileAnalysis, node: { readonly declared_type?: unknown; readonly value: ExprNode }, hints: InlayHint[]): void {
  if (node.declared_type !== undefined) return;
  const type = file.analysis.types.get(node.value);
  if (type === undefined) return;
  hints.push(hint_at(file, node.value.span.end.offset, type));
}

function add_for_hint(file: FileAnalysis, node: ExprNode, hints: InlayHint[]): void {
  if (node.kind !== "for_numeric" || node.variable_type !== undefined) return;
  const offset = file.source.text.indexOf(node.variable, node.span.start.offset);
  if (offset < 0) return;
  hints.push(hint_at(file, offset + node.variable.length, INT_TYPE));
}

function hint_at(file: FileAnalysis, offset: number, type: PenguType): InlayHint {
  return { position: to_position(file, offset), label: `: ${type_display(type)}`, kind: HINT_TYPE, paddingLeft: false };
}

function to_position(file: FileAnalysis, offset: number): { line: number; character: number } {
  const span = span_to_source(file.source, offset, offset);
  return to_lsp_range(file.source, span).start;
}

// Tokens semánticos: leyenda fija y deltas por línea.
export const TOKEN_TYPES: readonly string[] = [
  "namespace", "type", "function", "method", "property", "variable",
  "parameter", "keyword", "string", "number", "comment", "operator", "enumMember",
];

export interface SemanticTokens {
  readonly data: readonly number[];
}

export function semantic_tokens(file: FileAnalysis): SemanticTokens {
  const lexed = lex_text(file.file, file.source.text);
  const data: number[] = [];
  let previous_line = 0;
  let previous_character = 0;
  const file_symbols = new Map<string, string>();
  for (const symbol of file.analysis.locals) file_symbols.set(`${symbol.span.start.offset}`, "parameter");
  for (const [name, fn] of file.module.functions) file_symbols.set(`${fn.span.start.offset}`, "function");
  for (const [name, rune] of file.module.env.runes) file_symbols.set(`${rune.span.start.offset}`, "type");
  for (const [name, omen] of file.module.env.omens) file_symbols.set(`${omen.span.start.offset}`, "type");

  for (const token of lexed.tokens) {
    if (token.kind === "newline" || token.kind === "indent" || token.kind === "dedent" || token.kind === "eof") continue;
    const type = token_type(file, token.kind, token.text);
    if (type === undefined) continue;
    const range = to_lsp_range(file.source, token.span);
    const line = range.start.line;
    const character = range.start.character;
    const length = Math.max(1, token.span.end.offset - token.span.start.offset);
    if (line !== previous_line) {
      data.push(line - previous_line, character, length, TOKEN_TYPES.indexOf(type), 0);
      previous_character = character;
    } else {
      data.push(0, character - previous_character, length, TOKEN_TYPES.indexOf(type), 0);
      previous_character = character;
    }
    previous_line = line;
  }
  return { data };
}

function token_type(file: FileAnalysis, kind: string, text: string): string | undefined {
  if (kind === "comment") return "comment";
  if (kind === "string" || kind === "char") return "string";
  if (kind === "int" || kind === "float") return "number";
  if (kind === "keyword") return "keyword";
  if (kind === "ident") {
    const symbol = symbol_at_offset(file, text);
    if (symbol !== undefined) return symbol;
    if (is_builtin_type_name(text)) return "type";
    return "variable";
  }
  return "operator";
}

function symbol_at_offset(file: FileAnalysis, name: string): string | undefined {
  if (file.module.functions.has(name)) return "function";
  if (file.module.env.runes.has(name)) return "type";
  if (file.module.env.omens.has(name)) return "type";
  if (file.module.env.aliases.has(name)) return "type";
  return undefined;
}

export interface FoldingRange {
  readonly startLine: number;
  readonly endLine: number;
}

// Cada INDENT se pliega hasta su DEDENT.
export function folding_ranges(file: FileAnalysis): FoldingRange[] {
  const ranges: FoldingRange[] = [];
  const indents: number[] = [];
  for (const token of lex_text(file.file, file.source.text).tokens) {
    const line = to_lsp_range(file.source, token.span).start.line;
    if (token.kind === "indent") indents.push(line);
    else if (token.kind === "dedent") {
      const start = indents.pop();
      if (start === undefined) continue;
      if (line - 1 > start) ranges.push({ startLine: start, endLine: line - 1 });
    }
  }
  return ranges;
}
