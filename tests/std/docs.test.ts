// La referencia de la biblioteca estándar se genera desde el código.
//
// Si alguien añade un método a `std/` y olvida regenerar la documentación, esta
// prueba falla con la orden exacta que hay que ejecutar.

import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dir, "..", "..");

describe("documentación generada", () => {
  test("docs/stdlib_api.md está al día", () => {
    const result = spawnSync("bun", ["run", "scripts/gen_stdlib_docs.ts", "--check"], {
      cwd: root,
      encoding: "utf8",
    });
    expect(result.stdout + result.stderr).toContain("al día");
    expect(result.status).toBe(0);
  });

  test("docs/stdlib_js.md está al día", () => {
    const result = spawnSync("bun", ["run", "scripts/gen_stdlib_js_docs.ts", "--check"], {
      cwd: root,
      encoding: "utf8",
    });
    expect(result.stdout + result.stderr).toContain("al día");
    expect(result.status).toBe(0);
  });

  test("el catálogo del navegador se documenta entero", () => {
    const doc = readFileSync(join(root, "docs", "stdlib_js.md"), "utf8");
    // Un archivo de `std/js/` sin sección en la referencia pasaría inadvertido.
    const files = readdirSync(join(root, "std", "js")).filter((name) => name.endsWith(".pengu"));
    for (const file of files) {
      const name = file.replace(/\.(d\.)?pengu$/, "");
      expect(doc).toContain(`## \`std/js/${name}\``);
    }
    expect(doc).toContain("E0518");
  });
});
