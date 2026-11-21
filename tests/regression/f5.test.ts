// Regresiones de la fase F5: genéricos completos (runes, omens, seal,
// echo, funciones con sigilos y restricciones `needs`).

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
  const dir = mkdtempSync(join(tmpdir(), `pengu_f5_${name}_`));
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

describe("F5 genéricos", () => {
  test("rune genérico con método que devuelve T", () => {
    const source = `rune Caja<T>
  valor: T

  constructor(valor: T)

enchanting Caja<T>
  obtener = -> T
    @valor

main = ->
  c = Caja<int>(7)
  io::println("valor: #{c.obtener()}")
`;
    expect(codes(source)).toEqual([]);
    expect(run_source("rune", `invoke "std/io"\n${source}`)).toContain("valor: 7");
  });

  test("omen genérico: construir y hacer match", () => {
    const source = `invoke "std/io"

omen Resultado<T>
  Ok(T)
  Error(string)

main = ->
  r: Resultado<int> = Resultado<int>::Ok(5)
  valor = match r
    when Ok(v) then v
    when Error(_mensaje) then 0
  io::println("valor: #{valor}")
`;
    expect(codes(source)).toEqual([]);
    expect(run_source("omen", source)).toContain("valor: 5");
  });

  test("seal genérico y desenvuelto con as", () => {
    const source = `invoke "std/io"

seal Id<T> = int

main = ->
  id = Id<int>(7)
  io::println("id: #{id as int}")
`;
    expect(run_source("seal", source)).toContain("id: 7");
  });

  test("echo genérico se sustituye por su objetivo", () => {
    const source = `invoke "std/io"

echo Lista<T> = vector<T>

main = ->
  xs: Lista<int> = [1, 2, 3]
  io::println("lista: #{#xs}")
`;
    expect(codes(source)).toEqual([]);
    expect(run_source("echo", source)).toContain("lista: 3");
  });

  test("función genérica con instanciación explícita e inferida", () => {
    const source = `invoke "std/io"

identidad = <T>(x: T) -> T
  x

primero = <T>(xs: vector<T>) -> T
  xs[0]

main = ->
  io::println("a: #{identidad<int>(42)}")
  io::println("b: #{primero([7, 8])}")
`;
    const output = run_source("funciones", source);
    expect(output).toContain("a: 42");
    expect(output).toContain("b: 7");
  });

  test("los argumentos de tipo deben coincidir con los sigilos", () => {
    const source = `identidad = <T>(x: T) -> T
  x

main = ->
  y = identidad<int, int>(1)
`;
    expect(codes(source)).toContain(CODES.wrong_arity);
  });

  test("needs rechaza un tipo que no cumple la capacidad", () => {
    const source = `media = <T needs Floating>(x: T, y: T) -> T
  (x + y) / 2

main = ->
  m = media<int>(1, 2)
`;
    expect(codes(source)).toContain(CODES.missing_capability);
  });

  test("needs acepta un tipo que sí cumple la capacidad", () => {
    const source = `invoke "std/io"

media = <T needs Floating>(x: T, y: T) -> T
  (x + y) / 2

main = ->
  io::println("media: #{media<double>(1.0, 2.0)}")
`;
    expect(codes(source)).toEqual([]);
    expect(run_source("needs_ok", source)).toContain("media: 1.5");
  });

  test("un campo genérico con valor por defecto", () => {
    const source = `invoke "std/io"

rune Bolsa<T>
  cosas: vector<T> = []

main = ->
  b = Bolsa<int>()
  io::println("cosas: #{#b.cosas}")
`;
    const output = run_source("campo", source);
    expect(output).toContain("cosas: 0");
  });
});
