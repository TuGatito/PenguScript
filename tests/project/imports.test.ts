// Regresión de F1 (`scratch/plan_lsp_errores.md`): una importación `std/…`
// que no resuelve no puede ignorarse en silencio. Antes, el grafo se saltaba
// el módulo y el usuario solo veía errores de miembros y de tipos («el tipo
// «char» no tiene el miembro «is_space»»), que apuntaban al sitio equivocado.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { make_sink } from "../../src/diagnostics/sink.ts";
import type { Diagnostic } from "../../src/diagnostics/diagnostic.ts";
import { CODES } from "../../src/diagnostics/codes.ts";
import { analyze_graph } from "../../src/driver/analyze.ts";

function analyze(files: Readonly<Record<string, string>>): readonly Diagnostic[] {
  const dir = mkdtempSync(join(tmpdir(), "pengu_project_"));
  for (const [name, text] of Object.entries(files)) writeFileSync(join(dir, name), text);
  const sink = make_sink({ max: 100 });
  analyze_graph(join(dir, "main.pengu"), sink);
  return sink.diagnostics;
}

function with_code(diagnostics: readonly Diagnostic[], code: string): readonly Diagnostic[] {
  return diagnostics.filter((diagnostic) => diagnostic.code === code);
}

describe("importaciones de std/", () => {
  test("una importación std/ inexistente se reporta como módulo no encontrado", () => {
    const diagnostics = analyze({
      "main.pengu": `invoke "std/nope"

main = -> void
  1
`,
    });
    const missing = with_code(diagnostics, CODES.module_not_found);
    expect(missing).toHaveLength(1);
    expect(missing[0]?.message).toContain("no se encuentra el módulo «std/nope»");
    expect(missing[0]?.span.start.line).toBe(1);
    expect(missing[0]?.notes?.[0]).toContain("«std/nope.pengu»");
  });

  test("un typo en un módulo de std/ ya no produce solo errores de miembros", () => {
    const diagnostics = analyze({
      "main.pengu": `invoke "std/chr"

main = -> void
  'a'.is_space()
`,
    });
    expect(diagnostics.map((diagnostic) => diagnostic.code)).toContain(CODES.module_not_found);
  });

  test("una importación std/ válida sigue resolviendo y sus métodos funcionan", () => {
    const diagnostics = analyze({
      "main.pengu": `invoke "std/char"

main = -> void
  'a'.is_space()
`,
    });
    expect(with_code(diagnostics, CODES.module_not_found)).toHaveLength(0);
    expect(with_code(diagnostics, CODES.unknown_method)).toHaveLength(0);
  });
});
