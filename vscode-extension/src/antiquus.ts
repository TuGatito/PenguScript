import * as crypto from 'crypto';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { LanguageClient, LanguageClientOptions, ServerOptions } from 'vscode-languageclient/node';
import {
    AntiquusBlock,
    buildMirrorContent,
    findAntiquusBlocks,
    fromMirrorRange,
    insideBody,
    toMirrorPosition
} from './antiquusModel';

/**
 * Soporte de C real dentro de los bloques `antiquus`.
 *
 * PenguScript escribe el C de un bloque como una cadena cruda triple:
 *
 *     antiquus suma_c with a as int, b as int into int:
 *         r"""
 *         return a + b;
 *         """
 *
 * clangd no entiende de cadenas de PenguScript, así que por cada bloque se
 * genera un fichero C *espejo* en el almacenamiento de la extensión con las
 * líneas del cuerpo en la MISMA posición (más una cabecera). Sobre esos
 * espejos se habla con clangd y las posiciones se traducen en ambos sentidos,
 * de forma que los diagnósticos, el hover, la definición, las referencias, el
 * rename y el completado aparecen sobre el `.pengu` original.
 */

export interface MirrorBlock extends AntiquusBlock {
    source: vscode.Uri;
    mirror: vscode.Uri;
    offset: number;
}

function mirrorDirectory(context: vscode.ExtensionContext): string {
    const base = context.storageUri?.fsPath ?? path.join(os.tmpdir(), 'pengus-vscode');
    return path.join(base, 'antiquus');
}

function hashDocument(uri: vscode.Uri, folder: string): string {
    return path.join(
        folder,
        crypto.createHash('sha256').update(uri.toString()).digest('hex').slice(0, 16)
    );
}

/** Posición del documento de origen → posición del espejo. */
export function toMirror(block: AntiquusBlock, position: vscode.Position): vscode.Position {
    const p = toMirrorPosition(block, position);
    return new vscode.Position(p.line, p.character);
}

/** Rango del espejo → rango del documento de origen. */
export function fromMirror(block: AntiquusBlock, range: vscode.Range): vscode.Range | undefined {
    const mapped = fromMirrorRange(block, range);
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
export class AntiquusManager implements vscode.Disposable {
    private readonly mirrorRoot: string;
    private client: LanguageClient | undefined;
    private starting: Promise<LanguageClient | undefined> | undefined;
    private available: boolean | undefined;
    private readonly mirrors = new Map<string, MirrorBlock[]>(); // mirrorUri → bloques
    private readonly bySource = new Map<string, MirrorBlock[]>();
    private readonly diagnostics: vscode.DiagnosticCollection;
    private readonly disposables: vscode.Disposable[] = [];
    private syncTimer: NodeJS.Timeout | undefined;

    constructor(private readonly context: vscode.ExtensionContext) {
        this.mirrorRoot = mirrorDirectory(context);
        this.diagnostics = vscode.languages.createDiagnosticCollection('pengus-antiquus');
        this.disposables.push(this.diagnostics);
        this.disposables.push(
            vscode.workspace.onDidOpenTextDocument((doc) => this.schedule(doc)),
            vscode.workspace.onDidChangeTextDocument((ev) => this.schedule(ev.document)),
            vscode.workspace.onDidCloseTextDocument((doc) => this.forget(doc))
        );
        for (const doc of vscode.workspace.textDocuments) {
            this.schedule(doc);
        }
    }

    dispose(): void {
        for (const disposable of this.disposables) {
            disposable.dispose();
        }
        void this.client?.stop();
    }

    /** ¿Está clangd instalado? Se comprueba una sola vez. */
    isAvailable(): boolean {
        const config = vscode.workspace.getConfiguration('pengus');
        if (!config.get<boolean>('antiquus.enabled', true)) {
            return false;
        }
        const command = config.get<string>('antiquus.clangdPath', 'clangd') || 'clangd';
        if (this.available === undefined) {
            this.available = command.includes('/') ? exists(command) : lookPath(command) !== undefined;
        }
        return this.available;
    }

    private schedule(document: vscode.TextDocument): void {
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

    private forget(document: vscode.TextDocument): void {
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
    async sync(document: vscode.TextDocument): Promise<void> {
        const text = document.getText();
        const blocks = findAntiquusBlocks(text);
        const dir = hashDocument(document.uri, this.mirrorRoot);
        const previous = this.bySource.get(document.uri.toString()) ?? [];
        for (const old of previous) {
            this.mirrors.delete(old.mirror.toString());
        }
        const current: MirrorBlock[] = [];
        await fs.promises.mkdir(dir, { recursive: true });
        for (const block of blocks) {
            const { lines, offset } = buildMirrorContent(text, block);
            const file = path.join(dir, `${block.name}.c`);
            await fs.promises.writeFile(file, lines.join('\n') + '\n', 'utf8');
            const mirror: MirrorBlock = {
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
                } catch {
                    /* el fichero existe aunque el editor no lo abra */
                }
            }
        }
        this.bySource.set(document.uri.toString(), current);
        // Olvida diagnósticos cuyo bloque ya no existe.
        this.diagnostics.delete(document.uri);
    }

    private async refreshMirrorDocument(doc: vscode.TextDocument, lines: string[]): Promise<void> {
        const wanted = lines.join('\n');
        if (doc.getText() === wanted) {
            return;
        }
        const edit = new vscode.WorkspaceEdit();
        const last = doc.lineCount;
        edit.replace(
            doc.uri,
            new vscode.Range(new vscode.Position(0, 0), doc.lineAt(Math.max(last - 1, 0)).range.end),
            wanted
        );
        await vscode.workspace.applyEdit(edit);
        // Se guarda para que clangd vea el contenido actualizado aunque el
        // documento del espejo no esté visible.
        await doc.save();
    }

    /** Bloque del documento en la posición dada (si la hay). */
    activeBlock(document: vscode.TextDocument, position: vscode.Position): MirrorBlock | undefined {
        const blocks = this.bySource.get(document.uri.toString());
        if (!blocks) {
            return undefined;
        }
        return blocks.find((block) => insideBody(block, position));
    }

    /** Bloque cuyo espejo es `uri`. */
    blockForMirror(uri: vscode.Uri): MirrorBlock | undefined {
        return this.mirrors.get(uri.toString())?.[0];
    }

    private async ensureClient(): Promise<LanguageClient | undefined> {
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
                const configured = vscode.workspace.getConfiguration('pengus').get<string>('antiquus.clangdPath', 'clangd');
                const serverOptions: ServerOptions = {
                    command: configured && configured.length > 0 ? configured : 'clangd',
                    args: ['--log=error', '--background-index=false']
                };
                const clientOptions: LanguageClientOptions = {
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
                const client = new LanguageClient(
                    'clangd-antiquus',
                    'clangd (antiquus)',
                    serverOptions,
                    clientOptions
                );
                await client.start();
                this.client = client;
                return client;
            } catch {
                return undefined;
            } finally {
                this.starting = undefined;
            }
        })();
        return this.starting;
    }

    private onDiagnostics(uri: vscode.Uri, diagnostics: vscode.Diagnostic[]): void {
        const block = this.blockForMirror(uri);
        if (!block) {
            return;
        }
        const mapped: vscode.Diagnostic[] = [];
        for (const diagnostic of diagnostics) {
            const range = fromMirror(block, diagnostic.range);
            if (!range) {
                continue;
            }
            const item = new vscode.Diagnostic(
                range,
                diagnostic.message,
                diagnostic.severity as vscode.DiagnosticSeverity
            );
            item.source = 'clangd (antiquus)';
            if (diagnostic.code !== undefined) {
                item.code = diagnostic.code as string | number;
            }
            mapped.push(item);
        }
        this.diagnostics.set(block.source, mapped);
    }

    /** Envía una petición a clangd para la posición de un bloque. */
    async request<T>(
        block: MirrorBlock,
        method: string,
        position: vscode.Position,
        extra: Record<string, unknown> = {}
    ): Promise<T | undefined> {
        const client = await this.ensureClient();
        if (!client) {
            return undefined;
        }
        const mirrorPosition = toMirror(block, position);
        try {
            return await client.sendRequest<T>(method, {
                textDocument: { uri: block.mirror.toString() },
                position: { line: mirrorPosition.line, character: mirrorPosition.character },
                ...extra
            });
        } catch {
            return undefined;
        }
    }

    /** Aplica un WorkspaceEdit de clangd traduciendo las posiciones. */
    async applyRename(block: MirrorBlock, newName: string): Promise<boolean> {
        const client = await this.ensureClient();
        if (!client) {
            return false;
        }
        const response = await this.request<{
            changes?: Record<string, { range: vscode.Range; newText: string }[]>;
            documentChanges?: { textDocument: { uri: string }; edits: { range: vscode.Range; newText: string }[] }[];
        }>(block, 'textDocument/rename', new vscode.Position(block.bodyStart, 0), { newName });
        if (!response) {
            return false;
        }
        const edit = new vscode.WorkspaceEdit();
        let any = false;
        const apply = (uri: string, edits: { range: vscode.Range; newText: string }[]) => {
            const target = vscode.Uri.parse(uri);
            const owner = this.blockForMirror(target);
            for (const te of edits) {
                if (owner) {
                    const range = fromMirror(owner, te.range);
                    if (range) {
                        edit.replace(owner.source, range, te.newText);
                        any = true;
                    }
                } else {
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
    mirrorRange(block: MirrorBlock, range: vscode.Range): vscode.Range {
        const offset = block.offset;
        return new vscode.Range(
            range.start.line - block.bodyStart + offset,
            range.start.character,
            range.end.line - block.bodyStart + offset,
            range.end.character
        );
    }
}

function exists(file: string): boolean {
    try {
        fs.accessSync(file, fs.constants.X_OK);
        return true;
    } catch {
        return false;
    }
}

/** Busca un ejecutable en el PATH sin dependencias externas. */
function lookPath(command: string): string | undefined {
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
            } catch {
                /* sigue buscando */
            }
        }
    }
    return undefined;
}

/** Registra los proveedores de C-in-antiquus para el lenguaje `pengus`. */
export function registerAntiquusProviders(context: vscode.ExtensionContext): vscode.Disposable[] {
    const manager = new AntiquusManager(context);
    const selector: vscode.DocumentSelector = { language: 'pengus', scheme: 'file' };
    const disposables: vscode.Disposable[] = [manager];

    disposables.push(
        vscode.languages.registerHoverProvider(selector, {
            async provideHover(document, position) {
                const block = manager.activeBlock(document, position);
                if (!block) {
                    return undefined;
                }
                const hover = await manager.request<vscode.Hover>(
                    block,
                    'textDocument/hover',
                    position
                );
                return hover ?? undefined;
            }
        })
    );

    disposables.push(
        vscode.languages.registerDefinitionProvider(selector, {
            async provideDefinition(document, position) {
                const block = manager.activeBlock(document, position);
                if (!block) {
                    return undefined;
                }
                const result = await manager.request<
                    vscode.Location | vscode.Location[] | vscode.LocationLink[]
                >(block, 'textDocument/definition', position);
                return mapLocations(manager, result);
            }
        })
    );

    disposables.push(
        vscode.languages.registerReferenceProvider(selector, {
            async provideReferences(document, position, ctx) {
                const block = manager.activeBlock(document, position);
                if (!block) {
                    return undefined;
                }
                const result = await manager.request<vscode.Location[]>(block, 'textDocument/references', position, {
                    context: { includeDeclaration: ctx.includeDeclaration }
                });
                return mapLocations(manager, result) as vscode.Location[] | undefined;
            }
        })
    );

    disposables.push(
        vscode.languages.registerRenameProvider(selector, {
            async provideRenameEdits(document, position, newName) {
                const block = manager.activeBlock(document, position);
                if (!block) {
                    return undefined;
                }
                const browser = await manager.request<{
                    changes?: Record<string, { range: vscode.Range; newText: string }[]>;
                    documentChanges?: { textDocument: { uri: string }; edits: { range: vscode.Range; newText: string }[] }[];
                }>(block, 'textDocument/rename', position, { newName });
                if (!browser) {
                    return undefined;
                }
                const out = new vscode.WorkspaceEdit();
                const push = (uri: string, edits: { range: vscode.Range; newText: string }[]) => {
                    const target = vscode.Uri.parse(uri);
                    const owner = manager.blockForMirror(target);
                    for (const te of edits) {
                        if (owner) {
                            const range = fromMirror(owner, te.range);
                            if (range) {
                                out.replace(owner.source, range, te.newText);
                            }
                        } else {
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
        })
    );

    disposables.push(
        vscode.languages.registerCompletionItemProvider(
            selector,
            {
                async provideCompletionItems(document, position) {
                    const block = manager.activeBlock(document, position);
                    if (!block) {
                        return undefined;
                    }
                    const list = await manager.request<
                        vscode.CompletionList | vscode.CompletionItem[]
                    >(block, 'textDocument/completion', position);
                    if (!list) {
                        return undefined;
                    }
                    const items = Array.isArray(list) ? list : list.items ?? [];
                    return items.map((item) => {
                        if (item.range) {
                            const range = fromMirror(block, item.range as vscode.Range);
                            if (range) {
                                item.range = range;
                            }
                        }
                        return item;
                    });
                }
            },
            '.',
            '>',
            '(',
            ','
        )
    );

    disposables.push(
        vscode.languages.registerSignatureHelpProvider(
            selector,
            {
                async provideSignatureHelp(document, position) {
                    const block = manager.activeBlock(document, position);
                    if (!block) {
                        return undefined;
                    }
                    return manager.request<vscode.SignatureHelp>(
                        block,
                        'textDocument/signatureHelp',
                        position
                    );
                }
            },
            '(',
            ','
        )
    );

    disposables.push(
        vscode.languages.registerDocumentHighlightProvider(selector, {
            async provideDocumentHighlights(document, position) {
                const block = manager.activeBlock(document, position);
                if (!block) {
                    return undefined;
                }
                const result = await manager.request<vscode.DocumentHighlight[]>(
                    block,
                    'textDocument/documentHighlight',
                    position
                );
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
                    .filter((item): item is vscode.DocumentHighlight => item !== undefined);
            }
        })
    );

    disposables.push(
        vscode.commands.registerCommand('pengus.antiquus.restart', async () => {
            await manager.dispose();
            vscode.window.showInformationMessage('PenguScript: clangd (antiquus) reiniciado.');
        })
    );

    context.subscriptions.push(...disposables);
    return disposables;
}

function mapLocations(
    manager: AntiquusManager,
    result: vscode.Location | vscode.Location[] | vscode.LocationLink[] | undefined
): vscode.Location[] | undefined {
    if (!result) {
        return undefined;
    }
    const list = Array.isArray(result) ? result : [result];
    const out: vscode.Location[] = [];
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
