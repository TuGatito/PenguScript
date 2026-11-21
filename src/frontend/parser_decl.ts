// Parser de declaraciones de nivel superior.
//
// Un módulo es una secuencia plana de declaraciones: realm, invokes,
// constantes, funciones, runes, omens, echo/seal y bloques enchanting.

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
import type {
  ConstructorDecl,
  DeclNode,
  EchoDecl,
  EnchantingDecl,
  FieldDecl,
  FunctionDecl,
  InvokeItem,
  MethodDecl,
  OmenDecl,
  OmenVariant,
  RuneDecl,
  SealDecl,
  DeclareDecl,
  IntrinsicDecl,
} from "./ast_decl.ts";
import type { Program } from "./ast.ts";
import type { ParamNode } from "./ast_param.ts";
import type { Block } from "./ast_stmt.ts";
import type { TypeNode } from "./ast_type.ts";
import type { Token } from "./token.ts";
import type { Span } from "../util/span.ts";
import { parse_type, parse_type_arguments, expect_close_angle } from "./parser_type.ts";
import {
  looks_like_return_type,
  looks_like_signature,
  parse_params,
  parse_return_and_body,
  parse_expression,
} from "./parser_expr.ts";
import { open_indented, parse_block } from "./parser_stmt.ts";

export function parse_program(c: Cursor): Program {
  const start = peek(c).span;
  const decls: DeclNode[] = [];
  let last = start;

  skip_newlines(c);
  while (!at(c, "eof")) {
    const decl = parse_decl(c);
    if (decl) {
      decls.push(decl);
      last = decl.span;
    }

    accept_line_break(c, last, "tras la declaración");
    if (at(c, "dedent")) advance(c);
    skip_newlines(c);
  }

  return { kind: "program", decls, span: merge_span(start, last) };
}

export function parse_decl(c: Cursor): DeclNode | undefined {
  const token = peek(c);

  switch (token.kind) {
    case "realm":
      return parse_realm(c);
    case "invoke":
      return parse_invoke(c);
    case "const":
      return parse_const_decl(c, false, false);
    case "static":
      return parse_static_decl(c);
    case "rune":
      return parse_rune(c);
    case "omen":
      return parse_omen(c, false);
    case "flags": {
      advance(c);
      if (!at(c, "omen")) {
        push_error(c, CODES.invalid_declaration, "«flags» solo puede preceder a «omen»", token.span);
        synchronize(c);
        return undefined;
      }
      return parse_omen(c, true);
    }
    case "echo":
      return parse_echo_decl(c, "echo");
    case "seal":
      return parse_echo_decl(c, "seal");
    case "enchanting":
      return parse_enchanting(c);
    case "unsafe": {
      advance(c);
      const name = expect_ident(c, "tras unsafe");
      if (!name) return undefined;
      expect(c, "=", "en la firma de la función");
      return parse_function_decl(c, name, true);
    }
    case "declare":
      return parse_declare(c, token.span);
    case "extern":
      return parse_extern(c, token.span);
    case "ident":
      return parse_named_decl(c);
    default:
      push_error(
        c,
        CODES.invalid_declaration,
        `se esperaba una declaración, se encontró «${describe(c, token)}»`,
        token.span,
      );
      advance(c);
      synchronize(c);
      return undefined;
  }
}

function parse_realm(c: Cursor): DeclNode {
  const start = advance(c);
  const name = expect_ident(c, "tras realm");
  const end = name?.span ?? start.span;
  return { kind: "realm_decl", name: name?.text ?? "__error__", span: merge_span(start.span, end) };
}

function parse_invoke(c: Cursor): DeclNode {
  const start = advance(c);
  const items: InvokeItem[] = [];
  let alias: string | undefined;

  if (at(c, "{")) {
    advance(c);
    while (!at(c, "}") && !at(c, "eof")) {
      const name = expect_ident(c, "en el invoke selectivo");
      if (!name) break;
      let item_alias: string | undefined;
      if (eat(c, "as")) {
        item_alias = expect_ident(c, "tras as")?.text;
      }
      items.push({ name: name.text, alias: item_alias, span: name.span });
      if (eat(c, ",")) continue;
      break;
    }
    expect(c, "}", "en el invoke selectivo");
    expect(c, "from", "en el invoke selectivo");
  }

  const path_token = peek(c);
  if (path_token.kind !== "string") {
    push_error(c, CODES.expected_token, "se esperaba la ruta del módulo como string", path_token.span);
  } else {
    advance(c);
  }

  if (eat(c, "as")) {
    alias = expect_ident(c, "tras as")?.text;
  }

  const path = path_token.kind === "string" ? string_literal_text(path_token) : "";
  const end = alias ? peek(c).span : path_token.span;
  return {
    kind: "invoke_decl",
    path,
    alias,
    items: items.length > 0 ? items : undefined,
    span: merge_span(start.span, end),
  };
}

function parse_static_decl(c: Cursor): DeclNode {
  advance(c);
  const mutable = eat(c, "mut") !== undefined;
  if (!mutable) {
    push_error(c, CODES.invalid_declaration, "el estado global debe declararse «static mut»", peek(c).span);
  }
  return parse_const_decl(c, true, mutable);
}

function parse_const_decl(c: Cursor, is_static: boolean, mutable: boolean): DeclNode {
  const start = advance(c);
  const name = expect_ident(c, "en la declaración");
  const declared_type = at(c, ":") ? (advance(c), parse_type(c)) : undefined;
  expect(c, "=", "en la declaración");
  const value = parse_expression(c);
  return {
    kind: "const_decl",
    name: name?.text ?? "__error__",
    declared_type,
    value,
    is_static,
    mutable,
    span: merge_span(start.span, value.span),
  };
}

function parse_named_decl(c: Cursor): DeclNode | undefined {
  const name = advance(c);

  if (at(c, "=")) {
    advance(c);
    if (is_function_start(c)) {
      return parse_function_decl(c, name, false);
    }
    const value = parse_expression(c);
    return {
      kind: "const_decl",
      name: name.text,
      declared_type: undefined,
      value,
      is_static: false,
      mutable: false,
      span: merge_span(name.span, value.span),
    };
  }

  if (at(c, ":")) {
    advance(c);
    const declared_type = parse_type(c);
    expect(c, "=", "en la declaración tipada");
    const value = parse_expression(c);
    return {
      kind: "const_decl",
      name: name.text,
      declared_type,
      value,
      is_static: false,
      mutable: false,
      span: merge_span(name.span, value.span),
    };
  }

  push_error(
    c,
    CODES.invalid_declaration,
    `se esperaba «=» tras «${name.text}»`,
    name.span,
  );
  synchronize(c);
  return undefined;
}

function is_function_start(c: Cursor): boolean {
  return at(c, "<") || at(c, "->") || (at(c, "(") && looks_like_signature(c));
}

// `extern "C"` + bloque de firmas sin cuerpo. Lo usa `pengu bindgen`.
export function parse_declare(c: Cursor, start: Span): IntrinsicDecl | undefined {
  advance(c); // declare
  const open = open_indented(c, "de las declaraciones intrínsecas");
  if (open === undefined) return undefined;

  const declares: DeclareDecl[] = [];
  while (!at(c, "dedent") && !at(c, "eof")) {
    if (at(c, "newline")) {
      advance(c);
      continue;
    }
    const name_token = expect_ident(c, "en una declaración intrínseca");
    if (name_token === undefined) {
      synchronize(c);
      continue;
    }
    expect(c, "=", "en la firma intrínseca");
    const params = at(c, "->") ? [] : parse_params(c);
    expect(c, "->", "en la firma intrínseca");
    const result = parse_type(c);
    const end = result?.span ?? name_token.span;
    declares.push({
      name: name_token.text,
      name_span: name_token.span,
      params,
      result,
      variadic: false,
      span: merge_span(name_token.span, end),
    });
    accept_line_break(c, end, "entre declaraciones intrínsecas");
  }

  const last_end = declares[declares.length - 1]?.span ?? start;
  if (at(c, "dedent")) advance(c);
  return {
    kind: "intrinsic_decl",
    declares,
    span: merge_span(start, last_end),
  };
}

function parse_extern(c: Cursor, start: Span): DeclNode | undefined {
  advance(c); // extern
  let abi = "C";
  if (at(c, "string")) {
    const literal = advance(c);
    abi = literal.value ?? "C";
  }

  const open = open_indented(c, "de las declaraciones extern");
  if (open === undefined) return undefined;

  const declares: DeclareDecl[] = [];
  while (!at(c, "dedent") && !at(c, "eof")) {
    if (at(c, "newline")) {
      advance(c);
      continue;
    }
    const name_token = expect_ident(c, "en una declaración extern");
    if (name_token === undefined) {
      synchronize(c);
      continue;
    }
    expect(c, "=", "en la firma extern");
    const params_start = peek(c).span;
    const params = at(c, "->") ? [] : parse_params(c);
    expect(c, "->", "en la firma extern");
    const result = parse_type(c);
    const end = result?.span ?? params_start;
    declares.push({
      name: name_token.text,
      name_span: name_token.span,
      params,
      result,
      variadic: false,
      span: merge_span(name_token.span, end),
    });
    accept_line_break(c, end, "entre declaraciones extern");
  }

  const last_end = declares[declares.length - 1]?.span ?? start;
  if (at(c, "dedent")) advance(c);
  return {
    kind: "extern_decl",
    abi,
    declares,
    span: merge_span(start, last_end),
  };
}

function parse_function_decl(c: Cursor, name: Token, is_unsafe: boolean): FunctionDecl {
  const { sigils, needs } = parse_sigils(c);
  const params: readonly ParamNode[] = at(c, "->") ? [] : parse_params(c);
  expect(c, "->", "en la firma de la función");
  const { result, body } = parse_return_and_body(c);
  return {
    kind: "function_decl",
    name: name.text,
    name_span: name.span,
    sigils,
    needs,
    params,
    result,
    body,
    is_unsafe,
    span: merge_span(name.span, body.span),
  };
}

export function parse_sigils(c: Cursor): { sigils: readonly string[]; needs: readonly string[] } {
  const sigils: string[] = [];
  const needs: string[] = [];

  if (!at(c, "<")) return { sigils, needs };
  advance(c);

  for (;;) {
    const name = expect_ident(c, "en los sigilos");
    if (name) sigils.push(name.text);

    if (at(c, "needs")) {
      advance(c);
      for (;;) {
        const constraint = expect_ident(c, "en las restricciones");
        if (constraint) {
          needs.push(constraint.text);
          if (at(c, "<")) parse_type_arguments(c);
        }
        if (eat(c, ",")) continue;
        break;
      }
      break;
    }

    if (eat(c, ",")) continue;
    break;
  }

  expect_close_angle(c);
  return { sigils, needs };
}

function parse_rune(c: Cursor): RuneDecl {
  const start = advance(c);
  const name = expect_ident(c, "tras rune");
  const { sigils } = parse_sigils(c);

  let parent: string | undefined;
  if (eat(c, "heir")) {
    parent = expect_ident(c, "tras heir")?.text;
  }

  const fields: FieldDecl[] = [];
  let constructor: ConstructorDecl | undefined;
  let destructor: Block | undefined;

  if (at(c, "newline") && peek(c, 1).kind === "indent") {
    open_indented(c, "del rune");
    while (!at(c, "dedent") && !at(c, "eof")) {
      if (at(c, "newline")) {
        advance(c);
        continue;
      }

      let item_end = peek(c).span;
      if (at(c, "constructor")) {
        const ctor_start = advance(c);
        const params = at(c, "(") ? parse_params(c) : [];
        const body = parse_block(c, "del constructor");
        constructor = { params, body, span: merge_span(ctor_start.span, body.span) };
        item_end = body.span;
      } else if (at(c, "destructor")) {
        advance(c);
        destructor = parse_block(c, "del destructor");
        item_end = destructor.span;
      } else {
        const field = parse_field(c);
        fields.push(field);
        item_end = field.span;
      }

      accept_line_break(c, item_end, "en el rune");
    }
    if (at(c, "dedent")) advance(c);
  }

  const end = destructor?.span ?? constructor?.span ?? fields[fields.length - 1]?.span ?? name?.span ?? start.span;
  return {
    kind: "rune_decl",
    name: name?.text ?? "__error__",
    name_span: name?.span ?? start.span,
    sigils,
    parent,
    fields,
    constructor,
    destructor,
    span: merge_span(start.span, end),
  };
}

function parse_field(c: Cursor): FieldDecl {
  const name = expect_ident(c, "en el campo");
  expect(c, ":", "tras el nombre del campo");
  const type = parse_type(c);
  const default_value = eat(c, "=") ? parse_expression(c) : undefined;
  return {
    name: name?.text ?? "__error__",
    type,
    default_value,
    span: merge_span(name?.span ?? type.span, default_value?.span ?? type.span),
  };
}

function parse_omen(c: Cursor, is_flags: boolean): OmenDecl {
  const start = advance(c);
  const name = expect_ident(c, "tras omen");
  const { sigils } = parse_sigils(c);

  let underlying: TypeNode | undefined;
  if (at(c, ":")) {
    advance(c);
    underlying = parse_type(c);
  }

  const variants: OmenVariant[] = [];
  if (at(c, "newline") && peek(c, 1).kind === "indent") {
    open_indented(c, "del omen");
    while (!at(c, "dedent") && !at(c, "eof")) {
      if (at(c, "newline")) {
        advance(c);
        continue;
      }
      const variant = parse_variant(c);
      variants.push(variant);
      if (eat(c, ",")) continue;
      accept_line_break(c, variant.span, "en el omen");
    }
    if (at(c, "dedent")) advance(c);
  }

  const end = variants[variants.length - 1]?.span ?? underlying?.span ?? name?.span ?? start.span;
  return {
    kind: "omen_decl",
    name: name?.text ?? "__error__",
    name_span: name?.span ?? start.span,
    sigils,
    underlying,
    is_flags,
    variants,
    span: merge_span(start.span, end),
  };
}

function parse_variant(c: Cursor): OmenVariant {
  const name = expect_ident(c, "en la variante del omen");
  const payload: TypeNode[] = [];
  let end = name?.span ?? peek(c).span;

  if (at(c, "(")) {
    advance(c);
    if (!at(c, ")")) {
      for (;;) {
        payload.push(parse_type(c));
        if (eat(c, ",")) continue;
        break;
      }
    }
    const close = expect(c, ")", "en el payload de la variante");
    end = close?.span ?? end;
  }

  const value = eat(c, "=") ? parse_expression(c) : undefined;
  if (value) end = value.span;

  return {
    name: name?.text ?? "__error__",
    name_span: name?.span ?? peek(c).span,
    payload,
    value,
    span: merge_span(name?.span ?? peek(c).span, end),
  };
}

function parse_echo_decl(c: Cursor, form: "echo" | "seal"): EchoDecl | SealDecl {
  const start = advance(c);
  const name = expect_ident(c, `tras ${form}`);
  const { sigils } = parse_sigils(c);
  expect(c, "=", `en ${form}`);
  const target = parse_type(c);
  const base = {
    name: name?.text ?? "__error__",
    name_span: name?.span ?? start.span,
    sigils,
    target,
    span: merge_span(start.span, target.span),
  };
  if (form === "echo") return { kind: "echo_decl", ...base };
  return { kind: "seal_decl", ...base };
}

function parse_enchanting(c: Cursor): EnchantingDecl {
  const start = advance(c);
  const target = expect_ident(c, "tras enchanting");
  const { sigils } = parse_sigils(c);
  const methods: MethodDecl[] = [];

  if (at(c, "newline") && peek(c, 1).kind === "indent") {
    open_indented(c, "del enchanting");
    while (!at(c, "dedent") && !at(c, "eof")) {
      if (at(c, "newline")) {
        advance(c);
        continue;
      }
      const method = parse_method(c);
      methods.push(method);
      accept_line_break(c, method.span, "en el enchanting");
    }
    if (at(c, "dedent")) advance(c);
  }

  const end = methods[methods.length - 1]?.span ?? target?.span ?? start.span;
  return {
    kind: "enchanting_decl",
    target: target?.text ?? "__error__",
    target_span: target?.span ?? start.span,
    sigils,
    methods,
    span: merge_span(start.span, end),
  };
}

function parse_method(c: Cursor): MethodDecl {
  const mutable = eat(c, "mut") !== undefined;
  let name: Token | undefined;
  let operator: string | undefined;

  if (at(c, "operator")) {
    const operator_token = advance(c);
    if (at(c, "[")) {
      advance(c);
      expect(c, "]", "en operator []");
      operator = "[]";
    } else if (at(c, "(")) {
      advance(c);
      expect(c, ")", "en operator ()");
      operator = "()";
    } else {
      operator = advance(c).text;
    }
    name = operator_token;
  } else {
    name = expect_ident(c, "en el método");
  }

  expect(c, "=", "en el método");
  const params: readonly ParamNode[] = at(c, "->") ? [] : parse_params(c);
  expect(c, "->", "en la firma del método");
  const { result, body } = parse_return_and_body(c);

  return {
    name: name?.text ?? "__error__",
    name_span: name?.span ?? peek(c).span,
    operator,
    mutable,
    sigils: [],
    needs: [],
    params,
    result,
    body,
    is_unsafe: false,
    span: merge_span(name?.span ?? peek(c).span, body.span),
  };
}

function string_literal_text(token: Token): string {
  if (token.value !== undefined) return token.value;
  const parts = token.parts ?? [];
  return parts.map((part) => (part.kind === "text" ? part.text : "")).join("");
}

