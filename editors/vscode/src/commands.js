// Comandos de la paleta y de los menús. Ejecutan el CLI en una terminal para
// que la salida sea visible y cancelable.

const path = require("node:path");
const { commands, Uri, window, workspace } = require("vscode");
const { executable_command } = require("./executable");
const { run_in_terminal, project_cwd, quote } = require("./terminal");
const { extra_args } = require("./settings");

function active_pengu_file() {
  const editor = window.activeTextEditor;
  if (editor === undefined || editor.document.languageId !== "pengu") return undefined;
  return editor.document.uri.fsPath;
}

function requested_file(argument) {
  if (argument instanceof Uri) return argument.fsPath;
  return active_pengu_file();
}

function require_file(argument) {
  const file = requested_file(argument);
  if (file === undefined) {
    window.showWarningMessage("Abre un archivo .pengu para usar este comando.");
    return undefined;
  }
  return file;
}

function command_line(kind, file, key) {
  const parts = [quote(executable_command()), kind, ...extra_args(key).map(quote)];
  if (file !== undefined) parts.push(quote(file));
  return parts.join(" ");
}

function terminal_kind(kind, argument, key) {
  const file = require_file(argument);
  if (file === undefined) return;
  run_in_terminal(command_line(kind, file, key), file);
}

function workspace_cwd() {
  const folders = workspace.workspaceFolders;
  return folders === undefined || folders.length === 0 ? undefined : folders[0].uri.fsPath;
}

async function bindgen_prompt() {
  const cwd = workspace_cwd();
  const header = await window.showInputBox({
    prompt: "Ruta del encabezado de C (relativa al proyecto)",
    value: "include/demo.h",
  });
  if (header === undefined || header.trim().length === 0) return;
  const base = path.basename(header).replace(/\.[^.]+$/, "");
  const realm = await window.showInputBox({ prompt: "Realm para los enlaces", value: base });
  if (realm === undefined || realm.trim().length === 0) return;
  const full_header = cwd === undefined ? header : path.resolve(cwd, header);
  const out = cwd === undefined ? `${base}.d.pengu` : path.resolve(cwd, path.dirname(header), `${base}.d.pengu`);
  const line = `${quote(executable_command())} bindgen ${quote(full_header)} --realm ${realm.trim()} --out ${quote(out)}`;
  run_in_terminal(line, full_header);
}

function register_commands(context, state) {
  const register = (id, handler) => context.subscriptions.push(commands.registerCommand(id, handler));

  register("pengu.runFile", (argument) => terminal_kind("run", argument, "run.args"));
  register("pengu.buildFile", (argument) => terminal_kind("build", argument, "build.args"));
  register("pengu.checkFile", (argument) => terminal_kind("check", argument, "build.args"));
  register("pengu.runProject", () => {
    const cwd = workspace_cwd();
    run_in_terminal(command_line("run", undefined, "run.args"), cwd);
  });
  register("pengu.fmtFile", async () => {
    const file = active_pengu_file();
    if (file !== undefined) {
      await commands.executeCommand("editor.action.formatDocument");
      return;
    }
    run_in_terminal(command_line("fmt", undefined, "build.args"), project_cwd(undefined));
  });
  register("pengu.bindgen", () => bindgen_prompt());
  register("pengu.init", () => run_in_terminal(`${quote(executable_command())} init`, workspace_cwd()));
  register("pengu.doctor", () => run_in_terminal(`${quote(executable_command())} doctor`, workspace_cwd()));
  register("pengu.restartServer", () => state.restart());
  register("pengu.showOutput", () => state.output.show(true));
  register("pengu.showSize", () => show_size(state));
  register("pengu.configureExecutable", () => commands.executeCommand("workbench.action.openSettings", "pengu.executable"));
}

// Muestra el tamaño medido del símbolo bajo el cursor.
async function show_size(state) {
  const editor = window.activeTextEditor;
  if (editor === undefined || editor.document.languageId !== "pengu") {
    void window.showInformationMessage("Abre un archivo .pengu y coloca el cursor sobre un símbolo.");
    return;
  }
  const { size_at, format_size } = require("./sizes");
  const info = await size_at(state, editor.document, editor.selection.active);
  const text = format_size(info);
  void window.showInformationMessage(text === undefined ? "No hay un tamaño medido para ese símbolo." : text);
}

module.exports = { register_commands };
