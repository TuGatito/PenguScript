// Parser de tipos.
//
// Los tipos se escriben como en C++ moderno pero con azúcar propia:
// `T?`, `ref<T>`, `function<(A) -> B>`, `array<T, N>` y los
// primitivos de varias palabras (`unsigned long long`).

import type { Cursor } from "./parser_cursor.ts";
import {
  advance,
  at,
  eat,
  expect,
  peek,
  push_error,
  merge_span,
  describe,
} from "./parser_cursor.ts";
import { CODES } from "../diagnostics/codes.ts";
import type {
  ArrayTypeNode,
  FunctionTypeNode,
  NamedTypeNode,
  OptionalTypeNode,
  PrimitiveTypeNode,
  RefTypeNode,
  TupleTypeNode,
  TypeNode,
} from "./ast_type.ts";
import { is_primitive_type, multi_word_primitives } from "./ast_type.ts";
import type { ExprNode } from "./ast_expr.ts";
import { parse_expression } from "./parser_expr.ts";

export function parse_type(c: Cursor): TypeNode {
  let base = parse_type_base(c);
  while (at(c, "?")) {
    const question = advance(c);
    const optional: OptionalTypeNode = {
      kind: "optional_type",
      inner: base,
      span: merge_span(base.span, question.span),
    };
    base = optional;
  }
  return base;
}

function parse_type_base(c: Cursor): TypeNode {
  if (at(c, "mut")) {
    const mut_token = advance(c);
    if (peek(c).kind === "ident" && peek(c).text === "ref") {
      return parse_ref_type(c, true, mut_token.span);
    }
    push_error(
      c,
      CODES.invalid_declaration,
      "«mut» en un tipo solo se permite como «mut ref<T>»",
      mut_token.span,
    );
  }

  const token = peek(c);
  if (token.kind !== "ident") {
    push_error(
      c,
      CODES.unknown_type,
      `se esperaba un tipo, se encontró «${describe(c, token)}»`,
      token.span,
    );
    advance(c);
    return { kind: "primitive_type", name: "void", span: token.span };
  }

  const primitive = try_multi_word_primitive(c);
  if (primitive) return primitive;

  const name = token.text;
  if (is_primitive_type(name)) {
    advance(c);
    return { kind: "primitive_type", name, span: token.span };
  }
  if (name === "ref") {
    advance(c);
    return parse_ref_type(c, false, token.span);
  }
  if (name === "optional" && peek(c, 1).kind === "<") {
    advance(c);
    const inner = parse_type_arguments_single(c, "optional");
    return {
      kind: "optional_type",
      inner,
      span: merge_span(token.span, inner.span),
    };
  }
  if (name === "function" && peek(c, 1).kind === "<") {
    return parse_function_type(c);
  }
  if (name === "tuple" && peek(c, 1).kind === "<") {
    return parse_tuple_type(c);
  }
  if (name === "array" && peek(c, 1).kind === "<") {
    return parse_array_type(c);
  }

  advance(c);
  const args = at(c, "<") ? parse_type_arguments(c) : [];
  const named: NamedTypeNode = { kind: "named_type", name, args, span: token.span };
  return named;
}

function try_multi_word_primitive(c: Cursor): PrimitiveTypeNode | undefined {
  const words: string[] = [];
  for (let offset = 0; offset < 4; offset++) {
    const token = peek(c, offset);
    if (token.kind !== "ident") break;
    words.push(token.text);
  }
  if (words.length === 0) return undefined;

  const phrases = multi_word_primitives();
  for (const phrase of phrases) {
    const parts = phrase.split(" ");
    if (parts.length > words.length) continue;
    let matches = true;
    for (let i = 0; i < parts.length; i++) {
      if (parts[i] !== words[i]) {
        matches = false;
        break;
      }
    }
    if (!matches) continue;
    const first = peek(c);
    let last = first;
    for (let i = 0; i < parts.length; i++) last = advance(c);
    return {
      kind: "primitive_type",
      name: phrase,
      span: merge_span(first.span, last.span),
    };
  }
  return undefined;
}

function parse_ref_type(c: Cursor, mutable: boolean, start_span: TypeNode["span"]): RefTypeNode {
  if (at(c, "<")) {
    const inner = parse_type_arguments_single(c, "ref");
    return { kind: "ref_type", inner, mutable, span: merge_span(start_span, inner.span) };
  }
  push_error(c, CODES.expected_token, "se esperaba «<» después de ref", peek(c).span);
  return {
    kind: "ref_type",
    inner: { kind: "primitive_type", name: "void", span: peek(c).span },
    mutable,
    span: start_span,
  };
}

export function parse_type_arguments(c: Cursor): readonly TypeNode[] {
  expect(c, "<", "en los argumentos de tipo");
  const args: TypeNode[] = [];
  if (at(c, ">") || at(c, ">>")) {
    expect_close_angle(c);
    return args;
  }

  const debt_at_entry = c.angle_debt;
  for (;;) {
    args.push(parse_type(c));
    // Un `>>` puede haber cerrado ya este nivel; la coma siguiente
    // pertenece a la construcción de fuera, no a esta lista.
    if (c.angle_debt > debt_at_entry) break;
    if (eat(c, ",")) continue;
    break;
  }
  expect_close_angle(c);
  return args;
}

export function parse_type_arguments_single(c: Cursor, container: string): TypeNode {
  const args = parse_type_arguments(c);
  const first = args[0];
  if (!first) {
    push_error(
      c,
      CODES.expected_token,
      `«${container}» necesita al menos un argumento de tipo`,
      peek(c).span,
    );
    return { kind: "primitive_type", name: "void", span: peek(c).span };
  }
  if (args.length > 1) {
    push_error(
      c,
      CODES.expected_token,
      `«${container}» solo admite un argumento de tipo`,
      first.span,
    );
  }
  return first;
}

export function expect_close_angle(c: Cursor): void {
  if (c.angle_debt > 0) {
    c.angle_debt--;
    return;
  }
  const token = peek(c);
  if (token.kind === ">") {
    advance(c);
    return;
  }
  if (token.kind === ">>") {
    advance(c);
    c.angle_debt++;
    return;
  }
  push_error(
    c,
    CODES.expected_token,
    `se esperaba «>» para cerrar los argumentos de tipo, se encontró «${describe(c, token)}»`,
    token.span,
  );
}

function parse_function_type(c: Cursor): FunctionTypeNode {
  const start = advance(c);
  expect(c, "<", "en el tipo función");
  expect(c, "(", "en los parámetros del tipo función");
  const params: TypeNode[] = [];
  let variadic = false;
  if (!at(c, ")")) {
    for (;;) {
      if (eat(c, "...") !== undefined) variadic = true;
      params.push(parse_type(c));
      if (eat(c, ",")) continue;
      break;
    }
  }
  expect(c, ")", "en los parámetros del tipo función");
  expect(c, "->", "en el tipo función");
  const result = parse_type(c);
  expect_close_angle(c);
  return {
    kind: "function_type",
    params,
    result,
    variadic,
    span: merge_span(start.span, result.span),
  };
}

function parse_tuple_type(c: Cursor): TupleTypeNode {
  const start = advance(c);
  const args = parse_type_arguments(c);
  return { kind: "tuple_type", items: args, span: merge_span(start.span, peek(c).span) };
}

function parse_array_type(c: Cursor): ArrayTypeNode {
  const start = advance(c);
  expect(c, "<", "en array<T, N>");
  const element = parse_type(c);
  expect(c, ",", "en array<T, N>");
  const size = parse_const_expression(c);
  expect_close_angle(c);
  return {
    kind: "array_type",
    element,
    size,
    span: merge_span(start.span, peek(c).span),
  };
}

// El tamaño de `array<T, N>` es una expresión constante. La
// importación es circular a propósito: ambos módulos solo exportan
// funciones, así que la evaluación de los módulos no se toca.
// Expresión constante dentro de `<...>`: se detiene antes de `>`
// (que cierra el tipo) para no confundirlo con una comparación.
function parse_const_expression(c: Cursor): ExprNode {
  return parse_expression(c, 5);
}
