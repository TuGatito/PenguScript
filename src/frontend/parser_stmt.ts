// Parser de sentencias y bloques.
//
// Un bloque es una lista de sentencias con un valor: el de su última
// sentencia-expresión. La sangría la aporta el lexer con INDENT/DEDENT,
// así que aquí solo se valida la forma.

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
  synchronize,
  merge_span,
  describe,
  accept_line_break,
} from "./parser_cursor.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { AssignOp, Block, StmtNode } from "./ast_stmt.ts";
import type { ExprNode } from "./ast_expr.ts";
import type { TypeNode } from "./ast_type.ts";
import type { Span } from "../util/span.ts";
import { parse_type } from "./parser_type.ts";
import { parse_expression, parse_expression_or_tuple } from "./parser_expr.ts";

const ASSIGN_OPS: ReadonlySet<string> = new Set([
  "=",
  "+=",
  "-=",
  "*=",
  "/=",
  "%=",
  "&=",
  "|=",
  "^=",
  ">>=",
  "<<=",
]);

export function parse_block(c: Cursor, context: string): Block {
  const start = peek(c).span;
  if (!open_indented(c, context)) return empty_block(start);

  const statements: StmtNode[] = [];
  let last_span = start;

  while (!at(c, "dedent") && !at(c, "eof")) {
    if (at(c, "newline")) {
      advance(c);
      continue;
    }
    const stmt = parse_statement(c);
    statements.push(stmt);
    last_span = stmt.span;
    accept_line_break(c, stmt.span, "tras la sentencia");
  }

  if (at(c, "dedent")) advance(c);
  return { kind: "block", statements, span: merge_span(start, last_span) };
}

export function open_indented(c: Cursor, context: string): boolean {
  if (!at(c, "newline")) {
    push_error(
      c,
      CODES.invalid_block,
      `se esperaba un bloque indentado ${context}`,
      peek(c).span,
      "un bloque empieza en la línea siguiente, con más sangría",
    );
    return false;
  }

  advance(c);
  skip_newlines(c);

  if (!at(c, "indent")) {
    push_error(
      c,
      CODES.invalid_block,
      `el bloque ${context} no está indentado`,
      peek(c).span,
      "añade al menos un espacio o tabulador de sangría",
    );
    return false;
  }

  advance(c);
  return true;
}

export function parse_body(c: Cursor): Block {
  if (at(c, "newline") || at(c, "indent")) {
    return parse_block(c, "del cuerpo");
  }
  return block_of_expr(parse_expression(c));
}

export function block_of_expr(expr: ExprNode): Block {
  return {
    kind: "block",
    statements: [{ kind: "expr_stmt", expr, span: expr.span }],
    span: expr.span,
  };
}

export function empty_block(span: Span): Block {
  return { kind: "block", statements: [], span };
}

export function parse_brace_block(c: Cursor): Block {
  const start = peek(c).span;
  advance(c);
  skip_newlines(c);
  const statements: StmtNode[] = [];
  while (!at(c, "}") && !at(c, "eof")) {
    statements.push(parse_statement(c));
    if (at(c, "newline")) advance(c);
  }
  const close = expect(c, "}", "al cerrar el bloque");
  return {
    kind: "block",
    statements,
    span: merge_span(start, close?.span ?? start),
  };
}

export function parse_statement(c: Cursor): StmtNode {
  const token = peek(c);

  switch (token.kind) {
    case "return": {
      advance(c);
      const value = starts_expression(c) ? parse_expression(c) : undefined;
      return { kind: "return", value, span: token.span };
    }
    case "break": {
      advance(c);
      const value = starts_expression(c) ? parse_expression(c) : undefined;
      return { kind: "break", value, span: token.span };
    }
    case "continue":
      advance(c);
      return { kind: "continue", span: token.span };
    case "pass":
      advance(c);
      return { kind: "pass", span: token.span };
    case "const":
      return parse_const_statement(c);
    case "mut":
      return parse_mutable_binding(c);
    default:
      break;
  }

  if (token.kind === "ident" && peek(c, 1).kind === ":") {
    return parse_typed_binding(c);
  }

  const first = parse_expression(c);
  if (at(c, ",")) {
    const targets: ExprNode[] = [first];
    while (eat(c, ",")) targets.push(parse_expression(c));
    const op = expect(c, "=", "en la asignación múltiple");
    const value = parse_expression_or_tuple(c);
    return {
      kind: "assign",
      targets,
      op: "=",
      value,
      mutable: false,
      declared_type: undefined,
      span: merge_span(first.span, value.span),
    };
  }

  if (ASSIGN_OPS.has(peek(c).kind)) {
    const op_token = advance(c);
    const value = parse_expression_or_tuple(c);
    return {
      kind: "assign",
      targets: [first],
      op: op_token.kind as AssignOp,
      value,
      mutable: false,
      declared_type: undefined,
      span: merge_span(first.span, value.span),
    };
  }

  return { kind: "expr_stmt", expr: first, span: first.span };
}

function starts_expression(c: Cursor): boolean {
  return !at(c, "newline") && !at(c, "dedent") && !at(c, "eof");
}

function parse_const_statement(c: Cursor): StmtNode {
  const start = advance(c);
  const name = expect_ident(c, "tras const");
  const declared_type = at(c, ":") ? (advance(c), parse_type(c)) : undefined;
  expect(c, "=", "en la declaración const");
  const value = parse_expression(c);
  return {
    kind: "const_stmt",
    name: name?.text ?? "__error__",
    declared_type,
    value,
    span: merge_span(start.span, value.span),
  };
}

function parse_mutable_binding(c: Cursor): StmtNode {
  const start = advance(c);
  const targets: ExprNode[] = [];
  let declared_type: TypeNode | undefined;

  for (;;) {
    const name = expect_ident(c, "en la declaración mut");
    if (!name) break;
    targets.push({ kind: "ident", name: name.text, span: name.span });
    if (at(c, ":")) {
      advance(c);
      declared_type = parse_type(c);
      break;
    }
    if (eat(c, ",")) continue;
    break;
  }

  expect(c, "=", "en la declaración mut");
  const value = parse_expression_or_tuple(c);
  return {
    kind: "assign",
    targets,
    op: "=",
    value,
    mutable: true,
    declared_type,
    span: merge_span(start.span, value.span),
  };
}

function parse_typed_binding(c: Cursor): StmtNode {
  const name = advance(c);
  advance(c);
  const declared_type = parse_type(c);
  expect(c, "=", "en la declaración tipada");
  const value = parse_expression_or_tuple(c);
  const target: ExprNode = { kind: "ident", name: name.text, span: name.span };
  return {
    kind: "assign",
    targets: [target],
    op: "=",
    value,
    mutable: false,
    declared_type,
    span: merge_span(name.span, value.span),
  };
}
