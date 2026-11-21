// Análisis de un documento abierto en el editor.

import { make_sink } from "../diagnostics/sink.ts";
import type { Diagnostic } from "../diagnostics/diagnostic.ts";
import { parse_text } from "../frontend/parser.ts";
import type { Program } from "../frontend/ast.ts";
import { check_program } from "../semantic/checker.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import type { PenguType } from "../semantic/types.ts";
import type { ModuleInfo } from "../semantic/module_info.ts";
import type { MethodTarget } from "../semantic/type_env.ts";
import { make_source, span_from, type Source } from "../util/span.ts";

export interface Analysis {
  readonly file: string;
  readonly source: Source;
  readonly program: Program;
  readonly module: ModuleInfo;
  readonly types: Map<ExprNode, PenguType>;
  readonly member_targets: Map<ExprNode, MethodTarget>;
  readonly diagnostics: readonly Diagnostic[];
}

export function analysis_file_name(uri: string): string {
  if (uri.startsWith("file://")) return decodeURIComponent(uri.slice("file://".length));
  return uri;
}

export function analyze(uri: string, text: string): Analysis {
  const file = analysis_file_name(uri);
  const source = make_source(file, text);
  const parsed = parse_text(file, text);
  const sink = make_sink({ max: 200 });

  for (const diagnostic of parsed.diagnostics) sink.add(diagnostic);

  const types = new Map<ExprNode, PenguType>();
  const member_targets = new Map<ExprNode, MethodTarget>();
  const module = check_program(file, parsed.program, sink, { types, member_targets });

  return {
    file,
    source,
    program: parsed.program,
    module,
    types,
    member_targets,
    diagnostics: sink.diagnostics,
  };
}

export function span_of_diagnostic(diagnostic: Diagnostic): { start: { line: number; column: number }; end: { line: number; column: number } } {
  return { start: diagnostic.span.start, end: diagnostic.span.end };
}

export function source_span(source: Source, line: number, column: number): ReturnType<typeof span_from> {
  const offsets = source.line_starts;
  const length = source.text.length;
  const start = Math.min((offsets[line] ?? 0) + (column - 1), length);
  return span_from(source, start, start);
}
