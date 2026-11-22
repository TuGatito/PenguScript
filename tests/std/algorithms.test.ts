// Fase F5 del plan de la stdlib: algoritmos (iter, sort, result y test).
//
// Cada prueba compila y ejecuta un programa real: se comprueba el
// comportamiento, no solo que el checker acepte la API.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

interface Run {
  readonly stdout: string;
  readonly stderr: string;
  readonly status: number | null;
}

function compile_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_algo_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(
      result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output,
    );
  }
  return result.binary_path ?? "";
}

function run_raw(name: string, source: string): Run {
  const binary = compile_source(name, source);
  const run = spawnSync(binary, [], { encoding: "utf8" });
  return { stdout: run.stdout ?? "", stderr: run.stderr ?? "", status: run.status };
}

function run_source(name: string, source: string): string {
  const run = run_raw(name, source);
  expect(run.status).toBe(0);
  return run.stdout;
}

describe("iter", () => {
  test("map, filter, fold y búsquedas", () => {
    const output = run_source(
      "iter",
      `invoke "std/io"
invoke "std/iter"
invoke "std/int"
invoke "std/vector"

main = ->
  xs = [1, 2, 3, 4]
  io::println("map: #{iter::map<int, string>(ref(xs), (n: int) -> "#{n * 2}")}")
  io::println("filter: #{iter::filter<int>(ref(xs), (n: int) -> n.is_even())}")
  io::println("fold: #{iter::fold<int, int>(ref(xs), 0, (a: int, b: int) -> a + b)}")
  io::println("count: #{iter::count_if<int>(ref(xs), (n: int) -> n > 2)}")
  io::println("any: #{iter::any<int>(ref(xs), (n: int) -> n > 3)}")
  io::println("all: #{iter::all<int>(ref(xs), (n: int) -> n > 0)}")
  io::println("none: #{iter::none_of<int>(ref(xs), (n: int) -> n > 9)}")
  io::println("find: #{iter::find<int>(ref(xs), (n: int) -> n > 2)}")
  io::println("pos: #{iter::position<int>(ref(xs), (n: int) -> n == 3)}")
  0
`,
    );
    expect(output).toBe(
      [
        "map: [2, 4, 6, 8]",
        "filter: [2, 4]",
        "fold: 10",
        "count: 2",
        "any: true",
        "all: true",
        "none: true",
        "find: 3",
        "pos: 2",
        "",
      ].join("\n"),
    );
  });

  test("zip, enumerate, take, skip, chain y flatten", () => {
    const output = run_source(
      "iter2",
      `invoke "std/io"
invoke "std/iter"

main = ->
  xs = [1, 2, 3]
  ys = [10, 20]
  mut linea = ""
  for par in iter::zip<int, int>(ref(xs), ref(ys))
    linea = "#{linea}(#{par.first},#{par.second})"
  io::println("zip: #{linea}")
  mut linea2 = ""
  for par in iter::enumerate<int>(ref(ys))
    linea2 = "#{linea2}(#{par.first},#{par.second})"
  io::println("enumerate: #{linea2}")
  io::println("take: #{iter::take<int>(ref(xs), size_t::from(2))}")
  io::println("skip: #{iter::skip<int>(ref(xs), size_t::from(2))}")
  io::println("chain: #{iter::chain<int>(ref(xs), ref(ys))}")
  io::println("flatten: #{iter::flatten<int>(ref([xs, ys]))}")
  0
`,
    );
    expect(output).toBe(
      [
        "zip: (1,10)(2,20)",
        "enumerate: (0,10)(1,20)",
        "take: [1, 2]",
        "skip: [3]",
        "chain: [1, 2, 3, 10, 20]",
        "flatten: [1, 2, 3, 10, 20]",
        "",
      ].join("\n"),
    );
  });
});

describe("sort", () => {
  test("ordena mil aleatorios igual que vector.sort", () => {
    const output = run_source(
      "sort_rand",
      `invoke "std/io"
invoke "std/random"
invoke "std/sort"
invoke "std/vector"

main = ->
  random::seed(int64_t::from(7))
  mut xs: vector<int> = []
  mut i = 0
  while i < 1000
    xs.push(random::int(0, 100000))
    i += 1
  mut copia: vector<int> = []
  for valor in xs
    copia.push(valor)
  xs.sort()
  sort::insertion_sort<int>(mut ref(copia))
  mut iguales = true
  mut j = 0
  while j < 1000
    if xs[j] != copia[j]
      iguales = false
    j += 1
  io::println("iguales: #{iguales}")
  io::println("ordenado: #{sort::is_sorted<int>(ref(copia))}")
  io::println("busca: #{sort::binary_search_sorted<int>(ref(copia), xs[500])}")
  io::println("min: #{copia.first()} max: #{copia.last()}")
  0
`,
    );
    expect(output.split("\n")[0]).toBe("iguales: true");
    expect(output).toContain("ordenado: true");
    expect(output).toContain("busca: 500");
  });

  test("ordena runes y copia sin tocar el original", () => {
    const output = run_source(
      "sort_runes",
      `invoke "std/io"
invoke "std/sort"
invoke "std/vector"

rune Punto
  x: int
  y: int

  constructor(x: int, y: int)
    @x = x
    @y = y

enchanting Punto
  operator <=> = (otro: ref<Punto>) -> Ordering
    if @x != otro.x
      return @x <=> otro.x
    @y <=> otro.y

  to_string = -> string
    "(#{@x}, #{@y})"

main = ->
  mut puntos: vector<Punto> = []
  puntos.push(Punto(2, 1))
  puntos.push(Punto(1, 5))
  puntos.push(Punto(1, 2))
  sort::insertion_sort<Punto>(mut ref(puntos))
  io::println("puntos: #{puntos}")
  mut numeros: vector<int> = [3, 1, 2]
  copia = sort::sorted_copy<int>(ref(numeros))
  io::println("copia: #{copia}")
  io::println("original: #{numeros}")
  0
`,
    );
    expect(output).toBe("puntos: [(1, 2), (1, 5), (2, 1)]\ncopia: [1, 2, 3]\noriginal: [3, 1, 2]\n");
  });
});

describe("result", () => {
  test("ok, err, map, and_then y from_optional", () => {
    const output = run_source(
      "result",
      `invoke "std/io"
invoke "std/result"

dividir = (a: int, b: int) -> result::Result<int, string>
  if b == 0
    return result::err<int, string>("división por cero")
  result::ok<int, string>(a / b)

main = ->
  bien = dividir(10, 2)
  io::println("ok: #{bien} valor: #{bien.value()} is_ok: #{bien.is_ok()}")
  mal = dividir(1, 0)
  io::println("err: #{mal} error: #{mal.error_or("ninguno")} is_err: #{mal.is_err()}")
  io::println("respaldo: #{mal.value_or(-1)}")
  io::println("map: #{result::map<int, int, string>(bien, (n: int) -> n * 2)}")
  io::println("map_err: #{result::map_err<int, string, string>(mal, (e: string) -> "err: " + e)}")
  io::println("and_then: #{result::and_then<int, int, string>(bien, (n: int) -> result::ok<int, string>(n + 1))}")
  io::println("from_none: #{result::from_optional<int, string>(none, "vacío")}")
  0
`,
    );
    expect(output).toBe(
      [
        "ok: Ok(5) valor: 5 is_ok: true",
        "err: Err(división por cero) error: división por cero is_err: true",
        "respaldo: -1",
        "map: Ok(10)",
        "map_err: Err(err: división por cero)",
        "and_then: Ok(6)",
        "from_none: Err(vacío)",
        "",
      ].join("\n"),
    );
  });

  test("value y expect panican con un mensaje claro", () => {
    const run = run_raw(
      "result_panic",
      `invoke "std/io"
invoke "std/result"

main = ->
  mal = result::err<int, string>("roto")
  io::println("#{mal.value()}")
  0
`,
    );
    expect(run.status).not.toBe(0);
    expect(run.stderr).toContain("result::value sobre un Err");
  });
});

describe("test", () => {
  test("las comprobaciones que pasan no imprimen nada", () => {
    const output = run_source(
      "test_ok",
      `invoke "std/io"
invoke "std/test"

main = ->
  test::is_true(true)
  test::is_false(false)
  test::equal<int>(2 + 2, 4)
  test::not_equal<int>(1, 2)
  test::is_some<int>(3)
  test::is_none<int>(none)
  io::println("asserts ok")
  0
`,
    );
    expect(output).toBe("asserts ok\n");
  });

  test("una comprobación fallida panica con el mensaje", () => {
    const run = run_raw(
      "test_fail",
      `invoke "std/test"

main = ->
  test::equal<int>(1, 2)
  0
`,
    );
    expect(run.status).not.toBe(0);
    expect(run.stderr).toContain("los valores no coinciden");
  });
});

describe("tipos cualificados", () => {
  test("un rune importado se puede nombrar con su módulo", () => {
    const output = run_source(
      "qualified",
      `invoke "std/io"
invoke "std/time"

espera = (d: time::Duration) -> string
  d.to_string()

main = ->
  d = time::duration_from_millis(int64_t::from(1500))
  io::println(espera(d))
  0
`,
    );
    expect(output).toBe("1.500s\n");
  });
});
