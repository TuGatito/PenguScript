// Terminal dedicada para `run`, `build`, `check`, `fmt`, `bindgen`, `init` y
// `doctor`. La terminal muestra la salida y permite cancelar con Ctrl+C.

const path = require("node:path");
const { existsSync } = require("node:fs");
const { window, workspace } = require("vscode");

let terminal;

// Cita una ruta para la shell de la terminal (comillas simples POSIX y
// comillas dobles en PowerShell/cmd).
function quote(value) {
  if (process.platform === "win32") return `"${value.replace(/"/g, '""')}"`;
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

// Sube desde el archivo hasta encontrar `pengu.toml`; si no hay proyecto,
// usa la carpeta del archivo o la primera carpeta del espacio de trabajo.
function project_cwd(file) {
  if (file !== undefined) {
    let directory = path.dirname(file);
    for (;;) {
      if (existsSync(path.join(directory, "pengu.toml"))) return directory;
      const parent = path.dirname(directory);
      if (parent === directory) break;
      directory = parent;
    }
    const folder = workspace.getWorkspaceFolder(file);
    if (folder !== undefined) return folder.uri.fsPath;
    return path.dirname(file);
  }
  const folders = workspace.workspaceFolders;
  return folders === undefined || folders.length === 0 ? undefined : folders[0].uri.fsPath;
}

function run_in_terminal(command, file) {
  const cwd = project_cwd(file);
  if (terminal === undefined || terminal.exitStatus !== undefined) {
    terminal = window.createTerminal({ name: "PenguScript", cwd });
  }
  terminal.show(true);
  terminal.sendText(command, true);
}

module.exports = { run_in_terminal, quote, project_cwd };
