// Comando `pengu check`.
//
// Compila en memoria hasta el checker y presenta los diagnósticos.
// Es la primera fase completa del pipeline: lexer → parser → checker.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { default_entry } from "./entry.ts";
import { CODES } from "../diagnostics/codes.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import { make_source as source_of, span_from } from "../util/span.ts";
import { analyze_graph } from "../driver/analyze.ts";
import { generate_js_program } from "../codegen/js_module.ts";
import { parse_target } from "../driver/target.ts";
import { make_sink } from "../diagnostics/sink.ts";
import { render_diagnostics } from "../diagnostics/render.ts";
import { make_source } from "../util/span.ts";
import type { Diagnostic } from "../diagnostics/diagnostic.ts";
import type { Source } from "../util/span.ts";

export interface CheckCommandResult {
  readonly exit_code: number;
  readonly output: string;
}

export function run_check(
  positionals: readonly string[],
  flags: Readonly<Record<string, string | true>>,
): CheckCommandResult {
  const choice = parse_target(typeof flags.target === "string" ? flags.target : undefined);
  if (!choice.ok) return { exit_code: 1, output: `error: ${choice.message}` };
  const files = positionals.length > 0 ? positionals : [default_entry(positionals)];
  const messages: string[] = [];
  const sources = new Map<string, Source>();
  const diagnostics: Diagnostic[] = [];
  let failed = false;

  for (const file of files) {
    const absolute = resolve(file);
    let text: string;
    try {
      text = readFileSync(absolute, "utf8");
    } catch {
      const source = source_of(absolute, "");
      diagnostics.push(
        make_error(CODES.file_not_found, `no existe el archivo «${file}»`, span_from(source, 0, 0)),
      );
      messages.push(`error: no existe el archivo «${file}»`);
      failed = true;
      continue;
    }

    const source = make_source(absolute, text);
    sources.set(absolute, source);
    const sink = make_sink({ max: 200 });
    const analysis = analyze_graph(absolute, sink);
    // Con `--target js` se comprueba además lo que el emisor JavaScript no
    // sabe representar (FFI, `meld`, enlaces con C…), sin escribir archivos.
    if (choice.target === "js" && !sink.has_errors() && analysis.entry_module !== undefined) {
      const entry = analysis.units.find((unit) => unit.module === analysis.entry_module);
      if (entry !== undefined) generate_js_program(analysis.units, entry, sink, {});
    }
    // Los diagnósticos pueden venir de otros módulos del grafo.
    for (const diagnostic of sink.diagnostics) {
      const file = diagnostic.span.file;
      if (sources.has(file)) continue;
      try {
        sources.set(file, make_source(file, readFileSync(file, "utf8")));
      } catch {
        // Sin fuente disponible: el render muestra solo la ubicación.
      }
    }

    const file_diagnostics = [...sink.diagnostics];
    diagnostics.push(...file_diagnostics);
    if (sink.has_errors()) failed = true;

    if (file_diagnostics.length === 0) {
      messages.push(`✓ ${file}: sin diagnósticos`);
    } else {
      messages.push(`${file_diagnostics.length} diagnóstico(s) en ${file}`);
    }
  }

  // `--json`: salida legible por máquinas (editores y CI).
  if (flags.json === true) {
    const payload = {
      ok: !failed,
      diagnostics: diagnostics.map((diagnostic) => ({
        code: diagnostic.code,
        severity: diagnostic.severity,
        message: diagnostic.message,
        file: diagnostic.span.file,
        line: diagnostic.span.start.line,
        column: diagnostic.span.start.column,
        endLine: diagnostic.span.end.line,
        endColumn: diagnostic.span.end.column,
        notes: diagnostic.notes,
      })),
    };
    return { exit_code: failed ? 1 : 0, output: JSON.stringify(payload) };
  }

  const color = flags.color === true || (flags.color === undefined && process.stdout.isTTY);
  if (diagnostics.length > 0) {
    messages.push(render_diagnostics(diagnostics, sources, { color }));
  }

  return { exit_code: failed ? 1 : 0, output: messages.join("\n") };
}
