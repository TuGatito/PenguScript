# Auditoría: WebAssembly, Emscripten y Web para PenguScript

> **Documento temporal de auditoría.** No forma parte de la documentación
> publicada ni del release. Su objetivo es decidir el alcance antes de tocar
> código.
>
> - **Repositorio:** `PenguScript` (compilador auto-hospedado `psc`)
> - **Versión auditada:** `0.15.0` (`VERSION`, `pengu.toml`, `psc 0.15.0 (F12)`)
> - **Fecha:** 2026-10-29
> - **Entorno verificado:** Linux x86_64, `gcc`, Emscripten `6.0.13-git`
>   (`/usr/lib/emscripten/emcc`), `emar`, Node.js `26.12.1`
> - **Estado:** auditoría completa; **MVP F0–F4 + Track B F5–F6 implementados en 0.17.0**. F7–F9 quedan como plan.

---

## Índice

- [0. Resumen ejecutivo](#0-resumen-ejecutivo)
- [1. Objetivo, alcance y terminología](#1-objetivo-alcance-y-terminología)
- [2. Metodología y evidencia](#2-metodología-y-evidencia)
- [3. Inventario: qué existe, qué falta y qué está roto](#3-inventario-qué-existe-qué-falta-y-qué-está-roto)
- [4. Qué se perdió exactamente y de dónde recuperarlo](#4-qué-se-perdió-exactamente-y-de-dónde-recuperarlo)
- [5. Arquitectura actual y puntos de contacto con el target](#5-arquitectura-actual-y-puntos-de-contacto-con-el-target)
- [6. Auditoría detallada por capa](#6-auditoría-detallada-por-capa)
- [7. Hallazgos priorizados](#7-hallazgos-priorizados)
- [8. Evidencia experimental (verificada)](#8-evidencia-experimental-verificada)
- [9. Diseño propuesto](#9-diseño-propuesto)
- [10. Plan por fases](#10-plan-por-fases)
- [11. Decisiones que debes tomar (con recomendación)](#11-decisiones-que-debes-tomar-con-recomendación)
- [12. Riesgos y mitigaciones](#12-riesgos-y-mitigaciones)
- [13. Matriz de pruebas](#13-matriz-de-pruebas)
- [14. Criterios de aceptación](#14-criterios-de-aceptación)
- [15. Anexos](#15-anexos)
- [16. Próximo paso recomendado](#16-próximo-paso-recomendado)

---

## 0. Resumen ejecutivo

### 0.1. Diagnóstico en una frase

> **Actualización 0.17.0:** el MVP F0–F4 y los módulos web `std.web.*`
> (Track B, F5–F6) ya están implementados. Este documento conserva el
> diagnóstico y el plan; el estado real está en `CHANGELOG.md`.

El compilador **ya no sabe compilar a wasm**: el flag `--target` existe en el
parser de argumentos pero el driver lo rechaza explícitamente, el modelo de
target no existe, el codegen no entiende `when wasm`, y la cadena de runtime,
tests, CI, shell HTML y documentación específica de wasm fue eliminada en la
migración al compilador auto-hospedado (commit `4cdce10`).

### 0.2. Lo que sí sobrevivió

- `std/web.pengu` con el puente Emscripten (`console_*`, main loop, `now_ms`,
  `eval_js`, timers) y sus stubs nativos.
- El campo `SemaOptions.wasm_target` y la evaluación de `when wasm` en sema
  (parcial, ver H2/H3).
- Los guards `PENGU_EMSCRIPTEN` del runtime C (`exec`/`spawn` devuelven `-1`).
- `tests/wasm/filum_stress.pengu`, `tests/wasm/filum_handles_leakcheck.c` y
  `tests/wasm/std_web_smoke.pengu` (huérfanos: ningún runner los ejecuta).
- Secciones de `LANGUAGE.md` sobre `wasm`/`wasm_target` y
  `wasm32-unknown-emscripten` (desactualizadas: hablan de `pengu` y Python).
- La documentación histórica `docs/WASM.md` y `pengu_wasm_shell.html` son
  recuperables del historial (commit `20136f6`).
- El runtime C y el C generado **son compilables con `emcc` hoy**: lo he
  verificado a mano (ver §8). El problema es de driver, comptime y producto,
  no del backend C.

### 0.3. Los cinco bloqueadores reales

1. **Codegen de `when` top-level roto para ramas con más de un statement.**
   Solo recoge el primer hijo de la rama y malinterpreta el `else`
   (`src/psc/codegen/catalog.pengu:690-720`). Esto rompe `std/web.pengu` incluso
   en nativo y rompería cualquier `std.js`/`std.dom` que use `when wasm:` con
   varias declaraciones.
2. **Codegen no conoce `wasm`, `wasm_target`, `compiler`, `main` ni `debug`**,
   y sus errores de comptime son silenciosos
   (`src/psc/codegen/comptime.pengu:84-173`,
   `src/psc/codegen/api.pengu:36-53`).
3. **Sema y codegen no comparten el mismo entorno de compilación.** `when
   wasm_target == "emscripten"`, `when compiler == "emcc"`, `when main:` y
   `when zzz:` responden distinto en cada fase (H3).
4. **No existe modelo de target ni cadena de toolchain wasm**: `--target` se
   rechaza, no hay búsqueda de `build/wasm/lib`, no se detecta `emcc`/`emar`, y
   el manifiesto `cc = "gcc"` ganaría sobre `emcc` (H4/H5/H6).
5. **No hay interoperabilidad JavaScript real**: solo `eval_js` sin valor de
   retorno. No hay DOM, `fetch`, WebSocket, Canvas, promesas, callbacks ni
   manejo de errores JS. Sin esto, PenguScript en la web queda limitado a
   programas de consola o a bindings pesados tipo Raylib (H12).

### 0.4. Recomendación

Hacerlo en dos tracks:

- **Track A — restaurar el target wasm (MVP, ~3-4 semanas):** target model,
  toolchain/runtime wasm, arreglo de comptime/codegen, portabilidad de `std`,
  `std.web` funcionando, build/run/test con Node, tests y CI.
- **Track B — soporte Web/ECMAScript completo (~6-9 semanas más):**
  `std.js` genérico con handles, callbacks y errores; `std.dom`, `std.fetch`,
  `std.websocket`, `std.canvas2d`, `std.storage`; plantilla de proyecto web,
  shell, assets, `psc serve` opcional y pruebas de navegador.

El diseño recomendado para JS es **`--js-library` + un `std.js` de handles
opacos**, no `EM_ASM`. `EM_ASM` está prohibido por Emscripten bajo `-std=c11`
(verificado con `emcc 6.0.13`, §8.8), y cambiar a `-std=gnu11` rompería la
política C11 del proyecto. `--js-library` funciona en C11, permite callbacks
C↔JS y no obliga a `-sASYNCIFY`.

### 0.5. Decisiones que bloquean el arranque (detalle en §11)

| # | Decisión | Recomendación |
|---|---|---|
| D1 | ¿Solo Emscripten o también WASI? | Solo Emscripten; WASI se rechaza |
| D2 | ¿`--target wasm` o `--wasm`? | `--target wasm` + triple completo |
| D3 | ¿`when os` ve host o target? | Target (`emscripten`) |
| D4 | ¿`arch` en wasm? | `wasm32` |
| D5 | ¿Runtime wasm precompilado o on-demand? | Script on-demand + doctor; opcional prebuilt pinneado |
| D6 | ¿Cómo se hace JS interop? | `--js-library` + `std.js` de handles |
| D7 | ¿Async? | Callbacks primero; JSPI opcional; sin Asyncify por defecto |
| D8 | ¿Qué módulos web van en el repo? | `std.js`/`std.dom`/`std.fetch`/`std.websocket`/`std.canvas2d`; gráficos pesados como satélites |
| D9 | ¿Threads? | `-pthread` solo si `std.filum`; COOP/COEP documentado |

---

## 1. Objetivo, alcance y terminología

### 1.1. Petición original

> «Se ha perdido la posibilidad de compilar a wasm usando el Emscripten
> instalado en el PC. Debe poder compilarse con un nuevo argumento. Antes
> teníamos `when wasm`. Haz una auditoría completa para ver cómo dar soporte
> completo a ECMAScript para compilar a wasm. Para poder usar PenguScript en la
> web, no solo compilar proyectos de Raylib o derivados a wasm.»

### 1.2. Terminología: Emscripten ≠ ECMAScript

En la petición se mezclan dos términos. En esta auditoría se separan:

- **Emscripten** (`emcc`/`emar`): toolchain que compila C a wasm. Es lo que
  hay instalado en el PC y lo que hay que restaurar.
- **ECMAScript / JavaScript**: lenguaje del navegador (y de Node.js). Es la
  capa de interoperabilidad que hace que un programa PenguScript pueda usar
  DOM, `fetch`, WebSocket, Canvas, promesas, etc.
- **Node.js**: runtime ECMAScript que el CLI usa para ejecutar `app.js` en
  tests y en `psc run` sin navegador.

El soporte «completo» exige las tres piezas: **toolchain Emscripten**,
**runtime/STD portables** e **interoperabilidad JS**.

### 1.3. Dentro del alcance

- `wasm32-unknown-emscripten` (alias `wasm`, `wasm32`, `emscripten`).
- `psc build`, `psc run`, `psc test`, `psc check`, `psc emit-c` y
  `psc expand` con target wasm.
- Runtime `libpengu_runtime.a` para wasm y su build sin Python.
- Portabilidad de la stdlib y diagnóstico claro de módulos no soportados.
- `std.web` y una capa `std.js` + módulos Web.
- Plantilla de proyecto web, shell HTML, assets, runner Node y CI.
- Documentación y release.

### 1.4. Fuera del alcance (por ahora)

- **WASI** (`wasm32-wasi`): se reconoce y se rechaza con mensaje claro. No se
  implementa en esta fase.
- **Compilar `psc` a wasm** para un playground en el navegador: requiere
  filesystem, subprocess, libclang y red; es un proyecto aparte. Un playground
  serio se hace con compilación en servidor.
- **WebGPU**, **WebGL completo**, **SDL/raylib**: bindings satélite o fase
  posterior; no son el núcleo del soporte web.
- **WASM SIMD**, **WASI threads**, **shared libraries wasm** (`SIDE_MODULE`):
  fuera del MVP; `shared` se rechaza.

---

## 2. Metodología y evidencia

### 2.1. Qué se ha inspeccionado

1. **Código actual** del compilador: CLI, driver, manifest, paths, toolchain,
   sema, codegen, cache, comandos `build`/`run`/`test`/`eval`/`time`/`watch`/
   `dev`/`doctor`/`assets`/`init`.
2. **Historial git** completo: commits de wasm (`18c7044`, `20136f6`), la
   migración F11 (`4cdce10`) y los archivos eliminados.
3. **Documentación histórica** `docs/WASM.md` (511 líneas) recuperada de
   `20136f6`, `pengu_wasm_shell.html` (132 líneas) y el código Python
   `pengu_project.py`/`build_runtime.py` (solo como especificación de
   comportamiento).
4. **Runtime C** (`pengu_runtime.h`, `runtime/*.c`), guards de Emscripten y
   dependencias de plataforma.
5. **Stdlib** módulo a módulo: includes C, `link`, `ldflag`, uso de POSIX,
   libs nativas y patrones `when os`.
6. **Tests, CI, packaging y docs** actuales.
7. **Experimentos reales** con `emcc`/`emar`/`node` para validar hipótesis
   (§8).

### 2.2. Cómo se ha clasificado cada hallazgo

- **VERIFICADO:** reproducido con un comando en este entorno.
- **INFERIDO:** leído en código/historial, sin ejecución end-to-end.
- **PENDIENTE:** requiere decisión o prueba adicional.

### 2.3. Limitaciones de esta auditoría

- Las APIs DOM/Canvas se probaron contra un DOM falso en Node y se
  compilaron para wasm, pero no se ha hecho una prueba visual en navegador
  real.
- La matriz de stdlib no es exhaustiva: se han probado los módulos de mayor
  riesgo y se ha inferido el resto por sus includes/dependencias.
- El runtime wasm del §8 se construyó a mano, no con un script del repo; sirve
  para demostrar viabilidad, no para afirmar que el driver actual funcione.
- No se ha auditado el ABI wasm32 con un test de layout en ejecución; se marca
  como riesgo R7.

---

## 3. Inventario: qué existe, qué falta y qué está roto

| Área | Estado actual | Evidencia |
|---|---|---|
| Flag `--target` | **Rechazado** con «not available until F11» | `src/psc/cmd/build.pengu:198-203` |
| Modelo de target | **No existe** | no hay `Target`/triple parser en `src/psc/driver` |
| `SemaOptions.wasm_target` | **Campo huérfano**: nadie lo asigna | `src/psc/sema/options.pengu:32-33,62` |
| `when wasm` en sema | Parcial: funciona si se asigna el campo o `-D wasm` | `src/psc/sema/check/collect.pengu:315` |
| `when wasm` en codegen | **Roto**: no se evalúa; rama descartada en silencio | `src/psc/codegen/comptime.pengu:84-173` |
| `when` top-level con varias declaraciones | **Roto**: solo recoge la primera | `src/psc/codegen/catalog.pengu:690-720` |
| `when` con identificador desconocido | **Silencioso** en sema; error no propagado en codegen | ver H3 |
| `std/web.pengu` | Presente, pero **no compila ni en nativo** por H1 | §8.7 |
| Runtime C con guards Emscripten | Presente y compila con `emcc` | `pengu_runtime.h:311,3245`; §8.2 |
| Runtime wasm (`build/wasm/lib`) | **No se genera**; no hay script sin Python | `tools/build_runtime.sh` solo host |
| Búsqueda de runtime wasm | **No existe** | `src/psc/driver/paths.pengu:96-218` |
| Detección de `emcc`/`emar` | **No existe**; elige gcc/clang/tcc | `src/psc/driver/toolchain.pengu:98-170` |
| `cc` del manifiesto | **Gana sobre emcc** si el proyecto trae `cc = "gcc"` | `psc init` genera `cc = "gcc"` |
| `--target` en `run`/`test` | **No existe** | `src/psc/cmd/build.pengu:292-440`, `src/psc/cmd/test.pengu:105-140` |
| Runner Node | **No existe**; ejecuta el artefacto directamente | mismos archivos |
| Cache de artefactos | **No target-aware** y **monoarchivo** | `src/psc/cache/cache.pengu:60-110` |
| `ldflag` de módulo | **Se recoge en sema pero se ignora en driver** | `collect.pengu:374-392`; driver no lo lee |
| `build.ldflags` del manifiesto | **Se parsea pero se ignora** | `manifest.pengu:162`; driver no lo usa |
| `PENGU_CFLAGS`/`PENGU_LDFLAGS` | **No soportados** | sin referencias en `src/` |
| `PENGU_RUNTIME_CROSS` | **No soportado** | `paths.pengu` solo `PENGU_LIB_DIR` |
| `psc doctor --target` | **No existe** | `src/psc/cmd/doctor.pengu` |
| Assets `.incbin` en wasm | **Falla**: el ensamblador wasm rechaza `.incbin` | §8.9; `src/psc/cmd/assets.pengu:397-410` |
| `std.net` en wasm | Compila si están todos los headers, pero **Node exige `ws`** y el navegador no tiene sockets BSD | §8.5 |
| `std.dynlib`/`std.ffi_call`/`std.secrets`/`std.petitio` | **No enlazan en wasm** (libs nativas) | §8.6 |
| `std.rites.run_capture` | Bug de codegen preexistente (`.len` sobre puntero) | §8.4 |
| Tests wasm | **Huérfanos**; `tests/run.sh` no los ejecuta | `tests/run.sh` |
| CI wasm | **Eliminado**; solo build/vscode/release | `.github/workflows/ci.yml` |
| `docs/WASM.md` | **Eliminado**; recuperable de `20136f6` | `/tmp/WASM_old.md` |
| `pengu_wasm_shell.html` | **Eliminado**; recuperable | `git show 20136f6:pengu_wasm_shell.html` |
| `build_runtime.py --target emscripten` | **Eliminado** con Python | commit `4cdce10` |
| Interop JS (DOM/fetch/WebSocket/Canvas) | **No existe**; solo `eval_js` sin retorno | `std/web.pengu` |
| Plantilla de proyecto web | **No existe**: `exe`, `cli`, `pengu-lib`, `cbind` | `src/psc/cmd/init.pengu:20-33` |
| Packaging wasm | **No incluye** runtime wasm, shell ni JS library | `tools/package_ci.sh` |

---

## 4. Qué se perdió exactamente y de dónde recuperarlo

### 4.1. Cronología

| Commit | Fecha | Qué aportó / quitó |
|---|---|---|
| `18c7044` | 2026-10-13 | `wasm32-unknown-emscripten`, `std.web`, `build_runtime.py --target emscripten`, shell HTML, docs/WASM.md, tests wasm, CI wasm |
| `20136f6` | 2026-10-21 | Fixes de wasm: `emcc` en comptime, `ldflag`, shell, runtime dirs, tests |
| `4cdce10` | 2026-10-27 | Migración F11: elimina el compilador Python y, con él, **todo el wasm**: `build_runtime.py`, `pengu_project.py` (target), `docs/WASM.md`, `pengu_wasm_shell.html`, `tests/wasm/test_*.py`, `tests/compiler/test_comptime_wasm.py`, `make_release.py`, job de CI |

### 4.2. Inventario de archivos perdidos (recuperables del historial)

```text
docs/WASM.md                                  (511 líneas, commit 20136f6)
pengu_wasm_shell.html                         (132 líneas, commit 20136f6)
build_runtime.py                              (584 líneas, commit 20136f6)
pengu_project.py                              (8262 líneas; solo la parte target/wasm)
tests/wasm/test_wasm_target.py                (666 líneas)
tests/wasm/test_std_web.py                    (295 líneas)
tests/wasm/conftest.py                        (211 líneas)
tests/compiler/test_comptime_wasm.py          (218 líneas)
tests/build/test_wasm_lib_dirs.py
pengu_parser/pengu_comptime.py                (lógica `wasm`/`wasm_target`)
pengu_parser/pengu_checker.py / pengu_codegen (folding de `when`)
```

Los fixtures que sí sobrevivieron:

```text
tests/wasm/filum_stress.pengu
tests/wasm/filum_handles_leakcheck.c
tests/wasm/std_web_smoke.pengu
```

### 4.3. Qué hacía el wasm antiguo (especificación de paridad)

Resumen de `docs/WASM.md` y `pengu_project.py`:

- `--target wasm32-unknown-emscripten` (alias `wasm`, `wasm32`, `emscripten`)
  en `build`, `run`, `test`; `--target wasm32-wasi` se reconocía y se rechazaba.
- `build_runtime.py --target emscripten` producía
  `build/wasm/lib/libpengu_runtime.a` y `build/wasm/include/pengu_runtime.h`,
  separado de `build/lib`.
- Búsqueda wasm disjunta: `PENGU_LIB_DIR` (override), `PENGU_RUNTIME_CROSS/lib`
  y `build/wasm/lib`; nunca `build/lib`.
- `emcc` auto-detectado; si falta, mensaje con instrucciones de emsdk.
- `emar` para archivos estáticos (no `ar`).
- Artefactos: `exe` → `app.html` + `app.js` + `app.wasm`; `static` → `app.a`;
  `obj` → `app.o`; `c` → `bundle.c`; `shared` → **rechazado**.
- Flags de link: `-sWASM=1`, `-sALLOW_MEMORY_GROWTH=1`, `-sEXIT_RUNTIME=0`,
  `-sINITIAL_MEMORY=16MB`, `-sSTACK_SIZE=1MB`,
  `-sEXPORTED_RUNTIME_METHODS=ccall,cwrap,FS`,
  `-sENVIRONMENT=web,node,worker`, `--shell-file`.
- `-pthread` **solo si el programa importa `std.filum`**, más
  `-sPTHREAD_POOL_SIZE=4`.
- `std.web` con `when wasm:` y stubs nativos.
- Comptime: `wasm` (bool), `wasm_target` (`""`/`emscripten`/`wasi`),
  `defined(wasm)`, `compiler == "emcc"`; `os` veía `emscripten`.
- `psc run --target wasm` ejecutaba `node app.js`; sin Node, imprimía la ruta
  del `.html`.
- Tests: 666 líneas de target, 295 de `std.web`, 218 de comptime, stress de
  filum y leakcheck con `--wrap`.
- Shell HTML propio (`--shell-file`) con terminal, progreso y canvas oculto.
- Docs: `docs/WASM.md` con instalación, artefactos, threads, `std.web`,
  limitaciones, troubleshooting.

---

## 5. Arquitectura actual y puntos de contacto con el target

### 5.1. Pipeline

```text
argv
  └─ src/main.pengu (dispatch)
      └─ psc.cmd.build / test / run / eval / ...
          └─ psc.driver.build (BuildOptions, manifest, paths, toolchain)
              ├─ psc.sema.api.check_file  (SemaOptions)
              │   └─ sema/check/collect (when)
              ├─ psc.codegen.api.generate_c (CgOptions)
              │   └─ codegen/comptime, catalog, bundle
              └─ cc / ar / runner
```

### 5.2. Dónde tendría que entrar el target

| Capa | Archivo | Cambio |
|---|---|---|
| CLI | `src/psc/cmd/build.pengu`, `cmd/test.pengu`, `main.pengu` | aceptar `--target`, no rechazarlo |
| Opciones | `src/psc/driver/build.pengu` (`BuildOptions`) | `target`, `wasm_target`, `target_triple` |
| Manifiesto | `src/psc/driver/manifest.pengu` | `[build] target` |
| Target | nuevo `src/psc/driver/target.pengu` | parseo, alias, validación |
| Sema | `src/psc/sema/options.pengu` | `wasm`, `wasm_target`, `target_os`, `compiler` |
| Codegen | `src/psc/codegen/options.pengu` | mismos campos + `is_main`, `debug` |
| Comptime | `src/psc/codegen/comptime.pengu`, `sema/check/collect.pengu` | resolución unificada |
| `when` top-level | `src/psc/codegen/catalog.pengu` | recorrer **todos** los hijos de la rama |
| Paths | `src/psc/driver/paths.pengu` | búsqueda wasm disjunta |
| Toolchain | `src/psc/driver/toolchain.pengu` | `emcc`/`emar`, flags wasm, `ldflags` |
| Driver | `src/psc/driver/build.pengu` | link wasm, artefactos, runner, cache |
| Cache | `src/psc/cache/cache.pengu` | clave con target; multiarchivo |
| Runner | nuevo `src/psc/driver/runner.pengu` | ejecutar binario o `node app.js` |
| Doctor | `src/psc/cmd/doctor.pengu` | `--target wasm` |
| Runtime build | nuevo `tools/build_runtime_wasm.sh` | `emcc`/`emar` |
| Assets | `src/psc/cmd/assets.pengu` | array para wasm |
| Tests | nuevo `tests/wasm/run.sh` | sin Python |
| CI | `.github/workflows/ci.yml` | job wasm |
| Docs | `docs/WASM.md`, `docs/WEB.md`, `LANGUAGE.md` | actualizar |
| Release | `tools/package_ci.sh` | shell, JS library, runtime |

---

## 6. Auditoría detallada por capa

### 6.1. CLI (`src/main.pengu`, `cmd/*`)

- `psc build` ya declara `--target` como flag con valor
  (`src/psc/cmd/build.pengu:114`) pero lo rechaza en `:198-203`.
  **No hay que inventar el parser**, solo quitar el rechazo y propagar.
- `psc run` tiene un parser manual propio (`src/psc/cmd/build.pengu:292-440`)
  que no conoce `--target`, ni `--profile value` (solo `--profile=value`), ni
  `--out`. Duplica la lógica de `build`; conviene refactorizarlo a
  `psc.cli.args` antes de añadir target, o el target se implementará dos veces.
- `psc test` usa `cliargs` pero no declara `--target`
  (`src/psc/cmd/test.pengu:70-100`).
- `psc check` no acepta `-D` ni `--target` (`src/main.pengu:377-479`), así que
  no se puede validar una rama `when wasm` sin compilar.
- `psc emit-c` no acepta `-D` (solo `--target-os`, `--target-arch`,
  `--target-compiler`). Es la herramienta natural para depurar codegen wasm;
  debería aceptar `--target wasm` y `-D`.
- `psc expand` tampoco acepta `--target`; es útil para inspeccionar el bundle
  wasm sin `emcc`.
- `psc eval`, `psc time`, `psc watch`, `psc benchmark` compilan y ejecutan
  directamente; si se les pasa target wasm habría que ejecutar con Node.
  Recomendación: soportar target en `build/run/test/check/emit-c/expand` en el
  MVP; el resto, fase posterior (o rechazo explícito).
- `psc init` no tiene plantilla web (`src/psc/cmd/init.pengu:20-33`).
- `psc doctor` no comprueba `emcc`, `emar`, `node` ni runtime wasm.

### 6.2. Driver (`src/psc/driver/build.pengu`)

- `BuildOptions` no tiene target (`:34-59`).
- El flujo `build` no distingue target: resuelve `toolchain` con
  `o.cc`/manifiesto (`:270`), enlaza con `-lm -pthread -ldl` para todo no
  Windows (`:649-656`), y usa `ar` para `static` (`:691-698`).
- Para wasm:
  - **`-pthread` no debe añadirse siempre**: solo si el programa importa
    `std.filum` (como hacía el compilador Python). Si se añade siempre,
    cualquier programa wasm exige `SharedArrayBuffer`/COOP/COEP y crece.
  - **`-ldl` no aplica**; `std.dynlib` no existe en wasm.
  - **`-lm` sí aplica**.
  - **`ar` debe ser `emar`**.
  - **`shared` debe rechazarse** con mensaje accionable.
  - **`-o app.html`** debe activar la salida HTML+JS+WASM.
- El nombre del artefacto no contempla wasm (`:499-519`); `exe` produce
  `build/<name>` sin `.html`.
- La caché de artefacto (`:526-606`) copia **un solo archivo** y hace
  `chmod +x`; un `.html` wasm necesita `.js`/`.wasm` hermanos. Si se cachea
  solo el HTML, `psc run` falla. **Desactivar cache de artefacto para wasm en
  el MVP**.
- La clave de caché no incluye target (`:534-575`): un build nativo y uno wasm
  del mismo fuente podrían colisionar. **Añadir target/triple a la clave**.
- `-D` se propaga a sema y codegen (`:296-302`, `:431-440`), pero no a
  `psc check`/`emit-c`.
- El driver no lee `man.ldflags` ni `sr.program->symbols.ldflags`, aunque el
  manifiesto y sema los recogen. Para wasm esto es crítico:
  `ldflag "-sUSE_GLFW=3"`, `-sFETCH=1`, `-lwebsocket.js`, etc.
- El driver no soporta `PENGU_CFLAGS`/`PENGU_LDFLAGS`, que el wasm antiguo
  usaba para ASan/`EXIT_RUNTIME=1`/flags de usuario.
- `psc run` y `psc test` ejecutan `r.artifact` directamente; para wasm hay que
  ejecutar `node <artefacto>.js`. No hay módulo `runner`.
- Si el proyecto trae `cc = "gcc"` (lo genera `psc init`), el driver lo usa
  antes que `emcc`; un build wasm intentaría gcc. **El target debe mandar sobre
  el `cc` del manifiesto** (el `--cc` explícito sigue ganando).

### 6.3. Paths (`src/psc/driver/paths.pengu`)

- Solo busca `libpengu_runtime.a` host: `PENGU_RUNTIME_ARCHIVE`,
  `PENGU_LIB_DIR`, `$PENGU_HOME/lib`, `build/lib`, `runtime/lib`.
- No conoce `build/wasm/lib` ni `PENGU_RUNTIME_CROSS`.
- No distingue include wasm (`build/wasm/include`) del host.
- El mensaje de error sigue diciendo «run python build_runtime.py» (`:217`).
- El layout de release (`bin/psc`, `lib/`, `include/`, `std/`) no prevé
  `lib/wasm/`.
- **Riesgo:** si se añade `build/lib` a la búsqueda wasm, el linker intentará
  enlazar objetos host y fallará con un error confuso. La búsqueda debe ser
  **disjunta**.

### 6.4. Toolchain (`src/psc/driver/toolchain.pengu`)

- `choose_cc` ordena `override` → `manifest.cc` → `PSC_CC`/`PENGU_CC` →
  `gcc`/`clang`/`tcc`. Para wasm debe ser: `override` → `emcc` (auto) →
  `man.cc` solo si es emcc/clang compatible.
- `resolve` fija `-std=c11 -Wall`, añade cflags/defines del manifiesto e
  includes; no añade los `-s` de Emscripten, `--shell-file`, `--js-library`,
  `-pthread` condicional, `-sPTHREAD_POOL_SIZE`, ni flags de debug/release
  específicos de wasm.
- No hay `ldflags` en `Toolchain`.
- `add_lib` solo añade directorios existentes; para wasm debe buscar
  `lib/wasm` de proyecto y de cada binding, no `lib/`.
- El enlace final del driver añade `-lm -pthread -ldl` sin mirar target.
- `-fPIC`/`-shared` para `shared`: en wasm sería `SIDE_MODULE` y requiere
  `-fPIC` en **todos** los objetos, incluido el runtime; no está soportado.
- `emcc` es clang: el dialecto `target_compiler` debe ser `emcc` (el
  compilador Python lo hacía y `when compiler == "emcc"` dependía de ello).
  Hoy `CgOptions.compiler` se queda en `"gcc"` porque el driver solo asigna
  `target_compiler` (`driver/build.pengu:430`), y `comptime.option_value` lee
  `o.compiler` (`codegen/comptime.pengu:73`). **Bug de comptime** (H3).

### 6.5. Sema (`src/psc/sema`)

- `SemaOptions` tiene `wasm_target` (`options.pengu:32-33`) pero
  `default_options` lo deja `""` (`:62`) y el driver nunca lo asigna.
- `when_truth` (`check/collect.pengu:286-333`):
  - `wasm`: `wasm_target != "" or define_has("wasm")` (correcto en intención).
  - `main`: `opts->is_main` (global; no per-módulo).
  - `debug`: `opts->is_debug` (el driver no lo pone según perfil).
  - `os`/`arch`: devuelve `true` para el nombre desnudo; raro pero inofensivo.
  - **No hay `compiler`**.
- `when_value` (`:263-284`): solo resuelve `os` y `arch`; para
  `wasm_target`/`compiler` devuelve el **texto del identificador**, así que
  `when wasm_target == "emscripten"` compara `"wasm_target"` con
  `"emscripten"` → falso. `when compiler == "emcc"` → falso.
- `when_truth` para un `var_ref` desconocido devuelve `define_has` (false), **no
  E0039**. Verificado: `when zzz:` pasa `psc check` con exit 0 (§8.10).
- `is_main` no se ajusta por módulo; los módulos importados ven `main = true`,
  al contrario de lo que documenta `LANGUAGE.md`.
- `is_debug` no se deriva del perfil (`debug`/`release`), así que `when debug:`
  es siempre falso en sema.
- `compiler` existe en `SemaOptions` pero no se usa en `when`.

### 6.6. Codegen (`src/psc/codegen`)

- `CgOptions` no tiene `wasm`, `wasm_target`, `is_main`, `target_triple`;
  `os_name`/`arch`/`compiler`/`debug` existen pero el driver no los rellena
  correctamente (`driver/build.pengu:416-430`).
- `comptime.evaluate` (`comptime.pengu:84-173`):
  - `NdVarRef` solo resuelve `debug`; `wasm`, `wasm_target`, `main`,
    `compiler`, `os`, `arch` devuelven `-1` (desconocido).
  - `NdEq`/`NdNe` usan `option_value`, que solo resuelve `os`, `arch`,
    `compiler`; `wasm_target` no.
  - Si un operando es desconocido, devuelve `-1`.
  - `if v < 0: return` en `catalog.collect_top_node` (`:705-706`) descarta la
    rama **en silencio**; en `stmt.emit_when_stmt` (`:365-368`) incrementa
    `c->errors`, pero nadie lo comprueba.
- `generate_c` (`api.pengu:36-53`) devuelve siempre `ok = true`; `CgResult` no
  tiene error. **Los errores de codegen son invisibles.**
- **Bug H1:** `catalog.collect_top_node` (`:700-720`) asume que un
  `when_top_decl` tiene exactamente `cond`, `body`, `else` como hijos 0/1/2.
  El AST real tiene `cond` + N `top_stmt` + `else`. Para una rama con 3
  includes, `body = child 1` (primer include), `els = child 2` (segundo
  include, no el `else`), y el resto se pierde. Verificado: `when true:` con
  tres includes emite solo `a.h` (§8.7).
- El mismo bug afecta a `std/web.pengu`: la rama `when not wasm` tiene ~10
  declaraciones y solo se recoge la primera. Por eso `psc build
  tests/wasm/std_web_smoke.pengu` falla incluso en nativo (§8.7).
- `is_libc_name` (`bundle.pengu:19-53`) no incluye `emscripten_*`; al emitir
  `std.web` podría duplicar prototipos de `emscripten.h`. Hay que añadirlo o
  verificar que las firmas coinciden.
- `bundle.pengu` emite `main` con `pengu_init`, `pengu_install_crash_handler`,
  `fflush`; es portable a wasm (funciona en la prueba manual).
- `when main` en codegen no está implementado; `when debug` solo si
  `CgOptions.debug` se pone (hoy no).
- DCE: `std.web` depende de que `when` pliegue antes de DCE; con H1/H2 no lo
  hace.

### 6.7. Runtime C (`pengu_runtime.h`, `runtime/*.c`)

- `PENGU_EMSCRIPTEN` se define con `__EMSCRIPTEN__` (`:311-315`).
- `pengu_c_exec`/`pengu_c_spawn` tienen guard y devuelven `-1` con diagnóstico
  (`:3245-3334`).
- `pengu_c_filum_goroutine_id` tiene fallback `pthread_self()` para
  Emscripten (`runtime/pengu_runtime.c:100-...`).
- El runtime core compila con `emcc -std=c11 -pthread` (verificado, §8.2).
- `nanosleep`/`sleep` en el hilo principal del navegador es problemático:
  bloquea el event loop; `std.filum.sleep` no es una solución web. Para web
  hay que usar timers (`std.web.set_timeout`) o Asyncify/JSPI.
- La documentación del ABI (`pengu_runtime.h:50-100`) dice que las tallas son
  para 64 bits y que **32 bits no está cubierto**. wasm32 es ILP32; los tipos
  son fijos (`int32_t`, etc.), pero `size_t`/punteros son 4 bytes. Hay que
  añadir un test de layout wasm32 y revisar supuestos de `sizeof`.
- `pengu_runtime.h` incluye `<sys/stat.h>`, `<unistd.h>`, `<dirent.h>`,
  `<pthread.h>`; Emscripten los soporta (con MEMFS), pero no todos los
  simbolos (p. ej. sockets, dlopen).
- `std_c/miniz` usa `unsigned long` (`mz_ulong`); en wasm32 es 32 bits. El
  compilador Python ya documentó que clang/emcc no diagnostica
  `-Wtype-limits`; funciona. Verificado `compressus.crc32` en wasm (§8.3).

### 6.8. Stdlib: matriz de portabilidad

Leyenda: **OK** = compila y funciona en wasm (probado o inferido por C puro);
**PARCIAL** = compila pero con limitaciones; **NO** = no compila/enlaza o no
tiene sentido en web; **?** = pendiente de probar.

| Módulo | Estado wasm | Notas |
|---|---|---|
| `std.spark` | OK | print/panic sobre stdio; Emscripten lo lleva a consola |
| `std.scrolls` | OK | puro PenguScript |
| `std.builder` | OK | puro |
| `std.json`, `std.yaml`, `std.toml` | OK (probable) | `toml` usa `toml_min.h` C puro; JSON/YAML puros |
| `std.arithmancy`, `std.numerus`, `std.fractio` | OK | matemáticas/libc |
| `std.atlas`, `std.arena`, `std.bitset`, `std.ordinal` | OK | contenedores/puro |
| `std.diagnostic`, `std.sourcemap`, `std.chronicle` | OK | probado `chronicle` |
| `std.chrono` | OK | vaqt; probado `now`/`to_unix` |
| `std.digest`, `std.cipher` | OK (probable) | SHA-256 propio; sin libs externas |
| `std.compressus` | OK | miniz; probado `crc32` |
| `std.regulus` | OK | `re.c`; probado `is_match` |
| `std.lingua` | OK (probable) | `utf8.h` |
| `std.archivum` | PARCIAL | MEMFS: escribe/lee en `/out.txt`; no hay disco real; assets/preload/IDBFS |
| `std.io` | PARCIAL | stdin interactivo no existe; stdout/stderr OK |
| `std.rites` | PARCIAL | env/args/cwd OK; `exec` devuelve -1; `run_capture` usa `popen` y además tiene bug de codegen |
| `std.filum` | PARCIAL | funciona con `-pthread`; requiere COOP/COEP en navegador; `sleep` bloquea |
| `std.web` | OK una vez arreglado H1/H2 | consola, main loop, `now_ms`, `eval_js`, timers |
| `std.net` | **NO** | sockets BSD no existen en navegador; Node requirió `ws`; además bug de includes H1 |
| `std.dynlib` | **NO** | `dlopen` no existe; link `dl`; `ccx_dyn_*` no están en runtime wasm |
| `std.ffi_call` | **NO** | libffi nativo; no compilado para wasm |
| `std.secrets` | **NO** | libsodium nativo; no compilado para wasm |
| `std.petitio` | **NO** | libcurl nativo; no hay headers wasm; usar `std.fetch` |
| `std.web` (nativo) | **ROTO** por H1 | `std_web_smoke` no compila nativo |

### 6.9. Build scripts

- `tools/build_runtime.sh` es solo host: `CC`/`AR`, `build/lib`,
  `build/include`. No hay `--target`, no usa `emcc`/`emar`, no genera
  `build/wasm`.
- `tools/build_bootstrap.sh` llama a `build_runtime.sh` y compila stage0; no
  necesita wasm, pero CI wasm sí necesitará el nuevo script.
- `tools/package_ci.sh` copia `build/lib`, `build/include`, `std`, stubs y
  docs; no copia `build/wasm`, `pengu_wasm_shell.html` ni una JS library.
- `tools/gen_stage0.sh` no se ve afectado (el compilador sigue siendo nativo).
- `tools/release.sh` y `release.toml` no contemplan artefactos wasm.

### 6.10. Tests y CI

- `tests/run.sh` solo ejecuta `tests/pengu/*.pengu` y
  `tests/conformance/**/*.pengu`; **no** `tests/wasm`.
- `tests/wasm` tiene 3 fixtures huérfanos; el stress de filum no se ejecuta.
- No hay tests de target, artefactos, `when`, `std.web`, JS interop ni cache.
- `.github/workflows/ci.yml` solo tiene `build`, `vscode`, `release`; el job
  wasm que existía en `18c7044` fue eliminado.
- No hay job de navegador (Playwright) ni de `emcc --version`.
- El CI actual usa Python para tests LSP (`python3 tests/lsp/...`), pero el
  build no requiere Python. Para wasm conviene un runner shell, no Python.

### 6.11. Documentación

- `docs/WASM.md` no existe, pero `LANGUAGE.md` y `std/web.pengu` lo enlazan
  (`LANGUAGE.md:3454,3864,4919`; `std/web.pengu:15`).
- `LANGUAGE.md` §16 y §20.2.3.1 describen el wasm antiguo con `pengu` y
  `python build_runtime.py`; están desactualizados y contradicen el código
  actual (p. ej. dice que `--target` no cambia `os`).
- `docs/psc/CLI.md` dice «`psc build --target` F11» (placeholder).
- `docs/psc/DRIVER.md`, `docs/psc/MODULES.md` no mencionan target wasm salvo
  `SemaOptions.wasm_target`.
- `README.md` no menciona wasm/web.
- `CHANGELOG.md` conserva la historia 2.2.0, pero la versión actual 0.15.0 no
  anuncia wasm.
- `CHEATSHEET.md`/guías siguen hablando del compilador Python; fuera de este
  alcance, pero conviene no añadir más deuda.

### 6.12. Interoperabilidad JS/ECMAScript actual

Hoy solo existe:

- `std.web.eval_js(code)` → `emscripten_run_script` (sin valor de retorno, sin
  errores).
- `std.web.console_*` → consola.
- `std.web.set_main_loop` / timers.

No hay:

- Obtener/crear objetos JS, propiedades, arrays, funciones.
- Llamar funciones JS con argumentos y recibir valor.
- Callbacks JS → C (eventos DOM, promesas).
- Manejo de excepciones JS.
- `fetch`, `WebSocket`, DOM, Canvas, Storage.
- Módulos ES (`import()`), promesas/async, `BigInt`/i64.
- Tipos/ownership claros para valores JS.

`EM_ASM` no es una alternativa bajo `-std=c11`: verificado que `emcc 6.0.13`
emite `error: EM_ASM does not work in -std=c* modes` (§8.8). La solución
recomendada es `--js-library`.

---

## 7. Hallazgos priorizados

### H1 — `when` top-level con varias declaraciones pierde código (CRÍTICO)

**Estado:** verificado.
**Archivo:** `src/psc/codegen/catalog.pengu:690-720`.
**Qué pasa:** el codegen lee `body = child 1` y `els = child 2`; el AST real
tiene `cond` + N `top_stmt` + `else`. Solo se recoge el primer statement de la
rama; el resto se descarta o se interpreta como `else`.
**Evidencia:** `when true:` con `include "a.h"`, `"b.h"`, `"c.h"` emite solo
`a.h`; `psc build tests/wasm/std_web_smoke.pengu` falla con
`cancel_main_loop`/`now_ms`/`set_main_loop` no declarados.
**Impacto:** bloquea `std.web` (nativo y wasm), cualquier `std.js`/`std.dom`
con `when wasm:` y la recolección de includes (de ahí el fallo de `std.net`).
**Fix:** iterar todos los hijos entre `cond` y `else`; iterar todos los hijos
de `else`; manejar `else when` anidado; tests con 0/1/N statements y `else`.

### H2 — Codegen no evalúa las variables comptime de wasm (CRÍTICO)

**Estado:** verificado.
**Archivo:** `src/psc/codegen/comptime.pengu:84-173`.
**Qué pasa:** `wasm`, `wasm_target`, `main`, `compiler` (en `NdVarRef`) no se
resuelven; `wasm_target` tampoco en `NdEq`/`NdNe`; `evaluate` devuelve `-1` y
la rama se descarta.
**Evidencia:** `when wasm_target == ""` y `!= ""` se descartan ambas; la
función devuelve el fallback 909 (§8.7). `-D wasm` + `when wasm` produce C con
una llamada a una función que sema sí recolectó pero codegen no emitió (§8.7).
**Fix:** añadir un `CompileEnv` único (o, como mínimo, los mismos casos en
`option_value`/`evaluate` y en sema); distinguir «valor conocido vacío» de
«desconocido»; tests de las 8 combinaciones.

### H3 — Sema y codegen divergen; `when` desconocido no es E0039 (ALTO)

**Estado:** verificado.
**Archivos:** `src/psc/sema/check/collect.pengu:263-333`,
`src/psc/codegen/comptime.pengu`.
**Qué pasa:**
- `when zzz:` en sema es `false` silencioso; el test histórico espera E0039.
- `when wasm_target == "emscripten"` en sema compara `"wasm_target"` con el
  literal; en codegen falla.
- `when compiler == "emcc"` en sema es falso; en codegen usa `o.compiler`
  (que el driver deja en `gcc`), no `target_compiler`.
- `when main:` en sema usa `opts.is_main` global; los módulos importados ven
  `true`; en codegen no existe.
- `when debug:` no se deriva del perfil; ambos falsos.
**Impacto:** el código compilado no coincide con lo que el checker cree;
errores silenciosos; `std.web` roto.
**Fix:** `CompileEnv` compartido + diagnósticos E0039 + tests de paridad
sema/codegen.

### H4 — No hay modelo de target ni `--target` funcional (CRÍTICO)

**Estado:** verificado.
**Archivo:** `src/psc/cmd/build.pengu:198-203`.
**Qué pasa:** `--target` se rechaza; `BuildOptions` no tiene target; no hay
parser de triples; `SemaOptions.wasm_target` nunca se asigna; `CgOptions` no
tiene campos wasm.
**Impacto:** no se puede compilar a wasm de ninguna forma desde el CLI.
**Fix:** nuevo `Target`/`TargetTriple`, campos en opciones, propagación,
validación de alias y `wasi`, tests puros.

### H5 — Toolchain/paths/runtime wasm inexistentes (CRÍTICO)

**Estado:** verificado.
**Archivos:** `driver/paths.pengu`, `driver/toolchain.pengu`,
`tools/build_runtime.sh`.
**Qué pasa:** no se detecta `emcc`/`emar`; no se busca `build/wasm/lib`; no se
construye el runtime wasm sin Python; `psc init` pone `cc = "gcc"` y el driver
lo usaría; no hay `PENGU_RUNTIME_CROSS`.
**Impacto:** aunque se acepte `--target`, el build fallaría con gcc o con
«libpengu_runtime.a not found».
**Fix:** target-aware `paths`/`toolchain`, script `build_runtime_wasm.sh`,
detección de emsdk, mensajes accionables.

### H6 — Flags de enlace incorrectos; `ldflag` ignorado (ALTO)

**Estado:** verificado por lectura.
**Archivos:** `driver/build.pengu:641-656`,
`driver/toolchain.pengu`, `sema/check/collect.pengu:374-392`,
`driver/manifest.pengu:162`.
**Qué pasa:** `-pthread` y `-ldl` se añaden siempre; `man.ldflags` y
`symbols.ldflags` se recogen pero no se usan; no hay `-s` de Emscripten;
`shared` no se rechaza.
**Impacto:** programas wasm con hilos no arrancan/crecen; bindings con
`ldflag` (Raylib, SDL, WebSocket) no enlazan; `output = "shared"` produce algo
inválido.
**Fix:** flags wasm en `toolchain`/`driver`, `ldflags` fuera de
`--start-group`, `-pthread` condicional, `emar`, `shared` rechazado.

### H7 — Cache y artefactos no son target-aware ni multiarchivo (ALTO)

**Estado:** verificado por lectura.
**Archivos:** `driver/build.pengu:499-606`, `cache/cache.pengu:60-110`.
**Qué pasa:** la clave no incluye target; `cache.put` copia un solo archivo;
`psc run` ejecuta el artefacto como binario.
**Impacto:** colisiones nativo/wasm; `psc run --target wasm` intentaría
ejecutar un HTML; cache hits rotos.
**Fix:** target en la clave; desactivar cache de artefacto wasm en MVP; runner
target-aware; más adelante cache de directorio.

### H8 — Stdlib no portable sin gates (ALTO)

**Estado:** verificado parcialmente (§8.3-§8.6).
**Qué pasa:** `std.net` no compila sin headers (H1) y en Node necesita `ws`;
`std.dynlib`/`ffi_call`/`secrets`/`petitio` no enlazan; `std.rites.run_capture`
usa `popen` y tiene un bug de codegen; `std.archivum` es MEMFS; `std.filum`
requiere `-pthread`.
**Impacto:** el usuario que importa un módulo no soportado recibe errores C
crípticos o un link error, no un diagnóstico de PenguScript.
**Fix:** tabla de soporte, gates `when not wasm`, módulos sustitutos
(`std.fetch`, `std.websocket`), diagnóstico claro en driver/sema.

### H9 — Assets `.incbin` falla en wasm (MEDIO)

**Estado:** verificado.
**Archivo:** `src/psc/cmd/assets.pengu:397-410`.
**Qué pasa:** genera `__asm__(".section .rodata\n.incbin ...")`; el ensamblador
wasm de clang rechaza `.section`/`.previous`/`.incbin` (§8.9).
**Impacto:** cualquier proyecto con assets ≥ threshold no compila a wasm.
**Fix:** forzar el fallback de arrays para wasm (`PENGU_ASSETS_INCBIN_THRESHOLD=0`
o `--target wasm` en `psc assets`), o `--preload-file`.

### H10 — El runtime wasm no se puede construir sin Python (CRÍTICO)

**Estado:** verificado.
**Archivo:** `tools/build_runtime.sh`.
**Qué pasa:** el script es host-only; el comando que documenta el repo para
wasm (`python build_runtime.py --target emscripten`) ya no existe.
**Impacto:** no hay `build/wasm/lib/libpengu_runtime.a`; el build wasm no puede
enlazar.
**Fix:** `tools/build_runtime_wasm.sh` (o `psc runtime --target wasm`), con
`emcc`/`emar`, `-pthread` para el archivo, `miniz`/`re`/`vaqt`/`sds`/CC.

### H11 — Tests, CI, docs y release wasm perdidos (ALTO)

**Estado:** verificado.
**Qué pasa:** no hay runner wasm, no hay job CI, `docs/WASM.md` no existe, el
release no incluye shell/JS library/runtime wasm.
**Impacto:** la funcionalidad no se puede mantener; regresiones silenciosas.
**Fix:** `tests/wasm/run.sh`, job CI con emsdk, docs nuevas, packaging.

### H12 — No hay interop JS/ECMAScript (CRÍTICO para web)

**Estado:** verificado.
**Qué pasa:** solo `eval_js` sin retorno; no hay valores, callbacks, errores,
DOM, fetch, WebSocket, Canvas.
**Impacto:** PenguScript en web solo sirve para programas de consola o bindings
C pesados; no para aplicaciones web reales.
**Fix:** `std.js` + `--js-library`; módulos Web encima (F5/F6).

### H13 — ABI wasm32 no verificada (MEDIO)

**Estado:** inferido.
**Qué pasa:** el header documenta layouts de 64 bits y dice que 32 bits no está
cubierto; no hay test de layout wasm32.
**Impacto:** riesgo de suposiciones de tamaño en runtime/CC/vaqt.
**Fix:** test de layout en wasm32 y revisión de `size_t`/punteros; el codegen
usa tipos fijos, lo que ayuda.

### H14 — `psc run`/`test`/`eval`/`time` no tienen runner wasm (ALTO)

**Estado:** verificado.
**Qué pasa:** ejecutan `r.artifact` directamente.
**Impacto:** `psc run --target wasm` intentaría ejecutar un `.html`.
**Fix:** `runner` común: si target wasm, `node <artifact>.js`; si no hay Node,
imprimir ruta del HTML.

### H15 — El manifiesto puede forzar gcc en wasm (ALTO)

**Estado:** verificado por lectura.
**Qué pasa:** `choose_cc` usa `m.cc` antes de autodetectar; `psc init` escribe
`cc = "gcc"`.
**Impacto:** build wasm falla con gcc.
**Fix:** target manda; `--cc` explícito gana; `cc` del manifiesto solo para
nativo o si es un driver compatible.

### H16 — `psc check`/`emit-c` no permiten validar ramas wasm (MEDIO)

**Estado:** verificado.
**Qué pasa:** no aceptan `-D` ni `--target`.
**Impacto:** no se puede depurar `when wasm` sin compilar y enlazar.
**Fix:** añadir `-D` y `--target` a `check`/`emit-c`/`expand`.

### H17 — El mensaje de error del runtime está obsoleto (BAJO)

**Estado:** verificado.
**Qué pasa:** `paths.pengu:217` dice «run python build_runtime.py».
**Impacto:** confunde al usuario.
**Fix:** mensaje con `psc runtime --target wasm` / script.

### H18 — `std.web` nativo está roto (CRÍTICO, derivado de H1)

**Estado:** verificado.
**Evidencia:** `psc build tests/wasm/std_web_smoke.pengu` falla.
**Impacto:** no se puede usar `std.web` en código compartido.
**Fix:** H1 + tests nativos de `std.web`.

### H19 — No hay `psc doctor` para wasm (MEDIO)

**Estado:** verificado.
**Qué pasa:** solo comprueba gcc/clang/tcc/runtime host.
**Impacto:** el usuario no sabe si le falta emsdk, emar, node o el runtime wasm.
**Fix:** `--target wasm` con checks y versiones.

### H20 — El shell HTML y la experiencia de proyecto web no existen (MEDIO)

**Estado:** verificado.
**Qué pasa:** no hay `pengu_wasm_shell.html`, ni plantilla web, ni `[web]` en
el manifiesto, ni servidor con COOP/COEP.
**Impacto:** el usuario tiene que montar la página a mano; los threads no
funcionan sin headers.
**Fix:** shell, plantilla, `[web]`, `psc serve` opcional.

---

## 8. Evidencia experimental (verificada)

> Todos los experimentos se hicieron en `/tmp/psc-audit`, sin modificar el
> repositorio. El runtime wasm se construyó a mano para probar el C generado;
> no es el script definitivo.

### 8.1. Entorno

```text
$ emcc --version
emcc (Emscripten gcc/clang-like replacement + linker emulating GNU ld) 6.0.13-git
$ emar --version
$ node --version
v26.12.1
$ psc version
psc 0.15.0 (F12)
```

### 8.2. El runtime compila para wasm

```bash
emcc -O2 -std=c11 -pthread \
  -I. -Ibuild/include -Istd_c/sds -Istd_c/CC-main -Istd_c/vaqt/src \
  -ffunction-sections -fdata-sections \
  -DPENGU_ENABLE_THREADS=0 -DPENGU_RUNTIME_SUBSYSTEM_ONLY=0 \
  -c runtime/pengu_runtime.c -o /tmp/psc-audit/wasmobj/pengu_runtime.o
```

Resultado: `cc_exit=0`, objeto wasm de 5.6 KB. También compilaron
`pengu_runtime_filum.o`, `sds.o`, `vaqt_*.o`, `pengu_containers.o`,
`pengu_cc_extra.o`, `miniz.o` y `re.o`; se archivaron con `emar` en
`/tmp/psc-audit/libpengu_runtime.a` (90 KB).

### 8.3. El C generado por `psc` se enlaza y ejecuta en wasm

```bash
psc emit-c hello.pengu --out=hello_bundle.c
emcc -std=c11 hello_bundle.c \
  -I<repo> -I<repo>/build/include \
  -L/tmp/psc-audit -lpengu_runtime -lm \
  -s WASM=1 -s ALLOW_MEMORY_GROWTH=1 -s EXIT_RUNTIME=0 \
  -s INITIAL_MEMORY=16MB -s STACK_SIZE=1MB \
  -s ENVIRONMENT=web,node,worker \
  -s EXPORTED_RUNTIME_METHODS=ccall,cwrap,FS \
  -o app.html
node app.js
# hello from psc bundle
```

Tamaños con `-O2`:

```text
rel.wasm   3 056 B
rel.js    62 256 B
rel.html  19 596 B
```

Esto demuestra que el backend C, el runtime y el entry wrapper son viables en
wasm; lo que falta es el driver/comptime.

### 8.4. `std.filum` funciona con `-pthread`

```pengu
import std.filum
import std.spark

weave main into int:
    var m as filum.Mutex is calling filum.mutex
    calling m.lock
    calling m.unlock
    calling m.free
    calling filum.sleep with 10
    calling spark.println with "filum ok"
    return 0
```

Enlazado con `-pthread -sPTHREAD_POOL_SIZE=4`; `node filum.js` imprime
`filum ok` (con el warning informativo `-pthread + ALLOW_MEMORY_GROWTH`).

### 8.5. `std.archivum`, `std.chronicle`, `std.rites` (parcial)

```pengu
var ok as bool is calling archivum.write_text with "/out.txt", "hola"
...
calling chronicle.sleep_ms with 5
var v as maybe string is calling rites.getenv with "PATH"
```

`node misc.js` imprime `hola` y `env ok`. `std.archivum` usa el MEMFS de
Emscripten: `/tmp/psc-audit/...` no existe salvo que se cree; `/out.txt` sí.
`std.rites.run_shell` imprime `[PENGU] exec no soportado en wasm` y devuelve
-1; `getenv` funciona.

`std.rites.run_capture` no compila ni en nativo:

```text
std/rites.pengu:2103:25: error: member reference type 'PenguString *' is a pointer;
did you mean to use '->'?
```

Es un bug preexistente de codegen, no específico de wasm; hay que arreglarlo o
gatearlo.

### 8.6. `std.net` y módulos con libs nativas

- `std.net` sin headers: falla por `struct addrinfo` incompleto. Con
  `netdb.h`/`unistd.h`/`errno.h` añadidos a mano, compila y enlaza, pero
  `node net2.js` falla con `Cannot find module 'ws'`. En navegador no hay
  sockets BSD. **No es portable.**
- `std.dynlib`: `wasm-ld: undefined symbol: ccx_dyn_open` / `ccx_dyn_close`.
- `std.ffi_call`, `std.secrets`, `std.petitio`: dependen de libffi, libsodium
  y libcurl nativos; no están en el sysroot wasm.

### 8.7. Los bugs de `when` (evidencia directa)

**(a) `when` top-level con varias declaraciones:**

```pengu
when true:
    include "a.h"
    include "b.h"
    include "c.h"
else:
    include "d.h"
    include "e.h"
```

`psc emit-c` produce solo `#include "a.h"`. El AST (`psc parse`) muestra los
cinco hijos correctamente; el fallo está en `codegen/catalog.pengu`.

**(b) `std.web` nativo:**

```text
$ psc build tests/wasm/std_web_smoke.pengu
tests/wasm/std_web_smoke.pengu:34:16: error: declaración implícita de la función
'cancel_main_loop'
...
```

**(c) `-D wasm` + `when wasm`:**

```pengu
when wasm:
    weave only_wasm into int:
        return 7

weave main into int:
    return calling only_wasm
```

`psc build ... -D wasm` pasa sema pero falla en C:
`implicit declaration of function 'only_wasm'`. Sema recogió la rama; codegen
no la emitió.

**(d) `wasm_target == ""`:**

```pengu
weave pick into int:
    when wasm_target == "":
        return 707
    when wasm_target != "":
        return 808
    return 909
```

Nativo imprime `other` y el bundle contiene solo `return 909;`: ambas ramas se
descartaron.

**(e) `when zzz:`:**

`psc check when_unknown.pengu` devuelve exit 0; no emite E0039.

### 8.8. `EM_ASM` bajo `-std=c11` (verificado)

```c
#include <emscripten.h>
int main(void){ EM_ASM({ console.log("hi"); }); return 0; }
```

```text
em_asm.c:2:17: error: EM_ASM does not work in -std=c* modes, use -std=gnu* modes instead
```

Esto confirma que la interop JS debe ir por `--js-library` (o `emscripten_run_script`
sin retorno), no por `EM_ASM`.

### 8.9. `--js-library` funciona en C11 (prueba de concepto)

`pengu_js.js`:

```js
mergeInto(LibraryManager.library, {
  pengu_js_eval: function(ptr) {
    var code = UTF8ToString(ptr);
    var s = String((0, eval)(code));
    var len = lengthBytesUTF8(s) + 1;
    var buf = _malloc(len);
    stringToUTF8(s, buf, len);
    return buf;
  },
  pengu_js_call_c: function(id) {
    _pengu_c_callback(id);
  }
});
```

C con `EMSCRIPTEN_KEEPALIVE` en `pengu_c_callback`; enlace:

```bash
emcc -O2 -std=c11 js_lib_test.c --js-library pengu_js.js \
  -s WASM=1 -s ENVIRONMENT=node \
  -s EXPORTED_FUNCTIONS=_main,_malloc,_free,_pengu_c_callback \
  -s EXPORTED_RUNTIME_METHODS=UTF8ToString,lengthBytesUTF8,stringToUTF8 \
  -o js_lib.html
node js_lib.js
# eval=3
# callback 7
```

Conclusión: `--js-library` permite llamar JS desde C, devolver valores y llamar
C desde JS, sin `EM_ASM` y sin salir de C11. Es la base recomendada para
`std.js`.

### 8.10. `std.net` y assets

- `.incbin` bajo `emcc`:

```text
<inline asm>:1:17: error: Expected ,, instead got:
.section .rodata
<inline asm>:6:1: error: unknown directive
.previous
```

- `when zzz` check: exit 0 (silencioso).

### 8.11. Lo que NO se ha probado

- Navegador real (DOM, Canvas, WebSocket).
- `fetch` desde `std.js` (Node 26 tiene `fetch` global; se probará en F5).
- `psc test --target wasm`.
- ABI layout wasm32.
- Threads en navegador con COOP/COEP.
- `-sMODULARIZE`/`-sEXPORT_ES6`.

---

## 9. Diseño propuesto

### 9.1. Modelo de target

Nuevo `src/psc/driver/target.pengu`:

```pengu
rune Target:
    raw as string          # "wasm32-unknown-emscripten" o ""
    triple as string
    os as string           # "linux" | "macos" | "windows" | "emscripten"
    arch as string         # "x64" | "arm64" | "wasm32"
    env as string          # "gnu" | "musl" | "mingw" | "emscripten" | ""
    is_wasm as bool
    wasm_target as string  # "" | "emscripten" | "wasi"
    is_host as bool
```

Reglas:

- `""` → host nativo.
- `wasm`, `wasm32`, `emscripten` → `wasm32-unknown-emscripten`.
- `wasm32-unknown-emscripten` → wasm.
- `wasm32-wasi`/`wasi` → reconocido, `psc build` falla con mensaje claro.
- `x86_64-*linux*`, `aarch64-apple-darwin`, `*-mingw32` → nativos/cross
  existentes (no se tocan en esta fase).
- Target desconocido → error de uso (exit 2).
- `os` de compilación = `target.os` (para `when os`), `arch = target.arch`.
  **Decisión D3.**

Precedencia de `cc`:

1. `--cc` explícito.
2. `PSC_CC`/`PENGU_CC`.
3. `emcc` si target wasm (autodetectado; error accionable si falta).
4. `cc` del manifiesto (solo nativo).
5. `gcc`/`clang`/`tcc` nativo.

### 9.2. Entorno de compilación único (`CompileEnv`)

Un solo rune inmutable, copiado por módulo:

```pengu
rune CompileEnv:
    target as Target
    defines as list of string
    is_main as bool
    is_debug as bool
    os as string
    arch as string
    compiler as string
    wasm as bool
    wasm_target as string
```

Reglas de resolución (idénticas en sema y codegen):

- `os` → `env.os`; `arch` → `env.arch`; `compiler` → `env.compiler`.
- `wasm` → `env.wasm or defined("wasm")`; `wasm_target` → `env.wasm_target`.
- `main` → `env.is_main`; `debug` → `env.is_debug`.
- `defined(X)` → `X` en defines o en el entorno predefinido.
- `-D NAME[=VALUE]` gana para `os`, `arch`, `compiler` (documentado).
- `-D wasm` fuerza `wasm = true` pero **no** inventa `wasm_target`
  (comportamiento histórico).
- Comparaciones de strings con `""` son válidas para `wasm_target`; hay que
  distinguir «conocido vacío» de «desconocido».
- Identificador desconocido en `when` → E0039.

### 9.3. Toolchain y flags wasm

`Toolchain` gana `ldflags` y `target`; `resolve` para wasm:

```text
cc: emcc (autodetectado o --cc)
cflags:
  -std=c11 -Wall
  cflags/defines del manifiesto
  -I<build/wasm/include> -I<repo> -I<std_c/...>
  -ffunction-sections -fdata-sections (release)
  -g -O0 (debug) / -O2/-O3 (release)
link:
  -L<build/wasm/lib>
  -lpengu_runtime -lminiz -lre -lm
  --js-library <pengu_js.js>   (si std.js)
  --shell-file <shell>         (si exe y hay shell)
  -s WASM=1
  -s ALLOW_MEMORY_GROWTH=1
  -s INITIAL_MEMORY=16MB
  -s STACK_SIZE=1MB
  -s EXIT_RUNTIME=0
  -s ENVIRONMENT=web,node,worker
  -s EXPORTED_RUNTIME_METHODS=ccall,cwrap,UTF8ToString,stringToUTF8,lengthBytesUTF8,FS
  -s EXPORTED_FUNCTIONS=_main,_malloc,_free,<bridges>
  -pthread -sPTHREAD_POOL_SIZE=4   (solo si std.filum)
  ldflags de módulos/manifiesto/entorno
```

- `-ldl` **no** para wasm.
- `-pthread` **solo** si el programa importa `std.filum` (misma condición que
  `PENGU_ENABLE_THREADS`).
- `shared` wasm → error accionable; `static` usa `emar`.
- `-sASSERTIONS=1` en debug; `-g4`/`-sSOURCE_MAP=1` opcional.
- `-sMODULARIZE=1 -sEXPORT_ES6=1` opcional para bundlers.
- `--preload-file` opcional para assets.
- `PENGU_CFLAGS`/`PENGU_LDFLAGS` restaurados (split respetando `-s X`).
- `PENGU_WASM_SHELL=default` para usar el shell estándar.

### 9.4. Runtime wasm y layout

Script `tools/build_runtime_wasm.sh`:

```text
build/wasm/lib/libpengu_runtime.a  (core + filum + sds + vaqt + containers + cc)
build/wasm/lib/libminiz.a
build/wasm/lib/libre.a
build/wasm/include/pengu_runtime.h
build/wasm/obj/...
```

- Compila cada TU con `emcc -O2 -std=c11 -pthread` (el archivo lleva
  `-pthread`; el link decide si se activan threads).
- `-DPENGU_ENABLE_THREADS=0/1` y `PENGU_RUNTIME_SUBSYSTEM_ONLY` igual que host.
- `emar rcs` (nunca `ar`).
- `miniz`/`re` con los mismos flags; `petitio`/ffi/sodium se omiten con aviso.
- `--force`/`--rebuild`; cache por mtime.
- `psc doctor --target wasm` reporta si falta.

Layout de release:

```text
bin/psc
lib/libpengu_runtime.a          # host
lib/wasm/libpengu_runtime.a     # wasm
include/pengu_runtime.h
share/pengu/pengu_js.js
share/pengu/pengu_wasm_shell.html
std/...
```

`paths.find_paths(base, target)`:

1. `PENGU_RUNTIME_ARCHIVE` (si target coincide).
2. `PENGU_LIB_DIR` (override; si es wasm, debe apuntar a wasm).
3. `PENGU_RUNTIME_CROSS/lib` y `PENGU_RUNTIME_CROSS`.
4. `build/wasm/lib`, `build/wasm/include` (checkout).
5. `<exe>/../lib/wasm`, `<exe>/../share/pengu/wasm`.
6. `PENGU_HOME/lib/wasm`, `PENGU_HOME/include`.
7. **Nunca** `build/lib` para wasm.

### 9.5. Artefactos, runner y cache

Artefactos:

| `output` | Nativo | wasm |
|---|---|---|
| `exe` | `build/<name>` (`.exe` Windows) | `build/<name>.html` + `.js` + `.wasm` |
| `static` | `build/lib<name>.a` | `build/lib<name>.a` (emar) |
| `obj` | `build/<name>.o` | `build/<name>.o` |
| `c` | `build/bundle.c` | `build/bundle.c` |
| `shared` | `.so`/`.dylib`/`.dll` | **rechazado** |

Runner común (`psc/driver/runner.pengu`):

```pengu
weave run_artifact with artifact as string, target as Target, argv as list of string into int:
    if target.is_wasm:
        # derivar <artifact>.js; si no hay node -> imprimir .html y return 0
        return calling node_run with js_path, argv
    return calling proc.run_argv with [artifact] + argv
```

Cache:

- Clave incluye `target.triple`, `wasm_target`, `compiler`, flags, defines y
  fuentes.
- Para wasm exe, **no** cachear el artefacto final en el MVP (3 archivos).
- Cachear el `bundle.c` y los objetos intermedios si se quiere; o cachear el
  directorio completo (`app.html/app.js/app.wasm`) en una fase posterior.
- `psc run` debe usar el runner, no ejecutar el HTML.

### 9.6. Interop JS/ECMAScript (`std.js`)

#### Arquitectura

```text
PenguScript (std.js, std.dom, std.fetch, ...)
        │  declare / antiquus (C)
        ▼
runtime/pengu_js.c  (C bridge, compiled into wasm runtime)
        │  llamadas a funciones JS library
        ▼
runtime/pengu_js.js  (--js-library, Emscripten)
        │
        ▼
JS global / DOM / fetch / WebSocket / Canvas / Storage
```

- `--js-library` se pasa a `emcc`; no requiere `-std=gnu11`.
- C funciones puente exportadas con `EMSCRIPTEN_KEEPALIVE`.
- JS library usa `UTF8ToString`, `stringToUTF8`, `lengthBytesUTF8`, `_malloc`,
  `_free`; el driver exporta `_malloc`/`_free`.
- Callbacks JS→C: la JS library llama `_pengu_js_invoke(id, handle)`; C
  mantiene un registro de `(fn, user_data)`. Evita `addFunction` y
  `ALLOW_TABLE_GROWTH`.
- Promesas/async: callbacks. `-sJSPI` opcional para estilo `await`; no
  `-sASYNCIFY` por defecto.

#### Modelo de valores

```pengu
seal JsValue as i32   # 0 = undefined, 1 = null, >=2 handle
rune JsError:
    name as string
    message as string
    stack as string
```

- `js.eval(code)` → `result of JsValue to JsError`.
- `js.global()` → JsValue.
- `js.get(obj, name)`, `js.set(obj, name, v)`.
- `js.get_index(obj, i)`, `js.set_index(obj, i, v)`.
- `js.call(fn, this, args as list of JsValue)`.
- `js.new(ctor, args)`.
- `js.typeof(v)`, `js.is_undefined/null/truthy`.
- `js.to_string`, `js.to_f64`, `js.to_i64` (BigInt), `js.to_bool`.
- `js.string(s)` / `js.from_string(v)` (UTF-8 ↔ JS string).
- `js.object()`, `js.array()`, `js.length(v)`.
- `js.release(v)`, `js.retain(v)`, `js.scope_begin/end`.
- `js.import_module(url)` (dinámico; documentar CSP).
- `js.make_callback(fn, user)` / `js.free_callback(id)`.
- `js.promise_then(p, on_ok, on_err)` / `js.promise_catch`.
- `js.last_error()`.
- `js.IS_WASM`.

Semántica de memoria:

- Handles son índices JS; `release` los libera. No hay GC de C.
- Strings se copian entre mundos; nunca se devuelve un puntero a memoria JS.
- i64 se mapea a BigInt (`-sWASM_BIGINT`, default en 6.x).
- Errores JS no abortan el proceso; se convierten en `JsError`.
- `js.scope_begin/end` libera handles temporales (útil en bucles).

#### Ejemplo de uso

```pengu
import std.js
import std.spark

weave main into int:
    if not js.IS_WASM:
        return 0
    var doc as result of js.JsValue to js.JsError is calling js.eval with "document"
    if doc.is_ok:
        var title as result of js.JsValue to js.JsError is calling js.get with doc.value, "title"
        if title.is_ok:
            var s as string is calling js.from_string with title.value
            calling spark.println with s
            banish s
            calling js.release with title.value
        else:
            banish title.error.message
            banish title.error.stack
            banish title.error.name
        calling js.release with doc.value
    else:
        banish doc.error.message
        banish doc.error.stack
        banish doc.error.name
    return 0
```

(La API exacta se cerrará en F5; esto es una propuesta.)

### 9.7. Módulos Web

| Módulo | Dependencia | Alcance MVP |
|---|---|---|
| `std.web` | Emscripten (`console`, loop, timers) | sí |
| `std.js` | `--js-library` | sí |
| `std.dom` | `std.js` | sí (query/create/attrs/classes/events) |
| `std.fetch` | `std.js` + `fetch` | sí (GET/POST/headers/body, callback) |
| `std.websocket` | `std.js` + `WebSocket` | sí (connect/send/on_message) |
| `std.canvas` | `std.js` + `getContext("2d")` | fase 2 |
| `std.storage` | `std.js` + localStorage/IndexedDB | fase 2 |
| `std.webgl` | JS/`emscripten_webgl` | satélite |
| `std.raylib` | binding satélite + `-sUSE_GLFW` | fuera del núcleo |

Regla: **el núcleo web no debe exigir flags extra**. Si un módulo necesita
`-sFETCH`, `-lwebsocket.js`, `-lidbfs.js`, `-sUSE_SDL`, va a un satélite o a
un módulo opt-in documentado.

### 9.8. Proyecto web, shell y assets

`pengu.toml`:

```toml
[build]
target = "wasm32-unknown-emscripten"

[web]
shell = "web/index.html"      # opcional; si falta, shell integrado
title = "Mi app"
module = false                # true => -sMODULARIZE -sEXPORT_ES6
preload = ["assets"]          # opcional; --preload-file
js = ["web/app.js"]           # opcional; --pre-js/--post-js
css = ["web/style.css"]       # copiado al output
pthread = false               # auto si std.filum
```

`psc init --template web NAME`:

```text
pengu.toml
src/main.pengu
web/index.html
web/style.css
web/app.js
assets/
```

Shell integrado (recuperado de `pengu_wasm_shell.html`): terminal, progreso,
canvas oculto hasta WebGL, `Module.print/printErr`. `PENGU_WASM_SHELL=default`
usa el shell de Emscripten.

Assets:

- Para wasm, forzar arrays C (`incbin` no funciona).
- `[web] preload`: copia assets al MEMFS con `--preload-file`; el output
  incluye `app.data`, que debe servirse junto al `.wasm`.
- `psc assets --target wasm` para regenerar.

`psc serve` (opcional, F7): servidor HTTP nativo con COOP/COEP para threads,
sirve `build/`; evita depender de Python.

### 9.9. Tests y CI

Runner `tests/wasm/run.sh` (sin Python):

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT=...
PSC=${PSC:-$ROOT/build/psc}
command -v emcc >/dev/null || { echo "skip: emcc"; exit 0; }
command -v node >/dev/null || { echo "skip: node"; exit 0; }
# 1. build hello; 2. node; 3. static magic; 4. shared refused; 5. wasi refused
# 6. std.web smoke; 7. when folding; 8. js interop smoke; 9. filum (slow)
```

CI:

```yaml
wasm:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: mymindstorm/setup-emsdk@v14
      with: { version: '6.0.13' }   # o pin estable
    - run: bash tools/build_bootstrap.sh
    - run: ./build/psc-stage0 build .
    - run: bash tools/build_runtime_wasm.sh
    - run: bash tests/wasm/run.sh
    - uses: actions/upload-artifact@v4
      with: { name: wasm-demo, path: build/wasm-demo }
```

Opcional nightly: Playwright + `psc serve` para DOM/Canvas.

### 9.10. Documentación y release

- Restaurar `docs/WASM.md` adaptado a `psc` (sin Python).
- Nuevo `docs/WEB.md` (JS interop, DOM/fetch/websocket, async, memoria, CSP,
  COOP/COEP).
- `LANGUAGE.md`:
  - §16: `wasm`, `wasm_target`, `compiler`, `main`, `debug`, `os`/`arch`.
  - §19.1: añadir `std.js`, `std.dom`, `std.fetch`, `std.websocket`,
    `std.canvas`, `std.storage`.
  - §20.2.3.1: reescribir con `psc`, `tools/build_runtime_wasm.sh`, layout y
    limitaciones.
- `docs/psc/CLI.md`: quitar «F11», documentar `--target`, `--target wasm`.
- `docs/psc/DRIVER.md`, `MODULES.md`: target, `when` y paths.
- `README.md`: quickstart web.
- `CHANGELOG.md`: 0.16.0 (o 0.15.x) con sección wasm/web.
- `tools/package_ci.sh`: incluir `build/wasm`, shell, JS library, docs.
- `psc doctor --target wasm`.
- `VERSION`/`pengu.toml`/`release.toml`: bump.

---

## 10. Plan por fases

> Estimaciones para **un desarrollador** familiarizado con el código. No
> incluyen revisión externa ni imprevistos de Emscripten.

### Resumen

| Fase | Objetivo | Duración | Depende de | Entregable |
|---|---|---|---|---|
| F0 | Decisiones y alcance | 0.5-1 d | — | ADR/este doc firmado |
| F1 | Target model y CLI | 3-5 d | F0 | `--target` parseado y propagado |
| F2 | Toolchain/runtime wasm | 4-6 d | F1 | `build/wasm/lib` + `emcc` + artefactos |
| F3 | Comptime/codegen | 4-6 d | F1 | `when` correcto y errores |
| F4 | Portabilidad std | 4-6 d | F3 | Matriz + gates + diagnóstico |
| F5 | `std.js` interop | 8-12 d | F3 | eval/get/call/callbacks/errores |
| F6 | Módulos Web | 8-12 d | F5 | dom/fetch/websocket/canvas |
| F7 | Proyecto/shell/assets | 4-6 d | F2, F6 | `psc init web`, shell, serve |
| F8 | Tests/CI/docs/release | 4-6 d | F2-F7 | CI verde + docs + paquete |
| F9 | Avanzado (opcional) | — | F8 | JSPI, WebGL, WASI, playground |

**MVP (F0-F4 + `std.web` + runner + tests): ~3-4 semanas.**
**Web completo (F5-F8): ~8-12 semanas adicionales.**

### F0 — Decisiones y alcance (0.5-1 día)

Tareas:

- Cerrar D1-D22 (§11).
- Escribir un ADR corto con las decisiones.
- Confirmar que WASI y compilar `psc` a wasm quedan fuera.
- Confirmar el modelo de `os` (target vs host).

Salida: este documento actualizado + ADR.

### F1 — Modelo de target y CLI (3-5 días)

Tareas:

1. Crear `src/psc/driver/target.pengu` con `Target`, `parse`, `host`,
   `is_wasm`, `wasm_target`, `triple`.
2. Añadir `target` a `BuildOptions`; `wasm`, `wasm_target`, `target_os`,
   `compiler` a `SemaOptions`/`CgOptions`.
3. Leer `[build] target` en `manifest.pengu`.
4. `cmd/build`: quitar el rechazo; asignar target; `--target=`.
5. `cmd/test`: añadir `--target`.
6. `cmd/run`: refactorizar a `cliargs` o añadir `--target` al parser manual.
7. `main.pengu`: `emit-c`, `check`, `expand` aceptan `--target`/`-D`.
8. Artefactos wasm: `.html`/`.js`/`.wasm`, `static` `.a`, `obj` `.o`,
   `shared` rechazado.
9. Cache key con target.
10. Tests puros de parseo/alias/artefactos (sin emcc).

Criterios de salida:

- `psc build --target wasm` falla **después** de target, con un error de
  toolchain (no de CLI).
- `psc build --target wasi` falla con mensaje claro.
- `psc emit-c --target wasm` produce C (aunque `when` aún falle; ver F3).
- Tests de target en verde.

### F2 — Toolchain y runtime wasm (4-6 días)

Tareas:

1. `tools/build_runtime_wasm.sh` (emcc/emar, core/filum/sds/vaqt/CC/miniz/re).
2. `paths.find_paths` target-aware; búsqueda wasm disjunta;
   `PENGU_RUNTIME_CROSS`.
3. `toolchain.resolve` target-aware; `emcc`/`emar`; flags `-s`; `ldflags`.
4. `driver.build`: link wasm, `-pthread` condicional, `emar`, `shared`
   rechazado, `-o .html`.
5. Runner Node (`psc/driver/runner.pengu`) y uso en `run`/`test`.
6. `psc doctor --target wasm`.
7. Mensajes accionables (emsdk, runtime, Node).
8. Tests: hello, static magic, shared, wasi, missing emcc.

Criterios:

- `psc build --target wasm hello.pengu` produce `hello.html/js/wasm`.
- `node hello.js` imprime el programa.
- `psc run --target wasm hello.pengu` propaga el exit code.
- `psc build --target wasm` con `output = "static"` en `pengu.toml` produce un
  `.a` cuyos miembros empiezan por `\0asm`.
- `shared` y WASI fallan con mensajes claros.
- Sin `emcc`, el error dice cómo instalar emsdk.

### F3 — Comptime y codegen (4-6 días)

Tareas:

1. Arreglar H1: `catalog.collect_top_node` itera **todos** los hijos de la
   rama y del `else`; `else when` anidado.
2. Añadir casos `wasm`, `wasm_target`, `main`, `compiler` (y `os`/`arch` si
   faltan) a `comptime.evaluate`/`option_value`.
3. Unificar `CompileEnv` (recomendado) o duplicar reglas en sema/codegen.
4. `wasm_target` vacío conocido vs desconocido.
5. `-D` sobre `os`/`arch`/`compiler`; `-D wasm`.
6. `is_main` per módulo; `debug` por perfil; `compiler = emcc`.
7. `CgResult` con error; `generate_c` falla si `errors > 0`.
8. E0039 para `when` desconocido.
9. Tests de paridad sema/codegen y de `std.web` nativo/wasm.

Criterios:

- `when true:` con N includes emite N includes.
- `std_web_smoke` compila nativo y wasm.
- `when wasm_target == ""` nativo elige 707; wasm elige 808.
- `-D wasm` pliega `when wasm` en ambos.
- `when zzz` es E0039.
- `when compiler == "emcc"` funciona en wasm.
- `psc emit-c` con error de comptime falla (no silencio).

### F4 — Portabilidad de std (4-6 días)

Tareas:

1. Matriz §6.8 convertida en tests.
2. `std.net`: gate/unsupported; documentar `std.fetch`/`std.websocket`.
3. `std.dynlib`/`ffi_call`/`secrets`/`petitio`: `when not wasm` + stubs que
   panic o diagnóstico de driver; `link` gated.
4. `std.rites.run_capture`: arreglar bug de codegen o gatear en wasm.
5. `std.archivum`/`std.io`: documentar MEMFS/stdin.
6. `std.filum`: `-pthread` condicional; COOP/COEP.
7. Assets: arrays para wasm.
8. `psc check`/`emit-c` `--target` para validar.
9. Diagnóstico de módulo no soportado (driver o `compile_error`).

Criterios:

- Importar `std.net` en wasm da un mensaje claro, no un error de `addrinfo`.
- `std.dynlib`/ffi/secrets/petitio: error claro.
- `std.archivum` lee/escribe en MEMFS.
- Assets compilan con arrays.
- `std.filum` funciona con threads.

### F5 — `std.js` (8-12 días)

Tareas:

1. `runtime/pengu_js.js` (JS library).
2. `runtime/pengu_js.c` (bridge C; handles, callbacks, strings, errores).
3. `std/js.pengu` (`when wasm` + stubs nativos).
4. Driver: `--js-library`, exports `_malloc`/`_free`, bridges.
5. API de valores, propiedades, llamadas, arrays, tipos, conversiones.
6. Callbacks C↔JS con registro y `pengu_js_invoke`.
7. Promesas callback-style; opcional JSPI.
8. `import_module` dinámico.
9. Manejo de excepciones → `JsError`.
10. Tests Node (eval/get/set/call/callback) y browser opcional.

Criterios:

- `js.eval("1+2")` devuelve 3.
- `js.get(global, "Math")`, `js.call`, `js.new`.
- Callback JS→C funciona.
- Excepción JS no aborta; `JsError` con mensaje/stack.
- `js.release` no filtra handles (test de contador).

### F6 — Módulos Web (8-12 días)

Tareas:

1. `std.dom`: query/create/attrs/classes/styles/text/events.
2. `std.fetch`: GET/POST/headers/body/callback/errores.
3. `std.websocket`: connect/send/on_message/on_close.
4. `std.canvas`: 2D context, draw/fill/text/image.
5. `std.storage`: localStorage; IndexedDB (fase 2).
6. Tests Node (fetch/websocket) + browser (DOM/canvas) opcional.
7. Documentar CSP/COOP/COEP.

Criterios:

- Un programa wasm puede leer un input, escribir en el DOM y hacer fetch.
- WebSocket conecta en navegador.
- Canvas dibuja.
- Tests de humo en navegador (Playwright) opcional.

### F7 — Proyecto, shell, assets, serve (4-6 días)

Tareas:

1. `psc init --template web` / `psc new web`.
2. `pengu.toml` `[web]` (shell, title, module, preload, js, css).
3. Shell integrado restaurado.
4. Assets wasm (arrays/preload).
5. `psc serve` con COOP/COEP (opcional).
6. `psc run`/`test` wasm; `psc watch` wasm (opcional).
7. Documentar deploy (`app.html/js/wasm/data`).

Criterios:

- `psc init web demo && cd demo && psc run --target wasm` funciona.
- `psc build --target wasm` produce un sitio servible.
- Threads funcionan con `psc serve` (COOP/COEP).

### F8 — Tests, CI, docs, release (4-6 días)

Tareas:

1. `tests/wasm/run.sh` + fixtures.
2. CI wasm con emsdk pinneado.
3. `docs/WASM.md`, `docs/WEB.md`, `LANGUAGE.md`, `CLI.md`, README.
4. `psc doctor --target wasm`.
5. Packaging: shell, JS library, runtime wasm, docs.
6. CHANGELOG y versión.
7. Opcional nightly browser.

Criterios:

- CI wasm verde en Linux.
- `tools/package_ci.sh` incluye todo.
- Docs sin referencias a Python/`pengu`.
- `psc doctor --target wasm` verde.

### F9 — Avanzado (opcional)

- `-sJSPI` para `await` real.
- WebGL/WebGPU.
- WASI (si se decide).
- Playground/servidor de compilación.
- `psc bind --js` para generar bindings JS.
- Source maps integrados.
- `-sMODULARIZE`/ESM y TypeScript defs.

---

## 11. Decisiones que debes tomar (con recomendación)

### D1 — ¿Emscripten solamente, o también WASI?

- **A)** Solo `wasm32-unknown-emscripten`; WASI se rechaza. **(Recomendado)**
- **B)** Emscripten + WASI desde el inicio.

**Recomendación: A.** WASI no tiene DOM/fetch y exigiría un runtime JS aparte;
duplica el trabajo y no resuelve el objetivo web. Se puede añadir después.

### D2 — ¿Cómo se llama el argumento?

- **A)** `--target wasm` y `--target=wasm32-unknown-emscripten`. **(Recomendado)**
- **B)** Un flag dedicado `--wasm`.

**Recomendación: A.** Reutiliza el modelo de triples, permite `[build] target`
y no añade un flag nuevo que luego haya que mantener en todos los comandos.
Alias: `wasm`, `wasm32`, `emscripten`.

### D3 — ¿`when os` ve el host o el target?

- **A)** `os` = target (`emscripten` en wasm). **(Recomendado)**
- **B)** `os` = host; añadir `target_os` separado.

**Recomendación: A.** Es lo que hacía el wasm antiguo y lo que necesitan los
`when os == "windows"` de la stdlib para cross-compilar. Documentar el cambio
en `LANGUAGE.md` (hoy dice lo contrario). Si se necesita el host, añadir
`host_os` como variable nueva.

### D4 — ¿`arch` en wasm?

- **A)** `wasm32`. **(Recomendado)**
- **B)** `x64`/`arm64` del host.

**Recomendación: A.** `when arch == "wasm32"` es expresivo y evita confusión.

### D5 — ¿Cómo se construye el runtime wasm?

- **A)** Script `tools/build_runtime_wasm.sh` + `psc doctor`; build on demand;
  no empaquetar binario precompilado. **(Recomendado)**
- **B)** Empaquetar `libpengu_runtime.a` wasm precompilado en el release.
- **C)** Implementar `psc runtime --target wasm` en PenguScript desde el MVP.

**Recomendación: A** para el MVP, con C en F2/F8 si se quiere mejor UX. Un
archivo precompilado se acopla a la versión de Emscripten y puede fallar con
otra; si se empaqueta, debe ser para un emsdk pinneado y `psc doctor` debe
avisar. `psc runtime --target wasm` es la mejor UX a medio plazo.

### D6 — ¿Cómo se hace la interop JS?

- **A)** `--js-library` + `std.js` de handles opacos. **(Recomendado)**
- **B)** `EM_ASM`/`EM_JS` cambiando a `-std=gnu11`.
- **C)** Solo `emscripten_run_script` (sin valores).

**Recomendación: A.** `EM_ASM` no funciona en C11 (verificado). `--js-library`
permite valores, callbacks y errores, y mantiene el dialecto. `EM_JS` en
`-std=gnu11` es una alternativa, pero rompe la política C11 y complica el
strict-c99.

### D7 — Modelo async

- **A)** Callbacks primero; `-sJSPI` opcional; sin `-sASYNCIFY` por defecto.
  **(Recomendado)**
- **B)** `-sASYNCIFY` por defecto para `await` bloqueante.
- **C)** Solo callbacks, sin JSPI.

**Recomendación: A.** Los callbacks cubren `fetch`, WebSocket, DOM y timers sin
hinchar el wasm. JSPI es opt-in para código que quiera `await`; Asyncify es
caro y no debe ser el default. Documentar que `sleep` bloqueante no es viable
en el hilo principal.

### D8 — Alcance de módulos Web en el repo

- **A)** Núcleo en el repo: `std.js`, `std.dom`, `std.fetch`,
  `std.websocket`, `std.canvas` (2D), `std.storage`; gráficos pesados como
  satélites. **(Recomendado)**
- **B)** Todo como satélites.
- **C)** Todo en el repo, incluido WebGL/WebGPU.

**Recomendación: A.** El núcleo web debe funcionar sin flags y sin descargas;
WebGL/WebGPU/SDL/Raylib son satellite.

### D9 — Threads

- **A)** `-pthread` automático solo si `std.filum`; `-sPTHREAD_POOL_SIZE=4`;
  documentar COOP/COEP. **(Recomendado)**
- **B)** `-pthread` siempre.
- **C)** Sin threads en wasm.

**Recomendación: A.** Es el comportamiento histórico y evita exigir
`SharedArrayBuffer` a programas que no lo usan.

### D10 — Assets

- **A)** Arrays C para wasm por defecto; `--preload-file` opt-in para assets
  grandes. **(Recomendado)**
- **B)** Solo `--preload-file`.
- **C)** Arreglar `.incbin` (no es posible en wasm).

**Recomendación: A.** `.incbin` no existe en el ensamblador wasm. Arrays
funcionan siempre; preload es mejor para muchos archivos.

### D11 — Formato de salida

- **A)** `app.html` + `app.js` + `app.wasm` por defecto; `--out=.js`/`.mjs`
  soportado; `-sMODULARIZE` opt-in. **(Recomendado)**
- **B)** Solo `app.js` (sin HTML).
- **C)** Solo ES module.

**Recomendación: A.** El HTML es lo que un usuario abre; el `.js`/`.mjs` sirve
para bundlers. `-sMODULARIZE` se activa con `[web] module = true`.

### D12 — Cache

- **A)** Desactivar cache de artefacto final para wasm en el MVP; cachear
  `bundle.c`/objetos con target en la clave; cache de directorio después.
  **(Recomendado)**
- **B)** Cachear solo `app.wasm`.
- **C)** Cachear el directorio completo desde el inicio.

**Recomendación: A.** Evita bugs de archivos hermanos; el cache de bundle ya
aporta la mayor parte del ahorro. C es deseable pero más trabajo.

### D13 — Tests

- **A)** Runner shell + `psc`/Node; sin Python; browser opcional con
  Playwright. **(Recomendado)**
- **B)** Tests Python (como el wasm antiguo).
- **C)** Solo tests manuales.

**Recomendación: A.** Mantiene la promesa «no Python para build» y encaja con
`tests/run.sh`.

### D14 — Release

- **A)** Incluir shell, `pengu_js.js`, docs y el script de runtime; runtime
  wasm compilado on demand. **(Recomendado)**
- **B)** Incluir también `libpengu_runtime.a` wasm precompilado (pinneado).
- **C)** No incluir nada wasm; solo repo.

**Recomendación: A** + opcional B para un emsdk pinneado. El shell y la JS
library son pequeños y necesarios; el archivo fuego depende de emcc.

### D15 — `check`/`emit-c` con target

- **A)** Añadir `--target` y `-D` a `check`, `emit-c`, `expand`.
  **(Recomendado)**
- **B)** Solo `build`/`run`/`test`.

**Recomendación: A.** Es la forma de depurar `when` y de ver el C wasm sin
emcc; bajo coste.

### D16 — ¿Compilar el compilador a wasm?

- **A)** Fuera de alcance; playground en servidor. **(Recomendado)**
- **B)** Intentarlo ahora.

**Recomendación: A.** `psc` usa filesystem, subprocess, libclang y red; el
esfuerzo es enorme y no es necesario para «usar PenguScript en la web».

### D17 — Modelo de errores JS

- **A)** `result of ... to JsError`; nunca abortar por una excepción JS.
  **(Recomendado)**
- **B)** `panic` con el mensaje JS.
- **C)** Ignorar errores.

**Recomendación: A.** Permite manejar fallos de red/DOM; `panic` queda para
errores de programación.

### D18 — Ownership de handles JS

- **A)** `js.release` explícito + `js.scope_begin/end`; sin GC. **(Recomendado)**
- **B)** `FinalizationRegistry` y no liberar.
- **C)** Handles inmortales.

**Recomendación: A.** Es predecible y depurable; el GC de JS no ve los handles
de C. Añadir un contador de debug para detectar fugas.

### D19 — Navegador vs Node

- **A)** Ambos: Node para tests/CLI; navegador para DOM/Canvas; smoke opcional
  con Playwright. **(Recomendado)**
- **B)** Solo navegador.
- **C)** Solo Node.

**Recomendación: A.** Node permite CI rápido; el navegador es el objetivo real.

### D20 — `std.net` en web

- **A)** No portar sockets BSD; ofrecer `std.fetch` y `std.websocket`.
  **(Recomendado)**
- **B)** Intentar sockets con `ws`/WebRTC.
- **C)** Dejar `std.net` roto.

**Recomendación: A.** Los sockets no existen en el navegador; `fetch` y
WebSocket cubren HTTP y tiempo real. `std.net` queda nativo.

### D21 — Módulos nativos no soportados

- **A)** `when not wasm` + stubs que panicen y diagnóstico de driver.
  **(Recomendado)**
- **B)** Dejar que el linker falle.
- **C)** Eliminarlos.

**Recomendación: A.** Un mensaje «std.ffi_call no está disponible en wasm; usa
std.js» es mucho mejor que `undefined symbol`.

### D22 — Versión de Emscripten

- **A)** Pinnear una versión en CI (p. ej. 6.0.13 o la última estable) y
  comprobar la versión en `psc doctor`; el runtime se construye con la misma.
  **(Recomendado)**
- **B)** `latest` siempre.
- **C)** Soportar cualquier versión sin comprobar.

**Recomendación: A.** Emscripten cambia flags y ABI; un pin evita sorpresas.
El runtime wasm debe construirse con el mismo emcc que enlaza.

---

## 12. Riesgos y mitigaciones

| ID | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | H1/H2/H3 bloquean `std.web` y toda la interop | Alta | Alto | F3 antes de F4/F5; tests de `when` |
| R2 | Divergencia sema/codegen | Alta | Alto | `CompileEnv` único; tests de paridad |
| R3 | Cache nativo/wasm colisiona | Media | Alto | target en clave; desactivar cache wasm |
| R4 | `cc = "gcc"` del manifiesto | Alta | Alto | target manda; test |
| R5 | Runtime wasm no coincide con emcc | Media | Alto | build on demand; doctor; pin |
| R6 | Flags de Emscripten cambian | Media | Medio | pin + tests CI |
| R7 | ABI wasm32 (size_t/punteros) | Media | Medio | test de layout; revisar structs |
| R8 | `-pthread` siempre exige COOP/COEP | Alta | Medio | condicional a `std.filum` |
| R9 | `sleep` bloquea el event loop | Alta | Medio | documentar; timers/JSPI |
| R10 | Handles JS fugan memoria | Media | Medio | release/scope; contador debug |
| R11 | CSP bloquea `eval`/`import` | Media | Medio | documentar; API sin eval |
| R12 | `std.net`/dynlib/ffi fallan críptico | Alta | Medio | gates + diagnóstico |
| R13 | Assets `.incbin` | Alta | Medio | arrays/preload |
| R14 | Node vs browser APIs | Media | Medio | tests Node + browser opcional |
| R15 | Shell/packaging incompletos | Media | Bajo | checklist release |
| R16 | Docs desactualizadas | Alta | Bajo | F8 |
| R17 | `std.rites.run_capture` bug | Alta | Bajo | arreglar/gatear |
| R18 | `when` top-level con `else when` | Media | Medio | tests específicos |

---

## 13. Matriz de pruebas

| ID | Prueba | Comando | Esperado |
|---|---|---|---|
| T1 | Parseo de alias | `psc build --target wasm` | selecciona emscripten |
| T2 | WASI rechazado | `psc build --target wasm32-wasi` | exit 2, mensaje |
| T3 | Target desconocido | `psc build --target foo` | exit 2 |
| T4 | Nombres de artefacto | `psc build --target wasm hello.pengu` | `.html/.js/.wasm` |
| T5 | Hello + Node | `node build/hello.js` | salida correcta |
| T6 | `psc run` exit code | `psc run --target wasm exit7.pengu` | exit 7 |
| T7 | Static wasm | `emar t app.a` + `head -c4` | `\0asm` |
| T8 | Shared rechazado | `output="shared"` | error claro |
| T9 | Sin emcc | PATH sin emcc | error con emsdk |
| T10 | Sin runtime | borrar `build/wasm/lib` | error accionable |
| T11 | `when wasm` | `psc emit-c --target wasm` | rama wasm |
| T12 | `when wasm_target == ""` | nativo | 707 |
| T13 | `-D wasm` | build | rama wasm |
| T14 | `when zzz` | `psc check` | E0039 |
| T15 | `when` top-level N | emit-c | N includes |
| T16 | `std.web` nativo | `psc run tests/wasm/std_web_smoke.pengu` | OK |
| T17 | `std.web` wasm | `psc run --target wasm ...` | OK |
| T18 | DCE | `emit-c` con solo `now_ms` | no `set_main_loop` |
| T19 | `std.filum` wasm | stress | OK con `-pthread` |
| T20 | `std.archivum` | escribir/leer `/out.txt` | OK |
| T21 | `std.net` | importar en wasm | diagnóstico claro |
| T22 | `std.dynlib` | importar en wasm | diagnóstico claro |
| T23 | Assets | build con assets | arrays, compila |
| T24 | `js.eval` | Node | 3 |
| T25 | `js.call`/`get`/`set` | Node | OK |
| T26 | Callback JS→C | Node | OK |
| T27 | `JsError` | eval inválido | error, no abort |
| T28 | `fetch` | Node 26 | OK |
| T29 | DOM | Playwright | OK |
| T30 | Cache target | build nativo+wasm | artefactos distintos |
| T31 | Doctor | `psc doctor --target wasm` | emcc/emar/node/runtime |
| T32 | Package | `tools/package_ci.sh` | shell/JS/runtime incluidos |

---

## 14. Criterios de aceptación

### 14.1. MVP (Track A)

- [ ] `psc build --target wasm` compila y produce `app.html/js/wasm`.
- [ ] `psc run --target wasm` ejecuta con Node y propaga exit code.
- [ ] `psc test --target wasm` ejecuta el runner de tests.
- [ ] `psc build --target wasm` con `static` produce un `.a` wasm real.
- [ ] `shared` y WASI se rechazan con mensajes claros.
- [ ] `when wasm`, `when wasm_target`, `when compiler == "emcc"` y
      `when wasm_target == ""` pliegan correctamente en sema y codegen.
- [ ] `std.web` compila y funciona en nativo y wasm.
- [ ] `std.filum` funciona con `-pthread`; sin filum no se exige COOP/COEP.
- [ ] `std.archivum`/`io`/`rites` tienen comportamiento documentado.
- [ ] `std.net`/dynlib/ffi/secrets/petitio dan diagnóstico claro en wasm.
- [ ] Assets compilan con arrays.
- [ ] `psc doctor --target wasm` reporta toolchain/runtime.
- [ ] Tests wasm en CI y `tests/wasm/run.sh`.
- [ ] `docs/WASM.md` y `CLI.md` actualizados.

### 14.2. Web completo (Track B)

- [ ] `std.js` con eval/get/set/call/new/callbacks/errores.
- [ ] `std.dom` con query/create/attrs/classes/events.
- [ ] `std.fetch` GET/POST/headers/body/callback.
- [ ] `std.websocket` connect/send/on_message.
- [ ] `std.canvas` 2D.
- [ ] `psc init --template web` + `psc run --target wasm` funciona.
- [ ] Shell personalizable; `psc serve` con COOP/COEP (opcional).
- [ ] Prueba de navegador (Playwright) opcional.
- [ ] `docs/WEB.md` y ejemplos.

---

## 15. Anexos

### A. Archivos recuperables del historial

```bash
# Documentación wasm antigua (511 líneas)
git show 20136f6:docs/WASM.md > /tmp/WASM.md

# Shell HTML (132 líneas)
git show 20136f6:pengu_wasm_shell.html > /tmp/pengu_wasm_shell.html

# Build script Python (584 líneas) — solo referencia
git show 20136f6:build_runtime.py > /tmp/build_runtime.py

# Tests wasm antiguos
git show 20136f6:tests/wasm/test_wasm_target.py > /tmp/test_wasm_target.py
git show 20136f6:tests/wasm/test_std_web.py > /tmp/test_std_web.py
git show 20136f6:tests/wasm/conftest.py > /tmp/conftest.py
git show 20136f6:tests/compiler/test_comptime_wasm.py > /tmp/test_comptime_wasm.py

# Parte wasm del compilador Python
git show 20136f6:pengu_project.py | grep -n "wasm\|emcc\|emar" | head -120
```

### B. Flags de `emcc` propuestos (resumen)

```text
-std=c11 -Wall
-O2 (release) / -g -O0 (debug)
-pthread                         # solo std.filum
-s WASM=1
-s ALLOW_MEMORY_GROWTH=1
-s INITIAL_MEMORY=16MB
-s STACK_SIZE=1MB
-s EXIT_RUNTIME=0
-s ENVIRONMENT=web,node,worker
-s EXPORTED_RUNTIME_METHODS=ccall,cwrap,UTF8ToString,stringToUTF8,lengthBytesUTF8,FS
-s EXPORTED_FUNCTIONS=_main,_malloc,_free,<bridges>
--js-library <pengu_js.js>
--shell-file <shell>
-s PTHREAD_POOL_SIZE=4          # solo std.filum
-s ASSERTIONS=1                 # debug
-s MODULARIZE=1 -s EXPORT_ES6=1 # opt-in
--preload-file <assets>         # opt-in
```

### C. API propuesta de `std.js` (borrador)

```pengu
const JS_VERSION as string is "0.1.0"
const IS_WASM as bool is true            # false en nativo

rune JsError:
    name as string
    message as string
    stack as string

weave eval with code as string into result of JsValue to JsError
weave global into JsValue
weave get with obj as JsValue, name as string into result of JsValue to JsError
weave set with obj as JsValue, name as string, value as JsValue into result of bool to JsError
weave get_index with obj as JsValue, index as int into result of JsValue to JsError
weave set_index with obj as JsValue, index as int, value as JsValue into result of bool to JsError
weave call with fn as JsValue, this_v as JsValue, args as list of JsValue into result of JsValue to JsError
weave new with ctor as JsValue, args as list of JsValue into result of JsValue to JsError
weave typeof with v as JsValue into string
weave is_undefined with v as JsValue into bool
weave is_null with v as JsValue into bool
weave is_truthy with v as JsValue into bool
weave to_string with v as JsValue into result of string to JsError
weave to_f64 with v as JsValue into result of f64 to JsError
weave to_i64 with v as JsValue into result of i64 to JsError
weave to_bool with v as JsValue into result of bool to JsError
weave string with s as string into JsValue
weave from_string with v as JsValue into result of string to JsError
weave object into JsValue
weave array into JsValue
weave length with v as JsValue into int
weave release with v as JsValue into void
weave retain with v as JsValue into void
weave scope_begin into void
weave scope_end into void
weave make_callback with fn as ref to weave with arg as JsValue into void into JsValue
weave free_callback with id as int into void
weave promise_then with p as JsValue, on_ok as JsValue, on_err as JsValue into void
weave import_module with url as string into result of JsValue to JsError
weave last_error into JsError
```

### D. Glosario

- **Emscripten:** toolchain C→wasm (`emcc`, `emar`).
- **wasm32:** arquitectura de 32 bits de WebAssembly (ILP32).
- **MEMFS:** filesystem virtual en memoria de Emscripten.
- **COOP/COEP:** cabeceras HTTP necesarias para `SharedArrayBuffer` y threads.
- **JSPI:** JavaScript Promise Integration de WebAssembly (await real).
- **Asyncify:** transformación de Emscripten para pausar/reanudar C.
- **SIDE_MODULE:** biblioteca wasm compartida; requiere `-fPIC` global.
- **`--js-library`:** archivo JS que implementa funciones importadas por C.

### E. Referencias locales

- `src/psc/cmd/build.pengu` — rechazo de `--target`.
- `src/psc/driver/build.pengu` — flujo de build/link/cache.
- `src/psc/driver/toolchain.pengu` — selección de cc/flags.
- `src/psc/driver/paths.pengu` — runtime/std.
- `src/psc/sema/options.pengu` — `wasm_target`.
- `src/psc/sema/check/collect.pengu` — `when` en sema.
- `src/psc/codegen/comptime.pengu` — `when` en codegen.
- `src/psc/codegen/catalog.pengu` — bug H1.
- `src/psc/codegen/api.pengu` — error silencioso.
- `std/web.pengu` — puente Emscripten.
- `pengu_runtime.h` — guards Emscripten y ABI.
- `tests/wasm/` — fixtures huérfanos.
- `tools/build_runtime.sh` — runtime host.
- `.github/workflows/ci.yml` — CI sin wasm.
- `LANGUAGE.md` §16, §19.1, §20.2.3.1 — docs wasm obsoletas.

### F. Referencias externas

- Emscripten: <https://emscripten.org/>
- `emcc` settings: <https://emscripten.org/docs/tools_reference/settings_reference.html>
- `--js-library`: <https://emscripten.org/docs/porting/connecting_cpp_and_javascript/Interacting-with-code.html>
- JSPI: <https://emscripten.org/docs/porting/asyncify.html>
- `-sFETCH`, `-lwebsocket.js`: documentación de Emscripten.
- COOP/COEP: <https://web.dev/articles/coop-coep>

---

## 16. Próximo paso recomendado

1. **Aprobar D1-D5** (alcance, flag, `os`, `arch`, runtime) y **D6-D7**
   (interop, async) para no rehacer F5.
2. **Implementar F1 + F3 primero** (target model + arreglo de `when`), porque
   F2 sin F3 produce builds que fallan de forma confusa, y F4/F5 sin F3 no
   pueden compilar `when wasm`.
3. **F2 en paralelo** con F3 si hay dos personas: F2 no depende de F3 para
   compilar un hello sin `when`.
4. **No empezar F5/F6** hasta que `std.web` funcione en nativo y wasm y los
   tests de `when` estén en verde.
5. **Cerrar el MVP** con `tests/wasm/run.sh` y un job CI antes de añadir DOM.

---

### Nota final

El wasm antiguo no era solo un flag: era un contrato entre driver, comptime,
runtime, stdlib, shell, tests y release. La migración F11 se llevó el contrato
completo; restaurar solo el flag produciría un build que falla en el siguiente
paso. La buena noticia es que el C generado y el runtime **ya son wasm-capaces**
(verificado en §8): el trabajo es de plomería, comptime y producto, no de
reinventar el backend.
