// F5 de los bindings: buffers de C (`std/ffi`).
//
// Un `CString` es un `vector<char>` terminado en NUL: `ptr()` lo pasa a una
// función C, `text()` lee lo que la función escribió y `read`/`write` operan
// sobre punteros sueltos.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function run_source(source: string): string {
  const dir = mkdtempSync(join(tmpdir(), "pengu_ffi_"));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output);
  }
  const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout ?? "";
}

describe("std/ffi", () => {
  test("crear, leer, escribir y limpiar un CString", () => {
    const output = run_source(`invoke "std/ffi"
invoke "std/io"

main = -> void
  mut buffer = ffi::cstring("hola")
  io::println("texto=#{buffer.text()} len=#{buffer.len()} cap=#{buffer.capacity()} vacio=#{buffer.is_empty()}")
  buffer.set("adios")
  io::println("set=#{buffer.text()} len=#{buffer.len()}")
  unsafe
    ffi::write(buffer.ptr(), "xyz")
  io::println("write=#{buffer.text()}")
  mut leido = ""
  unsafe
    leido = ffi::read(buffer.ptr())
  io::println("read=#{leido}")
  buffer.clear()
  io::println("clear=[#{buffer.text()}] vacio=#{buffer.is_empty()}")
`);
    expect(output).toBe(
      "texto=hola len=4 cap=5 vacio=false\nset=adios len=5\nwrite=xyz\nread=xyz\nclear=[] vacio=true\n",
    );
  }, 30000);
});
