// Regresiones de la fase F6: runes, herencia y operadores de usuario.

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
  const dir = mkdtempSync(join(tmpdir(), `pengu_f6_${name}_`));
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

const PUNTO = `
rune Punto
  x: int
  y: int

  constructor(x: int, y: int)

enchanting Punto
  operator + = (otro: Punto) -> Punto
    Punto(@x + otro.x, @y + otro.y)

  mut operator += = (otro: Punto) -> void
    @x += otro.x
    @y += otro.y

  operator - = -> Punto
    Punto(-@x, -@y)

  mut operator [] = (i: int) -> mut ref<int>
    if i == 0 then ref(@x) else ref(@y)
`;

describe("F6 runes y operadores", () => {
  test("operator [] mutable permite leer y escribir", () => {
    const output = run_source(
      "index",
      `invoke "std/io"
${PUNTO}
main = ->
  mut p = Punto(1, 2)
  p[0] = 10
  io::println("#{p[0]} #{p[1]}")
`,
    );
    expect(output.trim()).toBe("10 2");
  });

  test("operadores binarios, compuestos y unarios", () => {
    const output = run_source(
      "ops",
      `invoke "std/io"
${PUNTO}
main = ->
  mut p = Punto(1, 2)
  p += Punto(3, 4)
  q = -p
  io::println("#{p.x} #{p.y} #{q.x} #{q.y}")
`,
    );
    expect(output.trim()).toBe("4 6 -4 -6");
  });

  test("un operador libre acepta al entero a la izquierda", () => {
    const output = run_source(
      "free",
      `invoke "std/io"
${PUNTO}
operator * = (escala: int, p: Punto) -> Punto
  Punto(escala * p.x, escala * p.y)

main = ->
  r = 3 * Punto(2, 5)
  io::println("#{r.x} #{r.y}")
`,
    );
    expect(output.trim()).toBe("6 15");
  });
});

const ANIMALES = `
rune Animal
  nombre: string

  constructor(nombre: string)

enchanting Animal
  hablar = -> string
    "..."

rune Perro heir Animal
  constructor(nombre: string)
    parent(nombre)

enchanting Perro
  hablar = -> string
    "guau"
`;

describe("F6 herencia", () => {
  test("parent(...) inicializa la base y el despacho es virtual", () => {
    const output = run_source(
      "dispatch",
      `invoke "std/io"
${ANIMALES}
presentar = (a: ref<Animal>) -> void
  io::println("#{a.nombre}: #{a.hablar()}")

main = ->
  presentar(ref<Animal>(ref(Perro("Toby"))))
`,
    );
    expect(output.trim()).toBe("Toby: guau");
  });

  test("un ref<Animal> no se toma implícitamente de un ref<Perro>", () => {
    const found = codes(`
${ANIMALES}
main = ->
  d = Perro("Toby")
  a: ref<Animal> = ref(d)
`);
    expect(found).toContain(CODES.type_mismatch);
  });

  test("un campo heredado no se puede sombrear", () => {
    const found = codes(`
rune Animal
  nombre: string

rune Perro heir Animal
  nombre: string
`);
    expect(found).toContain(CODES.field_shadow);
  });
});

describe("F6 enchanting sobre omens y aliases", () => {
  test("métodos de un omen y de un echo", () => {
    const output = run_source(
      "omen_echo",
      `invoke "std/io"

omen Color
  Rojo, Verde

enchanting Color
  nombre = -> string
    match @
      when Rojo then "rojo"
      when Verde then "verde"

echo Metros = double

enchanting Metros
  doble = -> double
    @ * 2

main = ->
  c = Color::Verde
  d: Metros = 2.5
  io::println("#{c.nombre()} #{d.doble()}")
`,
    );
    expect(output.trim()).toBe("verde 5");
  });

  test("un echo no admite operadores", () => {
    const found = codes(`
echo Metros = double

enchanting Metros
  operator + = (otro: Metros) -> Metros
    @ + otro

main = ->
  pass
`);
    expect(found).toContain(CODES.invalid_operator);
  });

  test("un operador libre que duplica al de la rune es un error", () => {
    const found = codes(`
${PUNTO}

operator + = (a: Punto, b: Punto) -> Punto
  Punto(a.x + b.x, a.y + b.y)

main = ->
  pass
`);
    expect(found).toContain(CODES.invalid_operator);
  });
});

describe("F6 Ordering", () => {
  test("is_lt, reverse y comparación con Ordering::Less", () => {
    const output = run_source(
      "ordering",
      `invoke "std/io"

main = ->
  o = 3 <=> 5
  io::println("#{o.is_lt()} #{o.reverse()} #{o == Ordering::Less}")
`,
    );
    expect(output.trim()).toBe("true greater true");
  });

  test("un <=> de usuario devuelve Ordering", () => {
    const output = run_source(
      "ordering_user",
      `invoke "std/io"

seal Metros = double

enchanting Metros
  operator <=> = (otro: Metros) -> Ordering
    @ <=> (otro as double)

main = ->
  a = Metros(1.0)
  b = Metros(2.0)
  o = a <=> b
  io::println("#{o.is_lt()}")
`,
    );
    expect(output.trim()).toBe("true");
  });
});
