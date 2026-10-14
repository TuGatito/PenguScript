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
import { PenguCommand, isFile, resolvePenguCommand } from './penguPath';

let client: LanguageClient | undefined;
let penguTerminal: vscode.Terminal | undefined;
let output: vscode.OutputChannel | undefined;

/** Writes to the extension's own output channel (view: "PenguScript"). */
function log(message: string): void {
    output?.appendLine(`[pengus] ${message}`);
}

/**
 * Feeds the current editor state into the pure search in `penguPath.ts`.
 *
 * `workspaceFolders` is what makes a project-local binary (`.venv/bin/pengu`,
 * `./pengu`) win over nothing at all when `PATH` has no `pengu` — the normal
 * case for a VS Code started from the desktop.
 */
function resolvePengu(): PenguCommand | undefined {
    const configured = vscode.workspace.getConfiguration('pengus').get<string>('executablePath');
    const workspaceFolders = (vscode.workspace.workspaceFolders ?? [])
        .filter((folder) => folder.uri.scheme === 'file')
        .map((folder) => folder.uri.fsPath);
    return resolvePenguCommand({
        configuredPath: configured,
        envPath: process.env.PENGU_BIN_PATH,
        workspaceFolders
    });
}

/** The command the terminal commands should run (falls back to a bare name). */
function getPenguCommand(): string {
    return resolvePengu()?.command ?? (process.platform === 'win32' ? 'pengu.exe' : 'pengu');
}

function getPenguProfile(): string {
    const config = vscode.workspace.getConfiguration('pengus');
    return config.get<string>('defaultProfile') || 'debug';
}

function getTerminal(): vscode.Terminal {
    if (!penguTerminal || penguTerminal.exitStatus !== undefined) {
        penguTerminal = vscode.window.createTerminal('PenguScript');
    }
    return penguTerminal;
}

function runInTerminal(cmd: string) {
    const terminal = getTerminal();
    terminal.show();
    terminal.sendText(cmd);
}

async function reportMissingPengu(configured?: string): Promise<void> {
    const detail = configured
        ? `\`${configured}\` no existe.`
        : 'No se encontró en `pengus.executablePath`, `$PENGU_BIN_PATH`, el `PATH` ni en las ubicaciones habituales.';
    log(`no pengu executable: ${detail}`);
    log(`PATH=${process.env.PATH || ''}`);

    const choice = await vscode.window.showErrorMessage(
        `PenguScript: no se encontró el binario \`pengu\`. ${detail} ` +
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

/** Starts the language client against the resolved executable. */
function startClient(): void {
    const resolved = resolvePengu();
    if (!resolved) {
        void reportMissingPengu();
        return;
    }
    if (!isFile(resolved.command)) {
        void reportMissingPengu(resolved.command);
        return;
    }
    log(`launching "${resolved.command}" lsp --stdio (from ${resolved.source})`);

    // Ejecuta el binario o script LSP.
    const serverOptions: ServerOptions = {
        run: { command: resolved.command, args: ['lsp', '--stdio'], transport: TransportKind.stdio },
        debug: { command: resolved.command, args: ['lsp', '--stdio'], transport: TransportKind.stdio }
    };

    // Observa los fuentes y los manifiestos del proyecto.
    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'pengus' }
        ],
        synchronize: {
            // Sources *and* manifests. The server caches module scopes and
            // symbol tables per project, and drops them on
            // `workspace/didChangeWatchedFiles`; watching only `**/*.pengu`
            // left the editor completing from the previous layout after a
            // `pengu.toml` (or `pengu.yaml`) edit until some source file was
            // reopened.
            fileEvents: [
                vscode.workspace.createFileSystemWatcher('**/*.{pengu,pengus}'),
                vscode.workspace.createFileSystemWatcher(
                    '**/{pengu,Pengu}.{toml,yaml,yml,json,lock}'
                )
            ]
        },
        // Log every protocol error; keep the client library's own retry policy.
        errorHandler: {
            error: (error, message, count) => {
                log(`protocol error (${message?.jsonrpc ?? '?'}, attempt ${count}): ${String(error)}`);
                return { action: ErrorAction.Continue };
            },
            closed: () => {
                log('connection closed');
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

    client.start();
}

//: In-flight restart, so a command and the configuration listener that it
//: triggers cannot both start a client.
let restarting: Promise<void> | undefined;

/** Stops the current client (if any) and starts a fresh one. */
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
        openLabel: 'Usar este pengu',
        title: 'Selecciona el ejecutable `pengu`'
    });
    if (!picked || picked.length === 0) {
        return;
    }
    const chosen = picked[0].fsPath;
    await vscode.workspace
        .getConfiguration('pengus')
        .update('executablePath', chosen, vscode.ConfigurationTarget.Global);
    log(`pengus.executablePath -> ${chosen}`);
    // `update()` fires onDidChangeConfiguration, which restarts the client; the
    // serialised `restartClient` makes doing it here harmless.
    await restartClient();
}

export function activate(context: vscode.ExtensionContext) {
    output = vscode.window.createOutputChannel('PenguScript');
    context.subscriptions.push(output);

    startClient();

    // Registro de comandos
    const restartCmd = vscode.commands.registerCommand('pengus.restartLsp', () => restartClient());

    const selectExecutableCmd = vscode.commands.registerCommand(
        'pengus.selectExecutable',
        () => selectExecutable()
    );

    const buildCmd = vscode.commands.registerCommand('pengus.build', () => {
        const cmd = getPenguCommand();
        const profile = getPenguProfile();
        runInTerminal(`${cmd} build --profile=${profile}`);
    });

    const runCmd = vscode.commands.registerCommand('pengus.run', () => {
        const cmd = getPenguCommand();
        const profile = getPenguProfile();
        runInTerminal(`${cmd} run --profile=${profile}`);
    });

    const testCmd = vscode.commands.registerCommand('pengus.test', () => {
        const cmd = getPenguCommand();
        runInTerminal(`${cmd} test`);
    });

    const docCmd = vscode.commands.registerCommand('pengus.doc', () => {
        const cmd = getPenguCommand();
        runInTerminal(`${cmd} doc`);
    });

    const cleanCmd = vscode.commands.registerCommand('pengus.clean', () => {
        const cmd = getPenguCommand();
        runInTerminal(`${cmd} clean`);
    });

    const initCmd = vscode.commands.registerCommand('pengus.init', async () => {
        const projectName = await vscode.window.showInputBox({
            prompt: 'Enter PenguScript project name',
            placeHolder: 'my_project'
        });
        if (projectName) {
            const cmd = getPenguCommand();
            runInTerminal(`${cmd} init ${projectName}`);
        }
    });

    const showMenuCmd = vscode.commands.registerCommand('pengus.showMenu', async () => {
        const items: vscode.QuickPickItem[] = [
            { label: '$(play) Run Project', description: 'pengu run', detail: 'Build and run the project' },
            { label: '$(tools) Build Project', description: 'pengu build', detail: 'Compile the project to native C / binary' },
            { label: '$(beaker) Run Tests', description: 'pengu test', detail: 'Compile in test mode and execute tests' },
            { label: '$(book) Generate Documentation', description: 'pengu doc', detail: 'Generate Markdown documentation from ## comments' },
            { label: '$(trash) Clean Project', description: 'pengu clean', detail: 'Clean build artifacts' },
            { label: '$(new-folder) Initialize Project', description: 'pengu init', detail: 'Initialize a new project scaffold' },
            { label: '$(file-binary) Select pengu Executable', description: 'pengus.selectExecutable', detail: 'Point the extension at a specific pengu binary' },
            { label: '$(sync) Restart Language Server', description: 'pengus.restartLsp', detail: 'Restart the PenguScript LSP server' }
        ];

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select a PenguScript command'
        });

        if (selected) {
            if (selected.label.includes('Run Project')) {
                vscode.commands.executeCommand('pengus.run');
            } else if (selected.label.includes('Build Project')) {
                vscode.commands.executeCommand('pengus.build');
            } else if (selected.label.includes('Run Tests')) {
                vscode.commands.executeCommand('pengus.test');
            } else if (selected.label.includes('Generate Documentation')) {
                vscode.commands.executeCommand('pengus.doc');
            } else if (selected.label.includes('Clean Project')) {
                vscode.commands.executeCommand('pengus.clean');
            } else if (selected.label.includes('Initialize Project')) {
                vscode.commands.executeCommand('pengus.init');
            } else if (selected.label.includes('Select pengu Executable')) {
                vscode.commands.executeCommand('pengus.selectExecutable');
            } else if (selected.label.includes('Restart Language Server')) {
                vscode.commands.executeCommand('pengus.restartLsp');
            }
        }
    });

    // A path chosen in the settings takes effect immediately.
    const configListener = vscode.workspace.onDidChangeConfiguration(async (event) => {
        if (event.affectsConfiguration('pengus.executablePath')) {
            log('pengus.executablePath changed; restarting the language client');
            await restartClient();
        }
    });

    // A folder added to the workspace can make a project-local binary visible.
    const folderListener = vscode.workspace.onDidChangeWorkspaceFolders(() => {
        if (!client) {
            startClient();
        }
    });

    context.subscriptions.push(
        restartCmd,
        selectExecutableCmd,
        buildCmd,
        runCmd,
        testCmd,
        docCmd,
        cleanCmd,
        initCmd,
        showMenuCmd,
        configListener,
        folderListener
    );
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
