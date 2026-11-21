// Operadores libres: `operator + = (a: int, b: Punto) -> Punto`.
//
// Se registran como funciones cuyo nombre es `operator <símbolo>`. El
// checker y el codegen los buscan cuando el operando izquierdo no
// declara el operador en un bloque `enchanting`.

import type { ExternalImports } from "./external.ts";
import type { FunctionInfo, ModuleInfo } from "./module_info.ts";
import type { PenguType } from "./types.ts";
import type { TypeEnv } from "./type_env.ts";
import { can_assign } from "./checker_context.ts";

export interface FreeOperator {
  readonly info: FunctionInfo;
  readonly module: ModuleInfo;
}

export function operator_symbol(operator: string): string {
  return `operator ${operator}`;
}

// Busca un operador libre cuyo primer parámetro acepte `left` y el
// segundo acepte `right`. Primero el módulo actual y luego los
// importados (el orden de `invoke`).
export function find_free_operator(
  module: ModuleInfo,
  external: ExternalImports | undefined,
  operator: string,
  left: PenguType,
  right: PenguType,
  env: TypeEnv,
): FreeOperator | undefined {
  const name = operator_symbol(operator);
  const own = module.functions.get(name);
  if (own !== undefined && accepts(own, left, right, env)) return { info: own, module };

  if (external !== undefined) {
    for (const imported of external.modules.values()) {
      const info = imported.functions.get(name);
      if (info !== undefined && accepts(info, left, right, env)) {
        return { info, module: imported };
      }
    }
  }
  return undefined;
}

function accepts(
  info: FunctionInfo,
  left: PenguType,
  right: PenguType,
  env: TypeEnv,
): boolean {
  const first = info.params[0];
  const second = info.params[1];
  if (first === undefined || second === undefined) return false;
  return can_assign(first.type, left, env) && can_assign(second.type, right, env);
}
