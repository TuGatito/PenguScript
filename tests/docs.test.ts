// Los códigos documentados y los del compilador deben coincidir.

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { CODES } from "../src/diagnostics/codes.ts";

describe("docs/errors.md", () => {
  test("documenta todos los códigos del compilador", () => {
    const text = readFileSync(new URL("../docs/errors.md", import.meta.url), "utf8");
    const missing = Object.values(CODES).filter((code) => !text.includes(code));
    expect(missing).toEqual([]);
  });

  test("no documenta códigos que no existen", () => {
    const text = readFileSync(new URL("../docs/errors.md", import.meta.url), "utf8");
    const documented = [...text.matchAll(/E\d{4}/g)].map((match) => match[0]);
    const known = new Set<string>(Object.values(CODES));
    expect(documented.filter((code) => !known.has(code))).toEqual([]);
  });
});
