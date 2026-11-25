// Informe de una ejecución de `pengu ts-bindgen`.
//
// Mismo espíritu que el de `pengu bindgen` (C): nada se omite en silencio.
// Cada omisión y cada colapso lleva su motivo y su ubicación en el `.d.ts`.

export interface ModuleCoverage {
  readonly types: number;
  readonly emitted: number;
  readonly members: number;
  readonly members_emitted: number;
}

export interface TsBindingReport {
  readonly text: string;
  readonly types: number;
  readonly members: number;
  readonly skipped: readonly string[];
  readonly collapsed: readonly string[];
  readonly coverage: Readonly<Record<string, ModuleCoverage>>;
}

export function empty_report(): TsBindingReport {
  return {
    text: "",
    types: 0,
    members: 0,
    skipped: [],
    collapsed: [],
    coverage: {},
  };
}

export function with_text(report: TsBindingReport, text: string): TsBindingReport {
  return { ...report, text };
}

export function coverage_percent(entry: ModuleCoverage): number {
  if (entry.members === 0) return 100;
  return Math.round((entry.members_emitted / entry.members) * 100);
}

export function format_report(report: TsBindingReport): string {
  const lines: string[] = [];
  lines.push(`Tipos: ${report.types} · miembros: ${report.members}`);
  const modules = Object.keys(report.coverage).sort();
  if (modules.length > 0) {
    lines.push("Cobertura por módulo:");
    for (const name of modules) {
      const entry = report.coverage[name];
      if (entry === undefined) continue;
      lines.push(
        `  ${name}: ${coverage_percent(entry)}% (${entry.members_emitted}/${entry.members} miembros, ${entry.emitted}/${entry.types} tipos)`,
      );
    }
  }
  if (report.collapsed.length > 0) {
    lines.push(`Colapsos: ${report.collapsed.length}`);
    for (const item of report.collapsed) lines.push(`  ${item}`);
  }
  if (report.skipped.length > 0) {
    lines.push(`Omitidas: ${report.skipped.length}`);
    for (const item of report.skipped) lines.push(`  ${item}`);
  }
  return lines.join("\n");
}

export interface ReportJson {
  readonly ok: boolean;
  readonly types: number;
  readonly members: number;
  readonly skipped: readonly string[];
  readonly collapsed: readonly string[];
  readonly coverage: Readonly<Record<string, ModuleCoverage & { readonly percent: number }>>;
}

export function report_to_json(report: TsBindingReport): ReportJson {
  const coverage: Record<string, ModuleCoverage & { percent: number }> = {};
  for (const [name, entry] of Object.entries(report.coverage)) {
    coverage[name] = { ...entry, percent: coverage_percent(entry) };
  }
  return {
    ok: true,
    types: report.types,
    members: report.members,
    skipped: report.skipped,
    collapsed: report.collapsed,
    coverage,
  };
}

export function render_report_json(report: TsBindingReport): string {
  return JSON.stringify(report_to_json(report), null, 2);
}
