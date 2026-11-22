// Emisión de expresiones a C++20.
//
// Las expresiones de control (`if`, `switch`, `match`, bucles) se
// traducen a lambdas invocadas al momento: así conservan su valor sin
// inventar sentencias temporales en el lugar del uso.

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
import {
  emit_binary,
  emit_call,
  emit_cast,
  emit_index,
  emit_map_lit,
  emit_path,
  emit_set_lit,
  emit_unary,
  emit_vector_lit,
} from "./cpp_expr_call.ts";
import {
  build_lambda,
  emit_comprehension,
  emit_for_iter,
  emit_for_numeric,
  emit_if,
  emit_lambda,
  emit_match,
  emit_repeat,
  emit_switch,
  emit_while,
} from "./cpp_expr_control.ts";

// `x.metodo` sin llamada: el checker anotó la función libre y su firma.
function emit_enchanted_member_value(
  g: GenContext,
  node: ExprNode,
  target: { readonly realm: string; readonly name: string },
  type: Extract<PenguType, { kind: "function" }>,
): string {
  const object = node.kind === "member" ? emit_expr(g, node.object) : "(*this)";
  const params = type.params.map((param, index) => `const ${cpp_type(param, g.type_realms)}& _a${index}`);
  const args = type.params.map((_param, index) => `_a${index}`);
  const result = cpp_type(type.result, g.type_realms);
  const callee = `${sanitize_namespace(target.realm)}::${cpp_identifier(target.name)}`;
  const call_args = ["self", ...args].join(", ");
  return `[self = ${object}](${params.join(", ")}) -> ${result} { return ${callee}(${call_args}); }`;
}

export function emit_expr(g: GenContext, node: ExprNode): string {
  switch (node.kind) {
    case "container_new": {
      if (node.name === "bitset") {
        const size = node.size === undefined ? "1" : emit_expr(g, node.size);
        const inner = node.args.length > 0 ? emit_expr(g, node.args[0]!.expr) : "0";
        return `std::bitset<${size}>(${inner})`;
      }
      const type_args = node.type_args.map((arg) => resolve_type_node(arg, g.module.env, g.sink));
      const container = STRING_TYPES.has(node.name) && type_args.length === 0 ? primitive(node.name) : named(node.name, type_args);
      const rendered = cpp_type(container, g.type_realms);
      const args = node.args.map((arg) => emit_expr(g, arg.expr)).join(", ");
      if (node.name === "variant" && node.args.length === 1) {
        const value = node.args[0]!.expr;
        const index = type_args.findIndex((option) => type_equals(option, type_of(g, value)));
        if (index >= 0) {
          return `${rendered}{std::in_place_index<${index}>, ${args}}`;
        }
      }
      return `${rendered}{${args}}`;
    }
    case "int_lit":
      return node.value;
    case "float_lit":
      return node.value;
    case "bool_lit":
      return node.value ? "true" : "false";
    case "char_lit":
      return cpp_char(node.value);
    case "string_lit":
      return emit_string(g, node.parts);
    case "none_lit":
      return "std::nullopt";
    case "nullptr_lit":
      return "nullptr";
    case "ident": {
      const imported_realm = g.selective_realms.get(node.name);
      if (
        imported_realm !== undefined &&
        !is_local_declared(g, node.name) &&
        !g.module.functions.has(node.name) &&
        !g.module.consts.has(node.name)
      ) {
        return `${sanitize_namespace(imported_realm)}::${cpp_identifier(node.name)}`;
      }
      return cpp_identifier(node.name);
    }
    case "self":
      return g.self_expression ?? "(*this)";
    case "path":
      return emit_path(g, node.segments);
    case "parent_call":
      gc_error(g, "«parent» solo puede aparecer como primera sentencia de un constructor", node.span);
      return "/* parent */";
    case "member": {
      // `enchanting` sobre un tipo incorporado: el checker anotó la
      // función libre, no un acceso a miembro.
      const enchanted = g.member_targets.get(node);
      if (enchanted !== undefined) {
        const function_type = type_of(g, node);
        if (function_type.kind === "function") {
          // Uso como valor: se captura el receptor por valor y se envuelve la
          // función libre en una lambda con la firma esperada.
          return emit_enchanted_member_value(g, node, enchanted, function_type);
        }
        return `${sanitize_namespace(enchanted.realm)}::${cpp_identifier(enchanted.name)}(${emit_expr(g, node.object)})`;
      }
      const object_code = emit_expr(g, node.object);
      const object_type = type_of(g, node.object);
      // `std::pair` tiene `.first`/`.second`; `std::tuple` no.
      const is_tuple =
        object_type.kind === "tuple" || (object_type.kind === "named" && object_type.name === "tuple");
      if (is_tuple && (node.name === "first" || node.name === "second")) {
        return `std::get<${node.name === "first" ? 0 : 1}>(${object_code})`;
      }
      const arrow =
        object_type.kind === "unique" || object_type.kind === "shared" || object_type.kind === "raw";
      return `${object_code}${arrow ? "->" : "."}${cpp_identifier(node.name)}`;
    }
    case "index":
      return emit_index(g, node.object, node.index);
    case "call":
      return emit_call(g, node);
    case "unary":
      return emit_unary(g, node);
    case "binary":
      return emit_binary(g, node);
    case "cast":
      return emit_cast(g, node);
    case "range":
      return `::pengu::Range{${emit_expr(g, node.start)}, ${emit_expr(g, node.end)}, ${node.inclusive ? "true" : "false"}}`;
    case "tuple": {
      const items = node.items.map((item) => emit_expr(g, item));
      const type = type_of(g, node);
      if (type.kind === "named" && (type.name === "pair" || type.name === "tuple")) {
        const args = type.args.map((arg) => cpp_type(arg, g.type_realms)).join(", ");
        return `std::${type.name}<${args}>{${items.join(", ")}}`;
      }
      return `std::make_tuple(${items.join(", ")})`;
    }
    case "vector_lit":
      return emit_vector_lit(g, node);
    case "map_lit":
      return emit_map_lit(g, node);
    case "set_lit":
      return emit_set_lit(g, node);
    case "comprehension":
      return emit_comprehension(g, node);
    case "if":
      return emit_if(g, node);
    case "switch":
      return emit_switch(g, node);
    case "match":
      return emit_match(g, node);
    case "do":
      return build_lambda(g, "", cpp_value_type(type_of(g, node), g.type_realms), () => {
        emit_value_block(g, node.block, cpp_value_type(type_of(g, node), g.type_realms));
      }) + "()";
    case "while":
      return emit_while(g, node);
    case "repeat":
      return emit_repeat(g, node);
    case "for_numeric":
      return emit_for_numeric(g, node);
    case "for_iter":
      return emit_for_iter(g, node);
    case "lambda":
      return emit_lambda(g, node);
    case "unsafe":
      return build_lambda(g, "", cpp_value_type(type_of(g, node), g.type_realms), () => {
        emit_value_block(g, node.block, cpp_value_type(type_of(g, node), g.type_realms));
      }) + "()";
  }
}

export function cpp_string(text: string): string {
  let out = '"';
  for (const char of text) {
    switch (char) {
      case "\\":
        out += "\\\\";
        break;
      case '"':
        out += '\\"';
        break;
      case "\n":
        out += "\\n";
        break;
      case "\t":
        out += "\\t";
        break;
      case "\r":
        out += "\\r";
        break;
      default:
        out += char;
        break;
    }
  }
  return `${out}"`;
}

function cpp_char(text: string): string {
  if (text === "\\") return "'\\\\'";
  if (text === "'") return "'\\''";
  if (text === "\n") return "'\\n'";
  if (text === "\t") return "'\\t'";
  return `'${text}'`;
}

function emit_string(g: GenContext, parts: readonly import("../frontend/ast_expr.ts").StringPartNode[]): string {
  if (parts.length === 1 && parts[0] !== undefined && parts[0].kind === "text_part") {
    return `std::string(${cpp_string((parts[0] as { text: string }).text)})`;
  }
  const pieces: string[] = [];
  for (const part of parts) {
    if (part.kind === "text_part") {
      pieces.push(`std::string(${cpp_string(part.text)})`);
    } else {
      pieces.push(`::pengu::to_string(${emit_expr(g, part.expr)})`);
    }
  }
  return pieces.length === 0 ? "std::string()" : `(${pieces.join(" + ")})`;
}


// El resto de la emisión vive en módulos aparte; se reexporta para que
// `cpp_stmt`, `cpp_decl` y `cpp_module` sigan importando desde aquí.
export { emit_call, emit_index, emit_member_call, emit_vector_lit, emit_map_lit, emit_set_lit } from "./cpp_expr_call.ts";
export { emit_as_statement, build_lambda } from "./cpp_expr_control.ts";
export { BUILTIN_FUNCTIONS, BUILTIN_CONSTANTS } from "./cpp_expr_call.ts";
