// Sentencias y bloques del emisor JavaScript.
//
// PenguScript no tiene `;` ni llaves: los bloques son indentados y su valor
// es la última expresión. `emit_value_block` reproduce eso devolviendo la
// última expresión, igual que el backend C++ (que emite `return`).

import type { StmtNode } from "../frontend/ast_stmt.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import type { TypeNode } from "../frontend/ast_type.ts";
import type { PenguType } from "../semantic/types.ts";
import { is_integer, is_void } from "../semantic/types.ts";
import { is_bigint_type } from "./js_types.ts";

import {
  cross_reference,
  current_unit,
  declare_local,
  declare_local_type,
  expression_type,
  is_local_declared,
  js_error,
  line,
  local_type,
  quiet_type_node,
  realm_of_type,
  runtime_name,
  type_of,
  type JsContext,
} from "./js_context.ts";
import { js_identifier } from "./js_names.ts";
import { needs_clone } from "./js_types.ts";
import { coerce, emit_as_statement, emit_expr, emit_store_target, is_control_expr } from "./js_expr.ts";
import { ensure_type } from "./js_module.ts";
import {
  free_method_export,
  operator_method_name,
  rune_operator_owner,
} from "./js_type_decl.ts";


// Tipo con el que se registra una variable: si la anotación es un nombre
// (`d: Metros`), se conserva el alias para resolver sus métodos.
function declared_named(
  g: JsContext,
  statement: Extract<StmtNode, { kind: "assign" }>,
  resolved: PenguType | undefined,
): PenguType {
  const declared = statement.declared_type;
  if (declared !== undefined) return quiet_type_node(g, declared);
  return resolved ?? expression_type(g, statement.value);
}


// `p += v` sobre un rune con `operator +=`: `<Tipo>__op_add_assign(p, v)`.
// El operador puede devolver un valor nuevo o mutar `p` (en ese caso la
// llamada se emite como sentencia, no como asignación).
function rune_operator_assign(
  g: JsContext,
  target: string,
  statement: Extract<StmtNode, { kind: "assign" }>,
  operator: string,
  value: string,
): { code: string; has_result: boolean } | undefined {
  const first = statement.targets[0]!;
  const type = first.kind === "ident" ? local_type(g, first.name) ?? expression_type(g, first) : expression_type(g, first);
  if (type === undefined || type.kind !== "named") return undefined;
  const realm = realm_of_type(g, type.name);
  if (realm === undefined) return undefined;
  const owner = rune_operator_owner(g, realm, type.name, operator);
  if (owner === undefined) return undefined;
  const exported = free_method_export(owner.type, operator_method_name(operator));
  ensure_type(g, owner.realm, owner.type);
  const callable = cross_reference(g, owner.realm, exported);
  const info = g.units.get(owner.realm)?.module.env.runes.get(owner.type)?.methods.get(operator);
  const has_result = info !== undefined && !is_void(info.result);
  return { code: `${callable}(${target}, ${value})`, has_result };
}

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
      declare_local_type(g, statement.name, expected ?? expression_type(g, statement.value));
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
      const slot = g.break_values[g.break_values.length - 1];
      const flag = g.break_flags[g.break_flags.length - 1];
      if (statement.value !== undefined) {
        if (slot === undefined || slot === "") {
          js_error(g, "`break` con valor fuera de un bucle con valor", statement.span);
          return;
        }
        line(g, `${slot} = ${emit_expr(g, statement.value)};`);
      }
      if (flag !== undefined && flag !== "") line(g, `${flag} = true;`);
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

// Asignación compuesta: `x += y` se emite como `x = x + y` para poder aplicar
// la conversión numérica (un `long` con `BigInt` no admite mezcla de tipos).
function compound(
  target: string,
  operator: string,
  value: string,
  g: JsContext,
  statement: Extract<StmtNode, { kind: "assign" }>,
  value_type: PenguType,
): string {
  const binary_operator = operator.slice(0, -1);
  const first = statement.targets[0]!;
  const target_type =
    (first.kind === "ident" ? local_type(g, first.name) : undefined) ??
    expression_type(g, first);
  const code = coerce(g, emit_expr(g, statement.value, target_type), value_type, target_type);
  if (binary_operator === "/" && target_type.kind === "primitive" && is_integer(target_type)) {
    if (!is_bigint_type(target_type, g.mode)) return `${target} / ${code} | 0`;
  }
  return `${target} ${binary_operator} ${code}`;
}

export function emit_assign(
  g: JsContext,
  statement: Extract<StmtNode, { kind: "assign" }>,
): void {
  const targets = statement.targets;
  const expected: PenguType | undefined = declared_hint(g, statement.declared_type, statement.value);
  const emitted_value = emit_expr(g, statement.value, expected);
  // Asignar un valor con semántica de valor copia (C++ copia siempre) (§3).
  const value_type = expression_type(g, statement.value);
  // La declaración puede estrechar el tipo (`mut j: size_t = #@ - 1`).
  const raw_value =
    expected === undefined ? emitted_value : coerce(g, emitted_value, value_type, expected);
  const value =
    needs_clone(value_type) && statement.op === "="
      ? `${runtime_name(g)}.clone(${raw_value})`
      : raw_value;
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
      declare_local_type(g, single.name, declared_named(g, statement, expected));
      const keyword = statement.mutable ? "let" : "const";
      line(g, `${keyword} ${name} = ${value};`);
      return;
    }
    if (statement.op !== "=") {
      const rune_call = rune_operator_assign(g, name, statement, statement.op, value);
      if (rune_call !== undefined) {
        line(g, rune_call.has_result ? `${name} = ${rune_call.code};` : `${rune_call.code};`);
        return;
      }
      line(g, `${name} = ${compound(name, statement.op, value, g, statement, value_type)};`);
      return;
    }
    line(g, `${name} = ${value};`);
    return;
  }

  if (single === undefined) return;
  if (single.kind === "index") {
    const store = emit_store_target(g, single, value, statement.op);
    line(g, `${store};`);
    return;
  }
  const target = emit_expr(g, single, expression_type(g, single));
  if (statement.op !== "=") {
    line(g, `${target} = ${compound(target, statement.op, value, g, statement, value_type)};`);
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
  return quiet_type_node(g, declared);
}
