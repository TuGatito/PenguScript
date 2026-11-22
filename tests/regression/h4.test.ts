// Regresiones de la fase H4: `string.get`/`string.pop` y las operaciones
// de conjuntos en `std/set`.

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
  const dir = mkdtempSync(join(tmpdir(), "pengu_h4_proj_"));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const sink = make_sink({ max: 100 });
  analyze_graph(file, sink);
  return sink.diagnostics.map((item) => item.code);
}

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_h4_${name}_`));
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

describe("H4 string.get y string.pop", () => {
  test("get devuelve el carácter o none", () => {
    const output = run_source(
      "get",
      `invoke "std/io"
invoke "std/string"

main = ->
  s = "hola"
  io::println("#{s.get(1)}")
  io::println("#{s.get(9).is_none()}")
`,
    );
    expect(output.trim()).toBe("o\ntrue");
  });

  test("pop quita y devuelve el último carácter", () => {
    const output = run_source(
      "pop",
      `invoke "std/io"
invoke "std/string"

main = ->
  mut s = "hola"
  io::println("#{s.pop()}")
  io::println("#{s}")
  io::println("#{s.pop()} #{s.pop()} #{s.pop()}")
  io::println("#{s.pop().is_none()}")
`,
    );
    expect(output.trim()).toBe("a\nhol\nl o h\ntrue");
  });

  test("pop en una cadena constante no compila", () => {
    const found = project_codes(`
invoke "std/string"
main = ->
  io::println("#{"hola".pop()}")
`);
    expect(found).toContain("E0406");
  });
});

describe("H4 operaciones de conjuntos", () => {
  test("intersección, diferencia, diferencia simétrica y subconjunto", () => {
    const output = run_source(
      "set_ops",
      `invoke "std/io"
invoke "std/set"

main = ->
  a = set{1, 2, 3, 4}
  b = set{3, 4, 5}
  io::println("#{a.intersection(ref(b))}")
  io::println("#{a.difference(ref(b))}")
  io::println("#{a.symmetric_difference(ref(b))}")
  io::println("#{set{1, 2}.is_subset(ref(a))}")
  io::println("#{a.is_subset(ref(set{1, 2}))}")
`,
    );
    expect(output.trim()).toBe("{3, 4}\n{1, 2}\n{1, 2, 5}\ntrue\nfalse");
  });
});

describe("H4 asignar al receptor", () => {
  test("un método mut puede reasignar @", () => {
    const output = run_source(
      "self_assign",
      `invoke "std/io"
invoke "std/string"

enchanting string
  mut vaciar = -> void
    @ = ""

main = ->
  mut s = "hola"
  s.vaciar()
  io::println("[#{s}]")
`,
    );
    expect(output.trim()).toBe("[]");
  });

  test("`@ =` en un método const no compila", () => {
    const found = codes(`
enchanting string
  malo = -> void
    @ = ""
`);
    expect(found).toContain("E0406");
  });
});
