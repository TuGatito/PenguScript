// Regresiones de la auditoría de la stdlib (fase F0 del plan).
//
// Cada prueba cubre un fallo real reproducido: métodos anunciados por el
// checker que emitían C++ inválido, o que no respetaban el contrato del
// cheatsheet.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function compile_source(name: string, source: string) {
  const dir = mkdtempSync(join(tmpdir(), `pengu_bug_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  return compile_file(file);
}

function run_source(name: string, source: string): string {
  const result = compile_source(name, source);
  if (!result.ok) {
    throw new Error(
      result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output,
    );
  }
  const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout;
}

describe("regresiones de la stdlib", () => {
  test("los miembros de contenedores emiten el C++ correcto", () => {
    const out = run_source(
      "containers",
      `invoke "std/io"
invoke "std/vector"
invoke "std/map"
invoke "std/set"
invoke "std/string"

main = ->
  mut xs: vector<int> = [1, 2, 3]
  io::println("pop: #{xs.pop()}")
  io::println("remove_at: #{xs.remove_at(0)}")
  xs.insert(1, 99)
  io::println("insert: #{xs}")
  io::println("remove: #{xs.remove(99)} #{xs}")

  mut m: map<string, int> = {"a": 1, "b": 2}
  io::println("asignar de nuevo: #{m.insert_or_assign("a", 10)}")
  io::println("claves: #{m.keys()}")
  io::println("valores: #{m.values()}")
  io::println("remove clave: #{m.remove("a").value()}")

  mut s: set<int> = set{1, 2}
  io::println("set remove: #{s.remove(2)} #{s}")

  io::println("find: #{"hola mundo".find("mundo").value()}")
`,
    );
    expect(out).toContain("pop: 3");
    expect(out).toContain("remove_at: 1");
    expect(out).toContain("insert: [2, 99]");
    expect(out).toContain("remove: true [2]");
    expect(out).toContain("asignar de nuevo: false");
    expect(out).toContain("claves: [a, b]");
    expect(out).toContain("valores: [10, 2]");
    expect(out).toContain("remove clave: 10");
    expect(out).toContain("set remove: true {1}");
    expect(out).toContain("find: 5");
  });

  test("first/last/insert de set funcionan sin importar std/vector", () => {
    const out = run_source(
      "builtins",
      `invoke "std/io"

main = ->
  v: vector<int> = [7, 8, 9]
  io::println("first: #{v.first()}")
  io::println("last: #{v.last()}")
  mut s: set<string> = set{"a"}
  io::println("insert: #{s.insert("b")} #{s.insert("a")}")
`,
    );
    expect(out).toContain("first: 7");
    expect(out).toContain("last: 9");
    expect(out).toContain("insert: true false");
  });

  test("shared admite métodos mut y pop panica en vacío", () => {
    const ok = run_source(
      "shared",
      `invoke "std/io"
invoke "std/memory"

main = ->
  p = shared<int>(41)
  p.set(42)
  io::println("shared: #{p.get()}")
`,
    );
    expect(ok).toContain("shared: 42");

    const empty = compile_source(
      "pop_vacio",
      `invoke "std/io"

main = ->
  mut xs: vector<int> = []
  io::println("no se imprime: #{xs.pop()}")
`,
    );
    expect(empty.ok).toBe(true);
    const run = spawnSync(empty.binary_path ?? "", [], { encoding: "utf8" });
    expect(run.status).not.toBe(0);
    expect(run.stderr).toContain("pop() sobre un contenedor vacío");
  });

  test("array no admite cambios estructurales", () => {
    const result = compile_source(
      "array",
      `main = ->
  v: array<int, 2> = [1, 2]
  v.push(3)
`,
    );
    expect(result.ok).toBe(false);
    expect(result.diagnostics.length).toBeGreaterThan(0);
  });

  test("format::fixed/scientific/radix controlan la precisión", () => {
    const out = run_source(
      "formato",
      `invoke "std/io"
invoke "std/format"

main = ->
  io::println(format::fixed(1.0 / 3.0, 4))
  io::println(format::fixed(2.5, 0))
  io::println(format::scientific(1234.5, 2))
  io::println(format::radix(255, 16))
  io::println(format::radix(-255, 16))
  io::println(format::radix(5, 2))
`,
    );
    expect(out).toContain("0.3333");
    expect(out).toContain("2");
    expect(out).toContain("1.23e+03");
    expect(out).toContain("ff");
    expect(out).toContain("-ff");
    expect(out).toContain("101");
  });

  test("un método de rune con valor por defecto se puede omitir", () => {
    const out = run_source(
      "defaults",
      `invoke "std/io"
realm prueba

rune Caja
  valor: int

enchanting Caja
  escala = (factor: int = 3) -> int
    @.valor * factor

main = ->
  c = Caja(2)
  io::println("sin args: #{c.escala()}")
  io::println("con args: #{c.escala(5)}")
`,
    );
    expect(out).toContain("sin args: 6");
    expect(out).toContain("con args: 10");
  });

  test("dos métodos con el mismo nombre en un rune son un error", () => {
    const result = compile_source(
      "duplicado",
      `realm prueba

rune Caja
  valor: int

enchanting Caja
  doble = -> int
    @.valor * 2
  doble = (k: int) -> int
    @.valor * k

main = ->
  0
`,
    );
    expect(result.ok).toBe(false);
    expect(result.diagnostics.some((item) => item.code === "E0707")).toBe(true);
  });
});
