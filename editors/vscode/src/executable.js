// Resolución del ejecutable `pengu` y comprobación de que responde.

const { execFile } = require("node:child_process");
const { accessSync, constants, statSync } = require("node:fs");
const { homedir } = require("node:os");
const { delimiter, join } = require("node:path");
const { workspace } = require("vscode");

// VS Code lanzado desde el escritorio no hereda el PATH del shell: los
// gestores de paquetes suelen instalar en estos directorios. Se buscan
// además del PATH del proceso.
const EXTRA_DIRECTORIES = ["~/.local/bin", "~/.bun/bin", "~/bin", "/usr/local/bin", "/opt/homebrew/bin", "/usr/bin"];

// Ruta o nombre configurado en `pengu.executable`.
function executable_setting() {
  return workspace.getConfiguration("pengu").get("executable", "pengu");
}

function expand(path) {
  if (path === "~") return homedir();
  if (path.startsWith("~/")) return join(homedir(), path.slice(2));
  return path;
}

function is_executable_file(path) {
  try {
    if (!statSync(path).isFile()) return false;
    accessSync(path, constants.X_OK);
    return true;
  } catch (_error) {
    return false;
  }
}

// Devuelve la ruta absoluta del ejecutable, o `undefined` si no existe.
// Acepta una ruta configurada o un nombre a buscar en el PATH (ampliado).
function resolve_executable(setting) {
  const expanded = expand(setting);
  if (expanded.includes("/") || expanded.includes("\\")) {
    return is_executable_file(expanded) ? expanded : undefined;
  }
  const names = process.platform === "win32" ? [setting, `${setting}.exe`, `${setting}.cmd`] : [setting];
  const directories = [...(process.env.PATH ?? "").split(delimiter), ...EXTRA_DIRECTORIES.map(expand)];
  for (const directory of directories) {
    if (directory === "") continue;
    for (const name of names) {
      const candidate = join(directory, name);
      if (is_executable_file(candidate)) return candidate;
    }
  }
  return undefined;
}

// Comando a ejecutar: la ruta resuelta si existe, o el valor configurado (para
// que el error del usuario mencione lo que escribió).
function executable_command() {
  const setting = executable_setting();
  return resolve_executable(setting) ?? setting;
}

function search_directories() {
  return [...(process.env.PATH ?? "").split(delimiter).filter((entry) => entry !== ""), ...EXTRA_DIRECTORIES.map(expand)];
}

// Devuelve la versión (`pengu 0.1.0`) o `undefined` si el ejecutable no
// responde. Se usa al activar y antes de arrancar el servidor LSP.
function probe(executable) {
  return new Promise((resolve) => {
    execFile(executable, ["--version"], { timeout: 5000 }, (error, stdout) => {
      if (error !== null) {
        resolve(undefined);
        return;
      }
      resolve(stdout.trim());
    });
  });
}

module.exports = { executable_setting, executable_command, resolve_executable, search_directories, probe };
