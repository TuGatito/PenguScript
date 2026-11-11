# Migración a C++ — decisiones de F0.4 (firmadas)

**Fecha:** 2026-11-10
**Estado:** firmadas. Cierran F0.4 y desbloquean F1.
**Contexto:** `scratch/INFORME_MIGRACION_CPP.es.md` §14 y §15 (mediciones), `docs/LANGUAGECPP.es.md` (dialecto objetivo).
**Regla de la casa:** cualquier decisión de este documento puede revisarse con datos nuevos, pero no se revisa por preferencia: se revisa si cambia una de las condiciones de revisión indicadas.

---

## A1 — Nombres del dialecto

**Decisión:** se adoptan los nombres del doc v1.0 tal cual: `born`, `die`, `mirror`, `inherit`, `vector`, `map`, `umap`, `span`, `unique`, `shared`, `weak`, `extern c`, `extern cpp`, `regnum`, `set`, `uset`, `array`, `maybe`, `result`, `string`, `many`.

**Por qué:** son los del apéndice A del doc y los que la documentación pública ya describe. Los contextuales (`born`/`die`/`mirror` dentro de `enchanting`, `inherit` tras el nombre de runa, `unique`/`shared`/`weak` como tipos, `extern` en su posición) siguen siendo identificadores válidos fuera de su posición, así que el fuente solo sufre por los **reservados** (los que dan `W0018`).

**Coste medido:** **66 renombrados** en el cierre del `psc` — `result` 47, `span` 12, `set` 3, `map` 2, `unique` 2. `vector`/`umap`/`array`/`maybe`/`string`/`shared`/`weak`/`many`: 0. Mecánicos, con `psc migrate`.

**Cuándo se aplica:** F2 (sintaxis). En F0/F1 no se toca el fuente.

**Condición de revisión:** que el renombrado de `result` (47 sitios, muchos en `std/spark` y `src/main.pengu`) revele una colisión semántica real con `result of T`, no solo de nombre.

---

## A2 — Representación de `string`

**Decisión:** `std::string` (doc §0.4), **sin ABI C**. La frontera con C usa `ref to frozen char` + longitud explícita; nunca se pasa un `std::string` por valor a una función `extern c`.

**Por qué:** `std::string` es la representación que hace posible el resto del dialecto (sin COW, con SSO y `data()` estable en C++17+). Mantener el `PenguString` actual en la frontera obligaría a dos representaciones y a convertir en cada llamada.

**Coste medido:** **87 firmas `declare`** que hoy cruzan `string`/`maybe string`/`list of` (de 202 `declare` en el cierre; `std/filum` 44, `std/archivum` 21, `std/rites` 14, `std/compass` 5, `std/chronicle` 2, `std/scrolls` 1). Cero runes cruzan por valor hoy, así que `@repr(c)` no tiene trabajo pendiente.

**Caso testigo:** `archivum.read_file_result` devuelve `maybe string` binario-seguro (puede contener `\0`). Al pasar a la frontera C hay que sustituirlo por `out` de longitud + código de error, no por `char*`. Documentado en `docs/ABI_C.md` (entregable de F2.5).

**Cuándo se aplica:** F2.5 (diseño de la frontera) y F3 (implementación).

**Condición de revisión:** que alguna de las 87 firmas necesite el `PenguString` COW por compatibilidad binaria con una librería externa que no podamos cambiar.

---

## A3 — `map` ordenado por defecto

**Decisión:** `map` = `std::map` (ordenado); `umap` = `std::unordered_map`. **Regla de oro:** no se itera un `map` para decidir el orden de salida del compilador; si el orden importa, se ordena explícitamente.

**Por qué:** el doc define `map` como ordenado (§ apéndice A) y el compilador ya depende hoy de orden estable en varios sitios (`sema/symbols/table`, catálogos, `codegen/catalog`). Un `std::map` lo da gratis; un hash obligaría a ordenar en cada punto de emisión.

**Coste medido:** **588 `map of`** en el cierre (105 líneas en 19 archivos solo en `src/`). `std/atlas` (368 `map of`) es candidata a desaparecer sobre `std::map`; se decide en F2.5.

**Cuándo se aplica:** F3 (semántica). En F2 el `map` sigue siendo el actual con COW.

**Condición de revisión:** que un perfil real del compilador muestre que `std::map` domina el tiempo de `psc check` (hoy `check .` caliente es 0,18 s, así que es improbable).

---

## A4 — JSON

**Decisión:** `derive Json` queda **fuera de alcance**. `std/json` se mantiene escrito a mano (como hoy: `JsonValue` es un omen recursivo con codec manual).

**Por qué:** el cierre del `psc` **no usa `derive Json`** (44 `derive` reales: solo `Par`, `Nexus`, `Imago`, `Vinculum`), así que el compilador no lo necesita para arrancar. Añadir `derive Json` al dialecto nuevo sería una feature nueva, no una migración.

**Coste medido:** 0 para el arranque; 4 omens algebraicos y ~53 `judge` en `std/` si algún día se reescribe.

**Cuándo se aplica:** F5 (si se decide añadirlo, ya con el compilador en C++).

**Condición de revisión:** que el LSP o `psc doc` necesiten serializar estructuras nuevas con `derive Json` antes de F5.

---

## A5 — MSVC

**Decisión:** se prueba Windows/MSVC desde **F1b** con un job de `windows-latest` en CI. Si un fallo concreto no se arregla en una semana, Windows se queda en el backend C hasta F5 (no bloquea la migración).

**Por qué:** el backend C++ no puede prometer Windows sin haberlo compilado nunca. Pero Windows no es necesario para el auto-hospedaje (Linux/macOS bastan) ni para F1–F3, así que no debe convertirse en un bloqueo del camino crítico.

**Coste medido:** 0 hoy (sin probar). Riesgo R2 del informe: MSVC no acepta varias cosas que g++/clang++ sí (designadores, `__attribute__`, statement expressions).

**Cuándo se aplica:** F1b (job) y F5 (retirada del backend C si MSVC no llega).

**Condición de revisión:** que F1b demuestre que MSVC compila el bundle con un conjunto pequeño de arreglos (entonces se sube a requisito de F4).

---

## A6 — Omens algebraicos

**Decisión:** `std::variant`, **sin `pengu::Variant` propio**.

**Por qué:** ya está validado con `scratch/audit_cpp/spike_variant.cpp`: los 4 patrones que emite el codegen (construcción, `std::get` por tipo, `std::visit` con overload set, `holds_alternative`) compilan con `-std=c++20 -fno-exceptions -fno-rtti` y 0 warnings. `std::get` inválido aborta (rc 134), pero el emisor solo lo usa detrás de un `judge` exhaustivo, así que el caso no se alcanza.

**Coste medido:** 4 tipos (`JsonValue`, `LinguaError`, `JsonRpcId`, `JsonRpcMessage`), 18 variantes con payload (6 caras: `string`/`list`/`map`), ~53 `judge` en `std/`. **En `src/` no hay ningún omen algebraico** (el AST del `psc` es `PsNode` plano), así que el auto-hospedaje no toca `std::variant` hasta F3.

**Cuándo se aplica:** F3.

**Condición de revisión:** que aparezca un caso de uso que `std::variant` no cubra con `-fno-exceptions` (p. ej. un payload que necesite `die` explícito y no quepa en el destructor del variant).

---

## A7 — `ritual new`

**Decisión:** los 9 `weave ritual new` **se quedan como están**. `born` es opcional: sin miembros especiales el tipo es agregado y se construye con `is with`. El emisor los mangla a `new_p` (colisión con el keyword de C++, sufijo `_p`).

**Por qué:** `ritual` **no se retira** en el dialecto (doc §6.6); lo retirado es `nasci`/`mori`/`imago`. Renombrar `new` a otra cosa no aporta nada y tocaría 9 sitios + sus llamadas solo por estética.

**Coste medido:** 0 (no hacer nada). Los otros 19 `ritual` tienen nombre propio (`with_capacity` 5, `from_str`, `cwd`, `from_text`, `from_bytes`, `from_source`, `with_block_size`, `null_value`, `bool_val`…).

**Cuándo se aplica:** nada que aplicar; el mangling ya está en F0.2.

**Condición de revisión:** que el doc cambie y retiren `ritual` (entonces sí habría que sustituir los 28).

---

## Qué queda cerrado con esto

- **F0 completo**: F0.1 (familia `--backend`), F0.2 (mangling de keywords C++), F0.3 (bundle C++ con 0 errores de `g++` + gate de CI), F0.4 (estas siete decisiones).
- **F1** arranca con el dialecto estricto (`-std=c++20`, sin `gnu++20`): convertir las 3.561 statement expressions a lambdas/IIFE, sustituir los `__attribute__`/`_Static_assert` que no sean portables y añadir `--dump-index-types` a la aceptación (F1, ~50 líneas en el checker).
