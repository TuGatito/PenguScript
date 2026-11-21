import type { Diagnostic } from "./diagnostic.ts";

export interface SinkOptions {
  readonly max?: number;
}

export interface DiagnosticSink {
  add(diagnostic: Diagnostic): void;
  readonly diagnostics: readonly Diagnostic[];
  has_errors(): boolean;
  is_truncated(): boolean;
}

const DEFAULT_MAX = 200;

export function make_sink(options: SinkOptions = {}): DiagnosticSink {
  const max = options.max ?? DEFAULT_MAX;
  const items: Diagnostic[] = [];
  const seen = new Set<string>();
  let truncated = false;

  return {
    add(diagnostic) {
      const key = `${diagnostic.code}:${diagnostic.span.start.offset}:${diagnostic.message}`;
      if (seen.has(key)) return;
      seen.add(key);
      if (items.length >= max) {
        truncated = true;
        return;
      }
      items.push(diagnostic);
    },
    get diagnostics() {
      return items;
    },
    has_errors() {
      return items.some((item) => item.severity === "error");
    },
    is_truncated() {
      return truncated;
    },
  };
}
