// Traducción de tipos PenguScript a JavaScript.
//
// El checker ya resolvió todos los tipos; aquí solo se decide cómo se
// representa cada uno en el código emitido. Este módulo no escribe nada:
// es la tabla de §2 del plan, en código, para que el emisor y el runtime
// no discrepen nunca.
//
// Modo de enteros de 64 bits (§12.1 #1): `bigint` por defecto, `number` con
// `--int64=number`. Los tipos host-nativos (§12.1 #8) quedan exentos de las
// dos cosas: ni se clonan ni se convierten.

import type { PenguType } from "../semantic/types.ts";
import { any_type, integer_shape } from "../semantic/types.ts";

export type Int64Mode = "bigint" | "number";

export const INT64_MODES: readonly Int64Mode[] = ["bigint", "number"];

export const DEFAULT_INT64_MODE: Int64Mode = "bigint";

export type Int64Choice =
  | { readonly ok: true; readonly mode: Int64Mode }
  | { readonly ok: false; readonly message: string };

// Lee `--int64`: `bigint` (por defecto) o `number` (con pérdida por encima
// de 2⁵³, documentada en el plan §12.1 #1).
export function parse_int64_mode(raw: string | undefined): Int64Choice {
  if (raw === undefined) return { ok: true, mode: DEFAULT_INT64_MODE };
  const normalized = raw.trim().toLowerCase();
  if (normalized === "bigint" || normalized === "number") return { ok: true, mode: normalized };
  return {
    ok: false,
    message: `--int64 «${raw}» no es válido; los modos disponibles son ${INT64_MODES.join(" y ")}`,
  };
}

// Tipos que representan directamente una referencia del host (futuros
// `std/js/*`). Se registran por nombre y nunca se clonan ni se convierten.
export const HOST_NATIVE_TYPES: ReadonlySet<string> = new Set<string>();

// Convención de los futuros `std/js/*`: sus tipos se llaman `js::Algo`.
export const HOST_NATIVE_PREFIX = "js::";

export function is_host_native(type: PenguType): boolean {
  if (type.kind !== "named") return false;
  if (HOST_NATIVE_TYPES.has(type.name) || type.name.startsWith(HOST_NATIVE_PREFIX)) return true;
  for (const arg of type.args) if (is_host_native(arg)) return true;
  return false;
}

// Nombre del tipo en el código emitido (para mensajes y JSDoc).
const PRIMITIVES: Readonly<Record<string, string>> = {
  bool: "boolean",
  char: "string",
  "signed char": "string",
  "unsigned char": "string",
  string: "string",
  wstring: "string",
  u8string: "string",
  u16string: "string",
  u32string: "string",
  string_view: "string",
  float: "number",
  double: "number",
  "long double": "number",
  wchar_t: "string",
  char8_t: "string",
  char16_t: "string",
  char32_t: "string",
  nullptr_t: "null",
};

const CONTAINERS: Readonly<Record<string, string>> = {
  vector: "Array",
  deque: "Array",
  list: "Array",
  forward_list: "Array",
  stack: "Array",
  queue: "Array",
  priority_queue: "Array",
  array: "Array",
  span: "Array",
  set: "Set",
  multiset: "Set",
  unordered_set: "Set",
  map: "Map",
  multimap: "Map",
  unordered_map: "Map",
  unordered_multimap: "Map",
  pair: "Array",
  tuple: "Array",
};

export function js_type(type: PenguType, mode: Int64Mode = DEFAULT_INT64_MODE): string {
  switch (type.kind) {
    case "primitive": {
      if (type.name === "void") return "undefined";
      if (type.name in PRIMITIVES) return PRIMITIVES[type.name] ?? type.name;
      if (type.name === "size_t" || type.name === "ptrdiff_t" || type.name === "intptr_t" || type.name === "uintptr_t") {
        return "number";
      }
      if (is_64_bit_integer(type) && mode === "bigint") return "bigint";
      return "number";
    }
    case "named": {
      if (type.name === "Ordering") return "number";
      if (type.name === "future") {
        return `Promise<${js_type(type.args[0] ?? any_type("future"), mode)}>`;
      }
      const container = CONTAINERS[type.name];
      if (container === "Array") {
        if (type.name === "pair" || type.name === "tuple") {
          return `[${type.args.map((arg) => js_type(arg, mode)).join(", ")}]`;
        }
        if (type.name === "array" || type.name === "span") {
          const element = type.args[0];
          return `${js_type(element ?? type, mode)}[]`;
        }
        const element = type.args[0];
        return `Array<${element === undefined ? "unknown" : js_type(element, mode)}>`;
      }
      if (container === "Set") {
        const element = type.args[0];
        return `Set<${element === undefined ? "unknown" : js_type(element, mode)}>`;
      }
      if (container === "Map") {
        const key = type.args[0];
        const value = type.args[1];
        return `Map<${key === undefined ? "unknown" : js_type(key, mode)}, ${value === undefined ? "unknown" : js_type(value, mode)}>`;
      }
      // Tipo de usuario (`rune`, `seal`, `echo`, `meld`): se usa su nombre.
      if (type.args.length === 0) return type.name;
      return `${type.name}<${type.args.map((arg) => js_type(arg, mode)).join(", ")}>`;
    }
    case "optional": {
      const inner = js_type(type.inner, mode);
      return needs_parentheses(type.inner) ? `(${inner}) | null` : `${inner} | null`;
    }
    case "ref":
      return js_type(type.inner, mode);
    case "raw":
      return `${js_type(type.inner, mode)} | null`;
    case "unique":
    case "shared":
      return js_type(type.inner, mode);
    case "weak":
      return `WeakRef<${js_type(type.inner, mode)}>`;
    case "function": {
      const params = type.variadic ? type.params.slice(0, -1) : type.params;
      const rendered = params.map((param, index) => `p${index}: ${js_type(param, mode)}`);
      if (type.variadic) {
        const element = type.params[type.params.length - 1];
        rendered.push(`...resto: Array<${element === undefined ? "unknown" : js_type(element, mode)}>`);
      }
      return `(${rendered.join(", ")}) => ${js_type(type.result, mode)}`;
    }
    case "tuple":
      return `[${type.items.map((item) => js_type(item, mode)).join(", ")}]`;
    case "array":
      return `${js_type(type.element, mode)}[]`;
    case "range":
      return "rt.Range";
    case "void":
      return "undefined";
    case "none":
      return "null";
    case "nullptr":
      return "null";
    case "any":
      return "any";
  }
}

// Tipo en posición de valor: lo mismo que `js_type`, pero una función
// variádica que no se puede deducir se degrada a la firma declarada.
export function js_value_type(type: PenguType | undefined, mode: Int64Mode = DEFAULT_INT64_MODE): string {
  if (type === undefined) return "undefined";
  return js_type(type, mode);
}

// Tipo para JSDoc (`--jsdoc`). En JS no hay tipos, así que se documenta el
// tipo de PenguScript con la forma de JS; es el mismo texto que `js_type`.
export function js_doc_type(type: PenguType, mode: Int64Mode = DEFAULT_INT64_MODE): string {
  return js_type(type, mode);
}

function needs_parentheses(type: PenguType): boolean {
  return type.kind === "function";
}

export function is_64_bit_integer(type: PenguType): boolean {
  const shape = integer_shape(type);
  return shape !== undefined && shape.bits === 64 && !is_size_like(type);
}

// `size_t` y compañía son de 64 bits en C++ pero se usan como índices y
// longitudes: se representan con `number` aunque el modo sea `bigint`.
function is_size_like(type: PenguType): boolean {
  if (type.kind !== "primitive") return false;
  return type.name === "size_t" || type.name === "ptrdiff_t" || type.name === "intptr_t" || type.name === "uintptr_t";
}

// ¿Este tipo se emite con literales y operaciones de `BigInt`?
export function is_bigint_type(type: PenguType, mode: Int64Mode = DEFAULT_INT64_MODE): boolean {
  if (mode !== "bigint") return false;
  if (is_host_native(type)) return false;
  return is_64_bit_integer(type);
}

// Etiqueta del tipo entero para la normalización de 32/16/8 bits.
export type JsIntegerKind = "int8" | "uint8" | "int16" | "uint16" | "int32" | "uint32";

export function js_integer_kind(type: PenguType): JsIntegerKind | undefined {
  const shape = integer_shape(type);
  if (shape === undefined) return undefined;
  if (shape.bits === 64) return undefined;
  if (shape.bits === 8) return shape.signed ? "int8" : "uint8";
  if (shape.bits === 16) return shape.signed ? "int16" : "uint16";
  return shape.signed ? "int32" : "uint32";
}

// Expresión que normaliza un valor entero al rango de su tipo. Se aplica en
// los puntos de copia (§2.2), no en cada operación.
export function js_int_normalizer(kind: JsIntegerKind): (expression: string) => string {
  switch (kind) {
    case "int8":
      return (expression) => `(((${expression}) << 24) >> 24)`;
    case "uint8":
      return (expression) => `((${expression}) & 0xff)`;
    case "int16":
      return (expression) => `(((${expression}) << 16) >> 16)`;
    case "uint16":
      return (expression) => `((${expression}) & 0xffff)`;
    case "int32":
      return (expression) => `((${expression}) | 0)`;
    case "uint32":
      return (expression) => `((${expression}) >>> 0)`;
  }
}

// Valor por defecto de un tipo cuando el fuente no da uno.
export function js_default_value(type: PenguType, mode: Int64Mode = DEFAULT_INT64_MODE): string {
  switch (type.kind) {
    case "primitive": {
      if (type.name === "bool") return "false";
      const js = PRIMITIVES[type.name];
      if (js === "string") return '""';
      if (is_bigint_type(type, mode)) return "0n";
      return "0";
    }
    case "optional":
    case "none":
    case "nullptr":
    case "raw":
    case "weak":
      return "null";
    case "void":
      return "undefined";
    case "any":
      return "null";
    case "named":
      if (type.name === "Ordering") return "rt.Ordering.Equal";
      return "undefined";
    default:
      return "undefined";
  }
}

// ¿Copiar un valor de este tipo en JS exige clonarlo para preservar la
// semántica de valor de C++? (§3.2 del plan)
export function needs_clone(type: PenguType): boolean {
  // Referencias del host: copiarlas por valor sería un error semántico.
  if (is_host_native(type)) return false;
  switch (type.kind) {
    case "primitive":
      // `string` y `char` son inmutables en JS; los números son valores.
      return false;
    case "named": {
      if (type.name === "Ordering") return false;
      // Un `future<T>` es una `Promise`: es un identificador, no un valor, y
      // clonarla rompería el objeto (`then` sobre un receptor incompatible).
      if (type.name === "future") return false;
      if (CONTAINERS[type.name] !== undefined) return true;
      // Un tipo de usuario (rune) puede ser un objeto plano o una clase:
      // ambos se copian campo a campo.
      return true;
    }
    case "optional":
      return needs_clone(type.inner);
    case "tuple":
      return true;
    case "array":
      return true;
    case "range":
    case "ref":
    case "raw":
    case "unique":
    case "shared":
    case "weak":
    case "function":
    case "void":
    case "none":
    case "nullptr":
      return false;
    case "any":
      return true;
  }
}
