// `pengu bindgen`: enlaces `.d.pengu` a partir de una cabecera C/C++.

import { existsSync, writeFileSync } from "node:fs";
import { basename, resolve } from "node:path";
import type { ParsedArgs } from "./args.ts";
import { flag_string } from "./args.ts";
import { collect_functions, dump_ast, find_clang } from "../bindgen/clang_ast.ts";
import { render_bindings, sanitize_realm } from "../bindgen/emit.ts";
import { CODES } from "../diagnostics/codes.ts";

export interface CommandResult {
  readonly exit_code: number;
  readonly output: string;
}

export function run_bindgen(args: ParsedArgs): CommandResult {
  const header_arg = args.positionals[0];
  if (header_arg === undefined) {
    return { exit_code: 2, output: "uso: pengu bindgen <cabecera.h> [--realm nombre] [--out archivo.d.pengu]" };
  }

  const header = resolve(header_arg);
  if (!existsSync(header)) {
    return { exit_code: 1, output: `no existe la cabecera «${header_arg}» (${CODES.file_not_found})` };
  }

  const clang = flag_string(args, "clang") ?? find_clang();
  if (clang === undefined) {
    return { exit_code: 1, output: "no se encontró clang; instala clang y vuelve a intentarlo" };
  }

  let ast: unknown;
  try {
    ast = dump_ast(header, clang);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    return { exit_code: 1, output: `clang falló al analizar la cabecera:\n${detail}` };
  }

  const realm = sanitize_realm(flag_string(args, "realm") ?? basename(header));
  const report = render_bindings(basename(header), realm, collect_functions(ast));

  const out = resolve(flag_string(args, "out") ?? header.replace(/\.[^./\\]+$/, ".d.pengu"));
  writeFileSync(out, report.text, "utf8");

  const lines = [`Enlaces: ${report.functions} función(es) en ${out}`];
  const link = flag_string(args, "link");
  if (link !== undefined) lines.push(`enlaza el ejecutable con: -l${link}`);
  if (report.skipped.length > 0) {
    lines.push("omitidas:");
    for (const item of report.skipped) lines.push(`  ${item}`);
  }
  return { exit_code: 0, output: lines.join("\n") };
}
