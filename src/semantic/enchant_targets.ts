// Tipos incorporados que admiten `enchanting`.
//
// El destino de un bloque `enchanting` puede ser un rune, un omen, un
// alias… o uno de estos tipos. La aridad indica cuántos sigilos declara
// el bloque (`vector<T>` → 1, `map<K, V>` → 2, `tuple<A, B>` → 2) y
// `reference` si el receptor se pasa por referencia en C++ (los tipos
// por valor no admiten métodos `mut`).

import type { TypeNode } from "../frontend/ast_type.ts";
import { PRIMITIVE_TYPES, STRING_TYPES, is_primitive_type } from "../frontend/ast_type.ts";
import type { PenguType } from "./types.ts";
import { UNKNOWN, named, optional, primitive, ref_to, tuple_type } from "./types.ts";

export interface EnchantTarget {
  /** Aridades (número de sigilos) que acepta el bloque. */
  readonly arities: readonly number[];
  /** El receptor se emite como `const T&` / `T&`. */
  readonly reference: boolean;
}

const CONTAINERS: ReadonlyMap<string, EnchantTarget> = new Map([
  // Secuencias y adaptadores de un argumento de tipo.
  ...["vector", "deque", "list", "forward_list", "span", "set", "multiset", "unordered_set", "unordered_multiset", "stack", "queue", "priority_queue", "optional", "atomic"].map(
    (name): [string, EnchantTarget] => [name, { arities: [1], reference: true }],
  ),
  // `array<T, N>`: el patrón declara solo el elemento; `N` es implícito.
  ["array", { arities: [1], reference: true }],
  // `bitset<N>`: `N` es una constante, no un tipo; el bloque no declara sigilos.
  ["bitset", { arities: [0], reference: true }],
  // Punteros inteligentes: el cuerpo del método ve el valor apuntado.
  ...["unique", "shared", "weak"].map(
    (name): [string, EnchantTarget] => [name, { arities: [1], reference: true }],
  ),
  // Mapas y pares de dos argumentos de tipo.
  ...["map", "multimap", "unordered_map", "unordered_multimap", "pair"].map(
    (name): [string, EnchantTarget] => [name, { arities: [2], reference: true }],
  ),
  // `tuple` tiene aridad variable: se registra una entrada por aridad.
  ["tuple", { arities: [1, 2, 3, 4, 5, 6, 7, 8], reference: true }],
]);

export function enchant_target_of(base: string): EnchantTarget | undefined {
  const known = CONTAINERS.get(base);
  if (known !== undefined) return known;
  if (base === "void" || base === "nullptr_t") return undefined;
  if (is_primitive_type(base)) return { arities: [0], reference: false };
  if (STRING_TYPES.has(base)) return { arities: [0], reference: true };
  if (base === "Ordering") return { arities: [0], reference: false };
  return undefined;
}

export function enchant_key(base: string, arity: number): string {
  return `${base}/${arity}`;
}

export function is_value_target(base: string): boolean {
  return enchant_target_of(base)?.reference === false;
}

/** Nombres válidos, para las sugerencias de E0709. */
export function enchant_target_names(): readonly string[] {
  const primitives = [...PRIMITIVE_TYPES].filter((name) => name !== "void" && name !== "nullptr_t");
  return [...CONTAINERS.keys(), ...primitives, ...STRING_TYPES, "Ordering"];
}

/** Nombre base de un patrón de `enchanting` (`vector<T>` → `vector`). */
export function type_pattern_base(node: TypeNode): string {
  if (node.kind === "primitive_type") return node.name;
  if (node.kind === "named_type") return node.name;
  // El parser convierte estas formas en tipos anónimos.
  if (node.kind === "tuple_type") return "tuple";
  if (node.kind === "array_type") return "array";
  if (node.kind === "optional_type") return "optional";
  if (node.kind === "ref_type") return "ref";
  return "__error__";
}

// Un argumento de tipo es sigilo si es un nombre corto en mayúsculas
// (`T`, `K`, `V`, `E`); los tipos concretos son minúsculas o PascalCase.
function is_sigil_name(name: string): boolean {
  return /^[A-Z][A-Z0-9]?$/.test(name);
}

/** Sigilos declarados por el patrón, en orden (`map<K, V>` → `[K, V]`). */
export function type_pattern_sigils(node: TypeNode): readonly string[] {
  const sigils: string[] = [];
  const visit = (child: TypeNode): void => {
    switch (child.kind) {
      case "named_type":
        if (child.args.length === 0) {
          if (is_sigil_name(child.name)) sigils.push(child.name);
          return;
        }
        for (const arg of child.args) visit(arg);
        return;
      case "tuple_type":
        for (const item of child.items) visit(item);
        return;
      case "array_type":
        visit(child.element);
        return;
      case "optional_type":
      case "ref_type":
        visit(child.inner);
        return;
      case "primitive_type":
      case "function_type":
        return;
    }
  };
  visit(node);
  return sigils;
}

/** Número de argumentos de tipo del patrón (`map<K, V>` → 2). */
export function type_pattern_arity(node: TypeNode): number {
  if (node.kind === "named_type") return node.args.length;
  if (node.kind === "tuple_type") return node.items.length;
  if (node.kind === "array_type" || node.kind === "optional_type" || node.kind === "ref_type") return 1;
  return 0;
}

/** Tipo del receptor de un patrón, con los sigilos sin resolver. */
export function type_pattern_type(node: TypeNode): PenguType {
  switch (node.kind) {
    case "primitive_type":
      return node.name === "void" ? UNKNOWN : primitive(node.name);
    case "named_type":
      // `string` y familia se resuelven como primitivos en el checker.
      if (STRING_TYPES.has(node.name) && node.args.length === 0) return primitive(node.name);
      return named(node.name, node.args.map(type_pattern_type));
    case "optional_type":
      return optional(type_pattern_type(node.inner));
    case "ref_type":
      return ref_to(type_pattern_type(node.inner), node.mutable);
    case "array_type":
      return named("array", [type_pattern_type(node.element)]);
    case "tuple_type":
      return tuple_type(node.items.map(type_pattern_type));
    default:
      return UNKNOWN;
  }
}
