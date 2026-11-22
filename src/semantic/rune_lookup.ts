// Búsqueda de runes declarados en el módulo propio o en uno importado.
//
// Un rune puede declararse en cualquier módulo y usarse desde otro (por
// ejemplo `std/time` publica `Duration`, `Instant` y `DateTime`). El
// checker solo miraba `ctx.module.env.runes`, así que los métodos, los
// campos, los operadores y `Display` de un rune importado no existían
// fuera de su archivo. Este módulo centraliza la búsqueda para que
// todos los sitios de resolución usen la misma regla: primero el
// módulo propio, después los módulos importados con `invoke`.

import type { CheckContext } from "./checker_context.ts";
import type { FieldInfo, MethodInfo, RuneInfo, TypeEnv } from "./type_env.ts";
import { find_rune_field, find_rune_method } from "./type_env.ts";

export interface RuneLookup {
  readonly rune: RuneInfo;
  // Entorno donde vive el rune: `find_rune_field`/`find_rune_method`
  // lo necesitan para resolver los runes heredados (`is`).
  readonly env: TypeEnv;
}

// Rune visible desde el módulo actual (propio o importado).
export function rune_lookup(ctx: CheckContext, name: string): RuneLookup | undefined {
  const own = ctx.module.env.runes.get(name);
  if (own !== undefined) return { rune: own, env: ctx.module.env };
  for (const module of ctx.external?.modules.values() ?? []) {
    const rune = module.env.runes.get(name);
    if (rune !== undefined) return { rune, env: module.env };
  }
  return undefined;
}

export function rune_field_of(ctx: CheckContext, name: string, field: string): FieldInfo | undefined {
  const lookup = rune_lookup(ctx, name);
  if (lookup === undefined) return undefined;
  return find_rune_field(lookup.env, lookup.rune, field);
}

export function rune_method_of(ctx: CheckContext, name: string, method: string): MethodInfo | undefined {
  const lookup = rune_lookup(ctx, name);
  if (lookup === undefined) return undefined;
  return find_rune_method(lookup.env, lookup.rune, method);
}

export function has_rune(ctx: CheckContext, name: string): boolean {
  return rune_lookup(ctx, name) !== undefined;
}
