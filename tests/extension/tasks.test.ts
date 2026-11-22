// El problem matcher debe reconocer el formato real de los diagnósticos del
// compilador, para que las tareas marquen archivo, línea y código.

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { make_diagnostic } from "../../src/diagnostics/diagnostic.ts";
import { render_diagnostic } from "../../src/diagnostics/render.ts";
import { make_source } from "../../src/util/span.ts";

const extension_root = new URL("../../editors/vscode/", import.meta.url).pathname;
const package_json = JSON.parse(readFileSync(join(extension_root, "package.json"), "utf8"));
const matcher = package_json.contributes.problemMatchers.find((entry: { name: string }) => entry.name === "pengu");

function rendered(): string {
  const source = make_source("/tmp/proyecto/main.pengu", 'main = ->\n  x: int = "texto"\n');
  const diagnostic = make_diagnostic({
    code: "E0501",
    severity: "error",
    message: "espera «int», recibí «string»",
    span: {
      file: source.file,
      start: { line: 2, column: 3, offset: 14 },
      end: { line: 2, column: 9, offset: 20 },
    },
  });
  return render_diagnostic(diagnostic, source, { color: false });
}

describe("problem matcher de PenguScript", () => {
  test("el formato del compilador se reconoce", () => {
    const line = rendered().split("\n")[0] ?? "";
    const pattern = new RegExp(matcher.pattern.regexp);
    const match = pattern.exec(line);
    expect(match).not.toBeNull();
    const groups = match as RegExpExecArray;
    expect(groups[1]).toBe("/tmp/proyecto/main.pengu");
    expect(groups[2]).toBe("2");
    expect(groups[3]).toBe("3");
    expect(groups[4]).toBe("error");
    expect(groups[5]).toBe("E0501");
    expect(groups[6]).toContain("espera «int»");
  });

  test("también reconoce avisos", () => {
    const pattern = new RegExp(matcher.pattern.regexp);
    const match = pattern.exec("/tmp/x.pengu:7:1: warning[E0701]: el switch no cubre todos los casos");
    expect(match).not.toBeNull();
    expect((match as RegExpExecArray)[4]).toBe("warning");
  });

  test("las tareas declaran el tipo y el matcher correctos", () => {
    const definition = package_json.contributes.taskDefinitions[0];
    expect(definition.type).toBe("pengu");
    expect(definition.required).toEqual(["command"]);
    expect(matcher.owner).toBe("pengu");
    expect(matcher.source).toBe("pengu");
  });
});
