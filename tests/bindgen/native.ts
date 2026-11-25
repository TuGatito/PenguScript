// Utilidades para las pruebas de bindgen que enlazan con C real.

import { expect } from "bun:test";
import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { join } from "node:path";

export function c_compiler(): string | undefined {
  for (const candidate of ["cc", "gcc", "clang"]) {
    if (spawnSync(candidate, ["--version"], { encoding: "utf8" }).status === 0) return candidate;
  }
  return undefined;
}

// Compila `source` como objeto C y devuelve su ruta; falla la prueba si el
// compilador rechaza el fixture.
export function build_object(compiler: string, dir: string, name: string, source: string): string {
  const c_file = join(dir, `${name}.c`);
  const object = join(dir, `${name}.o`);
  writeFileSync(c_file, source);
  const build = spawnSync(compiler, ["-c", "-O1", "-o", object, c_file], { encoding: "utf8" });
  expect(build.status).toBe(0);
  return object;
}
