// P0: tabla de tipos del backend JS (§2 del plan) y decisión de clonado
// (§3.2). Son funciones puras: lo que aquí se fija es el contrato que usan
// el emisor y el runtime, así que un cambio de criterio debe romper un test.

import { describe, expect, test } from "bun:test";
import {
  INT64_MODES,
  is_bigint_type,
  is_host_native,
  js_default_value,
  js_doc_type,
  js_int_normalizer,
  js_integer_kind,
  js_type,
  js_value_type,
  needs_clone,
  parse_int64_mode,
} from "../../src/codegen/js_types.ts";
import {
  BOOL,
  CHAR,
  INT,
  NONE,
  STRING,
  VOID,
  any_type,
  function_type,
  named,
  optional,
  primitive,
  range_type,
  ref_to,
  shared_type,
  tuple_type,
  unique_type,
  weak_type,
} from "../../src/semantic/types.ts";
import type { PenguType } from "../../src/semantic/types.ts";

const I64 = primitive("int64_t");
const U64 = primitive("uint64_t");
const SIZE = primitive("size_t");
const VECTOR_INT = named("vector", [INT]);
const MAP_STR_INT = named("map", [STRING, INT]);
const SET_STR = named("set", [STRING]);
const PAIR = named("pair", [INT, STRING]);
const RUNE = named("Punto");
const ARRAY3: PenguType = { kind: "array", element: INT, size: 3 };

describe("js_type", () => {
  test("primitivos", () => {
    expect(js_type(BOOL)).toBe("boolean");
    expect(js_type(CHAR)).toBe("string");
    expect(js_type(STRING)).toBe("string");
    expect(js_type(INT)).toBe("number");
    expect(js_type(VOID)).toBe("undefined");
    expect(js_type(NONE)).toBe("null");
    expect(js_type(primitive("float"))).toBe("number");
    expect(js_type(primitive("size_t"))).toBe("number");
  });

  test("enteros de 64 bits según el modo", () => {
    expect(js_type(I64)).toBe("bigint");
    expect(js_type(U64)).toBe("bigint");
    expect(js_type(I64, "number")).toBe("number");
    expect(js_type(SIZE)).toBe("number");
    expect(INT64_MODES).toEqual(["bigint", "number"]);
  });

  test("contenedores", () => {
    expect(js_type(VECTOR_INT)).toBe("Array<number>");
    expect(js_type(MAP_STR_INT)).toBe("Map<string, number>");
    expect(js_type(SET_STR)).toBe("Set<string>");
    expect(js_type(PAIR)).toBe("[number, string]");
    expect(js_type(ARRAY3)).toBe("number[]");
    expect(js_type(named("array", [STRING]))).toBe("string[]");
  });

  test("tipos de usuario y referencias", () => {
    expect(js_type(RUNE)).toBe("Punto");
    expect(js_type(named("Stack", [INT]))).toBe("Stack<number>");
    expect(js_type(optional(INT))).toBe("number | null");
    expect(js_type(optional(VECTOR_INT))).toBe("Array<number> | null");
    expect(js_type(ref_to(INT, true))).toBe("number");
    expect(js_type(unique_type(RUNE))).toBe("Punto");
    expect(js_type(shared_type(RUNE))).toBe("Punto");
    expect(js_type(weak_type(INT))).toBe("WeakRef<number>");
    expect(js_type(tuple_type([INT, STRING]))).toBe("[number, string]");
    expect(js_type(range_type(INT))).toBe("rt.Range");
    expect(js_type(function_type([INT], BOOL))).toBe("(p0: number) => boolean");
    expect(js_type(any_type("prueba"))).toBe("any");
    expect(js_type(named("Ordering"))).toBe("number");
  });

  test("js_value_type y js_doc_type coinciden con js_type", () => {
    expect(js_value_type(VECTOR_INT)).toBe("Array<number>");
    expect(js_value_type(undefined)).toBe("undefined");
    expect(js_doc_type(I64)).toBe("bigint");
  });
});

describe("needs_clone", () => {
  test("los valores inmutables y las referencias no se clonan", () => {
    expect(needs_clone(INT)).toBe(false);
    expect(needs_clone(STRING)).toBe(false);
    expect(needs_clone(CHAR)).toBe(false);
    expect(needs_clone(BOOL)).toBe(false);
    expect(needs_clone(VOID)).toBe(false);
    expect(needs_clone(NONE)).toBe(false);
    expect(needs_clone(ref_to(INT, false))).toBe(false);
    expect(needs_clone(unique_type(RUNE))).toBe(false);
    expect(needs_clone(shared_type(RUNE))).toBe(false);
    expect(needs_clone(weak_type(INT))).toBe(false);
    expect(needs_clone(range_type(INT))).toBe(false);
    expect(needs_clone(function_type([INT], BOOL))).toBe(false);
    expect(needs_clone(named("Ordering"))).toBe(false);
  });

  test("los tipos con semántica de valor se clonan", () => {
    expect(needs_clone(RUNE)).toBe(true);
    expect(needs_clone(VECTOR_INT)).toBe(true);
    expect(needs_clone(MAP_STR_INT)).toBe(true);
    expect(needs_clone(SET_STR)).toBe(true);
    expect(needs_clone(PAIR)).toBe(true);
    expect(needs_clone(tuple_type([INT]))).toBe(true);
    expect(needs_clone(ARRAY3)).toBe(true);
    expect(needs_clone(optional(VECTOR_INT))).toBe(true);
    expect(needs_clone(optional(INT))).toBe(false);
    // Conservador: `any` puede contener un contenedor.
    expect(needs_clone(any_type("prueba"))).toBe(true);
  });
});

describe("enteros y normalización", () => {
  test("tipo entero de 8, 16 y 32 bits", () => {
    expect(js_integer_kind(primitive("int8_t"))).toBe("int8");
    expect(js_integer_kind(primitive("uint8_t"))).toBe("uint8");
    expect(js_integer_kind(primitive("int16_t"))).toBe("int16");
    expect(js_integer_kind(primitive("unsigned short"))).toBe("uint16");
    expect(js_integer_kind(INT)).toBe("int32");
    expect(js_integer_kind(primitive("uint32_t"))).toBe("uint32");
    expect(js_integer_kind(I64)).toBeUndefined();
    expect(js_integer_kind(SIZE)).toBeUndefined();
    expect(js_integer_kind(STRING)).toBeUndefined();
  });

  test("normalizadores", () => {
    expect(js_int_normalizer("int32")("x + 1")).toBe("((x + 1) | 0)");
    expect(js_int_normalizer("uint32")("x")).toBe("((x) >>> 0)");
    expect(js_int_normalizer("int8")("x")).toBe("(((x) << 24) >> 24)");
    expect(js_int_normalizer("uint8")("x")).toBe("((x) & 0xff)");
  });

  test("BigInt solo para 64 bits reales", () => {
    expect(is_bigint_type(I64)).toBe(true);
    expect(is_bigint_type(U64)).toBe(true);
    expect(is_bigint_type(I64, "number")).toBe(false);
    expect(is_bigint_type(SIZE)).toBe(false);
    expect(is_bigint_type(INT)).toBe(false);
  });

  test("--int64 acepta bigint y number", () => {
    expect(parse_int64_mode(undefined)).toEqual({ ok: true, mode: "bigint" });
    expect(parse_int64_mode("number")).toEqual({ ok: true, mode: "number" });
    const invalid = parse_int64_mode("i128");
    expect(invalid.ok).toBe(false);
  });
});

describe("valores por defecto", () => {
  test("primitivos", () => {
    expect(js_default_value(BOOL)).toBe("false");
    expect(js_default_value(CHAR)).toBe('""');
    expect(js_default_value(STRING)).toBe('""');
    expect(js_default_value(INT)).toBe("0");
    expect(js_default_value(I64)).toBe("0n");
    expect(js_default_value(I64, "number")).toBe("0");
    expect(js_default_value(optional(INT))).toBe("null");
    expect(js_default_value(VOID)).toBe("undefined");
  });
});

describe("tipos host-nativos (§12.1 #8)", () => {
  const HOST = named("js::Number");

  test("se reconocen por el prefijo js::", () => {
    expect(is_host_native(HOST)).toBe(true);
    expect(is_host_native(named("vector", [HOST]))).toBe(true);
    expect(is_host_native(RUNE)).toBe(false);
  });

  test("no se clonan ni se convierten a BigInt", () => {
    expect(needs_clone(HOST)).toBe(false);
    expect(needs_clone(named("vector", [HOST]))).toBe(false);
    expect(is_bigint_type(HOST)).toBe(false);
  });
});
