// Resolución del ejecutable: VS Code puede arrancar sin el PATH del shell,
// así que la extensión busca en el PATH del proceso y en directorios habituales.

import { afterEach, describe, expect, test } from "bun:test";
import { createRequire } from "node:module";
import { chmodSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { mock } from "bun:test";

const require_cjs = createRequire(import.meta.url);

const settings: Record<string, unknown> = { "pengu.executable": "pengu" };

mock.module("vscode", () => ({
  workspace: {
    getConfiguration: () => ({
      get: (key: string, fallback: unknown) => settings[`pengu.${key}`] ?? fallback,
    }),
  },
}));

const { resolve_executable, executable_command } = require_cjs("../../editors/vscode/src/executable.js");

const directories: string[] = [];
const original_path = process.env.PATH;

function make_binary(name: string, mode = 0o755): string {
  const directory = mkdtempSync(join(tmpdir(), "pengu_bin_"));
  directories.push(directory);
  const path = join(directory, name);
  writeFileSync(path, "#!/bin/sh\nexit 0\n");
  chmodSync(path, mode);
  return path;
}

afterEach(() => {
  process.env.PATH = original_path;
  settings["pengu.executable"] = "pengu";
  for (const directory of directories.splice(0)) rmSync(directory, { recursive: true, force: true });
});

describe("resolución del ejecutable", () => {
  test("encuentra el nombre en el PATH del proceso", () => {
    const name = "pengu-prueba-path";
    const binary = make_binary(name);
    process.env.PATH = join(binary, "..");
    expect(resolve_executable(name)).toBe(binary);
  });

  test("acepta una ruta absoluta configurada", () => {
    const binary = make_binary("pengu");
    expect(resolve_executable(binary)).toBe(binary);
  });

  test("ignora archivos sin permiso de ejecución", () => {
    const name = "pengu-prueba-sin-permiso";
    const binary = make_binary(name, 0o644);
    process.env.PATH = join(binary, "..");
    expect(resolve_executable(name)).toBeUndefined();
  });

  test("sin coincidencia devuelve undefined", () => {
    process.env.PATH = "";
    expect(resolve_executable("pengu-inexistente")).toBeUndefined();
  });

  test("executable_command siempre devuelve algo para poder avisar", () => {
    expect(typeof executable_command()).toBe("string");
    expect(executable_command().length).toBeGreaterThan(0);
  });
});
