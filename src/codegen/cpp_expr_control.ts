// Emisión de las expresiones de control: `if`, `switch`, `match`,
// bucles, comprensiones y funciones literales.

import type {
  BinaryNode,
  CallNode,
  CastNode,
  ComprehensionNode,
  ExprNode,
  ForClauseNode,
  MatchNode,
  SwitchNode,
} from "../frontend/ast_expr.ts";
import type { PatternNode } from "../frontend/ast_pattern.ts";
import type { GenContext } from "./cpp_context.ts";
import {
  declare_local,
  fresh_name,
  is_local_declared,
  gc_error,
  line,
  pop_scope,
  push_scope,
  type_of,
} from "./cpp_context.ts";
import { cpp_identifier, cpp_type, cpp_type_node, cpp_value_type, sanitize_namespace } from "./cpp_types.ts";
import { is_adapter_type, is_map_type, is_sequence_container, is_set_type } from "../semantic/builtin_members.ts";
import { omen_methods_of } from "../semantic/module_info.ts";
import { find_echo_method } from "../semantic/type_env.ts";
import type { PenguType } from "../semantic/types.ts";
import { UNKNOWN, is_float, is_numeric, is_string, named, primitive, type_equals } from "../semantic/types.ts";
import { is_conversion_target } from "../semantic/checker_expr.ts";
import { resolve_type_node } from "../semantic/type_env.ts";
import { STRING_TYPES } from "../frontend/ast_type.ts";
import type { TypeNode } from "../frontend/ast_type.ts";
import { emit_block, emit_value_block } from "./cpp_stmt.ts";


import { cpp_string, emit_expr } from "./cpp_expr.ts";

export function emit_comprehension(g: GenContext, node: ComprehensionNode): string {
  const result_type = type_of(g, node);
  const result_cpp = cpp_value_type(result_type, g.type_realms);
  return build_lambda(g, "", result_cpp, () => {
    const out = fresh_name(g, "out");
    line(g, `${result_cpp} ${out};`);
    emit_comprehension_clauses(g, node, out, 0);
    line(g, `return ${out};`);
  }) + "()";
}

export function emit_comprehension_clauses(g: GenContext, node: ComprehensionNode, out: string, index: number): void {
  if (index >= node.clauses.length) {
    const body = emit_expr(g, node.body);
    if (node.container === "vector") {
      line(g, `${out}.push_back(${body});`);
    } else if (node.container === "set") {
      line(g, `${out}.insert(${body});`);
    } else {
      const key = node.key ? emit_expr(g, node.key) : "0";
      line(g, `${out}[${key}] = ${body};`);
    }
    return;
  }

  const clause = node.clauses[index] as ForClauseNode;
  const iterable = emit_expr(g, clause.iterable);
  push_scope(g);
  if (is_map_type(type_of(g, clause.iterable)) && clause.variables.length === 2) {
    const [first, second] = clause.variables;
    const prefix = clause.mutable ? "auto&" : "const auto&";
    line(g, `for (${prefix} [${cpp_identifier(first ?? "k")}, ${cpp_identifier(second ?? "v")}] : ${iterable}) {`);
    declare_local(g, first ?? "k");
    declare_local(g, second ?? "v");
  } else if (clause.variables.length === 2) {
    const [first, second] = clause.variables;
    const container = fresh_name(g, "c");
    const position = fresh_name(g, "i");
    line(g, `for (std::size_t ${position} = 0; ${position} < ${iterable}.size(); ++${position}) {`);
    line(g, `  const auto ${cpp_identifier(first ?? "i")} = ${position};`);
    line(g, `  const auto& ${cpp_identifier(second ?? "x")} = ${iterable}[${position}];`);
    declare_local(g, first ?? "i");
    declare_local(g, second ?? "x");
    void container;
  } else {
    const name = clause.variables[0] ?? "x";
    const prefix = clause.mutable ? "auto&" : "const auto&";
    line(g, `for (${prefix} ${cpp_identifier(name)} : ${iterable}) {`);
    declare_local(g, name);
  }
  g.indent += 1;
  if (clause.condition) {
    line(g, `if (${emit_expr(g, clause.condition)}) {`);
    g.indent += 1;
    emit_comprehension_clauses(g, node, out, index + 1);
    g.indent -= 1;
    line(g, "}");
  } else {
    emit_comprehension_clauses(g, node, out, index + 1);
  }
  g.indent -= 1;
  line(g, "}");
  pop_scope(g);
}

// Emite una expresión de control como sentencias sueltas cuando su valor
// se descarta: así `break`/`continue` siguen dentro del bucle real.
export function emit_as_statement(
  g: GenContext,
  node: import("../frontend/ast_expr.ts").ExprNode,
): boolean {
  if (node.kind === "if") {
    const condition = emit_expr(g, node.condition);
    line(g, `if (${node.unless ? `!(${condition})` : condition}) {`);
    g.indent += 1;
    emit_block(g, node.then_block);
    g.indent -= 1;
    if (node.else_block !== undefined) {
      line(g, "} else {");
      g.indent += 1;
      emit_block(g, node.else_block);
      g.indent -= 1;
    }
    line(g, "}");
    return true;
  }
  if (node.kind === "do") {
    push_scope(g);
    emit_value_block(g, node.block, "void");
    pop_scope(g);
    return true;
  }
  // Los bucles también se emiten como sentencias: así `return` dentro del
  // cuerpo sale de la función y no de una lambda.
  switch (node.kind) {
    case "while":
      emit_while(g, node, false);
      return true;
    case "repeat":
      emit_repeat(g, node, false);
      return true;
    case "for_numeric":
      emit_for_numeric(g, node, false);
      return true;
    case "for_iter":
      emit_for_iter(g, node, false);
      return true;
    default:
      return false;
  }
}

export function emit_if(g: GenContext, node: import("../frontend/ast_expr.ts").IfNode): string {
  const result = cpp_value_type(type_of(g, node), g.type_realms);
  return build_lambda(g, "", result, () => {
    const condition = emit_expr(g, node.condition);
    line(g, `if (${node.unless ? `!(${condition})` : condition}) {`);
    g.indent += 1;
    emit_value_block(g, node.then_block, result);
    g.indent -= 1;
    line(g, "} else {");
    g.indent += 1;
    if (node.else_block) {
      emit_value_block(g, node.else_block, result);
    } else if (result !== "void") {
      line(g, "return std::nullopt;");
    }
    g.indent -= 1;
    line(g, "}");
  }) + "()";
}

export function emit_switch(g: GenContext, node: SwitchNode): string {
  const result = cpp_value_type(type_of(g, node), g.type_realms);
  return build_lambda(g, "", result, () => {
    const subject = fresh_name(g, "s");
    line(g, `auto ${subject} = ${emit_expr(g, node.subject)};`);
    line(g, `switch (${subject}) {`);
    g.indent += 1;
    for (const arm of node.arms) {
      for (const pattern of arm.patterns) {
        line(g, `case ${emit_expr(g, pattern)}:`);
      }
      g.indent += 1;
      emit_value_block(g, arm.body, result);
      if (result === "void") line(g, "break;");
      g.indent -= 1;
    }
    if (node.else_block) {
      line(g, "default:");
      g.indent += 1;
      emit_value_block(g, node.else_block, result);
      if (result === "void") line(g, "break;");
      g.indent -= 1;
    } else if (result !== "void") {
      line(g, "default:");
      g.indent += 1;
      line(g, "return std::nullopt;");
      g.indent -= 1;
    }
    g.indent -= 1;
    line(g, "}");
  }) + "()";
}

export function emit_match(g: GenContext, node: MatchNode): string {
  const result = cpp_value_type(type_of(g, node), g.type_realms);
  const subject_type = type_of(g, node.subject);
  const omen = subject_type.kind === "named" ? g.module.env.omens.get(subject_type.name) : undefined;
  const omen_name = omen !== undefined && subject_type.kind === "named" ? subject_type.name : "";
  const omen_args =
    subject_type.kind === "named" && subject_type.args.length > 0
      ? `<${subject_type.args.map((arg) => cpp_type(arg, g.type_realms)).join(", ")}>`
      : "";
  const algebraic =
    omen !== undefined && [...omen.variants.values()].some((variant) => variant.payload.length > 0);
  return build_lambda(g, "", result, () => {
    const subject = fresh_name(g, "m");
    line(g, `auto ${subject} = ${emit_expr(g, node.subject)};`);
    for (const arm of node.arms) {
      const pattern = arm.pattern as PatternNode;
      if (pattern.kind === "wildcard_pattern" || pattern.kind === "binding_pattern") {
        if (pattern.kind === "binding_pattern") {
          line(g, `auto& ${cpp_identifier(pattern.name)} = ${subject};`);
        }
        emit_value_block(g, arm.body, result);
        continue;
      }
      if (pattern.kind === "variant_pattern") {
        const variant_name = pattern.path[pattern.path.length - 1] ?? "";
        const pointer = fresh_name(g, "p");
        if (algebraic) {
          const variant = omen?.variants.get(variant_name);
          if (variant === undefined) continue;
          if (variant.payload.length === 0) {
            line(g, `if (std::holds_alternative<${omen_name}_${variant_name}${omen_args}>(${subject}.value)) {`);
            g.indent += 1;
            emit_guard_and_body(g, arm, result, () => undefined);
            g.indent -= 1;
            line(g, "}");
            continue;
          }
          line(g, `if (auto* ${pointer} = std::get_if<${omen_name}_${variant_name}${omen_args}>(&${subject}.value)) {`);
          g.indent += 1;
          emit_guard_and_body(g, arm, result, () => {
            pattern.args.forEach((argument, position) => {
              if (argument.kind === "binding_pattern") {
                line(g, `auto& ${cpp_identifier(argument.name)} = ${pointer}->v${position};`);
                declare_local(g, argument.name);
              }
            });
          });
          g.indent -= 1;
          line(g, "}");
          continue;
        }
        line(g, `if (${subject} == ${omen_name}::${variant_name}) {`);
        g.indent += 1;
        emit_guard_and_body(g, arm, result, () => undefined);
        g.indent -= 1;
        line(g, "}");
        continue;
      }
      gc_error(g, "patrón no soportado en «match»", arm.span);
    }
    if (node.else_block !== undefined) {
      emit_value_block(g, node.else_block, result);
    } else if (result !== "void") {
      line(g, `::pengu::panic("match sin variante");`);
    }
  }) + "()";
}

export function emit_guard_and_body(
  g: GenContext,
  arm: import("../frontend/ast_expr.ts").MatchArm,
  result: string,
  bind: () => void,
): void {
  bind();
  if (arm.guard) {
    line(g, `if (${emit_expr(g, arm.guard)}) {`);
    g.indent += 1;
    emit_value_block(g, arm.body, result);
    g.indent -= 1;
    line(g, "}");
  } else {
    emit_value_block(g, arm.body, result);
  }
}

export function loop_result_expr_type(g: GenContext, node: ExprNode): string {
  const type = type_of(g, node);
  if (type.kind === "optional" && type.inner.kind !== "any") {
    return cpp_value_type(type, g.type_realms);
  }
  return "void";
}

// Declara la variable que recoge el `break value` (si el bucle la usa).
export function begin_loop_result(g: GenContext, result_type: string): string | undefined {
  if (result_type === "void") return undefined;
  const name = fresh_name(g, "res");
  line(g, `${result_type} ${name};`);
  g.break_values.push(name);
  return name;
}

export function end_loop_result(g: GenContext, result_var: string | undefined): void {
  if (result_var === undefined) return;
  g.break_values.pop();
  line(g, `return ${result_var};`);
}

function emit_loop(
  g: GenContext,
  node: ExprNode,
  as_value: boolean,
  build: (result_type: string) => void,
): string {
  const result_type = as_value ? loop_result_expr_type(g, node) : "void";
  if (!as_value) {
    // Como sentencia el bucle se emite directo: dentro de una lambda un
    // `return` saldría de la lambda y no de la función.
    build("void");
    return "";
  }
  return build_lambda(g, "", result_type, () => build(result_type)) + "()";
}

export function emit_while(
  g: GenContext,
  node: import("../frontend/ast_expr.ts").WhileNode,
  as_value = true,
): string {
  return emit_loop(g, node, as_value, (result_type) => {
    const result_var = begin_loop_result(g, result_type);
    const condition = emit_expr(g, node.condition);
    line(g, `while (${node.until ? `!(${condition})` : condition}) {`);
    g.indent += 1;
    emit_value_block(g, node.body, "void");
    g.indent -= 1;
    line(g, "}");
    end_loop_result(g, result_var);
  });
}

export function emit_repeat(
  g: GenContext,
  node: import("../frontend/ast_expr.ts").RepeatNode,
  as_value = true,
): string {
  return emit_loop(g, node, as_value, (result_type) => {
    const result_var = begin_loop_result(g, result_type);
    line(g, "do {");
    g.indent += 1;
    emit_value_block(g, node.body, "void");
    g.indent -= 1;
    line(g, `} while (!(${emit_expr(g, node.condition)}));`);
    end_loop_result(g, result_var);
  });
}

export function emit_for_numeric(
  g: GenContext,
  node: import("../frontend/ast_expr.ts").ForNumericNode,
  as_value = true,
): string {
  return emit_loop(g, node, as_value, (result_type) => {
    const result_var = begin_loop_result(g, result_type);
    const name = cpp_identifier(node.variable);
    const start = emit_expr(g, node.start);
    const end = emit_expr(g, node.end);
    const step = node.step ? emit_expr(g, node.step) : "1";
    const flag = node.else_block ? fresh_name(g, "broke") : undefined;
    if (flag !== undefined) line(g, `bool ${flag} = false;`);
    const declared = node.variable_type ? cpp_type_node(node.variable_type, g.module.env, g.type_realms) : "auto";
    line(g, `for (${declared} ${name} = ${start}; (${step}) > 0 ? ${name} <= ${end} : ${name} >= ${end}; ${name} += (${step})) {`);
    declare_local(g, node.variable);
    g.indent += 1;
    if (flag !== undefined) g.break_flags.push(flag);
    emit_value_block(g, node.body, "void");
    if (flag !== undefined) g.break_flags.pop();
    g.indent -= 1;
    line(g, "}");
    if (flag !== undefined && node.else_block) {
      line(g, `if (!${flag}) {`);
      g.indent += 1;
      emit_value_block(g, node.else_block, "void");
      g.indent -= 1;
      line(g, "}");
    }
    end_loop_result(g, result_var);
  });
}

export function emit_for_iter(
  g: GenContext,
  node: import("../frontend/ast_expr.ts").ForIterNode,
  as_value = true,
): string {
  return emit_loop(g, node, as_value, (result_type) => {
    const result_var = begin_loop_result(g, result_type);
    const iterable_type = type_of(g, node.iterable);
    const iterable = emit_expr(g, node.iterable);
    const flag = node.else_block ? fresh_name(g, "broke") : undefined;
    if (flag !== undefined) line(g, `bool ${flag} = false;`);
    if (flag !== undefined) g.break_flags.push(flag);
    if (is_map_type(iterable_type) && node.variables.length === 2) {
      const [first, second] = node.variables;
      const prefix = node.mutable ? "auto&" : "const auto&";
      line(g, `for (${prefix} [${cpp_identifier(first ?? "k")}, ${cpp_identifier(second ?? "v")}] : ${iterable}) {`);
      declare_local(g, first ?? "k");
      declare_local(g, second ?? "v");
      g.indent += 1;
      emit_value_block(g, node.body, "void");
      g.indent -= 1;
    } else if (node.variables.length === 2) {
      const [first, second] = node.variables;
      const container = fresh_name(g, "c");
      const position = fresh_name(g, "i");
      line(g, `auto ${container} = ${iterable};`);
      line(g, `for (std::size_t ${position} = 0; ${position} < ${container}.size(); ++${position}) {`);
      line(g, `  const auto ${cpp_identifier(first ?? "i")} = ${position};`);
      line(g, `  const auto& ${cpp_identifier(second ?? "x")} = ${container}[${position}];`);
      declare_local(g, first ?? "i");
      declare_local(g, second ?? "x");
      g.indent += 1;
      emit_value_block(g, node.body, "void");
      g.indent -= 1;
    } else {
      const name = node.variables[0] ?? "x";
      const prefix = node.mutable ? "auto&" : "const auto&";
      line(g, `for (${prefix} ${cpp_identifier(name)} : ${iterable}) {`);
      declare_local(g, name);
      g.indent += 1;
      emit_value_block(g, node.body, "void");
      g.indent -= 1;
    }
    if (flag !== undefined) g.break_flags.pop();
    line(g, "}");
    if (flag !== undefined && node.else_block) {
      line(g, `if (!${flag}) {`);
      g.indent += 1;
      emit_value_block(g, node.else_block, "void");
      g.indent -= 1;
      line(g, "}");
    }
    end_loop_result(g, result_var);
  });
}

export function emit_lambda(g: GenContext, node: import("../frontend/ast_expr.ts").LambdaNode): string {
  const params = node.params
    .map((param) => {
      const type = param.type ? cpp_type_node(param.type, g.module.env, g.type_realms) : "auto";
      const rendered = param.mutable && type !== "auto" ? `${type}&` : type;
      return `${rendered} ${cpp_identifier(param.name)}`;
    })
    .join(", ");
  const result = node.result ? cpp_type_node(node.result, g.module.env, g.type_realms) : "auto";
  return build_lambda(g, params, result, () => {
    push_scope(g);
    for (const param of node.params) declare_local(g, param.name);
    emit_value_block(g, node.body, result);
    pop_scope(g);
  });
}

// Construye una lambda capturando por referencia el contexto actual.
// `result === undefined` deja que C++ deduzca el tipo de retorno.
export function build_lambda(
  g: GenContext,
  params: string,
  result: string | undefined,
  build: () => void,
): string {
  const outer_lines = g.lines;
  const outer_indent = g.indent;
  const inner: string[] = [];
  g.lines = inner;
  g.indent = 0;
  build();
  g.lines = outer_lines;
  g.indent = outer_indent;
  const signature = result === undefined ? "" : ` -> ${result}`;
  const pad = "  ".repeat(outer_indent);
  const body = inner.length === 0 ? `${pad}  ;` : inner.map((text) => `${pad}  ${text}`).join("\n");
  return `[&](${params})${signature} {\n${body}\n${pad}}`;
}

