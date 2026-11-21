// Enlazado con código nativo: `extern "C"` + objeto compilado aparte.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { compile_file } from "../../src/driver/compile.ts";

function has_c_compiler(): string | undefined {
  for (const candidate of ["gcc", "clang", "cc"]) {
    if (spawnSync(candidate, ["--version"], { encoding: "utf8" }).status === 0) return candidate;
  }
  return undefined;
}

describe("enlaces nativos", () => {
  test("llama a una función C mediante extern", () => {
    const cc = has_c_compiler();
    if (cc === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-ffi-"));
    try {
      const c_file = join(dir, "demo.c");
      const obj = join(dir, "demo.o");
      writeFileSync(c_file, "int triple(int x) { return 3 * x; }\n");
      const build = spawnSync(cc, ["-c", "-O1", "-o", obj, c_file], { encoding: "utf8" });
      expect(build.status).toBe(0);

      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          "",
          'extern "C"',
          "  triple = (x: int) -> int",
          "",
          "main = ->",
          '  io::println("triple(7) = #{triple(7)}")',
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: [obj] });
      expect(result.ok).toBe(true);
      if (result.binary_path === undefined) throw new Error("sin binario");

      const run = spawnSync(result.binary_path, [], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toContain("triple(7) = 21");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60000);
});
