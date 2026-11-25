// Tests del checker para `async`/`await` (fase P5 del plan JavaScript).

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
  if (info === undefined) throw new Error(`no existe la función «${name}»`);
  return info.result;
}

describe("future<T>", () => {
  test("una función async devuelve future<T> y su cuerpo vale T", () => {
    const checked = expect_ok(`async doble = (n: int) -> int\n  n * 2\n`);
    const result = result_of(checked.module, "doble");
    expect(result.kind).toBe("named");
    if (result.kind !== "named") return;
    expect(result.name).toBe("future");
    expect(result.args[0]).toEqual({ kind: "primitive", name: "int" });
  });

  test("una función normal devuelve T", () => {
    const checked = expect_ok(`doble = (n: int) -> int\n  n * 2\n`);
    expect(result_of(checked.module, "doble")).toEqual({ kind: "primitive", name: "int" });
  });

  test("guardar el futuro sin await da un tipo future<T>", () => {
    expect_code(
      `async doble = (n: int) -> int
  n * 2

main = -> void
  const pendiente: int = doble(2)
`,
      "E0501",
    );
  });

  test("el mensaje de error nombra future<T>", () => {
    const checked = expect_code(
      `async doble = (n: int) -> int
  n * 2

main = -> void
  const pendiente: int = doble(2)
`,
      "E0501",
    );
    expect(checked.messages.some((message) => message.includes("future<int>"))).toBe(true);
  });

  test("await desenvuelve el futuro", () => {
    expect_ok(
      `async doble = (n: int) -> int
  n * 2

async main = -> int
  valor: int = await doble(21)
  valor
`,
    );
  });

  test("una lambda async devuelve future<T>", () => {
    expect_ok(
      `main = -> void
  f = async (n: int) -> int
    n
  const pendiente: future<int> = f(1)
`,
    );
  });
});

describe("await", () => {
  test("await fuera de async es E0516", () => {
    expect_code(
      `cargar = -> int
  await doble(1)
`,
      "E0516",
    );
  });

  test("una lambda no async dentro de una async no hereda el permiso", () => {
    expect_code(
      `async main = -> int
  f = (n: int) -> int
    await doble(n)
  0
`,
      "E0516",
    );
  });

  test("await de algo que no es un futuro es E0501", () => {
    const checked = expect_code(
      `async main = -> int
  await 3
`,
      "E0501",
    );
    expect(checked.messages.some((message) => message.includes("future<T>"))).toBe(true);
  });

  test("un ref local que cruza un await es E0606", () => {
    expect_code(
      `async esperar = () -> void
  pass

async leer = (texto: ref<string>) -> string
  r = ref(texto)
  await esperar()
  *r
`,
      "E0606",
    );
  });

  test("un ref que se suelta antes del await es legal", () => {
    expect_ok(
      `async esperar = () -> void
  pass

async leer = (valor: ref<int>) -> int
  copia = *valor
  await esperar()
  copia
`,
    );
  });

  test("await dentro de match, if, do y comprensiones es legal", () => {
    expect_ok(
      `async doble = (n: int) -> int
  n * 2

async main = -> int
  valor = match 1
    when 0 then await doble(1)
    else
      await doble(2)
  otro = if valor > 1
    await doble(valor)
  else
    0
  tercero = do
    await doble(3)
  valores = [await doble(i) for i in 0..2]
  if #valores > 0
    valor + otro + tercero
  else
    0
`,
    );
  });
});
