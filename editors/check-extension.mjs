// Verifica que la extensión se activa y arranca el servidor sin VS Code.
//
//   node editors/check-extension.mjs [ruta-al-binario-pengu]
//
// Carga `editors/vscode/src/extension.js` con un `vscode` simulado, comprueba
// que registra los providers y que lanza `pengu lsp`. No sustituye a probarla
// en VS Code, pero atrapa errores de API y de arranque en CI.

import Module from 'node:module';
import { spawn } from 'node:child_process';
import { mkdirSync, mkdtempSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const serverPath = process.argv[2] ?? 'target/debug/pengu';
const root = mkdtempSync(join(tmpdir(), 'pengu-ext-'));
writeFileSync(
  join(root, 'Tome.toml'),
  '[tome]\nname = "demo"\nversion = "0.1.0"\npengu = "0.1"\nedition = "2024"\n\n[[bin]]\nname = "demo"\npath = "main.pengu"\n',
);
const source = 'valor = () -> Int\n    1\n\ngrimoire\n    print(valor())\n';
writeFileSync(join(root, 'main.pengu'), source);

const registered = [];
const spawned = [];
const status = { text: '', command: '', tooltip: '', show: dispose };
const disposables = [];

function dispose() {}

class Uri {
  constructor(path) {
    this.fsPath = path;
    this.path = path;
    this.scheme = 'file';
  }
  static file(path) {
    return new Uri(path);
  }
  static parse(value) {
    return new Uri(value.replace(/^file:\/\//, ''));
  }
  toString() {
    return `file://${this.fsPath}`;
  }
}

class Position {
  constructor(line, character) {
    this.line = line;
    this.character = character;
  }
}

class Range {
  constructor(start, end) {
    this.start = start;
    this.end = end;
  }
}

class CompletionItem {
  constructor(label, kind) {
    this.label = label;
    this.kind = kind;
  }
}

class CodeLens {
  constructor(range, command) {
    this.range = range;
    this.command = command;
  }
}

class InlayHint {
  constructor(position, label) {
    this.position = position;
    this.label = label;
  }
}

class SemanticTokens {
  constructor(data) {
    this.data = data;
  }
}

function provider(kind) {
  return () => {
    registered.push(kind);
    return { dispose };
  };
}

const document = {
  uri: Uri.file(join(root, 'main.pengu')),
  languageId: 'pengu',
  fileName: join(root, 'main.pengu'),
  version: 1,
  lineCount: source.split('\n').length,
  getText: () => source,
  positionAt: (offset) => {
    const before = source.slice(0, offset).split('\n');
    return new Position(before.length - 1, before[before.length - 1].length);
  },
  offsetAt: (position) => {
    const lines = source.split('\n');
    let offset = 0;
    for (let line = 0; line < position.line; line += 1) {
      offset += lines[line].length + 1;
    }
    return offset + position.character;
  },
  save: async () => true,
};

function event() {
  return { dispose };
}

const mock = {
  Uri,
  Position,
  Range,
  Location: class Location {
    constructor(uri, range) {
      this.uri = uri;
      this.range = range;
    }
  },
  CodeLens,
  CompletionItem,
  InlayHint,
  SemanticTokens,
  SemanticTokensLegend: class {},
  SemanticTokensEdit: class {},
  Diagnostic: class {
    constructor(range, message, severity) {
      this.range = range;
      this.message = message;
      this.severity = severity;
    }
  },
  DocumentHighlight: class {
    constructor(range, kind) {
      this.range = range;
      this.kind = kind;
    }
  },
  FoldingRange: class {
    constructor(start, end, kind) {
      this.start = start;
      this.end = end;
      this.kind = kind;
    }
  },
  SelectionRange: class {
    constructor(range) {
      this.range = range;
    }
  },
  SignatureHelp: class {},
  SignatureInformation: class {},
  ParameterInformation: class {},
  TextEdit: {
    replace: (range, newText) => ({ range, newText }),
    insert: (position, newText) => ({ position, newText }),
  },
  CodeAction: class {
    constructor(title, kind) {
      this.title = title;
      this.kind = kind;
    }
  },
  CodeActionKind: { QuickFix: 'quickfix' },
  DocumentSymbol: class {
    constructor(name, detail, kind, range, selectionRange) {
      Object.assign(this, { name, detail, kind, range, selectionRange });
    }
  },
  SymbolInformation: class {
    constructor(name, kind, range) {
      Object.assign(this, { name, kind, range });
    }
  },
  CallHierarchyItem: class {},
  CallHierarchyIncomingCall: class {},
  CallHierarchyOutgoingCall: class {},
  StatusBarAlignment: { Left: 1, Right: 2 },
  DiagnosticSeverity: { Error: 0, Warning: 1, Information: 2, Hint: 3 },
  CompletionItemKind: {
    Text: 0,
    Variable: 5,
    Function: 2,
    Field: 4,
    Module: 8,
    Constant: 20,
    Struct: 21,
    EnumMember: 19,
    Keyword: 13,
  },
  SymbolKind: { Function: 11, Module: 1, Constant: 13, Struct: 22, Field: 7, Variable: 12 },
  DocumentHighlightKind: { Text: 0, Read: 1, Write: 2 },
  FoldingRangeKind: { Comment: 1, Region: 2, Imports: 3 },
  InlayHintKind: { Type: 1, Parameter: 2 },
  InsertTextFormat: { PlainText: 1, Snippet: 2 },
  EndOfLine: { LF: 1 },
  languages: {
    createDiagnosticCollection: () => ({ set: dispose, clear: dispose, dispose }),
    registerHoverProvider: provider('hover'),
    registerCompletionItemProvider: provider('completion'),
    registerDefinitionProvider: provider('definition'),
    registerTypeDefinitionProvider: provider('typeDefinition'),
    registerImplementationProvider: provider('implementation'),
    registerReferenceProvider: provider('references'),
    registerDocumentHighlightProvider: provider('highlight'),
    registerRenameProvider: provider('rename'),
    registerSignatureHelpProvider: provider('signature'),
    registerFoldingRangeProvider: provider('folding'),
    registerSelectionRangeProvider: provider('selection'),
    registerDocumentSymbolProvider: provider('documentSymbol'),
    registerWorkspaceSymbolProvider: provider('workspaceSymbol'),
    registerDocumentFormattingEditProvider: provider('formatting'),
    registerInlayHintsProvider: provider('inlayHints'),
    registerCodeLensProvider: provider('codeLens'),
    registerDocumentSemanticTokensProvider: provider('semanticTokens'),
    registerCodeActionsProvider: provider('codeActions'),
    registerCallHierarchyProvider: provider('callHierarchy'),
  },
  commands: {
    registerCommand: (name) => {
      registered.push(`command:${name}`);
      return { dispose };
    },
    executeCommand: async () => undefined,
  },
  window: {
    activeTextEditor: { document },
    terminals: [],
    createStatusBarItem: () => status,
    createOutputChannel: () => ({ appendLine: dispose, show: dispose, dispose }),
    createTerminal: () => ({ sendText: dispose, show: dispose }),
    showErrorMessage: async () => undefined,
    showWarningMessage: async () => undefined,
    showInformationMessage: async () => undefined,
  },
  workspace: {
    workspaceFolders: [{ uri: Uri.file(root) }],
    textDocuments: [document],
    getConfiguration: () => ({
      get: (key, fallback) => (key === 'serverPath' ? serverPath : fallback),
    }),
    getWorkspaceFolder: () => ({ uri: Uri.file(root) }),
    onDidOpenTextDocument: event,
    onDidChangeTextDocument: event,
    onDidSaveTextDocument: event,
    onDidCloseTextDocument: event,
    onDidChangeConfiguration: event,
  },
  env: { openExternal: async () => true },
};

const load = Module._load;
Module._load = function patched(request, parent, isMain) {
  // Solo `vscode`: si la extensión usara `node:vscode`, Node lo trataría como
  // builtin y fallaría, igual que en el host real. Así la prueba lo detecta.
  if (request === 'vscode') {
    return mock;
  }
  if (request === 'node:child_process') {
    return {
      spawn: (command, args, options) => {
        spawned.push({ command, args, options });
        return spawn(command, args, options);
      },
    };
  }
  return load.call(this, request, parent, isMain);
};

const modulePath = new URL('./vscode/src/extension.js', import.meta.url);
const extension = await import(pathToFileURL(modulePath.pathname).href);

const context = { subscriptions: { push: (item) => disposables.push(item) } };
extension.activate(context);

const deadline = Date.now() + 5000;
while (Date.now() < deadline && spawned.length === 0) {
  await new Promise((resolve) => setTimeout(resolve, 50));
}
if (spawned.length === 0) {
  throw new Error('la extensión no lanzó `pengu lsp`');
}
const expectedCommand = extension.resolveServer(serverPath) ?? serverPath;
if (spawned[0].command !== expectedCommand) {
  throw new Error(`lanzó \`${spawned[0].command}\` en vez de \`${expectedCommand}\``);
}
await new Promise((resolve) => setTimeout(resolve, 800));

const expected = [
  'hover',
  'completion',
  'definition',
  'typeDefinition',
  'implementation',
  'references',
  'highlight',
  'rename',
  'signature',
  'folding',
  'selection',
  'documentSymbol',
  'workspaceSymbol',
  'formatting',
  'inlayHints',
  'codeLens',
  'semanticTokens',
  'codeActions',
  'callHierarchy',
  'command:pengu.run',
  'command:pengu.test',
  'command:pengu.check',
  'command:pengu.restartServer',
];
const missing = expected.filter((name) => !registered.includes(name));
if (missing.length > 0) {
  throw new Error(`faltan providers o comandos: ${missing.join(', ')}`);
}
if (!/check|error|warning/.test(status.text)) {
  throw new Error(`la barra de estado no refleja el servidor: "${status.text}"`);
}
// VS Code lanzado desde el escritorio no hereda el `PATH` del shell: el cliente
// debe encontrar `pengu` en el proyecto o en las ubicaciones habituales.
const projectBin = join(root, 'bin');
mkdirSync(projectBin, { recursive: true });
const unique = `pengu-prueba-${process.pid}`;
symlinkSync(resolve(expectedCommand), join(projectBin, unique));
const savedPath = process.env.PATH;
process.env.PATH = '';
const resolved = extension.resolveServer(unique);
process.env.PATH = savedPath;
if (resolved !== join(projectBin, unique)) {
  throw new Error(`no resuelve \`${unique}\` desde el proyecto: ${resolved}`);
}

extension.deactivate();
console.log(`providers: ${registered.length}`);
console.log(`estado: ${status.text}`);
console.log('ok');
process.exit(0);
