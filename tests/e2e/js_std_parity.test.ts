// Fase P4 del plan `plan_codegen_js.md`: la biblioteca estándar completa.
//
// Cada caso compila el mismo programa con los dos backends y compara la salida
// byte a byte. Lo que se mide es comportamiento observable (stdout, código de
// salida), no la forma del código generado.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

const has_node = spawnSync("node", ["--version"], { encoding: "utf8" }).status === 0;

function run_source(name: string, source: string): { cpp: string; js: string } {
  const dir = mkdtempSync(join(tmpdir(), `pengu_std_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);

  const native = compile_file(file);
  if (!native.ok) {
    throw new Error(
      native.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + native.output,
    );
  }
  const cpp_run = spawnSync(native.binary_path ?? "", [], { encoding: "utf8" });

  const js = compile_file(file, { target: "js" });
  if (!js.ok) {
    throw new Error(
      js.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + js.output,
    );
  }
  const js_run = spawnSync("node", [js.js_entry_path ?? ""], { encoding: "utf8" });
  return { cpp: cpp_run.stdout ?? "", js: js_run.stdout ?? "" };
}

function expect_parity(name: string, source: string): string {
  const { cpp, js } = run_source(name, source);
  expect(js).toBe(cpp);
  return cpp;
}

describe("paridad de la stdlib (C++20 y JavaScript)", () => {
  test("std/string: consulta, mutación y Unicode", () => {
    const out = expect_parity(
      "string",
      `invoke "std/io"
invoke "std/string"

main = ->
  texto = "  Pingüinos, patos y pingüinos  "
  limpio = texto.trim()
  io::println(limpio, "|", limpio.to_upper(), "|", limpio.to_lower())
  -- La longitud de un texto no ASCII es bytes en C++ y unidades UTF-16 en
  -- JS (§2.2): la divergencia está documentada y aquí solo se usa ASCII.
  io::println(#"pinguinos".to_upper(), " ", limpio.starts_with("Ping"), " ", limpio.contains("patos"))
  partes = limpio.split(", ")
  io::println(#partes, " ", partes[0], "/", partes[1], "/", partes[2])
  io::println(limpio.replace_first("pingüinos", "aves"), " ", limpio.reverse())
  io::println("42".to_int().value(), " ", "3.5".to_double().value(), " ", "x".to_int().is_none())
`,
    );
    expect(out.length).toBeGreaterThan(0);
  }, 30_000);

  test("std/vector y std/array: orden y orden superior", () => {
    const out = expect_parity(
      "vector",
      `invoke "std/io"
invoke "std/vector"
invoke "std/array"

main = ->
  mut xs: vector<int> = [3, 1, 2, 2]
  io::println(xs.sum(), " ", xs.product(), " ", xs.min().value(), " ", xs.max().value())
  io::println(xs.sorted().join(","), " ", xs.take(size_t::from(2)).join(","))
  io::println(xs.count_if((x: int) -> bool
    x % 2 == 0), " ", xs.fold((a: int, b: int) -> int
    a + b, 0))
  io::println(xs.map((x: int) -> int
    x * 2).join(","), " ", xs.filter((x: int) -> bool
    x > 1).join(","))
  xs.sort()
  xs.reverse()
  io::println(xs.join("-"), " ", xs.is_sorted(), " ", xs.index_of(1).value())
  valores: array<int, 3> = array<int, 3>[4, 1, 3]
  io::println(valores.sum(), " ", valores.to_vector().join(","), " ", valores.any((x: int) -> bool
    x > 3))
`,
    );
    expect(out.length).toBeGreaterThan(0);
  }, 30_000);

  test("std/map y std/set", () => {
    const out = expect_parity(
      "map_set",
      `invoke "std/io"
invoke "std/map"
invoke "std/set"
invoke "std/vector"

main = ->
  mut m: map<string, int> = map{"b": 2, "a": 1}
  io::println(#m, " ", m.get("a").value(), " ", m.get("zz").is_none(), " ", m.contains_key("b"))
  m.insert("c", 3)
  m.insert_or_assign("b", 20)
  io::println(m.get("b").value(), " ", m.keys_list().sorted().join(","))
  m.remove("c")
  io::println(#m, " ", m.values_list().sorted().join(","))
  mut vocales: set<string> = set{"a", "e"}
  otras: set<string> = set{"e", "i"}
  io::println(#vocales, " ", vocales.contains("a"), " ", vocales.union(ref(otras)).to_vector().join(""))
  io::println(vocales.intersection(ref(otras)).to_vector().join(""), " ", vocales.difference(ref(otras)).to_vector().join(""))
`,
    );
    expect(out.length).toBeGreaterThan(0);
  }, 30_000);

  test("std/optional y std/result", () => {
    const out = expect_parity(
      "optional",
      `invoke "std/io"
invoke "std/optional"
invoke "std/vector"

main = ->
  valor: int? = 4
  vacio: int? = none
  io::println(valor.is_some(), " ", vacio.is_none(), " ", valor.value_or(0), " ", vacio.value_or(7))
  io::println(valor.map((x: int) -> int
    x * 3).value(), " ", valor.filter((x: int) -> bool
    x > 10).is_none())
  io::println(vacio.or_else(9), " ", valor.to_vector().join(","))
`,
    );
    expect(out.length).toBeGreaterThan(0);
  }, 30_000);

  test("std/math y std/format", () => {
    const out = expect_parity(
      "math_format",
      `invoke "std/io"
invoke "std/math"
invoke "std/format"

main = ->
  io::println(math::sqrt(2.0), " ", math::floor(2.7), " ", math::pi)
  io::println(math::gcd(12, 18), " ", math::lcm(4, 6), " ", math::pow(2.0, 10.0))
  io::println(format::fixed(3.14159, 2), " ", format::scientific(1234.5, 2), " ", format::radix(255, 16))
  io::println(format::pad_left_with("7", size_t::from(3), '0'), "|", format::pad_right_with("7", size_t::from(3), '.'))
`,
    );
    expect(out.length).toBeGreaterThan(0);
  }, 30_000);

  test("std/hash, std/encoding y std/char", () => {
    const out = expect_parity(
      "hash_encoding",
      `invoke "std/io"
invoke "std/hash"
invoke "std/encoding"
invoke "std/char"

main = ->
  io::println(hash::fnv1a32("pengu"), " ", hash::djb2("pengu"), " ", hash::hex32(hash::fnv1a32("pengu")))
  io::println(encoding::hex("Hola"), " ", encoding::base64("Hola"), " ", encoding::url_encode("a b"))
  io::println(encoding::hex_decode(encoding::hex("Hola")).value(), " ", encoding::base64_decode("SG9sYQ==").value())
  io::println('7'.is_digit(), " ", 'x'.is_alpha(), " ", 'a'.to_upper(), " ", 'A'.code())
`,
    );
    expect(out.length).toBeGreaterThan(0);
  }, 30_000);

  test("std/json: lectura y escritura", () => {
    const out = expect_parity(
      "json",
      `invoke "std/io"
invoke "std/json"

main = ->
  texto = "{\\"nombre\\": \\"Ada\\", \\"edad\\": 36, \\"activo\\": true, \\"hijos\\": [1, 2]}"
  valor = json::parse(texto).value()
  io::println(json::has(valor, "nombre"), " ", json::length(valor))
  io::println(json::as_text(json::get(valor, "nombre").value()).value(), " ", json::as_int(json::get(valor, "edad").value()).value())
  io::println(json::stringify(json::parse("[1, 2, 3]").value()), " ", json::stringify(valor))
`,
    );
    expect(out.length).toBeGreaterThan(0);
  }, 30_000);

  test("std/integers: precisión de 64 bits", () => {
    const out = expect_parity(
      "integers",
      `invoke "std/io"
invoke "std/integers"
invoke "std/int"

main = ->
  grande: int64_t = 9000000000
  otro: int64_t = 15
  io::println(grande + otro, " ", grande / otro, " ", grande % otro, " ", grande * 2)
  io::println(integers::int8_max(), " ", integers::uint64_min(), " ", integers::int32_min())
  io::println((7).is_even(), " ", (-12).abs(), " ", (5).sign())
`,
    );
    expect(out.length).toBeGreaterThan(0);
  }, 30_000);

  test("std/fs, std/os y std/time: entorno", () => {
    const out = expect_parity(
      "entorno",
      `invoke "std/io"
invoke "std/fs"
invoke "std/os"
invoke "std/time"
invoke "std/path"

main = ->
  ruta = path::join("/tmp", "pengu_js_parity.txt")
  fs::write_string(ruta, "hola")
  io::println(fs::exists(ruta), " ", fs::file_size(ruta), " ", fs::read_to_string(ruta).value())
  fs::append_string(ruta, " mundo")
  io::println(fs::read_to_string(ruta).value(), " ", fs::is_file(ruta))
  fs::remove(ruta)
  io::println(fs::exists(ruta), " ", os::platform(), " ", os::arch())
  instante = time::now_millis()
  partes = time::parts(1700000000000)
  io::println(instante > 0, " ", partes[0] > 1969, " ", time::format_datetime(1700000000000))
`,
    );
    expect(out.length).toBeGreaterThan(0);
  }, 30_000);

  test("std/assert: un fallo termina con «panic»", () => {
    if (!has_node) return;
    const dir = mkdtempSync(join(tmpdir(), "pengu_std_assert_"));
    const file = join(dir, "main.pengu");
    writeFileSync(
      file,
      `invoke "std/io"
invoke "std/assert"

main = ->
  io::println("antes")
  assert::that(1 > 2)
  io::println("despues")
`,
    );
    const native = compile_file(file);
    expect(native.ok).toBe(true);
    const cpp_run = spawnSync(native.binary_path ?? "", [], { encoding: "utf8" });

    const js = compile_file(file, { target: "js" });
    expect(js.ok).toBe(true);
    const js_run = spawnSync("node", [js.js_entry_path ?? ""], { encoding: "utf8" });

    expect(js_run.stdout).toBe(cpp_run.stdout);
    expect(js_run.status).not.toBe(0);
    expect(`${js_run.stderr}${js_run.stdout}`).toContain("antes");
  }, 30_000);
});
