// Inferencia de tipos para expresiones.
//
// Cada función devuelve el tipo de la expresión y emite diagnósticos
// cuando algo no encaja. Los errores devuelven `any` para no generar
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
  with_block_span,
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
import { infer_call, infer_construction, infer_declared, literal_element } from "./checker_call.ts";
import { infer_member, infer_path, rune_operator_method } from "./checker_member.ts";
import { infer_binary, infer_cast, infer_unary, is_display } from "./checker_ops.ts";
import {
  infer_comprehension,
  infer_for_iter,
  infer_for_numeric,
  infer_if,
  infer_lambda,
  infer_match,
  infer_switch,
} from "./checker_control.ts";

export function infer_block(ctx: CheckContext, block: Block): PenguType {
  return with_block_span(ctx, block.span, () => with_new_scope(ctx, () => {
    let last: PenguType = VOID;
    for (const statement of block.statements) {
      last = check_statement(ctx, statement);
    }
    return last;
  }));
}

export function with_new_scope<T>(ctx: CheckContext, fn: () => T): T {
  // `with_scope` lleva la profundidad y libera los préstamos del ámbito.
  return with_scope(ctx, () => fn());
}

export function infer_expr(ctx: CheckContext, node: ExprNode): PenguType {
  const type = infer_expr_impl(ctx, node);
  ctx.types?.set(node, type);
  return type;
}

function infer_expr_impl(ctx: CheckContext, node: ExprNode): PenguType {
  switch (node.kind) {
    case "container_new": {
      const args = node.type_args.map((arg) => resolve_type_node(arg, ctx.module.env, ctx.sink));
      for (const arg of node.args) infer_expr(ctx, arg.expr);
      if (STRING_TYPES.has(node.name) && node.type_args.length === 0) return primitive(node.name);
      if (node.name === "bitset") {
        if (node.size !== undefined) {
          const size = infer_expr(ctx, node.size);
          check_initialization(ctx, INT, size, node.size.span, "en el tamaño del bitset", node.size);
        }
        return named("bitset", [INT]);
      }
      return named(node.name, args);
    }
    case "int_lit":
      return INT;
    case "float_lit":
      return FLOAT;
    case "bool_lit":
      return BOOL;
    case "char_lit":
      return CHAR;
    case "string_lit":
      // Las interpolaciones `#{...}` también deben analizarse y su
      // valor tiene que implementar `Display`.
      for (const part of node.parts) {
        if (part.kind !== "expr_part") continue;
        const part_type = infer_expr(ctx, part.expr);
        if (!is_display(ctx, part_type)) {
          report_error(
            ctx,
            CODES.not_display,
            `«${type_display(part_type)}» no se puede interpolar: no implementa «Display»`,
            part.expr.span,
            ctx.module.env.runes.has(type_display(part_type))
              ? [`añade «enchanting ${type_display(part_type)}» con «to_string = -> string»`]
              : [],
          );
        }
      }
      return STRING;
    case "none_lit":
      return NONE;
    case "nullptr_lit":
      return NULLPTR;
    case "ident":
      return infer_ident(ctx, node.name, node.span);
    case "self":
      if (ctx.self_type === undefined) {
        report_error(ctx, CODES.unknown_identifier, "«@» solo puede usarse dentro de un rune", node.span);
        return UNKNOWN;
      }
      return ctx.self_type;
    case "parent_call":
      return any_type("llamada a parent");
    case "path":
      return infer_path(ctx, node.segments, node.span, node.type_args);
    case "member":
      return infer_member(ctx, infer_expr(ctx, node.object), node.name, node.span, node);
    case "index": {
      const object = infer_expr(ctx, node.object);
      infer_expr(ctx, node.index);
      const result = builtin_index_result(object);
      if (result !== undefined) return result;
      const user_index = rune_operator_method(ctx, object, "[]");
      if (user_index !== undefined) return user_index;
      if (node.object.kind === "member" && node.object.name === "map") return any_type("elemento");
      if (is_any(object)) return object;
      report_error(
        ctx,
        CODES.cannot_infer,
        `no se puede indexar un valor de tipo «${type_display(object)}»`,
        node.span,
      );
      return UNKNOWN;
    }
    case "call":
      return infer_call(ctx, node);
    case "unary":
      return infer_unary(ctx, node.op, node.operand, node.span);
    case "binary":
      return infer_binary(ctx, node.op, node.left, node.right, node.span);
    case "cast":
      return infer_cast(ctx, node);
    case "range": {
      const start = infer_expr(ctx, node.start);
      const end = infer_expr(ctx, node.end);
      if (is_float(start) || is_float(end)) return { kind: "range", element: FLOAT };
      return { kind: "range", element: INT };
    }
    case "tuple":
      return tuple_type(node.items.map((item) => infer_expr(ctx, item)));
    case "vector_lit": {
      const declared = infer_declared(ctx, node.declared_type);
      const element = literal_element(declared);
      if (declared !== undefined && declared.kind === "array" && node.items.length !== declared.size) {
        report_error(
          ctx,
          CODES.type_mismatch,
          `el literal tiene ${node.items.length} elemento(s) y «${type_display(declared)}» espera ${declared.size}`,
          node.span,
        );
      }
      const first_type = element ?? (node.items.length > 0 ? infer_expr(ctx, node.items[0] as ExprNode) : UNKNOWN);
      for (const item of node.items) {
        check_initialization(ctx, first_type, infer_expr(ctx, item), item.span, "en el vector", item);
      }
      return declared ?? named("vector", [first_type]);
    }
    case "set_lit": {
      const declared = infer_declared(ctx, node.declared_type);
      const element = literal_element(declared);
      const first_type = element ?? (node.items.length > 0 ? infer_expr(ctx, node.items[0] as ExprNode) : UNKNOWN);
      for (const item of node.items) {
        check_initialization(ctx, first_type, infer_expr(ctx, item), item.span, "en el conjunto", item);
      }
      return declared ?? named("set", [first_type]);
    }
    case "map_lit": {
      const declared = infer_declared(ctx, node.declared_type);
      const declared_key = declared?.kind === "named" ? declared.args[0] : undefined;
      const declared_value = declared?.kind === "named" ? declared.args[1] : undefined;
      if (node.entries.length === 0) {
        return declared ?? named("map", [declared_key ?? UNKNOWN, declared_value ?? UNKNOWN]);
      }
      const first = node.entries[0]!;
      const key = declared_key ?? infer_expr(ctx, first.key);
      const value = declared_value ?? infer_expr(ctx, first.value);
      for (const entry of node.entries) {
        check_initialization(ctx, key, infer_expr(ctx, entry.key), entry.key.span, "en la clave del mapa", entry.key);
        check_initialization(ctx, value, infer_expr(ctx, entry.value), entry.value.span, "en el valor del mapa", entry.value);
      }
      return declared ?? named("map", [key, value]);
    }
    case "comprehension":
      return infer_comprehension(ctx, node.container, node.body, node.key, node.clauses);
    case "if":
      return infer_if(ctx, node);
    case "switch":
      return infer_switch(ctx, node);
    case "match":
      return infer_match(ctx, node);
    case "do":
      return infer_block(ctx, node.block);
    case "while":
    case "repeat": {
      const condition = node.kind === "while" ? node.condition : node.condition;
      expect_bool(ctx, infer_expr(ctx, condition), condition.span, "la condición del bucle");
      const break_types: PenguType[] = [];
      with_loop(ctx, () => infer_block(ctx, node.body), break_types);
      return loop_result_type(break_types);
    }
    case "for_numeric":
      return infer_for_numeric(ctx, node);
    case "for_iter":
      return infer_for_iter(ctx, node);
    case "lambda":
      return infer_lambda(ctx, node);
    case "unsafe":
      ctx.unsafe_depth += 1;
      try {
        return infer_block(ctx, node.block);
      } finally {
        ctx.unsafe_depth -= 1;
      }
  }
}

export function with_loop<T>(ctx: CheckContext, fn: () => T, break_types?: PenguType[]): T {
  ctx.loop_depth += 1;
  if (break_types !== undefined) ctx.break_types.push(break_types);
  try {
    return fn();
  } finally {
    if (break_types !== undefined) ctx.break_types.pop();
    ctx.loop_depth -= 1;
  }
}

// Une los tipos de todos los `break value` de un bucle en un `T?`.
export function loop_result_type(break_types: readonly PenguType[]): PenguType {
  if (break_types.length === 0) return VOID;
  let joined: PenguType = break_types[0] ?? UNKNOWN;
  for (const type of break_types) joined = join_types(joined, type) ?? joined;
  return optional(joined);
}

export function report_error(
  ctx: CheckContext,
  code: string,
  message: string,
  span: Span,
  notes: readonly string[] = [],
): void {
  ctx.sink.add(make_error(code, message, span, ...notes));
}

function infer_ident(ctx: CheckContext, name: string, span: Span): PenguType {
  const variable = lookup(ctx.scope, name);
  if (variable !== undefined) {
    if (variable.moved) {
      report_error(ctx, CODES.use_after_move, `«${name}» se usó después de moverse`, span);
    }
    return variable.type;
  }

  const constant = ctx.module.consts.get(name);
  if (constant !== undefined) {
    // `static mut` solo se toca desde `unsafe`.
    if (constant.is_static && constant.mutable && ctx.unsafe_depth === 0) {
      report_error(
        ctx,
        CODES.unsafe_required,
        `«${name}» es «static mut»: su acceso requiere «unsafe»`,
        span,
      );
    }
    return constant.type;
  }

  const fn = ctx.module.functions.get(name);
  if (fn !== undefined) return function_type_of(fn);

  if (ctx.module.env.runes.has(name) || ctx.module.env.omens.has(name)) {
    return named(name);
  }

  // `invoke {a, b} from "mod"` importa los símbolos por su nombre.
  const selective = ctx.external?.selective.get(name);
  if (selective !== undefined) {
    const type = symbol_type_of(selective.module, selective.name);
    if (type !== undefined) return type;
  }

  const suggestion = suggest_name(name, known_names(ctx));
  const hint = suggestion === undefined ? "" : `; ¿quisiste decir «${suggestion}»?`;
  report_error(ctx, CODES.unknown_identifier, `no existe «${name}» en este ámbito${hint}`, span);
  return UNKNOWN;
}

// Nombres visibles en el ámbito: se usan para sugerir alternativas.
export function known_names(ctx: CheckContext): string[] {
  const names: string[] = [];
  let scope: typeof ctx.scope | undefined = ctx.scope;
  while (scope !== undefined) {
    names.push(...scope.vars.keys());
    scope = scope.parent;
  }
  names.push(...ctx.module.functions.keys());
  names.push(...ctx.module.consts.keys());
  names.push(...ctx.module.env.runes.keys());
  names.push(...ctx.module.env.omens.keys());
  names.push(...ctx.module.env.aliases.keys());
  return names;
}


// Las piezas viven en módulos aparte; se reexportan para que el resto
// del checker siga importando desde aquí.
export { check_arguments, infer_construction, param_binding_type, root_ident, mark_moved } from "./checker_call.ts";
export { infer_member, infer_path, rune_operator_method } from "./checker_member.ts";
export { infer_unary, infer_binary, infer_cast, is_safe_cast, is_display, is_conversion_target } from "./checker_ops.ts";
export { infer_if, infer_switch, infer_match, infer_comprehension, infer_for_numeric, infer_for_iter, infer_lambda } from "./checker_control.ts";