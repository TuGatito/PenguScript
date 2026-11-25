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
const PARITY_EXAMPLES = [
  "01_hello",
  "02_variables",
  "03_control",
  "04_functions",
  "05_runes",
  "06_omens",
  "07_seal",
  "08_modules",
];

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

  test(
    "runes: objeto literal, clase y herencia",
    () => {
      if (runtime === undefined) {
        expect(true).toBe(true);
        return;
      }
      const { cpp, js } = paridad(`invoke "std/io"

rune Punto
  x: int
  y: int

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

rune Contador
  total: int

  constructor()
    @total = 0

enchanting Contador
  mut sumar = (n: int) -> void
    @total += n

main = ->
  const p = Punto(2, 3)
  io::println("p = #{p.x},#{p.y}")
  mut q = p
  q.x = 9
  io::println("p sigue = #{p.x}, q = #{q.x}")
  const a = Animal("gato")
  const d = Perro("toby")
  io::println("a: #{a.hablar()} d: #{d.hablar()} nombre: #{d.nombre}")
  mut c = Contador()
  c.sumar(4)
  c.sumar(5)
  io::println("total = #{c.total}")
  mut copia = c
  copia.total = 100
  io::println("c = #{c.total}")
`);
      expect(js.stdout).toBe(cpp.stdout);
      expect(js.stdout).toContain("p = 2,3");
      expect(js.stdout).toContain("p sigue = 2, q = 9");
      expect(js.stdout).toContain("a: ... d: guau nombre: toby");
      expect(js.stdout).toContain("total = 9");
      expect(js.stdout).toContain("c = 9");
    },
    60000,
  );

  test(
    "comprensiones, break con valor y else de bucle",
    () => {
      if (runtime === undefined) {
        expect(true).toBe(true);
        return;
      }
      const { cpp, js } = paridad(`invoke "std/io"

buscar = (limite: int) -> int?
  for i in 0..<limite
    if i * i > 20
      break i

avisar = (valores: vector<int>, objetivo: int) -> void
  for v in valores
    if v == objetivo
      io::println("encontrado #{v}")
      break
  else
    io::println("no esta #{objetivo}")

primero_negativo = (valores: vector<int>) -> int?
  for v in valores
    if v < 0
      break v
  else
    none

main = ->
  const cuadrados = [i * i for i in 0..5 if i % 2 == 1]
  io::println("cuadrados = #{cuadrados}")
  const pares = [[x, y] for x in [1, 2] for y in [3, 4]]
  io::println("pares = #{#pares}")
  const letras = {[p]: #p for p in ["aa", "bbb"]}
  io::println("letras = #{letras}")
  const unicos = set{x % 3 for x in 0..<7}
  io::println("unicos = #{#unicos}")
  io::println("buscar(10) = #{buscar(10)}")
  io::println("buscar(3) = #{buscar(3)}")
  avisar([1, 2, 3], 2)
  avisar([1, 2, 3], 9)
  io::println("negativo = #{primero_negativo([3, -2, -5])}")
  io::println("negativo = #{primero_negativo([3, 2])}")
`);
      expect(js.stdout).toBe(cpp.stdout);
      expect(js.stdout).toContain("cuadrados = [1, 9, 25]");
      expect(js.stdout).toContain("pares = 4");
      expect(js.stdout).toContain("buscar(10) = 5");
      expect(js.stdout).toContain("encontrado 2");
      expect(js.stdout).toContain("no esta 9");
      expect(js.stdout).toContain("negativo = -2");
    },
    60000,
  );

  test(
    "seal y echo: métodos como funciones libres",
    () => {
      if (runtime === undefined) {
        expect(true).toBe(true);
        return;
      }
      const { cpp, js } = paridad(`invoke "std/io"

echo Etiqueta = string
seal UserId = int

enchanting UserId
  label = -> string
    "user-#{@ as int}"
  doble = -> int
    (@ as int) * 2

etiqueta_de = (id: UserId) -> string
  "id #{id as int}"

main = ->
  const u = UserId(21)
  io::println(u.label())
  io::println("doble = #{u.doble()}, #{etiqueta_de(u)}")
  const e: Etiqueta = "hola"
  io::println("#{e} · #{#e}")
`);
      expect(js.stdout).toBe(cpp.stdout);
      expect(js.stdout).toContain("user-21");
      expect(js.stdout).toContain("doble = 42");
    },
    60000,
  );

  test("el runtime existe si hay runtime de JavaScript", () => {
    if (runtime === undefined) return;
    expect(existsSync(runtime.command)).toBe(true);
  });
});
