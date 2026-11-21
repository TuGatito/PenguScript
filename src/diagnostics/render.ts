import type { Diagnostic } from "./diagnostic.ts";
import { line_text, type Source, type Span } from "../util/span.ts";

const ANSI = {
  reset: "\u001b[0m",
  bold: "\u001b[1m",
  red: "\u001b[31m",
  yellow: "\u001b[33m",
  blue: "\u001b[34m",
  dim: "\u001b[2m",
} as const;

interface RenderOptions {
  readonly color?: boolean;
}

function severity_label(diagnostic: Diagnostic, color: boolean): string {
  const text = diagnostic.severity;
  if (!color) return text;
  if (diagnostic.severity === "error") return `${ANSI.red}${ANSI.bold}${text}${ANSI.reset}`;
  if (diagnostic.severity === "warning") return `${ANSI.yellow}${ANSI.bold}${text}${ANSI.reset}`;
  return `${ANSI.blue}${ANSI.bold}${text}${ANSI.reset}`;
}

function caret_line(span: Span, color: boolean): string {
  const width = Math.max(1, span.end.column - span.start.column);
  const padding = " ".repeat(Math.max(0, span.start.column - 1));
  const caret = "^".repeat(Math.min(width, 120));
  return color ? `${padding}${ANSI.red}${caret}${ANSI.reset}` : `${padding}${caret}`;
}

export function render_diagnostic(
  diagnostic: Diagnostic,
  source: Source | undefined,
  options: RenderOptions = {},
): string {
  const color = options.color ?? false;
  const head = `${diagnostic.span.file}:${diagnostic.span.start.line}:${diagnostic.span.start.column}`;
  const label = severity_label(diagnostic, color);
  const head_line = color
    ? `${ANSI.bold}${head}${ANSI.reset}: ${label}${ANSI.bold}[${diagnostic.code}]${ANSI.reset}: ${diagnostic.message}`
    : `${head}: ${label}[${diagnostic.code}]: ${diagnostic.message}`;

  const lines: string[] = [head_line];
  if (source) {
    const text = line_text(source, diagnostic.span.start.line);
    if (text.length > 0) {
      lines.push(`  ${color ? ANSI.dim : ""}${text}${color ? ANSI.reset : ""}`);
      lines.push(`  ${caret_line(diagnostic.span, color)}`);
    }
  }
  for (const note of diagnostic.notes) lines.push(`  ${color ? ANSI.blue : ""}note${color ? ANSI.reset : ""}: ${note}`);
  if (diagnostic.fix) lines.push(`  ${color ? ANSI.blue : ""}fix${color ? ANSI.reset : ""}: ${diagnostic.fix.title}`);
  return lines.join("\n");
}

export function render_diagnostics(
  diagnostics: readonly Diagnostic[],
  sources: ReadonlyMap<string, Source>,
  options: RenderOptions = {},
): string {
  return diagnostics
    .map((diagnostic) => render_diagnostic(diagnostic, sources.get(diagnostic.span.file), options))
    .join("\n\n");
}
