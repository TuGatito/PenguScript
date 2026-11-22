// La referencia de la biblioteca estándar se genera desde el código.
//
// Si alguien añade un método a `std/` y olvida regenerar la documentación, esta
// prueba falla con la orden exacta que hay que ejecutar.

import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
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
});
