// Fase F2 del plan de la stdlib: contenedores.
//
// Cada prueba compila y ejecuta un programa de verdad: lo que se comprueba es
// el comportamiento de la API, no solo que el checker la acepte.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_con_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(
      result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output,
    );
  }
  const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout;
}

describe("contenedores", () => {
  test("std/vector: consulta y mutación", () => {
    const out = run_source(
      "vector_basico",
      `invoke "std/io"
invoke "std/vector"

main = ->
  mut xs: vector<int> = [3, 1, 2, 2]
  io::println(xs.sum(), " ", xs.product(), " ", xs.min().value(), " ", xs.max().value())
  io::println(xs.get_or(size_t::from(9), 99), " ", xs.first_or(99), " ", xs.last_or(99))
  io::println(xs.remove(2), " ", xs.remove_all(2), " ", #xs, " ", xs.join("-"))
  canal: vector<int> = [7, 8]
  xs.extend(ref(canal))
  io::println(xs.join("-"), " ", xs.is_empty())
`,
    );
    expect(out).toBe("8 12 1 3\n99 3 2\ntrue 1 2 3-1\n3-1-7-8 false\n");
  });

  test("std/vector: orden, búsqueda y partes", () => {
    const out = run_source(
      "vector_orden",
      `invoke "std/io"
invoke "std/vector"

main = ->
  mut xs: vector<int> = [3, 1, 2, 2]
  ordenado = xs.sorted()
  io::println(ordenado.join(","), " ", ordenado.is_sorted(), " ", ordenado.binary_search(2), " ", xs.is_sorted())
  xs.sort_by((a: int, b: int) -> int
    a - b)
  xs.dedup()
  io::println(xs.join(","), " ", #xs, " ", xs.join(","))
  desc = xs.sorted_by((a: int, b: int) -> int
    b - a)
  io::println(desc.join(","))
  io::println(xs.take(size_t::from(2)).join(","), " ", xs.skip(size_t::from(2)).join(","), " ", xs.slice(size_t::from(1), size_t::from(3)).join(","))
  tramos = xs.chunks(size_t::from(2))
  io::println(#tramos, " ", tramos[0].join(","), " ", tramos[1].join(","))
  ventanas = xs.windows(size_t::from(2))
  io::println(#ventanas, " ", ventanas[0].join(","), " ", ventanas[1].join(","))
`,
    );
    expect(out).toBe("1,2,2,3 true 1 false\n1,2,3 3 1,2,3\n3,2,1\n1,2 3 2,3\n2 1,2 3\n2 1,2 2,3\n");
  });

  test("std/vector: transformaciones y orden superior", () => {
    const out = run_source(
      "vector_orden_superior",
      `invoke "std/io"
invoke "std/vector"

main = ->
  xs: vector<int> = [1, 2, 3, 4]
  io::println(xs.any((x: int) -> bool
    x > 3), " ", xs.all((x: int) -> bool
    x > 0), " ", xs.none((x: int) -> bool
    x > 9))
  io::println(xs.count_if((x: int) -> bool
    x % 2 == 0), " ", xs.find_if((x: int) -> bool
    x > 2).value(), " ", xs.position_if((x: int) -> bool
    x % 2 == 0).value())
  io::println(xs.fold((acumulado: int, valor: int) -> int
    acumulado + valor, 0))
  io::println(xs.map((x: int) -> int
    x * 2).join(","), " ", xs.filter((x: int) -> bool
    x % 2 == 0).join(","))
  mut copia = xs
  copia.transform((x: int) -> int
    x * 10)
  copia.fill(7)
  copia.swap(size_t::from(0), size_t::from(3))
  io::println(copia.join(","))
`,
    );
    expect(out).toBe("true true true\n2 3 1\n10\n2,4,6,8 2,4\n7,7,7,7\n");
  });

  test("std/array: la misma API sin mutar el tamaño", () => {
    const out = run_source(
      "array",
      `invoke "std/io"
invoke "std/array"
invoke "std/vector"

main = ->
  valores: array<int, 4> = array<int, 4>[4, 1, 3, 2]
  io::println(valores.sum(), " ", valores.product(), " ", valores.min().value(), " ", valores.max().value())
  io::println(valores.to_vector().join(","), " ", valores.reversed().join(","), " ", valores.slice(size_t::from(1), size_t::from(3)).join(","))
  io::println(valores.join("-"), " ", valores.find_if((x: int) -> bool
    x % 2 == 0).value(), " ", valores.any((x: int) -> bool
    x > 3), " ", valores.all((x: int) -> bool
    x > 0), " ", valores.none((x: int) -> bool
    x > 9))
`,
    );
    expect(out).toBe("10 24 1 4\n4,1,3,2 2,3,1,4 1,3,2\n4-1-3-2 4 true true true\n");
  });

  test("std/map: inserción, actualización y fusión", () => {
    const out = run_source(
      "map",
      `invoke "std/io"
invoke "std/map"
invoke "std/vector"

main = ->
  mut m: map<string, int> = map{"b": 2, "a": 1}
  io::println(m.get_or_insert("c", 3), " ", m.get_or_insert("a", 9), " ", #m)
  io::println(m.update("a", (v: int) -> int
    v + 10), " ", m.update("z", (v: int) -> int
    v), " ", m.get("a").value())
  io::println(m.first_key().value(), " ", m.last_key().value(), " ", #m.entries())
  otro: map<string, int> = map{"a": 99, "d": 4}
  m.merge(ref(otro))
  io::println(m.get("a").value(), " ", m.get("d").value(), " ", #m)
  m.insert_or_assign("e", 5)
  io::println(m.keys().join(","), " ", m.values().join(","), " ", m.remove("b").value(), " ", m.contains_key("b"))
  m.retain((k: string, v: int) -> bool
    v > 4)
  io::println(m.keys().join(","))
`,
    );
    expect(out).toBe("3 1 3\ntrue false 11\na c 3\n11 4 4\na,b,c,d,e 11,2,3,4,5 2 false\na,e\n");
  });

  test("std/set: operaciones de conjuntos", () => {
    const out = run_source(
      "set",
      `invoke "std/io"
invoke "std/set"
invoke "std/vector"

main = ->
  mut s: set<int> = set{1, 2, 3}
  t: set<int> = set{2, 3}
  nueve: set<int> = set{9}
  io::println(s.is_superset(ref(t)), " ", s.is_disjoint(ref(nueve)), " ", s.first().value(), " ", s.last().value())
  io::println(s.union(ref(t)).to_vector().join(","), " ", s.intersection(ref(t)).to_vector().join(","))
  io::println(s.difference(ref(t)).to_vector().join(","), " ", s.symmetric_difference(ref(t)).to_vector().join(","))
  io::println(s.is_subset(ref(t)), " ", t.is_subset(ref(s)))
  uno: set<int> = set{1}
  s.remove_all(ref(uno))
  extras: vector<int> = [7, 8]
  s.extend(ref(extras))
  io::println(s.to_vector().join(","), " ", s.map((x: int) -> int
    x * 2).to_sorted_vector().join(","), " ", s.filter((x: int) -> bool
    x > 2).to_sorted_vector().join(","))
`,
    );
    expect(out).toBe("true true 1 3\n1,2,3 2,3\n1 1\nfalse true\n2,3,7,8 4,6,14,16 3,7,8\n");
  });

  test("std/optional: combinadores", () => {
    const out = run_source(
      "optional",
      `invoke "std/io"
invoke "std/optional"
invoke "std/vector"

main = ->
  valor: int? = 21
  vacio: int? = none
  io::println(valor.map((x: int) -> int
    x * 2).value(), " ", vacio.map((x: int) -> int
    x).is_empty())
  io::println(valor.and_then((x: int) -> int?
    if x > 10 then x + 1 else none).value())
  io::println(vacio.or_else_get(() -> int
    5), " ", valor.or_else_get(() -> int
    5), " ", valor.filter((x: int) -> bool
    x > 100).is_empty())
  otro: int? = 2
  par = valor.zip(otro).value()
  io::println(par.first, " ", par.second, " ", valor.any((x: int) -> bool
    x > 20), " ", valor.to_vector().join(","))
`,
    );
    expect(out).toBe("42 true\n22\n5 21 true\n21 2 true 21\n");
  });

  test("std/deque: doble extremo y adaptadores", () => {
    const out = run_source(
      "deque",
      `invoke "std/io"
invoke "std/deque"
invoke "std/vector"

main = ->
  mut d: deque<int> = deque<int>[2, 3]
  d.push_front(1)
  d.push(4)
  io::println(d.to_vector().join(","), " ", #d, " ", d.first().value(), " ", d.last().value())
  io::println(d.pop_front(), " ", d.pop(), " ", d.to_vector().join(","))
  d.insert_at(size_t::from(1), 9)
  io::println(d.to_vector().join(","), " ", d.remove_at(size_t::from(0)), " ", d.to_vector().join(","))
  io::println(d.contains(9), " ", d.index_of(9).value(), " ", d.join("|"), " ", d.get_or(size_t::from(9), -1))
`,
    );
    expect(out).toBe("1,2,3,4 4 1 4\n1 4 2,3\n2,9,3 2 9,3\ntrue 0 9|3 -1\n");
  });

  test("adaptadores y bitset", () => {
    const out = run_source(
      "adaptadores",
      `invoke "std/io"

main = ->
  mut s: stack<int> = stack<int>()
  s.push(1)
  s.push(2)
  io::println(s.size(), " ", s.top(), " ", s.pop(), " ", s.size())
  s.clear()
  io::println(s.is_empty())
  mut q: queue<int> = queue<int>()
  q.push(10)
  q.push(20)
  io::println(q.front(), " ", q.back(), " ", q.pop(), " ", q.size())
  q.clear()
  io::println(q.is_empty())
  mut pq: priority_queue<int> = priority_queue<int>()
  pq.push(5)
  pq.push(9)
  pq.push(7)
  io::println(pq.top(), " ", pq.pop(), " ", pq.size())
  mut bits = bitset<8>(0)
  bits.set(size_t::from(1))
  bits.set(size_t::from(3))
  io::println(bits.test(size_t::from(1)), " ", bits.count(), " ", bits.to_string(), " ", bits.all(), " ", bits.any(), " ", bits.none())
  bits.flip(size_t::from(1))
  bits.reset(size_t::from(3))
  io::println(bits.count(), " ", bits.to_uint64())
`,
    );
    expect(out).toBe("2 2 2 1\ntrue\n10 20 10 1\ntrue\n9 9 2\ntrue 2 00001010 false true false\n0 0\n");
  });

  test("std/ordering y tuplas", () => {
    const out = run_source(
      "ordering_tuple",
      `invoke "std/io"
invoke "std/ordering"
invoke "std/tuple"

main = ->
  mayor = 5 <=> 3
  igual = 3 <=> 3
  io::println(mayor.to_int(), " ", igual.to_int(), " ", igual.then(mayor).to_int())
  t: tuple<int, string, double> = (1, "dos", 3.5)
  io::println(t.first(), ",", t.second(), ",", t.third(), ",", t.len())
  pareja: pair<int, string> = (7, "siete")
  io::println(pareja.first, ",", pareja.second)
`,
    );
    expect(out).toBe("1 0 1\n1,dos,3.5,3\n7,siete\n");
  });

  test("mutar el contenedor durante el for sigue siendo un error", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_con_exclusivo_"));
    const file = join(dir, "main.pengu");
    writeFileSync(
      file,
      `invoke "std/vector"

main = ->
  mut xs: vector<int> = [1, 2]
  for x in xs
    xs.push(x)
`,
    );
    const result = compile_file(file);
    expect(result.ok).toBe(false);
    expect(result.diagnostics[0]?.code).toBe("E0602");
    expect(result.diagnostics[0]?.message).toContain("mientras se recorre");
  });
});
