// Prueba completa de bindgen: cabecera C → enlaces PenguScript → binario.

import { describe, expect, test } from "bun:test";
import { copyFileSync, mkdtempSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
import { run_bindgen } from "../../src/cli/bindgen_command.ts";
import { parse_args } from "../../src/cli/args.ts";
import { compile_file } from "../../src/driver/compile.ts";
import { find_clang } from "../../src/bindgen/clang_ast.ts";

const fixtures = new URL("../fixtures/native", import.meta.url).pathname;
const has_cc = spawnSync("gcc", ["--version"]).status === 0;

describe("bindgen de extremo a extremo", () => {
  test("genera enlaces, compila contra el objeto C y ejecuta", () => {
    if (!has_cc || find_clang() === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu_native_"));
    copyFileSync(join(fixtures, "demo.h"), join(dir, "demo.h"));
    copyFileSync(join(fixtures, "demo.c"), join(dir, "demo.c"));

    const object = join(dir, "demo.o");
    const cc = spawnSync("gcc", ["-c", "-o", object, join(dir, "demo.c")], { encoding: "utf8" });
    expect(cc.status).toBe(0);

    const bindings = run_bindgen(
      parse_args(["bindgen", join(dir, "demo.h"), "--out", join(dir, "demo.d.pengu"), "--realm", "demo"]),
    );
    expect(bindings.exit_code).toBe(0);

    const main = join(dir, "main.pengu");
    writeFileSync(
      main,
      `invoke "std/io"
invoke "./demo"

main = ->
  io::println("suma: #{demo::suma(1.5, 2.5)}")
  io::println("contar: #{demo::contar("hola")}")
  io::println("maximo: #{demo::maximo(4, 9)}")
`,
    );

    const result = compile_file(main, { link: [object] });
    if (!result.ok) {
      throw new Error(result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output);
    }
    const run = spawnSync(result.binary_path!, [], { encoding: "utf8" });
    expect(run.status).toBe(0);
    expect(run.stdout).toContain("suma: 4");
    expect(run.stdout).toContain("contar: 4");
    expect(run.stdout).toContain("maximo: 9");
  });
});
