// Análisis compartido por `check`, `build` y `run`: carga el grafo de
// módulos y ejecuta el checker sobre cada unidad.

import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { load_graph } from "../project/module_graph.ts";
import { check_loaded_module } from "../semantic/checker.ts";
import type { ProgramUnit } from "../codegen/cpp_module.ts";
import type { ModuleInfo } from "../semantic/module_info.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import type { PenguType } from "../semantic/types.ts";
import type { ModuleGraph } from "../project/module_graph.ts";

export interface Analysis {
  readonly graph: ModuleGraph;
  readonly units: readonly ProgramUnit[];
  readonly entry_module: ModuleInfo | undefined;
}

export function analyze_graph(source_path: string, sink: DiagnosticSink): Analysis {
  const graph = load_graph(source_path);
  for (const diagnostic of graph.diagnostics) sink.add(diagnostic);

  const units: ProgramUnit[] = [];
  for (const loaded of graph.order) {
    const types = new Map<ExprNode, PenguType>();
    const external_modules = new Map<string, ModuleInfo>();
    const external_realms = new Map<string, string>();
    for (const [alias, imported] of loaded.imports) {
      external_modules.set(alias, imported.info);
      external_realms.set(alias, imported.info.realm);
    }
    const selective = new Map<string, { module: ModuleInfo; name: string }>();
    for (const [name, symbol] of loaded.selective) {
      selective.set(name, { module: symbol.module.info, name: symbol.name });
    }
    // Se reutiliza el módulo ya recogido: al cargar el grafo se fusionan
    // los símbolos de los realms reabiertos en varios archivos.
    const module = loaded.info;
    check_loaded_module(module, loaded.program, sink, {
      types,
      external: { modules: external_modules, selective },
    });
    const selective_realms = new Map<string, string>();
    for (const [name, symbol] of loaded.selective) selective_realms.set(name, symbol.module.info.realm);
    units.push({ program: loaded.program, module, types, external_realms, selective_realms });
  }

  const entry_module = graph.entry?.info ?? units[units.length - 1]?.module;
  return { graph, units, entry_module };
}
