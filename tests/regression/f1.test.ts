// Regresiones de la fase F1: BOM, asignaciones, `static mut`,
// `then` con bloque, defaults, Display y avisos del checker.

import { describe, expect, test } from "bun:test";
import { parse_text } from "../../src/frontend/parser.ts";
import { check_program } from "../../src/semantic/checker.ts";
import { make_sink } from "../../src/diagnostics/sink.ts";
import type { Diagnostic } from "../../src/diagnostics/diagnostic.ts";
import { CODES } from "../../src/diagnostics/codes.ts";
import { lex_text } from "../../src/frontend/lexer.ts";

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

describe("F1 · BOM y palabras clave", () => {
  test("un BOM al inicio no rompe `invoke`", () => {
    const text = "\uFEFFinvoke \"std/io\"\n\nmain = ->\n  io::println(\"hola\")\n";
    const parsed = parse_text("test.pengu", text);
    expect(parsed.diagnostics).toEqual([]);
    expect(parsed.program.decls[0]?.kind).toBe("invoke_decl");
  });

  test("una palabra clave capitalizada sugiere la minúscula", () => {
    const diagnostics = parse_and_check("Invoke \"std/io\"\n\nmain = ->\n  pass\n");
    expect(diagnostics.map((item) => item.code)).toContain(CODES.invalid_declaration);
    expect(diagnostics[0]?.message).toContain("¿quisiste decir «invoke»?");
  });
});

describe("F1 · declaraciones", () => {
  test("`static mut` se analiza", () => {
    const diagnostics = parse_and_check("static mut velocidad = 0\n\nmain = ->\n  pass\n");
    expect(diagnostics).toEqual([]);
  });

  test("`static` sin `mut` avisa", () => {
    const diagnostics = parse_and_check("static velocidad = 0\n\nmain = ->\n  pass\n");
    expect(diagnostics.map((item) => item.code)).toContain(CODES.invalid_declaration);
  });

  test("`then` acepta un bloque indentado", () => {
    const text = `main = ->
  if true then
    io::println("sí")
`;
    expect(codes(text)).toEqual([]);
  });
});

describe("F1 · valores por defecto", () => {
  const source = `sumar = (x: int = 100, y: int = x + 1000) -> int
  x + y

main = ->
  pass
`;

  test("llamar con menos argumentos usa los defaults", () => {
    expect(codes(`${source}\nprueba = ->\n  sumar(1)\n`)).toEqual([]);
  });

  test("llamar con demasiados argumentos es E0504", () => {
    const diagnostics = parse_and_check(`${source}\nprueba = ->\n  sumar(1, 2, 3)\n`);
    expect(diagnostics.map((item) => item.code)).toContain(CODES.wrong_arity);
    expect(diagnostics[0]?.message).toContain("entre 0 y 2");
  });

  test("omitir un parámetro obligatorio es E0504", () => {
    const text = `g = (a: int, b: int = 2) -> int
  a + b

main = ->
  g()
`;
    const diagnostics = parse_and_check(text);
    expect(diagnostics.map((item) => item.code)).toContain(CODES.wrong_arity);
    expect(diagnostics[0]?.message).toContain("entre 1 y 2");
  });
});

describe("F1 · asignaciones que antes daban E0501 falso", () => {
  const cases: readonly (readonly [string, string])[] = [
    ["opcional con none", "x: int? = none"],
    ["puntero raw nulo", "p: raw<int> = nullptr"],
    ["entero ancho", "x: long long = 1"],
    ["entero con signo estrecho", "a: signed char = 1"],
    ["pair desde tupla", "p: pair<int, int> = (1, 2)"],
    ["tuple desde tupla", "t: tuple<int, string> = (1, \"a\")"],
  ];

  for (const [name, declaration] of cases) {
    test(name, () => {
      expect(codes(`main = ->\n  ${declaration}\n  pass\n`)).toEqual([]);
    });
  }

  test("un literal que no cabe en el tipo sí es error", () => {
    const diagnostics = parse_and_check("main = ->\n  x: signed char = 200\n  pass\n");
    expect(diagnostics.map((item) => item.code)).toContain(CODES.type_mismatch);
  });

  test("asignar un double a un int sigue siendo error", () => {
    const diagnostics = parse_and_check("main = ->\n  x: int = 2.5\n  pass\n");
    expect(diagnostics.map((item) => item.code)).toContain(CODES.type_mismatch);
  });
});

describe("F1 · Display en interpolaciones", () => {
  test("un rune sin `to_string` no se puede interpolar", () => {
    const text = `rune Punto
  x: int

main = ->
  p = Punto(1)
  io::println("p = #{p}")
`;
    const diagnostics = parse_and_check(text);
    expect(diagnostics.map((item) => item.code)).toContain(CODES.not_display);
  });

  test("con `to_string` sí se puede", () => {
    const text = `rune Punto
  x: int

enchanting Punto
  to_string = -> string
    "punto"

main = ->
  p = Punto(1)
  io::println("p = #{p}")
`;
    expect(codes(text)).toEqual([]);
  });
});

describe("F1 · avisos del switch", () => {
  test("un switch sin else sobre un omen avisa de variantes sin cubrir", () => {
    const text = `omen Color
  Red, Green

main = ->
  c = Color::Red
  switch c
    when Color::Red then 1
`;
    const warnings = parse_and_check(text).filter((item) => item.severity === "warning");
    expect(warnings.map((item) => item.code)).toContain(CODES.omen_not_exhaustive);
  });

  test("con else no avisa", () => {
    const text = `omen Color
  Red, Green

main = ->
  c = Color::Red
  switch c
    when Color::Red then 1
    else 2
`;
    expect(parse_and_check(text).filter((item) => item.severity === "warning")).toEqual([]);
  });
});

describe("F1 · indentación", () => {
  test("E0101 explica el nivel esperado y ofrece un arreglo", () => {
    const text = "main = ->\n    x = 1\n  y = 2\n";
    const lexed = lex_text("test.pengu", text);
    const diagnostic = lexed.diagnostics.find((item) => item.code === CODES.indent_mismatch);
    expect(diagnostic).toBeDefined();
    expect(diagnostic?.notes.join(" ")).toContain("la sangría más cercana es 4");
    expect(diagnostic?.fix?.replacement).toBe("    ");
  });
});
