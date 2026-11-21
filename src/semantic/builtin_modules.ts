// Firmas de la biblioteca estándar todavía intrínseca.
//
// Hasta que existan los módulos `std/*.pengu`, el checker conoce las
// firmas aquí declaradas y el codegen las traduce al runtime C++.

import { BOOL, DOUBLE, INT, STRING, VOID, any_type, function_type, named, optional } from "./types.ts";
import type { PenguType } from "./types.ts";

export interface BuiltinFunction {
  readonly params: readonly PenguType[];
  readonly result: PenguType;
  readonly variadic?: boolean;
}

const ANY = any_type("valor de la biblioteca estándar");
const T = (params: readonly PenguType[], result: PenguType, variadic = false): BuiltinFunction => ({
  params,
  result,
  variadic,
});

export const BUILTIN_SIGNATURES: ReadonlyMap<string, ReadonlyMap<string, BuiltinFunction>> = new Map([
  [
    "io",
    new Map([
      ["println", T([], VOID, true)],
      ["print", T([], VOID, true)],
      ["eprintln", T([], VOID, true)],
      ["eprint", T([], VOID, true)],
      ["read_line", T([], STRING)],
    ]),
  ],
  [
    "math",
    new Map<string, BuiltinFunction>([
      ["pi", T([], DOUBLE)],
      ["e", T([], DOUBLE)],
      ["abs", T([DOUBLE], DOUBLE)],
      ["sqrt", T([DOUBLE], DOUBLE)],
      ["pow", T([DOUBLE, DOUBLE], DOUBLE)],
      ["floor", T([DOUBLE], DOUBLE)],
      ["ceil", T([DOUBLE], DOUBLE)],
      ["round", T([DOUBLE], DOUBLE)],
      ["sin", T([DOUBLE], DOUBLE)],
      ["cos", T([DOUBLE], DOUBLE)],
      ["tan", T([DOUBLE], DOUBLE)],
      ["min", T([DOUBLE, DOUBLE], DOUBLE)],
      ["max", T([DOUBLE, DOUBLE], DOUBLE)],
      ["clamp", T([DOUBLE, DOUBLE, DOUBLE], DOUBLE)],
    ]),
  ],
  [
    "fs",
    new Map([
      ["read_to_string", T([STRING], optional(STRING))],
      ["write_string", T([STRING, STRING], BOOL)],
      ["exists", T([STRING], BOOL)],
      ["is_dir", T([STRING], BOOL)],
      ["remove", T([STRING], BOOL)],
      ["create_dir", T([STRING], BOOL)],
    ]),
  ],
  [
    "format",
    new Map([["format", T([STRING], STRING, true)]]),
  ],
  [
    "time",
    new Map([
      ["now_millis", T([], INT)],
      ["sleep_millis", T([INT], VOID)],
      ["now_seconds", T([], INT)],
    ]),
  ],
  [
    "os",
    new Map([
      ["args", T([], named("vector", [STRING]))],
      ["exit", T([INT], VOID)],
      ["get_env", T([STRING], optional(STRING))],
    ]),
  ],
  [
    "random",
    new Map([
      ["int", T([INT, INT], INT)],
      ["float", T([], DOUBLE)],
      ["bool", T([], BOOL)],
    ]),
  ],
  [
    "log",
    new Map([
      ["debug", T([], VOID, true)],
      ["info", T([], VOID, true)],
      ["warn", T([], VOID, true)],
      ["error", T([], VOID, true)],
    ]),
  ],
  [
    "assert",
    new Map([
      ["that", T([BOOL], VOID)],
      ["fail", T([STRING], VOID)],
    ]),
  ],
]);

export function builtin_function(module_name: string, symbol: string): BuiltinFunction | undefined {
  return BUILTIN_SIGNATURES.get(module_name)?.get(symbol);
}

export function is_builtin_module(module_name: string): boolean {
  return BUILTIN_SIGNATURES.has(module_name);
}

export type { PenguType };
