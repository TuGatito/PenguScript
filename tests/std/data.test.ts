// Fase F7 del plan de la stdlib: datos y CLI (encoding, hash, cli, console y JSON).
//
// Cada prueba compila y ejecuta un programa real, así que también cubre la
// emisión de C++ de los módulos (no solo el checker).

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_data_${name}_`));
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

describe("encoding", () => {
  test("base64, hexadecimal, URL y UTF-8", () => {
    const output = run_source(
      "encoding",
      `invoke "std/encoding"
invoke "std/io"

main = ->
  io::println("b64: #{encoding::base64("pingüino")}")
  io::println("texto: #{encoding::base64_decode("cGluZ8O8aW5v").value_or("?")}")
  io::println("hex: #{encoding::hex("abc")}")
  io::println("bytes: #{encoding::hex_decode("616263").value_or("?")}")
  io::println("url: #{encoding::url_encode("a b&c")}")
  io::println("urlvuelta: #{encoding::url_decode("a%20b%26c").value_or("?")}")
  io::println("utf8: #{encoding::is_utf8("añ")} #{encoding::is_utf8("abc")}")
  datos = encoding::bytes("añ")
  io::println("tamano: #{#datos}")
  io::println("bytesb64: #{encoding::base64_bytes(datos)}")
`,
    );
    expect(output).toBe(
      "b64: cGluZ8O8aW5v\n" +
        "texto: pingüino\n" +
        "hex: 616263\n" +
        "bytes: abc\n" +
        "url: a%20b%26c\n" +
        "urlvuelta: a b&c\n" +
        "utf8: true true\n" +
        "tamano: 3\n" +
        "bytesb64: YcOx\n",
    );
  });
});

describe("hash", () => {
  test("huellas conocidas de referencia", () => {
    const output = run_source(
      "hash",
      `invoke "std/hash"
invoke "std/io"

main = ->
  io::println("fnv32: #{hash::fnv1a32_hex("")}")
  io::println("fnv64: #{hash::fnv1a64_hex("hello")}")
  io::println("crc32: #{hash::crc32_hex("123456789")}")
  io::println("adler: #{hash::hex32(hash::adler32("Wikipedia"))}")
  io::println("djb2: #{hash::djb2("abc")}")
`,
    );
    expect(output).toBe(
      "fnv32: 811c9dc5\n" + "fnv64: a430d84680aabd0b\n" + "crc32: cbf43926\n" + "adler: 11e60398\n" + "djb2: 193485963\n",
    );
  });
});

describe("cli", () => {
  test("banderas, opciones, posicionales y errores", () => {
    const output = run_source(
      "cli",
      `invoke "std/cli"
invoke "std/io"
invoke "std/vector"

main = ->
  mut banderas = vector<cli::Flag>[]
  banderas.push(cli::short_option("salida", "s", "archivo de salida"))
  banderas.push(cli::short_flag("verbose", "v", "modo detallado"))
  mut argv = vector<string>["programa", "--salida=out.txt", "-v", "entrada.txt"]
  resultado = cli::parse(ref(banderas), ref(argv))
  io::println("ok: #{resultado.is_ok()} salida: #{resultado.get("salida").value_or("?")}")
  io::println("verbose: #{resultado.has("verbose")}")
  io::println("posicional: #{resultado.positional(size_t::from(0)).value_or("?")}")
  mut desconocida = vector<string>["programa", "--rara"]
  fallo = cli::parse(ref(banderas), ref(desconocida))
  io::println("desconocida: #{fallo.error()}")
  mut sinvalor = vector<string>["programa", "--salida"]
  falta = cli::parse(ref(banderas), ref(sinvalor))
  io::println("sinvalor: #{falta.error()}")
`,
    );
    expect(output).toBe(
      "ok: true salida: out.txt\n" +
        "verbose: true\n" +
        "posicional: entrada.txt\n" +
        "desconocida: opción desconocida: --rara\n" +
        "sinvalor: la opción --salida necesita un valor\n",
    );
  });
});

describe("console", () => {
  test("escapes ANSI y limpieza", () => {
    const output = run_source(
      "console",
      `invoke "std/console"
invoke "std/io"

main = ->
  io::println("negro: #{#console::bold()} #{#console::reset()}")
  io::println("rgb: #{#console::fg_rgb(255, 0, 128)}")
  io::println("pintado: #{console::strip(console::paint_rgb("hola", 255, 0, 0))}")
  io::println("limpio: #{console::strip(console::bold() + "x" + console::reset())}")
`,
    );
    expect(output).toBe("negro: 4 4\n" + "rgb: 17\n" + "pintado: hola\n" + "limpio: x\n");
  });
});

describe("json", () => {
  test("análisis, acceso y serialización", () => {
    const output = run_source(
      "json",
      `invoke "std/io"
invoke "std/json"
invoke "std/optional"
invoke "std/vector"

main = -> void
  texto = "{\\"nombre\\":\\"pengu\\",\\"edad\\":3,\\"activo\\":true,\\"lista\\":[1,2],\\"hijo\\":{\\"x\\":1.5}}"
  valor = json::parse(texto)
  if valor.is_none()
    motivo = json::error(texto).value_or("?")
    io::println("error: #{motivo}")
    return
  datos = valor.value()
  io::println("compacto: #{json::stringify(datos)}")
  nombre = json::get(datos, "nombre")
  if nombre.is_some()
    io::println("nombre: #{json::as_text(nombre.value()).value_or("?")}")
  edad = json::get(datos, "edad")
  if edad.is_some()
    io::println("edad: #{json::as_int(edad.value()).value_or(0)}")
  lista = json::get(datos, "lista")
  if lista.is_some()
    primero = json::at(lista.value(), size_t::from(0))
    mut valor_primero = 0 - 1
    if primero.is_some()
      valor_primero = json::as_int(primero.value()).value_or(0 - 1)
    io::println("lista: #{json::length(lista.value())} primero: #{valor_primero}")
  hijo = json::get(datos, "hijo")
  if hijo.is_some()
    x = json::get(hijo.value(), "x")
    if x.is_some()
      io::println("x: #{json::as_number(x.value()).value_or(0.0)}")
  io::println("pretty:\\n#{json::pretty(datos)}")
  io::println("error: #{json::error("{\\"a\\":}").value_or("?")}")
  io::println("sobra: #{json::error("1 2").value_or("?")}")
  io::println("nulo: #{json::stringify(json::null_value())}")
`,
    );
    expect(output).toBe(
      'compacto: {"nombre":"pengu","edad":3,"activo":true,"lista":[1,2],"hijo":{"x":1.5}}\n' +
        "nombre: pengu\n" +
        "edad: 3\n" +
        "lista: 2 primero: 1\n" +
        "x: 1.5\n" +
        'pretty:\n{\n  "nombre": "pengu",\n  "edad": 3,\n  "activo": true,\n  "lista": [\n    1,\n    2\n  ],\n  "hijo": {\n    "x": 1.5\n  }\n}\n' +
        "error: número vacío\n" +
        "sobra: contenido sobrante tras el valor\n" +
        "nulo: null\n",
    );
  });
});

describe("herramienta de datos", () => {
  test("aceptación: banderas, archivo y JSON", () => {
    const output = run_source(
      "tool",
      `invoke "std/cli"
invoke "std/encoding"
invoke "std/fs"
invoke "std/io"
invoke "std/json"
invoke "std/vector"

hash_texto = (texto: string) -> string
  datos = encoding::bytes(texto)
  mut suma = 0
  for dato in datos
    suma = (suma * 31 + (dato as int)) % 1000003
  "#{suma}"

main = -> void
  mut banderas = vector<cli::Flag>[]
  banderas.push(cli::short_option("nombre", "n", "nombre del paquete"))
  banderas.push(cli::flag("bonito", "json con sangría"))
  mut argv = vector<string>["programa", "-n", "pengu", "--bonito"]
  opciones = cli::parse(ref(banderas), ref(argv))
  if not opciones.is_ok()
    io::println("error: #{opciones.error()}")
    return
  nombre = opciones.get("nombre").value_or("?")
  mut claves = vector<string>["nombre", "huella"]
  mut valores = vector<json::Value>[]
  valores.push(json::text_value(nombre))
  valores.push(json::text_value(hash_texto(nombre)))
  documento = json::object_value(claves, valores)
  ruta = "paquete.json"
  texto = json::stringify(documento)
  fs::write_string(ruta, texto)
  leido = fs::read_to_string(ruta).value_or("")
  vuelta = json::parse(leido)
  if vuelta.is_none()
    io::println("no se pudo releer")
    return
  campo = json::get(vuelta.value(), "nombre")
  if campo.is_some()
    io::println("nombre: #{json::as_text(campo.value()).value_or("?")}")
  io::println("texto: #{texto}")
  fs::remove_if_exists(ruta)
`,
    );
    expect(output).toBe('nombre: pengu\ntexto: {"nombre":"pengu","huella":"551945"}\n');
  }, 20000);
});
