// Tabla de tamaños del lado del servidor: «stale-while-revalidate».
//
// Medir tamaños compila un programa C++ (~1,9 s), así que ninguna petición del
// editor puede esperarla. Las peticiones leen la última tabla conocida y, si
// las declaraciones cambiaron, la medición se agenda para cuando el usuario
// lleve un rato sin tocar nada.

import type { FieldLookup, SizeLookup } from "./hover.ts";
import type { ProjectSizes } from "./sizes.ts";

export interface SizesState {
  lookup: SizeLookup | undefined;
  fields: FieldLookup | undefined;
  stale: boolean;
  computing: boolean;
  timer: NodeJS.Timeout | undefined;
}

export function empty_sizes_state(): SizesState {
  return { lookup: undefined, fields: undefined, stale: true, computing: false, timer: undefined };
}

/** Las declaraciones cambiaron: la tabla sigue sirviendo, pero está vieja. */
export function invalidate_sizes(state: SizesState): void {
  state.stale = true;
}

export function has_sizes(state: SizesState): boolean {
  return state.lookup !== undefined;
}

/**
 * Agenda una medición para dentro de `delay` ms. Si ya había una agendada, se
 * sustituye (siempre se mide la última versión del proyecto).
 */
export function schedule_sizes(
  state: SizesState,
  delay: number,
  compute: () => ProjectSizes,
  on_update: () => void,
): void {
  if (state.timer !== undefined) clearTimeout(state.timer);
  state.timer = setTimeout(() => {
    state.timer = undefined;
    run_sizes(state, compute, on_update);
  }, delay);
}

/** Mide ahora y avisa al editor (para el comando «medir tamaños»). */
export function refresh_sizes(state: SizesState, compute: () => ProjectSizes, on_update: () => void): void {
  if (state.timer !== undefined) clearTimeout(state.timer);
  state.timer = undefined;
  state.stale = true;
  run_sizes(state, compute, on_update);
}

function run_sizes(state: SizesState, compute: () => ProjectSizes, on_update: () => void): void {
  if (state.computing) return;
  state.computing = true;
  try {
    const sizes = compute();
    state.lookup = sizes.lookup;
    state.fields = sizes.fields;
    state.stale = false;
  } finally {
    state.computing = false;
  }
  on_update();
}
