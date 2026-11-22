// Configuración del lenguaje: sangría, selección de palabras y reglas de Enter.

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const extension_root = new URL("../../editors/vscode/", import.meta.url).pathname;
const config = JSON.parse(readFileSync(join(extension_root, "language-configuration.json"), "utf8"));

function increases(line: string): boolean {
  return new RegExp(config.indentationRules.increaseIndentPattern).test(line);
}

function decreases(line: string): boolean {
  return new RegExp(config.indentationRules.decreaseIndentPattern).test(line);
}

describe("configuración del lenguaje", () => {
  test("los comentarios y los pares de cierre están definidos", () => {
    expect(config.comments.lineComment).toBe("--");
    const opens = config.autoClosingPairs.map((pair: { open: string }) => pair.open);
    for (const open of ["{", "[", "(", '"', "'"]) expect(opens).toContain(open);
  });

  test("wordPattern selecciona identificadores y números", () => {
    const pattern = new RegExp(`^(?:${config.wordPattern})$`);
    for (const word of ["campo", "xs", "_privado", "3.5", "42"]) {
      expect({ word, matched: pattern.test(word) }).toEqual({ word, matched: true });
    }
    expect(pattern.test("a.b")).toBe(false);
  });

  test("las líneas que abren bloque aumentan la sangría", () => {
    for (const line of ["main = ->", "  if x > 0", "  when 1 then", "rune Punto", "declare", "enchanting string", "  for i in 0..3", "  switch forma", "  match forma"]) {
      expect({ line, increases: increases(line) }).toEqual({ line, increases: true });
    }
  });

  test("las líneas que cierran bloque la reducen", () => {
    for (const line of ["  else", "  when 2", "  until listo"]) {
      expect({ line, decreases: decreases(line) }).toEqual({ line, decreases: true });
    }
    expect(decreases("  io::println(x)")).toBe(false);
  });

  test("las reglas de onEnter compilan", () => {
    for (const rule of config.onEnterRules) {
      expect(() => new RegExp(rule.beforeText)).not.toThrow();
      expect(["none", "indent", "indentOutdent", "outdent"]).toContain(rule.action.indent);
    }
  });
});
