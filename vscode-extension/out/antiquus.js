"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AntiquusManager = void 0;
exports.toMirror = toMirror;
exports.fromMirror = fromMirror;
exports.registerAntiquusProviders = registerAntiquusProviders;
const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const vscode = require("vscode");
const node_1 = require("vscode-languageclient/node");
const antiquusModel_1 = require("./antiquusModel");
function mirrorDirectory(context) {
    const base = context.storageUri?.fsPath ?? path.join(os.tmpdir(), 'pengus-vscode');
    return path.join(base, 'antiquus');
}
function hashDocument(uri, folder) {
    return path.join(folder, crypto.createHash('sha256').update(uri.toString()).digest('hex').slice(0, 16));
}
/** Posición del documento de origen → posición del espejo. */
function toMirror(block, position) {
    const p = (0, antiquusModel_1.toMirrorPosition)(block, position);
    return new vscode.Position(p.line, p.character);
}
/** Rango del espejo → rango del documento de origen. */
function fromMirror(block, range) {
    const mapped = (0, antiquusModel_1.fromMirrorRange)(block, range);
    if (!mapped) {
        return undefined;
    }
    return new vscode.Range(mapped.start.line, mapped.start.character, mapped.end.line, mapped.end.character);
}
/**
 * Gestiona los espejos y el cliente de clangd. Se registra una sola vez por
 * ventana; los proveedores consultan `activeBlock` para saber si el cursor
 * está dentro de un cuerpo.
 */
class AntiquusManager {
    constructor(context) {
        this.context = context;
        this.mirrors = new Map(); // mirrorUri → bloques
        this.bySource = new Map();
        this.disposables = [];
        this.mirrorRoot = mirrorDirectory(context);
        this.diagnostics = vscode.languages.createDiagnosticCollection('pengus-antiquus');
        this.disposables.push(this.diagnostics);
        this.disposables.push(vscode.workspace.onDidOpenTextDocument((doc) => this.schedule(doc)), vscode.workspace.onDidChangeTextDocument((ev) => this.schedule(ev.document)), vscode.workspace.onDidCloseTextDocument((doc) => this.forget(doc)));
        for (const doc of vscode.workspace.textDocuments) {
            this.schedule(doc);
        }
    }
    dispose() {
        for (const disposable of this.disposables) {
            disposable.dispose();
        }
        void this.client?.stop();
    }
    /** ¿Está clangd instalado? Se comprueba una sola vez. */
    isAvailable() {
        const config = vscode.workspace.getConfiguration('pengus');
        if (!config.get('antiquus.enabled', true)) {
            return false;
        }
        const command = config.get('antiquus.clangdPath', 'clangd') || 'clangd';
        if (this.available === undefined) {
            this.available = command.includes('/') ? exists(command) : lookPath(command) !== undefined;
        }
        return this.available;
    }
    schedule(document) {
        if (document.languageId !== 'pengus' || document.uri.scheme !== 'file') {
            return;
        }
        if (this.syncTimer) {
            clearTimeout(this.syncTimer);
        }
        this.syncTimer = setTimeout(() => {
            this.syncTimer = undefined;
            void this.sync(document);
        }, 120);
    }
    forget(document) {
        const blocks = this.bySource.get(document.uri.toString());
        if (!blocks) {
            return;
        }
        for (const block of blocks) {
            this.mirrors.delete(block.mirror.toString());
        }
        this.bySource.delete(document.uri.toString());
        this.diagnostics.delete(document.uri);
    }
    /** Regenera los espejos de un documento y avisa a clangd. */
    async sync(document) {
        const text = document.getText();
        const blocks = (0, antiquusModel_1.findAntiquusBlocks)(text);
        const dir = hashDocument(document.uri, this.mirrorRoot);
        const previous = this.bySource.get(document.uri.toString()) ?? [];
        for (const old of previous) {
            this.mirrors.delete(old.mirror.toString());
        }
        const current = [];
        await fs.promises.mkdir(dir, { recursive: true });
        for (const block of blocks) {
            const { lines, offset } = (0, antiquusModel_1.buildMirrorContent)(text, block);
            const file = path.join(dir, `${block.name}.c`);
            await fs.promises.writeFile(file, lines.join('\n') + '\n', 'utf8');
            const mirror = {
                ...block,
                offset,
                source: document.uri,
                mirror: vscode.Uri.file(file)
            };
            current.push(mirror);
            this.mirrors.set(mirror.mirror.toString(), [mirror]);
            if (this.isAvailable()) {
                try {
                    const doc = await vscode.workspace.openTextDocument(mirror.mirror);
                    await this.refreshMirrorDocument(doc, lines);
                }
                catch {
                    /* el fichero existe aunque el editor no lo abra */
                }
            }
        }
        this.bySource.set(document.uri.toString(), current);
        // Olvida diagnósticos cuyo bloque ya no existe.
        this.diagnostics.delete(document.uri);
    }
    async refreshMirrorDocument(doc, lines) {
        const wanted = lines.join('\n');
        if (doc.getText() === wanted) {
            return;
        }
        const edit = new vscode.WorkspaceEdit();
        const last = doc.lineCount;
        edit.replace(doc.uri, new vscode.Range(new vscode.Position(0, 0), doc.lineAt(Math.max(last - 1, 0)).range.end), wanted);
        await vscode.workspace.applyEdit(edit);
        // Se guarda para que clangd vea el contenido actualizado aunque el
        // documento del espejo no esté visible.
        await doc.save();
    }
    /** Bloque del documento en la posición dada (si la hay). */
    activeBlock(document, position) {
        const blocks = this.bySource.get(document.uri.toString());
        if (!blocks) {
            return undefined;
        }
        return blocks.find((block) => (0, antiquusModel_1.insideBody)(block, position));
    }
    /** Bloque cuyo espejo es `uri`. */
    blockForMirror(uri) {
        return this.mirrors.get(uri.toString())?.[0];
    }
    async ensureClient() {
        if (this.client) {
            return this.client;
        }
        if (this.starting) {
            return this.starting;
        }
        if (!this.isAvailable()) {
            return undefined;
        }
        this.starting = (async () => {
            try {
                await fs.promises.mkdir(this.mirrorRoot, { recursive: true });
                const configured = vscode.workspace.getConfiguration('pengus').get('antiquus.clangdPath', 'clangd');
                const serverOptions = {
                    command: configured && configured.length > 0 ? configured : 'clangd',
                    args: ['--log=error', '--background-index=false']
                };
                const clientOptions = {
                    documentSelector: [
                        { scheme: 'file', language: 'c', pattern: `${this.mirrorRoot.replace(/\\/g, '/')}/**/*.c` }
                    ],
                    workspaceFolder: {
                        uri: vscode.Uri.file(this.mirrorRoot),
                        name: 'pengus-antiquus',
                        index: 0
                    },
                    outputChannel: vscode.window.createOutputChannel('PenguScript · clangd (antiquus)'),
                    middleware: {
                        handleDiagnostics: (uri, diagnostics) => this.onDiagnostics(uri, diagnostics)
                    }
                };
                const client = new node_1.LanguageClient('clangd-antiquus', 'clangd (antiquus)', serverOptions, clientOptions);
                await client.start();
                this.client = client;
                return client;
            }
            catch {
                return undefined;
            }
            finally {
                this.starting = undefined;
            }
        })();
        return this.starting;
    }
    onDiagnostics(uri, diagnostics) {
        const block = this.blockForMirror(uri);
        if (!block) {
            return;
        }
        const mapped = [];
        for (const diagnostic of diagnostics) {
            const range = fromMirror(block, diagnostic.range);
            if (!range) {
                continue;
            }
            const item = new vscode.Diagnostic(range, diagnostic.message, diagnostic.severity);
            item.source = 'clangd (antiquus)';
            if (diagnostic.code !== undefined) {
                item.code = diagnostic.code;
            }
            mapped.push(item);
        }
        this.diagnostics.set(block.source, mapped);
    }
    /** Envía una petición a clangd para la posición de un bloque. */
    async request(block, method, position, extra = {}) {
        const client = await this.ensureClient();
        if (!client) {
            return undefined;
        }
        const mirrorPosition = toMirror(block, position);
        try {
            return await client.sendRequest(method, {
                textDocument: { uri: block.mirror.toString() },
                position: { line: mirrorPosition.line, character: mirrorPosition.character },
                ...extra
            });
        }
        catch {
            return undefined;
        }
    }
    /** Aplica un WorkspaceEdit de clangd traduciendo las posiciones. */
    async applyRename(block, newName) {
        const client = await this.ensureClient();
        if (!client) {
            return false;
        }
        const response = await this.request(block, 'textDocument/rename', new vscode.Position(block.bodyStart, 0), { newName });
        if (!response) {
            return false;
        }
        const edit = new vscode.WorkspaceEdit();
        let any = false;
        const apply = (uri, edits) => {
            const target = vscode.Uri.parse(uri);
            const owner = this.blockForMirror(target);
            for (const te of edits) {
                if (owner) {
                    const range = fromMirror(owner, te.range);
                    if (range) {
                        edit.replace(owner.source, range, te.newText);
                        any = true;
                    }
                }
                else {
                    edit.replace(target, te.range, te.newText);
                    any = true;
                }
            }
        };
        for (const change of response.documentChanges ?? []) {
            apply(change.textDocument.uri, change.edits);
        }
        for (const [uri, edits] of Object.entries(response.changes ?? {})) {
            apply(uri, edits);
        }
        return any ? vscode.workspace.applyEdit(edit) : false;
    }
    /** Rango en el espejo para una selección del documento de origen. */
    mirrorRange(block, range) {
        const offset = block.offset;
        return new vscode.Range(range.start.line - block.bodyStart + offset, range.start.character, range.end.line - block.bodyStart + offset, range.end.character);
    }
}
exports.AntiquusManager = AntiquusManager;
function exists(file) {
    try {
        fs.accessSync(file, fs.constants.X_OK);
        return true;
    }
    catch {
        return false;
    }
}
/** Busca un ejecutable en el PATH sin dependencias externas. */
function lookPath(command) {
    const pathValue = process.env.PATH ?? '';
    const exts = process.platform === 'win32' ? (process.env.PATHEXT ?? '.EXE;.CMD;.BAT').split(';') : [''];
    for (const dir of pathValue.split(path.delimiter)) {
        if (!dir) {
            continue;
        }
        for (const ext of exts) {
            const candidate = path.join(dir, command + ext.toLowerCase());
            try {
                if (fs.existsSync(candidate)) {
                    fs.accessSync(candidate, fs.constants.X_OK);
                    return candidate;
                }
            }
            catch {
                /* sigue buscando */
            }
        }
    }
    return undefined;
}
/** Registra los proveedores de C-in-antiquus para el lenguaje `pengus`. */
function registerAntiquusProviders(context) {
    const manager = new AntiquusManager(context);
    const selector = { language: 'pengus', scheme: 'file' };
    const disposables = [manager];
    disposables.push(vscode.languages.registerHoverProvider(selector, {
        async provideHover(document, position) {
            const block = manager.activeBlock(document, position);
            if (!block) {
                return undefined;
            }
            const hover = await manager.request(block, 'textDocument/hover', position);
            return hover ?? undefined;
        }
    }));
    disposables.push(vscode.languages.registerDefinitionProvider(selector, {
        async provideDefinition(document, position) {
            const block = manager.activeBlock(document, position);
            if (!block) {
                return undefined;
            }
            const result = await manager.request(block, 'textDocument/definition', position);
            return mapLocations(manager, result);
        }
    }));
    disposables.push(vscode.languages.registerReferenceProvider(selector, {
        async provideReferences(document, position, ctx) {
            const block = manager.activeBlock(document, position);
            if (!block) {
                return undefined;
            }
            const result = await manager.request(block, 'textDocument/references', position, {
                context: { includeDeclaration: ctx.includeDeclaration }
            });
            return mapLocations(manager, result);
        }
    }));
    disposables.push(vscode.languages.registerRenameProvider(selector, {
        async provideRenameEdits(document, position, newName) {
            const block = manager.activeBlock(document, position);
            if (!block) {
                return undefined;
            }
            const browser = await manager.request(block, 'textDocument/rename', position, { newName });
            if (!browser) {
                return undefined;
            }
            const out = new vscode.WorkspaceEdit();
            const push = (uri, edits) => {
                const target = vscode.Uri.parse(uri);
                const owner = manager.blockForMirror(target);
                for (const te of edits) {
                    if (owner) {
                        const range = fromMirror(owner, te.range);
                        if (range) {
                            out.replace(owner.source, range, te.newText);
                        }
                    }
                    else {
                        out.replace(target, te.range, te.newText);
                    }
                }
            };
            for (const change of browser.documentChanges ?? []) {
                push(change.textDocument.uri, change.edits);
            }
            for (const [uri, edits] of Object.entries(browser.changes ?? {})) {
                push(uri, edits);
            }
            return out;
        }
    }));
    disposables.push(vscode.languages.registerCompletionItemProvider(selector, {
        async provideCompletionItems(document, position) {
            const block = manager.activeBlock(document, position);
            if (!block) {
                return undefined;
            }
            const list = await manager.request(block, 'textDocument/completion', position);
            if (!list) {
                return undefined;
            }
            const items = Array.isArray(list) ? list : list.items ?? [];
            return items.map((item) => {
                if (item.range) {
                    const range = fromMirror(block, item.range);
                    if (range) {
                        item.range = range;
                    }
                }
                return item;
            });
        }
    }, '.', '>', '(', ','));
    disposables.push(vscode.languages.registerSignatureHelpProvider(selector, {
        async provideSignatureHelp(document, position) {
            const block = manager.activeBlock(document, position);
            if (!block) {
                return undefined;
            }
            return manager.request(block, 'textDocument/signatureHelp', position);
        }
    }, '(', ','));
    disposables.push(vscode.languages.registerDocumentHighlightProvider(selector, {
        async provideDocumentHighlights(document, position) {
            const block = manager.activeBlock(document, position);
            if (!block) {
                return undefined;
            }
            const result = await manager.request(block, 'textDocument/documentHighlight', position);
            if (!result) {
                return undefined;
            }
            return result
                .map((highlight) => {
                const range = fromMirror(block, highlight.range);
                return range
                    ? new vscode.DocumentHighlight(range, highlight.kind)
                    : undefined;
            })
                .filter((item) => item !== undefined);
        }
    }));
    disposables.push(vscode.commands.registerCommand('pengus.antiquus.restart', async () => {
        await manager.dispose();
        vscode.window.showInformationMessage('PenguScript: clangd (antiquus) reiniciado.');
    }));
    context.subscriptions.push(...disposables);
    return disposables;
}
function mapLocations(manager, result) {
    if (!result) {
        return undefined;
    }
    const list = Array.isArray(result) ? result : [result];
    const out = [];
    for (const item of list) {
        if ('targetUri' in item) {
            const block = manager.blockForMirror(item.targetUri);
            const range = block ? fromMirror(block, item.targetSelectionRange ?? item.targetRange) : undefined;
            if (block && range) {
                out.push(new vscode.Location(block.source, range));
            }
            continue;
        }
        const block = manager.blockForMirror(item.uri);
        const range = block ? fromMirror(block, item.range) : undefined;
        if (block && range) {
            out.push(new vscode.Location(block.source, range));
        }
    }
    return out;
}
//# sourceMappingURL=antiquus.js.map