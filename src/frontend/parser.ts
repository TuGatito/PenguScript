// Punto de entrada del parser: fuente → tokens → AST.

import type { Source } from "../util/span.ts";
import { make_source } from "../util/span.ts";
import type { Diagnostic } from "../diagnostics/diagnostic.ts";
import { lex } from "./lexer.ts";
import { make_cursor } from "./parser_cursor.ts";
import { parse_program } from "./parser_decl.ts";
import type { Program } from "./ast.ts";

export interface ParseResult {
  readonly program: Program;
  readonly diagnostics: readonly Diagnostic[];
}

// Analiza una fuente ya cargada.
export function parse(source: Source): ParseResult {
  const lexed = lex(source);
  const diagnostics: Diagnostic[] = [];
  const cursor = make_cursor(lexed.tokens, source.file, diagnostics);
  const program = parse_program(cursor);

  const all = [...lexed.diagnostics, ...diagnostics].sort(
    (a, b) => a.span.start.offset - b.span.start.offset,
  );

  return { program, diagnostics: all };
}

// Analiza un texto suelto (útil para tests y para el LSP).
export function parse_text(file: string, text: string): ParseResult {
  return parse(make_source(file, text));
}
