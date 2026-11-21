// Regresiones de la fase F2: modelo numérico, conversiones,
// métodos de flotante, `Ordering` y tipos de función.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { parse_text } from "../../src/frontend/parser.ts";
import { check_program } from "../../src/semantic/checker.ts";
import { make_sink } from "../../src/diagnostics/sink.ts";
import type { Diagnostic } from "../../src/diagnostics/diagnostic.ts";
import { CODES } from "../../src/diagnostics/codes.ts";
import { compile_file } from "../../src/driver/compile.ts";

function parse_and_check(text: string): readonly Diagnostic[] {
  const parsed = parse_text("test.pengu", text);
  const sink = make_sink({ max: 100 });
  for (const diagnostic of parsed.diagnostics) sink.add(diagnostic);
  check_program("test.pengu", parsed.program, sink);
  return sink.diagnostics;
}

function codes(text: string): readonly string[] {
  return parse_and_check(text).map((item) => item.code);
}

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_f2_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(
      result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output,
    );
  }
  const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout;
}

describe("F2 · tipo de función", () => {
  test("una variable puede tener tipo `function<(int) -> int>`", () => {
    const text = `doble = (x: int) -> int
  x * 2

main = ->
  fn: function<(int) -> int> = doble
  fn(3)
`;
    expect(codes(text)).toEqual([]);
  });

  test("una firma incompatible se rechaza", () => {
    const text = `doble = (x: int) -> int
  x * 2

main = ->
  fn: function<(string) -> int> = doble
  fn(3)
`;
    expect(codes(text)).toContain(CODES.type_mismatch);
  });
});

describe("F2 · modelo numérico", () => {
  test("`int + double` promociona a double", () => {
    const text = `main = ->
  a: int = 3
  b: double = 2.5
  c: double = a + b
  pass
`;
    expect(codes(text)).toEqual([]);
  });

  test("`%` no admite flotantes", () => {
    const text = `main = ->
  x: double = 5.5
  r = x % 2.0
  pass
`;
    const diagnostics = parse_and_check(text);
    expect(diagnostics.map((item) => item.code)).toContain(CODES.type_mismatch);
    expect(diagnostics[0]?.message).toContain("«%» solo admite enteros");
  });

  test("mezclar signo del mismo ancho exige conversión", () => {
    const text = `main = ->
  a: int = 1
  b: uint32_t = 2
  c = a + b
  pass
`;
    const diagnostics = parse_and_check(text);
    expect(diagnostics.map((item) => item.code)).toContain(CODES.type_mismatch);
    expect(diagnostics[0]?.message).toContain("mismo ancho y signo distinto");
  });
});

describe("F2 · conversiones", () => {
  test("`as` seguro entre enteros que ensanchan", () => {
    const text = `main = ->
  a: int8_t = 1
  b: int64_t = a as int64_t
  c: int32_t = a as int32_t
  pass
`;
    expect(codes(text)).toEqual([]);
  });

  test("`double as float` exige `unsafe`", () => {
    const text = `main = ->
  x: double = 1.5
  y = x as float
  pass
`;
    expect(codes(text)).toContain(CODES.unsafe_required);
  });

  test("un omen no se convierte a un entero arbitrario", () => {
    const text = `main = ->
  o = Ordering::Less
  n = o as int
  pass
`;
    expect(codes(text)).toContain(CODES.unsafe_required);
  });

  test("`try_from` y `from` de primitivos", () => {
    const text = `main = ->
  n: int? = int::try_from("42")
  m: int = int::from(3.9)
  x: float? = float::try_from(2.5)
  pass
`;
    expect(codes(text)).toEqual([]);
  });

  test("`try_from` de un tipo que no es numérico se rechaza", () => {
    const text = `main = ->
  n = int::try_from(true)
  pass
`;
    expect(codes(text)).toContain(CODES.type_mismatch);
  });
});

describe("F2 · Ordering y flotantes", () => {
  test("`<=>` sobre números da `Ordering`", () => {
    const text = `main = ->
  o: Ordering = 1 <=> 2
  if o == Ordering::Less
    pass
`;
    expect(codes(text)).toEqual([]);
  });

  test("métodos de flotante", () => {
    const text = `main = ->
  x: double = 16.0
  r: double = x.sqrt()
  a: double = x.abs()
  n: bool = x.is_nan()
  pass
`;
    expect(codes(text)).toEqual([]);
  });
});

describe("F2 · ejecución", () => {
  test("promociones, flotantes, comparación y conversiones", () => {
    const out = run_source(
      "run",
      `invoke "std/io"

doble = (x: int) -> int
  x * 2

main = ->
  fn: function<(int) -> int> = doble
  io::println("fn(4) = #{fn(4)}")

  a: int = 3
  b: double = 2.5
  io::println("total = #{a + b}")

  x: double = 16.0
  io::println("raíz = #{x.sqrt()}, ¿nan? #{x.is_nan()}")

  if a <=> 5 == Ordering::Less
    io::println("3 es menor que 5")

  n = int::try_from("42")
  if n.is_some()
    io::println("parseado: #{n.value()}")

  pequeño = int8_t::try_from(300)
  io::println("¿cabe 300 en int8_t? #{pequeño.is_none()}")

  io::println("double::try_from(7) = #{double::try_from(7)}")
`,
    );
    expect(out).toContain("fn(4) = 8");
    expect(out).toContain("total = 5.5");
    expect(out).toContain("raíz = 4, ¿nan? false");
    expect(out).toContain("3 es menor que 5");
    expect(out).toContain("parseado: 42");
    expect(out).toContain("¿cabe 300 en int8_t? true");
    expect(out).toContain("double::try_from(7) = 7");
  });
});
