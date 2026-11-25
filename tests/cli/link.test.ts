// G8: `--link raylib` significa `-lraylib`; una bandera que empieza por `-`
// se acepta tal cual, y las rutas a objetos o archivos no se tocan.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { parse_args } from "../../src/cli/args.ts";
import { link_flag, link_flags } from "../../src/driver/link.ts";
import { compile_file } from "../../src/driver/compile.ts";
import { build_object, c_compiler } from "../bindgen/native.ts";

describe("opciones de enlace", () => {
  test("un nombre suelto se convierte en -lnombre", () => {
    expect(link_flag("raylib")).toBe("-lraylib");
    expect(link_flag("m")).toBe("-lm");
    expect(link_flag(" -lm ")).toBe("-lm");
    expect(link_flag("/tmp/demo.o")).toBe("/tmp/demo.o");
    expect(link_flag("libdemo.a")).toBe("libdemo.a");
    expect(link_flag("./demo.so")).toBe("./demo.so");
    expect(link_flags(["raylib", "-lraylib", "m", "m"])).toEqual(["-lraylib", "-lm"]);
  });

  test("--link acepta un valor que empieza por guion", () => {
    expect(parse_args(["build", "x.pengu", "--link", "-lm"]).flags.link).toBe("-lm");
    expect(parse_args(["build", "x.pengu", "--link=-lm"]).flags.link).toBe("-lm");
    expect(parse_args(["build", "x.pengu", "--link", "raylib"]).flags.link).toBe("raylib");
    // Un `--` posterior sigue siendo otra bandera, no un valor de `--link`.
    const args = parse_args(["build", "x.pengu", "--link", "--out", "dist"]);
    expect(args.flags.link).toBe(true);
    expect(args.flags.out).toBe("dist");
  });

  test("el driver enlaza con -l a partir de un nombre y una ruta -L", () => {
    const compiler = c_compiler();
    if (compiler === undefined) return;
    if (spawnSync("ar", ["--version"], { encoding: "utf8" }).status !== 0) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-link-"));
    try {
      const object = build_object(compiler, dir, "triple", "int triple(int x) { return 3 * x; }\n");
      const archive = join(dir, "libpengudemo.a");
      expect(spawnSync("ar", ["rcs", archive, object], { encoding: "utf8" }).status).toBe(0);

      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          "",
          'extern "C"',
          "  triple = (x: int) -> int",
          "",
          "main = -> void",
          '  io::println("triple(7) = #{triple(7)}")',
          "",
        ].join("\n"),
      );

      // "pengudemo" no lleva guion: el driver debe normalizarlo a -lpengudemo.
      const result = compile_file(source, { link: [`-L${dir}`, "pengudemo"] });
      if (!result.ok) throw new Error(result.output);
      if (result.binary_path === undefined) throw new Error("sin binario");

      const run = spawnSync(result.binary_path, [], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toContain("triple(7) = 21");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60000);
});
