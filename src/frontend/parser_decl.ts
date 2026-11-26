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
  expect_name,
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
  ConstDecl,
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
  LinkDecl,
  OpaqueDecl,
  CallbackDecl,
  MeldDecl,
  HostGlobalDecl,
  HostIndex,
  HostMember,
  HostMethod,
  HostNamespaceDecl,
  HostProperty,
  HostTypeDecl,
  HostConstructor,
} from "./ast_decl.ts";
import type { Program } from "./ast.ts";
import type { ParamNode } from "./ast_param.ts";
import type { Block } from "./ast_stmt.ts";
import type { TypeNode } from "./ast_type.ts";
import type { Token } from "./token.ts";
import { KEYWORDS, is_keyword } from "./token.ts";
import { suggest_name } from "../util/suggest.ts";
import type { Span } from "../util/span.ts";
import { parse_type, parse_type_arguments, expect_close_angle } from "./parser_type.ts";
import { type_pattern_base, type_pattern_sigils } from "../semantic/enchant_targets.ts";
import {
  looks_like_return_type,
  looks_like_signature,
  parse_params,
  parse_return_and_body,
  parse_expression,
} from "./parser_expr.ts";
import { empty_block, open_indented, parse_block } from "./parser_stmt.ts";

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

  // `Invoke`, `Rune`, `Omen`… no son palabras clave; el usuario casi
  // siempre quería la versión en minúsculas.
  if (token.kind === "ident" && is_keyword(token.text.toLowerCase())) {
    push_error(
      c,
      CODES.invalid_declaration,
      `«${token.text}» no es una palabra clave; ¿quisiste decir «${token.text.toLowerCase()}»?`,
      token.span,
    );
    advance(c);
    synchronize(c);
    return undefined;
  }

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
    case "operator": {
      return parse_free_operator(c, token.span);
    }
    case "unsafe": {
      advance(c);
      const name = expect_ident(c, "tras unsafe");
      if (!name) return undefined;
      expect(c, "=", "en la firma de la función");
      return parse_function_decl(c, name, true, false);
    }
    case "async": {
      advance(c);
      if (at(c, "operator")) {
        push_error(
          c,
          CODES.async_not_allowed,
          "un operador libre no puede ser «async»",
          token.span,
        );
        // Se recupera analizando el operador como si no llevara «async».
        return parse_free_operator(c, token.span);
      }
      const is_unsafe = eat(c, "unsafe") !== undefined;
      const name = expect_ident(c, is_unsafe ? "tras async unsafe" : "tras async");
      if (!name) return undefined;
      expect(c, "=", "en la firma de la función");
      if (!is_function_start(c)) {
        push_error(
          c,
          CODES.async_not_allowed,
          "«async» solo puede acompañar a una función",
          token.span,
          "escribe una lambda o una función tras «async nombre =»",
        );
        // Se consume el valor para no encadenar errores de sintaxis.
        parse_expression(c);
        return undefined;
      }
      return parse_function_decl(c, name, is_unsafe, true);
    }
    case "declare":
      return parse_declare(c, token.span);
    case "extern":
      return parse_extern(c, token.span);
    case "link":
      return parse_link(c);
    case "define":
      return parse_define(c);
    case "opaque":
      return parse_opaque(c);
    case "callback":
      return parse_callback(c);
    case "meld":
      return parse_meld(c);
    case "host":
      return parse_host(c);
    case "ident":
      return parse_named_decl(c);
    default: {
      const suggestion = suggest_name(token.text, KEYWORDS);
      const hint = suggestion === undefined ? "" : `; ¿quisiste decir «${suggestion}»?`;
      push_error(
        c,
        CODES.invalid_declaration,
        `se esperaba una declaración, se encontró «${describe(c, token)}»${hint}`,
        token.span,
      );
      advance(c);
      synchronize(c);
      return undefined;
    }
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
  const start = advance(c);
  const has_mut = eat(c, "mut") !== undefined;
  if (!has_mut) {
    push_error(c, CODES.invalid_declaration, "el estado global debe declararse «static mut»", peek(c).span);
  }
  return parse_const_decl(c, true, true, start.span);
}

function parse_const_decl(
  c: Cursor,
  is_static: boolean,
  mutable: boolean,
  start_span?: Span,
): DeclNode {
  const start = start_span ?? advance(c).span;
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
    is_define: false,
    span: merge_span(start, value.span),
  };
}

// Operador libre: `operator + = (a: int, b: Punto) -> Punto`.
// Se parsea como una función cuyo nombre es el símbolo; el checker y
// el codegen lo tratan como una función normal con `operator` puesto.
function parse_free_operator(c: Cursor, start: Span): DeclNode | undefined {
  advance(c); // operator
  const symbol = operator_token(c);
  if (symbol === undefined) return undefined;
  expect(c, "=", "tras el operador libre");
  const params = at(c, "->") ? [] : parse_params(c);
  expect(c, "->", "en la firma del operador libre");
  const { result, body } = parse_return_and_body(c);

  // Solo se admiten los operadores que el lenguaje declara.
  if (!FREE_OPERATORS.has(symbol.text)) {
    push_error(
      c,
      CODES.expected_token,
      `«${symbol.text}» no se puede declarar como operador libre`,
      symbol.span,
    );
    return undefined;
  }

  return {
    kind: "function_decl",
    name: `operator ${symbol.text}`,
    name_span: symbol.span,
    sigils: [],
    needs: [],
    params,
    result,
    body,
    is_unsafe: false,
    is_async: false,
    operator: symbol.text,
    span: merge_span(start, body.span),
  };
}

// Símbolos válidos tras `operator`. Incluye los compuestos y `[]`/`()`
// aunque en la forma libre solo tengan sentido los binarios.
const FREE_OPERATORS = new Set([
  "+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>",
  "==", "!=", "<", "<=", ">", ">=", "<=>",
  "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=",
  "[]", "()",
]);

function operator_token(c: Cursor): Token | undefined {
  const token = peek(c);
  if (FREE_OPERATORS.has(token.text)) {
    advance(c);
    return token;
  }
  push_error(c, CODES.expected_token, "se esperaba un operador tras «operator»", token.span);
  return undefined;
}

function parse_named_decl(c: Cursor): DeclNode | undefined {
  const name = advance(c);

  if (at(c, "=")) {
    advance(c);
    // `main = async -> …` es una declaración de función asíncrona, igual que
    // `async main = …`: el azúcar de `nombre = (params) -> …` también vale
    // con «async» delante de la lambda.
    if (at(c, "async") && peek(c, 1).kind === "->") {
      advance(c);
      return parse_function_decl(c, name, false, true);
    }
    if (at(c, "async") && peek(c, 1).kind === "(") {
      advance(c);
      return parse_function_decl(c, name, false, true);
    }
    if (is_function_start(c)) {
      return parse_function_decl(c, name, false, false);
    }
    const value = parse_expression(c);
    return {
      kind: "const_decl",
      name: name.text,
      declared_type: undefined,
      value,
      is_static: false,
      mutable: false,
      is_define: false,
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
      is_define: false,
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
      variadic: params.some((param) => param.variadic),
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
      variadic: params.some((param) => param.variadic),
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

function parse_function_decl(
  c: Cursor,
  name: Token,
  is_unsafe: boolean,
  is_async: boolean,
): FunctionDecl {
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
    is_async,
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
        // Un constructor puede ser solo la lista de parámetros: los
        // campos se inicializan por nombre.
        const body = at(c, "newline") && peek(c, 1).kind !== "indent"
          ? empty_block(peek(c).span)
          : parse_block(c, "del constructor");
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
  // `bits 3 modo: uint32_t`: `bits` es contextual (solo aquí y seguido de
  // un entero), así que sigue siendo un identificador normal en el resto
  // del lenguaje.
  let bits: number | undefined;
  const first = peek(c);
  if (first.kind === "ident" && first.text === "bits" && peek(c, 1).kind === "int") {
    advance(c);
    const width = advance(c);
    const parsed = Number(width.text);
    bits = Number.isInteger(parsed) ? parsed : undefined;
  }
  const name = expect_ident(c, "en el campo");
  expect(c, ":", "tras el nombre del campo");
  const type = parse_type(c);
  const default_value = eat(c, "=") ? parse_expression(c) : undefined;
  return {
    name: name?.text ?? "__error__",
    type,
    default_value,
    bits,
    span: merge_span(name?.span ?? type.span, default_value?.span ?? type.span),
  };
}

function parse_link(c: Cursor): LinkDecl {
  const start = advance(c);
  const path_token = peek(c);
  let path = "";
  if (path_token.kind !== "string") {
    push_error(c, CODES.expected_token, "se esperaba el nombre de la biblioteca como string", path_token.span);
  } else {
    advance(c);
    path = string_literal_text(path_token);
  }
  return { kind: "link_decl", path, span: merge_span(start.span, path_token.span) };
}

function parse_define(c: Cursor): ConstDecl {
  const start = advance(c);
  const name = expect_ident(c, "tras define");
  const declared_type = at(c, ":") ? (advance(c), parse_type(c)) : undefined;
  expect(c, "=", "en el define");
  const value = parse_expression(c);
  return {
    kind: "const_decl",
    name: name?.text ?? "__error__",
    declared_type,
    value,
    is_static: false,
    mutable: false,
    is_define: true,
    span: merge_span(start.span, value.span),
  };
}

function parse_opaque(c: Cursor): OpaqueDecl {
  const start = advance(c);
  const name = expect_ident(c, "tras opaque");
  return {
    kind: "opaque_decl",
    name: name?.text ?? "__error__",
    name_span: name?.span ?? start.span,
    span: merge_span(start.span, name?.span ?? start.span),
  };
}

function parse_callback(c: Cursor): CallbackDecl {
  const start = advance(c);
  const name = expect_ident(c, "tras callback");
  expect(c, "=", "en la firma del callback");
  const params = at(c, "->") ? [] : parse_params(c);
  expect(c, "->", "en la firma del callback");
  const result = parse_type(c);
  return {
    kind: "callback_decl",
    name: name?.text ?? "__error__",
    name_span: name?.span ?? start.span,
    params,
    result,
    span: merge_span(start.span, result.span),
  };
}

function parse_meld(c: Cursor): MeldDecl {
  const start = advance(c);
  const name = expect_ident(c, "tras meld");
  const { sigils } = parse_sigils(c);

  const fields: FieldDecl[] = [];
  if (at(c, "newline") && peek(c, 1).kind === "indent") {
    open_indented(c, "del meld");
    while (!at(c, "dedent") && !at(c, "eof")) {
      if (at(c, "newline")) {
        advance(c);
        continue;
      }
      const field = parse_field(c);
      fields.push(field);
      accept_line_break(c, field.span, "en el meld");
    }
    if (at(c, "dedent")) advance(c);
  }

  const end = fields[fields.length - 1]?.span ?? name?.span ?? start.span;
  return {
    kind: "meld_decl",
    name: name?.text ?? "__error__",
    name_span: name?.span ?? start.span,
    sigils,
    fields,
    span: merge_span(start.span, end),
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
  // `echo js::String = string`: el alias también puede ser un nombre host.
  const name = expect_qualified_ident(c, `tras ${form}`);
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
  // El destino es un patrón de tipo: `string`, `vector<T>`, `tuple<int, string>`.
  // `array<T>` omite el tamaño: el patrón vale para cualquier `array<T, N>`.
  const target_type = parse_enchant_pattern(c)
    ?? parse_type(c)
    ?? { kind: "named_type", name: "__error__", args: [], span: start.span };
  const target = type_pattern_base(target_type);
  const sigils = type_pattern_sigils(target_type);
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

  const end = methods[methods.length - 1]?.span ?? target_type.span;
  return {
    kind: "enchanting_decl",
    target,
    target_span: target_type.span,
    target_type,
    sigils,
    methods,
    span: merge_span(start.span, end),
  };
}

function parse_enchant_pattern(c: Cursor): TypeNode | undefined {
  if (!at(c, "ident") || peek(c).text !== "array" || peek(c, 1).kind !== "<") return undefined;
  const name = advance(c);
  advance(c);
  const element = parse_type(c);
  expect(c, ">", "en el patrón array<T>");
  if (element === undefined) return undefined;
  return { kind: "named_type", name: "array", args: [element], span: merge_span(name.span, element.span) };
}

function parse_method(c: Cursor): MethodDecl {
  const async_token = eat(c, "async");
  const is_async = async_token !== undefined;
  const mutable = eat(c, "mut") !== undefined;
  let name: Token | undefined;
  let operator: string | undefined;

  if (at(c, "operator")) {
    if (async_token !== undefined) {
      push_error(
        c,
        CODES.async_not_allowed,
        "un operador no puede ser «async»",
        async_token.span,
      );
    }
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
    name = expect_name(c, "en el método");
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
    is_async,
    span: merge_span(name?.span ?? peek(c).span, body.span),
  };
}

function string_literal_text(token: Token): string {
  if (token.value !== undefined) return token.value;
  const parts = token.parts ?? [];
  return parts.map((part) => (part.kind === "text" ? part.text : "")).join("");
}


// Nombres de host: `js::Document`, `js::Array<T>`.
// Devuelve `{text, span}` para poder usarlo como un token.
export function expect_qualified_ident(c: Cursor, context: string): { text: string; span: Span } | undefined {
  // El nombre de un miembro del host puede coincidir con una palabra clave
  // (`host`, `delete`): en esa posición siempre es un nombre.
  const first = at(c, "ident") || is_keyword(peek(c).text) ? expect_name(c, context) : expect_ident(c, context);
  if (first === undefined) return undefined;
  let text = first.text;
  let end = first.span;
  while (at(c, "::")) {
    advance(c);
    const next = expect_ident(c, "tras «::»");
    if (next === undefined) break;
    text = `${text}::${next.text}`;
    end = next.span;
  }
  return { text, span: merge_span(first.span, end) };
}

// `host` describe un objeto del host sin código: propiedades, métodos,
// constructores e índice. La única construcción nueva del lenguaje (T1).
function parse_host(c: Cursor): DeclNode | undefined {
  const start = advance(c); // host

  const first = peek(c);
  if (first.kind === "ident" && first.text === "global" && peek(c, 1).kind === "ident") {
    advance(c);
    const name = expect_ident(c, "tras «host global»");
    let type: TypeNode | undefined;
    if (eat(c, ":") !== undefined) type = parse_type(c);
    const global: HostGlobalDecl = {
      kind: "host_global_decl",
      name: name?.text ?? "__error__",
      name_span: name?.span ?? start.span,
      type,
      span: merge_span(start.span, type?.span ?? name?.span ?? start.span),
    };
    return global;
  }

  if (first.kind === "ident" && first.text === "namespace" && peek(c, 1).kind === "ident") {
    advance(c);
    const name = expect_ident(c, "tras «host namespace»");
    const members = parse_host_members(c, "del namespace host");
    const namespace: HostNamespaceDecl = {
      kind: "host_namespace_decl",
      name: name?.text ?? "__error__",
      name_span: name?.span ?? start.span,
      members,
      span: merge_span(start.span, members[members.length - 1]?.span ?? name?.span ?? start.span),
    };
    return namespace;
  }

  const name = expect_qualified_ident(c, "tras «host»");
  const { sigils } = parse_sigils(c);
  let parent: TypeNode | undefined;
  if (eat(c, "heir") !== undefined) parent = parse_type(c);
  const members = parse_host_members(c, "del tipo host");
  const decl: HostTypeDecl = {
    kind: "host_decl",
    name: name?.text ?? "__error__",
    name_span: name?.span ?? start.span,
    sigils,
    parent,
    members,
    span: merge_span(start.span, members[members.length - 1]?.span ?? parent?.span ?? name?.span ?? start.span),
  };
  return decl;
}

function parse_host_members(c: Cursor, context: string): HostMember[] {
  const members: HostMember[] = [];
  if (!(at(c, "newline") && peek(c, 1).kind === "indent")) return members;

  open_indented(c, context);
  while (!at(c, "dedent") && !at(c, "eof")) {
    if (at(c, "newline")) {
      advance(c);
      continue;
    }
    const member = parse_host_member(c);
    if (member === undefined) {
      synchronize(c);
      continue;
    }
    members.push(member);
    accept_line_break(c, member.span, "entre miembros host");
  }
  if (at(c, "dedent")) advance(c);
  return members;
}

function parse_host_member(c: Cursor): HostMember | undefined {
  const start = peek(c).span;

  // `constructor(...)`: puede haber varias sobrecargas.
  if (at(c, "constructor")) {
    advance(c);
    const params = parse_params(c);
    const end = params[params.length - 1]?.span ?? start;
    const constructor: HostConstructor = {
      kind: "host_constructor",
      params,
      span: merge_span(start, end),
    };
    return constructor;
  }

  let is_static = false;
  if (at(c, "static")) {
    advance(c);
    is_static = true;
  }

  let mutable = false;
  if (at(c, "mut")) {
    advance(c);
    mutable = true;
  }

  // Índice: `mut [clave: int]: string`.
  if (at(c, "[")) {
    advance(c);
    const key_name = expect_ident(c, "en el índice host");
    expect(c, ":", "en el índice host");
    const key_type = parse_type(c);
    expect(c, "]", "en el índice host");
    expect(c, ":", "en el índice host");
    const value = parse_type(c);
    const index: HostIndex = {
      kind: "host_index",
      key_name: key_name?.text ?? "indice",
      key_type,
      value,
      mutable,
      span: merge_span(start, value.span),
    };
    return index;
  }

  const name = expect_qualified_ident(c, "en un miembro host");
  if (name === undefined) return undefined;
  const { sigils } = parse_sigils(c);
  const optional = eat(c, "?") !== undefined;

  // Dos formas equivalentes: `nombre: (a: T) -> R` y `nombre(a: T) -> R`.
  const colon_method = at(c, ":") && peek(c, 1).kind === "(";
  if (colon_method) advance(c);
  if (at(c, "(")) {
    const params = parse_params(c);
    expect(c, "->", "en la firma del método host");
    const result = parse_type(c);
    const method: HostMethod = {
      kind: "host_method",
      name: name.text,
      name_span: name.span,
      sigils,
      params,
      result,
      is_static,
      optional,
      span: merge_span(start, result?.span ?? name.span),
    };
    return method;
  }

  expect(c, ":", "en la propiedad host");
  const type = parse_type(c);
  const property: HostProperty = {
    kind: "host_property",
    name: name.text,
    name_span: name.span,
    type,
    mutable,
    optional,
    span: merge_span(start, type.span),
  };
  return property;
}
