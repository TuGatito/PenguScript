// P1: `--target js` emite módulos ESM ejecutables. Estos tests comprueban el
// contrato del comando (mensaje, archivos, errores) sin depender de C++.

import { describe, expect, test } from "bun:test";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse_args } from "../../src/cli/args.ts";
import { run_build } from "../../src/cli/build_command.ts";
import { run_check } from "../../src/cli/check_command.ts";
import { compile_file } from "../../src/driver/compile.ts";

function project(source: string): string {
  const dir = mkdtempSync(join(tmpdir(), "pengu_js1_"));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  return file;
}

const HELLO = `invoke "std/io"

main = ->
  io::println("hola")
`;

describe("build --target js", () => {
  test("emite un punto de entrada ejecutable", () => {
    const file = project(HELLO);
    const result = run_build(parse_args(["build", file, "--target", "js"]));
    expect(result.output).toContain("módulo(s) generados en");
    expect(result.output).toContain("entrada:");
    expect(result.exit_code).toBe(0);
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

describe("compile_file con target js", () => {
  test("devuelve los módulos generados y el punto de entrada", () => {
    const file = project(HELLO);
    const result = compile_file(file, { target: "js" });
    expect(result.ok).toBe(true);
    expect(result.target).toBe("js");
    expect(result.js_entry_path).toBeDefined();
    expect(existsSync(result.js_entry_path ?? "")).toBe(true);
    const names = (result.files ?? []).map((path) => path.slice(path.lastIndexOf("/") + 1));
    expect(names).toContain("main.mjs");
    expect(names).toContain("io.mjs");
    expect(names).toContain("pengu_rt.mjs");
    expect(names).toContain("index.mjs");
  });

  test("el código generado es ESM limpio y cita el realm", () => {
    const file = project(HELLO);
    const result = compile_file(file, { target: "js" });
    const main = (result.files ?? []).find((path) => path.endsWith("/main.mjs"));
    const code = readFileSync(main ?? "", "utf8");
    expect(code).toContain("export function main()");
    expect(code).toContain('from "./io.mjs"');
    expect(code).not.toContain("require(");
  });

  test("--out elige el directorio de salida", () => {
    const file = project(HELLO);
    const out = join(tmpdir(), `pengu_js_out_${Date.now()}`);
    const result = compile_file(file, { target: "js", out });
    expect(result.ok).toBe(true);
    expect(result.js_entry_path).toBe(join(out, "index.mjs"));
    expect(existsSync(join(out, "main.mjs"))).toBe(true);
  });

  test("una segunda compilación reutiliza los archivos si no cambian", () => {
    const file = project(HELLO);
    const first = compile_file(file, { target: "js" });
    const second = compile_file(file, { target: "js" });
    expect(first.reused).toBe(false);
    expect(second.reused).toBe(true);
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

  test("el runtime generado trae las piezas compartidas", () => {
    const file = project(HELLO);
    const result = compile_file(file, { target: "js" });
    const runtime = (result.files ?? []).find((path) => path.endsWith("/pengu_rt.mjs"));
    const code = readFileSync(runtime ?? "", "utf8");
    expect(code).toContain("export function fmt_float");
    expect(code).toContain("Ordering");
    expect(code).toContain("export function panic");
  });
});

describe("lo que el backend JavaScript no puede representar", () => {
  test("check --target js rechaza meld con E0807 antes de emitir", () => {
    const file = project(`meld Union
  a: int
  b: double

main = -> int
  0
`);
    const result = run_check([file], { target: "js" });
    expect(result.exit_code).toBe(1);
    expect(result.output).toContain("E0807");
  });

  test("check sin --target js acepta el mismo programa", () => {
    const file = project(`meld Union
  a: int
  b: double

main = -> int
  0
`);
    expect(run_check([file], {}).exit_code).toBe(0);
  });

  test("sin main, el backend JavaScript lo dice con E0407", () => {
    const file = project(`saluda = -> int
  0
`);
    const result = compile_file(file, { target: "js" });
    expect(result.ok).toBe(false);
    expect(result.diagnostics.map((item) => item.code)).toContain("E0407");
  });
});

describe("punto de entrada", () => {
  test("importa el módulo del realm y no filtra rutas absolutas", () => {
    const file = project(HELLO);
    const result = compile_file(file, { target: "js" });
    const entry = result.js_entry_path ?? "";
    const text = readFileSync(entry, "utf8");
    expect(text).toContain("./main.mjs");
    expect(text).not.toContain(tmpdir());
  });
});
