import type { Span } from "../util/span.ts";

export type Severity = "error" | "warning" | "info";

export interface Fix {
  readonly title: string;
  readonly span: Span;
  readonly replacement: string;
}

export interface Diagnostic {
  readonly code: string;
  readonly severity: Severity;
  readonly message: string;
  readonly span: Span;
  readonly notes: readonly string[];
  readonly fix?: Fix;
}

export interface DiagnosticInit {
  readonly code: string;
  readonly message: string;
  readonly span: Span;
  readonly severity?: Severity;
  readonly notes?: readonly string[];
  readonly fix?: Fix;
}

export function make_diagnostic(init: DiagnosticInit): Diagnostic {
  return {
    code: init.code,
    severity: init.severity ?? "error",
    message: init.message,
    span: init.span,
    notes: init.notes ?? [],
    ...(init.fix ? { fix: init.fix } : {}),
  };
}

export function error(
  code: string,
  message: string,
  span: Span,
  ...notes: string[]
): Diagnostic {
  return make_diagnostic({ code, message, span, notes });
}

export function warning(
  code: string,
  message: string,
  span: Span,
  ...notes: string[]
): Diagnostic {
  return make_diagnostic({ code, message, span, severity: "warning", notes });
}

export function with_note(diagnostic: Diagnostic, note: string): Diagnostic {
  return { ...diagnostic, notes: [...diagnostic.notes, note] };
}

export function with_fix(diagnostic: Diagnostic, fix: Fix): Diagnostic {
  return { ...diagnostic, fix };
}
