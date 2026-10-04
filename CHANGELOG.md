# Changelog
 
All notable changes to PenguScript will be documented in this file.


## [Unreleased] — FASE 4: Completar CLI

> Hace que el CLI **haga lo que su ayuda dice**: sin flags que no hacen nada,
> sin pérdida de datos, con errores formateados de forma consistente y con el
> contrato `--json` completo.

### 🔴 Fixed — B4 (item 4.1): `pengu fmt --indent N` corrompía la indentación

`format_pengu_source` (`pengu_lsp/formatting.py`) usaba el `tab_size` de
**destino** para *decodificar* la indentación del **fuente**
(`indent_level = leading_spaces // tab_size`). Cuando la unidad del fuente no
coincidía con la pedida, cada nivel se calculaba mal: un fuente de 2 espacios
con `--indent 4` colapsaba a columna 0 (`2 // 4 == 0`), y uno de 4 espacios con
`--indent 2` duplicaba la profundidad (`4 // 2 == 2`). El archivo resultante ya
no parseaba —`pengu check` → `Syntax error: unexpected 'var'`— y `pengu fmt`
salía con **exit 0**: corrupción destructiva y silenciosa.

La unidad del fuente es una propiedad del archivo, no de la invocación, así que
ahora se detecta del propio texto (el menor tramo no nulo de espacios iniciales;
un tab cuenta como un nivel) y `tab_size` se usa **solo** para re-codificar la
salida. Esto arregla a la vez el CLI y el formateo del LSP
(`textDocument/formatting`), que comparten el mismo módulo.

Medido antes del fix: `--indent 4` sobre 2 espacios colapsaba `var`/`if` a
columna 0. Después: la estructura se conserva en ambos sentidos (2↔4), tabs y
fuentes no idiomáticos se normalizan sin colapsar, `fmt(fmt(x)) == fmt(x)` y la
salida **sigue siendo PenguScript válido** (`pengu check` → 0) en los casos
medidos. `tests/test_fmt_indent.py` (24 casos, incluido el gate de compilación
del resultado). El test `TestFmt::test_format_preserves_clean_indentation`
fijaba por accidente la conducta antigua (`4 espacios con tab_size=2` no
cambiaba) y se ha reescrito para fijar la idempotencia real.

Nota: el formateo *on-type* del editor (`on_type_formatting`,
`pengu_lsp/server.py:1804`) usa una ruta propia (`_reindent`) y **no** pasa por
`format_pengu_source`; no queda cubierto por este fix y mantiene su
comportamiento anterior.

### 🟠 Fixed — A7 (item 4.2): `pengu fmt` defaulteaba a 2 espacios, no 4

El default de `--indent` era **2**, mientras que la guía de estilo y toda la
stdlib usan **4**. Consecuencia medida antes del cambio: `pengu fmt --check std/`
reportaba **27 archivos** que cambiarían, todos por reindentación sin cambio
semántico (4 → 2). Ahora el default es **4** (el CLI lo anuncia:
`--indent INDENT Spaces per indentation level (default: 4)`), y `--indent N`
sigue permitiendo el override.

`pengu bind` emitía además **2 espacios fijos** en su plantilla, así que los
bindings `.d.pengu` que genera el propio tool no pasaban su
`pengu fmt --check`: 13 de los 25 `.d.pengu` de `std/` seguían marcándose tras
cambiar el default. El generador emite ahora 4 espacios y los 13 bindings
afectados se reindentaron (sólo whitespace: `git diff -w` → 0 líneas; 1189
líneas cambiadas, 1189/1189 de ellas de indentación), de modo que
`pengu fmt --check std/` es **idempotente sobre todo `std/`** (0 archivos).
`tests/test_fmt_bind_indent.py` (5 casos: el binding generado pasa
`pengu fmt --check`, sus `rune`/`omen` van a 4, es PenguScript válido, y `std/`
entero queda limpio).

Nota medida: `regen_std_bindings.py --write` **no** se usó para esta
reindentación. Medido con `--check`: de los 13 archivos regenerables, 7 ganarían
declaraciones nuevas (`typis` +51, `imago` +7, `raygui` +6, `raymath` +5,
`stb_image_resize2` +5, `datastructura` +4, `pactum` +3), es decir la
regeneración mezclaría un cambio de contenido con la reindentación. Ésta se hizo
con `pengu fmt --indent 4` (la herramienta prevista para ello) y se verificó con
`git diff -w` por archivo (0 líneas no-whitespace) y
`pengu check --entry std/<mod>.d.pengu` (13/13 ok). Alinear esos 7 archivos con
su cabecera actual es trabajo aparte, con su propia medición.


## [Unreleased] — FASE 3: Runtime y ABI

> Cierra el runtime y la ABI: C99 legal **sin flags de supresión**, portabilidad
> declarada verificable, ABI comprobable end-to-end, y cada afirmación documental
> respaldada por un gate que **compila o ejecuta** (regla C1).

### 🔴 Fixed — Bloqueantes

- **B8 — el `.c` del runtime no era C válido.** `pengu_parser/pengu_runtime.c`
  incluye `<mbedtls/private/*.h>`, cuyas declaraciones mbedtls protege tras
  `MBEDTLS_ALLOW_PRIVATE_ACCESS`. `build_runtime.py` lo compensaba con
  `-Wno-incompatible-pointer-types -Wno-implicit-function-declaration`, que
  **suprimían los 24 errores de declaración implícita** de
  `mbedtls_md5`/`sha1`/`sha256`/`sha512`: nunca aparecían en el log de build, y
  `cl.exe` rechaza ambos flags, lo que hacía **imposible cualquier build MSVC**.
  Ahora `build_pengu_runtime` pasa `-DMBEDTLS_ALLOW_PRIVATE_ACCESS` y **ningún
  `-Wno-*`**. `gcc -std=c11 -Wall -Wextra` sobre la unidad → **0 errores, 0
  warnings**. (Los otros cinco sitios con `-Wno-*` en `build_runtime.py`
  compilan librerías de terceros y quedan fuera de alcance.)

- **`-Wmacro-redefined` en el runtime.** Los `#define` de `PCRE2_STATIC`,
  `LIBXML_STATIC` y `CURL_STATICLIB` en `pengu_runtime.c` se redefinían porque
  el build los pasa también por línea de órdenes, produciendo 3 warnings.
  Ahora están guardados con `#ifndef` y la unidad compila limpia **con y sin**
  los defines en la línea de órdenes.

- **Instalación atómica del crash handler.** El handler se instalaba con un
  `static volatile int` y un *check-then-set*, que es una carrera de datos (dos
  hilos pueden observar `0` y ejecutar la instalación ambos; `volatile` no ordena
  nada entre hilos). Además `pengu_frame_push()` lo llamaba **en cada empujón de
  frame**, en el camino caliente. Ahora usa `pthread_once` (POSIX) /
  `InitOnceExecuteOnce` (Windows), y la instalación se hace **una sola vez al
  arranque** desde el `main` generado. El header sigue compilando con
  `-Wall -Wextra -Werror`.

- **⏸️ TCC y `__auto_type` — fix revertido.** El cambio `__auto_type` →
  `__typeof__` eliminaba los 46 fallos de tcc (61/61 bundles compilaban), pero
  **`__typeof__` no es un renombrado**: conserva el tipo exacto de la expresión
  incluidos los cualificadores de nivel superior, mientras que `__auto_type` aplica
  la conversión de lvalue. Eso cambió el **objetivo de asignación** generado en
  `set r at 0 at 1 is 42` y rompió **cinco** tests que pasan en el commit base
  (`test_p2_review_fixes::test_chained_set_index_through_ref_to_array` y los cuatro
  de `test_regression_0_13_1*`). **Revertido**; ver `AUDIT_1.0_FASE3.md` §11 y §13.
  Diferido a 1.1. Tras la reversión: **2499 passed, 0 failed**.

### 🔴 Fixed — Cierre de la Fase 3 (items 3.5, 3.6, 3.7, 3.9, 3.11 y 3.13)

- **3.5 — la ABI es verificable, y `SECURITY.md` deja de sobreafirmar.**
  `pengu_abi_version()` se exporta como símbolo real desde
  `pengu_parser/pengu_runtime.c` (nunca inline en el header):
  `nm build/lib/libpengu_runtime.a | grep pengu_abi_version` → **1 símbolo (T)**.
  Cualquier consumidor que enlace el archivo y referencie el símbolo falla en
  **link** si el `.a` es anterior, en lugar de reinterpretar campos en silencio.
  El `_Static_assert` del bundle sigue cubriendo codegen-vs-header; ambos checks
  son complementarios. **No** se emite una referencia obligatoria desde cada
  bundle: se intentó primero y rompía `pengu build` en todo proyecto recién
  creado (`pengu init` no enlaza `libpengu_runtime.a`, el bundle es header-only),
  así que hacerla obligatoria es trabajo de Fase 4. `SECURITY.md` y `docs/ABI.md`
  dicen ahora exactamente qué se garantiza y qué no. Ver `AUDIT_1.0_FASE3.md` §14.

- **3.6 — `SIGFPE`/`SIGILL`/`SIGBUS` vuelcan la traza.** El handler instalaba solo
  `SIGSEGV`/`SIGABRT` con `signal()`. Una división entera por cero mataba el
  proceso sin mensaje ni frame, y `pengu eval "1/0"` salía con **248** (el CLI
  convertía el código de retorno negativo `-8` en `sys.exit(-8)`). Ahora usa
  `sigaction` —con `SA_RESETHAND`, para no recursar si el propio handler falla— e
  instala también `SIGFPE`, `SIGILL` y `SIGBUS`. `pengu eval "1/0"` imprime
  `[PENGU CRASH] fatal signal (signal/code 8)` con la traza y sale con **136**.

- **3.7 — el volcado de crash es async-signal-safe de verdad.**
  `pengu_dump_frame_stack` se construía con `snprintf`, que POSIX no lista como
  async-signal-safe, mientras `LANGUAGE.md` y este CHANGELOG afirmaban lo
  contrario (el propio header lo admitía en un comentario). Ahora formatea con
  primitivas propias —aritmética de punteros y división entera— y solo usa
  `write(2)`/`_exit()`; `pengu_bounds_panic` también. Medido sobre el artefacto
  compilado, el cierre de enlace del camino de crash referencia únicamente
  `_exit`, `write`, `signal`, `pthread_once` y el guardián de pila del compilador:
  ningún `snprintf`, `malloc` ni función de stdio. La afirmación es ahora
  verdadera en lugar de retirada.

- **3.9 — un solo formato de float en todas las vías.** `print x` daba
  `3.140000` (builtin del codegen), `(x to string)` daba `3.14`
  (`pengu_string_from_float`) y `"{x}"` daba `3.140000`
  (`pengu_string_format_ex`): tres funciones, dos formatos, según qué camino
  formateara el valor. Los tres usan ya `%g`. La nota de `LANGUAGE.md` que
  documentaba la divergencia como intencionada describía un accidente de
  implementación y se ha corregido (también en `LANGUAGE_Spanish.md`).

- **3.11 — `docs/ABI.md`.** Documento nuevo: qué cubre `PENGU_ABI_VERSION`, qué
  cambios la bumpean (cualquier cambio de layout —incluido añadir un campo al
  final, porque cambia `sizeof`— y cualquier cambio de firma de una función
  `pengu_*` exportada), qué no (añadir funciones nuevas), y cómo se verifica.

- **3.13 (hallazgo nuevo de esta sesión) — la traza atribuía el fallo al
  llamador.** El codegen emitía `pengu_frame_pop(); return <expr>;`, es decir
  retiraba el frame **antes** de evaluar la expresión de retorno. Un `return a / b`
  con división por cero se reportaba como `at pengu_main` —el llamador— en vez de
  `at divide`, y una cadena `return calling f` producía un solo frame. Ahora la
  expresión se evalúa en un temporal antes del `pop`. Esto es lo que hace
  verdadera la afirmación "escribe la pila de llamadas exacta" de `LANGUAGE.md`.

### ⏸️ Diferido — `--strict-c99` NO es un gate de portabilidad en 0.16.0

- **B5 (item 3.2) — `--strict-c99` no compila en programas que importan `std`.**
  Medido: **34 de 61** programas de `tests/std_programs/` fallan
  `gcc -std=c99 -pedantic-errors`, por tres causas independientes: **16** por el
  hoisting del índice fuera del bucle que declara su operando (`'k' undeclared`),
  **15** por statement-expressions `({...})` que quedan en el bundle estricto, y
  **3** por cualificadores/casts. Reproducción mínima de 4 líneas en
  `AUDIT_1.0_FASE3.md` §7.

  **Se retira la etiqueta de "gate de portabilidad"**: `RELEASE_CHECKLIST.md`
  deja de listarlo como gate y `LANGUAGE.md` pierde la afirmación —falsa— de que
  el bundle "compiles with `-std=c99 -pedantic-errors`". Ambas se sustituyen por
  la medición.

  Diferido a **1.1**. Consecuencias: el criterio #2 de "done" de la Fase 3 queda
  sin cumplir, y **B10 (Fase 8) sigue bloqueado**, porque su gate
  `tests/test_cli_strict_c99.py` no puede pasar mientras esto no se arregle.

### ⏸️ Diferido a 1.1 — con medición

- **3.3 — los 104 statement-expressions `({...})` en modo estricto.** Sigue sin
  hacerse, y **con medición, no por falta de tiempo**: está acoplado a 3.2 (B5)
  —eliminar `({...})` sin arreglar antes el *hoisting* que saca el índice del
  bucle que declara su operando **no compila**— y es el único item **XL** del
  roadmap. Medición en `AUDIT_1.0_FASE3.md` §6–§7 (34/61 programas de
  `tests/std_programs/` fallan `-std=c99 -pedantic-errors`) y registro en
  `ROADMAP_2.0.md` Fase 3 item 3.3.

- **3.10 — 55 símbolos del runtime sin Doxygen.** Cosmético y no bloqueante:
  ninguna afirmación de comportamiento depende de ello, y encaja mejor en la
  Fase 7 (documentación), donde el catálogo de símbolos se genera de una vez.
  Registrado en `ROADMAP_2.0.md` Fase 3 item 3.10.


## [Unreleased] — CI/CD: auditoría de GitHub Actions (Fase 7)

> Verificación previa contra los 4 workflows reales. **2 hallazgos de la
> auditoría resultaron falsos** en su formulación (B y parte de E/`bench.sh`) y
> se documentan abajo. Todo lo demás se confirmó y se corrigió.

### 🔴 Fixed — Bloqueantes

- **Race condition de doble release (bloqueante).** `ci.yml` creaba el tag **y**
  publicaba la GitHub Release, mientras `release.yml` (disparado por el push del
  tag) publicaba **la misma** release: dos workflows compitiendo por el mismo
  tag. Ahora `ci.yml` **solo crea el tag** y `release.yml` es el **único** que
  publica. Un test lo fija: exactamente un workflow contiene `gh release create`.
- **Tag `vUnreleased` (bloqueante, bug real y activo).** El extractor de versión
  usaba `re.search(r"^##\s*\[([^\]]+)\]")`, que toma la **primera** cabecera
  `## [...]`. Desde que el CHANGELOG tiene cabeceras
  `## [Unreleased] — FASE 5/6` **antes** de la versión real, el siguiente push a
  `main` habría creado y empujado un tag **`vUnreleased`**. Se sustituye por
  `scripts/release_version.py`, compartido por el tag y las notas, que salta
  `[Unreleased]`, falla con mensaje claro si no hay versión publicada y detecta
  prereleases. **Hallazgo adicional del propio script:** su primer regex no
  reconocía el **guion largo (`—`)** de las cabeceras, así que ni siquiera veía
  las secciones `[Unreleased]`; corregido y cubierto con test.
- **`bench.yml` en Windows.** Se añade `shell: bash` a los steps con `date`,
  `tee` y `[ -n ]`. **Refutación honesta:** el workflow **no incluía Windows** en
  su matriz, así que no estaba roto hoy; el arreglo es endurecimiento para que
  añadir Windows no lo rompa en silencio (y se documenta por qué Windows queda
  fuera: los números los domina el antivirus).
- **`cc` hardcodeado en el step de ABI layout (rompía Windows).** `cc` no existe
  en los runners de Windows. Ahora el shell decide el compilador según
  `$RUNNER_OS` (MinGW `gcc` en Windows, `${CC:-cc}` en el resto). Era un bug
  introducido en la Fase 5.

### 🟠 Fixed — Altos

- **`timeout-minutes` en todos los jobs** (el defecto de GitHub son 6 h): CI 60,
  release 90, bench 90, fuzz **780** (cubre el presupuesto de 12 h), sanitizers
  120/90, tag 10, VSIX 20.
- **`concurrency` en los 5 workflows**, con `cancel-in-progress: false` en
  `release.yml` y `bench.yml` (una release o una serie de benchmarks a medias es
  peor que una superseded).
- **`permissions` con mínimo privilegio**: `contents: read` a nivel de workflow y
  `contents: write` **solo** en el job de tag/release (antes era `write` para
  todos los steps, incluidos setup e install).
- **Caché del runtime** (`build/lib`, `build/include`, `build/tcc-dist`,
  `extern/`) con clave por SO+arquitectura y hash de `extern_manifest.py` /
  `build_runtime.py` / `requirements.txt`. Se cachean **solo esos directorios**,
  nunca `build/` entero (que contiene `bundle.c` y binarios).
- **Setup compartido** en `.github/actions/setup-pengu` (action compuesta): deps
  nativas por SO, deps de Python, caché y `build_runtime.py`. Elimina ~60 líneas
  duplicadas por workflow y **arregla que `bench.yml` no instalaba las
  dependencias de Linux** (hacía el benchmark menos representativo que CI).
- **Sin acción de terceros.** `softprops/action-gh-release@v2` (tag móvil, código
  ajeno con `contents: write`) se sustituye por la **CLI `gh`** de primera parte
  ya presente en los runners: no hay SHA que pinnear y se gana control sobre
  notas, checksums y `prerelease`. Un test prohíbe acciones fuera de
  `actions/`/`github/` y de `.github/actions/`.
- **VSIX una sola vez**: era idéntico en los 3 SO de la matriz; ahora hay un job
  dedicado y los artifacts se descargan como uno solo.
- **Config muerta eliminada** (`artifact_cmd`) y **step redundante** eliminado
  (el "fast fail on core reviews" ejecutaba los mismos ficheros que la suite
  completa).

### 🟡 Fixed — Integridad de releases

- **`SHA256SUMS.txt`** generado y publicado con la release, y validación de que
  hay al menos 3 assets antes de publicar (un glob vacío hacía fallar `gh` de
  forma críptica).
- **`prerelease` automático** para tags con `-rc`/`-beta`/`-alpha` (antes todo
  salía como estable, rompiendo el flujo RC de la Fase 7).
- **Notas desde el CHANGELOG** (`--notes-file`), no notas autogeneradas, y
  verificación de que el tag coincide con la primera versión publicada del
  CHANGELOG.
- **Descarga de TinyCC verificada**: `PENGU_TCC_SHA256` debe coincidir o el step
  falla en vez de empaquetar un binario de un mirror de terceros sin comprobar.
- **`workflow_dispatch` con tag real**: el input `version` se ignoraba y se
  publicaba contra `github.ref`; ahora se resuelve y se exige que el tag exista.

### 🟢 Added — Workflows y automatización

- **`sanitizers.yml`**: ASan+UBSan sobre **toda la suite** y sobre los programas
  de `std/`, más un job de **valgrind**. Para que sea real se añadió soporte de
  `PENGU_CFLAGS`/`PENGU_LDFLAGS` en `pengu_project.py` **y** en
  `tests/conftest.py`, y ambos entran en la **clave de caché** (si no, una build
  con sanitizers podría reutilizar un binario normal). Verificado localmente:
  `-fsanitize=address,undefined` compila y el programa termina sin fugas ni UB.
- **`PENGU_TEST_VALGRIND=1`** en `conftest`: prefija la ejecución con valgrind y
  **falla** si valgrind no está, en vez de fingir que lo usa.
- **`dependabot.yml`** (github-actions, pip, npm).
- **Gate CI/CD (FASE 7)** en `ci.yml` que ejecuta `tests/test_ci_workflows.py`:
  49 aserciones estáticas sobre los YAML (un solo publicador de releases,
  timeouts, permisos, concurrencia, `shell: bash`, caché sin `build/` entero,
  checksums, prerelease, VSIX único, sin acciones de terceros) más ejecuciones
  reales del extractor de versión.

### 🐛 Known issue (tracked, not hidden)

- **Fuga en las APIs legacy de contenedores bajo ASan.** La nueva verificación
  con `-fsanitize=address` sobre la suite encontró:
  `AddressSanitizer: 1033 byte(s) leaked in 5 allocation(s)`.
  Caracterización: un `list of int` mínimo (push + iterar + auto-banish) está
  **limpio**, así que el modelo de propiedad/auto-banish **no** es la causa; la
  fuga está en los caminos legacy que ejercita
  `tests/test_std_backward_compat.py` (`coven.SetString` y
  `map of string to int`). No hay error de memoria (ni use-after-free, ni
  overflow, ni UB): es "almacenamiento no liberado antes de salir". Se registra
  igualmente porque el proyecto afirma "cero fugas en programas libres de
  unsafe/FFI".
  - **No se oculta**: el workflow de sanitizers **des-selecciona ese test por
    nombre** (no desactiva `detect_leaks`), y `tests/test_known_issues.py`
    reproduce el caso y documenta el estado con `xfail`, de modo que el día que se
    arregle el `xpass` avise para retirar la entrada.

### ❌ Refutaciones

- **`bench.yml` "roto en Windows"** → **falso tal cual**: la matriz solo tenía
  `ubuntu` y `macos`, y en macOS el shell por defecto ya es `bash`. Se endurece
  igualmente.
- **`scripts/bench.sh` "verificar si existe"** → **existe** y mide los tiempos del
  toolchain; no se duplica.
- **`|| true` en `ci.yml`/`release.yml`** → solo aparecía en `brew install` y en
  los pasos de TinyCC/codesign, donde el fallback está documentado; se elimina del
  `brew install` (el resto se conserva a propósito porque el fallback es
  intencional).
- **`ci.yml`/`release.yml` sin `permissions`** → sí las tenían, pero a nivel
  `contents: write` para **todos** los steps; la corrección es de granularidad,
  no de ausencia. También había ya caché de pip/npm, que la auditoría daba por
  ausente.

## [Unreleased] — FASE 6: DX Verificable

> La Fase 6 del roadmap se reescribió tras la auditoría de viabilidad: benchmarks
> realistas, plantillas que cumplen su propio criterio, y el playground WASM
> **fuera del scope de 1.0** con justificación técnica. Primero, los bugs
> residuales de la Fase 5 (verificados contra el código; 1 refutado).

### 🐛 Fixed — 6.0 Bugs residuales de Fase 5

- **BUG-6.1** `--locked` **no fallaba** si `pengu.lock` no existía: sólo `--frozen`
  lo comprobaba, así que un CI con `pengu build --locked` en un repo sin lock
  pasaba en silencio (falso negativo). Ahora ambos exigen el lock y el mensaje
  nombra el flag usado. Un proyecto **sin dependencias** sigue sin necesitar
  lock (no hay nada que resolver) y se documenta con test.
- **BUG-6.2** la clave de caché de scripts no incluía `release_unsafe`: un script
  cacheado con los checks activos se reutilizaba al ejecutar `--release-unsafe`
  (y viceversa), de modo que el usuario creía haber desactivado los checks y
  ejecutaba el binario antiguo.
- **BUG-6.3** `--deny-deprecated` construía un **segundo** builder para la puerta
  de deprecación, duplicando la resolución de módulos. Ahora la comprobación se
  hace sobre el mismo builder que compila y `check_sources_diagnostics` está
  memoizado por builder (un solo pase).
- **BUG-6.9** `pengu verify` no comparaba la **URL de origen**: una dependencia
  sustituida por otro repositorio con el mismo nombre pasaba la verificación.
  Ahora se compara `git remote get-url origin` contra `source` del lock, con
  normalización tolerante (sufijo `.git`, barra final, mayúsculas).
- **BUG-6.10** `pengu run --deny-deprecated script.pengu` **ignoraba el flag**
  (sólo el `run` de proyecto lo respetaba). Ambos caminos comparten ahora
  `enforce_deny_deprecated`, y `pengu test --deny-deprecated` también.
- **BUG-6.12** el *threshold* de `.incbin` invalidaba el digest de assets (eso ya
  estaba bien) pero **no** el fingerprint del builder, así que un cambio de
  `PENGU_ASSETS_INCBIN_THRESHOLD` podía reutilizar el artefacto anterior. Añadido
  al fingerprint.

### 📚 Added — 6.3 Alcance y checklist de release

- **El playground WASM sale del scope de 1.0** y pasa a
  `ROADMAP_1.0.0.md` §"Fuera de scope para 1.0" con **justificación técnica**:
  el compilador es Python puro (Pyodide ≈30 MB, arranque 5-10 s), el codegen
  produce C (haría falta un toolchain C→WASM en el navegador, ~100 MB), el
  runtime no está compilado a WASM, reimplementarlo son meses y su mantenimiento
  es por release. Se documenta la alternativa realista para 1.1 (~2-3 días: un
  servidor `POST /check` que **no ejecuta código**, sobre `std.precis` +
  `libmicrohttpd`).
- **`RELEASE_CHECKLIST.md`**: separa lo **automatizable** (las 5 gates de CI,
  fmt/smoke, fuzzing 72 h, benchmarks, ASan/UBSan, `pengu verify`) de lo que es
  tarea **manual del autor** (Discord, Discussions, tag firmado, anuncios), y
  cierra con una lista explícita de **limitaciones conocidas** a declarar en el
  release (playground, rendimiento vs C, tamaño de binario, cache-hit, migración
  `Result` parcial, resolución sin backtracking, docs de stdlib).
- `README.md` enlaza `BENCHMARKS.md`, `RELEASE_CHECKLIST.md` y `SECURITY.md`.
- `ROADMAP_1.0.0.md`: estado de la Fase 6 reescrita, ítem por ítem.

### 📊 Added — 6.1 Benchmarks honestos y medidos

- **`benches/`** con 4 programas PenguScript (`hello_world`, `fib_40`,
  `string_ops`, `list_ops`) y sus equivalentes en **C `-O3`**, **Rust `-O`** y
  **Zig `-OReleaseFast`** (los baselines se omiten si falta el toolchain, y se
  informa como *skipped*, nunca como victoria).
- **`benches/run_bench.py`** (+ wrapper `benches/run_bench.sh`): mide tiempo de
  **build**, de **ejecución** (mejor de N tras un calentamiento) y **tamaño del
  artefacto ya con `strip`**, y exporta CSV. Portable (funciona en Windows sin
  bash).
- **`BENCHMARKS.md`** con las cifras **reales** medidas en este entorno
  (x86_64, gcc 16.2.1): binario de hello world **98.4 KiB** (no los 65 KB
  aspiracionales del roadmap, ni los 200-500 KB que estimaba la auditoría);
  `fib_40` 32 ms vs 6 ms de C.
- **Hallazgo accionable y publicado:** en `fib_40` el **frame tracing** (la pila
  de trazas que usa el reportero de crash de la Fase 5) cuesta **5.5×**
  (60 ms → 11 ms con `-DPENGU_FRAME_TRACE=0`), lo que deja PenguScript en
  **1.8× C** en vez de 5.5×. Se documenta el knob y **no** se cambia el valor por
  defecto: perder la traza en un pánico de límites sería peor para un lenguaje
  memory-safe. Queda anotado como optimización futura.
- **Targets revisados y publicados** en `BENCHMARKS.md`, con los que **no** se
  cumplen marcados explícitamente (`< 0.08 s` de cache-hit, `< 65 KB`, ±5% vs C).
- **CI** (`.github/workflows/bench.yml`): nightly y bajo demanda, con CSV como
  artefacto; **nunca** bloquea PRs (los runners compartidos son ruidosos).
- Nota: `scripts/bench.sh` **ya existía** y mide los tiempos del *toolchain*
  (cache-hit, frío con gcc/TCC, `bundle.c`, PCH); la auditoría pedía verificarlo.
  No se duplica: `BENCHMARKS.md` remite a él.
- Tests: `tests/test_benchmarks.py` (10 casos: programas presentes, bundle de
  cada uno, ejecución real del harness de un caso con CSV, y que el workflow no
  tenga `pull_request`).

### 🎁 Fixed — 6.2 Plantillas que cumplen su propio criterio

- **BUG-6.4 + BUG-6.5 — `--template game`**: ya no imprime tres líneas; abre una
  **ventana raylib** real (`InitWindow`/`BeginDrawing`/`ClearBackground`/
  `DrawText`/`EndDrawing`/`CloseWindow` con bucle hasta `WindowShouldClose`) y el
  manifiesto generado incluye **`links = ["raylib"]`**, sin el cual cualquier
  import de raylib fallaba con `undefined reference`. `pengu init` avisa de que
  hay que construir raylib si `pengu run` reporta símbolos ausentes.
- **BUG-6.6 — `--template cli`**: parsea argumentos de verdad con
  **`std.invoke`** + **`std.rites`**: flag `-v/--verbose`, opción `-o/--output`,
  posicional `input` y `--help` generado. Verificado E2E: el binario construido
  responde a `--verbose --output=out.txt in.csv` y a `--help`.
- **BUG-6.7 — `--template lib`**: incluye dos bloques `test` de humo con
  `std.ward`; `pengu test` pasa ("All 2 test(s) passed").
- Tests: `tests/test_init_templates.py` ampliado a 17 casos, incluidos los E2E
  que compilan y ejecutan las plantillas `cli` y `lib` (y el bundle de `game`).
  El arranque real de la ventana raylib no se puede verificar en este entorno
  porque `libraylib.a` no está construido; se documenta en el test.

#### ❌ Refutación

- **BUG-6.12 (parte de assets)** *"cambiar el threshold no invalida el digest"* →
  **falso**: `pengu_assets.generate` ya incluye `incbin=<threshold>` en su digest
  (con test y comentario en el código). El hueco real estaba en el fingerprint del
  builder, que es lo que se corrigió.
- **BUG-6.11** (`%` literal sin escapar) — la propia auditoría lo descartó;
  `_translate_string_lit` ya hace `.replace("%", "%%")`. Sin cambios.

## [Unreleased] — FASE 5: Seguridad y Robustez (v1.0)

> Política: el desbordamiento y los límites tienen comportamiento **definido**
> por defecto, la cadena de suministro está acotada, la deprecación es una
> política explícita y la robustez se valida con fuzzing continuo.
> Verificación previa: 4 de los 17 bugs de la auditoría resultaron **falsos**
> (BUG-5.1, 5.2, 5.4 y la parte de E0047) y se documentan como refutaciones con
> tests que fijan el comportamiento correcto.

### 🧪 Added — 5.5 Fuzzing continuo

- **5 harnesses** en `scripts/fuzz/`: `parser` (lexer + LALR), `bind` (header C →
  binding, con headers generados aleatoriamente además de los reales de
  `std_c/`/`build/include/`/`extern/`), `semver` (versiones y constraints),
  `lock` (round-trip TOML de `pengu.lock`) y `lsp` (documentos malformados y
  posiciones fuera de rango).
- **Contrato claro de fallo**: el objetivo puede fallar con un error *declarado*
  (`PenguError`, `SemVerError`, `LockError`, `HeaderParseError`, `ValueError`,
  `TypeError`); cualquier otra excepción (`IndexError`, `KeyError`,
  `AttributeError`, …) es un crash y falla el harness.
- **Dos modos**: con `atheris` instalado hace fuzzing guiado por cobertura; sin
  él (o con `PENGU_FUZZ_SMOKE=1`) ejecuta una pasada determinista sobre el corpus
  semilla + mutaciones con semilla fija. Esto permite que CI valide robustez sin
  la dependencia pesada, y que cualquier hallazgo se reproduzca.
- **Los crashes se guardan** en `build/fuzz_crashes/<harness>_<n>.bin` para
  replay directo.
- **CI** (`.github/workflows/fuzz.yml`): 5 min por harness en PR, 1 h en nightly y
  presupuesto configurable (72 h para release); sube el corpus de crashes como
  artefacto.
- **`docs/FUZZING.md`**: harnesses, modos, reproducción de hallazgos,
  minimización, calendario de CI y política de divulgación.
- Tests: `tests/test_fuzz_harnesses.py` (los 5 harnesses en modo smoke + corpus
  de regresión en `tests/fuzz_corpus/`).

### 🔐 Added — 5.3 Seguridad de la cadena de suministro

- **`SECURITY.md`**: alcance (front-end, codegen, runtime, `bind`, `add`,
  `lock`/`verify`, LSP y ejecución en build-time), versiones soportadas, canal de
  reporte (GitHub Security Advisories + email), acuse en 72 h, embargo de hasta
  90 días, SLAs de parche (crítico 7 d, alto 30 d, medio/bajo 90 d), integridad
  de releases y resumen de las mitigaciones ya presentes.
- **`pengu verify`**: recorre `pengu.lock` y comprueba que cada paquete está
  instalado, que el commit del checkout coincide (`git rev-parse HEAD`) y que el
  **SHA-256 del árbol de contenido** sigue siendo el registrado; informa por
  paquete y sale con código 1 ante cualquier desviación.
- **Sandbox del preprocesador de `pengu bind`** (los headers son entrada no
  confiable):
  - **Validación estática**: se rechazan `#include` absolutos (`/etc/passwd`,
    `C:\Windows\...`) y los que escapan del directorio del header (`../`).
    Opt-out explícito con `PENGU_ALLOW_ABSOLUTE_INCLUDES=1`.
  - **Aislamiento real en Linux con `bwrap`**: el preprocesador corre viendo sólo
    el toolchain (`/usr`, `/lib`, `/bin`, …) y los directorios necesarios
    (header, stubs, `-I`), todo de sólo lectura y **sin red** (`--unshare-net`).
    Los `-I` se absolutizan y el `cwd` pasa a ser el del header, para que el
    aislamiento no rompa la resolución. `PENGU_NO_SANDBOX=1` lo desactiva.
  - Entorno mínimo (sin `HOME` ni `LD_PRELOAD`).
- Nota honesta: sin `bwrap` (macOS/Windows) la garantía efectiva es la validación
  estática + entorno mínimo; se documenta como tal en `SECURITY.md`.
- Tests: `tests/test_supply_chain.py` (12 casos), más los de trust de build
  scripts en `tests/test_phase5_bugfixes.py`.

### 📜 Added — 5.4 Política de deprecación + `--deny-deprecated`

- **Hallazgo real (el auténtico problema detrás de BUG-5.1):** los warnings del
  checker (`W0001`–`W0007`) se calculaban y **se descartaban**; `pengu check`
  decía "Clean" sin mostrarlos. Ahora se convierten en diagnósticos con
  `severity: "warning"`, se imprimen en `pengu check` (con recuento en el
  resumen) y aparecen en `pengu check --json` con `ok`/`errors`/`warnings`.
- **Nuevo flag `--deny-deprecated`** en `check`, `build`, `run` y `test`:
  promueve cada `[W0006]` a error y falla con código 1 (los demás warnings siguen
  siendo warnings). `build --deny-deprecated` aborta **antes** de generar código.
- **`LANGUAGE.md` §23 — Deprecation & Stability Policy**: SemVer estricto, la
  **regla de las dos releases** (un símbolo `@deprecated` debe seguir funcionando
  ≥2 minors antes de poder eliminarse), soporte de `@deprecated` en `weave`/
  `declare`/`rune` y sus campos, y el uso de `--deny-deprecated` en CI.
- Documentados `W0005`/`W0006`/`W0007` también en `README.md`.
- Se actualizan tests que fijaban la numeración/emisión antigua:
  `test_compiler_core.py` (E0015 → E0058 para `error` fuera de `or:`, y
  normalización del wrapper de bounds en las aserciones de forma del codegen).
- Tests: `tests/test_deprecation_policy.py` (10 casos).

### 🔢 Added — 5.1 Política de desbordamiento de enteros

- **El desbordamiento firmado ya no es UB por defecto** (era el riesgo real: C lo
  deja indefinido y `-O2` puede reescribir la aritmética). Política aplicada con
  flags por perfil:
  - **debug** → `-ftrapv`: aborta con SIGABRT ante desbordamiento firmado.
  - **release** → `-fwrapv`: wrapping en complemento a dos **definido**.
  - **`--release-unsafe`** → sin flag: se recupera el UB de C, de forma explícita.
- Sólo para GCC/Clang; TCC y MSVC no soportan `-ftrapv` (la aritmética de MSVC ya
  envuelve en la práctica) y se omiten.
- El header del runtime define `PENGU_OVERFLOW_CHECK` (por defecto 1), simétrico
  a `PENGU_BOUNDS_CHECK`, para que `--release-unsafe` pueda desactivarlo.
- **Nota de implementación honesta:** la auditoría proponía insertar llamadas
  `pengu_assert_*_overflow_*(...)` desde el codegen. Se optó por los flags
  equivalentes porque (a) dan la misma garantía para GCC/Clang sin instrumentar
  cada operación, y (b) `libpengu_runtime.a` no puede reconstruirse en este
  entorno (faltan cabeceras de libxml2), así que añadir símbolos nuevos al
  runtime dejaría el enlace roto.
- Tests: `tests/test_overflow_policy.py`, incluida la **verificación de
  aceptación con `-fsanitize=signed-integer-overflow`** (release: 0 informes).
  `tests/conftest.py::compile_run` aplica la misma política por perfil.

### 🛡️ Added — 5.2 / 5.6 Comprobación de límites siempre activa + bloques `unsafe:`

- **Cambio de política (rompe la suposición de Fase 1):** las comprobaciones de
  límites **ya no son un extra de depuración**. Se emiten en *todos* los
  perfiles; un `pengu build --profile release` con `xs at 999999` aborta con
  `[PENGU] Index out of bounds` (código 134) en lugar de leer memoria arbitraria.
- **`-DPENGU_BOUNDS_CHECK` se desacopla del perfil**: ya no se inyecta
  `-DPENGU_BOUNDS_CHECK=0` por ser release; sólo `--release-unsafe` lo hace (y
  añade `-DPENGU_OVERFLOW_CHECK=0`).
- **Nuevo bloque `unsafe:`** (5.6): opt-out *local* y aditivo para las
  sentencias que envuelve. Es una sentencia (`unsafe_stmt`), admite anidamiento
  y el parser lo rechaza en el nivel superior (sólo dentro de cuerpos de
  función). Emite el aviso **`[W0007]`** para auditoría.
- **Nuevo flag `--release-unsafe`** en `build`, `run` y `test`: opt-out global.
  Se propaga al codegen (`set_release_unsafe`) y al runtime, y entra en la clave
  de caché de configuración para no reutilizar bundles con la política contraria.
- `tests/conftest.py::compile_run` acepta `expect_exit` (para programas que
  deben abortar) y `release_unsafe`.
- Tests: `tests/test_bounds_policy.py` (12 casos: política de codegen, bloque
  `unsafe:` aislado y anidado, `--release-unsafe`, desacople del perfil, W0007,
  rechazo en top-level y E2E de aborto en release). Se actualiza
  `tests/test_phase1_bounds.py`, cuya aserción de "release sin checks" queda
  obsoleta por diseño.

### 🐛 Fixed — FASE 5 §5.0: auditoría pre-vuelo (bugs confirmados)

Verificado contra el código antes de actuar; **4 hallazgos de la auditoría
resultaron falsos** y se documentan como refutaciones en los tests.

- **BUG-5.7** `_dump_toml` convertía `None` en `""` (corrupción silenciosa del
  manifiesto) → ahora lanza `TypeError`.
- **BUG-5.8** `_lock_target` no canonizaba triples: `x86_64-w64-mingw32` y
  `x86_64-pc-windows-gnu` generaban locks distintos → mismo target, misma
  entrada (`x86_64-windows-gnu`). Evita falsos positivos de `--frozen` en CI.
- **BUG-5.9** El bundle emitido no validaba el ABI: se añade
  `_Static_assert(PENGU_ABI_VERSION == 1, ...)` (guardado para C99 estricto).
  **Encontró inmediatamente un `pengu_runtime.h` obsoleto** en `build/include/`.
- **BUG-5.10** `or:` sobre un valor `any` reventaba en codegen con un mensaje
  interno → ahora es un `E0005` accionable en el checker.
- **BUG-5.14** `pengu bind` no limitaba el tamaño del header (un `.h` gigante
  agotaba la RAM de pycparser) → límite de 16 MB, configurable con
  `PENGU_BIND_MAX_BYTES`.
- **BUG-5.15** `pengu add`/`pengu update` ejecutaban `build.py`/`build.sh`/
  `Makefile` de terceros sin más: ahora exigen confianza explícita (`--trust`,
  `PENGU_TRUST_ALL=1` o confirmación interactiva); en shells no interactivos se
  omiten con aviso.
- **BUG-5.17** `error` fuera de un bloque `or:` compartía el código `E0015` con
  `UnknownArrayDimensionError` → código propio **`E0058`** (los `E0015`
  restantes son todos la misma condición: dimensión de array desconocida).
- **BUG-5.3** `W0005` (shadowing de weave global) y `W0006` (`@deprecated`) no
  aparecían en el catálogo → documentados en `LANGUAGE.md` §22.3 y `README.md`,
  junto con `W0007` (bloques `unsafe:`) y la nota de que `W0003` está reservado.

#### ❌ Refutaciones (la auditoría se equivocaba; se añaden tests que lo fijan)

- **BUG-5.1** *"`_check_deprecated_symbol` es código muerto"* → **falso**: la
  copia del checker no se usa, pero `pengu_infer.py` la llama en 17+ sitios y
  `W0006` **sí se emite** (verificado con weave y rune).
- **BUG-5.2** *"`@deprecated` no se propaga a `rune`"* → **falso**: el atributo
  llega al chequeo vía `RuneType.attributes`.
- **BUG-5.4** *"`pengu_string_format_ex` lee fuera de límites"* → **falso**: la
  cadena `p[1]=='l' && p[2]=='l'` cortocircuita, así que `p[3]` nunca se lee más
  allá del terminador NUL.
- **BUG-5.17 (E0047)** *"`E0047` se comparte con `DuplicateConceptBindingError`"*
  → **falso**: ambos sitios lanzan `AutoOwnedBanishError`.

- Tests: `tests/test_phase5_bugfixes.py` (17 casos, incluidos los de refutación).

### ⚠️ Added (scoped) — 4.4 API `Result` aditiva en `std.archivum`

> **Alcance.** La migración completa de la stdlib a `Result` es un cambio de
> API pública; la auditoría la marca como el ítem más peligroso y la sitúa al
> final. Aquí se implementa la **base no rompiente**: APIs nuevas junto a las
> históricas, que permanecen intactas (100% backward compat 0.14.x).

- **Decisión D5 documentada** en `LANGUAGE.md` §12: `maybe T` responde "¿hay
  valor?"; `result of T to E` responde "¿qué falló?". Cada uno tiene su lugar.
- **`std.archivum`**: nuevo omen `IoError` (`NotFound`, `IsADirectory`,
  `NotAFile`, `Permission`, `Unknown`) y weaves `read_file_result`,
  `write_file_result`, `delete_file_result` (→ `result of T to IoError`) más
  `describe_error` para mensajes legibles. Ahora se puede distinguir "no
  existe" de "es un directorio" sin FFI.
- Las APIs `maybe`/`bool` (`read_file`, `write_file`, `delete_file`, …) **no
  cambian**; los tests de backward compat siguen verdes.
- Caso sutil cubierto: en POSIX abrir un directorio para lectura "tiene éxito"
  sin bytes, así que `read_file_result` comprueba `is_dir` **antes** de leer y
  reporta `IsADirectory`.
- Pendiente (4.4 completo, fuera de esta entrega): migrar `precis` (HTTP),
  `cipher` (decoding) y el resto de módulos con el mismo patrón aditivo, con
  aliases `@deprecated` para los nombres viejos.
- Tests: `tests/test_result_io_api.py`.

### 📦 Added — 4.6 / 4.7 Vendor y caché global de dependencias

- **4.7 Caché global**: las dependencias git se guardan en
  `~/.cache/pengu/deps/<sha256(url+branch)[:16]>/` (o `PENGU_DEP_CACHE`, o
  `$XDG_CACHE_HOME/pengu/deps`). Un `pengu add` posterior restaura desde la
  caché sin clonar. `PENGU_NO_DEP_CACHE=1` lo desactiva.
- **4.6 `pengu vendor`**: copia cada dependencia instalada a `vendor/<name>/`
  (sin `build/`, conservando `.git` para que `upgrade` siga funcionando), junto
  con `vendor/pengu.lock` y un README. Si `lib/<name>/` falta, `pengu build`
  (y `--frozen`) la restaura desde `vendor/` sin red, y el lock verifica commits
  y hashes de contenido.
- Tests: `tests/test_vendor_cache.py` (clave de caché, overrides de entorno,
  restauración desde caché, vendor + build `--frozen` offline y conservación de
  `.git`).


### 🧱 Added — 5.7 / 5.8 / 5.9 Endurecimiento del runtime, códigos de error y docs

- **5.7 Endurecimiento del runtime**
  - `_Static_assert(PENGU_ABI_VERSION == N)` en el bundle emitido (5.0), que ya
    detectó un `pengu_runtime.h` obsoleto en `build/include/`.
  - Nueva política de OOM `PENGU_OOM_ABORT` (por defecto **1**): una asignación
    fallida imprime `[PENGU] out of memory` y `abort()` en lugar de devolver
    `NULL` y corromper memoria lejos del origen. Los embedders pueden compilar
    con `-DPENGU_OOM_ABORT=0` para recibir `NULL`.
  - `PENGU_OVERFLOW_CHECK` (por defecto 1), simétrico a `PENGU_BOUNDS_CHECK`.
  - `LANGUAGE.md` **§5.0 Safety guarantees and their opt-outs**: tabla única de
    los tres modos de fallo (límites, overflow, OOM), su comportamiento por
    defecto y su único opt-out; además de la política formal de **división por
    cero** (`SIGFPE` en POSIX, sin valor silencioso; el compilador no inserta la
    comprobación) y un ejemplo de `unsafe:`.
  - El ABI layout (`tests/abi/test_abi_layout.c`) pasa a ejecutarse en la matriz
    de CI (5.7.f).
- **5.8 Higiene de códigos de error**
  - Confirmado con evidencia: `E0047` **sólo** lo lanza `AutoOwnedBanishError`
    (la auditoría se equivocaba); los `E0015` restantes son todos la misma
    condición (dimensión de array desconocida).
  - Documentados `E0051`–`E0058` en `LANGUAGE.md` §22.2 (la tabla se quedaba en
    `E0050`) y el rango del título actualizado.
  - Tests que verifican que **todo** código `E` usado por el compilador está
    documentado y que los códigos de warning `W0001`–`W0007` aparecen en
    `LANGUAGE.md`/`README.md`.
- **5.9 Sincronización de documentación**
  - `README.md`: catálogo con `E0000`–`E0058` y la lista de warnings; sección
    "not there yet" reescrita (la Fase 5 cierra overflow, bounds, lockfile,
    sandbox, trust y deprecación).
  - `CHANGELOG.md`: cabecera `[Unreleased] — FASE 5: Seguridad y Robustez (v1.0)`.
  - `ROADMAP_1.0.0.md`: estado de Fase 5 ítem por ítem, incluidas las
    desviaciones deliberadas y los 4 hallazgos refutados.
- Tests: `tests/test_runtime_hardening.py` (11 casos).

## [Unreleased] — FASE 3 & 4: Tooling y Ecosistema
### 🎮 Added — 4.10 `pengu init --template`

- Plantillas `exe` (por defecto), `cli`, `lib` y `game`. `--template lib`
  produce un proyecto `static` salvo que se pase `--type` explícito.
- **Bug preexistente corregido**: las plantillas `static`/`shared` empezaban con
  `//`, que **no es un comentario en PenguScript**; `pengu init --type static`
  generaba código que no parseaba. Ahora usan `#`.
- `--type` pasa a `default=None` para poder distinguir "no especificado" de
  "exe explícito".
- Tests: `tests/test_init_templates.py` (contenido de cada plantilla + parseo y
  bundle E2E de todas, incluidos `static`/`shared`/`obj`/`c`).

### 📚 Added — 4.9 Política de versionado de la stdlib

- Documentada en `LANGUAGE.md` §19.0: la stdlib va **acoplada al compilador** en
  1.x (decisión D6) y cada módulo exporta `<MODULE>_VERSION` con la versión del
  toolchain; el desacople queda para 2.0.
- **Realizada la política**: los 27 módulos escritos a mano exportan su constante
  `*_VERSION` (se añadieron las 5 que faltaban: `celeris`, `oracle`, `scrolls`,
  `trial`, `xlsx`) y todas se sincronizaron a la versión actual del toolchain.
- Tests: `tests/test_std_versioning.py` (presencia, sincronía con `VERSION` y
  validez SemVer).

### 📦 Added — 4.1 `pengu.lock`: pinning reproducible y builds offline

- **Nuevo `pengu_lock.py`**: `pengu.lock` en TOML con, por paquete, `source`,
  `constraint`, `version`, `commit` exacto, **SHA-256 del árbol de contenido**,
  `required_by` y `children`; más `targets` con el triple de compilación.
- **`compute_tree_hash`**: hash determinista por fichero (ruta + contenido) que
  ignora `.git`, `build/`, caches y directorios ocultos, así que el mismo
  checkout en otra máquina hashea idéntico.
- **`pengu build`** escribe/refresca `pengu.lock` automáticamente;
  **`--locked`** verifica y falla con **`E0061`** si el lock falta o no coincide
  (nunca escribe); **`--frozen`** exige además que el lock exista y no resuelve
  nada nuevo (builds offline/CI). Flags en `build`, `run` y `test`.
- **Detección de desviaciones**: commit distinto, versión distinta, paquete
  añadido/eliminado, contenido cambiado (sha256) y target distinto, cada una con
  mensaje accionable.
- **`pengu update`** refresca el lock tras el `git pull` (4.1.g).
- Tests: `tests/test_lockfile.py` (hash determinista, round-trip TOML, las cinco
  clases de diff, y E2E: escritura del lock, `--locked`/`--frozen`, lock
  manipulado, lock ausente y cambio de contenido con refresco).

### 🔵 Added — 4.2 SemVer y dependencias transitivas (MVP) + 4.8 tree/metadata

- **`pengu_semver.py`**: parser de versiones (`1.2.3`, `v1.2.3`, prerelease) y de
  constraints (`^X.Y.Z`, `~X.Y.Z`, `>=X, <Y`, `=X`, `X.Y.Z`, `*`) con semántica
  Cargo (caret se estrecha en `0.x`), más `select_version` que elige el tag más
  alto que satisface el constraint. Los prereleases solo se eligen si el
  constraint menciona uno.
- **Constraints en el manifiesto**: `[dependencies.X] version = "^1.2.0"` se lee
  y se aplica (checkout del tag que satisface el constraint).
- **Resolución transitiva** (`resolve_transitive_dependencies`): al hacer
  `pengu add`, se leen los manifiestos de las dependencias instaladas y se
  instalan sus propias dependencias (hasta 5 niveles). Los ciclos se detectan y
  se cortan; los requisitos incompatibles lanzan `DependencyConflictError`
  (equivale a `E0062`) con las dos versiones pedidas y salen con código 1.
- **Rollback**: si un `add` provoca un conflicto, se deshacen el directorio
  instalado y la entrada del manifiesto (nunca queda un proyecto inconsistente).
- **Las dependencias transitivas no se registran** en el manifiesto raíz: viven
  en el de su padre (se corrigió un bug detectado en pruebas E2E).
- Resolución **forward-only** (sin backtracking) por diseño, como recomienda la
  auditoría; el backtracking completo queda para 4.2.j.
- **4.8 `pengu tree`** imprime el grafo jerárquico con versión y commit;
  **`pengu metadata`** (y `tree --json`) emite el grafo en JSON con `source`,
  `constraint`, `required_by`, `version`, `commit` y `children`.
- Tests: `tests/test_semver.py`, `tests/test_transitive_deps.py` (install
  transitivo, grafo, conflicto con rollback, ciclos y tree/metadata con repos
  git reales).

### 🔧 Added — 4.5 `pengu remove` y `pengu upgrade`

- **`pengu remove <name>`**: elimina `lib/<name>/` y su entrada del manifiesto
  (TOML/YAML/JSON), con guarda de ruta (nunca borra fuera de `lib/`) y error
  accionable si la dependencia no existe. `--keep-files` deja los ficheros.
- **`pengu upgrade <name> [--version <tag>] [--branch <b>]`**: `git fetch
  --tags`, checkout del tag (o `git pull --ff-only` si no hay versión) y
  reescritura de la entrada del manifiesto con `version`/`branch` y el commit
  resultante. Las copias locales sin `.git` se saltan con aviso.
- Helpers `_find_manifest`, `_read_config_dependency`, `_set_config_dependency`
  y `_remove_config_dependency` manejan los tres formatos de manifiesto.
- Tests: `tests/test_deps_commands.py` (E2E con repo git real: add → upgrade a
  tag → manifest válido → remove).

### 📦 Added — 4.11 TOML como manifiesto canónico

- La **lectura** ya prefería `pengu.toml`; ahora la **escritura** también:
  `pengu init` genera `pengu.toml` por defecto (`--format yaml` mantiene el
  manifiesto YAML para compatibilidad) y `pengu add` prefiere el `pengu.toml`
  existente y lo crea si no hay ninguno.
- Nuevo serializador TOML mínimo (`_dump_toml` / `_toml_scalar`, sin dependencias)
  que preserva el resto del manifiesto al añadir dependencias.
- YAML y JSON siguen siendo legibles; si ambos coexisten, gana `pengu.toml`.
- Tests: `tests/test_manifest_toml.py`.

### 📚 Fixed/Added — 4.3 Auditoría y enforcement de documentación en `std/`

> **Corrigendum.** El roadmap pedía "convertir `#` → `##` en los `.d.pengu`".
> Esa premisa está refutada: en 0.15.0 los bindings se migraron en dirección
> opuesta (`##` → `#`) para igualar la salida de `pengu_bind`, y tanto el
> checker como el hover del LSP leen **ambos** como doc text. Convertirlos a
> `##` rompería la convención acordada.

- **4.3.a — Auditoría automática** (`tests/test_std_docs_completeness.py`):
  verifica que los 77 módulos de `std/` tengan bloque de cabecera documentado
  (100%), fija un **ratchet** por tipo de declaración para que la cobertura
  documentada nunca retroceda, y comprueba que los `.d.pengu` mantengan el
  spelling `#` en las declaraciones (`##` solo en banner/cabecera).
- **4.3.b — `pengu_bind`**: los bloques con tags Doxygen se emiten como `#`
  estructurado (una línea por tag), conservando la convención de `.d.pengu` y
  sin perder información (hover y `pengu doc` siguen leyéndolos).
- **4.3.c — `pengu doc`** renderiza `#` y `##` por igual (test explícito).
- **4.3.e — `README.md`**: la promesa de documentación se ajusta a la realidad
  (`#`/`##`, auditada por test) en vez de afirmar "`##` docstrings" al 100%.
- Estado medido: `weave` 1129/1311 (86%), `rune` 91/111 (81%), `declare`
  630/1862, `const` 118/588. Los huecos restantes están concentrados en bindings
  generados (dependen de los comentarios del header C) y en `atlas`/`scrolls`.

### ✅ Verified — 3.7 / 3.8 ya implementados

- La auditoría asumía que `textDocument/signatureHelp`, `documentSymbol` y
  `foldingRange` no existían; los tres **ya estaban implementados** en
  `pengu_lsp/server.py`. Esta fase añade su cobertura de tests
  (`tests/test_lsp_navigation_extra.py`): parámetros y `active_parameter` en
  signature help, símbolos top-level en document symbols y rangos de plegado
  bien formados para bloques y comentarios.

### ✨ Added — 3.5 Cross-compilation (Linux ⇄ Windows)

- **`--target <triple>`** en `build`/`run`/`test` (y `build: target:` en
  `pengu.yaml`): `parse_target_triple` interpreta triples estilo
  `x86_64-w64-mingw32`, `aarch64-apple-darwin`, `x86_64-unknown-linux-gnu`.
- El nombre del artefacto sigue al **target**, no al host: `.exe`, `.dll`,
  `.dylib`, `.so` según el triple.
- **Auto-detección de cross-compiler**: con un target Windows en host no-Windows
  se prueban `<triple>-gcc` / `x86_64-w64-mingw32-gcc` / `i686-w64-mingw32-gcc`;
  `--cc` siempre gana. Si no hay ninguno, el error es accionable (instala
  mingw-w64 o pasa `--cc`) en vez de fallar con un link confuso.
- **`PENGU_RUNTIME_CROSS`**: directorio del runtime compilado para el target
  (añade `-L`/`-I`). El runtime prebuilt es del host, así que el link cruzado
  requiere este runtime; la generación del bundle C funciona para cualquier
  target sin toolchain cruzada.
- Los flags de link se eligen por target (`-lws2_32`… para Windows, frameworks
  para Darwin).
- Tests: `tests/test_cross_compile.py` (parseo, nombres de artefacto,
  detección/errores de compilador, `PENGU_RUNTIME_CROSS`, bundle Windows sin
  cross-cc; compilación real con MinGW marcada como skip si falta).

### ✨ Added — 3.11 `pengu doc`: Doxygen, deprecación, índice y búsqueda

- **Tags Doxygen**: `sym.doc` se divide en resumen + lista estructurada de tags
  (`@param`, `@return`, `@see`, `@deprecated`, `@note`, …) en vez de volcarse
  como prosa.
- **Badge de deprecación**: los símbolos con `@deprecated` (atributo o tag)
  muestran `> ⚠️ **Deprecated** — motivo` en su página.
- **Índice por categorías** en `index.md`: Concepts, Runes, Echoes, Omens,
  Seals, Aliases, Constants, Functions y declaraciones C, con firma y marca
  `[deprecated]`.
- **Búsqueda cliente** `index.html`: página autocontenida con el índice JSON
  embebido y un cuadro de búsqueda en JS que filtra por nombre, tipo, módulo,
  firma y resumen.
- Tests: `tests/test_doc_phase3.py`.

### ✨ Added — 3.10 / 3.12 Formatter: --diff, --stdin, config y on-type

- **3.10 `pengu fmt --diff`**: imprime un diff unificado por cada fichero que
  cambiaría, en vez de solo "would format".
- **3.10 `pengu fmt --stdin`**: lee el fuente de stdin y escribe el resultado
  formateado en stdout (integración con editores/CI); `--check` con `--stdin`
  devuelve 1 si el input cambiaría.
- **3.10 `.pengufmt.toml`**: `load_format_config` busca primero
  `.pengufmt.toml` y luego `pengu.yaml`/`pengu.toml`, acepta sintaxis TOML
  (`clave = valor`) y YAML (`clave: valor`) bajo `[formatting]`/`formatting:`, y
  soporta `tab_size`/`indent`/`indent_size`, `insert_spaces`/`use_tabs`/`tabs`,
  `blank_lines_max` y `line_width` (registrado para futuros wrappers).
- **3.10 `blank_lines_max`**: `format_pengu_source` colapsa las líneas en blanco
  consecutivas (nunca dentro de un literal multilínea); el LSP
  `textDocument/formatting` también lo aplica.
- **3.12 `textDocument/onTypeFormatting`**: al teclear `:` al final de un
  apertura de bloque se indenta la línea siguiente un nivel; al teclear salto de
  línea tras una apertura, la línea nueva recibe la indentación correcta. Solo
  se edita el espacio inicial de la línea afectada (nunca se refluye el
  documento).
- Tests: `tests/test_fmt_phase3.py`.

### ✨ Added — 3.2 / 3.9 LSP: semantic tokens, inlay hints y code lens

- **3.2.b `textDocument/semanticTokens/full`**: clasifica los tokens del lexer
  real con la `SymbolTable` (`function`, `struct`, `enum`, `type`, `namespace`,
  `parameter`, `variable`, `macro`, `keyword`, `string`, `number`, `decorator`)
  y añade modificadores `declaration`, `readonly` (`let`/`const`), `deprecated`
  y `defaultLibrary` (símbolos de `std/`). La leyenda se registra en las
  capacidades del servidor.
- **3.2.d `textDocument/inlayHint`**: hint de tipo inferido tras declaraciones
  `var`/`let` sin anotación (`var a is 42` → `: int`) y hint de nombre de
  parámetro en llamadas (`calling add with 1, 2` → `a: 1, b: 2`). No anota
  bindings/parámetros ya tipados.
- **3.9 `textDocument/codeLens`**: un lens "▶ Run test: <nombre>" por cada bloque
  `test "…":`, con el comando `pengu.runTest` y argumentos `[uri, nombre]`.
- Tests: `tests/test_lsp_semantic_tokens.py` (clasificación, codificación
  relativa ordenada, modificadores, hints de tipo/parámetro, code lens y
  registro de capacidades).

### 🐛 Fixed — 3.1 LSP: rename, highlights y references semánticos

- **`textDocument/rename`** ya no hace un `\\bpalabra\\b` sobre el texto crudo.
  Resuelve el símbolo bajo el cursor con la `SymbolTable` y reescribe solo las
  ocurrencias reales:
  - símbolos locales (`var`/`let`/`param`) → solo dentro de su ámbito léxico
    (un `x` en `weave f` no toca el `x` de `weave g`);
  - símbolos globales → en todo el proyecto cuando su declaración es
    inequívoca (una sola declaración top-level); si hay homónimos globales, se
    limita al documento activo;
  - nunca toca comentarios, literales de string ni accesos a miembro
    (`obj.campo`), pero **sí** actualiza las interpolaciones `"{x}"` (son
    referencias reales);
  - rechaza nombres nuevos que no sean identificadores válidos.
- **`textDocument/documentHighlight`** usa el mismo motor: resuelve el símbolo,
  filtra homónimos por resolución de ámbito y elimina la heurística anterior
  (marcaba como escritura cualquier palabra de una línea con ` is `).
- **`textDocument/references`** mantiene la distinción local/global pero ahora
  localiza ocurrencias con el lexer real en vez de un escaneo textual, así que
  ya no reporta homónimos dentro de comentarios o strings; los ficheros del
  proyecto se escanean por tokens (excluyendo `.d.pengu`).
- Base del motor: `_identifier_occurrences` (tokens `NAME` del lexer, con
  verificación `lookup_at(...) is sym` por ocurrencia), `_interpolation_positions`
  y `_iter_project_sources`.
- Tests: `tests/test_lsp_semantic_rename.py` (ámbitos, strings/comentarios,
  interpolaciones, member access, nombre inválido, highlights y references).

### ✨ Added — 3.6 Diagnósticos JSON para CI

- **`pengu check --json`**: emite JSON Lines con un objeto por diagnóstico
  (`type`, `file`, `line`, `col`, `code`, `severity`, `message`, `help`, `note`)
  y una línea final de resumen (`ok`, `errors`, `duration_ms`). Nada de texto
  humano contamina stdout, así que `jq`/CI pueden consumirlo directamente.
- **`pengu build --json`**: resumen `{ok, artifact, cached, profile, duration_ms}`
  en éxito y diagnóstico + resumen con salida 1 en fallo (semántico o de
  compilación), sin banners.
- `PenguBuilder.check_sources_diagnostics()` devuelve los diagnósticos
  estructurados; `check_sources()` sigue formateando el texto humano sobre ellos.
- Tests: `tests/test_json_diagnostics.py` (parseo, pureza de stdout, fallo con
  exit code 1 y presencia del flag).

### 🐛 Fixed — 3.3 Correcciones de `pengu bind`

- **3.3.1 — Enums anónimos.** Un `enum { A = 1, B = 2 };` sin nombre ya no se
  descarta en silencio: cada variante se emite como `const NAME as i64 is V`,
  de modo que los headers que dependen de esas constantes funcionan.
- **3.3.2 — Macros de floats, chars y expresiones.** `emit_consts` reconoce
  ahora literales `float`/`double` (`3.14`, `1.5f` → `const X as f64 is …`),
  literales de carácter (`'A'` → `const X as char is 'A'`) y expresiones
  constantes enteras que pliega (`(1 << 4)` → `16`, `(2 * 1024)` → `2048`),
  incluidas referencias a otros macros simples. Antes solo se aceptaban enteros
  y strings; todo lo demás se perdía.
- **3.3.3 — `@packed` / `@align(N)`.** El blanking de `__attribute__` (necesario
  para que pycparser lea el header) perdía la semántica. Ahora se recupera del
  texto original emparejando llaves por cada `struct` y se re-emite como
  `@packed` / `@align(N)` en el `rune`, enganchando con los atributos de 1.5.2.
- **3.3.4 — Docstrings Doxygen.** Los bloques con `@param`, `@return`, `@see`,
  `@deprecated`, `@note`, `@warning`, etc. se emiten como docstring `##`
  estructurado (consumible por `pengu doc` y hover); los comentarios planos
  siguen siendo `#` para no romper la salida histórica.
- **3.3.7 — Macros reservadas.** `_is_reserved_name` filtra identificadores
  reservados a la implementación (`__…`, `_[A-Z]…`, `_WIN32`, `_MSC_VER`, …)
  además de los patrones explícitos de `--ignore`.
- `_const_eval` amplía el plegado con `~`, `%`, `^`, unario `+` y casts.
- Tests: `tests/test_bind_phase3.py` cubre 3.3.1–3.3.7 y 3.3.8 (bind + check
  limpio de `zlib.h`, `sqlite3.h`, `xxhash.h` y `nanosvg.h` reales).

### 🐛 Fixed — 3.4 Assets grandes en `arca`

- **3.4.a/b/c — Emisión `.incbin` para assets grandes.** Los assets cuyo tamaño
  alcanza `PENGU_ASSETS_INCBIN_THRESHOLD` (1 MB por defecto; `0` desactiva;
  también vía `PENGU_ASSETS_INCBIN_THRESHOLD`) se incrustan con la directiva
  `.incbin` del ensamblador en GCC/Clang/MinGW, evitando la expansión ~5× a
  texto C que hacía OOM a GCC con assets de decenas de MB. MSVC y TCC siguen
  usando el array de bytes portable (`#if defined(__GNUC__) && ...`).
- **3.4.d — `arca.string()` preserva bytes NUL embebidos.** Nuevo helper C
  `_{module}_string` que construye un `PenguString` propietario con longitud
  exacta (`memcpy` del tamaño conocido) en lugar de pasar por
  `ffi.string_from_cstr` (que truncaba en el primer `\0`). `arca.bytes()`
  ya era correcto; ahora `arca.string()` también.
- **3.4.e — Rutas largas en modo disco.** `_{module}_load` ya no trunca en un
  buffer fijo de 1024 bytes: reserva la ruta con `malloc` + `snprintf`.
- El digest de `pengu assets` incluye el threshold de `.incbin`, de modo que
  cambiarlo regenera `build/<module>_assets.c` en vez de reutilizar el cache.
- Tests: umbral on/off y override por entorno, helper de longitud exacta,
  ausencia de buffer fijo, round-trip E2E de NULs embebidos y de un asset de
  2 MB con `.incbin` y todo el rango de bytes.

## [0.16.0] - 2026-10-02

### Added & Changed — FASE 1 & FASE 1.5 Language Core & Semantics

#### FASE 1 — Núcleo del Lenguaje y Gramática
- **1.1 Strict LALR(1) Parser + Delimitación Obligatoria de Sentencias:**
  - Inicialización estricta del parser Lark (`strict=True`) garantizando 0 conflictos Shift/Reduce o Reduce/Reduce no resueltos.
  - Exigencia estricta de delimitador de nueva línea (`_NEWLINE`) o punto y coma entre sentencias simples consecutivas, previniendo fusiones accidentales de declaraciones inline (`var x is 1 var y is 2` rechazado como `ParseError [E0000]`).
- **1.2 Captura de `DedentError`, Normalización de BOM e Indentación:**
  - `DedentError` capturado limpiamente en `PenguParser.parse()` y transformado en `ParseError(E0000)` con reporte exacto de línea y columna.
  - Normalización de BOM UTF-8 (`\ufeff`) en `strip_bom()`, asegurando que `get_tokens()` y parsing operen de manera idéntica.
  - Advertencia léxica ante mezcla de espacios y tabuladores en la indentación.
- **1.3 Desambiguación de Soft Keywords:**
  - Modificadores contextuales `inline`, `ritual`, y `borrowed` desambiguados para funcionar como palabras clave suaves o identificadores según la posición sintáctica.
  - Restricción formal de constructores reservados `list`, `map`, `maybe` en contextos de nombres de variable.
- **1.4 Enforcement de Concept Bounds en Runes Genéricas:**
  - Preservación de `bounds` dentro de `RuneType` y la tabla de símbolos.
  - Validación bidireccional estricta en tiempo de chequeo (`E0032`) al instanciar tipos genéricos como `Box of T` con respecto a las restricciones `where T: Concept`.
  - Refuerzo de `typeparam_accepts_value` para comprobación estricta de parámetros de tipo.
- **1.5 Mangling de Nombres C Calificado por Namespace:**
  - Desacoplamiento de nombres C monomorfizados incorporando el prefijo de módulo calificado (`{module}_{fn}_{types}`).
  - Eliminación de colisiones de símbolos y fallbacks ciegos en la generación de código entre módulos independientes.
- **1.6 Propagación de `FrozenType` y Const-Correctness Inquebrantable:**
  - Preservación del calificador `frozen` a través de accesos encadenados e indexación de colecciones (`arr at 0`).
  - Prohibición estricta de conversión implícita de `ref to frozen T` a `ref to void` mutable (`E0005`), garantizando inmutabilidad a través de punteros genéricos.

#### FASE 1.5 — Definición Semántica y Gaps del Lenguaje
- **1.5.1 Pattern Matching Maduro en `judge`:**
  - Soporte de *payload bindings* para capturar variables locales a partir de variantes de Omen (`when Status.Ok with value -> ...`).
  - Guards condicionales en cláusulas `when` mediante sintaxis `if <cond>` (`when Variant with val if val > 0 -> ...`).
  - Verificación formal de exhaustividad en omens algebraicos.
- **1.5.2 Sintaxis y Semántica de Atributos:**
  - Soporte para atributos `@inline`, `@cold`, `@deprecated("reason")`, `@packed` y `@align(N)` en `weave`, `rune` y `field`.
  - Emisión de advertencias `[W0006]` ante el uso de símbolos marcados con `@deprecated`.
  - Rechazo con error `E0056` ante atributos no reconocidos o inválidos para el objetivo.
  - Codegen genera directivas de compilador C concretas (`__attribute__((packed))`, `__attribute__((aligned(N)))`, `always_inline`, `cold`).
- **1.5.3 Constantes Locales Evaluables en Tiempo de Compilación:**
  - Habilitación de declaraciones `const` dentro del cuerpo de funciones (`weave`) siempre que su valor sea computable en comptime.
  - Emisión directa en C sin asignación de espacio dinámico en la pila.
- **1.5.4 Soporte Completo de Unicode y Normalización CRLF:**
  - Reconocimiento léxico de secuencias de escape hexadecimales de Unicode `\u{HEX}` y `\uNNNN` en strings sin conflicto con bloques de interpolación `{...}` ni daño a barras invertidas escapadas (`\\uNNNN`).
  - Soporte de escapes Unicode en literales `char` restringido a valores de 7 bits ASCII (0..127) emitiendo `E0057` para codepoints superiores.
  - Normalización transparente de retornos de carro CRLF (`\r\n`) de Windows a LF (`\n`), preservando posiciones y conteos idénticos entre plataformas.

### Added & Changed — FASE 2: ABI Freeze y Portabilidad C99 / MSVC / TCC

#### 🧊 ABI congelado (2.2)
- **`PENGU_ABI_VERSION 1`** en `pengu_runtime.h`, con el layout exacto (tamaños y
  offsets de 64 bits) de `PenguString`, `PenguSlice`, `PenguList`, `PenguMap`,
  `PenguMaybe`, `PenguResult` y `PenguRange` documentado junto a la macro.
- **`tests/abi/test_abi_layout.c`** + `tests/test_abi_layout.py`: verifican
  `sizeof`/`offsetof` de cada struct del runtime y `PENGU_ABI_VERSION == 1` con el
  compilador disponible. El ABI congelado refleja el runtime **real**; el layout
  aspiracional del roadmap (`size_t cap`, `flags`, `val_or_err`) era incorrecto y
  no se aplicó.

#### 🚫 Sin extensiones GNU en el C emitido (2.1)
- **Infraestructura de preludes (statement hoisting)** en `pengu_codegen.py`
  (`expr_prelude`, `_hoist`, `_block_expr`, `_emit_block_expr`): las expresiones
  que antes se envolvían en `__extension__(({ ... }))` ahora pueden descomponerse
  en sentencias previas + una expresión simple, conservando el nombre del
  temporal en ámbito.
- **Nuevo flag `--strict-c99`** (y `PENGU_STRICT_C99=1`, y `build: strict_c99: true`
  en `pengu.yaml`): emite C99 portable sin `({...})` ni `__auto_type`. El modo GNU
  sigue siendo el **predeterminado**, por lo que el C generado no cambia salvo que
  se pida explícitamente.
- Convertidos a la ruta de preludes en modo estricto: bounds checks, `some`/`ok`/`err`,
  `_translate_result_ctor`, `if`/`unless` en posición de valor, `do:`/`with:` en
  posición de valor, `or else`/`or return`/`try`, `judge` (guardas, payloads y
  switch), comprehensiones `for … then …`, literales de lista y de mapa,
  `slice at`, comprobaciones de pertenencia (`in`/`not in` sobre range/array/list/map/slice),
  literales de string con interpolación, y los métodos integrados de `list`/`map`
  (`push`, `contains`, `index_of`, `put`, `get`, `remove`, …).
- **Sin `_Generic`** en el C emitido (2.2.e): el codegen llama al productor
  concreto `pengu_string_from_int/float/bool/char/cstr` según el tipo inferido.
  La macro `pengu_to_string` se conserva solo para C anfitrión y se compila fuera
  bajo C99 puro (`__STDC_VERSION__ >= 201112L`).

#### 🪟 Portabilidad de backend (2.2)
- **`--target-compiler=<gcc|clang|msvc|tcc>`** (`PENGU_TARGET_COMPILER`,
  `build: target_compiler:`): selecciona el dialecto de atributos y `restrict`.
- **Mapeo de atributos a MSVC**: `@inline` → `__forceinline`, `@deprecated` →
  `__declspec(deprecated(...))`, `@align(N)` → `__declspec(align(N))`, `@packed`
  → `#pragma pack(push, 1)` / `#pragma pack(pop)`, `@cold` se omite (sin
  equivalente directo). `restrict` se emite como `__restrict` en MSVC.
- **Flags de compilación para MSVC** en `pengu_project.py`: traducción de los
  flags GNU del perfil (`-O0/-O2/-g/-Wall/-D/-I`) a `/Od`, `/O2`, `/Zi`, `/W3`,
  `/D`, `/I` y `/std:c11`.
- **`PENGU_BOUNDS_CHECK` separado de `PENGU_FRAME_TRACE`** (2.2.g): las
  comprobaciones de límites ya no dependen del crash handler; las builds de
  release pasan `-DPENGU_BOUNDS_CHECK=0`.
- **Enums planos emitidos completos**: se eliminó el reenvío inválido
  `typedef enum X X;` (extensión GNU, y redefinición inválida en ISO C), de modo
  que el runtime y el código generado compilan con `-std=c99 -pedantic-errors`.

#### 🧪 Tests de Fase 2
- `tests/test_c99_portability.py` (sin `({...})`/`__auto_type` en modo estricto +
  compilación real con `gcc -std=c99 -pedantic-errors` y ejecución),
  `tests/test_attributes_msvc.py`, `tests/test_cli_strict_c99.py`,
  `tests/test_no_generic.py`, `tests/test_abi_layout.py`,
  `tests/test_bounds_flag_independence.py`.

#### 🚨 Limitaciones conocidas de la Fase 2
- `restrict` sigue siendo opt-in: el codegen no lo emite para código de usuario;
  la infraestructura queda lista para el target.
- El corpus de `tests/` es 100% estricto tras la conversión, pero `--strict-c99`
  no cubre todavía constructs exóticos de terceros que usen statement expressions
  generadas por plantillas de C enlazado (los bindings de C se copian tal cual).
- ABI v1 cubre solo targets de 64 bits (LP64/LLP64).

## [0.15.0] - Unreleased

### Fixed — memory-subsystem audit (verified against the source, C1–H5)

Each item below was reproduced against HEAD before the fix; the audit's
roadmap 0.14 and 0.15 claims were checked and **refuted** (see below).

- **C1 — `PenguString.is_owned`** (already landed): constructors mark heap
  buffers as owned and `pengu_banish_string` only frees owned data, so
  banishing a literal/`from_cstr`/`from_bool` view no longer `free()`s
  `.rodata`.  Verified complete: every `.data =` assignment sets the flag.
- **C2/C3 — `x to string` ownership** (`pengu_checker.py`): `string to string`
  is the identity and `bool to string` returns the static `"true"`/`"false"`
  view; neither is auto-banished any more (previously a double free for an
  owned source and the C1 crash for a literal).  `int`/`float`/`char` casts
  still allocate and are released.
- **C4 — release-before-assign on `set`** (`pengu_checker.py`,
  `pengu_codegen.py`): a local whose initializer *and* every reassignment move
  in a fresh value is still auto-owned; the code generator stashes the old
  value in a temporary and releases it after the assignment, turning the O(n)
  loop leak into O(1).  `set s is s` and all borrowed rvalues keep auto-banish
  off.  M1 (static) and M2 (struct-field) reassignment stay conservative: a
  live view of the old cell cannot be ruled out statically, so no release is
  emitted (the leak remains, a use-after-free does not).
- **C5 — containers of `maybe`/`result`** (`pengu_codegen.py`,
  `pengu_types.py`): `list of maybe T` / `list of result of T to E` now
  register generated per-type cleanup and deep-clone callbacks (previously a
  shallow `memcpy` of the payload box → leak/UAF).  `list of array` is left
  shallow on purpose: the array element size is not representable in the
  current `_owned` callback API.
- **C6/C7 — payload release** (`pengu_codegen.py`): `_release_payload_stmts`
  now handles algebraic `OmenType` and `ResultType`, and the `MaybeType` branch
  materialises the box temporary *before* recursing (the old code emitted
  invalid C such as `m.value_m->value` for `maybe maybe T`).
- **H1 — local algebraic omens** (`pengu_checker.py`, `pengu_codegen.py`):
  `var e as Event is with Msg is …` is auto-banished at scope exit; the
  generated destructor releases the active variant payload.
- **H4 — escape analysis** (`pengu_checker.py`): `sigil of x.field` and
  `sigil of x at i` now count as escapes, so the backing buffer is not released
  while a returned pointer into it is live.
- **H5 — slices of stack arrays** (`pengu_checker.py`): returning
  `arr at a to b` where `arr` is a local fixed array is rejected with `E0051`.
- **Bonus regressions found while fixing:** omen variant payloads were
  translated against the variant struct, so `with Items is [1, 2, 3]` emitted
  an invalid raw `PenguList` initializer; `(some s) or:` did not free the box
  because the parenthesised operand was not unwrapped; `some (with f is 1)`
  failed with `E0005` because the expected element type was not propagated.

#### Refuted audit items (no code change)

- **Roadmap 0.14** (`_translate_string_lit` leak): the cleanup postambles are
  emitted after the format call, so the premise is false.
- **Roadmap 0.15** (`essence of sigil of local` escape): `essence_of` is in the
  view-rule set and `_contains_var_ref` already detects the escape; the
  analysis is conservative, not blind.
- **Audit H3** (or_block must release the box payload): the payload is *moved*
  into the result, so releasing it there would leave the result dangling.  The
  real bug was the missing `paren_expr` unwrap (the whole box leaked).
- **Audit H1 repro** (`with Msg is "hello"`): a literal is a non-owning
  `.rodata` view and does not leak; the general fresh-payload case is fixed.

### Added — Pengunic rewrite of the five core standard-library modules

- **`std.oracle`, `std.scrolls`, `std.tally`, `std.atlas`, `std.loom` rewritten
  from scratch in idiomatic Pengunic style** (`PenguScriptGuideSpanish.md` is
  normative): canonical section order, `##` docstrings with the parameter /
  return / ownership / complexity contract, no `+` on strings, no Hungarian
  prefixes, and a generic core instead of hand-specialized copies — e.g.
  `enchanting maybe shard T:`, `enchanting result of shard T to shard E:`,
  `enchanting list of shard T where T: Num:` and the existing
  `enchanting map of shard K to shard V where K: Par, V: Par:`, which let
  `std.atlas` drop six duplicated concrete map blocks (2168 → under the guide's
  1500-line limit).
- **100 % public-endpoint compatibility.** Every legacy rune, enchanting method
  and module weave keeps its exact signature; the documented aliases are plain
  forwarding weaves documented with `## @deprecated Use X instead.` (the
  toolchain has no `@deprecated` marker, so it is a documentation convention).
  The contracts exercised by `tests/test_std_backward_compat.py`,
  `test_std_data_backward_compat.py`, `test_std_system_backward_compat.py`,
  `test_std_util_backward_compat.py` and the `test_<module>.pengu` programs keep
  passing.
- **In-module `test` blocks** (private `_expect_*` harness over `std.spark`,
  because importing `std.ward` from these modules would be a circular import):
  125 for `std.oracle`, 124 for `std.scrolls`, and equivalent suites for the
  others, all run by `pengu test`.
- **`tests/std_programs/<module>.pengu`** exercise programs for the rewritten
  API, registered in `tests/test_stdlib.py::EXPECTED_MARKERS`.

### Fixed — compiler and formatter issues found while rewriting the stdlib

- **Implicit return is implemented** (`pengu_codegen.py`): the guide's rule
  ("if the last statement of a weave is an expression, do not write `return`")
  was documented but never emitted, so `weave f into int: x * 2` compiled to a
  bare expression statement and returned garbage.
- **Generic `if v as T is <maybe>` casts to the monomorphized type**
  (`pengu_codegen.py`): the unwrapping used the erased type
  (`int32_t v = *(void* *)m.value`), which does not compile.
- **`.value` / `.error` on a generic `maybe`/`result` cast correctly**
  (`pengu_codegen.py`): the concrete path cast, but inside
  `enchanting maybe shard T` the field access fell back to the erased container
  field (`return ((*self)).value;`).
- **Native `result` construction** (`pengu_grammar.py`, `pengu_codegen.py`,
  `pengu_infer.py`): `calling ok_of with v` / `calling err_of with e` build a
  heap-boxed `result of T to E` (requires type context, `E0014` otherwise).
  They are compiler intrinsics rather than `ok`/`err` keywords, because
  reserving those words breaks existing code that uses them as identifiers.
- **A generic method with its own `shard` parameter can be called more than
  once** (`pengu_infer.py`): the first call cached its specialized signature and
  the second failed with `E0005 Could not infer type parameter(s)`.
- **A module-level `weave` used as a value carries the module's insignia prefix**
  (`pengu_codegen.py`): inside a prefixed module the definition was emitted as
  `<prefix>_<name>` while the function-pointer reference used the bare name.
- **A local variable shadows a module-level weave of the same name**
  (`pengu_codegen.py`): the local was emitted as a decayed function pointer.
- **`bool to string` is not treated as an owned temporary**
  (`pengu_codegen.py`): `pengu_string_from_bool` returns a `.rodata` view, so
  releasing an interpolation temporary built from it aborted the process
  (`free(): invalid pointer`).
- **`pengu fmt` no longer rewrites string literals** (`pengu_lsp/formatting.py`):
  the line-based normalizer applied its comma/keyword spacing regexes inside
  literals (`"{out},"` → `"{out}, "`) and stripped trailing bytes inside
  triple-quoted strings, silently changing program data. Literals are now
  located first and copied verbatim (verified AST-preserving), and
  `pengu fmt --check std/` is enforced as a CI step.

### Added — documentation

- **`PenguScriptGuideEnglish.md`**: full English translation of the Pengunic
  style guide (same structure, code blocks byte-identical).
- **`LANGUAGE_Spanish.md`**: full Spanish translation of `LANGUAGE.md`.
- **`README.md` is now bilingual** with a `🌍 Languages / Idiomas` selector and
  a Documentation table listing all four documents in both languages.

### Fixed — compiler bugs (post 0.15.0)

- **Bug 5 — `or` / `and` boolean short-circuit vs fallback semantics clarified** (`LANGUAGE.md`, `LANGUAGE_Spanish.md`):
  Clarified in §6.2 that `and` and `or` are strictly boolean logical operators with short-circuiting (`bool and bool -> bool`), not value-coalescing or fallback operators. Unwrapping optionals or results with fallbacks must use `or else` (§12) or `or:` blocks (§12). Documented that eager bounds-checking on array/list indexing in debug mode must be guarded with explicit conditional logic or safe accessors.
  Pinned by `tests/test_compiler_bugfixes_v0150.py::TestBug5_OrAndBoolean`.


- **Bug 6 — `pengu test` bundles in-module tests of imported stdlib modules** (`pengu_codegen.py`):
  Executing `pengu test` on a compilation bundle collected every in-module `test` block from all imported modules in topological order, pulling in hundreds of unit tests across `std.oracle`, `std.scrolls`, `std.tally`, and `std.atlas`.
  Now `collect_declarations` filters out tests from imported `std` modules unless the stdlib module itself is the entry file being tested directly.
  Pinned by `tests/test_compiler_bugfixes_v0150.py::TestBug6_TestBundling`.


- **Bug 4 — Unqualified symbol collisions in `test` blocks across bundled modules** (`pengu_checker.py`, `pengu_codegen.py`):
  In test blocks, unqualified symbol references resolved against symbols from other modules in the same compilation bundle when short names collided (e.g. `is_empty`).
  Now `_check_test_decl` defines the test file's own symbols into the test scope so unqualified symbols resolve locally, and `_translate_expr::calling_expr` prioritizes module weaves matching `current_source_file` before global lookups.
  Pinned by `tests/test_compiler_bugfixes_v0150.py::TestBug4_UnqualifiedInTest`.

- **Bug 3 — Weave-as-value inside `test` blocks loses module prefix** (`pengu_codegen.py`):
  Inside a `test` block, a weave referenced as a first-class value (e.g. callback passed by name) was emitted without its module or insignia prefix because `sym.c_name` was unpopulated or bare in `_translate_expr::var_ref` and `field_access`.
  Now a pre-pass `_resolve_weave_refs_in_stmts` annotates AST nodes with their resolved C names from the module, and `var_ref` / `field_access` fall back to `fn_info` and module prefixes.
  Pinned by `tests/test_compiler_bugfixes_v0150.py::TestBug3_WeaveAsValueInTest`.

- **Bug 2 — Prefix heuristic hazards `flatten`** (`pengu_codegen.py`):
  When calling an imported function whose name matched the prefix of another module's monomorphization (e.g. `loom.flatten` matching `oracle`'s `flatten_maybe_string`), codegen rewrote the call to the unrelated monomorphization.
  Now imported module calls check `fn_info` first, and filter candidate monomorphizations to ensure their AST declared name matches the callee function name exactly.
  Pinned by `tests/test_compiler_bugfixes_v0150.py::TestBug2_PrefixHeuristicHazard`.

- **Bug 1 — `_resolve_call_target` splits at `_` and generates bogus monomorphized methods** (`pengu_infer.py`):
  Calls to generic module weaves containing an underscore (such as `map_size`) fell through to a heuristic that split the name into `("map", "size")`, generating a bogus entry in `symbols.monomorphized_methods` with the return type as receiver.
  Now `_resolve_call_target` guards against names in `self.symbols.generic_functions` and resolved function symbols (`weave`/`function`/`declare`), preventing bogus method monomorphization.
  Pinned by `tests/test_compiler_bugfixes_v0150.py::TestBug1_GenericModuleWeaveResolution`.

- **Bug 7 — Global symbol shadows local variable in `set` target** (`pengu_codegen.py`):
  Target resolution in `_translate_set_target` and `set_stmt` prioritized global `symbols.lookup` over `self.local_vars`, causing local container variables (e.g. `idx: list of int`) to be shadowed by globals from other imported modules (e.g. `idx: int` in `std.invoke`) and emitted as scalar array indexing `idx[i]`.
  Now `self.local_vars` takes precedence over global symbols in all `set` target lookups.
  Pinned by `tests/test_compiler_bugfixes_v0150.py::TestBug7_LocalShadowsGlobal`.

### Changed — ownership contract for `maybe` and rune lifetime (audit #5)

- **`some expr` deep-copies its payload (`pengu_codegen.py`)**: the box owns a
  private copy (`pengu_string_clone`/`pengu_list_clone`/`_pengu_auto_clone_*`), so
  it can no longer dangle when the source local is released. The escape analysis
  follows: boxing an owning payload is no longer an escape, so the source is
  released as usual (this removed a systematic leak).
- **`maybe T` boxes are released (`pengu_codegen.py`, `pengu_checker.py`,
  `pengu_runtime.h`)**: a binding releases the payload it owns and then the box
  (`pengu_banish_string((PenguString *)m.value)`, `free(m.value)`), including POD
  payloads; `pengu_banish_maybe`/`pengu_banish_result` were added. `result` boxes
  stay C-owned (the std/oracle helpers own their payloads).
- **`or:` moves the payload out of a maybe (`pengu_codegen.py`)**: the success
  value is transferred to the result and only the box allocation is freed, so
  `var s is (calling f) or: "fallback"` no longer leaks the box.
- **`x to string` on a string is the identity (`pengu_codegen.py`)**: it used to
  emit `pengu_to_string(x)`, which returned the *same* buffer; the interpolation
  temporary then freed it (`free(): invalid pointer` on a literal).
- **Implicit Imago/Nexus for runes with owned fields (`pengu_types.py`,
  `pengu_codegen.py`)**: a user rune with `string`/`list`/`map`/rune/array fields
  gets private `_pengu_auto_clone_*`/`_pengu_auto_cleanup_*` helpers and is
  deep-copied/released by containers, `some` boxes and `banish` — `list of Rune`
  used to leak every element's fields. std and `.d.pengu` runes are excluded
  (they free their buffers through explicit helpers, which would double-free).
- **Bare array literals as arguments (`pengu_codegen.py`)**: emitted as C99
  compound literals (`((int32_t[3]){ 1, 2, 3 })`) instead of the invalid
  `f({ 1, 2, 3 })`.
- **Iteration temporaries (`pengu_codegen.py`)**: the materialized list of a
  non-lvalue `for v in (calling f)` is released after the loop, and string
  iteration (statement and comprehension) releases each fresh character.
- **String comprehensions (`pengu_infer.py`, `pengu_codegen.py`)**: `for c in
  "abc" then c` works like the `for-in` statement.
- **`ord` (`pengu_codegen.py`)**: both paths guard on `data && len > 0`.
- **`defined(...)` at runtime (`pengu_infer.py`, `pengu_checker.py`)**: rejected
  with E0039 instead of emitting the bare identifier.
- **`or:` error binding (`pengu_checker.py`)**: the implicit `error` is a `let`.

### Fixed — compiler audit #4 (value blocks, nested escape, omen collisions)

- **`void` value blocks (`pengu_codegen.py`, `pengu_checker.py`)**: a `do:`/`if`
  whose value is `void` emits the expression as a statement instead of the
  invalid `void _val_N = f();`, and `var`/`let`/`static var x as void is …` is
  rejected (E0005) because a `void` value cannot be bound.
- **Loop values fed by `if`/`unless` (`pengu_codegen.py`)**: the block node
  reaches the ownership test, which now looks through value blocks — all
  branches fresh → the iteration temporary is released (it leaked one buffer per
  iteration); any borrowed branch → nothing is released.
- **Nested loop values (`pengu_codegen.py`)**: `_expr_owns_value` generalises the
  freshness test to collection elements, so an inner `list of T` produced by a
  loop value or a literal is released after the deep-copying push.
- **Escape analysis (`pengu_checker.py`)**: nested value blocks (`do: do: y`) and
  `else` branches of a value `if` are flattened, a trailing value-`if`/`do`/loop
  counts as the block's value, and the source local is no longer banished while
  the outer value borrows it (a use-after-free).
- **Omen variant collisions (`pengu_checker.py`)**: a `.d.pengu` declaration
  emits variants under the simple C name and an `insignia` module emits them
  prefixed, so only the *emitted* name is registered — a user
  `const KeyboardKey_KEY_LEFT` no longer collides with a binding, while real
  PenguScript omen collisions still report E0046.
- **`_check_or_block` (`pengu_checker.py`)**: the `or:` scope is popped in a
  `finally`.

### Fixed — compiler audit #3 (value blocks, interop, validation)

- **Value blocks (`pengu_codegen.py`)**: a `do:`/`if`/`unless` used as a value now
  snapshots its value into a temporary **before** the scope banish flush, so
  `let x is do: var y as string is …; y.length` no longer reads the nulled buffer.
- **Function-pointer aliases (`pengu_codegen.py`)**: `alias Cb as ref to weave …`
  emits `typedef void (*Cb)(int32_t);` (the identifier must live inside the C
  declarator) instead of invalid C.
- **Lambdas (`pengu_codegen.py`)**: parameter definitions live in their own
  pushed scope; they no longer leak into the global symbol table.
- **Integer literals (`pengu_infer.py`)**: literals outside the `int32` range are
  typed `i64` instead of silently truncating in C.
- **`enchanting` methods (`pengu_checker.py`)**: the implicit-return rules of a
  `weave` (last expression type / `_stmt_always_returns`) now apply, so a method
  that falls off the end into a non-void return type is E0020.
- **Ranges (`pengu_infer.py`)**: `to`/`..` require integer bounds (E0005);
  string bounds used to emit `int64_t = PenguString`.
- **Destructuring + `insignia` (`pengu_codegen.py`)**: fields are looked up by the
  C name, so `let health, who is p` reads the declared fields.
- **`derive Imago`/`Nexus` over arrays (`pengu_types.py`, `pengu_codegen.py`)**:
  an array implements its element's concepts, and the plain-rune Imago/Nexus
  loops now share the field helpers, cloning/releasing array elements per element.
- **Imports (`pengu_checker.py`)**: `file_imports` survives the `when` recursion
  and a module is never queued twice in `symbols.imports`.
- **Inlining (`pengu_codegen.py`)**: the checker's small-weave heuristic
  (`is_inline`) now reaches the emitted C as a plain `static inline` hint
  (`always_inline` stays reserved for the explicit `inline` keyword: forcing it
  on a recursive weave is a hard GCC error).
- **`static var` (`pengu_checker.py`, `pengu_codegen.py`)**: the declaration node
  carries its symbol, so the code generator no longer relies on a popped scope.
- **`or:` fallback typing (`pengu_checker.py`)**: the fallback value must match the
  success type (`maybe int or: "text"` is E0005); returning/void fallbacks remain
  valid. The `or:` result is deliberately **not** treated as owned: `some "x"`
  boxes a borrowed pointer, so releasing it would free `.rodata`.
- **Escape analysis (`pengu_checker.py`)**: block values (`do:`/`if`) participate,
  a view-bound local keeps the source alive only when the view itself escapes,
  and scalar members (`s.len`) are not views (no leak regression).
- **`judge_expr` (`pengu_codegen.py`)**: the `switch` fallback uses
  `__typeof__((subject))` instead of guessing `int32_t`.
- **Omen collisions (`pengu_checker.py`)**: a `pengu_bind`-generated const no
  longer clashes with its own variant.

### Fixed — compiler audit #2 (regressions introduced by the fixes + gaps)

- **Named arguments (`pengu_infer.py`, `pengu_codegen.py`)**: an all-named call is
  now emitted as a *complete positional* argument list with the skipped defaults
  inlined (`calling greet with times is 5` → `greet("world", 5)`), and the checker
  rejects unknown, duplicated and missing required named arguments. Previously a
  skipped default shifted every later value into the wrong parameter.
- **`let` with `or:` (`pengu_codegen.py`)**: the binding is declared non-const
  (the `or:` branch assigns it), which used to be a guaranteed C error.
- **Container aliases (`pengu_codegen.py`, `pengu_infer.py`)**: `.length`/
  `.capacity` map to the real C fields (`len`/`cap`) in direct and chained
  access, and `capacity`/`cap` are rejected for `string`/`slice`.
- **`%=` (`pengu_checker.py`)**: integer-only, matching the binary `%`
  (`set f %= 2.0` on a float is `E0005` instead of invalid C).
- **Views bound to locals (`pengu_checker.py`)**: escape analysis propagates
  through locals bound to a view (`var v is xs at 0`), so the source is left
  alive only when the view escapes; a locally-used view still releases it
  (leak-free) and a returned view can no longer dangle.
- **`for x in (<call>) then …` (`pengu_codegen.py`)**: non-lvalue iterables are
  bound to a temporary, like the `for-in` statement.
- **Comment stripping (`pengu_parser.py`)**: `_strip_comments` is a stateful
  scanner that understands `"`/`'`/`"""`/raw strings and `{…}` interpolation
  across lines. A `#` line inside a triple-quoted string and quotes/`#` inside a
  nested string in `{expr}` are no longer treated as comments (a JSON literal
  starting with `{` no longer swallowed following doc comments).
- **Signature validation completed (`pengu_checker.py`)**: `concept` methods,
  omen variant payloads and *concrete* `enchanting` methods are validated too;
  the old "any `include` disables validation" bail-out was replaced by a
  C-typedef heuristic (`va_list`, `FILE`, `…_t`, uppercase, `_`-prefixed) so a
  PenguScript typo is still reported in files that include a header.
- **Loop values (`pengu_codegen.py`)**: a fresh iteration temporary is released
  right after the deep-copying push (one buffer used to leak per iteration);
  borrowed values and shallow pushes keep the previous ownership rule.
- **`some` (`pengu_codegen.py`)**: an uninferable payload is a compiler error
  instead of a silent `int32_t` assumption.
- **`pengu_to_string` (`pengu_runtime.h`)**: accepts `char*`/`const char*`.

### Fixed — compiler audit round (correctness, codegen, ownership)

- **`insignia` + user types/methods (`pengu_checker.py`, `pengu_codegen.py`)**:
  `RuneType`/`EchoType`/`AliasType` now carry the prefixed `c_name`
  (`insignia my_` ⇒ `my_Player`), so declarations, struct literals and
  `CTypeMapper` agree. Enchanting call sites look the emitted name up in the
  collected weaves instead of rebuilding `<Type>_<method>` from the logical
  name, and `_element_cleanup_fn`/`_element_clone_fn` emit
  `_pengu_cleanup_my_Player` / `_pengu_clone_my_Player`. Previously any project
  using `insignia` with `enchanting` or a `list of Rune` failed to compile.
- **Type-parameter bounds (`pengu_types.py`, `pengu_checker.py`,
  `pengu_infer.py`)**: `BaseType.is_compatible(TypeParam)` is bound-aware for
  built-in concepts, and `typeparam_accepts_value` is now shared. A `T: Num`
  target rejects strings in `return`, `var`/`let` annotations, `maybe T`
  payloads, container elements and struct fields (`E0005`; container methods
  keep `E0018`). Unbounded `T`, `any`, `null` and `T`-to-`T` stay permissive.
- **Named arguments (`pengu_codegen.py`)**: `calling f with b is 2, a is 1` is
  emitted in declaration order (`f(1, 2)`); previously the C arguments kept the
  source order, silently swapping them. Positional/mixed calls and unresolved
  callees are left untouched.
- **Interpolation of wide integers (`pengu_codegen.py`, `pengu_runtime.h`)**:
  `"{x}"` picks `%lld`/`%llu`/`%u` + the matching cast instead of truncating
  every integer to `int32_t`.
- **`pengu_string_format_ex` (`pengu_runtime.h`)**: `%d`/`%f` used
  `snprintf`'s *would-be* length as the append count, which read past the
  64-byte scratch buffer for values like `1e300` (heap-buffer-overflow). It now
  retries into a heap buffer when the value does not fit, and also handles
  `%llu`/`%lld`/`%u`.
- **Compile-time integers (`pengu_comptime.py`, `pengu_infer.py`,
  `pengu_types.py`)**: `08`/`09` no longer crash the checker with a Python
  `ValueError`, and folded `div`/`mod` now truncate toward zero like C
  (`-7 / 2` is `-3`, not `-4`), so `when`/constant folding agrees with runtime.
- **Function/parameter validation (`pengu_checker.py`)**: `weave int` (any C
  keyword) is rejected with `E0035` instead of emitting `int32_t int(...)`, and
  duplicate parameter names are rejected (`E0005`) instead of silently
  overwriting the first one. Methods named after keywords stay valid
  (`<Type>_union`).
- **Ownership (`pengu_checker.py`, `pengu_codegen.py`)**:
  - A string stored into a rune/omen **string field** (`.field`, `with f is s`,
    `with:` builders) is deep-copied *and* the source is still auto-banished, so
    `var p as Player is with name is s` no longer leaks `s`.
  - `banish p` on a `ref to Rune derive Nexus` runs the field destructor before
    freeing the pointee (its fields used to leak).
  - A destructured **rvalue** list (`let a, b is calling make`) releases its
    temporary `PenguList`; a destructured *variable* list is still left alone.
- **Build speed (`pengu_checker.py`)**: imported modules are parsed once per
  (path, mtime, size) instead of once per importing file. A program importing
  several `std` modules re-parsed the graph ~200 times per build; a full bundle
  now takes roughly half the time (the `std_integration_backward_compat`
  release profile went from ~34 s to ~18 s). The `when_top_decl` recursion also
  keeps the precomputed import order instead of re-resolving it.
- **Tests**: `tests/test_audit_fixes.py` (44 regression tests) plus new
  `tests/test_modules_bindings.py::TestInsigniaCEmission` and
  `tests/test_string_composition/leak_slot_field_copy.pengu`.

### Breaking change — strings compose only with `"{expr}"` interpolation

- **`+` and `+=` no longer concatenate strings.** `"a" + b` raises `E0005` and
  `set s += x` raises `E0005`, both pointing at interpolation. `+` is
  numeric-only (integers, floats); the implicit `to string` promotion it used to
  perform is gone, so there is a single, explicit string-composition operator.
  - `ConstFolder` no longer folds `"a" + "b"` into `"ab"`, so the type checker
    always sees (and rejects) string concatenation instead of a silent fold.
  - Migration: `"a" + b` → `"a{b}"`; `a + b` (both strings) → `"{a}{b}"`;
    `prefix + ": " + value` → `"{prefix}: {value}"`;
    `set acc += item` → `set acc is "{acc}{item}"`; `(x to string) + y` →
    `"{(x to string)}{y}"` (the `to string` conversion is kept because
    interpolation formats floats with `%f` while `to string` uses `%g`).
  - The whole standard library (`std/*.pengu`, 27 modules, ~630 call sites) and
    every test program/doc example were migrated; `std` now contains no string
    `+`/`+=`.

### Added — owned string slots are deep-copied (soundness)

- **A `string` written into an owned slot is copied, not aliased
  (`pengu_codegen.py`)**: struct fields (`.field`, `p.field`, `p->field`,
  `with f is …`, `with:` builders), fixed/`list` elements (`xs at 0`) and
  pointee slots (`set essence of p is s`) now receive
  `pengu_string_copy(...)` unless the value is a fresh temporary
  (interpolation, `to string`, `chr`), which is moved in.
  - This fixes a real hazard exposed by the migration: a `derive Nexus` rune
    whose string field had been assigned a static literal (or a borrowed view)
    freed a `.rodata`/foreign pointer on `banish` → `free(): invalid pointer`.
  - The escape analysis was relaxed accordingly: a string local stored into a
    resolvable string slot no longer counts as escaping, so it is still
    auto-banished (the slot owns a copy). Non-string slots and unresolvable
    targets keep the previous conservative behaviour.
- **Interpolation temporaries are released (`pengu_codegen.py`)**: when an
  interpolated expression is a *fresh* string producer that needs a temporary
  (`"{(x to string)}"`), the temporary is freed right after
  `pengu_string_format` copied its bytes. Borrowed views (fields, parameters)
  are never freed.
- **Interpolation inside methods (`pengu_codegen.py`)**: `{expr}` re-inference
  now uses the general node-typing helper, so `"{(calling self.to_date)}"`
  works inside `enchanting` bodies (previously `E0019`/“cannot determine type”).
- **Byte-exact interpolation (`pengu_runtime.h`, `pengu_codegen.py`)**: the
  generated code now calls `pengu_string_format_ex`, which copies `%.*s`
  (PenguString) arguments with `memcpy(…, len)` instead of `printf`'s
  NUL-terminated rule. Interpolation previously truncated any string at its
  first `\0`, so `cipher.decode_base64`, the pure-Pengu hashes in `seal` and
  every migrated `a + (chr n)` site produced corrupted binary data (the `seal`
  extended test hung because of it).
- **Double quotes inside `{expr}` (`pengu_grammar.py`)**: the `STRING` terminal
  now matches a balanced `{…}` group as a unit, so an interpolated expression may
  contain a string literal (`"{calling getenv_or with k, \"\"}"`) without
  terminating the surrounding literal early.

### Known issues — remaining temporary leaks

- An inline freshly allocated argument (`calling f with "a{b}"`) is still not
  released by the caller, and a call result assigned to a local
  (`var s as string is calling f`) is not auto-banished. Freeing them requires a
  *fresh-return contract* (string-returning functions must return owned buffers,
  copying borrowed views), call-result ownership, plus storage copies for statics
  and a retention analysis for `declare`d C functions; anything less dangles on
  `weave identity with s as string into string: return s`. The earlier naive
  prototype produced `free(): invalid pointer` in `std.invoke`.
- Accumulating with `set acc is "{acc}{item}"` in a loop is O(n²); use a
  `list of string` plus a join for hot paths.

### Fixed — Generics soundness gaps (escape chains & `set` bounds)

- **Escape analysis resolves access chains (`pengu_checker.py`)**:
  - `_escape_receiver_type` now walks `dot_access` / `arrow_access` / `at_access`
    steps (`_resolve_chain_type` + `_lookup_field_type_on`) instead of stopping at
    the first identifier. The container behind `self->items`, `self.items`,
    `bag.items`, `bag->items`, `o->inner.items` and `xs at 0` is now found, so a
    `push`/`put` through a rune field is classified by that field's element type.
  - Previously the receiver resolved to the enclosing rune (e.g. `Bag`), whose
    `receiver_deep_copies_on_store` is `False`, so a fresh local string pushed
    through a field was marked as escaping and **never auto-banished** (silent
    leak). No case becomes more restrictive: chains that cannot be resolved keep
    the old conservative behaviour.
- **Bounds are enforced when assigning into a type parameter (`pengu_checker.py`)**:
  - `_check_set_stmt` rejects `set <target of type T: …> is <value>` when the
    value does not implement every bound (`_typeparam_accepts_value`), e.g.
    `set essence of x is "hello"` with `T: Num` — previously accepted and lowered
    to invalid C at monomorphization (`E0005` now, with the violated bound in the
    message). `any`, `null`, another type parameter and unbounded `T` stay
    accepted, so the change is strictly additive.
  - `Type.is_compatible` / `TypeParam.is_compatible` / `BaseType.is_compatible`
    are untouched: the hardening is local to `set`, which keeps the documented
    wildcard behaviour everywhere else (§6.6).
- **Tests**: `tests/test_generics/gap1_self_field_push/` (5 programs, leak-checked),
  `tests/test_generics/leak_self_field_push.pengu` (acceptance),
  `tests/test_generics/gap2_set_typeparam_bounds/` (6 passing + 4 expected-error
  programs). `tests/test_generics_suite.py` and `run_all.sh` now discover
  programs recursively.

### Known issue — fresh call arguments still leak

An inline freshly allocated argument (`calling f with "a{b}"`, previously
`calling f with "a" + b`) is not released by the caller. A local fix was prototyped (bind the argument to a temporary and
banish it after the call) but reverted: PenguScript passes parameters by value
and a callee may **alias** the buffer (e.g. `std.invoke`'s
`add_option_bool` stores `default_val` into a struct field, and `list of Option`
pushes it with `memcpy` because `Option` has no `derive Imago`). Freeing the
caller's temporary then produced `free(): invalid pointer`. A sound fix needs
deep-copying field assignment or a cross-function move/alias analysis; the issue
is documented rather than patched unsoundly.

### Added — Production generics: bounds, `derive`, `cyclus`, `donum`, ownership

- **Concepts & bounds (`pengu_types.py`, `pengu_infer.py`, `pengu_checker.py`)**:
  - New built-in concept `Integrum` (integer refinement of `Num`): `%`, `&`, `|`, `^`, `<<`, `>>` and `~` now require an `Integrum` bound instead of silently accepting floats.
  - `TypeParam.is_int()`/`is_float()`/`is_numeric()` are bound-driven; `Integrum` satisfies `Num`.
  - Every primitive type now participates in `Nexus` (trivial drop) so `derive Nexus` works with scalar fields; `PRIMITIVE_IMPLS` was extended with the missing integer spellings.
  - Bounds are propagated into the bodies of generic `weave`, `enchanting` **and** `bind` declarations (previously the `bind` path dropped them).
  - `TypeParam.is_compatible` is bound-aware: a `T: Num` value is no longer accepted where a `string` is required.
- **`derive` clause (`pengu_checker.py`, `pengu_codegen.py`)**:
  - Runes, algebraic omens and generic instantiations can derive `Par`, `Ordo`, `Vinculum`, `Imago` and `Nexus`; the code generator emits `_eq`/`_cmp`/`_Vinculum`/`_clone`/`_nexus` helpers (only the active variant's payload is inspected for omens).
  - `Imago` and `Nexus` are implied by each other so an owned container can always both copy and release its elements.
  - `derive` on an `echo` is rejected (`E0005`) because `echo` is an untagged C union; comparison on a rune/algebraic omen without the matching derive is `E0049` instead of an undefined-symbol link error.
  - Derived-concept cross-module detection now also consults `symbols.concept_bindings`.
- **`cyclus` modifier, `donum T`, generics polish**:
  - `cyclus` marks intentionally self-referential declarations; by-value cycles still raise `E0050`.
  - `donum T` yields the C zero value `(T){0}` for defaultable type parameters (`where T: Num`, `Par`, `Forma`, `Donum`, …).
  - Generic call resolution now unifies declared parameter types to pick the right monomorphized instance when several exist (`sum of int` vs `sum of float`).
  - Iterating a bare type parameter is rejected with a clear `E0005` pointing at `list of T`/`slice of T`.
  - `enchanting` methods on container receivers (`self`) emit pointer-correct member access (`self->len`) and `for k in self` iterates through the reference.
- **Runtime ownership (`pengu_runtime.h`)**:
  - Documented the `elem_cleanup`/`elem_clone` (and map `key_*`/`val_*`) immutability invariant after `pengu_list_new_owned` / `pengu_map_new_owned`.
  - Added FFI helpers `pengu_list_of_string_from_cstrs` and `pengu_list_of_string_from_cstrv` that build an owned `list of string` from a C array.
  - The generated `PenguList`/`PenguMap` compound literals used by `push`/`put` now carry the ownership callbacks, so deeply nested containers (`list of list of string`) keep their recursive cleanup.
- **Tests & tooling**:
  - `tests/test_generics/` (25 runnable programs + 7 expected-error programs), `tests/test_generics_suite.py`, `run_all.sh`, `run_valgrind.sh` and a README documenting the ownership model.
  - `tests/leakcheck.c`: an `LD_PRELOAD` malloc interposer with a conservative mark-and-sweep at exit, used automatically when `valgrind` is not installed.
  - `pengu run <script>` / `pengu build --entry <file>` now link the Pengu runtime archive, so standalone string/container programs link instead of failing with `undefined reference to pengu_string_copy`.

### Fixed — Generics and memory

- Deep copy and recursive cleanup for nested containers (`list of string`, `list of list of string`, `map of string to list of int`): pushing a container now transfers a *copy*, so the source keeps ownership and is still auto-banished — previously the source was treated as escaped and leaked.
- Escape analysis now classifies `push`/`put`/`insert` by the receiver's clone callbacks (including inside `with …:` blocks) instead of always disabling auto-banish.
- `bind` coherence: two `bind` blocks providing the same `(type, method)` pair raise `E0047` (`DuplicateConceptBindingError`).
- The rune record's `derived_concepts` now includes the `Imago`/`Nexus` pair implied by `derive`, so the checker/codegen see the destructor that the `derive` clause registered.
- Payload-less variants of algebraic omens now produce a tagged-struct value (`(Omen){ .tag = Omen_Variant }`) in value and comparison positions, instead of leaking the raw C enum tag into struct-typed slots (`invalid initializer` before).
- `banish` accepts a value whose type derives `Nexus` (runes and algebraic omens), lowering to the generated `_pengu_cleanup_<T>` destructor; this gives local runes with owned fields a leak-free release path.
- `std/loom.pengu`: `generic_index_of` now declares `where T: Par`.

### Added — Native Generic Container Enchanting (`enchanting map of shard K to shard V:`)

- **Grammar & AST (`pengu_grammar.py`, `pengu_types.py`)**:
  - Container type rules now accept `shard NAME` in element and key/value positions (`type_or_param`), enabling generic container enchanting declarations like `enchanting map of shard K to shard V:` and `enchanting list of shard T:`.
  - Added `shard_param_ref` rule returning `TypeParam`.
  - Added `type_args` property on container types (`MapType`, `ListType`, `SliceType`, `ArrayType`, `MaybeType`, `ResultType`) and implemented `get_type_base_name` and `extract_type_params_from_type` for reliable generic base-type resolution.
- **Type Checker & Symbol Resolution (`pengu_checker.py`, `pengu_infer.py`)**:
  - Generic enchanting method signatures are stored in `symbols.generic_methods[(base_tname, method_name)]`.
  - Added isolation guards ensuring concrete enchanting declarations (such as `enchanting map of string to int:`) do not overwrite or pollute generic method definitions under base container types like `"map"`.
  - Integrated generic method resolution into `pengu_infer.py`, matching generic signatures against concrete container invocations and auto-dereferencing `RefType(MapType)`.
  - Protected built-in container methods (`len`, `put`, `get`, `remove`, `clear`, `contains`, `is_empty`) on container references.
- **On-Demand Monomorphization Pipeline (`pengu_codegen.py`)**:
  - Implemented dynamic monomorphization of generic container methods on demand when invoked on concrete container instances.
  - Deep-scanned method bodies (`_collect_monomorphized_weave`) for calls on `self` to capture and register transitive dependencies (e.g. `m.copy()` delegating to `self.clone()`).
  - Transformed declaration collection into an iterative fixed-point loop, ensuring all transitive monomorphized function declarations and prototypes are registered before translation.
  - Preserved specialized concrete weave names (`c_name`) whenever a concrete specialization is available.
- **C Runtime Helpers (`pengu_runtime.h`)**:
  - Added `pengu_map_keys(const PenguMap *m)` and `pengu_map_values(const PenguMap *m)` supporting generic key and value extraction with deep-copy semantics for `PenguString` and clean auto-banish tracking.
- **Generic Map Operations in `std/atlas.pengu`**:
  - Added Section 0 `enchanting map of shard K to shard V:` providing universal implementations for:
    - Accessors & Predicates: `size`, `is_empty`, `has_key`, `get_or`, `get_safe`.
    - Lifecycle & Duplication: `clone`, `copy`.
    - Bulk Mutations & In-Place Operations: `put_all`, `remove_all`, `rename_key`.
    - Equality & Search: `is_equal`, `find_key_by_value`.
    - Collection Views: `keys`, `values`.
  - Retained 100% backward compatibility for concrete `map of string to int:` and all existing multi-type map blocks (`string->string`, `string->float`, `int->int`, `int->string`, `string->bool`) and module-level wrappers.
- **Zero Memory Leaks & Test Matrix**:
  - Created `tests/std_programs/test_atlas_generic_matrix.pengu` and `tests/test_std_atlas_generic_matrix.py` testing generic enchanting across 5 distinct key-value type combinations (`string->string`, `int->int`, `float->string`, `int->float`, empty maps).
  - Verified 0 memory leaks across container creation, insertion, cloning, renaming, and banishing via GNU `ld` wrapper memory tracking.


### Added — Standard Library Expansion (`std/spark`, `std/scrolls`, `std/oracle`)

- **`std/spark`**: Added 16 new I/O, range, and math helpers alongside updated version constants (`SPARK_VERSION = "0.7.0-spark"`, `STD_VERSION = "0.14.1"`):
  - Formatted and typed output: `print_int`, `println_int`, `print_float`, `println_float`, `print_bool`, `println_bool`.
  - Standard error output: `eprintln` (writing diagnostic messages to `stderr` via C `fputs`/`fputc`).
  - Typed console input: `read_line` (returns trimmed input string), `read_int` (reads and parses integer, fallback 0), `read_float` (reads and parses float, fallback 0.0).
  - Range generators: `range_to(start, end)` (half-open `[start, end)`), `range_inclusive(start, end)` (closed `[start, end]`).
  - Integer math utilities: `min_int(a, b)`, `max_int(a, b)`, `abs_int(n)`, `clamp_int(v, lo, hi)`.
  - Reordered `bool_to_string` before `print_bool` and reimplemented with `judge` pattern matching.
- **`std/scrolls`**: Expanded string enchanting methods with 25+ pure PenguScript algorithms and module-level helpers:
  - Casing transformations: `capitalize`, `title` (with `title_case` alias), `swap_case`, `to_snake_case`, `to_kebab_case`, `upper` (with `to_upper` alias), `lower` (with `to_lower` alias).
  - Searching and metrics: `find`, `rfind`, `count` (with `count_matches` alias), `line_count`, `word_count`.
  - Trimming, alignment, and padding: `lstrip`, `rstrip`, `ljust` (with `pad_right` alias), `rjust` (with `pad_left` alias), `zfill`, `center`, `truncate`.
  - Affixes and partitioning: `removeprefix`, `removesuffix`, `partition`, `split_lines`.
  - Iteration and representations: `chars` (returns `list of string` containing single-character elements), `bytes` (returns `list of int` byte values), `ellipsis(max_len)`.
  - Character and string classifications: `is_lower`, `is_upper`, `is_space` (with `is_whitespace` alias), `is_palindrome`.
  - Three-way string comparison: `compare` (returns -1, 0, or 1 based on lexicographical order, providing canonical string sorting).
  - Module-level `join(parts as list of string, sep as string) into string`.
- **`std/oracle`**: Introduced native `maybe` and `result` container helpers and modernized legacy runes:
  - Native constructors: `some_int`, `some_float`, `some_string`, `some_bool`, `none_int`, `none_float`, `none_string`, `none_bool`.
  - Native unwrappers with panics: `unwrap_int`, `unwrap_float`, `unwrap_string`, `unwrap_bool`.
  - Native fallback unwrappers (`or else`): `unwrap_or_int`, `unwrap_or_float`, `unwrap_or_string`, `unwrap_or_bool`.
  - Native `result of int to string` helpers: `is_ok_int_result`, `is_err_int_result`, `unwrap_int_result`, `unwrap_or_int_result`.
  - Bidirectional bridge conversions: `to_native_int`, `from_native_int`, `to_native_string`, `from_native_string`.
  - Description formatters: `describe_int`, `describe_string`, `describe_result_int`, `describe_result_string`, `describe_maybe_int`, `describe_maybe_string`, `describe_maybe_float`, `describe_maybe_bool`.
  - Reimplemented legacy enchanting methods `is_none`, `is_err`, and `unwrap_or` on `MaybeInt`, `MaybeString`, `ResultInt`, and `ResultString` using `judge` pattern matching.
- **`std/tally`**: Re-architected integer list utilities with `enchanting list of int:` and module-level functional wrappers (`TALLY_VERSION = "0.15.0"`):
  - Object-oriented method calling syntax (`calling xs.sum`, `calling xs.first`, `calling xs.reverse`, `calling xs.sort_asc`) alongside 100% backward-compatible module-level syntax (`calling tally.sum with xs`).
  - Length & access: `len`, `is_empty`, `first`, `last`, `at_or` (with fallback), `at_safe` (returns `maybe int`).
  - Search: `contains`, `index_of`, `count_of`, `find_first_gt`, `find_first_lt`, `last_index_of`.
  - Reductions: `sum`, `product` (returns 1 for empty list as multiplicative identity), `max_val`, `min_val`, `max_index`, `min_index`, `argmin`, `argmax`, `sum_of_squares`.
  - Statistics: `mean` (with `average` alias, documented integer division truncation toward zero), `median` (sorted mid-point), `mode`.
  - Transformations: `reverse`, `sort_asc`, `sort_desc` (insertion sort on freshly allocated lists), `unique`, `dedup`, `flatten`, `abs_all`, `clamp_all`.
  - Selection: `take`, `drop`, `slice_list`.
  - Combination (module-level): `concat`, `zip_sum`, `dot`, `repeat`.
  - Predicates: `is_sorted_asc`, `is_sorted_desc`, `all_positive`, `all_zero`, `any_negative`, `all_in_range`.
  - Filters: `filter_even`, `filter_odd`, `filter_positive`, `filter_negative`, `filter_in_range` (with `filter_range` alias).
  - Mappings: `map_double`, `map_square`, `map_negate`, `map_add_scalar`, `map_increment`.
- **`std/atlas`**: Multi-type map collection expansion across 6 key-value combinations (`ATLAS_VERSION = "0.15.0"`):
  - Supported concrete map types via direct `enchanting`:
    - `map of string to int` (baseline: counters, discrete IDs, numeric config)
    - `map of string to string` (JSON objects, HTTP headers, textual config)
    - `map of string to float` (metrics, stats, weights, embeddings, scientific computing)
    - `map of int to int` (caches, frequency tables, sparse integer arrays)
    - `map of int to string` (ID-to-label lookups, enum stringification tables)
    - `map of string to bool` (feature flags, capabilities, permission sets)
  - Object-oriented method calling syntax across all types (`calling m.keys`, `calling m.keys_sorted`, `calling m.get_or with k, default`, `calling m.update with k, v`, `calling m.rename_key with old_k, new_k`, `calling m.clone`, `calling m.remove with k`, `calling m.clear`).
  - Safe in-place mutation using `with self:` context blocks for reference mutation.
  - Predicates & accessors: `size`, `is_empty`, `has_key`, `has_any_key`, `has_all_keys`, `get_or`, `get_safe`, `find_key_by_value`.
  - Type-specific predicates & reductions:
    - Numeric maps (`string -> int`, `string -> float`, `int -> int`): `all_values_positive`, `any_value_negative`, `values_in_range`, `count_if_value_positive`, `count_if_value_negative`, `sum_values`, `max_value`, `min_value`.
    - Boolean maps (`string -> bool`): `count_true`, `count_false`.
  - Type-specific filters and transformations:
    - Substring and prefix filters (`filter_keys_contains`, `filter_keys_startswith`, `filter_values_contains`).
    - Numeric filters and scale/negate mappings (`filter_values_range`, `map_values_double`, `map_values_scale`, `map_values_negate`).
  - Sorted accessors: `keys_sorted` (alphabetical via `std.scrolls.compare` or numerical) and `values_sorted`.
  - Module-level binary operations per type: `merge_*` (right-precedence), `merge_keep_left_*` (left-precedence), `from_lists_*`.
  - Generic module-level utilities (`shard K, V`): `map_size`, `map_is_empty`, `map_has_key`, `map_get_or`, `map_keys`, `map_values`, `map_put`, `map_remove`, `map_clear`.
  - 100% backward compatible with all pre-existing `std.atlas` functions and calling conventions.
- **`std/coven`**: Expanded unique set collections `SetString` and `SetInt` (`COVEN_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved `new_set_string`, `new_set_int`, and all pre-existing methods (`add`, `contains`, `remove`, `len`, `clear`, `is_empty`).
  - Ritual constructors: top-level `empty_set_string`, `empty_set_int`, `from_list_string`, `from_list_int`, plus static rituals `SetString::empty`, `SetString::from_items`, `SetInt::empty`, `SetInt::from_items`.
  - Full set algebra on both `SetString` and `SetInt`: `union`, `intersect`, `difference`, `symmetric_difference`, `is_subset`, `is_superset`, `is_disjoint`, `equals`, `clone`.
  - Specialized conversions and filters: `SetString.to_list`, `SetString.to_set_int` (symmetric with `to_set_string`), `SetString.filter_starts_with`, `SetString.filter_length_ge`, `SetInt.to_list_int`, `SetInt.sum_ints`, `SetInt.min_int`, `SetInt.max_int`, `SetInt.to_set_string`.
- **`std/chronicle`**: Expanded date, time, calendar, and timer management (`CHRONICLE_VERSION = "0.15.0"`):
  - Clocks & high-resolution measurements: `now_ms`, `time_ms`, `monotonic_ms` millisecond resolution clocks.
  - Native PenguScript wrappers for UTC and local calendar components: `utc_weekday`, `utc_yearday`, `utc_is_dst`, `local_weekday`, `local_yearday`, `local_is_dst`.
  - Date & time formatting and ISO parsing: `now_utc_iso`, `now_local_iso`, `now_date`, `now_time`, `to_iso`, `from_iso`, `to_date_string`, `to_time_string`, `to_datetime_string`.
  - Calendar helpers & day boundaries: `is_leap_year`, `days_in_month`, `days_in_year`, `start_of_day`, `end_of_day`, `today`, `yesterday`, `tomorrow`, `start_of_month`, `start_of_year`.
  - Timestamp arithmetic & relations: `add_seconds`, `add_minutes`, `add_hours`, `add_days`, `add_weeks`, `diff_seconds`, `diff_days`, `is_before`, `is_after`, `is_between`.
  - Human duration formatting & parsing: `format_duration` ("1h 15m 30s"), `parse_duration` ("45s", "30m", "2h", "7d" returning `maybe float`).
  - `rune DateTime`: record holding year, month, day, hour, minute, second, weekday, yearday, is_dst with constructor helpers `datetime_utc`, `datetime_local` and methods `to_iso`, `to_date`, `to_time`.
  - `rune Stopwatch`: high-resolution monotonic timer with ritual constructor `Stopwatch.new`, module wrapper `new_stopwatch`, and methods `elapsed_sec`, `elapsed_ms`, `reset`.
- **`std/compass`**: Expanded cross-platform path manipulation with pure PenguScript and `Path` rune (`COMPASS_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved all pre-existing functions and `Path` methods with clean internal `cp_*` architectural decoupling preventing method/weave symbol collision in codegen.
  - Aliases and extension utilities: `filename`, `file_stem`, `with_extension`, `without_extension`, `with_filename`.
  - Path classification predicates: `is_hidden` (leading dot detection), `is_unc` (UNC network path detection), `has_wildcard` (`*` and `?` detection).
  - Wildcard pattern matching: `matches` implementing non-allocating iterative glob pattern matching.
  - Component analysis: `components` (split normalized components), `has_component` (membership check).
  - System environment & resolution: `cwd`, `expand_user` (expanding `~` via `HOME` or `USERPROFILE`), `absolute` (resolving against current working directory).
  - Enhanced `Path` rune: `ritual from_str`, `ritual cwd`, top-level `new_path`, `current_dir`, and instance methods `components`, `is_hidden`, `matches`, `exists`, `is_file`, `is_dir`, `to_absolute`, `expand_user`, `to_uri` (formatting `file://` URI).
- **`std/archivum`**: Expanded filesystem operations with metadata inspection, search, and binary I/O (`ARCHIVUM_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved all pre-existing file and directory operations with updated `##` docstrings.
  - Binary I/O buffers: `read_bytes`, `write_bytes`, `append_bytes`.
  - Extended metadata inspection: `file_size` (returns `maybe int` bytes), `dir_size` (direct or recursive total bytes), `modified_time`, `created_time`, `accessed_time` (Unix timestamp floats), `permissions` (octal integer mode).
  - Emptiness predicates: `is_empty_file` (0-byte file check), `is_empty_dir` (0-entry directory check).
  - Directory search & find helpers: `find_files` (direct or recursive regular files), `find_dirs` (subdirectories), `find_by_name` (basename match), `find_by_ext` (extension match).
  - Line utilities: `count_lines` (total line count), `read_first_n_lines` (streaming prefix slice).
- **`std/rites`**: Expanded OS, process, environment, and platform utilities (`RITES_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved all 16 pre-existing 0.14.x functions (`getenv`, `setenv`, `unsetenv`, `get_argc`, `get_argv`, `get_args`, `getpid`, `getppid`, `getcwd`, `chdir`, `exit`, `exec`, `spawn`, `uname`, `hostname`, `get_env_keys`).
  - Environment variable accessors: `getenv_or(name, default)` (safe lookup with fallback), `has_env(name)` (presence check), `getenv_int(name)` (parsed maybe int), `getenv_float(name)` (parsed maybe float), `getenv_bool(name)` (parsed maybe bool supporting boolean/numeric representations).
  - Bulk environment management: `get_env_map()` (snapshot key-value map of process environment), `set_env_map(m)` (bulk environment updates), `clear_env()` (removes variables from process environment with explicit safety warning).
  - Variable expansion: `expand_env(s)` and alias `env_substitute(s)` (cross-platform single-pass expansion supporting `$VAR`, `${VAR}`, `%VAR%`, and `$$` escaping).
  - Program arguments: `arg_at_or(idx, default)`, `parse_flags()` (parsing `--key=value` and `--flag` -> `"true"` while ignoring positionals), `has_flag(name)`, `get_flag_value(name)`.
  - Standard user and system directories: `home_dir()` (`USERPROFILE` / `HOME`), `temp_dir()` (`TEMP`/`TMP` with cross-platform fallback), `config_dir()` (`%APPDATA%` / `$XDG_CONFIG_HOME` / `~/.config`), `cache_dir()` (`%LOCALAPPDATA%` / `$XDG_CACHE_HOME` / `~/.cache`), `data_dir()` (`%APPDATA%` / `$XDG_DATA_HOME` / `~/.local/share`).
  - System and platform information: `os_arch()` (compile-time CPU architecture `"x64"`, `"arm64"`, `"x86"`, `"arm"`), `os_family()` (alias of `uname`), `is_windows()`, `is_unix()`, `is_macos()`, `is_linux()`.
  - Path and binary resolution: `which(cmd)` (locating first matching executable on `PATH`), `which_all(cmd)` (returning all candidates on `PATH` with platform-specific delimiters `;`/`:` and Windows executable extensions `.exe`, `.bat`, `.cmd`). Avoids circular imports with `std.archivum` by directly declaring runtime bridge `pengu_c_archivum_is_file`.
  - Process and shell execution: `exec_ok(cmd, args)` (boolean success check), `exec_or_panic(cmd, args)` (asserting exit code 0), `run_shell(cmdline)` (executing raw command line strings through platform shell), `shell_escape(s)` (cross-platform shell escaping), `current_user()` (resolving username across Windows and POSIX).
  - Documented TODOs for POSIX UID/GID manipulation, fork/waitpid, and process output capture.
- **`std/filum`**: Expanded concurrency primitives and added typed channels (`FILUM_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved all pre-existing functions, runes (`Mutex`, `WaitGroup`, `Once`, `Cond`, `AtomicInt`, `Chan`), and methods.
  - New typed channels: `ChanInt`, `ChanString`, `ChanFloat`, and `ChanBool` with rituals `new` (unbuffered) and `with_capacity(cap)` (buffered), methods `.send(v)`, `.recv()`, `.close()`, `.len()`, `.cap()`, `.free()`, and module-level constructors `chan_int`, `chan_string`, `chan_float`, `chan_bool`. Implemented using zero-overhead pointer transmutation into native C channel bridges.
  - Extended AtomicInt operations: `.sub(delta)` (atomic subtraction returning new value), `.inc_and_get()` and `.dec_and_get()` (atomic increment/decrement aliases), `.get_and_set(v)` (atomic swap alias), `.is_zero()` (atomic zero check), `.reset()` (atomic store zero), with corresponding module-level functions `sub_atomic`, `inc_and_get`, `dec_and_get`, `get_and_set`, `is_zero`, `reset_atomic`.
  - System helpers: `sleep_sec(sec as float)` (convenience wrapper with millisecond resolution).
  - Documented TODOs for `Barrier`, `RwLock`, `Semaphore`, `yield_now`, `park`/`unpark`, RAII `with_mutex` blocks, and non-destructive channel status inspection (`is_closed`).
- **`std/whisper`**: Expanded structured logging with instance-based `Logger` rune (`WHISPER_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved all pre-existing global log levels (`LOG_TRACE` through `LOG_FATAL`), ANSI color codes, and module weaves (`log`, `trace`, `debug`, `info`, `warn`, `error`, `fatal`, `get_level`, `set_level`, `get_level_name`, `get_level_color`).
  - `rune Logger`: instance-based structured logger supporting namespaces, independent log levels, optional timestamps, ANSI color toggles, JSON logging, and direct-to-file emission.
  - Ritual constructors: `Logger.new(name)` (LOG_TRACE minimum), `Logger.named(name, min_level)`, `Logger.from_env()` (configured from `LOG_LEVEL`, `RUST_LOG`, etc. with fallback `LOG_INFO`), plus module-level `default_logger()`.
  - Logger instance methods: `.log(level, msg)`, `.trace(msg)`, `.debug(msg)`, `.info(msg)`, `.warn(msg)`, `.error(msg)`, `.fatal(msg)`, `.set_level(level)`, `.get_level()`, `.is_enabled(level)`, `.enable_timestamp()`, `.disable_timestamp()`, `.enable_color()`, `.disable_color()`, `.to_file(path)` (redirecting logs to disk with silent failure fallback), `.child(subname)` (hierarchical child logger naming `parent.child`), `.log_json(level, msg, fields)`.
  - Global conveniences: `set_level_from_string(s)` (case-insensitive string parsing), `set_level_from_env()`, `is_enabled(level)`, `log_json(level, msg, fields)`, `fatal_and_exit(msg, code)`.
  - Level catalog: `log_levels()` returning ordered list of standard level names.
- **`std/cipher`**: Expanded cryptographic encodings, binary/text transforms, RFC 8259 JSON manipulation, and validation (`CIPHER_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved all 0.14.x baseline functions (`encode_base64`, `decode_base64`, `is_base64`, `parse_json`, `stringify_json`, `pretty_json`, `parse_value`).
  - Base64 & variants: `encode_base64_url`, `decode_base64_url`, `encode_base64_unpadded`, `encode_hex`, `decode_hex`, `is_hex`, `encode_base32`, `decode_base32`, `is_base32`.
  - String enchanting methods: `to_base64`, `from_base64`, `to_base64_url`, `from_base64_url`, `to_hex`, `from_hex`, `to_base32`, `from_base32`.
  - RFC 8259 JSON escaping & unescaping: fixed quote and backslash escaping bug in `stringify_json` and `pretty_json`; added standalone `json_escape` and `json_unescape`.
  - JSON arrays: `parse_json_array`, `stringify_json_array`.
  - Typed JSON getters: `json_get`, `json_get_int`, `json_get_float` (pure PenguScript decimal float parser bypassing runtime `sizeof(double)` bug), `json_get_bool`, `json_get_string`.
  - Navigation & transformation: `json_deep_clone`, `json_merge`, `json_path` (dot/bracket path traversal), `json_parse_at`.
  - Validation & classification: `omen JsonKind`, `json_kind_of`, `is_valid_json`.
- **`std/loom`**: Expanded functional sequence processing and generic algorithms (`LOOM_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved all 0.14.x baseline functions (`range`, `repeat`, `take`, `skip`, `chain`, `chunks`, `windows`, `sum`, `product_num`, `max_int`, `min_int`).
  - Reductions & aggregates: `mean`, `sum_squares`, `running_sum`, `running_max`, `running_min`, `differences`.
  - Predicates & sorting checks: `any_zero`, `all_equal`, `is_strictly_asc`, `is_strictly_desc`, `is_sorted_asc`, `is_sorted_desc`.
  - Transformations & combinatorics: `zip_with`, `zip_longest`, `enumerate`, `interleave`, `round_robin`, `rotate_left`, `rotate_right`, `intersperse`, `pairwise`, `flat_map_identity`.
  - Set-like sorted operations: `union_sorted`, `intersect_sorted`, `difference_sorted`, `symmetric_difference_sorted`.
  - Search & indexing: `find_first`, `find_last`, `binary_search`, `count_if_even`, `count_if_positive`, `index_min`, `index_max`.
  - Structural modifications: `insert_at`, `remove_at`, `replace_at`, `swap_at`, `pad_left`, `pad_right`.
  - Summary statistics: `median`, `mode`, `variance`, `stddev` (utilizing `arithmancy.sqrt`), `percentile`.
  - Generic algorithms (`shard T`): `first_or`, `generic_take`, `generic_take_last`, `generic_reverse`, `generic_chain`, `generic_index_of`.
- **`std/ledger`**: Expanded CSV/TSV processing, matrix operations, and table abstractions (`LEDGER_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved all 0.14.x baseline functions (`escape_field`, `detect_delimiter`, `parse_line`, `parse_csv`, `parse_tsv`, `to_csv_string`, `to_tsv_string`, `read_csv`, `read_tsv`, `write_csv`, `write_tsv`).
  - Enhanced parsing: `parse_csv_strict` (validating uniform row lengths), `parse_csv_nocomments` (skipping `#` comment rows), `parse_csv_skip` (skipping header lines), `parse_line_strict`, `parse_csv_normalized`.
  - `rune CsvTable`: tabular representation with rituals `from_csv`, `from_rows`, and methods `row_count`, `column_count`, `has_column`, `column_index`, `get`, `get_or`, `column`, `row_as_map`, `to_csv`.
  - Matrix operations (`enchanting list of list of string`): `row_count`, `column_count`, `is_rectangular`, `column`, `transpose`.
  - Key-value conversions: `parse_csv_as_pairs`, `parse_csv_key_value`, `write_key_value_map`.
  - Generators & formatters: `escape_field_rfc4180`, `escape_field_backslash`, `to_csv_string_no_trailing_newline`, `to_csv_string_crlf`, `write_csv_safe` (atomic temp-file write and replacement).
- **`std/lot`**: Expanded randomness, sampling, combinatorics, and probability distributions (`LOT_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved all 0.14.x functions (`seed`, `rand_int`, `rand_float`, `rand_range`, `rand_range_float`, `rand_normal`, `rand_exp`, `rand_bool`, `rand_poisson`).
  - Constants & bounds: `LOT_VERSION`, `rand_max`.
  - Sampling & selection: `choice`, `choice_string`, `choice_weighted`, `choice_weighted_string`, `shuffle`, `shuffle_string`, `sample`, `sample_with_replacement`, `sample_string`, `permutation`.
  - Booleans & signs: `rand_coin`, `rand_bit`, `rand_sign`, `rand_bool_with`.
  - Aliases: `rand_between` (alias of `rand_range`), `rand_uniform` (alias of `rand_range_float`), `rand_gauss` (alias of `rand_normal`).
  - Random strings: `rand_alpha`, `rand_digit_string`, `rand_alnum_string`, `rand_hex_string`, `rand_password` (with optional symbols), `rand_bytes_hex`, `rand_from_charset`.
  - Distributions (backed by `std.arithmancy`): `rand_triangular`, `rand_lognormal`, `rand_weibull`, `rand_gamma` (Marsaglia-Tsang), `rand_beta`.
- **`std/ward`**: Modernized and expanded assertions, invariants, and failure diagnostics (`WARD_VERSION = "0.15.0"`):
  - **Informative failure messages**: Rewrote failure messages across all pre-existing assertions (`assert_eq_int`, `assert_eq_string`, `assert_eq_bool`, `assert_true`, `assert_false`, `assert_ne_int`, `assert_ne_string`, `assert_ne_bool`, `assert_present_int`, `assert_present_string`, `assert_none_int`, `assert_none_string`, `assert_ok_int`, `assert_ok_string`, `assert_err_int`, `assert_err_string`) to display expected vs actual values, significantly improving debugging productivity.
  - Floating-point assertions: `assert_eq_float`, `assert_ne_float`, `assert_almost_eq` with configurable `epsilon` tolerance.
  - Relational & range comparisons: `assert_gt_int`, `assert_ge_int`, `assert_lt_int`, `assert_le_int`, `assert_gt_float`, `assert_ge_float`, `assert_lt_float`, `assert_le_float`, `assert_in_range_int`, `assert_in_range_float`.
  - String helpers: `assert_string_contains`, `assert_string_starts_with`, `assert_string_ends_with`, `assert_string_empty`, `assert_string_not_empty`.
  - Container assertions: `assert_eq_int_list`, `assert_eq_string_list`, `assert_list_empty_int`, `assert_list_not_empty_int`, `assert_list_len_int`, `assert_map_has_key`, `assert_map_not_has_key`.
  - Native `maybe`/`result` assertions (`shard T`): `assert_maybe_present`, `assert_maybe_none`, `assert_result_ok`, `assert_result_err`, `assert_result_ok_int`, `assert_result_err_int`.
  - Expectations & non-panicking checks: `expect_eq_float`, `expect_ne_int`, `expect_ne_string`, `expect_ne_bool`, `expect_gt_int`, `expect_ge_int`, `expect_lt_int`, `expect_le_int`, `expect_present_int`, `expect_present_string`, `expect_ok_int`, `expect_ok_string`, `check_eq_bool`, `check_eq_float`, `check_present_int`, `check_present_string`, `check_ok_int`, `check_ok_string`.
  - Invariant helpers: `fail`, `fail_unreachable`, `unreachable`.
- **`std/invoke`**: Expanded CLI parsing with subcommands, typed options, and typo suggestions (`INVOKE_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved existing `Parser` and `ParseResult` workflows.
  - Subcommands: `rune Subcommand`, `Parser.add_subcommand`, routing and `ParseResult.subcommand`.
  - Syntax improvements: `--key=value`, `-k=value`, `--no-flag` boolean negation, `--` positional argument terminator.
  - Typed options: `add_option_int`, `add_option_float`, `add_option_bool`, with corresponding `ParseResult.get_int`, `get_int_or`, `get_float`, `get_float_or`, `get_bool`, `get_bool_or`.
  - Multi-value options: `rune MultiOption`, `add_option_multi`, `ParseResult.get_all`.
  - Version handling: `Parser.set_version`, automatic `--version` and `-V` response.
  - Typo suggestions: Levenshtein distance matching (dist <= 2) offering helpful "Did you mean --<option>?" diagnostics.
  - Parse variants: `parse_no_exit` (non-terminating parse for tests and embedding), `parse_or_exit`, `parse_or_usage`.
  - Help formatting: Aligned column layout, categorized sections (`Usage`, `Description`, `Arguments`, `Subcommands`, `Options`), `usage_string`, `full_help`.
- **`std/regulus`**: Expanded PCRE2 regular expression engine and string enchanting methods (`REGULUS_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved existing `compile`, `match`, `search`, `find_all`, `replace`, `is_match`, `is_full_match`.
  - Match extraction and offsets: `match_count`, `match_at`, `match_offsets` (flat list of start/end byte offsets).
  - Pattern utilities & case-folding: `escape` (escaping PCRE meta-characters), `flag_is_case_insensitive`, `is_valid_pattern`.
  - Splitting: `split` (split string by regex delimiter), `split_n` (limited count splitting).
  - Advanced replacements: `replace_all` (global regex substitution), `replace_fn` (functional callback replacement bridge).
  - String enchanting methods: `to_regex`, `matches_regex`, `regex_replace`, `regex_split`.
- **`std/precis`**: Expanded HTTP client/server abstractions and URL utilities (`PRECIS_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved `get`, `post`, `head`, `put`, `delete_req`, `serve_http`, `url_encode`, `url_decode`, `parse_url`, `build_url`.
  - Request and Response builders: `rune Request` and `rune Response` supporting method, URL, headers map, body, status code, query parameters.
  - Ritual constructors: `Request.get`, `Request.post`, `Request.new`, `Response.ok`, `Response.json`, `Response.text`, `Response.status`, `Response.error`.
  - Instance methods: `Request.header`, `Request.with_header`, `Request.with_query_param`, `Response.header`, `Response.with_header`, `Response.is_success`.
  - Status classification helpers: `is_informational`, `is_success`, `is_redirect`, `is_client_error`, `is_server_error`, `status_text` (RFC 9110 status message mapping).
  - URL helpers: `url_join`, `url_query_encode` (map to query string), `url_query_decode` (query string to key-value map).
- **`std/parchment`**: Expanded libxml2-backed XML and HTML DOM parser (`PARCHMENT_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved `parse_xml`, `parse_html`, `to_string`, `doc_to_string`, `find`, `find_all`, `attr`, `set_attr`, `text`, `set_text`, `create_element`, `create_text`, `append_child`.
  - Node navigation & mutation: `remove_child`, `Node.attr`, `Node.set_attr`, `Node.text`, `Node.set_text`, `Node.free`.
  - CSS/class queries: `find_by_id`, `find_by_class`, `find_all_by_class`, `has_class`, `add_class`, `remove_class`.
  - Tag utilities: `is_void_element`, `normalize_tag`, `is_valid_tag_name`.
  - HTML text extraction: `strip_html_tags` (removes markup preserving text), `extract_text` (recursively extracts descendant text).
  - Enchanting methods: `enchanting Node:`, `enchanting Document:`, string enchantments `parse_xml`, `parse_html`.
- **`std/seal`**: Expanded cryptographic hashing, HMAC, and verification (`SEAL_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved `sha256`, `sha1`, `md5`, `crc32`, `adler32`, `hex_digest`, `base64_encode`, `base64_decode`, `zlib_compress`, `zlib_decompress`, `gzip_compress`, `gzip_decompress`.
  - Keyed HMAC (RFC 2104): `hmac_sha256`, `hmac_sha256_hex`, `hmac_sha1`, `hmac_md5`.
  - Constant-time verification: `constant_time_eq` (timing attack mitigation), `verify_sha256`, `verify_hmac_sha256`.
  - String enchanting methods: `to_sha256`, `to_md5`, `to_crc32`, `to_gzip`, `from_gzip`.
- **`std/ffi`**: Expanded null-safe C foreign function interface and canonical patterns (`FFI_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved `string_from_cstr`, `cstr_from_string`, `slice_from_ptr`.
  - Platform architecture & sizes: `SIZEOF_POINTER`, `SIZEOF_INT`, `SIZEOF_FLOAT`, `SIZEOF_BYTE`, `SIZEOF_CHAR`, `SIZEOF_BOOL`, `SIZEOF_SHORT`, `SIZEOF_LONG`, `SIZEOF_SIZE_T`, `pointer_size`, `pointer_size_bytes`.
  - Generic type queries: `size_of shard T`, `alignment_of shard T`.
  - Pointer & NULL utilities: `null_void`, `null_char`, `null_byte`, `is_null`, `is_valid`, `ptr_is_valid`, `ptr_eq`.
  - Generic collection bridges: `list_from_ptr shard T`, `map_from_entries shard K, V`.
  - Raw memory operations: `memcpy_raw`, `memset_raw`.
  - String & buffer conversions: `string_from_cstr_n`, `string_from_bytes`, `bytes_from_string`.
  - 10 Canonical C Interop Patterns documented in module header.
- **`std/arithmancy`**: Game-ready linear algebra and 2D/3D mathematics (`ARITHMANCY_VERSION = "0.15.0"`):
  - 100% backward compatible: preserved all 0.14.x math helpers (`abs_i`, `abs_f`, `min_i`, `max_i`, `min_f`, `max_f`, `clamp_i`, `clamp_f`, `sqrt_f`, `pow_f`, `sin_f`, `cos_f`, `tan_f`, `floor_f`, `ceil_f`, `round_f`, `deg_to_rad`, `rad_to_deg`).
  - Mathematical constants: `PI`, `TAU`, `E`, `EPSILON`.
  - Scalar functions: `sign_i`, `sign_f`, `lerp_f`, `smoothstep_f`, `asin_f`, `acos_f`, `atan_f`, `atan2_f`, `hypot_f`.
  - `rune Vec2`: 2D vector with rituals `new`, `zero`, `unit_x`, `unit_y`, and methods `add`, `sub`, `scale`, `dot`, `cross`, `length`, `length_sq`, `normalize`, `distance`, `lerp`.
  - `rune Vec3`: 3D vector with rituals `new`, `zero`, `unit_x`, `unit_y`, `unit_z`, and methods `add`, `sub`, `scale`, `dot`, `cross`, `length`, `length_sq`, `normalize`, `distance`, `lerp`.
  - `rune Vec4`: 4D vector with rituals `new`, `zero`, and methods `add`, `sub`, `scale`, `dot`, `length`, `normalize`.
  - `rune Mat4`: 4x4 matrix with 16 explicit fields `m00..m33`, rituals `identity`, `zero`, `translation`, `scaling`, `rotation_x`, `rotation_y`, `rotation_z`, `look_at`, `perspective`, `orthographic`, and methods `multiply`, `transpose`, `transform_vec4`, `transform_point3`.
  - `rune Quat`: Quaternion with rituals `identity`, `from_axis_angle`, `from_euler`, and methods `multiply`, `length`, `normalize`, `conjugate`, `slerp`, `to_mat4`.

### Fixed — Codegen Method Symbol Collision & Generic Monomorphization

- **`pengu_parser/pengu_codegen.py`**:
  - In `_lookup_type_fn`: checked `self.current_subst_map` during AST conversion within function bodies, ensuring generic type parameters (`shard T`) resolve to their monomorphized concrete types (`int`, etc.) instead of raising undefined type errors.
  - In `_collect_top_stmt`, guarded `self.fn_info[name]` registration with `if enchanted_type is None:`. Previously, instance methods declared in `enchanting T:` unconditionally overwrote standalone top-level functions with the same name in `self.fn_info[name]`, causing bare function calls (e.g. `calling log with ...`, `calling get_level`) within standard library modules to resolve to instance methods (e.g. `Logger_log`, `Logger_get_level`) and trigger C compiler signature mismatch errors.

### Fixed — Standard Library System Tier Review Fixes

- **`std/chronicle`**:
  - Fixed `now_local_iso`, `now_date`, and `now_time` which previously formatted UTC strings via `format_now`; they now correctly decompose the current timestamp via `datetime_local` using the OS local timezone.
  - Fixed `from_iso` to parse ISO 8601 strings (both with and without trailing "Z", as well as date-only "YYYY-MM-DD" and space-separated datetime), guaranteeing an exact second-precision round-trip `from_iso(to_iso(ts)) == ts` without timezone distortion.
  - Simplified `is_before` and `is_after` to return direct float comparison expressions (`a < b`, `a > b`).
  - Improved `parse_duration` to accept purely numeric strings as seconds (e.g. `"45"` -> 45.0s), and replaced non-idiomatic presence check with `if val_opt is not present:`.
  - Removed unused dead import `import std.oracle`.
- **`std/compass`**:
  - Fixed `cp_suffixes` to ensure only non-empty suffix strings are returned (`if slen > 0:`), preventing trailing dot edge cases (e.g. `"file."`) from emitting empty suffixes.
  - Eliminated dead code `if seg == ".": set i is i` in `cp_normalize`.
  - Updated `cp_split` to push platform-specific root separator (`cp_sep`) instead of hardcoded `"/"`.
  - Updated `Path.to_uri` to percent-encode spaces as `"%20"` and documented best-effort RFC 3986 file URI conversion.
  - Documented in `expand_user` that named user expansions (`~user`) are not supported and are returned unchanged.
- **`std/archivum`**:
  - Documented complete `metadata` contract: all returned map keys (`"size"`, `"is_file"`, `"is_dir"`, `"is_symlink"`, `"modified"`, `"created"`, `"accessed"`, `"permissions"`) and their value string formats.
  - Fixed variable reference in `find_by_ext`: `set ext_target is "." + ext_target` (previously referenced `extension`).
  - Documented non-transactional partial failure semantics in `copy_tree`.

### Fixed — Standard Library Concurrency, OS, and Logging Review Fixes (Batch 3)

- **`std/filum`**:
  - **`ChanString.send` Heap Ownership**: Fixed string buffer ownership in `ChanString.send` by allocating an owned deep copy of the string buffer via runtime bridge `pengu_string_copy`. Prevents use-after-free and memory corruption when strings created inside temporary function scopes are enqueued and subsequently auto-banished upon scope exit. Documented receiver ownership semantics and added cleanup safety warning on `free`.
  - Added naming rationale note on module-level functions `sub_atomic`, `add_atomic`, and `reset_atomic` explaining the `_atomic` suffix to avoid collisions with arithmetic or reset operations.
- **`std/whisper`**:
  - **JSON String Escaping**: Implemented internal `_json_escape` escaping backslashes (`\`), double-quotes (`"`), and whitespace control characters (`\n`, `\r`, `\t`) in `log_json` and `Logger.log_json` across keys, values, and messages, preventing invalid JSON formatting on structured log lines.
  - **Dual-Level Logging Documentation**: Added comprehensive architectural documentation in module header explaining the relationship between the global runtime log level (set via `set_level`/`set_level_from_env`) and instance-based `Logger` runes which evaluate independently against their own `min_level`.
  - Clarified `Logger.to_file` docstring noting lazy file open and append behavior on each emission via `std.archivum`, with silent discard if file writing fails.
- **`std/rites`**:
  - Removed unused dead imports `import std.oracle` and `import std.tally`.
  - Fixed `getenv` docstring to clarify that variables set to empty strings return `some ""`, not `maybe none`.
  - Added support for `%%` -> `%` escape handling in `expand_env`.
  - Documented that `which_all` checks for regular file existence in PATH directories via `pengu_c_archivum_is_file` on POSIX systems, noting that checking executable permission bits requires a dedicated runtime permission bridge.
- **Compiler / Codegen Regression Test**:
  - Added `tests/test_codegen_method_shadowing.py` verifying both compile-time bundle generation and runtime execution ensuring methods declared in `enchanting T:` do not shadow top-level functions with the same name.

### Fixed — Standard Library Data Tier Review Fixes (Batch 4)

- **`std/cipher`**:
  - **JSON Control & Unicode Character Unescaping**: Fixed asymmetric escape/unescape behavior in `json_unescape` and `json_read_str` by adding hex decoding for `\uXXXX` sequences. ASCII control characters (`\u0000`–`\u001F`) decode directly to their raw byte values, and unicode code points up to `0xFFFF` are properly UTF-8 encoded, ensuring RFC 8259 round-tripping with `json_escape`.
  - **Base64 Unpadded Aliases**: Added `encode_base64_unpadded` and `decode_base64_unpadded` aliases alongside `_nopad` variants.
  - **Decimal Float Parser**: Implemented pure PenguScript decimal float parser in `json_get_float` supporting scientific notation (`e`/`E`), explicit signs (`+`/`-`), and strict trailing syntax, cleanly bypassing the C runtime bridge `sizeof(double)` bug.
  - **Docstrings**: Clarified string format expectations in `json_get_string` and confirmed non-destructive immutable map traversal in `json_path`.
- **`std/loom`**:
  - Fixed `rotate_right` returning `list of int` expression on empty list by creating and returning an explicit local variable `var empty as list of int is list of int\n return empty`.
  - Added `flatten` alias for `flat_map_identity`.
  - Delegated `pairwise` to `calling windows with items, 2`.
- **`std/ledger`**:
  - Reordered `parse_csv_skip` parameters to put `skip_rows as int is 0` at the end (`data as string, delimiter as string is ",", skip_rows as int is 0`).
  - Added `csv_table_from_csv` alias for `CsvTable.from_csv`.
  - Updated `to_csv_string_no_trailing_newline` to strip both `\r\n` (CRLF) and `\n` (LF) endings.
  - Clarified `write_csv_safe` docstring explaining temp-file rename semantics and lack of crash atomicity due to runtime unlink-before-rename.
- **Compiler / Codegen Regression Test**:
  - Added `tests/test_codegen_generic_subst.py` verifying both compile-time bundle generation and runtime execution ensuring `shard T` type substitutions in local constructors monomorphize cleanly.

### Tests — Standard Library Expansion

- Added `tests/std_programs/test_spark_extended.pengu` testing all 16 new I/O, range, and math helpers.
- Added `tests/std_programs/test_scrolls_extended.pengu` testing all new string methods, casing, searching, padding, and ordering.
- Added `tests/std_programs/test_oracle_extended.pengu` testing native maybe/result constructors, unwrappers, bridges, and judge reimplementations.
- Added `tests/std_programs/test_tally_extended.pengu` testing all 43 list manipulation, reduction, sorting, and transformation functions.
- Added `tests/std_programs/test_atlas_extended.pengu` testing map predicates, access, combination, filtering, and sorting.
- Added `tests/std_programs/test_coven_extended.pengu` testing SetString and SetInt set algebra, rituals, conversions, and predicates.
- Added `tests/std_programs/test_chronicle_extended.pengu` testing calendar components, formatting, ISO parsing, day boundaries, arithmetic, and Stopwatch.
- Added `tests/std_programs/test_compass_extended.pengu` testing pure PenguScript path operations, wildcards, glob matching, CWD, and Path rune methods.
- Added `tests/std_programs/test_archivum_extended.pengu` testing binary I/O, file/dir sizes, timestamps, permissions, emptiness, and search.
- Added `tests/std_programs/test_rites_extended.pengu` testing OS environment, arguments, directories, architecture, search, and process helpers.
- Added `tests/std_programs/test_filum_extended.pengu` testing typed channels (ChanInt, ChanString, ChanFloat, ChanBool), extended atomics, and system helpers.
- Added `tests/std_programs/test_whisper_extended.pengu` testing Logger rune, level parsing, rituals, child loggers, JSON output, and file redirection.
- Added `tests/std_programs/test_cipher_extended.pengu` testing RFC 8259 JSON escaping/unescaping, control characters, JSON array manipulation, path navigation, and base64/hex/base32 encoding.
- Added `tests/std_programs/test_loom_extended.pengu` testing reductions, combinatorics, windows, zip, rotate, statistics, and generic shard T helpers.
- Added `tests/std_programs/test_ledger_extended.pengu` testing CSV/TSV parsing variants, matrix enchanting, CsvTable rune rituals, and key-value serialization.
- Added `tests/std_programs/test_lot_extended.pengu` testing randomness draws, sampling, shuffling, strings, and distributions.
- Added `tests/std_programs/test_ward_extended.pengu` testing all new asserts, float tolerance, string/list/map helpers, native maybe/result assertions, and checks.
- Added `tests/std_programs/test_invoke_extended.pengu` testing subcommands, inline key=val, typed options, multi options, typo suggestions, and terminator.
- Added `tests/std_programs/test_regulus_extended.pengu` testing PCRE2 matching, search, offsets, escape, split, and string enchantments.
- Added `tests/std_programs/test_precis_extended.pengu` testing HTTP Request/Response builders, URL query codecs, and status predicates.
- Added `tests/std_programs/test_parchment_extended.pengu` testing XML/HTML parsing, DOM class queries, tag utils, and text stripping.
- Added `tests/std_programs/test_seal_extended.pengu` testing HMAC SHA256/SHA1/MD5, constant-time verification, and hash enchantments.
- Added `tests/std_programs/test_ffi_extended.pengu` testing NULL safety, architecture constants, pointer comparisons, generic list/map from pointers, and string views.
- Added `tests/std_programs/test_arithmancy_extended.pengu` testing scalar helpers, constants, Vec2, Vec3, Vec4, Mat4, and Quat conversions and slerp.
- Added pytest test runners parameterized over `debug` and `release` compilation profiles:
  - `tests/test_std_spark_extended.py`
  - `tests/test_std_scrolls_extended.py`
  - `tests/test_std_oracle_extended.py`
  - `tests/test_std_tally_extended.py`
  - `tests/test_std_atlas_extended.py`
  - `tests/test_std_coven_extended.py`
  - `tests/test_std_chronicle_extended.py`
  - `tests/test_std_compass_extended.py`
  - `tests/test_std_archivum_extended.py`
  - `tests/test_std_rites_extended.py`
  - `tests/test_std_filum_extended.py`
  - `tests/test_std_whisper_extended.py`
  - `tests/test_std_cipher_extended.py`
  - `tests/test_std_loom_extended.py`
  - `tests/test_std_ledger_extended.py`
  - `tests/test_std_lot_extended.py`
  - `tests/test_std_ward_extended.py`
  - `tests/test_std_invoke_extended.py`
  - `tests/test_std_regulus_extended.py`
  - `tests/test_std_precis_extended.py`
  - `tests/test_std_parchment_extended.py`
  - `tests/test_std_seal_extended.py`
  - `tests/test_std_ffi_extended.py`
  - `tests/test_std_arithmancy_extended.py`
  - `tests/test_std_backward_compat.py` (verifying legacy 0.14.x collections API surface)
  - `tests/test_std_system_backward_compat.py` (verifying legacy 0.14.x system tier and batch 3 API surfaces)
  - `tests/test_std_data_backward_compat.py` (verifying legacy 0.14.x data processing API surface)
  - `tests/test_std_util_backward_compat.py` (verifying legacy 0.14.x utility API surface)
  - `tests/test_std_integration_backward_compat.py` (verifying legacy 0.14.x integration and math API surfaces)

### Documentation — Standard Library Expansion

- Added comprehensive `##` docstrings for all new methods and functions in `std/spark.pengu`, `std/scrolls.pengu`, `std/oracle.pengu`, `std/tally.pengu`, `std/atlas.pengu`, `std/coven.pengu`, `std/chronicle.pengu`, `std/compass.pengu`, `std/archivum.pengu`, `std/rites.pengu`, `std/filum.pengu`, `std/whisper.pengu`, `std/cipher.pengu`, `std/loom.pengu`, `std/ledger.pengu`, `std/lot.pengu`, `std/ward.pengu`, `std/invoke.pengu`, `std/regulus.pengu`, `std/precis.pengu`, `std/parchment.pengu`, `std/seal.pengu`, `std/ffi.pengu`, and `std/arithmancy.pengu` detailing signatures, ownership models, and edge cases.
- Updated `LANGUAGE.md` §19.1 module catalog entries for all standard library modules across Batches 1 through 6, declaring PenguScript 0.15.0 standard library Feature-Complete.
- Updated `LANGUAGE.md` §12 with cross-reference note directing users to `std.oracle` native container helpers.
- Updated `README.md` standard library overview with expanded capability descriptions.

### Fixed

- **Codegen (`_translate_binding_if` in `pengu_codegen.py`)**: Fixed duplicate closing braces emission (`}\n  }else {`) in if-binding statements with `else` blocks, properly formatting the branch closure as `} else {` without orphan braces. (Bug 1.1)
- **Codegen (`_build_call_args` in `pengu_codegen.py`)**: Fixed variadic `many T` call argument construction when passed a single `ArrayType` (such as `[1, 2, 3]` or an array variable), eliminating invalid nested brace initializers `{ { 1, 2, 3 } }` and correctly populating slice length `.len = N`. (Bug 1.2)
- **Codegen (`_translate_expr_impl` in `pengu_codegen.py`)**: Implemented code generation for built-in method calls (`.push`, `.append`, `.pop`, `.clear`, `.len`, etc.) on `list` and `map` collections (and references to them) inside `with target:` blocks, emitting C runtime calls (`pengu_list_push`, `pengu_map_put`, etc.) instead of invalid C++ dot member calls (`target.push(...)`). (Bug 1.3)
- **Checker (`_check_set_stmt` in `pengu_checker.py`)**: Added missing semantic validation in `normal_target` and `with_target` assignments for nonexistent fields on runes, correctly raising `E0013: SemanticError` ("Rune 'T' has no field 'f'") instead of silently ignoring unknown fields. (Bug 2.1)
- **Checker (`_check_set_stmt` in `pengu_checker.py`)**: Added intermediate type validation for nested field accesses (`set p.hp.sub is v` and `with p: set .hp.sub is v`), rejecting attempts to access fields on non-rune types with `E0013`. (Bug 2.2)
- **Checker (`_resolve_call_target` in `pengu_infer.py`)**: Fixed built-in collection method resolution under `with target:` when targeting a reference (`ref to list of T` or `ref to map of K to V`) by unwrapping `base_with_type` before checking `isinstance(base_with_type, (ListType, MapType))`. (Bug 2.3)
- **Checker (`_check_set_stmt` in `pengu_checker.py`)**: Added complete validation for arrow access in `set` statements (`set ptr->unknown_field is v` and `set p->field on non-reference`), raising `E0013` and `E0003` respectively. (Gap 4.2)
- **Docstrings & Translations (`pengu_infer.py`, `pengu_parser.py`, `pengu_checker.py`)**: Translated Spanish `NonExhaustiveJudgeError` messages to English, updated `PenguParser` docstring version to `v0.14.x`, cleaned up obsolete Lark rule references in `_check_banish_stmt`, and documented `essence of length_expr` compatibility. (Docs 3.3, 3.4, 3.5, 3.6)

### Docs

- **`LANGUAGE.md` §5.1**: Corrected example 3 to include explicit zero-initialization for array variable declaration (`var buffer as array of byte with size 64 is array of byte with size 64`). (Doc 3.1)
- **`LANGUAGE.md` §6.2 & §13.4**: Updated string operator descriptions and runtime table to document pass-by-value signatures for `pengu_string_concat(PenguString a, PenguString b)` and `pengu_string_equal(PenguString a, PenguString b)`, added `pengu_to_string` macro, and documented explicit memory ownership semantics. (Doc 3.2, Gap 4.6)
- **`LANGUAGE.md` §18.2**: Added documentation for `with` blocks operating on `list` and `map` collections with supported built-in methods. (Gap 4.1)
- **`LANGUAGE.md` §7.3**: Documented that `map` is a supported iterable in `for_comp` list comprehensions (iterating over active keys in hash order). (Gap 4.3)
- **`LANGUAGE.md` §16**: Documented `-D main` CLI flag usage example (`pengu build -D main`). (Gap 4.5)

### Tests

- Added `tests/test_codegen_binding_if.py` verifying Bug 1.1 with C syntax and runtime execution checks.
- Added `tests/test_codegen_variadic.py` verifying Bug 1.2 array arguments passed to variadic `many` parameters.
- Added `tests/test_codegen_with_list.py` verifying Bug 1.3 and Gap 4.1 collection `with` blocks.
- Added `tests/test_checker_fields.py` verifying Bugs 2.1, 2.2, and Gap 4.2 semantic field validation.
- Added `tests/test_checker_with_builtin_methods.py` verifying Bug 2.3 `ref to list/map` methods under `with`.
- Added `check_c_syntax` helper in `tests/conftest.py` running `gcc -fsyntax-only` / `clang -fsyntax-only` on generated C code.

### Fixed — Roadmap Phase 0 completion (0.1–0.21)

- **Test-block scoping (0.12)** (`pengu_checker.py`): `_check_test_decl` no
  longer copies same-file globals into the test scope.  Globals stay reachable
  through the scope chain, and the copy made a legitimate local shadowing a
  same-file global (`var last` vs the `last` weave) a false `E0035`
  redefinition.  This was failing every std module that declares a local named
  after one of its own weaves (`std/tally.pengu` and everything importing it).
- **Range counters follow the bound type (0.11)** (`pengu_codegen.py`): the
  previous fix forced `int64_t` on every `for i from a to b`, which contradicted
  the item's spec and broke the 0.13.5 loop-shape regressions.  An `int` range
  is `int32_t` again; only a 64-bit bound (`i64`/`u64`/`usize`) promotes the
  counter (and the loop variable's inferred type) to `int64_t`, so
  `for i from 0 to 5_000_000_000` still has no truncation.
- **String-valued omen variants assign to their omen type** (`pengu_checker.py`):
  `var m as HttpMethod is HttpMethod.Get` is accepted again for
  `omen HttpMethod with string`.  The variant stays typed `frozen string` (so it
  cannot be banished, per the C5 fix); the checker now recognises the explicit
  omen annotation as compatible.
- **GNU attribute blanking in `pengu bind` (0.16)** (`pengu_bind.py`): the
  object-like `-D__attribute__=` overrode the function-like macro and left
  `((packed))` behind, so `pycparser` rejected any header with
  `__attribute__((packed))` or an attribute with several arguments.  The list
  now uses a variadic `-D__attribute__(...)=` only; `__asm__` keeps its
  object-like form for `__asm__ __volatile__`.
- **Error codes are unique per class (0.6)** (`pengu_errors.py`,
  `pengu_checker.py`, `pengu_infer.py`): `DuplicateConceptBindingError` gets
  `E0052` (it shared `E0047` with `AutoOwnedBanishError`); redefinition in the
  same scope and duplicate destructuring bindings get `E0053` (they shared
  `E0035` with the reserved-C-keyword diagnostics); ambiguous struct
  initialization gets `E0054` (it shared `E0011` with conflicting constants);
  a static variable with an array type gets `E0055`.
- **Custom `lib_dir` is honoured (0.20)** (`pengu_parser/pengu_symbols.py`,
  `pengu_parser/pengu_checker.py`, `pengu_project.py`, `pengu_lsp/server.py`):
  `find_module_path`/`resolve_imports` accept the manifest's `lib_dir`
  (previously hard-coded to `lib`) and the builder threads it through.  The LSP
  now resolves imports from the project root with that `lib_dir` instead of
  looking only in `./lib`.
- **Version bump** (`VERSION`, `pengu_version.py`, `pengu_parser/pengu_codegen.py`,
  `README.md`): 0.14.0 → 0.15.0 so the badge, extension manifest, VERSION file,
  fallback constant and generated banner all agree again (the P0.5 "one
  version, everywhere" gate).
- **Dead code (0.21)** (`pengu_parser/pengu_infer.py`): removed the unused
  `_make_type_mismatch_error` and the no-op `_reject_glued_test`; the
  hard-coded Spanish lambda diagnostic had already been translated.

#### Verified already-complete in Phase 0

- **0.17**: the implicit `error` binding of `or:` (including inside
  `compound_set_stmt`) lives in its own scope and is reported with a dedicated
  message when used outside the block; there is no custom error-variable name
  to shadow.
- **0.18**: `pengu fmt` is idempotent on inline comments (`fmt --check std/`
  reports 0 files and a second pass is byte-identical).
- **0.19**: a default on a concrete parameter of a generic weave
  (`shard T with x as T, factor as int is 2`) compiles and folds at the call
  site, while a default on a generic-typed parameter is rejected with a clear
  message.

### Tests

- Added `tests/test_phase0_roadmap.py` (9 tests) pinning 0.11, 0.12, 0.16,
  0.17 and 0.20, plus the string-valued omen assignment.
- Added `tests/test_error_codes_uniqueness.py` asserting the class-level code
  registry and the 0.6 disambiguations.
- Updated `tests/test_audit_v0150_fixes.py`, `tests/test_compiler_core.py`,
  `tests/test_generics.py`, `tests/test_p1_features.py` and
  `tests/test_pengu_paths.py` for the new codes and the version-agnostic sync
  check.

## [0.14.0] - 2026-09-24

### Añadido (empaquetado y arquitectura)

- **Nuevo módulo `pengu_paths.py` para localización unificada de artefactos**: Se centraliza la detección del runtime (`pengu_runtime.h`), bibliotecas estáticas (`*.a`), biblioteca estándar (`std/*.pengu`) y archivo `VERSION` en `pengu_paths.py`. Soporta 4 layouts ordenados por prioridad: FHS (`$PREFIX/{bin,lib/pengu,include/pengu,share/pengu}`), bundle portable (`<exe_dir>/{runtime/{lib,include},std,VERSION}`), source checkout de desarrollo (`<repo>/{build/{lib,include},std,VERSION}`) y payload de PyInstaller (`_MEIPASS`). Se implementan overrides directos por variables de entorno: `PENGU_PREFIX`, `PENGU_INCLUDE_DIR`, `PENGU_LIB_DIR`, `PENGU_STD_DIR`, `PENGU_STD_PATH`, `PENGU_VERSION_FILE` y `PENGU_RUNTIME_HEADER`.
- **Layout de distribución FHS para Linux y macOS (`--layout fhs`)**: `make_release.py` incorpora el flag `--layout {portable,fhs}` (con `portable` como default intacto para Windows y entornos autocontenidos). El layout FHS estructura la salida en `bin/pengu`, `lib/pengu/*.a`, `include/pengu/*.h` y `share/pengu/{std/,VERSION}`.
- **Generación de scripts de instalación y desinstalación (`install.sh` y `uninstall.sh`)**: En modo FHS, `make_release.py` genera scripts POSIX que soportan instalación a nivel de usuario (`PREFIX=$HOME/.local`), instalación de sistema (`PREFIX=/usr/local`) y staging para empaquetadores de distribuciones mediante `DESTDIR`.
- **Inyección de flags `pkg-config` en sistemas POSIX**: En `pengu_project.py::build_compile_commands`, se consultan dinámicamente cflags y link flags mediante `pkg-config` para dependencias de sistema en Linux/macOS (`libxml-2.0`, `libcurl`, `libmicrohttpd`, `mbedtls`), además de agregar las rutas de cabeceras y bibliotecas de Homebrew (`/opt/homebrew` y `/usr/local`) en compilaciones POSIX.
- **Resolución nativa de la librería estándar en FHS**: Se actualizó `pengu_symbols.py::get_stdlib_dirs` para consultar `pengu_paths.std_dirs()`, permitiendo que ejecutables standalone en `$PREFIX/bin/pengu` resuelvan automáticamente módulos `import std.*` desde `$PREFIX/share/pengu/std`.
- **Copia de versión en bundles portables y delegación en `pengu_version.py`**: `pengu_version.py::read_version_file` delega en `pengu_paths.find_version_file()`, asegurando que `pengu --version` y banners del compilador lean la versión correcta en cualquier instalación o empaquetado.

### Añadido (assets embebidos en el binario — módulo `arca`)

- **Soporte de Assets Embebidos en Proyectos (`arca`)**:
  - Nuevo módulo generador `pengu_assets.py` que empaqueta archivos estáticos (imágenes, shaders, audio, configuraciones, etc.) desde un directorio configurado (por defecto `assets/`) generando una interfaz PenguScript autocontenida (`src/arca.pengu`), una cabecera C (`build/arca_assets.h`) y su implementación C (`build/arca_assets.c`).
  - Dos modos de operación configurables en `pengu.yaml` (`assets.embed`):
    - `embed: true` (por defecto): Empaqueta los bytes directamente en la sección `.rodata` del ejecutable como arreglos estáticos de bytes C con terminador nulo, permitiendo binarios 100% autocontenidos y portables.
    - `embed: false`: Generador de lectura diferida en disco mediante `fopen` con caché dinámica en memoria y soporte de override por variable de entorno `PENGU_ASSETS_DIR`.
  - Constantes de ruta por asset generadas automáticamente con sufijo hash SHA-1 de 8 caracteres `ASSET_<IDENTIFICADOR_MAYUSCULAS>_<HASH8>` (ej. `const ASSET_LOGO_PNG_A731E040 as string is "logo.png"`), garantizando identificadores C únicos y libres de colisiones incluso ante rutas con caracteres especiales, extensiones compartidas o dígitos iniciales.
  - Sanitización de nombres de módulo (`_sanitize_module`): normaliza el identificador de módulo en `pengu.yaml` a identificadores C válidos para archivos de interfaz, cabeceras y guardas `#ifndef`.
  - Caché de lecturas fallidas en modo disco: `_ArcaCacheEntry` en `_emit_disk_c` incorpora la bandera `attempted`, evitando llamadas redundantes a `fopen` en disco para archivos que no existen.
  - Const-correctness y seguridad de tipos en la interfaz PenguScript: se declaran punteros con `ref to frozen char` en funciones C de acceso y se transmuta a `ref to frozen byte` en `arca.bytes`, satisfaciendo las reglas estrictas de tipo de PenguScript sin descartar `frozen`.
  - API pública completa en `arca`: `count`, `name` / `name_at`, `size`, `has` / `exists`, `ptr` (puntero directo a `.rodata` o caché), `bytes` (slice de bytes no propietario) y `string` (copia propietaria mediante `pengu_string_new`, segura para `banish`).
  - Subcomando CLI `pengu assets`: Permite regenerar la interfaz y C (`pengu assets`), inspeccionar archivos rastreados, tamaños y constantes generadas en formato tabular (`pengu assets --list`) y forzar regeneración ignorando la caché de contenido (`pengu assets --force`).
  - Integración en el ciclo de vida del compilador (`PenguBuilder`): `generate_assets` se ejecuta antes de resolver importaciones en `bundle()`, `compile()` y `check_sources()`, agregando automáticamente `build/<module>_assets.c` a las fuentes C recopiladas y `build/<module>_assets.h` a las cabeceras.
  - Invalidación de caché incremental: `compute_sources_fingerprint` y `compute_config_hash` incorporan el digest criptográfico de los assets y la bandera `embed`, reconstruyendo el bundle cuando cambian los archivos en `assets/`.
  - Soporte en `pengu init`: Inicializa la carpeta `assets/`, genera `assets/README.md`, agrega la sección `assets:` a la plantilla `pengu.yaml` y `.gitignore`.
  - Ignorado en formateador: `pengu fmt` y el servidor LSP detectan la cabecera `## @generated` en las primeras 5 líneas de archivos como `src/arca.pengu` y omiten su reformateo.
  - Pruebas automatizadas y humo: Suite completa de pruebas unitarias y de integración en `tests/test_assets.py` (incluyendo prevención de colisiones, sanitización de módulos y caché de disco), test de humo `[TEST 3b]` en `make_release.py` y caso de uso real de Raylib con carga de texturas y shaders desde memoria en `scratch/port/assets_raylib/`.

### Documentación

- **Sincronización integral de `LANGUAGE.md` con PenguScript 0.14.x**:
  - Actualización completa de metadatos, tabla de contenidos y referencias cruzadas con `CHEATSHEET.md` y `README.md`.
  - §3: Documentación del strip de BOM (`strip_bom`), comentarios de una (`#`) y doble almohadilla (`##`), convención de visibilidad privada con prefijo `_` (`E0043`), identificador reservado `main` (`E0040`), y palabras reservadas de C (`C_RESERVED_*`, `E0035`).
  - §4: Tipos primitivos, cálculo de alineación y padding en tiempo de compilación con `estimate_size`, estructuras de memoria del runtime (`PenguString`, `PenguSlice`, `PenguList`, `PenguMap`, `PenguMaybe`, `PenguResult`, `PenguRange`, `PenguFrame`), y tabla de compatibilidad de tipos (`AliasType`, `SealType`, `FrozenType`, `RefType`, `ArrayType`, `FnType`, `CVarArgsType`).
  - §5: Las 8 sintaxis de declaración de variables/constantes, reglas de destructuring (`E0017`), los 6 targets de asignación `set` (incluyendo `set essence of ptr is val`), asignaciones compuestas y el modificador suave `borrowed`.
  - §6: Tabla completa de precedencia de operadores, reglas de desambiguación `and`/`or` (`_reject_list_glued_operator`, `E0005`), operador `in` sobre strings y mapas, tests de palabras clave (`is present`, `is not present`, `is true`, `is false`), reglas de paréntesis en argumentos con tests (`_reject_test_argument`), operadores de memoria (`sigil of`, `essence of`, `size of`, `transmute` con `W0001`, `bytes of`), y boxing en heap con `some`.
  - §7: Formas de `simple_stmt`, bindings `if`, bucles `for i, v in col` con validación de identificadores disjuntos (`E0037`), iteración sobre mapas y strings, comprensiones de listas `for_comp`, expresiones `judge` con chequeo de exhaustividad (`E0044`), y bloques de expresión (`do:`, `_pengu_value_type`, `_exclude_escaping_val_from_banish`).
  - §8: Diagnósticos en llamadas (`E0004`, `E0018`, `E0034`, `E0043`, `E0045`), wrapper `pengu_main` y `main(argc, argv)` con `pengu_init`, funciones variádicas de C (`declare ... with ...`) vs `many T`, decaimiento a puntero de función `FnType`, lambdas estáticas `_pengu_lambda_N`, y métodos estáticos `ritual` (`E0033`, `E0034`).
  - §9: Runes con campos privados `_` (`E0043`), uniones `echo` con warning `W0002`, omens con valores de cadena (`omen X with string:`), modos de emisión de omens (normal, `.d.pengu`, string-valued, algebraico), unicidad de variantes (`E0027`, `E0029`, `E0046`), `seal` nominal vs `alias` estructural vs `opaque` (`E0012`), y compatibilidad direccional de `frozen` (`_drops_frozen`) con protección de escritura de pointee.
  - §12: Manejo de `maybe T` y `result of T to E`, desazucarado de statement-expressions para `or else`, `or return` (con limpieza de frames y variables auto-owned) y `try` (`E0045`), y bloques `or:` con ámbito léxico de variable `error` (`E0015`).
  - §13: Indexación de punteros `p at i`, tabla de tipos estrictos de punteros (`_same_pointee`), convención de propiedad con buffers C, las 5 condiciones del auto-banish (`_compute_auto_banished`), análisis estático de escape, y errores `AutoOwnedBanishError` (`E0047`) y `BorrowedBanishError` (`E0048`).
  - §14: Esquema completo de `pengu.yaml` y prioridad de `pengu.toml`, integración de código C en `./c/`, layout `lib/<binding>/pengu/`, artefactos de compilación y estrategias de inicialización de `static var`.
  - §15: Requisitos de contexto de tipo para `null` (`E0014`), especificadores de formato en interpolación `{expr}` (`%c`, `%d`, `%f`, `%s`, `%.*s`), cadenas raw y multilínea, tamaño de arreglos referenciando constantes nombradas, arreglos multidimensionales, y validación estática de rangos (`E0042`).
  - §16: Bloques `when` en nivel superior con `else:`, `when_stmt` con `else when` y `else:`, expresiones `when_expr`, intrínseco `defined(NAME)`, y variables comptime (`main`, `debug`, `os`, `arch`, `compiler`).
  - §17: Bloques de test integrados, aislamiento, y flags `--watch` y `--json`.
  - §18: Construcción tipo builder (`with:`), desazucarado `_with_N = {0}`, sentencias permitidas vs prohibidas (`E0014`), mutabilidad y anidamiento.
  - §19: Inventario exhaustivo de los 52 módulos de la biblioteca estándar (27 módulos puros PenguScript y 25 bindings C `.d.pengu`), ejemplos detallados para `std.ffi`, `std.spark`, `std.scrolls`, `std.seal`, `std.precis`, `std.filum`, `std.regulus` y `std.raylib`/`std.raymath`, y documentación completa de assets embebidos (`arca`).
  - §20: Referencia completa y flags de todos los subcomandos de la CLI (`init`, `build`, `run`, `test`, `check`, `bind`, `fmt`, `doc`, `assets`, `lsp`, `add`, `update`, `clean`, `-V`), anillo circular de backtraces de 64 frames en tiempo de ejecución, comprobación opcional de límites en debug, y mapeo de fuentes C con directivas `#line`.
  - §21: Ejemplo completo y funcional actualizado a versión 0.14.x.
  - §22 (Apéndice): Catálogo completo de diagnósticos del compilador que cubre todos los códigos de error (`E0000` a `E0048`) y warnings (`W0001`, `W0002`, `W0004`), formato de reporte Rust-style, tabla de causas y sugerencias `help:`, y ejemplos de código erróneo con su resolución.
- **Actualización de `README.md`**:
  - Conciliación de notas Beta eliminando elementos marcados erróneamente como no implementados.
  - Enlaces directos a las secciones correspondientes de `LANGUAGE.md` en los Feature Highlights.
  - Inventario completo de los 52 módulos de la biblioteca estándar.
  - Incorporación de `LANGUAGE.md` en la tabla de documentación oficial.

### Corregido (compilación y pruebas CI)

- **Aislamiento de bibliotecas del toolchain runtime en detección de auto-links (`pengu_project.py`)**: Se corrigió `PenguBuilder.collect_lib_dirs_and_links` para que la detección automática de bibliotecas (`auto_links`) escanee únicamente los directorios de bibliotecas del proyecto y de bindings (`lib/`, `lib/*/lib/`, `config.lib_dirs`), evitando que los archivos `.a` del runtime del toolchain (`build/lib`, `runtime/lib`) sean vinculados inadvertidamente en binarios donde `links` está vacío o no los requiere. Esto soluciona los fallos en CI (`test_no_hardcoded_raylib_with_empty_links`) en Windows, Linux y macOS.
- **Escape de nombres de bindings con palabras clave de C (`pengu_codegen.py`)**: `_binding_cond`, `_translate_binding_if` y `_translate_binding_value_if` escapan ahora `bind_name` mediante `_c_ident`, registrando tanto el nombre Pengu como el nombre C en `local_vars`. Esto previene emitir declaraciones C inválidas como `int32_t switch = ...` en sentencias de binding (`if switch as int is maybe_val:`).
- **Destructuring de arreglos (`pengu_codegen.py`)**: En sentencias `let a, b, c is my_arr`, cuando el inicializador es una variable o expresión y no un literal compuesto `{`, se emite `const __auto_type _destruct_N = expr;`, evitando la sintaxis C ilegal `const int32_t _destruct_N[3] = my_arr;`.
- **Destructuring de runes con `insignia` y campos C-keyword (`pengu_codegen.py`)**: Se utiliza `getattr(actual_expr_type, "c_name", None)` o el nombre calificado para declarar la estructura en C, y se escapan los accesos a campos con `self._c_ident(field)`, permitiendo destructuring de runes con prefijos de módulo y campos que colisionan con palabras reservadas de C (`default`, `class`, `register`, etc.).
- **Literales indentados de runes con campos C-keyword (`pengu_codegen.py`)**: `indent_literal` busca campos tanto por el nombre Pengu crudo (`f_raw`) como escapado (`f_name`), y emite el nombre de tipo C calificado (`c_rune_name`), resolviendo los tipos de campo correctamente y generando inicializadores válidos.
- **Soporte de múltiples fuentes C en `OutputType.OBJ` (`pengu_project.py`)**: Al compilar proyectos con `--output obj` que contienen fuentes C adicionales (`c/glue.c`), cada archivo se compila por separado a un objeto temporal y se combina con `gcc -r -nostdlib -o out.o temp_objs` (o `link -lib` en MSVC), evitando el error fatal de GCC al especificar múltiples fuentes con `-c` y `-o`.
- **Verificación de presencia en rvalues (`pengu_codegen.py`)**: `is present` e `is not present` sobre rvalues o llamadas a función (`(calling f()) is present`) materializan el valor en un temporal de statement-expression `(__extension__({ __auto_type _m = (expr); pengu_maybe_is_present(&_m); }))`, evitando tomar la dirección de un rvalue `&(f())`.
- **Llamadas estáticas a métodos en tipos (`pengu_infer.py` y `pengu_codegen.py`)**: El inferidor de tipos valida que cualquier método invocado sobre un tipo (`calling Type.method`) tenga la marca `is_ritual`, arrojando `InvalidRitualCallError [E0034]` si es un método de instancia invocado sin receptor. El generador de código resuelve el nombre calificado del tipo (`c_name`) y escapa el nombre del método.
- **Resolución de llamadas sobre módulos con alias de importación (`pengu_checker.py` y `pengu_codegen.py`)**: Se asigna `c_name = last_name` al símbolo de importación en el checker, y el codegen resuelve el prefijo real del módulo (`mod_prefix = getattr(obj_sym, "c_name", None) or obj_name`), asegurando que `import std.spark as s` con `calling s.println` emita `spark_println(...)` y no `s_println(...)` ni nombres descalificados.
- **Simetría y nominalidad en `AliasType.__eq__` (`pengu_types.py`)**: Se corrigió la asimetría de igualdad donde `AliasType == BaseType` era `True` pero `BaseType == AliasType` era `False`. La igualdad de `AliasType` ahora es nominal y simétrica (`isinstance(other, AliasType) and self.name == other.name and self.target == other.target`), delegando la equivalencia estructural y de flujo a `is_compatible`.
- **Compatibilidad de punteros de múltiple nivel con alias (`pengu_types.py`)**: En `_same_pointee`, se añadió soporte recursivo para `RefType` anidados (`ref to ref to T`), permitiendo que punteros dobles a tipos con alias (p. ej. `ref to ref to sqlite3` frente a `ref to ref to opaque`) validen su equivalencia de forma transparente en llamadas a funciones C/FFI.
- **Tipo de retorno de `add` con `AnyType` (`pengu_infer.py`)**: La operación aritmética `+` solo retorna `STRING_TYPE` si al menos uno de los operandos es efectivamente de tipo `string`. Operaciones como `AnyType + int` ahora infieren `int` (o `AnyType`/`float`), evitando que expresiones aritméticas se tipen erróneamente como cadenas.
- **Aislamiento de módulos en código generado de assets (`pengu_assets.py`)**: `_emit_disk_c` interpola `{module}` en macros de entorno (`{MODULE}_ASSET_DIR_ENV`, `{MODULE}_DEFAULT_DIR`), estructuras (`_{Module}CacheEntry`), funciones auxiliares y arreglos estáticos, evitando colisiones de símbolos cuando se usan múltiples módulos de assets o nombres personalizados. Asimismo, `_asset_const_name` incorpora el prefijo de módulo si este no es el predeterminado `arca`.
- **Soporte de claves arbitrarias en mapas literales (`pengu_grammar.py`, `pengu_infer.py`, `pengu_codegen.py`)**: La gramática permite expresiones como claves en `map_entry: (NAME | string_token | expr) ":" list_expr`, infiriendo y declarando el tipo de clave correspondiente en el C generado.
- **Exportaciones públicas del sistema de tipos (`pengu_parser/__init__.py`)**: Se agregaron a `__all__` los tipos y utilidades públicas `FrozenType`, `TypeParam`, `NullType`, `NULL_TYPE`, `ConceptType`, `SealType`, `AnyType`, `ManyType`, `estimate_size`, `mangle_type`, `implements_concept`, `resolve_concept_method`, `is_opaque_type`, `ast_to_type`.
- **Preservación de última línea sin salto en `strip_comments` (`pengu_parser.py`)**: `blank(line)` retorna `"\n"` en lugar de `""` cuando la última línea del archivo no termina en salto de línea, evitando que la última línea desaparezca y desplace los diagnósticos de fin de archivo.
- **Propagación de módulo en `pengu assets --list` (`pengu_project.py`)**: Se pasa `module=getattr(config, "assets_module", "arca")` a `_asset_const_name`, garantizando que el listado imprima las constantes con el prefijo correcto de módulo.
- **Idempotencia en actualización de dependencias TOML (`pengu_project.py`)**: `_update_config_dependency` actualiza in-place las secciones `[dependencies.X]` existentes en lugar de duplicarlas, evitando errores de clave repetida al ejecutar `pengu add` múltiples veces.
- **Resolución de identificadores C-escapados en expresiones (`pengu_codegen.py`)**: Se centralizó `_lookup_symbol` y se adaptaron `_lookup_var_type`, `field_access`, `at_expr` y `length_expr` para resolver nombres originales cuando un identificador de C fue escapado con prefijo `_` (`_switch` -> `switch`), asegurando que accesos como `switch.hp` sobre referencias se traduzcan correctamente con `->`.
- **Sincronización en iteración de mapas ante `continue` (`pengu_codegen.py`)**: Se ajustó la generación de bucles `for k, v in m:` sobre `MapType` para iterar sobre la capacidad de slots y avanzar el contador de índice antes del cuerpo, evitando que `continue` desincronice el conteo o el índice.
- **Limpieza de comentarios inline `##` en preprocesador (`pengu_parser.py`)**: `_strip_comments` elimina comentarios inline fuera de cadenas de texto antes de entregarlos a Lark, previniendo que un `##` en medio de una línea sin cerrar engulla el código posterior.
- **Temporales únicos en verificaciones de presencia (`pengu_codegen.py`)**: `is present` e `is not present` utilizan `self.get_temp_name("_maybe")` en vez de un nombre fijo `_m`, previniendo colisiones de alcance en expresiones anidadas.
- **Protección ante OOM en `some_expr` (`pengu_codegen.py`)**: La inicialización de `PenguMaybe` asigna `is_present = (value != NULL)`, evitando maybes presentes con punteros nulos si `pengu_sigil_alloc` falla.
- **Comprobación de límites con índices de 64 bits (`pengu_codegen.py` y `pengu_runtime.h`)**: `_emit_bounds_check` utiliza `__auto_type` y pasa enteros `int64_t` a `pengu_assert_bounds` y `pengu_bounds_panic`, evitando truncamientos involuntarios a 32 bits.
- **Evento sintético de fin de pruebas en modo JSON (`pengu_project.py`)**: `test_project` en modo `--json` emite un evento `{"event": "end", "aborted": true}` en caso de que el proceso de prueba aborte o termine abruptamente.
- **Separación de argumentos en interpolación de strings (`pengu_codegen.py`)**: En `_translate_string_lit`, la longitud y el puntero de datos de cadenas Pengu interpoladas se agregan como entradas separadas a `c_args`.
- **Supresión de secuencias ANSI en `pengu test --watch --json` (`pengu_project.py`)**: Se condicionó el escape ANSI de borrado de pantalla `\033[2J\033[H` a `if not json_output`, garantizando que la salida estándar mantenga el contrato estricto de JSON Lines para herramientas CI/CD y scripts de integración.
- **Resiliencia en modo watch ante errores iniciales (`pengu_project.py`)**: `_watch_and_test` captura excepciones en la ejecución inicial de `test_project`, permitiendo que el watcher permanezca activo a la espera de modificaciones del código fuente.
- **Omisión de métodos genéricos en `enchanting` no-genérico (`pengu_codegen.py`)**: En `_collect_top_stmt`, las declaraciones de método con `shard_params` dentro de bloques `enchanting` se omiten durante la recolección estática y se difieren a la monomorfización bajo demanda, evitando emitir código C inválido con parámetros de tipo sin sustituir.
- **Detección de escape de contenedores en bloques `with` (`pengu_checker.py`)**: El análisis conservador de escape en `_check_symbol_escape` reconoce nodos `with_target` y accesores `arrow_access` para métodos mutadores de colecciones (`push`, `append`, `put`, etc.), marcando los argumentos como escapados y previniendo la liberación anticipada (*dangling pointer*) de variables auto-banished insertadas en listas o mapas.
- **Tipado en inicializadores de estructura para tipos alias (`pengu_codegen.py`)**: En `struct_init`, se añadió un fallback defensivo con `CTypeMapper.to_c_type` para emitir el tipo compuesto `(AliasRune){...}` en lugar de literales compuestos sin tipo cuando `expected_type` es un `AliasType` u otro tipo estructurado.
- **Resolución del nombre C en lookup de omens (`pengu_codegen.py`)**: `_lookup_type_fn` consulta el símbolo correspondiente en la tabla de símbolos para recuperar su `c_name` real (respetando prefijos de `insignia`), en lugar de asumir que coincide con el nombre lógico.
- **Prevención de recursión circular en cálculo de tamaño (`pengu_types.py`)**: `estimate_size` registra tipos `AliasType` y `SealType` en el conjunto `seen` para proteger contra ciclos de recursión infinita en definiciones circulares.
- **Reutilización del parser de expresiones en interpolación de cadenas (`pengu_codegen.py`)**: Se almacena en caché la instancia `PenguParser` en el generador de código, evitando instanciaciones repetitivas en cada interpolación.
- **Escape de caracteres en rutas de verificación de límites (`pengu_codegen.py`)**: `_emit_bounds_check` escapa comillas dobles y barras invertidas en la cadena de ubicación del archivo.
- **Tipado exacto de errores en bloques `or:` (`pengu_codegen.py`)**: `_translate_or_block` declara el binding `error` con el tipo concreto de error del contenedor `ResultType` (p. ej. `int32_t`, `double`, etc.) en lugar de asumir `PenguString`, evitando reinterpretaciones erróneas de memoria en runtime.
- **Plegado de constantes para strings crudos multilínea (`pengu_folder.py`)**: `ConstFolder` pliega cadenas crudas delimitadas por triple comilla `\"\"\"`, normalizando saltos de línea y permitiendo su uso en contextos que exigen constantes evaluadas en tiempo de compilación.
- **Rechazo de expresiones no constantes en declaraciones `const` (`pengu_checker.py`)**: Se valida que los inicializadores de `const` sean efectivamente constantes en tiempo de compilación, emitiendo diagnósticos claros ante llamadas a función o lecturas de variables.
- **Validación de lvalues en `banish essence of` (`pengu_checker.py` y `pengu_codegen.py`)**: Se rechaza la toma de dirección sobre rvalues, temporales o punteros no propietarios en sentencias de liberación de memoria `banish`.
- **Resolución de símbolos constantes en tamaños de array (`pengu_types.py` y `pengu_checker.py`)**: Se evalúan identificadores de constantes usados como tamaño en definiciones de arreglos fijos (`array of T with size N`).
- **Inferencia y tipado en for-comprehensions con rangos (`pengu_checker.py` y `pengu_infer.py`)**: Las comprensiones que iteran sobre rangos (`[x * 2 for x in 0..10]`) infieren correctamente el tipo entero de la variable de inducción y el tipo del resultado.
- **Indexación encadenada en destinos de asignación `set` (`pengu_codegen.py`)**: Se soporta la asignación a elementos anidados de arreglos, listas y mapas (`set grid[x][y] is val`).
- **Inmutabilidad estricta en cadenas de texto (`pengu_checker.py`)**: Se prohíbe la modificación in-place de caracteres individuales en strings mediante `set str[i] is ch`, preservando la semántica inmutable de `PenguString`.
- **Análisis de escape en llamadas a métodos encadenados (`pengu_checker.py`)**: Las llamadas encadenadas marcan adecuadamente los receptores intermedios para prevenir la liberación anticipada de variables de ámbito stack-allocated.
- **Protección contra escrituras en campos `frozen` dentro de `with` (`pengu_checker.py`)**: Se valida la mutabilidad de los campos cuando el objetivo de un bloque `with` está marcado como `frozen`.
- **Manejo defensivo de tamaños simbólicos en `estimate_size` (`pengu_types.py`)**: `estimate_size` maneja tokens y cadenas en `ArrayType.size` sin lanzar excepciones de tipo.
- **Prioridad de variables locales sobre campos de ámbito `with` (`pengu_codegen.py`)**: `_translate_set_target` prioriza variables locales activas sobre campos homónimos de estructuras en el stack de `with`.
- **Desugaring de `judge` no constante a cadenas ternarias (`pengu_codegen.py`)**: Las expresiones `judge` con patrones variables emiten cadenas condicionales `?:` en lugar de etiquetas `case` ilegales en C.
- **Verificación de tipos de patrones en `judge` (`pengu_checker.py`)**: Se validan los tipos de patrones contra el tipo del sujeto analizado, incluyendo variantes de omens con y sin prefijo de tipo.
- **Validación de elementos en operadores de pertenencia `in` sobre cadenas (`pengu_infer.py` y `pengu_codegen.py`)**: `elem in str` valida que el elemento sea de tipo `char`, `byte` o `string` y genera llamadas seguras a `strchr`.
- **Slicing uniforme en listas y rebanadas (`pengu_codegen.py`)**: Se genera la estructura `PenguSlice` para operaciones de corte sobre `ListType` y `SliceType`.
- **Iteración y operadores `in` en alias de cadena (`pengu_checker.py`, `pengu_codegen.py`, `pengu_infer.py`)**: Los tipos alias basados en cadenas heredan el comportamiento de iteración de caracteres y búsqueda de subcadenas.
- **Prevención de validación duplicada en constructores `with:` (`pengu_checker.py`)**: Se evita la doble comprobación de errores semánticos en inicializadores de variables con constructores en bloque `with:`.
- **Resolución de tablas de símbolos a través de clausuras en monomorfización (`pengu_types.py`)**: `_resolve_symbol_table` inspecciona recursivamente closures para registrar tipos monomorfizados en la tabla de símbolos adecuada.
- **Monomorfización de métodos genéricos en `enchanting` no genérico (`pengu_checker.py`, `pengu_codegen.py`, `pengu_infer.py`)**: Se registran y resuelven llamadas a métodos con parámetros genéricos propios (`shard T`) definidos en tipos base no genéricos.
- **Inclusión de directorios de búsqueda en `compute_config_hash` (`pengu_project.py`)**: La huella de configuración de compilación incluye `include_dirs` y `lib_dirs` para una invalidación precisa de la caché incremental.
- **Soporte de variantes de omens con guiones bajos (`pengu_infer.py` y `pengu_checker.py`)**: La resolución de variantes de omens que contienen guiones bajos preserva el nombre completo sin truncamientos prematuros de prefijos.
- **Corrección de `_check_or_block` ante operandos no-Tree (`pengu_checker.py`)**: Se inicializó `left_t = AnyType()` y se añadió una rama explícita para nodos con operandos que no sean `Tree`, evitando un potencial `NameError` en tiempo de compilación.
- **Liberación de puntero en `banish essence of p` (`pengu_codegen.py`)**: `_translate_banish_target` emite `pengu_banish((void*)(&((*p))))` en lugar de pasar el valor desreferenciado despojado a `void*`, liberando correctamente la dirección apuntada.
- **Desempaquetado de `RefType` en indexación encadenada con `set` (`pengu_codegen.py`)**: `_translate_access_op_step` desenvuelve `RefType` para arreglos (`ArrayType`, `SliceType`, `ManyType`, `ListType`), preservando los tipos de elemento e índices C correctos (`r[0][1] = 42`).
- **Propagación estricta de errores en lambdas (`pengu_codegen.py`)**: Se eliminó la captura silenciosa de excepciones con fallback a `AnyType()` en `_register_one_lambda`, propagando fielmente los errores semánticos (`SemanticError`) en el cuerpo de la lambda.
- **Validación de iterabilidad en `for_comp` (`pengu_infer.py`)**: Se exige que el iterable implemente `is_iterable()`, no sea `AnyType` y proporcione un `element_type()`, emitiendo `E0005` ante expresiones incompatibles.
- **Rechazo de `AnyType` en valores de retorno de bucles (`pengu_checker.py`)**: `_check_loop_value` rechaza bucles en posición de valor cuyo cuerpo se infiera como `AnyType`, exigiendo tipos concretos.
- **Orden de dimensiones en arreglos multidimensionales (`pengu_types.py`)**: `ast_to_type` construye arrays anidados respetando la profundidad del AST de adentro hacia afuera (`ArrayType(element=ArrayType(int, inner), outer)`), haciendo coincidir las dimensiones declaradas con los tipos C (`int[outer][inner]`).
- **Validación de patrones `omen` con prefijo `c_name` (`pengu_checker.py`)**: `_check_when_pattern_type` verifica variantes de omen considerando tanto el nombre Pengu como el prefijo de módulo en C (`c_name`).
- **Registro de métodos genéricos en `enchanting` no genérico (`pengu_codegen.py`)**: En `_collect_top_stmt`, los métodos con `shard_params` declarados en bloques `enchanting` no genéricos se registran correctamente en `generic_methods`.
- **Rechazo de `AnyType` en `some_expr` (`pengu_infer.py`)**: `visit_some_expr` valida que el valor contenido no sea `AnyType` ni `void`, emitiendo `TypeMismatchError` (`E0005`).
- **Cierre automático de bloques de documentación `##` unclosed (`pengu_parser.py`)**: Si un bloque `##` no encuentra delimitador de cierre, se blanquean todas las líneas hasta fin de archivo sin generar errores de sintaxis en el código circundante.
- **Inclusión de directorios y nombre de salida en hash de configuración (`pengu_project.py`)**: `compute_config_hash` incluye `src_dir`, `c_dir` y `output_name`, asegurando la invalidación de caché ante reorganizaciones de carpetas.
- **Soporte de `-D_GLFW_COCOA` en macOS para Raylib (`build_runtime.py`)**: Se añade el flag específico de Cocoa al compilar `libraylib.a` en plataformas darwin.
- **Liberación de cadenas temporales en interfaz de assets (`pengu_assets.py`)**: Se añade `defer calling ffi.cstr_free with c` en `size` y `ptr` dentro de la interfaz generada.
- **Sincronización de documentación (`LANGUAGE.md`)**: Se eliminó el ejemplo obsoleto de patrón `when` con `is` y se aclaró el alcance léxico del binding `error` tras un bloque `or:`.
- **Corrección de compilación y enlaces C multiplataforma en tests (`tests/test_p0_review_fixes.py`)**: Se migró el helper `_build_and_run` para usar directamente `PenguBuilder` (`OutputType.EXE`) en lugar de comandos `gcc` manuales con flags harcodeados (`-ldl`), resolviendo los fallos en Windows (donde `-ldl` no existe y se requieren bibliotecas de Win32 como `ws2_32`) y en macOS (donde las bibliotecas de Homebrew no estaban en el search path del linker).
- **Orden de flags `-L` antes de `-l` en invocaciones C (`pengu_project.py` y `tests/conftest.py`)**: Se reestructuró la generación de comandos de compilación para que todos los directorios de búsqueda de bibliotecas de Homebrew y `pkg-config` se incorporen en `common_flags` antes de los flags `-l`, asegurando que `clang` y `gcc` en macOS y Linux resuelvan dependencias como `libmicrohttpd`, `libxml2` y `libcurl` sin ambigüedad.
- **Protección de biblioteca estática en pruebas de Raylib (`tests/test_p2_review_fixes.py`)**: Se añadió un mock sobre `Path.unlink` en `test_raylib_build_flags_macos` para evitar la eliminación accidental de `build/lib/libraylib.a` durante la ejecución de pruebas deterministas.
- **Variables de entorno para Homebrew en CI de macOS (`.github/workflows/ci.yml`)**: Se exportaron `LIBRARY_PATH` y `CPATH` con las rutas correspondientes de Homebrew (`libmicrohttpd`, `libxml2`, `curl`) en los runners de macOS de GitHub Actions.

## [0.13.14] - 2026-09-18

### Corregido (alto)

- **Interpolación de strings con evaluación única**: En `pengu_codegen.py::_translate_string_lit`, expresiones de tipo `string` complejas o con posibles efectos secundarios dentro de interpolaciones (`"{calling ...}"`) ahora se materializan en temporales `PenguString _str_N = (expr);` dentro de un bloque `(__extension__({ ... }))`, garantizando orden estricto de evaluación de izquierda a derecha y previniendo la doble ejecución que causaba `%.*s` con `(int)(expr).len, (expr).data`.
- **Acceso a campos en `frozen RuneType`**: En `pengu_infer.py::{arrow_access, field_access}` y `pengu_checker.py::_check_set_stmt`, se desenrollan `AliasType`, `FrozenType` y `SealType` antes de consultar los campos de estructuras (`RuneType`, `EchoType`, `OmenType`), permitiendo leer campos en tipos `frozen Foo` y `ref to frozen Foo` con `.` y `->` así como en bloques `with p:` conforme a `LANGUAGE.md §9.5`.
- **Falso positivo `E0020` en funciones con ramas de una línea**: En `pengu_checker.py::_stmt_always_returns`, se normalizan los nodos de sentencia utilizando `SIMPLE_STMT_ALIASES`, reconociendo `return` en ramas de una sola línea (`if c: return 1 else: return 2`) como retornos definitivos.

### Corregido (medio)

- **Variables de bucle con palabras clave de C**: En `pengu_codegen.py::{_translate_for_range, _translate_for_in}`, los identificadores de iteradores y valores (`var_name`, `index_name`, `elem_name`, `loop_var`, `iter_idx`) ahora se escapan con `_c_ident`, evitando la generación de sintaxis C inválida cuando se usan identificadores reservados como `int`, `char`, etc.
- **Detección de `frozen` sobre aliases en `banish`**: En `pengu_checker.py::_check_banish_stmt`, se desenrollan recursivamente `AliasType` y `RefType` sobre el símbolo a banish, detectando y rechazando con `InvalidMemoryOpError [E0008]` cualquier intento de desasignar variables marcadas como `frozen` a través de un alias de tipo.
- **Prefijo de módulos para archivos `.d.pengu`**: En `pengu_codegen.py::_collect_top_stmt`, la extracción del nombre de módulo elimina correctamente el sufijo `.d.pengu` (en lugar de split por extensión única que producía `modulo.d`), asegurando identificadores C válidos y lookups consistentes de constantes.
- **Rechazo de literales desnudos en sentencias de una línea**: En `pengu_checker.py::_check_simple_stmt`, las expresiones simples que no son alias canónicos se validan como `expr_stmt`, rechazando literales de array y mapa sin efecto (`if c: [1, 2, 3]`) con `SemanticError [E0005]`.

### Corregido (menor)

- **Detección profunda de bucles para inlining**: En `pengu_checker.py::_check_weave_decl`, el análisis de bucles para determinar si una función califica para inlining (`is_inline`) inspecciona ahora todo el subárbol (`iter_subtrees()`), evitando marcar como inline funciones que contienen bucles dentro de bloques `if` u otras sentencias compuestas.
- **Destructuring sobre `FnType` en C**: En `pengu_codegen.py::let_decl`, todas las ramas de destructuring utilizan ahora `CTypeMapper.to_c_decl` para declarar las variables locales resultantes, emitiendo declaraciones de punteros a función válidas en C99.
- **Prohibición de valores por defecto en parámetros `many`**: En `pengu_checker.py::_check_weave_decl`, se prohíbe explícitamente asignar un valor por defecto a un parámetro variádico `many` con `SemanticError [E0005]`.

## [0.13.13] - 2026-09-18

### Corregido (crítico)

- **C5 & m12**: En `pengu_codegen.py::_infer_node_type`, se aísla la inferencia de expresiones locales creando un scope léxico temporal dedicado (`push_scope`) y restaurando de forma estricta `current_scope` y truncando `all_scopes` en un bloque `finally`. Esto elimina por completo la fuga lineal de memoria y previene la contaminación de símbolos y scopes de encantamientos o variables locales entre diferentes weaves. Se eliminó la doble definición redundante de `self`.
- **C6**: En `pengu_codegen.py::let_decl`, el destructuring de literales de array (`let a, b, c is [1, 2, 3]`) y de arrays multidimensionales ahora genera declaraciones válidas en C99 (`const int32_t _destruct[3] = { 1, 2, 3 };`), evitando inicializar punteros escalares con listas entre llaves y desintegrando filas 2D en punteros de fila C válidos (`const int32_t*`).

### Corregido (alto)

- **H4**: En `pengu_codegen.py::_translate_expr_impl`, las comprobaciones de pertenencia `in` / `not in` sobre colecciones (`array`, `list`, `slice`, `many`) ahora utilizan `pengu_string_equal` para cadenas de texto y `memcmp` para runes, echos y structs, evitando la comparación errónea de structs en C con `==`.

### Corregido (medio)

- **M8**: En `pengu_checker.py::_check_weave_decl`, funciones con retorno no-void que finalizan con `if_stmt` o `unless_stmt` donde las ramas no retornan incondicionalmente un valor ahora son detectadas y rechazadas con `TypeMismatchError [E0020]`, evitando que el compilador C emita advertencias `-Wreturn-type`.
- **M9**: En `pengu_checker.py::_check_value_exprs`, los inicializadores estructurados (`struct_init`) para tipos `OmenType` ahora propagan los tipos esperados correspondientes a los campos del payload de cada variante.

### Corregido (menor)

- **m13**: En `pengu_checker.py::_frozen_write_block`, se implementó el desenrollado recursivo de cadenas de tipos `RefType` y `AliasType`, asegurando que cualquier puntero o referencia que apunte a un `FrozenType` en cualquier nivel de indirección bloquee la escritura en asignaciones `set`.

## [0.13.12] - 2026-09-18

### Corregido (crítico)

- **C3**: En `pengu_infer.py::self_ref` y `pengu_codegen.py::_infer_node_type`, se inyecta el contexto de scope `enchanting` y el símbolo `self` (`RefType(current_enchanted_type)`), permitiendo inferir correctamente expresiones complejas como `with self->node:` y asegurando que las asignaciones a campos subsiguientes emitan `->` en lugar de `.`.
- **C4**: En `pengu_checker.py::_check_let_decl` y `pengu_codegen.py::let_decl`, el destructuring sobre `any` (`let a, b is x` donde `x as any`) ahora es rechazado con `SemanticError [E0017]`, impidiendo la emisión de sintaxis C inválida que intentaba indexar `void*` (`_destruct[i]`).

### Corregido (alto)

- **H3**: En `pengu_codegen.py::set_stmt`, la optimización con `memcpy` para runes de 3 o más campos ahora se restringe estrictamente a lvalues reales (variables, accesos a campos y elementos de arreglos), evitando tomar la dirección de rvalues como llamadas a funciones (`&calling make_big()`).

### Corregido (medio)

- **M6**: En `pengu_checker.py::_check_set_stmt`, los accesos a campos dentro de `with_target` validan que los tipos `RefType` utilicen el operador flecha `->` en vez de punto `.`, levantando `SelfDotAccessError [E0003]` ante infracciones.
- **M7**: En `pengu_checker.py::_collect_top_level`, las directivas `insignia` declaradas dentro de un bloque condicional `when_top_decl` quedan estrictamente limitadas a esa rama condicional y ya no se filtran hacia las declaraciones externas posteriores.

### Corregido (menor)

- **m8**: En `pengu_checker.py::_check_value_exprs`, cuando el nodo es `struct_init`, se resuelve el tipo esperado específico de cada campo y se propaga adecuadamente a cada expresión `field_init`.
- **m9**: En `pengu_grammar.py::when_pattern`, se introdujo la regla `bool_lit: "true" -> true_lit | "false" -> false_lit`, garantizando que Lark genere los árboles AST `true_lit` y `false_lit` esperados por el inferrer en expresiones `judge`.
- **m10**: En `pengu_checker.py`, se eliminaron referencias residuales a la cadena `"calling_stmt"` en las tuplas de inspección de sentencias.
- **m11**: En `pengu_codegen.py::_lookup_type_fn`, la resolución de tipos `omen` ahora preserva `variant_values` y `c_name`.

## [0.13.11] - 2026-09-18

### Corregido (crítico)

- **C1**: En `pengu_checker.py::_collect_top_level`, se propaga `current_insignia` al descender recursivamente en bloques condicionales `when_top_decl` y archivos anidados, garantizando que los tipos, funciones y símbolos definidos bajo `when os == "..."` hereden correctamente el prefijo `insignia` y mantengan coherencia con el codegen.
- **C2 & M5**: En `pengu_codegen.py::let_decl`, se implementa soporte completo para destructuring de colecciones (`ArrayType`, `SliceType`, `ManyType`, `ListType`, `RuneType`, `EchoType`), emitiendo código C estricto con punteros e indexación de listas (`pengu_list_at`), y se elimina el fallback frágil que emparejaba runas arbitrarias basándose únicamente en el número de campos. En `pengu_checker.py`, se rechaza el destructuring de tipos no estructurados con `E0017`.

### Corregido (alto)

- **H1**: En `pengu_codegen.py`, se implementa `with_type_stack` y `_get_current_with_target_type()` para rastrear el tipo semántico exacto del receptor en bloques `with target:`. Expresiones complejas como `with self->node:` o `with r.field:` ahora emiten el operador de acceso correcto (`->` en vez de `.`) para tipos puntero `ref to T`.
- **H2**: En `pengu_infer.py::_resolve_call_target`, llamadas a métodos sobre identificadores o variables no declaradas (`calling undefined_obj.method`) ahora levantan inmediatamente `UndefinedIdentifierError [E0004]` en lugar de tiparse silenciosamente como `AnyType`.

### Corregido (medio)

- **M4**: En `pengu_errors.py` y `pengu_checker.py::_check_with_builder`, las violaciones de sentencias dentro de bloques constructores `with:` emiten la nueva clase de error dedicada `InvalidBuilderStatementError` con código `E0014`, evitando diagnósticos engañosos de control de flujo (`E0007`).

### Corregido (menor)

- **m5**: En `pengu_codegen.py::collect_declarations`, se registra el número de línea fuente en el diccionario de tests integrados (`"line": self._node_line(inner)`), permitiendo que el frame push de backtraces en modo test reporte la línea real en lugar de `0`.
- **m6**: En `pengu_checker.py` y `pengu_codegen.py`, se eliminan ramas de código muerto para el non-terminal inexistente `calling_stmt`.
- **m7**: En `pengu_codegen.py::at_expr`, la indexación sobre referencias a slices (`ref to slice of T`) emite acceso directo al búfer interno `((({elem_cast})({base})->data)[{idx}])` en lugar de indexación de puntero directo `p[i]`.

## [0.13.10] - 2026-09-18

### Corregido (alto)

- **A1**: En `pengu_codegen.py::with_stmt`, las sentencias internas ahora se emiten dentro de un bloque C `{ ... }` con indentación adecuada y gestión del alcance de auto-banish (`_auto_banish_push("block")` y `_flush_current_scope_banish()`), impidiendo errores de compilación por redefinición de variables locales que ensombrecen variables externas.
- **A2**: En `pengu_codegen.py::struct_init`, la inicialización de variantes de `omen` utiliza el nombre C (`omen_cname = getattr(expected_type, "c_name", None) or expected_type.name`) para etiquetas de variante, inicializadores a cero y literales compuestos, solucionando errores de símbolo no encontrado en tipos declarados con `insignia`.

### Corregido (medio)

- **M1**: En `pengu_checker.py::_check_set_stmt`, la reasignación de arreglos de tamaño fijo (`set arr is [...]`) se rechaza con `E0008` ("Fixed-size arrays cannot be reassigned as a whole; use 'set arr at index is val' to update element-wise"), evitando la emisión de sintaxis C inválida.
- **M2**: En `pengu_infer.py::judge_expr` y `pengu_codegen.py::judge_expr`, los patrones calificados `Omen.Variant` validan que el prefijo coincida con el tipo `omen` analizado, impidiendo coincidencias erróneas con variantes homónimas de otros tipos.
- **M3**: En `pengu_grammar.py`, los literales booleanos en `when_pattern` usan alias (`"true" -> true_lit | "false" -> false_lit`), permitiendo que el árbol sintáctico conserve el valor en lugar de ser filtrado por Lark y restaurando la exhaustividad en expresiones `judge`.

### Corregido (menor)

- **m1**: En `pengu_checker.py::_check_banish_expr`, se rechaza el descarte de temporales que no sean lvalues (como `banish (s to string)`) con `E0008`, y en `pengu_codegen.py` se materializan temporales rvalue de forma segura.
- **m2**: En `pengu_checker.py::_check_weave_decl`, las funciones con retorno no-void que finalizan en sentencias sin valor (`let`, `var`, `set`, bucles) se rechazan con `E0020` para evitar advertencias y errores de compilación `-Wreturn-type` en C.
- **m3**: En `pengu_checker.py::_check_with_builder`, los bloques constructores `with:` restringen sus sentencias a `set .campo is ...` y llamadas a métodos `.metodo()`, rechazando expresiones libres.
- **m4**: En `pengu_checker.py::_check_omen_variant_collisions`, se valida la colisión de variantes tanto por su nombre lógico como por su identificador C (`c_name` bajo `insignia`).

## [0.13.9] - 2026-09-17

### Corregido (crítico)

- **C1**: En `pengu_codegen.py`, las vinculaciones inmutables `let` sujetas a `auto-banish` (`sym.is_auto_banished`) se emiten sin calificador `const` en C99 (`PenguString s` en vez de `const PenguString s`), evitando errores de compilación por descarte de calificadores (`-Wdiscarded-qualifiers` bajo `-Werror`) al llamar `pengu_banish_string(&s)`. La inmutabilidad de la variable sigue garantizada estrictamente en tiempo de compilación por el verificador semántico (`E0006`).
- **C2**: En `pengu_codegen.py`, se aísla el entorno de variables locales (`self.local_vars`) en bloques y expresiones de control de flujo anidadas (`with_stmt`, `_translate_nested_block_with_banish`, `_translate_value_block_with_banish`, `_translate_loop_body`, `_translate_else_block`, `_translate_value_if`, `_translate_binding_if`, `_translate_binding_value_if`, `_translate_or_block`, `with_init_expr`, `do_expr`) mediante copia y restauración en bloques `finally`. Esto evita que declaraciones o redefiniciones en scopes internos corrompan tipos o calificadores de variables externas (como receptores `r` en accesos a miembros).

### Corregido (alto)

- **A1**: En `pengu_infer.py::judge_expr`, se valida rigurosamente el sujeto de expresiones `judge`, rechazando con `E0005` tipos no escalares/no comparables (como `maybe T`, `result`, `list`, etc.) antes de codegen, impidiendo comparaciones inválidas en C como `PenguMaybe == 1`.
- **A2**: En `pengu_types.py` y `pengu_codegen.py`, los tipos `omen` con valores de cadena (`omen X with string:`) ya no devuelven `is_int() == True` ni `is_numeric() == True`, e implementan `is_string() == True`. En `judge_expr`, se excluyen de sentencias `switch` y se emiten a través de cadenas ternarias con `pengu_string_equal`.
- **A3**: En `pengu_codegen.py::bytes_expr`, `bytes of <string>` emite un puntero constante a bytes `((const uint8_t*)((({arg_c})).data))` en lugar de un puntero mutable `(uint8_t*)`, garantizando coherencia con el tipo inferido `ref to frozen byte` y compatibilidad con `-Werror`.

### Corregido (medio)

- **M1**: En `pengu_codegen.py::judge_expr`, los patrones de variantes calificadas (`when MyOmen.Variant`) normalizan el identificador para resolver variantes tanto bajo su nombre simple como con prefijos `insignia` o tipos de declaración `.d.pengu`, emitiendo los identificadores C correctos (`_get_omen_variant_c_name`).
- **M2**: En `pengu_codegen.py::_is_single_char_or_byte`, se desempaquetan en bucle cadenas anidadas arbitrarias de `SealType`, `AliasType` y `FrozenType`.
- **M3**: En `pengu_codegen.py::_lookup_with_field_type`, se desempaquetan en bucle `SealType`, `AliasType`, `FrozenType` y `RefType` tanto en el tipo base del bloque `with:` como en cada acceso a subcampo, resolviendo además nombres `BaseType` en la tabla de tipos.

### Corregido (menor)

- **m1**: En `pengu_checker.py::_check_weave_decl`, se rechaza que el punto de entrada `main` retorne un `OmenType` (incluso si es un enum entero no algebraico) con `E0020`.
- **m2**: En `pengu_infer.py::banish_expr`, el mensaje de ayuda de `E0008` clarifica que los tipos nominales sellados (`seal`) no son liberables directamente y requieren un cast explícito (`banish (v to string)`). Asimismo, `pengu_codegen.py::_translate_banish_target` desempaqueta `SealType` hacia el tipo subyacente.
- **m3**: En `pengu_checker.py::_extract_preceding_doc`, se eliminan en bucle todos los caracteres almohadilla `#` iniciales y finales, limpiando líneas de documentación como `# # # Comment`.

## [0.13.8] - 2026-09-17

### Corregido (crítico)

- **C1**: En `pengu_codegen.py`, `_translate_unwrap_expr` ahora ejecuta todas las sentencias `defer`, `errdefer` (en rutas de error) y llamadas de `auto-banish` de variables locales antes de emitir los retornos anticipados en expresiones `or_return` y `try_expr`, previniendo fugas deterministas de memoria en flujos de error o propagación.
- **C2**: En `pengu_checker.py`, `_check_const_decl` rechaza con `E0035` declaraciones de constantes cuyos nombres coincidan con palabras clave o tipos/macros reservados de C en archivos `.pengu`. Asimismo, en `pengu_codegen.py::generate_global_constants` se aplica `_c_ident(name)` a los `#define` y declaraciones `static const`.
- **C3**: En `pengu_codegen.py`, en la sustitución de `var_ref` por `sym.const_val`, se restringe el plegado exclusivamente a símbolos inmutables (`not sym.is_mutable` y `kind in ("const", "let")`), evitando que variables mutables `var` retengan valores plegados desactualizados e ignoren posteriores sentencias `set`.

### Corregido (alto)

- **A1**: En `pengu_codegen.py`, se preserva el nombre C efectivo de la función de entrada (`self.main_c_name`), de modo que directivas `insignia` aplicadas a `weave main` emitan la llamada correcta (p. ej. `mylib_main()`) en `generate_entry_point` en lugar de fallar en el enlazador con `undefined reference to pengu_main`.
- **A2**: En `pengu_checker.py`, en `_collect_top_level`, se validan los nombres de funciones en `weave_decl` y `declare_stmt` contra palabras clave y macros estándar de C en archivos `.pengu`, rechazando con `E0035` colisiones peligrosas con funciones de la biblioteca estándar de C como `printf` o `malloc`.
- **A3**: En `pengu_checker.py`, se detectan y rechazan con `E0046` múltiples definiciones de puntos de entrada `weave main` activos en un mismo proyecto o entre módulos importados.
- **A4**: En `pengu_infer.py`, `bytes of <string>` ahora devuelve un tipo de referencia inmutable `ref to frozen byte`, reflejando fielmente la semántica de vista de sólo lectura sobre `.rodata` y rechazando mutaciones en tiempo de compilación con `E0006`.

### Corregido (medio)

- **M1**: En `pengu_checker.py`, se amplió `C_RESERVED_TYPE_NAMES` con los tipos typedef fundamentales del runtime (`PenguString`, `PenguList`, `PenguMap`, `PenguSlice`, `PenguMaybe`, `PenguResult`, `PenguRange`, `PenguFrame`), rechazando colisiones con `E0035`.
- **M2**: En `pengu_codegen.py`, `_lookup_with_field_type` aplica `_c_ident` al buscar campos y subcampos en estructuras y uniones de bloques `with:`.
- **M3**: En `pengu_checker.py`, `_check_omen_variant_collisions` comprueba colisiones tanto contra el nombre lógico como contra el nombre C (`c_name`), detectando colisiones introducidas por directivas `insignia`.

### Corregido (menor)

- **m1**: En `pengu_checker.py`, `_extract_preceding_doc` normaliza el descarte de prefijos y sufijos `#` de forma robusta ante líneas de encabezado como `###`.

## [0.13.7] - 2026-09-17

### Corregido (crítico)

- **#1**: En `pengu_checker.py`, se rechazan con `E0035` declaraciones de tipos definidos por el usuario (`rune`, `echo`, `omen`, `seal`, `alias`, `concept`) cuyos nombres coincidan con palabras clave o macros estándar de C (como `int`, `char`, `NULL`, `FILE`, `bool`, etc.), impidiendo la emisión de definiciones de tipos inválidas en C. Se excluyen los archivos de enlace C `.d.pengu`.

### Corregido (alto)

- **#2**: En `pengu_codegen.py`, en `judge_expr` sobre valores int/enum, la evaluación de `else_val` ahora se realiza de forma perezosa dentro de la rama `default: _res = ({else_val}); break;` del switch en lugar de evaluarse incondicionalmente al declarar el temporal.
- **#3**: En `pengu_checker.py`, `chr_expr` se elimina de la lista de exclusión en `_is_fresh_heap_expr` y se añade como expresión asignadora de heap para `string`, habilitando su auto-liberación (`auto-banish`) y previniendo fugas de memoria deterministas.
- **#4**: En `pengu_checker.py` y `pengu_codegen.py`, se restringe la concatenación `+=` para no aplicarse a tipos `SealType` nominales basados en string, garantizando la inviolabilidad del tipado nominal a menos que se haga una conversión explícita.

### Corregido (medio)

- **#5**: En `pengu_checker.py`, `_check_const_decl` ahora acepta tipos compuestos estáticos no-heap (incluyendo omens algebraicos, runes y echos con miembros numéricos o estáticos) como elementos base de arrays constantes `const`.
- **#6**: En `pengu_checker.py`, `_check_const_decl` utiliza `_is_ref_char_type` para reconocer punteros constantes a char que incluyan calificaciones `ref to frozen char` o alias a char/byte.
- **#7**: En `pengu_codegen.py`, `_translate_string_lit` desenvuelve correctamente alias, frozen y seals para interpolación `%c` de char/byte, y reconoce `ref to byte` y alias a `ref to char` con casteo a `(const char*)` para formato `%s`.
- **#8**: En `pengu_codegen.py`, `_is_string_expr` utiliza consistentemente `.is_string()` en todos los chequeos de retorno y tipo inferido en vez de `name == "string"`, soportando alias a string.
- **#9**: En `pengu_checker.py`, se detectan colisiones silenciosas entre identificadores escapados en C (`_c_ident`), rechazando con `E0035` campos de runes y echos que generarían el mismo identificador en C (como `FILE` y `_FILE`).

### Corregido (menor)

- **#10**: En `pengu_checker.py`, `_check_weave_decl` sustituye la lista blanca incompleta de sentencias por un filtro que excluye únicamente parámetros y modificadores, garantizando que todas las sentencias del cuerpo sean analizadas para escape y retornos implícitos.
- **#11**: En `pengu_checker.py`, `_check_weave_decl` valida que el punto de entrada `weave main` únicamente retorne tipos enteros o `void`, rechazando con `E0020` firmas inválidas (punteros a función, structs, etc.).
- **#12**: En `pengu_codegen.py`, los literales numéricos interpolados directamente en strings se castean a `(int32_t)` para prevenir advertencias `-Wformat` de GCC.
- **#13**: En `pengu_codegen.py`, en bucles `for i, v in start to end`, la variable de índice `i` se declara explícitamente como `int32_t` previo al encabezado del bucle, concordando con `INT_TYPE` y evitando warnings de `-Wconversion`.

## [0.13.6] - 2026-09-17

### Corregido (crítico)

- **#1**: En `pengu_checker.py`, `_check_const_decl` ahora valida exhaustivamente que los elementos base de constantes de tipo array (`ArrayType`) sean estáticamente inicializables en C en tiempo de compilación (tipos numéricos, booleanos, char, o `ref to char`). Se rechazan con `E0005` constantes de tipo array de strings o estructuras heap que emitían llamadas en runtime no válidas para inicializadores estáticos C99.

### Corregido (alto)

- **#2**: En `pengu_codegen.py`, `generate_function_prototypes`, `generate_function_definitions`, `_register_one_lambda` y `return_stmt` ahora utilizan `CTypeMapper.to_c_decl` para construir firmas de retorno y declaraciones de variables cuando la función o lambda retorna un puntero a función (`FnType`), emitiendo C99 válido (`Ret (*fn(params))(Args)`).
- **#3**: En `pengu_codegen.py`, `_c_ident` protege los identificadores `NULL`, `bool`, `true`, `false`, `_Bool`, `wchar_t`, `FILE`, así como las palabras clave de C11 (`_Alignas`, `_Alignof`, `_Atomic`, `_Generic`, `_Noreturn`, `_Static_assert`, `_Thread_local`), escapándolos como `_<name>` para evitar colisiones con macros de `<stdbool.h>` y `<stddef.h>`.

### Corregido (medio)

- **#4**: En `pengu_codegen.py`, el acceso `.value` en `maybe T` y `.ok_val`/`.err_val` en `result` utiliza `CTypeMapper.to_c_decl(elem_t, "*")` para generar el casteo de desreferenciación correcto cuando `T` es un `FnType` (puntero a puntero a función `Ret (**)(Args)`).
- **#5**: En `pengu_codegen.py`, `judge_expr` cuando no tiene un tipo de resultado explícito utiliza `__typeof__(({else_val}))` e inicializa el temporal `{decl_res} = ({else_val});` previo a la sentencia `switch`, evitando errores de inicialización faltante de `__auto_type` en GCC y eliminando el uso inválido de `(__auto_type){0}`.
- **#6**: En `pengu_codegen.py`, la interpolación de strings (`_translate_string_lit`) y la comprobación `_is_string_expr` emplean métodos semánticos (`t.is_string()`, `t.is_int()`, `t.is_float()`, `t.is_bool()`), soportando correctamente tipos envueltos en `AliasType` o `FrozenType`.

### Corregido (menor)

- **#7**: En `pengu_checker.py` y `pengu_codegen.py`, `compound_set_stmt` con `+=` sobre tipos que descienden a `string` (como `AliasType(string)`) ahora es aceptado y emite `pengu_string_concat`.
- **#8**: En `pengu_checker.py`, `_check_omen_variant_collisions` ignora colisiones entre constantes del mismo archivo (`first_path == other_path`), delegando el diagnóstico al chequeo de redefinición intra-archivo.
- **#9**: En `pengu_types.py`, `estimate_size` evalúa `max(1, t.size or 1)` defensivamente para prevenir `TypeError` cuando una dimensión de array aún no ha sido resuelta.
- **#10**: En `pengu_codegen.py`, `_translate_string_lit` lanza un `SemanticError` explícito cuando se intenta interpolar un tipo no soportado, en lugar de generar accesos inválidos a `.data` y `.len`.
- **#11**: En `pengu_codegen.py`, `_translate_value_if` alinea `then_prologue` con el nivel de indentación contextual del bloque.
- **#12**: En `pengu_codegen.py`, `ord_expr` evalúa la expresión de entrada una sola vez en un temporal de bloque `_ord_s`, evitando efectos secundarios dobles ante llamadas a funciones y validando longitud no nula.

### Tests

- `tests/test_regression_0_13_6.py`: suite completa de regresión para las 12 correcciones de 0.13.6.

## [0.13.5] - 2026-09-17

### Corregido (crítico)

- **#1**: En `pengu_codegen.py` y `pengu_checker.py`, se unifica la resolución del `step_node` en `_translate_for_range` y `_check_for_range_stmt` usando `len(node.children) == 5 and node.children[3] is not None` y `block_node = node.children[-1]`. Esto evita fallbacks erróneos que interpretaban el cuerpo del bucle como expresión de paso.
- **#2**: En `pengu_checker.py` y `pengu_codegen.py`, soporte completo para bucles descendentes (`for i from 5 to 0 step -1`). El checker valida que `start >= end` ante pasos negativos (y rechaza `step == 0` con `E0042`), y el codegen emite la condición de corte descendente (`>`) e incrementos negativos (`--` / `+= step`) respetando la semántica *end-exclusive*.

### Corregido (alto)

- **#3**: En `pengu_codegen.py`, `judge_expr` utiliza `CTypeMapper.to_c_decl` para declarar los temporales de resultado y valor cuando son de tipo función (`FnType`), y emite `NULL` por defecto si `res_type` es una función o referencia, evitando sintaxis de declarador C inválida.
- **#4**: En `pengu_codegen.py`, `_translate_banish_target` desenvuelve iterativamente tipos `FrozenType` y `AliasType`, armonizando la selección del método de liberación (`pengu_banish_string`, `pengu_banish_list`, `pengu_banish_map`, o puntero de referencia).

### Corregido (medio)

- **#5**: En `pengu_codegen.py`, `var_ref` dentro de `with_stack` consulta el tipo del objeto receptor y emite el operador flecha `->` cuando es un `RefType`, evitando emitir accesos directos con punto `.` sobre punteros a estructuras.
- **#6**: En `pengu_codegen.py`, `_translate_or_block` exige un `target_ident` explícito cuando se proporciona un `target_decl`, eliminando el fallback basado en `.split()[-1]` que fallaba ante declaradores de tipo función.
- **#7**: En `pengu_codegen.py`, `_translate_string_lit` utiliza la especificación `%.*s` con `(int)(expr).len, (expr).data` para strings interpolados en `pengu_string_format`, sin asumir terminación en NUL en buffers de `PenguString`.
- **#8**: En `pengu_codegen.py` y `pengu_checker.py`, `const` con literales de array emite inicialización estática C99 (`static const <base> <name>[dims] = { ... };`), y el checker rechaza `const` de tipo `map` o `list` con `E0005` indicando que requieren alocación dinámica en el heap.

### Corregido (menor)

- **#10**: En `pengu_checker.py`, se evita la duplicación del error `E0014` cuando una declaración `var`/`let` con inicializador `with:` carece de anotación de tipo.
- **#12**: En `pengu_checker.py`, `_check_omen_variant_collisions` enriquece el diagnóstico cuando el valor de una constante no pudo plegarse en tiempo de compilación.
- **#14**: En `pengu_codegen.py`, los accesos indexados a mapas en `at_expr` y `_translate_set_target` utilizan `CTypeMapper.to_c_decl` para el casteo del puntero temporal cuando el valor almacenado es un `FnType`.

### Tests

- `tests/test_regression_0_13_5.py`: suite completa de regresión para las correcciones de 0.13.5.

## [0.13.4] - 2026-09-17

### Corregido (crítico)

- **N10**: En `pengu_codegen.py`, `_emit_iteration_value`, `_translate_for_in` y `for_comp` ahora emplean `CTypeMapper.to_c_decl` para declarar elementos y temporales con tipos funcionales (`FnType`), y `CTypeMapper.to_c_decl(elem_t, "*")` para los casteos a puntero de desreferenciación en colecciones, eliminando errores de sintaxis de declaradores inválidos en C.
- **N11**: En `pengu_checker.py`, `_check_or_block` captura `SemanticError` de `inferrer.infer` sobre el operando izquierdo y registra el error con `_record_error`, asignando `AnyType` y continuando el chequeo del bloque `or:`, preservando la política de acumulación multi-error del compilador.

### Corregido (alto)

- **N12**: En `pengu_infer.py`, el fallback sintáctico en `is_valid_col` para `in_expr` / `not_in_expr` se restringe a `col_t is None`, evitando aceptar expresiones como `x in (10 to float)` como rangos válidos cuando son casts escalares y emitiendo el diagnóstico `E0005`.

### Corregido (medio)

- **N9**: En `pengu_codegen.py`, se aplica `_c_ident` de forma exhaustiva a nombres de variables locales (`var_decl`, `let_decl`, `static_var_decl`), nombres de funciones (`_collect_weave`), parámetros de llamada y receptores encantados, evitando que palabras clave de C (como `asm`, `do`, `while`, etc.) colisionen como identificadores C sin escapar.

### Corregido (menor)

- **N13**: En `pengu_codegen.py`, `struct_init` preserva el nombre raw del campo para la resolución y coincidencia de variantes y campos de `omen`, utilizando el identificador C escapado con `_c_ident` para la emisión del payload y miembros del struct (`.data.{union_field}`), evitando diagnósticos falsos positivos `E0041` cuando una variante coincide con una keyword de C.

### Tests

- `tests/test_regression_0_13_4.py`: suite completa de regresión cubriendo N10, N11, N12, N9 y N13.

## [0.13.3] - 2026-09-17

### Corregido (crítico)

- **N1**: En `pengu_codegen.py`, `break_stmt` y `continue_stmt` ahora liberan las variables con auto-banish registradas en el propio scope del bucle antes de terminar el recorrido (`if kind == "loop": break` movido tras flushear `entries`), eliminando fugas de memoria silenciosas y deterministas.
- **N2**: En `pengu_codegen.py`, `_translate_or_block` y sus llamadores en `var_decl` y `let_decl` emplean `CTypeMapper.to_c_decl(t, name)` y pasan `target_ident` explícito; además, inicializan punteros y referencias con `NULL` y desreferencian valores con casteo a puntero correcto (`ptr_cast = CTypeMapper.to_c_decl(target_type, "*")`), evitando código C inválido con `FnType` o `RefType`.

### Corregido (alto)

- **N3**: `some <FnType>` en `pengu_codegen.py` utiliza `CTypeMapper.to_c_decl(arg_t, tmp)` para el almacenamiento temporal y `sizeof(tmp)` en la asignación heap, generando C válido para valores funcionales encapsulados en `maybe`.
- **N4**: Condicionales con binding tipado como función (`if f as weave ... is opt:`) en `_translate_binding_if` y `_translate_binding_value_if` emiten declaradores de función C válidos (`int32_t (*f)(int32_t) = (*((int32_t (**)(int32_t))_maybe.value))`).

### Corregido (medio)

- **N5**: `_c_ident` en `pengu_codegen.py` protege palabras reservadas adicionales de C (`if`, `else`, `while`, `for`, `do`, `break`, `continue`, `asm`), evitando colisiones en bindings FFI y headers importados.
- **N6**: `_check_set_stmt` en `pengu_checker.py` extiende la verificación de mutabilidad a `at_access`, rechazando modificaciones a elementos de arrays inmutables declarados con `let` (error `E0006`).
- **N7**: En `pengu_codegen.py`, la rama de rango sintáctico en `in_expr` y `not_in_expr` ahora solo actúa como fallback cuando `col_t is None`, evitando emitir range checks erróneos sobre expresiones de conversión (cast `to float`, etc.).

### Tests

- `tests/test_regression_0_13_3.py`: suite completa de regresión con tests unitarios y de compilación/ejecución para N1–N7.

## [0.13.2] - 2026-09-17

### Corregido (crítico)

- **C1**: `_mentions_set_target` en `pengu_checker.py` ahora reconoce `compound_set_stmt` (`set s += ...`), previniendo fugas de memoria por auto-banish indebido en strings reasignados.
- **C2**: `_translate_or_block` en `pengu_codegen.py` ahora envuelve `{ok_read}` dentro de una rama `else` e inicializa por defecto el valor de destino, eliminando el fallo por desreferenciación nula (UB) cuando el manejador `or:` no interrumpe el flujo.
- **C3**: Eliminada la regla sintáctica huérfana `named_stmt` (`x is 5`) y su alias `named_simple` en `pengu_grammar.py` y `pengu_codegen.py`. Las asignaciones requieren explícitamente `set` y las declaraciones `var`/`let`.

### Corregido (alto)

- **H1**: `_check_set_stmt` en `pengu_checker.py` procesa correctamente `arrow_access` (`->`) y `at_access` dentro de cadenas `with_target` (p. ej. `set .p->x is 5`).
- **H2**: `_translate_value_if` en `pengu_codegen.py` utiliza `CTypeMapper.to_c_decl` para declarar temporales de expresiones `if` que evalúan a funciones (`FnType`), generando declaradores C válidos (`ret (*_if_1)(args)`).
- **H3**: `some <array_lit>` es rechazado en `pengu_infer.py` con `TypeMismatchError` (`E0005`) indicando que los arreglos fijos de C no pueden encapsularse por valor en un `maybe`; debe usarse `slice of T` o `ref to array`.
- **H4**: `in` / `not in` valida en `pengu_infer.py` que el operando derecho sea una colección o rango válido (`RangeType`, `string`, `ArrayType`, `SliceType`, `ManyType`, `ListType`, `MapType`, `AnyType`), emitiendo `E0005` ante tipos no soportados.

### Corregido (medio)

- **M1**: Nombres de pruebas unitarias (`test """nombre""":`) con comillas triples o prefijo raw se despojan limpiamente en `_check_test_decl` y `collect_declarations`.
- **M2**: Acceso a campo `.value` sobre `ref to maybe T` y `ref to result of T to E` en `pengu_codegen.py` genera la desreferenciación adecuada mediante operador flecha `(*({elem_c}*){base}->value)`.

### Limpieza y consistencia

- **L1**: Eliminado método muerto `_main_exit_expression` en `pengu_codegen.py`.
- **L2**: `cast_expr` en `pengu_codegen.py` utiliza `self._lookup_type_fn` de forma null-safe.

### Tests

- `tests/test_regression_0_13_2.py`: suite de pruebas de regresión cubriendo C1–C3, H1–H4, M1–M2.

## [0.13.1] - 2026-09-17

### Corregido (residual 0.13.0)

- **R1**: Eliminado un use-after-free residual cuando el valor de un bloque
  (`if`, `unless`, `do:`, loops) era un identificador envuelto en paréntesis
  (`(s)`). El helper `_exclude_escaping_val_from_banish` ahora normaliza
  paréntesis balanceados antes de comparar.
- **R2**: `PenguChecker.check` reinicia `const_definitions` en cada invocación,
  evitando falsos E0046 por colisiones de constantes entre pasadas.
- **R3**: El cuerpo de un `with:` se chequeaba dos veces (una en
  `_check_with_init_body` y otra vía `_check_value_exprs`), duplicando los
  errores. Ahora `_check_with_init_body` setea `_pengu_value_type` en el nodo.

### Corregido (medio)

- **R4**: Eliminada rama muerta `ret_expr.data == "ident"` en `is_err_ret`.
- **R5**: `_translate_or_block` rechaza explícitamente operandos `any` con
  `E0005`, evitando generar C inválido que asumía `PenguResult`.
- **R6**: `_check_or_block` sigue chequeando el cuerpo del `or:` aunque el
  operando sea inválido, restaurando la acumulación multi-error completa.

### Consistencia

- **R7**: `_check_static_var_decl` usa `_decl_layout` como los demás.
- **R8**: `let borrowed a, b is ...` propaga `is_borrowed` a los nombres destructureados.
- **R9**: `decl_layout` se movió a `pengu_symbols.py` como función pública.
- **R10**: Documentada la rama `first is None` en `_has_borrowed_modifier`.

### Tests

- `tests/test_regression_0_13_1.py`: suite de pruebas cubriendo R1–R10.

## [0.13.0] - 2026-09-17

### Corregido (crítico)

- **B1**: `var borrowed x is <expr>` (sin anotación de tipo) ya no provoca
  `IndexError` en el checker ni en el codegen. Se corrigió la lectura de
  children para los 8 layouts posibles de `var`/`let` con/sin `borrowed`
  y con/sin tipo, con un helper compartido `_decl_layout`.
- **B2**: Eliminado un use-after-free determinista al usar un local con
  auto-banish como valor de una iteración de loop en posición de valor
  (`for i from 0 to N: var s is "a" + x; s`). El compilador ya no emite
  `pengu_banish_string(&s)` antes de pushear la copia estructural.
- **B3**: Mismo bug en `if`/`unless`/`do:` en posición de valor. Se unificó
  la lógica de flush bajo un helper común que excluye del banish la variable
  que actúa como valor del bloque.
- **B4**: Las comparaciones de orden (`< <= > >=`) sobre `string` se rechazan
  con `E0005`. Antes se emitía `(a < b)` en C, que no compila para `PenguString`.

### Corregido (medio)

- **M1**: `_check_or_block` acumula el error con `_record_error` en lugar de
  lanzar la excepción, restaurando la política multi-error del checker.
- **M2**: `_translate_or_block` levanta `E0005` explícito cuando el tipo del
  operando es `None` (invariante del checker violado).
- **M3**: `_block_ends_with_jump` / `_stmts_end_with_jump` normalizan los
  aliases de una línea (`return_simple`, `break_simple`, `continue_simple`)
  antes de comprobar si el bloque termina en salto.
- **M4**: Refactor de `_translate_loop_body` y `_translate_value_block_with_banish`
  para compartir la lógica de "push + flush seguro".

### Corregido (menor)

- **m1**: `is_err_ret` en `_translate_stmt` deriva del AST en vez de hacer
  substring matching sobre el C emitido.
- **m3**: `ord` sobre un string con `data == NULL` retorna `0` en vez de
  desreferenciar NULL.
- **m5**: El checker sigue detectando errores de tipo en ramas con condición
  constante (dead code), aunque mantiene el warning `W0004`.
- **m7**: Corregido el mojibake UTF-8 en `CHANGELOG.md`.
- **m10**: Detección de colisión `const` ↔ `const` entre módulos importados
  con valores distintos (`E0046`).

### Documentación

- **m8**: `print` documentado como builtin del compilador en `LANGUAGE.md` §19.
- **m9**: Aclarada la precedencia `pengu.toml` > `pengu.yaml` en `README.md`.
- `LANGUAGE.md` §6.3 y §5.4 actualizados.

### Tests

- `tests/test_regression_0_13_0.py`: tests cubriendo B1–B4, M1–M4, m3, m5, m6.
- Los tests de B2/B3 deben ejecutarse con `-fsanitize=address,undefined` en CI.

## [0.12.0] - 2026-09-16

### Corregido
- **B1**: Importaciones de typing faltantes (`List`, `Dict`, `Optional`, `Tuple`, etc.) en `pengu_parser/pengu_parser.py` para prevenir `NameError` en tiempo de ejecución.
- **B2**: Bloques `or:` fuera de declaraciones `var`/`let`: unificación del lowering en `_translate_or_block` para expresiones en asignaciones (`set_stmt`), retornos (`return_stmt`) y llamadas directas, generando `PenguResult` y captura de error válidos en C.
- **B3**: Iteración `for ... in map`: generación de bucle de ranuras de sondeo abierto acotado por `(col).len` y ranuras activas `is_occupied`, eliminando el uso inválido de `sizeof` sobre punteros a structs.
- **B4**: Acceso e inserción en mapas: corrección de `m at key` generando `pengu_map_get` y de `set m at k is v` generando `pengu_map_put`.
- **B5**: Operadores `in` y `not in` sobre colecciones: implementación de búsqueda secuencial elemento a elemento para `ListType` (mediante `pengu_list_at`) y para tipos `SliceType`/`ManyType`, en lugar de comparación directa de igualdad de punteros.
- **C1**: Emisión de constantes de rango globales: adición de `RangeConst` en el plegado de constantes de `pengu_infer.py` y generación correcta de inicializadores `(PenguRange){.start = ..., .end = ...}` en `pengu_codegen.py`.
- **C2**: Validación dimensional de arrays contra literales entre corchetes `[...]`: comprobación de longitud estática en `pengu_checker.py` con emisión de `E0041` (`ArraySizeMismatchError`) ante desajustes.
- **C4**: Preservación de variables en bucles: prevención de colisión donde la variable iteradora sobreescribía vinculaciones del ámbito exterior con el mismo nombre tras salir del bucle.
- **C5**: Limpieza de `with_stack` ante excepciones: encapsulamiento del procesamiento de `with_stmt` en `try ... finally: self.with_stack.pop()` para evitar fugas de contexto en el generador de código.
- **L1**: Limpieza de ramas `if/elif` redundantes en `_check_omen_variant_collisions` dentro de `pengu_checker.py`.
- **L3**: Evaluación única en `judge_expr`: el sujeto de la expresión de juicio se evalúa una sola vez asignándolo a un temporal `__auto_type` en una statement-expression en C si contiene posibles efectos secundarios o llamadas.
- **L4**: Detección de errores en interpolación de cadenas: `_translate_string_lit` eleva un `SemanticError` (`E0019`) ante fallos de re-parseo de expresiones interpoladas en lugar de ignorarlos silenciosamente.

### Cambiado
- **L2**: Cláusulas `when` con vinculación de payload (`when Variant with a, b -> ...`) en expresiones `judge`: deshabilitadas explícitamente y rechazadas con error semántico `E0005` indicando que el desempacado de payload en `when` aún no está soportado.

### Añadido
- **`std.ffi.cstr_free`**: Declaración nativa `cstr_free with p as ref to char into void` en `std/ffi.pengu` para liberar cadenas C asignadas en FFI de manera segura.
- **Suite de regresión**: `tests/test_regression_0_12_0.py` con 12 tests unitarios (T1–T10, L2) cubriendo exhaustivamente todos los fallos corregidos en esta versión.

### Corregido (fase 2)

- **Codegen**: `map at k` ya no envuelve la expresión-statement en un
  `*(…)` redundante que producía `*(int32_t)` (C inválido). Aplica tanto
  a `m at k` como a la rama de `_translate_access_op`.
- **Codegen**: `ref to map at k` ahora cae en la rama correcta y emite
  `pengu_map_get(m, …)` en lugar de `m[i]`.
- **Codegen**: `for … in <map> then <expr>` (comprensión) emite un bucle
  válido contra `PenguMap` en lugar de `sizeof(m)/sizeof((m)[0])`.
- **Checker**: `_validate_array_literal_size` ya no permite que un
  literal singleton (`[1]`) inicialice un array de tamaño mayor; ahora
  levanta `E0041` como cualquier otro mismatch.
- **Tipos**: `ArrayType.is_compatible` compara tamaños cuando ambos
  lados son conocidos, impidiendo pasar un `array of T with size 3`
  donde se espera `array of T with size 5`.
- **Codegen**: `_translate_or_block` ya no descarta silenciosamente el
  handler cuando el tipo inferido del LHS no es `maybe`/`result`;
  ahora levanta `E0005` (compiler bug) en su lugar.
- **Checker / Inferrer**: el rechazo de payload bindings en `judge`
  (`when Variant with field`) ya no se duplica entre los dos módulos.

### Documentación (fase 2)

- **LANGUAGE.md §12**: actualizada la advertencia sobre `or:` — ahora
  funciona en `var`/`let`/`set`/`return`/`expr_stmt`.
- **LANGUAGE.md**: cabecera sin versión hardcodeada.
- **CHEATSHEET.md §6.4**: corregido el C emitido por `map at k`; añadida
  fila para `ref to map`.
- **CHEATSHEET.md §7.2**: añadido el C de ejemplo para iterar un map.
- **CHEATSHEET.md §11.2**: corregido el ejemplo `(int32_t)(_res.ok_val)`
  a `*(int32_t*)_res.ok_val`.

### Tests

- Nuevos tests T1–T11 cubriendo los fixes de la fase 2.

## [0.11.0] - Unreleased

### Fixed — Nested `with:` blocks (construction & editing)

Previously, nesting a `with:` builder inside another `with:` block — either as
the initializer of a field being constructed (`var p as Person with: … set
.address is with: …`) or as the value of a `set` inside a `with target:` scope
— failed during code generation with:

    SemanticError: [line 1, col 1] 'with:' block construction requires a
    struct-like target type (rune/echo/omen) from an explicit annotation

The root cause was that `PenguCodegen._translate_stmt` resolved the target type
of a `set` statement by calling `self._infer_node_type(inner_target)`, and the
inferrer has no context for `with_target` (leading-dot field) nodes. When the
inference returned `None`, the existing fallbacks only covered `normal_target`
and bare `Token` targets — leaving `with_target` (the shape that appears inside
every `with:` block) unhandled. The nested `with_init_expr` then received
`expected_type = None` and could not determine its target type, so it raised
the diagnostic above.

The fix mirrors the checker's existing behaviour:

- **New helper `PenguCodegen._lookup_with_field_type`** resolves a field's type
  through the active `with_stack` (looking through `ref to T` and falling back
  to the codegen's own collected `runes`/`echos` field maps when the
  `RuneType` only carries a name).
- **`set_stmt` and `compound_set_stmt`** now call the helper when the target is
  a `with_target` and inference returns `None`. This is strictly additive: the
  old code paths are unchanged, and the new path only triggers where a
  `SemanticError` (or invalid C) was previously produced.
- **Rvalue expression handling in `set_stmt`**: avoids emitting `memcpy` with
  address-of (`&`) on rvalue/statement-expression blocks, which would be invalid C.
- **Chained access support in `pengu_checker.py`**: resolves nested member
  accesses (such as `set .c.n += 10`) on `with_target` AST nodes.

Supported today (with arbitrary nesting depth):

```pengu
# Construction
var a as Person with:
  set .name is "John"
  set .address is with:            # nested builder, inferred from Person.address
    set .street is "123 Main St"
    set .city is "New York"

# Editing
with a:
  set .name is "Jane"
  set .address is with:            # nested builder, same rules
    set .street is "456 Elm St"
    set .city is "Los Angeles"
```

Three-level nesting, nesting inside a loop-collect body, and compound
assignment inside a nested scope are covered by new tests.

### Tests

- `tests/test_nested_with_init.py`:
  - `test_nested_with_creation` — 2-level construction, verifies distinct
    `_with_N` temporaries and correct runtime output.
  - `test_nested_with_editing` — same shape inside `with a:` (edit in place).
  - `test_triple_nested_with` — 3-level construction.
  - `test_nested_with_in_loop_collect` — `with:` inside a value-position loop.
  - `test_nested_with_field_type_mismatch` — the checker still rejects type
    errors inside a nested builder (the fix does not weaken type checking).
  - `test_compound_set_inside_nested_with` — `set .c.n += 10` inside `with w:`.
  - `test_lookup_with_field_type_resolves_rune_field` — unit test for the new
    helper.
  - `test_lookup_with_field_type_empty_stack` / `_unknown_field` — negative
    cases.

### Documentation

- `LANGUAGE.md` §9.1 (`rune`) and §18 (`Block-style construction`) now show
  the nested-construction and nested-editing forms with runnable examples.

## [0.10.1] - Unreleased

### Runtime hardening (0.10.1) — octava pasada

- **Fase 1 — Desajuste entre documentación y comportamiento (N6)**:
  - **`pengu_string_from_bool`**: Corrección de la docstring que erróneamente indicaba que `pengu_banish_string` sobre el retorno era un no-op. El retorno tiene longitud `4` o `5`, por lo que llamar a `pengu_banish_string` ejecuta `free()` sobre un puntero a rodata, lo que constituye comportamiento indefinido (UB) / corrupción de heap. Se reemplazó la nota por una advertencia `@warning` explícita instruyendo copiar con `pengu_string_copy` antes de liberar, y se documentó el literal en el código con un comentario interno.

- **Fase 2 — Resolución del contrato de NUL-terminación (N7 — Opción A adoptada)**:
  - **Decisión adoptada**: Se seleccionó la **Opción A** (endurecer todos los consumidores) para alinearse estrictamente con el contrato formal de `PenguString` establecido en la ronda 7 ("PenguString NO garantiza NUL-terminación").
  - **`pengu_c_getenv`**: Copia `name` a un búfer temporal NUL-terminado antes de consultar `getenv()`.
  - **`pengu_c_setenv`**: Copia `name` y `value` a búferes temporales NUL-terminados antes de invocar `_putenv_s()` o `setenv()`.
  - **`pengu_c_unsetenv`**: Copia `name` a un búfer temporal NUL-terminado antes de invocar `_putenv_s()` o `unsetenv()`.
  - **`pengu_c_chdir`**: Copia `path` a un búfer temporal NUL-terminado antes de llamar a `_chdir()` o `chdir()`.
  - **`pengu_c_strftime`**: Copia `fmt` a un búfer temporal NUL-terminado antes de llamar a `strftime()`.
  - Esto garantiza que ninguna función del runtime lea más allá de `len` bytes ni cause fallos de segmentación cuando recibe cadenas no terminadas en NUL (como vistas sobre fragmentos de memoria o buffers FFI).

- **Fase 3 — Verificaciones**:
  - **Compilación estricta C11 (V1)**: `gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only pengu_runtime.h` con 0 errores y 0 advertencias.
  - **Compilación con sanitizadores (V2)**: `gcc -std=c11 -fsanitize=address,undefined -Wall -Wextra -fsyntax-only pengu_runtime.h` con 0 advertencias.
  - **Nuevos tests (V3)**: Pruebas añadidas en `tests/test_runtime_strings.py` (N6) y `tests/test_runtime_files.py` (N7, validando getenv, setenv, unsetenv, chdir y strftime con vistas parciales no NUL-terminadas).
  - **Suite completa (V4)**: Suite completa de pytest ejecutada y aprobada al 100%.

### Runtime hardening (0.10.1) — séptima pasada

- **Fase 1 — Contrato explícito de NUL-terminación (Documentación pura)**:
  - **`PenguString`**: Formalización del contrato de NUL-terminación en la docstring del typedef. Se documenta explícitamente que `PenguString` NO garantiza que `data` esté terminado en NUL (p.ej. vistas no propietarias creadas mediante `pengu_string_as_slice` o sobre buffers parciales). Aunque los constructores del runtime sí generan terminación en NUL, las funciones consumidoras que delegan en APIs de C que requieren cadenas NUL-terminadas no deben asumir esta propiedad sin comprobación o copia previa.

- **Fase 2 — Read-past-buffer en parsers que asumen NUL (N1)**:
  - **`pengu_parse_int` (N1a)**: Evita lecturas fuera de límites copiando `s` a un búfer temporal NUL-terminado en el heap antes de invocar `strtoll`. Soporta correctamente vistas no NUL-terminadas y rechaza de forma determinista cadenas con NULs embebidos o basura residual.
  - **`pengu_parse_float` (N1b)**: Misma corrección utilizando un búfer temporal NUL-terminado antes de invocar `strtod`.
  - **`pengu_c_strptime` (N1c)**: Copia `s` a un búfer temporal NUL-terminado antes de evaluar patrones con `sscanf`, previniendo lecturas más allá de `s.len`.

- **Fase 3 — getcwd dinámico (N2)**:
  - **`pengu_c_getcwd`**: Eliminado el límite fijo arbitrario de 4096 bytes. En POSIX se utiliza `getcwd(NULL, 0)` (extensión GNU/BSD) para asignación dinámica automática. En Windows, se utiliza el búfer de stack para el caso común y se escala dinámicamente con `_getcwd` en búferes crecientes (hasta 64 KB) si la ruta excede el tamaño.

- **Fase 4 — Documentación de pattern vacío (N4)**:
  - **`pengu_c_archivum_glob`**: Añadida nota `@note` documentando que un `pattern` con `len == 0` matchea todas las entradas (comportamiento implícito "match-all" de `pengu__find_sub`). Para no matchear nada, se debe proporcionar un patrón que no coincida con ningún nombre.

- **Fase 5 — Documentación de snprintf con NULs embebidos (N3)**:
  - **`pengu_c_archivum_read_dir`, `remove_dir`, `glob_rec`, `walk_rec`**: Añadidas notas `@note` aclarando que la construcción de rutas mediante `snprintf` y especificadores de formato trunca en el primer byte NUL embebido, lo cual es puramente teórico dado que los sistemas de archivos reales rechazan nombres con bytes NUL.

- **Fase 6 — Documentación de strftime (N5)**:
  - **`pengu_c_strftime`**: Añadida nota `@note` documentando el límite del búfer local de 512 bytes y su comportamiento ante formatos extendidos de usuario.

- **Fase 7 — Verificaciones**:
  - **Compilación estricta C11 (V1)**: `gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only pengu_runtime.h` con 0 errores y 0 advertencias.
  - **Compilación con sanitizadores (V2)**: `gcc -std=c11 -fsanitize=address,undefined -Wall -Wextra -fsyntax-only pengu_runtime.h` con 0 advertencias.
  - **Nuevos tests (V3)**: Pruebas añadidas en `tests/test_runtime_strings.py` (N1a, N1b), `tests/test_runtime_time.py` (N1c) y `tests/test_runtime_files.py` (N2, N4).
  - **Suite completa (V4)**: Suite completa de pytest ejecutada y aprobada al 100%.

### Runtime hardening (0.10.1) — sexta pasada

- **Fase 1 — Bug crítico residual (Windows realpath OOM)**:
  - **`pengu_c_archivum_realpath` (C15d-Win)**: Corrección de regresión introducida en la ronda 5 en la rama `#if PENGU_WINDOWS`. Si la asignación dinámica `malloc((size_t)len)` para rutas de longitud `>= 4096` fallaba por OOM, `len` conservaba el valor requerido devuelto por `GetFullPathNameA` y `target` permanecía apuntando al buffer de stack no inicializado `buf`. En la ruta de salida, `pengu_string_new(target)` leía memoria basura no inicializada pudiendo causar fallos de segmentación o lecturas indeterminadas. La corrección marca explícitamente `len = 0` ante fallo de `malloc`, retornando limpiamente `pengu_maybe_none()` sin tocar `buf`. La rama POSIX (que emplea `realpath(cpath, NULL)`) no está afectada.

- **Fase 2 — Correctitud NUL-aware**:
  - **`pengu_c_archivum_glob_rec` (B30)**: Migración de `strstr` y `strcmp` a búsquedas binario-exactas (NUL-aware) usando `pengu__find_sub` y comparación con `memcmp` y longitud exacta `name->len == pattern.len`. La extensión y los nombres sin comodines ahora preservan el patrón NUL-aware establecido en las rondas 3–5.

- **Fase 3 — Overflow 32-bit en helpers**:
  - **`pengu_list_push` y `pengu_map_put` (A20)**: Protección contra desbordamiento en arquitecturas de 32 bits en el producto `(size_t)new_cap * elem_size` comprobando `(size_t)new_cap > SIZE_MAX / list->elem_size` antes de invocar `realloc`. En `pengu_map_put` y `pengu_map_put_string_int`, se añadió verificación contra `(SIZE_MAX / 2) / sizeof(PenguMapEntry)`.
  - **`pengu_string_replace` (A21)**: Protección contra desbordamiento de `ptrdiff_t` en el cálculo `count * delta` en arquitecturas de 32 bits. Se utiliza aritmética de 64 bits (`int64_t delta` y `int64_t new_len_64 = (int64_t)s.len + (int64_t)count * delta`) para verificar los límites `[0, INT_MAX]` antes de asignar o retornar de forma segura cadena vacía.

- **Fase 4 — Documentación**:
  - **Asimetría owning/no-owning (D14)**: Nota `@note` en `pengu_string_from_bool` explicando que a diferencia de `pengu_string_from_char` (que asigna memoria propietaria en heap), `from_bool` retorna una vista constante sobre rodata (`"true"` / `"false"`), dado que los booleanos son un conjunto finito de dos valores sin bytes binarios, y `pengu_banish_string` es un no-op sobre ellos.
  - **Límite real de read_symlink (D15)**: Actualizada docstring de `pengu_c_archivum_read_symlink` indicando que el límite real aceptado es de 4094 bytes (buffer de 4096 bytes solicitando 4095 a `readlink` y rechazando el valor 4095) para evitar de forma conservadora devolver rutas truncadas.

- **Fase 5 — Verificaciones**:
  - **Compilación estricta C11 (V1)**: `gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only pengu_runtime.h` verificado con 0 errores y 0 advertencias.
  - **Compilación con sanitizadores (V2)**: Verificación con `gcc -std=c11 -fsanitize=address,undefined -Wall -Wextra -fsyntax-only pengu_runtime.h` con 0 advertencias.
  - **Nuevos tests (V3)**: Pruebas unitarias de regresión y cobertura añadidas en `tests/test_runtime_files.py` (C15d-Win y B30), `tests/test_runtime_collections.py` (A20) y `tests/test_runtime_strings.py` (A21).
  - **Suite completa (V4)**: Suite completa de pytest ejecutada y aprobada al 100%.

### Runtime hardening (0.10.1) — quinta pasada

- **Fase 1 — Consistencia NUL (Fix semántico y Behavior Change)**:
  - **`pengu_string_char_at` y `pengu_string_from_char` (S1)**: **Behavior change**: `chr 0` y `char_at` sobre posiciones con byte NUL (`'\0'`) ahora retornan una cadena propia de longitud 1 (`{data=[NUL], len=1}`) en lugar de colapsar a cadena vacía (`{data="", len=0}`). Esto resuelve la inconsistencia observable con `pengu_string_split(s, "")` (que siempre produce cadenas de longitud 1 para cada byte) y con constructores binarios.
  - **Migration**: Código o pruebas que comprobaran `len == 0` al extraer un byte NUL con `char_at` o `from_char` deben actualizarse para esperar `len == 1` y `data[0] == '\0'`.

- **Fase 2 — Truncación Silenciosa (Archivum)**:
  - **`pengu_c_archivum_walk_rec` (C15b)**: Eliminada la truncación silenciosa en buffers fijos de 4096 bytes. Si `snprintf >= sizeof(sub)`, se asigna dinámicamente memoria en heap para continuar la recursión en directorios profundos sin omitir subdirectorios.
  - **`pengu_c_archivum_read_symlink` (C15c)**: Comprobación estricta de longitud de destino `len == sizeof(buf) - 1` en `readlink`. Destinos que excedan la capacidad del buffer son rechazados retornando `none` en lugar de devolver una ruta truncada.
  - **`pengu_c_archivum_realpath` (C15d)**: En POSIX se emplea `realpath(cpath, NULL)` (POSIX.1-2008) para asignar dinámicamente el búfer canónico exacto; en Windows se comprueba el retorno de `GetFullPathNameA` y se redimensiona dinámicamente si la ruta excede 4096 bytes.

- **Fase 3 — Checks de Retorno en Funciones libc de Tiempo**:
  - **`pengu_c_strftime` y 18 getters de calendario (C16)**: Manejo seguro del valor de retorno de `gmtime_s` / `gmtime_r` y `localtime_s` / `localtime_r`. Ante timestamps fuera de rango (como valores infinitos o que desbordan `time_t`), `pengu_c_strftime` retorna cadena vacía y los 18 getters de componentes UTC y locales (`year`, `month`, `day`, `hour`, `minute`, `second`, `weekday`, `yearday`, `is_dst`) retornan `0` (o `false`) sin desreferenciar memoria no inicializada ni incurrir en UB.

- **Fase 4 — Overflow Defensivo en Helpers**:
  - **`pengu__find_sub` (A18)**: Guarda defensiva `if (needle.len > hay.len - from_idx) return -1;` y condición de bucle `i <= hay.len - needle.len`, previniendo desbordamiento de enteros con signo en `i + needle.len`.
  - **`pengu_map_put` y `pengu_map_put_string_int` (A19)**: Verificación de límite `if (old_cap > INT_MAX / 2) return;` antes de duplicar la capacidad del mapa, rechazando silenciosamente la inserción de manera consistente con `pengu_list_push`.

- **Fase 5 — Documentación**:
  - **Semántica NUL en char_at / from_char (D11)**: Actualizadas docstrings documentando el retorno exacto de cadenas de longitud 1 para cualquier byte (incluyendo `\0`).
  - **Truncación en Archivum (D12)**: Documentadas las notas `@note` en `read_symlink`, `realpath` y `walk_rec` especificando los límites y el uso de asignación dinámica.
  - **Limitación LLP64 de read_file (D13)**: Añadida nota `@note` en `pengu_c_archivum_read_file` indicando que en plataformas Windows (LLP64) `ftell` devuelve `long` de 32 bits, por lo que archivos mayores a 2 GB no son leíbles (`ftell` devuelve -1).

- **Fase 6 — Verificaciones**:
  - **Compilación estricta C11 (V1)**: `gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only pengu_runtime.h` verificado con 0 advertencias y 0 errores.
  - **Nuevas suites de tests (V2)**: Tests añadidos en `tests/test_runtime_strings.py`, `tests/test_runtime_collections.py`, `tests/test_runtime_files.py` y nueva suite dedicada `tests/test_runtime_time.py`.
  - **Suite completa (V3)**: Ejecución completa de la suite de pruebas sin fallos.

### Runtime hardening (0.10.1) — cuarta pasada

- **Fase 1 — Bug Sistemático / Root Cause**:
  - **`pengu_c_rand_range` (A17)**: Eliminación de comportamiento indefinido (UB) en la conversión double a int con rangos amplios (`min = INT_MIN, max = INT_MAX`). El producto `pengu_c_rand_double() * range` puede superar `INT_MAX`, causando UB en el cast `(int)`. Se utiliza un intermediario de 64 bits (`int64_t offset`) y suma en 64 bits antes de estrechar a `int`.

- **Fase 2 — Overflow Aritmético en Constructores de String**:
  - **`pengu_string_concat` (A14)**: Prevención de desbordamiento entero en `a.len + b.len`. Se comprueba `a.len > INT_MAX - b.len` (y `a.len < 0 || b.len < 0`), retornando vista vacía segura en lugar de incurrir en UB numérico y truncación.
  - **`pengu_string_repeat` (A15)**: Rechazo antes de `malloc` si `total_len > (size_t)INT_MAX`, evitando truncación a enteros negativos y fugas permanentes de memoria en `pengu_banish_string`.
  - **`pengu_string_replace` (A16)**: Rechazo si `new_len_signed > (ptrdiff_t)INT_MAX` o negativo, evitando desbordamiento y truncación en el cálculo de longitud resultante.
  - **`pengu_c_archivum_read_file` (B29)**: Si el tamaño del archivo o los bytes leídos exceden `INT_MAX`, se libera el búfer y se retorna `pengu_maybe_none()`, impidiendo truncaciones silenciosas al asignarse a `int len`.

- **Fase 3 — Correctitud NUL-Aware**:
  - **`pengu_string_replace` (B26)**: Eliminación de `strstr` en la ruta de búsqueda y reemplazo. Se implementa el helper `pengu__find_sub` basado en `memcmp` byte a byte, respetando `from.len` y permitiendo sustituciones exactas con NULs embebidos tanto en la cadena fuente como en el patrón buscado.
  - **`pengu_string_split` (B27)**: Reescritura del bucle de segmentación sobre `pengu__find_sub` y asignación byte-segura, respetando `delim.len` y bytes NUL embebidos en el delimitador sin truncamiento.
  - **`pengu_parse_int` y `pengu_parse_float` (B28)**: Validación estricta con límite superior `end_limit = s.data + s.len`. Cadenas con bytes residuales o NULs intermedios (como `{"42\0xyz", 7}`) son rechazadas correctamente retornando `none`.

- **Fase 4 — Fugas y Datos Perdidos**:
  - **`pengu_c_archivum_read_dir` (C13)**: Corrección de fuga de memoria en ramas de error (`FindFirstFileA`, `opendir`, o fallo de asignación de `cpath`). Se reemplaza el `free(list)` aislado por `pengu_banish_list(list); free(list);`, liberando el buffer `list->data` previamente inicializado por `pengu_list_new`.
  - **`pengu_c_get_env_keys` (Windows) (C14)**: Eliminación del límite estático de 255 caracteres (`char kbuf[256]`) en Windows; alineado simétricamente con POSIX usando `pengu_string_substring` para soportar claves de cualquier longitud sin descarte silencioso.
  - **`pengu_c_archivum_remove_dir` y `pengu_c_archivum_glob_rec` (C15)**: Prevención de truncación silenciosa en buffers fijos de 4096 bytes. Si `snprintf >= sizeof(buf)`, se asigna dinámicamente un buffer en heap o se descarta la entrada de manera segura, evitando operaciones destructivas sobre rutas truncadas.

- **Fase 5 — Documentación**:
  - **Límite INT_MAX en constructores (D8)**: Añadidas notas `@note` en `pengu_string_new`, `pengu_string_concat`, `pengu_string_repeat`, `pengu_string_replace` y `pengu_c_archivum_read_file` documentando el rechazo ante longitudes mayores a `INT_MAX`.
  - **Semántica NUL en replace / split (D9)**: Actualizadas docstrings de `pengu_string_replace` y `pengu_string_split` reflejando el soporte binario exacto sin truncar en NUL.
  - **`pengu_c_get_env_keys` (D10)**: Documentada la entrega completa de claves de entorno sin límites artificiales en Windows y POSIX.

- **Fase 6 — Verificaciones**:
  - **Compilación estricta C11 (V1)**: `gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only pengu_runtime.h` verificado con 0 advertencias y 0 errores.
  - **Tests de strings, colecciones y archivos (V2)**: Nuevas suites y aserciones en `tests/test_runtime_strings.py`, `tests/test_runtime_collections.py` y nuevo archivo `tests/test_runtime_files.py`.
  - **Suite completa (V3)**: Ejecución completa de pytest sin fallos.

### Runtime hardening (0.10.1) — tercera pasada

- **Fase 1 — Bug Sistemático (Root Cause)**:
  - **`pengu_string_new` (A13)**: Corrección de la causa raíz de fugas de 1 byte en el constructor central de cadenas. Cuando `len == 0` (cadena vacía `""`), ahora retorna inmediatamente una vista estática no-propietaria `{data="", len=0}` en lugar de asignar 1 byte en heap que `pengu_banish_string` no liberaba (al comprobar `len > 0`). Esto cierra de forma sistemática y transitiva las fugas potenciales en `pengu_string_char_at` con `\0` (B10) y `pengu_string_from_char('\0')` (B11).

- **Fase 2 — Correctitud**:
  - **`pengu_string_replace` (B21)**: Preservación de bytes NUL embebidos en rutas no-op (`from.len <= 0` o `count == 0`), utilizando `pengu_string_copy(s)` en lugar de `pengu_string_new(s.data)` para no truncar la cadena en NULs intermedios.
  - **`pengu_parse_float` (B22)**: Verificación de `errno == ERANGE` tras `strtod` para retornar `none` ante desbordamientos numéricos como `"1e999"`.
  - **`pengu_parse_int` y `pengu_parse_float` (B23)**: Rechazo explícito de cadenas compuestas únicamente por espacios en blanco (`"   "`, `"\t\n"`), mientras se preserva el soporte correcto para espacios en blanco circundantes válidos (`"  42  "` y `"  3.14  "`).
  - **`pengu_string_contains` (B24)**: Reemplazo de `strstr` por `pengu_string_index_of != -1`, asegurando búsqueda exacta de subcadenas binarias con bytes NUL embebidos.
  - **`pengu_string_starts_with` (B25)**: Reemplazo de `strncmp` por `memcmp`, permitiendo comparar prefijos binarios que contengan bytes NUL.

- **Fase 3 — NULL Deref / OOM Silencioso**:
  - **`pengu_c_strptime` (C11)**: Comprobación de retorno no nulo de `malloc` al asignar el contenedor del timestamp `double`, retornando `pengu_maybe_none()` de forma segura ante OOM.
  - **`pengu_c_archivum_metadata` (C12)**: Comprobación de `map->entries != NULL` tras `pengu_map_new`, retornando `none` y liberando el contenedor ante fallo de memoria en lugar de retornar un mapa incompleto o vacío.

- **Fase 4 — Consistencia y Documentación**:
  - **`pengu_banish_string` (D5)**: Añadido `@warning` explícito indicando que solo es seguro sobre cadenas propietarias heap y no debe invocarse sobre vistas de rodata (`pengu_string_from_cstr`) ni cadenas con `len == 0`.
  - **`pengu_string_copy` (D6)**: Documentación explícita de que la implementación no usa `strlen` y preserva bytes NUL embebidos mediante `memcpy` exacto sobre `s.len` bytes.
  - **`pengu_list_push` y `pengu_map_alloc_slot` (D7)**: Documentada la nota de que ante fallo de `realloc`/`malloc` retornan silenciosamente sin insertar.

- **Fase 5 — Verificaciones**:
  - **`pengu_string_copy` (V1)**: Confirmado que la implementación en `pengu_parser/pengu_runtime.c` utiliza `memcpy(buf, s.data, (size_t)s.len)` y no `strlen`/`pengu_string_new`, garantizando la integridad de datos binarios y claves de mapa con NULs.
  - **`pengu_string_as_slice` y `pengu_ffi_*` (V2)**: Confirmada su existencia y operatividad en `pengu_runtime.h` y `pengu_parser/pengu_runtime.c` cubiertas por la suite FFI.

### Runtime hardening (0.10.1) — segunda pasada

- **Fase 1 — Crashes por NULL Deref**:
  - **`pengu_map_new` (A10)**: Verificación de retorno de `calloc`. Si `calloc` falla al asignar el buffer de entradas, se establece `cap = 0` y `len = 0` para evitar desreferenciar `entries = NULL` en operaciones subsiguientes; el próximo `put` reintenta la asignación limpiamente.
  - **`pengu_map_put` y `pengu_map_put_string_int` (A11)**: Verificación de retorno de `calloc` durante el proceso de rehash/redimensionamiento. Ante fallo de memoria, se realiza rollback a la capacidad (`cap = old_cap`) y buffer de entradas previos (`entries = old_entries`), rechazando la inserción de manera segura sin dejar la estructura en un estado inconsistente.
  - **`pengu_map_alloc_slot` en `pengu_map_put` y `pengu_map_put_string_int` (A12)**: Introducción de helper privado `pengu_map_alloc_slot` para asignar memoria por slot (`key` y `val`) con comprobación atómica de `malloc` y rollback (`free` de punteros parciales) si falla la asignación de clave o valor. Reemplazados los sitios directos de asignación en `pengu_map_put` y `pengu_map_put_string_int`.

- **Fase 2 — Fugas de 1 Byte por String Vacío**:
  - Causa raíz: `pengu_banish_string` no libera cuando `len == 0`, pero varias funciones asignaban un buffer heap de 1 byte con `\0` para cadenas de longitud 0. Se unificó el retorno de vista no-propietaria `pengu_string_from_cstr("")` en todos los casos de longitud 0.
  - **`pengu_string_format` (B5)**: Retorna `pengu_string_from_cstr("")` cuando `size <= 0`.
  - **`pengu_string_concat` (B6)**: Retorna `pengu_string_from_cstr("")` cuando `total <= 0`.
  - **`pengu_string_replace` (B7)**: Retorna `pengu_string_from_cstr("")` cuando `new_len == 0`.
  - **`pengu_string_split` (B8)**: Retorna `pengu_string_from_cstr("")` en caso de cadena de entrada vacía y utiliza `pengu_string_from_cstr("")` para segmentos vacíos (`seg_len == 0` y `rem_len == 0`).
  - **`pengu_c_archivum_read_file` (B9)**: Cuando `read_bytes == 0` (archivo vacío), se libera el buffer asignado de 1 byte y se asigna `res->data = ""` con `res->len = 0`.

- **Fase 3 — Correctitud**:
  - **`pengu_map_put_string_int`, `pengu_map_get_string_int` y `pengu_map_remove_string_int` (C5)**: Soporte completo de `tombstones` en las funciones especializadas de mapas string-a-int. `put_string_int` rastrea `first_tombstone` y reutiliza ranuras con tombstone; `get_string_int` continúa el sondeo a través de tombstones; `remove_string_int` marca la ranura con `tombstone = true`.
  - **`pengu_map_clear` (C6)**: Reseteo explícito de `map->entries[i].tombstone = false` en todas las ranuras al limpiar el mapa para evitar acumulación y degradación del rendimiento de sondeo tras `clear`.
  - **`pengu_string_index_of` (C7)**: Búsqueda manual byte a byte mediante `memcmp` en lugar de `strstr`, garantizando búsqueda exacta en presencia de bytes NUL embebidos.
  - **`pengu_c_get_env_keys` (C8)**: Implementación para sistemas POSIX (Linux/macOS) utilizando `extern char **environ`, segmentación con `strchr` y extracción de claves de entorno.
  - **`pengu_c_rand_range` (C9)**: Cálculo de rango en precisión `double` (`(double)max - (double)min + 1.0`) para prevenir desbordamiento de enteros con rangos amplios como `[INT_MIN, INT_MAX]`.
  - **`pengu_list_push` (C10)**: Verificación de límite de crecimiento `list->cap > INT_MAX / 2` antes de duplicar la capacidad, evitando desbordamiento a valores negativos.

- **Fase 4 — Consistencia y Documentación**:
  - **`pengu_string_from_bool` (D1)**: Documentado que retorna un view no-owning sobre el cual `pengu_banish_string` es un no-op, recomendando `pengu_string_copy` si se requiere copia propia.
  - **`pengu_bounds_panic` (D2)**: Documentado el uso de `_exit(134)` para evitar doble volcado de signal handlers y la ausencia de flush en buffers stdio.
  - **`pengu_string_new` (D3)**: Verificación de seguridad `len > INT_MAX` retornando cadena vacía si la longitud excede `INT_MAX`.
  - **`pengu_string_format` (D4)**: Documentada la validez y propósito en C11 del doble `va_start` / `va_end` (para cálculo de tamaño y posterior formateo).

## [0.10.0] - Released

### Runtime hardening (0.10.0)

- **Fase 1 — Corrección de Bugs Críticos**:
  - **`pengu_string_replace` (A1)**: Corregido subdesbordamiento aritmético de `size_t` cuando `to.len < from.len`, el cual producía un entero gigante y causaba fallo silencioso en `malloc`. Ahora calcula deltas con signo mediante `ptrdiff_t`.
  - **`pengu_list_push` (A2)**: Se eliminó la modificación prematura de `cap` previa a `realloc`. En caso de fallo de asignación, el estado de `cap` y `data` se mantiene intacto sin corrupción ni fuga de datos.
  - **`pengu_list_new` (A3)**: Comprobación de asignación en `malloc`; ante fallos, inicializa de forma consistente `{data=NULL, cap=0, len=0}`.
  - **`pengu_string_repeat` (A4)**: Verificación contra desbordamiento de enteros en la multiplicación `len * times` y comprobación de sanidad de memoria contra `SIZE_MAX / 2`.
  - **`pengu_parse_int` y `pengu_parse_float` (A5)**: Comprobación de asignación de `malloc` (retornando `none` ante fallo), verificación de límites de 32 bits (`INT32_MIN` .. `INT32_MAX`) y detección de `ERANGE` multiplataforma (Windows LLP64 y POSIX LP64 con `strtoll`).
  - **`pengu_c_getenv` y `pengu_c_getcwd` (A6)**: Validación de puntero `NULL` en el contenedor `PenguString` asignado para `pengu_maybe_some`.
  - **`pengu_string_concat` (A7)**: Corrección de desbordamiento de enteros en la longitud combinada y retorno de cadena vacía válida `{data="", len=0}` ante fallo de asignación en lugar de estructuras inconsistentes `{data=NULL, len=N}`.
  - **`PenguMapEntry` y cadena de colisiones (`tombstones`) (A8)**: **Cambio de comportamiento observable**. Previamente, eliminar una entrada en un mapa (`pengu_map_remove`) reseteaba la ranura a `occupied = false`, truncando la cadena de sondeo lineal y haciendo inaccesibles todas las claves colisionantes subsiguientes. Se introdujo el campo `bool tombstone` en `PenguMapEntry`; las eliminaciones marcan `occupied = false; tombstone = true;`. Las operaciones `get`, `contains`, `put` y `remove` ahora continúan el sondeo a través de los tombstones sin romper la cadena. Las inserciones (`put`) reutilizan ranuras con tombstone y el rehash las descarta.
  - **Preservación de NULs embebidos en claves de mapas (A9)**: `pengu_map_put` utiliza ahora `pengu_string_copy` en lugar de `pengu_string_new`, garantizando la copia exacta de los `len` bytes de la clave y del valor sin truncar en bytes NUL intermedios.

- **Fase 2 — Eliminación de Fugas de Memoria**:
  - **`pengu_map_put` rehash (B1)**: En el redimensionamiento del mapa, las entradas migradas liberan explícitamente el buffer `.data` de claves y valores de tipo `PenguString` mediante `pengu_banish_string` antes de liberar las estructuras envolventes.
  - **Limpieza en consumidores de `read_dir` (B2, B3, B4)**: Se incorporó la función auxiliar `pengu_banish_string_list` para liberar cada `PenguString` dentro de una lista antes de liberar la lista. Se refactorizaron `pengu_c_archivum_remove_dir`, `pengu_c_archivum_glob_rec` y `pengu_c_archivum_walk_rec` para liberar completamente las entradas leídas de directorios.

- **Fase 3 — Mejoras de UX y Robustez**:
  - **`pengu_bounds_panic` (C1)**: Sustitución de `abort()` por `_exit(134)` tras volcar el volcado de pila para evitar la doble traza duplicada generada por el manejador de señal `SIGABRT`.
  - **`pengu_c_exec` (C2)**: Gestión dinámica de buffers de comando para prevenir desbordamientos de buffer fijo de 4KB en comandos largos, y documentación de advertencia de seguridad para uso de `system()`.
  - **`pengu_map_keys_string` (C3)**: Validación estricta de `m->key_size == sizeof(PenguString)` y punteros no nulos, devolviendo una lista vacía en lugar de interpretar mapas de enteros u otros tipos como cadenas.
  - **`pengu_string_format` (C4)**: Documentación aclaratoria en docstring de que los fallos de formateo o asignación retornan `""`.

- **Fase 4 — Documentación de Limitaciones de Header**:
  - Documentación de señal-seguridad en `pengu_dump_frame_stack`: clarificación del uso de `_write`/`write` con `snprintf`.
  - Nota en `pengu_string_new` y `pengu_string_from_cstr` sobre truncamiento de NULs vía `strlen` y recomendación de `pengu_string_copy` para cadenas binarias.
  - Nota de propiedad en `pengu_string_split`: clarificación de que el llamador posee cada elemento `PenguString` y debe liberarlo antes de `pengu_banish_list`.
  - Nota en `pengu_list_pop_val`: clarificación de que el puntero devuelto apunta al buffer interno y se invalida tras un push que redimensione.

### P2 — Scope-owned locals (auto-banish)

- **Ownership auto-gestionado (_scope-owned locals_)**: variables locales de tipo contenedor heap (`string`, `list`, `map`) con inicializadores fresh no-aliasing son gestionadas automáticamente por su ámbito léxico (`is_auto_banished`). Al salir del bloque que las declaró (`weave`, `if`, `while`, `for`, `with`, `or:`, `test`), el compilador emite llamadas deterministas en orden inverso (LIFO) a `pengu_banish_string`, `pengu_banish_list` o `pengu_banish_map`.
- **Modificador `borrowed`**: palabra clave suave (`var borrowed x is ...`, `let borrowed x is ...`) para declarar referencias prestadas o no propietarias, desactivando el auto-banish y prohibiendo la liberación explícita.
- **Análisis de escape estático y compatibilidad**: el compilador detecta fugas de propiedad (`return`, `push`, `put`, `set field`, `sigil of`, o pasajes a funciones) y desactiva el auto-banish de la variable origen.
- **Nuevos diagnósticos de ownership**:
  - `AutoOwnedBanishError` (`E0047`): prohíbe `banish` manual sobre una variable ya auto-gestionada para prevenir double-free.
  - `BorrowedBanishError` (`E0048`): prohíbe `banish` sobre variables marcadas con `borrowed`.
- **Notas de implementación**:
  - `pengu_codegen` preserva expresiones dinámicas de concatenación de strings (`+`) evitando constant-folding a `.rodata` cuando se requiere liberación segura en heap.
  - El desenrollado de auto-banish en sentencias de salto (`return`, `break`, `continue`) limpia únicamente los ámbitos activos correspondientes sin mutar prematuramente los marcos de ámbito léxico.
  - Los bloques `or:` inicializadores de `var` y `let` gestionan su propio ámbito léxico de auto-banish dentro de la rama de error C.
  - El análisis de escape (`_check_symbol_escape`) reconoce ahora variables incluidas en estructuras compuestas y literales contenedores (`struct_init`, `list_lit`, `map_lit`, `tuple_lit`, `some_expr`, `ok_expr`, `err_expr`) o asignaciones de aliasing (`var b is a`), desactivando el auto-banish para evitar liberaciones prematuras (use-after-free) de datos que escapan hacia estructuras o colecciones persistentes.
  - El análisis de escape (`_check_symbol_escape`) reconoce ahora literales indentados (`indent_literal` / `indent_entries` / `indent_array` / `field_entry` / `map_entry`) y bloques usados como valor de `return` (`if_stmt`, `unless_stmt`, `do_expr`, loops), desactivando el auto-banish para evitar liberaciones prematuras (use-after-free) de datos que se copian por valor en estructuras anidadas o se devuelven desde una rama.
- **Known issue (no bloqueante):** `or:` blocks en posición de expresión distinta al initializer directo de `var` / `let` (p. ej. `return f() or: ...` o `calling g with (x or: ...)`) caen en el fallback genérico de codegen y emiten C silenciosamente incorrecto. Workaround: extraer a una variable intermedia o usar `or else` / `or return`. Planificado para Phase 3.

### P1 — Confianza operativa (Fase 1)

- **Backtrace mínimo**: frame stack circular thread-local (`pengu_frame_push`, `pengu_frame_pop`) configurable mediante `PENGU_FRAME_TRACE` y `PENGU_MAX_FRAMES` (64 por defecto). Crash handler para `SIGSEGV` y `SIGABRT` (y `SetUnhandledExceptionFilter` en Windows) que vuelca la cadena de llamadas `.pengu` directamente a stderr de forma async-signal-safe (utilizando exclusivamente llamadas directas a `write(2)` / `_write`). *(Corrección — Fase 3, item 3.7: en 0.10.0 esta afirmación era **falsa**. El volcado se construía con `snprintf`, que no es async-signal-safe, y el propio header lo admitía en un comentario. El handler solo pasó a usar exclusivamente `write(2)`/`_exit()` con formateo manual en 0.16.0; ver `AUDIT_1.0.md` §5.2 y `AUDIT_1.0_FASE3.md` §14.)*
- **Bounds checking opt-in**: bajo el perfil `debug`, operaciones de indexación (`xs at i` y `set xs at i`) emiten verificaciones seguras con statement-expressions de GCC (`pengu_assert_bounds`), arrojando un panic descriptivo ante desbordamientos y volcando la traza de frames. En perfil `release`, tiene cero coste de runtime (no se emite la aserción).
- **Variable de compilación `debug`**: expuesta para directivas condicionales `when debug:`, evaluándose como verdadera únicamente cuando el perfil activo de compilación es `debug` (o vía `-D debug` / `-D debug=1`).
- **Salida estructurada `pengu test --json`**: emite eventos máquina JSON Lines (JSONL: `start`, `test_start`, `test_pass`, `end`) a stdout filtrando diagnósticos del compilador a stderr, idóneo para integración continua (CI).
- **Modo vigilancia `pengu test --watch`**: observa en tiempo real los archivos fuente `.pengu` y de configuración del proyecto mediante polling de `mtime` (500 ms), limpiando la pantalla y re-ejecutando la suite ante cualquier cambio detectado.
- **Correcciones en backtrace (fix-up)**: Se añadió la emisión de `pengu_frame_pop()` en las rutas de retorno anticipado de `or return` y `try` (evitando frames huérfanos en `g_pengu_frames`) y se corrigió el registro de lambdas para propagar la ruta del archivo fuente (`src_file`), asegurando que `pengu_frame_push` registre la ruta `.pengu` y el número de línea correspondientes en lugar de una cadena vacía.

### Added

- `pengu bind`: now emits `alias` declarations for type names referenced by
  the target header but defined in a companion header (e.g. `uLong`, `uInt`
  from `zconf.h` when binding `zlib.h`). Without this, bindings that
  reference such types failed the semantic check with E0005.
- `LANGUAGE.md` §13.3 documents C-buffer ownership: use
  `defer calling lib_free with p` for library-allocated memory, `banish` for
  PenguScript runtime containers.
- `std/ffi.pengu` header now carries a usage guide for the ownership model.

### Changed

- **Breaking:** A bare C function reachable only through `include` is no
  longer callable implicitly. Add an explicit `declare` signature to your
  module, or `import` a binding that declares it. This closes the
  "checker accepts, codegen emits invalid C" trap reported in H2 of
  PRODUCTION_READINESS.md.
- `calling f with [1, 2, 3]` (array literal as direct argument) is now a
  semantic error (E0005). Assign the literal to a typed variable first.
- `declare` now rejects `many T` parameters (E0005). Use `...` for C
  variadics; `many T` remains valid only in `weave` signatures.

### Fixed

- `pengu bind` no longer silently drops typedefs from companion headers
  when the target header references them.

### Fixed (production criticals)

The three production-critical defects identified in `PRODUCTION_READINESS.md` §9.3 (C1, C2, C3) are resolved, with comprehensive test coverage in `tests/test_p3_criticals.py`:

- **C1: Bare module-qualified binding variants (`module.VARIANT`).** Referencing constants and omen variants from C bindings using the bare module-qualified spelling (e.g. `raylib.FLAG_MSAA_4X_HINT`, `raylib.KEY_RIGHT`, `raylib.SHADER_UNIFORM_FLOAT`) previously emitted an invalid prefixed C identifier (`raylib_FLAG_MSAA_4X_HINT`), failing at C compilation time. The code generator now resolves these to the clean, unprefixed C identifiers defined by the native header, while keeping user-defined PenguScript omen variants properly prefixed (`Color_Rojo`).
- **C2: String interpolation diagnostics for non-PenguScript text (`{...}`).** Embedding text containing curly braces (such as GLSL/HLSL shader source or regexes) in normal strings previously failed with a generic `E0000` syntax error pointing at line 1 column 3 of the interpolated snippet. The type inferrer now reports `E0019` against the actual string literal location with clear context and explicit `help:` pointing to raw strings (`r"..."` or `r"""..."""`), where curly braces and escape characters are preserved verbatim.
- **C3: Dropped unconditional `restrict` from generated parameters and `self`.** Function parameter prototypes and definitions generated for `ref to T` and `self` previously emitted `T* restrict`, introducing undefined behavior under optimization (`-O2`) for APIs that alias or overlap buffers in-place. Generated C now emits standard pointers (`T* self`, `T* p`), guaranteeing aliasing safety. The mapper retains `restrict=True` as an explicit opt-in mechanism (`CTypeMapper.to_c_decl`).

### CI/CD and Cross-Platform Test Hardening

- **Automated Tagging and GitHub Release**: Enhanced GitHub Actions CI workflow (`.github/workflows/ci.yml`) to automatically parse release notes, title, and version from `CHANGELOG.md` upon successful test completion across all platforms (Windows, Linux, macOS), creating the Git tag and publishing a GitHub Release with platform binaries (`.zip`, `.tar.gz`) and the VS Code extension (`.vsix`).
- **Cross-Platform Raylib Test Guards**: Added `@requires_lib("raylib")` annotations to compile-and-run tests in `tests/test_p3_criticals.py` while keeping pure codegen verification enabled unconditionally across all platforms, resolving linker failures on POSIX CI runners where Raylib compilation is optional/best-effort.
- **Headless OpenGL Environment Tolerance**: Added `rl.IsWindowReady()` check to `test_rlgl_coexistence_with_raylib` in `tests/test_p2_features.py`, preventing GLFW initialization crashes on headless CI runners lacking hardware OpenGL contexts.
- **Release Smoke Test Argument Separator**: Fixed outdated pre-0.10.0 syntax in `make_release.py` where the smoke test used `and` instead of `,` as an argument separator in `calling ward.assert_eq_int with 40 + 2, 42`, which triggered `E0005: Ambiguous 'and' after a call with arguments` during the post-packaging verification step on all platforms.

### P0 toolchain hardening (production hygiene)

The five items the readiness assessment (`PRODUCTION_READINESS.md` §7, P0) called
out as "what makes everything else debuggable" are done, with regression tests in
`tests/test_p0_toolchain.py` (23 tests):

- **`weave main`'s value is the process exit status.** The generated wrapper used
  to call `pengu_main();` and `return 0`, so every program exited 0 and CI could
  not detect a failure. It now emits
  `int pengu_status = (int)pengu_main(); … return pengu_status;`, widening any
  integer return type (`u8`, `bool`, `i64`, …) and using `0` for `weave main into
void`. `pengu run` already forwarded the child's status, so the chain is now
  end to end.
- **Generated C carries `#line` directives.** Every statement in a function body
  and every function definition is preceded by
  `#line <n> "<relative .pengu path>"`, so a gcc/clang diagnostic names the file
  and line the user wrote instead of `build/bundle.c`. Compiler-generated
  sections (lambda trampolines, entry wrapper, test runner) are reset with
  `#line 1 "bundle.c"`. Markers are deliberately **not** emitted inside
  expression contexts, where the C is a GCC statement expression that may become
  the argument of the function-like macro `pengu_to_string(x)` (a directive there
  would break the macro invocation).
- **The build cache keys on content, not mtimes.** `build/` is shared by every
  program built in a directory, and the cache compared mtimes against
  `build/bundle.c`, so a _different_ program's older bundle could look "up to
  date" and its binary was shipped. The cache key is now
  `<config hash> <sources fingerprint>` in `build/.bundle_hash`, where the
  fingerprint covers the resolved entry path, every module's relative path and
  content and the project C sources; single-token (legacy) hash files are treated
  as stale. `compile()` additionally requires the artifact to be newer than the
  bundle, and identical content with a bumped mtime still counts as cached (so
  `touch` no longer forces a rebuild).
- **Program arguments reach the runtime.** The entry wrapper calls
  `pengu_init(argc, argv)` (and so does the test runner), so
  `rites.get_argc()` / `get_argv()` / `get_args()` return the real arguments
  instead of 0/empty.
- **One version, everywhere.** `VERSION` is the single source of truth, read by
  the new `pengu_version.py` (`__version__`, `__version_tag__`, fallback constant
  and `read_version_file()`). The CLI banner and the generated-C banner take the
  value from there, a new `pengu --version` / `-V` flag reports it,
  `make_release.py` now syncs the VS Code extension manifest from `VERSION`
  before packaging, and the places that used to spell a stale number (grammar
  docstring, runtime header, README badge, extension `package.json`) no longer
  claim one. `tests/test_p0_toolchain.py::TestVersion` fails if any of them drift.

### P1 — Unblock the raylib corpus

The five items identified in `PRODUCTION_READINESS.md` §7 (P1) to unlock ≈92% of the
raylib corpus:

- **P1.3 Fixed array length (`(xs length)`).** Codegen now checks the semantic
  type of array expressions and emits their declared compile-time size as an
  integer literal instead of invalid `.len` member accesses.
- **P1.2 Struct arrays and index assignment without spurious `E0011`.** Struct
  signatures in struct-initialization expressions are deduplicated by member
  fingerprint, element types propagate through array literals and assignment
  targets, and indexed field paths (`cs at 1 . x`) infer accurately.
- **P1.1 C varargs support (`...` in `declare`).** Added terminal `VARARGS` and
  `CVarArgsType` to grammar, checker, and inferrer. In C function calls, arguments
  matching the C varargs ellipsis are emitted directly without `PenguSlice` wrappers
  or argument type checks. `pengu_bind` automatically emits `...` for C ellipsis
  parameters, unblocking `raylib.TextFormat`, `raylib.TraceLog`, `sqlite3.mprintf`, etc.
- **P1.5 Pointer indexing (`p at i`) & generic slice bridge.** Inferrer and
  checker now permit indexing typed pointers (`RefType`), preserving `frozen`
  read-only qualifications and rejecting void/opaque pointers with actionable guidance.
  Array arguments decay to pointers for `RefType` parameters. Added generic
  `ffi.slice_from_ptr shard T with data as ref to void, count as int into slice of T`
  backed by `pengu_ffi_slice_raw` in the runtime.
- **P1.4 `raymath` C shim and std binding.** Added non-inline C wrapper library
  `libpengu_raymath.a` and header `pengu_raymath.h` wrapping all 146 inline functions
  from `raymath.h` with `pengu_rm_` symbols, integrated into `build_runtime.py`,
  and generated the full declaration binding `std/raymath.d.pengu`.

#### `at` index expressions: assignment targets now agree with reads (audit follow-up)

`at` is a **postfix** operator (CHEATSHEET §6.1), so `xs at i + 1` is
`(xs at i) + 1` and a computed index is written `xs at (i + 1)`. Reads already
behaved that way, but the _target_ grammar accepted an additive expression, so
`set xs at n - 1 is v` wrote to index `n-1` while the equivalent read computed
`(xs at n) - 1` — one spelling, two meanings, and the reading one can index out of
bounds. Both positions are now postfix, which means:

- `set xs at (n - 1) is v` is the (always correct) spelling for a computed index;
- `set xs at n - 1 is v` is a syntax error with a dedicated `E0000` hint
  ("The index after 'at' binds tighter than '-': parenthesise the index
  expression") instead of a bare parse failure;
- pinned by `tests/test_p1_features.py::TestAtIndexSemantics` (5 tests), and
  documented in `CHEATSHEET.md` §6.1.

### P2 — Breadth and safety (`PRODUCTION_READINESS.md` §7, P2)

The six "breadth" items, with regression tests in `tests/test_p2_features.py` (34 tests):

- **P2.2 — Multidimensional arrays.** `array of array of T with size M with size N`
  now maps to C `T[M][N]` (outer dimension first) instead of the invalid
  `T[M][None]` the previous codegen produced; the inner dimension is inferred from
  the initializer rows when omitted, and a missing/unknowable dimension is a
  semantic error (`E0015`, `UnknownArrayDimensionError`) rather than a leaked
  `None` in the generated C. Ragged literals are rejected (`E0041`), row length
  (`((m at 0) length)`) emits the inner size, 2-D values decay correctly when
  passed to a C parameter (`T (*)[N]`), and the syntax is documented in
  `CHEATSHEET.md`.
- **P2.4 — Explicit release for `string` / `list` / `map`.** `banish` now accepts
  `string`, `list of T` and `map of K to V` lvalues in addition to `ref to T`,
  emitting `pengu_banish_string` / `pengu_banish_list` / `pengu_banish_map`
  (the runtime already had them; nothing could call them from PenguScript
  before). Literals, temporaries, `const` and `frozen` targets stay `E0008`, and
  `defer banish x` works. Ownership semantics documented in `LANGUAGE.md` and
  `CHEATSHEET.md` (including that `pengu_banish_map` releases string keys/values).
- **P2.3 — Module state idiom.** Top-level `var` remains `E0002` **by design**;
  the two supported patterns are now documented (private `static var` behind
  accessor weaves, and an explicit context struct passed by `ref`), the `E0002`
  message suggests them, and a two-module executable test proves the state is
  per-module and persists across calls.
- **P2.1 — `rlgl` binding.** `std/rlgl.d.pengu` is generated (163 `declare`s,
  122 `const`s, 11 `omen`s, rlgl's own `rlDrawCall`/`rlVertexBuffer`/`rlRenderBatch`
  runes), imports `std.raylib` instead of redeclaring raylib's types, links
  `raylib`, and coexists with `std.raylib` in one program. A sixth ported example
  (`scratch/port/06_rlgl_solar_system.pengu`) builds and runs.
- **P2.5 — Strict pointer typing.** A pointer is only compatible with another
  pointer when its **pointee** matches: `_same_pointee` unwraps aliases/`frozen`
  and compares exactly (with `char` ↔ `byte` as the documented C
  `char*`/`uint8_t*` equivalence, so `bytes of s` keeps working, and
  `void`/`opaque` as the wildcard). This closes the hole where
  `ref to i32` was accepted for a `ref to char` parameter — and where an
  `array of i32` decayed to `ref to char` — with no diagnostic. Numeric widening
  of _values_ (`int` → `i64`) is unchanged; `frozen` stays one-directional.
- **P2.6 — `pengu bind` on real headers.** New flags (`--define/-D`,
  `--cpp-flags`, `--system-includes`, `--preprocessed FILE.i`,
  `--no-blank-extensions`), GNU-extension blanking enabled by default, new stubs
  (`pthread.h`, `unistd.h`, `limits.h`, `fcntl.h`, `sys/types.h`, documented in
  `c_bind_stubs/README.md`) and actionable failure diagnostics that name the
  offending construct and the flag to try. `zlib.h` (with `--define Z_SOLO`) is the
  first third-party header that used to fail and now binds end to end, and
  `sqlite3.h` / `rlgl.h` are covered as regressions.

#### Audit follow-ups (P2 review)

- **Generated names are kept verbatim.** The generator was sanitizing every
  struct member and parameter whose name is a language keyword or type name
  (`type` → `_type`, `size` → `_size`, `opaque` → `_opaque`). That silently
  blocked regeneration of `std/nanosvg.d.pengu` and `std/typis.d.pengu` (both use
  such member names) and changed the generated API for no compile-time gain: no
  parameter name breaks a `declare` signature, and no member name breaks a
  `rune`. The policy is now evidence-based — members are never renamed, `declare`
  parameters keep their C name (only `self`/`type` are quoted), and **callback
  aliases** (whose grammar _does_ reject type-like parameter names, e.g.
  `with opaque as voidpf`) sanitize exactly that class (`opaque`, `void`, `int`,
  the fixed-width type names, `null`). Covered by
  `tests/test_p2_features.py::TestPenguBind` (`…names_are_kept_verbatim`,
  `…callback_alias_sanitizes_type_like_parameter_names`) and verified by
  `regen_std_bindings.py --check` (13 tool-produced bindings identical, incl.
  nanosvg and typis).
- **`std/rlgl.d.pengu` explains its hand edit.** `rlgl.h` does not
  `#include "raylib.h"` (it expects the includer to have done so), so the
  generator cannot see the dependency and would emit a duplicate `Matrix` rune;
  the binding's `import std.raylib` is therefore added by hand and the file now
  documents that, why `regen_std_bindings.py` skips it, and how to regenerate it.
- **`bind` CLI-flag test fixed**: it asserted a `no_blank_extensions` namespace
  attribute while the flag is (correctly) `--no-blank-extensions` with
  `dest="blank_extensions"` and `store_false`; a default-value test was added too.

### Added

- **`frozen` type qualifier (C's `const`).** `frozen T` emits `const T`,
  `ref to frozen T` emits `const T*`, and `frozen ref to T` is sugar that
  normalises to `ref to frozen T` (the qualification always lands on the
  pointee; `T* const` is what `let` already expresses). It is orthogonal to
  `let`/`var`, has the same size and layout as its target and is usable as the
  target inside expressions — only writing is restricted, in the C direction:
  a mutable value flows into `frozen` (`int` → `frozen int`), the reverse is
  `E0005`, and `set` through a frozen value or frozen pointee is `E0006`.
  This is what makes C signatures carrying `const` expressible, e.g. `qsort`:

  ```pengu
  declare qsort with base as ref to void, nmemb as usize, size as usize, compar as ref to weave with a as ref to frozen void, b as ref to frozen void into int into void

  weave compare_ints with a as ref to frozen void, b as ref to frozen void into int:
      let xa is essence of (transmute a to ref to frozen int)
      ...
  ```

  emits `int32_t compare_ints(const void* restrict a, const void* restrict b)`
  and `qsort(xs, 3, sizeof(int32_t), ((int32_t (*)(const void*, const void*))compare_ints))`,
  which GCC 14+ accepts (before, the callback was spelled `void*` and rejected
  for differing qualifiers). See LANGUAGE §9.5.

- **`frozen` is a soft keyword.** It is a plain string literal in the grammar,
  so Lark's contextual lexer only prefers it where a type may start; identifiers
  named `frozen` (variables, fields, weaves, modules) keep working — verified by
  tests, and there were no such identifiers in `std/` or `tests/`.
- **Arrays decay to pointers where a reference is expected.**
  `calling qsort with xs, 3, …` now type-checks (`array of T` → `ref to T`,
  `ref to void`, `ref to frozen void`), matching C's array-to-pointer decay;
  the element type must still be compatible.

### Fixed

- **C callbacks with `const`-qualified parameters now compile under GCC 14+**
  when the binding is written with `ref to frozen void` (`qsort` and friends).
  The argument check also no longer accepts the reverse compatibility direction
  when it would silently discard a `frozen` qualification, so
  `ref to frozen int` → `ref to int` is `E0005` as in C.
- **`frozen` writes are rejected** (`E0006`): `set` on a `frozen`-typed binding,
  and any `set` that writes _through_ a frozen pointee (`set p->field is …`
  where `p as ref to frozen T`). Rebinding a `ref to frozen T` pointer itself
  stays allowed, because the qualification is on the pointee.
- **`ref to frozen void` (C's `const void*`) keeps C's wildcard behaviour.**
  The bindings spell `const void*` as `ref to frozen void`, but only a literal
  `ref to (frozen) void` argument was accepted, so
  `calling UpdateTexture with …, sigil of pixels` and
  `calling xxhash.XXH64 with "PenguScript", 11, 0` failed with `E0005`. As in C,
  a pointer target is now the same catch-all for both spellings: any `T*`
  (mutable or frozen) converts to `void*` and `const void*` in one direction
  (`frozen T*` → `T*` stays `E0005`), arrays still decay, and a string _literal_
  converts too — `char*` → `const void*` — emitting a C literal rather than a
  Pengu string object (`string_lit` and `_is_ref_char_type` look through
  `frozen`/aliases and list `void` next to `char`).
- **`std_c/rlights.h` restored.** The tracked header was missing from the
  working tree (reported by `git status` as deleted), which breaks
  `build_runtime.py`'s `SINGLE_HEADER_NAMES` staging step; it was restored from
  `HEAD`, so `std/rlights.d.pengu`'s `std_c/rlights.h` reference is accurate
  again.

- **Logical operators `and` / `or` (boolean, short-circuit).** New
  `bool_or_expr` / `bool_and_expr` levels sit between `try` and `comparison`
  (`or` looser than `and`), so `if a > 0 and b > 0:` and
  `let ok is (p and q) or not r` work. Operands must be `bool` (`E0005`
  otherwise, with a hint to use `&`/`|` for bitwise); codegen emits `&&`/`||`,
  `ConstFolder` folds constant operands and `eval_comptime` evaluates them with
  short-circuit (the right operand is only evaluated when needed).

  > **Implementation note (maintainers).** A plain `"or"`/`"and"` literal would
  > have created a shift/reduce conflict at the `or` token against the existing
  > `or else` / `or return` / `or:` chain, which LALR(1) cannot resolve (it would
  > need two tokens of lookahead) — resolving it as shift silently broke
  > `a or else b` / `a or:`. The operators are therefore **separate terminals**:
  > `_BOOL_OR.3: /or\b(?!\s*(else|return|:))/`, `_BOOL_AND.2: /and\b/`, plus
  > `_AND_SEP.5: "and"` for the separator sites that survive (type/name lists).
  > The negative lookahead keeps the unwrap forms on the plain `OR` token, the
  > priority keeps the boolean operators from being shadowed where both are
  > expected, and the leading underscore keeps all three out of the AST (so
  > `bool_and`/`bool_or` nodes have exactly two children).

- **Compound assignment: `set x += 1`** and the other nine operators
  (`-= *= /= %= &= |= ^= <<= >>=`), as a new `compound_set_stmt` alternative of
  `set_stmt` (plus the one-line `compound_set_simple`, wired through
  `SIMPLE_STMT_ALIASES`). The checker reuses the whole `set` target validation
  (mutability, `with_target`, `essence_target`, private fields, `self->`) and
  adds per-operator type rules: `+=` on a string requires a string (and lowers to
  `pengu_string_concat`), the arithmetic operators require numerics, the
  bitwise/shift operators require integers.
- **Lambda expressions with explicit parameter types:**
  `lambda into 42`, `lambda x as int into x * 2`,
  `lambda a as int, b as int into x + y`. Parameters are typed (the language is
  static), the return type is inferred from the body, and there is **no
  capture** — a body only sees its parameters and module-level symbols. That
  lets codegen emit **one top-level `static` C function per lambda**
  (`_pengu_lambda_N`, between the prototypes and the definitions), so the result
  is portable C99 with no GCC nested functions. A lambda value has a
  `weave … into …` (`FnType`) type: it can be bound with or without that
  annotation, passed as a callback argument and called through
  (`calling f with v`). Lambdas are runtime-only (not usable in
  `when`/`defined`).
- **Variable declarations of function-pointer type now emit a valid
  declarator.** `var f is lambda …` (or any `FnType`-valued `var`/`let`/
  `static var`) used to emit `int32_t (*)(int32_t) f = …;` — invalid C. They now
  emit `int32_t (*f)(int32_t) = …;` via `CTypeMapper.to_c_decl`.
- **Block-shaped values are no longer constant-folded.** `ConstFolder.fold` used
  to recurse into a single-child node and replace it with a constant, so
  `lambda into 42` compiled to the literal `42` (invalid initializer) and a
  one-statement `do:`/value-position `if`/loop could be reduced away, dropping
  behaviour. Those rules now return "not constant".
- **Friendly `E0000` syntax errors (no more raw Lark traceback).** Every Lark
  syntax exception raised while parsing a module is now converted to
  `ParseError` (a `SemanticError` subclass, code `E0000`), carrying the line, the
  column, the offending snippet and the usual `help`/`note`. When the parser
  actually fails _on_ an `and` that used to be a separator, the message explains
  the 0.10.0 change, points at that token and suggests `,` — e.g.
  `[E0000] 'and' is no longer a separator: use ',' (offending 'and' at line 2,
column 33)`. The hint is only used when the error lands on the `and` itself, so
  an unrelated error on the same line is reported as a plain syntax error.
  `pengu check` also wraps import resolution, so a syntax error inside an
  imported module is reported the same way instead of escaping as a traceback.
- **`is present` / `is not present` validate their operand.** The checker used to
  accept any operand and emit `pengu_maybe_is_present(&(expr))` regardless, which
  read a presence flag out of whatever type was there and failed in C. The
  operand must now be `maybe T` (unresolved generics and `any` are allowed);
  anything else is `E0005` — `'is present' requires a maybe type, got 'int'` —
  with a hint. The check binds to the expression on its left, so the result of a
  call must be parenthesised: `if (calling find_user with 1) is present:`.
- **`if NAME as T is <maybe>:` bindings compile (and actually run).** The
  pattern used to emit
  `if ((int32_t v = opt, pengu_maybe_is_present(&v)))` — the `PenguMaybe` (or the
  presence `bool`) assigned to the unwrapped type inside a comma expression,
  which is not even valid C (a declaration cannot appear there). It now lowers to
  a scoped block that evaluates the maybe **once**, tests presence and declares
  the bound name from the heap copy:

  ```c
  {
      PenguMaybe _maybe_1 = (opt);
      if (pengu_maybe_is_present(&_maybe_1)) {
          int32_t v = (*(int32_t*)_maybe_1.value);
          /* body */
      }
  }
  ```

  Bindings also work in value position (`let r is if v as int is opt: … else: …`)
  and are never constant-folded. A redundant trailing `is present` is accepted
  (`if v as int is opt is present:` — the presence test is inherent, and the
  grammar's `if_cond_binding_present` alternative is in fact unreachable because
  the operand would swallow the test), while `is not present` combined with a
  binding is `E0005`. The checker now requires the operand to be `maybe T`
  (`Binding 'v' requires a maybe value, got 'int'`) and the declared type to
  match the element type.

- **Parentheses now survive into the AST.** `"(" expr ")"` is aliased to
  `paren_expr` instead of being inlined. The node is semantically transparent
  (`infer`/`fold`/codegen unwrap it) but it is what lets the checker tell
  `calling f with a, b` from `(calling f with a) and b` — see the list rule
  below.
- **Single-element array literals are no longer folded to their element.**
  `ConstFolder.fold` collapsed any single-child node to its child, so
  `var p as array of byte with size 4 is [0]` emitted
  `uint8_t p[4] = 0;` — invalid C (`invalid initializer`). Array and map
  literals are now never folded, so the initializer is `{ 0 }`. Multi-element
  literals were unaffected.
- **A leading UTF-8 BOM no longer breaks the parser.** Editors on Windows
  (Notepad, Visual Studio, PowerShell's `Set-Content`) write one; it used to
  produce `Syntax error: unexpected '\ufeff' at line 1, column 1`. The parser
  strips a leading BOM from the entry file and from every imported module.
- **Cross-module bindings can be imported together (`E0046`).** Generated
  bindings are self-contained per header, so `raygui.h` (which includes
  `raylib.h`) re-declares raylib's `KEY_*` defines as `const … as i64` while
  `std/raylib.d.pengu` declares them as `KeyboardKey` omen variants. Importing
  both used to fail with `E0046 … collides with the built-in type 'KEY_RIGHT'`.
  A `const` whose value equals the variant's value now denotes the same number
  and is accepted; a genuine mismatch (say `std/whisper.pengu`'s `LOG_INFO` = 2
  against raylib's `TraceLogLevel.LOG_INFO` = 3) is still `E0046`, and the
  message now says "top-level constant" instead of "built-in type".
- **`std/raygui.d.pengu` imports `std.raylib` and `std/nanosvgrast.d.pengu`
  imports `std.nanosvg`.** Their signatures use types from the header they
  include (`Rectangle`, `Font`, `Color`, `NSVGimage`); without the import the
  type became a generic placeholder and every call failed with
  `Argument 'bounds' of 'Button' expects 'Rectangle_any', got 'Rectangle'`.
- **A bare array/map literal is no longer accepted as a statement (`E0005`).**
  C-style indexing (`arr[0]`, which PenguScript spells `arr at 0`) parses as the
  variable plus a stray `[0]` statement; it used to compile into a useless
  `{ 0 };` (and, before the folding fix above, into `0;`). The checker now
  reports _An array literal is not a statement_ with the hint "PenguScript
  indexes with 'x at i', not 'x[i]'".
- **The `ref to char` argument mismatch now explains the conversion.** Passing a
  `string` value where a binding expects `ref to char` says: _A string literal
  converts automatically, but a string value needs
  `calling ffi.cstr_from_string with s` (std.ffi)_.
- **`build_runtime.py` stages two more headers.** `stb_herringbone_wang_tile.h`
  and `stb_image_resize2.h` live in `std_c/` and have `std/*.d.pengu` bindings,
  but were missing from `SINGLE_HEADER_NAMES`, so any program importing
  `std.stb_herringbone_wang_tile` or `std.stb_image_resize2` failed with
  `fatal error: stb_image_resize2.h: No such file or directory`.

### Changed — BREAKING

- **`and` is no longer a list separator next to expressions** (it is the boolean
  operator now). It was removed from `arg_list`, `param_list`, `struct_init`,
  `array_lit`, `map_lit` and `indent_row`. Use `,`:

  | Before                                 | After                               |
  | -------------------------------------- | ----------------------------------- |
  | `calling f with 1 and 2`               | `calling f with 1, 2`               |
  | `weave g with x as int and y as int`   | `weave g with x as int, y as int`   |
  | `declare d with a as int and b as int` | `declare d with a as int, b as int` |
  | `with x is 1 and y is 2`               | `with x is 1, y is 2`               |
  | `1 and 2 and 3` (indented array row)   | `1, 2, 3`                           |

- **`and` stays a separator in pure name/type lists**, where no expression can
  follow: `shard_params` (`shard T and U`), `where_clause`,
  `fn_param_list` (the parameter list inside a `weave` **type**), `omen_field`
  and the judge `when … with` payload. Commas are accepted there too.
- **A bare `and`/`or` is not a list element.** Elements of a comma-separated
  list stop below the boolean operator levels, so the old separator can never be
  read silently as one boolean element:
  - array literals, map literals, indented literals and parameter defaults now
    fail at parse time with the `E0000` hint (`var xs is [1 and 2]` →
    `'and' is no longer a separator: use ','`);
  - a bare `and`/`or` glued to a **call with arguments** (`calling find with 1
and true`) or to a **struct literal** (`with flag is a and b`) is `E0005`
    — _Ambiguous 'and' after a call with arguments_ — because those shapes are
    where the removed separator was written most often and the boolean reading
    is silently valid when both operands happen to be `bool`.

  Parenthesise to pass a boolean: `[(a and b)]`, `with flag is (a and b)`,
  `(calling find with 1) and true`. Bare `and`/`or` keep working everywhere a
  single value is expected (conditions, `var`/`let` initialisers, `return`,
  `set`, nested calls), so `var ok as bool is a and b` and `if a and b:` are
  unchanged.

- Docs in this repo (`LANGUAGE.md`, `CHEATSHEET.md`) were migrated to commas;
  `CHEATSHEET` §3.4 now documents `,` as _the_ list separator.

### Migration

- Replace separator `and` with `,` in: `calling` arguments, `weave`/`declare`
  parameter lists, struct-init literals (`with x is …, y is …`), array and map
  literals (bracket and indented forms).
- `calling f with a and b` no longer means "two arguments" and it no longer
  compiles: it used to parse as `(calling f with a) and b`, which was silently
  accepted whenever both operands were `bool`. It is now `E0005`, so the
  mistake is caught at compile time instead of changing the meaning of the
  program. Write `calling f with a, b` for two arguments or
  `(calling f with a) and b` for a boolean combination.

### Migration performed in this change (repo-wide)

`std/` and `tests/` were migrated together with the language change, so the
repository compiles and the full suite is green (**610 passed**):

- **`std/*.pengu` and `std/*.d.pengu`**: 725 code-level separators rewritten in
  47 files. Comments and string literals were left untouched (the std modules are
  full of English prose containing "and"), and every file was re-parsed after the
  rewrite.
  > The `std/` half of this migration was re-applied later in the same release
  > (the parser-driven pass counted 697 separators this time; the difference is
  > the modules that were added or edited in between) because a `git checkout
-- std/` while regenerating bindings discarded it. The documentation that
  > those files carried was restored from the `pengucc_build/std/` snapshot
  > first, and the result is `pengu check`-clean for all 49 importable modules
  > and compiles as a single bundle.
- **`tests/**/\*.pengu`\*\* (the stdlib exercise programs) were migrated in the same
  pass.
- **Pengu sources embedded in `tests/*.py`**: 218 separators across 106 string
  literals plus one f-string, migrated by an `ast`-based pass that works on the
  literal _values_ and only rewrites snippets that parse as Pengu — so expected
  messages such as `"ranges and in ok"` or
  `"Omen variant name 'ONE' is used by both omen 'A' and omen 'B'"` and C header
  strings were preserved verbatim.
- **`std/lot.pengu`**: its `lambda` parameter was renamed to `rate`. `lambda` is
  a reserved word since this version (lambda expressions), so it can no longer be
  used as an identifier.
- **`README.md`**: its two ```pengu blocks (`with model is "Pengu" and speed is
  0.0`, `calling xxhash.XXH64 with "PenguScript" and 11 and 0`) and the
`weave name with a as T and b as T into R`prose were rewritten to commas.
All other fenced Pengu blocks in the repo were re-parsed with`PenguParser`; the remaining `and` occurrences are boolean operators or English
  prose inside comments.
- **VS Code extension snippets**: five bodies still expanded the removed
  separator (`weave` params, `ward.assert_eq_int`/`_string`, `weave_many`,
  the `test` template). They now use commas; the `and-or` snippet keeps `and`
  because it inserts the _operator_. Two snippets were added for the
  now-working maybe binding (`ifbind`/`iflet`) and the presence test
  (`present`).
- `examples/` does not exist in this repository (and `scratch/` is gitignored
  dev scratch that still contains pre-0.10.0 sources; it is not part of the
  tree).

### Added — C callbacks, word tests in argument lists

- **Function-pointer values and C callbacks work.** Three defects kept `alias …
as ref to weave …` / `ref to weave …` unusable:
  1. `FnType` was not compatible with a declared `ref to weave …` (nor with an
     alias of it), so `var cb as ref to weave with x as int into int is lambda …`
     failed with _declared as 'ref to weave …', but initialized with 'weave …'_.
     A function value now decays to a function pointer for compatibility.
  2. Calling **through** a function-pointer variable (`calling cb with 21`) was
     reported as _Undefined function 'cb'_; the callee resolution now unwraps
     `RefType(FnType)` (and aliases of it) and uses its signature.
  3. The C declarator for such a variable was emitted as
     `int32_t (*)(int32_t) cb` (invalid C — the identifier must go inside the
     parentheses) and `to_c_type` spelled `ref to weave …` as a pointer _to_ a
     function pointer. Both now go through `CTypeMapper.to_c_decl`.

  On top of that, a function value passed to a callback parameter is now
  **cast to the declared callback type** (`((AudioCallback)on_audio)`). That is
  what makes raylib's callbacks compile under GCC 14+: their C prototypes carry
  `const` qualifiers the `.d.pengu` binding does not express
  (`const char *text` in `TraceLogCallback`, `const void*` in `qsort`). Verified
  by building real programs for `SetAudioStreamCallback`,
  `SetTraceLogCallback`, `SetSaveFileDataCallback` and
  `SetLoadFileTextCallback`, plus an `atexit` callback that runs
  (`tests/test_callbacks.py`).

- **`va_list` (and every bare custom type) is no longer mangled.** The optional
  `of type …` part of a `custom_type` leaves a `None` child behind, and
  `ast_to_type` treated it as a type argument, turning `va_list` into the bogus
  generic `va_list_any` (`Rectangle_any`, `NSVGimage_any` had the same cause).
  Bare custom types now keep their plain name, so the emitted C uses `va_list`
  (from `<stdarg.h>`, already included by the runtime header).
- **A word test in argument position is now rejected (`E0005`).**
  `calling find with 1 is true` parses as `calling find with (1 is true)` — the
  test applies to the _last argument_, while a C-style `find(1) == true` tests
  the call's result, and the mistake was silent whenever the parameter happened
  to be `bool`. The checker now reports _Ambiguous 'is true' in the arguments of
  'find'_ and the help spells out both readings:
  `calling f with (x is true)` (test as the argument) and
  `(calling f with x) is true` (test the call's result). The same applies to
  `is false`, `is present` and `is not present`. Tests in other positions are
  unaffected (`if m is present:`, `calling ready is true` with no arguments,
  struct-literal field values), so nothing in `std/` or the suite needed
  changing.

### Known issues found while validating this change (not addressed here)

- **Inline callback parameters cannot express C `const` qualifiers.** A callback
  parameter written inline (`compar as ref to weave with a as ref to void, b as
ref to void into int`) is cast to the type spelled by those Pengu parameters,
  so `qsort`'s `int (*)(const void*, const void*)` still mismatches and GCC 14+
  rejects it. Callbacks declared through an alias of a **C typedef** are immune,
  because the cast names the typedef — which is how every raylib callback is
  bound. Fixing the inline case needs `const` in the type grammar (and in
  `pengu bind`), which is not part of this change.
- **`x to T` only casts to simple types.** The `to` operator is the _range_
  operator with a cast heuristic on the right operand, so
  `ptr to ref to int` is a syntax error; use `transmute ptr to ref to int` for
  pointers, `maybe T`, arrays and other compound types.
- **A Pengu function named after a C keyword is emitted unmangled in its
  definition** (`weave double …` → `int32_t double(int32_t x)`), while uses go
  through `_c_ident` (`_double`). Rename such functions for now.
- **The grammar's `if_cond_binding_present` alternative is unreachable.** Every
  `if NAME as T is <expr> is present:` parses as `if_cond_binding` with the
  presence test inside the operand (the operand is greedy), which is why the
  checker/codegen unwrap a trailing `is_present` themselves. The dead
  alternative is kept for now to avoid perturbing the LALR tables.
- **One silently-resolved LALR shift/reduce conflict (maintainers).** The
  grammar has always been built without `strict=True`, so Lark resolves
  conflicts by shift. It had one on `COMMA` before the list rule above; the
  same underlying `if_cond` binding ambiguity is now reported on `AS`. Both
  spellings are covered by tests (`tests/test_maybe_bindings.py`,
  `tests/test_error_ux.py`) and by the full suite.

### `std/` audit performed in this change (50 modules)

- **Separators**: an AST audit found **194 multi-argument calls** across the 50
  modules and **0 leftover `and` separators** — every code-level `and` in
  `std/` sits inside a `bool_and`/`bool_or` node (the boolean operator). The
  remaining `and` occurrences are English prose in comments.
- **Compilation**: every module parses and type-checks on its own, and a single
  entry importing **48 of them at once** (all but `whisper`, whose `LOG_*`
  constants genuinely clash with raylib's `TraceLogLevel`) builds with gcc and
  links in ~36 s. `pengu check` on the 50-module entry reports only those five
  `LOG_*` collisions.
- **Runtime**: the repository's own stdlib programs (27 `tests/std_programs/*`,
  compiled and run by `tests/test_stdlib.py`) are green, plus these new manual
  checks: a ported `raylib` **basic window** and a `raylib` + `raygui` window
  both open and stay alive; `perlinum` runs; `nanosvg`/`nanosvgrast` compile but
  the vendored library crashes (see below).

### `pengu bind`: the generator now targets the current language

`pengu_bind.py` was updated so a freshly generated binding is valid today, and
the tool-produced `std/*.d.pengu` files were regenerated with it:

- **Comments are PenguScript single-line `#` comments.** A multi-line C block
  (`/* … */`, `/** … */`) or a run of `//`/`///` lines becomes one `# …` line
  per source line, with the `*` gutters and the opening/closing markers
  stripped. Only the generated-file banner keeps `##`.
  A multi-line block was not even _detected_ before: `_comment_before` only
  recognised a comment whose first inspected line started with `/*`, so blocks
  closed by ` */` were dropped entirely.
- **`const` signatures become `frozen`.** `const char *text` →
  `text as ref to frozen char`, `const void *blob` → `ref to frozen void`,
  `const T value` → `frozen T`. A _const pointer_ (`T * const p`) is deliberately
  dropped — that is what `let` expresses, and `frozen` always qualifies the
  pointee. 98 parameters/returns across the regenerated bindings gained the
  qualifier.
- **`va_list` (and `__builtin_va_list`) map to `va_list`** instead of leaking a
  compiler-specific spelling, so raylib's `TraceLogCallback` can be described.
- **Callback aliases are hoisted out of the declaration that needs them.**
  `alias Callback1 as ref to weave …` used to be appended at the point of
  discovery, which put it _inside_ a `rune` body and produced invalid code
  (`alias Callback1 …` followed by `  read as Callback1`). They are queued and
  flushed before the `rune`/`declare` line.
- **Enum aliases are dropped with a warning.** C allows two enumerators to share
  a value; `omen` does not (`E0027`), so the second name is skipped instead of
  emitting a binding that cannot compile.
- **`import` lines for included headers are auto-detected.** The generator scans
  the sibling bindings' `## Source header:` banners and emits the `import`s a
  binding needs to reuse the _same_ types as the headers it includes
  (`raygui.h` includes `raylib.h` → `import std.raylib`, `nanosvgrast.h` →
  `import std.nanosvg`). Two mistakes are avoided here: a binding never imports
  itself (the `.d.pengu` suffix has two dots, so the module name is stripped by
  hand), and the scan is skipped when the header is bound elsewhere.
  New flag: `pengu bind --auto-import DIR` (default: the output directory,
  empty string disables it).
- **Regeneration tool**: `regen_std_bindings.py` re-runs the generator for the
  bindings that carry the tool banner, keeps each file's hand-written preamble
  and _refuses_ to rewrite a file when declarations would be lost — that is how
  the hand-curated ones (raylib's colour constants and platform links, the
  pure-Pengu wrappers, the hand-written webui/sqlite3/xxhash/yaml bindings) stay
  untouched. It regenerated 12 bindings: `datastructura`, `fenestra`, `imago`,
  `nanosvg`, `nanosvgrast`, `pactum`, `perlinum`, `raygui`, `scriptor`,
  `stb_herringbone_wang_tile`, `stb_image_resize2` and `typis`.

Because bindings now carry `frozen`, two call sites had to follow: a
`ref to frozen char` parameter still accepts a string literal (the literal and
`_is_ref_char_type` now look through `frozen`), and a `frozen` _result_ cannot be
stored in a mutable local without a conversion
(`tests/test_ffi_libs.py`'s `imago.failure_reason` smoke now declares
`var why as ref to frozen char`).

### Hand-written bindings migrated to the same style

The 11 bindings the generator cannot produce were brought in line by hand
(`migrate_manual_bindings.py` merges the generator's signatures into a
hand-written file by declaration name — parameters must line up — and refuses to
write when a declaration or a parse would be lost):

- **`const` → `frozen`.** `raylib.d.pengu` (146 signatures:
  `SetClipboardText with text as ref to frozen char`, `GetMonitorName into ref to
frozen char`, `SetShaderValue … value as ref to frozen void`), `sqlite3.d.pengu`
  (12, including the callback aliases that now take
  `ref to frozen Fts5ExtensionApi`), `xlsxio.d.pengu` (`get_version_string`,
  `open`'s filename/sheetname, `add_cell_string`, `add_column`),
  `xxhash.d.pengu` (`const void* input` → `ref to frozen void` on every one-shot
  hash and `_update`, and `XXH*_digest`'s `const XXH*_state_t*` →
  `ref to frozen XXH*_state_t`), `yaml.d.pengu` (`get_version_string`),
  `miniaudio.d.pengu` (`ma_version_string`).
- **`##` docs → `#`**, the generator's spelling. No documentation is lost:
  `pengu_lsp/hover.py`'s `extract_doc_from_file` and the checker's
  `_extract_preceding_doc` both read `#` comments as doc text, so hover and
  `pengu doc` keep working. `tomlum`, `uuid`, `minicoro` and `webui` needed only
  this change (0 signatures were stale).
- **Stale doc examples using `and` as an argument separator became `,`** (23
  comment lines across `std/*.pengu`), so the documentation a reader copies
  shows the current syntax.

These 5 files cannot be regenerated by the tool at all — `miniaudio.h` needs
`pthread.h` (absent from `c_bind_stubs/`), `xlsxio`/`xxhash`/`yaml` trip
pycparser on GNU constructs the preprocessed text keeps, and `rlights.h` has no
`include` line on purpose (it pulls in raylib plus an OpenGL loader) — so
`regen_std_bindings.py` skips them ("hand-written, no `pengu bind` banner") and
they stay hand-maintained.

### Known issues found while auditing `std/` (not addressed here)

- **`pengu build` can leave a stale binary and still report "(cached)".** The
  up-to-date check compares the output's mtime with the _entry source_ mtime on
  the fixed path `build/app.exe`, so it does not notice that the existing
  binary came from a **different** program. Repro (verified): build program A
  (fresh), build program B (fresh) and then build A again — the second A build
  prints `Finished (cached)` and leaves B's binary in place. Touching the source
  forces the rebuild. `pengu run` is not affected in the same way (it uses a
  per-entry `build/<tag>_run/` directory). Workaround: delete `build/app.exe`
  (and `build/.bundle_hash`) or touch the entry before building.
- **`std/nanosvg` + `std/nanosvgrast` compile but crash at run time.** The
  vendored single-header library segfaults inside `nsvgParse` for any non-empty
  SVG. It reproduces in **plain C** with the repository's own header and
  `libpengu_stb.a` (`nsvgParse("")` returns an image, `nsvgParse("<svg></svg>")`
  raises `0xC0000005`), at `-O0`, `-O1` and `-O2`, so it is a vendor-source
  problem, not a compiler or codegen bug. `perlinum` (same object file) works.
- **`weave main`'s return value is discarded.** The generated wrapper calls
  `pengu_main();` and returns 0, so a program whose `main` returns 42 still
  exits with status 0. Scripts that need an exit status must call
  `spark.exit`-style helpers or write to stderr.
- **A `string` value is not accepted where a binding declares `ref to char`.**
  String _literals_ are converted (`DrawText("hi", …)` works), but passing a
  `string` variable fails with
  `Argument 'input' of 'Parse' expects 'ref to char', got 'string'`.
- **`calling … with …` used as an operand needs parentheses.** In
  `if calling GuiButton with bounds, "Click me" == 1:` the comparison binds to
  the _last argument_, so the C idiom `GuiButton(...) == 1` must be written
  `(calling raygui.Button with bounds, "Click me") == 1`.
- **Two std modules can define the same constant name.** `std/whisper.pengu`
  (`LOG_INFO` = 2) and `std/raylib.d.pengu` (`TraceLogLevel.LOG_INFO` = 3)
  cannot be imported together; the `E0046` message tells the user to use the
  full omen name (`TraceLogLevel_LOG_INFO`) or rename. A `const`/`const`
  clash across modules (two modules defining the same plain constant) is not
  detected at all — the last registration wins silently.
- **`std/imago.d.pengu` and `std/sqlite3.d.pengu` reference `FILE` and
  `va_list`.** Those functions cannot be called from Pengu code (unknown C
  types become generic placeholders; variadic C functions are not callable
  anyway). The rest of both modules is usable.

## [0.9.1] - Unreleased

### Added

- **`try`, `or else` and `or return` now generate real C code.** Previously the
  three unwrap operators type-checked but fell through codegen's default branch
  (translating only the first child), so a program using them emitted invalid C
  (`PenguMaybe` assigned to the unwrapped type). They now lower to a GNU
  statement-expression that unwraps the success value lazily and `return`s on
  failure: `or else` yields the fallback, `or return X` returns `X` from the
  enclosing function, and `try` propagates `maybe none` / the error result to
  the caller.
- **`try` is now restricted to functions that can propagate the failure**
  (E0045). A `try` over `maybe T` requires the enclosing weave/enchanting to
  return `maybe T`; a `try` over `result of T to E` requires a result return
  whose error type is compatible with `E`. Misuse used to type-check and then
  fail in C; it is now a clear English semantic error.
- **Omen variant name collisions are detected** (E0046). Both the full
  (`Omen_variant`) and simple (`variant`) names occupy the global scope, so a
  weave/const/alias reusing one of them — or two omens sharing a variant name —
  silently shadowed a registration; it now reports a clear error.
- **`bind` validates that the bound target type exists** (E0004) before
  registering concept methods on it.
- **`pengu_precis_free_response()` runtime helper** releases a
  `PenguPrecisClientResponse` (header map, owned body string and the struct),
  matching the ownership contract documented in `pengu_runtime.h`.
- **Resource cleanup for native handles.** New runtime helpers plus std
  wrappers (functional weaves and `free` enchanting methods) for every
  concurrency primitive (`pengu_c_filum_{mutex,wait_group,once,cond,
atomic_int,chan}_free` in `std/filum.pengu`), compiled regexes
  (`pengu_c_regulus_regex_free`, `pengu_c_regulus_match_free` in
  `std/regulus.pengu`) and parsed XML/HTML documents and nodes
  (`pengu_c_parchment_document_free`, `pengu_c_parchment_node_free` in
  `std/parchment.pengu`). Because PenguScript copies wrapper structs by value,
  these helpers release the native resources (PCRE2 code, libxml2 document,
  owned string buffers) and null dangling fields instead of `free()`-ing the
  value-copied structs; the ownership contract is documented in
  `pengu_runtime.h`.
- **`include` no longer invents method signatures.** The raw-C fallback that
  turned _any_ unknown enchanting/instance method into a parameterless `void`
  call whenever a C header was included is gone: misspelled method calls now
  raise `E0004`. Bare unknown function calls in include modules remain the
  documented FFI escape hatch (the C header declares them).
- **Omen variant collisions with built-in types report a clear message**
  (E0046): `omen Color:\n  int` now explains that `int` is a reserved
  built-in type and points to the full `Color_int` variant name.
- **Ownership documentation completed** in `pengu_runtime.h` for every
  allocating function: Archivum file/metadata/dir reads, Regulus split/find-all,
  Parchment serialization/attribute/text, and Precis URL encode/decode and
  query parsing now state who owns the returned buffers.
- **LSP: instant completion for imported module members.** The server keeps a
  global module cache (import alias → module scope, only non-empty scopes)
  refreshed on every document validation (even when the document has errors,
  since imports are collected in pass 1). Completion for `spark.` / `alias.`
  resolves members from the cache only when the alias is **not** defined in the
  current document (unvalidated or unimported files); a defined import symbol
  is authoritative and never falls back to the cache, so a stale or foreign
  cached scope can no longer leak another module's members into the
  suggestions. Aliased imports (`import std.spark as s`) and project modules
  work the same way.
- **C ⇄ Pengu conversion bridges** (runtime + `std/ffi`). New runtime helpers
  in `pengu_runtime.h` / `pengu_runtime.c` for embedding/library code, all
  NULL-safe and documented with ownership rules:
  - string views: `pengu_string_to_cstr` / `pengu_string_bytes` (read-only,
    never NULL for empty strings), plus owning `pengu_string_copy`;
  - container accessors `pengu_slice_data` / `pengu_list_data`;
  - deep-copying constructors `pengu_list_from_data`,
    `pengu_map_from_entries`, exporters `pengu_map_to_entries`
    (`PenguEntryArray`) + `pengu_entry_array_free`, and
    `pengu_string_as_slice`.
    New module **`std/ffi.pengu`** exposes concrete PenguScript wrappers
    (string↔C string, byte views, byte/int/float slices and lists from raw
    pointers, and a string→int map built from parallel slices), each with
    module docstrings explaining the ownership model. PenguScript container
    types are nominal, so per-element-type typed symbols were added
    (`pengu_ffi_slice_i32`, `pengu_ffi_list_f64`, `pengu_ffi_cstr_string`, …);
    fully generic (`shard T`) buffer bridges cannot be expressed today because
    the language cannot infer type parameters that appear only in the return
    type of container conversions.
    Exercised by `tests/std_programs/test_ffi.pengu`, a C driver test
    (`tests/test_ffi_bridges.py`) and bundle-emission assertions on the
    generated `bundle.c`.
- **Standard-library documentation pass (`std/`).** Every wrapper module
  (non-`.d.pengu`) now matches the `std/ffi.pengu` documentation standard:
  module header with description, usage and ownership model; section
  separators; and a doc comment above each of the 789 public declarations
  (weave, declare, rune/enchanting methods, aliases, constants) with purpose,
  signature and ownership/null notes verified against the runtime sources. The
  `.d.pengu` C-binding files keep their extensive upstream documentation; they
  gained a consistent module header (purpose + "pure `.d` binding" note) and,
  where missing, an ownership note. Changes are comment-only; every file was
  re-parsed and the full suite stays green.
- **Omen variants declared in `.d.pengu` emit their simple C names.** When an
  `omen` lives in a `.d.pengu` declaration file it mirrors an enum already
  defined by the included C header, so codegen now emits the bare variant name
  (`KEY_LEFT`, `.tag = KeyDown`, `case KEY_LEFT:`) instead of the prefixed
  `Omen_variant` form, for every emission path: `var_ref` / bare names, module
  members (`keys.KEY_LEFT`), `Omen.variant` accesses, algebraic-tag
  initializers and `judge` cases. Omens declared in normal `.pengu` modules
  keep the collision-safe `Omen_variant` prefix, and declaration omens still
  generate no C type definitions. Centralized in
  `PenguCodegen._get_omen_variant_c_name`; covered by
  `TestOmenDeclarationEmission`.
- **LSP: module-name completion in `import` statements.** Typing `import ` now
  offers the standard-library modules (`std.spark`, …) plus project modules
  under `src/` (`components.player`, …); `import std.` suggests the short names
  (`spark`, `archivum`, `sqlite3`, …) and replaces exactly the typed prefix via
  a `textEdit`, so the selected module is inserted without duplicating text.
  Partial prefixes filter the list (`import st…`, `import std.s…`), private
  `_`-prefixed files/directories are hidden, and `.d.pengu` bindings are
  offered under their real spec (`std.sqlite3`). The directory scan is cached
  per project root for 5 seconds.
- **LSP lint warnings.** Clean documents are now linted for unused imports and
  unused local `var` / `let` declarations, published as
  `DiagnosticSeverity.Warning` diagnostics (conservative textual analysis:
  any occurrence outside the declaration counts as a use; `_`-prefixed discard
  names are exempt). Implemented in `server._style_warning_diagnostics`.
- **LSP "Organize imports" code action.** `code_actions.organize_imports_action`
  drops import statements whose module is never referenced outside the import
  block and sorts the remaining imports alphabetically by spec, replacing the
  contiguous import block in a single edit (no-op when the block is already
  tidy).
- **LSP Go to Implementation.** New `textDocument/implementation` handler
  returns every declaration of the symbol under the cursor across the standard
  library and the current project (functions, types, constants and
  enchanting/bind `weave` methods), via `code_actions.declaration_locations`
  (cached per set of roots; `.d.pengu` bodies skipped).
- **LSP Find References.** New `textDocument/references` handler: local
  `var`/`let`/`param` symbols resolve within the current document only, while
  global symbols resolve across stdlib + project sources
  (`code_actions.word_occurrences_in_roots`), honouring
  `context.include_declaration` for the active document. Bounded project-root
  discovery (never escalates to a filesystem root).
- **LSP contextual completion.** Three new completion contexts:
  - inside a `judge` block, typing `when ` offers the subject omen's variants
    (or `true`/`false` for a bool) plus an `else ->` item — resolved by walking
    up to the `judge <expr>:` line (takes precedence over the compile-time
    `when` variables);
  - typing `set.` inside a `with target:` block offers the rune's fields;
  - after `var x as Type is with ` offers the rune's fields with per-type
    default initializers and an "(all fields)" fill snippet.
    `get_completions` gained an optional `doc_text` parameter for the multi-line
    contexts (the server passes the document text).
- **LSP "Implement missing concept methods" code action.** When the cursor
  sits inside a `bind Target with Concept:` block,
  `code_actions.implement_concept_methods_action` appends a weave skeleton for
  every concept method not yet implemented there (correct parameter list,
  return type and a per-type default body: `return`, `return 0`, `return
false`, `return ""`, `return maybe none`, …), skipping methods that already
  exist. Wired into the `textDocument/codeAction` handler.
- **LSP richer hover.** Rune hovers now list the enchanting methods attached to
  the type (via `symbols.methods` and `RuneType.methods`) and, for generic
  runes, show the declared type parameters and concrete type arguments
  (`**Type arguments**: `int``). Omens/variants already listed payloads and
  sizes; docstrings stay appended.
- **LSP formatting reads `pengu.yaml`.** `formatting.load_format_config` finds
  the nearest project config (bounded upward walk) and extracts `tab_size` /
  `indent` / `indent_size` / `indent_width` and `insert_spaces` / `use_tabs`.
  `textDocument/formatting` honours client FormattingOptions first, then the
  project config, then the 2-space default.
- **Block-style construction expressions (`with:`).** `var x as SomeType with:`
  followed by an indented body of `set .field is ...` assignments and
  `calling .method` calls now builds a fresh value through an implicit mutable
  temporary and evaluates to the built object (any expression position). The
  target type must be annotated (`E0014` otherwise); unknown fields/methods
  and disallowed statements inside the body are semantic errors (`E0004` /
  `E0007` style). Grammar adds `with_init_expr`; typing mirrors `with target:`
  scopes; codegen emits a GNU statement-expression. The single-line
  `with field is … and …` initializer is unchanged. Covered by
  `TestWithInitBlock`.
- **Imported dotted types resolve correctly.** `rl.Rectangle` in type
  annotations used to fall through `lookup_type` (creating an empty rune and
  false `E0013`/`E0022` errors for fields and, with `with:` blocks, builder
  scopes). `SymbolTable.lookup_type` now resolves dotted names through the
  import-prefixed registries (`rl_Rectangle`) or the import's module scope,
  and codegen's type lookup delegates to it — fixing Raylib-style structs and
  any other binding whose types are referenced through an import alias.
  Covered by `TestImportedModuleDottedTypes`.
- **`do:` block expressions.** An indented `do:` block is an expression: its
  statements run in a fresh local scope (declared variables do not escape)
  and the block evaluates to its last expression statement (or `void`).
  Works as a `var`/`let` initializer with full type checking; type mismatches
  with the declared annotation are normal errors. Compiles to a GNU
  statement-expression. `do` is now a control keyword (VS Code TextMate +
  snippet, LSP snippet). Covered by `TestDoBlockExpression`. Block forms of
  `unless`/`judge` and value-returning `for`/`while` remain roadmap items.
- **`if … else:` blocks as expressions.** An `if` whose branches are indented
  statement blocks now supplies a value when it sits in a value position: each
  branch runs in its own scope and must end with an expression; all branches must
  share one common type. A value block's value is its last statement's value, so
  both `else if <cond>:` and `else:` + a nested indented `if` chain, and `do:`
  blocks ending in an `if`, all work. Value-ness is **positional**: `if cond:` +
  block is token-identical as a statement and as a value, so `if` keeps a single
  grammar rule (`if_stmt`) and the checker records the branch type on the node
  (`_pengu_value_type`) when the `if` is in a value slot; codegen emits a GNU
  statement-expression with a typed temporary assigned per branch. Statement
  `if` semantics (dead-code elimination, `W0004`, binding conditions) are
  untouched. Covered by `TestIfBlockExpression` (including a regression test
  that statement-level `if` bodies still execute) and
  `TestDoBlockExpression`; CHEATSHEET §6.1.2 documents it.

  > A separate `if_block_expr` grammar rule reachable from the expression chain
  > must **not** be reintroduced: it makes every statement-level `if` parse as an
  > expression and silently drops branch bodies.

- **`unless … else:` blocks as expressions, and more value positions.** `unless`
  is the mirror of the value-position `if` (`value_expr` now accepts
  `unless_stmt`; `PenguChecker._check_unless_value` reuses `_check_value_block`
  and `_merge_branch_value_types`, and codegen reuses `_translate_value_if` with
  the condition negated). The same machinery now also covers the remaining value
  slots, which share one walker (`_check_value_exprs`) so nested block values are
  validated wherever they appear:
  - `return` — `return if c: …` / `return unless c: …` (and a block value
    anywhere in the returned expression, e.g.
    `return calling pick with if c: …`); `return_stmt`'s trailing `_NEWLINE` is
    now optional, because a block value consumes its own line break.
  - call arguments — positional and `name is <block>`.
  - struct-literal fields — `with x is <block> and y is <block>`.
  - `set .field is <block>` inside a `with:` builder (composition with §18).

- **Loops as expressions (all loop forms).** Every loop the language has —
  `while cond:`, `for i from a to b [step s]:`, `for v in col:` and
  `for i, v in col:` (incl. `_` discard) — now works in a value position and
  **collects** its body's last expression per iteration into a `list of T`:
  - Grammar: `value_expr` accepts `while_stmt` / `for_stmt`, so loops work in
    every value slot already covered (`var`/`let`/`static var` initializers,
    `set`, `return`, call arguments, struct-literal fields, block tails). The
    `for … then …` comprehension keeps working (it stays a plain expression and
    is distinguished by `then` vs `:`).
  - Checker: `_check_loop_value` wraps the element type into
    `ListType(element=T)` and records it on the node (`_pengu_value_type`); the
    three loop checkers took a `collect` flag that checks the body as a value
    block instead of a statement block and returns the per-iteration type. A body
    that produces no value is `E0005` (_loop used as a value must produce a value
    on every iteration_). A loop that merely ends a value block is best-effort
    (no error) so statement-style bodies keep working.
  - Codegen: `_translate_loop_value` emits
    `({ PenguList l = pengu_list_new(sizeof(T), 8); for (…) { …; T v = <value>;
pengu_list_push(&l, &v); } l; })` by threading an `append_ctx` through the
    existing `while`/`for_range`/`for_in` translators, whose bodies now go through
    `_translate_loop_body`. The push sits at the end of the body, so `continue`
    skips a value and `break` ends the loop for free. Nested loops build
    `list of list of T`.
  - Types resolved through context: `_check_value_exprs` now takes the enclosing
    slot's expected type, so a trailing `with:` builder inside a loop body is
    typed from the list element (`var ps as list of Point is for …: with: …`), and
    the same plumbing now reaches `if`/`unless`/`do` initializers.
  - Docs: CHEATSHEET §6.1.3 (loops as expressions) and §6.1.4, the _definitive_
    table of what is and is not an expression (12 constructs × 8 value positions,
    verified by probe) — plus LANGUAGE.md §7.6.
  - Tests: `TestLoopValueExpression` (13).

- **Fixed: a loop variable was rewritten inside a `with:` builder.** Codegen
  treated any bare name inside a `with` scope as a field of the target unless the
  _global_ symbol table knew it, so a loop variable used in a builder emitted
  `_with_1.i` (invalid C: `'Point' has no member named 'i'`). Names present in
  `local_vars` now stay plain identifiers.

- **Fixed: `do:` nested as a block's tail lost its value** (a trailing
  `expr_stmt`-wrapped `do:` is a value block, like a trailing `if`/loop).

- **Fixed: iterating an inline array literal emitted invalid C.** `for v in
[1, 2, 3]` produced `({ 1, 2, 3 })[_i]` — an array literal is a brace
  initializer with no storage. The for-in codegen now materializes it into a
  temporary array (`int32_t _lit[] = { 1, 2, 3 };`) and indexes that.

  Covered by `TestUnlessValueExpression` and `TestBlockValuePositions`;
  LANGUAGE.md §7.6 and CHEATSHEET §6.1.2 document the positions.

- **Single-line block statements now compile and are type-checked.** The
  one-line block form (`block: ":" simple_stmt _NEWLINE`) parses into aliased
  nodes (`return_simple`, `set_simple`, `named_simple`, `continue_simple`,
  `break_simple`) or a bare `simple_stmt` holding one expression. The checker and
  codegen had no dispatch for those nodes, so `if c: return 0`,
  `while i < n: set i is i + 1` and `for i from 0 to 3: calling tick with i`
  silently emitted **no C at all** and skipped every semantic check. Both now
  re-dispatch through `SIMPLE_STMT_ALIASES` (exported by `pengu_grammar`) onto the
  canonical statement rules, so single-line bodies emit the same C as — and are
  validated exactly like — their indented spelling (mutability, return type,
  loop-control placement, expression type checking). Covered by
  `TestSingleLineBlockBodies`.

### Removed

- **The `pub` keyword is gone.** Visibility is determined exclusively by the
  underscore naming convention: identifiers starting with `_` are module
  private (E0043 on cross-module access) and everything else is public. `pub`
  never had semantic effect, so removing it simplifies the grammar, the
  checker/codegen top-level unwrapping and the docs with zero behavior change
  for existing programs.

## [0.9.0] - Minimal Modern C

### Stabilization pass (repo-preparation fixes)

- **Grammar file repaired**: duplicated trailing token definitions and a stray
  `"""` after `DOTDOT` made `pengu_parser` fail at import; the duplicate block
  was removed so the grammar imports cleanly.
- **`to` cast ambiguity removed**: the duplicate `logic_or "to" base_type ->
cast_expr` alternative in `range_expr` was deleted — casts live only in
  `postfix`, so `10 to float` is a cast while `1 to 10` is a range.
- **`at` chains are left-associative semantically**: `grid at 0 at 0` parsed
  right-nested (`at(grid, at(0, 0))`), breaking typing and codegen. A flatten
  helper now rewrites the chain to `[base, idx, idx, ...]` and folds it
  left-to-right in both `pengu_infer` and `pengu_codegen` (`g[0][0]`).
- **Rune/field indent literals**: indented literal blocks accept `NAME is expr`
  rows (in addition to array rows and `key: value` map entries) so
  `var p as Player is\n  x is 10.0\n  y is 20.0` parses.
- **English-only diagnostics**: E0041/E0042/E0044 messages (array-size
  mismatches, inverted ranges, non-exhaustive judge) were bilingual or mojibake;
  they are now English, matching the rest of the error catalogue.
- **Version strings**: bundle header and module docstrings now read
  **v0.9.0** (was `v0.6`); `VERSION` file bumped to `0.9.0`.

### Modern Language Expressiveness & Semantic Rigor

- **Multiline Arrays**: Bracket-delimited collections (`[ ... ]`) now bypass indentation rules via `OPEN_PAREN_types = ["LSQB", "LPAR", "LBRACE"]` in `PenguIndenter`, allowing naturally formatted multiline arrays across arbitrary indentation levels.
- **Triple-Quoted Strings & String Interpolation**:
  - Added triple-quoted strings (`"""..."""`) with automatic common whitespace dedent.
  - Added expression interpolation (`{expr}`) inside format strings, compiling directly into human-readable `snprintf` / `pengu_string_format` C99 output.
  - Added raw string literals (`r"..."` and `r"""..."""`) preventing escape sequences and interpolation expansion.
- **Indent Literals (Bare & Colon Syntax)**:
  - Introduced clean off-side literal syntax for 2D arrays (`indent_row` with `and`), 1D arrays, Runes (`field: value`), and Maps (`key: value`).
  - Supports both bare `is` and colon-prefixed `is:` without LALR(1) shift/reduce conflicts.
- **Enhanced Local Type & Size Inference**:
  - Full type inference for local declarations (`var x is 42`, `let arr is [1, 2, 3]`).
  - Array sizes automatically inferred from literal element counts when explicit sizes are omitted.
  - Semantic error `E0014` enforced on untyped `null` assignments (`var x is null`).
- **Ranges and Membership Operators**:
  - Native range expressions via `to` (`start to end`) and `..` (`start..end`), backed by stack-allocated `PenguRange` structs in C.
  - Direct range loop iteration in `for i in start to end:`.
  - Native `in` and `not in` operators for ranges, strings, arrays, and maps.
- **Semantic Checker Rigor (E0041 - E0044)**:
  - `E0041` (`ArraySizeMismatchError`): Detects dimension and shape mismatches in array literals at compile time.
  - `E0042` (`InvalidRangeError`): Validates static range boundaries to prevent inverted ranges (`start > end`).
  - `E0043` (`PrivateSymbolAccessError`): Enforces symbol privacy for identifiers prefixed with `_` outside their defining module or rune.
  - `E0044` (`NonExhaustiveJudgeError`): Guarantees exhaustive case handling in `judge` expressions for omens and booleans when no `else` fallback is present.
- **Multi-Line Defer & Errdefer Blocks**:
  - Extended `defer:` and `errdefer:` to accept multi-statement indented blocks alongside single expressions.
  - Compound statement blocks are scheduled on the LIFO defer stack, guaranteeing clean RAII-style cleanup upon function exit.
- **Verification & Zero Regressions**:
  - Full test suite expanded to 315 tests (209 core, 90 features, 16 v0.9.0 dedicated tests) with 100% pass rate.
  - Validated standalone end-to-end showcase `test_090.pengu` compiling cleanly to C99/C11 and executing via GCC.

## [0.8.4] - Released

### Repository, testing & cross-platform preparation

- **Cleanup before commit**: removed developer leftovers (`pengu_runtime_original.h`,
  personal scratch notes, stray root test artifacts) and extended `.gitignore`
  (logs, `*.csv`, caches, release staging).
- **Test-suite rewritten & unified**: the two test folders (`tests/`, `tests_std/`)
  were merged into `tests/` and the ~100 scattered test files were replaced by a
  small, organised suite — 7 pytest files grouped by area:
  `test_compiler_core.py`, `test_compiler_features.py`, `test_modules_bindings.py`,
  `test_lsp.py`, `test_cli_tools.py`, `test_ffi_libs.py`, `test_stdlib.py`
  (+ shared `tests/conftest.py` helpers and one exercise program per std module
  under `tests/std_programs/`, several libraries covered per file).
  Full suite: **484 passed / 0 failed** (up from 438).
- **Unbuildable extern removed**: `libwebsockets` was dropped from
  `extern_manifest.py` and `extern/` (2023-era sources do not build cleanly with
  modern GCC); `build_runtime.py` never referenced it. Manifest typo
  `tomic17`→`tomlc17` fixed and its docstring updated.
- **Cross-platform runtime builds**: `build_runtime.py` now selects the CMake
  generator per host (MinGW Makefiles + mingw32-make on Windows; Unix Makefiles /
  Ninja on POSIX), skips the Windows-tuned static builds of libxml2/libcurl/
  libmicrohttpd on Linux/macOS (the C runtime then links the system libraries;
  libxml2 include dirs discovered via `pkg-config`), makes best-effort builds
  non-fatal with a per-library summary, and skips the x64-only WebUI prebuilt on
  Apple Silicon. `pengu_project.py` links the POSIX runtime/system libraries
  (`-pthread -lm -ldl`, falling back to system libcurl/libxml2/libmicrohttpd)
  and `make_release.py` stays OS-generic.
- **CI on three operating systems**: `.github/workflows/ci.yml` now runs the full
  build + test + packaging matrix on **Windows, Linux and macOS** (Python 3.14 +
  Node 20, per-OS C-library dev packages via apt/brew, `build_runtime.py`,
  `pytest tests/`, `make_release.py`) and uploads per-OS standalone artifacts plus
  the VS Code extension `.vsix`. `release.yml` mirrors the matrix and publishes
  the release assets.
- **CI cross-platform fixes** (validated on the 3-OS matrix):
  - `build_runtime.py` re-applies the libuv MinGW const patch to
    `src/win/util.c` automatically (extern/ is re-downloaded per CI run) and
    stages libzip's CMake-generated `zipconf.h` after every build, fixing
    fresh-checkout xlsxio builds.
  - On POSIX the C runtime compiles against system libxml2/libcurl/
    libmicrohttpd headers via `pkg-config` (with a Homebrew include fallback),
    and the macOS workflow installs curl + sets `PKG_CONFIG_PATH`.
  - Link lines (tests and `pengu_project.py`) add the Homebrew `-L` prefix on
    macOS; Windows-only test libs (`bcrypt`, `comdlg32`, …) are now gated to
    Windows, and GUI link-probes (webui/raylib/tinyfd) run on Windows only.
  - `pengu_c_filum_goroutine_id` returns a real OS thread id on Linux/macOS
    (`pthread_threadid_np`) so `std.filum` reports it correctly there.
  - Test compile helpers tolerate newer-GCC error-promoted warnings
    (`-Wno-error=implicit-*`, `-Wno-error=int-conversion`).
- **Documentation overhaul**: `CHEATSHEET.md` rewritten from scratch — 2,300+
  lines, 20 numbered topical sections, entirely in English, every Pengu example
  that maps to generated code followed by the emitted C, balanced code fences and
  checked internal anchors. `README.md` rewritten with a current project layout
  and a complete Third-Party Acknowledgements section (Python + every C /
  single-header runtime dependency with license details read from the vendored
  headers).

### Language Server performance

- **Debounced validation on `didChange`**: typing no longer triggers a full
  parse + semantic-check per keystroke. Changes are coalesced per document
  with a 350 ms debounce, and any pending run is cancelled when new edits
  arrive, so a fast typing burst produces one validation of the final text.
  `didOpen` and `didSave` still validate immediately (and flush pending
  debounces on save).
- **Validation runs off the event loop**: the (now rarer) full-document
  checks execute in a worker thread via `run_in_executor`, keeping hover /
  completion / go-to-definition responsive while a large file validates;
  results are published back on the asyncio loop thread.
- **Content-hash validation cache**: re-validating a document whose text did
  not change (duplicate didChange / didSave after didChange) re-publishes the
  cached diagnostics instead of re-running the parser and checker.
- The programmatic sync entry points (`validate_document`, `did_open`,
  `did_change`, `did_save`) keep their immediate semantics for embedders and
  tests; new tests cover debounce coalescing, flush-on-save, cache hits and
  cache eviction.

### Call-argument type checking & imported enchanting methods

- **Function/method call arguments are now type-checked** (`E0005`): calling a
  weave or an `enchanting` method with a value that does not match the declared
  parameter type is a compile error that names the parameter, the expected type
  and the actual type — instead of silently generating C that fails at link
  time (e.g. passing a string where a `bool` is declared, or passing a `weave`
  where a `list of string` is expected). Same rules as assignments: numeric
  widening is allowed, unknown/type-param operands pass, `weave → ref to
void` / `ref to weave` function-pointer decay stays legal, and native
  `list.push`/`map.put` diagnostics (`E0018`) are unchanged.
- **LSP resolves imported `enchanting` methods on unsaved buffers**: the
  semantic checker loads imported modules relative to the entry file, so when
  the editor validates a document that is not yet saved to disk the LSP now
  materializes a temporary shadow file — methods like
  `Parser.add_option` from `std.invoke` are no longer reported as missing
  (`E0004`) while typing, and genuine argument mistakes surface as precise
  diagnostics instead.

### Compiler bug fixes (found by the rewritten test-suite)

- **`ritual` (static) methods no longer emit corrupted C**: the grammar wraps
  `ritual`/`inline` weave modifiers in a `weave_modifier` Tree, which the code
  generator previously mistook for the function name — leaking the raw AST
  repr into prototypes/definitions (e.g. `Vec2_Tree(Token('RULE', ...))`) and
  mangling the return type. `skip_weave_modifiers()` now handles both the Tree
  and bare-Token shapes in declares, weaves and monomorphized weaves; ritual
  methods emit clean `Type_name(void)` / `Type_name(params)` signatures with no
  `self` parameter.
- **Algebraic `omen` construction fixed and unified**: generated payload
  structs use a single `data` union member (was `as`) so construction,
  patterns and type definitions agree; `with Variant is with field is …`
  constructs the right tag + payload; and bare-payload forms such as
  `with code is 404` now resolve the field to its owning variant
  (`.tag = …_Failure, .data.Failure = {.code = 404}`) instead of emitting a
  bogus tag and dropping the value. Fields from different variants in one
  initializer and ambiguous/unknown fields are rejected (`E0041`).
- **Generic `omen` specializations print their mangled name**: a specialized
  `Status of string` now declares C variables as `Status_string` (the template's
  `c_name` leaked through `substitute()` before, producing an undeclared base
  type), making generic omens usable end to end.

### FFI language features (word-first style)

- **`bytes of <string>`** — borrows a string's characters as a read-only
  `ref to byte` for native C byte APIs (`((uint8_t*)((s).data))`), no copy.
- **`bytes of <array of byte>`** — yields a writable `ref to byte` to the first
  element of a fixed-size byte buffer (`&(buf)[0]`), enabling C output buffers.
  Non-string/non-byte-array operands are rejected (`E0005`).
- **Weave → C function pointers (proven at runtime, both directions)**: a
  `weave` name passed where a callback is expected decays to its C function
  pointer; a runtime helper in `pengu_runtime.h`
  (`pengu_call_callback_int`) plus a minicoro shim
  (`std_c/wrappers_minicoro.c` `pengu_mco_*`, externs in the runtime header)
  let C call PenguScript weaves and run a **PenguScript weave as a minicoro
  coroutine body** (resume/yield) from pure Pengu.
- VS Code: `bytes of` keyword + snippets; CHEATSHEET §14 (C Interop & FFI).
- **G5 xlsx stack**: `extern_manifest.py` += `libzip-1.11.3`, `expat-2.6.4`, `libyaml-0.2.5`; `build_runtime.py`
  gains tolerant `build_libzip`/`build_libexpat`/`build_xlsxio` builders (libzip & expat via CMake,
  xlsxio compiled directly with `-DSTATIC` incl. its shared-strings source). `pengu_project.py` injects
  `-DSTATIC` when xlsxio libs are linked (fixes `__imp_*` on Windows). `tests/test_extern_g5.py` proves a
  real write+read `.xlsx` round-trip.
- **libuv 1.52.1** integrated into `build_runtime.py` (`build/lib/libuv.a`, headers staged; one-line MinGW const fix in `extern/libuv-1.52.1/src/win/util.c`); `pengu_project.py` links `psapi/userenv/iphlpapi` on Windows.
- **YAML built**: `libyaml-0.2.5` (direct gcc of 8 sources + minimal `build/include/config.h` with `-DHAVE_CONFIG_H`) and `libcyaml-1.4.2` (direct gcc with `VERSION_*` defines) wired into `build_runtime.py` (`build_libyaml`/`build_libcyaml`, no-op verified); headers `yaml.h`/`cyaml/cyaml.h` staged.
- **G5 Pengu layer** (curated bindings + wrappers, all semantic-checked and compile+link+run verified):
  - `std/xlsxio.d.pengu` (xlsxio _write_ API: open/close/next_row/add_cell_string/int/float/add_column/set_detection_rows) + pure-Pengu wrapper `std/xlsx.pengu` (`xlsx.write_sheet` / `xlsx.write_rows`) that writes a real `.xlsx` workbook; runtime strings reach C `const char*` parameters via `bytes of <string>`. Verified by a Pengu compile+run that produces a valid workbook (sheet name + cell strings checked inside the produced zip).
  - `std_c/wrappers_tomlc17.c` + `std_c/pengu_tomlc17.h`: `pengu_toml_valid`/`pengu_toml_valid_file` shim over tomlc17's by-value `toml_result_t` API (which pure Pengu cannot express); `build_tomlc17` now compiles the shim into `libtomlc17.a` and stages the companion header. Binding: `std/tomlum.d.pengu`.
  - `std/yaml.d.pengu`: libyaml version query via out-`int` parameters (`yaml.get_version`, `sigil of`); YAML/libcyaml _parsing_ remains C-level only (schema/event structs) - documented in the module header.
  - libzip/libexpat/libuv stay C-level dependencies (no raw binding; xlsxio uses them); documented in CHEATSHEET §15 (Standard Library).
- Tests for the FFI/G5 features live in the consolidated suite: `tests/test_compiler_features.py`
  (bytes of, weave→pointer, coroutine) and `tests/test_ffi_libs.py` (xlsxio/xlsx round-trip,
  tomlum validity incl. file variant, yaml version, sqlite3, runtime + stb link checks,
  semantic sweep over every `std/*.d.pengu`).

## [0.8.3] - Unreleased

### Manual curated bindings for the remaining `std_c/` libraries

- **`std/xxhash.d.pengu`** — hand-written binding for the vendored `xxhash.h`
  (it cannot be auto-bound by `pengu bind`): `XXH_versionNumber`, the XXH32 /
  XXH64 / XXH3_64bits / XXH3_128bits one-shots (with `_withSeed`), the three
  opaque streaming state types and their `createState / freeState / reset /
update / digest` families, plus the `XXH128_hash_t` struct result. Uses the
  real C symbol names (no insignia). Verified end-to-end from PenguScript
  (canonical vectors + streaming==one-shot consistency).
- **`std/uuid.d.pengu`** — every public function of `uuid.h` (uuid0_generate,
  uuid4_generate, uuid_type, uuid_to_string, uuid_from_string, uuid_copy).
  uuid.h is C++-only upstream (uses the bare `uuid` tag without a typedef) and
  its Windows `uuid4_generate` only handled MSVC, so the vendored header was
  patched (added `typedef struct uuid uuid;`, `<stdbool.h>`, and a MinGW/
  `_WIN32` branch using the BCrypt RNG). `struct uuid` cannot yet be
  constructed from pure PenguScript (no fixed byte arrays), so the functions
  are verified with a C-level probe.
- **`std/minicoro.d.pengu`** — curated coroutine core: mco_create / destroy /
  resume / yield / status / running (current) / get_user_data /
  result_description plus the storage interface; state/result constants
  documented. Coroutine entry bodies need a C function pointer, which
  PenguScript weaves cannot supply yet, so the roundtrip is verified with a
  C-level probe against the compiled implementation.
- **`std/miniaudio.d.pengu`** — documented _small_ subset meaningful without an
  audio device (version macros + `ma_version_string` / `ma_version`). Audio
  backend APIs are intentionally omitted and the 4 MB single-header
  implementation is not compiled into the runtime; see module header comment.
- **`std/rlights.d.pengu`** — curated subset of the vendored raylib-6 "RLG"
  lighting framework expressible with plain numbers/bools and the opaque
  `RLG_Context` handle (context, view position, parallax, light control,
  shadow knobs). Signatures passing raylib structs by value/ref are
  intentionally omitted (documented); no implementation archive is built.
- **`std/celeris.pengu`** — pure-PenguScript wrapper over `std/xxhash`
  (`hash32/hash64/hash3_64/hash3_128` + `*_seeded`). Documents that a
  PenguString _variable_ cannot yet be passed where a C byte pointer is
  expected (codegen emits the PenguString struct, not its buffer), so data is
  given as `ref to char` plus an explicit byte `length`.

### Build integration (`build_runtime.py` / `libpengu_stb.a`)

- `SINGLE_HEADER_NAMES` extended so `xxhash.h`, `uuid.h`, `minicoro.h`,
  `miniaudio.h`, `raygui.h`, `rlights.h`, `tinyfiledialogs.h` and
  `tinyfd_moredialogs.h` are staged into `build/include/`.
- `build_pengu_stb` now compiles each implementation unit to its own object
  (`std_c/wrappers_xxhash.c`, `wrappers_uuid.c`, `wrappers_minicoro.c`,
  `wrappers_raygui.c`, plus the real `tinyfiledialogs.c` /
  `tinyfd_moredialogs.c` sources) so archive members stay independently
  linkable. xxhash uses `XXH_STATIC_LINKING_ONLY` + `XXH_IMPLEMENTATION` (this
  vendored header requires both); minicoro uses `MINICORO_IMPL`.
- Link probes (C) prove the archive symbols: xxhash canonical vectors,
  uuid4 generation/parse-back, minicoro create/resume/yield/resume/destroy
  roundtrip, `tinyfd_version` string print.

### Tests & docs

- `tests/test_std_c_libs.py` — semantic checks of every new binding + celeris,
  PenguScript compile+run tests for `std.xxhash` and `std.celeris`, and
  C-level run probes for uuid/minicoro/tinyfiledialogs; each skips cleanly
  when the matching archive member is missing.
- README "Third-Party Acknowledgments & Credits" extended with the vendored
  `std_c/` libraries (origin URLs + license notes); CHEATSHEET §30 tables and
  examples updated; completeness-gap report appended to
  `scratch/std_c_support_plan.md`.

## [0.8.2] - Unreleased

### Stdlib enrichment (grounded scope)

- **`std/archivum` recursive helpers (pure PenguScript)**: new `copy_tree`
  (iterative, whole-directory copy) and `list_files_recursive` (returns every
  file below a root), built on the existing C primitives; verified end-to-end
  (`tests/test_archivum_tree.py`).
- **Bindings for the remaining `std_c/` headers**: `stb_image_resize2.d.pengu`
  (`insignia stbir_`) and `stb_herringbone_wang_tile.d.pengu` (`insignia stbh_`)
  added via `pengu bind`; duplicate omen values deduplicated; both pass
  `pengu check`. Every header in `std_c/` now has a `.d.pengu` binding in
  `std/`.
- **Scope note**: the broader single-header/std-module expansion (std\_/ folder,
  XLSX/YAML/TOML/WebSocket/audio/GUI modules, async FS/watch, etc.) cannot be
  implemented from this repository alone — those headers/libraries are not
  present. See the agent report for the concrete gap list and next steps.

## [0.8.1] - Unreleased

### Integrated external libraries (build_runtime.py)

- **New static libraries** produced by `build_runtime.py` into `build/lib/`
  (headers staged in `build/include/`, `--rebuild`-aware and idempotent):
  - `libsqlite3.a` — SQLite3 3.53.4 amalgamation (`-DSQLITE_THREADSAFE=0`,
    FTS5) with `sqlite3.h`/`sqlite3ext.h`.
  - `libraylib.a` — Raylib 6.0 desktop (`PLATFORM_DESKTOP`, OpenGL 3.3,
    GLFW via raylib's amalgamated `rglfw.c`) + full `src/` header set.
  - `libwebui.a` — WebUI 2.5.0-beta.3 installed from the official prebuilt
    mingw release asset (the in-repo sources target the MSVC UNICODE API set
    and do not compile with mingw); cached under `extern/`.
  - `libpengu_stb.a` — the STB single headers renamed to Latin in `std_c/`
    (`imago.h`, `scriptor.h`, `typis.h`, `pactum.h`, `datastructura.h`,
    `perlinum.h`) plus `nanosvg`/`nanosvgrast`, compiled once from
    `std_c/wrappers_stb.c` (`*_IMPLEMENTATION` units; `pactum` precedes
    `typis` for stb_truetype's rect-pack coupling).
- **Bindings**: `std/*.d.pengu` updated for the new names — `imago`,
  `scriptor`, `typis`, `pactum`, `datastructura`, `perlinum` (renamed and
  re-checked), `webui` include/links fixed (`include "webui.h"`, `link
"webui"`), `sqlite3` and `raylib` verified; every binding passes
  `pengu check`.
- **Linking**: `pengu_project.py` auto-links any new `.a` found in `build/lib`
  and adds the Windows UI platform libs (`-lopengl32 -lgdi32 -lole32 -luuid
-lshell32`).
- **Tests**: `tests/test_integrated_libs.py` — sqlite3 + imago end-to-end via
  the std bindings (compile+run), semantic checks of the remaining renamed
  bindings, WebUI and Raylib link checks (headless host: link-only).
- **Docs**: PENGU_BUILD §4, CHEATSHEET §30 "Integrated External Libraries",
  README notes updated.

## [0.8.0] - Unreleased

### `pengu bind` — C header to PenguScript bindings

- New CLI command `pengu bind <header.h>` that translates a C header into a
  `.d.pengu` declaration file (`pengu_bind.py`):
  - Preprocesses with the C preprocessor (retaining line markers so pycparser
    can attribute every node to its source file) using a vendored minimal stub
    include tree (`c_bind_stubs/`) — the Windows/SDK-guarded sections are
    excluded by undefining their guards (`-U_WIN32` etc.) so real-world headers
    stay parseable; `--no-cpp` and `--include-paths` are available for custom
    setups.
  - Maps C types to PenguScript (`size_t`→`size_t`, `bool`, fixed-width
    integers, `char*`/`const char*`→`ref to char`, `T*`→`ref to T`,
    `struct`→`rune`, `union`→`echo`, `enum`→`omen` with values, typedefs and
    function pointers → `alias … as ref to weave …`).
  - Emits, in order: `include`/`link` directives, numeric/string `#define`
    constants, type declarations (runes/echos/omens/aliases), the
    `insignia <prefix>` directive, then `declare` lines for every function
    (the prefix spelled by the header is stripped so `insignia` does not
    double it).
  - Attaches `##` documentation comments from the source header (Doxygen
    `/** … */`, `///`, `//`); `--no-comments` disables them.
  - `--prefix`, `--links`, `--output`, `--ignore`, `--include-paths` options.
- The generated file is a pure declaration file: the real C header stays
  `include`d, so no C structs/enums/prototypes are duplicated.
- **Tests**: `tests/test_pengu_bind.py` (type mapping, structs/enums/callbacks,
  constants, ignore patterns, insignia, comments) plus an end-to-end run over
  `CToPenguTest/webui.h` whose output passes the semantic checker.
- **Release packaging**: `make_release.py` installs `pycparser` in the build
  venv, adds `pycparser` (c_parser/c_lexer/c_ast/plyparser/ast_transforms) and
  `pengu_bind`/`pengu_lsp.*` to the PyInstaller hidden imports, and bundles
  `c_bind_stubs/` as an `--add-data` folder so `pengu bind` works inside the
  frozen `pengu.exe` (stub lookup also checks `sys._MEIPASS`).
  `requirements.txt` gained `pycparser>=2.21`.

## [0.7.1] - Unreleased

### Bug fix: module-member calls no longer degrade to `void`

- **Root cause**: `PenguChecker._resolve_call_target` resolved calls of the
  form `calling archivum.write_file` only by heuristically looking up the
  prefixed name (`archivum_write_file`) or the bare member name, and when both
  misses it silently returned `FnType(return_type=void)` for any member of an
  imported module. In typing flows where the bare member name is not present in
  the global registry (module collection registers imported members under the
  import-scope and prefixed names only), every typed call into an imported
  module inferred as `void` — producing spurious
  `E0020 "Returned value of type 'void' does not match weave return type ..."`
  diagnostics in the LSP / `pengu check`.
- **Fix** (`pengu_parser/pengu_infer.py`): module member calls now resolve
  against the import's `module_scope` first (the authoritative `FnType`
  signature), then fall back to the prefixed registry names; a genuinely
  missing member raises `E0004 "Module ... has no exported member ..."` instead
  of silently guessing `void`. The tolerant extern fallback is kept only for
  documents that actually declare C `include`s.
- **Tests**: `tests/test_lsp_return_types.py` covers typed returns
  (`bool`/`int`/`string`/`maybe int`/`void`) for same-file, forward-reference,
  stdlib-module-member, import-alias and local-module-member calls, plus a
  negative test asserting unknown members raise `E0004` (they previously
  produced the misleading void/E0020 behaviour).

## [0.7.0] - Unreleased

### CLI developer experience

- **Clearer C-compile errors**: `PenguBuilder.compile()` now raises a dedicated
  `CompileFailedError` carrying the exact compiler command, exit code and the
  full compiler stdout/stderr; the `pengu` CLI prints it formatted (no raw
  traceback) and exits with status 1.
- **`pengu check`**: parses and type-checks every module (respecting per-module
  `when main`) without generating any code — CI friendly. Reports one
  `file:line:col [CODE] message` per problem and exits non-zero on failure
  (`PenguBuilder.check_sources()`).
- **`pengu fmt`**: formats `.pengu` files/directories with the standard style
  (reuses the LSP formatter, extracted to `pengu_lsp/formatting.py`). Defaults
  to writing files; `--check` only reports and exits 1 when changes are needed;
  `--indent` / `--tabs` control indentation.
- **`pengu update`**: for every configured dependency, runs `git pull` (with the
  configured branch) and re-runs the dependency build script
  (`build.py` / `build.bat` / `build.sh` / `Makefile`); local copies are
  rebuilt in place (`_run_dependency_build` shared with `pengu add`).
- **`--cc` override** on `build`, `run`, `test` and `run <script>` wins over the
  compiler configured in `pengu.yaml`.
- **`--verbose`** on `build`/`run`/`test`/`check`/`update`/`fmt` prints the
  resolved module order, phase timings (semantic check / codegen), every C
  command executed and per-file progress.

### LSP developer experience

- **Contextual completion**: after `when` the editor suggests the compile-time
  variables `main`, `os`, `arch`, `compiler`, `defined(...)` (plus literals);
  after `as` / `into` it suggests every built-in type plus the project's runes,
  echos, omens, aliases, seals and generic runes; a `when` snippet was added.
- **Hover documentation fallback**: when a symbol carries no doc text yet,
  `##`/`#` doc comments directly above its declaration are extracted from the
  source file (`extract_doc_from_file`), so stdlib and cross-file definitions
  show documentation. Memory-size annotations were already present.
- **Code actions**: new `textDocument/codeAction` handler offering
  "Add missing import" when the cursor is on an undefined identifier — a cached
  symbol index (stdlib + project modules) maps the symbol to its module and the
  fix inserts `import …` at the top or after existing imports.
- Go-to-definition already resolves local symbols, imported-module members and
  stdlib files (e.g. `spark.println` → `std/spark.pengu`).

### Tests & docs

- New suites: `tests/test_cli_tools.py` (check/fmt/update/--cc/--verbose),
  `tests/test_lsp_context.py` (when/type completion contexts),
  `tests/test_lsp_code_actions.py` (add-missing-import) and
  `tests/test_lsp_hover_docs.py` (doc fallback). Full pytest suite green.
- CHEATSHEET §28 (CLI & LSP tooling) and README usage notes updated.

## [0.6.0] - Unreleased

### Standalone scripts (`when main`)

- **Compile-time `main` variable**: `main` is `true` when the module currently
  being compiled is the program entry point and `false` for every imported
  module. Combined with the existing `when` clauses it enables Python-style
  `if __name__ == "__main__"` behavior:

  ```pengu
  when main:
      weave main into int:
          calling saludar with "Mundo"
          return 0
  ```

- **Per-module environment**: the builder/checker/code generator now resolve the
  `main` flag separately for each source file (`pengu_comptime.CompileTimeEnv`
  gained `is_main`, `with_main()`, and `main` in `eval_comptime`; `PenguCodegen`
  gained `entry_main_mode`/`entry_file` with per-file flag application), so
  importing a module never activates its `when main:` blocks.
- **CLI**: `pengu run <archivo.pengu>` compiles and runs a standalone script
  with `main=true` (new `run_script` helper; artifacts under `build/`). Plain
  `pengu build`/`pengu run`/`pengu test` are unchanged and default to
  `main=false`; an explicit opt-in is available via `-D main` or `-D main=true`.
- **Reserved name**: declaring `var main` / `let main` / `static var main` /
  `const main` now reports `error[E0040]: 'main' is a reserved compile-time
variable`. Defining the entry function `weave main ...` is unaffected.
- **Tests**: `tests/test_when_main.py` (9 tests) verifies codegen emission/drop
  of `when main` blocks, the `E0040` guard, direct-run vs import behavior of a
  real module (`tests/fixtures_when_main/`), default-off project builds, and the
  `pengu run <file>` CLI path end-to-end.
- **Docs**: CHEATSHEET gained Appendix C ("v0.6 Standalone Scripts
  (`when main`)"), §27; README usage notes updated.

## [0.5.0] - 2026-03-01

### Compiler extensions (stdlib-unblocking)

- **`some expr`**: keyword constructing a present `maybe T`; the value is heap-copied (`pengu_sigil_alloc` + `memcpy`) so it outlives the expression. Types as `MaybeType(element=T)` and is never constant-folded.
- **`ord expr`** / **`chr expr`**: byte-level access without parentheses. `ord` returns the byte code of a single-character string (string-literal length validated); `chr` builds a single-character string from an int in 0-255 (constant range validated). `pengu_string_from_char` in the runtime now allocates a heap copy (fixes a dangling-stack-pointer bug that made runtime `chr` empty).
- **`insignia` primitive-method exemption**: `insignia pengu_` prefixes module-level weaves/declares only; `enchanting` methods on primitive/collection types (`string`, `list`, `map`, `slice`, `maybe`, `result`) keep their plain C names, so `string.substring` can never collide with the runtime `pengu_string_substring` primitive.

### Stdlib migrations

- **`scrolls` fully pure**: `lower`, `upper`, `is_alpha`, `is_digit`, `is_alnum` now implemented in PenguScript via `ord`/`chr`; the remaining C primitives (`pengu_string_upper/lower/is_alpha/is_digit/is_alnum`) were removed from `pengu_runtime.h`. `std/scrolls.pengu` carries `insignia pengu_`.
- **`cipher` Base64 pure**: `encode_base64`/`decode_base64`/`is_base64` implemented in PenguScript (byte loops with `ord`/`chr`, `some`/`maybe none` for decoding); C implementations (`PENGU_B64_CHARS`, `pengu_c_cipher_encode_base64`, `pengu_b64_char_val`, `pengu_c_cipher_decode_base64`) removed from the header.
- **`ledger` fully pure (CSV/TSV)**: `escape_field`, `parse_line`, `parse_csv`, `to_csv_string`, `detect_delimiter`, TSV variants and `read_csv`/`write_csv`/`read_tsv`/`write_tsv` (file I/O via `std.archivum`) are now implemented in PenguScript; the whole C ledger block (`pengu_c_ledger_escape_field`, `_parse_line`, `_parse_csv`, `_generate_csv`, `_read_file`, `_write_file`, `_detect_delimiter`) was removed from `pengu_runtime.h`.
- **`cipher` fully pure (Base64 + JSON)**: JSON `parse_json`/`stringify_json`/`pretty_json`/`parse_value`/`stringify_value` and file helpers now use a PenguScript tokenizer (whitespace/string/escape/raw-token scanning) over the new `pengu_map_keys_string` runtime helper; the entire C JSON block (`pengu_json_skip_ws`, `pengu_json_parse_str`, `pengu_json_parse_val_str`, `pengu_c_cipher_parse_json`, `_stringify_json`, `_parse_value`, `_stringify_value`, `_pretty_json`) was removed from `pengu_runtime.h`.
- **`compass` fully pure (paths)**: `join`/`join_all`, `basename`, `dirname`, `ext`, `stem`, `suffixes`, `has_ext`/`has_suffix`, `normalize`, `parent`, `split`, `is_absolute`/`is_relative`, `is_root`, `drive`, `separator`/`alt_separator`, `change_ext`, `add_ext`, `relative_to` and every `Path` method are now implemented in PenguScript (internal `cp_*` helpers over string slicing/`ord`/`chr`, with platform semantics selected by `when os == "windows"`); the entire C path section (`pengu_c_path_is_sep` ... `pengu_c_path_relative_to`, ~470 lines) was removed from `pengu_runtime.h`. `precis` (MIME by extension) and the `compass` stdlib test remain green.
- **Compiler fix**: codegen field access now prefers the live local-variable type over (possibly stale/leaked) global symbols when resolving `.value`/fields, so `maybe`-deref on locals whose names were previously seen as parameters elsewhere works reliably.
- **Tests**: `tests/test_feature_some_ord_chr.py` added; `test_runtime_h.py` updated to assert the runtime header no longer defines the migrated string/Base64/JSON/path helpers.

## [0.4.0] - 2026-02-20

### Standard Library Reorganization (runtime -> PenguScript)

- **String utilities migrated out of the C runtime**:
  - Removed the `scrolls_len` ... `scrolls_reverse` block from `pengu_runtime.h`; those 19 functions are no longer implemented in C.
  - `std/scrolls.pengu` now implements the string API in pure PenguScript: `contains`, `starts_with`, `ends_with`, `index_of`, `last_index_of`, `substring`, `char_at`, `trim`/`trim_start`/`trim_end`, `replace`, `replace_all` (now a true global replacement), `split`, `repeat`, `reverse` - built on compiler string slicing/indexing and the retained primitives (`pengu_string_substring`, `pengu_string_char_at`, concat, equality).
  - Only byte-level ASCII case conversion and classification (`lower`, `upper`, `is_alpha`, `is_digit`, `is_alnum`) remain as declared C primitives.
- **Compiler string operations** (enablers for the migration):
  - `s at a to b` on strings now emits `pengu_string_substring(...)` (was invalid C).
  - `s at i` on strings now emits `pengu_string_char_at(...)`.
  - `for c in s` iterates a string character by character (single-char `PenguString` values).
  - Fixed `judge` string pattern emission (`pengu_string_equals` -> `pengu_string_equal`).
- **Fixes found during migration**:
  - `pengu_symbols.py` now imports `ConceptType`/`SealType` (previously raised `NameError` at runtime).
  - `PenguCodegen._infer_node_type` now seeds the temporary symbol table correctly.
- **`arithmancy` integer helpers migrated**: `is_prime`, `gcd`, `lcm` removed from `pengu_runtime.h` and reimplemented in `std/arithmancy.pengu` (pure PenguScript, Euclid/6k±1 algorithms), removing their C definitions (`pengu_c_is_prime`/`pengu_c_gcd`/`pengu_c_lcm`).
- **Tests**: full pytest suite green (353 tests), including `tests_std/*.pengu` compiled with GCC via `test_stdlib.py`.
- **Documentation**: CHEATSHEET §23 now describes the stdlib architecture (PenguScript modules over declared C primitives / external-library backends).

## [0.3.0] - 2026-01-30

### Language & Compiler

- **Indexed iteration (`for i, item in collection`)**:
  - Added two-binding `for` loops: index (`int`, immutable) plus element, with `_` discard support (`for i, _ in col`, `for _, v in col`); the classic single-binding `for v in col` is unchanged.
  - Generated C keeps the requested index identifier as the loop counter (`for (int32_t i = 0; i < N; i++) { Elem v = (col)[i]; ... }`); element/index type checking handled in `_check_for_in_stmt`.
- **Map literals (`{ key: value, ... }`)**:
  - Added `{ "Alice": 100, "Bob": 90 }`, identifier keys (`host: "localhost"` -> string keys), and `and`/`,` separators.
  - Keys unify to `string`; values must share one type (int/float/string unification); empty maps require an explicit `as map of K to V` annotation; duplicate keys are rejected (`E0038`).
  - Codegen emits `pengu_map_new(sizeof(K), sizeof(V))` plus one `pengu_map_put` per entry.
- **Import aliases (`import path as name`)**:
  - Added `import std.spark as sp`; the alias becomes the module symbol (`kind="import"`); members resolve as `alias.export`. Aliases must not be `_` or collide with existing symbols (`E0036`). Generated C names are unaffected by the alias.
- **Compile-time conditionals (`when`)**:
  - Top-level, statement-level and expression (`when c then a else b`) forms; the inactive branch is syntax-checked but discarded (no codegen, no symbols).
  - New compile-time environment (`pengu_parser/pengu_comptime.py`) exposing `os`, `arch`, `compiler` and `defined(NAME)`, overridable via `-D NAME` / `-D os=linux` etc.
  - Non-constant `when` conditions are rejected (`E0039`); `when` blocks splice textually at statement level.
- **Integrated unit tests (`test ...:` blocks)**:
  - Added top-level `test "name":` / `test name:` blocks; semantically validated as `void` functions in every build; `.d.pengu` files reject them (`E0025`).
  - Normal builds ignore tests; `--test` emits `static void pengu_test_N(void)`, a `pengu_run_tests()` runner and a test `main`.
  - New CLI: `pengu test`, `pengu build --test`, `pengu run --test`.
- **String-valued omens**:
  - `omen Color with string:` auto-assigns each variant its name as a string value; explicit `Variant is "value"` strings are also supported.
  - Integer/string value mixing is rejected (`E0029`); payload variants are forbidden in string mode; string omens generate `#define Color_Red pengu_string_from_cstr("Red")` macros instead of enums, and variant references type as `string`.
- **Function-static variables (`static var`)**:
  - Added `static var` inside function bodies: mutable, initialized once, persists between calls; top-level, nested-block and array statics are rejected (`E0035`).
  - Codegen emits `static int32_t count = 0;` for constant scalars and a first-call `_initialized` guard for non-constant initializers.
- **`##` doc comments now lex**:
  - Single-line (`## text`), self-closed (`## text ##`) and multi-line (`##` ... `##`) documentation comments are supported by the lexer while preserving source line numbers.

### Tooling & Docs

- **`pengu doc`**: new subcommand generating a Markdown reference site (per-module pages + `index.md`) from `##` docs and inferred signatures (`pengu_doc.py`).
- **`-D` defines** on `pengu build`/`run`/`test` feed the compile-time `when` environment (plain `-D NAME` sets `defined(NAME)`; `-D os=...`, `-D arch=...`, `-D compiler=...` override context variables; project/`cc` config is honored too).
- **Tests**: `tests/test_feature_indexed_for.py`, `test_feature_map_literals.py`, `test_feature_import_alias.py`, `test_feature_when.py`, `test_feature_string_omens.py`, `test_feature_static_var.py`, `test_feature_tests.py`, `test_features_e2e.py` (GCC compile+run gates), `test_pengu_doc.py`.
- **CHEATSHEET.md**: new "25. Appendix A: v0.3 Language Extensions" section covering every feature with examples and generated C.
- **VSCode extension**: keywords (`when`, `test`, `static`, `omen ... with string`, `defined`) added to syntax highlighting; snippets for `test`, `when`, `static var`, map literal and `import ... as`; `pengu doc`/`pengu test` documented in the extension README.

## [Unreleased]

- **Type System Enhancements (`concept`, `bind`, `seal`, `ritual`, `where`)**:
  - **Concepts (Traits & Interfaces - `concept`)**:
    - Added `concept` declarations to define method contracts with required parameter and return types.
    - Supported both instance methods and static `ritual` methods within concepts.
    - Added generic concepts with type parameters (`concept Sharded shard T:`).
  - **Concept Implementations (`bind ... with ...`)**:
    - Added `bind Type with Concept:` syntax to associate concepts with runes and types.
    - Enforces full implementation of all concept methods; emits `UnimplementedConceptMethodError` (`E0031`) if any method is missing.
    - Validates method signatures and parameter counts; emits `ConceptMethodMismatchError` (`E0030`) on signature mismatch.
  - **Distinct Types & Nominal Newtypes (`seal ... as ...`)**:
    - Added `seal NominalName as UnderlyingType` declarations creating zero-overhead distinct types.
    - Enforces strict type separation to prevent accidental assignments across different seals or between seal and underlying type without explicit `to` cast; emits `SealTypeMismatchError` (`E0035`).
    - Generates corresponding C `typedef UnderlyingType NominalName;` in `bundle.c`.
  - **Static & Factory Methods (`ritual`)**:
    - Added `ritual` modifier for methods declared inside `enchanting` blocks or `concept`/`bind` blocks.
    - Ritual methods do not receive a `self` instance parameter and are called statically on the type name (e.g. `calling Vec2.zero`).
    - Enforces safety: prevents accessing `self` inside a ritual method (`InvalidRitualSelfAccessError` / `E0033`) and prevents calling a ritual method on an instance (`InvalidRitualCallError` / `E0034`).
    - Codegen emits clean C functions without `self` pointer parameters.
  - **Generic Constraints (`where`)**:
    - Added `where <Param>: <Concept>` clause to generic functions, methods, runes, and concepts.
    - Validates that generic type arguments satisfy all declared concept bounds upon specialization/monomorphization; emits `ConceptBoundNotSatisfiedError` (`E0032`) if unfulfilled.
    - Allows method calls on generic type parameters (`calling item.print_me`) backed by concept bounds.
  - **Test Suite & Documentation**:
    - Added comprehensive unit and semantic tests in `tests/test_type_system_enhancements.py`.
    - Documented all 5 features with PenguScript examples and translated C code in `CHEATSHEET.md` Sections 8, 10, 11, and 13.

- **Null Pointer Literal (`null`)**:
  - Added the `null` literal for safe null pointer representation in C FFI interoperability and raw references.
  - Implemented `NullType` (and `NULL_TYPE` singleton), compatible strictly with reference types (`ref to T`), `opaque` types, and `any`.
  - Type safety rules: forbids assigning `null` to value types (`int`, `string`, `bool`, `rune`, etc.), emitting `TypeMismatchError` (`E0005`).
  - Requires explicit type annotations on declarations initialized with `null` (e.g. `var ptr as ref to int is null`), emitting `E0014` if omitted.
  - Supports equality and inequality comparisons (`==`, `!=`) against references, opaque handles, and `null`, rejecting non-pointer comparisons and ordering comparisons (`<`, `<=`, `>`, `>=`).
  - Memory safety: forbids taking address of `null` (`sigil of null`), emitting `E0008`.
  - Translates `null` expressions to standard C `NULL` in generated `bundle.c`.
  - Comprehensive unit test suite in `tests/test_null.py`.
  - Updated TextMate syntax highlighting for VSCode and documented in `CHEATSHEET.md` Section 20.

- **Explicit Values & Auto-Increment for `omen` Enums**:
  - Added support for assigning compile-time integer constant values to simple `omen` enum variants using `Variant is <expr>`.
  - Added automatic increment rules: default starts at `0` for unassigned first variants, and unassigned variants following an explicit value continue with `previous + 1`.
  - Added semantic validation enforcing integer types (evaluated with `ConstFolder`) and emitting compile error `E0029` (`InvalidOmenConstantValueError`) for non-integer or non-constant values.
  - Added duplicate value detection across all variants in an `omen`, emitting compile error `E0027` (`DuplicateOmenValueError`).
  - Added payload restriction forbidding `is <expr>` assignments on algebraic variants with payload (`with`), emitting compile error `E0028` (`InvalidOmenPayloadValueError`).
  - Updated C code generator to emit explicit `= <val>` expressions in `typedef enum Name { ... } Name;` C declarations.
  - Comprehensive unit test suite in `tests/test_omen_values.py`.
  - Documented in `CHEATSHEET.md` Section 9.

- **Insignia Module Prefix Directive (`insignia`)**:
  - Added the `insignia <PREFIX>` top-level directive in modules and declaration files to define a global C identifier prefix for subsequent declarations.
  - Automatically prepends prefix to generated C function names (`declare`, `weave`), struct/union/enum types (`rune`, `echo`, `omen`, `alias`), constants (`const`), and `enchanting` methods.
  - Keeps PenguScript call syntax clean without prefix (e.g. `webui.new_window` translates to `webui_new_window()`).
  - Position-dependent: declarations prior to `insignia` remain unprefixed.
  - Restricts modules to at most one `insignia` directive, emitting compile error `E0026` (`MultipleInsigniaError`) on duplicates.
  - Comprehensive unit and integration test suite in `tests/test_insignia.py`.
  - Documented in `CHEATSHEET.md` Section 3.

- **Declaration Files Support (`.d.pengu`)**:
  - Added support for TypeScript-like declaration files (`.d.pengu`) containing type definitions (`rune`, `echo`, `omen`, `alias`, `seal`, `concept`), linker flags (`link`), C includes (`include`), and external function declarations (`declare`).
  - Strict validation forbidding function implementation bodies (`weave`): emits compile error `E0025` (`"Implementation body not allowed in declaration file (.d.pengu)"`).
  - Import resolution (`find_module_path`) resolves `.d.pengu` files when importing modules, with priority given to `.pengu` implementation files when both exist.
  - Code generator suppresses C code emission (forward declarations, struct/union/enum/typedef definitions, `#define` constants, and `declare` prototypes) for declarations originating in `.d.pengu` files to prevent redefinition conflicts with included native C headers, while preserving full symbol and type information for semantic checking, LSP, and function call translation.
  - Comprehensive unit and integration test suite in `tests/test_declaration_files.py`.
  - Documented `.d.pengu` declaration files in `CHEATSHEET.md`.

- **Context-Aware String Literals for `ref to char` (`const char*`)**:
  - String literals assigned to `ref to char` (`const char*` / `char*`) variables, struct fields, or passed to function parameters expecting `ref to char` are now emitted directly as C string literals (`"..."`) without wrapping in `pengu_string_from_cstr`.
  - Type inference and semantic checker validate string literals against expected `ref to char` types.
  - String interpolation (`{expr}`) within string literals assigned or passed where `ref to char` is expected raises a compile-time `SemanticError`.
  - Full support for `ref to char` fields in struct/rune initializers (`with ...`).
  - Unit and integration tests in `tests/test_ref_char_literals.py`.
