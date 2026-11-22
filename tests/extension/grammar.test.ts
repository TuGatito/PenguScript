// La gramática no debe quedarse atrás respecto al compilador: cada palabra
// clave, tipo y operador de `src/frontend` debe tener un patrón que lo pinte.

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  BUILTIN_TYPE_NAMES,
  FIXED_WIDTH_TYPES,
  PRIMITIVE_TYPES,
  STRING_TYPES,
} from "../../src/frontend/ast_type.ts";
import { KEYWORDS, OPERATORS } from "../../src/frontend/token.ts";

const extension_root = new URL("../../editors/vscode/", import.meta.url).pathname;
const grammar = JSON.parse(readFileSync(join(extension_root, "syntaxes/pengu.tmLanguage.json"), "utf8"));

type GrammarPattern = { readonly match?: string; readonly begin?: string; readonly patterns?: readonly GrammarPattern[] };

function regexes_of(group: string): string[] {
  const entry = grammar.repository[group] as GrammarPattern | undefined;
  if (entry === undefined) throw new Error(`grupo «${group}» no existe en la gramática`);
  const found: string[] = [];
  const walk = (patterns: readonly GrammarPattern[] | undefined): void => {
    for (const pattern of patterns ?? []) {
      if (pattern.match !== undefined) found.push(pattern.match);
      if (pattern.begin !== undefined) found.push(pattern.begin);
      walk(pattern.patterns);
    }
  };
  walk(entry.patterns === undefined ? [entry] : entry.patterns);
  return found;
}

const KEYWORD_GROUPS = ["declarations", "storage", "control", "constants"];
const TYPE_GROUPS = ["types"];
const OPERATOR_GROUPS = ["operators", "punctuation", "constants"];

function compiles(groups: readonly string[]): RegExp[] {
  return groups.flatMap((group) => regexes_of(group)).map((source) => new RegExp(source));
}

// Las palabras se prueban solas y en contextos habituales: algunas reglas están
// ancladas (`^(\s*)(realm)`) y otras exigen un espacio o un paréntesis detrás.
function samples_of(candidate: string): string[] {
  return [
    candidate,
    ` ${candidate}`,
    `${candidate} `,
    ` ${candidate} X`,
    `${candidate} X`,
    `${candidate}(`,
    `x ${candidate} x`,
  ];
}

function covered(patterns: readonly RegExp[], candidate: string): boolean {
  return samples_of(candidate).some((sample) => patterns.some((pattern) => pattern.test(sample)));
}

function check_covered(groups: readonly string[], names: readonly string[], label: string): void {
  const patterns = compiles(groups);
  const missing = names.filter((name) => !covered(patterns, name));
  expect({ label, missing }).toEqual({ label, missing: [] });
}

describe("gramática de PenguScript", () => {
  test("todas las palabras clave del compilador tienen scope", () => {
    check_covered(KEYWORD_GROUPS, [...KEYWORDS], "keywords");
  });

  test("todos los tipos del compilador tienen scope", () => {
    const names = new Set<string>([
      ...PRIMITIVE_TYPES,
      ...STRING_TYPES,
      ...FIXED_WIDTH_TYPES,
      ...BUILTIN_TYPE_NAMES,
      "Ordering",
    ]);
    check_covered(TYPE_GROUPS, [...names], "types");
  });

  test("todos los operadores del compilador tienen scope", () => {
    check_covered(OPERATOR_GROUPS, [...OPERATORS], "operators");
  });

  test("las expresiones regulares compilan", () => {
    for (const group of Object.keys(grammar.repository)) {
      expect(() => regexes_of(group).map((source) => new RegExp(source))).not.toThrow();
    }
  });

  test("los números cubren hex, binario, octal y float", () => {
    const numbers = regexes_of("numbers").map((source) => new RegExp(source));
    for (const sample of ["0xFF", "0b1010", "0o755", "3.14", "1e9", "42"]) {
      expect({ sample, matched: numbers.some((pattern) => pattern.test(sample)) }).toEqual({ sample, matched: true });
    }
  });

  test("las declaraciones y el self tienen scope propio", () => {
    const declarations = regexes_of("declarations").map((source) => new RegExp(source));
    expect(declarations.some((pattern) => pattern.test(" declare x = 1"))).toBe(true);
    const constants = regexes_of("constants").map((source) => new RegExp(source));
    expect(constants.some((pattern) => pattern.test("ref(@campo)"))).toBe(true);
  });
});
