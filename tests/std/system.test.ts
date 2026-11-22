// Fase F4 del plan de la stdlib: sistema (fs, os, path, time, random, io).
//
// Cada prueba compila y ejecuta un programa real contra el sistema de
// archivos y el reloj: se comprueba el comportamiento, no solo que el
// checker acepte la API.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { compile_file } from "../../src/driver/compile.ts";

function compile_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_sys_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(
      result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output,
    );
  }
  return result.binary_path ?? "";
}

function run_source(name: string, source: string): string {
  const binary = compile_source(name, source);
  const run = spawnSync(binary, [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout;
}

let counter = 0;
function unique_base(nombre: string): string {
  counter += 1;
  return `${nombre}_${counter}_${Date.now()}`;
}

describe("sistema", () => {
  test("fs escribe, lee, lista y borra archivos", () => {
    const base = unique_base("pengu_fs");
    const output = run_source(
      "fs",
      `invoke "std/io"
invoke "std/fs"
invoke "std/os"
invoke "std/path"
invoke "std/vector"

main = ->
  carpeta = os::temp_dir().value_or("/tmp") + "/${base}"
  fs::remove_if_exists(carpeta)
  io::println("crear #{fs::ensure_dir(carpeta)}")
  archivo = path::join(carpeta, "notas.txt")
  io::println("escribir #{fs::write_string(archivo, "uno\\ndos\\n")}")
  io::println("leer [#{fs::read_to_string(archivo).value_or("?")}]")
  mut lineas = fs::read_lines(archivo).value()
  lineas.push("tres")
  io::println("lineas #{#lineas} #{lineas.join("|")}")
  io::println("guardar #{fs::write_lines(archivo, ref(lineas))} agregar #{fs::append_line(archivo, "cuatro")}")
  io::println("tamano #{fs::file_size(archivo).value_or(-1)}")
  io::println("archivo #{fs::is_file(archivo)} carpeta #{fs::is_dir(carpeta)} existe #{fs::exists(archivo)}")
  copia = path::join(carpeta, "copia.txt")
  final = path::join(carpeta, "final.txt")
  io::println("copiar #{fs::copy(archivo, copia)} renombrar #{fs::rename(copia, final)}")
  io::println("listar #{fs::list_dir(carpeta).join(",")}")
  io::println("canonico #{fs::canonicalize(archivo).is_some()}")
  io::println("nuevo #{fs::write_new(final, "x")} borrar #{fs::remove(carpeta)}")
  0
`,
    );
    expect(output).toBe(
      [
        "crear true",
        "escribir true",
        "leer [uno",
        "dos",
        "]",
        "lineas 3 uno|dos|tres",
        "guardar true agregar true",
        "tamano 20",
        "archivo true carpeta true existe true",
        "copiar true renombrar true",
        "listar final.txt,notas.txt",
        "canonico true",
        "nuevo false borrar true",
        "",
      ].join("\n"),
    );
  });

  test("path compone rutas sin tocar el disco", () => {
    const output = run_source(
      "path",
      `invoke "std/io"
invoke "std/path"
invoke "std/vector"

main = ->
  io::println("join #{path::join("/a", "b")} #{path::join("/a/", "b")} #{path::join("/a", "/b")}")
  io::println("abs #{path::is_absolute("/x")} #{path::is_absolute("x")}")
  io::println("name #{path::file_name("/a/b/c.tar.gz").value_or("-")}")
  io::println("stem #{path::stem("/a/b/c.tar.gz").value_or("-")} ext #{path::extension("/a/b/c.tar.gz").value_or("-")}")
  io::println("parent #{path::parent_dir("/a/b/c.txt").value_or("-")} raiz #{path::parent_dir("c.txt").is_none()}")
  io::println("with #{path::with_extension("/a/b/c.txt", "md")} #{path::with_extension("c.txt", ".md")}")
  io::println("norm #{path::normalize("/a/./b/../c//d")} #{path::normalize("a/../../b")}")
  io::println("comp #{path::components("/a/b/c").join("/")} #{path::components("/").is_empty()}")
  0
`,
    );
    expect(output).toBe(
      [
        "join /a/b /a/b /b",
        "abs true false",
        "name c.tar.gz",
        "stem c.tar ext gz",
        "parent /a/b raiz true",
        "with /a/b/c.md c.md",
        "norm /a/c/d ../b",
        "comp a/b/c true",
        "",
      ].join("\n"),
    );
  });

  test("time mide con Duration e Instant", () => {
    const output = run_source(
      "time",
      `invoke "std/io"
invoke "std/time"

main = ->
  d = time::duration_from_millis(1500)
  io::println("dur #{d.as_millis()} #{d.as_seconds()} [#{d}]")
  io::println("suma #{d + time::duration_from_seconds(2)} resta #{d - time::duration_from_millis(500)}")
  io::println("escala #{d.scaled(2.0).as_millis()} abs #{time::duration_from_millis(-5).abs().as_millis()}")
  io::println("minutos #{time::duration_from_minutes(2).as_seconds_int()} cero #{time::duration_zero().is_zero()}")
  inicio = time::instant_now()
  time::sleep_millis(15)
  io::println("elapsed #{inicio.elapsed().as_millis() >= 15}")
  io::println("until #{inicio.until(time::instant_now()).as_millis() >= 15}")
  ahora = time::datetime_now()
  partes = time::parts(ahora.as_millis())
  io::println("fecha #{ahora.year == partes[0]} #{ahora.month == partes[1]} #{ahora.day == partes[2]}")
  io::println("hora #{ahora.hour == partes[3]} formato #{ahora.to_string().starts_with("20")}")
  io::println("orden #{time::duration_from_seconds(1) < time::duration_from_seconds(2)}")
  0
`,
    );
    expect(output).toBe(
      [
        "dur 1500 1.5 [1.500s]",
        "suma 3.500s resta 1.000s",
        "escala 3000 abs 5",
        "minutos 120 cero true",
        "elapsed true",
        "until true",
        "fecha true true true",
        "hora true formato true",
        "orden true",
        "",
      ].join("\n"),
    );
  });

  test("random es reproducible y baraja sin perder elementos", () => {
    const output = run_source(
      "random",
      `invoke "std/io"
invoke "std/random"
invoke "std/vector"

main = ->
  random::seed(42)
  a = random::int(0, 1000)
  b = random::float()
  random::seed(42)
  c = random::int(0, 1000)
  d = random::float()
  io::println("reproducible #{a == c} #{b == d}")
  rango = random::float_range(1.0, 2.0)
  io::println("rango #{rango >= 1.0} #{rango <= 2.0}")
  mut xs = [1, 2, 3, 4, 5]
  xs.shuffle()
  io::println("elementos #{#xs} #{xs.contains(5)} #{xs.sum() == 15}")
  io::println("elegido #{xs.choose().is_some()} 0")
  0
`,
    );
    expect(output).toBe("reproducible true true\nrango true true\nelementos 5 true true\nelegido true 0\n");
  });

  test("os expone entorno, proceso y directorios", () => {
    const output = run_source(
      "os",
      `invoke "std/io"
invoke "std/os"

main = ->
  io::println("cpus #{os::cpu_count() >= 1} pid #{os::pid() > 0}")
  io::println("dirs #{os::home_dir().is_some()} #{os::temp_dir().is_some()} #{os::current_dir().is_some()}")
  io::println("plataforma #{os::platform().is_empty() == false} #{os::arch().is_empty() == false}")
  io::println("args #{#os::args() >= 1}")
  io::println("entorno #{os::env_or("PENGU_INEXISTENTE_F4", "respaldo")} #{os::has_env("PATH")}")
  io::println("set #{os::set_env("PENGU_F4", "ok")} #{os::get_env("PENGU_F4").value_or("-")}")
  0
`,
    );
    expect(output).toBe(
      [
        "cpus true pid true",
        "dirs true true true",
        "plataforma true true",
        "args true",
        "entorno respaldo true",
        "set true ok",
        "",
      ].join("\n"),
    );
  });

  test("aceptación: un `find` y un `du` mínimos y un bucle con Duration", () => {
    const base = unique_base("pengu_find");
    const output = run_source(
      "aceptacion",
      `invoke "std/io"
invoke "std/fs"
invoke "std/os"
invoke "std/path"
invoke "std/time"

main = ->
  carpeta = os::temp_dir().value_or("/tmp") + "/${base}"
  fs::remove_if_exists(carpeta)
  fs::ensure_dir(carpeta)
  fs::write_string(path::join(carpeta, "a.pengu"), "uno")
  fs::write_string(path::join(carpeta, "b.txt"), "dos")
  fs::write_string(path::join(carpeta, "c.pengu"), "tres")
  mut encontrados = 0
  mut bytes = 0
  for nombre in fs::list_dir(carpeta)
    ruta = path::join(carpeta, nombre)
    bytes += fs::file_size(ruta).value_or(0)
    if path::extension(nombre).value_or("") == "pengu"
      encontrados += 1
  io::println("find #{encontrados} du #{bytes}")
  mut vueltas = 0
  limite = time::duration_from_seconds(5)
  inicio = time::instant_now()
  while inicio.elapsed() < limite and vueltas < 3
    time::sleep_millis(2)
    vueltas += 1
  io::println("bucle #{vueltas} #{inicio.elapsed().as_millis() >= 0}")
  fs::remove(carpeta)
  0
`,
    );
    expect(output).toBe("find 2 du 10\nbucle 3 true\n");
  });
});
