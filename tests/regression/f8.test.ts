// Regresiones de la fase F8: módulos, constantes y evaluación.

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
import { load_graph } from "../../src/project/module_graph.ts";

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

function run_project(name: string, files: Readonly<Record<string, string>>): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_f8_${name}_`));
  writeFileSync(join(dir, "pengu.toml"), '[package]\nname = "f8"\n');
  for (const [file, source] of Object.entries(files)) writeFileSync(join(dir, file), source);
  const result = compile_file(join(dir, "main.pengu"));
  if (!result.ok) {
    throw new Error(result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output);
  }
  const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout;
}

describe("F8 constantes", () => {
  test("las constantes se evalúan y se ordenan por dependencia", () => {
    const output = run_project("consts", {
      "main.pengu": `invoke "std/io"

const TOTAL = BASE + 5
const BASE = 10

main = ->
  io::println("#{TOTAL} #{BASE}")
`,
    });
    expect(output.trim()).toBe("15 10");
  });

  test("static mut exige un valor const-evaluable", () => {
    const found = codes(`
hacer = -> int
  1

static mut x = hacer()
`);
    expect(found).toContain(CODES.not_const_evaluable);
  });

  test("static mut con literales y const se emite y muta en unsafe", () => {
    const output = run_project("static_mut", {
      "main.pengu": `invoke "std/io"

const PASO = 2
static mut total = 40

main = ->
  unsafe
    total += PASO
    io::println("#{total}")
`,
    });
    expect(output.trim()).toBe("42");
  });

  test("una const con atomic es mutable por dentro", () => {
    const output = run_project("atomic", {
      "main.pengu": `invoke "std/io"

const CONTADOR = atomic<int>(0)

main = ->
  CONTADOR.fetch_add(1)
  CONTADOR.fetch_add(2)
  io::println("#{CONTADOR.load()}")
`,
    });
    expect(output.trim()).toBe("3");
  });
});

describe("F8 realms reabiertos", () => {
  test("dos archivos comparten el realm y se accede por su nombre", () => {
    const output = run_project("reopen", {
      "geo.pengu": "realm geo\n\nsuma = (a: int, b: int) -> int\n  a + b\n",
      "escala.pengu": "realm geo\n\ndobla = (n: int) -> int\n  n * 2\n",
      "main.pengu": `invoke "std/io"
invoke "./geo"
invoke "./escala"

main = ->
  io::println("#{geo::suma(1, 2)} #{geo::dobla(4)}")
`,
    });
    expect(output.trim()).toBe("3 8");
  });

  test("los tipos se comparten entre archivos del mismo realm", () => {
    const output = run_project("reopen_types", {
      "geo.pengu": "realm geo\n\nrune Punto\n  x: int\n  y: int\n",
      "suma.pengu": "realm geo\n\nsuma = (p: Punto) -> int\n  p.x + p.y\n",
      "main.pengu": `invoke "std/io"
invoke "./geo"
invoke "./suma"

main = ->
  p = geo::Punto(3, 4)
  io::println("#{geo::suma(p)}")
`,
    });
    expect(output.trim()).toBe("7");
  });

  test("un tipo duplicado en el mismo realm es un error", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_f8_dup_"));
    writeFileSync(join(dir, "pengu.toml"), '[package]\nname = "f8"\n');
    writeFileSync(join(dir, "a.pengu"), "realm geo\n\nrune Punto\n  x: int\n");
    writeFileSync(join(dir, "b.pengu"), "realm geo\n\nrune Punto\n  y: int\n");
    writeFileSync(
      join(dir, "main.pengu"),
      'invoke "std/io"\ninvoke "./a"\ninvoke "./b"\n\nmain = -> void\n',
    );
    const graph = load_graph(join(dir, "main.pengu"));
    expect(graph.diagnostics.map((item) => item.code)).toContain(CODES.realm_duplicate);
  });
});
