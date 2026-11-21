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
import { is_map_type, is_sequence_container } from "../semantic/builtin_members.ts";
import type { PenguType } from "../semantic/types.ts";
import { emit_block, emit_value_block } from "./cpp_stmt.ts";

export function emit_expr(g: GenContext, node: ExprNode): string {
  switch (node.kind) {
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
      return g.self_value ? "value" : "(*this)";
    case "path":
      return emit_path(g, node.segments);
    case "parent_call":
      gc_error(g, "«parent» solo puede aparecer como primera sentencia de un constructor", node.span);
      return "/* parent */";
    case "member": {
      const object_code = emit_expr(g, node.object);
      const object_type = type_of(g, node.object);
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
    case "tuple":
      return `std::make_tuple(${node.items.map((item) => emit_expr(g, item)).join(", ")})`;
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

function emit_index(g: GenContext, object: ExprNode, index: ExprNode): string {
  const object_type = type_of(g, object);
  const rendered = `${emit_expr(g, object)}, ${emit_expr(g, index)}`;
  return is_map_type(object_type)
    ? `::pengu::map_at(${rendered})`
    : `::pengu::vec_at(${rendered})`;
}

function emit_call(g: GenContext, node: CallNode): string {
  const callee_type = type_of(g, node.callee);
  const params = callee_type.kind === "function" ? callee_type.params : [];
  const args = node.args
    .map((arg, index) => {
      const rendered = emit_expr(g, arg.expr);
      const param = params[index];
      // Pasar un `unique<T>` por valor lo mueve.
      return param?.kind === "unique" && !arg.mutable ? `std::move(${rendered})` : rendered;
    })
    .join(", ");
  const callee = node.callee;
  const type_args = node.type_args.map((arg) => cpp_type_node(arg, g.module.env, g.type_realms));
  if (callee.kind === "ident") {
    return emit_ident_call(g, callee.name, type_args, args, node);
  }
  if (callee.kind === "path") {
    return emit_path_call(g, callee.segments, type_args, args);
  }
  if (callee.kind === "member") {
    return emit_member_call(g, callee.object, callee.name, args);
  }
  return `(${emit_expr(g, callee)})(${args})`;
}

export const BUILTIN_FUNCTIONS: Readonly<Record<string, string>> = {
  "io::println": "::pengu::println",
  "io::print": "::pengu::print",
  "io::eprintln": "::pengu::eprintln",
  "io::eprint": "::pengu::eprint",
  "io::read_line": "::pengu::read_line",
  "format::format": "::pengu::format_all",
  "log::debug": "::pengu::log_debug",
  "log::info": "::pengu::log_info",
  "log::warn": "::pengu::log_warn",
  "log::error": "::pengu::log_error",
  "os::args": "::pengu::os_args",
  "debug::println": "::pengu::println",
  "console::println": "::pengu::println",
  "math::sqrt": "std::sqrt",
  "math::abs": "std::abs",
  "math::floor": "std::floor",
  "math::ceil": "std::ceil",
  "math::round": "std::round",
  "math::pow": "std::pow",
  "math::min": "std::min",
  "math::max": "std::max",
  "math::sin": "std::sin",
  "math::cos": "std::cos",
  "math::tan": "std::tan",
  "fs::read_to_string": "::pengu::read_file",
  "fs::write_string": "::pengu::write_file",
  "fs::exists": "::pengu::path_exists",
  "fs::is_dir": "::pengu::path_is_dir",
  "fs::remove": "::pengu::path_remove",
  "fs::create_dir": "::pengu::create_dir",
  "time::now_millis": "::pengu::now_millis",
  "time::now_seconds": "::pengu::now_seconds",
  "time::sleep_millis": "::pengu::sleep_millis",
  "os::get_env": "::pengu::get_env",
  "os::exit": "std::exit",
  "random::int": "::pengu::random_int",
  "random::float": "::pengu::random_float",
  "random::bool": "::pengu::random_bool",
  "assert::that": "::pengu::assert_that",
  "assert::fail": "::pengu::panic",
  "math::clamp": "std::clamp",
};

const BUILTIN_CONSTANTS: Readonly<Record<string, string>> = {
  "math::pi": "std::numbers::pi",
  "math::e": "std::numbers::e",
};

function emit_ident_call(
  g: GenContext,
  name: string,
  type_args: readonly string[],
  args: string,
  node: CallNode,
): string {
  if ((name === "unique" || name === "shared") && type_args.length === 1) {
    const maker = name === "unique" ? "std::make_unique" : "std::make_shared";
    return `${maker}<${type_args[0]}>(${args})`;
  }

  if (name === "weak") {
    const arg = node.args[0];
    const arg_type = arg === undefined ? undefined : type_of(g, arg.expr);
    const inner = arg_type?.kind === "shared" ? cpp_type(arg_type.inner, g.type_realms) : "auto";
    return `std::weak_ptr<${inner}>(${args})`;
  }

  if (name === "ref") {
    const first = node.args[0];
    return first === undefined ? "/* ref */" : emit_expr(g, first.expr);
  }
  if (name === "panic") return `::pengu::panic(${args})`;

  // Variantes de omen sin prefijo: `Circle(1.0)` → `Shape{Shape_Circle{1.0}}`.
  for (const [omen_name, omen] of g.module.env.omens) {
    const variant = omen.variants.get(name);
    if (variant === undefined) continue;
    if (variant.payload.length === 0) {
      return `${cpp_identifier(omen_name)}::${cpp_identifier(name)}`;
    }
    const rendered = variant.payload.map((_type, index) => `v${index}`).join(", ");
    return `${cpp_identifier(omen_name)}{${cpp_identifier(omen_name)}_${cpp_identifier(name)}{${args}}}`;
  }

  const rune = g.module.env.runes.get(name);
  if (rune !== undefined) {
    const rendered_name = type_args.length > 0 ? `${name}<${type_args.join(", ")}>` : name;
    if (rune.constructor !== undefined) return `${rendered_name}(${args})`;
    return `${rendered_name}{${args}}`;
  }

  const alias = g.module.env.aliases.get(name);
  if (alias !== undefined) {
    return `${name}(${args})`;
  }

  const sigils = type_args.length > 0 ? `<${type_args.join(", ")}>` : "";
  const imported_realm = g.selective_realms.get(name);
  if (imported_realm !== undefined && !g.module.functions.has(name) && !g.module.consts.has(name)) {
    return `${sanitize_namespace(imported_realm)}::${cpp_identifier(name)}${sigils}(${args})`;
  }
  return `${cpp_identifier(name)}${sigils}(${args})`;
}

// `alias::simbolo` de un módulo importado se traduce a `realm::simbolo`.
function emit_path(g: GenContext, segments: readonly string[]): string {
  const constant = BUILTIN_CONSTANTS[segments.join("::")];
  if (constant !== undefined) return constant;

  const first = segments[0];
  const realm = first !== undefined ? g.external_realms.get(first) : undefined;
  if (realm !== undefined) {
    return [sanitize_namespace(realm), ...segments.slice(1).map(cpp_identifier)].join("::");
  }
  return segments.map(cpp_identifier).join("::");
}

function emit_path_call(
  g: GenContext,
  segments: readonly string[],
  type_args: readonly string[],
  args: string,
): string {
  const joined = emit_path(g, segments);
  const builtin = BUILTIN_FUNCTIONS[segments.join("::")];
  if (builtin !== undefined) return `${builtin}(${args})`;

  const head = segments[0] ?? "";
  const last = segments[segments.length - 1] ?? "";
  const omen = g.module.env.omens.get(head);
  if (omen !== undefined) {
    if (last === "try_from") return `::pengu::try_from<${head}>(${args})`;
    if (last === "from") return `::pengu::from<${head}>(${args})`;
    const variant = omen.variants.get(last);
    if (variant !== undefined) {
      if (variant.payload.length === 0) return `${head}::${last}`;
      return `${head}{${head}_${last}{${args}}}`;
    }
  }

  const sigils = type_args.length > 0 ? `<${type_args.join(", ")}>` : "";
  return `${joined}${sigils}(${args})`;
}

function emit_member_call(g: GenContext, object: ExprNode, name: string, args: string): string {
  const rendered = emit_expr(g, object);
  const object_type = type_of(g, object);
  // Los métodos declarados por el usuario tienen prioridad sobre las
  // tablas de métodos incorporados (por ejemplo `len` en un rune).
  if (object_type.kind === "named") {
    const rune = g.module.env.runes.get(object_type.name);
    if (rune?.methods.has(name) === true) {
      return `${rendered}.${cpp_identifier(name)}(${args})`;
    }
  }
  switch (name) {
    case "is_some":
      return `${rendered}.has_value()`;
    case "is_none":
      return `!${rendered}.has_value()`;
    case "len":
      return `static_cast<std::size_t>(${rendered}.size())`;
    case "has":
      return `::pengu::has(${rendered}, ${args})`;
    case "pop_opt":
      return `::pengu::pop_opt(${rendered})`;
    case "lock":
      return `::pengu::lock_weak(${rendered})`;
    case "get": {
      if (is_map_type(object_type)) return `::pengu::map_get(${rendered}, ${args})`;
      if (is_sequence_container(object_type)) return `::pengu::get_at(${rendered}, ${args})`;
      return `${rendered}.get(${args})`;
    }
    case "get_unchecked":
      return `::pengu::vec_at(${rendered}, ${args})`;
    case "get_or":
      return `::pengu::map_get_or(${rendered}, ${args})`;
    case "extract":
      return `::pengu::map_extract(${rendered}, ${args})`;
    case "insert":
      if (is_map_type(object_type)) return `::pengu::map_insert(${rendered}, ${args})`;
      if (object_type.kind === "named" && object_type.name === "set") {
        return `::pengu::set_insert(${rendered}, ${args})`;
      }
      return `${rendered}.insert(${args})`;
    case "value":
      return `${rendered}.value()`;
    case "value_or":
      return `${rendered}.value_or(${args})`;
    default:
      return `${rendered}.${cpp_identifier(name)}(${args})`;
  }
}

function emit_unary(g: GenContext, node: import("../frontend/ast_expr.ts").UnaryNode): string {
  const operand = emit_expr(g, node.operand);
  switch (node.op) {
    case "not":
      return `!(${operand})`;
    case "#":
      return `::pengu::len(${operand})`;
    case "&":
      return `&(${operand})`;
    case "*":
      return `*(${operand})`;
    default:
      return `${node.op}(${operand})`;
  }
}

function emit_binary(g: GenContext, node: BinaryNode): string {
  const left = emit_expr(g, node.left);
  const right = emit_expr(g, node.right);
  switch (node.op) {
    case "and":
      return `(${left} && ${right})`;
    case "or":
      return `(${left} || ${right})`;
    case "in":
      return `::pengu::contains(${right}, ${left})`;
    default:
      return `(${left} ${node.op} ${right})`;
  }
}

function emit_cast(g: GenContext, node: CastNode): string {
  const target = cpp_type_node(node.type, g.module.env, g.type_realms);
  const value_type = type_of(g, node.value);
  let value = emit_expr(g, node.value);
  const is_seal = value_type.kind === "named" && g.module.env.aliases.get(value_type.name)?.seal === true;
  const is_self_value = g.self_value && node.value.kind === "self";
  if (is_seal && !is_self_value) {
    value = `${value}.value`;
  }
  return `static_cast<${target}>(${value})`;
}

function emit_vector_lit(g: GenContext, node: import("../frontend/ast_expr.ts").VectorLitNode): string {
  const type = type_of(g, node);
  const element = type.kind === "named" ? type.args[0] : undefined;
  const prefix = element ? `std::vector<${cpp_type(element, g.type_realms)}>` : "std::vector<auto>";
  return `${prefix}{${node.items.map((item) => emit_expr(g, item)).join(", ")}}`;
}

function emit_map_lit(g: GenContext, node: import("../frontend/ast_expr.ts").MapLitNode): string {
  const type = type_of(g, node);
  const key = type.kind === "named" ? type.args[0] : undefined;
  const value = type.kind === "named" ? type.args[1] : undefined;
  const prefix = key && value ? `std::map<${cpp_type(key)}, ${cpp_type(value)}>` : "std::map<auto, auto>";
  const entries = node.entries
    .map((entry) => `{${emit_expr(g, entry.key)}, ${emit_expr(g, entry.value)}}`)
    .join(", ");
  return `${prefix}{${entries}}`;
}

function emit_set_lit(g: GenContext, node: import("../frontend/ast_expr.ts").SetLitNode): string {
  const type = type_of(g, node);
  const element = type.kind === "named" ? type.args[0] : undefined;
  const prefix = element ? `std::set<${cpp_type(element, g.type_realms)}>` : "std::set<auto>";
  return `${prefix}{${node.items.map((item) => emit_expr(g, item)).join(", ")}}`;
}

function emit_comprehension(g: GenContext, node: ComprehensionNode): string {
  const result_type = type_of(g, node);
  const result_cpp = cpp_value_type(result_type, g.type_realms);
  return build_lambda(g, "", result_cpp, () => {
    const out = fresh_name(g, "out");
    line(g, `${result_cpp} ${out};`);
    emit_comprehension_clauses(g, node, out, 0);
    line(g, `return ${out};`);
  }) + "()";
}

function emit_comprehension_clauses(g: GenContext, node: ComprehensionNode, out: string, index: number): void {
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
  return false;
}

function emit_if(g: GenContext, node: import("../frontend/ast_expr.ts").IfNode): string {
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

function emit_switch(g: GenContext, node: SwitchNode): string {
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

function emit_match(g: GenContext, node: MatchNode): string {
  const result = cpp_value_type(type_of(g, node), g.type_realms);
  const subject_type = type_of(g, node.subject);
  const omen = subject_type.kind === "named" ? g.module.env.omens.get(subject_type.name) : undefined;
  const omen_name = omen !== undefined && subject_type.kind === "named" ? subject_type.name : "";
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
            line(g, `if (std::holds_alternative<${omen_name}_${variant_name}>(${subject}.value)) {`);
            g.indent += 1;
            emit_guard_and_body(g, arm, result, () => undefined);
            g.indent -= 1;
            line(g, "}");
            continue;
          }
          line(g, `if (auto* ${pointer} = std::get_if<${omen_name}_${variant_name}>(&${subject}.value)) {`);
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
    if (result !== "void") line(g, `::pengu::panic("match sin variante");`);
  }) + "()";
}

function emit_guard_and_body(
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

function loop_result_expr_type(g: GenContext, node: ExprNode): string {
  const type = type_of(g, node);
  if (type.kind === "optional" && type.inner.kind !== "any") {
    return cpp_value_type(type, g.type_realms);
  }
  return "void";
}

// Declara la variable que recoge el `break value` (si el bucle la usa).
function begin_loop_result(g: GenContext, result_type: string): string | undefined {
  if (result_type === "void") return undefined;
  const name = fresh_name(g, "res");
  line(g, `${result_type} ${name};`);
  g.break_values.push(name);
  return name;
}

function end_loop_result(g: GenContext, result_var: string | undefined): void {
  if (result_var === undefined) return;
  g.break_values.pop();
  line(g, `return ${result_var};`);
}

function emit_while(g: GenContext, node: import("../frontend/ast_expr.ts").WhileNode): string {
  const result_type = loop_result_expr_type(g, node);
  return build_lambda(g, "", result_type, () => {
    const result_var = begin_loop_result(g, result_type);
    const condition = emit_expr(g, node.condition);
    line(g, `while (${node.until ? `!(${condition})` : condition}) {`);
    g.indent += 1;
    emit_value_block(g, node.body, "void");
    g.indent -= 1;
    line(g, "}");
    end_loop_result(g, result_var);
  }) + "()";
}

function emit_repeat(g: GenContext, node: import("../frontend/ast_expr.ts").RepeatNode): string {
  const result_type = loop_result_expr_type(g, node);
  return build_lambda(g, "", result_type, () => {
    const result_var = begin_loop_result(g, result_type);
    line(g, "do {");
    g.indent += 1;
    emit_value_block(g, node.body, "void");
    g.indent -= 1;
    line(g, `} while (!(${emit_expr(g, node.condition)}));`);
    end_loop_result(g, result_var);
  }) + "()";
}

function emit_for_numeric(g: GenContext, node: import("../frontend/ast_expr.ts").ForNumericNode): string {
  const result_type = loop_result_expr_type(g, node);
  return build_lambda(g, "", result_type, () => {
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
  }) + "()";
}

function emit_for_iter(g: GenContext, node: import("../frontend/ast_expr.ts").ForIterNode): string {
  const result_type = loop_result_expr_type(g, node);
  return build_lambda(g, "", result_type, () => {
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
  }) + "()";
}

function emit_lambda(g: GenContext, node: import("../frontend/ast_expr.ts").LambdaNode): string {
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

