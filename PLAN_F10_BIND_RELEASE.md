# PLAN F10 — Bind externo y release

> **Estado:** propuesta para aprobación. No implementado todavía.
> **Base:** F9 cerrada; `psc bind` sigue siendo un stub y `make_release.py`
> empaqueta el `pengu` de Python, no PSC.
> **Objetivo:** `psc bind` nativo con helper `pengu-bind`, y release de PSC sin
> Python en el equipo de destino.

---

## 1. Resumen ejecutivo

Hoy `pengu_bind.py` genera `.d.pengu` desde cabeceras C, pero sólo se invoca
desde `pengu_project.py` (Python). F10 debe:

1. congelar el generador como **`pengu-bind`** ejecutable;
2. implementar **`psc bind`** que lo localiza y le pasa los flags;
3. empaquetar `psc` + `pengu-bind` + `std/` + runtime + headers/stubs en
   **portable y FHS**, con checksums y smoke tests;
4. retirar el `pengu` Python del paquete de release.

El binario `psc` **no** debe requerir Python. `pengu-bind` es un binario
autocontenido (PyInstaller onefile u equivalente): puede llevar CPython dentro,
pero no exige un Python instalado.

**Fuera de F10:** reescribir el parser de cabeceras en PSC (F10b/libclang),
firma/notarización, LSP, package manager (F9), switchover (F11).

---

## 2. Estado actual

| Pieza | Estado |
|---|---|
| `pengu_bind.py` | generador funcional; sin `main()`/CLI propio |
| `pengu bind` | flags en `pengu_project.py`; llama `generate_bind_file` |
| `psc bind` | stub “not available until F10” |
| `make_release.py` | PyInstaller de `pengu_project.py`; paquete con Python |
| `psc` release | no empaquetado como binario principal |
| VSIX | `vscode-extension/`; versión sincronizada por release |
| Stubs | `c_bind_stubs/`; usados por el preprocesador |
| Runtime | `build/lib/libpengu_runtime.a`, headers |

### Contrato actual de `pengu bind`

```text
pengu bind HEADER
  [--prefix P]
  [--links L...]
  [--output PATH]
  [--no-comments]
  [--ignore SYM...]
  [--include-paths DIR...]
  [--define NAME[=V]]
  [--cpp-flags "..."]
  [--system-includes]
  [--preprocessed FILE.i]
  [--no-blank-extensions]
  [--no-cpp]
  [--auto-import DIR]
```

Salida por defecto: `<header>.d.pengu` junto a la cabecera. Errores a stderr,
exit 1; uso inválido 2.

---

## 3. Decisiones

### D1 — `pengu-bind` congelado, no parser nuevo

- ✅ **Recomendado:** congelar `pengu_bind.py` con PyInstaller `--onefile` para
  Linux/macOS/Windows. El usuario final no necesita Python.
- ⚠️ Alternativa: F10b (parser C puro o libclang). Es un proyecto aparte; no
  bloquea el release.

### D2 — Contrato estable y paridad

- ✅ **Recomendado:** mismos flags, misma salida byte a byte que stage0 en el
  corpus; exit codes 0/1/2; stdout sólo con `--output -` (nuevo, opt-in);
  diagnóstico a stderr.
- ⚠️ Alternativa: romper flags. Inaceptable.

### D3 — `psc bind` como wrapper nativo

- ✅ **Recomendado:** `psc bind` no reimplementa el parser: localiza el helper,
  valida flags, ejecuta con **argv** (sin shell), captura stderr/stdout, propaga
  exit code y escribe la salida de forma atómica si el helper no lo hace.
- ⚠️ Alternativa: portar el generador a PSC. F10b.

### D4 — Localización del helper

Orden:

1. `$PENGU_BIND` (path explícito);
2. mismo directorio que `psc` (`pengu-bind` / `pengu-bind.exe`);
3. `libexec/pengu/pengu-bind` relativo a `PENGU_HOME`;
4. `PATH`.

Si no aparece: error claro con `PENGU_BIND` e instrucciones de instalación.
Validar `--version` y, en release, SHA-256 contra el manifiesto.

### D5 — Sólo TOML para configuración

- ✅ **Recomendado:** manifiesto de release `release.toml` y checksums en texto.
  Nada de YAML/JSON para configuración de release.
- ⚠️ Alternativa: JSON. Rechazado por la regla del proyecto.

### D6 — Layout portable y FHS

**Portable** (`pengu-<ver>-<os>-<arch>/`):

```text
bin/psc
bin/pengu-bind
std/
include/
lib/libpengu_runtime.a
c_bind_stubs/
share/doc/pengu/{README,LICENSE,CHANGELOG}
VERSION
```

**FHS** (`/usr/local` o prefijo):

```text
bin/psc
bin/pengu-bind
lib/pengu/libpengu_runtime.a
include/pengu/...
share/pengu/std/...
share/doc/pengu/...
```

`psc` resuelve `std/`, runtime y helper desde su propio path / `PENGU_HOME`,
con overrides `PENGU_STD_DIR`, `PENGU_LIB_DIR`, `PENGU_INCLUDE_DIR`,
`PENGU_BIND`.

### D7 — Sin Python en destino

- ✅ **Recomendado:** `psc` es C nativo; `pengu-bind` es un onefile autocontenido.
  Smoke con `python3` eliminado del `PATH` y `PYTHONHOME`/`PYTHONPATH` vacíos.
- ⚠️ Alternativa: exigir Python en el helper. Rompe F10.

### D8 — Release determinista

- ✅ **Recomendado:** `SOURCE_DATE_EPOCH`, `PYTHONHASHSEED=0`, tar/zip con
  timestamps normalizados, checksums `SHA256SUMS`, sin rutas absolutas.
- ⚠️ Alternativa: releases no reproducibles. Inaceptable.

### D9 — Plataformas

- ✅ **Recomendado:** Linux x86_64 y aarch64; macOS x86_64/arm64; Windows x86_64.
  CI nativo por plataforma; el helper se construye en cada runner.
- ⚠️ Alternativa: sólo Linux. No cumple el criterio de salida.

### D10 — Seguridad

- ✅ **Recomendado:**
  - ejecutar helper con argv, sin shell;
  - validar `--include-paths`/`--preprocessed`/header y salida;
  - no escribir fuera de `--output`/directorio del header;
  - `--output` atómico (tmp + rename);
  - límites de tamaño/tiempo del helper;
  - stubs y `-nostdinc` por defecto; `--system-includes` explícito;
  - rechazar includes inseguros (ya existe);
  - checksum del helper en release.
- ⚠️ Alternativa: confiar en flags del usuario. Inaceptable.

### D11 — Sin cambios de runtime/ABI

`psc bind` y release no tocan `pengu_runtime.h`. Sólo empaquetan lo existente.

### D12 — `make_release.py`

- ✅ **Recomendado:** conservarlo como orquestador dev, pero que empaquete
  **PSC** y `pengu-bind`, no `pengu_project.py` congelado. Nuevo
  `psc/tools/release.py` puede sustituirlo; ambos escriben `release.toml`.
- ⚠️ Alternativa: dos releases distintos. Confuso.

---

## 4. Arquitectura

```text
psc/src/psc/cmd/bind.pengu       # wrapper CLI
psc/src/psc/bind/locate.pengu    # $PENGU_BIND, sibling, libexec, PATH
psc/src/psc/bind/args.pengu      # flags y validación
psc/src/psc/bind/run.pengu       # argv, timeout, stdout/stderr, exit codes
psc/src/psc/release/paths.pengu  # layout portable/FHS
psc/src/psc/release/checksum.pengu
psc/tools/pengu_bind_entry.py    # entry PyInstaller (dev-only)
psc/tools/release.py             # empaquetado PSC (dev-only)
release.toml                     # versión, artefactos, plataformas
```

`pengu_bind.py` se mantiene como fuente única del generador; el entry sólo llama
`generate_bind_file` y traduce flags a exit codes.

---

## 5. CLI

```bash
psc bind HEADER [flags de pengu bind]
psc bind --helper-version
psc bind --print-helper
```

- `--output -`: escribe `.d.pengu` a stdout (opt-in; no rompe el default).
- `--helper-version`: imprime versión del helper localizado.
- `--print-helper`: ruta resuelta (debug/empaquetado).
- Flags desconocidos: exit 2 antes de ejecutar.
- Si el helper devuelve 1: propagar 1 y stderr; si no existe: 1 con ayuda.
- `--output` se valida y se crea el directorio padre sólo si ya existe (no
  inventar árboles).

---

## 6. Contrato del helper

```text
pengu-bind --version
pengu-bind HEADER [--prefix ...] ... [--output PATH|-]
```

- `--version`: `pengu-bind <release-version>`; exit 0.
- Sin `HEADER`: exit 2, usage a stderr.
- Header inexistente / parse error: exit 1, mensaje accionable.
- `--output -`: salida a stdout, sin logs.
- Errores/warnings a stderr; nada de logs en stdout.
- No escribe archivos temporales fuera de `TMPDIR`.
- Límite de tiempo configurable por `PENGU_BIND_TIMEOUT` (default 120 s).
- No requiere `python` en `PATH`.

---

## 7. Release

### 7.1 Artefactos

```text
pengu-0.10.0-linux-x86_64.tar.gz
pengu-0.10.0-linux-aarch64.tar.gz
pengu-0.10.0-macos-x86_64.tar.gz
pengu-0.10.0-macos-arm64.tar.gz
pengu-0.10.0-windows-x86_64.zip
SHA256SUMS
```

Cada artefacto incluye portable y/o FHS según matriz; el nombre lleva layout.

### 7.2 Pipeline

1. bootstrap PSC (stage4 fijo) y `psc version`.
2. build runtime (`libpengu_runtime.a`, headers) con el C compiler.
3. build `psc` nativo.
4. build `pengu-bind` onefile con PyInstaller (sólo build-time).
5. ensamblar portable/FHS; copiar std, stubs, docs, VERSION.
6. normalizar permisos/timestamps; generar `release.toml` y `SHA256SUMS`.
7. smoke sin Python:
   - `psc version`;
   - `psc build/run/check/fmt` en fixture;
   - `psc lsp --stdio` initialize/shutdown;
   - `pengu-bind --version`;
   - `psc bind` sobre corpus y comparación con stage0;
   - `psc bind` sin helper => error esperado.
8. publicar artefactos (fuera de este plan).

### 7.3 Descubrimiento de recursos

`psc` debe encontrar `std/`, `include/`, runtime y `pengu-bind`:

- `PENGU_HOME` (raíz del paquete);
- ruta del ejecutable (`dirname`);
- layout portable/FHS;
- overrides por variable de entorno.

Sin rutas absolutas embebidas; smoke desde un directorio temporal y con el
paquete movido de sitio.

---

## 8. Bind: paridad y corpus

- Corpus: `c_bind_stubs/**`, headers de `extern/` usados por std, y fixtures
  con structs/enums/callbacks/typedefs/macros.
- Para cada header: generar con stage0 (`pengu bind`) y con `psc bind`; comparar
  bytes de `.d.pengu`, stderr normalizado y exit code.
- Casos especiales:
  - `--preprocessed`;
  - `--no-cpp`;
  - `--system-includes`;
  - `--auto-import`;
  - `--define`/`--cpp-flags`;
  - nombres reservados/ignorados;
  - header con include inseguro.
- Golden actualizable sólo con `--update-golden` (dev).

---

## 9. Seguridad

- Helper ejecutado con `argv`, sin `shell=True`.
- Timeout y límite de salida (p. ej. 64 MiB).
- Validar que `--output` no sea un symlink que escape; escritura atómica.
- `--include-paths` existentes; rechazar paths con `..` fuera del proyecto salvo
  absolutos explícitos.
- `--preprocessed` sólo archivo regular.
- No heredar `PYTHONPATH`/`PYTHONHOME` en el helper congelado.
- Firma/notarización: fuera de F10 (documentar).

---

## 10. Tests

### 10.1 Bind

- `test_f10_bind_locator.py`: `$PENGU_BIND`, sibling, libexec, PATH, ausente.
- `test_f10_bind_contract.py`: flags, exit codes, `--output -`, stderr.
- `test_f10_bind_parity.py`: corpus stage0 vs PSC byte a byte.
- `test_f10_bind_security.py`: output symlink, header ausente, timeout,
  include inseguro.
- `test_f10_bind_no_python.py`: ejecutar con `PATH` sin Python.

### 10.2 Release

- `test_f10_release_layout.py`: portable/FHS, permisos, symlinks.
- `test_f10_release_manifest.py`: `release.toml`, checksums, VERSION.
- `test_f10_release_smoke.py`: binario movido, `PENGU_HOME`, `psc` commands.
- `test_f10_release_determinism.py`: dos builds mismo SHA256SUMS (mismo SO).
- `test_f10_release_no_python.py`: contenedor/entorno sin Python.
- CI Linux/macOS/Windows; artefactos subidos como job artifacts.

### 10.3 Regresión

F1–F9 verdes, bootstrap, preflight, LSP smoke.

---

## 11. Fases y estimación

| Fase | Contenido | Semanas |
|---|---|---:|
| F10.0 | Contrato, corpus, goldens, `release.toml` | 1 |
| F10a | `psc bind` wrapper + locator + tests | 1.5 |
| F10b | Entry `pengu-bind`, onefile, versión, no-Python | 1.5 |
| F10c | Release portable/FHS de PSC | 2 |
| F10d | CI matriz, determinismo, smoke sin Python | 1.5 |
| F10e | Docs, seguridad, VSIX, cierre | 1 |
| **Total** | | **7–9** |

Timebox: 8–10 semanas. Si F10b (onefile) se desborda, F10b puede entregar el
helper como script dev-only **sólo para tests**, pero el criterio de salida exige
el binario congelado.

---

## 12. Criterios de aceptación

1. `psc bind` funciona y genera `.d.pengu` byte-idéntico a stage0 en el corpus.
2. `psc bind` localiza `$PENGU_BIND`, sibling, libexec y PATH; error claro si no.
3. `pengu-bind` funciona sin Python instalado.
4. Release portable y FHS arrancan desde un directorio movido.
5. `psc build/run/check/fmt/lsp` funcionan en el paquete.
6. `psc bind` funciona en el paquete; sin helper falla con ayuda.
7. Checksums y `release.toml` correctos; build determinista en el mismo SO.
8. Linux/macOS/Windows CI verdes (o limitación documentada y aprobada).
9. Sin Python en destino; sin cambios de runtime/ABI.
10. F1–F9, bootstrap y preflight verdes.
11. Docs/CLI/CHANGELOG actualizados; commit final en `main`, sin push.

---

## 13. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| PyInstaller no es determinista | Alta | Medio | `SOURCE_DATE_EPOCH`, smoke de hash |
| Helper no encuentra pycparser/stubs | Media | Alto | hidden imports + add-data + test |
| `psc` no encuentra std/runtime al mover | Media | Alto | `PENGU_HOME` + layout + smoke |
| Paridad de bind incompleta | Media | Alto | corpus + goldens |
| Windows paths/quoting | Media | Medio | CI Windows, argv sin shell |
| macOS gatekeeper | Media | Medio | documentar no notarizado |
| Tamaño del onefile | Baja | Bajo | aceptar; medirlo |
| Scope creep a F10b | Alta | Alto | fuera de alcance |

---

## 14. Fuera de alcance

- Parser de cabeceras C en PSC/libclang (F10b).
- Firma Authenticode/notarización macOS.
- Auto-update.
- Publicación en gestores de paquetes (Homebrew, apt, winget).
- Cambios de runtime/ABI.

---

## 15. Preguntas para aprobar

1. ¿Aprobado `pengu-bind` congelado con PyInstaller, sin parser nuevo (D1)?
2. ¿Aprobado `psc bind` como wrapper argv con `$PENGU_BIND`/sibling/libexec/PATH
   (D3/D4)?
3. ¿Aprobado el contrato de flags y `--output -` opt-in (D2)?
4. ¿Aprobado release portable + FHS sin Python en destino (D6/D7)?
5. ¿Aprobado `release.toml` y checksums, sin YAML/JSON (D5)?
6. ¿Aprobado el pipeline determinista y la matriz Linux/macOS/Windows (D8/D9)?
7. ¿Aprobado el presupuesto 7–9 semanas?

Si se aprueba, empiezo por **F10.0 + F10a**: contrato, corpus, locator y
`psc bind` wrapper con tests, antes de congelar el helper y empaquetar.
