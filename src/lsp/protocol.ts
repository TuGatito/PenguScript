// Tipos mínimos del protocolo LSP (JSON-RPC 2.0 sobre stdio).
//
// El servidor habla con el editor mediante mensajes con cabecera
// `Content-Length`; aquí solo modelamos lo que necesitamos.

export interface LspPosition {
  readonly line: number;
  readonly character: number;
}

export interface LspRange {
  readonly start: LspPosition;
  readonly end: LspPosition;
}

export interface LspDiagnostic {
  readonly range: LspRange;
  readonly severity?: 1 | 2 | 3 | 4;
  readonly code?: string;
  readonly source?: string;
  readonly message: string;
}

export interface LspLocation {
  readonly uri: string;
  readonly range: LspRange;
}

export interface LspDocumentSymbol {
  readonly name: string;
  readonly kind: number;
  readonly range: LspRange;
  readonly selectionRange: LspRange;
}

export interface LspTextEdit {
  readonly range: LspRange;
  readonly newText: string;
}

export interface LspTextDocumentItem {
  readonly uri: string;
  readonly languageId?: string;
  readonly version?: number;
  readonly text: string;
}

export interface LspDocumentIdentifier {
  readonly uri: string;
}

export interface LspPositionParams extends LspDocumentIdentifier {
  readonly position: LspPosition;
}

export interface LspCompletionItem {
  readonly label: string;
  readonly kind?: number;
  readonly detail?: string;
  readonly insertText?: string;
}

export interface LspHover {
  readonly contents: { readonly kind: "markdown"; readonly value: string };
  readonly range?: LspRange;
}

export interface JsonRpcRequest {
  readonly jsonrpc: "2.0";
  readonly id?: number | string;
  readonly method: string;
  readonly params?: unknown;
}

export interface JsonRpcNotification {
  readonly jsonrpc?: "2.0";
  readonly method: string;
  readonly params?: unknown;
}

export type JsonRpcMessage = JsonRpcRequest | JsonRpcNotification;

export const COMPLETION_KIND = {
  keyword: 14,
  function: 3,
  variable: 6,
  class: 7,
  enum_member: 20,
} as const;

export const DIAGNOSTIC_SEVERITY = {
  error: 1,
  warning: 2,
  info: 3,
} as const;
