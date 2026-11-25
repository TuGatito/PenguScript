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
import { is_any, is_float, is_numeric, is_string } from "../semantic/types.ts";
import {
  cross_reference,
  current_unit,
  expression_type,
  is_local_declared,
  resolve_realm,
  js_error,
  runtime_name,
  type_of,
  type JsContext,
} from "./js_context.ts";
import { js_identifier } from "./js_names.ts";
import { needs_clone } from "./js_types.ts";
import { emit_expr } from "./js_expr.ts";
import { builtin_js_target } from "./builtins_emit_js.ts";
import { ensure_function, ensure_constant, ensure_type, rune_is_class } from "./js_module.ts";
import { omen_methods_of } from "../semantic/module_info.ts";
import { free_method_export } from "./js_type_decl.ts";
import { realm_of_type } from "./js_context.ts";

type CallNode = Extract<ExprNode, { kind: "call" }>;

export function emit_call(g: JsContext, node: CallNode, expected?: PenguType): string {
  const callee = node.callee;
  if (callee.kind === "ident") return emit_named_call(g, callee.name, undefined, node, expected);
  if (callee.kind === "path") {
    const segments = callee.segments;
    const realm = segments[0];
    const name = segments[1];
    const variant = emit_variant_call(g, segments, node);
    if (variant !== undefined) return variant;
    if (segments.length === 2 && realm !== undefined && name !== undefined) {
      return emit_named_call(g, name, realm, node, expected);
    }
    js_error(g, "llamada a una ruta no soportada todavía en JavaScript", node.span);
    return "undefined";
  }
  if (callee.kind === "member") {
    return emit_member_call(g, callee, node);
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
  if (realm === undefined) {
    const constructed = emit_type_construction(g, target_name, node);
    if (constructed !== undefined) return constructed;
  }
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
      // C++ pasa por valor: el argumento se copia salvo que sea una celda
      // (`ref`) o un tipo con identidad (`unique`/`shared`) (§3).
      if (declared !== undefined && arg.spread !== true && needs_clone(declared) && !is_any(declared)) {
        runtime_name(g);
        return `${spread}rt.clone(${code})`;
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
    // `Color::Red` y `Ordering::Less`: variantes de una `omen` unitaria.
    const unit = current_unit(g);
    const omen = unit.module.env.omens.get(realm);
    if (omen !== undefined) {
      const type_name = cross_reference(g, unit.module.realm, realm);
      return `${type_name}.${js_identifier(name)}`;
    }
    if (realm === "Ordering") {
      runtime_name(g);
      return `rt.Ordering.${js_identifier(name)}`;
    }
    const owner = g.units.get(realm);
    const constant = owner?.module.consts.get(name);
    if (constant !== undefined) ensure_constant(g, realm, name);
    const fn = owner?.module.functions.get(name);
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

// Construcción de un valor de tipo: `Punto(1, 2)` (fábrica), `new Point(...)`
// (clase), `UserId(5)` (`seal`/`echo`, que se borran) y `Shape::Circle(...)`
// (`omen` algebraica).
function emit_type_construction(g: JsContext, name: string, node: CallNode): string | undefined {
  const unit = current_unit(g);
  const env = unit.module.env;
  const alias = env.aliases.get(name);
  if (alias !== undefined) {
    // `seal`/`echo`: el valor es el del argumento, sin envoltorio.
    const first = node.args[0];
    return first === undefined ? "undefined" : emit_expr(g, first.expr, alias.target);
  }
  const rune = env.runes.get(name);
  if (rune !== undefined) {
    ensure_type(g, unit.module.realm, name);
    const reference = cross_reference(g, unit.module.realm, name);
    const params = rune.constructor?.params ?? [...rune.fields.values()].map((field) => field.type);
    const args = emit_args(g, params, false, node.args);
    return rune_is_class(g, unit.module.realm, name) ? `new ${reference}(${args})` : `${reference}(${args})`;
  }
  return undefined;
}

// `Shape::Circle(2.0)` → `Shape.Circle(2.0)`; `Color::Red` sin llamada se
// resuelve en `emit_path_reference`.
function emit_variant_call(g: JsContext, segments: readonly string[], node: CallNode): string | undefined {
  if (segments.length !== 2) return undefined;
  const type_name = segments[0];
  const variant = segments[1];
  if (type_name === undefined || variant === undefined) return undefined;
  const unit = current_unit(g);
  const omen = unit.module.env.omens.get(type_name);
  if (omen === undefined) return undefined;
  const info = omen.variants.get(variant);
  if (info === undefined) return undefined;
  const name = cross_reference(g, unit.module.realm, type_name);
  return `${name}.${js_identifier(variant)}(${emit_args(g, info.payload, false, node.args)})`;
}

// Llamada a un método: los métodos de un rune son métodos de su clase; los de
// `enchanting` sobre tipos incorporados son funciones libres (fase P3).
function emit_member_call(
  g: JsContext,
  member: Extract<ExprNode, { kind: "member" }>,
  node: CallNode,
): string {
  const object_type = expression_type(g, member.object);
  const object = emit_expr(g, member.object);
  const name = js_identifier(member.name);
  if (object_type.kind === "named") {
    const unit = current_unit(g);
    const flags = unit.module.env.omens.get(object_type.name);
    if (flags !== undefined && flags.is_flags && member.name === "has") {
      runtime_name(g);
      return `((${object} & ${emit_args(g, [flags.underlying ?? object_type], false, node.args)}) !== 0)`;
    }
    const rune = unit.module.env.runes.get(object_type.name);
    if (rune !== undefined && rune.methods.has(member.name)) {
      ensure_type(g, unit.module.realm, object_type.name);
      return `${object}.${name}(${emit_args(g, undefined, false, node.args)})`;
    }
    // `omen`, `seal` y `echo` no tienen prototipo donde colgar métodos: son
    // funciones libres con el receptor primero (§4.1).
    const omen = unit.module.env.omens.get(object_type.name);
    const omen_method = omen === undefined ? undefined : omen_methods_of(omen)?.get(member.name);
    const alias = unit.module.env.aliases.get(object_type.name);
    const alias_method = alias?.methods.get(member.name);
    const method = omen_method ?? alias_method;
    if (method !== undefined) {
      const realm = realm_of_type(g, object_type.name) ?? unit.module.realm;
      if (ensure_type(g, realm, object_type.name)) {
        const target = cross_reference(g, realm, free_method_export(object_type.name, member.name));
        const args = emit_args(g, method.params, method.variadic, node.args);
        return `${target}(${object}${args.length === 0 ? "" : `, ${args}`})`;
      }
    }
  }
  if (is_string(object_type) && member.name === "bytes_raw") {
    runtime_name(g);
    return `rt.bytes_raw(${object})`;
  }
  js_error(
    g,
    `la llamada al método «${member.name}» todavía no se emite a JavaScript (fase P2/P3)`,
    node.span,
  );
  return "undefined";
}
