// Parser de patrones para `match`.
//
// Un patrón describe la forma de un valor: comodín, literal, binding,
// variante de omen (con sub-patrones) o tupla.

import type { Cursor } from "./parser_cursor.ts";
import { advance, at, eat, expect, expect_ident, peek, push_error, describe } from "./parser_cursor.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { PatternNode } from "./ast_pattern.ts";
import type { Span } from "../util/span.ts";
import { merge_span } from "./parser_cursor.ts";

export function parse_pattern(c: Cursor): PatternNode {
  const token = peek(c);

  if (token.kind === "(") {
    const start = advance(c);
    const items: PatternNode[] = [];
    if (!at(c, ")")) {
      for (;;) {
        items.push(parse_pattern(c));
        if (eat(c, ",")) continue;
        break;
      }
    }
    const close = expect(c, ")", "en el patrón de tupla");
    return {
      kind: "tuple_pattern",
      items,
      span: merge_span(start.span, close?.span ?? start.span),
    };
  }

  if (token.kind === "int" || token.kind === "float" || token.kind === "string" || token.kind === "char") {
    return parse_literal_pattern(c);
  }
  if (
    token.kind === "true" ||
    token.kind === "false" ||
    token.kind === "none" ||
    token.kind === "nullptr"
  ) {
    return parse_literal_pattern(c);
  }

  if (token.kind === "ident") {
    if (token.text === "_") {
      const wildcard = advance(c);
      return { kind: "wildcard_pattern", span: wildcard.span };
    }
    return parse_path_pattern(c);
  }

  push_error(
    c,
    CODES.invalid_match_arm,
    `se esperaba un patrón, se encontró «${describe(c, token)}»`,
    token.span,
  );
  const fallback = advance(c);
  return { kind: "wildcard_pattern", span: fallback.span };
}

function parse_literal_pattern(c: Cursor): PatternNode {
  const token = advance(c);
  return {
    kind: "literal_pattern",
    value: literal_expr(token),
    span: token.span,
  };
}

function literal_expr(token: ReturnType<typeof peek>): import("./ast_expr.ts").ExprNode {
  switch (token.kind) {
    case "int":
      return { kind: "int_lit", value: token.value ?? token.text, span: token.span };
    case "float":
      return { kind: "float_lit", value: token.value ?? token.text, span: token.span };
    case "string": {
      const text = (token.parts ?? []).map((part) => (part.kind === "text" ? part.text : "")).join("");
      return { kind: "string_lit", parts: [{ kind: "text_part", text, span: token.span }], span: token.span };
    }
    case "char":
      return { kind: "char_lit", value: token.value ?? token.text, span: token.span };
    case "true":
    case "false":
      return { kind: "bool_lit", value: token.kind === "true", span: token.span };
    case "none":
      return { kind: "none_lit", span: token.span };
    case "nullptr":
      return { kind: "nullptr_lit", span: token.span };
    default:
      return { kind: "none_lit", span: token.span };
  }
}

function parse_path_pattern(c: Cursor): PatternNode {
  const first = advance(c);
  const path: string[] = [first.text];
  let end_span: Span = first.span;

  while (at(c, "::")) {
    advance(c);
    const segment = expect_ident(c, "en el patrón");
    if (!segment) break;
    path.push(segment.text);
    end_span = segment.span;
  }

  const args: PatternNode[] = [];
  if (at(c, "(")) {
    advance(c);
    if (!at(c, ")")) {
      for (;;) {
        args.push(parse_pattern(c));
        if (eat(c, ",")) continue;
        break;
      }
    }
    const close = expect(c, ")", "en el patrón de variante");
    if (close) end_span = close.span;
  }

  const head = path[0] ?? "";
  const is_variant = /^[A-Z]/.test(head) || path.length > 1;

  if (is_variant) {
    return {
      kind: "variant_pattern",
      path,
      args,
      span: merge_span(first.span, end_span),
    };
  }

  if (args.length > 0) {
    push_error(
      c,
      CODES.invalid_match_arm,
      `un binding no puede llevar sub-patrones: «${head}»`,
      first.span,
    );
  }
  return {
    kind: "binding_pattern",
    name: head,
    mutable: false,
    span: merge_span(first.span, end_span),
  };
}
