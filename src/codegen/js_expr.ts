// Expresiones del emisor JavaScript.
//
// Reglas de tipos numéricos (paridad con C++): el checker anota los literales
// como `int`, así que el tipo *esperado* viaja por las funciones de emisión
// (`expected`) y decide si un entero de 64 bits se escribe `1000n` o `1000`.
// La división entera se traduce a `Math.trunc(a / b)` porque `/` en JS es
// siempre flotante.

import type { ExprNode, StringPartNode } from "../frontend/ast_expr.ts";
import type { Block } from "../frontend/ast_stmt.ts";
import type { PenguType } from "../semantic/types.ts";
import { INT, is_char, is_float, is_integer, is_string, is_void, type_equals } from "../semantic/types.ts";
import {
  is_64_bit_integer,
  js_default_value,
  is_bigint_type,
  js_integer_kind,
  js_int_normalizer,
} from "./js_types.ts";
import {
  cross_reference,
  current_unit,
  realm_of_type,
  expression_type,
  fresh_name,
  is_local_declared,
  js_error,
  local_type,
  line,
  pop_scope,
  push_scope,
  runtime_name,
  symbol_name,
  type JsContext,
} from "./js_context.ts";
import { free_operator_name, js_identifier, js_string_literal } from "./js_names.ts";
import { emit_call, emit_path_reference } from "./js_expr_call.ts";
import {
  emit_comprehension,
  emit_match_statement,
  emit_match_value,
  emit_switch_statement,
  emit_switch_value,
} from "./js_expr_control.ts";
import { ensure_constant, ensure_function, ensure_realm } from "./js_module.ts";
import { free_method_export, operator_method_name, rune_operator_owner } from "./js_type_decl.ts";
import { emit_statement } from "./js_stmt.ts";

type NumKind = "int" | "float" | "bigint";

function num_kind(type: PenguType, g: JsContext): NumKind | undefined {
  if (is_bigint_type(type, g.mode)) return "bigint";
  if (is_float(type)) return "float";
  if (is_integer(type)) return "int";
  return undefined;
}

// Convierte un valor numérico al tipo destino (`BigInt`/`Number`), respetando
// la promoción que C++ hace de forma implícita.
export function coerce(g: JsContext, code: string, from: PenguType, to: PenguType): string {
  const from_kind = num_kind(from, g);
  const to_kind = num_kind(to, g);
  if (from_kind === undefined || to_kind === undefined) return code;
  if (to_kind === "bigint" && from_kind !== "bigint") {
    // Un literal ya emitido como `123n` (porque se le pasó el tipo esperado)
    // no necesita conversión.
    return /^[+-]?\d+n$/.test(code) ? code : `BigInt(${code})`;
  }
  if (to_kind !== "bigint" && from_kind === "bigint") return `Number(${code})`;
  return code;
}

export function emit_expr(g: JsContext, node: ExprNode, expected?: PenguType): string {
  switch (node.kind) {
    case "int_lit": {
      const bigint = expected !== undefined && is_bigint_type(expected, g.mode);
      return bigint ? `${node.value}n` : node.value;
    }
    case "float_lit": {
      return node.value;
    }
    case "bool_lit": {
      return node.value ? "true" : "false";
    }
    case "char_lit": {
      return js_string_literal(node.value);
    }
    case "string_lit": {
      return emit_string_lit(g, node.parts);
    }
    case "none_lit":
    case "nullptr_lit": {
      return "null";
    }
    case "ident": {
      return emit_ident(g, node.name, node.span);
    }
    case "self": {
      return g.self_expression ?? "this";
    }
    case "parent_call": {
      return `super(${node.args.map((arg) => emit_expr(g, arg.expr)).join(", ")})`;
    }
    case "path": {
      return emit_path_reference(g, node.segments, node.span);
    }
    case "member": {
      return `${emit_expr(g, node.object)}.${js_identifier(node.name)}`;
    }
    case "index": {
      return emit_index(g, node);
    }
    case "call": {
      return emit_call(g, node, expected);
    }
    case "unary": {
      return emit_unary(g, node);
    }
    case "binary": {
      return emit_binary(g, node);
    }
    case "cast": {
      return emit_cast(g, node);
    }
    case "tuple": {
      return `[${node.items.map((item) => emit_expr(g, item)).join(", ")}]`;
    }
    case "vector_lit": {
      return `[${node.items.map((item) => emit_expr(g, item, expected)).join(", ")}]`;
    }
    case "map_lit": {
      const args = type_args(g, node);
      const entries = node.entries.map(
        (entry) => `[${emit_expr(g, entry.key, args[0])}, ${emit_expr(g, entry.value, args[1])}]`,
      );
      return `new Map([${entries.join(", ")}])`;
    }
    case "set_lit": {
      const args = type_args(g, node);
      return `new Set([${node.items.map((item) => emit_expr(g, item, args[0])).join(", ")}])`;
    }
    case "range": {
      runtime_name(g);
      const start = emit_expr(g, node.start);
      const end = emit_expr(g, node.end);
      return `rt.range(${start}, ${end}, ${node.inclusive ? "true" : "false"})`;
    }
    case "if": {
      return emit_if(g, node, expected);
    }
    case "while":
    case "for_numeric":
    case "for_iter":
    case "repeat": {
      return emit_loop_value(g, node, expected);
    }
    case "switch": {
      return emit_switch_value(g, node, expected);
    }
    case "match": {
      return emit_match_value(g, node, expected);
    }
    case "comprehension": {
      return emit_comprehension(g, node, expected);
    }
    case "do": {
      return capture_iife(g, () => emit_value_block(g, node.block, expected));
    }
    case "unsafe": {
      return capture_iife(g, () => emit_value_block(g, node.block, expected));
    }
    case "await": {
      if (g.await_depth === 0) {
        js_error(
          g,
          "«await» fuera de una función «async»: el checker debería haberlo rechazado",
          node.span,
        );
      }
      g.await_seen += 1;
      return `await (${emit_expr(g, node.value)})`;
    }
    case "lambda": {
      return emit_lambda(g, node);
    }
    default: {
      js_error(
        g,
        `la expresión «${node.kind}» todavía no se emite a JavaScript (fase posterior del plan)`,
        node.span,
      );
      return "undefined";
    }
  }
}

function type_args(g: JsContext, node: ExprNode): readonly PenguType[] {
  const type = expression_type(g, node);
  return type.kind === "named" ? type.args : [];
}

function emit_ident(g: JsContext, name: string, span: ExprNode["span"]): string {
  if (is_local_declared(g, name)) return js_identifier(name);
  const unit = current_unit(g);
  const module = unit.module;
  const realm = module.realm;
  const imported = unit.selective_symbols.get(name);
  if (imported !== undefined) {
    ensure_realm(g, imported.realm);
    return cross_reference(g, imported.realm, imported.name);
  }
  if (module.consts.has(name)) {
    ensure_constant(g, realm, name);
    return symbol_name(g, name);
  }
  if (module.functions.has(name)) {
    ensure_function(g, realm, name);
    return cross_reference(g, realm, name);
  }
  js_error(g, `no se encontró el símbolo «${name}» al emitir JavaScript`, span);
  return "undefined";
}

// Índice numérico como `number`: en PenguScript los índices son `size_t` (64
// bits), pero un array de JS se indexa con números (§2.2).
export function emit_index_number(g: JsContext, node: ExprNode): string {
  const type = expression_type(g, node);
  const code = emit_expr(g, node, INT);
  if (is_64_bit_integer(type)) return `Number(${code})`;
  return code;
}

// Destino de una asignación a un índice: `obj[i]` para secuencias y
// `obj.set(k, v)` para mapas; `rt.vec_at`/`rt.map_at` solo leen.
export function emit_store_target(
  g: JsContext,
  node: Extract<ExprNode, { kind: "index" }>,
  value: string,
  operator: string,
): string {
  const object = emit_expr(g, node.object);
  const operator_index = rune_index_call(g, node);
  if (operator_index !== undefined) {
    if (operator === "=") return `${operator_index}.value = ${value}`;
    return `${operator_index}.value ${operator} ${value}`;
  }
  const index = emit_index_number(g, node.index);
  const type = expression_type(g, node.object);
  const container = type.kind === "named" ? type.name : "";
  if (container === "map" || container === "unordered_map" || container === "multimap") {
    if (operator === "=") return `${object}.set(${index}, ${value})`;
    runtime_name(g);
    return `${object}.set(${index}, rt.map_at(${object}, ${index}) ${operator.slice(0, -1)} ${value})`;
  }
  if (operator === "=") return `${object}[${index}] = ${value}`;
  return `${object}[${index}] ${operator} ${value}`;
}

// `operator []` de un rune devuelve `ref<T>`: se lee y se escribe por `.value`.
function rune_index_call(
  g: JsContext,
  node: Extract<ExprNode, { kind: "index" }>,
): string | undefined {
  const type = expression_type(g, node.object);
  if (type.kind !== "named") return undefined;
  const realm = realm_of_type(g, type.name) ?? current_unit(g).module.realm;
  const owner = rune_operator_owner(g, realm, type.name, "[]");
  if (owner === undefined) return undefined;
  const exported = free_method_export(owner.type, operator_method_name("[]"));
  const target = cross_reference(g, owner.realm, exported);
  const object = emit_expr(g, node.object);
  const index = emit_index_number(g, node.index);
  return `${target}(${object}, ${index})`;
}

function emit_index(g: JsContext, node: Extract<ExprNode, { kind: "index" }>): string {
  const operator_index = rune_index_call(g, node);
  if (operator_index !== undefined) return `${operator_index}.value`;
  const object = emit_expr(g, node.object);
  const index = emit_index_number(g, node.index);
  const type = expression_type(g, node.object);
  const container = type.kind === "named" ? type.name : "";
  if (container === "array" || container === "span") return `${object}[${index}]`;
  if (is_string(type)) return `${object}[${index}]`;
  runtime_name(g);
  if (container === "map" || container === "unordered_map") return `rt.map_at(${object}, ${index})`;
  return `rt.vec_at(${object}, ${index})`;
}

function emit_unary(g: JsContext, node: Extract<ExprNode, { kind: "unary" }>): string {
  const op = node.op;
  if (op === "not" || op === "!") return `!(${emit_expr(g, node.operand)})`;
  if (op === "#") {
    runtime_name(g);
    return `rt.len(${emit_expr(g, node.operand)})`;
  }
  const unary_operator = unary_rune_operator(g, node, op);
  if (unary_operator !== undefined) return unary_operator;
  if (op === "-") return `-(${emit_expr(g, node.operand)})`;
  if (op === "~") return `~(${emit_expr(g, node.operand)})`;
  if (op === "+") return `+(${emit_expr(g, node.operand)})`;
  js_error(g, `el operador unario «${op}» todavía no se emite a JavaScript (fase P3)`, node.span);
  return "undefined";
}


// Tipo de un operando: el declarado de una variable manda sobre la anotación
// del checker (que puede haber perdido el nombre del alias o del rune).
function operand_type(g: JsContext, node: ExprNode): PenguType {
  if (node.kind === "ident") {
    const declared = local_type(g, node.name);
    if (declared !== undefined) return declared;
  }
  return expression_type(g, node);
}


// Operador unario declarado por un rune (`operator -` sin parámetros): `-p` →
// `Punto__op_sub(p)`.
function unary_rune_operator(
  g: JsContext,
  node: Extract<ExprNode, { kind: "unary" }>,
  op: string,
): string | undefined {
  if (op !== "-" && op !== "+" && op !== "~") return undefined;
  const type = operand_type(g, node.operand);
  if (type.kind !== "named") return undefined;
  const realm = realm_of_type(g, type.name);
  if (realm === undefined) return undefined;
  const owner = rune_operator_owner(g, realm, type.name, op);
  if (owner === undefined) return undefined;
  const callable = cross_reference(g, owner.realm, free_method_export(owner.type, operator_method_name(op)));
  return `${callable}(${emit_expr(g, node.operand)})`;
}

function emit_binary(g: JsContext, node: Extract<ExprNode, { kind: "binary" }>): string {
  const op = node.op;
  const result = expression_type(g, node);
  const left_type = operand_type(g, node.left);
  const right_type = operand_type(g, node.right);

  if (op === "and") return `(${emit_expr(g, node.left, left_type)} && ${emit_expr(g, node.right, right_type)})`;
  if (op === "or") return `(${emit_expr(g, node.left, left_type)} || ${emit_expr(g, node.right, right_type)})`;
  if (op === "in") {
    runtime_name(g);
    return `rt.contains(${emit_expr(g, node.right)}, ${emit_expr(g, node.left)})`;
  }
  const operator = rune_operator_call(g, node, op, left_type, right_type);
  if (operator !== undefined) return operator;

  if (op === "<=>") {
    runtime_name(g);
    return `rt.compare(${emit_expr(g, node.left)}, ${emit_expr(g, node.right)})`;
  }

  const comparison =
    op === "==" || op === "!=" || op === "<" || op === "<=" || op === ">" || op === ">=";
  const target = comparison ? right_type : result;
  const left = coerce(g, emit_expr(g, node.left, target), left_type, target);
  const right = coerce(g, emit_expr(g, node.right, comparison ? left_type : result), right_type, target);

  if (op === "==" || op === "!=") {
    const any_bigint = num_kind(left_type, g) === "bigint" || num_kind(right_type, g) === "bigint";
    const js_op = any_bigint ? op : `${op}=`;
    return `(${left} ${js_op} ${right})`;
  }
  if (comparison) return `(${left} ${op} ${right})`;

  if (op === "/" && is_integer(result) && !is_bigint_type(result, g.mode)) {
    return `Math.trunc(${left} / ${right})`;
  }
  if (op === ">>" && js_integer_kind(result) === "uint32") {
    return `(${left} >>> ${right})`;
  }
  return `(${left} ${op} ${right})`;
}

function emit_cast(g: JsContext, node: Extract<ExprNode, { kind: "cast" }>): string {
  const value = emit_expr(g, node.value);
  const target = expression_type(g, node);
  const source = expression_type(g, node.value);
  const target_kind = num_kind(target, g);
  const source_kind = num_kind(source, g);

  // `char` es una cadena de un carácter en JS: hay que convertir el code unit.
  if (is_char(source) && target_kind === "int") return `(${value}).charCodeAt(0)`;
  if (is_char(target) && source_kind !== undefined && source_kind !== "float") {
    return `String.fromCharCode(${value})`;
  }

  if (target_kind === "bigint") {
    if (source_kind === "float") return `BigInt(Math.trunc(${value}))`;
    return `BigInt(${value})`;
  }
  if (target_kind === "float") return `Number(${value})`;
  if (target_kind === "int") {
    const kind = js_integer_kind(target);
    if (kind !== undefined) return js_int_normalizer(kind)(value);
    return `Number(${value})`;
  }
  // `seal` y `echo` se borran en tiempo de ejecución: el cast es identidad.
  if (is_string(target) && is_integer(source)) return `String.fromCharCode(${value})`;
  return `(${value})`;
}

function emit_string_lit(g: JsContext, parts: readonly StringPartNode[]): string {
  if (parts.length === 1) {
    const only = parts[0];
    if (only !== undefined && only.kind === "text_part") return js_string_literal(only.text);
  }
  const pieces = parts.map((part) => {
    if (part.kind === "text_part") return escape_template(part.text);
    const type = expression_type(g, part.expr);
    const code = emit_expr(g, part.expr, type);
    if (is_string(type)) return `\${${code}}`;
    runtime_name(g);
    if (type.kind === "tuple" || (type.kind === "named" && type.name === "pair")) {
      return `\${rt.show_tuple(${code})}`;
    }
    // Un rune con `to_string` en su `enchanting` es dueño de su presentación,
    // como `to_string_value` en el runtime C++ (§5.2).
    const renderer = show_renderer(g, type);
    if (renderer !== undefined) return `\${${renderer}(${code})}`;
    // Un contenedor de runes con `to_string`: cada elemento se presenta igual.
    const element = element_renderer(g, type);
    if (element !== undefined) {
      return `\${rt.show_list(${code}.map((_x) => ${element}(_x)))}`;
    }
    return `\${rt.show(${code})}`;
  });
  return `\`${pieces.join("")}\``;
}


// Función libre `Tipo__to_string` si el rune declara `to_string`.
function show_renderer(g: JsContext, type: PenguType): string | undefined {
  if (type.kind !== "named") return undefined;
  const realm = realm_of_type(g, type.name);
  if (realm === undefined) return undefined;
  const unit = g.units.get(realm);
  const rune = unit?.module.env.runes.get(type.name);
  if (rune === undefined || !rune.methods.has("to_string")) return undefined;
  return cross_reference(g, realm, free_method_export(type.name, "to_string"));
}

// Renderizador de los elementos de un contenedor de runes con `to_string`.
function element_renderer(g: JsContext, type: PenguType): string | undefined {
  if (type.kind !== "named") return undefined;
  if (type.name !== "vector" && type.name !== "array" && type.name !== "set") return undefined;
  const inner = type.args[0];
  return inner === undefined ? undefined : show_renderer(g, inner);
}

function escape_template(text: string): string {
  return js_string_literal(text).slice(1, -1).replace(/`/g, "\\`").replace(/\$\{/g, "\\${");
}

function emit_lambda(g: JsContext, node: Extract<ExprNode, { kind: "lambda" }>): string {
  const params = node.params.map((param) => {
    const name = js_identifier(param.name);
    if (param.default_value !== undefined) return `${name} = ${emit_expr(g, param.default_value)}`;
    return name;
  });
  const result = node.result === undefined ? undefined : expression_type(g, node);
  const saved_return = g.return_type;
  const saved_async = g.await_depth;
  push_scope(g);
  for (const param of node.params) declare_local_name(g, param.name);
  g.return_type = result;
  g.await_depth = node.is_async ? saved_async + 1 : 0;
  const body = capture_lines(
    g,
    () => emit_value_block(g, node.body, result),
    g.indent + 1,
  );
  pop_scope(g);
  g.return_type = saved_return;
  g.await_depth = saved_async;
  const indent = "  ".repeat(g.indent);
  return `(${node.is_async ? "async " : ""}(${params.join(", ")}) => {\n${body}\n${indent}})`;
}

function declare_local_name(g: JsContext, name: string): void {
  const scope = g.scopes[g.scopes.length - 1];
  if (scope !== undefined) scope.push(js_identifier(name));
}

// `if` como expresión: ternario cuando ambas ramas son una sola expresión,
// IIFE (que devuelve) cuando hay sentencias de por medio.
function emit_if(g: JsContext, node: Extract<ExprNode, { kind: "if" }>, expected?: PenguType): string {
  const condition = condition_code(g, node);
  const then_expr = single_expression(node.then_block);
  const else_expr = node.else_block === undefined ? undefined : single_expression(node.else_block);
  if (then_expr !== undefined && else_expr !== undefined) {
    return `(${condition} ? ${emit_expr(g, then_expr, expected)} : ${emit_expr(g, else_expr, expected)})`;
  }
  return capture_iife(g, () => {
    emit_if_statement(g, node, expected, true);
  });
}

function condition_code(g: JsContext, node: Extract<ExprNode, { kind: "if" }>): string {
  const code = emit_expr(g, node.condition);
  return node.unless === true ? `!(${code})` : code;
}

function single_expression(block: Block): ExprNode | undefined {
  if (block.statements.length !== 1) return undefined;
  const only = block.statements[0];
  if (only === undefined || only.kind !== "expr_stmt") return undefined;
  return only.expr;
}

export function emit_if_statement(
  g: JsContext,
  node: Extract<ExprNode, { kind: "if" }>,
  expected?: PenguType,
  value_branches = false,
): void {
  line(g, `if (${condition_code(g, node)}) {`);
  emit_branch(g, node.then_block, expected, value_branches);
  if (node.else_block !== undefined) {
    line(g, "} else {");
    emit_branch(g, node.else_block, expected, value_branches);
  }
  line(g, "}");
}

function emit_branch(
  g: JsContext,
  block: Block,
  expected: PenguType | undefined,
  value: boolean,
): void {
  push_scope(g);
  g.indent += 1;
  if (value) {
    emit_value_block(g, block, expected);
  } else {
    for (const statement of block.statements) emit_statement(g, statement);
  }
  g.indent -= 1;
  pop_scope(g);
}

// Emisión como sentencia de una expresión de control (los `break`/`return`
// must stay reales: no se encierran en una lambda).
export function emit_as_statement(g: JsContext, node: ExprNode): void {
  switch (node.kind) {
    case "if": {
      emit_if_statement(g, node);
      return;
    }
    case "do": {
      emit_value_block(g, node.block, undefined);
      return;
    }
    case "unsafe": {
      for (const statement of node.block.statements) emit_statement(g, statement);
      return;
    }
    case "while":
    case "for_numeric":
    case "for_iter":
    case "repeat": {
      emit_loop_statement(g, node);
      return;
    }
    case "switch": {
      emit_switch_statement(g, node);
      return;
    }
    case "match": {
      emit_match_statement(g, node);
      return;
    }
    default: {
      js_error(
        g,
        `la expresión «${node.kind}» todavía no se emite como sentencia (fase P2)`,
        node.span,
      );
    }
  }
}

export type LoopNode = Extract<ExprNode, { kind: "while" | "repeat" | "for_numeric" | "for_iter" }>;

// Un bucle puede devolver valor (`break valor`) y llevar `else` (se ejecuta
// solo si no hubo `break`). JS no tiene ninguna de las dos cosas: se emite un
// flag `_cortadoN` y, si hay valor, un IIFE con `_resN`.
interface LoopBreak {
  readonly flag: string;
  readonly slot: string;
}

const PLAIN_BREAK: LoopBreak = { flag: "", slot: "" };

function loop_else(node: LoopNode): Block | undefined {
  return "else_block" in node ? node.else_block : undefined;
}

export function emit_loop_statement(g: JsContext, node: LoopNode): void {
  const else_block = loop_else(node);
  const flag = else_block === undefined ? "" : fresh_name(g, "cortado");
  if (flag !== "") line(g, `let ${flag} = false;`);
  // Un `break valor` en posición de sentencia descarta el valor, pero la
  // asignación tiene que existir para no romper el flujo.
  const wants_value = expression_type(g, node).kind === "optional";
  const slot = wants_value ? fresh_name(g, "descartado") : "";
  if (slot !== "") line(g, `let ${slot} = null;`);
  emit_loop_core(g, node, { flag, slot });
  if (else_block !== undefined) {
    line(g, `if (!${flag}) {`);
    emit_branch(g, else_block, undefined, false);
    line(g, "}");
  }
}

export function emit_loop_value(g: JsContext, node: LoopNode, expected?: PenguType): string {
  const result = expected ?? expression_type(g, node);
  const else_block = loop_else(node);
  return capture_iife(g, () => {
    const slot = fresh_name(g, "res");
    line(g, `let ${slot} = ${js_default_value(result, g.mode)};`);
    const flag = else_block === undefined ? "" : fresh_name(g, "cortado");
    if (flag !== "") line(g, `let ${flag} = false;`);
    emit_loop_core(g, node, { flag, slot });
    if (else_block !== undefined) {
      line(g, `if (!${flag}) {`);
      emit_value_block(g, else_block, result);
      line(g, "}");
    }
    line(g, `return ${slot};`);
  });
}

function emit_loop_core(g: JsContext, node: LoopNode, brk: LoopBreak): void {
  g.break_flags.push(brk.flag);
  g.break_values.push(brk.slot);
  try {
    switch (node.kind) {
      case "while": {
        emit_while(g, node);
        return;
      }
      case "repeat": {
        emit_repeat(g, node);
        return;
      }
      case "for_numeric": {
        emit_for_numeric(g, node);
        return;
      }
      default: {
        emit_for_iter(g, node);
      }
    }
  } finally {
    g.break_flags.pop();
    g.break_values.pop();
  }
}

function emit_while(g: JsContext, node: Extract<ExprNode, { kind: "while" }>): void {
  const code = emit_expr(g, node.condition);
  const condition = node.until === true ? `!(${code})` : code;
  line(g, `while (${condition}) {`);
  emit_loop_body(g, node.body);
  line(g, "}");
}

// `repeat … until c` repite *mientras* `c` sea falsa: `do { } while (!c)`.
function emit_repeat(g: JsContext, node: Extract<ExprNode, { kind: "repeat" }>): void {
  const condition = emit_expr(g, node.condition);
  line(g, "do {");
  emit_loop_body(g, node.body);
  line(g, `} while (!(${condition}));`);
}

function emit_loop_body(g: JsContext, block: Block): void {
  push_scope(g);
  g.indent += 1;
  for (const statement of block.statements) emit_statement(g, statement);
  g.indent -= 1;
  pop_scope(g);
}

function emit_for_numeric(g: JsContext, node: Extract<ExprNode, { kind: "for_numeric" }>): void {
  const variable = js_identifier(node.variable);
  const start = emit_expr(g, node.start);
  const end = emit_expr(g, node.end);
  const step = node.step;
  push_scope(g);
  declare_local_name(g, node.variable);

  if (step === undefined) {
    line(g, `for (let ${variable} = ${start}; ${variable} <= ${end}; ${variable} += 1) {`);
  } else if (step.kind === "int_lit") {
    const negative = step.value.startsWith("-");
    line(
      g,
      `for (let ${variable} = ${start}; ${variable} ${negative ? ">=" : "<="} ${end}; ${variable} += ${step.value}) {`,
    );
  } else {
    const name = `${variable}_paso`;
    line(
      g,
      `for (let ${variable} = ${start}, ${name} = ${emit_expr(g, step)}; ${name} > 0 ? ${variable} <= ${end} : ${variable} >= ${end}; ${variable} += ${name}) {`,
    );
  }
  g.indent += 1;
  for (const statement of node.body.statements) emit_statement(g, statement);
  g.indent -= 1;
  line(g, "}");
  pop_scope(g);
}

function emit_for_iter(g: JsContext, node: Extract<ExprNode, { kind: "for_iter" }>): void {
  push_scope(g);
  const variables = node.variables.map((name) => js_identifier(name));
  for (const name of node.variables) declare_local_name(g, name);

  if (node.iterable.kind === "range") {
    runtime_name(g);
    const start = emit_expr(g, node.iterable.start);
    const end = emit_expr(g, node.iterable.end);
    const flag = node.iterable.inclusive ? "true" : "false";
    line(g, `for (const ${variables[0] ?? "_"} of rt.range(${start}, ${end}, ${flag})) {`);
    g.indent += 1;
    for (const statement of node.body.statements) emit_statement(g, statement);
    g.indent -= 1;
    line(g, "}");
  } else if (variables.length > 1) {
    const pair = `_par${g.temp}`;
    g.temp += 1;
    line(g, `for (const ${pair} of ${emit_expr(g, node.iterable)}) {`);
    push_scope(g);
    g.indent += 1;
    for (const name of node.variables) declare_local_name(g, name);
    line(g, `const [${variables.join(", ")}] = ${pair};`);
    for (const statement of node.body.statements) emit_statement(g, statement);
    g.indent -= 1;
    pop_scope(g);
    line(g, "}");
  } else {
    line(g, `for (const ${variables[0] ?? "_"} of ${emit_expr(g, node.iterable)}) {`);
    g.indent += 1;
    for (const statement of node.body.statements) emit_statement(g, statement);
    g.indent -= 1;
    line(g, "}");
  }

  pop_scope(g);
}

// Cuerpo con valor: la última expresión se convierte en `return`; si no hay
// ninguna (o es una estructura de control), se devuelve el valor por defecto.
export function emit_value_block(g: JsContext, block: Block, result: PenguType | undefined): void {
  const last = block.statements[block.statements.length - 1];
  const value_expr = last !== undefined && last.kind === "expr_stmt" ? last.expr : undefined;
  const expr_type = value_expr === undefined ? undefined : expression_type(g, value_expr);
  const declared_value = result !== undefined && !is_voidish(result) && result.kind !== "any";
  const returns_implicitly =
    value_expr !== undefined &&
    (declared_value ||
      (expr_type !== undefined && !is_voidish(expr_type) && expr_type.kind !== "any"));
  for (const statement of block.statements) {
    if (returns_implicitly && statement === last && statement.kind === "expr_stmt") {
      line(g, `return ${emit_expr(g, statement.expr, result)};`);
      continue;
    }
    emit_statement(g, statement);
  }
  if (!returns_implicitly && result !== undefined && needs_default(result)) {
    line(g, `return ${js_default_value(result, g.mode)};`);
  }
}

// `none` y `void` significan "no devuelve nada": ni `return` implícito ni
// valor por defecto.
export function is_voidish(type: PenguType): boolean {
  return is_void(type) || type.kind === "none" || type.kind === "any";
}

// Una función sin tipo de retorno declarado (`any`) devuelve lo que devuelva
// su última expresión; no se le añade un `return` sintético.
function needs_default(result: PenguType | undefined): boolean {
  if (result === undefined) return false;
  if (result.kind === "any") return false;
  return !is_voidish(result);
}

// `if`, `while`, `for`, `switch` y `match` como valor necesitan un `return`
// real dentro de su IIFE; como sentencia, no.
export function is_control_expr(node: ExprNode): boolean {
  return (
    node.kind === "if" ||
    node.kind === "while" ||
    node.kind === "for_numeric" ||
    node.kind === "for_iter" ||
    node.kind === "repeat" ||
    node.kind === "switch" ||
    node.kind === "match"
  );
}

// --- Captura de bloques ---------------------------------------------------
// Las expresiones que necesitan un cuerpo con `return` (IIFE) emiten sus
// líneas en una lista aparte y se incrustan como texto.

export function capture_lines(g: JsContext, body: () => void, indent?: number): string {
  const saved_file = g.file;
  const saved_indent = g.indent;
  const captured: string[] = [];
  g.file = { ...saved_file, lines: captured };
  g.indent = indent ?? 0;
  g.file = { ...saved_file, lines: captured };
  try {
    body();
  } finally {
    // `uses_rt` es un booleano: el objeto temporal lo copia, así que se
    // propaga a mano al archivo real.
    saved_file.uses_rt = saved_file.uses_rt || g.file.uses_rt;
    g.file = saved_file;
    g.indent = saved_indent;
  }
  return captured.join("\n");
}

export function capture_iife(g: JsContext, body: () => void): string {
  const before = g.await_seen;
  const inner = capture_lines(g, body, g.indent + 1);
  const indent = "  ".repeat(g.indent);
  const opening = inner.length === 0 ? "" : `\n${inner}\n${indent}`;
  // Una IIFE con `await` dentro tiene que ser `async` y esperarse: si no, el
  // `await` quedaría fuera de una función `async` (error de sintaxis).
  if (g.await_seen > before) return `await (async () => {${opening}})()`;
  return `(() => {${opening}})()`;
}

// Operadores declarados por un `rune`: `p + q` → `p.op_add(q)`. Las
// comparaciones derivan de `<=>` cuando no hay método propio (§4.4).
function rune_operator_call(
  g: JsContext,
  node: Extract<ExprNode, { kind: "binary" }>,
  op: string,
  left_type: PenguType,
  right_type: PenguType,
): string | undefined {
  const left = emit_expr(g, node.left);
  const right = emit_expr(g, node.right);
  if (left_type.kind !== "named") {
    // Operador libre con el tipo a la derecha (`2 * p`).
    const free = free_operator_function(g, op, left_type, right_type);
    if (free === undefined) return undefined;
    const exported = free_operator_name(`operator ${op}`) ?? op;
    ensure_function(g, free.realm, `operator ${op}`);
    const target = cross_reference(g, free.realm, exported);
    return `${target}(${left}, ${right})`;
  }
  const realm = realm_of_type(g, left_type.name) ?? current_unit(g).module.realm;
  const direct = rune_operator_owner(g, realm, left_type.name, op);
  if (direct !== undefined) {
    const exported = free_method_export(direct.type, operator_method_name(op));
    const target = cross_reference(g, direct.realm, exported);
    return `${target}(${left}, ${right})`;
  }
  if (op === "<" || op === "<=" || op === ">" || op === ">=") {
    const cmp = rune_operator_owner(g, realm, left_type.name, "<=>");
    if (cmp !== undefined) {
      const exported = free_method_export(cmp.type, operator_method_name("<=>"));
      const target = cross_reference(g, cmp.realm, exported);
      return `(${target}(${left}, ${right}) ${op} 0)`;
    }
  }
  // Operador libre (`operator * = (escala: int, p: Punto)`): una función del
  // programa con dos parámetros que aceptan los operandos (§4.4).
  const free = free_operator_function(g, op, left_type, right_type);
  if (free !== undefined) {
    const exported = free_operator_name(`operator ${op}`) ?? op;
    ensure_function(g, free.realm, `operator ${op}`);
    const target = cross_reference(g, free.realm, exported);
    return `${target}(${left}, ${right})`;
  }
  return undefined;
}

// Operador definido como función libre en cualquier realm del programa.
function free_operator_function(
  g: JsContext,
  op: string,
  left_type: PenguType,
  right_type: PenguType,
): { realm: string } | undefined {
  const wanted = `operator ${op}`;
  for (const unit of g.units.values()) {
    for (const info of unit.module.functions.values()) {
      if (info.name !== wanted || info.params.length !== 2) continue;
      const [first, second] = info.params;
      if (first === undefined || second === undefined) continue;
      if (!accepts_operand(first.type, left_type)) continue;
      if (!accepts_operand(second.type, right_type)) continue;
      return { realm: unit.module.realm };
    }
  }
  return undefined;
}

function accepts_operand(parameter: PenguType, operand: PenguType): boolean {
  if (parameter.kind === "any" || parameter.kind === "named") {
    // Un parámetro genérico (`T`) acepta cualquier cosa.
    return parameter.kind === "any" || type_equals(parameter, operand) || operand.kind === "named";
  }
  return type_equals(parameter, operand);
}
