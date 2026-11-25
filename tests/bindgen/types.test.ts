// F3: bindgen traduce structs, uniones, enums, typedefs, arrays y
// bitfields, y el layout coincide con el de C.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { run_bindgen } from "../../src/cli/bindgen_command.ts";
import { parse_args } from "../../src/cli/args.ts";
import { find_clang } from "../../src/bindgen/clang_ast.ts";
import { compile_file } from "../../src/driver/compile.ts";
import { run_size } from "../../src/cli/size_command.ts";
import { build_object, c_compiler } from "./native.ts";

const HEADER = [
  "typedef struct Punto { float x; float y; } Punto;",
  "typedef Punto Coordenada;",
  "typedef enum { MODO_A = 1, MODO_B = 4, MODO_C } Modo;",
  "typedef union Dato { int entero; float real; } Dato;",
  "typedef struct Registro {",
  "  Punto p;",
  "  Dato d;",
  "  Modo m;",
  "  unsigned int activo : 1;",
  "  unsigned int nivel : 3;",
  "  float pesos[2];",
  "} Registro;",
  "typedef void (*Aviso)(int nivel);",
  "int probar(Punto p, Coordenada c, Modo m, Dato d, Registro r);",
  "int avisar_si_hay(Aviso aviso);",
  "",
].join("\n");

const IMPLEMENTATION = [
  "#include \"tipos.h\"",
  "int probar(Punto p, Coordenada c, Modo m, Dato d, Registro r) {",
  "  return (int)(p.x + p.y + c.x + m + d.entero + r.nivel + r.pesos[1]);",
  "}",
  "int avisar_si_hay(Aviso aviso) { return aviso == 0 ? 0 : 1; }",
  "",
].join("\n");

describe("bindgen tipos", () => {
  test("records, uniones, enums, alias y bitfields cruzan la ABI", () => {
    if (find_clang() === undefined) return;
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-f3-"));
    try {
      const header = join(dir, "tipos.h");
      writeFileSync(header, HEADER);
      const binding = join(dir, "tipos.d.pengu");
      const generated = run_bindgen(parse_args(["bindgen", header, "--out", binding, "--realm", "tipos"]));
      expect(generated.exit_code).toBe(0);
      const text = readFileSync(binding, "utf8");
      expect(text).toContain("rune Punto");
      expect(text).toContain("meld Dato");
      expect(text).toContain("omen Modo");
      expect(text).toContain("MODO_A = 1");
      expect(text).toContain("MODO_B = 4");
      expect(text).toContain("MODO_C = 5");
      expect(text).toContain("echo Coordenada = Punto");
      expect(text).toContain("bits 1 activo: uint32_t");
      expect(text).toContain("bits 3 nivel: uint32_t");
      expect(text).toContain("pesos: array<float, 2>");
      expect(text).toContain("probar = (p: Punto, c: Coordenada, m: Modo, d: Dato, r: Registro) -> int");
      expect(text).toContain("avisar_si_hay = (aviso: raw<void>) -> int");

      const object = build_object(compiler, dir, "tipos", IMPLEMENTATION);

      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          `invoke "${binding.replace(/\.pengu$/, "")}"`,
          "",
          "main = -> void",
          "  p = tipos::Punto(3.0, 4.0)",
          "  c = tipos::Coordenada(1.0, 1.0)",
          "  mut d = tipos::Dato()",
          "  d.entero = 5",
          "  unsafe",
          "    io::println(\"entero: #{d.entero}\")",
          "  pesos = array<float, 2>[1.5, 2.5]",
          "  r = tipos::Registro(p, d, tipos::Modo::MODO_B, 1, 3, pesos)",
          "  io::println(\"suma: #{tipos::probar(p, c, tipos::Modo::MODO_B, d, r)}\")",
          "  io::println(\"aviso: #{tipos::avisar_si_hay(nullptr)}\")",
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: [object] });
      if (!result.ok) throw new Error(result.output);
      if (result.binary_path === undefined) throw new Error("sin binario");
      const run = spawnSync(result.binary_path, [], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toBe("entero: 5\nsuma: 22\naviso: 0\n");

      // El layout de los tipos generados coincide con el de C.
      const size = run_size([source], { json: true });
      const parsed = JSON.parse(size.output) as {
        types: { name: string; size: number; align: number; fields: { name: string; offset?: number; width?: number }[] }[];
      };
      const find = (name: string) => parsed.types.find((item) => item.name === `tipos::${name}`);
      expect(find("Punto")?.size).toBe(8);
      expect(find("Punto")?.align).toBe(4);
      expect(find("Dato")?.size).toBe(4);
      expect(find("Registro")?.size).toBe(28);
      const registro = find("Registro");
      expect(registro?.fields.find((field) => field.name === "d")?.offset).toBe(8);
      expect(registro?.fields.find((field) => field.name === "pesos")?.offset).toBe(20);
      expect(registro?.fields.find((field) => field.name === "nivel")?.width).toBe(3);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60000);
});
