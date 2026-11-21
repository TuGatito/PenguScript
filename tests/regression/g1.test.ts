// G1: sintaxis y registro de `enchanting` sobre tipos incorporados.
//
// En esta fase el checker todavía no consulta los enhechizamientos; lo que
// se comprueba es que se registran bien, con su aridad, sus sigilos y sus
// errores (E0707, E0709, E0710, E0711).

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { load_graph } from "../../src/project/module_graph.ts";
import { format_text } from "../../src/formatter/format_tokens.ts";
import type { LoadedModule, ModuleGraph } from "../../src/project/module_graph.ts";

interface Loaded {
  readonly graph: ModuleGraph;
  readonly entry: LoadedModule;
  readonly codes: readonly string[];
}

function load(files: Readonly<Record<string, string>>, entry = "main.pengu"): Loaded {
  const dir = mkdtempSync(join(tmpdir(), "pengu_g1_"));
  try {
    for (const [name, text] of Object.entries(files)) {
      const path = join(dir, name);
      mkdirSync(join(path, ".."), { recursive: true });
      writeFileSync(path, text);
    }
    const graph = load_graph(join(dir, entry));
    return {
      graph,
      entry: graph.entry ?? graph.order[0]!,
      codes: graph.diagnostics.map((diagnostic) => diagnostic.code),
    };
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

describe("G1 registro de enchanting", () => {
  test("registra un tipo primitivo con aridad cero", () => {
    const { entry } = load({
      "main.pengu": [
        "realm main",
        "",
        "enchanting string",
        "  compare = (otro: string) -> int",
        "    0",
      ].join("\n"),
    });
    const enchanted = entry.info.env.enchants.get("string/0");
    expect(enchanted).toBeDefined();
    expect(enchanted!.methods.get("compare")![0]!.info.params.length).toBe(1);
    expect(enchanted!.methods.get("compare")![0]!.realm).toBe("main");
  });

  test("registra un contenedor genérico y liga sus sigilos", () => {
    const { entry } = load({
      "main.pengu": [
        "enchanting vector<T>",
        "  take_first = -> T",
        "    @[0]",
      ].join("\n"),
    });
    const enchanted = entry.info.env.enchants.get("vector/1");
    expect(enchanted!.sigils).toEqual(["T"]);
    expect(enchanted!.methods.get("take_first")![0]!.info.result.kind).toBe("named");
  });

  test("tuple convive por aridad", () => {
    const { entry } = load({
      "main.pengu": [
        "enchanting tuple<A, B>",
        "  first_pair = -> A",
        "    @[0]",
        "",
        "enchanting tuple<A, B, C>",
        "  first_triple = -> A",
        "    @[0]",
      ].join("\n"),
    });
    expect(entry.info.env.enchants.has("tuple/2")).toBe(true);
    expect(entry.info.env.enchants.has("tuple/3")).toBe(true);
  });

  test("E0711 si la aridad del patrón no encaja", () => {
    const { codes } = load({
      "main.pengu": ["enchanting vector<T, U>", "  metodo = -> int", "    0"].join("\n"),
    });
    expect(codes).toContain("E0711");
  });

  test("E0709 con sugerencia para un destino desconocido", () => {
    const { graph } = load({
      "main.pengu": ["enchanting strin", "  metodo = -> int", "    0"].join("\n"),
    });
    const message = graph.diagnostics.map((diagnostic) => diagnostic.message).join("\n");
    expect(graph.diagnostics[0]!.code).toBe("E0709");
    expect(message).toContain("string");
  });

  test("E0710 para mut sobre un tipo por valor", () => {
    const { codes } = load({
      "main.pengu": ["enchanting int", "  mut doblar = -> void", "    pass"].join("\n"),
    });
    expect(codes).toContain("E0710");
  });

  test("E0707 para la misma firma dos veces", () => {
    const { codes } = load({
      "main.pengu": [
        "enchanting string",
        "  compare = (otro: string) -> int",
        "    0",
        "  compare = (otro: string) -> int",
        "    1",
      ].join("\n"),
    });
    expect(codes).toContain("E0707");
  });

  test("el formateador es idempotente con el patrón de tipo", () => {
    const source = ["enchanting map<K, V>", "  clave_max = -> K", "    @.first", ""].join("\n");
    const once = format_text("main.pengu", source);
    expect(format_text("main.pengu", once)).toBe(once);
    expect(once).toContain("enchanting map<K, V>");
  });

  test("un realm reabierto comparte los enhechizamientos", () => {
    const { graph } = load({
      "main.pengu": ['realm texto', "", 'invoke "./extra"', "", "main = -> void", "  pass"].join("\n"),
      "extra.pengu": [
        'realm texto',
        "",
        "enchanting string",
        "  largo = -> size_t",
        "    0",
      ].join("\n"),
    });
    const module = graph.order.find((loaded) => loaded.file.endsWith("main.pengu"))!;
    expect(module.info.env.enchants.get("string/0")?.methods.has("largo")).toBe(true);
  });
});
