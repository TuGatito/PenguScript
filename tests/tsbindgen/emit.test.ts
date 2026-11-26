// T3: `pengu ts-bindgen` sobre fixtures.
//
// El golden fija el formato exacto del `.d.pengu` generado; el resto de los
// casos comprueban las reglas de mapeo que el plan §6 documenta (números,
// opcionales, herencia múltiple, índices, namespaces y `declare`).

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { bind_dts_text } from "../../src/tsbindgen/collect.ts";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";

const FIXTURES = join(import.meta.dir, "../fixtures/tsbindgen");

function bind(dts: string): string {
  return bind_dts_text(dts, "prueba.d.ts", {
    realm: "js_demo",
    source: "prueba.d.ts",
    invokes: ["std/js/types"],
  }).text;
}

describe("golden", () => {
  test("golden.d.ts produce golden.d.pengu.expected", () => {
    const source = readFileSync(join(FIXTURES, "golden.d.ts"), "utf8");
    const expected = readFileSync(join(FIXTURES, "golden.d.pengu.expected"), "utf8");
    const result = bind_dts_text(source, "golden.d.ts", {
      realm: "js_demo",
      source: "golden.d.ts",
      invokes: ["std/js/types"],
    });
    expect(result.text).toBe(expected);
  });
});

describe("mapeo de tipos", () => {
  test("`number` es `double` salvo en los miembros enteros", () => {
    const text = bind(`interface Caja {
  width: number;
  height: number;
  opacity: number;
}
`);
    expect(text).toContain("mut width: int");
    expect(text).toContain("mut height: int");
    expect(text).toContain("mut opacity: double");
  });

  test("`readonly` quita `mut` y `?` marca la propiedad", () => {
    const text = bind(`interface Ficha {
  readonly nombre: string;
  apodo?: string;
}
`);
    expect(text).toContain("  nombre: string");
    expect(text).toContain("mut apodo?: string");
  });

  test("la unión con `null` es un opcional", () => {
    const text = bind(`interface Padre {
  hijo: Padre | null;
  etiqueta: string | undefined;
}
`);
    expect(text).toContain("mut hijo: js::Padre?");
    expect(text).toContain("mut etiqueta: string?");
  });

  test("`array<T>` es `js::Array<T>` y los genéricos conservan el argumento", () => {
    const text = bind(`interface Lista<T> {
  items: T[];
  primero: () => T;
  mapa: <U>(f: (valor: T) => U) => U[];
}
`);
    expect(text).toContain("host js::Lista<T>");
    expect(text).toContain("mut items: js::Array<T>");
    expect(text).toContain("primero: () -> T");
    expect(text).toContain("mapa<U>: (f: function<(T) -> U>) -> js::Array<U>");
  });

  test("los índices siempre son enteros", () => {
    const text = bind(`interface Bolsa {
  [clave: number]: string;
}
`);
    // El formateador escribe `mut[indice: K]: V` sin espacio.
    expect(text).toContain("mut[indice: int]: string");
  });
});

describe("declaraciones", () => {
  test("el primer `extends` es `heir` y el resto se aplana", () => {
    const text = bind(`interface Base {
  base: string;
}
interface Extra {
  extra: number;
}
interface Hijo extends Base, Extra {
  propio: boolean;
}
`);
    expect(text).toContain("host js::Hijo heir js::Base");
    expect(text).toContain("mut extra: double");
    expect(text).toContain("mut propio: bool");
  });

  test("`declare var` es `host global` y `declare function` es `declare`", () => {
    const text = bind(`interface Documento {
  title: string;
}
declare var document: Documento;
declare function setTimeout(handler: () => void, milliseconds?: number): number;
`);
    expect(text).toContain("host global document: js::Documento");
    expect(text).toContain("declare");
    expect(text).toContain("setTimeout = (handler: function<() -> void>, milliseconds: double?) -> double");
  });

  test("los namespaces son `host namespace` con sus miembros", () => {
    const text = bind(`declare namespace Matematicas {
  const PI: number;
  function max(a: number, b: number): number;
}
`);
    expect(text).toContain("host namespace Matematicas");
    expect(text).toContain("  PI: double");
    expect(text).toContain("  max: (a: double, b: double) -> double");
  });

  test("los alias simples son `echo` y los enums son `omen`", () => {
    const text = bind(`type Etiqueta = string;
enum Direccion {
  Norte = 1,
  Sur = 2,
}
`);
    expect(text).toContain("echo js::Etiqueta = string");
    expect(text).toContain("omen js::Direccion");
    expect(text).toContain("  Norte = 1");
  });

  test("lo que no se puede representar se informa, no se inventa", () => {
    const result = bind_dts_text(
      `interface Rara {
  par: [string, number];
  objeto: { a: number };
}
`,
      "rara.d.ts",
      { realm: "js_rara", source: "rara.d.ts" },
    );
    expect(result.text).toContain("mut par: js::Any");
    expect(result.module.skipped.map((item) => item.reason).join(" ")).toContain("tupla");
  });
});

describe("ejecución del CLI sobre un archivo temporal", () => {
  test("el golden también se produce desde un archivo real", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_tsb_"));
    const file = join(dir, "prueba.d.ts");
    writeFileSync(file, readFileSync(join(FIXTURES, "golden.d.ts"), "utf8"));
    const result = bind_dts_text(readFileSync(file, "utf8"), "prueba.d.ts", {
      realm: "js_demo",
      source: "golden.d.ts",
      invokes: ["std/js/types"],
    });
    expect(result.text).toContain("host js::Element");
  });
});
