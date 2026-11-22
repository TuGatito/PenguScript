// La biblioteca estándar viaja dentro del binario: si se edita `std/` y no se
// regenera `std_bundle.ts`, el ejecutable instalado usaría una copia vieja.

import { describe, expect, test } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { STD_SOURCES } from "../../src/project/std_bundle.ts";
import { is_bundled, read_source } from "../../src/project/paths.ts";

const root = join(import.meta.dir, "..", "..");

describe("std empotrado", () => {
  test("std_bundle.ts está al día", () => {
    const result = spawnSync("bun", ["run", "scripts/embed_std.ts", "--check"], { cwd: root, encoding: "utf8" });
    expect(result.status).toBe(0);
  });

  test("cada archivo de std existe en el paquete", () => {
    const files = readdirSync(join(root, "std")).filter((name) => name.endsWith(".pengu"));
    for (const name of files) expect(STD_SOURCES[`std/${name}`]).toBeDefined();
  });

  test("read_source devuelve el mismo texto que el disco", () => {
    const virtual = "std:std/string.pengu";
    expect(is_bundled(virtual)).toBe(true);
    expect(read_source(virtual)).toBe(readFileSync(join(root, "std", "string.pengu"), "utf8"));
    expect(read_source(join(root, "std", "string.pengu"))).toBeUndefined();
  });

  test("un archivo normal no es empotrado", () => {
    expect(is_bundled(join(root, "examples", "01_hello", "main.pengu"))).toBe(false);
  });
});
