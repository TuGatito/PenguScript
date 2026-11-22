// Tamaños medidos para el editor: reutiliza la medición del compilador
// (`compute_layout`) y traduce tipos PenguScript a sus nombres C++.

import { dirname, join } from "node:path";
import { compute_layout } from "../driver/layout.ts";
import type { LayoutTable } from "../driver/layout.ts";
import type { PenguType } from "../semantic/types.ts";
import type { FieldLookup, SizeLookup } from "./hover.ts";
import type { ProjectState } from "./project.ts";

export interface ProjectSizes {
  readonly table: LayoutTable;
  readonly lookup: SizeLookup;
  readonly fields: FieldLookup;
}

const EMPTY: ProjectSizes = {
  table: { available: false, message: "sin medición", types: new Map(), values: new Map(), functions: new Map() },
  lookup: () => undefined,
  fields: () => undefined,
};

// `cache_dir` vive junto al proyecto para que sobreviva a reinicios del
// servidor y se invalide sola cuando cambian las declaraciones.
export function project_sizes(project: ProjectState, cache_dir?: string): ProjectSizes {
  const directory = cache_dir ?? join(dirname(project.entry), ".pengu-cache", "layout");
  const table = compute_layout(project.units, project.entry_module, { cache_dir: directory });
  if (!table.available) return { table, lookup: () => undefined, fields: () => undefined };
  return { table, lookup: make_lookup(project, table), fields: make_fields(project, table) };
}

function make_lookup(project: ProjectState, table: LayoutTable): SizeLookup {
  return (type: PenguType) => {
    const name = layout_name(project, type);
    if (name === undefined) return undefined;
    const layout = table.types.get(name);
    if (layout === undefined) return undefined;
    return { size: layout.size, align: layout.align };
  };
}

function make_fields(project: ProjectState, table: LayoutTable): FieldLookup {
  return (type: PenguType, field: string) => {
    const name = layout_name(project, type);
    if (name === undefined) return undefined;
    const layout = table.types.get(name);
    return layout?.fields.find((item) => item.name === field);
  };
}

// Nombre con el que `layout_targets` registra cada tipo medido.
export function layout_name(project: ProjectState, type: PenguType): string | undefined {
  switch (type.kind) {
    case "primitive": {
      const name = type.name === "long long" ? "long long" : type.name;
      return name;
    }
    case "named": {
      const realm = project.type_realms.get(type.name);
      return realm === undefined ? type.name : `${realm}::${type.name}`;
    }
    case "optional":
      return layout_name(project, type.inner);
    case "ref":
      return layout_name(project, type.inner);
    default:
      return undefined;
  }
}

export { EMPTY as empty_sizes };
