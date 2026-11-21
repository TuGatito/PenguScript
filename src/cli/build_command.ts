// Comando `pengu build`: compila un archivo a un ejecutable nativo.

import { copyFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { compile_file } from "../driver/compile.ts";
import { render_diagnostics } from "../diagnostics/render.ts";
import { make_source } from "../util/span.ts";
import { readFileSync } from "node:fs";
import { flag_string, type ParsedArgs } from "./args.ts";

export interface CommandResult {
  readonly exit_code: number;
  readonly output: string;
}

export function run_build(args: ParsedArgs): CommandResult {
  const file = args.positionals[0] ?? "main.pengu";
  const out = flag_string(args, "out");
  const compiler = flag_string(args, "compiler");
  const link = flag_string(args, "link");
  const result = compile_file(file, {
    compiler,
    link: link === undefined ? [] : link.split(",").map((item) => item.trim()).filter((item) => item.length > 0),
  });

  if (!result.ok) {
    return { exit_code: 1, output: explain_failure(result, file) };
  }

  let message = result.reused === true ? `✓ ${file} sin cambios (caché)` : `✓ ${file} compilado`;
  if (result.binary_path !== undefined) {
    if (out !== undefined) {
      copyFileSync(result.binary_path, out);
      message = result.reused === true ? `✓ ${file} sin cambios (caché)` : `✓ ${file} compilado en ${out}`;
    } else {
      message =
        result.reused === true
          ? `✓ ${file} sin cambios (caché)`
          : `✓ ${file} compilado en ${result.binary_path}`;
    }
  }
  return { exit_code: 0, output: message };
}

export function explain_failure(
  result: ReturnType<typeof compile_file>,
  file: string,
): string {
  const source_path = resolve(result.source_path ?? file);
  const sources = new Map<string, ReturnType<typeof make_source>>();
  if (existsSync(source_path)) {
    sources.set(source_path, make_source(source_path, readFileSync(source_path, "utf8")));
  }
  const rendered = render_diagnostics(result.diagnostics, sources, { color: process.stderr.isTTY === true });
  if (result.output.length > 0 && rendered.length === 0) return result.output;
  return rendered.length > 0 ? rendered : result.output;
}
