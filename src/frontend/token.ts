import type { Span } from "../util/span.ts";

export const KEYWORDS = [
  "realm",
  "invoke",
  "from",
  "as",
  "rune",
  "omen",
  "echo",
  "seal",
  "enchanting",
  "heir",
  "constructor",
  "destructor",
  "parent",
  "flags",
  "match",
  "when",
  "then",
  "else",
  "if",
  "unless",
  "switch",
  "do",
  "while",
  "until",
  "repeat",
  "for",
  "in",
  "break",
  "continue",
  "return",
  "pass",
  "mut",
  "const",
  "static",
  "unsafe",
  "needs",
  "operator",
  "true",
  "false",
  "none",
  "nullptr",
  "and",
  "or",
  "not",
  "declare",
  "extern",
] as const;

export type Keyword = (typeof KEYWORDS)[number];

const KEYWORD_SET: ReadonlySet<string> = new Set(KEYWORDS);

export function is_keyword(text: string): text is Keyword {
  return KEYWORD_SET.has(text);
}

export const OPERATORS = [
  "<=>",
  "...",
  "<<=",
  ">>=",
  "..<",
  "->",
  "::",
  "==",
  "!=",
  "<=",
  ">=",
  "+=",
  "-=",
  "*=",
  "/=",
  "%=",
  "&=",
  "|=",
  "^=",
  "<<",
  ">>",
  "..",
  "(",
  ")",
  "[",
  "]",
  "{",
  "}",
  ",",
  ":",
  ".",
  "=",
  "+",
  "-",
  "*",
  "/",
  "%",
  "&",
  "|",
  "^",
  "~",
  "!",
  "<",
  ">",
  "?",
  "#",
  "@",
] as const;

export type Operator = (typeof OPERATORS)[number];

export type TokenKind =
  | "eof"
  | "newline"
  | "indent"
  | "dedent"
  | "comment"
  | "ident"
  | "int"
  | "float"
  | "string"
  | "char"
  | Keyword
  | Operator;

export interface TextPart {
  readonly kind: "text";
  readonly text: string;
}

export interface ExprPart {
  readonly kind: "expr";
  readonly tokens: readonly Token[];
  readonly span: Span;
}

export type StringPart = TextPart | ExprPart;

export interface Token {
  readonly kind: TokenKind;
  readonly text: string;
  readonly span: Span;
  readonly value?: string;
  readonly parts?: readonly StringPart[];
}

export function is_operator(token: Token, operator: Operator): boolean {
  return token.kind === operator;
}

export function has_interpolation(token: Token): boolean {
  return token.parts?.some((part) => part.kind === "expr") ?? false;
}

export function token_debug(token: Token): string {
  const text = token.kind === "newline" ? "\\n" : token.text;
  return `${token.kind}(${text})`;
}
