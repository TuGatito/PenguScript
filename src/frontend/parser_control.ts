// Parser de expresiones de control.
//
// `if`, `switch`, `match`, `do`, los bucles y el `for` son expresiones.
// Todos comparten la misma forma: una cabecera, un bloque indentado y
// un `else` opcional.

import type { Cursor } from "./parser_cursor.ts";
import {
  advance,
  at,
  eat,
  expect,
  expect_ident,
  peek,
  push_error,
  skip_newlines,
  merge_span,
  describe,
} from "./parser_cursor.ts";
import { CODES } from "../diagnostics/codes.ts";
import type {
  DoNode,
  ForIterNode,
  ForNumericNode,
  IfNode,
  MatchArm,
  MatchNode,
  RepeatNode,
  SwitchArm,
  SwitchNode,
  WhileNode,
} from "./ast_expr.ts";
import type { Block } from "./ast_stmt.ts";
import { block_of_expr, open_indented, parse_block } from "./parser_stmt.ts";
import { parse_expression } from "./parser_expr.ts";
import { parse_pattern } from "./parser_pattern.ts";
import type { TypeNode } from "./ast_type.ts";
import { parse_type } from "./parser_type.ts";

// Tras `then` cabe una expresión en la misma línea o un bloque
// indentado; las dos formas producen un `Block`.
function then_body(c: Cursor, context: string): Block {
  if (at(c, "newline") || at(c, "indent")) return parse_block(c, context);
  return block_of_expr(parse_expression(c));
}

export function parse_if(c: Cursor, unless: boolean): IfNode {
  const start = advance(c);
  const condition = parse_expression(c);

  const then_block = eat(c, "then") ? then_body(c, "del then") : parse_block(c, "del if");

  let else_block: Block | undefined;
  if (at(c, "else")) {
    advance(c);
    if (at(c, "if") || at(c, "unless")) {
      else_block = block_of_expr(parse_if(c, at(c, "unless")));
    } else if (at(c, "newline")) {
      else_block = parse_block(c, "del else");
    } else {
      else_block = block_of_expr(parse_expression(c));
    }
  }

  const end = else_block?.span ?? then_block.span;
  return {
    kind: "if",
    condition,
    then_block,
    else_block,
    unless,
    span: merge_span(start.span, end),
  };
}

export function parse_switch(c: Cursor): SwitchNode {
  const start = advance(c);
  const subject = parse_expression(c);
  const arms: SwitchArm[] = [];
  let else_block: Block | undefined;

  if (open_indented(c, "del switch")) {
    while (!at(c, "dedent") && !at(c, "eof")) {
      if (at(c, "when")) {
        const when_token = advance(c);
        const patterns = [parse_expression(c)];
        while (eat(c, ",")) patterns.push(parse_expression(c));
        const body = eat(c, "then")
          ? then_body(c, "del when")
          : parse_block(c, "del when");
        arms.push({ patterns, body, span: merge_span(when_token.span, body.span) });
      } else if (at(c, "else")) {
        advance(c);
        else_block = at(c, "newline") || at(c, "indent")
          ? parse_block(c, "del else")
          : block_of_expr(parse_expression(c));
        skip_newlines(c);
        break;
      } else {
        push_error(
          c,
          CODES.unexpected_token,
          `se esperaba «when» o «else» en el switch, se encontró «${describe(c, peek(c))}»`,
          peek(c).span,
        );
        break;
      }
      skip_newlines(c);
    }
    if (at(c, "dedent")) advance(c);
  }

  const end = else_block?.span ?? arms[arms.length - 1]?.span ?? subject.span;
  return { kind: "switch", subject, arms, else_block, span: merge_span(start.span, end) };
}

export function parse_match(c: Cursor): MatchNode {
  const start = advance(c);
  const subject = parse_expression(c);
  const arms: MatchArm[] = [];

  if (open_indented(c, "del match")) {
    while (!at(c, "dedent") && !at(c, "eof")) {
      if (at(c, "when")) {
        const when_token = advance(c);
        const pattern = parse_pattern(c);
        const guard = eat(c, "if") ? parse_expression(c) : undefined;
        const body = eat(c, "then")
          ? then_body(c, "del when")
          : parse_block(c, "del when");
        arms.push({ pattern, guard, body, span: merge_span(when_token.span, body.span) });
      } else {
        push_error(
          c,
          CODES.unexpected_token,
          `se esperaba «when» en el match, se encontró «${describe(c, peek(c))}»`,
          peek(c).span,
        );
        break;
      }
      skip_newlines(c);
    }
    if (at(c, "dedent")) advance(c);
  }

  const end = arms[arms.length - 1]?.span ?? subject.span;
  return { kind: "match", subject, arms, span: merge_span(start.span, end) };
}

export function parse_do(c: Cursor): DoNode {
  const start = advance(c);
  const block = parse_block(c, "del do");
  return { kind: "do", block, span: merge_span(start.span, block.span) };
}

export function parse_while(c: Cursor, until: boolean): WhileNode {
  const start = advance(c);
  const condition = parse_expression(c);
  const body = parse_block(c, until ? "del until" : "del while");
  return {
    kind: "while",
    condition,
    body,
    until,
    span: merge_span(start.span, body.span),
  };
}

export function parse_repeat(c: Cursor): RepeatNode {
  const start = advance(c);
  const body = parse_block(c, "del repeat");
  expect(c, "until", "tras el bloque repeat");
  const condition = parse_expression(c);
  return {
    kind: "repeat",
    body,
    condition,
    span: merge_span(start.span, condition.span),
  };
}

export function parse_for(c: Cursor): ForNumericNode | ForIterNode {
  const start = advance(c);

  let mutable = eat(c, "mut") !== undefined;
  const first = expect_ident(c, "en la cabecera del for");
  const variable = first?.text ?? "__error__";

  let variable_type: TypeNode | undefined;
  if (at(c, ":")) {
    advance(c);
    variable_type = parse_type(c);
  }

  if (at(c, "=")) {
    advance(c);
    const from = parse_expression(c);
    expect(c, ",", "entre los límites del for");
    const to = parse_expression(c);
    const step = eat(c, ",") ? parse_expression(c) : undefined;
    const body = parse_block(c, "del for");
    const else_block = parse_loop_else(c);
    const end = else_block?.span ?? body.span;
    return {
      kind: "for_numeric",
      variable,
      variable_type,
      mutable,
      start: from,
      end: to,
      step,
      body,
      else_block,
      span: merge_span(start.span, end),
    };
  }

  const variables: string[] = [variable];
  while (eat(c, ",")) {
    if (eat(c, "mut")) mutable = true;
    const next = expect_ident(c, "en la cabecera del for");
    if (next) variables.push(next.text);
  }

  expect(c, "in", "en el for iterable");
  const iterable = parse_expression(c);
  const body = parse_block(c, "del for");
  const else_block = parse_loop_else(c);
  const end = else_block?.span ?? body.span;
  return {
    kind: "for_iter",
    variables,
    mutable,
    iterable,
    body,
    else_block,
    span: merge_span(start.span, end),
  };
}

function parse_loop_else(c: Cursor): Block | undefined {
  if (!at(c, "else")) return undefined;
  advance(c);
  return at(c, "newline") || at(c, "indent")
    ? parse_block(c, "del else del bucle")
    : block_of_expr(parse_expression(c));
}
