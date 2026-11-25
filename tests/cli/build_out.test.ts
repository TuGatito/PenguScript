// P0: `-o <ruta>` copia el binario fuera de la caché. La caché se reutiliza
// entre compilaciones, así que la copia tiene que ocurrir también cuando la
// compilación sale "sin cambios".

import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse_args } from "../../src/cli/args.ts";
import { run_build } from "../../src/cli/build_command.ts";

const HELLO = `invoke "std/io"

main = ->
  io::println("hola -o")
`;

function project(): string {
  const dir = mkdtempSync(join(tmpdir(), "pengu_out_"));
  const file = join(dir, "main.pengu");
  writeFileSync(file, HELLO);
  return file;
}

describe("build -o", () => {
  test("el binario aparece en la ruta pedida, también con caché", () => {
    const file = project();
    const dir = join(file, "..");
    const first = run_build(parse_args(["build", file, "-o", join(dir, "uno")]));
    expect(first.exit_code).toBe(0);
    const binary = join(dir, "uno");
    expect(existsSync(binary)).toBe(true);
    const run = spawnSync(binary, [], { encoding: "utf8" });
    expect(run.stdout.trim()).toBe("hola -o");

    const second = run_build(parse_args(["build", file, "-o", join(dir, "dos")]));
    expect(second.exit_code).toBe(0);
    expect(second.output).toContain("sin cambios");
    expect(existsSync(join(dir, "dos"))).toBe(true);
  }, 60000);
});
