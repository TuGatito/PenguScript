// F4: bindgen traduce las macros constantes de una cabecera a `define` y
// `const`, y las que no son constantes se omiten con un motivo.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { existsSync } from "node:fs";
import { run_bindgen } from "../../src/cli/bindgen_command.ts";
import { parse_args } from "../../src/cli/args.ts";
import { find_clang } from "../../src/bindgen/clang_ast.ts";
import { compile_file } from "../../src/driver/compile.ts";
import { build_object, c_compiler } from "./native.ts";

const HEADER = [
  "#define CONTEO 7",
  "#define NEGATIVO (-3)",
  "#define GRANDE 5000000000LL",
  "#define PI_F 3.14159265358979323846f",
  "#define ESCALA 2.5f",
  "#define MEDIO_PI (PI_F / 2.0f)",
  "#define SALUDO \"hola\"",
  "#define INICIAL 'p'",
  "#define DOBLE(x) ((x) * 2)",
  "#define _PLATAFORMA 1",
  "#define flags 3",
  "typedef struct Color { unsigned char r, g, b, a; } Color;",
  "#define ROJO CLITERAL(Color){255, 0, 0, 255}",
  "typedef enum { TIPO_A = 1, TIPO_B = 2 } Tipo;",
  "#define TIPO_POR_DEFECTO TIPO_A",
  "int probar(void);",
  "",
].join("\n");

const IMPLEMENTATION = [
  '#include "macros.h"',
  "int probar(void) { return CONTEO + (int)ESCALA + TIPO_POR_DEFECTO; }",
  "",
].join("\n");

describe("bindgen macros", () => {
  test("enteros, decimales, texto, caracteres, colores y alias de enum", () => {
    if (find_clang() === undefined) return;
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-f4-"));
    try {
      const header = join(dir, "macros.h");
      writeFileSync(header, HEADER);
      const binding = join(dir, "macros.d.pengu");
      const generated = run_bindgen(parse_args(["bindgen", header, "--out", binding, "--realm", "macros"]));
      expect(generated.exit_code).toBe(0);
      const text = readFileSync(binding, "utf8");

      expect(text).toContain("define CONTEO: int = 7");
      expect(text).toContain("define NEGATIVO: int64_t = -3");
      expect(text).toContain("define GRANDE: int64_t = 5000000000");
      expect(text).toContain("define ESCALA: double = 2.5");
      expect(text).toContain("define MEDIO_PI: double = 1.5707963267948966");
      expect(text).toContain('define SALUDO: string = "hola"');
      expect(text).toContain("define INICIAL: char = 'p'");
      expect(text).toContain("const ROJO: Color = Color(255, 0, 0, 255)");
      expect(text).toContain("define TIPO_POR_DEFECTO: int = 1");

      expect(text).not.toContain("_PLATAFORMA");
      expect(text).not.toContain("flags");
      expect(text).not.toContain("DOBLE");

      const object = build_object(compiler, dir, "macros", IMPLEMENTATION);

      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          `invoke "${binding.replace(/\.pengu$/, "")}"`,
          "",
          "main = -> void",
          '  io::println("valor: #{macros::probar()}")',
          '  io::println("saludo: #{macros::SALUDO}")',
          '  io::println("color: #{macros::ROJO.r},#{macros::ROJO.g},#{macros::ROJO.b}")',
          '  io::println("tipo: #{macros::TIPO_POR_DEFECTO} medio: #{macros::MEDIO_PI}")',
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: [object] });
      if (!result.ok) throw new Error(result.output);
      if (result.binary_path === undefined) throw new Error("sin binario");
      const run = spawnSync(result.binary_path, [], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toBe("valor: 10\nsaludo: hola\ncolor: 255,0,0\ntipo: 1 medio: 1.5708\n");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60000);

  test("raylib: versión, banderas, colores y constantes derivadas", () => {
    if (find_clang() === undefined) return;
    const header = "/usr/include/raylib.h";
    if (!existsSync(header)) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-f4-rl-"));
    try {
      const binding = join(dir, "raylib.d.pengu");
      const generated = run_bindgen(parse_args(["bindgen", header, "--out", binding, "--realm", "raylib"]));
      expect(generated.exit_code).toBe(0);
      const text = readFileSync(binding, "utf8");

      expect(text).toContain('define RAYLIB_VERSION: string = "6.2"');
      expect(text).toContain("FLAG_VSYNC_HINT = 64");
      expect(text).toContain("const LIGHTGRAY: Color = Color(200, 200, 200, 255)");
      expect(text).toContain("define DEG2RAD: double = 0.017453292519943295");
      expect(text).toContain("define MOUSE_LEFT_BUTTON: int = 0");
      expect(generated.output).toContain("619 función(es)");

      const check = spawnSync("bun", ["run", "src/main.ts", "check", binding], { encoding: "utf8", cwd: process.cwd() });
      expect(check.status).toBe(0);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60000);
});
