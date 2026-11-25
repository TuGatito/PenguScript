// G1: un `extern "C"` que devuelve `const char*` se envuelve en el punto de
// llamada (`::pengu::from_c_string`), sin la sobrecarga ilegal de antes.
// Un puntero nulo se convierte en la cadena vacía.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { compile_file } from "../../src/driver/compile.ts";
import { build_object, c_compiler } from "./native.ts";

describe("extern con retorno string", () => {
  test("convierte const char* a string y tolera nullptr", () => {
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-extstr-"));
    try {
      const object = build_object(
        compiler,
        dir,
        "strings",
        [
          "#include <string.h>",
          "static char buffer[64];",
          "const char* saluda(const char* quien) {",
          "  strcpy(buffer, \"hola \");",
          "  strcat(buffer, quien);",
          "  return buffer;",
          "}",
          "const char* nombre_nulo(void) { return 0; }",
          "",
        ].join("\n"),
      );

      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          "",
          'extern "C"',
          "  saluda = (quien: string) -> string",
          "  nombre_nulo = () -> string",
          "",
          "main = -> void",
          '  io::println(saluda("mundo"))',
          '  io::println("nulo:[#{nombre_nulo()}]")',
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: [object] });
      if (!result.ok) throw new Error(result.output);
      expect(result.ok).toBe(true);
      if (result.binary_path === undefined) throw new Error("sin binario");

      const run = spawnSync(result.binary_path, [], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toBe("hola mundo\nnulo:[]\n");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60000);
});
