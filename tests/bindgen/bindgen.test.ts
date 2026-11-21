import { describe, expect, test } from "bun:test";
import { readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { run_bindgen } from "../../src/cli/bindgen_command.ts";
import { parse_args } from "../../src/cli/args.ts";
import { parse_text } from "../../src/frontend/parser.ts";
import { find_clang } from "../../src/bindgen/clang_ast.ts";

const fixtures = new URL("../fixtures/native", import.meta.url).pathname;
const out = join(fixtures, "demo.d.pengu");

describe("bindgen", () => {
  test("genera enlaces a partir de una cabecera C", () => {
    if (find_clang() === undefined) return;
    const result = run_bindgen(parse_args(["bindgen", fixtures + "/demo.h", "--out", out, "--realm", "demo"]));
    expect(result.exit_code).toBe(0);
    const text = readFileSync(out, "utf8");
    expect(text).toContain("realm demo");
    expect(text).toContain("suma = (a: double, b: double) -> double");
    expect(text).toContain("contar = (texto: string) -> int");
    expect(text).toContain("maximo = (a: int, b: int) -> int");

    const parsed = parse_text(out, text);
    expect(parsed.diagnostics).toEqual([]);
    rmSync(out);
  });
});
