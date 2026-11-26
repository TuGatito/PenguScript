// Tests del emisor JavaScript para la construcción `host` (fase T1 del plan
// ts-bindgen): los tipos, globales y namespaces del host se emiten como los
// nombres reales del navegador, sin clones, sin cajas y sin runtime de más.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { compile_file } from "../../src/driver/compile.ts";

interface Emitted {
  readonly codes: readonly string[];
  readonly files: ReadonlyMap<string, string>;
}

function emitir(name: string, source: string): Emitted {
  const dir = mkdtempSync(join(tmpdir(), `pengu_host_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file, { target: "js", out: join(dir, "out") });
  const files = new Map<string, string>();
  for (const path of result.files ?? []) {
    files.set(path.slice(path.lastIndexOf("/") + 1), readFileSync(path, "utf8"));
  }
  return { codes: result.diagnostics.map((item) => item.code), files };
}

function cuerpo(name: string, source: string): string {
  const result = emitir(name, source);
  expect(result.codes).toEqual([]);
  return result.files.get("main.mjs") ?? "";
}

const TIPOS = `realm main
echo js::String = string
host js::Point
  mut x: double
  y: double
  length: () -> double
  scale: (factor: double) -> void
  static origin: () -> js::Point
  constructor(x: double, y: double)

host js::Point3 heir js::Point
  z: double
  constructor(x: double, y: double, z: double)
`;

describe("tipos del host en el emisor JavaScript", () => {
  test("construir un tipo del host emite `new`", () => {
    const code = cuerpo(
      "construir",
      `${TIPOS}
main = ->
  mut p = js::Point(1.0, 2.0)
  p.x
`,
    );
    expect(code).toContain("new Point(1.0, 2.0)");
  });

  test("las propiedades se emiten como propiedades de JavaScript", () => {
    const code = cuerpo(
      "propiedades",
      `${TIPOS}
main = ->
  mut p = js::Point(1.0, 2.0)
  p.x = 4.0
  const y: double = p.y
  y
`,
    );
    expect(code).toContain("p.x = 4.0;");
    expect(code).toContain("p.y");
  });

  test("los métodos se llaman con el receptor delante", () => {
    const code = cuerpo(
      "metodos",
      `${TIPOS}
main = ->
  mut p = js::Point(1.0, 2.0)
  p.scale(2.0)
  p.length()
`,
    );
    expect(code).toContain("p.scale(2.0);");
    expect(code).toContain("p.length()");
  });

  test("un miembro estático de un tipo del host", () => {
    const code = cuerpo(
      "estatico",
      `${TIPOS}
main = ->
  const p = js::Point::origin()
  p
`,
    );
    expect(code).toContain("Point.origin()");
  });

  test("el tipo del host se escribe en la anotación generada", () => {
    const code = cuerpo(
      "anotacion",
      `${TIPOS}
crear = -> js::Point
  js::Point(1.0, 2.0)

main = ->
  const p = crear()
  p.length()
`,
    );
    expect(code).toContain("Point");
    expect(code).not.toContain("js::Point");
  });
});

describe("globales y namespaces del host en el emisor", () => {
  test("un global del host se emite con su nombre de JavaScript", () => {
    const code = cuerpo(
      "global",
      `realm main
host global document: js::Document
host js::Document
  mut title: string

main = ->
  document.title = "hola"
`,
    );
    expect(code).toContain('document.title = "hola";');
  });

  test("un namespace del host emite el objeto y la función", () => {
    const code = cuerpo(
      "namespace",
      `realm main
host namespace Maths
  max: (a: double, b: double) -> double

main = ->
  const m: double = Maths::max(1.0, 2.0)
  m
`,
    );
    expect(code).toContain("Maths.max(1.0, 2.0)");
  });

  test("una función del catálogo se emite con su equivalente del navegador", () => {
    const code = cuerpo(
      "catalogo",
      `realm main
invoke "std/js/number"

main = ->
  const n: double = js_number::parse_float("2.5")
  n
`,
    );
    expect(code).toContain("rt.js_parse_float(");
    expect(code).toContain("import * as rt from \"./pengu_rt.mjs\"");
  });
});
