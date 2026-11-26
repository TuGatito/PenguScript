// Estado compartido por el checker.
//
// El checker recorre el AST con un contexto que lleva el ámbito
// actual, el módulo, el tipo de retorno esperado y si estamos dentro
// de `unsafe`.

import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { CODES } from "../diagnostics/codes.ts";
import { check_first_class_value } from "./checker_first_class.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import type { Span } from "../util/span.ts";
import type { ModuleInfo } from "./module_info.ts";
import type { MethodTarget, TypeEnv } from "./type_env.ts";
import { is_heir_of } from "./type_env.ts";
import type { Scope } from "./scopes.ts";
import { make_scope } from "./scopes.ts";
import type { PenguType } from "./types.ts";
import type { ExprNode } from "../frontend/ast.ts";
import {
  type_display,
  type_equals,
  is_any,
  integer_shape,
  float_rank,
  UNKNOWN,
} from "./types.ts";
import { literal_fits_type } from "./literal_fit.ts";
import { host_is_ancestor, is_host_name } from "./host_types.ts";
import type { IntegerShape } from "./types.ts";
import type { ExternalImports } from "./external.ts";
import type { LocalSymbol } from "./symbols.ts";

// Préstamo activo de una variable (`r = ref(x)`): mientras viva, `x`
// no se puede mutar ni pasar como `mut` (Ley de Exclusividad).
export interface Borrow {
  readonly name: string;
  readonly depth: number;
  readonly span: Span;
}

export interface CheckContext {
  readonly file: string;
  readonly sink: DiagnosticSink;
  readonly module: ModuleInfo;
  scope: Scope;
  current_return: PenguType | undefined;
  unsafe_depth: number;
  // 0 fuera de una función `async`: `await` solo es legal si es > 0.
  async_depth: number;
  loop_depth: number;
  // Tipos de los `break value` del bucle actual (pila por anidamiento).
  break_types: PenguType[][];
  self_type: PenguType | undefined;
  self_mutable: boolean;
  self_assign: boolean;
  // Mapa opcional expresión → tipo, que usa el generador de código.
  types: Map<ExprNode, PenguType> | undefined;
  // Métodos enhechizados ya resueltos: nodo del miembro → función libre.
  member_targets: Map<ExprNode, MethodTarget> | undefined;
  // Módulos importados con `invoke`, resueltos por el cargador.
  external: ExternalImports | undefined;
  // Préstamos activos y profundidad de ámbitos.
  borrows: Borrow[];
  scope_depth: number;
  // Contenedores que se están recorriendo con `for`: mutarlos
  // estructuralmente invalida el iterador.
  iterating: { readonly name: string; readonly span: Span }[];
  // Declaraciones locales (parámetros, variables de bucle, patrones):
  // alimentan el índice de símbolos del LSP.
  locals: LocalSymbol[];
  // Bloque que se está chequeando: ámbito de las variables declaradas.
  block_span: Span | undefined;
}

// Registra una declaración local para el índice de símbolos.
export function record_local(
  ctx: CheckContext,
  name: string,
  type: PenguType,
  mutable: boolean,
  kind: "parameter" | "variable",
  span: Span,
  scope: Span,
): void {
  ctx.locals.push({ name, type, mutable, kind, span, scope });
}

// Ejecuta `fn` con `block_span` apuntando al bloque indicado.
export function with_block_span<T>(ctx: CheckContext, span: Span | undefined, fn: () => T): T {
  const previous = ctx.block_span;
  ctx.block_span = span ?? previous;
  try {
    return fn();
  } finally {
    ctx.block_span = previous;
  }
}

export function make_context(
  file: string,
  module: ModuleInfo,
  sink: DiagnosticSink,
): CheckContext {
  return {
    file,
    sink,
    module,
    scope: make_scope(),
    current_return: undefined,
    unsafe_depth: 0,
    async_depth: 0,
    loop_depth: 0,
    break_types: [],
    self_type: undefined,
    self_mutable: false,
    self_assign: false,
    types: undefined,
    member_targets: undefined,
    external: undefined,
    borrows: [],
    scope_depth: 0,
    iterating: [],
    locals: [],
    block_span: undefined,
  };
}

// Registra un préstamo de `name` en el ámbito actual.
export function add_borrow(ctx: CheckContext, name: string, span: Span): void {
  ctx.borrows.push({ name, depth: ctx.scope_depth, span });
}

// Devuelve el préstamo activo de `name`, si lo hay.
export function borrow_of(ctx: CheckContext, name: string): Borrow | undefined {
  for (let index = ctx.borrows.length - 1; index >= 0; index -= 1) {
    const borrow = ctx.borrows[index];
    if (borrow !== undefined && borrow.name === name) return borrow;
  }
  return undefined;
}

// Error si `name` se está recorriendo con `for`.
export function ensure_not_iterating(
  ctx: CheckContext,
  name: string,
  span: Span,
  action: string,
): boolean {
  const active = ctx.iterating.find((item) => item.name === name);
  if (active === undefined) return true;
  ctx.sink.add(
    make_error(
      CODES.exclusive_borrow,
      `no se puede ${action} «${name}» mientras se recorre con «for»`,
      span,
      `el bucle empieza en la línea ${active.span.start.line}`,
      "recorre una copia o recoge los cambios y aplícalos después",
    ),
  );
  return false;
}

// Error si `name` está prestado: mutar mientras hay un alias activo
// rompe la exclusividad.
export function ensure_not_borrowed(
  ctx: CheckContext,
  name: string,
  span: Span,
  action: string,
): boolean {
  const borrow = borrow_of(ctx, name);
  if (borrow === undefined) return true;
  ctx.sink.add(
    make_error(
      CODES.exclusive_borrow,
      `no se puede ${action} «${name}» mientras existe un préstamo activo`,
      span,
      `el préstamo se creó en la línea ${borrow.span.start.line}`,
      "cierra el préstamo en un bloque «do» o deja de usar la referencia",
    ),
  );
  return false;
}

export function with_scope<T>(ctx: CheckContext, fn: (inner: CheckContext) => T): T {
  const previous = ctx.scope;
  const previous_depth = ctx.scope_depth;
  ctx.scope = make_scope(previous);
  ctx.scope_depth += 1;
  try {
    return fn(ctx);
  } finally {
    ctx.scope = previous;
    ctx.scope_depth = previous_depth;
    // Los préstamos del ámbito que se cierra dejan de existir.
    while (ctx.borrows.length > 0) {
      const last = ctx.borrows[ctx.borrows.length - 1];
      if (last === undefined || last.depth <= previous_depth) break;
      ctx.borrows.pop();
    }
  }
}

export function child_context(ctx: CheckContext): CheckContext {
  return { ...ctx, scope: make_scope(ctx.scope) };
}

export function report_type_mismatch(
  ctx: CheckContext,
  expected: PenguType,
  actual: PenguType,
  span: Span,
  context: string,
): void {
  if (is_any(expected) || is_any(actual)) return;
  if (is_generic_type(ctx, expected) || is_generic_type(ctx, actual)) return;
  if (type_equals(expected, actual)) return;
  ctx.sink.add(
    make_error(
      CODES.type_mismatch,
      `se esperaba «${type_display(expected)}» ${context}, se encontró «${type_display(actual)}»`,
      span,
    ),
  );
}

export function report_type_mismatch_reversed(
  ctx: CheckContext,
  found: PenguType,
  expected: PenguType,
  span: Span,
  context: string,
): void {
  report_type_mismatch(ctx, expected, found, span, context);
}

export function expect_bool(ctx: CheckContext, type: PenguType, span: Span, context: string): void {
  if (is_any(type)) return;
  if (type.kind === "primitive" && type.name === "bool") return;
  ctx.sink.add(
    make_error(
      CODES.condition_not_bool,
      `${context} debe ser «bool», se encontró «${type_display(type)}»`,
      span,
    ),
  );
}

// Comprobación de asignación con las conversiones seguras del
// lenguaje. `none` encaja en opcionales y `nullptr` solo en `raw<T>`.
//
// Las conversiones numéricas siguen el spec: ensanchado entero,
// unsigned → signed más ancho, entero → coma flotante y float → double.
// Cualquier otra cosa exige `as` (y, si es estrecha, `unsafe`).

function integer_assignable(target: IntegerShape, source: IntegerShape): boolean {
  if (target.signed === source.signed) return source.bits <= target.bits;
  return source.bits < target.bits;
}

function float_assignable(target_rank: number, source_int: boolean, source_rank: number | undefined): boolean {
  if (source_int) return true;
  if (source_rank === undefined) return false;
  return source_rank <= target_rank;
}

function is_host_any(type: PenguType): boolean {
  return type.kind === "named" && type.name === "js::Any";
}

export function can_assign(
  target: PenguType,
  source: PenguType,
  env?: TypeEnv,
): boolean {
  if (is_any(target) || is_any(source)) return true;
  // `js::Any` del catálogo del navegador: entra y sale de cualquier sitio.
  if (is_host_any(target) || is_host_any(source)) return true;
  if (type_equals(target, source)) return true;

  if (
    target.kind === "primitive" &&
    target.name === "string_view" &&
    source.kind === "primitive" &&
    source.name === "string"
  ) {
    return true;
  }

  if (target.kind === "named" && target.name === "variant") {
    return target.args.some((option) => can_assign(option, source, env));
  }

  if (target.kind === "optional") {
    if (source.kind === "none") return true;
    if (source.kind === "optional") return can_assign(target.inner, source.inner, env);
    return can_assign(target.inner, source, env);
  }
  if (source.kind === "none") return false;
  if (source.kind === "nullptr") return target.kind === "raw";

  // Un literal tupla encaja en `pair<A, B>` / `tuple<A, B>`.
  if (target.kind === "named" && source.kind === "tuple") {
    if (target.name !== "pair" && target.name !== "tuple") return false;
    return (
      target.args.length === source.items.length &&
      target.args.every((item, index) => can_assign(item, source.items[index] ?? UNKNOWN, env))
    );
  }

  const target_int = integer_shape(target);
  const source_int = integer_shape(source);
  if (target_int !== undefined && source_int !== undefined) {
    return integer_assignable(target_int, source_int);
  }

  const target_float = float_rank(target);
  if (target_float !== undefined) {
    return float_assignable(target_float, source_int !== undefined, float_rank(source));
  }

  // Un objeto del host encaja en el tipo del host del que hereda
  // (`HTMLElement` en un parámetro `js::Node`). El reparto de tipos lo pone
  // el navegador, no el compilador.
  if (target.kind === "named" && source.kind === "named" && is_host_name(target.name) && is_host_name(source.name)) {
    if (host_is_ancestor(env, target.name, source.name)) return true;
  }

  // `ref<Dog>` no es `ref<Animal>`: el upcast debe ser explícito con
  // `ref<Animal>(ref(d))`, que es lo único que evita el slicing.
  if (target.kind === "ref" && source.kind === "ref") {
    return type_equals(target.inner, source.inner) && (target.mutable === source.mutable || !target.mutable);
  }

  return false;
}

// Comprueba una inicialización (declaración, constante, retorno o
// valor por defecto) y solo diagnostica si de verdad no es asignable.
// ¿Es un tipo genérico (`T`) declarado por el sigilo de la
// declaración que se está comprobando? Dentro de su cuerpo el checker
// no conoce la operación concreta, así que acepta cualquier valor.
export function is_generic_type(_ctx: CheckContext, type: PenguType): boolean {
  return type.kind === "named" && type.generic === true;
}

// ¿El tipo menciona algún sigilo? Un `vector<T>` dentro de una función
// genérica no se puede comprobar todavía, pero sí se puede anotar para que
// el codegen emita el literal con el tipo correcto.
export function contains_generic(type: PenguType): boolean {
  switch (type.kind) {
    case "named":
      if (type.generic === true) return true;
      return type.args.some(contains_generic);
    case "optional":
    case "ref":
    case "raw":
    case "unique":
    case "shared":
    case "weak":
      return contains_generic(type.inner);
    case "array":
      return contains_generic(type.element);
    case "range":
      return contains_generic(type.element);
    case "tuple":
      return type.items.some(contains_generic);
    case "function":
      return type.params.some(contains_generic) || contains_generic(type.result);
    default:
      return false;
  }
}

const LITERAL_KINDS: ReadonlySet<string> = new Set(["vector_lit", "map_lit", "set_lit", "tuple"]);

// Anota un literal con el tipo esperado cuando ese tipo menciona sigilos:
// no se puede comprobar, pero el codegen necesita saber qué emitir.
export function annotate_literal(ctx: CheckContext, expected: PenguType, value: ExprNode | undefined): void {
  if (value === undefined) return;
  if (!LITERAL_KINDS.has(value.kind)) return;
  // Un literal de contenedor toma el tipo del contexto también cuando es
  // concreto: `map{}` anotado como `map<string, int>` debe emitirse así.
  const contextual = expected.kind === "named" || expected.kind === "array" || expected.kind === "tuple";
  if (!contextual && !contains_generic(expected)) return;
  ctx.types?.set(value, expected);
}

export function check_initialization(
  ctx: CheckContext,
  expected: PenguType,
  actual: PenguType,
  span: Span,
  context: string,
  value?: ExprNode,
): void {
  if (is_any(expected) || is_any(actual)) return;
  if (is_generic_type(ctx, expected) || is_generic_type(ctx, actual)) return;
  if (contains_generic(expected) && value !== undefined && LITERAL_KINDS.has(value.kind)) {
    ctx.types?.set(value, expected);
    return;
  }
  annotate_literal(ctx, expected, value);
  if (expected.kind === "function") check_first_class_value(ctx, value);
  if (compound_fits(ctx, expected, value, actual)) return;
  if (can_assign(expected, actual, ctx.module.env)) return;
  if (literal_fits(ctx, expected, value)) return;
  report_type_mismatch(ctx, expected, actual, span, context);
}

// Un literal compuesto adopta el tipo esperado: `[1, 2, 3]` en un
// `array<int, 3>` y `(1, "a")` en un `pair<int, string>`.
function compound_fits(
  ctx: CheckContext,
  expected: PenguType,
  value: ExprNode | undefined,
  actual: PenguType,
): boolean {
  if (value === undefined) return false;

  if (expected.kind === "array" && value.kind === "vector_lit") {
    if (value.items.length !== expected.size) return false;
    const element = actual.kind === "named" ? actual.args[0] : undefined;
    if (element === undefined || !can_assign(expected.element, element, ctx.module.env)) return false;
    ctx.types?.set(value, expected);
    return true;
  }

  if (
    expected.kind === "named" &&
    (expected.name === "pair" || expected.name === "tuple") &&
    value.kind === "tuple"
  ) {
    if (contains_generic(expected)) {
      ctx.types?.set(value, expected);
      return true;
    }
    if (!can_assign(expected, actual, ctx.module.env)) return false;
    ctx.types?.set(value, expected);
    return true;
  }

  return false;
}

// Un literal entero se ajusta al tipo declarado si su valor cabe.
function literal_fits(ctx: CheckContext, expected: PenguType, value: ExprNode | undefined): boolean {
  return literal_fits_type(ctx, expected, value);
}
