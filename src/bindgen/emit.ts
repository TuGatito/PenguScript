// Generación del archivo `.d.pengu` a partir de una cabecera C.
//
// El archivo lleva, en este orden: enums (omens), records (runes y
// melds) ordenados por dependencias, alias (echo) y el bloque
// `extern "C"` con las funciones.

import type { NativeEnum, NativeHeader, NativeRecord } from "./clang_ast.ts";
import type { MacroTable, NativeConstant } from "./macros.ts";
import type { BaseTypes } from "./base.ts";
import { build_registry, resolve_native_type } from "./native_types.ts";
import type { TypeRegistry } from "./native_types.ts";
import { order_records } from "./records.ts";
import { is_keyword } from "../frontend/token.ts";

export interface BindingReport {
  readonly text: string;
  readonly functions: number;
  readonly constants: number;
  readonly skipped: readonly string[];
}

export function sanitize_realm(name: string): string {
  const base = name.replace(/\.[^.]*$/, "");
  let out = "";
  for (const char of base) out += /[A-Za-z0-9_]/.test(char) ? char : "_";
  return /^[A-Za-z_]/.test(out) ? out : `_${out}`;
}

// Un identificador de C que es keyword de PenguScript se sufija con `_`:
// los nombres de parámetros y campos no afectan al símbolo del enlazador.
export function sanitize_identifier(name: string): string {
  if (name.length === 0) return "_";
  const base = /^[A-Za-z_]/.test(name) ? name : `_${name}`;
  return is_keyword(base) ? `${base}_` : base;
}

function render_enum(item: NativeEnum): string[] {
  const lines = [`omen ${item.name}`];
  for (const variant of item.variants) {
    lines.push(`  ${sanitize_identifier(variant.name)} = ${variant.value}`);
  }
  return lines;
}

function render_record(record: NativeRecord, registry: TypeRegistry): { lines: string[]; error: string | undefined } {
  const fields: string[] = [];
  for (const field of record.fields) {
    // Dentro de los records los alias se resuelven al tipo final: el
    // `echo` se emite después y no puede usarse antes de declararse.
    const target = final_field_type(field.type, registry);
    if (target === undefined) {
      return { lines: [], error: `campo «${field.name}» de tipo no traducible «${field.type}»` };
    }
    if (field.bits !== undefined) {
      if (record.is_union) return { lines: [], error: `el campo «${field.name}» es un bitfield en una unión` };
      fields.push(`  bits ${field.bits} ${sanitize_identifier(field.name)}: ${target}`);
    } else {
      fields.push(`  ${sanitize_identifier(field.name)}: ${target}`);
    }
  }
  return { lines: [`${record.is_union ? "meld" : "rune"} ${record.name}`, ...fields], error: undefined };
}

function final_field_type(qual_type: string, registry: TypeRegistry, depth = 0): string | undefined {
  if (depth > 12) return undefined;
  const text = qual_type
    .replace(/\bconst\b/g, "")
    .replace(/\bvolatile\b/g, "")
    .replace(/\s+/g, " ")
    .trim();
  const pointer = /^(.*?)\s*\*+$/.exec(text);
  if (pointer !== null) {
    const inner = (pointer[1] ?? "").trim();
    const resolved = final_field_type(inner, registry, depth + 1);
    // Un puntero a un tipo que no conocemos sigue siendo un puntero.
    return resolved === undefined ? "raw<void>" : `raw<${resolved}>`;
  }
  const array = /^(.*)\[(\d+)\]$/.exec(text);
  if (array !== null) {
    const inner = final_field_type(array[1] ?? "", registry, depth + 1);
    return inner === undefined ? undefined : `array<${inner}, ${array[2]}>`;
  }
  const bare = text.replace(/^(struct|class|union|enum)\s+/, "");
  const alias = registry.aliases.get(bare);
  if (alias !== undefined) return final_field_type(alias, registry, depth + 1);
  const resolved = resolve_native_type(bare, registry);
  if (resolved.ok) return resolved.pengu;
  return undefined;
}

function alias_target(qual_type: string, registry: TypeRegistry): string | undefined {
  const text = qual_type.replace(/\s+/g, " ").trim();
  const alias = registry.aliases.get(text);
  if (alias !== undefined) return alias_target(alias, registry);
  const bare = text.replace(/^(struct|class|union|enum)\s+/, "");
  if (registry.records.has(bare) || registry.enums.has(bare)) return bare;
  const resolved = resolve_native_type(bare, registry);
  return resolved.ok && resolved.pengu !== "int" ? resolved.pengu : undefined;
}

function render_constant(item: NativeConstant): string {
  return `${item.kind} ${item.name}: ${item.type} = ${item.value}`;
}

export function render_bindings(
  header_name: string,
  realm: string,
  header: NativeHeader,
  macros: MacroTable = { constants: [], skipped: [] },
  links: readonly string[] = [],
  base?: BaseTypes,
): BindingReport {
  const registry = build_registry(header, base);
  const lines: string[] = [
    `-- Enlaces generados por «pengu bindgen» desde ${header_name}.`,
    "-- No edites este archivo a mano: vuelve a ejecutar bindgen.",
    "",
    `realm ${realm}`,
    "",
  ];
  for (const library of links) lines.push(`link "${library}"`, "");
  if (base !== undefined) lines.push(`invoke "${base.module}"`, "");
  const skipped: string[] = [...header.skipped];

  for (const item of header.enums) {
    if (base?.names.has(item.name) === true) continue;
    if (is_keyword(item.name)) {
      skipped.push(`${item.name}: el nombre del enum es palabra reservada de PenguScript`);
      continue;
    }
    lines.push(...render_enum(item), "");
  }

  const { ordered, cycles } = order_records(header.records, registry);
  for (const cycle of cycles) skipped.push(`${cycle}: ciclo de records por valor`);
  const in_cycle = new Set(cycles.flatMap((cycle) => cycle.split(" → ").slice(0, -1)));

  for (const record of ordered) {
    if (base?.names.has(record.name) === true) continue;
    if (in_cycle.has(record.name)) {
      skipped.push(`${record.name}: record en un ciclo de dependencias`);
      continue;
    }
    if (is_keyword(record.name)) {
      skipped.push(`${record.name}: el nombre del record es palabra reservada de PenguScript`);
      continue;
    }
    const rendered = render_record(record, registry);
    if (rendered.error !== undefined) {
      skipped.push(`${record.name}: ${rendered.error}`);
      continue;
    }
    lines.push(...rendered.lines, "");
  }

  for (const item of header.typedefs) {
    if (base?.names.has(item.name) === true) continue;
    if (item.function_pointer) {
      skipped.push(`${item.name}: callback (se usa como raw<void>)`);
      continue;
    }
    const target = alias_target(item.type, registry);
    if (target === undefined || target === item.name) continue;
    if (is_keyword(item.name)) {
      skipped.push(`${item.name}: el alias es palabra reservada de PenguScript`);
      continue;
    }
    lines.push(`echo ${item.name} = ${target}`, "");
  }

  // Constantes de la cabecera (#define): después de los tipos, porque un
  // `const Color` necesita el rune, y antes del `extern`.
  let constants = 0;
  for (const item of macros.skipped) skipped.push(item);
  for (const item of macros.constants) {
    if (base?.constants.has(item.name) === true) continue;
    if (is_keyword(item.name)) {
      skipped.push(`${item.name}: el nombre es palabra reservada de PenguScript`);
      continue;
    }
    lines.push(render_constant(item), "");
    constants += 1;
  }

  lines.push('extern "C"');
  let emitted = 0;
  for (const fn of header.functions) {
    if (base?.functions.has(fn.name) === true) continue;
    // El nombre de la función es el símbolo del enlazador: no se puede
    // renombrar. Si choca con una keyword, se omite y se reporta.
    if (is_keyword(fn.name)) {
      skipped.push(`${fn.name}: el nombre es palabra reservada de PenguScript`);
      continue;
    }
    const params: string[] = [];
    let supported = true;
    for (const param of fn.params) {
      const mapped = resolve_native_type(param.type, registry);
      if (!mapped.ok) supported = false;
      params.push(`${sanitize_identifier(param.name)}: ${mapped.pengu}`);
    }
    const result = resolve_native_type(fn.result, registry);
    if (!result.ok) supported = false;
    if (!supported) {
      skipped.push(`${fn.name}: tipo no traducible`);
      continue;
    }
    if (fn.variadic) params.push("...resto: any");
    lines.push(`  ${fn.name} = (${params.join(", ")}) -> ${result.pengu}`);
    emitted += 1;
  }

  lines.push("");
  return { text: lines.join("\n"), functions: emitted, constants, skipped };
}

