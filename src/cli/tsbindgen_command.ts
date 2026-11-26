// `pengu ts-bindgen`: enlaces `.d.pengu` a partir de declaraciones `.d.ts`.
//
// Es el hermano de `pengu bindgen` (C): mismo contrato de informe honesto de
// lo omitido y mismo `--check` para la suite, pero la fuente de verdad son los
// tipos del navegador en vez de una cabecera C.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import type { ParsedArgs } from "./args.ts";
import { flag_bool, flag_string } from "./args.ts";
import { CODES } from "../diagnostics/codes.ts";
import { bind_dts_file, domain_of } from "../tsbindgen/collect.ts";
import { DOMAINS, is_domain } from "../tsbindgen/domain.ts";
import { format_report, render_report_json } from "../tsbindgen/report.ts";

export interface CommandResult {
  readonly exit_code: number;
  readonly output: string;
}

const USAGE =
  "uso: pengu ts-bindgen <archivo.d.ts> [--realm nombre] [--out ruta] [--only dominio] [--check] [--report] [--json]";

// Módulos que necesita cualquier `.d.pengu` generado.
const DEFAULT_INVOKES = ["std/js/types"] as const;

export function run_ts_bindgen(args: ParsedArgs): CommandResult {
  const source_arg = args.positionals[0];
  if (source_arg === undefined) return { exit_code: 2, output: USAGE };

  // La extensión se comprueba antes que la existencia: así un `pengu
  // ts-bindgen algo.txt` explica el uso y no un «no existe».
  if (!source_arg.endsWith(".d.ts")) {
    return { exit_code: 2, output: `«${source_arg}» no es un archivo .d.ts\n${USAGE}` };
  }
  const source = resolve(source_arg);
  if (!existsSync(source)) {
    return { exit_code: 1, output: `no existe «${source_arg}» (${CODES.file_not_found})` };
  }

  const only = flag_string(args, "only");
  if (only !== undefined && !is_domain(only)) {
    return {
      exit_code: 2,
      output: `--only «${only}» no es un dominio conocido; los disponibles son ${Object.keys(DOMAINS).join(", ")} (${CODES.ts_bindgen_failed})`,
    };
  }
  const domain = only ?? domain_of(source);
  const realm = sanitize_realm(flag_string(args, "realm") ?? `js_${domain}`);
  let result;
  try {
    result = bind_dts_file(source, {
      realm,
      source: basename(source),
      invokes: DEFAULT_INVOKES,
      only,
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    return { exit_code: 1, output: `no se pudo leer «${source_arg}»:\n${detail} (${CODES.ts_bindgen_failed})` };
  }

  const out = resolve_output(args, source, domain);
  if (flag_bool(args, "check")) {
    return check_output(out, result.text);
  }

  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, result.text, "utf8");
  return { exit_code: 0, output: summary_output(out, result, args) };
}

function resolve_output(args: ParsedArgs, source: string, domain: string): string {
  const out = flag_string(args, "out");
  if (out === undefined) {
    // Por defecto, junto al `.d.ts`: `lib.dom.d.ts` → `dom.d.pengu`.
    return resolve(source.slice(0, source.lastIndexOf("/") + 1), `${domain}.d.pengu`);
  }
  const path = resolve(out);
  // `--out` es un archivo cuando nombra un `.d.pengu` (o cualquier nombre con
  // extensión) y un directorio cuando no.
  if (/\.(d\.pengu|pengu|expected|txt)$/.test(path)) return path;
  return join(path, `${domain}.d.pengu`);
}

function check_output(out: string, text: string): CommandResult {
  if (!existsSync(out)) {
    return {
      exit_code: 1,
      output: `no existe «${out}»: ejecuta pengu ts-bindgen para generarlo (${CODES.ts_bindgen_missing})`,
    };
  }
  const current = readFileSync(out, "utf8");
  if (current !== text) {
    return {
      exit_code: 1,
      output: `«${out}» está desactualizado: vuelve a ejecutar pengu ts-bindgen (${CODES.ts_bindgen_stale})`,
    };
  }
  return { exit_code: 0, output: `«${out}» al día` };
}

function summary_output(
  out: string,
  result: { readonly module: { readonly skipped: readonly { name: string; reason: string }[] }; readonly summary: string; readonly report: Parameters<typeof format_report>[0] },
  args: ParsedArgs,
): string {
  if (flag_bool(args, "json")) return render_report_json(result.report);
  if (flag_bool(args, "report")) return `${format_report(result.report)}\n→ ${out}`;

  const lines = [`Enlaces: ${result.summary} en ${out}`];
  if (result.module.skipped.length > 0) {
    lines.push("omitidas:");
    for (const item of result.module.skipped.slice(0, 20)) lines.push(`  ${item.name}: ${item.reason}`);
    if (result.module.skipped.length > 20) {
      lines.push(`  … y ${result.module.skipped.length - 20} más (--report para verlas todas)`);
    }
  }
  return lines.join("\n");
}

// `js_dom` a partir de un nombre libre: mismo criterio que el bindgen de C.
export function sanitize_realm(name: string): string {
  const cleaned = name.replace(/[^A-Za-z0-9_]/g, "_");
  return /^[0-9]/.test(cleaned) ? `_${cleaned}` : cleaned === "" ? "js_binding" : cleaned;
}
