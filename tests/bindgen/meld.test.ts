// F2: uniones C (`meld`). Se escribe el campo activo libremente y se lee
// solo dentro de `unsafe`, porque el tipo del valor depende de la última
// escritura.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { compile_file } from "../../src/driver/compile.ts";
import { build_object, c_compiler } from "./native.ts";

const C_SOURCE = [
  "typedef union { int i; float f; unsigned char bytes[4]; } Bits;",
  "int leer_i(Bits b) { return b.i; }",
  "Bits crear(int i) { Bits b; b.i = i; return b; }",
  "",
].join("\n");

describe("uniones (meld)", () => {
  test("cruza la ABI y la lectura va dentro de unsafe", () => {
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-meld-"));
    try {
      const object = build_object(compiler, dir, "bits", C_SOURCE);
      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          "",
          "meld Bits",
          "  i: int",
          "  f: float",
          "  bytes: array<uint8_t, 4>",
          "",
          'extern "C"',
          "  leer_i = (b: Bits) -> int",
          "  crear = (i: int) -> Bits",
          "",
          "main = -> void",
          "  mut b = Bits()",
          "  b.i = 42",
          "  io::println(leer_i(b))",
          "  c = crear(7)",
          "  unsafe",
          "    io::println(c.i)",
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: [object] });
      expect(result.diagnostics.map((diagnostic) => diagnostic.message)).toEqual([]);
      expect(result.ok).toBe(true);
      const ran = spawnSync(result.binary_path as string, [], { encoding: "utf8" });
      expect(ran.stdout).toBe("42\n7\n");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("leer un campo fuera de unsafe es un error", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu-meld-"));
    try {
      const source = join(dir, "main.pengu");
      writeFileSync(source, "meld Bits\n  i: int\n  f: float\n\nmain = -> int\n  mut b = Bits()\n  b.f = 1.0\n  b.i\n");
      const result = compile_file(source);
      expect(result.ok).toBe(false);
      expect(result.diagnostics.map((diagnostic) => diagnostic.code)).toContain("E0714");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
