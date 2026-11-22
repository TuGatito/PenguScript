import { describe, expect, test } from "bun:test";
import { apply_changes, offset_of_position, touches } from "../../src/lsp/sync.ts";

describe("sincronización de documentos", () => {
  test("un cambio incremental reemplaza solo su rango", () => {
    const text = "main = ->\n  x = 1\n";
    const applied = apply_changes(text, [
      { range: { start: { line: 1, character: 6 }, end: { line: 1, character: 7 } }, text: "2" },
    ]);
    expect(applied.text).toBe("main = ->\n  x = 2\n");
    expect(applied.hot).toEqual({ start: 16, end: 17 });
  });

  test("varios cambios se aplican en orden", () => {
    const text = "abc";
    const applied = apply_changes(text, [
      { range: { start: { line: 0, character: 1 }, end: { line: 0, character: 1 } }, text: "X" },
      { range: { start: { line: 0, character: 4 }, end: { line: 0, character: 4 } }, text: "Y" },
    ]);
    expect(applied.text).toBe("aXbcY");
  });

  test("un cambio de documento completo no deja zona caliente", () => {
    const applied = apply_changes("viejo", [{ text: "nuevo documento" }]);
    expect(applied.text).toBe("nuevo documento");
    expect(applied.hot).toBeUndefined();
  });

  test("offset_of_position cuenta líneas y caracteres", () => {
    expect(offset_of_position("uno\ndos\n", { line: 1, character: 2 })).toBe(6);
    expect(offset_of_position("uno", { line: 9, character: 9 })).toBe(3);
  });

  test("touches incluye los bordes de la zona caliente", () => {
    const span = { start: { offset: 10 }, end: { offset: 14 } };
    expect(touches(span, { start: 15, end: 20 })).toBe(true);
    expect(touches(span, { start: 16, end: 20 })).toBe(false);
  });
});
