// Acceso a miembros, rutas `realm::simbolo` e índices implícitos.


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
import { infer_block, infer_expr, report_error, known_names, with_new_scope, with_loop, loop_result_type } from "./checker_expr.ts";
import { resolve_enchanted_member } from "./checker_enchants.ts";
import { infer_primitive_conversion, is_conversion_target, is_display, ORDERING_VARIANTS } from "./checker_ops.ts";


export function infer_path(
  ctx: CheckContext,
  segments: readonly string[],
  span: Span,
  type_args: readonly TypeNode[] = [],
): PenguType {
  const first = segments[0];
  const second = segments[1];
  if (first === undefined) return UNKNOWN;

  // Módulos importados con `invoke "ruta"`: `alias::simbolo`.
  const imported_module = ctx.external?.modules.get(first);
  if (imported_module !== undefined && second !== undefined) {
    const type = symbol_type_of(imported_module, second);
    if (type !== undefined) return type;
    report_error(ctx, CODES.unknown_identifier, `el módulo «${first}» no exporta «${second}»`, span);
    return UNKNOWN;
  }

  if (is_builtin_module(first)) {
    if (second !== undefined) {
      const signature = builtin_function(first, second);
      if (signature !== undefined) {
        return function_type(signature.params, signature.result, signature.variadic ?? false);
      }
      report_error(ctx, CODES.unknown_identifier, `el módulo «${first}» no exporta «${second}»`, span);
      return UNKNOWN;
    }
    return any_type(`módulo std::${first}`);
  }

  if (first === "Ordering" && second !== undefined) {
    if (ORDERING_VARIANTS.has(second)) return named("Ordering");
    report_error(
      ctx,
      CODES.unknown_identifier,
      `«Ordering» no tiene la variante «${second}» (usa Less, Equal o Greater)`,
      span,
    );
    return UNKNOWN;
  }

  if (
    segments.length === 2 &&
    second !== undefined &&
    (second === "try_from" || second === "from") &&
    is_conversion_target(first)
  ) {
    return any_type(`conversión ${first}::${second}`);
  }

  const instance = type_args.length > 0
    ? named(first, type_args.map((arg) => resolve_type_node(arg, ctx.module.env, ctx.sink)))
    : named(first);

  if (segments.length === 2 && second !== undefined) {
    const omen = ctx.module.env.omens.get(first);
    if (omen !== undefined) {
      if (second === "try_from") return function_type([INT], optional(instance));
      if (second === "from") return function_type([INT], instance);
      const variant = omen.variants.get(second);
      if (variant !== undefined) {
        if (variant.payload.length > 0) {
          return function_type(variant.payload, instance);
        }
        return instance;
      }
      report_error(ctx, CODES.unknown_identifier, `el omen «${first}» no tiene la variante «${second}»`, span);
      return UNKNOWN;
    }

    const rune = ctx.module.env.runes.get(first);
    if (rune !== undefined) {
      const method = rune.methods.get(second);
      if (method !== undefined) {
        return function_type(
          method.params,
          method.result,
          method.variadic,
          method.required,
        );
      }
      return any_type(`método asociado ${first}::${second}`);
    }
  }

  // `realm::symbol` dentro del mismo módulo.
  if (first === ctx.module.realm) {
    const rest = segments.slice(1).join("::");
    const constant = ctx.module.consts.get(rest);
    if (constant !== undefined) return constant.type;
    const fn = ctx.module.functions.get(rest);
    if (fn !== undefined) return function_type_of(fn);
    return any_type(`símbolo ${rest}`);
  }

  const imported = ctx.module.imports.get(first);
  if (imported !== undefined) {
    return any_type(`símbolo importado ${segments.join("::")}`);
  }

  if (ctx.module.env.omens.has(first) || ctx.module.env.runes.has(first)) {
    return named(first);
  }

  const suggestion = suggest_name(segments.join("::"), known_names(ctx));
  const hint = suggestion === undefined ? "" : `; ¿quisiste decir «${suggestion}»?`;
  report_error(ctx, CODES.unknown_identifier, `no se reconoce «${segments.join("::")}»${hint}`, span);
  return UNKNOWN;
}

// Resultado de un operador declarado en `enchanting` para una rune.
export function rune_operator_method(
  ctx: CheckContext,
  type: PenguType,
  operator: string,
): PenguType | undefined {
  if (type.kind !== "named") return undefined;
  const rune = ctx.module.env.runes.get(type.name);
  if (rune === undefined) return undefined;
  return find_rune_method(ctx.module.env, rune, operator)?.result;
}

export function infer_member(
  ctx: CheckContext,
  object: PenguType,
  name: string,
  span: Span,
  node?: Extract<ExprNode, { kind: "member" }>,
): PenguType {
  if (is_any(object)) return object;

  if (object.kind === "ref" || object.kind === "unique" || object.kind === "shared" || object.kind === "raw") {
    return infer_member(ctx, object.inner, name, span, node);
  }

  if (object.kind === "weak") {
    if (name === "lock") return function_type([], optional(shared_type(object.inner)));
  }

  if (object.kind === "named") {
    const rune = ctx.module.env.runes.get(object.name);
    if (rune !== undefined) {
      const field = find_rune_field(ctx.module.env, rune, name);
      if (field !== undefined) return field.type;
      const method = find_rune_method(ctx.module.env, rune, name);
      if (method !== undefined) {
        return function_type(
          method.params,
          method.result,
          method.variadic,
          method.required,
        );
      }
      report_error(ctx, CODES.unknown_field, `el rune «${object.name}» no tiene «${name}»`, span);
      return UNKNOWN;
    }
    const alias = ctx.module.env.aliases.get(object.name);
    if (alias !== undefined) {
      const method = alias.methods.get(name);
      if (method !== undefined) {
        return function_type(
          method.params,
          method.result,
          method.variadic,
          method.required,
        );
      }
    }
    const omen = ctx.module.env.omens.get(object.name);
    if (omen !== undefined) {
      const method = omen_methods_of(omen)?.get(name);
      if (method !== undefined) {
        return function_type(
          method.params,
          method.result,
          method.variadic,
          method.required,
        );
      }
      if (omen.is_flags && name === "has") {
        return function_type([named(object.name)], BOOL);
      }
    }
  }

  const echo_method = find_echo_method(ctx.module.env, object, name);
  if (echo_method !== undefined) {
    return function_type(
      echo_method.params,
      echo_method.result,
      echo_method.variadic,
      echo_method.params.length - (echo_method.variadic ? 1 : 0),
    );
  }

  // `enchanting` sobre tipos incorporados: manda sobre la tabla nativa.
  if (node !== undefined) {
    const enchanted = resolve_enchanted_member(ctx, node, object);
    if (enchanted !== undefined) return enchanted;
  }

  const builtin = member_of_builtin(object, name);
  if (builtin !== undefined) return builtin;

  report_error(
    ctx,
    CODES.unknown_field,
    `el tipo «${type_display(object)}» no tiene el miembro «${name}»`,
    span,
  );
  return UNKNOWN;
}


// Capacidades estructurales de los sigilos (`needs Ord, Copy`).
// Solo se comprueban sobre tipos primitivos y contenedores conocidos;
// para runes y omens se confía en el compilador de C++.
