// Análisis compartido por `check`, `build`, `run` y el LSP: carga el grafo
// de módulos y ejecuta el checker sobre cada unidad.

import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { make_sink } from "../diagnostics/sink.ts";
import type { Diagnostic } from "../diagnostics/diagnostic.ts";
import { load_graph } from "../project/module_graph.ts";
import type { ParseCache } from "../project/module_graph.ts";
import { same_method_signature } from "../semantic/module_info.ts";
import type { EnchantedType } from "../semantic/type_env.ts";
import { check_loaded_module } from "../semantic/checker.ts";
import type { ProgramUnit } from "../codegen/cpp_module.ts";
import type { ModuleInfo } from "../semantic/module_info.ts";
import type { LoadedModule } from "../project/module_graph.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import type { PenguType } from "../semantic/types.ts";
import type { MethodTarget } from "../semantic/type_env.ts";
import type { ModuleGraph } from "../project/module_graph.ts";
import type { LocalSymbol } from "../semantic/symbols.ts";

// Lo que el LSP necesita de un archivo: su programa, su módulo, los tipos
// anotados, sus locales y sus diagnósticos, sin volver a analizar nada.
export interface LoadedAnalysis {
  readonly loaded: LoadedModule;
  readonly unit: ProgramUnit;
  readonly types: Map<ExprNode, PenguType>;
  readonly member_targets: Map<ExprNode, MethodTarget>;
  readonly locals: LocalSymbol[];
  readonly diagnostics: readonly Diagnostic[];
  readonly imports: ReadonlyMap<string, { readonly module: ModuleInfo; readonly realm: string }>;
  readonly selective: ReadonlyMap<string, { readonly module: ModuleInfo; readonly name: string }>;
  readonly enchants: ReadonlyMap<string, EnchantedType>;
}

export interface ProjectAnalysis {
  readonly graph: ModuleGraph;
  readonly modules: readonly LoadedAnalysis[];
  readonly entry: LoadedAnalysis | undefined;
}

export interface Analysis {
  readonly graph: ModuleGraph;
  readonly units: readonly ProgramUnit[];
  readonly entry_module: ModuleInfo | undefined;
}

export interface AnalyzeOptions {
  // Sustituye la lectura de disco (buffers sin guardar del editor).
  readonly read_file?: (path: string) => string | undefined;
  // Reutiliza el AST de los archivos cuyo contenido no cambió.
  readonly parse_cache?: ParseCache;
}

export function analyze_project(source_path: string, options: AnalyzeOptions = {}): ProjectAnalysis {
  const graph = load_graph(source_path, { read_file: options.read_file, parse_cache: options.parse_cache });

  const modules: LoadedAnalysis[] = [];
  for (const loaded of graph.order) {
    const types = new Map<ExprNode, PenguType>();
    const member_targets = new Map<ExprNode, MethodTarget>();
    const locals: LocalSymbol[] = [];
    const external_modules = new Map<string, ModuleInfo>();
    const external_realms = new Map<string, string>();
    for (const [alias, imported] of loaded.imports) {
      external_modules.set(alias, imported.info);
      external_realms.set(alias, imported.info.realm);
    }
    const enchants = new Map<string, EnchantedType>();
    for (const imported of loaded.imports.values()) {
      for (const [key, entry] of imported.info.env.enchants) {
        const existing = enchants.get(key);
        if (existing === undefined) {
          enchants.set(key, { ...entry, methods: new Map(entry.methods) });
          continue;
        }
        for (const [name, methods] of entry.methods) {
          const list = existing.methods.get(name);
          if (list === undefined) existing.methods.set(name, [...methods]);
          else for (const method of methods) if (!list.some((other) => other.realm === method.realm && same_method_signature(other.info, method.info))) list.push(method);
        }
      }
    }

    const selective = new Map<string, { module: ModuleInfo; name: string }>();
    for (const [name, symbol] of loaded.selective) {
      selective.set(name, { module: symbol.module.info, name: symbol.name });
    }

    // Cada módulo tiene su sumidero: así el LSP publica diagnósticos por
    // archivo y `check` los cuenta todos.
    const sink = make_sink({ max: 200 });
    for (const diagnostic of graph.by_file.get(loaded.file) ?? []) sink.add(diagnostic);
    // Se reutiliza el módulo ya recogido: al cargar el grafo se fusionan
    // los símbolos de los realms reabiertos en varios archivos.
    const module = loaded.info;
    check_loaded_module(module, loaded.program, sink, {
      types,
      member_targets,
      locals,
      external: { modules: external_modules, selective, enchants },
    });

    // Alias visible → realm de origen y nombre real del símbolo (puede diferir
    // del alias: `invoke {format as fmt} from "std/format"`).
    const selective_symbols = new Map<string, { realm: string; name: string }>();
    for (const [name, symbol] of loaded.selective) {
      selective_symbols.set(name, { realm: symbol.module.info.realm, name: symbol.name });
    }
    modules.push({
      loaded,
      unit: {
        program: loaded.program,
        module,
        types,
        member_targets,
        external_realms,
        selective_symbols,
        external_modules,
      },
      types,
      member_targets,
      locals,
      diagnostics: sink.diagnostics,
      imports: external_modules.size === 0
        ? new Map()
        : new Map([...loaded.imports].map(([alias, imported]) => [alias, { module: imported.info, realm: imported.info.realm }])),
      selective,
      enchants,
    });
  }

  const entry = modules.find((item) => item.loaded === graph.entry)
    ?? modules[modules.length - 1];
  return { graph, modules, entry };
}

export function analyze_graph(source_path: string, sink: DiagnosticSink, options: AnalyzeOptions = {}): Analysis {
  const project = analyze_project(source_path, options);
  for (const diagnostic of project.graph.diagnostics) sink.add(diagnostic);
  for (const module of project.modules) {
    for (const diagnostic of module.diagnostics) sink.add(diagnostic);
  }
  const units = project.modules.map((item) => item.unit);
  const entry_module = project.entry?.loaded.info ?? units[units.length - 1]?.module;
  return { graph: project.graph, units, entry_module };
}
