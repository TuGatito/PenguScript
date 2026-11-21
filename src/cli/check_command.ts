// Comando `pengu check`.
//
// Compila en memoria hasta el checker y presenta los diagnósticos.
// Es la primera fase completa del pipeline: lexer → parser → checker.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { analyze_graph } from "../driver/analyze.ts";
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
  const files = positionals.length > 0 ? positionals : ["main.pengu"];
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
      messages.push(`error: no se pudo leer «${file}»`);
      failed = true;
      continue;
    }

    const source = make_source(absolute, text);
    sources.set(absolute, source);
    const sink = make_sink({ max: 200 });
    analyze_graph(absolute, sink);
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

  const color = flags.color === true || (flags.color === undefined && process.stdout.isTTY);
  if (diagnostics.length > 0) {
    messages.push(render_diagnostics(diagnostics, sources, { color }));
  }

  return { exit_code: failed ? 1 : 0, output: messages.join("\n") };
}
