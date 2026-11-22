// Publicación de diagnósticos.
//
// Publicar en cada tecla todos los archivos del proyecto hace parpadear la
// lista de problemas y satura el canal. Aquí se calcula una huella por
// archivo y solo se envía lo que cambió. Además se filtra el error del
// identificador que el usuario está escribiendo: mientras no se detenga, ese
// error es ruido.

import type { Diagnostic } from "../diagnostics/diagnostic.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { FileAnalysis, ProjectState } from "./project.ts";
import { to_lsp_range } from "./features.ts";
import { file_uri } from "./navigation.ts";
import { DIAGNOSTIC_SEVERITY } from "./protocol.ts";
import type { LspDiagnostic } from "./protocol.ts";
import { touches } from "./sync.ts";

/** Códigos que no se publican sobre la zona que se está editando. */
const TYPING_CODES: ReadonlySet<string> = new Set([CODES.unknown_identifier, CODES.unknown_field]);

/** Zona recién editada, con el archivo al que pertenece. */
export interface HotSpot {
  readonly uri: string;
  readonly start: number;
  readonly end: number;
}

export interface Publisher {
  (method: string, params: unknown): void;
}

export function to_lsp_diagnostics(file: FileAnalysis): LspDiagnostic[] {
  return file.diagnostics.map((diagnostic) => ({
    range: to_lsp_range(file.source, diagnostic.span),
    severity: DIAGNOSTIC_SEVERITY[diagnostic.severity],
    code: diagnostic.code,
    source: "pengu",
    message: diagnostic.message,
  }));
}

/** Los diagnósticos que sí debe ver el usuario, ya filtrada la zona caliente. */
export function visible_diagnostics(file: FileAnalysis, hot: HotSpot | undefined): Diagnostic[] {
  if (hot === undefined || hot.uri !== file.file) return [...file.diagnostics];
  return file.diagnostics.filter((diagnostic) => !(TYPING_CODES.has(diagnostic.code) && touches(diagnostic.span, hot)));
}

export function diagnostic_fingerprint(diagnostics: readonly LspDiagnostic[]): string {
  return diagnostics.map((item) => `${item.code ?? ""}:${item.range.start.line}:${item.range.start.character}:${item.range.end.line}:${item.range.end.character}:${item.message}`).join("|");
}

/**
 * Envía `publishDiagnostics` solo de los archivos cuya lista cambió. Los
 * módulos empotrados (`std:…`) no son archivos del usuario y no se publican.
 */
export function publish_project(send: Publisher, project: ProjectState, published: Map<string, string>, hot: HotSpot | undefined): void {
  for (const file of project.files.values()) {
    if (file.file.startsWith("std:")) continue;
    const uri = file_uri(file.file);
    const diagnostics = visible_diagnostics(file, hot).map((diagnostic) => ({
      range: to_lsp_range(file.source, diagnostic.span),
      severity: DIAGNOSTIC_SEVERITY[diagnostic.severity],
      code: diagnostic.code,
      source: "pengu",
      message: diagnostic.message,
    }));
    const fingerprint = diagnostic_fingerprint(diagnostics);
    if (published.get(uri) === fingerprint) continue;
    published.set(uri, fingerprint);
    send("textDocument/publishDiagnostics", { uri, diagnostics });
  }
}

/** Al cerrar un documento se vacía su lista y se olvida la huella. */
export function clear_file(send: Publisher, published: Map<string, string>, uri: string): void {
  if (published.get(uri) === "") return;
  published.set(uri, "");
  send("textDocument/publishDiagnostics", { uri, diagnostics: [] });
}
