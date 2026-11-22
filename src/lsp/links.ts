// Enlaces y lentes: los `invoke` se pueden abrir y `main` se puede ejecutar
// desde el editor.

import { resolve } from "node:path";
import type { FileAnalysis } from "./project.ts";
import type { LspRange } from "./features.ts";
import { file_uri } from "./navigation.ts";
import { to_lsp_range } from "./features.ts";
import { find_project_root, resolve_module_file } from "../project/paths.ts";

export interface DocumentLink {
  readonly range: LspRange;
  readonly target: string;
  readonly tooltip?: string;
}

// Cada `invoke "ruta"` enlaza con el archivo que resuelve, si existe.
export function document_links(file: FileAnalysis): DocumentLink[] {
  const links: DocumentLink[] = [];
  const root = find_project_root(file.file);
  for (const decl of file.program.decls) {
    if (decl.kind !== "invoke_decl") continue;
    const resolved = resolve_module_file(file.file, decl.path, root);
    if (resolved === undefined) continue;
    links.push({
      range: to_lsp_range(file.source, decl.span),
      target: file_uri(resolve(resolved)),
      tooltip: `Abrir ${decl.path}`,
    });
  }
  return links;
}

export interface CodeLens {
  readonly range: LspRange;
  readonly command: { readonly title: string; readonly command: string; readonly arguments?: readonly unknown[] };
}

// Lente sobre `main` para ejecutar el archivo sin salir del editor.
export function code_lenses(file: FileAnalysis): CodeLens[] {
  const lenses: CodeLens[] = [];
  for (const [name, fn] of file.module.functions) {
    if (name !== "main") continue;
    lenses.push({
      range: to_lsp_range(file.source, fn.span),
      command: { title: "▶ Ejecutar", command: "pengu.runFile", arguments: [file.file] },
    });
  }
  return lenses;
}
