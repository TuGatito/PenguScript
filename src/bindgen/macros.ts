// Lectura de las macros de una cabecera (`clang -E -dM`) y traducción
// de las que tienen un valor constante utilizable desde PenguScript.

import { spawnSync } from "node:child_process";
import type { NativeEnum } from "./clang_ast.ts";
import { is_keyword } from "../frontend/token.ts";

export interface NativeConstant {
  readonly name: string;
  readonly type: string;
  readonly value: string;
  // `define` emite `inline constexpr`; `const` se usa para inicializar
  // tipos que no son constantes de compilación (p. ej. un `Color`).
  readonly kind: "define" | "const";
}

export interface MacroTable {
  readonly constants: readonly NativeConstant[];
  readonly skipped: readonly string[];
}

interface RawMacro {
  readonly name: string;
  readonly body: string;
}

const INTEGER_LITERAL = /^[+-]?(0x[0-9a-fA-F]+|\d+)([uUlL]*)$/;
const FLOAT_LITERAL = /^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?([fFlL]?)$/;
const STRING_LITERAL = /^"(?:[^"\\]|\\.)*"$/;
const CHAR_LITERAL = /^'(?:[^'\\]|\\.)'$/;
const COMPOUND_LITERAL = /^(?:CLITERAL\(\s*([A-Za-z_]\w*)\s*\)|\(\s*([A-Za-z_]\w*)\s*\))\s*\{([^}]*)\}$/;

// Macros que vienen del compilador o de la plataforma y no describen la API.
const PLATFORM_PREFIXES = ["_", "PLATFORM_", "__"];

export function collect_macros(
  header: string,
  clang: string,
  include_dirs: readonly string[] = [],
  enums: readonly NativeEnum[] = [],
): MacroTable {
  const defines = spawnSync(
    clang,
    ["-x", "c++-header", "-std=c++20", ...include_dirs.flatMap((dir) => ["-I", dir]), "-E", "-dM", header],
    { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 },
  );
  if (defines.status !== 0) {
    return { constants: [], skipped: [(defines.stderr ?? "clang -dM falló").trim()] };
  }

  const macros: RawMacro[] = [];
  for (const line of (defines.stdout ?? "").split("\n")) {
    const match = /^#define\s+([A-Za-z_]\w*)(\([^)]*\))?\s*(.*)$/.exec(line.trim());
    if (match === null) continue;
    const name = match[1] ?? "";
    if (match[2] !== undefined) continue; // macro de función
    if (name.length === 1) continue;
    if (PLATFORM_PREFIXES.some((prefix) => name.startsWith(prefix))) continue;
    const body = (match[3] ?? "").trim();
    if (body.length === 0) continue; // guardas y macros vacías
    macros.push({ name, body });
  }

  const skipped: string[] = [];
  const known_enums = new Map<string, number>();
  for (const item of enums) {
    for (const variant of item.variants) known_enums.set(variant.name, variant.value);
  }
  const enum_names = new Set(enums.map((item) => item.name));

  const raw_by_name = new Map<string, string>();
  for (const macro of macros) raw_by_name.set(macro.name, macro.body);

  const constants: NativeConstant[] = [];
  const resolved = new Map<string, number>();
  const resolving = new Set<string>();

  // Valor numérico de un identificador: ya resuelto, variante de un omen o
  // una macro anterior a la que se puede seguir la pista.
  const lookup = (identifier: string, depth: number): number | undefined => {
    if (depth > 12) return undefined;
    const known = resolved.get(identifier);
    if (known !== undefined) return known;
    const variant = known_enums.get(identifier);
    if (variant !== undefined) return variant;
    const alias = raw_by_name.get(identifier);
    if (alias === undefined || resolving.has(identifier)) return undefined;
    resolving.add(identifier);
    const value = evaluate(alias, depth + 1);
    resolving.delete(identifier);
    return value;
  };

  const evaluate = (body: string, depth: number): number | undefined => {
    if (depth > 12) return undefined;
    const text = body.trim();
    const literal = INTEGER_LITERAL.exec(text);
    if (literal !== null) return Number(BigInt(text.replace(/[uUlL]+$/, "")));
    if (/^[A-Za-z_]\w*$/.test(text)) return lookup(text, depth);
    const integer = evaluate_integer(text, (identifier) => {
      const value = lookup(identifier, depth);
      return value === undefined || !Number.isInteger(value) ? undefined : BigInt(value);
    });
    if (integer !== undefined) return Number(integer);
    return evaluate_decimal(text, (identifier) => lookup(identifier, depth));
  };

  for (const macro of macros) {
    if (is_keyword(macro.name)) {
      skipped.push(`${macro.name}: el nombre es palabra reservada de PenguScript`);
      continue;
    }
    if (known_enums.has(macro.name) || enum_names.has(macro.name)) continue;

    const compound = COMPOUND_LITERAL.exec(macro.body);
    if (compound !== null) {
      const type = compound[1] ?? compound[2] ?? "";
      const args = (compound[3] ?? "").split(",").map((part) => part.trim());
      if (!/^[A-Za-z_]\w*$/.test(type) || args.length === 0 || args.some((arg) => !is_literal(arg))) {
        skipped.push(`${macro.name}: inicializador compuesto no traducible`);
        continue;
      }
      constants.push({ name: macro.name, type, value: `${type}(${args.join(", ")})`, kind: "const" });
      continue;
    }

    if (STRING_LITERAL.test(macro.body)) {
      constants.push({ name: macro.name, type: "string", value: macro.body, kind: "define" });
      continue;
    }
    if (CHAR_LITERAL.test(macro.body)) {
      constants.push({ name: macro.name, type: "char", value: macro.body, kind: "define" });
      continue;
    }
    if (FLOAT_LITERAL.test(macro.body) && /\d\.\d|[eE]/.test(macro.body)) {
      const value = Number(macro.body.replace(/[fFlL]$/, ""));
      if (!Number.isFinite(value)) {
        skipped.push(`${macro.name}: valor decimal no representable`);
        continue;
      }
      resolved.set(macro.name, value);
      constants.push({ name: macro.name, type: "double", value: format_decimal(value), kind: "define" });
      continue;
    }

    const value = evaluate(macro.body, 0);
    if (value === undefined || !Number.isFinite(value)) {
      skipped.push(`${macro.name}: valor no constante`);
      continue;
    }
    resolved.set(macro.name, value);
    if (Number.isInteger(value)) {
      const type = value < 0 ? "int64_t" : value <= 2147483647 ? "int" : "int64_t";
      constants.push({ name: macro.name, type, value: String(value), kind: "define" });
    } else {
      constants.push({ name: macro.name, type: "double", value: format_decimal(value), kind: "define" });
    }
  }

  return { constants, skipped };
}

function is_literal(text: string): boolean {
  return INTEGER_LITERAL.test(text) || FLOAT_LITERAL.test(text) || CHAR_LITERAL.test(text);
}

function format_decimal(value: number): string {
  const text = String(value);
  return /[.eE]/.test(text) ? text : `${text}.0`;
}

// Evaluador mínimo de expresiones enteras de C: enteros, identificadores,
// paréntesis y los operadores aritméticos y de bits habituales.
function evaluate_integer(
  text: string,
  lookup: (identifier: string) => bigint | undefined,
): bigint | undefined {
  let index = 0;
  const peek = (): string => text[index] ?? "";
  const skip = (): void => {
    while (/\s/.test(peek())) index += 1;
  };

  const parse_primary = (): bigint | undefined => {
    skip();
    const char = peek();
    if (char === "(") {
      index += 1;
      const inner = parse_or();
      skip();
      if (peek() !== ")") return undefined;
      index += 1;
      return inner;
    }
    if (char === "~") {
      index += 1;
      const inner = parse_primary();
      return inner === undefined ? undefined : ~inner;
    }
    if (char === "-") {
      index += 1;
      const inner = parse_primary();
      return inner === undefined ? undefined : -inner;
    }
    if (char === "+") {
      index += 1;
      return parse_primary();
    }
    const number = /^(0x[0-9a-fA-F]+|\d+)[uUlL]*/.exec(text.slice(index));
    if (number !== null) {
      index += number[0].length;
      return BigInt(number[0].replace(/[uUlL]+$/, ""));
    }
    const identifier = /^[A-Za-z_]\w*/.exec(text.slice(index));
    if (identifier !== null) {
      index += identifier[0].length;
      return lookup(identifier[0]);
    }
    return undefined;
  };

  const parse_shift = (): bigint | undefined => {
    let left = parse_primary();
    while (left !== undefined) {
      skip();
      if (text.startsWith("<<", index)) {
        index += 2;
        const right = parse_primary();
        left = right === undefined ? undefined : left << right;
      } else if (text.startsWith(">>", index)) {
        index += 2;
        const right = parse_primary();
        left = right === undefined ? undefined : left >> right;
      } else break;
    }
    return left;
  };

  const parse_term = (): bigint | undefined => {
    let left = parse_shift();
    while (left !== undefined) {
      skip();
      const char = peek();
      if (char !== "*" && char !== "/" && char !== "%") break;
      index += 1;
      const right = parse_shift();
      if (right === undefined) return undefined;
      if ((char === "/" || char === "%") && right === 0n) return undefined;
      left = char === "*" ? left * right : char === "/" ? left / right : left % right;
    }
    return left;
  };

  const parse_sum = (): bigint | undefined => {
    let left = parse_term();
    while (left !== undefined) {
      skip();
      const char = peek();
      if (char !== "+" && char !== "-") break;
      index += 1;
      const right = parse_term();
      if (right === undefined) return undefined;
      left = char === "+" ? left + right : left - right;
    }
    return left;
  };

  const parse_and = (): bigint | undefined => {
    let left = parse_sum();
    while (left !== undefined && peek() === "&" && !text.startsWith("&&", index)) {
      index += 1;
      const right = parse_sum();
      left = right === undefined ? undefined : left & right;
    }
    return left;
  };

  const parse_xor = (): bigint | undefined => {
    let left = parse_and();
    while (left !== undefined && peek() === "^") {
      index += 1;
      const right = parse_and();
      left = right === undefined ? undefined : left ^ right;
    }
    return left;
  };

  const parse_or = (): bigint | undefined => {
    let left = parse_xor();
    while (left !== undefined && peek() === "|") {
      index += 1;
      const right = parse_xor();
      left = right === undefined ? undefined : left | right;
    }
    return left;
  };

  const value = parse_or();
  skip();
  if (value === undefined || index !== text.length) return undefined;
  return value;
}

// Evaluador decimal: es el que resuelve expresiones como `(PI/180.0f)`,
// donde los enteros no bastan porque la división no es exacta.
function evaluate_decimal(
  text: string,
  lookup: (identifier: string) => number | undefined,
): number | undefined {
  let index = 0;
  const peek = (): string => text[index] ?? "";
  const skip = (): void => {
    while (/\s/.test(peek())) index += 1;
  };

  const parse_primary = (): number | undefined => {
    skip();
    const char = peek();
    if (char === "(") {
      index += 1;
      const inner = parse_sum();
      skip();
      if (peek() !== ")") return undefined;
      index += 1;
      return inner;
    }
    if (char === "-") {
      index += 1;
      const inner = parse_primary();
      return inner === undefined ? undefined : -inner;
    }
    if (char === "+") {
      index += 1;
      return parse_primary();
    }
    const number = /^(0x[0-9a-fA-F]+|(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)[fFlLuU]*/.exec(text.slice(index));
    if (number !== null) {
      index += number[0].length;
      const cleaned = number[0].replace(/[fFlLuU]+$/, "");
      const value = cleaned.startsWith("0x") ? Number.parseInt(cleaned, 16) : Number(cleaned);
      return Number.isFinite(value) ? value : undefined;
    }
    const identifier = /^[A-Za-z_]\w*/.exec(text.slice(index));
    if (identifier !== null) {
      index += identifier[0].length;
      return lookup(identifier[0]);
    }
    return undefined;
  };

  const parse_term = (): number | undefined => {
    let left = parse_primary();
    while (left !== undefined) {
      skip();
      const char = peek();
      if (char !== "*" && char !== "/") break;
      index += 1;
      const right = parse_primary();
      if (right === undefined) return undefined;
      if (char === "/" && right === 0) return undefined;
      left = char === "*" ? left * right : left / right;
    }
    return left;
  };

  const parse_sum = (): number | undefined => {
    let left = parse_term();
    while (left !== undefined) {
      skip();
      const char = peek();
      if (char !== "+" && char !== "-") break;
      index += 1;
      const right = parse_term();
      if (right === undefined) return undefined;
      left = char === "+" ? left + right : left - right;
    }
    return left;
  };

  const value = parse_sum();
  skip();
  if (value === undefined || index !== text.length) return undefined;
  return value;
}
