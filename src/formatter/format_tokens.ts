// Formateador de tokens.
//
// El lexer ya resolvió la indentación (INDENT/DEDENT) y los finales de
// línea (NEWLINE), así que el formateador reconstruye el texto sin
// reinterpretar el programa. El resultado es estable: formatear dos
// veces produce el mismo texto.

import { lex } from "../frontend/lexer.ts";
import { OPERATORS } from "../frontend/token.ts";
import type { Token } from "../frontend/token.ts";
import { is_keyword } from "../frontend/token.ts";
import { make_source } from "../util/span.ts";

export interface FormatOptions {
  /** Espacios por nivel de indentación. */
  readonly indent_width?: number;
  /** Líneas en blanco consecutivas que se conservan como máximo. */
  readonly max_blank_lines?: number;
}

const BINARY_OPERATORS: ReadonlySet<string> = new Set([
  "=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=",
  "->", "<=>", "==", "!=", "<=", ">=", "<", ">", "+", "-", "*", "/",
  "%", "&", "|", "^", "<<", ">>", ":", ",", "and", "or", "in", "as",
]);

const PREFIX_OPERATORS: ReadonlySet<string> = new Set(["#", "@", "~"]);

const NO_SPACE_BEFORE: ReadonlySet<string> = new Set([")", "]", "}", ",", ":", "::", ".", "?"]);

const NO_SPACE_AFTER: ReadonlySet<string> = new Set(["(", "[", "::", ".", "#", "@"]);

const TIGHT_OPERATORS: ReadonlySet<string> = new Set(["..", "..<", "!"]);

const OPERATOR_KINDS: ReadonlySet<string> = new Set(OPERATORS);

function is_operator_token(token: Token): boolean {
  return OPERATOR_KINDS.has(token.kind);
}

function is_comment(token: Token): boolean {
  return token.kind === "comment";
}

function is_layout(token: Token): boolean {
  return token.kind === "indent" || token.kind === "dedent" || token.kind === "newline" || token.kind === "eof";
}

function is_unary_position(previous: Token | undefined): boolean {
  if (previous === undefined) return true;
  if (is_layout(previous) || is_comment(previous)) return true;
  if (is_keyword(previous.kind)) return true;
  if (is_operator_token(previous)) {
    if (previous.text === ")" || previous.text === "]" || previous.text === "}") return false;
    return previous.text !== "?";
  }
  return false;
}

// Un operador de prefijo (por ejemplo `-` en `-x`) no lleva espacio
// detrás, pero sí delante cuando hay algo antes.
function is_prefix_operator(token: Token, previous: Token | undefined): boolean {
  if (!is_operator_token(token)) return false;
  if (previous !== undefined && previous.text === "operator") return false;
  if (PREFIX_OPERATORS.has(token.text)) return true;
  if (token.text === "-" || token.text === "+" || token.text === "*" || token.text === "&") {
    return is_unary_position(previous);
  }
  return false;
}

function space_between(previous: Token | undefined, token: Token, tight: boolean): boolean {
  if (previous === undefined) return false;
  if (tight) return false;

  const text = token.text;

  if (TIGHT_OPERATORS.has(text) || TIGHT_OPERATORS.has(previous.text)) return false;

  // Los ángulos de los genéricos se escriben pegados (`vector<T>`); las
  // comparaciones llevan espacios. La cercanía original decide.
  const near_angle = text === "<" || text === ">" || previous.text === "<" || previous.text === ">";
  if (near_angle && token.span.start.offset === previous.span.end.offset) return false;
  if (previous.text === "operator") return true;
  if (is_operator_token(token) && NO_SPACE_BEFORE.has(text)) return false;
  if (is_operator_token(previous) && NO_SPACE_AFTER.has(previous.text)) return false;

  // Llamadas: `f(x)`, `xs[0]`, `f<int>(x)`.
  if (text === "(" || text === "[") {
    if (previous.kind === "ident" || previous.text === ")" || previous.text === "]") return false;
    if (previous.text === "constructor" || previous.text === "destructor" || previous.text === "parent") return false;
  }

  // En `a < b` hay espacio; en `vector<int>` no. La cercanía original
  // es la pista más fiable y se conserva entre pasadas.
  if (text === "<" || text === ">") {
    return token.span.start.offset > previous.span.end.offset;
  }

  if (is_operator_token(token) && BINARY_OPERATORS.has(text)) return true;
  if (is_keyword(text)) return true;
  if (is_keyword(previous.text)) return true;
  if (is_operator_token(previous) && BINARY_OPERATORS.has(previous.text)) return true;
  return false;
}

interface Builder {
  readonly lines: string[];
  buffer: string;
  indent: number;
  blanks: number;
  last_line: number;
}

function flush(builder: Builder, max_blank_lines: number): void {
  const text = builder.buffer.trimEnd();
  builder.buffer = "";
  if (text.length === 0) {
    builder.blanks += 1;
    if (builder.blanks > max_blank_lines) return;
    builder.lines.push("");
    return;
  }
  builder.blanks = 0;
  builder.lines.push(`${" ".repeat(builder.indent)}${text}`);
}

export function format_tokens(tokens: readonly Token[], options: FormatOptions = {}): string {
  const indent_width = options.indent_width ?? 2;
  const max_blank_lines = options.max_blank_lines ?? 1;
  const builder: Builder = { lines: [], buffer: "", indent: 0, blanks: 0, last_line: 0 };

  let previous: Token | undefined;
  let prefix_pending = false;

  for (const token of tokens) {
    switch (token.kind) {
      case "eof":
        flush(builder, max_blank_lines);
        break;
      case "indent":
        builder.indent += indent_width;
        previous = undefined;
        break;
      case "dedent":
        builder.indent = Math.max(0, builder.indent - indent_width);
        previous = undefined;
        break;
      case "newline":
        flush(builder, max_blank_lines);
        previous = undefined;
        prefix_pending = false;
        break;
      case "comment": {
        // Un comentario ocupa su propia línea.
        if (builder.buffer.trim().length > 0) flush(builder, max_blank_lines);
        if (token.span.start.line > builder.last_line + 1) builder.lines.push("");
        builder.buffer = token.text.trimEnd();
        flush(builder, max_blank_lines);
        builder.last_line = token.span.end.line;
        previous = undefined;
        break;
      }
      default: {
        if (builder.buffer.length === 0 && token.span.start.line > builder.last_line + 1) {
          builder.lines.push("");
        }
        const tight = prefix_pending;
        const space = builder.buffer.length > 0 && space_between(previous, token, tight);
        const appended = `${space ? " " : ""}${token.text}`;

        const pieces = appended.split("\n");
        builder.buffer += pieces[0] ?? "";
        for (let index = 1; index < pieces.length; index += 1) {
          builder.lines.push(builder.buffer);
          builder.buffer = pieces[index] as string;
        }

        prefix_pending = is_prefix_operator(token, previous);
        builder.last_line = token.span.end.line;
        previous = token;
        break;
      }
    }
  }

  while (builder.lines.length > 0 && (builder.lines[builder.lines.length - 1] as string).length === 0) {
    builder.lines.pop();
  }

  return `${builder.lines.join("\n")}\n`;
}

export function format_text(file: string, text: string, options: FormatOptions = {}): string {
  return format_tokens(lex(make_source(file, text)).tokens, options);
}
