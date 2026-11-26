// E2E de los dominios grandes: el programa usa WebGL desde el catálogo
// generado (`std/js/dom_generated`) contra un mock que registra cada llamada a
// la API. WebGPU todavía no está en `lib.dom.d.ts` (5.7), así que su dominio se
// comprueba como «vacío y honesto» en vez de inventarlo.

import { describe, expect, test } from "bun:test";
import { copyFileSync, mkdtempSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { compile_file } from "../../src/driver/compile.ts";
import { find_js_runtime } from "../../src/driver/js_runner.ts";
import { bind_dts_file } from "../../src/tsbindgen/collect.ts";
import { DOMAINS } from "../../src/tsbindgen/domain.ts";

const runtime = find_js_runtime();
const FIXTURES = join(import.meta.dir, "../fixtures/js");
const DTS = join(import.meta.dir, "../../third_party/dts/lib.dom.d.ts");

interface Resultado {
  readonly stdout: string;
  readonly stderr: string;
  readonly status: number;
}

// Ejecuta el programa con los dos mocks y devuelve lo que registraron.
function ejecutar(name: string, source: string): Resultado & { readonly gl: readonly string[] } {
  const dir = mkdtempSync(join(tmpdir(), `pengu_gl_${name}_`));
  const source_file = join(dir, "main.pengu");
  writeFileSync(source_file, source);
  const out = join(dir, "out");
  const result = compile_file(source_file, { target: "js", out });
  if (!result.ok || result.js_entry_path === undefined) {
    throw new Error(
      `no compiló ${name}: ${result.diagnostics.map((item) => `${item.code} ${item.message}`).join(" | ")}`,
    );
  }
  copyFileSync(join(FIXTURES, "dom_mock.mjs"), join(out, "dom_mock.mjs"));
  copyFileSync(join(FIXTURES, "webgl_mock.mjs"), join(out, "webgl_mock.mjs"));
  writeFileSync(
    join(out, "arranque.mjs"),
    'import "./webgl_mock.mjs";\nawait import("./index.mjs");\nconsole.log("__GL__" + JSON.stringify(globalThis.__GL));\n',
  );
  const run = spawnSync(runtime?.command ?? "node", [join(out, "arranque.mjs")], {
    encoding: "utf8",
    cwd: out,
    timeout: 30_000,
  });
  const stdout = run.stdout ?? "";
  const marcador = stdout.indexOf("__GL__");
  const lineas = marcador < 0 ? stdout : stdout.slice(0, marcador);
  const gl = marcador < 0 ? [] : (JSON.parse(stdout.slice(marcador + 6).trim()) as string[]);
  return { stdout: lineas, stderr: run.stderr ?? "", status: run.status ?? 1, gl };
}

const PROGRAMA = `invoke "std/js/dom_generated"
invoke "std/js/types"

const VERTICE = "attribute vec2 posicion;\\nvoid main() {\\n  gl_Position = vec4(posicion, 0.0, 1.0);\\n}"
const FRAGMENTO = "precision mediump float;\\nvoid main() {\\n  gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);\\n}"

main = ->
  mut lienzo = document.createElement("canvas") as js::HTMLCanvasElement
  lienzo.width = 320
  lienzo.height = 240
  mut gl = lienzo.getContext("webgl").value() as js::WebGLRenderingContext
  const programa = gl.createProgram()
  const vertice = gl.createShader(gl.VERTEX_SHADER)
  gl.shaderSource(vertice, VERTICE)
  gl.compileShader(vertice)
  const fragmento = gl.createShader(gl.FRAGMENT_SHADER)
  gl.shaderSource(fragmento, FRAGMENTO)
  gl.compileShader(fragmento)
  gl.attachShader(programa, vertice)
  gl.attachShader(programa, fragmento)
  gl.linkProgram(programa)
  gl.useProgram(programa)
  gl.viewport(0, 0, 320, 240)
  gl.clearColor(0.09, 0.1, 0.13, 1.0)
  gl.clear(gl.COLOR_BUFFER_BIT)
  gl.drawArrays(gl.TRIANGLES, 0, 3)
  console.log("dibujado")
`;

describe("WebGL desde el catálogo generado", () => {
  test("compila y dibuja: shaders, programa y drawArrays", () => {
    const result = ejecutar("dibujo", PROGRAMA);
    expect(result.status).toBe(0);
    expect(result.stdout.trim()).toBe("dibujado");
    expect(result.gl).toContain("createProgram");
    expect(result.gl).toContain("createShader:35633");
    expect(result.gl).toContain("createShader:35632");
    expect(result.gl.filter((linea) => linea.startsWith("compileShader(")).length).toBe(2);
    expect(result.gl).toContain("linkProgram(2)");
    expect(result.gl).toContain("useProgram()");
    expect(result.gl).toContain("viewport(320,240)");
    expect(result.gl).toContain("drawArrays(0,3)");
  }, 60_000);

  test("las constantes de WebGL llegan con su valor numérico", () => {
    const result = ejecutar("constantes", PROGRAMA);
    expect(result.gl).toContain("clearColor(0.09,0.1,0.13,1)");
  }, 60_000);
});

describe("dominios grandes", () => {
  test("webgl, webaudio y webgpu son dominios conocidos", () => {
    for (const nombre of ["webgl", "webaudio", "webgpu"]) {
      expect(Object.keys(DOMAINS)).toContain(nombre);
    }
  });

  test("webgpu no está en lib.dom.d.ts y el generador lo dice", () => {
    const result = bind_dts_file(DTS, {
      realm: "js_webgpu_generated",
      source: "lib.dom.d.ts",
      invokes: ["std/js/types"],
      only: "webgpu",
    });
    expect(result.report.types).toBe(0);
    expect(result.report.skipped.length).toBeGreaterThan(0);
    // El texto sigue siendo un `.d.pengu` válido aunque no declare nada.
    expect(result.text).toContain("realm js_webgpu_generated");
    expect(result.text).not.toContain("host js::GPUDevice");
  }, 120_000);

  test("webgl sí está y trae los tipos del contexto", () => {
    const result = bind_dts_file(DTS, {
      realm: "js_webgl_generated",
      source: "lib.dom.d.ts",
      invokes: ["std/js/types"],
      only: "webgl",
    });
    expect(result.report.types).toBeGreaterThan(700);
    expect(result.text).toContain("host js::WebGLRenderingContext");
    expect(result.text).toContain("host js::WebGLShader");
  }, 120_000);
});
