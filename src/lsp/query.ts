// Consultas sobre el AST para hover y finalización.

import type { Program } from "../frontend/ast.ts";

export interface SpanLike {
  readonly start: { readonly offset: number };
  readonly end: { readonly offset: number };
}

interface NodeLike {
  readonly kind: string;
  readonly span?: SpanLike;
}

function is_node(value: unknown): value is NodeLike {
  return typeof value === "object" && value !== null && "kind" in value;
}

export function find_node_at(program: Program, offset: number): NodeLike | undefined {
  let best: NodeLike | undefined;

  function visit(value: unknown): void {
    if (Array.isArray(value)) {
      for (const item of value) visit(item);
      return;
    }
    if (typeof value !== "object" || value === null) return;

    if (is_node(value) && value.span !== undefined) {
      const span = value.span;
      if (offset >= span.start.offset && offset <= span.end.offset) {
        if (best === undefined || span.end.offset - span.start.offset <= best.span!.end.offset - best.span!.start.offset) {
          best = value;
        }
      }
    }

    for (const key of Object.keys(value)) visit((value as Record<string, unknown>)[key]);
  }

  visit(program);
  return best;
}

export function node_label(node: { kind: string; name?: string; segments?: readonly string[] }): string {
  if (typeof node.name === "string") return node.name;
  if (Array.isArray(node.segments)) return node.segments.join("::");
  return node.kind;
}
