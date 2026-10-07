# 🗺️ ROADMAP 1.1 — después de PenguScript 1.0.0

> Este documento **reemplaza a `ROADMAP_2.0.md`** (movido con `git mv`, así que su
> historia de git se conserva). `ROADMAP_2.0.md` era el camino a 1.0 y está
> cerrado; lo que queda aquí es lo que 1.0 **no** hizo, con la medición que
> justificó diferirlo. El detalle item por item de cada fase cerrada vive en los
> `AUDIT_1.0_FASE*.md`, no se duplica aquí.
>
> **Nota sobre enlaces.** Los documentos escritos **antes** del renombrado (los
> `AUDIT_1.0_FASE*.md`, `AUDIT_1.0.md`, `CHANGELOG.md`, `CLEANUP_PLAN.md` y los
> docstrings de tests que citan el "Anexo C" o un número de item) siguen
> nombrando `ROADMAP_2.0.md`: son el registro de lo que se midió entonces y no se
> reescriben. Cualquier mención a `ROADMAP_2.0.md` en un documento histórico
> apunta a **este** fichero.

## Estado de partida (2026-10, tras la Fase 11)

- **`1.0.0` publicado en el árbol.** `VERSION` = `FALLBACK_VERSION` =
  `pengu_version.__version__` = `1.0.0`, los 26 `<MOD>_VERSION` de `std/` siguen al
  toolchain (política §19.0; `spark` es la única excepción, es revisión de API) y
  las 12 afirmaciones de versión de la documentación cuadran con `tests/test_version.py`.
- **Superficie congelada** en `docs/FREEZE.md`, comparada contra el árbol por
  `tests/test_freeze_manifest.py` (regla C1: introspección y ejecución, no texto).
- **El tag firmado `v1.0.0` es ⏸️ humano.** El entorno no tiene clave GPG
  (`git config user.signingkey` vacío). El comando exacto y el mecanismo de
  publicación están en `docs/RELEASE.md` y `docs/ANNOUNCEMENT_1.0.md` §Publicación.
- **Corpus ejecutable depositado**: 54 programas de compliance
  (`tests/compliance/`) y 10 de migración (`tests/migration/`), ambos con README
  normativo ("esto define la compatibilidad de 1.x") enlazados desde `LANGUAGE.md`
  §22 y `MIGRATION.md`.

## Convenciones (las mismas que en 2.0, siguen vigentes)

- **C1** — Ninguna propiedad se aprueba inspeccionando texto: se compila, se
  ejecuta o se mide.
- **C2** — Todo bloqueante tiene un test que **falla al revertir** el fix.
- **C3** — Toda afirmación de la documentación de release tiene un gate.
- **C4** — Ninguna entrada de usuario produce un traceback de Python.
- **C5** — Ningún cambio de sintaxis sin entrada en el corpus de compliance y de
  migración.
- **C6** — Las funciones nuevas en `pengu_parser/` no superan el umbral acordado y
  las existentes **no crecen**.
- **C7** — `ruff --select F821,E9` limpio (un nombre indefinido es un crash, no un
  nit de estilo).

## Candidatos a 1.1

Cada fila dice **qué falta** y **qué lo midió**. Ninguna se reabre sin volver a
correr el comando de medición: un diferido sin medición es una excusa.

| # | Item | Qué falta | Medición que lo justifica | Estimación |
|---|------|-----------|---------------------------|------------|
| **A** | **Borrow checking real** | Modelar tiempos de vida y periodos de préstamo | Cambio de análisis, no de sintaxis; puede invalidar código válido. Es el "holy grail" de AUDIT §9.11 | XL (feature estrella de 1.1) |
| **B** | **Fugas de stdlib bajo LeakSanitizer** (F8-N2 / 8.19) | Cambio de propiedad de memoria en `std/*.pengu` / `pengu_codegen.py` | Trazas en `std/invoke.pengu:105/292` (`pengu_list_new`, `pengu_map_new_owned`); el suite bajo ASan acumula **164 fallos al 92 %** | L |
| **C** | **`--strict-c99` genera C inválido y miscompila** (F8-N4/N4a) | Hoisting de comprehensions y el caso de `std/loom.pengu:347` | 18 de 56 programas con 13 errores duros (`'k' undeclared`) y 1 que compila y aborta (`Index out of bounds`) mientras el build por defecto sale rc 0. **18 + 1 filas en `xfail(strict=True)`** | L |
| **D** | **`array of T` sin tamaño → Traceback** (F8-N6) | Capturar `SemanticError` de codegen en el CLI | El ejemplo de `LANGUAGE.md` §5.0 hace que `check` pase y `build` lance Traceback: **viola C4**. Pin `xfail(strict=True)` | S |
| **E** | **Contrato del CLI en rutas de entrada** (F8-N7) | `time`/`fmt` con archivo inexistente; `build`/`test`/`doc --entry` inexistente devuelven rc 0 | Medido: los dos primeros lanzan Traceback (C4); los tres últimos construyen la entrada por defecto y **salen 0**. 5 filas `xfail(strict=True)` | S–M |
| **F** | **`compute_config_hash()` ignora `PENGU_NO_DCE`** (F8-N9) | Incluir la variable en la clave de caché | Mismo origen: 3254 B con DCE y 16047 B sin DCE dan la **misma clave** `8c5f7a759af9810d`; el rebuild devuelve `is_cached=True` con el bundle obsoleto | S |
| **G** | **Array a variádica C: referencia colgante** (F8-N10) | Copia con duración suficiente al pasar a `...` | ASan: `stack-use-after-scope ... in sum_args` en `tests/compliance/020-declare-extern-c.pengu:17`. Sin ASan el valor sale correcto, por eso solo lo ve el job de sanitizers | M |
| **H** | **`-DPENGU_FRAME_TRACE=0`** (F10-N3) | Verificar que no reaparezca | Se arregló en Fase 10 (el comando documentado no compilaba); es un ratchet, no trabajo nuevo | S (verificación) |
| **I** | **`pengu migrate`** (4.14b) | El rewriter `and` → `,` con información de tipos y `--dry-run` | El corpus (`tests/migration/`, **8 de 10 pasan; 2 fallan a propósito** con `E0000`/`E0005`, ver `EXPECTED.json`) y `MIGRATION.md` ya existen: sus dos entradas pendientes están servidas | M–L |
| **J** | **Unificación `loom` ∩ `tally`** (6.5b) | Alias `@deprecated` con ventana de dos releases | 15 nombres públicos compartidos, **0 con la misma firma**: `loom.mean([1,2])==1.5` y `tally.mean([1,2])==1`; `loom.mode([])==none` y `tally.mode([])==0`. No hay duplicación que resolver, hay dos filosofías | M (depende de la ventana de deprecación) |
| **K** | **`compass.cp_*` → `_cp_*`** (6.11b) | Decidir si se renombran o se promueven a espacio de nombres documentado | 32 helpers `cp_*`, **0 referencias externas** en `std/`, `tests/`, `benches/`, `docs/`; ~169 usos internos en `compass.pengu`. El `CHANGELOG` dice que la separación es deliberada | S–M |
| **L** | **Nombres públicos duplicados entre módulos** (7.6b) | Unificar los divergentes | **49** nombres públicos repetidos (10 son reexports `assert*`); no 15 — eso era solo `loom`∩`tally` | M–L |
| **M** | **Traducción pendiente de la referencia** (7.14b) | Traducir `LANGUAGE_Spanish.md` §5.0/§19.0/§19.1.1/§23 | ≈279 líneas, 5 bloques. El inglés es canónico; el ratchet bidireccional ya fija el techo y la lista | M |
| **N** | **Semantic tokens por rango y delta** (5.9) | `TEXT_DOCUMENT_SEMANTIC_TOKENS_RANGE` + `SemanticTokensDelta` con caché `uri -> (hash, resultId, data)` | `semanticTokens/full` tarda **151 ms** en `std/loom.pengu` y **1 817 ms** en un sintético de 10 000 líneas; el coste solo se ve por encima de ~2 000 líneas, que en el repo es código **generado** | M |
| **O** | **Associated types** (`alias Item` en `concept`) | Resolución en bounds; hoy se hace con `shard T and U` | Feature de lenguaje mediana. Mientras no exista, el ejemplo **retirado** de la doc no vuelve | M |
| **P** | **Backtracking completo en deps** | Resolvedor con retroceso | No hay evidencia de fallo: el resolvedor actual maneja los 52 módulos y las deps locales. Añadirlo es especulativo | solo si aparece un caso real |
| **Q** | **Migración completa de `Result` en la stdlib** | Unificar `write_file` + `write_file_result` | La API de doble vía funciona; forzar la migración rompería los 174 tests de std y a los usuarios. Requiere deprecación larga | L |
| **R** | **`derive` para el 100 % de los concepts** | Cubrir los derivables restantes | `Par`/`Ordo` cubren los casos reales; el resto no tiene demanda medida. La matriz se documenta en §2.8 | S–M |
| **S** | **`pengu repl`** | Estado incremental en el compilador | `pengu eval` cubre la necesidad puntual; hoy el `inferrer` se reconstruye por llamada | M |
| **T** | **Estabilidad de los tarballs de GitHub** (F9-N5) | Migrar los 7 `sha256` que fijan `/archive/refs/tags/…` a assets de release o espejo propio | GitHub puede regenerar el archivo (ya cambió el envoltorio gzip una vez). Un cambio upstream ahora **aborta** el build; `python scripts/extern_digests.py --update` es la mitigación manual | S |
| **U** | **Notarización macOS** (9.9, reivindicación **retirada**) | `notarytool` + cuenta de desarrollador de Apple | Sin cuenta, `spctl --assess` **no se cumple y no se afirma**. Lo gateado es `codesign --verify --strict`; `release-verify.yml` publica la salida real de `spctl` | 1.1 solo si hay cuenta |
| **V** | **Cobertura `clang -Weverything`** (389 warnings) | Nada | 267 son `-Wunsafe-buffer-usage`, preferencia de estilo de una toolchain, no un bug. Se mantiene `-Wall -Wextra -Werror` | No planificado |
| **W** | **Diferidos sin fecha de features mayores** | Async/await nativo (1.2+), closures con captura (1.2+), macros de AST (1.3+), dynamic dispatch/vtable (1.3+ solo con demanda), reflection/RTTI (no planificado), playground WASM (1.3+) | Cada uno rompe una decisión de diseño central (zero-overhead de los concepts, funciones C `static` de nivel superior, C puro) o requiere un target que no existe | — |

## Criterios de reapertura (los que exigen medición)

Estos cuatro se difirieron **con** un criterio explícito de reapertura. Reabrirlos
sin cumplirlo es saltarse el roadmap:

- **I — `pengu migrate`:** las dos entradas que faltaban (corpus y `MIGRATION.md`)
  ya están. Criterio: implementar `--dry-run` y verificarlo contra el corpus.
- **J/K — unificación de superficie `std`:** criterio común — primero la **ventana
  real de `@deprecated`** (hoy la stdlib no aplica atributos `@deprecated` reales,
  así que la migración no puede avisar a nadie). Sin aviso previo, renombrar 32
  símbolos públicos es romper sin transición.
- **N — semantic tokens:** criterio de reapertura — medir `semanticTokens/full`
  > 300 ms en un fichero que un usuario **edite de verdad** (no generado), o que
  el cliente reporte lag al escribir.
- **C — `--strict-c99`:** las **18 + 1 filas `xfail(strict=True)`** pasan a
  `xpass` el día que se arregle; el gate falla solo, no hay que recordarlo.

## Hallazgos de la Fase 11 (`F11-N*`)

Ninguno es una feature: son refutaciones y trampas medidas al publicar. El detalle
está en `AUDIT_1.0_FASE11.md`.

| Código | Hallazgo | Estado |
|--------|----------|--------|
| **F11-N1** | `tests/compliance/README.md` **no existía**: el item 11.6 pedía "añadir cabecera normativa", pero el fichero no estaba. Se **creó** (lo que existe y se ejecuta es `corpus.json` + `run_all.py` + `EXPECTED.md`) | Cerrado en la fase |
| **F11-N2** | `CONTRIBUTING.md` seguía afirmando **"Current version: 0.16.0, in beta"** y **ninguna** de las 12 afirmaciones gateadas lo cubría: la deriva real sobrevivió a la Fase 10, que declaró "0 deriva de versión" midiendo solo sus 6 ficheros | Cerrado + gate propuesto abajo |
| **F11-N3** | Promover el `CHANGELOG` a `[1.0.0]` rompe `tests/test_ci_workflows.py::test_release_version_skips_unreleased`, que fijaba `v0.16.0` a mano. No es un fallo del mecanismo: es un test que no seguía a `VERSION` | Cerrado (el test ahora deriva de `VERSION`) |
| **F11-N4** | El **entorno no tiene clave GPG** (`git config user.signingkey` vacío): 11.3 no es automatizable aquí. No es un defecto del repo; se registra como ⏸️ humano | ⏸️ humano |
| **F11-N5** | `SECURITY.md` mantenía una fila `0.16.x` descrita como "con fixes hasta que salga `1.0.0`" y una mención `1.0.0-rc1` como "current pre-release". Publicado 1.0.0, ambas frases eran falsas y el ratchet de tokens obsoletos no las cubría | Cerrado (tabla y `JUSTIFIED_TOKENS` actualizados) |

**Candidato nuevo para 1.1 (de F11-N2):** gate de versión para `CONTRIBUTING.md`
y para el *badge* de `README.md`. Hoy `CURRENT_VERSION_CLAIMS` cubre 6 ficheros
normativos; la afirmación de versión del `CONTRIBUTING.md` y del badge del README
no están en la tabla, y por eso una de ellas llevaba **tres releases** de retraso.
Añadirlas a `CURRENT_VERSION_CLAIMS` es barato y cierra la clase de bug — se deja
como primer item de 1.1 para no tocar la tabla de gates el día del release
(regla: ningún gate se estrena el día que se publica).

## Qué cerró 1.0 (índice, sin duplicar)

Los 11 bloqueantes de `AUDIT_1.0.md` §20.1 quedaron cerrados con un item y un test
que falla al revertir; el detalle está en los audits de fase y en `CHANGELOG.md`
§`[1.0.0]`:

| Fase | Nombre | Audit |
|------|--------|-------|
| 0 | Limpieza y consolidación | — (ver `CLEANUP_PLAN.md`) |
| 1 | Correctitud del compilador | `AUDIT_1.0_FASE1.md` |
| 2 | Completar 1.0 del lenguaje | `AUDIT_1.0_FASE2.md` |
| 3 | Runtime y ABI | `AUDIT_1.0_FASE3.md` |
| 4 | CLI | (cerrado; ver `CHANGELOG.md`) |
| 5 | LSP | (cerrado; ver `CHANGELOG.md`) |
| 6 | stdlib | `AUDIT_1.0_FASE6.md` |
| 7 | Style Guide y Docs | `AUDIT_1.0_FASE7.md` |
| 8 | Tests | `AUDIT_1.0_FASE8.md` |
| 9 | Herramientas de release | `AUDIT_1.0_FASE9.md` |
| 10 | Congelación y RC | `AUDIT_1.0_FASE10.md` |
| 11 | 1.0.0 | `AUDIT_1.0_FASE11.md` |

### Anexo — Matriz bloqueante → fase → test de regresión

El contrato de la auditoría con el roadmap. Sigue siendo la lista contra la que se
comprueba que un bloqueante **no** reabre.

| Bloqueante | Severidad | Fase / item | Test de regresión | Comando que debe pasar |
|-----------|-----------|-------------|-------------------|------------------------|
| **B1** `check <archivo>` ignora el archivo | 🔴 | 1.2 | `tests/test_cli_contract.py::test_check_positional` | `pengu check roto.pengu; echo $?` → `1` |
| **B2** entry inexistente devuelve ok | 🔴 | 1.3 | `tests/test_cli_contract.py::test_check_missing_entry` | `cd /tmp/vacio && pengu check; echo $?` → ≠0 |
| **B3** `parse_known_args` descarta flags | 🔴 | 1.1 | `tests/test_cli_contract.py::test_unknown_flag` | `pengu check --bogus; echo $?` → `2` |
| **B4** `fmt --indent` corrompe | 🔴 | 4.1, 4.2 | `tests/test_properties.py::test_fmt_idempotent`, `::test_fmt_preserves_semantics` | `pengu fmt --check std/` → 0 cambios |
| **B5** `--strict-c99` no compila | 🔴 | 3.2, 3.3 | `tests/test_c99_portability.py::test_strict_mode_over_std_programs` | `gcc -std=c99 -pedantic-errors` sobre los 56 bundles → 0 errores |
| **B6** `node`→`target_node` (`NameError`) | 🔴 | 1.4 | `tests/test_module_qualified_types.py::test_private_symbol_access_raises_E0043` | programa con `lib._privado` → `E0043`, no traceback |
| **B7** tipos cualificados pierden campos | 🔴 | 1.5, 1.6 | `tests/test_module_qualified_types.py::test_dep_qualified_rune_fields` | programa de 3 módulos compila; `raymath.Vector2` funciona |
| **B8** runtime `.c` no compila sin supresión | 🟠 | 3.1 | `tests/test_runtime_clean_compile.py` | `gcc -Wall -Wextra -c pengu_parser/pengu_runtime.c` → 0 errores |
| **B9** job de sanitizers rojo | 🔴 | 8.2 | (workflow) | El job `sanitizers` pasa en CI |
| **B10** gates por texto | 🔴 | 8.1 | Los 4 tests reescritos | `grep -rn 'not in bundle\|not in result' tests/` → 0 gates por texto |
| **B11** 188 conflictos shift/reduce | 🟠 | 2.4, 2.4b | `tests/test_precedence.py::test_associativity_and_precedence` | `Lark(GRAMMAR, parser='lalr', strict=True)` sin excepción; los 9 árboles de §1.1 intactos |

## Riesgos de 1.1

- **Riesgo:** 1.1 se convierte en un cajón de sastre donde todo "importante" entra.
  **Mitigación:** cada entrada de la tabla de candidatos tiene **una medición** y una
  estimación; lo que no la tenga se devuelve a discusión.
- **Riesgo:** las unificaciones de superficie (`loom`/`tally`, `compass.cp_*`,
  nombres duplicados) rompen código de 1.0 sin aviso. **Mitigación:** ninguna se
  hace antes de que exista la ventana real de `@deprecated`; el orden es
  deprecación → aviso `W0006` → retirada.
- **Riesgo:** los arreglos de memoria (B, C, G) tocan codegen y propiedad de
  memoria a la vez. **Mitigación:** hacerlos con el job de sanitizers verde como
  red y una fila `xfail(strict=True)` por caso, como ya están pinneados.
