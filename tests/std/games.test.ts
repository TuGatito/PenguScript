// Fase F6 del plan de la stdlib: juegos (geometría, easing, noise, color y física).
//
// Cada prueba compila y ejecuta un programa real. Las cifras con decimales se
// imprimen con `format::fixed` para que la salida sea estable.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_games_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output);
  }
  const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout ?? "";
}

describe("geometría", () => {
  test("vectores: operaciones, operadores y normalización", () => {
    const output = run_source(
      "vec",
      `invoke "std/io"
invoke "std/math"
invoke "std/format"
invoke "std/geometry"

main = ->
  a = geometry::vec2(3.0, 4.0)
  b = geometry::vec2(1.0, 2.0)
  io::println("len: #{format::fixed(a.length(), 3)}")
  io::println("dot: #{format::fixed(a.dot(b), 3)}")
  io::println("cross: #{format::fixed(a.cross(b), 3)}")
  io::println("norm: #{a.normalized()}")
  io::println("norm_len: #{format::fixed(a.normalized().length(), 3)}")
  io::println("sum: #{a + b} diff: #{a - b} escala: #{a * 2.0}")
  io::println("dist: #{format::fixed(a.distance_to(b), 3)}")
  io::println("rot: #{format::fixed(a.rotated(math::pi / 2.0).x, 3)} #{format::fixed(a.rotated(math::pi / 2.0).y, 3)}")
  io::println("¿iguales?: #{a.equals(geometry::vec2(3.0, 4.0))}")
`,
    );
    expect(output).toContain("len: 5.000");
    expect(output).toContain("dot: 11.000");
    expect(output).toContain("cross: 2.000");
    expect(output).toContain("norm: (0.6, 0.8)");
    expect(output).toContain("norm_len: 1.000");
    expect(output).toContain("sum: (4, 6) diff: (2, 2) escala: (6, 8)");
    expect(output).toContain("dist: 2.828");
    expect(output).toContain("rot: -4.000 3.000");
    expect(output).toContain("¿iguales?: true");
  });

  test("rectángulos: área, centro, intersección y unión", () => {
    const output = run_source(
      "rect",
      `invoke "std/io"
invoke "std/format"
invoke "std/geometry"

main = ->
  caja = geometry::rect(0.0, 0.0, 10.0, 10.0)
  otra = geometry::rect(5.0, 5.0, 5.0, 5.0)
  io::println("area: #{format::fixed(caja.area(), 3)}")
  io::println("centro: #{caja.center()}")
  io::println("esquina: #{caja.right()} #{caja.bottom()}")
  io::println("cruzan: #{caja.intersects(otra)}")
  io::println("inter: #{caja.intersection(otra).value_or(geometry::rect(0.0, 0.0, 0.0, 0.0))}")
  io::println("union: #{caja.union(otra)}")
  io::println("contiene: #{caja.contains(geometry::vec2(5.0, 5.0))}")
  io::println("expandido: #{caja.expanded(2.0)}")
  io::println("vacio: #{geometry::rect(0.0, 0.0, 0.0, 0.0).is_empty()}")
`,
    );
    expect(output).toContain("area: 100.000");
    expect(output).toContain("centro: (5, 5)");
    expect(output).toContain("esquina: 10 10");
    expect(output).toContain("cruzan: true");
    expect(output).toContain("inter: Rect(5, 5, 5, 5)");
    expect(output).toContain("union: Rect(0, 0, 10, 10)");
    expect(output).toContain("contiene: true");
    expect(output).toContain("expandido: Rect(-2, -2, 14, 14)");
    expect(output).toContain("vacio: true");
  });

  test("transformaciones: aplicar y deshacer", () => {
    const output = run_source(
      "transform",
      `invoke "std/io"
invoke "std/math"
invoke "std/format"
invoke "std/geometry"

main = ->
  t = geometry::Transform2D(geometry::vec2(10.0, 0.0), math::pi / 2.0, geometry::vec2(2.0, 2.0))
  aplicado = t.apply(geometry::vec2(3.0, 0.0))
  io::println("apply: #{format::fixed(aplicado.x, 3)} #{format::fixed(aplicado.y, 3)}")
  inverso = t.inverse_apply(geometry::vec2(10.0, 2.0))
  io::println("inverse: #{format::fixed(inverso.x, 3)} #{format::fixed(inverso.y, 3)}")
  io::println("direccion: #{format::fixed(t.apply_direction(geometry::vec2(0.0, 1.0)).length(), 3)}")
`,
    );
    expect(output).toContain("apply: 10.000 6.000");
    expect(output).toContain("inverse: 1.000 0.000");
    expect(output).toContain("direccion: 2.000");
  });
});

describe("animación y color", () => {
  test("easing: extremos y curvas", () => {
    const output = run_source(
      "easing",
      `invoke "std/io"
invoke "std/format"
invoke "std/easing"

main = ->
  io::println("q_in: #{format::fixed(easing::quadratic_in(0.25), 3)}")
  io::println("q_out: #{format::fixed(easing::quadratic_out(0.25), 3)}")
  io::println("q_in_out: #{format::fixed(easing::quadratic_in_out(0.25), 3)}")
  io::println("inicio: #{easing::linear(0.0)} fin: #{easing::linear(1.0)}")
  io::println("bounce: #{easing::bounce_out(0.0)} #{easing::bounce_out(1.0)}")
  io::println("smooth: #{format::fixed(easing::smoothstep(0.0, 1.0, 0.5), 3)}")
  io::println("ping: #{format::fixed(easing::ping_pong(1.25), 3)}")
`,
    );
    expect(output).toContain("q_in: 0.062");
    expect(output).toContain("q_out: 0.438");
    expect(output).toContain("q_in_out: 0.125");
    expect(output).toContain("inicio: 0 fin: 1");
    expect(output).toContain("bounce: 0 1");
    expect(output).toContain("smooth: 0.500");
    expect(output).toContain("ping: 0.750");
  });

  test("noise: determinista y en rango", () => {
    const output = run_source(
      "noise",
      `invoke "std/io"
invoke "std/format"
invoke "std/noise"

main = ->
  primero = noise::value_2d(1.5, 2.5, 7)
  segundo = noise::value_2d(1.5, 2.5, 7)
  io::println("determinista: #{primero == segundo}")
  io::println("rango: #{primero >= 0.0 and primero <= 1.0}")
  io::println("cero octavas: #{noise::fractal_2d(0.5, 0.5, 0, 1)}")
  io::println("fractal: #{format::fixed(noise::fractal_2d(0.5, 0.5, 3, 1), 3)}")
  io::println("con semilla: #{format::fixed(noise::value_2d(1.5, 2.5, 99), 3)}")
`,
    );
    expect(output).toContain("determinista: true");
    expect(output).toContain("rango: true");
    expect(output).toContain("cero octavas: 0");
    expect(output).toContain("fractal: ");
    expect(output).toContain("con semilla: ");
  });

  test("color: hex, mezcla, hsv y alpha", () => {
    const output = run_source(
      "color",
      `invoke "std/io"
invoke "std/color"

main = ->
  rojo = color::from_hex(0xFF0000)
  azul = color::from_hex(0x0000FF)
  io::println("hex: #{rojo.to_hex()} rgba: #{rojo.to_hex_rgba()}")
  io::println("mezcla: #{rojo.lerp(azul, 0.5).to_hex()}")
  io::println("rgb8: #{rojo.red8()} #{rojo.green8()} #{rojo.blue8()}")
  io::println("hsv: #{color::from_hsv(120.0, 1.0, 1.0).to_hex()}")
  io::println("alpha: #{rojo.with_alpha(0.5).to_hex_rgba()}")
  io::println("invertido: #{color::from_hex(0x00FFFF).inverted().to_hex()}")
  io::println("limpio: #{color::rgb(2.0, -1.0, 0.5).clamped()}")
`,
    );
    expect(output).toContain("hex: #ff0000 rgba: #ff0000ff");
    expect(output).toContain("mezcla: #800080");
    expect(output).toContain("rgb8: 255 0 0");
    expect(output).toContain("hsv: #00ff00");
    expect(output).toContain("alpha: #ff000080");
    expect(output).toContain("invertido: #ff0000");
    expect(output).toContain("limpio: Color(1, 0, 0.5, 1)");
  });
});

describe("física", () => {
  test("gravedad, integración y rebote", () => {
    const output = run_source(
      "physics",
      `invoke "std/io"
invoke "std/format"
invoke "std/geometry"
invoke "std/physics"

main = ->
  mut cuerpo = physics::body_at(geometry::Vec2(0.0, 0.0))
  cuerpo.apply_gravity(geometry::Vec2(0.0, 10.0), 1.0)
  io::println("vel: #{cuerpo.velocity}")
  cuerpo.integrate(1.0)
  io::println("pos: #{cuerpo.position}")
  cuerpo.position = geometry::Vec2(0.0, 5.0)
  cuerpo.velocity = geometry::Vec2(3.0, -4.0)
  cuerpo.bounce_floor(10.0, 0.5)
  io::println("rebote: #{cuerpo.velocity}")
  mut copia = physics::step(physics::body_moving(geometry::Vec2(0.0, 0.0), geometry::Vec2(0.0, 0.0)), geometry::Vec2(0.0, 10.0), 0.0, 1.0)
  io::println("paso: #{copia.velocity} #{copia.position}")
  io::println("energia: #{format::fixed(copia.kinetic_energy(), 3)}")
  copia.stop()
  io::println("parado: #{copia.is_moving()}")
  io::println("impulso: #{physics::gravity_force(2.0, geometry::Vec2(0.0, 10.0))}")
`,
    );
    expect(output).toContain("vel: (0, 10)");
    expect(output).toContain("pos: (0, 10)");
    expect(output).toContain("rebote: (3, 2)");
    expect(output).toContain("paso: (0, 10) (0, 10)");
    expect(output).toContain("energia: 50.000");
    expect(output).toContain("parado: false");
    expect(output).toContain("impulso: (0, 20)");
  });
});
