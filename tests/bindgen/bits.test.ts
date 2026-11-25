// F2: campos con ancho en bits (`bits`). El C++ emitido es un bitfield y
// `pengu size --fields` informa del ancho en vez de un desplazamiento.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { compile_file } from "../../src/driver/compile.ts";
import { run_size } from "../../src/cli/size_command.ts";
import { build_object, c_compiler } from "./native.ts";

const C_SOURCE = [
  "typedef struct { unsigned int modo: 3; unsigned int nivel: 5; } Flags;",
  "Flags crear(unsigned int modo, unsigned int nivel) { Flags f; f.modo = modo; f.nivel = nivel; return f; }",
  "unsigned int leer(Flags f) { return f.modo * 10u + f.nivel; }",
  "",
].join("\n");

describe("bitfields (bits)", () => {
  test("cruzan la ABI igual que el struct C", () => {
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-bits-"));
    try {
      const object = build_object(compiler, dir, "flags", C_SOURCE);
      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          "",
          "rune Flags",
          "  bits 3 modo: uint32_t",
          "  bits 5 nivel: uint32_t",
          "",
          'extern "C"',
          "  crear = (modo: uint32_t, nivel: uint32_t) -> Flags",
          "  leer = (f: Flags) -> uint32_t",
          "",
          "main = -> void",
          "  f = crear(3, 5)",
          "  io::println(leer(f))",
          "  io::println(f.modo)",
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: [object] });
      expect(result.diagnostics.map((diagnostic) => diagnostic.message)).toEqual([]);
      const ran = spawnSync(result.binary_path as string, [], { encoding: "utf8" });
      expect(ran.stdout).toBe("35\n3\n");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("el ancho que no cabe en el tipo es un error", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu-bits-"));
    try {
      const source = join(dir, "main.pengu");
      writeFileSync(source, "rune Flags\n  bits 40 modo: uint32_t\n\nmain = -> void\n  f = Flags(0)\n");
      const result = compile_file(source);
      expect(result.ok).toBe(false);
      expect(result.diagnostics.map((diagnostic) => diagnostic.code)).toContain("E0712");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("`pengu size --fields` muestra el ancho en bits", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu-bits-"));
    try {
      const source = join(dir, "main.pengu");
      writeFileSync(source, "rune Flags\n  bits 3 modo: uint32_t\n  bits 5 nivel: uint32_t\n\nmain = -> void\n  f = Flags(0, 0)\n");
      const { output } = run_size([source], { fields: true });
      expect(output).toContain("bits 3");
      expect(output).toContain("bits 5");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
