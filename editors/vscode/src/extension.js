// Activación de la extensión de PenguScript: comprueba el ejecutable, arranca
// el servidor LSP, registra comandos/tareas y mantiene la barra de estado.

const { StatusBarAlignment, commands, window, workspace } = require("vscode");
const { executable_command, executable_setting, probe, resolve_executable, search_directories } = require("./executable");
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
  const output = window.createOutputChannel("PenguScript", { log: true });
  const status = window.createStatusBarItem(StatusBarAlignment.Left, 10);
  const size_item = create_size_item();
  const state = { client: undefined, output, available: false, version: undefined, last_error: undefined };
  let warned = false;

  const on_missing = () => {
    state.available = false;
    show_status(status, state);
    const resolved = resolve_executable(executable_setting());
    const probed = state.version !== undefined;
    if (probed) {
      output.appendLine(`[LSP] el servidor no arrancó: ${state.last_error ?? state.last_message ?? "motivo desconocido"}`);
    } else if (resolved === undefined) {
      output.appendLine(
        `No se encontró «${executable_setting()}». Directorios buscados:\n  ${search_directories().join("\n  ")}`,
      );
    } else {
      output.appendLine(`Se encontró «${resolved}» pero no respondió a «--version».`);
    }
    if (warned) return;
    warned = true;
    const detail = probed
      ? "Mira «Mostrar salida» en el botón de estado para el detalle del error."
      : resolved === undefined
        ? "VS Code no siempre hereda el PATH del shell. Instálalo con scripts/install.sh o indica la ruta en «pengu.executable»."
        : "El archivo no respondió a «--version»: revisa la ruta configurada.";
    const title = probed
      ? "PenguScript: el servidor LSP no arrancó."
      : `No se encontró el ejecutable de PenguScript («${executable_setting()}»).`;
    void window
      .showWarningMessage(`${title} ${detail}`, "Configurar ruta", "Mostrar salida")
      .then((choice) => {
        warned = false;
        if (choice === "Configurar ruta") {
          void commands.executeCommand("workbench.action.openSettings", "pengu.executable");
        }
        if (choice === "Mostrar salida") output.show(true);
      });
  };

  const start = async () => {
    state.version = await probe(executable_command());
    state.available = state.version !== undefined && state.version.startsWith("pengu");
    show_status(status, state);
    if (!state.available) {
      on_missing();
      return;
    }
    output.appendLine(`Ejecutable: ${executable_command()} (${state.version})`);
    await start_client(state, executable_command(), workspace_root(), on_missing);
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
      if (state.available) check_document(document, executable_command());
    }),
    workspace.onDidCloseTextDocument((document) => clear(document.uri)),
  );
  await start();
}

async function deactivate() {
  if (active_state !== undefined) await stop_client(active_state);
}

module.exports = { activate, deactivate };
