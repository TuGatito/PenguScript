// Traducción de tipos de TypeScript a tipos de PenguScript.
//
// El catálogo del navegador se escribe con tipos `js::` (decisiones §10 del
// plan): los primitivos son `string`/`double`/`bool` para que los literales
// nativos pasen sin conversión, los contenedores son `js::Array<T>` y
// compañía, y todo lo demás es un tipo del host con su nombre real.
//
// `number` es el caso delicado: JavaScript no distingue enteros de flotantes,
// así que el mapeo por defecto es `double` y solo los miembros que el plan
// marca como enteros (`width`, `length`, `nodeType`…) se traducen a `int`.

import type { DtsKeyword, DtsMember, DtsParam, DtsType } from "./dts_type.ts";
import { is_keyword } from "../frontend/token.ts";

export interface MappedType {
  readonly text: string;
  // `false` cuando el tipo original no tiene traducción: el texto es solo una
  // aproximación (`js::Any`) y el llamante lo anota como omisión.
  readonly exact: boolean;
  readonly reason?: string;
}

// Miembros que el navegador documenta como enteros. Cambiar esta lista es la
// forma de ajustar el mapeo sin tocar el emisor.
export const INTEGER_MEMBERS: ReadonlySet<string> = new Set([
  "width",
  "height",
  "length",
  "size",
  "count",
  "index",
  "offset",
  "offsetX",
  "offsetY",
  "offsetWidth",
  "offsetHeight",
  "offsetLeft",
  "offsetTop",
  "clientWidth",
  "clientHeight",
  "clientLeft",
  "clientTop",
  "scrollWidth",
  "scrollHeight",
  "scrollLeft",
  "scrollTop",
  "nodeType",
  "nodeValue",
  "childElementCount",
  "tabIndex",
  "maxLength",
  "minLength",
  "selectionStart",
  "selectionEnd",
  "cols",
  "rows",
  "charCode",
  "keyCode",
  "button",
  "buttons",
  "detail",
  "deltaX",
  "deltaY",
  "deltaZ",
  "deltaMode",
  "pointerId",
  "pointerType",
  "clientX",
  "clientY",
  "screenX",
  "screenY",
  "pageX",
  "pageY",
  "movementX",
  "movementY",
  "ticks",
  "timeStamp",
  "lineNumber",
  "columnNumber",
  "newSize",
  "oldSize",
]);

// Nombres de TypeScript que no son tipos del host sino alias estructurales.
const ALIASES: Readonly<Record<string, string>> = {
  ReadonlyArray: "js::Array",
  ArrayLike: "js::Array",
  PromiseLike: "js::Promise",
  Record: "js::Object",
  Function: "js::Function",
  object: "js::Object",
  Object: "js::Object",
  HTMLElement: "js::HTMLElement",
  Element: "js::Element",
  Node: "js::Node",
  Document: "js::Document",
  Window: "js::Window",
};

// Genéricos donde `Partial<T>` y `Readonly<T>` solo envuelven al tipo real.
const TRANSPARENT = new Set(["Partial", "Readonly", "Required", "NonNullable"]);

export interface MapContext {
  // Nombre del miembro o parámetro que se está traduciendo (`width` → `int`).
  readonly name?: string;
  // Parámetros de tipo en vigor (`T` de `interface Lista<T>`): se emiten tal
  // cual, sin el prefijo `js::`.
  readonly params?: ReadonlySet<string>;
  // Tipos del módulo ya declarados (`interface`, `class`, `enum`): los demás
  // nombres se emiten igual, con el prefijo `js::`.
  readonly known?: ReadonlySet<string>;
}

export function map_type(type: DtsType, context: MapContext = {}): MappedType {
  switch (type.kind) {
    case "keyword":
      return map_keyword(type.name, context);
    case "literal":
      return { text: literal_type(type.value), exact: true };
    case "ref":
      return map_ref(type, context);
    case "array":
      return wrap("js::Array", [map_type(type.element, context)]);
    case "union":
      return map_union(type.items, context);
    case "intersection":
      return map_intersection(type.items, context);
    case "function":
      return {
        text: `function<(${type.params.map((param) => map_param(param, context).text).join(", ")}) -> ${map_type(type.result, context).text}>`,
        exact: true,
      };
    case "tuple":
      return {
        text: "js::Any",
        exact: false,
        reason: "tupla de TypeScript (usa una interfaz o `js::Array<T>`)",
      };
    case "object_literal":
      return { text: "js::Any", exact: false, reason: "objeto literal anónimo" };
    case "indexed":
      return {
        text: "js::Any",
        exact: false,
        reason: "tipo indexado (`T[K]`)",
      };
    case "keyof":
      return { text: "string", exact: false, reason: "`keyof` se traduce a `string`" };
    case "typeof":
      return { text: "js::Any", exact: false, reason: "`typeof` de un valor" };
    case "this_type":
      return { text: "js::Any", exact: false, reason: "tipo `this`" };
    case "unsupported":
      return { text: "js::Any", exact: false, reason: type.because };
  }
}

function map_keyword(name: DtsKeyword, context: MapContext): MappedType {
  switch (name) {
    case "string":
      return { text: "string", exact: true };
    case "number":
      return { text: integer_name(context.name) ? "int" : "double", exact: true };
    case "boolean":
      return { text: "bool", exact: true };
    case "void":
      return { text: "void", exact: true };
    case "any":
    case "unknown":
    case "object":
      return { text: "js::Any", exact: true };
    case "bigint":
      return { text: "int64_t", exact: true };
    case "symbol":
      return { text: "js::Any", exact: false, reason: "`symbol` no se puede construir" };
    case "null":
    case "undefined":
      // `null` no es un tipo en PenguScript: lo opcional se escribe `T?`.
      return { text: "js::Any", exact: false, reason: "tipo nulo suelto" };
    case "never":
      return { text: "js::Any", exact: false, reason: "tipo `never`" };
  }
}

function integer_name(name: string | undefined): boolean {
  return name !== undefined && INTEGER_MEMBERS.has(name);
}

function literal_type(value: string | number | boolean): string {
  if (typeof value === "string") return "string";
  if (typeof value === "boolean") return "bool";
  return Number.isInteger(value) ? "int" : "double";
}

function map_ref(type: Extract<DtsType, { kind: "ref" }>, context: MapContext): MappedType {
  const bare = type.name.includes(".") ? type.name.slice(type.name.lastIndexOf(".") + 1) : type.name;
  if (TRANSPARENT.has(bare) && type.args.length === 1) {
    const inner = type.args[0];
    return inner === undefined ? { text: "js::Any", exact: false } : map_type(inner, context);
  }
  if (context.params?.has(bare) === true) return { text: bare, exact: true };
  const alias = ALIASES[bare];
  const text = alias ?? `js::${bare}`;
  if (type.args.length === 0) return { text, exact: true };
  const args = type.args.map((arg) => map_type(arg, context));
  const exact = args.every((arg) => arg.exact);
  const reason = args.find((arg) => !arg.exact)?.reason;
  return {
    text: `${text}<${args.map((arg) => arg.text).join(", ")}>`,
    exact,
    reason: exact ? undefined : reason,
  };
}

function wrap(name: string, items: readonly MappedType[]): MappedType {
  const exact = items.every((item) => item.exact);
  return {
    text: `${name}<${items.map((item) => item.text).join(", ")}>`,
    exact,
    reason: items.find((item) => !item.exact)?.reason,
  };
}

function map_union(items: readonly DtsType[], context: MapContext): MappedType {
  const rest = items.filter((item) => !is_nullish(item));
  if (rest.length === 1) {
    const inner = rest[0];
    return inner === undefined
      ? { text: "none", exact: true }
      : { ...map_type(inner, context), text: `${map_type(inner, context).text}?` };
  }
  const all_literals = rest.every((item) => item.kind === "literal");
  if (all_literals && rest.length > 0) {
    const first = rest[0];
    if (first?.kind === "literal") {
      return { text: literal_type(first.value), exact: false, reason: "unión de literales" };
    }
  }
  return { text: "js::Any", exact: false, reason: "unión de varios tipos" };
}

function map_intersection(items: readonly DtsType[], context: MapContext): MappedType {
  const first = items[0];
  if (items.length === 1 && first !== undefined) return map_type(first, context);
  // `Window & typeof globalThis` y compañía: el objeto real es el primer tipo
  // con nombre (lo demás son mixins o `typeof`), así que se usa ese.
  const named = items.find((item) => item.kind === "ref");
  if (named !== undefined) return map_type(named, context);
  return { text: "js::Any", exact: false, reason: "intersección de tipos" };
}

function is_nullish(type: DtsType): boolean {
  return type.kind === "keyword" && (type.name === "null" || type.name === "undefined");
}

export function map_param(param: DtsParam, context: MapContext = {}): MappedType {
  const mapped = map_type(param.type, { ...context, name: param.name });
  if (param.rest) return mapped;
  if (param.optional) return { ...mapped, text: `${mapped.text}?` };
  return mapped;
}

export function map_result(type: DtsType, context: MapContext = {}): MappedType {
  return map_type(type, { ...context, name: undefined });
}

// Los parámetros con nombre que PenguScript no admite como nombre se sanean
// igual que en el bindgen de C.
// Nombre de parámetro válido en PenguScript: `from`, `in` y `as` son palabras
// clave del lenguaje, así que se les añade un guion bajo.
export function param_name(name: string): string {
  const cleaned = name.replace(/[^A-Za-z0-9_]/g, "_");
  if (cleaned === "") return "valor";
  if (/^[0-9]/.test(cleaned)) return `_${cleaned}`;
  return is_keyword(cleaned) ? `${cleaned}_` : cleaned;
}

export function param_text(param: DtsParam, context: MapContext = {}): string {
  const mapped = map_param(param, context);
  const name = param.rest ? `...${param_name(param.name)}` : param_name(param.name);
  return `${name}: ${mapped.text}`;
}

export function member_signature(member: DtsMember, context: MapContext = {}): MappedType {
  if (member.kind !== "method") {
    return { text: "js::Any", exact: false, reason: "miembro que no es método" };
  }
  const params = member.params.map((param) => param_text(param, context)).join(", ");
  const result = map_result(member.result, context).text;
  return { text: `(${params}) -> ${result}`, exact: true };
}
