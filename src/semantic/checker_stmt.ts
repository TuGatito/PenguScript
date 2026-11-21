// Comprobación de sentencias.
//
// Las sentencias no producen valor, salvo una expresión final en un
// bloque; por eso `check_statement` devuelve el tipo de la expresión
// cuando la sentencia lo es.

import type { AssignStmtNode, Block, StmtNode } from "../frontend/ast.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import { CODES } from "../diagnostics/codes.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import type { Span } from "../util/span.ts";
import type { CheckContext } from "./checker_context.ts";
import { can_assign, report_type_mismatch } from "./checker_context.ts";
import { declare, lookup } from "./scopes.ts";
import { infer_expr, mark_moved } from "./checker_expr.ts";
import {
  UNKNOWN,
  VOID,
  is_any,
  is_numeric,
  is_string,
  type_display,
} from "./types.ts";
import type { PenguType } from "./types.ts";
import { resolve_type_node } from "./type_env.ts";
import { builtin_index_result, member_of_builtin } from "./builtin_members.ts";

export function check_statement(ctx: CheckContext, statement: StmtNode): PenguType {
  switch (statement.kind) {
    case "expr_stmt":
      return infer_expr(ctx, statement.expr);
    case "assign":
      return check_assign(ctx, statement);
    case "const_stmt": {
      const value = infer_expr(ctx, statement.value);
      const type = statement.declared_type === undefined
        ? value
        : resolve_type_node(statement.declared_type, ctx.module.env, ctx.sink);
      if (statement.declared_type !== undefined) {
        report_type_mismatch(ctx, type, value, statement.value.span, "en la constante");
      }
      if (declare(ctx.scope, statement.name, type, {
        mutable: false,
        kind: "const",
        span: statement.span,
      }) === undefined) {
        report_error(ctx, CODES.duplicate_symbol, `«${statement.name}» ya está declarado`, statement.span);
      }
      return VOID;
    }
    case "return":
      return check_return(ctx, statement.value, statement.span);
    case "break": {
      if (ctx.loop_depth === 0) {
        ctx.sink.add(
          make_error(CODES.invalid_assignment, "«break» solo puede usarse dentro de un bucle", statement.span),
        );
      }
      if (statement.value !== undefined) {
        const value = infer_expr(ctx, statement.value);
        const current = ctx.break_types[ctx.break_types.length - 1];
        if (current !== undefined) current.push(value);
      }
      return VOID;
    }
    case "continue":
      if (ctx.loop_depth === 0) {
        ctx.sink.add(
          make_error(CODES.invalid_assignment, "«continue» solo puede usarse dentro de un bucle", statement.span),
        );
      }
      return VOID;
    case "pass":
      return VOID;
  }
}

function report_error(
  ctx: CheckContext,
  code: string,
  message: string,
  span: Span,
): void {
  ctx.sink.add(make_error(code, message, span));
}

function check_assign(ctx: CheckContext, node: AssignStmtNode): PenguType {
  const value = infer_expr(ctx, node.value);
  if (node.op === "=") mark_moved(ctx, node.value, value);

  // `x: T = v` declara la variable además de asignarla.
  if (node.declared_type !== undefined && node.targets.length === 1) {
    const declared = resolve_type_node(node.declared_type, ctx.module.env, ctx.sink);
    report_type_mismatch(ctx, declared, value, node.value.span, "en la inicialización");
    const target = node.targets[0];
    if (target !== undefined && target.kind === "ident") {
      if (declare(ctx.scope, target.name, declared, {
        mutable: node.mutable,
        kind: "local",
        span: node.span,
      }) === undefined) {
        report_error(ctx, CODES.duplicate_symbol, `«${target.name}» ya está declarado`, node.span);
      }
      ctx.types?.set(target, declared);
      return VOID;
    }
  }

  if (node.targets.length > 1) {
    const items = value.kind === "tuple" ? value.items : undefined;
    if (items === undefined || items.length !== node.targets.length) {
      report_error(
        ctx,
        CODES.type_mismatch,
        `se esperaban ${node.targets.length} valores para las variables, se recibió «${type_display(value)}»`,
        node.value.span,
      );
      return VOID;
    }
    node.targets.forEach((target, index) => {
      assign_target(ctx, target, items[index] ?? UNKNOWN, node, true);
    });
    return VOID;
  }

  const target = node.targets[0];
  if (target === undefined) return VOID;
  const expected = target_type(ctx, target);
  if (node.op === "=") {
    assign_target(ctx, target, value, node, true);
    return VOID;
  }

  // Asignación compuesta: el valor debe operar con el tipo actual.
  if (!is_any(expected) && !is_any(value)) {
    const binary = node.op.slice(0, -1);
    const valid =
      (binary === "+" && (is_numeric(expected) || is_string(expected))) ||
      (binary !== "+" && is_numeric(expected)) ||
      (binary === "&" || binary === "|" || binary === "^" || binary === "<<" || binary === ">>");
    if (!valid) {
      report_error(
        ctx,
        CODES.type_mismatch,
        `«${node.op}» no está definido para «${type_display(expected)}»`,
        node.span,
      );
    }
  }
  assign_target(ctx, target, expected, node, false);
  return VOID;
}

function assign_target(
  ctx: CheckContext,
  target: ExprNode,
  value: PenguType,
  node: AssignStmtNode,
  declare_new: boolean,
): void {
  switch (target.kind) {
    case "ident": {
      const variable = lookup(ctx.scope, target.name);
      if (variable === undefined) {
        if (declare_new) {
          // `x = v` y `mut x = v` declaran la variable.
          declare(ctx.scope, target.name, value, {
            mutable: node.mutable,
            kind: "local",
            span: target.span,
          });
          ctx.types?.set(target, value);
          return;
        }
        report_error(ctx, CODES.unknown_identifier, `no existe «${target.name}» en este ámbito`, target.span);
        return;
      }
      if (!variable.mutable) {
        report_error(
          ctx,
          CODES.mutable_required,
          `«${target.name}» es inmutable; decláralo con «mut»`,
          target.span,
        );
        return;
      }
      if (!can_assign(variable.type, value)) {
        report_type_mismatch(ctx, variable.type, value, node.value.span, `al asignar a «${target.name}»`);
      }
      return;
    }
    case "member": {
      const object = infer_expr(ctx, target.object);
      const expected = member_of_builtin(object, target.name);
      if (expected === undefined) {
        const rune = object.kind === "named" ? ctx.module.env.runes.get(object.name) : undefined;
        const field = rune?.fields.get(target.name);
        if (field === undefined) {
          report_error(
            ctx,
            CODES.unknown_field,
            `«${type_display(object)}» no tiene el campo «${target.name}»`,
            target.span,
          );
          return;
        }
        if (!can_assign(field.type, value)) {
          report_type_mismatch(ctx, field.type, value, node.value.span, `al asignar a «${target.name}»`);
        }
        return;
      }
      if (!can_assign(expected, value)) {
        report_type_mismatch(ctx, expected, value, node.value.span, `al asignar a «${target.name}»`);
      }
      return;
    }
    case "index": {
      const object = infer_expr(ctx, target.object);
      infer_expr(ctx, target.index);
      const expected = builtin_index_result(object);
      if (expected === undefined) {
        report_error(
          ctx,
          CODES.cannot_infer,
          `no se puede indexar un valor de tipo «${type_display(object)}»`,
          target.span,
        );
        return;
      }
      if (!can_assign(expected, value)) {
        report_type_mismatch(ctx, expected, value, node.value.span, "al asignar al índice");
      }
      return;
    }
    default:
      report_error(ctx, CODES.invalid_assignment, "el destino de la asignación no es asignable", target.span);
  }
}

function target_type(ctx: CheckContext, target: ExprNode): PenguType {
  switch (target.kind) {
    case "ident": {
      const variable = lookup(ctx.scope, target.name);
      return variable?.type ?? UNKNOWN;
    }
    case "member":
      return member_of_builtin(infer_expr(ctx, target.object), target.name) ?? UNKNOWN;
    case "index":
      return builtin_index_result(infer_expr(ctx, target.object)) ?? UNKNOWN;
    default:
      return UNKNOWN;
  }
}

function check_return(
  ctx: CheckContext,
  valueNode: ExprNode | undefined,
  span: Span,
): PenguType {
  if (ctx.current_return === undefined) {
    report_error(ctx, CODES.missing_return, "«return» fuera de una función", span);
    return VOID;
  }

  if (valueNode === undefined) {
    if (ctx.current_return.kind !== "void" && !is_any(ctx.current_return)) {
      report_error(
        ctx,
        CODES.missing_return,
        `la función debe devolver «${type_display(ctx.current_return)}»`,
        span,
      );
    }
    return VOID;
  }

  const value = infer_expr(ctx, valueNode);
  if (ctx.current_return.kind === "void") {
    report_error(ctx, CODES.type_mismatch, "una función «void» no devuelve valor", valueNode.span);
    return VOID;
  }
  report_type_mismatch(ctx, ctx.current_return, value, valueNode.span, "como valor de retorno");
  return VOID;
}

export function check_block(ctx: CheckContext, block: Block): PenguType {
  const previous = ctx.scope;
  ctx.scope = { parent: previous, vars: new Map() };
  try {
    let last: PenguType = VOID;
    for (const statement of block.statements) {
      last = check_statement(ctx, statement);
      if (statement.kind === "return" || statement.kind === "break" || statement.kind === "continue") {
        last = VOID;
      }
    }
    return last;
  } finally {
    ctx.scope = previous;
  }
}
