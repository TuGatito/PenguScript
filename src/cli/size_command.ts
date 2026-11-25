// Comando `pengu size`.
//
// Muestra los tamaños reales (bytes y alineación) de tipos y variables del
// proyecto, medidos compilando un programa de sondeo con el toolchain.

import { dirname, join, resolve } from "node:path";
import { default_entry } from "./entry.ts";
import { analyze_graph } from "../driver/analyze.ts";
import { parse_target } from "../driver/target.ts";
import { compute_layout } from "../driver/layout.ts";
import { make_sink } from "../diagnostics/sink.ts";
import { render_diagnostics } from "../diagnostics/render.ts";

function by_name(left: { readonly name: string }, right: { readonly name: string }): number {
  return left.name.localeCompare(right.name);
}

export interface SizeCommandResult {
  readonly exit_code: number;
  readonly output: string;
}

export function run_size(
  positionals: readonly string[],
  flags: Readonly<Record<string, string | true>>,
): SizeCommandResult {
  const choice = parse_target(typeof flags.target === "string" ? flags.target : undefined);
  if (!choice.ok) return { exit_code: 1, output: `error: ${choice.message}` };
  if (choice.target === "js") {
    return {
      exit_code: 1,
      output: "error: «size» mide el diseño de memoria del backend C++; en JavaScript no hay tamaños ni alineación",
    };
  }
  const file = resolve(positionals.length > 0 ? (positionals[0] ?? default_entry(positionals)) : default_entry(positionals));
  const json = flags.json === true;
  const sink = make_sink({ max: 200 });
  const analysis = analyze_graph(file, sink);
  if (sink.has_errors()) {
    return { exit_code: 1, output: render_diagnostics(sink.diagnostics, new Map(), { color: false }) };
  }
  const entry_module = analysis.entry_module;
  if (entry_module === undefined) {
    return { exit_code: 1, output: `no se pudo analizar «${file}»` };
  }
  const compiler = typeof flags.compiler === "string" ? flags.compiler : undefined;
  const cache_dir = join(dirname(file), ".pengu-cache", "layout");
  const table = compute_layout(analysis.units, entry_module, { compiler, cache_dir });
  if (!table.available) {
    return { exit_code: 1, output: table.message ?? "medición no disponible" };
  }

  const only = typeof flags.type === "string" ? flags.type : undefined;
  const keep = (name: string): boolean => only === undefined || name.includes(only);
  const types = [...table.types.values()].filter((row) => keep(row.name)).sort(by_name);
  const values = [...table.values.values()].filter((row) => keep(row.name)).sort(by_name);
  const functions = [...table.functions.values()].filter((row) => keep(row.name)).sort(by_name);
  const fields = flags.fields === true;

  if (json) {
    return {
      exit_code: 0,
      output: `${JSON.stringify({ ok: true, types, values, functions }, null, 2)}\n`,
    };
  }
  const lines: string[] = ["Tipos", "Tipo\tBytes\tAlineación"];
  for (const row of types) {
    lines.push(`${row.name}\t${row.size}\t${row.align}`);
    if (fields) {
      for (const field of row.fields) {
        lines.push(
          field.width !== undefined
            ? `  .${field.name}\t${field.size}\tbits ${field.width}`
            : `  .${field.name}\t${field.size}\t+${field.offset ?? 0}`,
        );
      }
    }
  }
  if (values.length > 0) {
    lines.push("", "Valores", "Nombre\tBytes\tAlineación");
    for (const row of values) lines.push(`${row.name}\t${row.size}\t${row.align}`);
  }
  if (functions.length > 0) {
    lines.push("", "Funciones", "Nombre\tRetorno\tParámetros\tTotal\tstd::function");
    for (const row of functions) {
      lines.push(`${row.name}\t${row.result}\t${row.params}\t${row.total}\t${row.callable}`);
    }
  }
  return { exit_code: 0, output: `${lines.join("\n")}\n` };
}
