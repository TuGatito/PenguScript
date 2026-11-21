import { CODES } from "../diagnostics/codes.ts";
import { make_diagnostic, type Diagnostic } from "../diagnostics/diagnostic.ts";
import { make_source, span_from, type Source } from "../util/span.ts";
import { OPERATORS, is_keyword, type StringPart, type Token, type TokenKind } from "./token.ts";
export interface LexResult {
  readonly source: Source;
  readonly tokens: readonly Token[];
  readonly diagnostics: readonly Diagnostic[];
}

interface LexerState {
  readonly source: Source;
  readonly text: string;
  index: number;
  readonly indent_stack: number[];
  paren_depth: number;
  at_line_start: boolean;
  readonly diagnostics: Diagnostic[];
}

interface TokenExtra {
  readonly value?: string;
  readonly parts?: readonly StringPart[];
}

function emit(
  state: LexerState,
  sink: Token[],
  kind: TokenKind,
  start: number,
  end: number,
  extra: TokenExtra = {},
): Token {
  const token: Token = {
    kind,
    text: state.text.slice(start, end),
    span: span_from(state.source, start, end),
    ...(extra.value !== undefined ? { value: extra.value } : {}),
    ...(extra.parts !== undefined ? { parts: extra.parts } : {}),
  };
  sink.push(token);
  return token;
}

function fail(
  state: LexerState,
  code: string,
  message: string,
  start: number,
  end: number,
  ...notes: string[]
): void {
  state.diagnostics.push(make_diagnostic({ code, message, span: span_from(state.source, start, end), notes }));
}

function warn(
  state: LexerState,
  code: string,
  message: string,
  start: number,
  end: number,
  ...notes: string[]
): void {
  state.diagnostics.push(
    make_diagnostic({ code, message, span: span_from(state.source, start, end), severity: "warning", notes }),
  );
}

function skip_horizontal(state: LexerState): void {
  while (state.index < state.text.length) {
    const ch = state.text.charAt(state.index);
    if (ch !== " " && ch !== "\t") return;
    state.index += 1;
  }
}

function skip_newline(state: LexerState, from: number): number {
  if (state.text.charAt(from) === "\r" && state.text.charAt(from + 1) === "\n") return from + 2;
  return from + 1;
}

function handle_newline(state: LexerState, sink: Token[]): void {
  const start = state.index;
  const next = skip_newline(state, start);
  state.index = next;
  if (state.paren_depth > 0) return;
  emit(state, sink, "newline", start, next);
  state.at_line_start = true;
}

function scan_comment(state: LexerState, sink: Token[]): void {
  const start = state.index;
  while (state.index < state.text.length) {
    const ch = state.text.charAt(state.index);
    if (ch === "\n" || ch === "\r") break;
    state.index += 1;
  }
  emit(state, sink, "comment", start, state.index);
}

function is_ident_start(ch: string): boolean {
  if (ch === "_") return true;
  const code = ch.charCodeAt(0);
  if (code === 0) return false;
  return (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || code > 127;
}

function is_ident_continue(ch: string): boolean {
  if (ch === "_") return true;
  const code = ch.charCodeAt(0);
  if (code === 0) return false;
  return (
    (code >= 65 && code <= 90) ||
    (code >= 97 && code <= 122) ||
    (code >= 48 && code <= 57) ||
    code > 127
  );
}

function is_digit(ch: string): boolean {
  const code = ch.charCodeAt(0);
  return code >= 48 && code <= 57;
}

function scan_ident(state: LexerState, sink: Token[]): void {
  const start = state.index;
  while (state.index < state.text.length && is_ident_continue(state.text.charAt(state.index))) {
    state.index += 1;
  }
  const text = state.text.slice(start, state.index);
  emit(state, sink, is_keyword(text) ? text : "ident", start, state.index);
}

function scan_number(state: LexerState, sink: Token[]): void {
  const start = state.index;
  const rest = state.text.slice(start);
  const prefixed = /^(0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+)/.exec(rest);
  if (prefixed) {
    const raw = prefixed[0];
    state.index = start + raw.length;
    emit(state, sink, "int", start, state.index, { value: raw.replace(/_/g, "") });
    return;
  }
  const decimal = /^\d[\d_]*(?:\.[0-9][0-9_]*)?(?:[eE][+-]?\d[\d_]*)?/.exec(rest);
  if (!decimal) {
    fail(state, CODES.invalid_number, "número inválido", start, start + 1);
    state.index = start + 1;
    return;
  }
  const raw = decimal[0];
  state.index = start + raw.length;
  const kind: TokenKind = raw.includes(".") || /[eE]/.test(raw) ? "float" : "int";
  emit(state, sink, kind, start, state.index, { value: raw.replace(/_/g, "") });
}

function decode_escape(state: LexerState): string {
  const start = state.index;
  state.index += 1;
  const ch = state.text.charAt(state.index);
  if (ch === "") {
    fail(state, CODES.invalid_escape, "escape incompleto al final del archivo", start, state.index);
    return "";
  }
  state.index += 1;
  switch (ch) {
    case "n":
      return "\n";
    case "t":
      return "\t";
    case "r":
      return "\r";
    case "0":
      return "\0";
    case "a":
      return "\x07";
    case "b":
      return "\b";
    case "f":
      return "\f";
    case "v":
      return "\v";
    case "\\":
      return "\\";
    case '"':
      return '"';
    case "'":
      return "'";
    case "#":
      return "#";
    case "x": {
      const hex = state.text.slice(state.index, state.index + 2);
      if (!/^[0-9a-fA-F]{2}$/.test(hex)) {
        fail(state, CODES.invalid_escape, `escape '\\x' requiere dos dígitos hexadecimales`, start, state.index);
        return "";
      }
      state.index += 2;
      return String.fromCharCode(Number.parseInt(hex, 16));
    }
    case "u": {
      if (state.text.charAt(state.index) !== "{") {
        fail(state, CODES.invalid_escape, `escape '\\u' requiere la forma '\\u{...}'`, start, state.index);
        return "";
      }
      const close = state.text.indexOf("}", state.index);
      if (close < 0) {
        fail(state, CODES.invalid_escape, "escape '\\u{...}' sin cerrar", start, state.index);
        state.index = state.text.length;
        return "";
      }
      const hex = state.text.slice(state.index + 1, close);
      state.index = close + 1;
      if (!/^[0-9a-fA-F]{1,6}$/.test(hex)) {
        fail(state, CODES.invalid_escape, `código Unicode inválido '${hex}'`, start, state.index);
        return "";
      }
      const code = Number.parseInt(hex, 16);
      if (code > 0x10ffff) {
        fail(state, CODES.invalid_escape, `código Unicode fuera de rango '${hex}'`, start, state.index);
        return "";
      }
      return String.fromCodePoint(code);
    }
    default:
      warn(state, CODES.invalid_escape, `escape desconocido '\\${ch}'`, start, state.index);
      return ch;
  }
}

function scan_string(state: LexerState, sink: Token[]): void {
  const start = state.index;
  state.index += 1;
  let closed = false;
  let buffer = "";
  const parts: StringPart[] = [];

  const flush_text = (): void => {
    if (buffer.length > 0) {
      parts.push({ kind: "text", text: buffer });
      buffer = "";
    }
  };

  while (state.index < state.text.length) {
    const ch = state.text.charAt(state.index);
    if (ch === '"') {
      state.index += 1;
      closed = true;
      break;
    }
    if (ch === "\\") {
      buffer += decode_escape(state);
      continue;
    }
    if (ch === "#" && state.text.charAt(state.index + 1) === "{") {
      flush_text();
      const expr_start = state.index + 2;
      state.index += 2;
      const tokens = scan_interpolation(state);
      parts.push({
        kind: "expr",
        tokens,
        span: span_from(state.source, expr_start, Math.max(expr_start, state.index - 1)),
      });
      continue;
    }
    buffer += ch;
    state.index += 1;
  }

  if (!closed) {
    fail(state, CODES.unterminated_string, "cadena sin cerrar", start, state.index);
  }
  flush_text();

  const has_expr = parts.some((part) => part.kind === "expr");
  if (!has_expr && parts.length <= 1) {
    const text = parts[0]?.kind === "text" ? parts[0].text : "";
    emit(state, sink, "string", start, state.index, { value: text });
    return;
  }
  emit(state, sink, "string", start, state.index, { parts });
}

function scan_char(state: LexerState, sink: Token[]): void {
  const start = state.index;
  state.index += 1;
  let value = "";
  if (state.text.charAt(state.index) === "'") {
    state.index += 1;
    fail(state, CODES.invalid_char, "literal de carácter vacío", start, state.index);
    emit(state, sink, "char", start, state.index, { value });
    return;
  }
  if (state.text.charAt(state.index) === "\\") {
    value = decode_escape(state);
  } else {
    const ch = state.text.charAt(state.index);
    if (ch === "" || ch === "\n" || ch === "\r") {
      fail(state, CODES.invalid_char, "literal de carácter sin cerrar", start, state.index);
      emit(state, sink, "char", start, state.index, { value });
      return;
    }
    value = ch;
    state.index += 1;
  }
  if (state.text.charAt(state.index) !== "'") {
    fail(state, CODES.invalid_char, "un literal de carácter debe contener exactamente un carácter", start, state.index);
    while (state.index < state.text.length) {
      const ch = state.text.charAt(state.index);
      if (ch === "'" || ch === "\n" || ch === "\r") break;
      state.index += 1;
    }
    if (state.text.charAt(state.index) === "'") state.index += 1;
    emit(state, sink, "char", start, state.index, { value });
    return;
  }
  state.index += 1;
  if (value.length !== 1) {
    fail(state, CODES.invalid_char, "un literal de carácter debe contener exactamente un carácter", start, state.index);
  }
  emit(state, sink, "char", start, state.index, { value });
}

function scan_interpolation(state: LexerState): Token[] {
  const tokens: Token[] = [];
  const start = state.index;
  let depth = 0;
  while (state.index < state.text.length) {
    const ch = state.text.charAt(state.index);
    if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r") {
      state.index += 1;
      continue;
    }
    if (ch === "}" && depth === 0) {
      state.index += 1;
      return tokens;
    }
    if (ch === "}") {
      depth -= 1;
      emit(state, tokens, "}", state.index, state.index + 1);
      state.index += 1;
      continue;
    }
    if (ch === "{") {
      depth += 1;
      emit(state, tokens, "{", state.index, state.index + 1);
      state.index += 1;
      continue;
    }
    scan_plain_token(state, tokens);
  }
  fail(state, CODES.unterminated_interpolation, "interpolación '#{' sin cerrar", start, state.index);
  return tokens;
}

function match_operator(text: string, start: number): string | undefined {
  for (const operator of OPERATORS) {
    if (text.startsWith(operator, start)) return operator;
  }
  return undefined;
}

function scan_plain_token(state: LexerState, sink: Token[]): void {
  const start = state.index;
  const ch = state.text.charAt(start);
  if (ch === "-" && state.text.charAt(start + 1) === "-") {
    scan_comment(state, sink);
    return;
  }
  if (is_ident_start(ch)) {
    scan_ident(state, sink);
    return;
  }
  if (is_digit(ch)) {
    scan_number(state, sink);
    return;
  }
  if (ch === '"') {
    scan_string(state, sink);
    return;
  }
  if (ch === "'") {
    scan_char(state, sink);
    return;
  }
  const operator = match_operator(state.text, start);
  if (operator !== undefined) {
    state.index = start + operator.length;
    emit(state, sink, operator as TokenKind, start, state.index);
    if (operator === "(" || operator === "[" || operator === "{") {
      state.paren_depth += 1;
    } else if (operator === ")" || operator === "]" || operator === "}") {
      state.paren_depth = Math.max(0, state.paren_depth - 1);
    }
    return;
  }
  fail(state, CODES.unexpected_char, `carácter inesperado '${ch}'`, start, start + 1);
  state.index = start + 1;
}

function begin_line(state: LexerState, sink: Token[]): "code" | "blank" | "comment" | "eof" {
  const start = state.index;
  const text = state.text;
  let probe = start;
  let spaces = 0;
  let tabs = 0;
  while (probe < text.length) {
    const ch = text.charAt(probe);
    if (ch === " ") {
      spaces += 1;
      probe += 1;
    } else if (ch === "\t") {
      tabs += 1;
      probe += 1;
    } else {
      break;
    }
  }
  if (probe >= text.length) {
    state.index = probe;
    return "eof";
  }
  const ch = text.charAt(probe);
  if (ch === "\n" || ch === "\r") {
    state.index = skip_newline(state, probe);
    return "blank";
  }
  if (ch === "-" && text.charAt(probe + 1) === "-") {
    state.index = probe;
    scan_comment(state, sink);
    state.index = skip_newline(state, state.index);
    return "comment";
  }
  if (spaces > 0 && tabs > 0) {
    fail(
      state,
      CODES.indent_mixed,
      "indentación mixta: usa espacios o tabuladores, no ambos en la misma línea",
      start,
      probe,
    );
  }
  const width = probe - start;
  const stack = state.indent_stack;
  const top = stack[stack.length - 1] ?? 0;
  if (width > top) {
    stack.push(width);
    emit(state, sink, "indent", start, probe);
  } else if (width < top) {
    const open_levels = [...stack];
    while (stack.length > 1 && (stack[stack.length - 1] ?? 0) > width) {
      stack.pop();
      emit(state, sink, "dedent", start, probe);
    }
    if ((stack[stack.length - 1] ?? 0) !== width) {
      report_indent_mismatch(state, start, probe, width, open_levels);
      stack.push(width);
      emit(state, sink, "indent", start, probe);
    }
  }
  state.index = probe;
  state.at_line_start = false;
  return "code";
}

// El ancho no coincide con ningún nivel abierto. Se sugiere el nivel
// más cercano y se ofrece un arreglo que reemplaza la sangría.
function report_indent_mismatch(
  state: LexerState,
  start: number,
  probe: number,
  width: number,
  open_levels: readonly number[],
): void {
  // El nivel más cercano; en caso de empate preferimos el mayor
  // (la sangría a la que probablemente se quería llegar).
  let expected = open_levels[0] ?? 0;
  for (const level of open_levels) {
    const distance = Math.abs(level - width);
    const current = Math.abs(expected - width);
    if (distance < current || (distance === current && level > expected)) expected = level;
  }
  const unit = state.text.slice(start, probe).includes("\t") ? "\t" : " ";
  const fix = {
    title: `usar ${expected} de sangría`,
    span: span_from(state.source, start, probe),
    replacement: unit.repeat(expected),
  };
  state.diagnostics.push(
    make_diagnostic({
      code: CODES.indent_mismatch,
      message: `la indentación (${width}) no coincide con ningún bloque abierto`,
      span: span_from(state.source, start, probe),
      notes: [
        `niveles abiertos: ${open_levels.join(", ")}`,
        `la sangría más cercana es ${expected}`,
      ],
      fix,
    }),
  );
}

export function lex(source: Source): LexResult {
  const state: LexerState = {
    source,
    text: source.text,
    // Un BOM UTF-8 al inicio no es parte del código: se salta sin
    // desplazar las posiciones del resto del archivo.
    index: source.text.charCodeAt(0) === 0xfeff ? 1 : 0,
    indent_stack: [0],
    paren_depth: 0,
    at_line_start: true,
    diagnostics: [],
  };
  const tokens: Token[] = [];

  while (state.index < state.text.length) {
    if (state.at_line_start && state.paren_depth === 0) {
      const line = begin_line(state, tokens);
      if (line !== "code") continue;
    }
    skip_horizontal(state);
    if (state.index >= state.text.length) break;
    const ch = state.text.charAt(state.index);
    if (ch === "\n" || ch === "\r") {
      handle_newline(state, tokens);
      continue;
    }
    scan_plain_token(state, tokens);
  }

  const end = state.text.length;
  while (state.indent_stack.length > 1) {
    state.indent_stack.pop();
    emit(state, tokens, "dedent", end, end);
  }
  emit(state, tokens, "eof", end, end);

  return { source, tokens, diagnostics: state.diagnostics };
}

export function lex_text(file: string, text: string): LexResult {
  return lex(make_source(file, text));
}
