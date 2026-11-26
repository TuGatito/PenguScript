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

  // Las pruebas de arriba solo comprueban que existe *algún* patrón capaz de
  // pintar cada palabra. Estas comprueban el resultado: se recorre la gramática
  // en el mismo orden que usa el editor (gana el patrón que empieza antes y, en
  // empate, el que aparece antes) y se mira el scope del token concreto.
  test("cada construcción se pinta con su scope", () => {
    const cases: readonly [string, string, string][] = [
      ["  const total = 3", "total", "variable.other.definition.pengu"],
      ["  const total = 3", "const", "storage.modifier.pengu"],
      ["  mut vidas: int = 3", "vidas", "variable.other.definition.pengu"],
      ["  cadena += \"m\"", "cadena", "variable.other.assign.pengu"],
      ["saludar(\"hola\")", "saludar", "entity.name.function.call.pengu"],
      ["  io::println(\"x\")", "io", "entity.name.namespace.realm.pengu"],
      ["  io::println(\"x\")", "println", "entity.name.function.call.pengu"],
      ["  math::pi", "pi", "variable.other.namespace-member.pengu"],
      ["  Color::Red", "Red", "support.constant.omen.pengu"],
      ["  Ordering::Less", "Ordering", "entity.name.type.pengu"],
      ["  Shape::Circle(2.0)", "Circle", "support.constant.omen.pengu"],
      ["  js::Document", "Document", "support.type.host.pengu"],
      ["  document.title = \"x\"", "title", "variable.other.property.pengu"],
      ["  document.getElementById(\"a\")", "getElementById", "entity.name.function.call.pengu"],
      ["  letras.push(c)", "push", "entity.name.function.call.pengu"],
      ["  const p = Punto(1.0, 2.0)", "Punto", "entity.name.function.constructor-call.pengu"],
      ["main = ->", "main", "entity.name.function.pengu"],
      ["  pedir = (n: int) -> int", "pedir", "entity.name.function.pengu"],
      ["  pedir = (n: int) -> int", "n", "variable.parameter.pengu"],
      ["  mut translate: (dx: double) -> void", "translate", "entity.name.function.method.pengu"],
      ["  mut[indice: int]: string", "indice", "variable.parameter.index.pengu"],
      ["  mut[indice: int]: string", "mut", "storage.modifier.pengu"],
      ["  for i in 0..<3", "i", "variable.other.definition.pengu"],
      ["  for clave, valor in mapa", "valor", "variable.other.definition.pengu"],
      ["rune Punto heir Base", "Punto", "entity.name.type.pengu"],
      ["rune Punto heir Base", "Base", "entity.name.type.pengu"],
      ["host global document", "document", "entity.name.variable.global.pengu"],
      ["host namespace Math", "Math", "entity.name.namespace.pengu"],
      ["host js::URL", "js::URL", "entity.name.type.host.pengu"],
      ["  const x = valor as Punto", "Punto", "entity.name.type.cast.pengu"],
      ["  pedir = () -> Punto", "Punto", "entity.name.type.pengu"],
      ["  constructor(x: double)", "constructor", "entity.name.function.constructor.pengu"],
      ["  mut @x = 3", "@", "variable.language.self.pengu"],
      ["  -- un comentario", "-- un comentario", "comment.line.double-dash.pengu"],
      ["  return suma(1, 2)", "return", "keyword.control.pengu"],
      ["  if not vacio then", "not", "keyword.operator.word.pengu"],
      ["  match forma", "match", "keyword.control.pengu"],
    ];
    for (const [line, text, expected] of cases) {
      const found = scopes_of(line, text);
      expect({ line, text, found: found.includes(expected) }).toEqual({ line, text, found: true });
    }
  });
});

// --- Simulador mínimo del motor de TextMate ------------------------------
//
// Recorre el texto como el editor: en cada paso gana el patrón que empieza
// antes y, si empatan, el que se declara primero. No modela las regiones
// `begin`/`end` (cadenas y comentarios) más allá de su comienzo, que es lo que
// necesitan las comprobaciones de arriba.

interface RawPattern {
  readonly name?: string;
  readonly match?: string;
  readonly begin?: string;
  readonly captures?: Readonly<Record<string, { readonly name?: string }>>;
  readonly beginCaptures?: Readonly<Record<string, { readonly name?: string }>>;
  readonly patterns?: readonly RawPattern[];
}

interface OrderedPattern {
  readonly pattern: RawPattern;
}

function ordered_patterns(): OrderedPattern[] {
  const repository = grammar.repository as Record<string, RawPattern>;
  const ordered: OrderedPattern[] = [];
  const walk = (patterns: readonly RawPattern[] | undefined): void => {
    for (const pattern of patterns ?? []) {
      ordered.push({ pattern });
      walk(pattern.patterns);
    }
  };
  for (const entry of grammar.patterns as { include: string }[]) {
    const group = repository[entry.include.slice(1)];
    if (group === undefined) throw new Error(`grupo «${entry.include}» no existe`);
    if (group.patterns === undefined) ordered.push({ pattern: group });
    else walk(group.patterns);
  }
  return ordered;
}

const ordered = ordered_patterns();

function scopes_of(line: string, text: string): string[] {
  const scopes: string[] = [];
  let rest = line;
  let guard = 0;
  while (rest.length > 0 && guard++ < 200) {
    let best: { index: number; pattern: RawPattern; match: RegExpMatchArray } | undefined;
    for (const { pattern } of ordered) {
      const source = pattern.match ?? pattern.begin;
      if (source === undefined) continue;
      const match = new RegExp(source).exec(rest);
      if (match === null) continue;
      if (best === undefined || match.index < best.index) best = { index: match.index, pattern, match };
    }
    if (best === undefined) break;
    const matched = best.match[0];
    if (matched.length === 0) break;
    const captures = { ...(best.pattern.beginCaptures ?? {}), ...(best.pattern.captures ?? {}) };
    let captured = false;
    for (const [index, capture] of Object.entries(captures)) {
      if (best.match[Number(index)]?.trim() !== text || capture.name === undefined) continue;
      scopes.push(capture.name);
      captured = true;
    }
    if (!captured && best.pattern.name !== undefined && matched.trim() === text) scopes.push(best.pattern.name);
    rest = rest.slice(best.index + matched.length);
  }
  return scopes;
}
