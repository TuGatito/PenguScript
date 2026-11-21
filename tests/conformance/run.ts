// Runner de conformidad: cada carpeta de `tests/conformance` tiene un
// `esperado.json` que describe qué debe pasar con el `.pengu` hermano.
//
// Formato:
//   { "check": "ok" }                      → sin diagnósticos
//   { "check": ["E0501", "E0406"] }        → esos códigos, en cualquier orden
//   { "run": ["línea 1", "línea 2"] }      → compila, ejecuta y compara stdout

import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";
import { analyze_graph } from "../../src/driver/analyze.ts";
import { compile_file } from "../../src/driver/compile.ts";
import { make_sink } from "../../src/diagnostics/sink.ts";

export interface Expected {
  readonly check?: "ok" | readonly string[];
  readonly run?: readonly string[];
}

export interface Case {
  readonly name: string;
  readonly file: string;
  readonly expected: Expected;
}

export function find_cases(root: string): readonly Case[] {
  const cases: Case[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir)) {
      const path = join(dir, entry);
      if (statSync(path).isDirectory()) {
        walk(path);
        continue;
      }
      if (entry !== "esperado.json") continue;
      const expected = JSON.parse(readFileSync(path, "utf8")) as Expected;
      const source = path.replace(/esperado\.json$/, "main.pengu");
      cases.push({ name: path.slice(root.length + 1).replace(/[\\/]/g, "/"), file: source, expected });
    }
  };
  walk(root);
  return cases;
}

export function run_case(item: Case): void {
  const sink = make_sink({ max: 100 });
  analyze_graph(item.file, sink);

  if (item.expected.check !== undefined) {
    const codes = sink.diagnostics.map((diagnostic) => diagnostic.code);
    if (item.expected.check === "ok") {
      if (codes.length > 0) {
        throw new Error(`${item.name}: se esperaba compilar, diagnósticos: ${codes.join(", ")}`);
      }
      return;
    }
    const missing = item.expected.check.filter((code) => !codes.includes(code));
    if (missing.length > 0) {
      throw new Error(`${item.name}: faltan diagnósticos ${missing.join(", ")} (recibidos: ${codes.join(", ") || "ninguno"})`);
    }
    return;
  }

  if (item.expected.run !== undefined) {
    // Un caso puede vivir junto a `esperado.json` o dentro de una carpeta.
    const result = compile_file(item.file);
    if (!result.ok) {
      const codes = result.diagnostics.map((diagnostic) => `${diagnostic.code} ${diagnostic.message}`);
      throw new Error(`${item.name}: no compiló\n${codes.join("\n")}\n${result.output}`);
    }
    const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
    if (run.status !== 0) throw new Error(`${item.name}: salida ${run.status}`);
    const expected = `${item.expected.run.join("\n")}\n`;
    if (run.stdout !== expected) {
      throw new Error(`${item.name}: salida inesperada\n--- esperado ---\n${expected}--- recibido ---\n${run.stdout}`);
    }
    return;
  }

  throw new Error(`${item.name}: esperado.json vacío`);
}

export function conformance_root(): string {
  return dirname(new URL(import.meta.url).pathname);
}
