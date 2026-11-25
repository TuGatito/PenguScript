// Pruebas de extremo a extremo: cada ejemplo de `examples/` debe
// compilar a C++20 y ejecutarse sin errores.

import { describe, expect, test } from "bun:test";
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

const examples_root = join(import.meta.dir, "..", "..", "examples");
// Los ejemplos con `native.txt` necesitan bibliotecas nativas (raylib) y se
// validan en `tests/bindgen/native_examples.test.ts`: aquí no se ejecutan.
const directories = readdirSync(examples_root)
  .filter((name) => !name.startsWith("."))
  .filter((name) => !existsSync(join(examples_root, name, "native.txt")))
  .sort();

describe("ejemplos de extremo a extremo", () => {
  for (const directory of directories) {
    test(`${directory} compila y se ejecuta`, () => {
      const source = join(examples_root, directory, "main.pengu");
      const result = compile_file(source);
      const errors = result.diagnostics.filter((diagnostic) => diagnostic.severity === "error");
      expect(errors.map((diagnostic) => diagnostic.message)).toEqual([]);
      expect(result.ok).toBe(true);
      expect(result.binary_path).toBeDefined();

      const execution = spawnSync(result.binary_path as string, [], { encoding: "utf8" });
      expect(execution.status).toBe(0);
      expect((execution.stdout as string).length).toBeGreaterThan(0);
    }, 30_000);
  }
});
