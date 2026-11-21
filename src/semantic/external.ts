// Símbolos importados de otros módulos.
//
// El cargador de módulos produce este mapa; el checker lo consulta
// cuando un nombre no está en el ámbito local ni en el módulo actual.

import type { ModuleInfo } from "./module_info.ts";
import type { PenguType } from "./types.ts";
import { function_type_of } from "./module_info.ts";
import { named, optional } from "./types.ts";

export interface ExternalSymbol {
  readonly module: ModuleInfo;
  readonly name: string;
}

export interface ExternalImports {
  readonly modules: ReadonlyMap<string, ModuleInfo>;
  readonly selective: ReadonlyMap<string, ExternalSymbol>;
}

// Tipo de un símbolo público de `module`; `undefined` si no existe.
export function symbol_type_of(module: ModuleInfo, name: string): PenguType | undefined {
  const constant = module.consts.get(name);
  if (constant !== undefined) return constant.type;

  const fn = module.functions.get(name);
  if (fn !== undefined) return function_type_of(fn);

  const rune = module.env.runes.get(name);
  if (rune !== undefined) return named(name);

  const omen = module.env.omens.get(name);
  if (omen !== undefined) return named(name);

  const alias = module.env.aliases.get(name);
  if (alias !== undefined) return alias.seal ? named(name) : alias.target;

  return undefined;
}

export function external_value_type(external: ExternalImports | undefined, alias: string, name: string): PenguType | undefined {
  if (external === undefined) return undefined;
  const module = external.modules.get(alias);
  if (module === undefined) return undefined;
  return symbol_type_of(module, name);
}

export function external_optional_result(type: PenguType): PenguType {
  return optional(type);
}
