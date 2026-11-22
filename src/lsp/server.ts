// Servidor LSP de PenguScript.
//
// Sin clases: un objeto de estado y funciones que lo cierran. Mantiene los
// documentos abiertos, reconstruye el proyecto analizado en cada cambio,
// publica diagnósticos por archivo y responde a las consultas del editor.

import { make_transport } from "./transport.ts";
import type { Transport } from "./transport.ts";
import type {
  JsonRpcMessage,
  LspCompletionItem,
  LspDiagnostic,
  LspDocumentIdentifier,
  LspDocumentSymbol,
  LspLocation,
  LspPositionParams,
  LspTextDocumentItem,
  LspTextEdit,
} from "./protocol.ts";
import { DIAGNOSTIC_SEVERITY } from "./protocol.ts";
import { analysis_file_name } from "./analysis.ts";
import { find_node_at } from "./query.ts";
import { format_text } from "../formatter/format_tokens.ts";
import { span_of, type Source } from "../util/span.ts";
import { build_project } from "./project.ts";
import type { FileAnalysis, ProjectState } from "./project.ts";
import { completions_at } from "./completion.ts";
import { hover_at, signature_at } from "./hover.ts";
import {
  definition_at,
  document_symbols as symbols_of_document,
  prepare_rename_at,
  references_at,
  rename_at,
  file_uri,
} from "./navigation.ts";
import { folding_ranges, inlay_hints, semantic_tokens, TOKEN_TYPES } from "./inlay.ts";
import { code_actions_at } from "./actions.ts";
import { code_lenses, document_links } from "./links.ts";
import type { LspRange } from "./features.ts";
import { existing_symbol, to_lsp_range } from "./features.ts";
import { type_display } from "../semantic/types.ts";
import { project_sizes } from "./sizes.ts";
import type { FieldLookup, SizeLookup } from "./hover.ts";

interface Document {
  readonly uri: string;
  version: number;
  text: string;
}

interface ServerState {
  readonly transport: Transport;
  readonly documents: Map<string, Document>;
  project: ProjectState | undefined;
  sizes: SizeLookup | undefined;
  fields: FieldLookup | undefined;
  sizes_in_hints: boolean;
  shutdown: boolean;
}

const SERVER_NAME = "pengu-lsp";
const SERVER_VERSION = "0.1.0";

function respond(state: ServerState, id: number | string | undefined, result: unknown): void {
  if (id === undefined) return;
  state.transport.send({ jsonrpc: "2.0", id, result });
}

function respond_error(state: ServerState, id: number | string | undefined, code: number, message: string): void {
  if (id === undefined) return;
  state.transport.send({ jsonrpc: "2.0", id, error: { code, message } });
}

function notify(state: ServerState, method: string, params: unknown): void {
  state.transport.send({ jsonrpc: "2.0", method, params });
}

function request_id(message: JsonRpcMessage): number | string | undefined {
  return (message as { readonly id?: number | string }).id;
}

function document_uri_of(params: Record<string, unknown> | undefined): string | undefined {
  return (params?.textDocument as { readonly uri?: string } | undefined)?.uri;
}

function position_of(params: Record<string, unknown> | undefined): { line: number; character: number } | undefined {
  return (params as { readonly position?: { line: number; character: number } } | undefined)?.position;
}

// Los buffers abiertos son la fuente: el proyecto se analiza con ellos.
function overlays(state: ServerState): Map<string, string> {
  const map = new Map<string, string>();
  for (const document of state.documents.values()) map.set(analysis_file_name(document.uri), document.text);
  return map;
}

function rebuild(state: ServerState, entry: string): void {
  try {
    state.project = build_project(entry, overlays(state));
    state.sizes = undefined;
    state.fields = undefined;
  } catch {
    state.project = undefined;
    state.sizes = undefined;
    return;
  }
  publish_all(state);
}

function publish_all(state: ServerState): void {
  const project = state.project;
  if (project === undefined) return;
  for (const file of project.files.values()) {
    notify(state, "textDocument/publishDiagnostics", {
      uri: file_uri(file.file),
      diagnostics: to_lsp_diagnostics(file),
    });
  }
}

function to_lsp_diagnostics(file: FileAnalysis): LspDiagnostic[] {
  return file.diagnostics.map((diagnostic) => ({
    range: to_lsp_range(file.source, diagnostic.span),
    severity: DIAGNOSTIC_SEVERITY[diagnostic.severity],
    code: diagnostic.code,
    source: "pengu",
    message: diagnostic.message,
  }));
}

// Archivo analizado del documento (o el del proyecto si el documento no
// está en el grafo todavía).
function file_of(state: ServerState, uri: string): FileAnalysis | undefined {
  const project = state.project;
  if (project === undefined) return undefined;
  return project.files.get(analysis_file_name(uri)) ?? project.files.get(project.entry);
}

function offset_of(file: FileAnalysis, position: { line: number; character: number }): number {
  return to_offset_in(file.source, position.line, position.character);
}

function to_offset_in(source: Source, line: number, character: number): number {
  const base = source.line_starts[line] ?? 0;
  return Math.min(base + character, source.text.length);
}

function handle_request(state: ServerState, message: JsonRpcMessage): void {
  const params = message.params as Record<string, unknown> | undefined;
  const id = request_id(message);
  const uri = document_uri_of(params);
  const position = position_of(params);

  switch (message.method) {
    case "initialize": {
      state.sizes_in_hints = initialization_wants_sizes(params);
      respond(state, id, {
        capabilities: {
          textDocumentSync: { openClose: true, change: 1, save: true },
          hoverProvider: true,
          completionProvider: { triggerCharacters: [".", ":", "@", "#"], resolveProvider: false },
          signatureHelpProvider: { triggerCharacters: ["(", ","] },
          definitionProvider: true,
          referencesProvider: true,
          renameProvider: { prepareProvider: true },
          documentSymbolProvider: true,
          workspaceSymbolProvider: true,
          documentFormattingProvider: true,
          inlayHintProvider: true,
          semanticTokensProvider: { legend: { tokenTypes: [...TOKEN_TYPES], tokenModifiers: [] }, full: true },
          foldingRangeProvider: true,
          codeActionProvider: { codeActionKinds: ["quickfix", "refactor"] },
          documentLinkProvider: { resolveProvider: false },
          codeLensProvider: { resolveProvider: false },
          documentRangeFormattingProvider: true,
        },
        serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
      });
      return;
    }
    case "shutdown":
      state.shutdown = true;
      respond(state, id, null);
      return;
    case "textDocument/hover": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined || position === undefined) return respond(state, id, null);
      const hovered = hover_at(state.project as ProjectState, file, offset_of(file, position), size_lookup(state), field_lookup(state));
      respond(state, id, hovered === undefined ? null : { contents: { kind: "markdown", value: hovered.markdown } });
      return;
    }
    case "textDocument/completion": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined || position === undefined) return respond(state, id, []);
      const offset = offset_of(file, position);
      const items: LspCompletionItem[] = completions_at(state.project as ProjectState, file, offset).map((item) => ({
        label: item.label,
        kind: item.kind,
        detail: item.detail,
        documentation: item.documentation,
        insertText: item.insertText,
        sortText: item.sortText,
      }));
      respond(state, id, items);
      return;
    }
    case "textDocument/signatureHelp": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined || position === undefined) return respond(state, id, null);
      respond(state, id, signature_at(state.project as ProjectState, file, offset_of(file, position)) ?? null);
      return;
    }
    case "textDocument/definition": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined || position === undefined) return respond(state, id, null);
      respond(state, id, definition_at(state.project as ProjectState, file, offset_of(file, position)) ?? null);
      return;
    }
    case "textDocument/references": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined || position === undefined) return respond(state, id, []);
      respond(state, id, references_at(state.project as ProjectState, file, offset_of(file, position)).map((reference) => ({
        uri: file_uri(reference.file),
        range: reference.range,
      })));
      return;
    }
    case "textDocument/prepareRename": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined || position === undefined) return respond(state, id, null);
      const prepared = prepare_rename_at(state.project as ProjectState, file, offset_of(file, position));
      if (prepared === undefined) {
        respond_error(state, id, -32602, "no se puede renombrar este símbolo (¿es de «std/»?)");
        return;
      }
      respond(state, id, prepared);
      return;
    }
    case "textDocument/rename": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      const new_name = (params as { readonly newName?: string } | undefined)?.newName;
      if (file === undefined || position === undefined || new_name === undefined) return respond(state, id, null);
      respond(state, id, rename_at(state.project as ProjectState, file, offset_of(file, position), new_name) ?? null);
      return;
    }
    case "textDocument/documentSymbol": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined) return respond(state, id, []);
      respond(state, id, symbols_of_document(file));
      return;
    }
    case "workspace/symbol": {
      const query = ((params as { readonly query?: string } | undefined)?.query ?? "").toLowerCase();
      const project = state.project;
      if (project === undefined) return respond(state, id, []);
      const symbols = project.index.symbols
        .filter((symbol) => symbol.scope === undefined && symbol.name.toLowerCase().includes(query))
        .slice(0, 200)
        .map((symbol) => {
          const file = project.files.get(symbol.file);
          const range: LspRange = file === undefined
            ? { start: { line: 0, character: 0 }, end: { line: 0, character: 0 } }
            : to_lsp_range(file.source, symbol.span);
          return { name: symbol.name, kind: 12, location: { uri: file_uri(symbol.file), range } };
        });
      respond(state, id, symbols);
      return;
    }
    case "textDocument/formatting": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      const document = uri === undefined ? undefined : state.documents.get(uri);
      if (file === undefined || document === undefined) return respond(state, id, []);
      const formatted = format_text(file.file, document.text);
      if (formatted === document.text) return respond(state, id, []);
      const edit: LspTextEdit = {
        range: to_lsp_range(file.source, span_of(file.source, 0, document.text.length)),
        newText: formatted,
      };
      respond(state, id, [edit]);
      return;
    }
    case "textDocument/documentLink": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined) return respond(state, id, []);
      respond(state, id, document_links(file));
      return;
    }
    case "textDocument/codeLens": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined) return respond(state, id, []);
      respond(state, id, code_lenses(file));
      return;
    }
    case "textDocument/rangeFormatting": {
      // Solo se reformatea cuando el rango cubre el documento completo: un
      // bloque suelto podría depender de la indentación de su contexto.
      const file = uri === undefined ? undefined : file_of(state, uri);
      const document = uri === undefined ? undefined : state.documents.get(uri);
      const range = (params as { readonly range?: { start: { line: number }; end: { line: number } } } | undefined)?.range;
      if (file === undefined || document === undefined || range === undefined) return respond(state, id, []);
      const total_lines = document.text.split("\n").length - 1;
      if (range.start.line > 0 || range.end.line < total_lines) return respond(state, id, []);
      const formatted = format_text(file.file, document.text);
      if (formatted === document.text) return respond(state, id, []);
      respond(state, id, [
        {
          range: { start: { line: 0, character: 0 }, end: { line: total_lines, character: 0 } },
          newText: formatted,
        },
      ]);
      return;
    }
    case "textDocument/inlayHint": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined) return respond(state, id, []);
      respond(state, id, inlay_hints_with_sizes(state, file));
      return;
    }
    case "pengu/sizeAt": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined || position === undefined) return respond(state, id, null);
      respond(state, id, size_at(state, file, offset_of(file, position)));
      return;
    }
    case "textDocument/semanticTokens/full": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined) return respond(state, id, { data: [] });
      respond(state, id, semantic_tokens(file));
      return;
    }
    case "textDocument/foldingRange": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined) return respond(state, id, []);
      respond(state, id, folding_ranges(file));
      return;
    }
    case "textDocument/codeAction": {
      const file = uri === undefined ? undefined : file_of(state, uri);
      if (file === undefined) return respond(state, id, []);
      const range = (params as { readonly range?: LspRange } | undefined)?.range ?? { start: { line: 0, character: 0 }, end: { line: 0, character: 0 } };
      const offset = to_offset_in(file.source, range.start.line, range.start.character);
      respond(state, id, code_actions_at(state.project as ProjectState, file, offset, range));
      return;
    }
    default:
      respond_error(state, id, -32601, `método no soportado: ${message.method}`);
  }
}

// La medición compila un programa de sondeo la primera vez; se guarda
// junto al proyecto y se reutiliza mientras no cambien las declaraciones.
// El editor pide `initializationOptions.inlayHints.sizes` desde sus ajustes.
function initialization_wants_sizes(params: Record<string, unknown> | undefined): boolean {
  const options = params?.initializationOptions as { inlayHints?: { sizes?: unknown } } | undefined;
  return options?.inlayHints?.sizes === true;
}

function inlay_hints_with_sizes(state: ServerState, file: FileAnalysis): unknown[] {
  const hints = inlay_hints(file);
  if (!state.sizes_in_hints) return [...hints];
  const lookup = size_lookup(state);
  if (lookup === undefined) return [...hints];
  return hints.map((hint) => {
    const node = find_node_at(file.program, to_offset_in(file.source, hint.position.line, hint.position.character));
    const type = node === undefined ? undefined : file.analysis.types.get(node as never);
    const measured = type === undefined ? undefined : lookup(type);
    return measured === undefined ? hint : { ...hint, label: `${hint.label} · ${measured.size} B` };
  });
}

// Tamaño del símbolo bajo el cursor, para la barra de estado del editor.
function size_at(state: ServerState, file: FileAnalysis, offset: number): unknown {
  const lookup = size_lookup(state);
  if (lookup === undefined) return null;
  const node = find_node_at(file.program, offset);
  const type = node === undefined ? undefined : file.analysis.types.get(node as never);
  const measured = type === undefined ? undefined : lookup(type);
  if (measured === undefined) return null;
  const name = existing_symbol(state.project as ProjectState, file, offset)?.name;
  return { name, type: type === undefined ? undefined : type_display(type), size: measured.size, align: measured.align };
}

function size_lookup(state: ServerState): SizeLookup | undefined {
  const project = state.project;
  if (project === undefined) return undefined;
  if (state.sizes === undefined) {
    const sizes = project_sizes(project);
    state.sizes = sizes.lookup;
    state.fields = sizes.fields;
  }
  return state.sizes;
}

function field_lookup(state: ServerState): FieldLookup | undefined {
  size_lookup(state);
  return state.fields;
}

function handle_notification(state: ServerState, message: JsonRpcMessage): void {
  const params = message.params as Record<string, unknown> | undefined;

  switch (message.method) {
    case "initialized":
      return;
    case "textDocument/didOpen": {
      const item = (params as { textDocument?: LspTextDocumentItem } | undefined)?.textDocument;
      if (item === undefined) return;
      state.documents.set(item.uri, { uri: item.uri, version: item.version ?? 0, text: item.text });
      rebuild(state, analysis_file_name(item.uri));
      return;
    }
    case "textDocument/didChange": {
      const identifier = (params as { textDocument?: { uri: string; version?: number } } | undefined)?.textDocument;
      const changes = (params as { contentChanges?: readonly { text: string }[] } | undefined)?.contentChanges;
      if (identifier === undefined || changes === undefined || changes.length === 0) return;
      const document = state.documents.get(identifier.uri);
      if (document === undefined) return;
      const last = changes[changes.length - 1];
      if (last !== undefined) document.text = last.text;
      document.version = identifier.version ?? document.version;
      rebuild(state, analysis_file_name(identifier.uri));
      return;
    }
    case "textDocument/didSave": {
      const identifier = document_uri_of(params);
      if (identifier === undefined) return;
      const document = state.documents.get(identifier);
      if (document === undefined) return;
      rebuild(state, analysis_file_name(identifier));
      return;
    }
    case "textDocument/didClose": {
      const identifier = document_uri_of(params);
      if (identifier === undefined) return;
      state.documents.delete(identifier);
      notify(state, "textDocument/publishDiagnostics", { uri: identifier, diagnostics: [] });
      return;
    }
    case "exit":
      process.exit(state.shutdown ? 0 : 1);
  }
}

export function start_lsp_server(): void {
  const transport = make_transport(process.stdin, { write: (text) => process.stdout.write(text) });
  const state: ServerState = { transport, documents: new Map(), project: undefined, sizes: undefined, fields: undefined, sizes_in_hints: false, shutdown: false };

  transport.on_message((message) => {
    const is_request = request_id(message) !== undefined;
    try {
      if (is_request) handle_request(state, message);
      else handle_notification(state, message);
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      if (is_request) respond_error(state, request_id(message), -32603, detail);
    }
  });
}

export function analysis_name_for_uri(uri: string): string {
  return analysis_file_name(uri);
}

export { find_node_at };
export type { LspDocumentIdentifier, LspDocumentSymbol, LspLocation };
