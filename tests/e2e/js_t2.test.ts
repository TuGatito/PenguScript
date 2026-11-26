// T2: globales y namespaces del host, construcción con `new`, temporizadores
// y futuros. Los programas se compilan a JavaScript y se ejecutan con el mock
// del DOM (que también simula `fetch`).

import { describe, expect, test } from "bun:test";
import { copyFileSync, mkdtempSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { compile_file } from "../../src/driver/compile.ts";
import { find_js_runtime } from "../../src/driver/js_runner.ts";

const runtime = find_js_runtime();
const MOCK = join(import.meta.dir, "../fixtures/js/dom_mock.mjs");

function ejecutar(name: string, source: string): { stdout: string; stderr: string; status: number } {
  const dir = mkdtempSync(join(tmpdir(), `pengu_t2_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file, { target: "js", out: join(dir, "out") });
  if (!result.ok || result.js_entry_path === undefined) {
    throw new Error(
      `no compiló ${name}: ${result.diagnostics.map((item) => `${item.code} ${item.message}`).join(" | ")}`,
    );
  }
  const out = join(dir, "out");
  copyFileSync(MOCK, join(out, "dom_mock.mjs"));
  writeFileSync(join(out, "arranque.mjs"), 'import "./dom_mock.mjs";\nawait import("./index.mjs");\n');
  const run = spawnSync(runtime?.command ?? "node", [join(out, "arranque.mjs")], {
    encoding: "utf8",
    cwd: out,
    timeout: 30_000,
  });
  return { stdout: run.stdout ?? "", stderr: run.stderr ?? "", status: run.status ?? 1 };
}

function esperar(name: string, source: string, lineas: readonly string[]): void {
  const result = ejecutar(name, source);
  if (result.status !== 0) throw new Error(`falló ${name}: ${result.stderr}`);
  expect(result.stdout.trimEnd().split("\n")).toEqual([...lineas]);
}

describe("namespaces del host", () => {
  test("`Math` expone constantes y funciones", () => {
    esperar(
      "math",
      `invoke "std/js/console"
invoke "std/js/math"

main = ->
  const raiz: double = Math::sqrt(144.0)
  const techo: double = Math::ceil(2.1)
  const mayor: double = Math::max(3.0, 8.0)
  console.log(raiz, techo, mayor)
  console.log(Math::PI > 3.0, Math::sign(-2.0))
`,
      ["12 3 8", "true -1"],
    );
  });
});

describe("construcción y miembros estáticos", () => {
  test("`js::URL` se construye y expone sus partes", () => {
    esperar(
      "url",
      `invoke "std/js/console"
invoke "std/js/url"

main = ->
  const u = js::URL("https://example.test:8080/ruta?x=1")
  console.log(u.hostname, u.port, u.pathname)
  u.searchParams.set("y", "2")
  console.log(u.searchParams.get("y"), u.searchParams.has("x"))
  console.log(u.toString())
`,
      ["example.test 8080 /ruta", "2 true", "https://example.test:8080/ruta?x=1&y=2"],
    );
  });

  test("`URL::canParse` es un miembro estático", () => {
    esperar(
      "url_estatico",
      `invoke "std/js/console"
invoke "std/js/url"

main = ->
  console.log(js::URL::canParse("https://a.test"))
`,
      ["true"],
    );
  });
});

describe("temporizadores y futuros", () => {
  test("`set_timeout` dispara y `clear_timeout` cancela", () => {
    esperar(
      "timers",
      `invoke "std/js/console"
invoke "std/js/timers"

main = async ->
  js_timers::set_timeout(() -> console.log("dispara"), 1)
  const cancelado = js_timers::set_timeout(() -> console.log("no"), 1)
  js_timers::clear_timeout(cancelado)
  await js_timers::delay(5)
  console.log("fin")
`,
      ["dispara", "fin"],
    );
  });

  test("un `future` del host se espera con `await`", () => {
    esperar(
      "futuros",
      `invoke "std/js/console"
invoke "std/js/promise"

main = async ->
  const f: future<int> = js_promise::resolve(7)
  const valor = await f
  console.log(valor)
  const del_hilo = await js_promise::resolve("texto")
  console.log(del_hilo)
`,
      ["7", "texto"],
    );
  });
});

describe("console como objeto global", () => {
  test("`console.log` acepta varios argumentos", () => {
    esperar(
      "console",
      `invoke "std/js/console"

main = ->
  console.log("a", 1, 2.5, true)
`,
      ["a 1 2.5 true"],
    );
  });
});
