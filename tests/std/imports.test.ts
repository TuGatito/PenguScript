// `invoke {a, b as c} from "modulo"`: alias de símbolos y varias importaciones
// selectivas del mismo módulo.
//
// El alias es local al archivo y el código generado debe seguir llamando al
// símbolo real del módulo (`format::format`, `math::sqrt`), no al alias.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function build(name: string, source: string): ReturnType<typeof compile_file> {
  const dir = mkdtempSync(join(tmpdir(), `pengu_imports_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  return compile_file(file);
}

function run_source(name: string, source: string): string {
  const result = build(name, source);
  if (!result.ok) {
    throw new Error(result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output);
  }
  const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout ?? "";
}

describe("importaciones selectivas", () => {
  test("el alias funciona y el código llama al símbolo real", () => {
    const output = run_source(
      "alias",
      `invoke "std/io"
invoke {sqrt as raiz, pow as potencia} from "std/math"

main = ->
  io::println("raiz: #{raiz(16.0)}")
  io::println("potencia: #{potencia(2.0, 10.0)}")
`,
    );
    expect(output).toBe("raiz: 4\npotencia: 1024\n");
  });

  test("dos importaciones selectivas del mismo módulo se acumulan", () => {
    const output = run_source(
      "acumula",
      `invoke "std/io"
invoke {format as uno} from "std/format"
invoke {format as otro} from "std/format"

main = ->
  io::println("uno: #{uno("x", 1)}")
  io::println("otro: #{otro("y", 2)}")
`,
    );
    expect(output).toContain("uno: x1");
    expect(output).toContain("otro: y2");
  });

  test("importar un símbolo que no existe es un error", () => {
    const result = build(
      "desconocido",
      `invoke {no_existe} from "std/math"

main = ->
  1
`,
    );
    expect(result.ok).toBe(false);
    expect(result.diagnostics.some((item) => item.message.includes("no exporta «no_existe»"))).toBe(true);
  });
});
