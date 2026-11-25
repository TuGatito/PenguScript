// Intrínsecos de la biblioteca estándar: `realm::nombre` de un `declare` que
// el backend C++ resuelve a `::pengu::algo` o a `std::…` y que aquí resuelve
// al runtime JavaScript (`rt.algo`) o a un global (`Math.…`).
//
// Solo aparecen aquí las funciones que **no** se pueden escribir en
// PenguScript puro: el resto de `std/` se compila desde su fuente, así que
// este mapa es pequeño a propósito (crece por fases, §9 P4).

import { runtime_name, type JsContext } from "./js_context.ts";

// Las primitivas de `<cmath>` tienen equivalente directo en `Math` salvo las
// que redondean distinto (`round`, `nearbyint`) o no existen (`clamp`, `gcd`).
const MATH_JS: Readonly<Record<string, string>> = {
  sqrt: "Math.sqrt",
  cbrt: "Math.cbrt",
  abs: "Math.abs",
  floor: "Math.floor",
  ceil: "Math.ceil",
  trunc: "Math.trunc",
  pow: "Math.pow",
  min: "Math.min",
  max: "Math.max",
  sin: "Math.sin",
  cos: "Math.cos",
  tan: "Math.tan",
  asin: "Math.asin",
  acos: "Math.acos",
  atan: "Math.atan",
  atan2: "Math.atan2",
  sinh: "Math.sinh",
  cosh: "Math.cosh",
  tanh: "Math.tanh",
  asinh: "Math.asinh",
  acosh: "Math.acosh",
  atanh: "Math.atanh",
  exp: "Math.exp",
  exp2: "rt.exp2",
  expm1: "Math.expm1",
  ln: "Math.log",
  log2: "Math.log2",
  log10: "Math.log10",
  log1p: "Math.log1p",
  hypot: "Math.hypot",
  fmod: "rt.fmod",
  remainder: "rt.remainder",
  fdim: "rt.fdim",
  fmax: "Math.max",
  fmin: "Math.min",
  copysign: "rt.copysign",
  fma: "rt.fma",
  signbit: "rt.signbit",
  is_finite: "Number.isFinite",
  is_infinite: "rt.is_infinite",
  is_nan: "Number.isNaN",
  round: "rt.round",
  nearbyint: "rt.nearbyint",
  clamp: "rt.clamp",
  gcd: "rt.gcd",
  lcm: "rt.lcm",
  infinite: "rt.infinite",
  not_a_number: "rt.nan",
};

// `std/string`: las variantes `*_raw` reciben `ref<string>` pero leen la
// cadena tal cual (las cadenas de JS son inmutables).
const STRING_JS: Readonly<Record<string, string>> = {
  find_raw: "rt.find_raw",
  rfind_raw: "rt.rfind_raw",
  find_from_raw: "rt.find_from_raw",
  trim_raw: "rt.trim_raw",
  to_upper_raw: "rt.to_upper_raw",
  to_lower_raw: "rt.to_lower_raw",
  split_raw: "rt.split_raw",
  split_whitespace_raw: "rt.split_whitespace_raw",
  replace_first_raw: "rt.replace_first_raw",
  reverse_raw: "rt.reverse_raw",
  char_count_raw: "rt.char_count_raw",
  parse_int_raw: "rt.parse_int_raw",
  parse_double_raw: "rt.parse_double_raw",
  bytes_raw: "rt.bytes_raw",
};

const STRING_FUNCTIONS: ReadonlyMap<string, string> = new Map(
  Object.entries(STRING_JS).map(([name, target]) => [`string::${name}`, target]),
);

const MATH_FUNCTIONS: ReadonlyMap<string, string> = new Map(
  Object.entries(MATH_JS).map(([name, target]) => [`math::${name}`, target]),
);

// `std/float` y `std/long_double` re-declaran las mismas primitivas (§7.3).
const FLOAT_FUNCTIONS: ReadonlyMap<string, string> = new Map(
  ["float", "long_double"].flatMap((realm) =>
    Object.entries(MATH_JS).map(([name, target]) => [`${realm}::${name}`, target]),
  ),
);

export const BUILTIN_JS: ReadonlyMap<string, string> = new Map([
  // Salida y entrada (P1).
  ["io::write_values", "rt.write_values"],
  ["io::eprint_values", "rt.eprint_values"],
  ["io::flush", "rt.flush"],
  ["io::is_terminal", "rt.is_terminal"],
  ["format::format_values", "rt.format_values"],
  ["assert::that", "rt.assert_that"],
  ["assert::fail", "rt.assert_fail"],
  ...MATH_FUNCTIONS,
  ...FLOAT_FUNCTIONS,
  ...STRING_FUNCTIONS,
]);

// Intrínsecos del lenguaje (no vienen de un `declare`). En C++ son
// `::pengu::panic`; aquí `rt.panic`.
export const LANGUAGE_BUILTINS_JS: ReadonlyMap<string, string> = new Map([
  ["panic", "rt.panic"],
]);

// Destino JS de un intrínseco, o `undefined` si no está implementado todavía.
export function builtin_js_target(g: JsContext, realm: string, name: string): string | undefined {
  const target = BUILTIN_JS.get(`${realm}::${name}`) ?? LANGUAGE_BUILTINS_JS.get(name);
  if (target === undefined) return undefined;
  // `Math.*` y `Number.*` son globales: no arrastran el runtime.
  if (target.startsWith("rt.")) runtime_name(g);
  return target;
}
