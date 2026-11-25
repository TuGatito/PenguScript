// F1: coerción de literales y constantes.
//
// Un literal cuyo valor cabe en el destino no necesita `::from`; una
// variable, aunque su valor quepa en ejecución, sigue exigiendo la
// conversión explícita.

import { describe, expect, test } from "bun:test";
import { parse_text } from "../../src/frontend/parser.ts";
import { check_program } from "../../src/semantic/checker.ts";
import { make_sink } from "../../src/diagnostics/sink.ts";

function check(text: string): readonly string[] {
  const parsed = parse_text("test.pengu", text);
  const sink = make_sink({ max: 100 });
  for (const diagnostic of parsed.diagnostics) sink.add(diagnostic);
  check_program("test.pengu", parsed.program, sink);
  return sink.diagnostics.map((item) => item.code);
}

const PRELUDE = `rune Color
  r: uint8_t
  g: uint8_t
  b: uint8_t
  a: uint8_t

pinta = (estado: uint32_t) -> uint32_t
  estado

escala = (factor: float) -> float
  factor

`;

describe("coerción de literales", () => {
  test("los literales caben en los campos de un rune", () => {
    expect(check(`${PRELUDE}main = -> void
  c = Color(255, 0, 0, 255)
  _ = c.r
`)).toEqual([]);
  });

  test("un literal entero cabe en un parámetro de otro ancho y signo", () => {
    expect(check(`${PRELUDE}main = -> void
  a = pinta(64)
  b = pinta(4294967295)
  _ = a
`)).toEqual([]);
  });

  test("un literal decimal cabe en float", () => {
    expect(check(`${PRELUDE}main = -> void
  a = escala(0.5)
  b = escala(2)
  _ = a
`)).toEqual([]);
  });

  test("una constante entera evaluable también cabe", () => {
    expect(check(`${PRELUDE}const FLAG: int = 0x40

main = -> void
  a = pinta(FLAG)
  b = Color(FLAG, 0, 0, 0)
  _ = a
`)).toEqual([]);
  });

  test("un literal fuera de rango se rechaza", () => {
    expect(check(`${PRELUDE}main = -> void
  c = Color(256, 0, 0, 0)
  _ = c.r
`)).toContain("E0501");
  });

  test("un literal negativo no cabe en un entero sin signo", () => {
    expect(check(`${PRELUDE}main = -> void
  a = pinta(-1)
  _ = a
`)).toContain("E0501");
  });

  test("una constante negativa tampoco cabe en unsigned", () => {
    expect(check(`${PRELUDE}const NEG: int = -1

main = -> void
  a = pinta(NEG)
  _ = a
`)).toContain("E0501");
  });

  test("una variable no se convierte sola", () => {
    expect(check(`${PRELUDE}main = -> void
  mut n = 5
  a = pinta(n)
  _ = a
`)).toContain("E0501");
  });

  test("un literal cabe en un parámetro uint64_t", () => {
    expect(check(`dobla = (x: uint64_t) -> uint64_t
  x

main = -> void
  a = dobla(21)
  _ = a
`)).toEqual([]);
  });
});
