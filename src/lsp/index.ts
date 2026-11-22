// Índice del proyecto: símbolos de todos los archivos analizados.

import type { Symbol, SymbolIndex } from "../semantic/symbols.ts";
import { local_symbols, make_symbol_index, module_symbols } from "../semantic/symbols.ts";
import type { FileAnalysis } from "./project.ts";

export function build_index(files: ReadonlyMap<string, FileAnalysis>): SymbolIndex {
  const symbols: Symbol[] = [];
  const seen = new Set<string>();
  for (const file of files.values()) {
    for (const symbol of module_symbols(file.file, file.module, file.source)) {
      if (seen.has(symbol.id)) continue;
      seen.add(symbol.id);
      symbols.push(symbol);
    }
    for (const symbol of local_symbols(file.file, file.analysis.locals, file.module.realm)) {
      if (seen.has(symbol.id)) continue;
      seen.add(symbol.id);
      symbols.push(symbol);
    }
  }
  return make_symbol_index(symbols);
}
