// F5: `char*` escribible cruza como `raw<char>` y `std/ffi::CString` da el
// buffer terminado en NUL para que las funciones C escriban en él.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { existsSync } from "node:fs";
import { run_bindgen } from "../../src/cli/bindgen_command.ts";
import { parse_args } from "../../src/cli/args.ts";
import { find_clang } from "../../src/bindgen/clang_ast.ts";
import { compile_file } from "../../src/driver/compile.ts";
import { build_object, c_compiler } from "./native.ts";

const HEADER = [
  "void rellenar(char *texto, int n);",
  "int medir(const char *texto);",
  "void copiar(char *destino, const char *origen);",
  "",
].join("\n");

const IMPLEMENTATION = [
  "#include <string.h>",
  "void rellenar(char *p, int n) { for (int i = 0; i < n; i++) p[i] = (char)('a' + i); p[n] = 0; }",
  "int medir(const char *p) { return (int)strlen(p); }",
  "void copiar(char *destino, const char *origen) { strcpy(destino, origen); }",
  "",
].join("\n");

describe("bindgen buffers", () => {
  test("char* escribible como raw<char> y const char* como string", () => {
    if (find_clang() === undefined) return;
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-f5-"));
    try {
      const header = join(dir, "chars.h");
      writeFileSync(header, HEADER);
      const binding = join(dir, "chars.d.pengu");
      const generated = run_bindgen(parse_args(["bindgen", header, "--out", binding, "--realm", "chars"]));
      expect(generated.exit_code).toBe(0);
      const text = readFileSync(binding, "utf8");
      expect(text).toContain("rellenar = (texto: raw<char>, n: int) -> void");
      expect(text).toContain("medir = (texto: string) -> int");
      expect(text).toContain("copiar = (destino: raw<char>, origen: string) -> void");

      const object = build_object(compiler, dir, "chars", IMPLEMENTATION);

      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          'invoke "std/ffi"',
          `invoke "${binding.replace(/\.pengu$/, "")}"`,
          "",
          "main = -> void",
          '  mut buffer = ffi::cstring("hola", size_t::from(8))',
          '  io::println("texto: #{buffer.text()} len: #{buffer.len()} cap: #{buffer.capacity()}")',
          "  unsafe",
          "    chars::rellenar(buffer.ptr(), 5)",
          '  io::println("tras C: #{buffer.text()}")',
          "  unsafe",
          "    chars::copiar(buffer.ptr(), \"pengu\")",
          '  io::println("copia: #{buffer.text()}")',
          '  buffer.set("otra cosa")',
          '  io::println("set: #{buffer.text()} medida: #{chars::medir(buffer.text())}")',
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: [object] });
      if (!result.ok) throw new Error(result.output);
      if (result.binary_path === undefined) throw new Error("sin binario");
      const run = spawnSync(result.binary_path, [], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toBe(
        "texto: hola len: 4 cap: 9\ntras C: abcde\ncopia: pengu\nset: otra cosa medida: 9\n",
      );
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60000);

  test("raylib: TextCopy escribe en un CString", () => {
    if (find_clang() === undefined) return;
    const header = "/usr/include/raylib.h";
    if (!existsSync(header)) return;
    const compiler = c_compiler();
    if (compiler === undefined) return;

    const dir = mkdtempSync(join(tmpdir(), "pengu-f5-rl-"));
    try {
      const binding = join(dir, "raylib.d.pengu");
      const generated = run_bindgen(parse_args(["bindgen", header, "--out", binding, "--realm", "raylib"]));
      expect(generated.exit_code).toBe(0);
      const text = readFileSync(binding, "utf8");
      expect(text).toContain("TextCopy = (dst: raw<char>, src: string) -> int");

      const source = join(dir, "main.pengu");
      writeFileSync(
        source,
        [
          'invoke "std/io"',
          'invoke "std/ffi"',
          `invoke "${binding.replace(/\.pengu$/, "")}"`,
          "",
          "main = -> void",
          '  mut buffer = ffi::cstring("", size_t::from(32))',
          "  unsafe",
          '    raylib::TextCopy(buffer.ptr(), "hola desde C")',
          '  io::println("texto: #{buffer.text()}")',
          "",
        ].join("\n"),
      );

      const result = compile_file(source, { link: ["raylib"] });
      if (!result.ok) throw new Error(result.output);
      if (result.binary_path === undefined) throw new Error("sin binario");
      const run = spawnSync(result.binary_path, [], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toBe("texto: hola desde C\n");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  }, 60000);
});
