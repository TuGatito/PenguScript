import { describe, expect, test } from "bun:test";
import { format_text } from "../../src/formatter/format_tokens.ts";

function formatted(text: string): string {
  return format_text("prueba.pengu", text);
}

describe("formateador", () => {
  test("normaliza espacios alrededor de operadores", () => {
    const text = "main = ->\n  const x=1+2*3\n  io::println(\"#{x}\")\n";
    expect(formatted(text)).toBe("main = ->\n  const x = 1 + 2 * 3\n  io::println(\"#{x}\")\n");
  });

  test("conserva comentarios y líneas en blanco", () => {
    const text = "-- uno\n-- dos\n\nmain=->\n  pass\n";
    expect(formatted(text)).toBe("-- uno\n-- dos\n\nmain = ->\n  pass\n");
  });

  test("no separa los genéricos ni las llamadas", () => {
    const text = "f = <T>(x: T) -> vector<T>\n  [x]\n";
    expect(formatted(text)).toBe("f = <T>(x: T) -> vector<T>\n  [x]\n");
  });

  test("es idempotente", () => {
    const text = "rune P\n  x: double\n\n  constructor(x: double)\n    @x=x\n";
    const once = formatted(text);
    expect(formatted(once)).toBe(once);
  });

  test("mantiene la indentación de bloques anidados", () => {
    const text = "main = ->\n  while true\n    break\n";
    expect(formatted(text)).toBe("main = ->\n  while true\n    break\n");
  });

  test("un prefijo no se pega al operador binario que le sigue", () => {
    const source = "enchanting string\n  compare = (otro: string) -> int\n    if @< otro then -1 else 1\n";
    const once = format_text("test.pengu", source);
    expect(once).toContain("if @ < otro then -1 else 1");
    expect(format_text("test.pengu", once)).toBe(once);
  });
});
