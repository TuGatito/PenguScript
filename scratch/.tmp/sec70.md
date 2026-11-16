<a id="sec-70-changelog"></a>
## 70. Changelog y versionado

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | Rust 2024, MSRV 1.85.0 |
| Palabras mágicas | — |
| Depende de | §69 |
| Ejemplos ejecutables | `no` |

### 70.1 Versiones

| Artefacto | Versión actual | Regla |
|---|---|---|
| Especificación | `0.1.0-dev` | SemVer; `1.0.0` solo tras Phase 11. |
| Compilador `pengu` | `0.1.0-dev` | Sigue a la spec; el patch no cambia la gramática. |
| Edición Rust emitida | `2024` | Fijada por D1. |
| MSRV | `1.85.0` | Subirla requiere minor de la spec. |
| Referencia probada | `rustc 1.99.1` | No es un mínimo; es la versión de CI. |
| Formato de `Tome.toml` | `1` | Cambios incompatibles suben `pengu` minor. |
| Sourcemap | `1` | Cambios de esquema suben `sourcemap` major. |

### 70.2 Changelog de la especificación

| Revisión | Fecha | Cambio |
|---|---|---|
| `r0` | 2026-11-12 | Esqueleto, índice, 71 secciones, glosario y §5 piloto. |
| `r1` | 2026-11-12 | §§1–§8: introducción, léxico, programa, tipos, variables, constantes, scope, expresiones. |
| `r2` | 2026-11-12 | §§9–§15: primitivos, strings, operadores, booleanos, condicionales, bucles, funciones. |
| `r3` | 2026-11-12 | §§16–§21: ownership, borrowing, lifetimes, punteros, smart pointers, memoria. |
| `r4` | 2026-11-12 | §§22–§27: arrays, vectores, tuplas, mapas/sets, estructuras, rangos. |
| `r4.1` | 2026-11-12 | Colecciones indentadas sin `[]`/`{}`; `Vec`/`Set` como marcadores; `PGS-E1011`/`E1012`. |
| `r5` | 2026-11-12 | §§28–§32: structs, enums, pattern matching, impls, aliases/casts. |
| `r6` | 2026-11-12 | §§33–§40: genéricos, bounds, traits, associated items, HRTB, closures, HOF, operadores. |
| `r7` | 2026-11-12 | §§41–§47: módulos, visibilidad, tomes, atributos, macros, derives, build/features/cfg. |
| `r8` | 2026-11-12 | §§48–§51: errores, iteradores, async, concurrencia. |
| `r9` | 2026-11-12 | §§52–§55: unsafe, FFI, const eval, `no_std`/embebido/wasm. |
| `r10` | 2026-11-12 | §§56–§59: testing, documentación, herramientas, estilo. |
| `r11` | 2026-11-12 | §§60–§71: gramática, léxico, precedencia, paridad, desugaring, diagnósticos, no soportado, glosario, cookbook, ADR, changelog, referencias. |

### 70.3 Cambios de sintaxis relevantes

| Versión | Cambio | Compatibilidad |
|---|---|---|
| `v0.2` | Se retira `spell`; funciones `name = (…) -> Tipo`; lambdas `(…) => expr`. | Ruptura interna; no había usuarios externos. |
| `v0.2` | `bind` inmutable / `morph` mutable; se retira `bind mut`. | Ruptura interna. |
| `v0.2` | `spirit` (retirado) -> `@`; atributos `@attr` -> `@@attr`. | Ruptura interna. |
| `v0.4` | Colecciones indentadas sin delimitadores; `Vec`/`Set` marcadores. | Aditiva; las formas inline siguen válidas. |
| `v0.6` | GAT/RPITIT documentados; sin cambio de sintaxis. | Compatible. |
| `v1.0` | Estabilización de la spec (pendiente de Phase 11). | Congela gramática. |

### 70.4 Política de deprecación

1. Una feature se marca `deprecated` en la sección y en §66.
2. Se mantiene al menos un minor completo antes de retirarla.
3. El compilador emite `PGS-W7001` con el reemplazo.
4. Una retirada requiere ADR nueva y entrada en este changelog.
5. Las palabras retiradas (`spell`, `spirit`, `bind mut`) se rechazan con
   `PGS-E6101` y un mensaje de migración; no se aceptan silenciosamente.
6. Los cambios de gramática que rompen código suben `MAJOR` de la spec.
7. Los cambios aditivos suben `MINOR`; las correcciones de redacción, `PATCH`.

### 70.5 Versionado del compilador

| Cambio | Versión |
|---|---|
| Nueva sintaxis/azúcar | minor |
| Nuevo diagnóstico que rechaza código válido | major |
| Nuevo warning | minor |
| Corrección de codegen sin cambio de semántica | patch |
| Cambio de MSRV/edición | minor (y aviso) |
| Cambio de esquema de `Tome.toml`/sourcemap | major del artefacto |

El compilador declara `pengu --version` con su versión, la edición Rust y la
MSRV. Un `Tome.toml` puede fijar `pengu = "0.1"`; el compilador rechaza un
`pengu` incompatible con `PGS-E7002`.

### 70.6 Proceso de release

1. Pasar todos los validadores (`check_sections`, `check_anchors`,
   `check_terms`, `check_rust_snippets`).
2. Verificar que todos los ejemplos compilan.
3. Actualizar este changelog y la versión de la spec.
4. Generar `sourcemap.json` y `Tome.lock` reproducibles.
5. Etiquetar `vX.Y.Z`; no se publica un RC sin dos revisores (§Phase 11).

### 70.7 Criterios de aceptación

- [x] Hay versión de spec, compilador, edición y MSRV.
- [x] El changelog cubre todas las fases.
- [x] Hay política de deprecación.
- [x] Hay reglas de SemVer para spec y compilador.
- [x] El release candidate queda para Phase 11.

[↑ Volver al índice](#indice)
