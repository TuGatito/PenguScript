// F0: un `.d.pengu` escrito a mano con struct por valor, enum y enteros de
// ancho fijo genera C++ válido, enlaza y devuelve lo que dice el C.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { compile_file } from "../../src/driver/compile.ts";
import { build_object, c_compiler } from "./native.ts";

describe("tipos nativos", () => {
  test("struct por valor, enum y uint64_t cruzan la ABI", () => {
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-types-"));
    try {
      const object = build_object(
        compiler,
        dir,
        "types",
        [
          "typedef struct { unsigned char r, g, b, a; } Color;",
          "typedef enum { ROJO = 1, VERDE = 2 } ColorId;",
          "Color fade(Color color, float alpha, int veces) {",
          "  Color out = color;",
          "  out.a = (unsigned char)(color.a * alpha);",
          "  out.b = (unsigned char)veces;",
          "  return out;",
          "}",
          "int id_de(ColorId id) { return (int)id; }",
          "unsigned long long dobla(unsigned long long x) { return x * 2; }",
          "",
        ].join("\n"),
      );

      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          "",
          "rune Color",
          "  r: uint8_t",
          "  g: uint8_t",
          "  b: uint8_t",
          "  a: uint8_t",
          "",
          "omen ColorId",
          "  ROJO = 1",
          "  VERDE = 2",
          "",
          'extern "C"',
          "  fade = (color: Color, alpha: float, veces: int) -> Color",
          "  id_de = (id: ColorId) -> int",
          "  dobla = (x: uint64_t) -> uint64_t",
          "",
          "main = -> void",
          "  base = Color(255, 0, 0, 255)",
          "  resultado = fade(base, 0.5, 3)",
          '  io::println("r=#{resultado.r} a=#{resultado.a} veces=#{resultado.b}")',
          '  io::println("id=#{id_de(ColorId::VERDE)}")',
          '  io::println("dobla=#{dobla(21)}")',
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: [object] });
      if (!result.ok) throw new Error(result.output);
      if (result.binary_path === undefined) throw new Error("sin binario");

      const run = spawnSync(result.binary_path, [], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toBe("r=255 a=127 veces=3\nid=2\ndobla=42\n");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60000);
});
