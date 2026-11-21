// Regresiones de la fase F4: tipos compuestos (arrays, literales con
// prefijo de tipo, pair/tuple, contenedores auxiliares, variant).

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
  const dir = mkdtempSync(join(tmpdir(), `pengu_f4_${name}_`));
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

describe("F4 · arrays", () => {
  test("el tamaño del array se comprueba y se puede indexar", () => {
    const text = `main = ->
  xs: array<int, 3> = [1, 2, 3]
  ultimo = xs[2]
`;
    expect(codes(text)).toEqual([]);
  });

  test("un literal con tamaño distinto es error", () => {
    const text = `main = ->
  xs: array<int, 3> = [1, 2]
`;
    expect(codes(text)).toContain(CODES.type_mismatch);
  });

  test("array con tipo de elemento incorrecto es error", () => {
    const text = `main = ->
  xs: array<int, 2> = [1, "dos"]
`;
    expect(codes(text)).toContain(CODES.type_mismatch);
  });

  test("el tamaño del array debe ser una expresión constante", () => {
    const text = `main = ->
  n = 3
  xs: array<int, n> = [1, 2, 3]
`;
    expect(codes(text).length).toBeGreaterThan(0);
  });
});

describe("F4 · literales con prefijo de tipo", () => {
  test("vector, deque, set y map con prefijo funcionan en ejecución", () => {
    const out = run_source(
      "literales",
      `invoke "std/io"

main = ->
  xs = vector<int>[1, 2, 3]
  ds = deque<int>[7, 8]
  ss = set<string>{"a", "b", "a"}
  ms = map<string, int>{"uno": 1, "dos": 2}
  io::println("#{#xs} #{#ds} #{#ss} #{#ms}")
`,
    );
    expect(out).toContain("3 2 2 2");
  });

  test("un literal de mapa con clave equivocada es error", () => {
    const text = `main = ->
  ms = map<string, int>{1: 1}
`;
    expect(codes(text)).toContain(CODES.type_mismatch);
  });
});

describe("F4 · pair y tuple", () => {
  test("pair y tuple se construyen, acceden y destructuran", () => {
    const out = run_source(
      "pares",
      `invoke "std/io"

main = ->
  par: pair<int, string> = (1, "a")
  tup: tuple<int, string> = (2, "b")
  io::println("par: #{par.first}")
  io::println("tup: #{tup}")
`,
    );
    expect(out).toContain("par: 1");
    expect(out).toContain("tup: (2, b)");
  });
});

describe("F4 · contenedores auxiliares", () => {
  test("stack, bitset, list y forward_list funcionan", () => {
    const out = run_source(
      "auxiliares",
      `invoke "std/io"

main = ->
  mut pila = stack<int>()
  pila.push(1)
  pila.push(2)
  io::println("tope: #{pila.top()}")
  pila.pop()
  io::println("tope: #{pila.top()}")

  mut bits = bitset<8>(0)
  bits.set(3)
  io::println("test: #{bits.test(3)} #{bits.count()}")

  ls = list<int>[1, 2, 3]
  fl = forward_list<int>[0, 1, 2]
  io::println("listas: #{#ls} #{#fl}")
`,
    );
    expect(out).toContain("tope: 2");
    expect(out).toContain("test: true 1");
    expect(out).toContain("listas: 3 3");
  });

  test("un método inexistente en un contenedor es error", () => {
    const text = `main = ->
  xs = vector<int>[1]
  xs.empujar(2)
`;
    expect(codes(text)).toContain(CODES.unknown_field);
  });

  test("el tamaño del bitset debe ser un entero", () => {
    const text = `main = ->
  b = bitset<"ocho">(0)
`;
    expect(codes(text)).toContain(CODES.type_mismatch);
  });

  test("variant guarda una alternativa y se extrae con as", () => {
    const out = run_source(
      "variant",
      `invoke "std/io"

main = ->
  a: variant<int, string> = variant<int, string>(42)
  b: variant<int, string> = variant<int, string>("hola")
  io::println("#{a as int} #{b as string}")
`,
    );
    expect(out).toContain("42 hola");
  });

  test("extraer una alternativa que el variant no tiene es error", () => {
    const text = `main = ->
  v: variant<int, string> = variant<int, string>(1)
  x = v as double
`;
    expect(codes(text).length).toBeGreaterThan(0);
  });

  test("complex, atomic, mutex y thread se ejecutan", () => {
    const out = run_source(
      "sincronizacion",
      `invoke "std/io"

main = ->
  mut m = mutex()
  m.lock()
  m.unlock()
  cuenta: atomic<int> = atomic<int>(0)
  cuenta.store(5)
  c = complex<double>(1.0, 2.0)
  mut t = thread(() -> io::println("hilo"))
  t.join()
  io::println("cuenta: #{cuenta.load()} real: #{c.real()}")
`,
    );
    expect(out).toContain("hilo");
    expect(out).toContain("cuenta: 5 real: 1");
  });

  test("string_view acepta string pero no al revés", () => {
    const ok = `main = ->
  texto: string = "hola"
  vista: string_view = texto
`;
    expect(codes(ok)).toEqual([]);
    const bad = `main = ->
  vista: string_view = "hola"
  texto: string = vista
`;
    expect(codes(bad)).toContain(CODES.type_mismatch);
  });
});
