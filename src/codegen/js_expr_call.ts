// Llamadas del emisor JavaScript.
//
// Un `declare` de la stdlib se traduce a su destino en el runtime
// (`builtins_emit_js.ts`); una función de PenguScript se emite en su realm y
// se referencia con import si vive en otro archivo. Los argumentos variádicos
// que llegan a un parámetro `any` se boxean para que la presentación conserve
// el tipo estático (C++ lo resuelve con `Value`).

import type { ArgNode, ExprNode } from "../frontend/ast_expr.ts";
import type { PenguType } from "../semantic/types.ts";
import type { Span } from "../util/span.ts";
import { is_any, is_float, is_numeric } from "../semantic/types.ts";
import {
  cross_reference,
  current_unit,
  is_local_declared,
  resolve_realm,
  js_error,
  runtime_name,
  type_of,
  type JsContext,
} from "./js_context.ts";
import { js_identifier } from "./js_names.ts";
import { emit_expr } from "./js_expr.ts";
import { builtin_js_target } from "./builtins_emit_js.ts";
import { ensure_function, ensure_constant } from "./js_module.ts";

type CallNode = Extract<ExprNode, { kind: "call" }>;

export function emit_call(g: JsContext, node: CallNode, expected?: PenguType): string {
  const callee = node.callee;
  if (callee.kind === "ident") return emit_named_call(g, callee.name, undefined, node, expected);
  if (callee.kind === "path") {
    const segments = callee.segments;
    const realm = segments[0];
    const name = segments[1];
    if (segments.length === 2 && realm !== undefined && name !== undefined) {
      return emit_named_call(g, name, realm, node, expected);
    }
    js_error(g, "llamada a una ruta no soportada todavía en JavaScript", node.span);
    return "undefined";
  }
  if (callee.kind === "member") {
    js_error(
      g,
      "las llamadas a métodos todavía no se emiten a JavaScript (fase P2/P3)",
      node.span,
    );
    return "undefined";
  }
  return `${emit_expr(g, callee)}(${emit_args(g, undefined, false, node.args)})`;
}

// Llamada a `nombre(…)` o `realm::nombre(…)`.
function emit_named_call(
  g: JsContext,
  name: string,
  realm: string | undefined,
  node: CallNode,
  expected: PenguType | undefined,
): string {
  void expected;
  const current = current_unit(g);
  const imported = realm === undefined ? current.selective_symbols.get(name) : undefined;
  const owner = resolve_realm(g, realm ?? "") ?? imported?.realm ?? (realm === undefined ? current.module.realm : realm);
  const target_name = imported !== undefined && imported.realm === owner ? imported.name : name;
  const unit = g.units.get(owner);
  const info = unit?.module.functions.get(target_name);

  if (info !== undefined && (info.is_intrinsic || info.is_extern)) {
    const target = builtin_js_target(g, owner, target_name);
    if (target === undefined) {
      js_error(
        g,
        `el intrínseco «${owner}::${target_name}» todavía no tiene implementación en JavaScript (fase posterior del plan)`,
        node.span,
      );
      return "undefined";
    }
    return `${target}(${emit_args(g, info.params.map((param) => param.type), info.variadic, node.args)})`;
  }

  if (info !== undefined) {
    ensure_function(g, owner, target_name);
    const reference = realm === undefined && is_local_declared(g, name) ? js_identifier(name) : cross_reference(g, owner, target_name);
    const params = info.params.map((param) => param.type);
    return `${reference}(${emit_args(g, params, info.variadic, node.args)})`;
  }

  // Constante que guarda una función (`callback`/primera clase).
  if (unit?.module.consts.has(target_name) === true) {
    ensure_constant(g, owner, target_name);
    const reference = realm === undefined && is_local_declared(g, name) ? js_identifier(name) : cross_reference(g, owner, target_name);
    return `${reference}(${emit_args(g, undefined, false, node.args)})`;
  }

  const language = builtin_js_target(g, owner, target_name);
  if (language !== undefined) return `${language}(${emit_args(g, undefined, false, node.args)})`;

  js_error(g, `no se encontró la función «${name}» al emitir JavaScript`, node.span);
  return "undefined";
}

// Argumentos de una llamada, bboxeando los que van a un parámetro `any`.
function emit_args(
  g: JsContext,
  params: readonly PenguType[] | undefined,
  variadic: boolean,
  args: readonly ArgNode[],
): string {
  const last = params?.[params.length - 1];
  return args
    .map((arg, index) => {
      const declared = variadic && index >= (params?.length ?? 0) - 1 ? last : params?.[index];
      const expected = declared ?? type_of(g, arg.expr);
      const code = emit_expr(g, arg.expr, expected);
      const spread = arg.spread ? "..." : "";
      if (expected !== undefined && is_any(expected) && is_numeric(type_of(g, arg.expr))) {
        runtime_name(g);
        return `${spread}rt.box(${code}, "${box_kind(type_of(g, arg.expr))}")`;
      }
      return `${spread}${code}`;
    })
    .join(", ");
}

// Pista de presentación para los valores que cruzan un `any`: solo los
// flotantes se distinguen de los enteros (`%g` frente a dígitos).
function box_kind(type: PenguType): string {
  return is_float(type) ? "float" : "int";
}

// Acceso a una ruta `realm::simbolo` como expresión (sin llamada).
export function emit_path_reference(g: JsContext, segments: readonly string[], span: Span): string {
  const realm = segments[0];
  const name = segments[1];
  if (segments.length === 2 && realm !== undefined && name !== undefined) {
    const unit = g.units.get(realm);
    const constant = unit?.module.consts.get(name);
    if (constant !== undefined) ensure_constant(g, realm, name);
    const fn = unit?.module.functions.get(name);
    if (fn !== undefined && (fn.is_intrinsic || fn.is_extern)) {
      const target = builtin_js_target(g, realm, name);
      if (target === undefined) {
        js_error(g, `el intrínseco «${realm}::${name}» todavía no tiene implementación en JavaScript`, span);
        return "undefined";
      }
      return target;
    }
    return cross_reference(g, realm, name);
  }
  js_error(g, "ruta no soportada todavía en JavaScript", span);
  return "undefined";
}
