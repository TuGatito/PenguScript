// Control de flujo como expresión del emisor JavaScript: `match`, `switch`,
// comprensiones y bucles que devuelven valor (`break valor`, `else`).
//
// JS no tiene `match` ni bucles con valor, así que se emiten como IIFE con
// `return` internos, igual que el backend C++ usa lambdas.

import type {
  ComprehensionNode,
  ExprNode,
  ForClauseNode,
  MatchNode,
  SwitchNode,
} from "../frontend/ast_expr.ts";
import type { PatternNode } from "../frontend/ast_pattern.ts";
import type { Block } from "../frontend/ast_stmt.ts";
import type { PenguType } from "../semantic/types.ts";
import { is_void } from "../semantic/types.ts";
import {
  current_unit,
  declare_local,
  expression_type,
  fresh_name,
  js_error,
  line,
  pop_scope,
  push_scope,
  runtime_name,
  symbol_name,
  type JsContext,
} from "./js_context.ts";
import { js_identifier } from "./js_names.ts";
import { capture_iife, emit_expr, emit_value_block } from "./js_expr.ts";
import { ensure_type } from "./js_module.ts";
import { emit_statement } from "./js_stmt.ts";

// --- match ---------------------------------------------------------------

export function emit_match_value(g: JsContext, node: MatchNode, expected?: PenguType): string {
  const result = expected ?? expression_type(g, node);
  return capture_iife(g, () => {
    const subject = fresh_name(g, "m");
    line(g, `const ${subject} = ${emit_expr(g, node.subject)};`);
    emit_match_arms(g, node, subject, { value: true, result });
    if (node.else_block !== undefined) {
      emit_value_block(g, node.else_block, result);
      return;
    }
    if (!is_void(result) && result.kind !== "any") {
      runtime_name(g);
      line(g, 'return rt.panic("match sin variante");');
    }
  });
}

export function emit_match_statement(g: JsContext, node: MatchNode): void {
  const subject = fresh_name(g, "m");
  line(g, `const ${subject} = ${emit_expr(g, node.subject)};`);
  // Con `else` hay que recordar si alguna variante coincidió: si no, el bloque
  // se ejecutaría siempre (C++ usa el mismo flag).
  const flag = node.else_block === undefined ? undefined : fresh_name(g, "coincide");
  if (flag !== undefined) line(g, `let ${flag} = false;`);
  emit_match_arms(g, node, subject, { value: false, flag });
  if (node.else_block !== undefined) {
    line(g, `if (!${flag}) {`);
    g.indent += 1;
    for (const statement of node.else_block.statements) emit_statement(g, statement);
    g.indent -= 1;
    line(g, "}");
  }
}

interface MatchMode {
  readonly value: boolean;
  readonly result?: PenguType;
  readonly flag?: string;
}

function emit_match_arms(g: JsContext, node: MatchNode, subject: string, mode: MatchMode): void {
  const subject_type = expression_type(g, node.subject);
  const omen =
    subject_type.kind === "named"
      ? current_unit(g).module.env.omens.get(subject_type.name)
      : undefined;
  const omen_type = subject_type.kind === "named" ? subject_type.name : "";
  const algebraic =
    omen !== undefined && [...omen.variants.values()].some((variant) => variant.payload.length > 0);

  for (const arm of node.arms) {
    const pattern = arm.pattern as PatternNode;
    if (pattern.kind === "wildcard_pattern") {
      open_scope(g, () => {
        matched(g, mode);
        emit_arm_body(g, arm.body, mode);
      });
      continue;
    }
    if (pattern.kind === "binding_pattern") {
      open_scope(g, () => {
        line(g, `const ${js_identifier(pattern.name)} = ${subject};`);
        declare_local(g, pattern.name);
        matched(g, mode);
        emit_arm_body(g, arm.body, mode);
      });
      continue;
    }
    if (pattern.kind === "literal_pattern") {
      emit_condition(g, `${subject} === ${emit_expr(g, pattern.value)}`, () => undefined, arm, mode);
      continue;
    }
    if (pattern.kind === "tuple_pattern") {
      open_scope(g, () => {
        const names: string[] = [];
        pattern.items.forEach((item, index) => {
          if (item.kind !== "binding_pattern") return;
          names.push(`${js_identifier(item.name)} = ${subject}[${index}]`);
          declare_local(g, item.name);
        });
        if (names.length > 0) line(g, `const [${names.join(", ")}] = ${subject};`);
        matched(g, mode);
        emit_arm_body(g, arm.body, mode);
      });
      continue;
    }
    if (pattern.kind === "variant_pattern") {
      const variant_name = pattern.path[pattern.path.length - 1] ?? "";
      const variant = omen?.variants.get(variant_name);
      if (variant === undefined) {
        js_error(g, `la variante «${variant_name}» no pertenece a la omen del «match»`, pattern.span);
        continue;
      }
      const condition = algebraic
        ? `${subject}.tag === "${variant_name}"`
        : `${subject} === ${variant_reference(g, omen_type, variant_name)}`;
      emit_condition(
        g,
        condition,
        () => {
          if (!algebraic) return;
          pattern.args.forEach((argument, position) => {
            if (argument.kind !== "binding_pattern") return;
            line(g, `const ${js_identifier(argument.name)} = ${subject}._${position};`);
            declare_local(g, argument.name);
          });
        },
        arm,
        mode,
      );
      continue;
    }
    const unknown = pattern as PatternNode;
    js_error(g, "patrón no soportado en «match» al emitir JavaScript", unknown.span);
  }
}

function variant_reference(g: JsContext, omen_type: string, variant: string): string {
  const realm = current_unit(g).module.realm;
  ensure_type(g, realm, omen_type);
  const base = symbol_name(g, omen_type);
  return `${base}.${js_identifier(variant)}`;
}

function open_scope(g: JsContext, body: () => void): void {
  push_scope(g);
  try {
    body();
  } finally {
    pop_scope(g);
  }
}

function emit_condition(
  g: JsContext,
  condition: string,
  bind: () => void,
  arm: { readonly guard?: ExprNode; readonly body: Block },
  mode: MatchMode,
): void {
  line(g, `if (${condition}) {`);
  g.indent += 1;
  push_scope(g);
  try {
    bind();
    if (arm.guard !== undefined) {
      line(g, `if (${emit_expr(g, arm.guard)}) {`);
      g.indent += 1;
      matched(g, mode);
      emit_arm_body(g, arm.body, mode);
      g.indent -= 1;
      line(g, "}");
    } else {
      matched(g, mode);
      emit_arm_body(g, arm.body, mode);
    }
  } finally {
    pop_scope(g);
    g.indent -= 1;
    line(g, "}");
  }
}

function matched(g: JsContext, mode: MatchMode): void {
  if (mode.flag !== undefined) line(g, `${mode.flag} = true;`);
}

function emit_arm_body(g: JsContext, body: Block, mode: MatchMode): void {
  if (mode.value) {
    emit_value_block(g, body, mode.result);
    return;
  }
  for (const statement of body.statements) emit_statement(g, statement);
}

// --- switch --------------------------------------------------------------

export function emit_switch_value(g: JsContext, node: SwitchNode, expected?: PenguType): string {
  const result = expected ?? expression_type(g, node);
  return capture_iife(g, () => {
    const subject = fresh_name(g, "s");
    line(g, `const ${subject} = ${emit_expr(g, node.subject)};`);
    for (const arm of node.arms) emit_switch_arm(g, subject, arm, result);
    if (node.else_block !== undefined) {
      emit_value_block(g, node.else_block, result);
      return;
    }
    // C++ devuelve `std::nullopt` cuando ningún `when` coincide.
    if (!is_void(result) && result.kind !== "any") line(g, "return null;");
  });
}

export function emit_switch_statement(g: JsContext, node: SwitchNode): void {
  const subject = fresh_name(g, "s");
  line(g, `const ${subject} = ${emit_expr(g, node.subject)};`);
  for (const arm of node.arms) emit_switch_arm(g, subject, arm, undefined);
  const else_block = node.else_block;
  if (else_block === undefined) return;
  line(g, "{");
  g.indent += 1;
  open_scope(g, () => {
    for (const statement of else_block.statements) emit_statement(g, statement);
  });
  g.indent -= 1;
  line(g, "}");
}

function emit_switch_arm(
  g: JsContext,
  subject: string,
  arm: { readonly patterns: readonly ExprNode[]; readonly body: Block },
  result: PenguType | undefined,
): void {
  const conditions = arm.patterns.map((pattern) => `${subject} === ${emit_expr(g, pattern)}`);
  if (conditions.length === 0) return;
  line(g, `if (${conditions.join(" || ")}) {`);
  g.indent += 1;
  open_scope(g, () => {
    if (result === undefined) {
      for (const statement of arm.body.statements) emit_statement(g, statement);
      return;
    }
    emit_value_block(g, arm.body, result);
  });
  g.indent -= 1;
  line(g, "}");
}

// --- comprensiones -------------------------------------------------------

export function emit_comprehension(
  g: JsContext,
  node: ComprehensionNode,
  expected?: PenguType,
): string {
  const result = expected ?? expression_type(g, node);
  const container = node.container;
  return capture_iife(g, () => {
    const out = fresh_name(g, "out");
    const constructor =
      container === "vector" ? "Array" : container === "map" ? "Map" : "Set";
    line(g, `const ${out} = new ${constructor}();`);
    push_scope(g);
    try {
      emit_clauses(g, node.clauses, 0, () => {
        const body = emit_expr(g, node.body, element_type(result));
        if (container === "map") {
          const key = node.key === undefined ? "undefined" : emit_expr(g, node.key, key_type(result));
          line(g, `${out}.set(${key}, ${body});`);
        } else if (container === "set") {
          line(g, `${out}.add(${body});`);
        } else {
          line(g, `${out}.push(${body});`);
        }
      });
    } finally {
      pop_scope(g);
    }
    line(g, `return ${out};`);
  });
}

function emit_clauses(
  g: JsContext,
  clauses: readonly ForClauseNode[],
  index: number,
  body: () => void,
): void {
  const clause = clauses[index];
  if (clause === undefined) {
    body();
    return;
  }
  const iterable = emit_expr(g, clause.iterable);
  const names = clause.variables.map((name) => js_identifier(name));
  const target = names.length > 1 ? `[${names.join(", ")}]` : (names[0] ?? "_");
  line(g, `for (const ${target} of ${iterable}) {`);
  g.indent += 1;
  push_scope(g);
  try {
    for (const name of clause.variables) declare_local(g, name);
    if (clause.condition === undefined) {
      emit_clauses(g, clauses, index + 1, body);
    } else {
      line(g, `if (${emit_expr(g, clause.condition)}) {`);
      g.indent += 1;
      emit_clauses(g, clauses, index + 1, body);
      g.indent -= 1;
      line(g, "}");
    }
  } finally {
    pop_scope(g);
    g.indent -= 1;
    line(g, "}");
  }
}

function element_type(type: PenguType): PenguType | undefined {
  if (type.kind !== "named") return undefined;
  if (type.name === "map") return type.args[1];
  if (type.name === "vector" || type.name === "set") return type.args[0];
  return undefined;
}

function key_type(type: PenguType): PenguType | undefined {
  return type.kind === "named" && type.name === "map" ? type.args[0] : undefined;
}
