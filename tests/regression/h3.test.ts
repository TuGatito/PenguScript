// Regresiones de la fase H3: hash sintetizado y requisitos de las claves
// de los contenedores asociativos.

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

function parse_and_check(text: string): readonly Diagnostic[] {
  const parsed = parse_text("test.pengu", text);
  const sink = make_sink({ max: 100 });
  for (const diagnostic of parsed.diagnostics) sink.add(diagnostic);
  check_program("test.pengu", parsed.program, sink);
  return sink.diagnostics;
}

function messages(text: string): readonly string[] {
  return parse_and_check(text).map((item) => item.message);
}

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_h3_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(
      result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output,
    );
  }
  const spawned = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
  expect(spawned.status).toBe(0);
  return spawned.stdout;
}

const PUNTO = `
rune Punto
  x: int
  y: int

  constructor(x: int, y: int)
`;

const IGUALES = `
enchanting Punto
  operator == = (otro: Punto) -> bool
    @x == otro.x and @y == otro.y
`;

const ORDEN = `
enchanting Punto
  operator <=> = (otro: Punto) -> Ordering
    @x <=> otro.x
`;

describe("H3 hash sintetizado", () => {
  test("una rune con «==» y campos hasheables sirve de clave", () => {
    const output = run_source(
      "unordered_rune",
      `invoke "std/io"
${PUNTO}
${IGUALES}
main = ->
  mut m: unordered_map<Punto, string> = unordered_map<Punto, string>{}
  m.insert(Punto(1, 1), "uno")
  m.insert(Punto(2, 5), "dos")
  io::println("#{#m}")
  io::println("#{Punto(1, 1) == Punto(1, 1)}")
`,
    );
    expect(output.trim()).toBe("2\ntrue");
  });

  test("un sello hashea su valor subyacente", () => {
    const output = run_source(
      "unordered_seal",
      `invoke "std/io"
seal Id = int

enchanting Id
  operator == = (otro: Id) -> bool
    @ == (otro as int)

main = ->
  mut m: unordered_map<Id, string> = unordered_map<Id, string>{}
  m.insert(Id(1), "uno")
  io::println("#{#m}")
`,
    );
    expect(output.trim()).toBe("1");
  });

  test("sin «==» la clave no vale para unordered_", () => {
    const found = messages(`${PUNTO}
main = ->
  mut m: unordered_map<Punto, int> = unordered_map<Punto, int>{}
`);
    expect(found.some((message) => message.includes("no declara «operator ==»"))).toBe(true);
  });

  test("un campo no hasheable se detecta", () => {
    const found = messages(`
rune Bolsa
  cosas: vector<int>

  constructor(cosas: vector<int>)

enchanting Bolsa
  operator == = (otra: Bolsa) -> bool
    true

main = ->
  mut s: unordered_set<Bolsa> = unordered_set<Bolsa>{}
`);
    expect(found.some((message) => message.includes("no se puede hashear"))).toBe(true);
  });
});

describe("H3 claves ordenadas", () => {
  test("map con rune exige «<=>» o «<»", () => {
    const found = messages(`${PUNTO}
main = ->
  mut m: map<Punto, int> = map<Punto, int>{}
`);
    expect(found.some((message) => message.includes("no define «<=>» ni «<»"))).toBe(true);
  });

  test("con «<=>» el map ordena por la rune", () => {
    const output = run_source(
      "ordered_rune",
      `invoke "std/io"
${PUNTO}
${ORDEN}
main = ->
  mut m: map<Punto, int> = map<Punto, int>{}
  m.insert(Punto(2, 0), 20)
  m.insert(Punto(1, 0), 10)
  for k, v in m
    io::println("#{k.x}: #{v}")
`,
    );
    expect(output.trim()).toBe("1: 10\n2: 20");
  });

  test("las comparaciones derivadas de «<=>» funcionan", () => {
    const output = run_source(
      "ordered_compare",
      `invoke "std/io"
${PUNTO}
${ORDEN}
main = ->
  a = Punto(1, 0)
  b = Punto(2, 0)
  io::println("#{a < b} #{a > b} #{a <= b} #{a >= b}")
`,
    );
    expect(output.trim()).toBe("true false true false");
  });
});
