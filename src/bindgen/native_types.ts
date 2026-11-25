// Resolución de tipos de C a tipos de PenguScript con el registro del
// encabezado: records, enums, typedefs (alias) y callbacks.

import type { NativeEnum, NativeHeader, NativeRecord } from "./clang_ast.ts";
import { map_c_type } from "./type_map.ts";

export interface TypeRegistry {
  readonly records: ReadonlyMap<string, NativeRecord>;
  readonly enums: ReadonlyMap<string, NativeEnum>;
  readonly aliases: ReadonlyMap<string, string>;
  readonly callbacks: ReadonlySet<string>;
}

export interface ResolvedType {
  readonly pengu: string;
  readonly ok: boolean;
  readonly note: string | undefined;
}

const MAX_DEPTH = 12;

function clean(qual_type: string): string {
  return qual_type
    .replace(/\bconst\b/g, "")
    .replace(/\bvolatile\b/g, "")
    .replace(/\brestrict\b/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^(struct|class|union|enum)\s+/, "")
    .replace(/[&]+$/, "")
    .trim();
}

export function build_registry(header: NativeHeader): TypeRegistry {
  const records = new Map<string, NativeRecord>();
  for (const record of header.records) records.set(record.name, record);
  const enums = new Map<string, NativeEnum>();
  for (const item of header.enums) enums.set(item.name, item);
  const callbacks = new Set<string>();
  const aliases = new Map<string, string>();
  for (const item of header.typedefs) {
    if (item.function_pointer) callbacks.add(item.name);
    else aliases.set(item.name, item.type);
  }
  return { records, enums, aliases, callbacks };
}

export function resolve_native_type(
  qual_type: string,
  registry: TypeRegistry,
  depth = 0,
): ResolvedType {
  const text = clean(qual_type);
  if (depth > MAX_DEPTH) return { pengu: "raw<void>", ok: true, note: "ciclo de typedefs" };

  // Arrays: `float[4]` → `array<float, 4>`.
  const array = /^(.*)\[(\d+)\]$/.exec(text);
  if (array !== null) {
    const inner = resolve_native_type(array[1] ?? "", registry, depth + 1);
    if (!inner.ok) return inner;
    return { pengu: `array<${inner.pengu}, ${array[2]}>`, ok: true, note: undefined };
  }

  // Punteros a función: se enlazan como `raw<void>`.
  if (/\(\s*\*/.test(text)) return { pengu: "raw<void>", ok: true, note: "puntero a función" };

  // Punteros: `char*` cruza como `string`; el resto como `raw<T>`.
  const pointer = /^(.*?)\s*\*+$/.exec(text);
  if (pointer !== null) {
    const inner = clean(pointer[1] ?? "");
    if (inner === "char") return { pengu: "string", ok: true, note: undefined };
    if (inner === "void") return { pengu: "raw<void>", ok: true, note: undefined };
    if (registry.aliases.has(inner)) return { pengu: `raw<${inner}>`, ok: true, note: undefined };
    if (registry.records.has(inner) || registry.enums.has(inner)) {
      return { pengu: `raw<${inner}>`, ok: true, note: undefined };
    }
    const primitive = map_c_type(inner);
    if (primitive.ok) return { pengu: `raw<${primitive.pengu}>`, ok: true, note: undefined };
    return { pengu: "raw<void>", ok: true, note: `puntero a «${inner}»` };
  }

  // Un typedef de función es un callback: se enlaza como `raw<void>`
  // (el puntero cruza la ABI igual y el usuario puede pasar `nullptr`).
  if (registry.callbacks.has(text)) return { pengu: "raw<void>", ok: true, note: "callback" };
  if (registry.aliases.has(text)) return { pengu: text, ok: true, note: undefined };
  if (registry.records.has(text) || registry.enums.has(text)) {
    return { pengu: text, ok: true, note: undefined };
  }

  const primitive = map_c_type(text);
  if (primitive.ok) return { pengu: primitive.pengu, ok: true, note: undefined };
  return { pengu: "int", ok: false, note: `tipo no traducible «${text}»` };
}

// Nombre final de un tipo (deshace alias) para ordenar records.
export function final_type_name(qual_type: string, registry: TypeRegistry, depth = 0): string | undefined {
  const text = clean(qual_type);
  if (depth > MAX_DEPTH) return undefined;
  const array = /^(.*)\[(\d+)\]$/.exec(text);
  if (array !== null) return final_type_name(array[1] ?? "", registry, depth + 1);
  if (/\(\s*\*/.test(text)) return undefined;
  const pointer = /^(.*?)\s*\*+$/.exec(text);
  if (pointer !== null) return final_type_name(pointer[1] ?? "", registry, depth + 1);
  if (registry.records.has(text) || registry.enums.has(text)) return text;
  const alias = registry.aliases.get(text);
  if (alias !== undefined) return final_type_name(alias, registry, depth + 1);
  return undefined;
}
