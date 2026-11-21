// Regresiones de la fase G2: resolución de métodos enhechizados sobre
// tipos incorporados (sobrecargas, prioridad, `mut` y aridad del receptor).

import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse_text } from "../../src/frontend/parser.ts";
import { check_program } from "../../src/semantic/checker.ts";
import { make_sink } from "../../src/diagnostics/sink.ts";
import type { Diagnostic } from "../../src/diagnostics/diagnostic.ts";
import { CODES } from "../../src/diagnostics/codes.ts";
import { analyze_graph } from "../../src/driver/analyze.ts";
import { compile_file } from "../../src/driver/compile.ts";
import { spawnSync } from "node:child_process";

function parse_and_check(text: string): readonly Diagnostic[] {
  const parsed = parse_text("test.pengu", text);
  const sink = make_sink({ max: 100 });
  for (const diagnostic of parsed.diagnostics) sink.add(diagnostic);
  check_program("test.pengu", parsed.program, sink);
  return sink.diagnostics;
}

function codes(text: string): readonly string[] {
  return parse_and_check(text).map((item) => item.code);
}

// Proyecto de varios archivos: se usa para comprobar ambigüedad entre
// enhechizamientos importados.
function analyze_project(files: Readonly<Record<string, string>>): readonly Diagnostic[] {
  const dir = mkdtempSync(join(tmpdir(), "pengu_g2_"));
  for (const [name, text] of Object.entries(files)) writeFileSync(join(dir, name), text);
  const sink = make_sink({ max: 100 });
  analyze_graph(join(dir, "main.pengu"), sink);
  return sink.diagnostics;
}

const COMPARE = `
enchanting string
  compare = (otro: string) -> int
    if @ < otro
      -1
    else if @ > otro
      1
    else
      0
`;

function run_source(name: string, source: string): string {
  const dir = mkdtempSync(join(tmpdir(), `pengu_g2_${name}_`));
  const file = join(dir, "main.pengu");
  writeFileSync(file, source);
  const result = compile_file(file);
  if (!result.ok) {
    throw new Error(
      result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output,
    );
  }
  const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
  expect(run.status).toBe(0);
  return run.stdout;
}

describe("G2 enchanting de tipos incorporados", () => {
  test("string gana un método que la tabla nativa no tiene", () => {
    expect(codes(`${COMPARE}\nmain = ->\n  a = "manzana"\n  b = "banana"\n  x = a.compare(b)\n`)).toEqual([]);
  });

  test("el método enhechizado admite sobrecargas por aridad", () => {
    const text = `
enchanting string
  compare = (otro: string) -> int
    0

  compare = (otro: string, ignorar_mayusculas: bool) -> int
    1

main = ->
  a = "uno"
  b = "dos"
  x = a.compare(b)
  y = a.compare(b, true)
`;
    expect(codes(text)).toEqual([]);
  });

  test("un método enhechizado gana a la tabla nativa", () => {
    const text = `
enchanting string
  size = -> int
    @.substr(0, 0).substr(0, 0).size() + 100

main = ->
  a = "uno"
  x: int = a.size()
`;
    expect(codes(text)).toEqual([]);
  });

  test("el método enhechizado conserva el tipo del receptor genérico", () => {
    const text = `
enchanting vector<T>
  segundo = -> T
    @[1]

main = ->
  xs = vector<int>[1, 2, 3]
  x: int = xs.segundo()
`;
    expect(codes(text)).toEqual([]);
  });

  test("un método mut exige receptor mutable", () => {
    const text = `
enchanting vector<T>
  mut agregar = (valor: T) -> void
    @.push(valor)

main = ->
  xs = vector<int>[1]
  xs.agregar(2)
`;
    expect(codes(text)).toContain(CODES.mutable_required);
  });

  test("un método mut acepta un receptor mut", () => {
    const text = `
enchanting vector<T>
  mut agregar = (valor: T) -> void
    @.push(valor)

main = ->
  mut xs = vector<int>[1]
  xs.agregar(2)
`;
    expect(codes(text)).toEqual([]);
  });

  test("la aridad del receptor separa tuple de 2 y de 3", () => {
    const text = `
enchanting tuple<int, string>
  primera = -> int
    @.first

main = ->
  t = (1, "a", true)
  x = t.primera()
`;
    expect(codes(text)).toContain(CODES.unknown_field);
  });

  test("dos imports con la misma firma son ambiguos", () => {
    const diagnostics = analyze_project({
      "uno.pengu": `realm uno\n${COMPARE}`,
      "dos.pengu": `realm dos\n${COMPARE}`,
      "main.pengu": `realm main\ninvoke "./uno" as uno\ninvoke "./dos" as dos\n\nmain = ->\n  a = "x"\n  b = "y"\n  z = a.compare(b)\n`,
    });
    expect(diagnostics.map((item) => item.code)).toContain(CODES.ambiguous_method);
  });

  test("una llamada sin sobrecarga compatible lo dice con candidatos", () => {
    const text = `
enchanting string
  recortar = (veces: int) -> string
    @

main = ->
  a = "uno"
  x = a.recortar("dos")
`;
    const messages = parse_and_check(text).map((item) => item.message);
    expect(messages.some((message) => message.includes("ninguna sobrecarga de «recortar»"))).toBe(true);
  });

  test("acceder al método sin llamarlo respeta la sobrecarga", () => {
    const text = `
enchanting string
  compare = (otro: string) -> int
    0

main = ->
  a = "uno"
  f = a.compare
  x = f("dos")
`;
    expect(codes(text)).toEqual([]);
  });

  test("codegen: el método enhechizado se emite como función libre", () => {
    const output = run_source(
      "string",
      `invoke "std/io"
${COMPARE}
main = ->
  io::println("#{"manzana".compare("banana")}")
`,
    );
    expect(output.trim()).toBe("1");
  });

  test("codegen: contenedor genérico con receptor mutable", () => {
    const output = run_source(
      "vector",
      `invoke "std/io"

enchanting vector<T>
  segundo = -> T
    @[1]

  mut agregar = (valor: T) -> void
    @.push(valor)

main = ->
  mut xs = vector<int>[1, 2, 3]
  io::println("segundo: #{xs.segundo()}")
  xs.agregar(9)
  io::println("cuenta: #{#xs}")
`,
    );
    expect(output).toBe("segundo: 2\ncuenta: 4\n");
  });

  test("codegen: tuple concreto por aridad", () => {
    const output = run_source(
      "tuple",
      `invoke "std/io"

enchanting tuple<int, string>
  primera = -> int
    @.first

main = ->
  t: tuple<int, string> = (7, "siete")
  io::println("primera: #{t.primera()}")
`,
    );
    expect(output).toBe("primera: 7\n");
  });

  test("codegen: el método importado se cualifica con su realm", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_g2_import_"));
    writeFileSync(join(dir, "texto.pengu"), `realm texto\n${COMPARE}`);
    const main = join(dir, "main.pengu");
    writeFileSync(
      main,
      `realm main
invoke "std/io"
invoke "./texto" as texto

main = ->
  io::println("#{"uno".compare("dos")}")
`,
    );
    const result = compile_file(main);
    if (!result.ok) {
      throw new Error(result.diagnostics.map((item) => `${item.code}: ${item.message}`).join("\n") + "\n" + result.output);
    }
    const run = spawnSync(result.binary_path ?? "", [], { encoding: "utf8" });
    expect(run.status).toBe(0);
    expect(run.stdout.trim()).toBe("1");
  });
});
