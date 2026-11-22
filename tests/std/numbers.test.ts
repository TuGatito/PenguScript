// Fase F1 del plan de la stdlib: el núcleo numérico.
//
// Cubre `std/int`, `std/double`, `std/float`, `std/long_double`,
// `std/integers` y `std/char` con programas que se compilan y ejecutan de
// verdad: lo que se prueba es el comportamiento, no que el checker acepte.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_num_${name}_`));
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

describe("núcleo numérico", () => {
  test("std/int: división, módulo y utilidades de enteros", () => {
    const out = run_source(
      "int",
      `invoke "std/io"
invoke "std/int"

main = ->
  io::println((-7).div_floor(2), " ", (-7).mod_floor(2), " ", 7.div_ceil(2), " ", (-7).mod_euclid(3))
  io::println(3.wrap(0, 5), " ", 7.wrap(0, 5), " ", (-1).wrap(0, 5), " ", 10.next_multiple_of(4))
  io::println(3.abs_diff(10), " ", 1024.digits(), " ", 1024.is_power_of_two(), " ", 2.pow(10))
  io::println(255.to_radix(16), " ", (-255).to_radix(16), " ", 42.between(0, 100), " ", 42.sign())
`,
    );
    expect(out).toBe("-4 1 4 2\n3 2 4 12\n7 4 true 1024\nff -ff true 1\n");
  });

  test("std/double: precisión, redondeo y utilidades", () => {
    const out = run_source(
      "double",
      `invoke "std/io"
invoke "std/double"

main = ->
  tercio = 1.0 / 3.0
  io::println(tercio.to_fixed(4), " ", tercio.to_scientific(3), " ", (2.5).round(), " ", (-2.5).fract())
  io::println(3.0.hypot(4.0), " ", (-7.0).signum(), " ", 10.0.lerp(20.0, 0.25), " ", (1.0 / 3.0).approx_eq(0.3333333333))
  io::println(180.0.to_radians().to_fixed(3), " ", 3.141592653589793.to_degrees().to_fixed(1), " ", 2.7.to_int().value_or(0))
`,
    );
    expect(out).toBe("0.3333 3.333e-01 3 0.5\n5 -1 12.5 true\n3.142 180.0 2\n");
  });

  test("std/float y std/long_double: misma superficie", () => {
    const out = run_source(
      "float",
      `invoke "std/io"
invoke "std/float"
invoke "std/long_double"

main = ->
  f: float = float::from(2.0)
  io::println(f.sqrt().to_fixed(3), " ", f.pow(float::from(3.0)).to_fixed(1), " ", f.to_double())
  g: long double = 2.0 as long double
  io::println(g.sqrt().to_fixed(3), " ", g.pow(3.0 as long double).to_fixed(1), " ", g.to_double())
`,
    );
    expect(out).toBe("1.414 8.0 2\n1.414 8.0 2\n");
  });

  test("std/integers: los anchos fijos tienen límites y métodos", () => {
    const out = run_source(
      "integers",
      `invoke "std/io"
invoke "std/integers"

main = ->
  a: int8_t = 100
  io::println(a.max_value(), " ", a.min_value(), " ", a.is_even(), " ", a.abs())
  b: uint8_t = 200
  io::println(b.max_value(), " ", b.to_double(), " ", b.to_int().value_or(0))
  c: int64_t = -7
  io::println(c.abs(), " ", c.sign(), " ", c.clamp(-3, 3), " ", c.to_uint64().is_none())
`,
    );
    expect(out).toBe("127 -128 true 100\n255 200 200\n7 -1 -3 true\n");
  });

  test("std/char: clasificación y conversión de caja", () => {
    const out = run_source(
      "char",
      `invoke "std/io"
invoke "std/char"

main = ->
  io::println('a'.is_alpha(), " ", '7'.is_digit(), " ", 'A'.is_upper(), " ", 'a'.is_lower())
  io::println('a'.to_upper(), 'Z'.to_lower(), " ", 'a'.code(), " ", 'f'.hex_value())
  io::println(' '.is_space(), " ", '\\n'.is_control(), " ", '!'.is_punctuation(), " ", 'a'.is_alphanumeric())
`,
    );
    expect(out).toBe("true true true true\nAz 97 15\ntrue true true true\n");
  });
});
