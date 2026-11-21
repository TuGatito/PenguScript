// Regresiones de la fase F7: préstamos, `mut` y `unsafe`.

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
  const dir = mkdtempSync(join(tmpdir(), `pengu_f7_${name}_`));
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

describe("F7 ley de exclusividad", () => {
  test("mutar mientras hay un préstamo activo es un error", () => {
    const found = codes(`
main = ->
  mut n = 1
  r = ref(n)
  n = 2
`);
    expect(found).toContain(CODES.exclusive_borrow);
  });

  test("un bloque do cierra el préstamo", () => {
    const output = run_source(
      "do_borrow",
      `invoke "std/io"

main = ->
  mut n = 1
  do
    r = ref(n)
    io::println("#{r}")
  n = 2
  io::println("#{n}")
`,
    );
    expect(output.trim()).toBe("1\n2");
  });

  test("mutar el contenedor mientras se recorre es un error", () => {
    const found = codes(`
main = ->
  mut xs = [1, 2, 3]
  for x in xs
    xs.push(x)
`);
    expect(found).toContain(CODES.exclusive_borrow);
  });
});

describe("F7 contrato mut", () => {
  test("mut en la llamada modifica la variable", () => {
    const output = run_source(
      "mut_call",
      `invoke "std/io"

incrementar = (mut n: int) -> void
  n += 1

main = ->
  mut n = 1
  incrementar(mut n)
  io::println("#{n}")
`,
    );
    expect(output.trim()).toBe("2");
  });

  test("un parámetro mut exige llamarlo con mut", () => {
    const found = codes(`
incrementar = (mut n: int) -> void
  n += 1

main = ->
  mut n = 1
  incrementar(n)
`);
    expect(found).toContain(CODES.mutable_required);
  });

  test("mut sobre un parámetro que no lo declara es un error", () => {
    const found = codes(`
doble = (n: int) -> int
  n * 2

main = ->
  mut n = 1
  x = doble(mut n)
`);
    expect(found).toContain(CODES.mutable_required);
  });

  test("un binding inmutable no muta campos ni llama a métodos mut", () => {
    const found = codes(`
rune Punto
  x: int

  constructor(x: int)

enchanting Punto
  mut mover = -> void
    @x += 1

main = ->
  p = Punto(1)
  p.x = 2
  p.mover()
`);
    expect(found.filter((code) => code === CODES.mutable_required).length).toBe(2);
  });
});

describe("F7 movimiento", () => {
  test("usar una variable después de moverla es un error", () => {
    const found = codes(`
rune Caja
  valor: int

consumir = (c: unique<Caja>) -> int
  c.valor

main = ->
  caja = unique<Caja>(Caja{valor: 1})
  consumir(caja)
  x = caja.valor
`);
    expect(found).toContain(CODES.use_after_move);
  });
});

describe("F7 unsafe", () => {
  test("desreferenciar raw fuera de unsafe es un error", () => {
    const found = codes(`
main = ->
  p: raw<int> = nullptr
  x = *p
`);
    expect(found).toContain(CODES.unsafe_required);
  });

  test("static mut solo se toca en unsafe", () => {
    const found = codes(`
static mut contador = 0

main = ->
  contador = 1
  x = contador
`);
    expect(found.filter((code) => code === CODES.unsafe_required).length).toBe(2);
  });

  test("raw, lectura y unsafe funcionan juntos", () => {
    const output = run_source(
      "unsafe_raw",
      `invoke "std/io"

unsafe leer = (p: raw<int>) -> int
  *p

static mut contador = 40

main = ->
  mut valor = 2
  unsafe
    r = raw<int>(ref(valor))
    contador += 1
    io::println("#{leer(r) + contador}")
`,
    );
    expect(output.trim()).toBe("43");
  });

  test("llamar a una función unsafe desde código seguro es un error", () => {
    const found = codes(`
unsafe borrar = (p: raw<int>) -> void
  *p = 0

main = ->
  p: raw<int> = nullptr
  borrar(p)
`);
    expect(found).toContain(CODES.unsafe_required);
  });

  test("get_unchecked exige unsafe", () => {
    const found = codes(`
main = ->
  xs = [1, 2, 3]
  x = xs.get_unchecked(1)
`);
    expect(found).toContain(CODES.unsafe_required);
  });
});
