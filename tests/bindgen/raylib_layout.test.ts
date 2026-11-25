// F3 contra raylib instalada: los tipos generados por bindgen tienen el
// mismo tamaño y alineación que los de C, y las funciones enlazan.
//
// Si raylib no está instalada, la prueba se omite (no falla en máquinas
// sin ella).

import { describe, expect, test } from "bun:test";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { run_bindgen } from "../../src/cli/bindgen_command.ts";
import { parse_args } from "../../src/cli/args.ts";
import { run_size } from "../../src/cli/size_command.ts";
import { compile_file } from "../../src/driver/compile.ts";

const HEADER = "/usr/include/raylib.h";

function raylib_available(): boolean {
  return existsSync(HEADER) && spawnSync("pkg-config", ["--exists", "raylib"]).status === 0;
}

describe("raylib real", () => {
  test("los tipos generados conservan el layout de C y las llamadas enlazan", () => {
    if (!raylib_available()) return;
    const dir = mkdtempSync(join(tmpdir(), "pengu-raylib-f3-"));
    try {
      const binding = join(dir, "raylib.d.pengu");
      const generated = run_bindgen(parse_args(["bindgen", HEADER, "--out", binding, "--realm", "raylib"]));
      expect(generated.exit_code).toBe(0);
      expect(generated.output).toContain("función(es)");

      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          `invoke "${binding.replace(/\.pengu$/, "")}"`,
          "",
          "main = -> void",
          "  c = raylib::Color(255, 0, 0, 255)",
          "  apagado = raylib::Fade(c, 0.5)",
          "  r = raylib::Rectangle(0.0, 0.0, 10.0, 10.0)",
          "  toca = raylib::CheckCollisionRecs(r, raylib::Rectangle(5.0, 5.0, 2.0, 2.0))",
          '  io::println("fade: #{apagado.a} toca: #{toca}")',
          "",
        ].join("\n"),
      );
      const compiled = compile_file(source, { link: ["raylib"] });
      if (!compiled.ok) throw new Error(compiled.output || JSON.stringify(compiled.diagnostics));
      if (compiled.binary_path === undefined) throw new Error("sin binario");
      const run = spawnSync(compiled.binary_path, [], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toBe("fade: 127 toca: true\n");

      const size = run_size([source], { json: true });
      const parsed = JSON.parse(size.output) as {
        types: { name: string; size: number; align: number; fields: { name: string; offset?: number }[] }[];
      };
      const find = (name: string) => parsed.types.find((item) => item.name === `raylib::${name}`);
      const expected: Record<string, [number, number]> = {
        Vector2: [8, 4],
        Vector3: [12, 4],
        Color: [4, 1],
        Rectangle: [16, 4],
        Image: [24, 8],
        Camera3D: [44, 4],
        Matrix: [64, 4],
        Material: [40, 8],
        Model: [136, 8],
      };
      for (const [name, [bytes, align]] of Object.entries(expected)) {
        expect(find(name)?.size).toBe(bytes);
        expect(find(name)?.align).toBe(align);
      }
      const rectangle = find("Rectangle");
      expect(rectangle?.fields.find((field) => field.name === "width")?.offset).toBe(8);
      expect(rectangle?.fields.find((field) => field.name === "height")?.offset).toBe(12);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 120000);
});
