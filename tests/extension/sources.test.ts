// Controles estructurales del código de la extensión: sintaxis válida, sin
// clases y con los puntos de activación conectados.

import { describe, expect, test } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const extension_root = new URL("../../editors/vscode/", import.meta.url).pathname;
const source_dir = join(extension_root, "src");
const sources = readdirSync(source_dir).filter((name) => name.endsWith(".js"));

function source_of(name: string): string {
  return readFileSync(join(source_dir, name), "utf8");
}

describe("código de la extensión", () => {
  test("todos los módulos tienen sintaxis válida", () => {
    const failures: string[] = [];
    for (const name of sources) {
      const result = spawnSync("node", ["--check", join(source_dir, name)], { encoding: "utf8" });
      if (result.status !== 0) failures.push(`${name}: ${result.stderr.trim()}`);
    }
    expect(failures).toEqual([]);
  });

  test("no se usan clases (estilo del proyecto)", () => {
    const offenders = sources.filter((name) => /\bclass\s+[A-Za-z_]/.test(source_of(name)));
    expect(offenders).toEqual([]);
  });

  test("cada módulo exporta algo", () => {
    for (const name of sources) expect({ name, exports: /module\.exports\s*=/.test(source_of(name)) }).toEqual({ name, exports: true });
  });

  test("la activación conecta servidor, comandos, tareas y diagnósticos", () => {
    const extension = source_of("extension.js");
    for (const required of ["./lsp", "./commands", "./tasks", "./diagnostics", "createStatusBarItem", "createOutputChannel"]) {
      expect({ required, present: extension.includes(required) }).toEqual({ required, present: true });
    }
    expect(extension).toContain("onDidChangeConfiguration");
    expect(extension).toContain("onDidSaveTextDocument");
    expect(extension).toContain("module.exports = { activate, deactivate }");
  });

  test("el cliente LSP se reinicia y se detiene", () => {
    const lsp = source_of("lsp.js");
    for (const fn of ["start_client", "stop_client", "restart_client", "setTrace"]) {
      expect({ fn, present: lsp.includes(fn) }).toEqual({ fn, present: true });
    }
  });

  test("los comandos delegan en el CLI y usan la terminal", () => {
    const commands = source_of("commands.js");
    expect(commands).toContain("run_in_terminal");
    expect(commands).toContain("editor.action.formatDocument");
    for (const kind of ['"run"', '"build"', '"check"', '"fmt"']) {
      expect({ kind, present: commands.includes(kind) }).toEqual({ kind, present: true });
    }
  });
});
