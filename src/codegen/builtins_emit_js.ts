// Intrínsecos de la biblioteca estándar: `realm::nombre` de un `declare` que
// el backend C++ resuelve a `::pengu::algo` y que aquí resuelve al runtime
// JavaScript (`rt.algo`).
//
// Solo aparecen aquí las funciones que **no** se pueden escribir en
// PenguScript puro: el resto de `std/` se compila desde su fuente, así que
// este mapa es pequeño a propósito (crece por fases, §9 P4).

import { runtime_name, type JsContext } from "./js_context.ts";

export const BUILTIN_JS: ReadonlyMap<string, string> = new Map([
  // Salida y entrada (P1).
  ["io::write_values", "rt.write_values"],
  ["io::eprint_values", "rt.eprint_values"],
  ["io::flush", "rt.flush"],
  ["io::is_terminal", "rt.is_terminal"],
  ["format::format_values", "rt.format_values"],
  ["assert::that", "rt.assert_that"],
  ["assert::fail", "rt.assert_fail"],
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
  runtime_name(g);
  return target;
}
