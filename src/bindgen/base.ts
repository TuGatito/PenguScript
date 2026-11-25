// Reutilización de un módulo base: al generar los enlaces de una cabecera que
// incluye otra (raygui sobre raylib), los nombres declarados en la base no se
// vuelven a emitir y sus tipos se cualifican con el reino de la base.

import type { NativeHeader } from "./clang_ast.ts";
import type { MacroTable } from "./macros.ts";

export interface BaseTypes {
  readonly realm: string;
  readonly module: string;
  readonly names: ReadonlySet<string>;
  readonly functions: ReadonlySet<string>;
  readonly constants: ReadonlySet<string>;
}

export function collect_base(
  header: NativeHeader,
  macros: MacroTable,
  realm: string,
  module: string,
): BaseTypes {
  const names = new Set<string>();
  for (const record of header.records) names.add(record.name);
  for (const item of header.enums) names.add(item.name);
  for (const item of header.typedefs) names.add(item.name);
  const functions = new Set(header.functions.map((item) => item.name));
  const constants = new Set(macros.constants.map((item) => item.name));
  return { realm, module, names, functions, constants };
}
