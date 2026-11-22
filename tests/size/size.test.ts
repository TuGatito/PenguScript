// Medición de tamaños: `pengu size` compila un sondeo y reporta lo real.

import { afterAll, describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { run_size } from "../../src/cli/size_command.ts";

const roots: string[] = [];

afterAll(() => {
  for (const root of roots) rmSync(root, { recursive: true, force: true });
});

function make_project(text: string): string {
  const dir = mkdtempSync(join(tmpdir(), "pengu_size_"));
  roots.push(dir);
  const file = join(dir, "main.pengu");
  writeFileSync(file, text);
  return file;
}

interface SizeRow {
  readonly name: string;
  readonly size: number;
  readonly align: number;
  readonly fields: readonly { readonly name: string; readonly offset: number; readonly size: number }[];
}

function rows(output: string): SizeRow[] {
  return (JSON.parse(output) as { types: SizeRow[] }).types;
}

describe("pengu size", () => {
  test("mide una rune con sus campos y un sello", () => {
    const file = make_project(
      [
        "rune Punto",
        "  x: double",
        "  y: double",
        "",
        "seal Id = uint8_t",
        "",
        "main = ->",
        "  p = Punto(1.0, 2.0)",
        "",
      ].join("\n"),
    );
    const result = run_size([file], { json: true });
    expect(result.exit_code).toBe(0);
    const table = rows(result.output);
    const punto = table.find((row) => row.name.endsWith("::Punto"));
    expect(punto?.size).toBe(16);
    expect(punto?.align).toBe(8);
    expect(punto?.fields.find((item) => item.name === "y")?.offset).toBe(8);
    const seal = table.find((row) => row.name.endsWith("::Id"));
    expect(seal?.size).toBe(1);
  });

  test("mide primitivos del lenguaje", () => {
    const file = make_project("main = ->\n  0\n");
    const result = run_size([file], { json: true });
    const table = rows(result.output);
    expect(table.find((row) => row.name === "int")?.size).toBe(4);
    expect(table.find((row) => row.name === "double")?.size).toBe(8);
    expect(table.find((row) => row.name === "bool")?.size).toBe(1);
  });

  test("la tabla legible tiene cabecera y filas", () => {
    const file = make_project("main = ->\n  0\n");
    const result = run_size([file], {});
    expect(result.exit_code).toBe(0);
    const lines = result.output.trim().split("\n");
    expect(lines[0]).toContain("Tipos");
    expect(lines[1]).toContain("Bytes");
    expect(lines.length).toBeGreaterThan(3);
  });
});
