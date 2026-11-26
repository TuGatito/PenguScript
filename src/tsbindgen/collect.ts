// Orquestación de `pengu ts-bindgen`: del `.d.ts` al texto `.d.pengu` y al
// informe de lo que quedó fuera.

import { CORE_HOST_TYPES, partition_module } from "./partition.ts";
import { binding_summary, emit_binding_module } from "./emit_dts.ts";
import { empty_report } from "./report.ts";
import type { TsBindingReport } from "./report.ts";
import type { EmitOptions } from "./emit_dts.ts";
import type { PenguBindingModule } from "./partition.ts";
import { read_dts_file, read_dts_text } from "./dts_reader.ts";
import { domain_names, filter_module } from "./domain.ts";
import type { DtsModule } from "./dts_ast.ts";

export interface BindOptions {
  // Realm del módulo generado; si no se indica se deduce del dominio.
  readonly realm: string;
  // Nombre del `.d.ts` tal cual aparece en la cabecera (`lib.dom.d.ts`).
  readonly source: string;
  readonly invokes?: readonly string[];
  // Dominio del catálogo (`dom`, `canvas`…): recorta el módulo a ese dominio.
  readonly only?: string;
}

export interface BindResult {
  readonly module: PenguBindingModule;
  readonly dts: DtsModule;
  readonly text: string;
  readonly summary: string;
  readonly report: TsBindingReport;
}

function narrowed(dts: DtsModule, only: string | undefined): DtsModule {
  if (only === undefined) return dts;
  return filter_module(dts, domain_names(only));
}

function report_of(module: PenguBindingModule, text: string, source: string): TsBindingReport {
  const base = empty_report();
  return {
    ...base,
    text,
    types: module.host_types.length,
    members: module.members,
    skipped: module.skipped.map((item) => `${item.name}: ${item.reason}`),
    collapsed: module.collapsed,
    overrides: module.overrides,
    coverage: {
      [source]: {
        types: module.host_types.length,
        emitted: module.host_types.length,
        members: module.members,
        members_emitted: module.members,
      },
    },
  };
}

export function bind_dts_text(text: string, file: string, options: BindOptions): BindResult {
  const dts = narrowed(read_dts_text(file, text), options.only);
  const module = partition_module(dts, {
    declared: (options.invokes ?? []).includes("std/js/types") ? CORE_HOST_TYPES : [],
  });
  const emitted = emit_binding_module(module, options);
  return {
    module,
    dts,
    text: emitted,
    summary: binding_summary(module),
    report: report_of(module, emitted, options.source),
  };
}

export function bind_dts_file(path: string, options: BindOptions): BindResult {
  const dts = narrowed(read_dts_file(path), options.only);
  const module = partition_module(dts, {
    declared: (options.invokes ?? []).includes("std/js/types") ? CORE_HOST_TYPES : [],
  });
  const emit: EmitOptions = options;
  const emitted = emit_binding_module(module, emit);
  return {
    module,
    dts,
    text: emitted,
    summary: binding_summary(module),
    report: report_of(module, emitted, options.source),
  };
}

// Dominio por defecto de un `.d.ts`: `lib.dom.d.ts` → `dom`, `lib.es2022.d.ts`
// → `es2022`.
export function domain_of(path: string): string {
  const base = path.slice(path.lastIndexOf("/") + 1);
  const match = /^lib\.([A-Za-z0-9_]+?)(?:\.[A-Za-z0-9_.]+)?\.d\.ts$/.exec(base);
  return match?.[1] ?? base.replace(/\.d\.ts$/, "").replace(/[^A-Za-z0-9]+/g, "_");
}
