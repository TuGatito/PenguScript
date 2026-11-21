// Capacidades de `needs` e instanciación de funciones genéricas.


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
import { infer_primitive_conversion, is_conversion_target, is_display, ORDERING_VARIANTS } from "./checker_ops.ts";


export const NUMERIC_PRIMITIVES = new Set([
  "int", "long", "long long", "short", "unsigned int", "unsigned long",
  "unsigned long long", "unsigned short", "signed char", "unsigned char",
  "char", "byte", "int8_t", "int16_t", "int32_t", "int64_t", "uint8_t",
  "uint16_t", "uint32_t", "uint64_t", "size_t", "ptrdiff_t", "intptr_t",
  "uintptr_t", "float", "double", "long double",
]);

export const FLOATING_PRIMITIVES = new Set(["float", "double", "long double"]);

export const ORDERED_PRIMITIVES = new Set([
  "int", "long", "long long", "short", "unsigned int", "unsigned long",
  "unsigned long long", "unsigned short", "signed char", "unsigned char",
  "char", "byte", "int8_t", "int16_t", "int32_t", "int64_t", "uint8_t",
  "uint16_t", "uint32_t", "uint64_t", "size_t", "ptrdiff_t", "intptr_t",
  "uintptr_t", "float", "double", "long double", "string", "bool",
]);

export function implements_capability(ctx: CheckContext, capability: string, type: PenguType): boolean {
  if (is_any(type)) return true;
  if (type.kind === "primitive") {
    switch (capability) {
      case "Numeric":
        return NUMERIC_PRIMITIVES.has(type.name);
      case "Floating":
        return FLOATING_PRIMITIVES.has(type.name);
      case "Eq":
      case "Ord":
        return ORDERED_PRIMITIVES.has(type.name);
      case "Hash":
      case "Copy":
      case "Move":
      case "Default":
        return type.name !== "void" && type.name !== "nullptr_t";
      case "Display":
        return is_display(ctx, type);
      default:
        return true;
    }
  }
  if (type.kind === "optional") return implements_capability(ctx, capability, type.inner);
  if (type.kind === "named" && type.args.length > 0) {
    if (capability === "Display") return is_display(ctx, type);
    return type.args.every((arg) => implements_capability(ctx, capability, arg));
  }
  return true;
}

export function check_capabilities(
  ctx: CheckContext,
  needs: readonly string[],
  mapping: ReadonlyMap<string, PenguType>,
  name: string,
  span: Span,
): void {
  // `needs Ord, Copy` enumera capacidades que deben cumplir todos
  // los sigilos de la declaración.
  for (const need of needs) {
    const capability = need.trim();
    for (const type of mapping.values()) {
      if (is_generic_type(ctx, type)) continue;
      if (implements_capability(ctx, capability, type)) continue;
      report_error(
        ctx,
        CODES.missing_capability,
        `«${name}» necesita «${capability}» y «${type_display(type)}» no lo implementa`,
        span,
        [`usa un tipo que cumpla «${capability}» o quita la restricción`],
      );
    }
  }
}

// Empareja el tipo declarado con el real para deducir los sigilos
// (`vector<T>` con `vector<int>` deduce T = int).
export function unify_sigils(
  declared: PenguType,
  actual: PenguType,
  mapping: Map<string, PenguType>,
): void {
  if (declared.kind === "named" && declared.generic === true && declared.args.length === 0) {
    if (!mapping.has(declared.name)) mapping.set(declared.name, actual);
    return;
  }
  if (declared.kind === "named" && actual.kind === "named") {
    declared.args.forEach((arg, index) => {
      const real = actual.args[index];
      if (real !== undefined) unify_sigils(arg, real, mapping);
    });
    return;
  }
  if (declared.kind === "optional" && actual.kind === "optional") {
    unify_sigils(declared.inner, actual.inner, mapping);
    return;
  }
  if (declared.kind === "ref" && actual.kind === "ref") {
    unify_sigils(declared.inner, actual.inner, mapping);
    return;
  }
  if (declared.kind === "array" && actual.kind === "array") {
    unify_sigils(declared.element, actual.element, mapping);
    return;
  }
  if (declared.kind === "function" && actual.kind === "function") {
    declared.params.forEach((param, index) => {
      const real = actual.params[index];
      if (real !== undefined) unify_sigils(param, real, mapping);
    });
    unify_sigils(declared.result, actual.result, mapping);
  }
}

export function check_generic_instantiation(
  ctx: CheckContext,
  fn: FunctionInfo,
  node: CallNode,
  name: string,
): void {
  if (node.type_args.length > 0 && node.type_args.length !== fn.sigils.length) {
    report_error(
      ctx,
      CODES.wrong_arity,
      `«${name}» espera ${fn.sigils.length} argumento(s) de tipo, recibió ${node.type_args.length}`,
      node.span,
    );
    return;
  }

  const explicit = node.type_args.map((arg) => resolve_type_node(arg, ctx.module.env, ctx.sink));
  const inferred = fn.params.map((param, index) => {
    if (param.type.kind === "named" && param.type.generic === true && explicit.length === 0) {
      const arg = node.args[index];
      return arg === undefined ? UNKNOWN : infer_expr(ctx, arg.expr);
    }
    return undefined;
  });

  const mapping = new Map<string, PenguType>();
  fn.sigils.forEach((sigil, index) => {
    const from_explicit = explicit[index];
    if (from_explicit !== undefined) {
      mapping.set(sigil, from_explicit);
      return;
    }
    for (let param = 0; param < fn.params.length; param++) {
      const type = fn.params[param]?.type;
      const value = inferred[param];
      if (type !== undefined && type.kind === "named" && type.generic === true && type.name === sigil && value !== undefined) {
        mapping.set(sigil, value);
      }
    }
  });

  check_capabilities(ctx, fn.needs, mapping, name, node.span);
}

