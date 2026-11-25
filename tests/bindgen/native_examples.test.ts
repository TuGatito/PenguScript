// F6: los ejemplos que usan los enlaces comprometidos compilan y enlazan
// contra las bibliotecas reales. No se ejecutan: abren una ventana.

import { describe, expect, test } from "bun:test";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { compile_file } from "../../src/driver/compile.ts";

const root = join(import.meta.dir, "..", "..");

function raylib_available(): boolean {
  const probe = spawnSync("pkg-config", ["--exists", "raylib"], { encoding: "utf8" });
  return probe.status === 0;
}

function raygui_header(): string | undefined {
  const path = join(root, "..", "raylib-pengu", "include", "raygui.h");
  return existsSync(path) ? path : undefined;
}

describe("ejemplos nativos", () => {
  test("examples/17_raylib compila y enlaza", () => {
    if (!raylib_available()) return;
    const source = join(root, "examples", "17_raylib", "main.pengu");
    const result = compile_file(source);
    expect(result.diagnostics.map((diagnostic) => diagnostic.message)).toEqual([]);
    expect(result.ok).toBe(true);
  }, 60_000);

  test("examples/18_raygui compila y enlaza con raygui", () => {
    const header = raygui_header();
    if (!raylib_available() || header === undefined) return;
    const dir = mkdtempSync(join(tmpdir(), "pengu-raygui-"));
    try {
      const object = join(dir, "raygui.o");
      const compiled = spawnSync(
        "cc",
        ["-c", "-DRAYGUI_IMPLEMENTATION", "-I", join(root, "..", "raylib-pengu", "include"), "-x", "c", header, "-o", object],
        { encoding: "utf8" },
      );
      expect(compiled.status).toBe(0);
      const source = join(root, "examples", "18_raygui", "main.pengu");
      const result = compile_file(source, { link: [object] });
      expect(result.diagnostics.map((diagnostic) => diagnostic.message)).toEqual([]);
      expect(result.ok).toBe(true);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 90_000);
});
