// T3: el generador sobre las librerías reales del navegador.
//
// No compara texto (cambiaría con cada versión de TypeScript que se suba a
// `third_party/dts`), sino que comprueba lo que el plan considera la
// aceptación de la fase: el `.d.pengu` generado se puede volver a leer con el
// parser de PenguScript y cubre la mayoría de los tipos.

import { describe, expect, test } from "bun:test";
import { join } from "node:path";
import { bind_dts_file } from "../../src/tsbindgen/collect.ts";
import { parse_text } from "../../src/frontend/parser.ts";

const DTS = join(import.meta.dir, "../../third_party/dts");

function bind_lib(name: string): ReturnType<typeof bind_dts_file> {
  return bind_dts_file(join(DTS, name), {
    realm: `js_${name.replace(/^lib\./, "").replace(/\.d\.ts$/, "").replace(/\./g, "_")}`,
    source: name,
    invokes: ["std/js/types"],
  });
}

describe("lib.dom.d.ts", () => {
  test("genera un catálogo grande y sin errores de sintaxis", () => {
    const result = bind_lib("lib.dom.d.ts");
    expect(result.module.host_types.length).toBeGreaterThan(500);
    expect(result.module.members).toBeGreaterThan(5000);
    const parsed = parse_text("lib.dom.d.pengu", result.text);
    expect(parsed.diagnostics.map((item) => `${item.code} ${item.message}`)).toEqual([]);
  });

  test("los tipos clave del DOM están y heredan como el navegador", () => {
    const result = bind_lib("lib.dom.d.ts");
    const names = result.module.host_types.map((host) => host.name);
    for (const name of ["Document", "Element", "HTMLElement", "Node", "HTMLCanvasElement"]) {
      expect(names).toContain(name);
    }
    const element = result.module.host_types.find((host) => host.name === "HTMLElement");
    expect(element?.parent).toBe("Element");
    const canvas = result.module.host_types.find((host) => host.name === "HTMLCanvasElement");
    expect(canvas?.parent).toBe("HTMLElement");
  });

  test("`document` es un global y `window` también", () => {
    const result = bind_lib("lib.dom.d.ts");
    const globals = result.module.globals.map((global) => global.name);
    expect(globals).toContain("document");
    expect(globals).toContain("window");
  });

  test("lo omitido se informa con su motivo", () => {
    const result = bind_lib("lib.dom.d.ts");
    expect(result.module.skipped.length).toBeGreaterThan(0);
    const reasons = new Set(result.module.skipped.map((item) => item.reason));
    expect(reasons.has("unión de varios tipos")).toBe(true);
  });
});

describe("lib.es2022.d.ts", () => {
  test("también genera un módulo que el parser acepta", () => {
    // `lib.es2022.d.ts` solo encadena referencias a las librerías anteriores,
    // así que se genera desde `lib.es5.d.ts`, que sí declara los tipos base.
    const result = bind_lib("lib.es5.d.ts");
    expect(result.module.host_types.length).toBeGreaterThan(20);
    const parsed = parse_text("lib.es5.d.pengu", result.text);
    expect(parsed.diagnostics.map((item) => item.code)).toEqual([]);
  });
});
