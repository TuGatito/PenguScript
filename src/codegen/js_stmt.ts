// Sentencias y bloques del emisor JavaScript.
//
// PenguScript no tiene `;` ni llaves: los bloques son indentados y su valor
// es la última expresión. `emit_value_block` reproduce eso devolviendo la
// última expresión, igual que el backend C++ (que emite `return`).

import type { StmtNode } from "../frontend/ast_stmt.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import type { TypeNode } from "../frontend/ast_type.ts";
import type { PenguType } from "../semantic/types.ts";
import { resolve_type_node } from "../semantic/type_env.ts";
import {
  current_unit,
  declare_local,
  is_local_declared,
  js_error,
  line,
  type_of,
  expression_type,
  type JsContext,
} from "./js_context.ts";
import { js_identifier } from "./js_names.ts";
import { emit_expr, emit_as_statement, is_control_expr } from "./js_expr.ts";

export function emit_statement(g: JsContext, statement: StmtNode): void {
  switch (statement.kind) {
    case "expr_stmt": {
      if (is_control_expr(statement.expr)) {
        emit_as_statement(g, statement.expr);
        return;
      }
      line(g, `${emit_expr(g, statement.expr)};`);
      return;
    }
    case "assign": {
      emit_assign(g, statement);
      return;
    }
    case "const_stmt": {
      const expected = declared_hint(g, statement.declared_type, statement.value);
      if (is_local_declared(g, statement.name)) {
        line(g, `${js_identifier(statement.name)} = ${emit_expr(g, statement.value, expected)};`);
        return;
      }
      declare_local(g, statement.name);
      line(
        g,
        `const ${js_identifier(statement.name)} = ${emit_expr(g, statement.value, expected)};`,
      );
      return;
    }
    case "return": {
      if (statement.value === undefined) {
        line(g, "return;");
        return;
      }
      line(g, `return ${emit_expr(g, statement.value, g.return_type)};`);
      return;
    }
    case "break": {
      if (g.break_values.length > 0) {
        js_error(g, "`break` con valor todavía no se emite a JavaScript (fase P2)", statement.span);
        return;
      }
      line(g, "break;");
      return;
    }
    case "continue": {
      line(g, "continue;");
      return;
    }
    case "pass": {
      return;
    }
    default: {
      js_error(g, "sentencia desconocida en el emisor JavaScript", (statement as StmtNode).span);
    }
  }
}

// Emisión de `mut x = …`, `x = …`, `x += …` y asignación múltiple.
export function emit_assign(
  g: JsContext,
  statement: Extract<StmtNode, { kind: "assign" }>,
): void {
  const targets = statement.targets;
  const expected: PenguType | undefined = declared_hint(g, statement.declared_type, statement.value);
  const value = emit_expr(g, statement.value, expected);
  const single = targets.length === 1 ? targets[0] : undefined;

  if (targets.length > 1) {
    if (targets.some((target) => target.kind !== "ident")) {
      js_error(g, "la asignación múltiple solo admite nombres en JavaScript (fase P2)", statement.span);
      return;
    }
    const names = targets.flatMap((target) =>
      target.kind === "ident" ? [js_identifier(target.name)] : [],
    );
    const fresh = targets.filter(
      (target) => target.kind === "ident" && !is_local_declared(g, target.name),
    );
    if (fresh.length > 0 && fresh.length !== targets.length) {
      js_error(
        g,
        "la asignación múltiple con nombres ya declarados y nombres nuevos llegará en la fase P2",
        statement.span,
      );
      return;
    }
    for (const target of fresh) if (target.kind === "ident") declare_local(g, target.name);
    const keyword = fresh.length > 0 ? `${statement.mutable ? "let" : "const"} ` : "";
    line(g, `${keyword}[${names.join(", ")}] = ${value};`);
    return;
  }

  if (single !== undefined && single.kind === "ident") {
    const name = js_identifier(single.name);
    if (!is_local_declared(g, single.name)) {
      declare_local(g, single.name);
      const keyword = statement.mutable ? "let" : "const";
      line(g, `${keyword} ${name} = ${value};`);
      return;
    }
    if (statement.op !== "=") {
      line(g, `${name} ${statement.op} ${value};`);
      return;
    }
    line(g, `${name} = ${value};`);
    return;
  }

  if (single === undefined) return;
  const target = emit_expr(g, single, expression_type(g, single));
  if (statement.op !== "=") {
    line(g, `${target} ${statement.op} ${value};`);
    return;
  }
  line(g, `${target} = ${value};`);
}

// Tipo esperado de una asignación: el declarado si lo hay (resuelto a
// `PenguType`), y si no el que el checker infirió para el valor.
function declared_hint(
  g: JsContext,
  declared: TypeNode | undefined,
  value: ExprNode,
): PenguType | undefined {
  if (declared === undefined) return type_of(g, value);
  return resolve_type_node(declared, current_unit(g).module.env, g.sink);
}
