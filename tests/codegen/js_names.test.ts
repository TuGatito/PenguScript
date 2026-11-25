// P0: nombres y literales del backend JS (§1.4 del plan). En JS no hay
// espacios de nombres, así que cada realm es un archivo y los símbolos que
// chocan con palabras reservadas o globales se sanean aquí, en un solo sitio.

import { describe, expect, test } from "bun:test";
import {
  JS_FILE_SUFFIX,
  RESERVED_FILE_NAMES,
  js_alias,
  js_bigint_literal,
  js_char_literal,
  js_file_name,
  js_identifier,
  js_number_literal,
  js_string_literal,
  js_unique_file_name,
} from "../../src/codegen/js_names.ts";

describe("js_identifier", () => {
  test("deja intactos los nombres normales", () => {
    expect(js_identifier("punto")).toBe("punto");
    expect(js_identifier("max_value")).toBe("max_value");
    expect(js_identifier("$tmp")).toBe("$tmp");
  });

  test("sanea caracteres prohibidos", () => {
    expect(js_identifier("a-b")).toBe("a_b");
    expect(js_identifier("a.b")).toBe("a_b");
    expect(js_identifier("a b")).toBe("a_b");
  });

  test("prefija si empieza por dígito", () => {
    expect(js_identifier("2d")).toBe("_2d");
  });

  test("escapa palabras reservadas y globales", () => {
    expect(js_identifier("class")).toBe("class_");
    expect(js_identifier("await")).toBe("await_");
    expect(js_identifier("Object")).toBe("Object_");
    expect(js_identifier("rt")).toBe("rt_");
    expect(js_identifier("len")).toBe("len");
  });
});

describe("js_alias", () => {
  test("el primero se queda con el nombre base", () => {
    const taken = new Set<string>();
    const alias = js_alias("abs", taken);
    expect(alias).toBe("abs");
    taken.add(alias);
    expect(js_alias("abs", taken)).toBe("abs_2");
  });

  test("no registra el alias: el llamante decide cuándo ocuparlo", () => {
    const taken = new Set<string>();
    expect(js_alias("abs", taken)).toBe("abs");
    expect(js_alias("abs", taken)).toBe("abs");
    expect(taken.size).toBe(0);
  });

  test("respeta colisiones con nombres reservados", () => {
    const taken = new Set<string>();
    expect(js_alias("class", taken)).toBe("class_");
  });
});

describe("js_file_name", () => {
  test("un archivo por realm, en minúsculas", () => {
    expect(js_file_name("puntos")).toBe("puntos.mjs");
    expect(js_file_name("String")).toBe("string.mjs");
    expect(js_file_name("std-io")).toBe("std-io.mjs");
    expect(JS_FILE_SUFFIX).toBe(".mjs");
  });

  test("un realm con caracteres raros produce un archivo válido", () => {
    expect(js_file_name("mi realm")).toBe("mi_realm.mjs");
    expect(js_file_name("2d")).toBe("_2d.mjs");
    expect(js_file_name("")).toBe("realm.mjs");
  });

  test("los nombres fijos del backend no se pierden al sanear", () => {
    expect(js_file_name("pengu_rt")).toBe("pengu_rt.mjs");
    expect([...RESERVED_FILE_NAMES].sort()).toEqual(["index.mjs", "pengu_rt.mjs"]);
  });
});

describe("js_unique_file_name", () => {
  test("respeta los nombres reservados del backend", () => {
    expect(js_unique_file_name("index.mjs", RESERVED_FILE_NAMES)).toBe("index_2.mjs");
    expect(js_unique_file_name("pengu_rt.mjs", RESERVED_FILE_NAMES)).toBe("pengu_rt_2.mjs");
  });

  test("dos realms que sanean igual no comparten archivo", () => {
    const taken = new Set<string>(RESERVED_FILE_NAMES);
    const first = js_unique_file_name(js_file_name("a b"), taken);
    taken.add(first);
    const second = js_unique_file_name(js_file_name("a_b"), taken);
    expect(first).toBe("a_b.mjs");
    expect(second).toBe("a_b_2.mjs");
  });

  test("acepta el nombre sin sufijo", () => {
    expect(js_unique_file_name("puntos", new Set())).toBe("puntos.mjs");
  });
});

describe("literales", () => {
  test("cadenas y caracteres", () => {
    expect(js_string_literal('hola "mundo"')).toBe('"hola \\"mundo\\""');
    expect(js_string_literal("línea\nnueva")).toBe('"línea\\nnueva"');
    expect(js_char_literal("a")).toBe('"a"');
    expect(js_char_literal("'")).toBe('"\'"');
    expect(js_char_literal("\n")).toBe('"\\n"');
    expect(js_char_literal("\\")).toBe('"\\\\"');
  });

  test("números", () => {
    expect(js_number_literal(1.5)).toBe("1.5");
    expect(js_number_literal(-2)).toBe("-2");
    expect(js_number_literal(1e21)).toBe("1e+21");
    expect(js_number_literal(-0)).toBe("-0");
    expect(js_number_literal(Infinity)).toBe("Infinity");
    expect(js_number_literal(-Infinity)).toBe("-Infinity");
    expect(js_number_literal(Number.NaN)).toBe("NaN");
  });

  test("BigInt", () => {
    expect(js_bigint_literal("42")).toBe("42n");
    expect(js_bigint_literal("-9223372036854775808")).toBe("-9223372036854775808n");
  });
});
