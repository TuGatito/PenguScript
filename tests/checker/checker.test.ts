import { describe, expect, test } from "bun:test";
import { parse_text } from "../../src/frontend/parser.ts";
import { check_program } from "../../src/semantic/checker.ts";
import { make_sink } from "../../src/diagnostics/sink.ts";
import type { ModuleInfo } from "../../src/semantic/module_info.ts";

interface Checked {
  readonly codes: readonly string[];
  readonly module: ModuleInfo;
}

function check(text: string): Checked {
  const parsed = parse_text("test.pengu", text);
  const sink = make_sink({ max: 100 });
  for (const diagnostic of parsed.diagnostics) sink.add(diagnostic);
  const module = check_program("test.pengu", parsed.program, sink);
  return { codes: sink.diagnostics.map((item) => item.code), module };
}

function expect_ok(text: string): Checked {
  const result = check(text);
  expect(result.codes).toEqual([]);
  return result;
}

function expect_code(text: string, code: string): void {
  const result = check(text);
  expect(result.codes).toContain(code);
}

describe("posesión", () => {
  test("pasar un unique lo mueve y usar el origen es E0601", () => {
    expect_code(
      `invoke "std/io"

rune Node
  value: int

consumir = (n: unique<Node>) -> int
  n.value

main = ->
  const caja = unique<Node>(7)
  const a = consumir(caja)
  io::println("#{caja.value}")
`,
      "E0601",
    );
  });

  test("shared se copia sin mover", () => {
    expect_ok(
      `invoke "std/io"

rune Node
  value: int

leer = (n: shared<Node>) -> int
  n.value

main = ->
  const nodo = shared<Node>(3)
  const a = leer(nodo)
  const b = leer(nodo)
  io::println("#{a + b}")
`,
    );
  });
});

describe("firmas de la biblioteca estándar", () => {
  test("math::sqrt exige y devuelve double", () => {
    expect_ok(
      `invoke "std/math"

main = ->
  const x: double = math::sqrt(9.0)
  io::println(x)
`,
    );
    expect_code(
      `invoke "std/math"

main = ->
  const x: double = math::sqrt("nueve")
`,
      "E0501",
    );
    expect_code(
      `invoke "std/math"

main = ->
  const x = math::sqrt(9.0, 2.0)
`,
      "E0504",
    );
  });

  test("io::println acepta cualquier número de argumentos", () => {
    expect_ok(
      `invoke "std/io"

main = ->
  io::println("hola")
  io::println(1, 2.5, "tres", true)
`,
    );
  });

  test("un símbolo desconocido del módulo se diagnostica", () => {
    expect_code(
      `invoke "std/math"

main = ->
  const x = math::no_existe(1.0)
`,
      "E0403",
    );
  });
});

describe("checker", () => {
  test("acepta un programa completo", () => {
    expect_ok(
      `const MAX = 10

double_of = (x: int) -> int
  x * 2

rune Point
  x: double
  y: double

enchanting Point
  len = -> double
    @x + @y

main = ->
  p = Point(1.0, 2.0)
  d: double = p.len()
  io::println(double_of(3))
`,
    );
  });

  test("detecta un tipo incompatible", () => {
    expect_code(`x: int = "hola"\n`, "E0501");
  });

  test("detecta un identificador desconocido", () => {
    expect_code(`main = ->\n  foo_bar()\n`, "E0403");
  });

  test("exige mut para reasignar", () => {
    expect_code(`main = ->\n  y = 1\n  y = 2\n`, "E0406");
  });

  test("acepta la reasignación con mut", () => {
    expect_ok(`main = ->\n  mut y = 1\n  y = 2\n`);
  });

  test("detecta un match no exhaustivo", () => {
    expect_code(
      `omen Color
  Red, Green, Blue

main = (c: Color) -> int
  match c
    when Red then 1
    when Green then 2
`,
      "E0701",
    );
  });

  test("acepta un match exhaustivo", () => {
    expect_ok(
      `omen Color
  Red, Green, Blue

main = (c: Color) -> int
  match c
    when Red then 1
    when Green then 2
    when Blue then 3
`,
    );
  });

  test("detecta una aridad incorrecta", () => {
    expect_code(`f = (x: int) -> int\n  x\n\nmain = ->\n  f(1, 2)\n`, "E0504");
  });

  test("exige unsafe para un cast estrecho", () => {
    expect_code(`main = ->\n  n = 3.5 as int\n`, "E0603");
  });

  test("acepta un cast seguro", () => {
    expect_ok(`main = ->\n  x: double = 3 as double\n`);
  });

  test("la condición debe ser bool", () => {
    expect_code(`main = ->\n  if 3 then 1 else 2\n`, "E0503");
  });

  test("resuelve variantes de omen", () => {
    expect_ok(
      `omen Color
  Red, Green

main = ->
  c: Color = Color::Red
`,
    );
  });

  test("resuelve campos y métodos de runes", () => {
    const result = expect_ok(
      `rune Point
  x: double

enchanting Point
  half = -> double
    @x / 2.0

main = ->
  p = Point(1.0)
  a: double = p.x
  b: double = p.half()
`,
    );
    expect(result.module.env.runes.has("Point")).toBe(true);
  });

  test("acepta bucles y comprensiones", () => {
    expect_ok(
      `main = ->
  mut total = 0
  for i = 0, 10
    total += i
  xs = [1, 2, 3]
  ys = [x * 2 for x in xs]
  n = #ys
`,
    );
  });

  test("el for iterable declara la variable", () => {
    expect_code(`main = ->\n  for x in [1, 2]\n    y = x\n  z = x\n`, "E0403");
  });

  test("detecta un miembro inexistente", () => {
    expect_code(
      `rune Point
  x: double

main = ->
  p = Point(1.0)
  p.z
`,
      "E0506",
    );
  });

  test("detecta retorno incompatible", () => {
    expect_code(`f = (x: int) -> string\n  x\n`, "E0501");
  });
});

describe("negación booleana", () => {
  test("`!` de prefijo niega la expresión y no rompe el bloque siguiente", () => {
    expect_ok(
      `main = -> void
  a = 1
  b = if !(a > 5) then 10 else 20
  c = if !false then 1 else 0
  b + c
`,
    );
  });

  test("`!` de prefijo con una llamada", () => {
    expect_ok(
      `listo = (valor: bool) -> bool
  !valor

main = ->
  if !listo(true)
    1
  else
    2
`,
    );
  });
});
