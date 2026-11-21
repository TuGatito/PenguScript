// Servidor LSP de PenguScript.
//
// Sin clases: un objeto de estado y funciones que lo cierran. El
// servidor mantiene los documentos abiertos, publica diagnósticos en
// cada cambio y responde a hover, finalización y formato.

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
import { COMPLETION_KIND, DIAGNOSTIC_SEVERITY } from "./protocol.ts";
import { analyze, analysis_file_name } from "./analysis.ts";
import type { Analysis } from "./analysis.ts";
import { find_node_at, node_label } from "./query.ts";
import { format_text } from "../formatter/format_tokens.ts";
import { KEYWORDS } from "../frontend/token.ts";
import { position_at, span_of, type Source, type Span } from "../util/span.ts";
import { type_display, type PenguType } from "../semantic/types.ts";
import type { ModuleInfo } from "../semantic/module_info.ts";
import type { EnchantedMethod, MethodTarget } from "../semantic/type_env.ts";

interface Document {
  readonly uri: string;
  version: number;
  text: string;
  analysis: Analysis;
}

interface ServerState {
  readonly transport: Transport;
  readonly documents: Map<string, Document>;
  shutdown: boolean;
}

const SERVER_NAME = "pengu-lsp";
const SERVER_VERSION = "0.1.0";

function to_lsp_range(source: Source, span: { start: { offset: number }; end: { offset: number } }): {
  start: { line: number; character: number };
  end: { line: number; character: number };
} {
  const start = position_at(source, span.start.offset);
  const end = position_at(source, span.end.offset);
  return {
    start: { line: start.line - 1, character: start.column - 1 },
    end: { line: end.line - 1, character: end.column - 1 },
  };
}

function to_offset(source: Source, line: number, character: number): number {
  const base = source.line_starts[line] ?? 0;
  return Math.min(base + character, source.text.length);
}

function to_lsp_diagnostics(analysis: Analysis): LspDiagnostic[] {
  return analysis.diagnostics.map((diagnostic) => ({
    range: to_lsp_range(analysis.source, diagnostic.span),
    severity: DIAGNOSTIC_SEVERITY[diagnostic.severity],
    code: diagnostic.code,
    source: "pengu",
    message: diagnostic.message,
  }));
}

// Los parámetros de LSP anidan el documento en `textDocument.uri`.
function document_uri_of(params: Record<string, unknown> | undefined): string | undefined {
  const identifier = params?.textDocument as { readonly uri?: string } | undefined;
  return identifier?.uri;
}

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

function publish_diagnostics(state: ServerState, document: Document): void {
  notify(state, "textDocument/publishDiagnostics", {
    uri: document.uri,
    diagnostics: to_lsp_diagnostics(document.analysis),
  });
}

function refresh(state: ServerState, document: Document): void {
  document.analysis = analyze(document.uri, document.text);
  publish_diagnostics(state, document);
}

function enchanted_signature(module: ModuleInfo, target: MethodTarget): string | undefined {
  for (const enchanted of module.env.enchants.values()) {
    for (const [name, methods] of enchanted.methods) {
      if (name !== target.name) continue;
      for (const method of methods) {
        if (method.realm !== target.realm) continue;
        const params = method.info.params.map((param) => type_display(param)).join(", ");
        return `${name} = (${params}) -> ${type_display(method.info.result)}`;
      }
    }
  }
  return undefined;
}

function hover_markdown(document: Document, offset: number): string | undefined {
  const node = find_node_at(document.analysis.program, offset);
  if (node === undefined) return undefined;

  const target = document.analysis.member_targets.get(node as never);
  if (target !== undefined) {
    const signature = enchanted_signature(document.analysis.module, target);
    if (signature !== undefined) {
      return `\`\`\`pengu
${signature}
\`\`\`

realm \`${target.realm}\``;
    }
  }

  const type = document.analysis.types.get(node as never);
  if (type !== undefined) {
    return `\`\`\`pengu\n${node_label(node)}: ${type_display(type)}\n\`\`\``;
  }

  const name = node_label(node);
  const module = document.analysis.module;
  const fn = module.functions.get(name);
  if (fn !== undefined) {
    const params = fn.params.map((param) => `${param.name}: ${type_display(param.type)}`).join(", ");
    return `\`\`\`pengu\n${name} = (${params}) -> ${type_display(fn.result)}\n\`\`\``;
  }
  const constant = module.consts.get(name);
  if (constant !== undefined) return `\`\`\`pengu\nconst ${name}: ${type_display(constant.type)}\n\`\`\``;
  const rune = module.env.runes.get(name);
  if (rune !== undefined) return `\`\`\`pengu\nrune ${name}\n\`\`\``;
  const omen = module.env.omens.get(name);
  if (omen !== undefined) return `\`\`\`pengu\nomen ${name}\n\`\`\``;
  return undefined;
}

function receiver_shape(type: PenguType): string | undefined {
  switch (type.kind) {
    case "primitive":
      return `${type.name}/0`;
    case "named":
      return type.generic === true ? undefined : `${type.name}/${type.args.length}`;
    case "tuple":
      return `tuple/${type.items.length}`;
    case "array":
      return "array/1";
    case "optional":
    case "ref":
      return `${type.kind}/1`;
    default:
      return undefined;
  }
}

function member_completion_items(document: Document, offset: number): LspCompletionItem[] | undefined {
  const before = document.text.slice(0, offset);
  const dot = before.lastIndexOf(".");
  if (dot < 0) return undefined;
  const between = before.slice(dot + 1);
  if (between.length > 0 && !/^[A-Za-z0-9_]*$/.test(between)) return undefined;

  const node = find_node_at(document.analysis.program, Math.max(dot - 1, 0));
  if (node === undefined) return undefined;
  const type = document.analysis.types.get(node as never);
  if (type === undefined) return undefined;

  const items: LspCompletionItem[] = [];
  const module = document.analysis.module;
  const shape = receiver_shape(type);
  if (shape !== undefined) {
    const enchanted = module.env.enchants.get(shape);
    if (enchanted !== undefined) {
      for (const [name, methods] of enchanted.methods) {
        const method: EnchantedMethod | undefined = methods[0];
        if (method === undefined) continue;
        const params = method.info.params.map((param) => type_display(param)).join(", ");
        items.push({
          label: name,
          kind: COMPLETION_KIND.function,
          detail: `(${params}) -> ${type_display(method.info.result)}`,
        });
      }
    }
  }
  const type_name = type.kind === "named" ? type.name : undefined;
  const rune = type_name === undefined ? undefined : module.env.runes.get(type_name);
  if (rune !== undefined) {
    for (const name of rune.methods.keys()) {
      items.push({ label: name, kind: COMPLETION_KIND.function, detail: `rune ${type_name}` });
    }
  }
  return items.length > 0 ? items : undefined;
}

function collect_words(text: string): string[] {
  const words = new Set<string>();
  for (const match of text.matchAll(/[A-Za-z_][A-Za-z0-9_]*/g)) words.add(match[0]);
  return [...words];
}

function completion_items(document: Document): LspCompletionItem[] {
  const items: LspCompletionItem[] = [];
  for (const keyword of KEYWORDS) items.push({ label: keyword, kind: COMPLETION_KIND.keyword });

  for (const [name, fn] of document.analysis.module.functions) {
    items.push({
      label: name,
      kind: COMPLETION_KIND.function,
      detail: `(${fn.params.length} parámetros) -> ${type_display(fn.result)}`,
    });
  }
  for (const [name, constant] of document.analysis.module.consts) {
    items.push({ label: name, kind: COMPLETION_KIND.variable, detail: type_display(constant.type) });
  }
  for (const name of document.analysis.module.env.runes.keys()) {
    items.push({ label: name, kind: COMPLETION_KIND.class, detail: "rune" });
  }
  for (const name of document.analysis.module.env.omens.keys()) {
    items.push({ label: name, kind: COMPLETION_KIND.class, detail: "omen" });
  }
  for (const name of collect_words(document.text)) {
    items.push({ label: name, kind: COMPLETION_KIND.variable });
  }

  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.label)) return false;
    seen.add(item.label);
    return true;
  });
}

function symbol_span(document: Document, name: string): Span | undefined {
  const module = document.analysis.module;
  const fn = module.functions.get(name);
  if (fn !== undefined) return fn.span;
  const constant = module.consts.get(name);
  if (constant !== undefined) return constant.span;
  const rune = module.env.runes.get(name);
  if (rune !== undefined) return rune.span;
  const omen = module.env.omens.get(name);
  if (omen !== undefined) return omen.span;
  const alias = module.env.aliases.get(name);
  return alias?.span;
}

function definition_location(document: Document, offset: number): LspLocation | undefined {
  const node = find_node_at(document.analysis.program, offset);
  if (node === undefined) return undefined;
  const span = symbol_span(document, node_label(node));
  if (span === undefined) return undefined;
  return { uri: document.uri, range: to_lsp_range(document.analysis.source, span) };
}

const SYMBOL_KIND = { function: 12, variable: 13, class: 5, enum: 10 } as const;

function document_symbols(document: Document): LspDocumentSymbol[] {
  const symbols: LspDocumentSymbol[] = [];
  for (const decl of document.analysis.program.decls) {
    let name: string | undefined;
    let kind: number = SYMBOL_KIND.variable;
    switch (decl.kind) {
      case "function_decl":
        name = decl.name;
        kind = SYMBOL_KIND.function;
        break;
      case "const_decl":
        name = decl.name;
        kind = SYMBOL_KIND.variable;
        break;
      case "rune_decl":
      case "echo_decl":
      case "seal_decl":
        name = decl.name;
        kind = SYMBOL_KIND.class;
        break;
      case "omen_decl":
        name = decl.name;
        kind = SYMBOL_KIND.enum;
        break;
      case "enchanting_decl":
        name = `enchanting ${decl.target}`;
        kind = SYMBOL_KIND.class;
        break;
      default:
        name = undefined;
    }
    if (name === undefined) continue;
    const range = to_lsp_range(document.analysis.source, decl.span);
    symbols.push({ name, kind, range, selectionRange: range });
  }
  return symbols;
}

function handle_request(state: ServerState, message: JsonRpcMessage): void {
  const params = message.params as Record<string, unknown> | undefined;
  const id = (message as { readonly id?: number | string }).id;

  switch (message.method) {
    case "initialize": {
      respond(state, id, {
        capabilities: {
          textDocumentSync: 1,
          hoverProvider: true,
          completionProvider: { triggerCharacters: [".", ":", "@", "#"] },
          definitionProvider: true,
          documentSymbolProvider: true,
          documentFormattingProvider: true,
        },
        serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
      });
      return;
    }
    case "shutdown": {
      state.shutdown = true;
      respond(state, id, null);
      return;
    }
    case "textDocument/hover": {
      const hover_params = params as unknown as LspPositionParams | undefined;
      const hover_uri = document_uri_of(params);
      if (hover_params === undefined || hover_uri === undefined) return respond(state, id, null);
      const document = state.documents.get(hover_uri);
      if (document === undefined) return respond(state, id, null);
      const offset = to_offset(document.analysis.source, hover_params.position.line, hover_params.position.character);
      const markdown = hover_markdown(document, offset);
      if (markdown === undefined) return respond(state, id, null);
      respond(state, id, { contents: { kind: "markdown", value: markdown } });
      return;
    }
    case "textDocument/completion": {
      const completion_uri = document_uri_of(params);
      if (completion_uri === undefined) return respond(state, id, []);
      const document = state.documents.get(completion_uri);
      if (document === undefined) return respond(state, id, []);
      const completion_params = params as unknown as LspPositionParams | undefined;
      if (completion_params !== undefined) {
        const completion_offset = to_offset(
          document.analysis.source,
          completion_params.position.line,
          completion_params.position.character,
        );
        const members = member_completion_items(document, completion_offset);
        if (members !== undefined) {
          respond(state, id, members);
          return;
        }
      }
      respond(state, id, completion_items(document));
      return;
    }
    case "textDocument/definition": {
      const definition_params = params as unknown as LspPositionParams | undefined;
      const definition_uri = document_uri_of(params);
      if (definition_params === undefined || definition_uri === undefined) return respond(state, id, null);
      const document = state.documents.get(definition_uri);
      if (document === undefined) return respond(state, id, null);
      const offset = to_offset(document.analysis.source, definition_params.position.line, definition_params.position.character);
      respond(state, id, definition_location(document, offset) ?? null);
      return;
    }
    case "textDocument/documentSymbol": {
      const symbols_uri = document_uri_of(params);
      if (symbols_uri === undefined) return respond(state, id, []);
      const document = state.documents.get(symbols_uri);
      if (document === undefined) return respond(state, id, []);
      respond(state, id, document_symbols(document));
      return;
    }
    case "textDocument/formatting": {
      const formatting_uri = document_uri_of(params);
      if (formatting_uri === undefined) return respond(state, id, []);
      const document = state.documents.get(formatting_uri);
      if (document === undefined) return respond(state, id, []);
      const formatted = format_text(document.analysis.file, document.text);
      if (formatted === document.text) return respond(state, id, []);
      const edit: LspTextEdit = {
        range: to_lsp_range(document.analysis.source, span_of(document.analysis.source, 0, document.text.length)),
        newText: formatted,
      };
      respond(state, id, [edit]);
      return;
    }
    default:
      respond_error(state, id, -32601, `método no soportado: ${message.method}`);
  }
}

function handle_notification(state: ServerState, message: JsonRpcMessage): void {
  const params = message.params as Record<string, unknown> | undefined;

  switch (message.method) {
    case "initialized":
      return;
    case "textDocument/didOpen": {
      const item = (params as { textDocument?: LspTextDocumentItem } | undefined)?.textDocument;
      if (item === undefined) return;
      const document: Document = {
        uri: item.uri,
        version: item.version ?? 0,
        text: item.text,
        analysis: analyze(item.uri, item.text),
      };
      state.documents.set(item.uri, document);
      publish_diagnostics(state, document);
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
      refresh(state, document);
      return;
    }
    case "textDocument/didSave": {
      const identifier = document_uri_of(params);
      if (identifier === undefined) return;
      const document = state.documents.get(identifier);
      if (document !== undefined) publish_diagnostics(state, document);
      return;
    }
    case "textDocument/didClose": {
      const identifier = document_uri_of(params);
      if (identifier === undefined) return;
      state.documents.delete(identifier);
      notify(state, "textDocument/publishDiagnostics", { uri: identifier, diagnostics: [] });
      return;
    }
    case "exit": {
      process.exit(state.shutdown ? 0 : 1);
    }
  }
}

export function start_lsp_server(): void {
  const transport = make_transport(process.stdin, { write: (text) => process.stdout.write(text) });
  const state: ServerState = { transport, documents: new Map(), shutdown: false };

  transport.on_message((message) => {
    const is_request = "id" in message && (message as { id?: unknown }).id !== undefined;
    try {
      if (is_request) handle_request(state, message);
      else handle_notification(state, message);
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      if (is_request) respond_error(state, (message as { id?: number | string }).id, -32603, detail);
    }
  });
}

export function analysis_name_for_uri(uri: string): string {
  return analysis_file_name(uri);
}
