// Ejecución del código generado con `--target js`.
//
// El backend emite ESM puro, así que sirve cualquier motor moderno. Se
// prefiere `bun` (es el runtime del compilador y arranca más rápido) y, si
// no está, `node` (18+ por el top-level await del lanzador).

import { spawnSync } from "node:child_process";
import { statSync } from "node:fs";

export interface JsRuntime {
  readonly command: string;
  readonly label: string;
}

// Busca un ejecutable en `PATH` sin lanzar procesos: es una comprobación de
// arranque y `pengu run` no debe pagar un `spawn` extra.
export function find_on_path(name: string): string | undefined {
  const path = process.env.PATH ?? "";
  const separator = path.includes(";") && !path.includes(":") ? ";" : ":";
  const extensions = process.platform === "win32" ? [".exe", ".cmd", ""] : [""];
  for (const directory of path.split(separator)) {
    if (directory.length === 0) continue;
    for (const extension of extensions) {
      const candidate = `${directory}/${name}${extension}`;
      if (is_executable(candidate)) return candidate;
    }
  }
  return undefined;
}

function is_executable(path: string): boolean {
  try {
    const stat = statSync(path);
    return stat.isFile();
  } catch {
    return false;
  }
}

export function find_js_runtime(): JsRuntime | undefined {
  const bun = find_on_path("bun");
  if (bun !== undefined) return { command: bun, label: "bun" };
  const node = find_on_path("node");
  if (node !== undefined) return { command: node, label: "node" };
  return undefined;
}

export interface JsExecution {
  readonly exit_code: number;
  readonly output: string;
}

export function run_js_entry(entry: string, args: readonly string[]): JsExecution {
  const runtime = find_js_runtime();
  if (runtime === undefined) {
    return {
      exit_code: 1,
      output: "no se encontró un runtime de JavaScript (instala bun o node)",
    };
  }
  const execution = spawnSync(runtime.command, [entry, ...args], { stdio: "inherit" });
  if (execution.error !== undefined) {
    return { exit_code: 1, output: `no se pudo ejecutar ${runtime.label}: ${execution.error.message}` };
  }
  return { exit_code: execution.status ?? 1, output: "" };
}
