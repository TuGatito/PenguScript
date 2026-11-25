// F6: paridad de ABI con C/C++ en un tipo que mezcla unión, bitfields y
// arrays. El sondeo C++ imprime sizeof/alignof/offsetof y se compara con la
// medición real de `pengu size`.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { compile_file } from "../../src/driver/compile.ts";
import { run_size } from "../../src/cli/size_command.ts";

const C_SOURCE = [
  'extern "C" {',
  "union Dato { int entero; double real; void* puntero; };",
  "struct Mezcla { char etiqueta; Dato dato; unsigned int a:3; unsigned int b:5; float pesos[2]; };",
  "Mezcla crear() { Mezcla m; m.etiqueta = 'p'; m.dato.entero = 7; m.a = 3; m.b = 5; m.pesos[0] = 1.5f; m.pesos[1] = 2.5f; return m; }",
  "int leer(Mezcla m) { return m.dato.entero * 100 + (int)m.a * 10 + (int)m.b + (int)(m.pesos[0] + m.pesos[1]); }",
  "}",
  "",
].join("\n");

const PROBE = [
  "#include <cstddef>",
  "#include <cstdio>",
  C_SOURCE,
  "int main() {",
  `  std::printf("%zu %zu %zu %zu %zu\\n", sizeof(Mezcla), alignof(Mezcla),`,
  "    offsetof(Mezcla, etiqueta), offsetof(Mezcla, dato), offsetof(Mezcla, pesos));",
  "  return 0;",
  "}",
  "",
].join("\n");

const PENGU = [
  'invoke "std/io"',
  "",
  "meld Dato",
  "  entero: int",
  "  real: double",
  "  puntero: raw<void>",
  "",
  "rune Mezcla",
  "  etiqueta: char",
  "  dato: Dato",
  "  bits 3 a: uint32_t",
  "  bits 5 b: uint32_t",
  "  pesos: array<float, 2>",
  "",
  'extern "C"',
  "  crear = () -> Mezcla",
  "  leer = (m: Mezcla) -> int",
  "",
  "main = -> void",
  "  m = crear()",
  "  io::println(leer(m))",
  "  io::println(m.etiqueta)",
  "  unsafe",
  "    io::println(m.dato.entero)",
  "",
].join("\n");

interface SizeRow {
  readonly name: string;
  readonly size: number;
  readonly align: number;
  readonly fields: readonly { readonly name: string; readonly offset?: number; readonly size: number; readonly width?: number }[];
}

function c_compiler(): string | undefined {
  for (const candidate of ["c++", "g++", "clang++"]) {
    const probe = spawnSync(candidate, ["--version"], { encoding: "utf8" });
    if (probe.status === 0) return candidate;
  }
  return undefined;
}

describe("ABI de uniones, bitfields y arrays", () => {
  test("coincide con C++ y cruza llamadas por valor", () => {
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-abi-"));
    try {
      const probe_source = join(dir, "probe.cpp");
      writeFileSync(probe_source, PROBE);
      const probe_binary = join(dir, "probe");
      const built = spawnSync(compiler, ["-std=c++20", "-O0", probe_source, "-o", probe_binary], { encoding: "utf8" });
      expect(built.status).toBe(0);
      const probe = spawnSync(probe_binary, [], { encoding: "utf8" });
      expect(probe.status).toBe(0);
      const [size, align, etiqueta, dato, pesos] = (probe.stdout as string).trim().split(" ").map(Number);
      expect(size).toBeDefined();

      const source = join(dir, "main.pengu");
      writeFileSync(source, PENGU);
      const measured = run_size([source], { json: true });
      expect(measured.exit_code).toBe(0);
      const payload = JSON.parse(measured.output) as { types: SizeRow[] };
      const row = payload.types.find((item) => item.name === "main_realm::Mezcla");
      expect(row).toBeDefined();
      expect(row?.size).toBe(size as number);
      expect(row?.align).toBe(align as number);
      const field = (name: string) => row?.fields.find((item) => item.name === name);
      expect(field("etiqueta")?.offset).toBe(etiqueta as number);
      expect(field("dato")?.offset).toBe(dato as number);
      expect(field("pesos")?.offset).toBe(pesos as number);
      expect(field("a")?.width).toBe(3);
      expect(field("b")?.width).toBe(5);

      const object = join(dir, "abi.o");
      const object_built = spawnSync(compiler, ["-std=c++20", "-O0", "-c", "-x", "c++", "-o", object, "-"], {
        input: C_SOURCE,
        encoding: "utf8",
      });
      expect(object_built.status).toBe(0);

      const result = compile_file(source, { link: [object] });
      expect(result.diagnostics.map((diagnostic) => diagnostic.message)).toEqual([]);
      const ran = spawnSync(result.binary_path as string, [], { encoding: "utf8" });
      // 7*100 + 3*10 + 5 + 4 = 739
      expect(ran.stdout).toBe("739\np\n7\n");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60_000);
});
