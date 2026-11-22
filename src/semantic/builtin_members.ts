// Miembros y métodos de los tipos incorporados.
//
// Los métodos reales vivirán en `std/`; aquí se declaran las firmas
// mínimas que el checker necesita para no dar falsos errores.

import type { PenguType } from "./types.ts";
import {
  BOOL,
  CHAR,
  DOUBLE,
  SIZE_T,
  STRING,
  VOID,
  any_type,
  function_type,
  named,
  optional,
  ref_to,
} from "./types.ts";

export const ANY_UNUSED = any_type("método incorporado");

const FLOATING_METHODS: ReadonlySet<string> = new Set(["float", "double", "long double"]);

const FIXED_SEQUENCES = new Set(["array", "span"]);

const container_names = new Set([
  "vector",
  "deque",
  "list",
  "forward_list",
  "span",
  "array",
]);

const set_names = new Set(["set", "multiset", "unordered_set", "unordered_multiset"]);

const map_names = new Set([
  "map",
  "multimap",
  "unordered_map",
  "unordered_multimap",
]);

const string_names = new Set([
  "string",
  "wstring",
  "u8string",
  "u16string",
  "u32string",
  "string_view",
]);

export function is_sequence_container(type: PenguType): boolean {
  if (type.kind === "array") return true;
  return type.kind === "named" && container_names.has(type.name);
}

export function sequence_element(type: PenguType): PenguType | undefined {
  if (type.kind === "array") return type.element;
  if (type.kind === "named" && container_names.has(type.name)) return type.args[0];
  return undefined;
}

export function is_string_type(type: PenguType): boolean {
  return type.kind === "primitive" && string_names.has(type.name);
}

export function is_map_type(type: PenguType): boolean {
  return type.kind === "named" && map_names.has(type.name);
}

export function is_set_type(type: PenguType): boolean {
  return type.kind === "named" && set_names.has(type.name);
}

export function map_key_value(type: PenguType): { key: PenguType; value: PenguType } | undefined {
  if (!is_map_type(type) || type.kind !== "named") return undefined;
  const key = type.args[0] ?? ANY_UNUSED;
  const value = type.args[1] ?? ANY_UNUSED;
  return { key, value };
}

export const adapter_names = new Set(["stack", "queue", "priority_queue"]);

export function is_adapter_type(type: PenguType): boolean {
  return type.kind === "named" && adapter_names.has(type.name);
}

const bitset_names = new Set(["bitset"]);

const sync_names = new Set(["mutex", "shared_mutex", "condition_variable"]);

// Métodos de `Ordering`: comparan el resultado de un `<=>`.
const ORDERING_METHODS: ReadonlyMap<string, PenguType> = new Map([
  ["is_lt", function_type([], BOOL)],
  ["is_eq", function_type([], BOOL)],
  ["is_gt", function_type([], BOOL)],
  ["reverse", function_type([], named("Ordering"))],
]);

export function member_of_builtin(type: PenguType, name: string): PenguType | undefined {
  if (type.kind === "any") return any_type("miembro desconocido");

  if (type.kind === "named" && type.name === "Ordering") return ORDERING_METHODS.get(name);

  if (type.kind === "named" && type.name === "atomic") {
    const inner = type.args[0] ?? ANY_UNUSED;
    if (name === "load") return function_type([], inner);
    if (name === "store") return function_type([inner], VOID);
    if (name === "fetch_add") return function_type([inner], inner);
    return undefined;
  }

  if (type.kind === "named" && type.name === "complex") {
    if (name === "real" || name === "imag") return function_type([], type.args[0] ?? DOUBLE);
    return undefined;
  }

  if (type.kind === "named" && type.name === "thread") {
    if (name === "join" || name === "detach") return function_type([], VOID);
    return undefined;
  }

  if (type.kind === "named" && sync_names.has(type.name)) {
    if (name === "lock" || name === "unlock") return function_type([], VOID);
    if (name === "lock_shared" || name === "unlock_shared") return function_type([], VOID);
    return undefined;
  }

  if (type.kind === "named" && adapter_names.has(type.name)) {
    const element = type.args[0] ?? ANY_UNUSED;
    switch (name) {
      case "size":
      case "len":
        return function_type([], SIZE_T);
      case "is_empty":
        return function_type([], BOOL);
      case "push":
      case "push_back":
        return function_type([element], VOID);
      case "pop":
        return function_type([], VOID);
      case "top":
      case "front":
      case "back":
        return function_type([], ref_to(element, false));
      default:
        return undefined;
    }
  }

  if (type.kind === "named" && bitset_names.has(type.name)) {
    switch (name) {
      case "size":
      case "len":
      case "count":
        return function_type([], SIZE_T);
      case "test":
        return function_type([SIZE_T], BOOL);
      case "set":
      case "reset":
      case "flip":
        return function_type([SIZE_T], VOID);
      case "all":
      case "any":
      case "none":
        return function_type([], BOOL);
      default:
        return undefined;
    }
  }

  if (type.kind === "primitive" && FLOATING_METHODS.has(type.name)) {
    switch (name) {
      case "sqrt":
      case "abs":
        return function_type([], type);
      case "is_nan":
        return function_type([], BOOL);
    }
    return undefined;
  }

  if (type.kind === "optional") {
    if (name === "value") return function_type([], type.inner);
    if (name === "value_or") return function_type([type.inner], type.inner);
    if (name === "is_some" || name === "is_none") return function_type([], BOOL);
    return undefined;
  }

  if (is_sequence_container(type)) {
    const element = sequence_element(type) ?? ANY_UNUSED;
    // `array<T, N>` y `span<T>` tienen longitud fija: no admiten cambios
    // estructurales (el cheatsheet lo promete y el C++ lo impone).
    const fixed =
      type.kind === "array" || (type.kind === "named" && FIXED_SEQUENCES.has(type.name));
    const structural = new Set([
      "push",
      "push_back",
      "pop",
      "pop_opt",
      "pop_back",
      "insert",
      "remove",
      "remove_at",
      "clear",
    ]);
    if (fixed && structural.has(name)) return undefined;
    switch (name) {
      case "size":
      case "len":
        return function_type([], SIZE_T);
      case "is_empty":
        return function_type([], BOOL);
      case "push":
      case "push_back":
        return function_type([element], VOID);
      case "insert":
        return function_type([SIZE_T, element], VOID);
      case "pop":
        return function_type([], element);
      case "pop_opt":
      case "pop_back":
        return function_type([], optional(element));
      case "remove":
        return function_type([element], BOOL);
      case "get":
        return function_type([SIZE_T], optional(element));
      case "get_unchecked":
        return function_type([SIZE_T], ref_to(element, false));
      case "first":
      case "front":
        return function_type([], ref_to(element, false));
      case "last":
      case "back":
        return function_type([], ref_to(element, false));
      case "contains":
        return function_type([element], BOOL);
      case "clear":
        return function_type([], VOID);
      case "remove_at":
        return function_type([SIZE_T], element);
      default:
        return undefined;
    }
  }

  if (is_map_type(type)) {
    const pair = map_key_value(type);
    if (!pair) return undefined;
    switch (name) {
      case "size":
      case "len":
        return function_type([], SIZE_T);
      case "is_empty":
        return function_type([], BOOL);
      case "get":
        return function_type([pair.key], optional(pair.value));
      case "get_or":
        return function_type([pair.key, pair.value], pair.value);
      case "extract":
        return function_type([pair.key], optional(pair.value));
      case "insert":
        return function_type([pair.key, pair.value], BOOL);
      case "insert_or_assign":
        return function_type([pair.key, pair.value], BOOL);
      case "remove":
        return function_type([pair.key], optional(pair.value));
      case "contains":
        return function_type([pair.key], BOOL);
      case "keys":
        return function_type([], named("vector", [pair.key]));
      case "values":
        return function_type([], named("vector", [pair.value]));
      case "clear":
        return function_type([], VOID);
      default:
        return undefined;
    }
  }

  if (is_set_type(type)) {
    const element = type.kind === "named" ? (type.args[0] ?? ANY_UNUSED) : ANY_UNUSED;
    switch (name) {
      case "size":
      case "len":
        return function_type([], SIZE_T);
      case "is_empty":
        return function_type([], BOOL);
      case "insert":
        return function_type([element], BOOL);
      case "remove":
        return function_type([element], BOOL);
      case "contains":
        return function_type([element], BOOL);
      case "clear":
        return function_type([], VOID);
      default:
        return undefined;
    }
  }

  if (is_string_type(type)) {
    switch (name) {
      case "size":
      case "len":
        return function_type([], SIZE_T);
      case "is_empty":
        return function_type([], BOOL);
      case "contains":
        return function_type([STRING], BOOL);
      case "find":
        return function_type([STRING], optional(SIZE_T));
      case "substr":
        return function_type([SIZE_T, SIZE_T], STRING);
      case "starts_with":
      case "ends_with":
        return function_type([STRING], BOOL);
      default:
        return undefined;
    }
  }

  if (type.kind === "range") {
    switch (name) {
      case "start":
      case "end":
        return function_type([], type.element);
      case "is_empty":
        return function_type([], BOOL);
      default:
        return undefined;
    }
  }

  if (type.kind === "tuple" || (type.kind === "named" && type.name === "pair")) {
    const items = type.kind === "tuple" ? type.items : type.args;
    if (name === "first") return items[0] ?? ANY_UNUSED;
    if (name === "second") return items[1] ?? ANY_UNUSED;
    return undefined;
  }

  if (type.kind === "ref") return member_of_builtin(type.inner, name);
  if (type.kind === "unique" || type.kind === "shared") return member_of_builtin(type.inner, name);
  if (type.kind === "weak" && name === "lock") return function_type([], optional(type.inner));

  return undefined;
}

export function builtin_index_result(type: PenguType): PenguType | undefined {
  if (type.kind === "array") return type.element;
  if (type.kind === "named" && container_names.has(type.name)) return type.args[0];
  if (type.kind === "named" && map_names.has(type.name)) return type.args[1];
  if (type.kind === "named" && type.name === "bitset") return BOOL;
  if (is_string_type(type)) return CHAR;
  return undefined;
}

// Nombres de miembros incorporados que puede tener un tipo: los usa la
// finalización del LSP para enumerar sin duplicar las tablas.
const MEMBER_CANDIDATES: readonly string[] = [
  "size", "len", "is_empty", "push", "push_back", "pop", "pop_back", "pop_opt",
  "get", "get_unchecked", "front", "back", "top", "contains", "clear", "remove",
  "remove_at", "insert", "insert_or_assign", "get_or", "extract", "keys", "values",
  "find", "substr", "starts_with", "ends_with", "value", "value_or", "is_some",
  "is_none", "first", "second", "lock", "unlock", "lock_shared", "unlock_shared",
  "is_lt", "is_eq", "is_gt", "reverse", "load", "store", "fetch_add", "real",
  "imag", "join", "detach", "test", "set", "reset", "flip", "count", "all",
  "any", "none", "sqrt", "abs", "is_nan",
];

export function builtin_member_names(type: PenguType): string[] {
  return MEMBER_CANDIDATES.filter((name) => member_of_builtin(type, name) !== undefined);
}
