import { describe, expect, test } from "bun:test";
import { readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { run_bindgen } from "../../src/cli/bindgen_command.ts";
import { parse_args } from "../../src/cli/args.ts";
import { parse_text } from "../../src/frontend/parser.ts";
import { find_clang } from "../../src/bindgen/clang_ast.ts";

const fixtures = new URL("../fixtures/native", import.meta.url).pathname;
const out = join(fixtures, "demo.d.pengu");

describe("bindgen", () => {
  test("genera enlaces a partir de una cabecera C", () => {
    if (find_clang() === undefined) return;
    const result = run_bindgen(parse_args(["bindgen", fixtures + "/demo.h", "--out", out, "--realm", "demo"]));
    expect(result.exit_code).toBe(0);
    const text = readFileSync(out, "utf8");
    expect(text).toContain("realm demo");
    expect(text).toContain("suma = (a: double, b: double) -> double");
    expect(text).toContain("contar = (texto: string) -> int");
    expect(text).toContain("maximo = (a: int, b: int) -> int");
    // G2: una keyword de PenguScript en un parámetro se sufija con `_`.
    expect(text).toContain("SetWindowState = (flags_: uint32_t) -> void");
    // G4: los enteros de C se mapean a tipos de ancho fijo (LP64).
    expect(text).toContain("suma_grande = (a: uint64_t, b: uint64_t) -> uint64_t");
    // Un retorno `const char*` se declara como `string`.
    expect(text).toContain("nombre_del_programa = () -> string");

    const parsed = parse_text(out, text);
    expect(parsed.diagnostics).toEqual([]);
    rmSync(out);
  });

  test("los -I llegan a clang y no se comen el archivo de salida", () => {
    if (find_clang() === undefined) return;
    const includes = join(fixtures, "includes");
    const target = join(fixtures, "usa_include.d.pengu");
    const args = parse_args([
      "bindgen",
      join(fixtures, "usa_include.h"),
      "-I",
      includes,
      "--out",
      target,
      "--realm",
      "incluye",
    ]);
    expect(args.include_dirs).toEqual([includes]);
    expect(args.positionals).toEqual([join(fixtures, "usa_include.h")]);

    const result = run_bindgen(args);
    expect(result.exit_code).toBe(0);
    const text = readFileSync(target, "utf8");
    expect(text).toContain("base_valor = () -> int");
    expect(text).toContain("usa_base = () -> int");
    rmSync(target);
  });
});
