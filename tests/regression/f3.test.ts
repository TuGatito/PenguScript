// Regresiones de la fase F3: funciones variádicas, `any` y la
// biblioteca `io`/`format`/`log` escrita en PenguScript.

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
  const dir = mkdtempSync(join(tmpdir(), `pengu_f3_${name}_`));
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

describe("F3 · parámetros variádicos", () => {
  test("el parámetro variádico vale un vector dentro del cuerpo", () => {
    const text = `sumar = (...numeros: int) -> int
  mut total = 0
  for n in numeros
    total += n
  total

main = ->
  sumar(1, 2, 3)
`;
    expect(codes(text)).toEqual([]);
  });

  test("debe ser el último parámetro", () => {
    const text = `raro = (...numeros: int, extra: int) -> int
  extra
`;
    expect(codes(text)).toContain(CODES.expected_token);
  });

  test("no admite valor por defecto", () => {
    const text = `raro = (...numeros: int = 1) -> int
  0
`;
    expect(codes(text)).toContain(CODES.unexpected_token);
  });

  test("solo se puede expandir un vector", () => {
    const text = `sumar = (...numeros: int) -> int
  0

main = ->
  sumar(...(1, 2))
`;
    expect(codes(text)).toContain(CODES.type_mismatch);
  });
});

describe("F3 · any y Display", () => {
  test("una variádica any exige Display", () => {
    const text = `rune Caja
  valor: int

println = (...partes: any) -> void
  0

main = ->
  println(Caja(1))
`;
    expect(codes(text)).toContain(CODES.not_display);
  });

  test("un rune con `to_string` sí pasa", () => {
    const text = `rune Punto
  x: int

enchanting Punto
  to_string = -> string
    "punto"

println = (...partes: any) -> void
  0

main = ->
  println(Punto(1))
`;
    expect(codes(text)).toEqual([]);
  });
});

describe("F3 · ejecución de variádicas", () => {
  test("suma, cero argumentos, argumentos mezclados y spread", () => {
    const source = `invoke "std/io"

sumar = (...numeros: int) -> int
  mut total = 0
  for n in numeros
    total += n
  total

main = ->
  io::println(sumar(1, 2, 3))
  io::println(sumar())
  io::println("a", 1, true)
  numeros = [4, 5, 6]
  io::println(sumar(...numeros))
`;
    expect(run_source("variadicas", source)).toBe("6\n0\na1true\n15\n");
  });

  test("un rune con `to_string` se interpola en una variádica", () => {
    const source = `invoke "std/io"

rune Punto
  x: int
  y: int

enchanting Punto
  to_string = -> string
    "(#{@x}, #{@y})"

main = ->
  io::println(Punto(3, 4))
`;
    expect(run_source("rune_display", source)).toBe("(3, 4)\n");
  });

  test("un `extern` variádico se emite como varargs de C", () => {
    const source = `extern "C"
  printf = (formato: string, ...extras: any) -> int

main = ->
  printf("hola %d\\n", 7)
  pass
`;
    expect(run_source("extern_variadico", source)).toBe("hola 7\n");
  });

  test("`format` y `log` se resuelven como módulos PenguScript", () => {
    const source = `invoke "std/io"
invoke "std/format"

main = ->
  io::println(format::format("x=", 7, " y=", 2.5))
`;
    expect(run_source("format", source)).toBe("x=7 y=2.5\n");
  });
});
