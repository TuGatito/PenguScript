// Operadores, conversiones, precedencia y `Display`.
//
// Parte de la inferencia de expresiones: reglas de los operadores
// binarios y unarios, `as` seguros y el tipo `Ordering`.

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

export function infer_unary(
  ctx: CheckContext,
  operator: string,
  operand: ExprNode,
  span: Span,
): PenguType {
  switch (operator) {
    case "not": {
      const type = infer_expr(ctx, operand);
      expect_bool(ctx, type, span, "el operando de «not»");
      return BOOL;
    }
    case "-": {
      const type = infer_expr(ctx, operand);
      if (is_any(type) || is_numeric(type)) return type;
      if (type.kind === "named") {
        const rune = ctx.module.env.runes.get(type.name);
        const method = rune === undefined ? undefined : find_rune_method(ctx.module.env, rune, "-");
        if (method !== undefined) return method.result;
      }
      report_error(ctx, CODES.type_mismatch, `«-» espera un número, recibió «${type_display(type)}»`, span);
      return UNKNOWN;
    }
    case "~": {
      const type = infer_expr(ctx, operand);
      if (is_any(type) || is_integer(type)) return type;
      if (type.kind === "named") {
        const flags = ctx.module.env.omens.get(type.name);
        if (flags?.is_flags === true) return type;
      }
      report_error(ctx, CODES.type_mismatch, `«~» espera un entero, recibió «${type_display(type)}»`, span);
      return UNKNOWN;
    }
    case "#": {
      infer_expr(ctx, operand);
      return SIZE_T;
    }
    case "&": {
      const type = infer_expr(ctx, operand);
      return ref_to(type, false);
    }
    case "*": {
      const type = infer_expr(ctx, operand);
      if (type.kind === "raw" && ctx.unsafe_depth === 0) {
        report_error(
          ctx,
          CODES.unsafe_required,
          "desreferenciar un «raw<T>» requiere «unsafe»",
          span,
        );
      }
      if (
        type.kind === "raw" ||
        type.kind === "ref" ||
        type.kind === "unique" ||
        type.kind === "shared" ||
        type.kind === "weak"
      ) {
        return type.inner;
      }
      if (type.kind === "optional") return type.inner;
      return any_type("desreferencia");
    }
    default:
      return infer_expr(ctx, operand);
  }
}

export function infer_binary(
  ctx: CheckContext,
  operator: string,
  leftNode: ExprNode,
  rightNode: ExprNode,
  span: Span,
): PenguType {
  const left = infer_expr(ctx, leftNode);
  const right = infer_expr(ctx, rightNode);

  if (is_any(left) || is_any(right)) return any_type("operación");
  if (is_generic_type(ctx, left) || is_generic_type(ctx, right)) {
    // Una comparación de un valor genérico siempre produce «bool»: el tipo
    // concreto lo comprobará el compilador de C++ al instanciar.
    if (GENERIC_COMPARISONS.has(operator)) return BOOL;
    return is_generic_type(ctx, left) ? left : right;
  }

  switch (operator) {
    case "and":
    case "or":
      expect_bool(ctx, left, leftNode.span, `el operando izquierdo de «${operator}»`);
      expect_bool(ctx, right, rightNode.span, `el operando derecho de «${operator}»`);
      return BOOL;
    case "==":
    case "!=":
      return BOOL;
    case "<=>":
      return ordering_result(ctx, left, right, span);
    case "<":
    case ">":
    case "<=":
    case ">=":
      if (is_numeric(left) && is_numeric(right)) return BOOL;
      if (is_string(left) && is_string(right)) return BOOL;
      if (left.kind === "named") {
        const methods = ctx.module.env.runes.get(left.name)?.methods;
        if (methods?.has("<=>") === true || methods?.has("operator <=>") === true) return BOOL;
      }
      report_error(ctx, CODES.type_mismatch, `«${operator}» no compara «${type_display(left)}» con «${type_display(right)}»`, span);
      return BOOL;
    case "+":
      if (is_string(left) && is_string(right)) return STRING;
      if (is_numeric(left) && is_numeric(right)) return arithmetic_result(ctx, operator, left, right, span);
      break;
    case "-":
    case "*":
    case "/":
    case "%":
      if (is_numeric(left) && is_numeric(right)) return arithmetic_result(ctx, operator, left, right, span);
      break;
    case "&":
    case "|":
    case "^":
    case "<<":
    case ">>":
      if (is_integer(left) && is_integer(right)) {
        if (is_name(left, "bool") || is_name(right, "bool")) {
          report_error(ctx, CODES.type_mismatch, `«${operator}» no está definido sobre «bool»`, span);
          return UNKNOWN;
        }
        return left;
      }
      break;
    case "in": {
      if (is_string(left) && is_string(right)) return BOOL;
      if (is_map_type(right)) return BOOL;
      if (is_set_type(right)) return BOOL;
      if (is_sequence_container(right)) return BOOL;
      return BOOL;
    }
  }

  // Banderas: `|`, `&` y `^` están definidos sobre el omen.
  if (left.kind === "named" && (operator === "|" || operator === "&" || operator === "^")) {
    const flags = ctx.module.env.omens.get(left.name);
    if (flags?.is_flags === true) return left;
  }

  // Operadores declarados por el usuario.
  if (left.kind === "named") {
    const rune = ctx.module.env.runes.get(left.name);
    const method = rune === undefined ? undefined : find_rune_method(ctx.module.env, rune, operator);
    if (method !== undefined) return method.result;
  }

  // Operador libre (`operator + = (a: int, b: Punto) -> Punto`).
  const free = find_free_operator(ctx.module, ctx.external, operator, left, right, ctx.module.env);
  if (free !== undefined) return free.info.result;

  report_error(
    ctx,
    CODES.type_mismatch,
    `«${operator}» no está definido para «${type_display(left)}» y «${type_display(right)}»`,
    span,
  );
  return UNKNOWN;
}

// Resultado de una operación aritmética, con el modelo numérico del
// lenguaje (promoción al entero mayor, float domina, sin mezclas de
// signo del mismo ancho).
export function arithmetic_result(
  ctx: CheckContext,
  operator: string,
  left: PenguType,
  right: PenguType,
  span: Span,
): PenguType {
  // Dentro de un cuerpo genérico la operación concreta no se conoce
  // (la garantiza el `needs Numeric` de C++): se propaga el tipo.
  if (is_generic_type(ctx, left) || is_generic_type(ctx, right)) {
    // Una comparación de un valor genérico siempre produce «bool»: el tipo
    // concreto lo comprobará el compilador de C++ al instanciar.
    if (GENERIC_COMPARISONS.has(operator)) return BOOL;
    return is_generic_type(ctx, left) ? left : right;
  }
  if (!is_numeric(left) || !is_numeric(right)) {
    report_error(
      ctx,
      CODES.type_mismatch,
      `«${operator}» no está definido para «${type_display(left)}» y «${type_display(right)}»`,
      span,
    );
    return UNKNOWN;
  }
  if (operator === "%" && (is_float(left) || is_float(right))) {
    report_error(ctx, CODES.type_mismatch, "«%» solo admite enteros", span);
    return UNKNOWN;
  }
  const joined = numeric_join(left, right);
  if (joined === undefined) {
    report_error(
      ctx,
      CODES.type_mismatch,
      `«${type_display(left)}» y «${type_display(right)}» tienen el mismo ancho y signo distinto; conviértelos con «as»`,
      span,
    );
    return left;
  }
  return joined;
}

export function ordering_result(ctx: CheckContext, left: PenguType, right: PenguType, span: Span): PenguType {
  if ((is_numeric(left) && is_numeric(right)) || (is_string(left) && is_string(right))) {
    return named("Ordering");
  }
  if (left.kind === "named") {
    const methods = ctx.module.env.runes.get(left.name)?.methods;
    const method = methods?.get("<=>") ?? methods?.get("operator <=>");
    if (method !== undefined) return method.result;
    // Sellos y echoes declaran `<=>` en su bloque `enchanting`.
    const alias = ctx.module.env.aliases.get(left.name);
    const alias_method = alias?.methods.get("<=>");
    if (alias_method !== undefined) return alias_method.result;
    // Los omens no sobrecargan operadores, pero comparan por igualdad.
    const omen = ctx.module.env.omens.get(left.name);
    if (omen !== undefined) return named("Ordering");
  }
  report_error(
    ctx,
    CODES.type_mismatch,
    `«<=>» no compara «${type_display(left)}» con «${type_display(right)}»`,
    span,
  );
  return UNKNOWN;
}

export function infer_cast(ctx: CheckContext, node: Extract<ExprNode, { kind: "cast" }>): PenguType {
  const source = infer_expr(ctx, node.value);
  const target = resolve_type_node(node.type, ctx.module.env, ctx.sink);

  if (is_any(source) || is_any(target)) return target;

  if (source.kind === "named" && source.name === "variant" && source.args.length > 0) {
    if (!source.args.some((option) => type_equals(option, target))) {
      report_error(
        ctx,
        CODES.unsafe_required,
        `«${type_display(source)}» no contiene «${type_display(target)}»`,
        node.span,
      );
    }
    return target;
  }

  const safe = is_safe_cast(source, target, ctx.module.env);
  if (!safe) {
    if (ctx.unsafe_depth === 0) {
      report_error(
        ctx,
        CODES.unsafe_required,
        `la conversión de «${type_display(source)}» a «${type_display(target)}» requiere «unsafe»`,
        node.span,
      );
    }
  }
  return target;
}

// Reglas de `as` seguro según el cheatsheet: solo se permite lo que
// nunca pierde información. Todo lo demás exige `unsafe`.
export function is_safe_cast(source: PenguType, target: PenguType, env?: TypeEnv): boolean {
  if (type_equals(source, target)) return true;
  if (source.kind === "any" || target.kind === "any") return true;

  const source_int = integer_shape(source);
  const target_int = integer_shape(target);
  if (source_int !== undefined && target_int !== undefined) {
    if (source_int.signed === target_int.signed) return target_int.bits >= source_int.bits;
    return target_int.signed && target_int.bits > source_int.bits;
  }

  const source_float = float_rank(source);
  const target_float = float_rank(target);
  if (source_int !== undefined && target_float !== undefined) return true;
  if (source_float !== undefined && target_float !== undefined) return target_float >= source_float;

  if (env !== undefined && source.kind === "named" && target.kind === "primitive") {
    // Desenvolver un seal es seguro: es su tipo subyacente.
    const alias = env.aliases.get(source.name);
    if (alias !== undefined && alias.seal) return type_equals(target, alias.target);

    // Un omen solo se convierte a su tipo subyacente exacto.
    const omen = env.omens.get(source.name);
    if (omen !== undefined) {
      const underlying = omen.underlying ?? INT;
      return type_equals(target, underlying);
    }
  }

  return false;
}

export function is_display(ctx: CheckContext, type: PenguType): boolean {
  if (type.kind === "named" && type.generic === true) return true;
  switch (type.kind) {
    case "any":
    case "primitive":
    case "none":
    case "nullptr":
      return true;
    case "optional":
      return is_display(ctx, type.inner);
    case "ref":
      return is_display(ctx, type.inner);
    case "tuple":
      return type.items.every((item) => is_display(ctx, item));
    case "array":
      return is_display(ctx, type.element);
    case "range":
      return is_display(ctx, type.element);
    case "named": {
      if (CONTAINER_TYPES.has(type.name)) {
        return type.args.every((arg) => is_display(ctx, arg));
      }
      const rune = ctx.module.env.runes.get(type.name);
      if (rune !== undefined) return rune.methods.has("to_string");
      const omen = ctx.module.env.omens.get(type.name);
      if (omen !== undefined) {
        // Los omens unitarios y de flags se imprimen como número; los
        // algebraicos no sabrían qué variante mostrar.
        return [...omen.variants.values()].every((variant) => variant.payload.length === 0);
      }
      if (type.name === "Ordering") return true;
      const alias = ctx.module.env.aliases.get(type.name);
      if (alias !== undefined) return is_display(ctx, alias.target);
      return false;
    }
    case "function":
    case "raw":
    case "unique":
    case "shared":
    case "weak":
    case "void":
      return false;
  }
}

export const CONTAINER_TYPES: ReadonlySet<string> = new Set(["vector", "set", "map", "deque", "list", "span"]);

const GENERIC_COMPARISONS: ReadonlySet<string> = new Set(["==", "!=", "<", ">", "<=", ">=", "in"]);

export const ORDERING_VARIANTS: ReadonlySet<string> = new Set(["Less", "Equal", "Greater"]);

// Tipos a los que se les puede pedir `T::try_from(x)` / `T::from(x)`.
export function is_conversion_target(name: string): boolean {
  return is_primitive_type(name) && name !== "void" && name !== "nullptr_t";
}

export function infer_primitive_conversion(
  ctx: CheckContext,
  target_name: string,
  operation: "try_from" | "from",
  args: readonly ArgNode[],
  span: Span,
): PenguType {
  const target = primitive(target_name);
  const result = operation === "try_from" ? optional(target) : target;
  const context = `${target_name}::${operation}`;

  if (args.length !== 1) {
    report_error(
      ctx,
      CODES.wrong_arity,
      `«${context}» espera 1 argumento, recibió ${args.length}`,
      span,
    );
    return result;
  }
  const arg = args[0];
  if (arg === undefined) return result;
  const source = infer_expr(ctx, arg.expr);
  if (is_any(source)) return result;

  const numeric =
    is_numeric(source) && is_numeric(target) && !is_name(source, "bool") && !is_name(target, "bool");
  const from_text = is_string(source) && is_numeric(target);
  if (!numeric && !from_text) {
    report_error(
      ctx,
      CODES.type_mismatch,
      `«${context}» no convierte «${type_display(source)}»`,
      span,
    );
  }
  return result;
}

