// `async`/`await`: el backend JavaScript ejecuta de verdad el programa y el
// backend C++20 lo rechaza con E0804 (no hay promesas en C++20).

import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { compile_file } from "../../src/driver/compile.ts";
import { find_js_runtime } from "../../src/driver/js_runner.ts";

const runtime = find_js_runtime();

function fuente(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_async_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  return file;
}

// Compila a JavaScript, ejecuta el lanzador y devuelve stdout.
function ejecutar_js(file: string): { stdout: string; status: number } {
  const result = compile_file(file, { target: "js" });
  if (!result.ok) {
    const errores = result.diagnostics.map((d) => `${d.code}: ${d.message}`).join("\n");
    throw new Error(`JavaScript no compiló ${file}:\n${errores}`);
  }
  const entry = result.js_entry_path;
  if (entry === undefined || runtime === undefined) throw new Error("sin entrada o sin runtime");
  const run = spawnSync(runtime.command, [entry], { encoding: "utf8" });
  return { stdout: run.stdout ?? "", status: run.status ?? 1 };
}

describe("async/await en JavaScript", () => {
  test("el orden de ejecución de una cadena de awaits es secuencial", () => {
    const file = fuente(
      "cadena",
      `invoke "std/io"

async paso = (nombre: string, resultado: int) -> int
  io::println("entra #{nombre}")
  io::println("sale #{nombre}")
  resultado

async main = -> int
  a = await paso("uno", 1)
  b = await paso("dos", 2)
  io::println("total #{a + b}")
  0
`,
    );
    expect(ejecutar_js(file).stdout).toBe(
      ["entra uno", "sale uno", "entra dos", "sale dos", "total 3", ""].join("\n"),
    );
  }, 30_000);

  test("await dentro de match, if, do y comprensión mantiene el valor", () => {
    const file = fuente(
      "control",
      `invoke "std/io"

async doble = (n: int) -> int
  n * 2

async main = -> int
  valor = match 2
    when 1 then await doble(1)
    else
      await doble(3)
  otro = if valor > 4
    await doble(valor)
  else
    0
  tercero = do
    await doble(5)
  valores = [await doble(i) for i in 0..2]
  io::println("#{valor} #{otro} #{tercero} #{#valores}")
  0
`,
    );
    expect(ejecutar_js(file).stdout).toBe("6 12 10 3\n");
  }, 30_000);

  test("una lambda async y un método async funcionan", () => {
    const file = fuente(
      "lambda",
      `invoke "std/io"

rune Caja
  total: int

enchanting Caja
  async recargar = (n: int) -> int
    @.total + n

async main = -> int
  f = async (n: int) -> int
    n * 2
  mut caja = Caja(10)
  io::println("#{await f(21)} #{await caja.recargar(5)}")
  0
`,
    );
    expect(ejecutar_js(file).stdout).toBe("42 15\n");
  }, 30_000);

  test("await en un bucle con break conserva el valor de ruptura", () => {
    const file = fuente(
      "break",
      `invoke "std/io"

async doble = (n: int) -> int
  n * 2

async main = -> int
  encontrado = for i in 0..10
    if i == 3
      break await doble(i)
  io::println("encontrado #{encontrado}")
  0
`,
    );
    expect(ejecutar_js(file).stdout).toBe("encontrado 6\n");
  }, 30_000);

  test("los futuros se guardan en un contenedor y se esperan después", () => {
    const file = fuente(
      "futuros",
      `invoke "std/io"

async suma = (a: int, b: int) -> int
  a + b

async main = -> int
  pendientes: vector<future<int>> = [suma(1, 1), suma(2, 2)]
  mut total = 0
  for p in pendientes
    total += await p
  io::println("total #{total}")
  0
`,
    );
    expect(ejecutar_js(file).stdout).toBe("total 6\n");
  }, 30_000);

  test("el backend C++20 rechaza async/await con E0804", () => {
    const file = fuente(
      "cpp",
      `async esperar = () -> void
  pass

async cargar = () -> int
  await esperar()
  1

async main = -> int
  await cargar()
`,
    );
    const result = compile_file(file, { target: "cpp" });
    expect(result.ok).toBe(false);
    const codes = result.diagnostics.map((item) => item.code);
    expect(codes).toContain("E0804");
    // Una por cada declaración `async`; el cuerpo de una función `async` no se
    // emite, así que sus `await` no duplican el diagnóstico.
    expect(codes.filter((code) => code === "E0804").length).toBeGreaterThanOrEqual(3);
    expect(result.diagnostics.every((item) => item.severity === "error")).toBe(true);
  }, 30_000);

  test("await fuera de async y ref a través de await no llegan a emitirse", () => {
    const fuera = fuente(
      "fuera",
      `cargar = -> int
  await esperar()
  1
`,
    );
    expect(compile_file(fuera, { target: "js" }).ok).toBe(false);
    const ref = fuente(
      "ref",
      `async esperar = () -> void
  pass

async leer = (texto: ref<string>) -> string
  r = ref(texto)
  await esperar()
  *r
`,
    );
    const result = compile_file(ref, { target: "js" });
    expect(result.diagnostics.map((item) => item.code)).toContain("E0606");
  }, 30_000);
});
