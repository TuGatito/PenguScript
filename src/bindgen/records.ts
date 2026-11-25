// Orden de los records para emitirlos: PenguScript no tiene
// declaraciones adelantadas de runes, así que un record debe aparecer
// antes que cualquier otro al que se refiera su cuerpo.

import type { NativeRecord } from "./clang_ast.ts";
import type { TypeRegistry } from "./native_types.ts";
import { final_type_name } from "./native_types.ts";

export interface RecordOrder {
  readonly ordered: readonly NativeRecord[];
  readonly cycles: readonly string[];
}

export function order_records(records: readonly NativeRecord[], registry: TypeRegistry): RecordOrder {
  const by_name = new Map<string, NativeRecord>();
  for (const record of records) by_name.set(record.name, record);

  const dependencies = new Map<string, string[]>();
  for (const record of records) {
    const deps: string[] = [];
    for (const field of record.fields) {
      const name = final_type_name(field.type, registry);
      if (name !== undefined && name !== record.name && by_name.has(name) && !deps.includes(name)) {
        deps.push(name);
      }
    }
    dependencies.set(record.name, deps);
  }

  const ordered: NativeRecord[] = [];
  const cycles: string[] = [];
  const state = new Map<string, "visiting" | "done">();

  const visit = (name: string, chain: string[]): void => {
    const current = state.get(name);
    if (current === "done") return;
    if (current === "visiting") {
      const cycle = [...chain.slice(chain.indexOf(name)), name].join(" → ");
      if (!cycles.includes(cycle)) cycles.push(cycle);
      return;
    }
    const record = by_name.get(name);
    if (record === undefined) return;
    state.set(name, "visiting");
    for (const dep of dependencies.get(name) ?? []) visit(dep, [...chain, name]);
    state.set(name, "done");
    ordered.push(record);
  };

  for (const record of records) visit(record.name, []);
  return { ordered, cycles };
}
