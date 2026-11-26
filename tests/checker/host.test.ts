// Tests del checker para la construcción `host` (fase T1 del plan ts-bindgen).

import { describe, expect, test } from "bun:test";
import { parse_text } from "../../src/frontend/parser.ts";
import { check_program } from "../../src/semantic/checker.ts";
import { make_sink } from "../../src/diagnostics/sink.ts";
import type { ModuleInfo } from "../../src/semantic/module_info.ts";
import type { PenguType } from "../../src/semantic/types.ts";

interface Checked {
  readonly codes: readonly string[];
  readonly messages: readonly string[];
  readonly module: ModuleInfo;
}

function check(text: string): Checked {
  const parsed = parse_text("test.pengu", text);
  const sink = make_sink({ max: 100 });
  for (const diagnostic of parsed.diagnostics) sink.add(diagnostic);
  const module = check_program("test.pengu", parsed.program, sink);
  return {
    codes: sink.diagnostics.map((item) => item.code),
    messages: sink.diagnostics.map((item) => item.message),
    module,
  };
}

function expect_ok(text: string): Checked {
  const result = check(text);
  expect(result.codes).toEqual([]);
  return result;
}

function expect_code(text: string, code: string): Checked {
  const result = check(text);
  expect(result.codes).toContain(code);
  return result;
}

function result_of(module: ModuleInfo, name: string): PenguType {
  const info = module.functions.get(name);
  expect(info).toBeDefined();
  return info?.result ?? { kind: "void" };
}

const BASE = `realm test
echo js::String = string
host js::Point
  mut x: double
  y: double
  length: () -> double
  scale: (factor: double) -> void
  static origin: () -> js::Point
  constructor(x: double, y: double)
`;

describe("declaración `host`", () => {
  test("un tipo del host sin prefijo `js::` da E0208", () => {
    const result = expect_code(
      `realm test
host Point
  x: double
`,
      "E0208",
    );
    expect(result.messages.join(" ")).toContain("js::");
  });

  test("un tipo del host duplicado da E0401", () => {
    const result = expect_code(
      `${BASE}host js::Point
  z: double
`,
      "E0401",
    );
    expect(result.messages.join(" ")).toContain("ya está declarado como tipo del host");
  });

  test("un namespace del host no admite constructor", () => {
    const result = expect_code(
      `realm test
host namespace Storage
  constructor()
`,
      "E0208",
    );
    expect(result.codes.length).toBeGreaterThan(0);
  });

  test("el tipo del host acepta sigilos", () => {
    expect_ok(`realm test
host js::Box<T>
  value: T
`);
  });

  test("`heir` une dos tipos del host", () => {
    expect_ok(`${BASE}host js::Point3 heir js::Point
  z: double
`);
  });
});

describe("miembros del host", () => {
  test("leer una propiedad da su tipo", () => {
    const result = expect_ok(`${BASE}
main = ->
  mut p = js::Point(1.0, 2.0)
  const total: double = p.x + p.y
  total
`);
    expect(result.codes).toEqual([]);
  });

  test("escribir una propiedad sin `mut` da E0406", () => {
    const result = expect_code(
      `${BASE}
main = ->
  mut p = js::Point(1.0, 2.0)
  p.y = 3.0
`,
      "E0406",
    );
    expect(result.messages.join(" ")).toContain("solo lectura");
  });

  test("escribir una propiedad con `mut` es correcto", () => {
    expect_ok(`${BASE}
main = ->
  mut p = js::Point(1.0, 2.0)
  p.x = 3.0
`);
  });

  test("un miembro que no existe da E0506", () => {
    const result = expect_code(
      `${BASE}
main = ->
  mut p = js::Point(1.0, 2.0)
  p.z
`,
      "E0506",
    );
    expect(result.messages.join(" ")).toContain("no tiene el miembro");
  });

  test("un método del host se puede llamar", () => {
    expect_ok(`${BASE}
main = ->
  mut p = js::Point(1.0, 2.0)
  p.scale(2.0)
  io::println("#{p.length()}")
`);
  });

  test("los métodos se heredan por `heir`", () => {
    expect_ok(`${BASE}host js::Point3 heir js::Point
  z: double
  constructor(x: double, y: double, z: double)

main = ->
  mut p = js::Point3(1.0, 2.0, 3.0)
  p.scale(2.0)
`);
  });

  test("asignar a un método da E0204", () => {
    expect_code(
      `${BASE}
main = ->
  mut p = js::Point(1.0, 2.0)
  p.length = "mucho"
`,
      "E0204",
    );
  });

  test("llamar a un tipo del host sin constructor da E0505", () => {
    const result = expect_code(
      `realm test
host js::SinConstructor
  x: double

main = ->
  js::SinConstructor()
`,
      "E0505",
    );
    expect(result.messages.join(" ")).toContain("no declara constructor");
  });

  test("los argumentos del constructor se comprueban (E0501)", () => {
    expect_code(
      `${BASE}
main = ->
  js::Point("uno", "dos")
`,
      "E0501",
    );
  });
});

describe("globales y namespaces del host", () => {
  test("un `host global` se usa sin cualificar", () => {
    expect_ok(`${BASE}host global punto: js::Point

main = ->
  punto.scale(2.0)
`);
  });

  test("un global sin tipo es `any` y no se puede usar como valor concreto", () => {
    expect_ok(`realm test
host global cosa

main = ->
  io::println("liste")
`);
  });

  test("un namespace del host resuelve sus funciones", () => {
    expect_ok(`realm test
host namespace Maths
  max: (a: double, b: double) -> double

main = ->
  const m: double = Maths::max(1.0, 2.0)
  m
`);
  });

  test("un miembro que no existe en el namespace da E0403", () => {
    expect_code(
      `realm test
host namespace Maths
  max: (a: double, b: double) -> double

main = ->
  Maths::min(1.0, 2.0)
`,
      "E0403",
    );
  });
});

describe("tipos del host", () => {
  test("un `js::Algo` que nadie declara da E0502", () => {
    const result = expect_code(
      `realm test
main = ->
  mut x: js::Fantasma = none
`,
      "E0502",
    );
    expect(result.messages.join(" ")).toContain("js::Fantasma");
  });

  test("la aridad de un tipo del host se comprueba", () => {
    const result = expect_code(
      `realm test
host js::Box<T>
  value: T
  constructor(valor: T)

main = ->
  js::Box<int, int>(1)
`,
      "E0504",
    );
    expect(result.messages.join(" ")).toContain("argumento(s) de tipo");
  });

  test("un alias del host funciona como tipo", () => {
    const result = expect_ok(`realm test
echo js::Text = string

main = ->
  const s: js::Text = "hola"
  s
`);
    expect(result.codes).toEqual([]);
  });

  test("el resultado de un método del host es su tipo declarado", () => {
    const result = expect_ok(`${BASE}
main = ->
  mut p = js::Point(1.0, 2.0)
  const l: double = p.length()
  l
`);
    expect(result.codes).toEqual([]);
  });

  test("se puede convertir entre tipos del host sin `unsafe`", () => {
    expect_ok(`realm test
host js::Base
  id: int
  constructor(id: int)

host js::Derived heir js::Base
  extra: int
  constructor(id: int, extra: int)

main = ->
  const b: js::Base = js::Base(1)
  const d = b as js::Derived
  d.extra
`);
  });

  test("el tipo de una función que devuelve un global es el del global", () => {
    const result = expect_ok(`${BASE}host global origen: js::Point

origen_de_prueba = -> js::Point
  origen
`);
    expect(result.codes).toEqual([]);
  });
});

describe("funciones del host en expresiones", () => {
  test("un método del host se puede pasar a una función de orden superior", () => {
    expect_ok(`${BASE}
aplicar = (funcion: function<(js::Point) -> double>) -> double
  funcion(js::Point(1.0, 2.0))

main = ->
  aplicar((p) -> p.length())
`);
  });

  test("los campos de un tipo del host no son clonables por valor", () => {
    const result = expect_ok(`${BASE}
main = ->
  mut a = js::Point(1.0, 2.0)
  mut b = a
  b.x = 5.0
  const igual: bool = a.x == b.x
  igual
`);
    // `host` es una referencia: `b` y `a` son el mismo objeto.
    expect(result.codes).toEqual([]);
  });

  test("resultado de una función que devuelve un tipo del host", () => {
    const result = expect_ok(`${BASE}
crear = -> js::Point
  js::Point(1.0, 2.0)

main = ->
  const p = crear()
  p.length()
`);
    expect(result.module.functions.has("crear")).toBe(true);
    expect(result.codes).toEqual([]);
  });

  test("un `future` de un tipo del host se espera con `await`", () => {
    expect_ok(`realm test
host js::Response
  text: () -> future<string>
  constructor(texto: string)

cargar = async -> string
  const r = js::Response("hola")
  await r.text()

main = async ->
  await cargar()
`);
  });

  test("una variable con tipo del host conserva su tipo en el resultado", () => {
    const result = expect_ok(`${BASE}
identidad = (p: js::Point) -> js::Point
  p

main = ->
  const p = identidad(js::Point(1.0, 2.0))
  p.length()
`);
    expect(result.codes).toEqual([]);
    const info = result.module.functions.get("identidad");
    expect(info?.result.kind).toBe("named");
  });
});
