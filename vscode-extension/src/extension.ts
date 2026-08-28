import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: vscode.ExtensionContext) {
    // Leer la ruta del ejecutable de PenguScript desde la configuración
    const config = vscode.workspace.getConfiguration('pengus');
    const customPath = config.get<string>('executablePath');
    
    // Si no hay customPath, asume que está en las variables de entorno (PATH)
    const command = customPath ? customPath : (process.platform === 'win32' ? 'pengu.exe' : 'pengu');

    // Configuración del servidor: Ejecuta el binario compilado por PyInstaller
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
            // Notifica al servidor sobre cambios en los archivos de la extensión
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

    // Registro del comando de reinicio
    const restartCmd = vscode.commands.registerCommand('pengus.restartLsp', () => {
        if (client) {
            client.stop().then(() => client.start());
        }
    });

    context.subscriptions.push(restartCmd);
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}