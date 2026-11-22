// Navegación: definición, referencias, renombrado y símbolos del documento.

import { lex_text } from "../frontend/lexer.ts";
import type { FileAnalysis, ProjectState } from "./project.ts";
import type { LspDocumentSymbol, LspLocation } from "./protocol.ts";
import { existing_symbol, span_to_source, to_lsp_range } from "./features.ts";
import { is_bundled } from "../project/paths.ts";

export function definition_at(project: ProjectState, file: FileAnalysis, offset: number): LspLocation | undefined {
  const symbol = existing_symbol(project, file, offset);
  if (symbol === undefined) return undefined;
  const target = project.files.get(symbol.file);
  if (target === undefined) return undefined;
  return { uri: file_uri(symbol.file), range: to_lsp_range(target.source, symbol.span) };
}

export interface Reference {
  readonly file: string;
  readonly range: { readonly start: { readonly line: number; readonly character: number }; readonly end: { readonly line: number; readonly character: number } };
}

// Ocurrencias del nombre en todo el proyecto: se buscan en los tokens del
// lexer, así no se tocan cadenas ni comentarios.
export function references_at(project: ProjectState, file: FileAnalysis, offset: number): Reference[] {
  const symbol = existing_symbol(project, file, offset);
  if (symbol === undefined) return [];
  const references: Reference[] = [];
  for (const candidate of project.files.values()) {
    const lexed = lex_text(candidate.file, candidate.source.text);
    for (const token of lexed.tokens) {
      if (token.kind !== "ident" || token.text !== symbol.name) continue;
      references.push({ file: candidate.file, range: to_lsp_range(candidate.source, token.span) });
    }
  }
  return references;
}

export interface WorkspaceEdit {
  readonly changes: Record<string, { readonly range: Reference["range"]; readonly newText: string }[]>;
}

export interface PrepareRename {
  readonly range: Reference["range"];
  readonly placeholder: string;
}

// Lo que `prepareRename` necesita: rango del nombre y texto actual.
export function prepare_rename_at(project: ProjectState, file: FileAnalysis, offset: number): PrepareRename | undefined {
  const symbol = existing_symbol(project, file, offset);
  if (symbol === undefined || is_bundled(symbol.file)) return undefined;
  return { range: to_lsp_range(file.source, symbol.span), placeholder: symbol.name };
}

export function rename_at(project: ProjectState, file: FileAnalysis, offset: number, new_name: string): WorkspaceEdit | undefined {
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(new_name)) return undefined;
  const symbol = existing_symbol(project, file, offset);
  if (symbol === undefined) return undefined;
  if (symbol.scope === undefined && symbol.kind === "realm") return undefined;
  // Renombrar `std/` rompería la biblioteca: se rechaza con mensaje claro.
  if (is_bundled(symbol.file)) return undefined;
  const changes: Record<string, { range: Reference["range"]; newText: string }[]> = {};
  for (const reference of references_at(project, file, offset)) {
    const list = changes[reference.file] ?? [];
    list.push({ range: reference.range, newText: new_name });
    changes[reference.file] = list;
  }
  return { changes };
}

const SYMBOL_KIND = { function: 12, variable: 13, class: 5, enum: 10, method: 6, field: 8 } as const;

export function document_symbols(file: FileAnalysis): LspDocumentSymbol[] {
  const symbols: LspDocumentSymbol[] = [];
  for (const decl of file.program.decls) {
    switch (decl.kind) {
      case "function_decl":
        symbols.push(symbol_of(file, decl.name, SYMBOL_KIND.function, decl.span));
        break;
      case "const_decl":
        symbols.push(symbol_of(file, decl.name, SYMBOL_KIND.variable, decl.span));
        break;
      case "rune_decl": {
        const children: LspDocumentSymbol[] = [];
        for (const field of decl.fields) children.push(symbol_of(file, field.name, SYMBOL_KIND.field, field.span));
        symbols.push({ ...symbol_of(file, decl.name, SYMBOL_KIND.class, decl.span), children });
        break;
      }
      case "omen_decl": {
        const children: LspDocumentSymbol[] = [];
        for (const variant of decl.variants) children.push(symbol_of(file, variant.name, SYMBOL_KIND.enum, variant.span));
        symbols.push({ ...symbol_of(file, decl.name, SYMBOL_KIND.enum, decl.span), children });
        break;
      }
      case "echo_decl":
      case "seal_decl":
        symbols.push(symbol_of(file, decl.name, SYMBOL_KIND.class, decl.span));
        break;
      case "enchanting_decl": {
        const children: LspDocumentSymbol[] = [];
        for (const method of decl.methods) {
          children.push(symbol_of(file, method.name, SYMBOL_KIND.method, method.span));
        }
        symbols.push({ ...symbol_of(file, `enchanting ${decl.target}`, SYMBOL_KIND.class, decl.span), children });
        break;
      }
      default:
        break;
    }
  }
  return symbols;
}

function symbol_of(file: FileAnalysis, name: string, kind: number, span: { readonly start: { readonly offset: number }; readonly end: { readonly offset: number } }): LspDocumentSymbol {
  const source_span = span_to_source(file.source, span.start.offset, span.end.offset);
  const range = to_lsp_range(file.source, source_span);
  return { name, kind, range, selectionRange: range };
}

export function file_uri(file: string): string {
  return `file://${encodeURI(file)}`;
}
