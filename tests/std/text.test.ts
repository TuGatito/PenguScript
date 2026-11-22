// Fase F3 del plan de la stdlib: texto (string, format y log).
//
// Como en F2, cada prueba compila y ejecuta un programa real: se comprueba el
// comportamiento de la API, no solo que el checker la acepte.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function compile_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_txt_${name}_`));
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

function run_source(name: string, source: string): string {
  const binary = compile_source(name, source);
  const run = spawnSync(binary, [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout;
}

function run_source_with_stderr(name: string, source: string): { stdout: string; stderr: string } {
  const binary = compile_source(name, source);
  const run = spawnSync(binary, [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return { stdout: run.stdout, stderr: run.stderr };
}

describe("texto", () => {
  test("std/string: búsqueda y reemplazo", () => {
    const out = run_source(
      "busqueda",
      `invoke "std/io"
invoke "std/string"

main = ->
  texto = "banana"
  io::println(texto.contains("nan"), " ", texto.find("an").value(), " ", texto.rfind("an").value())
  io::println(texto.find_from("an", 2).value(), " ", texto.count("an"), " ", texto.find("zz").is_none())
  io::println("a-b-c".replace("-", "+"), " ", "a-b-c".replace_first("-", "+"))
  io::println("abc".starts_with("ab"), " ", "abc".ends_with("bc"), " ", "abc".compare_ignore_case("ABC"))
`,
    );
    expect(out).toBe("true 1 3\n3 2 true\na+b+c a+b-c\ntrue true 0\n");
  });

  test("std/string: recorte, caja y prefijos", () => {
    const out = run_source(
      "recorte",
      `invoke "std/io"
invoke "std/string"

main = ->
  io::println("[#{"  hola  ".trim()}] [#{"  hola  ".trim_start()}] [#{"  hola  ".trim_end()}]")
  io::println("[#{"xxholaxx".trim_matches('x')}] [#{"xxholaxx".trim_start_matches('x')}]")
  io::println("hOLA".capitalize(), " ", "Hola".decapitalize(), " ", "hola mundo cruel".title_case())
  io::println("prefijo-resto".remove_prefix("prefijo-"), " ", "resto.txt".remove_suffix(".txt"))
  io::println("abc".remove_prefix("zzz"))
`,
    );
    expect(out).toBe("[hola] [hola  ] [  hola]\n[hola] [holaxx]\nHola hola Hola Mundo Cruel\nresto resto\nabc\n");
  });

  test("std/string: partes y UTF-8", () => {
    const out = run_source(
      "partes",
      `invoke "std/io"
invoke "std/string"
invoke "std/vector"

main = ->
  io::println("a,b,,c".split(",").join("|"), " ", "  a  bb   c ".split_whitespace().join("|"))
  io::println("a\\nb\\nc".split_lines().join("|"))
  io::println(#"abc".chars(), " ", #"abc".bytes(), " ", "año".char_count(), " ", #"año".bytes())
  io::println("abc".reverse(), " ", "año".reverse())
`,
    );
    expect(out).toBe("a|b||c a|bb|c\na|b|c\n3 3 3 4\ncba oña\n");
  });

  test("std/string: relleno y alineación", () => {
    const out = run_source(
      "relleno",
      `invoke "std/io"
invoke "std/string"
invoke "std/format"

main = ->
  io::println("[#{"7".pad_start(3)}] [#{"7".pad_start_with(3, '0')}] [#{"7".pad_end(3)}]")
  io::println("[#{"ab".pad_center(6)}] [#{"ab".pad_center_with(6, '*')}] [#{"abcdef".pad_start(3)}]")
  io::println("[#{format::pad_left("7", 3)}] [#{format::pad_right("7", 3)}] [#{format::center("ab", 6)}]")
`,
    );
    expect(out).toBe("[  7] [007] [7  ]\n[  ab  ] [**ab**] [abcdef]\n[  7] [7  ] [  ab  ]\n");
  });

  test("std/string: índices, cortes y conversiones", () => {
    const out = run_source(
      "cortes",
      `invoke "std/io"
invoke "std/string"
invoke "std/format"

main = ->
  io::println("ac".insert_at(1, "b"), " ", "abcdef".remove_range(2, 2), " ", "abcdef".truncate(3), " ", "abcdef".substring(1, 4))
  io::println("42".to_int().value_or(-1), " ", "4x".to_int().is_none(), " ", "2.5".to_double().value_or(0.0))
  io::println("true".to_bool().value_or(false), " ", "sí".to_bool().is_none())
  io::println(format::hex(255), " ", format::bin(5), " ", format::oct(8), " ", format::radix(-255, 16))
  io::println(format::separated(1234567, "."), " ", format::separated(-42, ","), " ", format::separated(12, ","))
`,
    );
    expect(out).toBe("abc abef abc bcd\n42 true 2.5\ntrue true\nff 101 10 -ff\n1.234.567 -42 12\n");
  });

  test("std/string: escape y desescape", () => {
    const out = run_source(
      "escape",
      `invoke "std/io"
invoke "std/string"

main = ->
  original = "a\\nb\\tc\\\\d"
  escapado = original.escape()
  io::println(escapado)
  io::println(escapado.unescape() == original, " ", escapado.unescape().char_count())
`,
    );
    expect(out).toBe("a\\nb\\tc\\\\d\ntrue 7\n");
  });

  test("std/format: template y join", () => {
    const out = run_source(
      "plantilla",
      `invoke "std/io"
invoke "std/format"
invoke "std/vector"

main = ->
  io::println(format::template("{} + {} = {}", 2, 3, 5))
  io::println(format::template("sin huecos"))
  io::println(format::template("{} y {}", "uno"))
  partes = ["uno", "dos", "tres"]
  io::println(format::join(ref(partes), ", "))
`,
    );
    expect(out).toBe("2 + 3 = 5\nsin huecos\nuno y \nuno, dos, tres\n");
  });

  test("std/log: niveles, filtro y marca de tiempo", () => {
    const { stdout, stderr } = run_source_with_stderr(
      "niveles",
      `invoke "std/io"
invoke "std/log"

main = ->
  log::set_level(log::Level::Warn)
  log::debug("no sale")
  log::info("tampoco")
  log::warn("sale")
  log::error("sale mas")
  io::println("nivel: #{log::level().name()} #{log::level().to_int()}")
  io::println("debug: #{log::enabled(log::Level::Debug)} error: #{log::enabled(log::Level::Error)}")
`,
    );
    expect(stdout).toBe("nivel: warn 2\ndebug: false error: true\n");
    expect(stderr).toBe("[warn] sale\n[error] sale mas\n");
  });
});
