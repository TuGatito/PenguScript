// Resolución del ejecutable `pengu` y comprobación de que responde.

const { execFile } = require("node:child_process");
const { workspace } = require("vscode");

// Ruta o nombre configurado en `pengu.executable`.
function executable_setting() {
  return workspace.getConfiguration("pengu").get("executable", "pengu");
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

module.exports = { executable_setting, probe };
