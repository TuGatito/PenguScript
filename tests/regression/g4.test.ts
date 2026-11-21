// Regresiones de la fase G4: módulos `std/*.pengu` que enhechizan los
// tipos incorporados (texto, secuencias, colecciones, opcionales y números).

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse_text } from "../../src/frontend/parser.ts";
import { check_program } from "../../src/semantic/checker.ts";
import { make_sink } from "../../src/diagnostics/sink.ts";
import type { Diagnostic } from "../../src/diagnostics/diagnostic.ts";
import { compile_file } from "../../src/driver/compile.ts";
import { analyze_graph } from "../../src/driver/analyze.ts";
import { spawnSync } from "node:child_process";

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
  const dir = mkdtempSync(join(tmpdir(), "pengu_g4_proj_"));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const sink = make_sink({ max: 100 });
  analyze_graph(file, sink);
  return sink.diagnostics.map((item) => item.code);
}

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_g4_${name}_`));
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

describe("G4 std/string", () => {
  test("métodos de texto", () => {
    const output = run_source("string", `
invoke "std/io"
invoke "std/string"
invoke "std/vector"
invoke "std/optional"

main = ->
  texto = "  Hola, Mundo  "
  limpio = texto.trim()
  io::println(limpio.compare("Hola, Mundo"))
  io::println(limpio.compare("Zzz"))
  io::println(limpio.starts_with("Hola"))
  io::println(limpio.ends_with("Mundo"))
  io::println(limpio.to_upper())
  io::println("a,b".split(",").join("-"))
  io::println("ab".repeat(3))
  io::println(limpio.find("Mundo").or_else(0))
`);
    expect(output).toBe("0\n-1\ntrue\ntrue\nHOLA, MUNDO\na-b\nababab\n6\n");
  });
});

describe("G4 std/vector y std/array", () => {
  test("vector completo", () => {
    const output = run_source("vector", `
invoke "std/io"
invoke "std/vector"
invoke "std/optional"

main = ->
  mut xs = [3, 1, 2]
  io::println(xs.first().or_else(0))
  io::println(xs.last().or_else(0))
  io::println(xs.index_of(1).or_else(99))
  io::println(xs.contains(2))
  io::println(xs.join(","))
  xs.sort()
  io::println(xs.join(","))
  xs.reverse()
  io::println(xs.join(","))
`);
    expect(output).toBe("3\n2\n1\ntrue\n3,1,2\n1,2,3\n3,2,1\n");
  });

  test("array sin tamaño en el patrón", () => {
    const output = run_source("array", `
invoke "std/io"
invoke "std/array"
invoke "std/optional"

main = ->
  xs: array<int, 3> = [7, 8, 9]
  io::println(xs.first().or_else(0))
  io::println(xs.last().or_else(0))
  io::println(xs.contains(8))
`);
    expect(output).toBe("7\n9\ntrue\n");
  });
});

describe("G4 std/map y std/set", () => {
  test("claves, valores y unión", () => {
    const output = run_source("colecciones", `
invoke "std/io"
invoke "std/map"
invoke "std/set"
invoke "std/vector"

main = ->
  precios = {"pan": 2, "leche": 3}
  io::println(#precios)
  io::println(precios.contains_key("pan"))
  io::println(#precios.keys_list())
  mut letras = set{"a", "b"}
  otras = set{"b", "c"}
  letras = letras.union(ref(otras))
  io::println(#letras)
  io::println(letras.to_vector().join(""))
`);
    expect(output).toBe("2\ntrue\n2\n3\nabc\n");
  });
});

describe("G4 std/optional, std/pair y std/tuple", () => {
  test("opcionales, pares y tuplas", () => {
    const output = run_source("opcionales", `
invoke "std/io"
invoke "std/optional"
invoke "std/pair"
invoke "std/tuple"
invoke "std/vector"
invoke "std/int"

es_par = (n: int) -> bool
  n.is_even()

main = ->
  xs = [1, 3]
  io::println(xs.first().or_else(0))
  io::println(xs.first().filter(es_par).or_else(-1))
  io::println(#xs.first().to_vector())
  par: pair<int, string> = (1, "uno")
  invertido = par.swap()
  io::println("#{invertido.first}#{invertido.second}")
  trio: tuple<int, string, bool> = (5, "cinco", true)
  io::println(trio.len())
  io::println(trio.third())
`);
    expect(output).toBe("1\n-1\n1\nuno1\n3\ntrue\n");
  });
});

describe("G4 std/int, std/double y std/ordering", () => {
  test("métodos numéricos", () => {
    const output = run_source("numeros", `
invoke "std/io"
invoke "std/int"
invoke "std/double"
invoke "std/ordering"
invoke "std/optional"

main = ->
  numero = -7
  io::println(numero.abs())
  io::println(numero.clamp(-5, 5))
  io::println(numero.sign())
  io::println(6.is_even())
  io::println(6.is_odd())
  io::println(3.to_double())
  io::println(2.5.max(4.0))
  io::println(9.9.to_int().or_else(0))
  io::println(Ordering::Less.then(Ordering::Equal))
`);
    expect(output).toBe("7\n-5\n-1\ntrue\nfalse\n3\n4\n9\nless\n");
  });

  test("un método enhechizado no existe para otro tipo", () => {
    const found = project_codes(`
invoke "std/string"

main = ->
  x = 42
  io::println(x.starts_with("4"))
`);
    expect(found).toContain("E0506");
  });

  test("aridad incorrecta del método enhechizado", () => {
    const found = project_codes(`
invoke "std/string"

main = ->
  s = "hola"
  io::println(s.compare())
`);
    expect(found).toContain("E0501");
  });
});
