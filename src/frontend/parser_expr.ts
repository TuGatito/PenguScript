// Parser de expresiones.
//
// Precedencia por binding powers. Las expresiones de control viven en
// `parser_control.ts` y los patrones en `parser_pattern.ts`; aquí solo
// se decide qué forma tiene cada expresión.

import type { Cursor } from "./parser_cursor.ts";
import {
  advance,
  expect_name,
  at,
  eat,
  expect,
  expect_ident,
  peek,
  push_error,
  merge_span,
  describe,
  save,
  rewind,
} from "./parser_cursor.ts";
import { CODES } from "../diagnostics/codes.ts";
import { is_keyword } from "./token.ts";
import type {
  ArgNode,
  BinaryNode,
  ExprNode,
  ForClauseNode,
  LambdaNode,
  MapEntryNode,
  StringPartNode,
} from "./ast_expr.ts";
import type { ParamNode } from "./ast_param.ts";
import type { TypeNode } from "./ast_type.ts";
import { BUILTIN_TYPE_NAMES, is_primitive_type, multi_word_primitives } from "./ast_type.ts";
import type { Block } from "./ast_stmt.ts";
import type { Span } from "../util/span.ts";
import { parse_type, parse_type_arguments } from "./parser_type.ts";
import { block_of_expr, parse_block, parse_body, parse_brace_block } from "./parser_stmt.ts";
import {
  parse_do,
  parse_for,
  parse_if,
  parse_match,
  parse_repeat,
  parse_switch,
  parse_while,
} from "./parser_control.ts";
import { make_cursor } from "./parser_cursor.ts";

const BINARY_POWER: Readonly<Record<string, number>> = {
  or: 1,
  and: 2,
  "==": 4,
  "!=": 4,
  "<": 4,
  "<=": 4,
  ">": 4,
  ">=": 4,
  "<=>": 4,
  in: 4,
  "..": 5,
  "..<": 5,
  "|": 6,
  "^": 7,
  "&": 8,
  "<<": 9,
  ">>": 9,
  "+": 10,
  "-": 10,
  "*": 11,
  "/": 11,
  "%": 11,
};

export function parse_expression(c: Cursor, min_bp = 0): ExprNode {
  let left = parse_unary(c);

  for (;;) {
    const token = peek(c);

    if (token.kind === "as") {
      advance(c);
      const type = parse_type(c);
      left = {
        kind: "cast",
        value: left,
        type,
        span: merge_span(left.span, type.span),
      };
      continue;
    }

    const power = BINARY_POWER[token.kind];
    if (power === undefined || power < min_bp) break;

    advance(c);
    const right = parse_expression(c, power + 1);
    const span = merge_span(left.span, right.span);

    if (token.kind === ".." || token.kind === "..<") {
      left = { kind: "range", start: left, end: right, inclusive: token.kind === "..", span };
      continue;
    }

    const binary: BinaryNode = { kind: "binary", op: token.kind, left, right, span };
    left = binary;
  }

  return left;
}

export function parse_expression_or_tuple(c: Cursor): ExprNode {
  const first = parse_expression(c);
  if (!at(c, ",")) return first;

  const items: ExprNode[] = [first];
  while (eat(c, ",")) {
    if (at(c, "newline") || at(c, "eof") || at(c, "dedent")) break;
    items.push(parse_expression(c));
  }
  const last = items[items.length - 1] ?? first;
  return { kind: "tuple", items, span: merge_span(first.span, last.span) };
}

function parse_unary(c: Cursor): ExprNode {
  const token = peek(c);

  if (token.kind === "not") {
    advance(c);
    const operand = parse_expression(c, 4);
    return { kind: "unary", op: "not", operand, span: merge_span(token.span, operand.span) };
  }

  if (
    token.kind === "-" ||
    token.kind === "~" ||
    token.kind === "&" ||
    token.kind === "*" ||
    token.kind === "#"
  ) {
    advance(c);
    const operand = parse_expression(c, 12);
    return { kind: "unary", op: token.kind, operand, span: merge_span(token.span, operand.span) };
  }

  return parse_postfix(c);
}

function parse_postfix(c: Cursor): ExprNode {
  let expr = parse_primary(c);

  for (;;) {
    if (at(c, ".")) {
      advance(c);
      const name = expect_name(c, "tras «.»");
      if (!name) break;
      expr = {
        kind: "member",
        object: expr,
        name: name.text,
        name_span: name.span,
        span: merge_span(expr.span, name.span),
      };
      continue;
    }

    if (at(c, "::")) {
      advance(c);
      // Tras «::» se aceptan también palabras clave usadas como
      // símbolos (`Color::from`, `T::try_from`).
      const raw = peek(c);
      const segment = is_keyword(raw.text) ? advance(c) : expect_ident(c, "tras «::»");
      if (!segment) break;
      if (expr.kind === "ident" || expr.kind === "path") {
        const segments = expr.kind === "ident" ? [expr.name, segment.text] : [...expr.segments, segment.text];
        expr = { kind: "path", segments, span: merge_span(expr.span, segment.span) };
      } else {
        push_error(
          c,
          CODES.unexpected_token,
          "«::» solo puede seguir al nombre de un realm, un omen o un tipo",
          segment.span,
        );
        break;
      }
      continue;
    }

    if (at(c, "[")) {
      advance(c);
      const index = parse_expression(c);
      const close = expect(c, "]", "en el índice");
      expr = {
        kind: "index",
        object: expr,
        index,
        span: merge_span(expr.span, close?.span ?? index.span),
      };
      continue;
    }

    if (at(c, "(") && expr.kind === "ident" && DEFAULT_NEW_NAMES.has(expr.name)) {
      const name = expr.name;
      const parsed = parse_args(c);
      expr = {
        kind: "container_new",
        name,
        type_args: [],
        args: parsed.args,
        span: merge_span(expr.span, parsed.end),
      };
      continue;
    }

    if (at(c, "(")) {
      const parsed = parse_args(c);
      expr = {
        kind: "call",
        callee: expr,
        type_args: [],
        args: parsed.args,
        span: merge_span(expr.span, parsed.end),
      };
      continue;
    }

    if (at(c, "!")) {
      const bang = advance(c);
      expr = {
        kind: "call",
        callee: expr,
        type_args: [],
        args: [],
        span: merge_span(expr.span, bang.span),
      };
      continue;
    }

    if (at(c, "<") && expr.kind === "ident" && looks_like_generic_path(c)) {
      const name = expr.name;
      const type_args = parse_type_arguments(c);
      expect(c, "::", "entre el tipo y su variante");
      const raw = peek(c);
      const segment = is_keyword(raw.text) ? advance(c) : expect_ident(c, "tras «::»");
      if (!segment) break;
      expr = {
        kind: "path",
        segments: [name, segment.text],
        type_args,
        span: merge_span(expr.span, segment.span),
      };
      continue;
    }

    if (at(c, "<") && expr.kind === "ident" && is_container_new_name(expr.name)) {
      const name = expr.name;
      advance(c);
      if (name === "bitset") {
        const size = parse_expression(c, 5);
        expect(c, ">", "al cerrar el tamaño del bitset");
        const parsed = parse_args(c);
        expr = {
          kind: "container_new",
          name,
          type_args: [],
          size,
          args: parsed.args,
          span: merge_span(expr.span, parsed.end),
        };
        continue;
      }
      const type_args = parse_type_arguments_open(c);
      const parsed = parse_args(c);
      expr = {
        kind: "container_new",
        name,
        type_args,
        args: parsed.args,
        span: merge_span(expr.span, parsed.end),
      };
      continue;
    }

    if (at(c, "<") && looks_like_sigil_call(c)) {
      const type_args = parse_type_arguments(c);
      const parsed = parse_args(c);
      expr = {
        kind: "call",
        callee: expr,
        type_args,
        args: parsed.args,
        span: merge_span(expr.span, parsed.end),
      };
      continue;
    }

    break;
  }

  return expr;
}


const CONTAINER_NEW_NAMES: ReadonlySet<string> = new Set([
  "vector",
  "deque",
  "list",
  "forward_list",
  "set",
  "multiset",
  "unordered_set",
  "unordered_multiset",
  "map",
  "multimap",
  "unordered_map",
  "unordered_multimap",
  "stack",
  "queue",
  "priority_queue",
  "span",
  "bitset",
  "variant",
  "complex",
  "atomic",
  "mutex",
  "shared_mutex",
  "condition_variable",
  "thread",
  "string",
  "wstring",
  "u8string",
  "u16string",
  "u32string",
  "string_view",
]);

// Constructores sin argumentos de tipo (`mutex()`, `thread(...)`).
const DEFAULT_NEW_NAMES: ReadonlySet<string> = new Set([
  "mutex",
  "shared_mutex",
  "condition_variable",
  "thread",
  "string",
  "wstring",
  "u8string",
  "u16string",
  "u32string",
  "string_view",
]);

function is_container_new_name(name: string): boolean {
  return CONTAINER_NEW_NAMES.has(name);
}

// A diferencia de `parse_type_arguments`, ya se consumió el «<».
function parse_type_arguments_open(c: Cursor): readonly TypeNode[] {
  const args: TypeNode[] = [];
  if (at(c, ">")) {
    advance(c);
    return args;
  }
  args.push(parse_type(c));
  while (eat(c, ",")) args.push(parse_type(c));
  expect(c, ">", "al cerrar los argumentos de tipo");
  return args;
}

// `Resultado<int>::Ok`: argumentos de tipo seguidos de `::`.
function looks_like_generic_path(c: Cursor): boolean {
  let depth = 0;
  for (let offset = 0; offset < 96; offset++) {
    const token = peek(c, offset);
    if (token.kind === "eof" || token.kind === "newline") return false;
    if (token.kind === "<") {
      depth++;
      continue;
    }
    if (token.kind === ">") {
      depth--;
      if (depth === 0) return peek(c, offset + 1).kind === "::";
      continue;
    }
    if (token.kind === ">>") {
      depth -= 2;
      if (depth <= 0) return peek(c, offset + 1).kind === "::";
      continue;
    }
  }
  return false;
}

function looks_like_sigil_call(c: Cursor): boolean {
  let depth = 0;
  for (let offset = 0; offset < 96; offset++) {
    const token = peek(c, offset);
    if (token.kind === "eof" || token.kind === "newline") return false;
    if (token.kind === "<") {
      depth++;
      continue;
    }
    if (token.kind === ">") {
      depth--;
      if (depth === 0) return peek(c, offset + 1).kind === "(";
      continue;
    }
    if (token.kind === ">>") {
      depth -= 2;
      if (depth <= 0) return depth === 0 && peek(c, offset + 1).kind === "(";
    }
  }
  return false;
}

export function parse_args(c: Cursor): { args: readonly ArgNode[]; end: Span } {
  const open = expect(c, "(", "en los argumentos");
  const args: ArgNode[] = [];

  if (!at(c, ")")) {
    for (;;) {
      const mutable = eat(c, "mut") !== undefined;
      const spread = eat(c, "...") !== undefined;
      const expr = parse_expression(c);
      args.push({ kind: "arg", expr, mutable, spread, span: expr.span });
      if (eat(c, ",")) continue;
      break;
    }
  }

  const close = expect(c, ")", "en los argumentos");
  return { args, end: close?.span ?? open?.span ?? peek(c).span };
}

export function parse_params(c: Cursor): readonly ParamNode[] {
  expect(c, "(", "en los parámetros");
  const params: ParamNode[] = [];

  if (!at(c, ")")) {
    for (;;) {
      const variadic = eat(c, "...") !== undefined;
      const mutable = eat(c, "mut") !== undefined;
      const name = expect_ident(c, "en los parámetros");
      const type = at(c, ":") ? (advance(c), parse_type(c)) : undefined;
      const default_value = eat(c, "=") ? parse_expression(c) : undefined;
      const span = name?.span ?? peek(c).span;
      if (variadic && type === undefined) {
        push_error(c, CODES.expected_token, "el parámetro variádico necesita un tipo tras «:»", span);
      }
      if (variadic && default_value !== undefined) {
        push_error(c, CODES.unexpected_token, "un parámetro variádico no puede tener valor por defecto", span);
      }
      params.push({
        kind: "param",
        name: name?.text ?? "__error__",
        type,
        default_value,
        mutable,
        variadic,
        span,
      });
      if (eat(c, ",")) {
        if (variadic) {
          push_error(c, CODES.expected_token, "el parámetro variádico debe ser el último", span);
        }
        continue;
      }
      break;
    }
  }

  expect(c, ")", "en los parámetros");
  return params;
}

export function parse_return_and_body(c: Cursor): { result: TypeNode | undefined; body: Block } {
  if (looks_like_return_type(c)) {
    const result = parse_type(c);
    const body = parse_body(c);
    return { result, body };
  }
  if (at(c, "newline")) {
    const body = parse_block(c, "del cuerpo de la función");
    return { result: undefined, body };
  }
  const body = block_of_expr(parse_expression(c));
  return { result: undefined, body };
}

export function looks_like_return_type(c: Cursor): boolean {
  const token = peek(c);
  if (token.kind === "mut") return true;
  if (token.kind !== "ident") return false;

  const name = token.text;
  if (
    name === "ref" ||
    name === "raw" ||
    name === "unique" ||
    name === "shared" ||
    name === "weak" ||
    name === "optional" ||
    name === "function" ||
    name === "tuple" ||
    name === "array"
  ) {
    return true;
  }
  if (is_primitive_type(name) || BUILTIN_TYPE_NAMES.has(name)) return true;
  for (const phrase of multi_word_primitives()) {
    if (phrase === name || phrase.startsWith(`${name} `)) return true;
  }

  let offset = 1;
  if (peek(c, offset).kind === "?") offset++;
  const next = peek(c, offset).kind;
  return next === "newline" || next === "eof" || next === "dedent" || next === "indent";
}

export function looks_like_signature(c: Cursor): boolean {
  let depth = 0;
  for (let offset = 0; offset < 160; offset++) {
    const token = peek(c, offset);
    if (token.kind === "eof") return false;
    if (token.kind === "(") {
      depth++;
      continue;
    }
    if (token.kind === ")") {
      depth--;
      if (depth === 0) return peek(c, offset + 1).kind === "->";
    }
  }
  return false;
}

function parse_primary(c: Cursor): ExprNode {
  const token = peek(c);

  switch (token.kind) {
    case "int":
      advance(c);
      return { kind: "int_lit", value: token.value ?? token.text, span: token.span };
    case "float":
      advance(c);
      return { kind: "float_lit", value: token.value ?? token.text, span: token.span };
    case "char":
      advance(c);
      return { kind: "char_lit", value: token.value ?? token.text, span: token.span };
    case "string":
      advance(c);
      return { kind: "string_lit", parts: parse_string_parts(c, token), span: token.span };
    case "true":
    case "false":
      advance(c);
      return { kind: "bool_lit", value: token.kind === "true", span: token.span };
    case "none":
      advance(c);
      return { kind: "none_lit", span: token.span };
    case "nullptr":
      advance(c);
      return { kind: "nullptr_lit", span: token.span };
    case "ident": {
      const typed = try_typed_literal(c);
      return typed ?? parse_ident_primary(c);
    }
    case "@":
      return parse_self(c);
    case "parent": {
      const parent = advance(c);
      const parsed = parse_args(c);
      return { kind: "parent_call", args: parsed.args, span: merge_span(parent.span, parsed.end) };
    }
    case "(":
      if (looks_like_signature(c)) return parse_lambda(c);
      return parse_group_or_tuple(c);
    case "[":
      return parse_vector_literal(c);
    case "{":
      return parse_map_literal(c);
    case "if":
      return parse_if(c, false);
    case "unless":
      return parse_if(c, true);
    case "switch":
      return parse_switch(c);
    case "match":
      return parse_match(c);
    case "do":
      return parse_do(c);
    case "while":
      return parse_while(c, false);
    case "until":
      return parse_while(c, true);
    case "repeat":
      return parse_repeat(c);
    case "for":
      return parse_for(c);
    case "unsafe":
      return parse_unsafe(c);
    default:
      break;
  }

  push_error(
    c,
    CODES.expected_expression,
    `se esperaba una expresión, se encontró «${describe(c, token)}»`,
    token.span,
  );
  advance(c);
  return { kind: "ident", name: "__error__", span: token.span };
}


// Literales con prefijo de tipo: `vector<int>[...]`, `deque<int>[...]`,
// `map<string, int>{...}`, `set<int>{...}`, `array<int, 3>[...]`.
const VECTOR_LITERAL_TYPES: ReadonlySet<string> = new Set([
  "vector",
  "deque",
  "list",
  "forward_list",
  "span",
  "array",
  "bitset",
]);
const SET_LITERAL_TYPES: ReadonlySet<string> = new Set([
  "set",
  "multiset",
  "unordered_set",
  "unordered_multiset",
]);
const MAP_LITERAL_TYPES: ReadonlySet<string> = new Set([
  "map",
  "multimap",
  "unordered_map",
  "unordered_multimap",
]);

function try_typed_literal(c: Cursor): ExprNode | undefined {
  const token = peek(c);
  if (token.kind !== "ident" || peek(c, 1).kind !== "<") return undefined;

  const name = token.text;
  const vectorish = VECTOR_LITERAL_TYPES.has(name);
  const setish = SET_LITERAL_TYPES.has(name);
  const mapish = MAP_LITERAL_TYPES.has(name);
  if (!vectorish && !setish && !mapish) return undefined;

  const saved = save(c);
  const type = parse_type(c);

  if (mapish) {
    if (!at(c, "{")) {
      rewind(c, saved);
      return undefined;
    }
    const literal = parse_map_literal(c);
    if (literal.kind !== "map_lit") {
      rewind(c, saved);
      return undefined;
    }
    return { ...literal, declared_type: type, span: merge_span(type.span, literal.span) };
  }

  if (setish) {
    if (!at(c, "{")) {
      rewind(c, saved);
      return undefined;
    }
    const literal = parse_set_literal(c, type.span);
    if (literal.kind !== "set_lit") {
      rewind(c, saved);
      return undefined;
    }
    return { ...literal, declared_type: type, span: merge_span(type.span, literal.span) };
  }

  if (!at(c, "[")) {
    rewind(c, saved);
    return undefined;
  }
  const literal = parse_vector_literal(c);
  if (literal.kind !== "vector_lit") {
    rewind(c, saved);
    return undefined;
  }
  return { ...literal, declared_type: type, span: merge_span(type.span, literal.span) };
}

function parse_ident_primary(c: Cursor): ExprNode {
  const token = advance(c);
  if (token.text === "set" && at(c, "{")) return parse_set_literal(c, token.span);
  return { kind: "ident", name: token.text, span: token.span };
}

function parse_self(c: Cursor): ExprNode {
  const at_token = advance(c);
  const next = peek(c);
  if (next.kind === "ident" && next.span.start.offset === at_token.span.end.offset) {
    const name = advance(c);
    return {
      kind: "member",
      object: { kind: "self", span: at_token.span },
      name: name.text,
      name_span: name.span,
      span: merge_span(at_token.span, name.span),
    };
  }
  return { kind: "self", span: at_token.span };
}

function parse_group_or_tuple(c: Cursor): ExprNode {
  const open = advance(c);
  if (at(c, ")")) {
    const close = advance(c);
    push_error(c, CODES.expected_expression, "paréntesis vacíos", merge_span(open.span, close.span));
    return { kind: "ident", name: "__error__", span: merge_span(open.span, close.span) };
  }

  const first = parse_expression(c);
  if (!at(c, ",")) {
    expect(c, ")", "al cerrar la expresión");
    return first;
  }

  const items: ExprNode[] = [first];
  while (eat(c, ",")) {
    if (at(c, ")")) break;
    items.push(parse_expression(c));
  }
  const close = expect(c, ")", "al cerrar la tupla");
  return {
    kind: "tuple",
    items,
    span: merge_span(open.span, close?.span ?? first.span),
  };
}

function parse_lambda(c: Cursor): LambdaNode {
  const start = peek(c);
  const params = parse_params(c);
  expect(c, "->", "en la lambda");
  const { result, body } = parse_return_and_body(c);
  return {
    kind: "lambda",
    sigils: [],
    needs: [],
    params,
    result,
    body,
    is_unsafe: false,
    span: merge_span(start.span, body.span),
  };
}

function parse_unsafe(c: Cursor): ExprNode {
  const start = advance(c);
  if (at(c, "{")) {
    const block = parse_brace_block(c);
    return { kind: "unsafe", block, span: merge_span(start.span, block.span) };
  }
  const block = parse_block(c, "del unsafe");
  return { kind: "unsafe", block, span: merge_span(start.span, block.span) };
}

function parse_vector_literal(c: Cursor): ExprNode {
  const open = advance(c);
  if (at(c, "]")) {
    const close = advance(c);
    return { kind: "vector_lit", items: [], span: merge_span(open.span, close.span) };
  }

  const first = parse_expression(c);
  if (at(c, "for")) {
    const clauses = parse_comprehension_clauses(c);
    const close = expect(c, "]", "en la comprensión");
    return {
      kind: "comprehension",
      container: "vector",
      body: first,
      key: undefined,
      clauses,
      span: merge_span(open.span, close?.span ?? first.span),
    };
  }

  const items: ExprNode[] = [first];
  while (eat(c, ",")) {
    if (at(c, "]")) break;
    items.push(parse_expression(c));
  }
  const close = expect(c, "]", "en el literal de vector");
  const last = items[items.length - 1] ?? first;
  return { kind: "vector_lit", items, span: merge_span(open.span, close?.span ?? last.span) };
}

function parse_map_literal(c: Cursor): ExprNode {
  const open = advance(c);
  if (at(c, "}")) {
    const close = advance(c);
    return { kind: "map_lit", entries: [], span: merge_span(open.span, close.span) };
  }

  const key = parse_expression(c);
  expect(c, ":", "entre clave y valor del mapa");
  const value = parse_expression(c);

  if (at(c, "for")) {
    const clauses = parse_comprehension_clauses(c);
    const close = expect(c, "}", "en la comprensión de mapa");
    return {
      kind: "comprehension",
      container: "map",
      body: value,
      key,
      clauses,
      span: merge_span(open.span, close?.span ?? value.span),
    };
  }

  const entries: MapEntryNode[] = [{ key, value, span: merge_span(key.span, value.span) }];
  while (eat(c, ",")) {
    if (at(c, "}")) break;
    const next_key = parse_expression(c);
    expect(c, ":", "entre clave y valor del mapa");
    const next_value = parse_expression(c);
    entries.push({ key: next_key, value: next_value, span: merge_span(next_key.span, next_value.span) });
  }

  const close = expect(c, "}", "en el literal de mapa");
  const last = entries[entries.length - 1];
  return {
    kind: "map_lit",
    entries,
    span: merge_span(open.span, close?.span ?? last?.span ?? open.span),
  };
}

function parse_set_literal(c: Cursor, set_span: Span): ExprNode {
  const open = advance(c);
  if (at(c, "}")) {
    const close = advance(c);
    return { kind: "set_lit", items: [], span: merge_span(set_span, close.span) };
  }

  const first = parse_expression(c);
  if (at(c, "for")) {
    const clauses = parse_comprehension_clauses(c);
    const close = expect(c, "}", "en la comprensión de conjunto");
    return {
      kind: "comprehension",
      container: "set",
      body: first,
      key: undefined,
      clauses,
      span: merge_span(set_span, close?.span ?? first.span),
    };
  }

  const items: ExprNode[] = [first];
  while (eat(c, ",")) {
    if (at(c, "}")) break;
    items.push(parse_expression(c));
  }
  const close = expect(c, "}", "en el literal de conjunto");
  return { kind: "set_lit", items, span: merge_span(set_span, close?.span ?? first.span) };
}

function parse_comprehension_clauses(c: Cursor): readonly ForClauseNode[] {
  const clauses: ForClauseNode[] = [];

  while (at(c, "for")) {
    const start = advance(c);
    const mutable = eat(c, "mut") !== undefined;
    const variables: string[] = [];
    const first = expect_ident(c, "en la comprensión");
    if (first) variables.push(first.text);
    while (eat(c, ",")) {
      const next = expect_ident(c, "en la comprensión");
      if (next) variables.push(next.text);
    }
    expect(c, "in", "en la comprensión");
    const iterable = parse_expression(c);
    const condition = eat(c, "if") ? parse_expression(c) : undefined;
    const end = condition?.span ?? iterable.span;
    clauses.push({
      kind: "for_clause",
      variables,
      mutable,
      iterable,
      condition,
      span: merge_span(start.span, end),
    });
  }

  return clauses;
}

function parse_string_parts(c: Cursor, token: ReturnType<typeof peek>): readonly StringPartNode[] {
  if (token.parts === undefined && token.value !== undefined) {
    return [{ kind: "text_part", text: token.value, span: token.span }];
  }

  const parts = token.parts ?? [];
  const result: StringPartNode[] = [];

  for (const part of parts) {
    if (part.kind === "text") {
      result.push({ kind: "text_part", text: part.text, span: token.span });
      continue;
    }

    const eof = { kind: "eof" as const, text: "", span: part.span };
    const sub = make_cursor([...part.tokens, eof], c.file, c.diagnostics);
    const expr = parse_expression(sub);
    if (!at(sub, "eof")) {
      push_error(
        sub,
        CODES.unexpected_token,
        `sobra «${describe(sub, peek(sub))}» en la interpolación`,
        peek(sub).span,
      );
    }
    result.push({ kind: "expr_part", expr, span: part.span });
  }

  return result;
}
