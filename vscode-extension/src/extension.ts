import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;
let penguTerminal: vscode.Terminal | undefined;

function getPenguCommand(): string {
    const config = vscode.workspace.getConfiguration('pengus');
    const customPath = config.get<string>('executablePath');
    return customPath ? customPath : (process.platform === 'win32' ? 'pengu.exe' : 'pengu');
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

export function activate(context: vscode.ExtensionContext) {
    const command = getPenguCommand();

    // Configuración del servidor: Ejecuta el binario o script LSP
    const serverOptions: ServerOptions = {
        run: { command: command, args: ['lsp', '--stdio'], transport: TransportKind.stdio },
        debug: { command: command, args: ['lsp', '--stdio'], transport: TransportKind.stdio }
    };

    // Opciones del cliente: Observa los archivos .pengu y .pengus
    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'pengus' }
        ],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.pengu')
        }
    };

    // Crea y arranca el cliente LSP
    client = new LanguageClient(
        'pengusLSP',
        'PenguScript Language Server',
        serverOptions,
        clientOptions
    );

    client.start();

    // Registro de comandos
    const restartCmd = vscode.commands.registerCommand('pengus.restartLsp', () => {
        if (client) {
            client.stop().then(() => client.start());
        }
    });

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
            } else if (selected.label.includes('Restart Language Server')) {
                vscode.commands.executeCommand('pengus.restartLsp');
            }
        }
    });

    context.subscriptions.push(restartCmd, buildCmd, runCmd, testCmd, docCmd, cleanCmd, initCmd, showMenuCmd);
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}