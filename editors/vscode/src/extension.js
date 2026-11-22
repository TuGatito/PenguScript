// Activación de la extensión de PenguScript: comprueba el ejecutable, arranca
// el servidor LSP, registra comandos/tareas y mantiene la barra de estado.

const { StatusBarAlignment, commands, window, workspace } = require("vscode");
const { executable_setting, probe } = require("./executable");
const { start_client, stop_client } = require("./lsp");
const { register_commands } = require("./commands");
const { register: register_tasks } = require("./tasks");
const { check_document, clear } = require("./diagnostics");
const { project_cwd } = require("./terminal");
const { size_at, format_size, create_size_item } = require("./sizes");
const { status_size } = require("./settings");

let active_state;

function workspace_root() {
  const folders = workspace.workspaceFolders;
  if (folders === undefined || folders.length === 0) return undefined;
  const found = project_cwd(undefined);
  return found === undefined ? folders[0].uri.fsPath : found;
}

function show_status(status, state) {
  if (state.available) {
    status.text = `$(check) ${state.version ?? "PenguScript"}`;
    status.tooltip = "PenguScript: servidor LSP activo. Clic para ver la salida.";
    status.command = "pengu.showOutput";
  } else {
    status.text = "$(warning) PenguScript: pengu no encontrado";
    status.tooltip = "Configura «pengu.executable» con la ruta del ejecutable.";
    status.command = "pengu.configureExecutable";
  }
  status.show();
}

async function activate(context) {
  const output = window.createOutputChannel("PenguScript");
  const status = window.createStatusBarItem(StatusBarAlignment.Left, 10);
  const size_item = create_size_item();
  const state = { client: undefined, output, available: false, version: undefined };
  let warned = false;

  const on_missing = () => {
    state.available = false;
    show_status(status, state);
    if (warned) return;
    warned = true;
    void window
      .showWarningMessage("No se encontró el ejecutable de PenguScript («pengu»).", "Configurar ruta")
      .then((choice) => {
        warned = false;
        if (choice === "Configurar ruta") {
          void commands.executeCommand("workbench.action.openSettings", "pengu.executable");
        }
      });
  };

  const start = async () => {
    state.version = await probe(executable_setting());
    state.available = state.version !== undefined && state.version.startsWith("pengu");
    show_status(status, state);
    if (!state.available) {
      on_missing();
      return;
    }
    output.appendLine(`Ejecutable: ${executable_setting()} (${state.version})`);
    await start_client(state, executable_setting(), workspace_root(), on_missing);
  };

  state.restart = async () => {
    await stop_client(state);
    await start();
  };

  const refresh_size = () => {
    if (!status_size()) {
      size_item.hide();
      return;
    }
    const editor = window.activeTextEditor;
    if (editor === undefined || editor.document.languageId !== "pengu") {
      size_item.hide();
      return;
    }
    void size_at(state, editor.document, editor.selection.active).then((info) => {
      const text = format_size(info);
      if (text === undefined) {
        size_item.hide();
        return;
      }
      size_item.text = `$(symbol-ruler) ${text}`;
      size_item.tooltip = "Tamaño medido del símbolo bajo el cursor";
      size_item.show();
    });
  };

  active_state = state;
  register_commands(context, state);
  context.subscriptions.push(status, output, size_item, register_tasks());
  context.subscriptions.push(
    window.onDidChangeTextEditorSelection(() => refresh_size()),
    window.onDidChangeActiveTextEditor(() => refresh_size()),
  );
  context.subscriptions.push(
    workspace.onDidChangeConfiguration((event) => {
      const restarts = ["pengu.executable", "pengu.lsp.trace.server", "pengu.inlayHints.sizes", "pengu.completion.docs"];
      if (restarts.some((key) => event.affectsConfiguration(key))) void state.restart();
    }),
    workspace.onDidSaveTextDocument((document) => {
      if (state.available) check_document(document, executable_setting());
    }),
    workspace.onDidCloseTextDocument((document) => clear(document.uri)),
  );
  await start();
}

async function deactivate() {
  if (active_state !== undefined) await stop_client(active_state);
}

module.exports = { activate, deactivate };
