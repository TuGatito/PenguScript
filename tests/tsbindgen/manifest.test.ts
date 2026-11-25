// Integridad de los `.d.ts` comprometidos en `third_party/dts/`.
//
// El manifiesto es lo que hace reproducible a `pengu ts-bindgen` sin red ni
// `bun install`: si alguien edita un `.d.ts` a mano o cambia de versión de
// TypeScript sin regenerar el manifiesto, este test lo dice.

import { describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const dts_dir = join(root, "third_party", "dts");
const manifest_path = join(dts_dir, "MANIFEST.json");

interface ManifestFile {
  readonly name: string;
  readonly bytes: number;
  readonly sha256: string;
}

interface Manifest {
  readonly source: string;
  readonly version: string;
  readonly files: readonly ManifestFile[];
}

function sha256(bytes: Uint8Array): string {
  return createHash("sha256").update(bytes).digest("hex");
}

describe("third_party/dts", () => {
  test("tiene manifiesto y licencia", () => {
    expect(existsSync(manifest_path)).toBe(true);
    expect(existsSync(join(dts_dir, "LICENSE.txt"))).toBe(true);
  });

  test("el manifiesto coincide con los archivos", () => {
    const manifest = JSON.parse(readFileSync(manifest_path, "utf8")) as Manifest;
    const expected = new Set(manifest.files.map((file) => file.name));
    for (const file of manifest.files) {
      const bytes = readFileSync(join(dts_dir, file.name));
      expect(bytes.length).toBe(file.bytes);
      expect(sha256(bytes)).toBe(file.sha256);
    }
    const present = readdirSync(dts_dir).filter((name) => name.endsWith(".d.ts"));
    expect(new Set(present)).toEqual(expected);
  });

  test("están las librerías que necesita el navegador", () => {
    const manifest = JSON.parse(readFileSync(manifest_path, "utf8")) as Manifest;
    const names = manifest.files.map((file) => file.name);
    expect(names).toContain("lib.dom.d.ts");
    expect(names).toContain("lib.dom.iterable.d.ts");
    expect(names).toContain("lib.es2022.d.ts");
    expect(names).toContain("lib.es5.d.ts");
    expect(manifest.version).toBe("5.7.3");
  });
});
