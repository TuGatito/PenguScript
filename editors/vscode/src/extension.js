// Cliente LSP de PenguScript para VS Code, sin dependencias.
//
// Habla JSON-RPC con framing `Content-Length` sobre `stdin`/`stdout` de
// `pengu lsp`. Mantenerlo sin dependencias permite instalar la extensión sin
// `npm install` y garantiza que el protocolo se prueba desde un cliente que no
// es Rust.
//
// Responsabilidades:
//   - arrancar y reiniciar el servidor, con mensajes de error útiles;
//   - mantener sincronizados los documentos, incluidos los que ya estaban
//     abiertos cuando se activó la extensión;
//   - exponer todas las capacidades que anuncia el servidor;
//   - ejecutar y probar el programa desde el editor.

// `vscode` no es un módulo de Node: lo inyecta el host de extensiones. Con el
// prefijo `node:` Node lo busca como builtin y la activación falla.
const vscode = require('vscode');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const LANGUAGE = 'pengu';
const OUTPUT_NAME = 'PenguScript';

// Debe coincidir con `crates/pengu-lsp/src/semantic.rs`.
const SEMANTIC_LEGEND = {
  tokenTypes: [
    'namespace',
    'type',
    'function',
    'variable',
    'keyword',
    'string',
    'number',
    'comment',
    'operator',
  ],
  tokenModifiers: ['declaration', 'readonly'],
};

const symbolKinds = {
  2: vscode.SymbolKind.Module,
  8: vscode.SymbolKind.Field,
  12: vscode.SymbolKind.Function,
  13: vscode.SymbolKind.Variable,
  14: vscode.SymbolKind.Constant,
  23: vscode.SymbolKind.Struct,
};

const completionKinds = {
  3: vscode.CompletionItemKind.Function,
  5: vscode.CompletionItemKind.Field,
  6: vscode.CompletionItemKind.Variable,
  9: vscode.CompletionItemKind.Module,
  14: vscode.CompletionItemKind.Keyword,
  20: vscode.CompletionItemKind.EnumMember,
  21: vscode.CompletionItemKind.Constant,
  22: vscode.CompletionItemKind.Struct,
};

let diagnosticsCollection;

function diagnostics() {
  if (!diagnosticsCollection) {
    diagnosticsCollection = vscode.languages.createDiagnosticCollection(LANGUAGE);
  }
  return diagnosticsCollection;
}

// VS Code lanzado desde el escritorio no siempre hereda el `PATH` del shell y
// entonces `pengu` no se encuentra aunque esté instalado. Se buscan también las
// ubicaciones habituales y el propio proyecto: el primero que exista es el
// servidor que se ejecuta.
function serverCandidates(command) {
  const executable = process.platform === 'win32' ? `${command}.exe` : command;
  if (command.includes('/') || command.includes('\\')) return [command];

  const candidates = [];
  for (const directory of (process.env.PATH ?? '').split(path.delimiter)) {
    if (directory) candidates.push(path.join(directory, executable));
  }
  const home = require('node:os').homedir();
  candidates.push(
    path.join(home, '.pengu', 'bin', executable),
    path.join(home, 'pengu', 'bin', executable),
    path.join(home, '.local', 'bin', executable),
    path.join('/usr/local/bin', executable),
  );
  for (const folder of vscode.workspace.workspaceFolders ?? []) {
    const root = folder.uri.fsPath;
    candidates.push(
      path.join(root, 'target', 'release', executable),
      path.join(root, 'target', 'debug', executable),
      path.join(root, 'bin', executable),
    );
  }
  return candidates;
}

function resolveServer(command) {
  for (const candidate of serverCandidates(command)) {
    try {
      if (fs.statSync(candidate).isFile()) return candidate;
    } catch {
      // El candidato no existe: se prueba el siguiente.
    }
  }
  return loginShellServer(command);
}

// Último recurso: preguntar al shell de login, que sí lee `.profile`/`.bashrc`
// aunque VS Code se haya abierto desde el escritorio con un `PATH` mínimo.
function loginShellServer(command) {
  if (process.platform === 'win32' || !/^[\w.-]+$/.test(command)) return undefined;
  try {
    const { execFileSync } = require('node:child_process');
    if (typeof execFileSync !== 'function') return undefined;
    const shell = process.env.SHELL || '/bin/sh';
    const found = execFileSync(shell, ['-lc', `command -v ${command}`], {
      encoding: 'utf8',
      timeout: 3000,
    }).trim();
    if (found && fs.statSync(found).isFile()) return found;
  } catch {
    // Sin shell, sin resultado o sin permiso: se deja que el error de arranque
    // muestre el mensaje con la ruta configurada.
  }
  return undefined;
}

class LspClient {
  constructor(output, command, logFile) {
    this.output = output;
    this.command = command;
    this.logFile = logFile;
    this.nextId = 1;
    this.pending = new Map();
    this.buffer = Buffer.alloc(0);
    this.notifications = new Set();
    this.exitHandlers = new Set();
    this.process = undefined;
    this.ready = false;
    this.queue = [];
    this.disposed = false;
  }

  start() {
    this.process = spawn(this.command, ['lsp'], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, ...(this.logFile ? { PENGU_LSP_LOG: this.logFile } : {}) },
    });
    this.process.stdout.on('data', (chunk) => this.onData(chunk));
    this.process.stderr.on('data', (chunk) => {
      this.output.appendLine(`[servidor] ${chunk.toString().trimEnd()}`);
    });
    this.process.on('error', (error) => {
      this.output.appendLine(`[error] no se pudo ejecutar \`${this.command}\`: ${error.message}`);
      this.failAll(new Error(`no se pudo ejecutar \`${this.command}\`: ${error.message}`));
      for (const handler of this.exitHandlers) handler(-1, error);
    });
    this.process.on('exit', (code) => {
      this.ready = false;
      this.failAll(new Error(`el servidor terminó con código ${code}`));
      if (!this.disposed) {
        for (const handler of this.exitHandlers) handler(code);
      }
    });
    return this;
  }

  failAll(error) {
    for (const [, entry] of this.pending) entry.reject(error);
    this.pending.clear();
    this.queue = [];
  }

  onData(chunk) {
    this.buffer = Buffer.concat([this.buffer, chunk]);
    for (;;) {
      const headerEnd = this.buffer.indexOf('\r\n\r\n');
      if (headerEnd < 0) return;
      const header = this.buffer.subarray(0, headerEnd).toString('ascii');
      const match = /content-length:\s*(\d+)/i.exec(header);
      if (!match) {
        this.buffer = this.buffer.subarray(headerEnd + 4);
        continue;
      }
      const length = Number.parseInt(match[1], 10);
      const start = headerEnd + 4;
      if (this.buffer.length < start + length) return;
      const body = this.buffer.subarray(start, start + length).toString('utf8');
      this.buffer = this.buffer.subarray(start + length);
      let message;
      try {
        message = JSON.parse(body);
      } catch (error) {
        this.output.appendLine(`[error] mensaje no válido: ${error.message}`);
        continue;
      }
      this.onMessage(message);
    }
  }

  onMessage(message) {
    if (message.method) {
      if (message.id !== undefined) {
        // El servidor no hace peticiones al cliente: se responde `null`.
        this.write({ jsonrpc: '2.0', id: message.id, result: null });
      }
      for (const handler of this.notifications) handler(message);
      return;
    }
    const entry = this.pending.get(message.id);
    if (!entry) return;
    this.pending.delete(message.id);
    if (message.error) {
      entry.reject(new Error(message.error.message ?? 'error del servidor'));
    } else {
      entry.resolve(message.result);
    }
  }

  write(message) {
    if (!this.process?.stdin.writable) return;
    const body = Buffer.from(JSON.stringify(message), 'utf8');
    this.process.stdin.write(`Content-Length: ${body.length}\r\n\r\n`);
    this.process.stdin.write(body);
  }

  send(message) {
    if (!this.ready && message.method !== 'initialize') {
      this.queue.push(message);
      return;
    }
    this.write(message);
  }

  flush() {
    this.ready = true;
    const queue = this.queue;
    this.queue = [];
    for (const message of queue) this.write(message);
  }

  request(method, params) {
    const id = this.nextId++;
    const promise = new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
    this.send({ jsonrpc: '2.0', id, method, params });
    return promise;
  }

  notify(method, params) {
    this.send({ jsonrpc: '2.0', method, params });
  }

  onNotification(handler) {
    this.notifications.add(handler);
    return () => this.notifications.delete(handler);
  }

  onExit(handler) {
    this.exitHandlers.add(handler);
  }

  async stop() {
    this.disposed = true;
    try {
      await this.request('shutdown', null);
      this.write({ jsonrpc: '2.0', method: 'exit', params: null });
    } catch {
      // El servidor pudo cerrarse antes.
    }
    this.process?.kill();
  }
}

function toRange(range) {
  return new vscode.Range(
    range.start.line,
    range.start.character,
    range.end.line,
    range.end.character,
  );
}

function toLocation(location) {
  return new vscode.Location(vscode.Uri.parse(location.uri), toRange(location.range));
}

function toPosition(position) {
  return { line: position.line, character: position.character };
}

function documentUri(document) {
  return document.uri.toString(true);
}

function projectRoot(document) {
  if (!document) return undefined;
  let directory = path.dirname(document.uri.fsPath);
  for (;;) {
    if (fs.existsSync(path.join(directory, 'Tome.toml'))) return directory;
    const parent = path.dirname(directory);
    if (parent === directory) return undefined;
    directory = parent;
  }
}

function workspaceFolders() {
  const folders = vscode.workspace.workspaceFolders ?? [];
  return folders.map((folder) => ({ uri: folder.uri.toString(true), name: folder.name }));
}


async function runInTerminal(document, command) {
  if (!document) {
    void vscode.window.showWarningMessage('Abre un archivo de PenguScript para ejecutarlo.');
    return;
  }
  const root = projectRoot(document);
  if (!root) {
    void vscode.window.showWarningMessage(
      'No encontré `Tome.toml`: abre la carpeta del proyecto para ejecutarlo.',
    );
    return;
  }
  await document.save();
  const terminal =
    vscode.window.terminals.find((item) => item.name === 'PenguScript') ??
    vscode.window.createTerminal({ name: 'PenguScript', cwd: root });
  terminal.show(true);
  terminal.sendText(command);
}

class State {
  constructor(context, output) {
    this.context = context;
    this.output = output;
    this.client = undefined;
    this.status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    this.status.command = 'pengu.restartServer';
    this.status.text = '$(sync~spin) PenguScript';
    this.status.tooltip = 'Arrancando el servidor LSP de PenguScript';
    this.status.show();
    this.context.subscriptions.push(this.status);
  }

  configuration() {
    const configuration = vscode.workspace.getConfiguration('pengu');
    return {
      command: configuration.get('serverPath', 'pengu'),
      logFile: configuration.get('logFile', ''),
    };
  }

  async start() {
    const { command, logFile } = this.configuration();
    const server = resolveServer(command);
    if (server) {
      this.output.appendLine(`[info] servidor: ${server}`);
    } else {
      this.output.appendLine(`[error] no se encontró \`${command}\` en: ${serverCandidates(command).join(', ')}`);
    }
    this.client = new LspClient(this.output, server ?? command, logFile).start();
    this.client.onExit((code, error) => this.serverStopped(code, error));
    this.client.onNotification((message) => this.onNotification(message));

    this.status.text = '$(sync~spin) PenguScript';
    this.status.tooltip = 'Arrancando `pengu lsp`…';

    const initialize = this.client.request('initialize', {
      processId: process.pid,
      clientInfo: { name: 'pengu-vscode' },
      rootUri: vscode.workspace.workspaceFolders?.[0]?.uri.toString(true) ?? null,
      capabilities: {
        general: { positionEncodings: ['utf-16'] },
        textDocument: {
          hover: { contentFormat: ['markdown', 'plaintext'] },
          completion: {
            completionItem: {
              snippetSupport: true,
              documentationFormat: ['markdown', 'plaintext'],
            },
            contextSupport: true,
          },
          documentSymbol: { hierarchicalDocumentSymbolSupport: true },
          publishDiagnostics: { relatedInformation: true },
          semanticTokens: {
            requests: { range: true, full: true },
            tokenTypes: SEMANTIC_LEGEND.tokenTypes,
            tokenModifiers: SEMANTIC_LEGEND.tokenModifiers,
            formats: ['relative'],
          },
          inlayHint: {},
          codeLens: {},
          signatureHelp: { signatureInformation: { documentationFormat: ['markdown'] } },
          rename: { prepareSupport: true },
        },
        workspace: { workspaceFolders: true, symbol: {} },
      },
      workspaceFolders: workspaceFolders(),
    });

    try {
      await initialize;
    } catch (error) {
      this.status.text = '$(error) PenguScript';
      this.status.tooltip = error.message;
      this.output.appendLine(`[error] initialize falló: ${error.message}`);
      const action = await vscode.window.showErrorMessage(
        `El servidor de PenguScript no arrancó: ${error.message}`,
        'Instalar / comprobar',
        'Configurar ruta',
        'Ver registro',
      );
      if (action === 'Instalar / comprobar') {
        void vscode.env.openExternal(
          vscode.Uri.parse('https://github.com/TuGatito/PenguScript-Rust/blob/main/docs/INSTALL.md'),
        );
      } else if (action === 'Configurar ruta') {
        void vscode.commands.executeCommand('workbench.action.openSettings', 'pengu.serverPath');
      } else if (action === 'Ver registro') {
        this.output.show();
      }
      return false;
    }

    this.client.flush();
    this.client.notify('initialized', {});
    this.status.text = '$(check) PenguScript';
    this.status.tooltip = 'Servidor LSP de PenguScript en marcha';
    this.output.appendLine('[info] servidor LSP iniciado');

    for (const document of vscode.workspace.textDocuments) {
      if (document.languageId === LANGUAGE) this.didOpen(document);
    }
    return true;
  }

  async restart() {
    if (this.client) {
      await this.client.stop();
      this.client = undefined;
    }
    this.output.appendLine('[info] reiniciando el servidor LSP');
    await this.start();
  }

  serverStopped(code, error) {
    this.status.text = '$(warning) PenguScript';
    this.status.tooltip = `El servidor se detuvo (código ${code}). Pulsa para reiniciar.`;
    if (code === -1) {
      void vscode.window
        .showErrorMessage(
          `No se encontró \`${this.configuration().command}\`. Instala el compilador con scripts/install.sh o configura \`pengu.serverPath\`.`,
          'Abrir ajustes',
        )
        .then((action) => {
          if (action === 'Abrir ajustes') {
            void vscode.commands.executeCommand('workbench.action.openSettings', 'pengu.serverPath');
          }
        });
    } else {
      this.output.appendLine(`[aviso] el servidor terminó con código ${code}`);
    }
  }

  didOpen(document) {
    this.client?.notify('textDocument/didOpen', {
      textDocument: {
        uri: documentUri(document),
        languageId: LANGUAGE,
        version: document.version,
        text: document.getText(),
      },
    });
  }

  onNotification(message) {
    if (message.method !== 'textDocument/publishDiagnostics') return;
    const params = message.params;
    const items = (params.diagnostics ?? []).map((item) => {
      const diagnostic = new vscode.Diagnostic(
        toRange(item.range),
        item.message,
        item.severity === 1
          ? vscode.DiagnosticSeverity.Error
          : item.severity === 3
            ? vscode.DiagnosticSeverity.Information
            : vscode.DiagnosticSeverity.Warning,
      );
      diagnostic.source = item.source ?? 'pengu';
      if (item.code) diagnostic.code = item.code;
      return diagnostic;
    });
    diagnostics().set(vscode.Uri.parse(params.uri), items);
  }
}

function registerProviders(context, state, documents, versions) {
  const feature = (method, params) => state.client.request(method, params);
  const textDocument = (document) => ({ uri: documentUri(document) });

  context.subscriptions.push(
    vscode.languages.registerHoverProvider(LANGUAGE, {
      provideHover: async (document, position) => {
        const result = await feature('textDocument/hover', {
          textDocument: textDocument(document),
          position: toPosition(position),
        });
        if (!result) return undefined;
        const contents = result.contents;
        const value = typeof contents === 'string' ? contents : contents.value;
        return new vscode.Hover(
          new vscode.MarkdownString(value ?? ''),
          result.range ? toRange(result.range) : undefined,
        );
      },
    }),

    vscode.languages.registerCompletionItemProvider(
      LANGUAGE,
      {
        provideCompletionItems: async (document, position) => {
          const result = await feature('textDocument/completion', {
            textDocument: textDocument(document),
            position: toPosition(position),
          });
          const items = (result?.items ?? []).map((item) => {
            const completion = new vscode.CompletionItem(
              item.label,
              completionKinds[item.kind] ?? vscode.CompletionItemKind.Text,
            );
            if (item.detail) completion.detail = item.detail;
            if (item.documentation) {
              completion.documentation = new vscode.MarkdownString(String(item.documentation));
            }
            if (item.sortText) completion.sortText = item.sortText;
            if (item.filterText) completion.filterText = item.filterText;
            if (item.insertText) {
              completion.insertText = item.insertText;
              completion.insertTextFormat =
                item.insertTextFormat === 2
                  ? vscode.InsertTextFormat.Snippet
                  : vscode.InsertTextFormat.PlainText;
            }
            return completion;
          });
          return new vscode.CompletionList(items, false);
        },
      },
      '.',
      ':',
      ' ',
    ),

    vscode.languages.registerDefinitionProvider(LANGUAGE, {
      provideDefinition: async (document, position) => {
        const result = await feature('textDocument/definition', {
          textDocument: textDocument(document),
          position: toPosition(position),
        });
        if (!result) return undefined;
        return (Array.isArray(result) ? result : [result]).map(toLocation);
      },
    }),

    vscode.languages.registerTypeDefinitionProvider(LANGUAGE, {
      provideTypeDefinition: async (document, position) => {
        const result = await feature('textDocument/typeDefinition', {
          textDocument: textDocument(document),
          position: toPosition(position),
        });
        if (!result) return undefined;
        return (Array.isArray(result) ? result : [result]).map(toLocation);
      },
    }),

    vscode.languages.registerImplementationProvider(LANGUAGE, {
      provideImplementation: async (document, position) => {
        const result = await feature('textDocument/implementation', {
          textDocument: textDocument(document),
          position: toPosition(position),
        });
        if (!result) return undefined;
        return (Array.isArray(result) ? result : [result]).map(toLocation);
      },
    }),

    vscode.languages.registerReferenceProvider(LANGUAGE, {
      provideReferences: async (document, position, referenceContext) => {
        const result = await feature('textDocument/references', {
          textDocument: textDocument(document),
          position: toPosition(position),
          context: { includeDeclaration: referenceContext.includeDeclaration },
        });
        return (result ?? []).map(toLocation);
      },
    }),

    vscode.languages.registerDocumentHighlightProvider(LANGUAGE, {
      provideDocumentHighlights: async (document, position) => {
        const result = await feature('textDocument/documentHighlight', {
          textDocument: textDocument(document),
          position: toPosition(position),
        });
        return (result ?? []).map((item) => {
          const kind =
            item.kind === 3
              ? vscode.DocumentHighlightKind.Write
              : item.kind === 2
                ? vscode.DocumentHighlightKind.Read
                : vscode.DocumentHighlightKind.Text;
          return new vscode.DocumentHighlight(toRange(item.range), kind);
        });
      },
    }),

    vscode.languages.registerRenameProvider(LANGUAGE, {
      prepareRename: async (document, position) => {
        const result = await feature('textDocument/prepareRename', {
          textDocument: textDocument(document),
          position: toPosition(position),
        });
        if (!result) throw new Error('no se puede renombrar este símbolo');
        return { range: toRange(result.range), placeholder: result.placeholder };
      },
      provideRenameEdits: async (document, position, newName) => {
        const result = await feature('textDocument/rename', {
          textDocument: textDocument(document),
          position: toPosition(position),
          newName,
        });
        if (!result) return undefined;
        const edit = new vscode.WorkspaceEdit();
        for (const [uri, changes] of Object.entries(result.changes ?? {})) {
          for (const change of changes) {
            edit.replace(vscode.Uri.parse(uri), toRange(change.range), change.newText);
          }
        }
        return edit;
      },
    }),

    vscode.languages.registerSignatureHelpProvider(
      LANGUAGE,
      {
        provideSignatureHelp: async (document, position) => {
          const result = await feature('textDocument/signatureHelp', {
            textDocument: textDocument(document),
            position: toPosition(position),
          });
          if (!result) return undefined;
          const help = new vscode.SignatureHelp();
          help.signatures = (result.signatures ?? []).map((signature) => {
            const information = new vscode.SignatureInformation(signature.label);
            information.parameters = (signature.parameters ?? []).map(
              (parameter) => new vscode.ParameterInformation(parameter.label),
            );
            if (signature.documentation) {
              information.documentation = new vscode.MarkdownString(String(signature.documentation));
            }
            return information;
          });
          help.activeSignature = result.activeSignature ?? 0;
          help.activeParameter = result.activeParameter ?? 0;
          return help;
        },
      },
      '(',
      ',',
    ),

    vscode.languages.registerFoldingRangeProvider(LANGUAGE, {
      provideFoldingRanges: async (document) => {
        const result = await feature('textDocument/foldingRange', {
          textDocument: textDocument(document),
        });
        return (result ?? []).map(
          (range) =>
            new vscode.FoldingRange(
              range.startLine,
              range.endLine,
              range.kind === 'comment'
                ? vscode.FoldingRangeKind.Comment
                : range.kind === 'imports'
                  ? vscode.FoldingRangeKind.Imports
                  : vscode.FoldingRangeKind.Region,
            ),
        );
      },
    }),

    vscode.languages.registerSelectionRangeProvider(LANGUAGE, {
      provideSelectionRanges: async (document, positions) => {
        const result = await feature('textDocument/selectionRange', {
          textDocument: textDocument(document),
          positions: positions.map(toPosition),
        });
        const build = (item) => {
          if (!item) return undefined;
          return new vscode.SelectionRange(toRange(item.range), build(item.parent));
        };
        return (result ?? []).map(build);
      },
    }),

    vscode.languages.registerDocumentSymbolProvider(LANGUAGE, {
      provideDocumentSymbols: async (document) => {
        const result = await feature('textDocument/documentSymbol', {
          textDocument: textDocument(document),
        });
        return (result ?? []).map((symbol) => ({
          name: symbol.name,
          kind: symbolKinds[symbol.kind] ?? vscode.SymbolKind.Function,
          detail: symbol.detail ?? '',
          range: toRange(symbol.range),
          selectionRange: toRange(symbol.selectionRange ?? symbol.range),
          children: [],
        }));
      },
    }),

    vscode.languages.registerWorkspaceSymbolProvider({
      provideWorkspaceSymbols: async (query) => {
        const result = await feature('workspace/symbol', { query });
        return (result ?? []).map(
          (symbol) =>
            new vscode.SymbolInformation(
              symbol.name,
              symbolKinds[symbol.kind] ?? vscode.SymbolKind.Function,
              '',
              toLocation(symbol.location),
            ),
        );
      },
    }),

    vscode.languages.registerDocumentFormattingEditProvider(LANGUAGE, {
      provideDocumentFormattingEdits: async (document) => {
        const result = await feature('textDocument/formatting', {
          textDocument: textDocument(document),
          options: { tabSize: 4, insertSpaces: true },
        });
        return (result ?? []).map((edit) => new vscode.TextEdit(toRange(edit.range), edit.newText));
      },
    }),

    vscode.languages.registerInlayHintsProvider(LANGUAGE, {
      provideInlayHints: async (document, range) => {
        const result = await feature('textDocument/inlayHint', {
          textDocument: textDocument(document),
          range: { start: toPosition(range.start), end: toPosition(range.end) },
        });
        return (result ?? []).map((hint) => {
          const inlay = new vscode.InlayHint(
            new vscode.Position(hint.position.line, hint.position.character),
            hint.label,
            hint.kind === 2 ? vscode.InlayHintKind.Type : vscode.InlayHintKind.Parameter,
          );
          if (hint.paddingLeft) inlay.paddingLeft = true;
          if (hint.paddingRight) inlay.paddingRight = true;
          if (hint.tooltip) inlay.tooltip = hint.tooltip;
          return inlay;
        });
      },
    }),

    vscode.languages.registerCodeLensProvider(LANGUAGE, {
      provideCodeLenses: async (document) => {
        const lenses = [];
        const result = await feature('textDocument/codeLens', {
          textDocument: textDocument(document),
        });
        for (const lens of result ?? []) {
          const name = lens.command?.command;
          if (name === 'pengu.run') {
            lenses.push(
              new vscode.CodeLens(toRange(lens.range), {
                title: lens.command?.title ?? '▶ Ejecutar programa',
                command: 'pengu.run',
                arguments: [document],
              }),
            );
            continue;
          }
          lenses.push(
            new vscode.CodeLens(toRange(lens.range), {
              title: lens.command?.title ?? 'ejecutar test',
              command: 'pengu.runTest',
              arguments: [document.uri.toString(true), lens.command?.arguments?.[1] ?? ''],
            }),
          );
        }
        return lenses;
      },
    }),

    vscode.languages.registerDocumentSemanticTokensProvider(
      LANGUAGE,
      {
        provideDocumentSemanticTokens: async (document) => {
          const result = await feature('textDocument/semanticTokens/full', {
            textDocument: textDocument(document),
          });
          return result ? new vscode.SemanticTokens(Uint32Array.from(result.data ?? [])) : undefined;
        },
      },
      SEMANTIC_LEGEND,
    ),

    vscode.languages.registerCodeActionsProvider(LANGUAGE, {
      provideCodeActions: async (document, range, codeActionContext) => {
        const result = await feature('textDocument/codeAction', {
          textDocument: textDocument(document),
          range: { start: toPosition(range.start), end: toPosition(range.end) },
          context: {
            diagnostics: codeActionContext.diagnostics.map((diagnostic) => ({
              range: {
                start: {
                  line: diagnostic.range.start.line,
                  character: diagnostic.range.start.character,
                },
                end: { line: diagnostic.range.end.line, character: diagnostic.range.end.character },
              },
              message: diagnostic.message,
              code: typeof diagnostic.code === 'object' ? diagnostic.code.value : (diagnostic.code ?? ''),
              severity: diagnostic.severity === vscode.DiagnosticSeverity.Error ? 1 : 2,
              source: diagnostic.source ?? 'pengu',
            })),
          },
        });
        return (result ?? []).map((action) => {
          const item = new vscode.CodeAction(action.title, vscode.CodeActionKind.QuickFix);
          if (action.edit?.changes) {
            const edit = new vscode.WorkspaceEdit();
            for (const [uri, changes] of Object.entries(action.edit.changes)) {
              for (const change of changes) {
                edit.insert(vscode.Uri.parse(uri), toRange(change.range).start, change.newText);
              }
            }
            item.edit = edit;
          }
          return item;
        });
      },
    }),

    vscode.languages.registerCallHierarchyProvider(LANGUAGE, {
      prepareCallHierarchy: async (document, position) => {
        const result = await feature('textDocument/prepareCallHierarchy', {
          textDocument: textDocument(document),
          position: toPosition(position),
        });
        return (result ?? []).map(toCallHierarchyItem);
      },
      provideCallHierarchyIncomingCalls: async (item) => {
        const result = await feature('callHierarchy/incomingCalls', { item: toCallItem(item) });
        return (result ?? []).map((call) => ({
          from: toCallHierarchyItem(call.from),
          fromRanges: (call.fromRanges ?? []).map(toRange),
        }));
      },
      provideCallHierarchyOutgoingCalls: async (item) => {
        const result = await feature('callHierarchy/outgoingCalls', { item: toCallItem(item) });
        return (result ?? []).map((call) => ({
          to: toCallHierarchyItem(call.to),
          fromRanges: (call.fromRanges ?? []).map(toRange),
        }));
      },
    }),
  );

  const sync = (document) => {
    const version = (versions.get(documentUri(document)) ?? document.version) + 1;
    versions.set(documentUri(document), version);
    state.client.notify('textDocument/didChange', {
      textDocument: { uri: documentUri(document), version },
      contentChanges: [{ text: document.getText() }],
    });
  };

  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument((document) => {
      if (document.languageId !== LANGUAGE) return;
      documents.set(documentUri(document), document);
      versions.set(documentUri(document), document.version);
      state.didOpen(document);
    }),
    vscode.workspace.onDidChangeTextDocument((event) => {
      if (event.document.languageId === LANGUAGE) sync(event.document);
    }),
    vscode.workspace.onDidSaveTextDocument((document) => {
      if (document.languageId !== LANGUAGE) return;
      state.client.notify('textDocument/didSave', { textDocument: textDocument(document) });
    }),
    vscode.workspace.onDidCloseTextDocument((document) => {
      if (document.languageId !== LANGUAGE) return;
      documents.delete(documentUri(document));
      state.client.notify('textDocument/didClose', { textDocument: textDocument(document) });
      diagnostics().delete(document.uri);
    }),
  );
}

function toCallItem(item) {
  return {
    name: item.name,
    kind: 12,
    detail: item.detail,
    uri: item.uri.toString(true),
    range: { start: toPosition(item.range.start), end: toPosition(item.range.end) },
    selectionRange: {
      start: toPosition(item.selectionRange.start),
      end: toPosition(item.selectionRange.end),
    },
  };
}

function toCallHierarchyItem(item) {
  return new vscode.CallHierarchyItem(
    symbolKinds[item.kind] ?? vscode.SymbolKind.Function,
    item.name,
    item.detail ?? '',
    vscode.Uri.parse(item.uri),
    toRange(item.range),
    toRange(item.selectionRange ?? item.range),
  );
}

async function activate(context) {
  const output = vscode.window.createOutputChannel(OUTPUT_NAME);
  context.subscriptions.push(output);
  const state = new State(context, output);
  const documents = new Map();
  const versions = new Map();

  registerProviders(context, state, documents, versions);

  context.subscriptions.push(
    vscode.commands.registerCommand('pengu.run', (document) =>
      runInTerminal(document ?? vscode.window.activeTextEditor?.document, 'pengu run'),
    ),
    vscode.commands.registerCommand('pengu.test', (document) =>
      runInTerminal(document ?? vscode.window.activeTextEditor?.document, 'pengu test'),
    ),
    vscode.commands.registerCommand('pengu.check', (document) =>
      runInTerminal(document ?? vscode.window.activeTextEditor?.document, 'pengu check'),
    ),
    vscode.commands.registerCommand('pengu.runTest', (_uri, name) => {
      const document = vscode.window.activeTextEditor?.document;
      if (name) output.appendLine(`[info] prueba: ${name}`);
      return runInTerminal(document, 'pengu test');
    }),
    vscode.commands.registerCommand('pengu.restartServer', () => state.restart()),
    vscode.commands.registerCommand('pengu.showOutput', () => output.show()),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration('pengu.serverPath') || event.affectsConfiguration('pengu.logFile')) {
        void state.restart();
      }
    }),
  );

  await state.start();
  context.subscriptions.push({ dispose: () => void state.client?.stop() });
}

function deactivate() {
  diagnosticsCollection?.dispose();
}

module.exports = { activate, deactivate, resolveServer };
