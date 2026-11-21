// Estado compartido por el checker.
//
// El checker recorre el AST con un contexto que lleva el ámbito
// actual, el módulo, el tipo de retorno esperado y si estamos dentro
// de `unsafe`.

import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { CODES } from "../diagnostics/codes.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import type { Span } from "../util/span.ts";
import type { ModuleInfo } from "./module_info.ts";
import type { Scope } from "./scopes.ts";
import { make_scope } from "./scopes.ts";
import type { PenguType } from "./types.ts";
import type { ExprNode } from "../frontend/ast.ts";
import { type_display, type_equals, is_any, is_numeric, is_float } from "./types.ts";
import type { ExternalImports } from "./external.ts";

export interface CheckContext {
  readonly file: string;
  readonly sink: DiagnosticSink;
  readonly module: ModuleInfo;
  scope: Scope;
  current_return: PenguType | undefined;
  unsafe_depth: number;
  loop_depth: number;
  // Tipos de los `break value` del bucle actual (pila por anidamiento).
  break_types: PenguType[][];
  self_type: PenguType | undefined;
  self_mutable: boolean;
  self_assign: boolean;
  // Mapa opcional expresión → tipo, que usa el generador de código.
  types: Map<ExprNode, PenguType> | undefined;
  // Módulos importados con `invoke`, resueltos por el cargador.
  external: ExternalImports | undefined;
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
    loop_depth: 0,
    break_types: [],
    self_type: undefined,
    self_mutable: false,
    self_assign: false,
    types: undefined,
    external: undefined,
  };
}

export function with_scope<T>(ctx: CheckContext, fn: (inner: CheckContext) => T): T {
  const previous = ctx.scope;
  ctx.scope = make_scope(previous);
  try {
    return fn(ctx);
  } finally {
    ctx.scope = previous;
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
// lenguaje. `none` y `nullptr` encajan en opcionales y punteros.
export function can_assign(target: PenguType, source: PenguType): boolean {
  if (is_any(target) || is_any(source)) return true;
  if (type_equals(target, source)) return true;

  if (target.kind === "optional") {
    if (source.kind === "none") return true;
    if (source.kind === "optional") return can_assign(target.inner, source.inner);
    return can_assign(target.inner, source);
  }
  if (source.kind === "none") return false;
  if (source.kind === "nullptr") {
    return (
      target.kind === "raw" ||
      target.kind === "unique" ||
      target.kind === "shared" ||
      target.kind === "weak"
    );
  }

  // Promoción numérica: entero → coma flotante.
  if (is_numeric(target) && is_numeric(source)) {
    if (!is_float(target)) return true;
    return true;
  }

  // Un `ref<T>` acepta la dirección de un T.
  if (target.kind === "ref" && source.kind === "ref") {
    return type_equals(target.inner, source.inner) && (target.mutable === source.mutable || !target.mutable);
  }

  return false;
}
