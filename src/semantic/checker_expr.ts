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
import { error as make_error } from "../diagnostics/diagnostic.ts";
import type { Span } from "../util/span.ts";
import { declare, lookup } from "./scopes.ts";
import type { CheckContext } from "./checker_context.ts";
import { symbol_type_of } from "./external.ts";
import {
  can_assign,
  expect_bool,
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
  function_type,
  is_any,
  is_float,
  is_integer,
  is_numeric,
  is_string,
  join_types,
  named,
  optional,
  ref_to,
  tuple_type,
  type_display,
  type_equals,
  types_equal,
} from "./types.ts";
import type { PenguType } from "./types.ts";
import type { OmenVariantInfo } from "./type_env.ts";
import { builtin_function, is_builtin_module } from "./builtin_modules.ts";
import { shared_type, unique_type, weak_type } from "./types.ts";
import { resolve_type_node } from "./type_env.ts";
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

export function infer_block(ctx: CheckContext, block: Block): PenguType {
  return with_new_scope(ctx, () => {
    let last: PenguType = VOID;
    for (const statement of block.statements) {
      last = check_statement(ctx, statement);
    }
    return last;
  });
}

function with_new_scope<T>(ctx: CheckContext, fn: () => T): T {
  const previous = ctx.scope;
  ctx.scope = { parent: previous, vars: new Map() };
  try {
    return fn();
  } finally {
    ctx.scope = previous;
  }
}

export function infer_expr(ctx: CheckContext, node: ExprNode): PenguType {
  const type = infer_expr_impl(ctx, node);
  ctx.types?.set(node, type);
  return type;
}

function infer_expr_impl(ctx: CheckContext, node: ExprNode): PenguType {
  switch (node.kind) {
    case "int_lit":
      return INT;
    case "float_lit":
      return FLOAT;
    case "bool_lit":
      return BOOL;
    case "char_lit":
      return CHAR;
    case "string_lit":
      // Las interpolaciones `#{...}` también deben analizarse.
      for (const part of node.parts) {
        if (part.kind === "expr_part") infer_expr(ctx, part.expr);
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
      return infer_path(ctx, node.segments, node.span);
    case "member":
      return infer_member(ctx, infer_expr(ctx, node.object), node.name, node.span);
    case "index": {
      const object = infer_expr(ctx, node.object);
      infer_expr(ctx, node.index);
      const result = builtin_index_result(object);
      if (result !== undefined) return result;
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
      const element = node.items.length > 0 ? infer_expr(ctx, node.items[0] as ExprNode) : UNKNOWN;
      for (const item of node.items) report_type_mismatch(ctx, element, infer_expr(ctx, item), item.span, "en el vector");
      return named("vector", [element]);
    }
    case "set_lit": {
      const element = node.items.length > 0 ? infer_expr(ctx, node.items[0] as ExprNode) : UNKNOWN;
      for (const item of node.items) report_type_mismatch(ctx, element, infer_expr(ctx, item), item.span, "en el conjunto");
      return named("set", [element]);
    }
    case "map_lit": {
      if (node.entries.length === 0) return named("map", [UNKNOWN, UNKNOWN]);
      const first = node.entries[0]!;
      const key = infer_expr(ctx, first.key);
      const value = infer_expr(ctx, first.value);
      for (const entry of node.entries) {
        report_type_mismatch(ctx, key, infer_expr(ctx, entry.key), entry.key.span, "en la clave del mapa");
        report_type_mismatch(ctx, value, infer_expr(ctx, entry.value), entry.value.span, "en el valor del mapa");
      }
      return named("map", [key, value]);
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

function with_loop<T>(ctx: CheckContext, fn: () => T, break_types?: PenguType[]): T {
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
function loop_result_type(break_types: readonly PenguType[]): PenguType {
  if (break_types.length === 0) return VOID;
  let joined: PenguType = break_types[0] ?? UNKNOWN;
  for (const type of break_types) joined = join_types(joined, type) ?? joined;
  return optional(joined);
}

function report_error(
  ctx: CheckContext,
  code: string,
  message: string,
  span: Span,
): void {
  ctx.sink.add(make_error(code, message, span));
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
  if (constant !== undefined) return constant.type;

  const fn = ctx.module.functions.get(name);
  if (fn !== undefined) {
    return function_type(
      fn.params.map((param) => param.type),
      fn.result,
    );
  }

  if (ctx.module.env.runes.has(name) || ctx.module.env.omens.has(name)) {
    return named(name);
  }

  // `invoke {a, b} from "mod"` importa los símbolos por su nombre.
  const selective = ctx.external?.selective.get(name);
  if (selective !== undefined) {
    const type = symbol_type_of(selective.module, selective.name);
    if (type !== undefined) return type;
  }

  report_error(ctx, CODES.unknown_identifier, `no existe «${name}» en este ámbito`, span);
  return UNKNOWN;
}

function infer_path(ctx: CheckContext, segments: readonly string[], span: Span): PenguType {
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

  if (segments.length === 2 && second !== undefined) {
    const omen = ctx.module.env.omens.get(first);
    if (omen !== undefined) {
      if (second === "try_from") return function_type([INT], optional(named(first)));
      if (second === "from") return function_type([INT], named(first));
      const variant = omen.variants.get(second);
      if (variant !== undefined) {
        if (variant.payload.length > 0) {
          return function_type(variant.payload, named(first));
        }
        return named(first);
      }
      report_error(ctx, CODES.unknown_identifier, `el omen «${first}» no tiene la variante «${second}»`, span);
      return UNKNOWN;
    }

    const rune = ctx.module.env.runes.get(first);
    if (rune !== undefined) {
      const method = rune.methods.get(second);
      if (method !== undefined) {
        return function_type(method.params, method.result);
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
    if (fn !== undefined) {
      return function_type(fn.params.map((param) => param.type), fn.result);
    }
    return any_type(`símbolo ${rest}`);
  }

  const imported = ctx.module.imports.get(first);
  if (imported !== undefined) {
    return any_type(`símbolo importado ${segments.join("::")}`);
  }

  if (ctx.module.env.omens.has(first) || ctx.module.env.runes.has(first)) {
    return named(first);
  }

  report_error(ctx, CODES.unknown_identifier, `no se reconoce «${segments.join("::")}»`, span);
  return UNKNOWN;
}

export function infer_member(
  ctx: CheckContext,
  object: PenguType,
  name: string,
  span: Span,
): PenguType {
  if (is_any(object)) return object;

  if (object.kind === "unique" || object.kind === "shared" || object.kind === "raw") {
    return infer_member(ctx, object.inner, name, span);
  }

  if (object.kind === "weak") {
    if (name === "lock") return function_type([], optional(shared_type(object.inner)));
  }

  if (object.kind === "named") {
    const rune = ctx.module.env.runes.get(object.name);
    if (rune !== undefined) {
      const field = rune.fields.get(name);
      if (field !== undefined) return field.type;
      const method = rune.methods.get(name);
      if (method !== undefined) {
        return function_type(method.params, method.result);
      }
      report_error(ctx, CODES.unknown_field, `el rune «${object.name}» no tiene «${name}»`, span);
      return UNKNOWN;
    }
    const alias = ctx.module.env.aliases.get(object.name);
    if (alias !== undefined && alias.seal) {
      const method = alias.methods.get(name);
      if (method !== undefined) return function_type(method.params, method.result);
    }
    const omen = ctx.module.env.omens.get(object.name);
    if (omen !== undefined && omen.is_flags && name === "has") {
      return function_type([named(object.name)], BOOL);
    }
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

function infer_call(ctx: CheckContext, node: CallNode): PenguType {
  // `ref(x)` es una construcción del lenguaje, no una función.
  if (node.callee.kind === "ident" && node.callee.name === "ref") {
    const first = node.args[0];
    if (first === undefined) return UNKNOWN;
    const inner = infer_expr(ctx, first.expr);
    if (first.mutable) {
      return ref_to(inner, true);
    }
    return ref_to(inner, false);
  }

  // Construcción de un rune, `seal` o `echo` por nombre.
  if (node.callee.kind === "ident") {
    const name = node.callee.name;
    const variant = find_omen_variant(ctx, name);
    if (variant !== undefined) {
      check_arguments(ctx, variant.variant.payload, node.args, node.span, name);
      return named(variant.omen);
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
      if (omen !== undefined) {
        if (second === "try_from" || second === "from") {
          check_arguments(ctx, [INT], node.args, node.span, `${first}::${second}`);
          return second === "try_from" ? optional(named(first)) : named(first);
        }
        const variant = omen.variants.get(second);
        if (variant !== undefined) {
          check_arguments(ctx, variant.payload, node.args, node.span, `${first}::${second}`);
          return named(first);
        }
      }
    }
  }

  const callee_type = infer_expr(ctx, node.callee);

  if (callee_type.kind === "function") {
    check_arguments(
      ctx,
      callee_type.params,
      node.args,
      node.span,
      describe_callee(node.callee),
      callee_type.variadic,
    );
    return callee_type.result;
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

function describe_callee(callee: ExprNode): string {
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
function find_omen_variant(
  ctx: CheckContext,
  name: string,
): { omen: string; variant: OmenVariantInfo } | undefined {
  for (const [omen_name, omen] of ctx.module.env.omens) {
    const variant = omen.variants.get(name);
    if (variant !== undefined) return { omen: omen_name, variant };
  }
  return undefined;
}

function infer_construction(
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

  const fields = [...rune.fields.values()].map((field) => field.type);
  check_arguments(ctx, fields, args, span, name);
  return named(name);
}

function check_arguments(
  ctx: CheckContext,
  params: readonly PenguType[],
  args: readonly ArgNode[],
  span: Span,
  name: string,
  variadic = false,
): void {
  if (variadic ? params.length > args.length : params.length !== args.length) {
    report_error(
      ctx,
      CODES.wrong_arity,
      `«${name}» espera ${params.length} argumento(s), recibió ${args.length}`,
      span,
    );
  }

  const total = variadic ? args.length : Math.min(params.length, args.length);
  for (let index = 0; index < total; index += 1) {
    const arg = args[index];
    if (arg === undefined) continue;
    const actual = infer_expr(ctx, arg.expr);
    const param = params[index];
    if (param === undefined) continue;
    if (!arg.mutable) mark_moved(ctx, arg.expr, param);
    if (!can_assign(param, actual)) {
      report_error(
        ctx,
        CODES.type_mismatch,
        `el argumento ${index + 1} de «${name}» espera «${type_display(param)}», recibió «${type_display(actual)}»`,
        arg.expr.span,
      );
    }
  }
}

// Marca el origen de un valor move-only como movido (`use after move`).
export function mark_moved(ctx: CheckContext, expr: ExprNode, target: PenguType): void {
  if (target.kind !== "unique") return;
  if (expr.kind !== "ident") return;
  const variable = lookup(ctx.scope, expr.name);
  if (variable !== undefined) variable.moved = true;
}

function infer_unary(
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

function infer_binary(
  ctx: CheckContext,
  operator: string,
  leftNode: ExprNode,
  rightNode: ExprNode,
  span: Span,
): PenguType {
  const left = infer_expr(ctx, leftNode);
  const right = infer_expr(ctx, rightNode);

  if (is_any(left) || is_any(right)) return any_type("operación");

  switch (operator) {
    case "and":
    case "or":
      expect_bool(ctx, left, leftNode.span, `el operando izquierdo de «${operator}»`);
      expect_bool(ctx, right, rightNode.span, `el operando derecho de «${operator}»`);
      return BOOL;
    case "==":
    case "!=":
      return BOOL;
    case "<":
    case ">":
    case "<=":
    case ">=":
      if (is_numeric(left) && is_numeric(right)) return BOOL;
      if (is_string(left) && is_string(right)) return BOOL;
      report_error(ctx, CODES.type_mismatch, `«${operator}» no compara «${type_display(left)}» con «${type_display(right)}»`, span);
      return BOOL;
    case "+":
      if (is_string(left) && is_string(right)) return STRING;
      if (is_numeric(left) && is_numeric(right)) return join_types(left, right) ?? left;
      break;
    case "-":
    case "*":
    case "/":
    case "%":
      if (is_numeric(left) && is_numeric(right)) return join_types(left, right) ?? left;
      break;
    case "&":
    case "|":
    case "^":
    case "<<":
    case ">>":
      if (is_integer(left) && is_integer(right)) return left;
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
    const method = rune?.methods.get(operator) ?? rune?.methods.get(`operator ${operator}`);
    if (method !== undefined) return method.result;
  }

  report_error(
    ctx,
    CODES.type_mismatch,
    `«${operator}» no está definido para «${type_display(left)}» y «${type_display(right)}»`,
    span,
  );
  return UNKNOWN;
}

function infer_cast(ctx: CheckContext, node: Extract<ExprNode, { kind: "cast" }>): PenguType {
  const source = infer_expr(ctx, node.value);
  const target = resolve_type_node(node.type, ctx.module.env, ctx.sink);

  if (is_any(source) || is_any(target)) return target;

  const safe = is_safe_cast(source, target);
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

export function is_safe_cast(source: PenguType, target: PenguType): boolean {
  if (type_equals(source, target)) return true;
  if (source.kind === "any" || target.kind === "any") return true;

  if (is_integer(source) && is_integer(target)) {
    return integer_width(target) >= integer_width(source) && !is_signed(target);
  }
  if (is_integer(source) && is_float(target)) return true;
  if (is_float(source) && is_float(target)) return true;

  // Desenvolver un seal es seguro.
  if (source.kind === "named" && target.kind === "primitive") return true;

  // Omen → tipo subyacente exacto.
  if (source.kind === "named" && target.kind === "primitive") return true;

  return false;
}

function integer_width(type: PenguType): number {
  if (type.kind !== "primitive") return 64;
  const name = type.name;
  if (name.includes("8")) return 8;
  if (name.includes("16")) return 16;
  if (name.includes("32")) return 32;
  if (name === "char" || name === "byte") return 8;
  if (name === "short") return 16;
  return 64;
}

function is_signed(type: PenguType): boolean {
  return !(type.kind === "primitive" && type.name.startsWith("u"));
}

function infer_if(ctx: CheckContext, node: Extract<ExprNode, { kind: "if" }>): PenguType {
  const condition = infer_expr(ctx, node.condition);
  expect_bool(ctx, condition, node.condition.span, "la condición del «if»");
  const then_type = infer_block(ctx, node.then_block);

  if (node.else_block === undefined) {
    if (then_type.kind === "void" || is_any(then_type)) return VOID;
    return optional(then_type);
  }

  const else_type = infer_block(ctx, node.else_block);
  const joined = join_types(then_type, else_type);
  if (joined === undefined) {
    report_error(
      ctx,
      CODES.type_mismatch,
      `las ramas del «if» tienen tipos distintos: «${type_display(then_type)}» y «${type_display(else_type)}»`,
      node.span,
    );
    return UNKNOWN;
  }
  return joined;
}

function infer_switch(ctx: CheckContext, node: Extract<ExprNode, { kind: "switch" }>): PenguType {
  const subject = infer_expr(ctx, node.subject);
  let result: PenguType | undefined;
  const arms = node.arms as readonly SwitchArm[];
  for (const arm of arms) {
    for (const pattern of arm.patterns) {
      const type = infer_expr(ctx, pattern);
      if (!can_assign(subject, type) && !type_equals(subject, type)) {
        report_type_mismatch(ctx, subject, type, pattern.span, "en un «when» del switch");
      }
    }
    const body = infer_block(ctx, arm.body);
    result = result === undefined ? body : join_types(result, body) ?? any_type("ramas");
  }

  if (node.else_block !== undefined) {
    const else_type = infer_block(ctx, node.else_block);
    result = result === undefined ? else_type : join_types(result, else_type) ?? any_type("ramas");
    return result;
  }

  if (result === undefined) return VOID;
  if (result.kind === "void" || is_any(result)) return VOID;
  return optional(result);
}

function infer_match(ctx: CheckContext, node: Extract<ExprNode, { kind: "match" }>): PenguType {
  const subject = infer_expr(ctx, node.subject);
  const omen = subject.kind === "named" ? ctx.module.env.omens.get(subject.name) : undefined;
  if (subject.kind === "named" && omen === undefined) {
    report_error(ctx, CODES.type_mismatch, `«match» solo admite omens, se recibió «${type_display(subject)}»`, node.span);
    return UNKNOWN;
  }

  let result: PenguType | undefined;
  const covered = new Set<string>();
  let catch_all = false;

  for (const arm of node.arms as readonly MatchArm[]) {
    if (arm.guard === undefined) {
      if (arm.pattern.kind === "wildcard_pattern" || arm.pattern.kind === "binding_pattern") {
        catch_all = true;
      }
      if (arm.pattern.kind === "variant_pattern") covered.add(arm.pattern.path[arm.pattern.path.length - 1] ?? "");
    }
    const body = with_pattern_scope(ctx, () => {
      bind_pattern(ctx, arm.pattern, subject, omen);
      return infer_block(ctx, arm.body);
    });
    result = result === undefined ? body : join_types(result, body) ?? any_type("ramas");
  }

  if (omen !== undefined && !catch_all) {
    const missing = [...omen.variants.keys()].filter((name) => !covered.has(name));
    if (missing.length > 0) {
      ctx.sink.add(
        make_error(
          CODES.omen_not_exhaustive,
          `faltan variantes en el «match»: ${missing.join(", ")}`,
          node.span,
        ),
      );
    }
  }

  return result ?? VOID;
}

function with_pattern_scope<T>(ctx: CheckContext, fn: () => T): T {
  const previous = ctx.scope;
  ctx.scope = { parent: previous, vars: new Map() };
  try {
    return fn();
  } finally {
    ctx.scope = previous;
  }
}

function bind_pattern(
  ctx: CheckContext,
  pattern: PatternNode,
  subject: PenguType,
  omen: OmenInfo | undefined,
): void {
  switch (pattern.kind) {
    case "wildcard_pattern":
      return;
    case "literal_pattern":
      return;
    case "binding_pattern":
      declare(ctx.scope, pattern.name, subject, {
        mutable: pattern.mutable,
        kind: "local",
        span: pattern.span,
      });
      return;
    case "tuple_pattern": {
      const items = subject.kind === "tuple" ? subject.items : [];
      pattern.items.forEach((item, index) => {
        bind_pattern(ctx, item, items[index] ?? UNKNOWN, omen);
      });
      return;
    }
    case "variant_pattern": {
      const variant = omen?.variants.get(pattern.path[pattern.path.length - 1] ?? "");
      if (variant === undefined) {
        if (omen !== undefined) {
          report_error(
            ctx,
            CODES.unknown_identifier,
            `variante desconocida en el «match»: ${pattern.path.join("::")}`,
            pattern.span,
          );
        }
        return;
      }
      pattern.args.forEach((arg, index) => {
        bind_pattern(ctx, arg, variant.payload[index] ?? UNKNOWN, omen);
      });
      if (pattern.args.length !== variant.payload.length) {
        report_error(
          ctx,
          CODES.wrong_arity,
          `la variante espera ${variant.payload.length} dato(s), recibió ${pattern.args.length}`,
          pattern.span,
        );
      }
      return;
    }
  }
}

function infer_comprehension(
  ctx: CheckContext,
  container: "vector" | "map" | "set",
  body: ExprNode,
  key: ExprNode | undefined,
  clauses: readonly ForClauseNode[],
): PenguType {
  return with_new_scope(ctx, () => {
    for (const clause of clauses) {
      const iterable = infer_expr(ctx, clause.iterable);
      const [first, second] = clause.variables;
      if (first === undefined) continue;
      const element = element_of_iterable(iterable);
      if (second !== undefined) {
        const index = INT;
        declare(ctx.scope, first, index, { mutable: clause.mutable, kind: "local", span: clause.span });
        declare(ctx.scope, second, element, { mutable: clause.mutable, kind: "local", span: clause.span });
      } else {
        declare(ctx.scope, first, element, { mutable: clause.mutable, kind: "local", span: clause.span });
      }
      if (clause.condition !== undefined) {
        expect_bool(ctx, infer_expr(ctx, clause.condition), clause.condition.span, "el filtro de la comprensión");
      }
    }

    const value = infer_expr(ctx, body);
    if (container === "map") {
      const key_type = key === undefined ? UNKNOWN : infer_expr(ctx, key);
      return named("map", [key_type, value]);
    }
    return named(container, [value]);
  });
}

function element_of_iterable(type: PenguType): PenguType {
  if (is_any(type)) return type;
  if (type.kind === "range") return type.element;
  if (is_string_type(type)) return CHAR;
  if (is_map_type(type)) {
    const pair = map_key_value(type);
    if (pair !== undefined) return tuple_type([pair.key, pair.value]);
    return UNKNOWN;
  }
  const element = sequence_element(type);
  if (element !== undefined) return element;
  if (is_set_type(type) && type.kind === "named") return type.args[0] ?? UNKNOWN;
  return UNKNOWN;
}

function infer_for_numeric(
  ctx: CheckContext,
  node: Extract<ExprNode, { kind: "for_numeric" }>,
): PenguType {
  const start = infer_expr(ctx, node.start);
  const end = infer_expr(ctx, node.end);
  if (node.step !== undefined) {
    infer_expr(ctx, node.step);
  }
  if (!is_any(start) && !is_numeric(start)) {
    report_error(ctx, CODES.type_mismatch, "el inicio del «for» debe ser numérico", node.start.span);
  }
  if (!is_any(end) && !is_numeric(end)) {
    report_error(ctx, CODES.type_mismatch, "el fin del «for» debe ser numérico", node.end.span);
  }
  const variable_type = node.variable_type === undefined
    ? INT
    : resolve_type_node(node.variable_type, ctx.module.env, ctx.sink);

  return with_new_scope(ctx, () => {
    declare(ctx.scope, node.variable, variable_type, {
      mutable: node.mutable,
      kind: "local",
      span: node.span,
    });
    const break_types: PenguType[] = [];
    with_loop(ctx, () => infer_block(ctx, node.body), break_types);
    if (node.else_block !== undefined) infer_block(ctx, node.else_block);
    return VOID;
  });
}

function infer_for_iter(
  ctx: CheckContext,
  node: Extract<ExprNode, { kind: "for_iter" }>,
): PenguType {
  const iterable = infer_expr(ctx, node.iterable);
  const element = element_of_iterable(iterable);

  return with_new_scope(ctx, () => {
    const [first, second] = node.variables;
    if (first === undefined) return VOID;
    if (second !== undefined) {
      const indexed = is_map_type(iterable) ? INT : INT;
      declare(ctx.scope, first, indexed, { mutable: false, kind: "local", span: node.span });
      declare(ctx.scope, second, element, { mutable: node.mutable, kind: "local", span: node.span });
    } else {
      declare(ctx.scope, first, element, { mutable: node.mutable, kind: "local", span: node.span });
    }
    const break_types: PenguType[] = [];
    with_loop(ctx, () => infer_block(ctx, node.body), break_types);
    if (node.else_block !== undefined) infer_block(ctx, node.else_block);
    return loop_result_type(break_types);
  });
}

function infer_lambda(ctx: CheckContext, node: LambdaNode): PenguType {
  const params = node.params.map((param) =>
    param.type === undefined ? UNKNOWN : resolve_type_node(param.type, ctx.module.env, ctx.sink),
  );
  const declared_result = node.result === undefined
    ? undefined
    : resolve_type_node(node.result, ctx.module.env, ctx.sink);

  const previous_return = ctx.current_return;
  ctx.current_return = declared_result;
  try {
    const body = with_new_scope(ctx, () => {
      node.params.forEach((param, index) => {
        declare(ctx.scope, param.name, params[index] ?? UNKNOWN, {
          mutable: param.mutable,
          kind: "param",
          span: param.span,
        });
      });
      return infer_block(ctx, node.body);
    });

    const result = declared_result ?? body;
    if (declared_result !== undefined && !type_equals(declared_result, body)) {
      report_type_mismatch(ctx, declared_result, body, node.span, "como valor de retorno de la lambda");
    }
    return function_type(params, result);
  } finally {
    ctx.current_return = previous_return;
  }
}

// Reexportado para que el checker de declaraciones use el mismo
// criterio al comprobar cuerpos.
export { is_any, types_equal };
