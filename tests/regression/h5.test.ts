// Regresiones de la fase H5: los rangos son valores de primera clase.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_h5_${name}_`));
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

describe("H5 rangos como valores", () => {
  test("anotar, pasar a una función, recorrer y medir", () => {
    const output = run_source(
      "valor",
      `invoke "std/io"

sumar = (r: range<int>) -> int
  mut total = 0
  for x in r
    total += x
  total

main = ->
  r = 1..10
  io::println("largo: #{#r}")
  io::println("suma: #{sumar(r)}")
`,
    );
    expect(output.trim()).toBe("largo: 10\nsuma: 55");
  });

  test("devolver un rango desde una función", () => {
    const output = run_source(
      "retorno",
      `invoke "std/io"

hasta = (n: int) -> range<int>
  1..n

main = ->
  io::println("#{#hasta(5)}")
  for x in hasta(3)
    io::println("#{x}")
`,
    );
    expect(output.trim()).toBe("5\n1\n2\n3");
  });

  test("contains sobre un rango inclusivo y exclusivo", () => {
    const output = run_source(
      "contiene",
      `invoke "std/io"

main = ->
  inclusivo = 1..5
  exclusivo = 1..<5
  io::println("#{3 in inclusivo} #{5 in inclusivo}")
  io::println("#{3 in exclusivo} #{5 in exclusivo}")
`,
    );
    expect(output.trim()).toBe("true true\ntrue false");
  });

  test("un rango vacío mide cero", () => {
    const output = run_source(
      "vacio",
      `invoke "std/io"

main = ->
  io::println("#{#(5..1)}")
`,
    );
    expect(output.trim()).toBe("0");
  });
});
