// El catálogo `std/js/*_generated.d.pengu` está comprometido en el repo: estos
// tests garantizan que sigue al día con `third_party/dts` y que el texto
// generado se parsea sin diagnósticos (si el parser no lo acepta, el catálogo
// no sirve para nada).

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse_text } from "../../src/frontend/parser.ts";
import { bind_dts_file } from "../../src/tsbindgen/collect.ts";
import { TARGETS } from "../../scripts/gen_std_js.ts";

const ROOT = join(import.meta.dir, "../..");
const DTS = join(ROOT, "third_party", "dts");

function parsea_limpio(text: string): readonly string[] {
  const result = parse_text("<catalogo>", text);
  return result.diagnostics.map((item) => `${item.code} ${item.message}`);
}

describe("catálogo generado comprometido", () => {
  test("los archivos están al día con third_party/dts", () => {
    for (const target of TARGETS) {
      const source = join(DTS, target.lib);
      const text = readFileSync(join(ROOT, target.out), "utf8");
      const fresh = bind_dts_file(source, {
        realm: target.realm,
        source: target.lib,
        invokes: target.invokes,
        only: target.only,
      });
      expect(fresh.text).toBe(text);
    }
  }, 600_000);

  test("cada archivo se parsea sin diagnósticos", () => {
    for (const target of TARGETS) {
      const text = readFileSync(join(ROOT, target.out), "utf8");
      expect({ archivo: target.out, errores: parsea_limpio(text) }).toEqual({ archivo: target.out, errores: [] });
    }
  }, 120_000);

  test("el catálogo del DOM cubre lo que promete el plan", () => {
    const text = readFileSync(join(ROOT, "std/js/dom_generated.d.pengu"), "utf8");
    const tipos = text.match(/^host js::/gm) ?? [];
    const globales = text.match(/^host global /gm) ?? [];
    expect(tipos.length).toBeGreaterThan(1_000);
    expect(globales.length).toBeGreaterThan(100);
    for (const nombre of ["js::Document", "js::Element", "js::HTMLElement", "js::HTMLCanvasElement", "js::Event"]) {
      expect(text).toContain(`host ${nombre}`);
    }
  });

  test("los módulos por dominio traen sus globales", () => {
    const storage = readFileSync(join(ROOT, "std/js/storage_generated.d.pengu"), "utf8");
    expect(storage).toContain("host global localStorage");
    expect(storage).toContain("host js::Storage");
    const fetch_domain = readFileSync(join(ROOT, "std/js/fetch_generated.d.pengu"), "utf8");
    expect(fetch_domain).toContain("host js::Response");
    const performance = readFileSync(join(ROOT, "std/js/performance_generated.d.pengu"), "utf8");
    expect(performance).toContain("host global performance");
  });
});
