// `pengu bindgen`: enlaces `.d.pengu` a partir de una cabecera C/C++.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { basename, resolve } from "node:path";
import type { ParsedArgs } from "./args.ts";
import { flag_bool, flag_string } from "./args.ts";
import { collect_base } from "../bindgen/base.ts";
import type { BaseTypes } from "../bindgen/base.ts";
import { collect_header, dump_ast, find_clang } from "../bindgen/clang_ast.ts";
import { render_bindings, sanitize_realm } from "../bindgen/emit.ts";
import { collect_macros } from "../bindgen/macros.ts";
import { CODES } from "../diagnostics/codes.ts";
import { link_flag } from "../driver/link.ts";

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
    ast = dump_ast(header, clang, args.include_dirs);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    return { exit_code: 1, output: `clang falló al analizar la cabecera:\n${detail}` };
  }

  const realm = sanitize_realm(flag_string(args, "realm") ?? basename(header));
  const parsed = collect_header(ast);
  const macros = collect_macros(header, clang, args.include_dirs, parsed.enums);
  const link = flag_string(args, "link");
  const libraries = link === undefined ? [] : [library_name(link)].filter((name) => name.length > 0);
  const base = base_types(args, clang);
  if (base instanceof Object && "error" in base) return base.error;
  const report = render_bindings(basename(header), realm, parsed, macros, libraries, base);

  const out = resolve(flag_string(args, "out") ?? header.replace(/\.[^./\\]+$/, ".d.pengu"));
  if (flag_bool(args, "check")) {
    if (!existsSync(out)) return { exit_code: 1, output: `no existe «${out}»: ejecuta pengu bindgen para generarlo` };
    const current = readFileSync(out, "utf8");
    if (current !== report.text) {
      return { exit_code: 1, output: `«${out}» está desactualizado: vuelve a ejecutar pengu bindgen` };
    }
    return { exit_code: 0, output: `«${out}» al día` };
  }

  writeFileSync(out, report.text, "utf8");

  const lines = [`Enlaces: ${report.functions} función(es) y ${report.constants} constante(s) en ${out}`];
  if (link !== undefined) lines.push(`enlaza el ejecutable con: ${link_flag(link)}`);
  if (report.skipped.length > 0) {
    lines.push("omitidas:");
    for (const item of report.skipped) lines.push(`  ${item}`);
  }
  return { exit_code: 0, output: lines.join("\n") };
}

// `--base cabecera.h` reutiliza los enlaces de otra cabecera: sus tipos se
// cualifican con `--base-realm` y no se vuelven a emitir.
function base_types(args: ParsedArgs, clang: string): BaseTypes | undefined | { readonly error: CommandResult } {
  const base_header = flag_string(args, "base");
  if (base_header === undefined) return undefined;
  const path = resolve(base_header);
  if (!existsSync(path)) {
    return { error: { exit_code: 1, output: `no existe la cabecera base «${base_header}»` } };
  }
  try {
    const base_ast = dump_ast(path, clang, args.include_dirs);
    const base_parsed = collect_header(base_ast);
    const base_macros = collect_macros(path, clang, args.include_dirs, base_parsed.enums);
    const base_realm = sanitize_realm(flag_string(args, "base-realm") ?? basename(path).replace(/\.[^./\\]+$/, ""));
    const module = flag_string(args, "base-module") ?? basename(path).replace(/\.[^./\\]+$/, "");
    return collect_base(base_parsed, base_macros, base_realm, module);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    return { error: { exit_code: 1, output: `clang falló al analizar la cabecera base:\n${detail}` } };
  }
}

// Nombre de biblioteca que se puede declarar con `link` en el archivo
// generado: `raylib` o `-lraylib` sí; rutas y objetos no.
function library_name(link: string): string {
  const name = link.startsWith("-l") ? link.slice(2) : link;
  if (name.startsWith("-") || name.includes("/") || name.includes("\\")) return "";
  if (/\.(o|a|so|dylib|dll|lib)$/.test(name)) return "";
  return name;
}
