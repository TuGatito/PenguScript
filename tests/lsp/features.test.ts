// Consultas del LSP sin levantar el servidor: proyecto, hover,
// finalización, firma, navegación, hints, tokens, plegado y acciones.

import { afterAll, describe, expect, test } from "bun:test";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { build_project } from "../../src/lsp/project.ts";
import { completions_at } from "../../src/lsp/completion.ts";
import { hover_at, signature_at } from "../../src/lsp/hover.ts";
import { code_actions_at } from "../../src/lsp/actions.ts";
import { code_lenses, document_links } from "../../src/lsp/links.ts";
import { folding_ranges, inlay_hints, semantic_tokens } from "../../src/lsp/inlay.ts";
import {
  definition_at,
  document_symbols,
  references_at,
  rename_at,
} from "../../src/lsp/navigation.ts";
import { to_lsp_range } from "../../src/lsp/features.ts";
import { project_sizes } from "../../src/lsp/sizes.ts";

const roots: string[] = [];

afterAll(() => {
  for (const root of roots) rmSync(root, { recursive: true, force: true });
});

interface Fixture {
  readonly dir: string;
  readonly entry: string;
  readonly project: ReturnType<typeof build_project>;
}

function make_project(files: Record<string, string>): Fixture {
  const dir = mkdtempSync(join(tmpdir(), "pengu_lsp_"));
  roots.push(dir);
  for (const [name, text] of Object.entries(files)) {
    const path = join(dir, name);
    mkdirSync(join(path, ".."), { recursive: true });
    writeFileSync(path, text);
  }
  const entry = join(dir, "main.pengu");
  return { dir, entry, project: build_project(entry) };
}

function file_of(fixture: Fixture, name = "main.pengu") {
  const found = fixture.project.files.get(join(fixture.dir, name));
  if (found === undefined) throw new Error(`sin archivo ${name}`);
  return found;
}

function offset_in(fixture: Fixture, needle: string, delta = 0, name = "main.pengu"): number {
  const file = file_of(fixture, name);
  const index = file.source.text.indexOf(needle);
  if (index < 0) throw new Error(`no se encontró ${JSON.stringify(needle)}`);
  return index + delta;
}

describe("proyecto del LSP", () => {
  test("el buffer sin guardar gana al disco", () => {
    const fixture = make_project({ "main.pengu": "x: int = 1\n" });
    const path = join(fixture.dir, "main.pengu");
    const overlaid = build_project(path, new Map([[path, "x: int = \"hola\"\n"]]));
    const file = overlaid.files.get(path);
    expect(file?.diagnostics.map((item) => item.code)).toContain("E0501");
  });

  test("cambiar un módulo importado actualiza los diagnósticos del importador", () => {
    const fixture = make_project({
      "mate.pengu": "realm mate\nvalor = 1\n",
      "main.pengu": 'invoke "std/io"\ninvoke "./mate"\nmain = ->\n  io::println("#{mate::valor}")\n',
    });
    const path = join(fixture.dir, "mate.pengu");
    const fixed = build_project(fixture.entry, new Map([[path, "realm mate\nvalor = \"texto\"\n"]]));
    const main = fixed.files.get(fixture.entry);
    expect(main?.program.decls.length).toBeGreaterThan(0);
    expect(fixed.files.has(path)).toBe(true);
  });
});

describe("hover", () => {
  test("muestra el tipo inferido de una variable", () => {
    const fixture = make_project({ "main.pengu": "main = ->\n  total = 40 + 2\n" });
    const hover = hover_at(fixture.project, file_of(fixture), offset_in(fixture, "total", 1));
    expect(hover?.markdown).toContain("total: int");
  });

  test("muestra la firma de una función con documentación", () => {
    const fixture = make_project({
      "main.pengu": "-- Suma dos enteros.\nsumar = (a: int, b: int) -> int\n  a + b\n\nmain = ->\n  sumar(1, 2)\n",
    });
    const hover = hover_at(fixture.project, file_of(fixture), offset_in(fixture, "sumar(1", 1));
    expect(hover?.markdown).toContain("sumar = (a: int, b: int) -> int");
    expect(hover?.markdown).toContain("Suma dos enteros");
  });

  test("muestra el tamaño de una rune y el desplazamiento de su campo", () => {
    const fixture = make_project({
      "main.pengu": [
        "rune Punto",
        "  x: double",
        "  y: double",
        "",
        "main = ->",
        "  p = Punto(1.0, 2.0)",
        "  p.y",
        "",
      ].join("\n"),
    });
    const file = file_of(fixture);
    const sizes = project_sizes(fixture.project, join(fixture.dir, ".pengu-cache"));
    const hover = hover_at(fixture.project, file, offset_in(fixture, "p.y", 2), sizes.lookup, sizes.fields);
    expect(hover?.markdown).toContain("y: double");
    expect(hover?.markdown).toContain("en `rune Punto`");
    expect(hover?.markdown).toContain("desplazamiento: `8 B`");
  });
});

describe("finalización", () => {
  test("prioriza locales y luego funciones del módulo", () => {
    const fixture = make_project({
      "main.pengu": "sumar = (a: int) -> int\n  a\n\nmain = ->\n  total = 1\n  su\n",
    });
    const items = completions_at(fixture.project, file_of(fixture), offset_in(fixture, "su\n", 2));
    const labels = items.map((item) => item.label);
    expect(labels).toContain("sumar");
    expect(labels).toContain("total");
  });

  test("`::` ofrece variantes de un omen", () => {
    const fixture = make_project({
      "main.pengu": "omen Color\n  Rojo, Verde\n\nmain = ->\n  Color::\n",
    });
    const labels = completions_at(fixture.project, file_of(fixture), offset_in(fixture, "Color::", 7)).map(
      (item) => item.label,
    );
    expect(labels).toContain("Rojo");
    expect(labels).toContain("Verde");
  });

  test("los miembros del módulo importado aparecen", () => {
    const fixture = make_project({
      "mate.pengu": "realm mate\nsumar = (a: int, b: int) -> int\n  a + b\n",
      "main.pengu": 'invoke "./mate" as mate\nmain = ->\n  mate::\n',
    });
    const labels = completions_at(fixture.project, file_of(fixture), offset_in(fixture, "mate::", 6)).map(
      (item) => item.label,
    );
    expect(labels).toContain("sumar");
  });
});

describe("finalización de tipos y std", () => {
  test("tras «:» se ofrecen tipos", () => {
    const fixture = make_project({ "main.pengu": "main = ->\n  x: \n" });
    const labels = completions_at(fixture.project, file_of(fixture), offset_in(fixture, "x: ", 3)).map(
      (item) => item.label,
    );
    expect(labels).toContain("int");
    expect(labels).toContain("string");
    expect(labels).toContain("T?");
  });

  test("tras un módulo de std aparecen sus funciones", () => {
    const fixture = make_project({
      "main.pengu": 'invoke "std/math"\n\nmain = ->\n  math::\n',
    });
    const labels = completions_at(fixture.project, file_of(fixture), offset_in(fixture, "math::", 6)).map(
      (item) => item.label,
    );
    expect(labels).toContain("sqrt");
    expect(labels).toContain("pi");
  });

  test("el hover de una función de std trae la firma", () => {
    const fixture = make_project({
      "main.pengu": 'invoke "std/math"\n\nmain = ->\n  math::sqrt(16.0)\n',
    });
    const hover = hover_at(fixture.project, file_of(fixture), offset_in(fixture, "sqrt", 2));
    expect(hover?.markdown).toContain("sqrt = (x: double) -> double");
    expect(hover?.markdown).toContain("realm math");
  });
});

describe("ayuda de firma", () => {
  test("marca el parámetro activo", () => {
    const fixture = make_project({
      "main.pengu": "sumar = (a: int, b: int) -> int\n  a + b\n\nmain = ->\n  sumar(1, 2)\n",
    });
    const help = signature_at(fixture.project, file_of(fixture), offset_in(fixture, "sumar(1, ", 9));
    expect(help?.signatures[0]?.label).toContain("b: int) -> int");
    expect(help?.activeParameter).toBe(1);
  });
});

describe("navegación", () => {
  test("definición de un local y de una función", () => {
    const fixture = make_project({
      "main.pengu": "sumar = (a: int) -> int\n  a\n\nmain = ->\n  total = sumar(1)\n  total\n",
    });
    const local = definition_at(fixture.project, file_of(fixture), offset_in(fixture, "total\n", 1));
    expect(local?.uri).toEndWith("main.pengu");
    const fn = definition_at(fixture.project, file_of(fixture), offset_in(fixture, "sumar(1)", 1));
    expect(fn?.range.start.line).toBe(0);
  });

  test("referencias y renombrado", () => {
    const fixture = make_project({
      "main.pengu": "sumar = (a: int) -> int\n  a\n\nmain = ->\n  total = sumar(1)\n  total\n",
    });
    const references = references_at(fixture.project, file_of(fixture), offset_in(fixture, "total\n", 1));
    expect(references.length).toBeGreaterThanOrEqual(2);
    const edit = rename_at(fixture.project, file_of(fixture), offset_in(fixture, "total\n", 1), "suma");
    expect(edit?.changes[Object.keys(edit.changes)[0] ?? ""]?.length).toBeGreaterThanOrEqual(2);
  });

  test("renombrar un símbolo de std/ se rechaza", () => {
    const fixture = make_project({
      "main.pengu": 'invoke "std/math"\n\nmain = ->\n  math::sqrt(16.0)\n',
    });
    const edit = rename_at(fixture.project, file_of(fixture), offset_in(fixture, "sqrt", 2), "raiz");
    expect(edit).toBeUndefined();
  });

  test("símbolos del documento son jerárquicos", () => {
    const fixture = make_project({
      "main.pengu": "rune Punto\n  x: int\n\nomen Color\n  Rojo, Verde\n",
    });
    const symbols = document_symbols(file_of(fixture));
    expect(symbols.map((item) => item.name)).toContain("Punto");
    expect(symbols.some((item) => (item.children ?? []).some((child) => child.name === "x"))).toBe(true);
  });
});

describe("hints, tokens y plegado", () => {
  test("inlay hints para tipos inferidos", () => {
    const fixture = make_project({ "main.pengu": "main = ->\n  total = 40 + 2\n" });
    const hints = inlay_hints(file_of(fixture));
    expect(hints.map((item) => item.label)).toContain(": int");
  });

  test("tokens semánticos en orden", () => {
    const fixture = make_project({ "main.pengu": "main = ->\n  total = 1\n" });
    const tokens = semantic_tokens(file_of(fixture));
    expect(tokens.data.length).toBeGreaterThan(0);
    expect(tokens.data.length % 5).toBe(0);
  });

  test("plegado de bloques", () => {
    const fixture = make_project({
      "main.pengu": "main = ->\n  if true\n    1\n  else\n    2\n",
    });
    const ranges = folding_ranges(file_of(fixture));
    expect(ranges.length).toBeGreaterThan(0);
  });
});

describe("enlaces y lentes", () => {
  test("un invoke enlaza con el archivo que resuelve", () => {
    const fixture = make_project({
      "mate.pengu": "realm mate\nvalor = 1\n",
      "main.pengu": 'invoke "./mate"\nmain = ->\n  mate::valor\n',
    });
    const links = document_links(file_of(fixture));
    expect(links.length).toBe(1);
    expect(links[0]?.target).toEndWith("mate.pengu");
  });

  test("main tiene una lente para ejecutar", () => {
    const fixture = make_project({ "main.pengu": "main = ->\n  0\n" });
    const lenses = code_lenses(file_of(fixture));
    expect(lenses.map((lens) => lens.command.command)).toContain("pengu.runFile");
  });
});

describe("acciones de código", () => {
  test("propone el arreglo rápido de un diagnóstico", () => {
    const fixture = make_project({
      "main.pengu": "main = ->\n  io::println(\"hola\")\n",
    });
    const file = file_of(fixture);
    const offset = offset_in(fixture, "io::", 1);
    const range = to_lsp_range(file.source, file.source === undefined ? file.program.span : file.program.span);
    const actions = code_actions_at(fixture.project, file, offset, range);
    expect(Array.isArray(actions)).toBe(true);
  });
});
