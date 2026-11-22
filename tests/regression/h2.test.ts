// Regresiones de la fase H2: herencia sin despacho virtual.
//
// La especificación dice que las runes no tienen despacho dinámico: cada
// llamada se resuelve con el tipo estático del receptor.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

const ANIMALES = `
rune Animal
  nombre: string

  constructor(nombre: string)

enchanting Animal
  hablar = -> string
    "..."

rune Perro heir Animal
  constructor(nombre: string)
    parent(nombre)

enchanting Perro
  hablar = -> string
    "guau"
`;

function build(name: string, source: string): { cpp: string; run: () => string } {
  const dir = mkdtempSync(join(tmpdir(), `pengu_h2_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n"));
  }
  const cpp = readFileSync(result.cpp_path ?? "", "utf8");
  return {
    cpp,
    run: () => {
      const spawned = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
      expect(spawned.status).toBe(0);
      return spawned.stdout;
    },
  };
}

describe("H2 despacho estático", () => {
  test("el C++ generado no usa virtual", () => {
    const built = build("no_virtual", `invoke "std/io"
${ANIMALES}
main = ->
  io::println(Perro("Toby").hablar())
`);
    expect(built.cpp).not.toContain("virtual");
    expect(built.run().trim()).toBe("guau");
  });

  test("el tipo estático decide el método", () => {
    const built = build("estatico", `invoke "std/io"
${ANIMALES}
presentar = (a: ref<Animal>) -> void
  io::println(a.hablar())

main = ->
  perro = Perro("Toby")
  io::println(perro.hablar())
  presentar(ref<Animal>(ref(perro)))
`);
    expect(built.run().trim()).toBe("guau\n...");
  });
});
