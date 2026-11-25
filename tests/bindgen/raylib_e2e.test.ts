// F6: los enlaces comprometidos de `bindings/raylib` se usan de verdad desde
// PenguScript (tipos, constantes, structs por valor y enlace automático).

import { describe, expect, test } from "bun:test";
import { rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { compile_file } from "../../src/driver/compile.ts";

const root = join(import.meta.dir, "..", "..");

const SOURCE = [
  'invoke "std/io"',
  'invoke "std/random"',
  'invoke "../../bindings/raylib/raylib.d"',
  "",
  "main = -> void",
  "  color = raylib::Fade(raylib::LIGHTGRAY, 0.5)",
  "  io::println(color.r)",
  "  io::println(color.a)",
  "  set = raylib::Rectangle(0.0, 0.0, 10.0, 10.0)",
  "  punto = raylib::Vector2(5.0, 5.0)",
  "  io::println(raylib::CheckCollisionPointRec(punto, set))",
  "  random::seed(int64_t::from(7))",
  "  io::println(raylib::GetRandomValue(1, 10))",
  "",
].join("\n");

describe("raylib desde PenguScript", () => {
  test("usa los enlaces comprometidos y enlaza solo con link", () => {
    const probe = spawnSync("pkg-config", ["--exists", "raylib"], { encoding: "utf8" });
    if (probe.status !== 0) return;

    // El programa de prueba vive en `examples/17_raylib` para que
    // `../../bindings/raylib/raylib.d` resuelva desde ahí.
    const program = join(root, "examples", "17_raylib", ".pengu-e2e.pengu");
    writeFileSync(program, SOURCE);
    try {
      {
        const built = compile_file(program);
        expect(built.diagnostics.map((diagnostic) => diagnostic.message)).toEqual([]);
        const ran = spawnSync(built.binary_path as string, [], { encoding: "utf8" });
        expect(ran.status).toBe(0);
        // Fade(LIGHTGRAY, 0.5): 200→100; alpha 255→127.
        expect(ran.stdout).toBe("200\n127\ntrue\n4\n");
      }
    } finally {
      rmSync(program, { force: true });
    }
  }, 90_000);
});
