// Paridad de comportamiento entre los dos backends: el mismo programa se
// compila a C++20 y a JavaScript, se ejecuta y se comparan las salidas byte a
// byte. Es la red de seguridad del plan (§10.2): cualquier divergencia
// semántica aparece aquí y no en producción.

import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { compile_file } from "../../src/driver/compile.ts";
import { find_js_runtime } from "../../src/driver/js_runner.ts";

const runtime = find_js_runtime();
const examples = join(import.meta.dir, "../../examples");

// Ejemplos que el backend JavaScript ya cubre. Cada fase añade los suyos.
const PARITY_EXAMPLES = ["01_hello", "02_variables", "04_functions", "08_modules"];

function ejecutar(comando: string, args: readonly string[]): { stdout: string; status: number } {
  const result = spawnSync(comando, [...args], { encoding: "utf8" });
  return { stdout: result.stdout ?? "", status: result.status ?? 1 };
}

function compilar_cpp(file: string): string {
  const result = compile_file(file, {});
  if (!result.ok) {
    throw new Error(`C++ no compiló ${file}: ${result.diagnostics.map((d) => d.code).join(", ")}`);
  }
  return result.binary_path ?? "";
}

// Compila un fuente suelto con ambos backends y devuelve las dos salidas.
function paridad(source: string): { cpp: { stdout: string; status: number }; js: { stdout: string; status: number } } {
  const dir = mkdtempSync(join(tmpdir(), "pengu_parity_"));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const cpp = ejecutar(compilar_cpp(file), []);
  const js = runtime === undefined ? cpp : ejecutar(runtime.command, [compilar_js(file)]);
  return { cpp, js };
}

function compilar_js(file: string): string {
  const result = compile_file(file, { target: "js" });
  if (!result.ok) {
    throw new Error(`JS no compiló ${file}: ${result.diagnostics.map((d) => d.code).join(", ")}`);
  }
  return result.js_entry_path ?? "";
}

describe("paridad C++ / JavaScript", () => {
  for (const name of PARITY_EXAMPLES) {
    test(
      name,
      () => {
        if (runtime === undefined) {
          expect(true).toBe(true);
          return;
        }
        const file = join(examples, name, "main.pengu");
        const cpp = compilar_cpp(file);
        const js = compilar_js(file);
        const esperado = ejecutar(cpp, []);
        const obtenido = ejecutar(runtime.command, [js]);
        expect(obtenido.stdout).toBe(esperado.stdout);
        expect(obtenido.status).toBe(esperado.status);
      },
      60000,
    );
  }

  test(
    "bucles, negaciones y textos",
    () => {
      if (runtime === undefined) {
        expect(true).toBe(true);
        return;
      }
      const { cpp, js } = paridad(`invoke "std/io"

contar = (n: int) -> int
  mut veces = 0
  repeat
    veces += 1
  until veces >= n
  veces

main = ->
  mut total = 0
  mut i = 1
  while i <= 4
    total += i
    i += 1
  io::println("total = #{total}, veces = #{contar(3)}")
  unless 1 > 2
    io::println("unless ok")
  mut texto = "hola"
  texto += " mundo"
  io::println("#{texto} · #{17 % 5} · #{-7 / 2}")
  for j in 0..<3
    io::print("#{j} ")
  io::println("")
`);
      expect(js.stdout).toBe(cpp.stdout);
      expect(js.status).toBe(cpp.status);
      expect(js.stdout).toContain("total = 10, veces = 3");
      expect(js.stdout).toContain("hola mundo · 2 · -3");
    },
    60000,
  );

  test(
    "enteros, división y formato de dobles",
    () => {
      if (runtime === undefined) {
        expect(true).toBe(true);
        return;
      }
      const dir = mkdtempSync(join(tmpdir(), "pengu_parity_"));
      const file = join(dir, "main.pengu");
      writeFileSync(
        file,
        `invoke "std/io"

main = ->
  const grande: int64_t = 10000000000
  io::println("suma = #{grande + 1}")
  io::println("entera = #{7 / 2}")
  io::println("real = #{7.0 / 2.0}")
  io::println("tercio = #{1.0 / 3.0}")
  io::println("bool = #{2 > 1}")
`,
      );
      const esperado = ejecutar(compilar_cpp(file), []);
      const obtenido = ejecutar(runtime.command, [compilar_js(file)]);
      expect(obtenido.stdout).toBe(esperado.stdout);
      expect(obtenido.stdout).toContain("suma = 10000000001");
      expect(obtenido.stdout).toContain("tercio = 0.333333");
    },
    60000,
  );

  test("el runtime existe si hay runtime de JavaScript", () => {
    if (runtime === undefined) return;
    expect(existsSync(runtime.command)).toBe(true);
  });
});
