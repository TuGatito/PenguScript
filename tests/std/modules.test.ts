// Todos los módulos de `std/` deben compilar juntos con g++.
//
// Un `invoke` no ejecuta código, pero el compilador de C++ sí compila cada
// unidad importada: este programa es la red que atrapa colisiones de
// nombres con la biblioteca C (el caso de `std/log`) y cuerpos de
// `enchanting` que emiten C++ inválido.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

const MODULES = [
  "array",
  "assert",
  "double",
  "format",
  "fs",
  "int",
  "io",
  "log",
  "map",
  "math",
  "memory",
  "optional",
  "ordering",
  "os",
  "pair",
  "random",
  "set",
  "string",
  "time",
  "tuple",
  "vector",
];

describe("módulos de la biblioteca estándar", () => {
  test("todos compilan juntos y se ejecutan", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_std_all_"));
    const file = join(dir, "main.pengu");
    const invokes = MODULES.map((name) => `invoke "std/${name}"`).join("\n");
    writeFileSync(file, `${invokes}\n\nmain = ->\n  io::println("todos")\n`);
    const result = compile_file(file);
    expect(result.diagnostics).toEqual([]);
    expect(result.ok).toBe(true);
    const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
    expect(run.status).toBe(0);
    expect(run.stdout).toContain("todos");
  });
});
