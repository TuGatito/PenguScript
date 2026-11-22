// Regresiones de la fase H6: enchanting de punteros inteligentes y bindgen
// de funciones C variádicas.

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
  const dir = mkdtempSync(join(tmpdir(), `pengu_h6_${name}_`));
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

describe("H6 enchanting de punteros inteligentes", () => {
  test("unique y shared exponen get/set sobre el valor apuntado", () => {
    const output = run_source(
      "unique_shared",
      `invoke "std/io"
invoke "std/memory"

rune Caja
  valor: int

  constructor(valor: int)

main = ->
  mut u = unique<Caja>(1)
  u.set(Caja(2))
  io::println("u: #{u.get().valor}")

  s = shared<Caja>(7)
  io::println("s: #{s.get().valor}")
`,
    );
    expect(output.trim()).toBe("u: 2\ns: 7");
  });

  test("weak solo permite métodos const", () => {
    const output = run_source(
      "weak",
      `invoke "std/io"
invoke "std/memory"

rune Caja
  valor: int

  constructor(valor: int)

main = ->
  s = shared<Caja>(5)
  w = weak(s)
  io::println("vivo: #{w.is_alive()}")
`,
    );
    expect(output.trim()).toBe("vivo: true");
  });

  test("un método mut en weak<T> es E0710", () => {
    const found = codes(`
invoke "std/io"

enchanting weak<T>
  mut romper = -> void
    pass
`);
    expect(found).toContain("E0710");
  });

  test("`raw<T>` no se puede enhechizar", () => {
    const found = codes(`
invoke "std/io"

enchanting raw<T>
  leer = -> T
    @
`);
    expect(found).toContain("E0709");
  });
});
