// Fase F8 del plan de la stdlib: módulos avanzados seguros para 0.1.0.
//
// Cubre archivos con manejador (`std/file`), procesos (`std/process`) y
// SHA-256 (`std/crypto`). Los módulos de concurrencia y red se aplazaron en la
// bitácora del plan porque necesitan garantías que el checker de 0.1.0 aún no
// ofrece.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_advanced_${name}_`));
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

describe("archivos con manejador", () => {
  test("crear, escribir, leer por líneas y cerrar", () => {
    const output = run_source(
      "file",
      `invoke "std/file"
invoke "std/io"
invoke "std/string"

main = -> void
  ruta = "/tmp/pengu_archivo_demo.txt"
  creado = file::create(ruta)
  if creado.is_none()
    io::println("sin archivo")
    return
  mut escritor = creado.value()
  escritor.write_line("uno")
  escritor.write("dos\\n")
  escritor.flush()
  io::println("abierto: #{escritor.is_open()} #{escritor.path()}")
  escritor.close()
  io::println("cerrado: #{escritor.is_open()}")

  io::println("texto: #{file::read_text(ruta).value_or("?").trim()}")
  lector = file::open(ruta)
  if lector.is_none()
    io::println("no se pudo abrir")
    return
  mut flujo = lector.value()
  io::println("l1: #{flujo.read_line().value_or("?")}")
  io::println("l2: #{flujo.read_line().value_or("?")}")
  io::println("l3: #{flujo.read_line().value_or("fin")}")
  io::println("eof: #{flujo.is_eof()}")
  flujo.close()
  io::println("faltante: #{file::read_text("/tmp/pengu_no_existe.txt").is_none()}")
`,
    );
    expect(output).toBe(
      "abierto: true /tmp/pengu_archivo_demo.txt\n" +
        "cerrado: false\n" +
        "texto: uno\n" +
        "dos\n" +
        "l1: uno\n" +
        "l2: dos\n" +
        "l3: fin\n" +
        "eof: true\n" +
        "faltante: true\n",
    );
  });
});

describe("procesos", () => {
  test("salida, estado y código de salida", () => {
    const output = run_source(
      "process",
      `invoke "std/io"
invoke "std/process"
invoke "std/string"

main = -> void
  io::println("salida: #{process::output("echo hola").trim()}")
  io::println("estado: #{process::status("true")} #{process::status("false")}")
  io::println("codigo: #{process::run("exit 3")}")
`,
    );
    expect(output).toBe("salida: hola\n" + "estado: true false\n" + "codigo: 3\n");
  });
});

describe("crypto", () => {
  test("SHA-256 con vectores conocidos", () => {
    const output = run_source(
      "crypto",
      `invoke "std/crypto"
invoke "std/io"

main = -> void
  io::println(crypto::sha256(""))
  io::println(crypto::sha256("abc"))
  io::println(crypto::sha256("pingüino"))
  io::println(crypto::sha256_hex("abc"))
`,
    );
    expect(output).toBe(
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n" +
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad\n" +
        "7237eaeb2093fe4ea674b6d8c69666d0c56e4c6beb42429d3769bebea74700c2\n" +
        "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad\n",
    );
  });
});

describe("herramienta de huellas", () => {
  test("aceptación: leer un archivo y verificar su SHA-256", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_huellas_"));
    const ruta = join(dir, "datos.txt");
    writeFileSync(ruta, "pengu\n");
    const output = run_source(
      "tool",
      `invoke "std/crypto"
invoke "std/file"
invoke "std/io"
invoke "std/string"

main = -> void
  ruta = "${ruta}"
  texto = file::read_text(ruta)
  if texto.is_none()
    io::println("sin datos")
    return
  contenido = texto.value()
  io::println("lineas: #{#contenido.split_lines()}")
  io::println("huella: #{crypto::sha256(contenido.trim())}")
`,
    );
    expect(output).toBe("lineas: 2\nhuella: 50a7fd573aba1d07865d3ce1b0471bb47d7656e8300ee8af07c217659663d306\n");
  });
});
