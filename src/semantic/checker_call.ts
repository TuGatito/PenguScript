// Llamadas: resolución del destino, argumentos, contrato `mut` y
// comprobaciones de `unsafe`.


// cascadas de errores secundarios.

import type {
  ArgNode,
  Block,
  CallNode,
  ExprNode,
  ForClauseNode,
  LambdaNode,
  MatchArm,
  PatternNode,
  SwitchArm,
} from "../frontend/ast.ts";
import { CODES } from "../diagnostics/codes.ts";
import { error as make_error, warning as make_warning } from "../diagnostics/diagnostic.ts";
import type { Span } from "../util/span.ts";
import type { ParamNode } from "../frontend/ast_param.ts";
import { suggest_name } from "../util/suggest.ts";
import { declare, lookup } from "./scopes.ts";
import type { CheckContext } from "./checker_context.ts";
import { with_scope } from "./checker_context.ts";
import { symbol_type_of } from "./external.ts";
import { has_enchanted_method, resolve_enchanted_call } from "./checker_enchants.ts";
import {
  add_borrow,
  ensure_not_iterating,
  can_assign,
  check_initialization,
  ensure_not_borrowed,
  expect_bool,
  is_generic_type,
  report_type_mismatch,
} from "./checker_context.ts";
import {
  BOOL,
  CHAR,
  FLOAT,
  INT,
  NONE,
  NULLPTR,
  SIZE_T,
  STRING,
  UNKNOWN,
  VOID,
  any_type,
  float_rank,
  function_type,
  integer_shape,
  is_any,
  is_float,
  is_integer,
  is_name,
  is_numeric,
  is_string,
  join_types,
  named,
  numeric_join,
  primitive,
  optional,
  ref_to,
  tuple_type,
  type_display,
  type_equals,
  types_equal,
} from "./types.ts";
import type { PenguType } from "./types.ts";
import { STRING_TYPES, is_primitive_type } from "../frontend/ast_type.ts";
import type { TypeNode } from "../frontend/ast_type.ts";
import type { OmenVariantInfo } from "./type_env.ts";
import { function_type_of, omen_methods_of } from "./module_info.ts";
import { find_free_operator } from "./operators.ts";
import { substitute_generics } from "./types.ts";
import type { FunctionInfo } from "./module_info.ts";
import { builtin_function, is_builtin_module } from "./builtin_modules.ts";
import { shared_type, unique_type, weak_type } from "./types.ts";
import { find_echo_method, find_rune_field, find_rune_method, is_heir_of, resolve_type_node } from "./type_env.ts";
import type { TypeEnv } from "./type_env.ts";
import type { OmenInfo } from "./type_env.ts";
import {
  builtin_index_result,
  is_map_type,
  is_sequence_container,
  is_set_type,
  is_string_type,
  map_key_value,
  member_of_builtin,
  sequence_element,
} from "./builtin_members.ts";
import { check_statement } from "./checker_stmt.ts";
import { infer_member } from "./checker_member.ts";
import { check_capabilities, check_generic_instantiation, unify_sigils } from "./checker_generics.ts";
import { infer_block, infer_expr, report_error, known_names, with_new_scope, with_loop, loop_result_type } from "./checker_expr.ts";
import { infer_primitive_conversion, is_conversion_target, is_display, ORDERING_VARIANTS } from "./checker_ops.ts";


export function infer_call(ctx: CheckContext, node: CallNode): PenguType {
  // Métodos declarados con `enchanting` sobre tipos incorporados: el
  // receptor no lleva realm, así que la sobrecarga se elige aquí.
  if (node.callee.kind === "member" && has_enchanted_method(ctx, node.callee.name)) {
    const object = infer_expr(ctx, node.callee.object);
    const enchanted = resolve_enchanted_call(ctx, node, object, node.callee.name);
    if (enchanted !== undefined) return enchanted;
  }

  // `ref(x)` es una construcción del lenguaje, no una función.
  // `ref<T>(x)` es el upcast explícito: solo se permite hacia un
  // ancestro de la rune de `x`.
  if (node.callee.kind === "ident" && node.callee.name === "ref") {
    const first = node.args[0];
    if (first === undefined) return UNKNOWN;
    const inner = infer_expr(ctx, first.expr);
    // `ref(@campo)` dentro de un método `mut` produce un préstamo
    // mutable: el receptor lo permite.
    const self_field = first.expr.kind === "member" && first.expr.object.kind === "self";
    const mutable = first.mutable || (self_field && ctx.self_mutable);
    const root = root_ident(first.expr);
    if (root !== undefined) add_borrow(ctx, root.name, node.span);
    const target = node.type_args[0];
    if (target === undefined) return ref_to(inner, mutable);
    const resolved = resolve_type_node(target, ctx.module.env, ctx.sink);
    const base = inner.kind === "ref" ? inner.inner : inner;
    if (resolved.kind === "named" && base.kind === "named" && !is_heir_of(ctx.module.env, base.name, resolved.name)) {
      report_error(
        ctx,
        CODES.type_mismatch,
        `«${type_display(base)}» no desciende de «${type_display(resolved)}»`,
        node.span,
      );
    }
    return ref_to(resolved, mutable);
  }

  // `raw<T>(ref(x))` crea un puntero crudo (solo dentro de `unsafe`).
  if (node.callee.kind === "ident" && node.callee.name === "raw" && node.type_args.length === 1) {
    const inner = infer_expr(ctx, node.args[0]?.expr ?? node.callee);
    const target = resolve_type_node(node.type_args[0] as TypeNode, ctx.module.env, ctx.sink);
    if (ctx.unsafe_depth === 0) {
      report_error(ctx, CODES.unsafe_required, "crear un «raw<T>» requiere «unsafe»", node.span);
    }
    const payload = inner.kind === "ref" ? inner.inner : inner;
    if (inner.kind !== "ref" && inner.kind !== "nullptr") {
      report_error(
        ctx,
        CODES.type_mismatch,
        `«raw<T>» espera un «ref<T>» o «nullptr», recibió «${type_display(inner)}»`,
        node.span,
      );
    }
    return target.kind === "raw" ? target : { kind: "raw", inner: payload };
  }

  // Construcción de un rune, `seal` o `echo` por nombre.
  if (node.callee.kind === "ident") {
    const name = node.callee.name;
    const variant = find_omen_variant(ctx, name);
    if (variant !== undefined) {
      check_arguments(ctx, variant.variant.payload, node.args, node.span, name);
      return named(variant.omen);
    }
    const generic_fn = ctx.module.functions.get(name);
    if (generic_fn !== undefined && generic_fn.sigils.length > 0) {
      check_generic_instantiation(ctx, generic_fn, node, name);
    }
    if (ctx.module.env.runes.has(name) || ctx.module.env.aliases.has(name)) {
      return infer_construction(ctx, name, node.args, node.span);
    }
  }

  if (node.callee.kind === "ident" && node.type_args.length === 1) {
    const pointer = node.callee.name;
    if (pointer === "unique" || pointer === "shared") {
      const inner_node = node.type_args[0];
      if (inner_node !== undefined) {
        const inner = resolve_type_node(inner_node, ctx.module.env, ctx.sink);
        if (inner.kind === "named" && ctx.module.env.runes.has(inner.name)) {
          infer_construction(ctx, inner.name, node.args, node.span);
        } else {
          check_arguments(ctx, [inner], node.args, node.span, pointer);
        }
        return pointer === "unique" ? unique_type(inner) : shared_type(inner);
      }
    }
  }

  if (node.callee.kind === "ident" && node.callee.name === "weak" && node.args.length === 1) {
    const first = node.args[0];
    if (first !== undefined) {
      const actual = infer_expr(ctx, first.expr);
      const inner = actual.kind === "shared" ? actual.inner : actual;
      return weak_type(inner);
    }
  }

  if (node.callee.kind === "path") {
    const segments = node.callee.segments;
    const first = segments[0];
    const second = segments[1];
    if (first !== undefined && second !== undefined) {
      const omen = ctx.module.env.omens.get(first);
      const instance = node.callee.type_args !== undefined && node.callee.type_args.length > 0
        ? named(first, node.callee.type_args.map((arg) => resolve_type_node(arg, ctx.module.env, ctx.sink)))
        : named(first);
      if (omen !== undefined) {
        if (second === "try_from" || second === "from") {
          check_arguments(ctx, [INT], node.args, node.span, `${first}::${second}`);
          return second === "try_from" ? optional(instance) : instance;
        }
        const variant = omen.variants.get(second);
        if (variant !== undefined) {
          check_arguments(ctx, variant.payload, node.args, node.span, `${first}::${second}`);
          return instance;
        }
      }
    }
  }

  // Conversión explícita de un primitivo: `int::try_from(x)`.
  if (node.callee.kind === "path" && node.callee.segments.length === 2) {
    const target_name = node.callee.segments[0];
    const operation = node.callee.segments[1];
    if (
      target_name !== undefined &&
      (operation === "try_from" || operation === "from") &&
      is_conversion_target(target_name)
    ) {
      return infer_primitive_conversion(ctx, target_name, operation, node.args, node.span);
    }
  }

  const callee_type = infer_expr(ctx, node.callee);
  if (node.callee.kind === "member") {
    check_mut_receiver(ctx, node.callee);
    if (node.callee.name === "get_unchecked" && ctx.unsafe_depth === 0) {
      report_error(
        ctx,
        CODES.unsafe_required,
        "«get_unchecked» no comprueba límites: úsalo dentro de «unsafe»",
        node.span,
      );
    }
  }
  check_unsafe_call(ctx, node);

  if (callee_type.kind === "function") {
    let params = callee_type.params;
    let result = callee_type.result;
    if (node.callee.kind === "ident") {
      const fn = ctx.module.functions.get(node.callee.name);
      if (fn !== undefined && fn.sigils.length > 0) {
        const mapping = new Map<string, PenguType>();
        fn.sigils.forEach((sigil, index) => {
          const explicit = node.type_args[index];
          if (explicit !== undefined) {
            mapping.set(sigil, resolve_type_node(explicit, ctx.module.env, ctx.sink));
          }
        });
        fn.params.forEach((param, index) => {
          const arg = node.args[index];
          if (arg === undefined) return;
          unify_sigils(param.type, infer_expr(ctx, arg.expr), mapping);
        });
        params = params.map((param) => substitute_generics(param, mapping));
        result = substitute_generics(result, mapping);
      }
    }
    check_arguments(
      ctx,
      params,
      node.args,
      node.span,
      describe_callee(node.callee),
      callee_type.variadic,
      callee_type.required,
      param_mutables_of(ctx, node.callee),
    );
    return result;
  }

  if (callee_type.kind === "named") {
    return infer_construction(ctx, callee_type.name, node.args, node.span);
  }

  if (is_any(callee_type)) {
    // Una función de la stdlib es opaca, pero sus argumentos también
    // deben analizarse (por ejemplo interpolaciones).
    for (const arg of node.args) infer_expr(ctx, arg.expr);
    return callee_type;
  }

  report_error(
    ctx,
    CODES.not_callable,
    `«${describe_callee(node.callee)}» no es invocable`,
    node.span,
  );
  return UNKNOWN;
}

// Una función `unsafe` solo se puede llamar desde `unsafe`.
export function check_unsafe_call(ctx: CheckContext, node: CallNode): void {
  if (ctx.unsafe_depth > 0) return;
  let unsafe_function = false;
  if (node.callee.kind === "ident") {
    unsafe_function = ctx.module.functions.get(node.callee.name)?.is_unsafe === true;
  } else if (node.callee.kind === "path" && node.callee.segments.length >= 2) {
    const imported = ctx.external?.modules.get(node.callee.segments[0] ?? "");
    unsafe_function = imported?.functions.get(node.callee.segments[1] ?? "")?.is_unsafe === true;
  }
  if (!unsafe_function) return;
  const callee = node.callee;
  const name = callee.kind === "ident" ? callee.name : callee.kind === "path" ? callee.segments.join("::") : "?";
  report_error(
    ctx,
    CODES.unsafe_required,
    `«${name}» es «unsafe»: llámala dentro de un bloque «unsafe»`,
    node.span,
  );
}

// Llamar a un método `mut` (o a un método de contenedor que muta) exige
// que el receptor sea mutable y no esté prestado.
export const INTERIOR_MUTABLE = new Set(["atomic", "mutex", "shared_mutex", "condition_variable"]);

export const MUTATING_MEMBERS = new Set([
  "push",
  "push_back",
  "pop",
  "pop_back",
  "pop_opt",
  "insert",
  "insert_or_assign",
  "remove",
  "remove_at",
  "clear",
  "extract",
  "store",
  "fetch_add",
  "set",
  "reset",
  "flip",
]);

export function check_mut_receiver(
  ctx: CheckContext,
  callee: Extract<ExprNode, { kind: "member" }>,
): void {
  const root = root_ident(callee.object);
  if (root === undefined) return;
  const variable = lookup(ctx.scope, root.name);
  if (variable === undefined) return;
  const receiver = infer_expr(ctx, callee.object);
  // `atomic` y los mutex tienen mutabilidad interior: no exigen `mut`.
  if (receiver.kind === "named" && INTERIOR_MUTABLE.has(receiver.name)) return;
  const mutating =
    (receiver.kind === "named" && is_mutating_method(ctx, receiver, callee.name)) ||
    (receiver.kind === "named" && MUTATING_MEMBERS.has(callee.name)) ||
    (receiver.kind === "ref" || receiver.kind === "unique" || receiver.kind === "shared"
      ? MUTATING_MEMBERS.has(callee.name)
      : false);
  if (!mutating) return;
  ensure_not_borrowed(ctx, root.name, callee.span, "modificar");
  ensure_not_iterating(ctx, root.name, callee.span, "modificar");
  if (variable.mutable) return;
  if (
    variable.type.kind === "ref" ||
    variable.type.kind === "shared" ||
    variable.type.kind === "unique" ||
    variable.type.kind === "raw"
  ) {
    return;
  }
  report_error(
    ctx,
    CODES.mutable_required,
    `«${root.name}» es inmutable; decláralo con «mut» para llamar a «${callee.name}»`,
    root.span,
  );
}

export function is_mutating_method(ctx: CheckContext, receiver: PenguType, name: string): boolean {
  if (receiver.kind !== "named") return false;
  const rune = ctx.module.env.runes.get(receiver.name);
  if (rune === undefined) return false;
  const method = find_rune_method(ctx.module.env, rune, name);
  return method?.mutable === true;
}

// `mut` declarado por el destino de la llamada, en orden. Lista vacía si
// el destino es opaco (stdlib, `extern` sin firma, etc.).
export function param_mutables_of(ctx: CheckContext, callee: ExprNode): readonly boolean[] {
  if (callee.kind === "ident") {
    const fn = ctx.module.functions.get(callee.name);
    return fn === undefined ? [] : fn.params.map((param) => param.mutable);
  }
  if (callee.kind === "path") {
    const first = callee.segments[0];
    if (callee.segments.length >= 2 && first !== undefined) {
      const imported = ctx.external?.modules.get(first);
      const fn = imported?.functions.get(callee.segments[1] ?? "");
      if (fn !== undefined) return fn.params.map((param) => param.mutable);
    }
    return [];
  }
  if (callee.kind === "member") {
    const receiver = type_of_member_object(ctx, callee.object);
    if (receiver !== undefined && receiver.kind === "named") {
      const rune = ctx.module.env.runes.get(receiver.name);
      if (rune !== undefined) {
        const method = find_rune_method(ctx.module.env, rune, callee.name);
        if (method !== undefined) return method.param_mutables;
      }
      const alias = ctx.module.env.aliases.get(receiver.name);
      const method = alias?.methods.get(callee.name);
      if (method !== undefined) return method.param_mutables;
    }
    return [];
  }
  if (callee.kind === "lambda") {
    return callee.params.map((param) => param.mutable);
  }
  return [];
}

export function type_of_member_object(ctx: CheckContext, object: ExprNode): PenguType | undefined {
  return infer_expr(ctx, object);
}

export function describe_callee(callee: ExprNode): string {
  switch (callee.kind) {
    case "ident":
      return callee.name;
    case "member":
      return callee.name;
    case "path":
      return callee.segments.join("::");
    default:
      return "la expresión";
  }
}

// Busca `Circle(1.0)` sin `Omen::`: el nombre de la variante basta.

// Tipo declarado de un literal con prefijo (`vector<int>[...]`).
export function infer_declared(ctx: CheckContext, node: TypeNode | undefined): PenguType | undefined {
  if (node === undefined) return undefined;
  return resolve_type_node(node, ctx.module.env, ctx.sink);
}

export function literal_element(type: PenguType | undefined): PenguType | undefined {
  if (type === undefined) return undefined;
  if (type.kind === "array") return type.element;
  if (type.kind === "named") return type.args[0];
  return undefined;
}

export function find_omen_variant(
  ctx: CheckContext,
  name: string,
): { omen: string; variant: OmenVariantInfo } | undefined {
  for (const [omen_name, omen] of ctx.module.env.omens) {
    const variant = omen.variants.get(name);
    if (variant !== undefined) return { omen: omen_name, variant };
  }
  return undefined;
}

export function infer_construction(
  ctx: CheckContext,
  name: string,
  args: readonly ArgNode[],
  span: Span,
): PenguType {
  const alias = ctx.module.env.aliases.get(name);
  if (alias !== undefined) {
    check_arguments(ctx, [alias.target], args, span, name);
    return alias.seal ? named(name) : alias.target;
  }

  const rune = ctx.module.env.runes.get(name);
  if (rune === undefined) return any_type(name);

  if (rune.constructor !== undefined) {
    check_arguments(
      ctx,
      rune.constructor.params,
      args,
      span,
      name,
    );
    return named(name);
  }

  const fields = [...rune.fields.values()];
  check_arguments(
    ctx,
    fields.map((field) => field.type),
    args,
    span,
    name,
    false,
    fields.filter((field) => !field.has_default).length,
  );
  return named(name);
}

export function check_arguments(
  ctx: CheckContext,
  params: readonly PenguType[],
  args: readonly ArgNode[],
  span: Span,
  name: string,
  variadic = false,
  required = params.length,
  param_mutables: readonly boolean[] = [],
): void {
  const fixed_count = variadic ? Math.max(params.length - 1, 0) : params.length;
  const element = variadic ? params[params.length - 1] : undefined;
  const spread_count = args.filter((arg) => arg.spread).length;
  const plain_count = args.length - spread_count;

  if (plain_count < required || (spread_count === 0 && !variadic && plain_count > params.length)) {
    const expected = variadic
      ? `al menos ${required}`
      : required === params.length
        ? `${params.length}`
        : `entre ${required} y ${params.length}`;
    report_error(
      ctx,
      CODES.wrong_arity,
      `«${name}» espera ${expected} argumento(s), recibió ${plain_count}`,
      span,
    );
  }

  let position = 0;
  for (const arg of args) {
    const actual = infer_expr(ctx, arg.expr);
    check_mut_argument(ctx, param_mutables, position, arg, name);

    if (arg.spread) {
      if (!variadic || element === undefined) {
        report_error(
          ctx,
          CODES.type_mismatch,
          `no se puede expandir «...» en «${name}»: no es una función variádica`,
          arg.expr.span,
        );
        continue;
      }
      const spread_element = arg.expr.kind === "ident" ? actual : actual;
      const inner = sequence_element_of(spread_element);
      if (inner === undefined) {
        report_error(
          ctx,
          CODES.type_mismatch,
          `«${name}» solo puede expandir un vector, recibió «${type_display(actual)}»`,
          arg.expr.span,
        );
        continue;
      }
      check_argument_value(ctx, element, inner, position, name, arg.expr.span);
      continue;
    }

    if (position < fixed_count) {
      const param = params[position];
      position += 1;
      if (param === undefined) continue;
      if (!arg.mutable) mark_moved(ctx, arg.expr, param);
      check_argument_value(ctx, param, actual, position - 1, name, arg.expr.span);
      continue;
    }

    if (variadic && element !== undefined) {
      check_argument_value(ctx, element, actual, position, name, arg.expr.span);
      position += 1;
      if (!arg.mutable) mark_moved(ctx, arg.expr, element);
    }
  }
}

// Contrato `mut`: el parámetro debe declararse `mut` y el argumento
// debe ser un lugar mutable (`mut x`), no una expresión temporal.
export function check_mut_argument(
  ctx: CheckContext,
  param_mutables: readonly boolean[],
  position: number,
  arg: ArgNode,
  name: string,
): void {
  if (param_mutables.length === 0) return;
  const expects = param_mutables[position] === true;
  if (arg.mutable && !expects) {
    report_error(
      ctx,
      CODES.mutable_required,
      `«${name}» no declara «mut» en el parámetro ${position + 1}`,
      arg.expr.span,
    );
    return;
  }
  if (expects && !arg.mutable) {
    report_error(
      ctx,
      CODES.mutable_required,
      `el parámetro ${position + 1} de «${name}» es «mut»: escribe «mut» en el argumento`,
      arg.expr.span,
    );
    return;
  }
  if (!arg.mutable) return;
  const root = root_ident(arg.expr);
  const variable = root === undefined ? undefined : lookup(ctx.scope, root.name);
  if (variable === undefined || !variable.mutable) {
    report_error(
      ctx,
      CODES.mutable_required,
      `«mut» requiere una variable declarada con «mut»`,
      arg.expr.span,
    );
  }
}

export function check_argument_value(
  ctx: CheckContext,
  expected: PenguType,
  actual: PenguType,
  index: number,
  name: string,
  span: Span,
): void {
  if (is_generic_type(ctx, expected) || is_generic_type(ctx, actual)) return;
  if (!can_assign(expected, actual, ctx.module.env)) {
    report_error(
      ctx,
      CODES.type_mismatch,
      `el argumento ${index + 1} de «${name}» espera «${type_display(expected)}», recibió «${type_display(actual)}»`,
      span,
    );
    return;
  }
  // Una variádica `any` exige que cada argumento sea Display.
  if (is_any(expected) && !is_display(ctx, actual)) {
    report_error(
      ctx,
      CODES.not_display,
      `«${type_display(actual)}» no implementa «Display» y no puede pasar a una variádica «any»`,
      span,
    );
  }
}

// Elemento de un valor expandible con `...` (solo vectores).
export function sequence_element_of(type: PenguType): PenguType | undefined {
  if (type.kind === "named" && type.name === "vector" && type.args.length === 1) {
    return type.args[0];
  }
  return undefined;
}

// Tipo con el que se declara un parámetro dentro del cuerpo: un
// variádico vale `vector<T>`.
export function param_binding_type(param: ParamNode, declared: PenguType): PenguType {
  return param.variadic ? named("vector", [declared]) : declared;
}

// Marca el origen de un valor move-only como movido (`use after move`).
export function mark_moved(ctx: CheckContext, expr: ExprNode, target: PenguType): void {
  if (target.kind !== "unique") return;
  const root = root_ident(expr);
  if (root === undefined) return;
  const variable = lookup(ctx.scope, root.name);
  if (variable !== undefined) variable.moved = true;
}

// Identificador raíz de una expresión de acceso (`p.x`, `xs[0]`, `p`).
export function root_ident(expr: ExprNode): Extract<ExprNode, { kind: "ident" }> | undefined {
  if (expr.kind === "ident") return expr;
  if (expr.kind === "member") return root_ident(expr.object);
  if (expr.kind === "index") return root_ident(expr.object);
  return undefined;
}


