"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const os = require("os");
const vscode = require("vscode");
const node_1 = require("vscode-languageclient/node");
const vscode_jsonrpc_1 = require("vscode-jsonrpc");
const pscPath_1 = require("./pscPath");
const antiquus_1 = require("./antiquus");
let client;
let pscTerminal;
let output;
let statusBar;
let watchers = [];
let restarting;
/** Writes to the extension's own output channel (view: "PenguScript"). */
function log(message) {
    output?.appendLine(`[pengus] ${message}`);
}
function config() {
    return vscode.workspace.getConfiguration('pengus');
}
function workspaceRoot() {
    const folder = (vscode.workspace.workspaceFolders ?? []).find((candidate) => candidate.uri.scheme === 'file');
    return folder?.uri.fsPath;
}
/**
 * Resolves the `psc` executable. In an untrusted workspace we deliberately do
 * not execute a project-local binary: a repository must not be able to run
 * arbitrary code merely by being opened.
 */
function resolvePsc() {
    const configured = config().get('executablePath');
    const folders = (vscode.workspace.workspaceFolders ?? [])
        .filter((folder) => folder.uri.scheme === 'file')
        .map((folder) => folder.uri.fsPath);
    const resolved = (0, pscPath_1.resolvePscCommand)({
        configuredPath: configured,
        penguPsc: process.env.PENGU_PSC,
        envPath: process.env.PSC_BIN_PATH ?? process.env.PENGU_BIN_PATH,
        penguHome: process.env.PENGU_HOME,
        envFile: (0, pscPath_1.defaultEnvFile)(os.homedir()),
        // Workspace candidates are only trusted when the user trusts the folder.
        workspaceFolders: vscode.workspace.isTrusted ? folders : []
    });
    if (resolved && configured && resolved.source !== 'pengus.executablePath') {
        log(`pengus.executablePath no es válido (${configured}); usando ${resolved.command} (${resolved.source})`);
    }
    return resolved;
}
function getPscCommand() {
    return resolvePsc()?.command ?? (process.platform === 'win32' ? 'psc.exe' : 'psc');
}
function getPscProfile() {
    return config().get('defaultProfile') || 'debug';
}
function quote(value) {
    if (process.platform === 'win32') {
        return `"${value.replace(/"/g, '\\"')}"`;
    }
    return `'${value.replace(/'/g, `'\\''`)}'`;
}
function getTerminal() {
    if (!pscTerminal || pscTerminal.exitStatus !== undefined) {
        pscTerminal = vscode.window.createTerminal('PenguScript');
    }
    return pscTerminal;
}
function runInTerminal(args) {
    const command = [quote(getPscCommand()), ...args.map(quote)].join(' ');
    log(`run: ${command}`);
    const terminal = getTerminal();
    terminal.show();
    terminal.sendText(command);
}
function runProject(mode) {
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
function uriToPath(uri) {
    if (typeof uri !== 'string') {
        return undefined;
    }
    try {
        const parsed = vscode.Uri.parse(uri);
        return parsed.scheme === 'file' ? parsed.fsPath : undefined;
    }
    catch {
        return undefined;
    }
}
function runFile(uri, mode) {
    const file = uriToPath(uri) ?? vscode.window.activeTextEditor?.document.uri.fsPath;
    if (!file) {
        runProject(mode);
        return;
    }
    if (mode === 'test') {
        runInTerminal(['test', file]);
    }
    else {
        runInTerminal(['run', `--profile=${getPscProfile()}`, file]);
    }
}
function checkFile() {
    const file = vscode.window.activeTextEditor?.document.uri.fsPath;
    if (!file) {
        void vscode.window.showWarningMessage('PenguScript: no active file to check.');
        return;
    }
    runInTerminal(['check', file]);
}
async function reportMissingPsc(configured) {
    const detail = configured
        ? `\`${configured}\` no existe o no es ejecutable.`
        : 'No se encontró en `pengus.executablePath`, `$PENGU_PSC`, `$PSC_BIN_PATH`, `~/.config/pengu/env.json`, `$PENGU_HOME/build/psc`, el `PATH` ni en las ubicaciones habituales.';
    log(`no psc executable: ${detail}`);
    log(`PATH=${process.env.PATH || ''}`);
    const choice = await vscode.window.showErrorMessage(`PenguScript: no se encontró el binario \`psc\`. ${detail} ` +
        'El servidor de lenguaje no puede arrancar.', 'Seleccionar el ejecutable…', 'Abrir ajustes', 'Ver registro');
    if (choice === 'Seleccionar el ejecutable…') {
        await vscode.commands.executeCommand('pengus.selectExecutable');
    }
    else if (choice === 'Abrir ajustes') {
        await vscode.commands.executeCommand('workbench.action.openSettings', 'pengus.executablePath');
    }
    else if (choice === 'Ver registro') {
        output?.show();
    }
}
function disposeWatchers() {
    for (const watcher of watchers) {
        watcher.dispose();
    }
    watchers = [];
}
/** Environment inherited by the LSP, including the persistent build description. */
function lspEnvironment(command) {
    const env = { ...process.env, PENGU_PSC: command };
    const fromFile = (0, pscPath_1.readPenguEnv)((0, pscPath_1.defaultEnvFile)(os.homedir()));
    if (fromFile?.home) {
        env.PENGU_HOME = fromFile.home;
    }
    if (fromFile?.std) {
        env.PENGU_STD_DIR = fromFile.std;
    }
    if (fromFile?.include) {
        env.PENGU_INCLUDE_DIR = fromFile.include;
    }
    if (fromFile?.lib) {
        env.PENGU_LIB_DIR = fromFile.lib;
    }
    if (fromFile?.wasm) {
        env.PENGU_RUNTIME_CROSS = fromFile.wasm;
    }
    if (fromFile?.bind) {
        env.PENGU_BIND = fromFile.bind;
    }
    return env;
}
/** Starts the language client against the resolved executable. */
function startClient() {
    if (client) {
        return;
    }
    const resolved = resolvePsc();
    if (!resolved) {
        void reportMissingPsc();
        return;
    }
    if (!(0, pscPath_1.isExecutable)(resolved.command)) {
        void reportMissingPsc(resolved.command);
        return;
    }
    log(`launching "${resolved.command}" lsp --stdio (from ${resolved.source})`);
    const root = workspaceRoot();
    const serverEnv = lspEnvironment(resolved.command);
    const serverOptions = {
        run: {
            command: resolved.command,
            args: ['lsp', '--stdio'],
            transport: node_1.TransportKind.stdio,
            options: { cwd: root, env: serverEnv }
        },
        debug: {
            command: resolved.command,
            args: ['lsp', '--stdio'],
            transport: node_1.TransportKind.stdio,
            options: { cwd: root, env: serverEnv }
        }
    };
    disposeWatchers();
    watchers.push(vscode.workspace.createFileSystemWatcher('**/*.{pengu,pengus}'), vscode.workspace.createFileSystemWatcher('**/{pengu,Pengu}.{toml,lock}'));
    const clientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'pengus' },
            { scheme: 'file', pattern: '**/*.d.pengu' }
        ],
        outputChannel: output,
        traceOutputChannel: output,
        workspaceFolder: root ? (vscode.workspace.workspaceFolders ?? []).find((folder) => folder.uri.fsPath === root) : undefined,
        initializationOptions: {
            stdDir: config().get('stdDir') || process.env.PENGU_STD_DIR || '',
            executablePath: resolved.command,
            inlayHints: config().get('inlayHints.enabled', true),
            inlayHintOptions: {
                sizes: config().get('inlayHints.sizes', true),
                types: config().get('inlayHints.types', true)
            },
            semanticHighlighting: config().get('semanticHighlighting.enabled', true)
        },
        synchronize: { fileEvents: watchers },
        errorHandler: {
            error: (error, message, count) => {
                log(`protocol error (${message?.jsonrpc ?? '?'}, attempt ${count}): ${String(error)}`);
                return { action: node_1.ErrorAction.Continue };
            },
            closed: () => {
                log('connection closed; restarting');
                return { action: node_1.CloseAction.Restart };
            }
        }
    };
    client = new node_1.LanguageClient('pengusLSP', 'PenguScript Language Server', serverOptions, clientOptions);
    const trace = config().get('trace.server') || 'off';
    if (client) {
        client.setTrace(trace === 'verbose' ? vscode_jsonrpc_1.Trace.Verbose : trace === 'messages' ? vscode_jsonrpc_1.Trace.Messages : vscode_jsonrpc_1.Trace.Off);
    }
    client.start().catch(async (error) => {
        log(`language client failed to start: ${String(error)}`);
        client = undefined;
        await vscode.window.showErrorMessage(`PenguScript: el servidor de lenguaje no arrancó. ${String(error)}`);
    });
}
async function restartClient() {
    if (restarting) {
        return restarting;
    }
    restarting = (async () => {
        if (client) {
            const previous = client;
            client = undefined;
            try {
                await previous.stop();
            }
            catch (error) {
                log(`stopping the previous client failed: ${String(error)}`);
            }
        }
        disposeWatchers();
        startClient();
    })();
    try {
        await restarting;
    }
    finally {
        restarting = undefined;
    }
}
async function selectExecutable() {
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
function updateStatusBar() {
    if (!statusBar) {
        return;
    }
    const enabled = config().get('statusBar.enabled', true);
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
async function showMenu() {
    const entries = [
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
function registerCommands(context) {
    const commands = [
        vscode.commands.registerCommand('pengus.restartLsp', () => restartClient()),
        vscode.commands.registerCommand('pengus.selectExecutable', () => selectExecutable()),
        vscode.commands.registerCommand('pengus.build', () => runProject('build')),
        vscode.commands.registerCommand('pengus.run', (...args) => {
            if (args.length > 0) {
                runFile(args[0], 'run');
            }
            else {
                runProject('run');
            }
        }),
        vscode.commands.registerCommand('pengus.test', (...args) => {
            if (args.length > 0) {
                runFile(args[0], 'test');
            }
            else {
                runProject('test');
            }
        }),
        vscode.commands.registerCommand('pengus.runFile', (uri) => runFile(uri, 'run')),
        vscode.commands.registerCommand('pengus.testFile', (uri) => runFile(uri, 'test')),
        vscode.commands.registerCommand('pengus.check', () => checkFile()),
        vscode.commands.registerCommand('pengus.doc', () => runProject('doc')),
        vscode.commands.registerCommand('pengus.clean', () => runProject('clean')),
        vscode.commands.registerCommand('pengus.format', () => vscode.commands.executeCommand('editor.action.formatDocument')),
        vscode.commands.registerCommand('pengus.openOutput', () => output?.show()),
        vscode.commands.registerCommand('pengus.showMenu', () => showMenu()),
        vscode.commands.registerCommand('pengus.init', async () => {
            const name = await vscode.window.showInputBox({
                prompt: 'PenguScript project name',
                placeHolder: 'my_project',
                validateInput: (value) => /^[A-Za-z_][A-Za-z0-9_-]*$/.test(value)
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
function registerConfigListener(context) {
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration(async (event) => {
        if (event.affectsConfiguration('pengus.executablePath')) {
            log('pengus.executablePath changed; restarting the language client');
            await restartClient();
        }
        if (event.affectsConfiguration('pengus.defaultProfile') ||
            event.affectsConfiguration('pengus.statusBar.enabled')) {
            updateStatusBar();
        }
        if (event.affectsConfiguration('pengus.inlayHints.enabled') ||
            event.affectsConfiguration('pengus.inlayHints.sizes') ||
            event.affectsConfiguration('pengus.inlayHints.types') ||
            event.affectsConfiguration('pengus.semanticHighlighting.enabled') ||
            event.affectsConfiguration('pengus.stdDir') ||
            event.affectsConfiguration('pengus.trace.server')) {
            await restartClient();
        }
    }), vscode.workspace.onDidChangeWorkspaceFolders(() => {
        updateStatusBar();
        if (!client) {
            startClient();
        }
    }));
}
function registerDebugger(context) {
    const factory = {
        createDebugAdapterDescriptor() {
            return new vscode.DebugAdapterExecutable(getPscCommand(), ['debug-adapter'], { cwd: workspaceRoot() });
        }
    };
    context.subscriptions.push(vscode.debug.registerDebugAdapterDescriptorFactory('pengu', factory));
}
function activate(context) {
    output = vscode.window.createOutputChannel('PenguScript');
    context.subscriptions.push(output);
    statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.command = 'pengus.showMenu';
    context.subscriptions.push(statusBar);
    registerCommands(context);
    registerConfigListener(context);
    registerDebugger(context);
    (0, antiquus_1.registerAntiquusProviders)(context);
    updateStatusBar();
    startClient();
}
function deactivate() {
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
//# sourceMappingURL=extension.js.map