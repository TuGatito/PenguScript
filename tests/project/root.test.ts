// Regresión de F2 (`scratch/plan_lsp_errores.md`): la raíz del proyecto la
// fija `pengu.toml`. Sin manifiesto, la raíz es el directorio del archivo y un
// `invoke "lib/util"` desde `src/` no resuelve; con manifiesto, sí.

import { describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { make_sink } from "../../src/diagnostics/sink.ts";
import type { Diagnostic } from "../../src/diagnostics/diagnostic.ts";
import { CODES } from "../../src/diagnostics/codes.ts";
import { analyze_graph } from "../../src/driver/analyze.ts";
import { find_project_root } from "../../src/project/paths.ts";

const MANIFEST = `[package]
name = "demo"
version = "0.1.0"
entry = "src/main.pengu"
`;

const UTIL = `realm util

saludo = -> string
  "hola"
`;

const MAIN = `invoke "lib/util"

main = -> void
  util::saludo()
`;

function project(with_manifest: boolean): { dir: string; entry: string } {
  const dir = mkdtempSync(join(tmpdir(), "pengu_root_"));
  if (with_manifest) writeFileSync(join(dir, "pengu.toml"), MANIFEST);
  mkdirSync(join(dir, "lib"), { recursive: true });
  mkdirSync(join(dir, "src"), { recursive: true });
  writeFileSync(join(dir, "lib", "util.pengu"), UTIL);
  const entry = join(dir, "src", "main.pengu");
  writeFileSync(entry, MAIN);
  return { dir, entry };
}

function analyze(entry: string): readonly Diagnostic[] {
  const sink = make_sink({ max: 100 });
  analyze_graph(entry, sink);
  return sink.diagnostics;
}

describe("raíz del proyecto", () => {
  test("el repositorio tiene su propio pengu.toml en la raíz", () => {
    const root = join(import.meta.dir, "..", "..");
    expect(existsSync(join(root, "pengu.toml"))).toBe(true);
    expect(find_project_root(join(root, "examples", "16_herramienta"))).toBe(root);
    expect(find_project_root(join(root, "std"))).toBe(root);
  });

  test("find_project_root usa el directorio con pengu.toml", () => {
    const { dir, entry } = project(true);
    expect(find_project_root(join(dir, "src"))).toBe(dir);
    expect(find_project_root(join(dir, "src", "main.pengu"))).toBe(dir);
  });

  test("con manifiesto, una importación desde src/ resuelve en la raíz", () => {
    const { entry } = project(true);
    const diagnostics = analyze(entry);
    expect(diagnostics.filter((item) => item.code === CODES.module_not_found)).toHaveLength(0);
  });

  test("sin manifiesto, la importación no resuelve y se explica", () => {
    const { entry } = project(false);
    const missing = analyze(entry).filter((item) => item.code === CODES.module_not_found);
    expect(missing).toHaveLength(1);
    expect(missing[0]?.message).toContain("«lib/util»");
  });

  test("el std/ del proyecto gana a la copia empotrada", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_root_std_"));
    writeFileSync(join(dir, "pengu.toml"), MANIFEST);
    mkdirSync(join(dir, "std"), { recursive: true });
    writeFileSync(join(dir, "std", "propia.pengu"), `realm propia\n\nvalor = -> int\n  7\n`);
    const entry = join(dir, "main.pengu");
    writeFileSync(entry, `invoke "std/propia"\n\nmain = -> void\n  propia::valor()\n`);
    const diagnostics = analyze(entry);
    expect(diagnostics.filter((item) => item.code === CODES.module_not_found)).toHaveLength(0);
  });
});
