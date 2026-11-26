// Tests E2E de `std/js`: el programa se compila a JavaScript, se ejecuta con
// el mock del DOM (plan §8) y se comprueba lo que el programa vio y lo que
// quedó registrado en el mock.

import { describe, expect, test } from "bun:test";
import { copyFileSync, existsSync, mkdtempSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { compile_file } from "../../src/driver/compile.ts";
import { find_js_runtime } from "../../src/driver/js_runner.ts";

const runtime = find_js_runtime();
const MOCK = join(import.meta.dir, "../fixtures/js/dom_mock.mjs");

interface Resultado {
  readonly stdout: string;
  readonly stderr: string;
  readonly status: number;
}

function ejecutar_dom(name: string, source: string): Resultado {
  const dir = mkdtempSync(join(tmpdir(), `pengu_dom_${name}_`));
  const source_file = join(dir, "main.pengu");
  writeFileSync(source_file, source);
  const result = compile_file(source_file, { target: "js", out: join(dir, "out") });
  if (!result.ok || result.js_entry_path === undefined) {
    throw new Error(
      `no compiló ${name}: ${result.diagnostics.map((item) => `${item.code} ${item.message}`).join(" | ")}`,
    );
  }
  const out = join(dir, "out");
  copyFileSync(MOCK, join(out, "dom_mock.mjs"));
  writeFileSync(
    join(out, "arranque.mjs"),
    'import "./dom_mock.mjs";\nawait import("./index.mjs");\n',
  );
  const run = spawnSync(runtime?.command ?? "node", [join(out, "arranque.mjs")], {
    encoding: "utf8",
    cwd: out,
    timeout: 30_000,
  });
  return { stdout: run.stdout ?? "", stderr: run.stderr ?? "", status: run.status ?? 1 };
}

function esperar(name: string, source: string, lineas: readonly string[]): Resultado {
  const result = ejecutar_dom(name, source);
  if (result.status !== 0) {
    throw new Error(`falló ${name}: ${result.stderr}`);
  }
  expect(result.stdout.trimEnd().split("\n")).toEqual([...lineas]);
  return result;
}

const CABECERA = `invoke "std/js/types"
invoke "std/js/dom"
invoke "std/js/canvas"
invoke "std/js/console"
`;

describe("std/js: DOM", () => {
  test("leer y escribir propiedades del documento", () => {
    esperar(
      "documento",
      `${CABECERA}
main = ->
  document.title = "Hola, DOM"
  console.log(document.title)
  const cuerpo = document.body
  mut hijo = document.createElement("p")
  hijo.innerHTML = "texto"
  cuerpo.appendChild(hijo)
  console.log(#cuerpo.childNodes)
`,
      ["Hola, DOM", "1"],
    );
  });

  test("una propiedad sin `mut` no se puede escribir (E0406)", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_dom_err_"));
    const file = join(dir, "main.pengu");
    writeFileSync(
      file,
      `${CABECERA}
main = ->
  const cuerpo = document.body
  cuerpo.nodeName = "x"
`,
    );
    const result = compile_file(file, { target: "js" });
    expect(result.ok).toBe(false);
    expect(result.diagnostics.map((item) => item.code)).toContain("E0406");
  });

  test("un tipo del host se puede convertir al concreto", () => {
    esperar(
      "cast",
      `${CABECERA}
main = ->
  mut lienzo = document.createElement("canvas") as js::HTMLCanvasElement
  lienzo.width = 320
  lienzo.height = 200
  console.log(lienzo.width, lienzo.height)
`,
      ["320 200"],
    );
  });

  test("un canvas dibuja con su contexto", () => {
    esperar(
      "canvas",
      `${CABECERA}
main = ->
  mut lienzo = document.createElement("canvas") as js::HTMLCanvasElement
  lienzo.width = 64
  lienzo.height = 32
  mut ctx = lienzo.getContext("2d")
  ctx.fillStyle = "rojo"
  ctx.fillRect(0.0, 0.0, 10.0, 20.0)
  console.log(ctx.fillStyle)
`,
      ["rojo"],
    );
  });

  test("un global del host sin tipo se usa como `any`", () => {
    esperar(
      "global",
      `${CABECERA}
main = ->
  console.log("hola", 1)
`,
      ["hola 1"],
    );
  });
});

describe("std/js: temporizadores y promesas", () => {
  test("`set_timeout` no rompe el programa", () => {
    esperar(
      "timers",
      `invoke "std/js/timers"
invoke "std/js/console"

main = ->
  const id = js_timers::set_timeout(() -> console.log("listo"), 0)
  js_timers::clear_timeout(id)
  console.log("programado")
`,
      ["programado"],
    );
  });

  test("`future` de una función del host se espera con `await`", () => {
    esperar(
      "fetch",
      `invoke "std/js/fetch"
invoke "std/js/console"

cargar = async -> string
  const respuesta = await js_fetch::fetch("https://example.test")
  await respuesta.text()

main = async ->
  const texto = await cargar()
  console.log(texto)
`,
      ["respuesta"],
    );
  });
});
