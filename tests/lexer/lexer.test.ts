import { describe, expect, test } from "bun:test";
import { lex_text } from "../../src/frontend/lexer.ts";
import type { Token } from "../../src/frontend/token.ts";

function shape(tokens: readonly Token[]): string[] {
  return tokens.map((token) => {
    if (token.kind === "newline") return "nl";
    if (token.kind === "indent") return "INDENT";
    if (token.kind === "dedent") return "DEDENT";
    if (token.kind === "comment") return `comment:${token.text}`;
    if (token.kind === "eof") return "eof";
    return `${token.kind}:${token.text}`;
  });
}

describe("lexer", () => {
  test("declaraciones simples", () => {
    const result = lex_text("test.pengu", "x = 5\ny = 6\n");
    expect(result.diagnostics).toEqual([]);
    expect(shape(result.tokens)).toEqual([
      "ident:x",
      "=:=",
      "int:5",
      "nl",
      "ident:y",
      "=:=",
      "int:6",
      "nl",
      "eof",
    ]);
  });

  test("bloques con indentación", () => {
    const result = lex_text("test.pengu", "if x\n  y = 1\nz = 2\n");
    expect(shape(result.tokens)).toEqual([
      "if:if",
      "ident:x",
      "nl",
      "INDENT",
      "ident:y",
      "=:=",
      "int:1",
      "nl",
      "DEDENT",
      "ident:z",
      "=:=",
      "int:2",
      "nl",
      "eof",
    ]);
  });

  test("los corchetes suprimen saltos de línea", () => {
    const result = lex_text("test.pengu", "a = [\n  1,\n  2,\n]\nb = 3\n");
    expect(shape(result.tokens)).toEqual([
      "ident:a",
      "=:=",
      "[:[",
      "int:1",
      ",:,",
      "int:2",
      ",:,",
      "]:]",
      "nl",
      "ident:b",
      "=:=",
      "int:3",
      "nl",
      "eof",
    ]);
  });

  test("comentarios en línea y al inicio", () => {
    const result = lex_text("test.pengu", "-- arriba\nx = 1 -- final\n");
    expect(shape(result.tokens)).toEqual([
      "comment:-- arriba",
      "ident:x",
      "=:=",
      "int:1",
      "comment:-- final",
      "nl",
      "eof",
    ]);
  });

  test("interpolación de cadenas", () => {
    const result = lex_text("test.pengu", 's = "a#{b}c"\n');
    const string = result.tokens.find((token) => token.kind === "string");
    expect(string).toBeDefined();
    expect(string?.parts?.length).toBe(3);
    expect(string?.parts?.[0]).toEqual({ kind: "text", text: "a" });
    const expr = string?.parts?.[1];
    expect(expr?.kind).toBe("expr");
    if (expr?.kind === "expr") {
      expect(expr.tokens.map((token) => token.kind)).toEqual(["ident"]);
    }
    expect(string?.parts?.[2]).toEqual({ kind: "text", text: "c" });
  });

  test("cadenas multilínea", () => {
    const result = lex_text("test.pengu", 's = "linea\n  dos"\n');
    const string = result.tokens.find((token) => token.kind === "string");
    expect(string?.value).toBe("linea\n  dos");
  });

  test("números enteros, hexadecimales, binarios y flotantes", () => {
    const result = lex_text("test.pengu", "0xFF 0b1010 42 1.5e-3 7\n");
    expect(shape(result.tokens)).toEqual([
      "int:0xFF",
      "int:0b1010",
      "int:42",
      "float:1.5e-3",
      "int:7",
      "nl",
      "eof",
    ]);
  });

  test("caracteres y escapes", () => {
    const result = lex_text("test.pengu", "'a' '\\n' '\\\\'\n");
    const chars = result.tokens.filter((token) => token.kind === "char");
    expect(chars.map((token) => token.value)).toEqual(["a", "\n", "\\"]);
    expect(result.diagnostics).toEqual([]);
  });

  test("error de indentación inconsistente", () => {
    const result = lex_text("test.pengu", "if x\n    y = 1\n  z = 2\n");
    expect(result.diagnostics.map((diagnostic) => diagnostic.code)).toContain("E0101");
  });

  test("error de cadena sin cerrar", () => {
    const result = lex_text("test.pengu", 's = "sin cerrar\n');
    expect(result.diagnostics.map((diagnostic) => diagnostic.code)).toContain("E0104");
  });
});
