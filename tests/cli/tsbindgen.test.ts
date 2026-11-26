// T3: el CLI `pengu ts-bindgen` (salida, `--check`, informe y errores).

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { parse_args } from "../../src/cli/args.ts";
import { run_ts_bindgen } from "../../src/cli/tsbindgen_command.ts";
import { COMMANDS, command_help } from "../../src/cli/help.ts";

const SAMPLE = `interface Caja {
  width: number;
  etiqueta: string;
}
declare var document: Caja;
`;

function workspace(dts = SAMPLE): { dir: string; file: string } {
  const dir = mkdtempSync(join(tmpdir(), "pengu_tsb_cli_"));
  const file = join(dir, "lib.dom.d.ts");
  writeFileSync(file, dts);
  return { dir, file };
}

function run(...argv: string[]) {
  // `parse_args` recibe el `argv` completo tras el nombre del programa.
  const args = parse_args(["ts-bindgen", ...argv]);
  expect(args.command).toBe("ts-bindgen");
  return run_ts_bindgen(args);
}

describe("pengu ts-bindgen", () => {
  test("está en la ayuda y en la lista de comandos", () => {
    expect(COMMANDS).toContain("ts-bindgen");
    expect(command_help("ts-bindgen")).toContain("--check");
  });

  test("genera el .d.pengu junto al .d.ts por defecto", () => {
    const { dir, file } = workspace();
    const result = run(file, "--realm", "js_dom");
    expect(result.exit_code).toBe(0);
    const out = join(dir, "dom.d.pengu");
    expect(existsSync(out)).toBe(true);
    const text = readFileSync(out, "utf8");
    expect(text).toContain("realm js_dom");
    expect(text).toContain("host js::Caja");
    expect(text).toContain("mut width: int");
  });

  test("`--out` acepta un archivo y un directorio", () => {
    const { dir, file } = workspace();
    const target = join(dir, "salida.d.pengu");
    expect(run(file, "--out", target).exit_code).toBe(0);
    expect(existsSync(target)).toBe(true);

    const folder = join(dir, "catalogo");
    expect(run(file, "--out", folder).exit_code).toBe(0);
    expect(existsSync(join(folder, "dom.d.pengu"))).toBe(true);
  });

  test("`--check` acepta el archivo al día y rechaza el desactualizado", () => {
    const { dir, file } = workspace();
    const target = join(dir, "catalogo.d.pengu");
    expect(run(file, "--out", target).exit_code).toBe(0);
    expect(run(file, "--out", target, "--check").exit_code).toBe(0);

    writeFileSync(target, `${readFileSync(target, "utf8")}\n-- editado a mano\n`);
    const stale = run(file, "--out", target, "--check");
    expect(stale.exit_code).toBe(1);
    expect(stale.output).toContain("E0906");
  });

  test("`--check` sin archivo generado da E0905", () => {
    const { dir, file } = workspace();
    const result = run(file, "--out", join(dir, "nada.d.pengu"), "--check");
    expect(result.exit_code).toBe(1);
    expect(result.output).toContain("E0905");
  });

  test("`--report` y `--json` informan sin romper la salida", () => {
    const { dir, file } = workspace(`interface Rara { par: [string, number]; }\n`);
    const target = join(dir, "rara.d.pengu");
    const report = run(file, "--out", target, "--report");
    expect(report.exit_code).toBe(0);
    expect(report.output).toContain("Cobertura por módulo");

    const json = run(file, "--out", target, "--json");
    expect(json.exit_code).toBe(0);
    const parsed = JSON.parse(json.output) as { ok: boolean; types: number; skipped: string[] };
    expect(parsed.ok).toBe(true);
    expect(parsed.types).toBe(1);
    expect(parsed.skipped.join(" ")).toContain("tupla");
  });

  test("los errores de uso son claros", () => {
    expect(run().exit_code).toBe(2);
    const missing = run("/no/existe.d.ts");
    expect(missing.exit_code).toBe(1);
    expect(missing.output).toContain("E0005");

    const { file } = workspace();
    const not_dts = run(file.replace(".d.ts", ".txt"));
    expect(not_dts.exit_code).toBe(2);
    expect(not_dts.output).toContain(".d.ts");
  });

  test("`--only` cambia el dominio y el nombre del archivo", () => {
    const { dir, file } = workspace();
    expect(run(file, "--out", dir, "--only", "canvas").exit_code).toBe(0);
    expect(existsSync(join(dir, "canvas.d.pengu"))).toBe(true);
  });
});
