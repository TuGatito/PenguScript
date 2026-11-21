// Inferencia de las expresiones de control: `if`, `unless`, `switch`,
// `match`, `do`, bucles, comprensiones y funciones literales.

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
import { param_binding_type, root_ident } from "./checker_call.ts";
import { is_display } from "./checker_ops.ts";

export function infer_if(ctx: CheckContext, node: Extract<ExprNode, { kind: "if" }>): PenguType {
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

export function infer_switch(ctx: CheckContext, node: Extract<ExprNode, { kind: "switch" }>): PenguType {
  const subject = infer_expr(ctx, node.subject);
  let result: PenguType | undefined;
  const arms = node.arms as readonly SwitchArm[];
  const omen = subject.kind === "named" ? ctx.module.env.omens.get(subject.name) : undefined;
  const covered = new Set<string>();

  for (const arm of arms) {
    for (const pattern of arm.patterns) {
      // `when Rojo` nombra una variante directamente, sin `Color::`.
      const bare_variant =
        pattern.kind === "ident" && omen?.variants.has(pattern.name) ? pattern.name : undefined;
      const type = bare_variant !== undefined ? subject : infer_expr(ctx, pattern);
      if (pattern.kind === "path") {
        covered.add(pattern.segments[pattern.segments.length - 1] ?? "");
      } else if (bare_variant !== undefined) {
        covered.add(bare_variant);
      }
      if (!can_assign(subject, type, ctx.module.env) && !type_equals(subject, type)) {
        check_initialization(ctx, subject, type, pattern.span, "en un «when» del switch", pattern);
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

  // Un `switch` sin `else` sobre un omen de variantes unitarias avisa
  // si deja variantes sin cubrir (un `match` sería más seguro).
  if (omen !== undefined && !omen.is_flags) {
    const unit_like = [...omen.variants.values()].every((variant) => variant.payload.length === 0);
    const missing = [...omen.variants.keys()].filter((name) => !covered.has(name));
    if (unit_like && missing.length > 0) {
      ctx.sink.add(
        make_warning(
          CODES.omen_not_exhaustive,
          `el «switch» no cubre ${missing.map((name) => `«${name}»`).join(", ")}; añade esas variantes o un «else»`,
          node.span,
        ),
      );
    }
  }

  if (result === undefined) return VOID;
  if (result.kind === "void" || is_any(result)) return VOID;
  return optional(result);
}

export function infer_match(ctx: CheckContext, node: Extract<ExprNode, { kind: "match" }>): PenguType {
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
      bind_pattern(ctx, arm.pattern, subject, omen, match_mapping(subject, omen));
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

export function with_pattern_scope<T>(ctx: CheckContext, fn: () => T): T {
  const previous = ctx.scope;
  ctx.scope = { parent: previous, vars: new Map() };
  try {
    return fn();
  } finally {
    ctx.scope = previous;
  }
}

// Los datos de una variante pueden ser genéricos: se sustituyen por
// los argumentos reales del sujeto (`Resultado<int>` → `T` = int).
export function match_mapping(subject: PenguType, omen: OmenInfo | undefined): ReadonlyMap<string, PenguType> {
  if (omen === undefined || subject.kind !== "named" || subject.args.length === 0) return new Map();
  const mapping = new Map<string, PenguType>();
  omen.sigils.forEach((sigil, index) => mapping.set(sigil, subject.args[index] ?? UNKNOWN));
  return mapping;
}

export function bind_pattern(
  ctx: CheckContext,
  pattern: PatternNode,
  subject: PenguType,
  omen: OmenInfo | undefined,
  mapping: ReadonlyMap<string, PenguType> = new Map(),
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
        bind_pattern(ctx, item, items[index] ?? UNKNOWN, omen, mapping);
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
        bind_pattern(ctx, arg, substitute_generics(variant.payload[index] ?? UNKNOWN, mapping), omen, mapping);
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

export function infer_comprehension(
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

export function element_of_iterable(type: PenguType): PenguType {
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

export function infer_for_numeric(
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

export function infer_for_iter(
  ctx: CheckContext,
  node: Extract<ExprNode, { kind: "for_iter" }>,
): PenguType {
  const iterable = infer_expr(ctx, node.iterable);
  const element = element_of_iterable(iterable);

  return with_new_scope(ctx, () => {
    const [first, second] = node.variables;
    if (first === undefined) return VOID;
    // Mientras dure el bucle no se puede mutar el contenedor.
    const root = root_ident(node.iterable);
    if (root !== undefined) ctx.iterating.push({ name: root.name, span: node.span });
    if (second !== undefined) {
      const indexed = is_map_type(iterable) ? INT : INT;
      declare(ctx.scope, first, indexed, { mutable: false, kind: "local", span: node.span });
      declare(ctx.scope, second, element, { mutable: node.mutable, kind: "local", span: node.span });
    } else {
      declare(ctx.scope, first, element, { mutable: node.mutable, kind: "local", span: node.span });
    }
    const break_types: PenguType[] = [];
    try {
      with_loop(ctx, () => infer_block(ctx, node.body), break_types);
      if (node.else_block !== undefined) infer_block(ctx, node.else_block);
    } finally {
      if (root !== undefined) {
        const index = ctx.iterating.findIndex((item) => item.name === root.name && item.span === node.span);
        if (index >= 0) ctx.iterating.splice(index, 1);
      }
    }
    return loop_result_type(break_types);
  });
}

export function infer_lambda(ctx: CheckContext, node: LambdaNode): PenguType {
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
        declare(ctx.scope, param.name, param_binding_type(param, params[index] ?? UNKNOWN), {
          mutable: param.mutable,
          kind: "param",
          span: param.span,
        });
      });
      return infer_block(ctx, node.body);
    });

    const variadic = node.params.some((param) => param.variadic);
    const required = node.params.filter(
      (param) => param.default_value === undefined && !param.variadic,
    ).length;
    const result = declared_result ?? body;
    if (declared_result !== undefined) {
      check_initialization(ctx, declared_result, body, node.span, "como valor de retorno de la lambda");
    }
    return function_type(params, result, variadic, required);
  } finally {
    ctx.current_return = previous_return;
  }
}

// Reexportado para que el checker de declaraciones use el mismo
// criterio al comprobar cuerpos.
export { is_any, types_equal };

// ¿El tipo puede aparecer dentro de una interpolación `"#{...}"`?
// Los tipos nativos y los contenedores de tipos Display lo son; un
// `rune` necesita declarar `to_string` en un bloque `enchanting`.
