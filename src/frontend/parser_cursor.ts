// Cursor de tokens para el parser.
//
// Encapsula el avance sobre la lista de tokens, el manejo de
// comentarios (que son trivia) y la deuda de `>` partidos: en
// `vector<vector<int>>` el lexer produce un solo token `>>` y el
// parser de tipos lo reparte entre dos cierres.

import type { Diagnostic } from "../diagnostics/diagnostic.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { Token, TokenKind } from "./token.ts";
import type { Span } from "../util/span.ts";

export interface Cursor {
  readonly tokens: readonly Token[];
  readonly file: string;
  readonly diagnostics: Diagnostic[];
  index: number;
  angle_debt: number;
}

export function make_cursor(
  tokens: readonly Token[],
  file: string,
  diagnostics: Diagnostic[] = [],
): Cursor {
  return { tokens, file, diagnostics, index: 0, angle_debt: 0 };
}

export function cursor_eof(c: Cursor): Token {
  const last = c.tokens[c.tokens.length - 1];
  if (last && last.kind === "eof") return last;
  const fallback = c.tokens[c.tokens.length - 1];
  const span = fallback?.span ?? {
    file: c.file,
    start: { line: 1, column: 1, offset: 0 },
    end: { line: 1, column: 1, offset: 0 },
  };
  return { kind: "eof", text: "", span };
}

export function peek(c: Cursor, offset = 0): Token {
  let i = c.index;
  let seen = 0;
  while (i < c.tokens.length) {
    const token = c.tokens[i];
    if (!token) break;
    if (token.kind === "comment") {
      i++;
      continue;
    }
    if (seen === offset) return token;
    seen++;
    i++;
  }
  return cursor_eof(c);
}

export function peek_kind(c: Cursor, offset = 0): TokenKind {
  return peek(c, offset).kind;
}

export function advance(c: Cursor): Token {
  while (c.index < c.tokens.length) {
    const token = c.tokens[c.index];
    if (!token) break;
    if (token.kind === "comment") {
      c.index++;
      continue;
    }
    if (token.kind === "eof") return token;
    c.index++;
    return token;
  }
  return cursor_eof(c);
}

export function at(c: Cursor, kind: TokenKind): boolean {
  return peek(c).kind === kind;
}

export function at_any(c: Cursor, kinds: readonly TokenKind[]): boolean {
  const kind = peek(c).kind;
  return kinds.includes(kind);
}

export function eat(c: Cursor, kind: TokenKind): Token | undefined {
  if (!at(c, kind)) return undefined;
  return advance(c);
}

export function expect(c: Cursor, kind: TokenKind, context: string): Token | undefined {
  const token = peek(c);
  if (token.kind === kind) return advance(c);
  push_error(
    c,
    CODES.expected_token,
    `se esperaba «${kind}» ${context}, se encontró «${describe(c, token)}»`,
    token.span,
  );
  return undefined;
}

export function expect_ident(c: Cursor, context: string): Token | undefined {
  const token = peek(c);
  if (token.kind === "ident") return advance(c);
  push_error(
    c,
    CODES.expected_token,
    `se esperaba un identificador ${context}, se encontró «${describe(c, token)}»`,
    token.span,
  );
  return undefined;
}

export function push_error(
  c: Cursor,
  code: string,
  message: string,
  span: Span,
  ...notes: string[]
): void {
  c.diagnostics.push(make_error(code, message, span, ...notes));
}

export function describe(c: Cursor, token: Token): string {
  if (token.kind === "eof") return "fin de archivo";
  if (token.kind === "newline") return "fin de línea";
  if (token.kind === "indent") return "sangría";
  if (token.kind === "dedent") return "fin de bloque";
  return token.text;
}

export function skip_comments(c: Cursor): void {
  while (c.index < c.tokens.length && c.tokens[c.index]?.kind === "comment") {
    c.index++;
  }
}

export function skip_newlines(c: Cursor): void {
  while (at(c, "newline")) advance(c);
}

export function expect_newline(c: Cursor, context: string): void {
  if (at(c, "newline")) {
    advance(c);
    return;
  }
  if (at(c, "eof") || at(c, "dedent")) return;
  const token = peek(c);
  push_error(
    c,
    CODES.unexpected_token,
    `se esperaba fin de línea ${context}, se encontró «${describe(c, token)}»`,
    token.span,
  );
  synchronize(c);
}

// Consume el separador entre elementos de una lista (declaraciones,
// sentencias, campos). El lexer puede haber consumido ya el NEWLINE
// cuando el elemento anterior terminaba en bloque indentado, así que
// aceptamos también que el siguiente token empiece en una línea nueva.
export function accept_line_break(c: Cursor, previous_end: Span, context: string): void {
  if (at(c, "newline")) {
    advance(c);
    return;
  }
  if (at(c, "dedent") || at(c, "eof")) return;
  if (peek(c).span.start.line > previous_end.end.line) return;

  push_error(
    c,
    CODES.unexpected_token,
    `se esperaba fin de línea ${context}, se encontró «${describe(c, peek(c))}»`,
    peek(c).span,
  );
  synchronize(c);
}

export function synchronize(c: Cursor): void {
  while (!at(c, "eof") && !at(c, "dedent") && !at(c, "newline")) {
    advance(c);
  }
  if (at(c, "newline")) advance(c);
}

export function merge_span(a: Span, b: Span): Span {
  return {
    file: a.file,
    start: a.start.offset <= b.start.offset ? a.start : b.start,
    end: a.end.offset >= b.end.offset ? a.end : b.end,
  };
}

export function mark(c: Cursor): number {
  return c.index;
}

export function rewind(c: Cursor, saved: { index: number; diagnostics: number; angle_debt: number }): void {
  c.index = saved.index;
  c.diagnostics.length = saved.diagnostics;
  c.angle_debt = saved.angle_debt;
}

export function save(c: Cursor): { index: number; diagnostics: number; angle_debt: number } {
  return { index: c.index, diagnostics: c.diagnostics.length, angle_debt: c.angle_debt };
}
