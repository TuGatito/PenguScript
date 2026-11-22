// Fase F1: `std/math` completo, con las constantes y los intrínsecos de
// <cmath> que necesita un motor de física o de juegos.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_math_${name}_`));
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

describe("std/math", () => {
  test("constantes, trigonometría y aritmética entera", () => {
    const out = run_source(
      "consts",
      `invoke "std/io"
invoke "std/math"
invoke "std/int"
invoke "std/double"

main = ->
  io::println(math::pi.to_fixed(4), " ", math::tau.to_fixed(4), " ", math::e.to_fixed(4), " ", math::phi.to_fixed(4))
  io::println(math::sin(math::pi / 2.0).to_fixed(3), " ", math::cos(0.0).to_fixed(3), " ", math::atan2(1.0, 1.0).to_fixed(3))
  io::println(math::gcd(12, 18), " ", math::lcm(4, 6), " ", 2.pow(10), " ", math::cbrt(27.0).to_fixed(1))
  io::println(math::floor(-2.5), " ", math::ceil(-2.5), " ", math::round(-2.5), " ", math::trunc(-2.5))
`,
    );
    expect(out).toBe(
      "3.1416 6.2832 2.7183 1.6180\n1.000 1.000 0.785\n6 12 1024 3.0\n-3 -2 -3 -2\n",
    );
  });

  test("utilidades puras para física y juegos", () => {
    const out = run_source(
      "helpers",
      `invoke "std/io"
invoke "std/math"
invoke "std/double"

main = ->
  io::println(math::lerp(0.0, 10.0, 0.25), " ", math::inverse_lerp(0.0, 10.0, 2.5), " ", math::remap(5.0, 0.0, 10.0, 0.0, 100.0))
  io::println(math::clamp01(-1.0), " ", math::smoothstep(0.0, 1.0, 0.5), " ", math::wrap(7.5, 0.0, 5.0), " ", math::wrap_angle(3.0 * math::pi).to_fixed(3))
  io::println(math::deg_to_rad(180.0).to_fixed(3), " ", math::rad_to_deg(math::pi).to_fixed(1), " ", math::is_power_of_two(64), " ", math::next_power_of_two(100))
  io::println(math::ipow(2, 10), " ", math::align_up(13, 8), " ", math::min3(3, 1, 2), " ", math::max3(3, 1, 2), " ", math::average(2.0, 4.0))
  io::println(math::approx_eq(0.1 + 0.2, 0.3), " ", math::sign(-3.0), " ", math::is_finite(math::infinite()), " ", math::is_nan(math::not_a_number()))
`,
    );
    expect(out).toBe(
      "2.5 0.25 50\n0 0.5 2.5 -3.142\n3.142 180.0 true 128\n1024 16 1 3 3\ntrue -1 false true\n",
    );
  });

  test("aceptación: caída libre y rebote con math::lerp", () => {
    const out = run_source(
      "bounce",
      `invoke "std/io"
invoke "std/math"
invoke "std/double"

main = ->
  gravedad = 9.81
  altura = 10.0
  caida = math::sqrt(2.0 * altura / gravedad)
  rebote = math::sqrt(2.0 * (altura / 2.0) / gravedad)
  suavizado = math::lerp(altura, 0.0, math::smoothstep(0.0, 1.0, 0.5))
  io::println(caida.to_fixed(3), " ", rebote.to_fixed(3), " ", suavizado.to_fixed(3))
`,
    );
    expect(out).toBe("1.428 1.010 5.000\n");
  });
});
