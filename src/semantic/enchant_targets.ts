// Tipos incorporados que admiten `enchanting`.
//
// El destino de un bloque `enchanting` puede ser un rune, un omen, un
// alias… o uno de estos tipos. La aridad indica cuántos sigilos declara
// el bloque (`vector<T>` → 1, `map<K, V>` → 2, `tuple<A, B>` → 2) y
// `reference` si el receptor se pasa por referencia en C++ (los tipos
// por valor no admiten métodos `mut`).

import { PRIMITIVE_TYPES, STRING_TYPES, is_primitive_type } from "../frontend/ast_type.ts";

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
