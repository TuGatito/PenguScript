// Divergencias deliberadas entre los dos backends (§10.4 del plan).
//
// Estos tests no buscan paridad: fijan la diferencia para que nadie la
// descubra en producción y para que un cambio accidental la haga visible.

import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { compile_file } from "../../src/driver/compile.ts";
import { find_js_runtime } from "../../src/driver/js_runner.ts";

const runtime = find_js_runtime();

function fuente(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_div_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  return file;
}

interface Salida {
  readonly stdout: string;
  readonly status: number;
}

function correr(comando: string, args: readonly string[]): Salida {
  const run = spawnSync(comando, [...args], { encoding: "utf8" });
  return { stdout: run.stdout ?? "", status: run.status ?? 1 };
}

function cpp(file: string): Salida {
  const result = compile_file(file, {});
  if (!result.ok || result.binary_path === undefined) throw new Error("C++ no compiló");
  return correr(result.binary_path, []);
}

function js(file: string, options: { int64?: "bigint" | "number" } = {}): Salida {
  const result = compile_file(file, { target: "js", int64: options.int64 });
  if (!result.ok || result.js_entry_path === undefined) {
    throw new Error(result.diagnostics.map((item) => item.code).join(", "));
  }
  if (runtime === undefined) throw new Error("sin runtime de JavaScript");
  return correr(runtime.command, [result.js_entry_path]);
}

describe("divergencias documentadas entre C++20 y JavaScript", () => {
  test("#texto mide bytes en C++ y unidades UTF-16 en JavaScript", () => {
    const file = fuente(
      "longitud",
      `invoke "std/io"

main = -> int
  const texto = "pingüinos"
  io::println("#{#texto}")
  0
`,
    );
    // «ü» ocupa dos bytes en UTF-8 y una unidad en UTF-16.
    expect(cpp(file).stdout).toBe("10\n");
    expect(js(file).stdout).toBe("9\n");
  });

  test("map y set iteran ordenados en C++ y en orden de inserción en JavaScript", () => {
    const file = fuente(
      "orden",
      `invoke "std/io"

main = -> int
  mut precios = map<string, int>{}
  precios.insert("zeta", 1)
  precios.insert("alfa", 2)
  precios.insert("media", 3)
  for clave, _ in precios
    io::println(clave)
  0
`,
    );
    expect(cpp(file).stdout).toBe("alfa\nmedia\nzeta\n");
    expect(js(file).stdout).toBe("zeta\nalfa\nmedia\n");
  });

  test("--int64 number pierde precisión por encima de 2^53", () => {
    const file = fuente(
      "int64",
      `invoke "std/io"

main = -> int
  const grande: int64_t = 9007199254740993
  io::println("grande #{grande}")
  0
`,
    );
    expect(cpp(file).stdout).toBe("grande 9007199254740993\n");
    expect(js(file).stdout).toBe("grande 9007199254740993\n");
    expect(js(file, { int64: "number" }).stdout).toBe("grande 9007199254740992\n");
  });

  test("os::arch() usa los nombres de C++ en los dos backends", () => {
    const file = fuente(
      "arch",
      `invoke "std/io"
invoke "std/os"

main = -> int
  io::println(os::arch())
  0
`,
    );
    const salida_cpp = cpp(file).stdout;
    expect(salida_cpp).toMatch(/^(x86_64|aarch64|i686)\n$/);
    expect(js(file).stdout).toBe(salida_cpp);
  });
});
