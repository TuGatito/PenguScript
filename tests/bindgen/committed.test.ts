// F6: los enlaces comprometidos en `bindings/` siguen al día con sus
// cabeceras. `pengu bindgen --check` regenera en memoria y compara.

import { describe, expect, test } from "bun:test";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";

const root = join(import.meta.dir, "..", "..");
const main = join(root, "src", "main.ts");

interface BindgenRun {
  readonly status: number | null;
  readonly output: string;
}

function bindgen(args: readonly string[]): BindgenRun {
  const run = spawnSync("bun", ["run", main, "bindgen", ...args], { encoding: "utf8", cwd: root });
  return { status: run.status, output: `${run.stdout}${run.stderr}` };
}

function raylib_header(): string | undefined {
  for (const path of ["/usr/include/raylib.h", "/usr/local/include/raylib.h"]) {
    if (existsSync(path)) return path;
  }
  return undefined;
}

function raygui_header(): string | undefined {
  const path = join(root, "..", "raylib-pengu", "include", "raygui.h");
  return existsSync(path) ? path : undefined;
}

describe("enlaces comprometidos", () => {
  test("bindings/raylib está al día", () => {
    const header = raylib_header();
    if (header === undefined) return;
    const run = bindgen([
      header,
      "--realm", "raylib",
      "--link", "raylib",
      "--out", join(root, "bindings", "raylib", "raylib.d.pengu"),
      "--check",
    ]);
    expect(run.status).toBe(0);
    expect(run.output).toContain("al día");
  }, 60_000);

  test("bindings/raygui está al día", () => {
    const header = raygui_header();
    const raylib = raylib_header();
    if (header === undefined || raylib === undefined) return;
    const include = join(root, "..", "raylib-pengu", "include");
    const run = bindgen([
      header,
      "-I", include,
      "-I", "/usr/include",
      "--base", raylib,
      "--base-realm", "raylib",
      "--base-module", "../raylib/raylib.d",
      "--realm", "raygui",
      "--link", "raylib",
      "--out", join(root, "bindings", "raygui", "raygui.d.pengu"),
      "--check",
    ]);
    expect(run.status).toBe(0);
    expect(run.output).toContain("al día");
  }, 60_000);

  test("un archivo generado en otra plataforma se avisa", () => {
    const header = raylib_header();
    if (header === undefined) return;
    const dir = mkdtempSync(join(tmpdir(), "pengu-platform-"));
    try {
      const out = join(dir, "raylib.d.pengu");
      const committed = readFileSync(join(root, "bindings", "raylib", "raylib.d.pengu"), "utf8");
      writeFileSync(out, committed.replace(/-- Plataforma: [^\n]*/, "-- Plataforma: win32 x64 (LP64)."));
      const run = bindgen([header, "--realm", "raylib", "--link", "raylib", "--out", out, "--check"]);
      expect(run.status).toBe(1);
      expect(run.output).toContain("otra plataforma");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60_000);

  test("un archivo desactualizado falla y no se reescribe", () => {
    const header = raylib_header();
    if (header === undefined) return;
    const dir = mkdtempSync(join(tmpdir(), "pengu-check-"));
    try {
      const out = join(dir, "raylib.d.pengu");
      const committed = readFileSync(join(root, "bindings", "raylib", "raylib.d.pengu"), "utf8");
      writeFileSync(out, `${committed}-- modificado\n`);
      const run = bindgen([header, "--realm", "raylib", "--link", "raylib", "--out", out, "--check"]);
      expect(run.status).toBe(1);
      expect(run.output).toContain("desactualizado");
      expect(readFileSync(out, "utf8")).toBe(`${committed}-- modificado\n`);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60_000);
});
