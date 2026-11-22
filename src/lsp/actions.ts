// Acciones de código: arreglos rápidos de los diagnósticos y tipos
// explícitos para variables inferidas.

import { type_display } from "../semantic/types.ts";
import type { FileAnalysis, ProjectState } from "./project.ts";
import { span_to_source, to_lsp_range } from "./features.ts";
import { find_node_at } from "./query.ts";
import { file_uri } from "./navigation.ts";

export interface CodeAction {
  readonly title: string;
  readonly kind: "quickfix" | "refactor";
  readonly diagnostics?: readonly { readonly range: ReturnType<typeof to_lsp_range>; readonly message: string; readonly code?: string }[];
  readonly edit?: { readonly changes: Record<string, { readonly range: ReturnType<typeof to_lsp_range>; readonly newText: string }[]> };
}

export function code_actions_at(
  project: ProjectState,
  file: FileAnalysis,
  offset: number,
  range: ReturnType<typeof to_lsp_range>,
): CodeAction[] {
  const actions: CodeAction[] = [];
  for (const diagnostic of file.diagnostics) {
    if (diagnostic.fix === undefined) continue;
    if (!span_contains(diagnostic.span, offset)) continue;
    const target = span_to_source(file.source, diagnostic.fix.span.start.offset, diagnostic.fix.span.end.offset);
    actions.push({
      title: diagnostic.fix.title,
      kind: "quickfix",
      diagnostics: [{ range, message: diagnostic.message, code: diagnostic.code }],
      edit: { changes: { [file_uri(file.file)]: [{ range: to_lsp_range(file.source, target), newText: diagnostic.fix.replacement }] } },
    });
  }

  const node = find_node_at(file.program, offset);
  if (node !== undefined && node.kind === "ident" && node.span !== undefined) {
    const type = file.analysis.types.get(node as never);
    if (type !== undefined) {
      const edit_range = to_lsp_range(file.source, span_to_source(file.source, node.span.end.offset, node.span.end.offset));
      actions.push({
        title: `Añadir tipo explícito «${type_display(type)}»`,
        kind: "refactor",
        edit: { changes: { [file_uri(file.file)]: [{ range: edit_range, newText: `: ${type_display(type)}` }] } },
      });
    }
  }

  void project;
  return actions;
}

function span_contains(span: { readonly start: { readonly offset: number }; readonly end: { readonly offset: number } }, offset: number): boolean {
  return offset >= span.start.offset - 1 && offset <= span.end.offset + 1;
}
