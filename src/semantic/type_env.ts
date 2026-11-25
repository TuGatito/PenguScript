// Tabla de tipos declarados por el módulo (runes, omens, alias).
//
// El checker la construye una vez y luego resuelve cada TypeNode
// contra ella.

import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { CODES } from "../diagnostics/codes.ts";
import { check_key_requirements } from "./key_types.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import type { Span } from "../util/span.ts";
import type { TypeNode } from "../frontend/ast_type.ts";
import { is_primitive_type, STRING_TYPES } from "../frontend/ast_type.ts";
import type { PenguType } from "./types.ts";
import {
  UNKNOWN,
  VOID,
  any_type,
  type_equals,
  named,
  optional,
  primitive,
  range_type,
  ref_to,
  tuple_type,
  function_type,
  substitute_generics,
} from "./types.ts";

export interface FieldInfo {
  readonly name: string;
  readonly type: PenguType;
  readonly has_default: boolean;
  // Ancho en bits de un bitfield (`bits 3 modo: uint32_t`).
  readonly bits: number | undefined;
  readonly span: Span;
}

export interface MethodInfo {
  readonly name: string;
  readonly params: readonly PenguType[];
  /** `mut` de cada parámetro: contrato en la llamada. */
  readonly param_mutables: readonly boolean[];
  readonly variadic: boolean;
  /** Parámetros sin valor por defecto: mínimo exigido en la llamada. */
  readonly required: number;
  readonly result: PenguType;
  readonly mutable: boolean;
  readonly operator: string | undefined;
  readonly sigils: readonly string[];
  readonly span: Span;
}

export interface ConstructorInfo {
  readonly params: readonly PenguType[];
  readonly span: Span;
}

export interface RuneInfo {
  readonly kind: "rune";
  readonly name: string;
  // `meld`: unión C; sus campos se escriben libremente y se leen con `unsafe`.
  readonly meld?: boolean;
  readonly sigils: readonly string[];
  readonly fields: Map<string, FieldInfo>;
  readonly methods: Map<string, MethodInfo>;
  readonly constructor: ConstructorInfo | undefined;
  readonly parent: string | undefined;
  readonly span: Span;
}

// `opaque Nombre`: tipo incompleto declarado por el usuario.
export interface OpaqueInfo {
  readonly kind: "opaque";
  readonly name: string;
  readonly span: Span;
}

// `callback Nombre = (params) -> ret`: puntero a función con ABI C.
export interface CallbackInfo {
  readonly kind: "callback";
  readonly name: string;
  readonly params: readonly PenguType[];
  readonly result: PenguType;
  readonly span: Span;
}

export interface OmenVariantInfo {
  readonly name: string;
  readonly payload: readonly PenguType[];
  readonly value: number | undefined;
  readonly span: Span;
}

export interface OmenInfo {
  readonly kind: "omen";
  readonly name: string;
  readonly sigils: readonly string[];
  readonly is_flags: boolean;
  readonly underlying: PenguType | undefined;
  readonly variants: Map<string, OmenVariantInfo>;
  readonly span: Span;
}

export interface AliasInfo {
  readonly kind: "alias";
  readonly name: string;
  readonly seal: boolean;
  readonly target: PenguType;
  readonly sigils: readonly string[];
  readonly span: Span;
  readonly methods: Map<string, MethodInfo>;
}

export interface PendingType {
  readonly name: string;
  readonly span: Span;
}

/** Método enhechizado a un tipo incorporado. */
export interface EnchantedMethod {
  readonly info: MethodInfo;
  /** Realm que lo declara: el codegen cualifica la llamada con él. */
  readonly realm: string;
}

/** Destino codegen de una llamada enhechizada: `realm::nombre`. */
export interface MethodTarget {
  readonly realm: string;
  readonly name: string;
  /** Tipos de los parámetros declarados: el codegen los usa para convertir
   *  literales y elegir la sobrecarga correcta en C++. */
  readonly params: readonly PenguType[];
  readonly variadic: boolean;
}

/** Métodos declarados sobre un tipo incorporado, por aridad. */
export interface EnchantedType {
  readonly base: string;
  readonly arity: number;
  readonly sigils: readonly string[];
  readonly methods: Map<string, EnchantedMethod[]>;
}

export interface TypeEnv {
  readonly runes: Map<string, RuneInfo>;
  readonly omens: Map<string, OmenInfo>;
  readonly aliases: Map<string, AliasInfo>;
  readonly opaques: Map<string, OpaqueInfo>;
  readonly callbacks: Map<string, CallbackInfo>;
  /** Clave `base/aridad`: `string/0`, `vector/1`, `tuple/2`. */
  readonly enchants: Map<string, EnchantedType>;
  readonly sigils: Map<string, PenguType>;
  // Tipos que aún no existen: pueden llegar de otro archivo del mismo
  // realm (realm reabierto) y se validan al terminar de cargar el grafo.
  readonly pending_types: PendingType[];
  // Nombres cualificados de tipos importados (`result::Result`): el
  // alias del módulo no forma parte del tipo, solo ayuda a encontrarlo.
  readonly qualified: Map<string, string>;
}

export function make_type_env(): TypeEnv {
  return {
    runes: new Map(),
    omens: new Map(),
    aliases: new Map(),
    opaques: new Map(),
    callbacks: new Map(),
    sigils: new Map(),
    enchants: new Map(),
    pending_types: [],
    qualified: new Map(),
  };
}

const POINTER_NAMES: ReadonlyMap<string, (inner: PenguType) => PenguType> = new Map([
  ["raw", (inner: PenguType): PenguType => ({ kind: "raw", inner })],
  ["unique", (inner: PenguType): PenguType => ({ kind: "unique", inner })],
  ["shared", (inner: PenguType): PenguType => ({ kind: "shared", inner })],
  ["weak", (inner: PenguType): PenguType => ({ kind: "weak", inner })],
]);

export function resolve_type_node(
  node: TypeNode,
  env: TypeEnv,
  sink: DiagnosticSink,
): PenguType {
  switch (node.kind) {
    case "primitive_type":
      return node.name === "void" ? VOID : primitive(node.name);

    case "optional_type":
      return optional(resolve_type_node(node.inner, env, sink));

    case "ref_type":
      return ref_to(resolve_type_node(node.inner, env, sink), node.mutable);

    case "function_type":
      return function_type(
        node.params.map((param) => resolve_type_node(param, env, sink)),
        resolve_type_node(node.result, env, sink),
        node.variadic,
        node.params.length - (node.variadic ? 1 : 0),
      );

    case "tuple_type":
      return tuple_type(node.items.map((item) => resolve_type_node(item, env, sink)));

    case "array_type": {
      const element = resolve_type_node(node.element, env, sink);
      const size = node.size.kind === "int_lit" ? Number.parseInt(node.size.value, 10) : 0;
      return { kind: "array", element, size: Number.isNaN(size) ? 0 : size };
    }

    case "named_type": {
      const args = node.args.map((arg) => resolve_type_node(arg, env, sink));
      return resolve_named_type(node.name, args, node.span, env, sink);
    }
  }
}

export function resolve_named_type(
  name: string,
  args: readonly PenguType[],
  span: Span,
  env: TypeEnv,
  sink: DiagnosticSink,
): PenguType {
  if (name === "void") return VOID;
  if (name === "any") return any_type("any");
  if (is_primitive_type(name)) return primitive(name);
  if (STRING_TYPES.has(name)) return primitive(name);

  const sigil = env.sigils.get(name);
  if (sigil && args.length === 0) return sigil;

  const pointer = POINTER_NAMES.get(name);
  if (pointer) {
    if (args.length !== 1) {
      sink.add(
        make_error(
          CODES.wrong_arity,
          `«${name}» necesita exactamente un argumento de tipo`,
          span,
        ),
      );
      return UNKNOWN;
    }
    return pointer(args[0] as PenguType);
  }

  const alias = env.aliases.get(name);
  if (alias) {
    if (!alias.seal) {
      if (alias.sigils.length > 0) {
        const mapping = new Map<string, PenguType>();
        alias.sigils.forEach((sigil, index) => mapping.set(sigil, args[index] ?? UNKNOWN));
        return substitute_generics(alias.target, mapping);
      }
      return alias.target;
    }
    return named(name, args);
  }

  if (env.runes.has(name) || env.omens.has(name) || env.opaques.has(name) || env.callbacks.has(name)) {
    return named(name, args);
  }

  if (name === "range") {
    if (args.length !== 1) {
      sink.add(make_error(CODES.wrong_arity, "«range» necesita exactamente un argumento de tipo", span));
      return UNKNOWN;
    }
    return range_type(args[0] as PenguType);
  }

  if (BUILTIN_CONTAINERS.has(name)) {
    check_key_requirements(env, name, args, span, sink);
    return named(name, args);
  }

  // `Ordering` es el resultado de `<=>` y lo aporta el runtime.
  if (name === "Ordering" && args.length === 0) return named("Ordering");

  // Un tipo cualificado (`result::Result`) es el mismo tipo que su
  // nombre base: el alias solo sirve para encontrarlo en otro módulo.
  if (name.includes("::")) {
    const bare = name.slice(name.lastIndexOf("::") + 2);
    env.pending_types.push({ name, span });
    return named(bare, args);
  }

  // Puede venir de otro archivo del mismo realm: se resuelve al final.
  env.pending_types.push({ name, span });
  return named(name, args);
}

// Comprueba que los tipos aplazados existen ya (tras fusionar realms).
export function report_pending_types(env: TypeEnv, sink: DiagnosticSink): void {
  for (const pending of env.pending_types) {
    const bare = pending.name.includes("::") ? pending.name.slice(pending.name.lastIndexOf("::") + 2) : pending.name;
    if (env.qualified.has(pending.name)) continue;
    if (
      env.runes.has(bare) ||
      env.omens.has(bare) ||
      env.aliases.has(bare) ||
      env.opaques.has(bare) ||
      env.callbacks.has(bare)
    ) {
      continue;
    }
    sink.add(
      make_error(
        CODES.unknown_type,
        `no existe el tipo «${pending.name}»${qualified_hint(env, bare)}`,
        pending.span,
      ),
    );
  }
  env.pending_types.length = 0;
}

// Si el tipo existe en un módulo importado, sugiere el nombre cualificado.
function qualified_hint(env: TypeEnv, bare: string): string {
  const matches: string[] = [];
  for (const full of env.qualified.keys()) {
    if (full.endsWith(`::${bare}`)) matches.push(full);
  }
  if (matches.length === 0) return "";
  const list = matches.map((name) => `«${name}»`).join(" o ");
  return ` (¿querías ${list}?)`;
}

// Registra los tipos públicos de los módulos importados para que se
// puedan nombrar cualificados: `result::Result`, `time::Duration`.
export function register_qualified_types(
  env: TypeEnv,
  modules: ReadonlyMap<string, { readonly env: Pick<TypeEnv, "runes" | "omens" | "aliases"> }>,
): void {
  for (const [alias, module] of modules) {
    for (const name of module.env.runes.keys()) env.qualified.set(`${alias}::${name}`, name);
    for (const name of module.env.omens.keys()) env.qualified.set(`${alias}::${name}`, name);
    for (const name of module.env.aliases.keys()) env.qualified.set(`${alias}::${name}`, name);
  }
}

export const BUILTIN_CONTAINERS: ReadonlySet<string> = new Set([
  "vector",
  "array",
  "deque",
  "list",
  "forward_list",
  "set",
  "multiset",
  "unordered_set",
  "map",
  "multimap",
  "unordered_map",
  "unordered_multimap",
  "stack",
  "queue",
  "priority_queue",
  "span",
  "pair",
  "tuple",
  "bitset",
  "optional",
  "variant",
  "init_list",
  "complex",
  "any",
  "function",
  "atomic",
  "mutex",
  "shared_mutex",
  "condition_variable",
  "thread",
  "string",
  "wstring",
  "u8string",
  "u16string",
  "u32string",
  "string_view",
]);

// Búsqueda de campos y métodos a través de la cadena `heir`. Las runes
// heredan todo del padre y pueden sombrear métodos, pero no campos.
export function find_rune_field(
  env: TypeEnv,
  rune: RuneInfo,
  name: string,
): FieldInfo | undefined {
  let current: RuneInfo | undefined = rune;
  while (current !== undefined) {
    const field = current.fields.get(name);
    if (field !== undefined) return field;
    current = current.parent === undefined ? undefined : env.runes.get(current.parent);
  }
  return undefined;
}

export function find_rune_method(
  env: TypeEnv,
  rune: RuneInfo,
  name: string,
): MethodInfo | undefined {
  let current: RuneInfo | undefined = rune;
  while (current !== undefined) {
    const method = current.methods.get(name) ?? current.methods.get(`operator ${name}`);
    if (method !== undefined) return method;
    current = current.parent === undefined ? undefined : env.runes.get(current.parent);
  }
  return undefined;
}

// ¿`name` es una rune o desciende de `ancestor`?
export function is_heir_of(env: TypeEnv, name: string, ancestor: string): boolean {
  let current: RuneInfo | undefined = env.runes.get(name);
  while (current !== undefined) {
    if (current.name === ancestor) return true;
    current = current.parent === undefined ? undefined : env.runes.get(current.parent);
  }
  return false;
}

// Un `echo` es transparente: en C++ es un alias, así que el tipo del
// valor es el subyacente. Sus métodos viven en `AliasInfo.methods` y se
// encuentran por el tipo subyacente (si dos alias declaran el mismo
// método, gana el primero en el fuente).
export function find_echo_method(
  env: TypeEnv,
  type: PenguType,
  name: string,
): MethodInfo | undefined {
  for (const alias of env.aliases.values()) {
    if (alias.seal) continue;
    if (!type_equals(alias.target, type)) continue;
    const method = alias.methods.get(name);
    if (method !== undefined) return method;
  }
  return undefined;
}

export function generic_sigil_type(name: string): PenguType {
  return any_type(name);
}
