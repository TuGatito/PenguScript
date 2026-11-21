// El CLI resuelve el archivo de entrada desde `pengu.toml` cuando no se
// pasan argumentos, y reporta E0005 (también en `--json`) si no existe.

import { describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const root = new URL("../..", import.meta.url).pathname;

function run_cli(cwd: string, argv: readonly string[]): { status: number | null; stdout: string } {
  const result = spawnSync("bun", ["run", join(root, "src/main.ts"), ...argv], { cwd, encoding: "utf8" });
  return { status: result.status, stdout: result.stdout };
}

describe("entrada del proyecto", () => {
  test("sin argumentos usa el entry de pengu.toml", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_project_"));
    mkdirSync(join(dir, "src"), { recursive: true });
    writeFileSync(join(dir, "pengu.toml"), '[package]\nname = "demo"\nentry = "src/main.pengu"\n');
    writeFileSync(join(dir, "src/main.pengu"), 'invoke "std/io"\n\nmain = ->\n  io::println("hola")\n');

    const result = run_cli(dir, ["check", "--json"]);
    expect(result.status).toBe(0);
    const payload = JSON.parse(result.stdout) as { ok: boolean; diagnostics: readonly unknown[] };
    expect(payload.ok).toBe(true);
    expect(payload.diagnostics).toEqual([]);
  });

  test("sin proyecto, un archivo ausente produce E0005 en --json", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_empty_"));
    const result = run_cli(dir, ["check", "--json"]);
    expect(result.status).toBe(1);
    const payload = JSON.parse(result.stdout) as { ok: boolean; diagnostics: readonly { code: string }[] };
    expect(payload.ok).toBe(false);
    expect(payload.diagnostics.map((item) => item.code)).toContain("E0005");
  });
});
