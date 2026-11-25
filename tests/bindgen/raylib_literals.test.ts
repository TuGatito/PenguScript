// F1 contra una ABI real: raylib instalada.
//
// Sin coerción de literales este programa necesitaría `uint8_t::from` en
// cada campo y `float::from` en el alpha. Si raylib no está instalada, la
// prueba se omite (no falla en máquinas sin ella).

import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { compile_file } from "../../src/driver/compile.ts";

function raylib_available(): boolean {
  return spawnSync("pkg-config", ["--exists", "raylib"]).status === 0;
}

describe("literales contra raylib", () => {
  test("struct por valor, float y flags con literales", () => {
    if (!raylib_available()) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-raylib-lit-"));
    try {
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
          'extern "C"',
          "  Fade = (color: Color, alpha: float) -> Color",
          "  GetRandomValue = (minimo: int, maximo: int) -> int",
          "  SetTraceLogLevel = (nivel: int) -> void",
          "",
          "main = -> void",
          "  SetTraceLogLevel(4)",
          "  base = Color(255, 0, 0, 255)",
          "  mitad = Fade(base, 0.5)",
          '  io::println("r=#{mitad.r} a=#{mitad.a}")',
          '  io::println("fijo=#{GetRandomValue(7, 7)}")',
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: ["raylib"] });
      if (!result.ok) throw new Error(result.output);
      if (result.binary_path === undefined) throw new Error("sin binario");

      const run = spawnSync(result.binary_path, [], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toBe("r=255 a=127\nfijo=7\n");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60000);
});
