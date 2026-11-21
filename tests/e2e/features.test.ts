// Pruebas de extremo a extremo de características del lenguaje:
// compilan el programa con g++ y comprueban la salida real.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_feat_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output);
  }
  const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout;
}

describe("características del lenguaje", () => {
  test("rangos con paso, break con valor y else de bucle", () => {
    const out = run_source(
      "loops",
      `invoke "std/io"

main = ->
  mut total = 0
  for i = 0, 10, 2
    total += i
  io::println("total: #{total}")

  const encontrado = for n in [4, 5, 6]
    if n == 5
      break n
  io::println("encontrado: #{encontrado.value()}")

  mut ninguno = false
  for n in [1, 2, 3]
    if n > 10
      break
  else
    ninguno = true
  io::println("sin ruptura: #{ninguno}")
`,
    );
    expect(out).toContain("total: 30");
    expect(out).toContain("encontrado: 5");
    expect(out).toContain("sin ruptura: true");
  });

  test("archivos, tiempo y azar del runtime", () => {
    const out = run_source(
      "runtime",
      `invoke "std/io"
invoke "std/fs"
invoke "std/time"
invoke "std/random"

main = ->
  const ruta = "/tmp/pengu_fs_demo.txt"
  if fs::exists(ruta)
    fs::remove(ruta)

  io::println("escrito: #{fs::write_string(ruta, "hola archivo")}")
  const leido = fs::read_to_string(ruta)
  io::println("leido: #{leido.value()}")
  io::println("existe: #{fs::exists(ruta)}")
  fs::remove(ruta)
  io::println("tras borrar: #{fs::exists(ruta)}")

  const momento = time::now_millis()
  io::println("tiempo: #{momento > 0}")
  io::println("azar: #{random::int(5, 5)}")
`,
    );
    expect(out).toContain("escrito: true");
    expect(out).toContain("leido: hola archivo");
    expect(out).toContain("existe: true");
    expect(out).toContain("tras borrar: false");
    expect(out).toContain("tiempo: true");
    expect(out).toContain("azar: 5");
  });

  test("formato, argumentos y stderr", () => {
    const out = run_source(
      "format",
      `invoke "std/io"
invoke "std/format"
invoke "std/os"

main = ->
  const mensaje = format::format("x=", 7, " y=", 2.5)
  io::println(mensaje)
  io::println("args: #{#os::args() >= 1}")
  io::eprintln("aviso")
`,
    );
    expect(out).toContain("x=7 y=2.5");
    expect(out).toContain("args: true");
  });

  test("weak, flags y operadores de omen", () => {
    const out = run_source(
      "pointers",
      `invoke "std/io"

rune Node
  value: int

flags omen Permiso
  Leer
  Escribir

main = ->
  const hijo = shared<Node>(1)
  const debil = weak(hijo)
  const vivo = debil.lock()
  io::println("lock: #{vivo.is_some()}")

  const permisos = Permiso::Leer | Permiso::Escribir
  io::println("flags: #{permisos as int}")
  io::println("tiene: #{permisos.has(Permiso::Escribir)}")
`,
    );
    expect(out).toContain("lock: true");
    expect(out).toContain("flags: 3");
    expect(out).toContain("tiene: true");
  });

  test("comprensiones de vector, mapa y conjunto", () => {
    const out = run_source(
      "comprehensions",
      `invoke "std/io"

main = ->
  xs = [1, 2, 3, 4]
  ys = [x * 2 for x in xs if x % 2 == 0]
  io::println("ys: #{ys}")

  cuadrados = {x: x * x for x in xs}
  io::println("cuadrados: #{cuadrados}")

  resto = set{x % 3 for x in xs}
  io::println("resto: #{resto}")
`,
    );
    expect(out).toContain("ys: [4, 8]");
    expect(out).toContain("cuadrados: {1: 1, 2: 4, 3: 9, 4: 16}");
    expect(out).toContain("resto: {0, 1, 2}");
  });

  test("strings, índices y conversiones seguras", () => {
    const out = run_source(
      "strings",
      `invoke "std/io"

main = ->
  const texto = "hola mundo"
  io::println("len: #{#texto}")
  io::println("contiene: #{"mundo" in texto}")
  io::println("inicial: #{texto[0]}")
  io::println("sub: #{texto.substr(0, 4)}")
  const d = 3 as double
  io::println("d: #{d}")
`,
    );
    expect(out).toContain("len: 10");
    expect(out).toContain("contiene: true");
    expect(out).toContain("inicial: h");
    expect(out).toContain("sub: hola");
    expect(out).toContain("d: 3");
  });

  test("switch con tipo común y match con guardas y carga útil", () => {
    const out = run_source(
      "omens",
      `invoke "std/io"

omen Color
  Red, Green, Blue

omen Shape
  Circle(double)
  Rect(double, double)

nombre = (c: Color) -> string
  switch c
    when Color::Red then "rojo"
    when Color::Green then "verde"
    else "azul"

area = (s: Shape) -> double
  match s
    when Circle(r) then 3.14 * r * r
    when Rect(w, h) if w == h then w * w
    when Rect(w, h) then w * h

main = ->
  io::println(nombre(Color::Green))
  io::println("círculo: #{area(Circle(1.0))}")
  io::println("cuadrado: #{area(Rect(2.0, 2.0))}")
  io::println("rect: #{area(Rect(2.0, 3.0))}")

  const c = Color::try_from(2)
  io::println("try_from: #{c.is_some()}")
  io::println("from: #{Color::from(1) as int}")
`,
    );
    expect(out).toContain("verde");
    expect(out).toContain("círculo: 3.14");
    expect(out).toContain("cuadrado: 4");
    expect(out).toContain("rect: 6");
    expect(out).toContain("try_from: true");
  });
});
