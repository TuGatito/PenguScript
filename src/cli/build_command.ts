// Comando `pengu build`: compila un archivo a un binario nativo (backend
// C++) o a un conjunto de módulos ESM (backend JavaScript).

import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { compile_file } from "../driver/compile.ts";
import { render_diagnostics } from "../diagnostics/render.ts";
import { make_source } from "../util/span.ts";
import { readFileSync } from "node:fs";
import { flag_bool, flag_string, type ParsedArgs } from "./args.ts";
import { default_entry } from "./entry.ts";
import { parse_target } from "../driver/target.ts";
import { parse_int64_mode } from "../codegen/js_types.ts";

export interface CommandResult {
  readonly exit_code: number;
  readonly output: string;
}

// ¿La salida va a un `--out` explícito (no a la caché)?
function options_out(args: ParsedArgs): boolean {
  return flag_string(args, "out") !== undefined;
}

export function run_build(args: ParsedArgs): CommandResult {
  const file = default_entry(args.positionals);
  const out = flag_string(args, "out");
  const compiler = flag_string(args, "compiler");
  const link = flag_string(args, "link");
  const choice = parse_target(flag_string(args, "target"));
  if (!choice.ok) return { exit_code: 1, output: `error: ${choice.message}` };
  const int64 = parse_int64_mode(flag_string(args, "int64"));
  if (!int64.ok) return { exit_code: 1, output: `error: ${int64.message}` };

  const result = compile_file(file, {
    compiler,
    link: link === undefined ? [] : link.split(",").map((item) => item.trim()).filter((item) => item.length > 0),
    target: choice.target,
    out: out === undefined ? undefined : resolve(out),
    release: flag_bool(args, "release"),
    int64: int64.mode,
    jsdoc: flag_bool(args, "jsdoc"),
  });

  if (!result.ok) {
    return { exit_code: 1, output: explain_failure(result, file) };
  }

  if (choice.target === "js") {
    const dir = result.output_dir ?? "";
    const count = result.files?.length ?? 0;
    const generated = `✓ ${count} módulo(s) generados en ${dir}`;
    const cached = options_out(args) ? `✓ ${file} sin cambios en ${dir}` : `✓ ${file} sin cambios (caché)`;
    const message = result.reused === true ? cached : generated;
    const entry = result.js_entry_path;
    const base = entry === undefined ? message : `${message}\n  entrada: ${entry}`;
    const extra = emit_cpp_notice(args, file, result);
    return { exit_code: 0, output: extra === undefined ? base : `${base}\n${extra}` };
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
  const extra = emit_cpp_notice(args, file, result);
  return { exit_code: 0, output: extra === undefined ? message : `${message}\n${extra}` };
}

// `--emit-cpp`: copia el `.cpp` generado y la cabecera del runtime junto al
// fuente, para poder leerlos o depurarlos.
function emit_cpp_notice(
  args: ParsedArgs,
  file: string,
  result: ReturnType<typeof compile_file>,
): string | undefined {
  if (!flag_bool(args, "emit-cpp")) return undefined;
  // El backend JavaScript no genera C++: se avisa en vez de ignorarlo en
  // silencio.
  if (result.target === "js") {
    return "aviso: --emit-cpp solo aplica a --target cpp; se ignoró";
  }
  if (result.cpp_path === undefined || result.cache_dir === undefined) return undefined;
  const target_dir = dirname(resolve(file));
  const stem = basename(file).replace(/\.pengu$/, "");
  const cpp_out = join(target_dir, `${stem}.cpp`);
  const header_out = join(target_dir, "pengu_rt.hpp");
  try {
    mkdirSync(target_dir, { recursive: true });
    copyFileSync(result.cpp_path, cpp_out);
    copyFileSync(join(result.cache_dir, "pengu_rt.hpp"), header_out);
  } catch (error) {
    return `aviso: no se pudo conservar el C++ generado (${String(error)})`;
  }
  return `  C++ generado: ${cpp_out}`;
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
