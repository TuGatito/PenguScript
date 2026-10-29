import * as vscode from 'vscode';
import {
    CloseAction,
    ErrorAction,
    ErrorHandler,
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';
import { Trace } from 'vscode-jsonrpc';
import { PscCommand, isExecutable, resolvePscCommand } from './pscPath';

let client: LanguageClient | undefined;
let pscTerminal: vscode.Terminal | undefined;
let output: vscode.OutputChannel | undefined;
let statusBar: vscode.StatusBarItem | undefined;
let watchers: vscode.FileSystemWatcher[] = [];
let restarting: Promise<void> | undefined;

/** Writes to the extension's own output channel (view: "PenguScript"). */
function log(message: string): void {
    output?.appendLine(`[pengus] ${message}`);
}

function config() {
    return vscode.workspace.getConfiguration('pengus');
}

function workspaceRoot(): string | undefined {
    const folder = (vscode.workspace.workspaceFolders ?? []).find(
        (candidate) => candidate.uri.scheme === 'file'
    );
    return folder?.uri.fsPath;
}

/**
 * Resolves the `psc` executable. In an untrusted workspace we deliberately do
 * not execute a project-local binary: a repository must not be able to run
 * arbitrary code merely by being opened.
 */
function resolvePsc(): PscCommand | undefined {
    const configured = config().get<string>('executablePath');
    const folders = (vscode.workspace.workspaceFolders ?? [])
        .filter((folder) => folder.uri.scheme === 'file')
        .map((folder) => folder.uri.fsPath);
    return resolvePscCommand({
        configuredPath: configured,
        envPath: process.env.PSC_BIN_PATH ?? process.env.PENGU_BIN_PATH,
        // Workspace candidates are only trusted when the user trusts the folder.
        workspaceFolders: vscode.workspace.isTrusted ? folders : []
    });
}

function getPscCommand(): string {
    return resolvePsc()?.command ?? (process.platform === 'win32' ? 'psc.exe' : 'psc');
}

function getPscProfile(): string {
    return config().get<string>('defaultProfile') || 'debug';
}

function quote(value: string): string {
    if (process.platform === 'win32') {
        return `"${value.replace(/"/g, '\\"')}"`;
    }
    return `'${value.replace(/'/g, `'\\''`)}'`;
}

function getTerminal(): vscode.Terminal {
    if (!pscTerminal || pscTerminal.exitStatus !== undefined) {
        pscTerminal = vscode.window.createTerminal('PenguScript');
    }
    return pscTerminal;
}

function runInTerminal(args: string[]): void {
    const command = [quote(getPscCommand()), ...args.map(quote)].join(' ');
    log(`run: ${command}`);
    const terminal = getTerminal();
    terminal.show();
    terminal.sendText(command);
}

function runProject(mode: 'run' | 'build' | 'test' | 'doc' | 'clean'): void {
    const profile = getPscProfile();
    switch (mode) {
        case 'run':
            runInTerminal(['run', `--profile=${profile}`]);
            break;
        case 'build':
            runInTerminal(['build', `--profile=${profile}`]);
            break;
        case 'test':
            runInTerminal(['test']);
            break;
        case 'doc':
            runInTerminal(['doc']);
            break;
        case 'clean':
            runInTerminal(['clean']);
            break;
    }
}

function uriToPath(uri: unknown): string | undefined {
    if (typeof uri !== 'string') {
        return undefined;
    }
    try {
        const parsed = vscode.Uri.parse(uri);
        return parsed.scheme === 'file' ? parsed.fsPath : undefined;
    } catch {
        return undefined;
    }
}

function runFile(uri: unknown, mode: 'run' | 'test'): void {
    const file = uriToPath(uri) ?? vscode.window.activeTextEditor?.document.uri.fsPath;
    if (!file) {
        runProject(mode);
        return;
    }
    if (mode === 'test') {
        runInTerminal(['test', file]);
    } else {
        runInTerminal(['run', `--profile=${getPscProfile()}`, file]);
    }
}

function checkFile(): void {
    const file = vscode.window.activeTextEditor?.document.uri.fsPath;
    if (!file) {
        void vscode.window.showWarningMessage('PenguScript: no active file to check.');
        return;
    }
    runInTerminal(['check', file]);
}

async function reportMissingPsc(configured?: string): Promise<void> {
    const detail = configured
        ? `\`${configured}\` no existe o no es ejecutable.`
        : 'No se encontró en `pengus.executablePath`, `$PSC_BIN_PATH`, el `PATH` ni en las ubicaciones habituales.';
    log(`no psc executable: ${detail}`);
    log(`PATH=${process.env.PATH || ''}`);
    const choice = await vscode.window.showErrorMessage(
        `PenguScript: no se encontró el binario \`psc\`. ${detail} ` +
        'El servidor de lenguaje no puede arrancar.',
        'Seleccionar el ejecutable…',
        'Abrir ajustes',
        'Ver registro'
    );
    if (choice === 'Seleccionar el ejecutable…') {
        await vscode.commands.executeCommand('pengus.selectExecutable');
    } else if (choice === 'Abrir ajustes') {
        await vscode.commands.executeCommand('workbench.action.openSettings', 'pengus.executablePath');
    } else if (choice === 'Ver registro') {
        output?.show();
    }
}

function disposeWatchers(): void {
    for (const watcher of watchers) {
        watcher.dispose();
    }
    watchers = [];
}

/** Starts the language client against the resolved executable. */
function startClient(): void {
    if (client) {
        return;
    }
    const resolved = resolvePsc();
    if (!resolved) {
        void reportMissingPsc();
        return;
    }
    if (!isExecutable(resolved.command)) {
        void reportMissingPsc(resolved.command);
        return;
    }
    log(`launching "${resolved.command}" lsp --stdio (from ${resolved.source})`);
    const root = workspaceRoot();
    const serverOptions: ServerOptions = {
        run: {
            command: resolved.command,
            args: ['lsp', '--stdio'],
            transport: TransportKind.stdio,
            options: root ? { cwd: root } : undefined
        },
        debug: {
            command: resolved.command,
            args: ['lsp', '--stdio'],
            transport: TransportKind.stdio,
            options: root ? { cwd: root } : undefined
        }
    };

    disposeWatchers();
    watchers.push(
        vscode.workspace.createFileSystemWatcher('**/*.{pengu,pengus}'),
        vscode.workspace.createFileSystemWatcher('**/{pengu,Pengu}.{toml,lock}')
    );

    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'pengus' }],
        outputChannel: output,
        traceOutputChannel: output,
        workspaceFolder: root ? (vscode.workspace.workspaceFolders ?? []).find(
            (folder) => folder.uri.fsPath === root
        ) : undefined,
        initializationOptions: {
            stdDir: config().get<string>('stdDir') || '',
            executablePath: resolved.command,
            inlayHints: config().get<boolean>('inlayHints.enabled', true),
            semanticHighlighting: config().get<boolean>('semanticHighlighting.enabled', true)
        },
        synchronize: { fileEvents: watchers },
        errorHandler: {
            error: (error, message, count) => {
                log(`protocol error (${message?.jsonrpc ?? '?'}, attempt ${count}): ${String(error)}`);
                return { action: ErrorAction.Continue };
            },
            closed: () => {
                log('connection closed; restarting');
                return { action: CloseAction.Restart };
            }
        } as ErrorHandler
    };

    client = new LanguageClient(
        'pengusLSP',
        'PenguScript Language Server',
        serverOptions,
        clientOptions
    );
    const trace = config().get<string>('trace.server') || 'off';
    if (client) {
        client.setTrace(trace === 'verbose' ? Trace.Verbose : trace === 'messages' ? Trace.Messages : Trace.Off);
    }
    client.start().catch(async (error) => {
        log(`language client failed to start: ${String(error)}`);
        client = undefined;
        await vscode.window.showErrorMessage(
            `PenguScript: el servidor de lenguaje no arrancó. ${String(error)}`
        );
    });
}

async function restartClient(): Promise<void> {
    if (restarting) {
        return restarting;
    }
    restarting = (async () => {
        if (client) {
            const previous = client;
            client = undefined;
            try {
                await previous.stop();
            } catch (error) {
                log(`stopping the previous client failed: ${String(error)}`);
            }
        }
        disposeWatchers();
        startClient();
    })();
    try {
        await restarting;
    } finally {
        restarting = undefined;
    }
}

async function selectExecutable(): Promise<void> {
    const picked = await vscode.window.showOpenDialog({
        canSelectMany: false,
        openLabel: 'Usar este psc',
        title: 'Selecciona el ejecutable `psc`'
    });
    if (!picked || picked.length === 0) {
        return;
    }
    const chosen = picked[0].fsPath;
    await config().update('executablePath', chosen, vscode.ConfigurationTarget.Global);
    log(`pengus.executablePath -> ${chosen}`);
    await restartClient();
}

function updateStatusBar(): void {
    if (!statusBar) {
        return;
    }
    const enabled = config().get<boolean>('statusBar.enabled', true);
    if (!enabled) {
        statusBar.hide();
        return;
    }
    const profile = getPscProfile();
    const root = workspaceRoot();
    const project = root ? root.split(/[\\/]/).pop() : 'sin proyecto';
    statusBar.text = `$(play) PenguScript (${profile})`;
    statusBar.tooltip = `Proyecto: ${project}\nPerfil: ${profile}\nClic para abrir el menú`;
    statusBar.show();
}

type MenuEntry = vscode.QuickPickItem & { command: string; args?: unknown[] };

async function showMenu(): Promise<void> {
    const entries: MenuEntry[] = [
        { label: '$(play) Run Project', description: 'psc run', detail: 'Build and run the project', command: 'pengus.run' },
        { label: '$(beaker) Run Tests', description: 'psc test', detail: 'Compile in test mode and execute tests', command: 'pengus.test' },
        { label: '$(tools) Build Project', description: 'psc build', detail: 'Compile the project to native C / binary', command: 'pengus.build' },
        { label: '$(check) Check File', description: 'psc check', detail: 'Type-check the active file', command: 'pengus.check' },
        { label: '$(book) Generate Documentation', description: 'psc doc', detail: 'Generate Markdown from # and ## comments', command: 'pengus.doc' },
        { label: '$(trash) Clean Project', description: 'psc clean', detail: 'Clean build artifacts', command: 'pengus.clean' },
        { label: '$(new-folder) Initialize Project', description: 'psc init', detail: 'Initialize a new project scaffold', command: 'pengus.init' },
        { label: '$(file-binary) Select psc Executable', description: 'pengus.selectExecutable', detail: 'Point the extension at a specific psc binary', command: 'pengus.selectExecutable' },
        { label: '$(sync) Restart Language Server', description: 'pengus.restartLsp', detail: 'Restart the PenguScript LSP server', command: 'pengus.restartLsp' },
        { label: '$(output) Show Output', description: 'pengus.openOutput', detail: 'Show the PenguScript/LSP log', command: 'pengus.openOutput' }
    ];
    const selected = await vscode.window.showQuickPick(entries, {
        placeHolder: 'Select a PenguScript command'
    });
    if (selected) {
        await vscode.commands.executeCommand(selected.command, ...(selected.args ?? []));
    }
}

function registerCommands(context: vscode.ExtensionContext): void {
    const commands: vscode.Disposable[] = [
        vscode.commands.registerCommand('pengus.restartLsp', () => restartClient()),
        vscode.commands.registerCommand('pengus.selectExecutable', () => selectExecutable()),
        vscode.commands.registerCommand('pengus.build', () => runProject('build')),
        vscode.commands.registerCommand('pengus.run', (...args: unknown[]) => {
            if (args.length > 0) {
                runFile(args[0], 'run');
            } else {
                runProject('run');
            }
        }),
        vscode.commands.registerCommand('pengus.test', (...args: unknown[]) => {
            if (args.length > 0) {
                runFile(args[0], 'test');
            } else {
                runProject('test');
            }
        }),
        vscode.commands.registerCommand('pengus.runFile', (uri: unknown) => runFile(uri, 'run')),
        vscode.commands.registerCommand('pengus.testFile', (uri: unknown) => runFile(uri, 'test')),
        vscode.commands.registerCommand('pengus.check', () => checkFile()),
        vscode.commands.registerCommand('pengus.doc', () => runProject('doc')),
        vscode.commands.registerCommand('pengus.clean', () => runProject('clean')),
        vscode.commands.registerCommand('pengus.format', () =>
            vscode.commands.executeCommand('editor.action.formatDocument')
        ),
        vscode.commands.registerCommand('pengus.openOutput', () => output?.show()),
        vscode.commands.registerCommand('pengus.showMenu', () => showMenu()),
        vscode.commands.registerCommand('pengus.init', async () => {
            const name = await vscode.window.showInputBox({
                prompt: 'PenguScript project name',
                placeHolder: 'my_project',
                validateInput: (value) =>
                    /^[A-Za-z_][A-Za-z0-9_-]*$/.test(value)
                        ? undefined
                        : 'Use letters, digits, _ or -; start with a letter or _.'
            });
            if (name) {
                runInTerminal(['init', name]);
            }
        })
    ];
    context.subscriptions.push(...commands);
}

function registerConfigListener(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration(async (event) => {
            if (event.affectsConfiguration('pengus.executablePath')) {
                log('pengus.executablePath changed; restarting the language client');
                await restartClient();
            }
            if (
                event.affectsConfiguration('pengus.defaultProfile') ||
                event.affectsConfiguration('pengus.statusBar.enabled')
            ) {
                updateStatusBar();
            }
            if (
                event.affectsConfiguration('pengus.inlayHints.enabled') ||
                event.affectsConfiguration('pengus.semanticHighlighting.enabled') ||
                event.affectsConfiguration('pengus.stdDir') ||
                event.affectsConfiguration('pengus.trace.server')
            ) {
                await restartClient();
            }
        }),
        vscode.workspace.onDidChangeWorkspaceFolders(() => {
            updateStatusBar();
            if (!client) {
                startClient();
            }
        })
    );
}

export function activate(context: vscode.ExtensionContext): void {
    output = vscode.window.createOutputChannel('PenguScript');
    context.subscriptions.push(output);
    statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.command = 'pengus.showMenu';
    context.subscriptions.push(statusBar);

    registerCommands(context);
    registerConfigListener(context);
    updateStatusBar();
    startClient();
}

export function deactivate(): Thenable<void> | undefined {
    disposeWatchers();
    statusBar?.dispose();
    pscTerminal?.dispose();
    if (!client) {
        return undefined;
    }
    const current = client;
    client = undefined;
    return current.stop();
}
