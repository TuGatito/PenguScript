// Tests E2E del catálogo **generado** con `pengu ts-bindgen`: el programa usa
// solo `std/js/dom_generated` (1 123 tipos salidos de `lib.dom.d.ts`) y se
// ejecuta con el mock del DOM. Comprueban que lo generado no es un premio de
// consolación: sirve para escribir canvas, almacenamiento, eventos y fetch.

import { describe, expect, test } from "bun:test";
import { copyFileSync, mkdtempSync, writeFileSync } from "node:fs";
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
  readonly llamadas: readonly string[];
}

function ejecutar(name: string, source: string): Resultado {
  const dir = mkdtempSync(join(tmpdir(), `pengu_gen_${name}_`));
  const source_file = join(dir, "main.pengu");
  writeFileSync(source_file, `invoke "std/js/dom_generated"\ninvoke "std/js/types"\n\n${source}`);
  const out = join(dir, "out");
  const result = compile_file(source_file, { target: "js", out });
  if (!result.ok || result.js_entry_path === undefined) {
    throw new Error(
      `no compiló ${name}: ${result.diagnostics.map((item) => `${item.code} ${item.message}`).join(" | ")}`,
    );
  }
  copyFileSync(MOCK, join(out, "dom_mock.mjs"));
  writeFileSync(
    join(out, "arranque.mjs"),
    'import "./dom_mock.mjs";\nawait import("./index.mjs");\nconsole.log("__LLAMADAS__" + JSON.stringify(globalThis.__LLAMADAS));\n',
  );
  const run = spawnSync(runtime?.command ?? "node", [join(out, "arranque.mjs")], {
    encoding: "utf8",
    cwd: out,
    timeout: 30_000,
  });
  const stdout = run.stdout ?? "";
  const marcador = stdout.indexOf("__LLAMADAS__");
  const lineas = marcador < 0 ? stdout : stdout.slice(0, marcador);
  const llamadas = marcador < 0 ? [] : (JSON.parse(stdout.slice(marcador + 12).trim()) as string[]);
  return { stdout: lineas, stderr: run.stderr ?? "", status: run.status ?? 1, llamadas };
}

describe("catálogo generado desde lib.dom.d.ts", () => {
  test("canvas: crear el lienzo, pintar y leer las propiedades", () => {
    const result = ejecutar(
      "canvas",
      `main = ->
  mut lienzo = document.createElement("canvas") as js::HTMLCanvasElement
  lienzo.width = 320
  lienzo.height = 200
  mut ctx = lienzo.getContext("2d").value()
  ctx.fillStyle = "#123456"
  ctx.fillRect(0.0, 0.0, 320.0, 200.0)
  ctx.globalAlpha = 0.5
  console.log("#{lienzo.width}x#{lienzo.height} estilo=#{ctx.fillStyle} alfa=#{ctx.globalAlpha}")
`,
    );
    expect(result.status).toBe(0);
    expect(result.stdout.trim()).toBe("320x200 estilo=#123456 alfa=0.5");
  });

  test("almacenamiento: `getItem` devuelve `string?` y `setItem` escribe", () => {
    const result = ejecutar(
      "storage",
      `main = ->
  const antes = localStorage.getItem("tema").value_or("(sin tema)")
  localStorage.setItem("tema", "oscuro")
  const despues = localStorage.getItem("tema").value_or("(sin tema)")
  console.log("antes=#{antes} despues=#{despues}")
`,
    );
    expect(result.status).toBe(0);
    expect(result.stdout.trim()).toBe("antes=(sin tema) despues=oscuro");
  });

  test("eventos: el manejador registrado se guarda en el mock", () => {
    const result = ejecutar(
      "eventos",
      `main = ->
  mut boton = document.createElement("button")
  boton.addEventListener("click", (_evento: js::Event) -> console.log("clic recibido"))
  console.log("registrado")
`,
    );
    expect(result.status).toBe(0);
    expect(result.stdout.trim()).toBe("registrado");
  });

  test("fetch declarado en el catálogo devuelve un futuro", () => {
    const result = ejecutar(
      "fetch",
      `async cargar = ->
  const respuesta = await window.fetch("https://example.test/datos")
  console.log("estado=#{respuesta.status}")

main = ->
  cargar()
`,
    );
    expect(result.status).toBe(0);
    expect(result.stdout.trim()).toBe("estado=200");
  });

  test("dibujo: la secuencia de llamadas al contexto es la del programa", () => {
    const result = ejecutar(
      "dibujo",
      `main = ->
  mut lienzo = document.createElement("canvas") as js::HTMLCanvasElement
  lienzo.width = 64
  lienzo.height = 64
  mut ctx = lienzo.getContext("2d").value()
  ctx.beginPath()
  ctx.arc(32.0, 32.0, 20.0, 0.0, 6.283185)
  ctx.fillStyle = "#f00"
  ctx.fill()
  ctx.save()
  ctx.translate(8.0, 8.0)
  ctx.rotate(0.5)
  ctx.restore()
  console.log("pintado")
`,
    );
    expect(result.status).toBe(0);
    expect(result.stdout.trim()).toBe("pintado");
    const dibujo = result.llamadas.filter((linea) => linea !== "createElement:div");
    expect(dibujo).toEqual([
      "createElement:canvas",
      "getContext:2d:CANVAS",
      "beginPath()",
      "arc(32,32,20,0,6.283185)",
      "fill()",
      "save()",
      "translate(8,8)",
      "rotate(0.5)",
      "restore()",
    ]);
  }, 60_000);

  test("DOM: `appendChild` y `textContent` dejan el árbol como se espera", () => {
    const result = ejecutar(
      "arbol",
      `main = ->
  mut titulo = document.createElement("h1")
  titulo.textContent = "Hola"
  document.body.appendChild(titulo)
  mut parrafo = document.createElement("p")
  parrafo.textContent = "mundo"
  document.body.appendChild(parrafo)
  console.log("hijos=#{#document.body.childNodes} texto=#{titulo.textContent}")
`,
    );
    expect(result.status).toBe(0);
    expect(result.stdout.trim()).toBe("hijos=2 texto=Hola");
    expect(result.llamadas).toContain("createElement:h1");
    expect(result.llamadas).toContain("createElement:p");
  }, 60_000);

  test("fetch: `text()` devuelve el cuerpo como string", () => {
    const result = ejecutar(
      "fetch_texto",
      `async cargar = ->
  const respuesta = await window.fetch("https://example.test/datos")
  const cuerpo = await respuesta.text()
  console.log("estado=#{respuesta.status} cuerpo=#{cuerpo}")

main = ->
  cargar()
`,
    );
    expect(result.status).toBe(0);
    expect(result.stdout.trim()).toBe("estado=200 cuerpo=respuesta");
  }, 60_000);
});
