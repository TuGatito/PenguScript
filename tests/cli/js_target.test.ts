// P0: el comando `build --target js` todavía no emite código, pero debe
// analizar el programa (mismos diagnósticos que C++) y decirlo con claridad en
// vez de fallar con un error de compilador de C++.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse_args } from "../../src/cli/args.ts";
import { run_build } from "../../src/cli/build_command.ts";
import { compile_file } from "../../src/driver/compile.ts";

function project(source: string): string {
  const dir = mkdtempSync(join(tmpdir(), "pengu_js0_"));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  return file;
}

const HELLO = `invoke "std/io"

main = ->
  io::println("hola")
`;

describe("build --target js (P0)", () => {
  test("informa de que el backend aún no emite código", () => {
    const file = project(HELLO);
    const result = run_build(parse_args(["build", file, "--target", "js"]));
    expect(result.exit_code).toBe(1);
    expect(result.output).toContain("E0807");
    expect(result.output).toContain("todavía no emite código");
    expect(result.output).toContain("--target cpp");
  });

  test("los errores de tipo se detectan antes de emitir", () => {
    const file = project(`main = -> int\n  "no es un entero"\n`);
    const result = run_build(parse_args(["build", file, "--target", "js"]));
    expect(result.exit_code).toBe(1);
    expect(result.output).toContain("E0501");
  });

  test("un backend desconocido se rechaza antes de compilar", () => {
    const file = project(HELLO);
    const result = run_build(parse_args(["build", file, "--target", "wasm"]));
    expect(result.exit_code).toBe(1);
    expect(result.output).toContain("backend desconocido");
    expect(result.output).toContain("wasm");
  });

  test("un modo --int64 desconocido se rechaza", () => {
    const file = project(HELLO);
    const result = run_build(parse_args(["build", file, "--target", "js", "--int64", "i128"]));
    expect(result.exit_code).toBe(1);
    expect(result.output).toContain("--int64");
    expect(result.output).toContain("bigint");
  });
});

describe("compile_file con target js (P0)", () => {
  test("devuelve target js y un diagnóstico E0807", () => {
    const file = project(HELLO);
    const result = compile_file(file, { target: "js" });
    expect(result.ok).toBe(false);
    expect(result.target).toBe("js");
    expect(result.diagnostics.map((item) => item.code)).toEqual(["E0807"]);
  });

  test("sin target sigue compilando con C++ (target por defecto)", () => {
    const file = project(HELLO);
    const result = compile_file(file, {});
    expect(result.ok).toBe(true);
    expect(result.target).toBe("cpp");
    expect(result.binary_path).toBeDefined();
  });

  test("un archivo inexistente comparte el diagnóstico con C++", () => {
    const result = compile_file("/ruta/que/no/existe.pengu", { target: "js" });
    expect(result.ok).toBe(false);
    expect(result.target).toBe("js");
    expect(result.diagnostics.map((item) => item.code)).toEqual(["E0005"]);
  });
});
