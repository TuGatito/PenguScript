// Proyecto analizado para el LSP: todos los archivos que alcanza el
// documento abierto (él mismo, sus imports y `std/`), con sus diagnósticos
// y con un índice de símbolos listo para responder consultas.

import { readFileSync } from "node:fs";
import { dirname } from "node:path";
import { find_project_root } from "../project/paths.ts";
import { make_source } from "../util/span.ts";
import type { Source } from "../util/span.ts";
import type { Program } from "../frontend/ast.ts";
import type { Diagnostic } from "../diagnostics/diagnostic.ts";
import { analyze_project } from "../driver/analyze.ts";
import type { LoadedAnalysis } from "../driver/analyze.ts";
import type { SymbolIndex } from "../semantic/symbols.ts";
import type { ProgramUnit } from "../codegen/cpp_module.ts";
import { collect_type_realms } from "../codegen/cpp_module.ts";
import type { ModuleInfo } from "../semantic/module_info.ts";
import type { ParseCache } from "../project/module_graph.ts";
import { build_index } from "./index.ts";

export interface FileAnalysis {
  readonly file: string;
  readonly source: Source;
  readonly program: Program;
  readonly module: ModuleInfo;
  readonly analysis: LoadedAnalysis;
  readonly diagnostics: readonly Diagnostic[];
}

export interface ProjectState {
  readonly entry: string;
  readonly root: string;
  readonly files: ReadonlyMap<string, FileAnalysis>;
  readonly index: SymbolIndex;
  // Unidades listas para codegen: la medición de tamaños las reutiliza.
  readonly units: readonly ProgramUnit[];
  readonly entry_module: ModuleInfo;
  readonly type_realms: ReadonlyMap<string, string>;
}

// `overlays` son los buffers sin guardar, indexados por ruta absoluta:
// el editor manda lo que se ve, no lo que hay en disco.
export interface ProjectOptions {
  // Caché de parseo que el servidor conserva entre pulsaciones.
  readonly parse_cache?: ParseCache;
  // Raíz del workspace: manda sobre la raíz deducida del archivo abierto.
  readonly root?: string;
}

export function build_project(
  entry: string,
  overlays: ReadonlyMap<string, string> = new Map(),
  options: ProjectOptions = {},
): ProjectState {
  const project = analyze_project(entry, {
    read_file: (path) => overlays.get(path),
    parse_cache: options.parse_cache,
    root: options.root,
  });

  const files = new Map<string, FileAnalysis>();
  for (const analyzed of project.modules) {
    const file = analyzed.loaded.file;
    const text = overlays.get(file) ?? read_text(file);
    if (text === undefined) continue;
    files.set(file, {
      file,
      source: make_source(file, text),
      program: analyzed.loaded.program,
      module: analyzed.loaded.info,
      analysis: analyzed,
      diagnostics: analyzed.diagnostics,
    });
  }

  const entry_file = files.get(entry) ?? files.values().next().value;
  if (entry_file === undefined) {
    throw new Error(`el proyecto «${entry}» no produjo ningún archivo analizable`);
  }
  const units = project.modules.map((analyzed) => analyzed.unit);
  const entry_module = project.entry?.loaded.info ?? entry_file.module;
  return {
    entry,
    root: options.root ?? find_project_root(dirname(entry)),
    files,
    index: build_index(files),
    units,
    entry_module,
    type_realms: collect_type_realms(units),
  };
}

function read_text(file: string): string | undefined {
  try {
    return readFileSync(file, "utf8");
  } catch {
    return undefined;
  }
}
