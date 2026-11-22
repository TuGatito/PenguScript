// Regresiones de la fase H1: el checker nunca acepta algo que el codegen no
// sabe emitir, y los panics salen como mensaje controlado (exit 1).

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { parse_text } from "../../src/frontend/parser.ts";
import { check_program } from "../../src/semantic/checker.ts";
import { make_sink } from "../../src/diagnostics/sink.ts";
import type { Diagnostic } from "../../src/diagnostics/diagnostic.ts";
import { compile_file } from "../../src/driver/compile.ts";
import { analyze_graph } from "../../src/driver/analyze.ts";

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

function project_codes(source: string): readonly string[] {
  const dir = mkdtempSync(join(tmpdir(), "pengu_h1_proj_"));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const sink = make_sink({ max: 100 });
  analyze_graph(file, sink);
  return sink.diagnostics.map((item) => item.code);
}

function run_source(name: string, source: string): { status: number | null; stdout: string; stderr: string } {
  const dir = mkdtempSync(join(tmpdir(), `pengu_h1_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(
      result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output,
    );
  }
  return spawnSync(result.binary_path ?? "", [], { encoding: "utf8" }) as {
    status: number | null;
    stdout: string;
    stderr: string;
  };
}

describe("H1 any", () => {
  test("no se puede convertir any con as", () => {
    const text = `
main = ->
  x: any = 4
  n = x as int
`;
    expect(codes(text)).toContain("E0514");
  });

  test("tampoco se puede convertir a any", () => {
    const text = `
main = ->
  n = 4 as any
`;
    expect(codes(text)).toContain("E0514");
  });
});

describe("H1 funciones que no son valores", () => {
  test("una función con parámetros mut no se guarda en function<...>", () => {
    const text = `
incrementar = (mut x: int) -> void
  x += 1

main = ->
  f: function<(int) -> void> = incrementar
`;
    expect(codes(text)).toContain("E0515");
  });

  test("una función unsafe no se guarda en function<...>", () => {
    const text = `
unsafe leer = (p: raw<int>) -> int
  *p

main = ->
  f: function<(raw<int>) -> int> = leer
`;
    expect(codes(text)).toContain("E0515");
  });

  test("llamar a una función mut directamente sigue permitido", () => {
    const output = run_source("mut_call", `
invoke "std/io"
incrementar = (mut x: int) -> void
  x += 1
main = ->
  mut n = 1
  incrementar(mut n)
  io::println("#{n}")
`);
    expect(output.status).toBe(0);
    expect(output.stdout.trim()).toBe("2");
  });
});

describe("H1 métodos enhechizados como valor", () => {
  test("una sobrecarga es usable como valor", () => {
    const output = run_source("member_value", `
invoke "std/io"
invoke "std/string"
main = ->
  f = "manzana".compare
  io::println("#{f("banana")}")
`);
    expect(output.status).toBe(0);
    expect(output.stdout.trim()).toBe("1");
  });

  test("varias sobrecargas no son un valor", () => {
    const text = `
enchanting string
  recortar = (n: int) -> string
    @
  recortar = (n: int, desde: int) -> string
    @

main = ->
  a = "x"
  f = a.recortar
`;
    expect(codes(text)).toContain("E0708");
  });

  test("un método mut no es un valor", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_h1_mut_member_"));
    const file = join(dir, "main.pengu");
    writeFileSync(file, `
invoke "std/vector"

main = ->
  mut xs = [3, 1]
  f = xs.sort
  f()
`);
    const sink = make_sink({ max: 100 });
    analyze_graph(file, sink);
    expect(sink.diagnostics.map((item) => item.code)).toContain("E0515");
  });
});

describe("H1 panics", () => {
  test("un índice fuera de rango termina con «panic:» y exit 1", () => {
    const output = run_source("panic", `
invoke "std/io"
main = ->
  xs = [1, 2]
  io::println("#{xs[5]}")
`);
    expect(output.status).toBe(1);
    expect(output.stderr).toContain("panic: índice 5 fuera de rango");
    expect(output.stderr).toContain("tamaño 2");
  });
});

describe("H1 rangos", () => {
  test("un rango se anota y se pasa a una función", () => {
    const output = run_source("range", `
invoke "std/io"
contar = (r: range<int>) -> int
  mut n = 0
  for x in r
    n += 1
  n
main = ->
  s: range<int> = 2..5
  io::println("#{contar(s)}")
`);
    expect(output.status).toBe(0);
    expect(output.stdout.trim()).toBe("4");
  });

  test("la anotación de rango no produce un diagnóstico absurdo", () => {
    const text = `
main = ->
  r: range<int> = 1..10
`;
    const messages = parse_and_check(text).map((item) => item.message);
    expect(messages.some((message) => message.includes("se encontró «range<int>»"))).toBe(false);
  });
});
