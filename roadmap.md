Roadmap sugerido
P0 (~1–2 días, higiene): código de salida, #line, invalidación real de caché, pengu_init/argv, unificar versiones. Es lo que hace todo lo demás depurable.
P1 (~1–2 semanas, desbloquea raylib): ... en declare + codegen + pengu_bind; arreglar el E0011 de arrays de structs; arreglar el codegen de (xs length) (hoy genera xs.len → error de gcc); shim de raymath; slices de cualquier tipo + indexado de punteros.
P2 (~2–4 semanas, amplitud): binding de rlgl, arrays 2D, idioma de estado de módulo, API de liberación para string/list/map, tipado estricto de punteros, pengu bind usable con headers reales.
