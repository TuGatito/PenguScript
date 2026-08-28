import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as cp from 'child_process';
import * as os from 'os';
import { LanguageClient, LanguageClientOptions, ServerOptions, State } from 'vscode-languageclient/node';

let client: LanguageClient | undefined;
let outputChannel: vscode.OutputChannel;
let statusBarItem: vscode.StatusBarItem;

interface ExecutableInfo {
  command: string;
  args: string[];
}

/**
 * Finds the pengu executable or suitable python fallback for LSP.
 */
function getLspServerOptions(workspaceFolder: string): ServerOptions | undefined {
  const config = vscode.workspace.getConfiguration('pengus');
  const userPath = config.get<string>('executablePath', '').trim();
  const isWindows = process.platform === 'win32';
  const exeName = isWindows ? 'pengu.exe' : 'pengu';

  // 1. User-configured explicit path from settings
  if (userPath) {
    if (fs.existsSync(userPath)) {
      outputChannel.appendLine(`[LSP] Using user-configured executable: ${userPath}`);
      return {
        command: userPath,
        args: ['lsp', '--stdio'],
        options: { cwd: workspaceFolder }
      };
    } else {
      outputChannel.appendLine(`[LSP WARNING] User-configured path does not exist: ${userPath}`);
    }
  }

  // 2. Check system PATH for `pengu` or `pengu.exe`
  try {
    const checkCmd = isWindows ? 'where.exe pengu' : 'which pengu';
    const resolvedPath = cp.execSync(checkCmd, { encoding: 'utf-8' }).split(/\r?\n/)[0].trim();
    if (resolvedPath && fs.existsSync(resolvedPath)) {
      outputChannel.appendLine(`[LSP] Found pengu in system PATH: ${resolvedPath}`);
      return {
        command: resolvedPath,
        args: ['lsp', '--stdio'],
        options: { cwd: workspaceFolder }
      };
    }
  } catch {
    // Not found in system PATH
  }

  // 3. Look in workspace or parent build directories
  const candidates = [
    path.join(workspaceFolder, 'pengucc_build', exeName),
    path.join(workspaceFolder, '..', 'pengucc_build', exeName),
    path.join(workspaceFolder, 'bin', exeName),
    path.join(os.homedir(), '.pengu', 'bin', exeName),
  ];

  for (const cand of candidates) {
    if (fs.existsSync(cand)) {
      outputChannel.appendLine(`[LSP] Found pengu standalone binary: ${cand}`);
      return {
        command: cand,
        args: ['lsp', '--stdio'],
        options: { cwd: workspaceFolder }
      };
    }
  }

  // 4. Fallback to Python virtualenv or system python interpreter
  const venvPython = isWindows
    ? path.join(workspaceFolder, '.venv', 'Scripts', 'python.exe')
    : path.join(workspaceFolder, '.venv', 'bin', 'python');

  let pythonCommand = venvPython;
  if (!fs.existsSync(venvPython)) {
    const altVenv = isWindows
      ? path.join(workspaceFolder, 'venv', 'Scripts', 'python.exe')
      : path.join(workspaceFolder, 'venv', 'bin', 'python');
    if (fs.existsSync(altVenv)) {
      pythonCommand = altVenv;
    } else {
      pythonCommand = isWindows ? 'python' : 'python3';
    }
  }

  outputChannel.appendLine(`[LSP] Falling back to python interpreter: ${pythonCommand}`);
  return {
    command: pythonCommand,
    args: ['-m', 'pengu_lsp', '--stdio'],
    options: {
      cwd: workspaceFolder,
      env: { ...process.env, PYTHONPATH: workspaceFolder }
    }
  };
}

/**
 * Resolves the CLI command to run pengu build/run/clean/init.
 */
function getPenguCli(workspaceFolder: string): ExecutableInfo {
  const config = vscode.workspace.getConfiguration('pengus');
  const userPath = config.get<string>('executablePath', '').trim();
  const isWindows = process.platform === 'win32';
  const exeName = isWindows ? 'pengu.exe' : 'pengu';

  // 1. User specified explicit path
  if (userPath && fs.existsSync(userPath)) {
    return { command: userPath, args: [] };
  }

  // 2. Check system PATH
  try {
    const checkCmd = isWindows ? 'where.exe pengu' : 'which pengu';
    const resolvedPath = cp.execSync(checkCmd, { encoding: 'utf-8' }).split(/\r?\n/)[0].trim();
    if (resolvedPath && fs.existsSync(resolvedPath)) {
      return { command: resolvedPath, args: [] };
    }
  } catch {
    // Not in PATH
  }

  // 3. Workspace candidates
  const candidates = [
    path.join(workspaceFolder, 'pengucc_build', exeName),
    path.join(workspaceFolder, '..', 'pengucc_build', exeName),
    path.join(os.homedir(), '.pengu', 'bin', exeName),
  ];

  for (const cand of candidates) {
    if (fs.existsSync(cand)) {
      return { command: cand, args: [] };
    }
  }

  // 4. Python project script fallback
  const venvPython = isWindows
    ? path.join(workspaceFolder, '.venv', 'Scripts', 'python.exe')
    : path.join(workspaceFolder, '.venv', 'bin', 'python');
  const py = fs.existsSync(venvPython) ? venvPython : (isWindows ? 'python' : 'python3');
  const projectScript = path.join(workspaceFolder, 'pengu_project.py');

  if (fs.existsSync(projectScript)) {
    return { command: py, args: [projectScript] };
  }

  return { command: exeName, args: [] };
}

/**
 * Runs a CLI build/clean/init command in the PenguScript output channel.
 */
function runInOutputChannel(workspaceFolder: string, args: string[]) {
  const cli = getPenguCli(workspaceFolder);
  const fullArgs = [...cli.args, ...args];
  outputChannel.show(true);
  outputChannel.appendLine(`\n[EXEC] ${cli.command} ${fullArgs.join(' ')}`);

  const proc = cp.spawn(cli.command, fullArgs, {
    cwd: workspaceFolder,
    shell: true,
  });

  proc.stdout.on('data', (data: Buffer) => {
    outputChannel.append(data.toString());
  });

  proc.stderr.on('data', (data: Buffer) => {
    outputChannel.append(data.toString());
  });

  proc.on('close', (code: number | null) => {
    if (code === 0) {
      outputChannel.appendLine(`[SUCCESS] Process completed with code 0.`);
      vscode.window.showInformationMessage(`PenguScript: '${args[0]}' succeeded.`);
    } else {
      outputChannel.appendLine(`[ERROR] Process failed with exit code ${code}.`);
      vscode.window.showErrorMessage(`PenguScript: '${args[0]}' failed with code ${code}.`);
    }
  });
}

// Flag to prevent showing "stopped" message on intentional deactivation
let isDeactivating = false;

function handleStateChange(event: { oldState: State; newState: State }) {
  outputChannel.appendLine(`[LSP] State changed: ${State[event.oldState]} -> ${State[event.newState]}`);
  if (event.newState === State.Stopped) {
    if (!isDeactivating) {
      vscode.window.showErrorMessage(
        'PenguScript Language Server stopped unexpectedly. Check the output channel for details.',
        'Restart LSP'
      ).then((selection) => {
        if (selection === 'Restart LSP') {
          vscode.commands.executeCommand('pengus.restartLsp');
        }
      });
    }
  } else if (event.newState === State.Starting) {
    outputChannel.appendLine('[LSP] Server is starting...');
  } else if (event.newState === State.Running) {
    outputChannel.appendLine('[LSP] Server is running.');
  }
}

export function activate(context: vscode.ExtensionContext) {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
  outputChannel = vscode.window.createOutputChannel('PenguScript');
  context.subscriptions.push(outputChannel);

  // 1. Initialize LSP Language Client
  const serverOptions = getLspServerOptions(workspaceFolder);
  if (!serverOptions) {
    vscode.window.showErrorMessage(
      "PenguScript LSP: Could not find 'pengu' binary or Python environment. Please set 'pengus.executablePath' in Settings.",
      'Open Settings'
    ).then((selection) => {
      if (selection === 'Open Settings') {
        vscode.commands.executeCommand('workbench.action.openSettings', 'pengus.executablePath');
      }
    });
    return;
  }

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: 'file', language: 'pengus' }],
    synchronize: {
      fileEvents: vscode.workspace.createFileSystemWatcher('**/*.pengu')
    },
    outputChannel: outputChannel,
    outputChannelName: 'PenguScript LSP'
  };

  client = new LanguageClient('pengus', 'PenguScript LSP', serverOptions, clientOptions);

  // Listen for state changes to notify user of issues
  client.onDidChangeState(handleStateChange);

  // Start the client with error handling
  outputChannel.appendLine(`[LSP] Starting language server...`);
  outputChannel.appendLine(`[LSP] Command: ${JSON.stringify(serverOptions)}`);
  client.start().then(() => {
    outputChannel.appendLine('[LSP] Language server started successfully.');
  }).catch((err: Error) => {
    outputChannel.appendLine(`[LSP ERROR] Failed to start language server: ${err.message}`);
    vscode.window.showErrorMessage(
      `PenguScript LSP failed to start: ${err.message}. Check the 'PenguScript' output channel for details.`
    );
  });

  // 2. Status Bar Item
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  statusBarItem.text = '$(flame) PenguScript';
  statusBarItem.tooltip = 'PenguScript Build & Language Server';
  statusBarItem.command = 'pengus.showMenu';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // 3. Register Commands
  const buildCmd = vscode.commands.registerCommand('pengus.build', () => {
    const config = vscode.workspace.getConfiguration('pengus');
    const profile = config.get<string>('defaultProfile', 'debug');
    runInOutputChannel(workspaceFolder, ['build', '--profile', profile]);
  });

  const runCmd = vscode.commands.registerCommand('pengus.run', () => {
    const config = vscode.workspace.getConfiguration('pengus');
    const profile = config.get<string>('defaultProfile', 'debug');

    const term = vscode.window.terminals.find(t => t.name === 'PenguScript Run') || vscode.window.createTerminal('PenguScript Run');
    const cli = getPenguCli(workspaceFolder);
    const cmdStr = `${cli.command} ${cli.args.join(' ')} run --profile ${profile}`;
    term.show();
    term.sendText(cmdStr);
  });

  const cleanCmd = vscode.commands.registerCommand('pengus.clean', () => {
    runInOutputChannel(workspaceFolder, ['clean']);
  });

  const initCmd = vscode.commands.registerCommand('pengus.init', async () => {
    const name = await vscode.window.showInputBox({
      prompt: 'Enter project name',
      placeHolder: 'my_pengu_app',
      validateInput: (v) => (!v || !/^[a-zA-Z0-9_-]+$/.test(v) ? 'Invalid project name' : null)
    });
    if (!name) return;

    const type = await vscode.window.showQuickPick(['exe', 'static', 'shared'], {
      placeHolder: 'Select project target type'
    }) || 'exe';

    runInOutputChannel(workspaceFolder, ['init', name, '--type', type, '--links', 'pengu_runtime']);
  });

  const restartLspCmd = vscode.commands.registerCommand('pengus.restartLsp', async () => {
    if (client) {
      await client.stop();
      const newServerOpts = getLspServerOptions(workspaceFolder);
      if (newServerOpts) {
        client = new LanguageClient('pengus', 'PenguScript LSP', newServerOpts, clientOptions);
        client.onDidChangeState(handleStateChange);
        client.start().then(() => {
          vscode.window.showInformationMessage('PenguScript Language Server restarted.');
        }).catch((err: Error) => {
          vscode.window.showErrorMessage(`Failed to restart LSP: ${err.message}`);
        });
      }
    }
  });

  const showMenuCmd = vscode.commands.registerCommand('pengus.showMenu', async () => {
    const selected = await vscode.window.showQuickPick([
      { label: '$(play) Run Project', command: 'pengus.run' },
      { label: '$(tools) Build Project', command: 'pengus.build' },
      { label: '$(trash) Clean Project', command: 'pengus.clean' },
      { label: '$(add) Initialize New Project', command: 'pengus.init' },
      { label: '$(refresh) Restart Language Server', command: 'pengus.restartLsp' },
    ]);
    if (selected) {
      vscode.commands.executeCommand(selected.command);
    }
  });

  context.subscriptions.push(buildCmd, runCmd, cleanCmd, initCmd, restartLspCmd, showMenuCmd);
}

export function deactivate(): Thenable<void> | undefined {
  isDeactivating = true;
  if (statusBarItem) {
    statusBarItem.dispose();
  }
  if (!client) {
    return undefined;
  }
  return client.stop();
}