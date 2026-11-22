// Los snippets deben ser código PenguScript válido: se quitan los marcadores
// del editor y se parsea el resultado, solo o dentro de un envoltorio.

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse_text } from "../../src/frontend/parser.ts";

const extension_root = new URL("../../editors/vscode/", import.meta.url).pathname;
const snippets = JSON.parse(readFileSync(join(extension_root, "snippets/penguscript.code-snippets"), "utf8")) as Record<
  string,
  { prefix: string; body: string[]; description?: string }
>;

function strip(body: readonly string[]): string {
  return body
    .join("\n")
    .replace(/\$\{\d+:([^{}]*)\}/g, "$1")
    .replace(/\$\{\d+\}/g, "")
    .replace(/\$\d+/g, "")
    .replace(/\$TM_[A-Z_]+/g, "x");
}

function indent(source: string, spaces: number): string {
  const pad = " ".repeat(spaces);
  return source
    .split("\n")
    .map((line) => (line.length === 0 ? line : pad + line))
    .join("\n");
}

function parses(source: string): boolean {
  return parse_text("snippet.pengu", source).diagnostics.every((diagnostic) => diagnostic.severity !== "error");
}

function wraps(body: string): string[] {
  return [
    body,
    `main = ->\n${indent(body, 2)}\n`,
    `rune Ejemplo\n  campo: int\n\n  constructor()\n    pass\n\n${indent(body, 2)}\n`,
    `rune Ejemplo\n  campo: int\n\nenchanting Ejemplo\n${indent(body, 2)}\n`,
  ];
}

describe("snippets de PenguScript", () => {
  test("hay suficientes snippets y los prefijos no se repiten", () => {
    const entries = Object.values(snippets);
    expect(entries.length).toBeGreaterThanOrEqual(45);
    const prefixes = entries.map((entry) => entry.prefix);
    expect(new Set(prefixes).size).toBe(prefixes.length);
  });

  test("cada snippet tiene descripción y cuerpo", () => {
    for (const [name, entry] of Object.entries(snippets)) {
      expect({ name, described: typeof entry.description === "string" && entry.description.length > 0 }).toEqual({
        name,
        described: true,
      });
      expect({ name, body: entry.body.length > 0 }).toEqual({ name, body: true });
    }
  });

  test("todos los snippets parsean en algún contexto", () => {
    const failures: string[] = [];
    for (const [name, entry] of Object.entries(snippets)) {
      const body = strip(entry.body);
      if (!wraps(body).some(parses)) failures.push(name);
    }
    expect(failures).toEqual([]);
  });

  test("los snippets principales cubren el lenguaje", () => {
    const prefixes = new Set(Object.values(snippets).map((entry) => entry.prefix));
    for (const prefix of ["main", "invoke", "rune", "omen-algebraico", "flags", "declare", "match", "for-mapa", "unsafe"]) {
      expect({ prefix, present: prefixes.has(prefix) }).toEqual({ prefix, present: true });
    }
  });
});
