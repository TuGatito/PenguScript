// F2: `opaque`, `callback`, `define` y `link` en un módulo de declaraciones.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { compile_file } from "../../src/driver/compile.ts";
import { build_object, c_compiler } from "./native.ts";

const C_SOURCE = [
  "typedef struct Textura Textura;",
  "struct Textura { int id; };",
  "static Textura muestra = {0};",
  "Textura *crear_textura(int id) { muestra.id = id; return &muestra; }",
  "int id_de(Textura *t) { return t->id; }",
  "int aplicar(int (*f)(int), int x) { return f == 0 ? -1 : f(x); }",
  "int suma(int a, int b) { return a + b; }",
  "",
].join("\n");

describe("declaraciones de .d.pengu", () => {
  test("opaque solo cruza por raw y se rechaza por valor", () => {
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-decls-"));
    try {
      const object = build_object(compiler, dir, "decls", C_SOURCE);
      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          "",
          "opaque Textura",
          "",
          'extern "C"',
          "  crear_textura = (id: int) -> raw<Textura>",
          "  id_de = (t: raw<Textura>) -> int",
          "",
          "main = -> void",
          "  t = crear_textura(9)",
          "  io::println(id_de(t))",
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: [object] });
      expect(result.diagnostics.map((diagnostic) => diagnostic.message)).toEqual([]);
      const ran = spawnSync(result.binary_path as string, [], { encoding: "utf8" });
      expect(ran.stdout).toBe("9\n");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("un opaco por valor da E0715", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu-decls-"));
    try {
      const source = join(dir, "main.pengu");
      writeFileSync(source, 'opaque Textura\n\nextern "C"\n  id_de = (t: Textura) -> int\n\nmain = -> void\n  pass\n');
      const result = compile_file(source);
      expect(result.ok).toBe(false);
      expect(result.diagnostics.map((diagnostic) => diagnostic.code)).toContain("E0715");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("callback se emite como puntero a función C", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu-decls-"));
    try {
      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        'callback Doble = (x: int) -> int\n\nextern "C"\n  aplicar = (f: Doble, x: int) -> int\n\nmain = -> void\n  pass\n',
      );
      const result = compile_file(source);
      expect(result.diagnostics.map((diagnostic) => diagnostic.message)).toEqual([]);
      const cpp = readFileSync(result.cpp_path as string, "utf8");
      expect(cpp).toContain("using Doble = int (*)(int);");
      expect(cpp).toContain("int aplicar(Doble f, int x);");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("define se emite como inline constexpr", () => {
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-decls-"));
    try {
      const object = build_object(compiler, dir, "decls", C_SOURCE);
      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          "",
          "define CUATRO = 4",
          "",
          'extern "C"',
          "  suma = (a: int, b: int) -> int",
          "",
          "main = -> void",
          "  io::println(suma(CUATRO, 3))",
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: [object] });
      expect(result.diagnostics.map((diagnostic) => diagnostic.message)).toEqual([]);
      const cpp = readFileSync(result.cpp_path as string, "utf8");
      expect(cpp).toContain("inline constexpr");
      const ran = spawnSync(result.binary_path as string, [], { encoding: "utf8" });
      expect(ran.stdout).toBe("7\n");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("link \"m\" enlaza la biblioteca sin pasarla por la línea de órdenes", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu-decls-"));
    try {
      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          'link "m"',
          "",
          'extern "C"',
          "  cos = (x: double) -> double",
          "",
          "main = -> void",
          "  io::println(cos(0.0))",
          "",
        ].join("\n"),
      );

      const result = compile_file(source);
      expect(result.ok).toBe(true);
      const ran = spawnSync(result.binary_path as string, [], { encoding: "utf8" });
      expect(ran.stdout.startsWith("1")).toBe(true);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
