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

function is_word(token: Token): boolean {
  return token.kind === "ident" || is_keyword(token.text);
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
  // `@` y `#` designan un valor (el receptor o una interpolación): detrás de
  // ellos un `-` es resta, no signo.
  if (previous.text === "@" || previous.text === "#") return false;
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

function space_between(
  previous: Token | undefined,
  token: Token,
  tight: boolean,
  next: Token | undefined,
): boolean {
  if (previous === undefined) return false;
  // La cercanía del prefijo (`#xs`, `@campo`) no debe pegar el operador
  // binario que venga después: `@ < otro`, no `@< otro`.
  if (tight) {
    // La puntuación nunca se separa: `f(x, y)`, `xs[0]`.
    if (NO_SPACE_BEFORE.has(token.text)) return false;
    // Un operador binario detrás de `@`/`#` es una operación: `@ - x`.
    if (is_operator_token(token) && BINARY_OPERATORS.has(token.text)) return true;
    // Una palabra clave nunca se pega al operador de prefijo: `#@ then`.
    if (is_keyword(token.text)) return true;
    if (NO_SPACE_AFTER.has(previous.text)) return false;
    return false;
  }

  const text = token.text;

  if (TIGHT_OPERATORS.has(text) || TIGHT_OPERATORS.has(previous.text)) return false;

  // Los ángulos de los genéricos se escriben pegados (`vector<T>`); las
  // comparaciones llevan espacios. La cercanía original decide.
  const near_angle =
    text === "<" || text === ">" || text === ">>" || previous.text === "<" || previous.text === ">";
  if (near_angle && token.span.start.offset === previous.span.end.offset) return false;
  // `>>` que cierra argumentos de tipo: `ref<set<T>>`; el desplazamiento
  // binario (`a >> b`) conserva espacios porque le siguen operandos.
  if (text === ">>" && closes_type_arguments(next)) return false;
  if (previous.text === "operator") return true;
  if (is_operator_token(token) && NO_SPACE_BEFORE.has(text)) return false;
  // `#@then` no: una palabra clave nunca se pega a `#` ni `@`. Detrás de
  // `::` o `.` sí se pega, aunque sea palabra reservada: `size_t::from(4)`,
  // `result::Result`, `log::Level::Warn`.
  if (is_operator_token(previous) && NO_SPACE_AFTER.has(previous.text)) {
    if (!is_keyword(text)) return false;
    if (previous.text === "::" || previous.text === ".") return false;
  }

  // Llamadas: `f(x)`, `xs[0]`, `f<int>(x)`.
  if (text === "(" || text === "[") {
    if (is_word(previous) || previous.text === ")" || previous.text === "]") return false;
    if (previous.text === "constructor" || previous.text === "destructor" || previous.text === "parent") return false;
  }

  // En `a < b` hay espacio; en `vector<int>` no. La cercanía original
  // es la pista más fiable y se conserva entre pasadas.
  if (text === "<" || text === ">" || text === ">>" || text === "<<") {
    return token.span.start.offset > previous.span.end.offset;
  }

  if (is_operator_token(token) && BINARY_OPERATORS.has(text)) return true;
  if (is_keyword(text)) return true;
  if (is_keyword(previous.text)) return true;
  if (is_operator_token(previous) && BINARY_OPERATORS.has(previous.text)) return true;
  // Dos palabras seguidas son un nombre compuesto: «long double»,
  // «unsigned long». Pegarlas cambiaría el tipo.
  if (is_word(previous) && is_word(token)) return true;
  return false;
}

function next_content(tokens: readonly Token[], index: number): Token | undefined {
  for (let cursor = index + 1; cursor < tokens.length; cursor += 1) {
    const token = tokens[cursor];
    if (token === undefined) return undefined;
    if (token.kind === "comment") continue;
    return token;
  }
  return undefined;
}

function closes_type_arguments(next: Token | undefined): boolean {
  if (next === undefined) return true;
  if (next.kind === "newline" || next.kind === "dedent" || next.kind === "eof") return true;
  return [")", "]", "}", ",", ">", ">>", "=", "->", ":", "?"].includes(next.text);
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

  for (let token_index = 0; token_index < tokens.length; token_index += 1) {
    const token = tokens[token_index] as Token;
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
        const space =
          builder.buffer.length > 0 && space_between(previous, token, tight, next_content(tokens, token_index));
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
