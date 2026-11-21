// Los archivos `std/*.d.pengu` son la fuente de verdad de las firmas:
// cada función declarada debe tener una implementación en el runtime.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { load_graph } from "../../src/project/module_graph.ts";
import { collect_module } from "../../src/semantic/module_info.ts";
import { parse_text } from "../../src/frontend/parser.ts";
import { make_sink } from "../../src/diagnostics/sink.ts";
import { symbol_type_of } from "../../src/semantic/external.ts";
import { BUILTIN_FUNCTIONS } from "../../src/codegen/cpp_expr.ts";

const STD_DIR = join(import.meta.dir, "..", "..", "std");

function std_files(): string[] {
  return readdirSync(STD_DIR)
    .filter((name) => name.endsWith(".d.pengu"))
    .map((name) => join(STD_DIR, name));
}

describe("biblioteca estándar", () => {
  test("cada declaración tiene implementación en el runtime", () => {
    const missing: string[] = [];
    for (const file of std_files()) {
      const parsed = parse_text(file, readFileSync(file, "utf8"));
      expect(parsed.diagnostics).toEqual([]);
      const info = collect_module(file, parsed.program, make_sink({}));
      for (const name of info.functions.keys()) {
        const key = `${info.realm}::${name}`;
        if (BUILTIN_FUNCTIONS[key] === undefined) missing.push(key);
      }
    }
    expect(missing).toEqual([]);
  });

  test("el cargador resuelve `std/...` al directorio incluido", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_std_"));
    const main = join(dir, "main.pengu");
    writeFileSync(main, 'invoke "std/io"\ninvoke "std/fs"\ninvoke {sqrt} from "std/math"\n\nmain = ->\n  io::println("ok")\n');
    const graph = load_graph(main);
    expect(graph.diagnostics).toEqual([]);
    const files = graph.order.map((module) => module.file);
    expect(files.some((file) => file.endsWith("std/fs.d.pengu"))).toBe(true);
    expect(files.some((file) => file.endsWith("std/math.d.pengu"))).toBe(true);
    const entry = graph.entry;
    const sqrt = entry?.selective.get("sqrt");
    expect(sqrt?.name).toBe("sqrt");
    const type = symbol_type_of(sqrt!.module.info, "sqrt");
    expect(type === undefined).toBe(false);
  });
});
