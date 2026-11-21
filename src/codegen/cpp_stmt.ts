// Emisión de sentencias y bloques.
//
// Un bloque de función se emite como sentencias C++ normales; cuando
// el bloque produce el valor de una función o de una rama, su última
// expresión se convierte en `return`.

import type { Block, StmtNode } from "../frontend/ast_stmt.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import { emit_expr } from "./cpp_expr.ts";
import { cpp_type_node, cpp_identifier } from "./cpp_types.ts";
import type { GenContext } from "./cpp_context.ts";
import { declare_local, gc_error, line, pop_scope, push_scope, type_of } from "./cpp_context.ts";
import { emit_as_statement } from "./cpp_expr.ts";

export function emit_block(g: GenContext, block: Block): void {
  push_scope(g);
  for (const statement of block.statements) {
    emit_statement(g, statement, false);
  }
  pop_scope(g);
}

export function emit_value_block(g: GenContext, block: Block, result_type: string): void {
  push_scope(g);
  const statements = block.statements;
  let emitted_return = false;
  for (let index = 0; index < statements.length; index += 1) {
    const statement = statements[index] as StmtNode;
    const is_last = index === statements.length - 1;
    if (is_last && result_type !== "void" && statement.kind === "expr_stmt") {
      line(g, `return ${emit_expr(g, statement.expr)};`);
      emitted_return = true;
      continue;
    }
    if (statement.kind === "return") emitted_return = true;
    emit_statement(g, statement, is_last && result_type !== "void");
  }
  if (!emitted_return && result_type !== "void" && result_type !== "auto") {
    line(g, "return {};");
  }
  pop_scope(g);
}

export function emit_statement(g: GenContext, statement: StmtNode, need_value: boolean): void {
  switch (statement.kind) {
    case "expr_stmt": {
      if (!need_value && emit_as_statement(g, statement.expr)) return;
      const value = emit_expr(g, statement.expr);
      line(g, need_value ? `return ${value};` : `${value};`);
      return;
    }
    case "assign":
      emit_assign(g, statement);
      return;
    case "const_stmt": {
      const value = emit_expr(g, statement.value);
      if (statement.declared_type) {
        line(g, `const ${cpp_type_node(statement.declared_type, g.module.env, g.type_realms)} ${cpp_identifier(statement.name)} = ${value};`);
      } else {
        const qualifier = type_of(g, statement.value).kind === "unique" ? "auto" : "const auto";
        line(g, `${qualifier} ${cpp_identifier(statement.name)} = ${value};`);
      }
      declare_local(g, statement.name);
      return;
    }
    case "return":
      line(g, statement.value ? `return ${emit_expr(g, statement.value)};` : "return;");
      return;
    case "break": {
      const flag = g.break_flags[g.break_flags.length - 1];
      const result = g.break_values[g.break_values.length - 1];
      if (statement.value !== undefined) {
        const value = emit_expr(g, statement.value);
        if (result !== undefined) {
          const mark = flag !== undefined ? ` ${flag} = true;` : "";
          line(g, `{ ${result} = ${value};${mark} break; }`);
        } else {
          gc_error(g, "«break» con valor fuera de un bucle con resultado", statement.span);
        }
        return;
      }
      if (flag !== undefined) {
        line(g, `{ ${flag} = true; break; }`);
      } else {
        line(g, "break;");
      }
      return;
    }
    case "continue":
      line(g, "continue;");
      return;
    case "pass":
      line(g, ";");
      return;
  }
}

interface AssignLike {
  readonly kind: "assign";
  readonly targets: readonly ExprNode[];
  readonly op: string;
  readonly value: ExprNode;
  readonly mutable: boolean;
  readonly declared_type: import("../frontend/ast_type.ts").TypeNode | undefined;
}

function emit_assign(g: GenContext, statement: AssignLike): void {
  const value = emit_expr(g, statement.value);
  if (statement.op !== "=") {
    const target = statement.targets[0];
    if (target === undefined) return;
    line(g, `${emit_expr(g, target)} ${statement.op} ${value};`);
    return;
  }

  const first = statement.targets[0];
  const is_single = statement.targets.length === 1 && first !== undefined && first.kind === "ident";
  if (is_single && !is_local_declared(g, (first as { name: string }).name)) {
    const name = cpp_identifier((first as { name: string }).name);
    if (statement.declared_type) {
      const type = cpp_type_node(statement.declared_type, g.module.env, g.type_realms);
      line(g, `${type} ${name} = ${value};`);
    } else if (statement.mutable) {
      line(g, `auto ${name} = ${value};`);
    } else if (type_of(g, statement.value).kind === "unique") {
      // `unique<T>` no se puede copiar: sin `const` para poder moverlo.
      line(g, `auto ${name} = ${value};`);
    } else {
      line(g, `const auto ${name} = ${value};`);
    }
    declare_local(g, (first as { name: string }).name);
    return;
  }

  if (!is_single && statement.targets.every((target) => target.kind === "ident")) {
    const names = statement.targets.map((target) => cpp_identifier((target as { name: string }).name));
    line(g, `auto [${names.join(", ")}] = ${value};`);
    for (const target of statement.targets) {
      declare_local(g, (target as { name: string }).name);
    }
    return;
  }

  const targets = statement.targets.map((target) => emit_expr(g, target)).join(", ");
  line(g, `${targets} = ${value};`);
}

function is_local_declared(g: GenContext, name: string): boolean {
  const cpp_name = cpp_identifier(name);
  for (let index = g.scopes.length - 1; index >= 0; index -= 1) {
    const scope = g.scopes[index];
    if (scope !== undefined && scope.includes(cpp_name)) return true;
  }
  return false;
}
