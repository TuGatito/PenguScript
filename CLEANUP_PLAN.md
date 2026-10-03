# 🧹 PLAN DE LIMPIEZA DEL REPOSITORIO — PENGUSCRIPT

> **Objetivo:** reducir el ruido del repositorio (archivos muertos, cachés sucios, documentos de
> proceso, duplicaciones) **sin romper un solo import, test o workflow**.
> **Regla de oro:** cada eliminación y cada movimiento de este plan se ejecuta **después** de
> verificar con `grep`/`git ls-files` que nada lo referencia. Nada se borra "porque parece viejo".
> **Base:** `AUDIT_1.0.md` §12 (organización) y §19 (deuda técnica).
> **Secuencia:** este plan se ejecuta como **Fase 0** de `ROADMAP_2.0.md`, **antes** de tocar
> cualquier lógica. Ver §7 para el orden exacto con tests de verificación por paso.

---

## §0. Estado verificado del repositorio

Antes de proponer nada, esto es lo que hay realmente (medido, no supuesto):

| Métrica | Valor verificado | Comando |
|---------|------------------|---------|
| Archivos rastreados en git | **509** | `git ls-files \| wc -l` |
| Archivos totales (sin `.git`) | 38 505 | `find . -type f -not -path "./.git/*" \| wc -l` |
| Archivos en la raíz | **40** (16 `.py`, 20 `.md`, `.h`, `.c`, `VERSION`, `requirements.txt`, `.gitignore`, `.gitattributes`) | `ls -1 *.py *.md *.h *.c` |
| Documentos `.md` en la raíz | **20** (~1 MB de Markdown) | `ls -1 *.md \| wc -l` |
| Directorios de primer nivel | 18 | `ls -d */` |
| `extern/` (gitignored) | 329 MB | `du -sh extern` |
| `vscode-extension/` (incluye `node_modules`) | 123 MB | `du -sh vscode-extension` |
| `build/` (gitignored) | 49 MB | `du -sh build` |
| `tests/` | 6.7 MB, 155 archivos `.py`, 36 590 líneas | `wc -l tests/*.py \| tail -1` |
| `std_c/` | 6.5 MB de headers de terceros | `du -sh std_c` |
| `pengu_parser/` | 3.0 MB, 27 204 líneas | `wc -l pengu_parser/*.py \| tail -1` |
| `__pycache__/` propios (fuera de `extern/`) | **7 directorios** | `find . -name __pycache__ -not -path "./extern/*"` |
| `.pytest_cache/` | **1** | `ls -d .pytest_cache` |
| `.gitignore` | 1 385 B, de calidad alta | — |

### §0.1 Lo que el enunciado sospechaba y resultó **falso** (❌ REFUTADO)

Debe quedar registrado antes de proponer borrados, para no eliminar cosas que **sí** se usan:

| Sospecha | Veredicto | Evidencia |
|----------|-----------|-----------|
| `scratch/` existe y está sucio | ❌ **REFUTADO** | `ls -d scratch` → no existe |
| `tests_std/` existe duplicando `tests/` | ❌ **REFUTADO** | `ls -d tests_std` → no existe |
| `pengu_runtime_original.h` existe | ❌ **REFUTADO** | No existe; el CHANGELOG 0.8.4 lo dio por eliminado **y efectivamente lo está** |
| `build/` no está gitignored | ❌ **REFUTADO** | `.gitignore:12`; `git ls-files \| grep '^build/'` → vacío |
| `extern/` no está gitignored | ❌ **REFUTADO** | `.gitignore:7`; `git ls-files \| grep extern` → vacío |
| `pengucc_build/` existe | ❌ **REFUTADO** | No existe; `.gitignore:14` lo cubre por si acaso |
| Hay archivos `.log`/`.csv`/`.tmp`/`.bak`/`.orig` rastreados | ❌ **REFUTADO** | `git ls-files` limpio; `.gitignore` los cubre |
| Hay `*.vsix`/`*.tar.gz`/`*.zip`/`*.exe`/`*.o`/`*.a` rastreados | ❌ **REFUTADO** | `git ls-files` limpio; `.gitignore:18-27,39` los cubre |
| Hay archivos `_old`/`_backup`/`_v1`/`_new`/`_test` sueltos | ❌ **REFUTADO** | `git ls-files \| grep -E '_(old\|backup\|v1\|new)\b'` → 0 |
| Los módulos del compilador "se fugan a la raíz" (`pengu_checker.py`, `pengu_infer.py`, `pengu_parser.py`, `pengu_symbols.py`, `pengu_types.py`, `pengu_errors.py`, `pengu_comptime.py`) | ❌ **REFUTADO** | Viven **exclusivamente** en `pengu_parser/`; ver §4.1 |
| `pengu_folder.py` es un archivo suelto en la raíz | ❌ **REFUTADO** | **No existe en ningún sitio del repositorio** |
| `pengu_dce.py` (raíz) es código muerto | ❌ **REFUTADO** | Es un shim de reexportación con `__all__`, importado por `tests/test_dce_tcc_pch.py:12` y referenciado en `docs/PERFORMANCE.md:163` |
| Hay dependencias circulares entre módulos | ❌ **REFUTADO** | 0 ciclos verificados en los 5 pares sospechosos (§5) |

**Consecuencia:** el `.gitignore` y la higiene de archivos generados de este repositorio son
**mejores de lo que el enunciado suponía**. El trabajo real de limpieza es mucho más pequeño y se
concentra en: **(a)** documentos de proceso histórico en la raíz, **(b)** un archivo rastreado de 0
bytes, **(c)** cachés de Python en el árbol de trabajo, **(d)** duplicación de superficie
(`pengu_bind.main`, `pengu_dce` shim), y **(e)** la reorganización del CLI monolítico.

---

## §1. Archivos a eliminar

### §1.1 Alta confianza — eliminar

| Archivo | Tamaño | Razón | ¿Lo usa algo? | Reemplazo |
|---------|--------|-------|---------------|-----------|
| `pengu_runtime.c` (raíz) | **0 bytes** | Archivo **vacío rastreado en git** desde `ef57c84` (`[0.15.0]`). La implementación real vive en `pengu_parser/pengu_runtime.c` (68 373 B), que es la que usa `build_runtime.py:1174` (`PARSER_DIR / "pengu_runtime.c"`) | **No.** Verificado: `git cat-file -s HEAD:pengu_runtime.c` → `0`; `grep -rn "ROOT_DIR / \"pengu_runtime.c\"\|'pengu_runtime.c'" build_runtime.py make_release.py pengu_project.py` → solo la ruta de `PARSER_DIR` | Ninguno. **Actualizar `CHEATSHEET.md:64`**, que dice *"The runtime that generated code links against lives in `pengu_runtime.h` / `pengu_runtime.c`"* y hace pensar que es el de la raíz |
| `__pycache__/` (raíz) | 684 KB | Bytecode de Python; regenerable | No (gitignored, pero **presente en el árbol**) | Ninguno |
| `pengu_parser/__pycache__/` | — | Ídem | No | Ninguno |
| `pengu_lsp/__pycache__/` | — | Ídem | No | Ninguno |
| `tests/__pycache__/` | — | Ídem | No | Ninguno |
| `scripts/fuzz/__pycache__/` | — | Ídem | No | Ninguno |
| `.pytest_cache/` | — | Caché de pytest | No | Ninguno |

**Nota sobre los `__pycache__` de `extern/`:** existen 8 más dentro de `extern/curl-8.21.0/` y
`extern/mbedtls-4.2.0/`. Como `extern/` está gitignored y se regenera por descarga, **no forman parte
de este plan** (borrarlos no aporta nada y `make_release.py` los ignora).

**Riesgo global de §1.1:** **nulo**. Ninguno está rastreado salvo `pengu_runtime.c`, y ese está
vacío. El único cuidado es actualizar la mención de `CHEATSHEET.md:64`.

### §1.2 Documentos de proceso histórico — mover a `docs/archive/` (recomendado) o eliminar

Estos 7 documentos suman **~125 KB** y compiten por la atención del lector con `README.md`. Ninguno
está referenciado por código, tests ni workflows (verificado con `grep -rn`).

| Archivo | Tamaño | Razón para archivarlo | ¿Referenciado? |
|---------|--------|----------------------|----------------|
| `AUDIT_RESPONSE.md` | 32 474 B | Respuesta a una **auditoría anterior**; su contenido está superado por `AUDIT_1.0.md`. No es documentación de usuario | Verificado: solo se autorreferencia |
| `PRODUCTION_READINESS.md` | 57 194 B | Estado de readiness de una versión anterior; solapa con `RELEASE_CHECKLIST.md` (3 947 B) y `CRITICALS_PROGRESS.md` | No |
| `P1_PROGRESS.md` | 10 813 B | Progreso de una fase **terminada** ("Fase 1") | No |
| `P2_PROGRESS.md` | 7 723 B | Progreso de una fase terminada ("Fase 2") | No |
| `CRITICALS_PROGRESS.md` | 6 407 B | Progreso de críticos, ya resueltos o incorporados al CHANGELOG | No |
| `Plan.md` | 7 341 B | Plan superado por `ROADMAP_1.0.0.md` (65 411 B) y por `ROADMAP_2.0.md` | No |
| `roadmap.md` | 2 608 B | Roadmap **duplicado** de `ROADMAP_1.0.0.md` | No |

**Recomendación:** **mover** a `docs/archive/` con un `docs/archive/README.md` de una línea que
explique que son documentos históricos no normativos. **No borrar**, porque:
1. Conservan la historia de decisiones (valor para contribuidores futuros).
2. Borrarlos destruiría el `git blame` de discusiones de diseño.
3. El coste de mantenerlos es cero una vez fuera de la raíz.

**Si el objetivo es minimizar el repositorio**, el orden de borrado por menor valor sería:
`roadmap.md` → `Plan.md` → `P1_PROGRESS.md` → `P2_PROGRESS.md` → `CRITICALS_PROGRESS.md` →
`AUDIT_RESPONSE.md` → `PRODUCTION_READINESS.md` (el último tiene algo de valor histórico).

**Kill switch:** antes de mover, ejecutar
`for f in AUDIT_RESPONSE PRODUCTION_READINESS P1_PROGRESS P2_PROGRESS CRITICALS_PROGRESS Plan roadmap; do echo "== $f"; grep -rn "$f" --include="*.md" --include="*.yml" --include="*.py" --include="*.json" . 2>/dev/null | grep -v extern | grep -v "^./$f.md"; done`
y comprobar que no hay referencias entrantes fuera de los propios archivos.

### §1.3 Documentos a **mover**, no eliminar

| Archivo | Destino | Razón | Enlaces a actualizar |
|---------|---------|-------|---------------------|
| `PENGU_BUILD.md` | `docs/` | Documento de build del runtime; pertenece a `docs/` junto a `PERFORMANCE.md` | `grep -rn "PENGU_BUILD"` sobre `.md`/`.yml` |
| `README_RELEASE.md` | `docs/` | Notas de release; no es un README de proyecto (el README es `README.md`) | `grep -rn "README_RELEASE"` |
| `AUDIT_RESPONSE.md` … `roadmap.md` | `docs/archive/` | Ver §1.2 | `grep -rn` por cada uno |

### §1.4 Código muerto — eliminar o conectar

| Ubicación | Qué es | Tamaño | Decisión | Justificación |
|-----------|--------|--------|----------|---------------|
| `pengu_bind.py:1567-1617` | `main()` + `argparse` completo (14 flags) **duplicando** el subcomando `bind` ya declarado en `pengu_project.py` | ~50 líneas | **Eliminar `main()`**, conservar el módulo como librería (`generate_bind_file`, `HeaderParseError`) | `pengu_project.py:5090` importa **solo** `HeaderParseError, generate_bind_file`; el `main()` no lo llama nadie. Dos superficies CLI para un subcomando pueden divergir |
| `pengu_lsp/code_actions.py:396` | `organize_imports_action` implementada, **0 call sites** | ~40 líneas | **Conectar** (no borrar) en `server.py:1059-1089` | Está completa y es una feature esperada por los usuarios; el coste de conectarla es una línea. Borrarla sería tirar trabajo hecho (ver `ROADMAP_2.0.md` item 5.3) |
| `pengu_lsp/server.py:1790` | CodeLens que emite `Command(command="pengu.runTest")`, comando **no registrado** | ~10 líneas | **Conectar o eliminar** | Hoy es un botón inerte; ver item 5.4 |
| `pengu_parser/pengu_grammar.py` — reglas `guard_*` (12 reglas) | Duplican la jerarquía de expresión completa para el guard de `when_clause` | ~35 líneas | **Consolidar** (Fase 2, no Fase 0) | Requiere un flag de contexto en el parser; es refactor de grammar, no limpieza |
| `pengu_parser/pengu_grammar.py` — reglas `*_no_cast` (11 reglas) | Duplican la jerarquía completa para excluir `transmute` en `for`/`slice_range` | ~40 líneas | **Consolidar** (Fase 2) | Ídem |
| `pengu_parser/pengu_grammar.py` — `simple_stmt` | Probablemente inalcanzable (se usan los aliases de `SIMPLE_STMT_ALIASES`) | 6 líneas | **Verificar y eliminar** si es inalcanzable | Requiere instrumentar el parser; hacerlo en Fase 2 |
| `pengu_parser/pengu_infer.py:1886` | `covered_variants: Set[str]` sin `Set` importado | 1 línea | **Añadir `Set` al import** | Falso positivo de pyflakes por PEP 563, pero es ruido en cada lint; arreglarlo cuesta una palabra |
| `pengu_project.py:1192` | `List[Tuple[str, Tree]]` sin `Tree` importado | 1 línea | **Añadir `Tree` al import** | Ídem |
| 10 variables locales asignadas y nunca usadas | `ret_str` ×2, `sign`, `raw_name`, `package`, `key_c`, `iter_elem_c`, `is_local`, `is_cyclus`, `elem_c`, `current_abs`, `concept_name_node`, `base_target` | ~12 líneas | **Eliminar** | Detectadas por pyflakes; eliminar reduce el ruido y a veces revela bugs (una variable calculada y no usada suele indicar un camino incompleto) |
| 4 `f-string` sin placeholders | `pengu_project.py:3623,3873,4292,4477` | 4 líneas | **Quitar el prefijo `f`** | Ruido de pyflakes |
| 101 importaciones sin usar | Repartidas por todo el tooling | ~101 líneas | **Eliminar** tras activar `ruff --select F401` | Ruido; oculta imports que sí importan |
| `pengu_folder.py` | Mencionado en el encargo y en documentación potencial | — | **Verificar y corregir la documentación** | **No existe.** Si algún `.md` lo menciona, la mención es fantasma |

### §1.5 `c_bind_stubs/` — verificar antes de decidir

| Aspecto | Estado |
|---------|--------|
| Tamaño | 76 KB |
| Contenido | Stubs de bindings C |
| Referencias | **A verificar** con `grep -rn "c_bind_stubs" --include="*.py" --include="*.yml" --include="*.md" --include="*.sh" .` |

**Decisión:** **NO borrar en Fase 0.** Si `grep` da 0 referencias **y** `regen_std_bindings.py` no lo
usa, entonces:
- **Opción A:** borrarlo.
- **Opción B (recomendada):** conservarlo y añadir un `c_bind_stubs/README.md` de 3 líneas que
  explique qué son y cuándo se regeneran. Es más barato documentar 76 KB que arriesgarse a romper un
  flujo de regeneración poco usado.

**Kill switch obligatorio:** el `grep` anterior **debe** devolver 0 referencias **y** hay que
ejecutar `regen_std_bindings.py` en modo dry-run si existe esa opción. Si hay cualquier duda, no
borrar.

### §1.6 Archivos que **NO** se deben tocar (aunque parezcan candidatos)

| Archivo | Por qué parece candidato | Por qué conservarlo |
|---------|-------------------------|---------------------|
| `pengu_dce.py` (raíz, 491 B) | "Es un duplicado de `pengu_parser/pengu_dce.py`" | **Es un shim deliberado**: reexporta 4 símbolos con `__all__`, lo importa `tests/test_dce_tcc_pch.py:12` y lo referencia `docs/PERFORMANCE.md:163`. **❌ REFUTADO como código muerto.** Mejor: añadirle un docstring que diga "usa `pengu_parser.pengu_dce`" |
| `README_RELEASE.md` | "Es un README duplicado" | Es documentación de release; se **mueve** a `docs/`, no se borra (§1.3) |
| `std_c/*.h` (incluidos headers con `TODO` de terceros) | "Tienen 68 TODO/FIXME" | Son **headers de terceros vendorizados** (miniaudio, raygui, xxhash, imago, …). Sus TODOs no son deuda nuestra y modificarlos impide actualizar la librería |
| `pengu_parser/pengu_runtime.c` | "Hay otro `pengu_runtime.c` en la raíz" | **Este es el real** (68 373 B). Es el que elimina la ambigüedad, borrando el de la raíz |
| `AUDIT_1.0.md`, `ROADMAP_2.0.md`, `CLEANUP_PLAN.md` | "La raíz ya tiene muchos `.md`" | Son los **entregables de esta auditoría**; viven en la raíz por decisión explícita del encargo |
| `tests/__init__.py`, `pengu_parser/__init__.py`, `pengu_lsp/__init__.py` | "Vacíos o casi" | Son marcadores de paquete **necesarios** para los imports relativos y para `pyinstaller` |
| `std/`, `std_c/` | "6.5 MB de headers" | Fuente de verdad de los bindings C; sin ellos no compila la stdlib |

---

## §2. `.gitignore` propuesto

### §2.1 Diff contra el actual

El `.gitignore` actual tiene 1 385 B y es de **calidad alta**: cubre `extern/`, `build/`, `dist/`,
`pengu_build/`, `scratch/`, `pyinstaller_work/`, bytecode, entornos, Node/VS Code, IDE, SO, logs,
`*.profraw`, `*.lcov`, `cscope.out`. La propuesta es **mínima y justificada**, no una reescritura.

```diff
--- a/.gitignore
+++ b/.gitignore
@@ -0,0 +1,2 @@
+# Audit deliverables for the 1.0 review (AUDIT_1.0.md / ROADMAP_2.0.md / CLEANUP_PLAN.md are
+# intentionally tracked; nothing to add here for them)
@@
 # External C libraries (downloaded automatically by make_release.py / extern_manifest.py)
 extern/
 
 prompt.md
+
+# ------------------------------------------------------------------------------
+# Editor / tooling state that has appeared in practice but is not yet covered
+# ------------------------------------------------------------------------------
+.clangd/
+.cache/clangd/
+compile_commands.json
+
+# Lua/Neovim LSP client state and debug logs from 'pengu lsp'
+.pengu-lsp/
+*.pengu-lsp.log
+
+# Distribution artefacts produced by 'pengu bind' / 'pengu doc' / 'pengu assets'
+docs/api/
+**/pengu_doc_out/
+
+# Wheel/sdist metadata produced if the toolchain is ever packaged
+*.egg-info/
+build/lib/
+dist/*.whl
+
+# Coverage artefacts (the tooling may adopt pytest-cov; see ROADMAP_2.0 item 8.6)
+.coverage
+.coverage.*
+coverage.xml
+htmlcov/
+*.lcov
+
+# macOS / Windows leftovers beyond what is already covered
+*.local
+*.lnk
+ehthumbs.db
+$RECYCLE.BIN/
@@
 # Python Bytecode & Cache
 __pycache__/
 *.py[cod]
 *$py.class
 *.egg-info/
 .eggs/
 *.egg
 .pytest_cache/
 .coverage
 .coverage.*
 htmlcov/
 .tox/
 .nox/
 .mypy_cache/
 .ruff_cache/
+
+# Type-checker caches that will appear once mypy is added (ROADMAP_2.0 item 8.3)
+.pytype/
+.pyre/
+
+# C/C++ build detritus from manual experimentation
+*.gcda
+*.gcno
+*.gcov
+*.dSYM/
+vgrind.log*
+perf.data*
```

### §2.2 Justificación línea por línea de lo **añadido**

| Línea añadida | Justificación |
|---------------|---------------|
| `.clangd/`, `.cache/clangd/` | El repo tiene un `compile_commands.json` (lo genera `build_compile_commands`, `pengu_project.py:1387`), así que es esperable que los contribuidores usen clangd; su caché no debe rastrearse |
| `compile_commands.json` | **Generado** por el CLI. Hoy no está cubierto y es un archivo de build que cambiaría en cada compilación |
| `.pengu-lsp/`, `*.pengu-lsp.log` | Estado y logs de depuración del LSP; el servidor ya escribe en stderr y puede escribir logs |
| `docs/api/` | Salida propuesta para el generador de referencia de API (item 7.13 del roadmap); es contenido **generado** |
| `**/pengu_doc_out/` | Salida de `pengu doc`; generada |
| `*.egg-info/`, `build/lib/`, `dist/*.whl` | `*.egg-info/` ya está en el archivo; se añaden las rutas de packaging por si el toolchain se empaqueta como wheel |
| `.coverage`, `.coverage.*`, `coverage.xml`, `htmlcov/`, `*.lcov` | Parcialmente presentes (`.coverage`, `htmlcov/`, `*.lcov` ya están). Se añade `coverage.xml` y se mantienen, porque el roadmap propone adoptar `pytest-cov` |
| `*.local`, `*.lnk`, `ehthumbs.db`, `$RECYCLE.BIN/` | Restos de macOS/Windows que no estaban cubiertos; el proyecto soporta Windows (MinGW) y macOS |
| `.pytype/`, `.pyre/` | Cachés de type checkers alternativos; se adoptará `mypy` (`.mypy_cache/` ya está) y estas son las de las alternativas |
| `*.gcda`, `*.gcno`, `*.gcov` | Artefactos de cobertura de C; el runtime es C y se puede instrumentar localmente |
| `*.dSYM/` | Símbolos de depuración de macOS; el proyecto publica un artefacto macOS |
| `vgrind.log*`, `perf.data*` | Salidas de valgrind/perf que los contribuidores generan al perfilar el runtime (el repo ya tiene un job de valgrind) |

### §2.3 Lo que **NO** se añade (y por qué)

| Candidato | Por qué **no** |
|-----------|----------------|
| `*.md` sueltos o `docs/archive/` | Los documentos históricos **deben** rastrearse (son la memoria del proyecto); se **mueven**, no se ignoran |
| `AUDIT_1.0.md`, `ROADMAP_2.0.md`, `CLEANUP_PLAN.md` | Son entregables explícitos del encargo; rastrearlos es el objetivo |
| `std_c/` | Es fuente, no artefacto: los bindings dependen de esos headers |
| `tests/compliance/`, `tests/migration/` | Van a existir y son fuente (item 8.4/8.5) |
| `prompt.md` | **Ya está ignorado** en el archivo actual (línea 8) y es correcto: contiene el encargo, no el proyecto |
| `*.csv` (global) | **Ya está** en el actual (`*.csv`) y es deliberadamente amplio; mantenerlo |
| Un patrón para `pengu_runtime.c` | Sería un parche para ocultar el archivo de 0 bytes en vez de borrarlo. **Borrar es la solución correcta** |

### §2.4 Verificación de que el `.gitignore` propuesto no rompe nada

```bash
# 1. Ningún archivo rastreado debe quedar ignorado por las reglas nuevas
git ls-files | git check-ignore --stdin --no-index || echo "ninguno ignorado (correcto)"

# 2. Las rutas nuevas no deben capturar fuentes reales
for p in .clangd .cache/clangd compile_commands.json .pengu-lsp docs/api pengu_doc_out \
         '*.gcda' '*.gcno' '*.dSYM' 'perf.data'; do
  printf "%-24s -> " "$p"; git check-ignore -v "$p" 2>/dev/null || echo "(no ignorado)"
done

# 3. El árbol debe quedar limpio tras borrar las cachés de §1.1
git status --short
```

---

## §3. Reorganización de directorios

### §3.1 Principio y restricción dura

**Restricción dura:** no romper **ningún** import, test, workflow ni la invocación del CLI.
Concretamente, hay que preservar:

| Invariante | Por qué |
|-----------|---------|
| `import pengu_parser` y `from pengu_parser.pengu_checker import PenguChecker` funcionan | Los usan ~130 archivos de test y el LSP |
| `python pengu_project.py <sub>` funciona desde la raíz y desde cualquier directorio | Es la entrada del CLI y está en `pengu.bat`/`pengu` (scripts instalados por PyInstaller) |
| `pengu_project.main()` es importable | Lo usan los tests de CLI vía `subprocess` y algunos vía import |
| `from pengu_bind import HeaderParseError, generate_bind_file` funciona | `pengu_project.py:5090` |
| `from pengu_cache import grammar_digest, parser_cache_path` funciona | Lo importa **lazy** `pengu_parser/pengu_parser.py:106` dentro de un `try` |
| `from pengu_paths import find_version_file` funciona | `pengu_version.py:44` |
| `.github/workflows/*.yml` invocan `python build_runtime.py`, `python pengu_project.py`, `pytest tests/` | Cualquier movimiento de estos archivos rompe CI |
| `make_release.py` y `pyinstaller` localizan sus módulos por ruta relativa a la raíz | `ROOT_DIR = os.path.dirname(os.path.abspath(__file__))` en varios módulos |

**Debido a `ROOT_DIR`:** mover un módulo que calcula `ROOT_DIR` desde su propia ubicación **rompe la
detección de la raíz**. `pengu_paths.py`, `pengu_version.py`, `build_runtime.py`, `make_release.py` y
`pengu_project.py` calculan la raíz así (o la infieren). **Cualquier movimiento obliga a usar
`pathlib(__file__).parent.parent` y a verificar `find_version_file()`.**

### §3.2 Propuesta A (recomendada) — reorganización quirúrgica

Minimiza el riesgo: **no mueve ningún módulo Python**. Solo saca ruido de la raíz.

```
PenguScript/
├── pengu_parser/            # SIN CAMBIOS — compilador (27 204 líneas)
├── pengu_lsp/               # SIN CAMBIOS — LSP (4 144 líneas)
├── std/                     # SIN CAMBIOS — 52 módulos
├── std_c/                   # SIN CAMBIOS — headers C de terceros
├── benches/                 # SIN CAMBIOS
├── tests/                   # SIN CAMBIOS (+ compliance/ y migration/ en el roadmap)
├── scripts/                 # SIN CAMBIOS
├── extern/                  # gitignored
├── build/                   # gitignored
├── .github/                 # SIN CAMBIOS
├── docs/
│   ├── README.md            # NUEVO — índice de documentación
│   ├── ARCHITECTURE.md      # NUEVO (roadmap 7.9)
│   ├── ABI.md               # NUEVO (roadmap 7.10)
│   ├── CROSS_COMPILATION.md # NUEVO (roadmap 7.11)
│   ├── RELEASE.md           # NUEVO (roadmap 9.10)
│   ├── DEPRECATIONS.md      # NUEVO (roadmap 6.15)
│   ├── FUZZING.md           # ya existe
│   ├── PERFORMANCE.md       # ya existe
│   ├── PENGU_BUILD.md       # MOVIDO desde la raíz
│   ├── README_RELEASE.md    # MOVIDO desde la raíz
│   └── archive/             # NUEVO — documentos históricos
│       ├── README.md        # NUEVO — "documentos históricos, no normativos"
│       ├── AUDIT_RESPONSE.md
│       ├── PRODUCTION_READINESS.md
│       ├── P1_PROGRESS.md
│       ├── P2_PROGRESS.md
│       ├── CRITICALS_PROGRESS.md
│       ├── Plan.md
│       └── roadmap.md
├── pengu_*.py               # SIN CAMBIOS (16 módulos de tooling)
├── pengu_runtime.h          # SIN CAMBIOS
├── build_runtime.py         # SIN CAMBIOS
├── extern_manifest.py       # SIN CAMBIOS
├── make_release.py          # SIN CAMBIOS
├── regen_std_bindings.py    # SIN CAMBIOS
├── migrate_manual_bindings.py # SIN CAMBIOS
├── pengu_raymath.py         # SIN CAMBIOS
├── VERSION                  # SIN CAMBIOS
├── requirements.txt         # SIN CAMBIOS
├── LANGUAGE.md              # SIN CAMBIOS (raíz, por convención)
├── LANGUAGE_Spanish.md      # SIN CAMBIOS
├── CHEATSHEET.md            # SIN CAMBIOS
├── README.md                # SIN CAMBIOS
├── CHANGELOG.md             # SIN CAMBIOS
├── BENCHMARKS.md            # SIN CAMBIOS
├── SECURITY.md              # SIN CAMBIOS
├── RELEASE_CHECKLIST.md     # SIN CAMBIOS
├── ROADMAP_1.0.0.md         # SIN CAMBIOS (histórico)
├── ROADMAP_2.0.md           # SIN CAMBIOS (vivo)
├── AUDIT_1.0.md             # SIN CAMBIOS
├── CLEANUP_PLAN.md          # SIN CAMBIOS
├── CONTRIBUTING.md          # NUEVO (roadmap 7.8)
├── MIGRATION.md             # NUEVO (roadmap 7.12)
├── LICENSE                  # SIN CAMBIOS
├── .gitignore / .gitattributes
└── vscode-extension/        # SIN CAMBIOS
```

**Resultado:** los `.md` de la raíz bajan de **20 a 14**; la raíz pierde 9 archivos
(7 históricos + 2 movidos) y gana 3 entregables nuevos. **Cero cambios en código Python.**

**Ventaja decisiva:** riesgo casi nulo y se ejecuta en horas.

### §3.3 Propuesta B (estructural) — paquetes, para 1.1

Reorganización profunda, **explícitamente diferida a 1.1** porque toca imports, `ROOT_DIR`,
`pyinstaller` y los workflows:

```
penguscript/
├── cli/                     # pengu_project.py (5207 líneas) dividido en 6 módulos
│   ├── __init__.py
│   ├── parser.py            # create_cli_parser (318 líneas)
│   ├── project.py           # ProjectConfig, init_project (326)
│   ├── builder.py           # PenguBuilder, bundle, cache
│   ├── runner.py            # run_script (221), watch, eval
│   ├── assets.py            # integración con pengu_assets
│   ├── compile_db.py        # build_compile_commands (322)
│   └── gc.py                # gestión de caché
├── compiler/                # contenido actual de pengu_parser/
├── runtime/
│   ├── pengu_runtime.h
│   └── pengu_runtime.c      # movido desde pengu_parser/
├── lsp/                     # contenido actual de pengu_lsp/
├── stdlib/                  # std/ + std_c/
├── tests/
└── scripts/
```

**Por qué se difiere:**

| Obstáculo | Detalle |
|-----------|---------|
| `pengu_parser` es el **nombre público** del paquete | Renombrarlo a `compiler` rompe los ~130 archivos de test que hacen `from pengu_parser...`, el LSP, y probablemente la documentación |
| Los scripts `pengu`/`pengu.bat` invocan un entry point concreto | Hay que regenerar la configuración de PyInstaller y verificar las 3 plataformas |
| `pengu_runtime.c` movido de `pengu_parser/` cambia `build_runtime.py:1174` y el `#include` del bundle | Toca la ruta más crítica del build |
| `ROOT_DIR` en 5 módulos | Cada movimiento requiere recalcular la raíz y verificar `find_version_file()` |
| 20 `.md` referencian rutas de archivo | Hay que actualizarlas todas |
| Los 5 workflows referencian rutas | Ídem |

**Estimación de Propuesta B:** **L** (1-2 semanas) + **L** de verificación cross-platform. **No es
prerequisito de 1.0** y hacerlo junto con los fixes de la Fase 1 multiplicaría el riesgo (ver
`ROADMAP_2.0.md` riesgo G6).

### §3.4 Comparación de las dos propuestas

| Criterio | Propuesta A (quirúrgica) | Propuesta B (estructural) |
|----------|-------------------------|---------------------------|
| Riesgo de romper imports | **Nulo** (no mueve Python) | Alto |
| Riesgo de romper workflows | **Nulo** | Alto |
| Beneficio inmediato | Ruido de la raíz (-9 archivos) | Navegabilidad real |
| Es prerequisito de 1.0 | **Sí** (parte de Fase 0) | No |
| Estimación | **S** (2 días) | **L-XL** (2-3 semanas) |
| Cuándo | Ahora | 1.1 |
| Revierte el problema de §12.2 (archivo de 5207 líneas) | No | Sí |

**Recomendación: hacer A ahora y B en 1.1**, después de que la suite de tests tenga un test de
contrato del CLI (item 8.8) que detecte cualquier regresión de la reorganización.

---

## §4. Archivos huérfanos

### §4.1 Análisis de referencias del tooling de la raíz

Método: para cada `.py` de la raíz y de `pengu_parser/`, contar referencias desde otros archivos
(`grep -rn "<basename>" --include="*.py" --include="*.yml" --include="*.md"`).

| Archivo | Referenciado por | ¿Huérfano? |
|---------|-----------------|-----------|
| `pengu_project.py` | El CLI (`python pengu_project.py`), PyInstaller, los tests de CLI vía `subprocess` | No — es la entrada |
| `pengu_bind.py` | `pengu_project.py:5090` (import local); `pengu_bind.py:1567-1617` (`main()` muerto) | **Parcialmente**: el módulo sí, su `main()` no |
| `pengu_doc.py` | El subcomando `doc` de `pengu_project.py` | No |
| `pengu_assets.py` | El subcomando `assets` | No |
| `pengu_cache.py` | `pengu_project.py` y, **lazy**, `pengu_parser/pengu_parser.py:106` | No — es crítico para el arranque |
| `pengu_lock.py` | `pengu_project.py` (`pengu verify`, `--locked`, `--frozen`) | No |
| `pengu_paths.py` | `pengu_version.py:44` y la lógica FHS | No |
| `pengu_semver.py` | `pengu_project.py` (resolución de versiones de deps) | No |
| `pengu_tcc.py` | `pengu_project.py` (`doctor`, `pick_dev_compiler`) | No |
| `pengu_version.py` | El CLI (`-V`), el codegen, el LSP | No — es la fuente única de versión |
| `pengu_dce.py` (raíz) | `tests/test_dce_tcc_pch.py:12`, `docs/PERFORMANCE.md:163` | **No** — es un shim deliberado |
| `pengu_raymath.py` | `std/raymath.d.pengu` (`include "pengu_raymath.h"` y `link "pengu_raymath"`) y `build_runtime.py` | No |
| `build_runtime.py` | Los 5 workflows, `make_release.py`, el subcomando `doctor` | No — **crítico** |
| `extern_manifest.py` | `make_release.py:96-100` | Sí, **solo** desde `make_release.py`. No es huérfano, pero es de un solo consumidor |
| `make_release.py` | `.github/workflows/release.yml` | No |
| `regen_std_bindings.py` | Script manual de mantenimiento | **Herramienta manual** — verificar que esté documentado |
| `migrate_manual_bindings.py` | Script manual de migración puntual | **Candidato a `docs/archive/` o `scripts/`** si la migración ya se completó |
| **`pengu_folder.py`** | **Nada** | **NO EXISTE** — si algún doc lo menciona, es documentación fantasma |

### §4.2 Los dos únicos huérfanos reales de código

| Archivo | Referencias | Veredicto |
|---------|-------------|-----------|
| `migrate_manual_bindings.py` (8 466 B) | Solo se referencia a sí mismo | **Herramienta de un solo uso.** Verificar si la migración manual de bindings ya se completó (probablemente sí, dado que los 52 módulos existen). Si es así: mover a `scripts/` o a `docs/archive/`, **no borrar** (documenta un paso histórico de migración) |
| `pengu_bind.py:main()` | 0 referencias | **Código muerto** → eliminar (§1.4) |

**Los scripts de mantenimiento manual (`regen_std_bindings.py`, `migrate_manual_bindings.py`) no son
huérfanos en el sentido de "código muerto": son herramientas que se ejecutan a mano.** La acción
correcta es **consolidarlos en `scripts/`** (§6) y documentarlos en `CONTRIBUTING.md`.

### §4.3 Herramientas de análisis de huérfanos usadas

Para que el resultado sea reproducible, esto es lo que se ejecutó:

```bash
# 1. Referencias por basename desde todo el código Python
for f in *.py pengu_parser/*.py; do
  b=$(basename "$f" .py)
  n=$(grep -rn "\b$b\b" --include="*.py" --include="*.yml" --include="*.md" . 2>/dev/null \
      | grep -v extern | grep -v "^./$f" | wc -l)
  printf "%-32s %s\n" "$b" "$n"
done | sort -k2 -n | head -20

# 2. Módulos definidos pero nunca importados (AST)
.venv/bin/python - <<'EOF'
import ast, pathlib
mods = {p.stem: p for p in pathlib.Path(".").glob("*.py")}
mods.update({p.stem: p for p in pathlib.Path("pengu_parser").glob("*.py")})
imported = set()
for p in list(pathlib.Path(".").glob("*.py")) + list(pathlib.Path("pengu_parser").glob("*.py")) \
       + list(pathlib.Path("pengu_lsp").glob("*.py")):
    try: t = ast.parse(p.read_text())
    except Exception: continue
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            for a in n.names: imported.add(a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom) and n.module:
            imported.add(n.module.split(".")[0])
for name in sorted(set(mods) - imported):
    print("nunca importado:", name, mods[name].stat().st_size, "B")
EOF
```

### §4.4 Huérfanos en la stdlib (referencia cruzada con `AUDIT_1.0.md` §8)

Aunque pertenecen a la Fase 6 del roadmap, se listan aquí porque son el mismo tipo de hallazgo:

| Módulo | Referencias en `std/` | Test que lo cubre | Veredicto |
|--------|----------------------|------------------|-----------|
| `std/celeris.pengu` (96 LOC) | **0** | Solo `tests/test_ffi_libs.py::test_celeris_wrapper_hashes` | **Huérfano de facto** |
| `std/xlsx.pengu` (102 LOC) | **0** | Solo `test_ffi_libs.py::TestXlsxio::test_pengu_wrapper_writes_xlsx` | **Huérfano opt-in** |
| `std/trial.pengu` (136 LOC) | **0** | Solo `tests/std_programs/test_trial.pengu` | **Huérfano**; duplica parte de `ward` |

**Acción:** `ROADMAP_2.0.md` item 6.14. **No borrar** sin decidir antes si son opt-in documentados.

---

## §5. Dependencias circulares

### §5.1 Resultado: **0 ciclos de importación**

El enunciado pedía detectarlos. **No existen.** Verificación de los cinco pares sospechosos:

| Par | ¿Ciclo? | Evidencia |
|-----|---------|-----------|
| `pengu_project` ↔ `pengu_bind` | **No** | `grep -n "pengu_project" pengu_bind.py` → **0 coincidencias**. La dependencia es en una sola dirección: `pengu_project.py:5090` hace `from pengu_bind import HeaderParseError, generate_bind_file` **dentro** de la rama del subcomando `bind` (import perezoso) |
| `pengu_checker` ↔ `pengu_infer` | **No** | `pengu_checker` importa `TypeInferrer`; el inferrer recibe el `SymbolTable` **por inyección** (`TypeInferrer(self.symbols, …)`) y no importa el checker. Dependencia unidireccional |
| `pengu_codegen` ↔ `pengu_checker` | **No** | `pengu_codegen` importa `pengu_types`, `pengu_symbols`, `pengu_dce`. **No** importa `pengu_checker` |
| `pengu_parser` ↔ `pengu_lsp` | **No** | El LSP importa el parser (`pengu_lsp/server.py:431` instancia `PenguChecker`); el parser no conoce el LSP |
| `pengu_types` ↔ otros | **No** | `pengu_types` define los tipos y no importa módulos hermanos del compilador |
| `pengu_cache` ↔ `pengu_parser` | **No** | `pengu_parser.py:106` importa `pengu_cache` **lazy** dentro de un `try/except` con fallback; `pengu_cache` no importa el parser |

### §5.2 El patrón que evita los ciclos (y que hay que preservar)

El proyecto usa **tres técnicas** que mantienen el grafo acíclico. Documentarlas evita que se pierdan:

1. **Import perezoso en función** (`pengu_project.py:5090`): rompe el único ciclo potencial
   (`project` → `bind`) porque el import solo ocurre cuando se ejecuta el subcomando.
2. **Inyección de dependencias** (`TypeInferrer(symbols, …)`): `pengu_infer` no necesita importar
   `pengu_checker` porque recibe la tabla por parámetro. Es la técnica que hace que el archivo de
   238 KB no dependa del de 380 KB.
3. **`try/except ImportError` con fallback** (`pengu_parser.py:106`, `pengu_version.py:44`): permite
   que el paquete funcione tanto en el checkout como en el binario congelado por PyInstaller, donde
   los módulos de la raíz pueden no estar en el mismo lugar.

### §5.3 Riesgo futuro detectado

| Riesgo | Detalle | Mitigación |
|--------|---------|-----------|
| La Propuesta B (§3.3) puede **introducir** ciclos | Al dividir `pengu_project.py` en `pengu_cli/*`, es fácil que `builder.py` importe `runner.py` e `runner.py` importe `builder.py` | Documentar el grafo permitido en `docs/ARCHITECTURE.md` y añadir un test que detecte ciclos (ver §5.4) |
| Mover `pengu_runtime.c` a `runtime/` | Podría crear un acoplamiento entre `build_runtime.py` y `make_release.py` si ambos calculan rutas | Un solo módulo de rutas (`pengu_paths.py`) como fuente única |

### §5.4 Test propuesto para prevenir ciclos

```python
# tests/test_no_import_cycles.py
import ast, pathlib, sys

def build_graph(root: pathlib.Path) -> dict:
    graph = {}
    for p in list(root.glob("*.py")) + list((root / "pengu_parser").glob("*.py")) \
           + list((root / "pengu_lsp").glob("*.py")):
        deps = set()
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    deps.add(a.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom):
                # relative import inside pengu_parser/ -> sibling module
                if n.level and n.module:
                    deps.add(n.module.split(".")[0])
                elif n.module:
                    deps.add(n.module.split(".")[0])
        graph[p.stem] = {d for d in deps if d in {q.stem for q in root.rglob("*.py")}}
    return graph

def test_no_cycles():
    root = pathlib.Path(__file__).resolve().parent.parent
    g = build_graph(root)
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in g}
    stack = []

    def visit(n):
        color[n] = GREY
        stack.append(n)
        for m in g.get(n, ()):
            if color.get(m) == GREY:
                raise AssertionError(f"import cycle: {' -> '.join(stack + [m])}")
            if color.get(m) == WHITE:
                visit(m)
        stack.pop()
        color[n] = BLACK

    for n in g:
        if color[n] == WHITE:
            visit(n)
```

**Nota:** el import perezoso de `pengu_project.py:5090` aparecería en este grafo como una arista
estática aunque en tiempo de ejecución no se recorra. Como el grafo **ya es acíclico**, el test pasa
hoy; si en el futuro alguien cierra el ciclo, el test lo detecta.

---

## §6. Consolidaciones

### §6.1 Scripts sueltos que deberían ir juntos

| Actual | Propuesta | Justificación |
|--------|-----------|---------------|
| `regen_std_bindings.py` (raíz) | `scripts/regen_std_bindings.py` | Es una herramienta de mantenimiento manual, no parte del toolchain que usa el usuario |
| `migrate_manual_bindings.py` (raíz) | `scripts/migrate_manual_bindings.py` o `docs/archive/` | Migración puntual ya completada (los 52 módulos existen) |
| `pengu_raymath.py` (raíz) | **Dejar en la raíz** ⚠️ | Lo referencia `std/raymath.d.pengu` (`include "pengu_raymath.h"`) y `build_runtime.py`; **moverlo rompe la resolución del header** |
| `scripts/bench.sh` | **Dejar** | Coherente con `scripts/` |
| `scripts/release_version.py` | **Dejar**; o fusionar con `pengu_semver.py` | `release_version.py` y `pengu_semver.py` (7 228 B) solapan en parsing de versiones → ver §6.2 |
| `scripts/smoke.py` | **Dejar** | Smoke test |
| `scripts/fuzz/` | **Dejar** | Coherente con `fuzz.yml` |

**Resultado:** mover solo **2** archivos, con su referencia en `CONTRIBUTING.md`.

### §6.2 Herramientas que se solapan

| Par | Solapamiento | Decisión |
|-----|-------------|----------|
| `scripts/release_version.py` ↔ `pengu_semver.py` | Ambos manejan versiones semver. `pengu_semver.py` está probado y es parte del toolchain (resolución de deps); `release_version.py` es un script de release | **Hacer que `release_version.py` importe `pengu_semver`** en vez de reimplementar; verificar con `grep -n "def.*version\|re.match.*\\\\d" scripts/release_version.py` |
| `pengu_dce.py` (raíz, shim) ↔ `pengu_parser/pengu_dce.py` (impl) | Duplicación de superficie | **Mantener** (shim deliberado, §1.6) pero añadir docstring: *"Compatibility re-export of `pengu_parser.pengu_dce`; import from there in new code."* |
| `pengu_bind.py` ↔ `pengu_project.py` (subcomando `bind`) | Dos CLI para un subcomando | **Eliminar `pengu_bind.main()`** (§1.4) |
| `pengu_project.py` (5207 líneas) | 6 responsabilidades | Dividir en 1.1 (Propuesta B, §3.3) |
| `scripts/fuzz/fuzz_common.py` ↔ `pengu_parser/pengu_parser.py` | El fuzzer probablemente reimplementa el parseo de errores | Verificar con `grep -n "except\|ParseError" scripts/fuzz/fuzz_common.py`; si reimplementa, importar del parser |
| `docs/FUZZING.md` ↔ `.github/workflows/fuzz.yml` | Duplicación de la política de fuzzing, ya divergente (72 h vs 12 h) | **Un solo origen de verdad**: el workflow; `docs/FUZZING.md` referencia los valores reales (item 9.5) |
| `docs/PERFORMANCE.md` ↔ `BENCHMARKS.md` ↔ `benches/` | Tres fuentes de números | Unificar: `benches/` produce los números, `BENCHMARKS.md` los publica, `PERFORMANCE.md` explica la metodología. Hoy `BENCHMARKS.md` y `PERFORMANCE.md` pueden divergir |
| `ROADMAP_1.0.0.md` (65 KB) ↔ `roadmap.md` (2 KB) ↔ `Plan.md` (7 KB) | Tres roadmaps | `ROADMAP_1.0.0.md` a `docs/archive/`; `roadmap.md` y `Plan.md` a `docs/archive/` (§1.2) |
| `PRODUCTION_READINESS.md` ↔ `RELEASE_CHECKLIST.md` ↔ `CRITICALS_PROGRESS.md` | Tres estados de release | `RELEASE_CHECKLIST.md` es el vivo; los otros dos a `docs/archive/` |
| `README.md` ↔ `README_RELEASE.md` ↔ `PENGU_BUILD.md` | Solapamiento en build/instalación | `README.md` manda; los otros dos a `docs/` (§1.3) |

### §6.3 Candidatos a consolidación **diferida** (no en Fase 0)

| Consolidación | Por qué se difiere |
|---------------|-------------------|
| Dividir `pengu_project.py` | Requiere que exista el test de contrato de CLI (item 8.8) para detectar regresiones; Propuesta B |
| Dividir los 3 archivos grandes del compilador | Ver `ROADMAP_2.0.md` riesgo G6: **prohibido refactorizar antes de cerrar los bloqueantes** |
| Fusionar `LANGUAGE.md` y `LANGUAGE_Spanish.md` | La cobertura bilingüe es un activo; la política correcta es declarar el inglés canónico (item 7.14), no fusionar |
| Unificar `std/tally` y `std/loom` | Requiere decisión de API y periodo de deprecación (item 6.5) |

---

## §7. Plan de ejecución

### §7.1 Orden concreto con tests de verificación por paso

Cada paso **termina con una verificación** y **no se empieza el siguiente si falla**. La suite
completa (910 s) se ejecuta al final de cada **bloque**, no en cada paso.

#### Bloque A — Higiene sin riesgo (≈2 horas)

| Paso | Acción | Verificación |
|------|--------|--------------|
| A1 | `git rm pengu_runtime.c` (raíz, 0 bytes) | `git cat-file -s HEAD:pengu_runtime.c` falla tras el commit; `grep -n "pengu_runtime.c" CHEATSHEET.md` para actualizar la mención |
| A2 | Actualizar `CHEATSHEET.md:64` para no sugerir el archivo de la raíz | `sed -n '64p' CHEATSHEET.md` menciona `pengu_parser/pengu_runtime.c` |
| A3 | Borrar los 7 `__pycache__` propios y `.pytest_cache/` | `find . -name __pycache__ -not -path "./extern/*" \| wc -l` → 0; `ls -d .pytest_cache` falla |
| A4 | `git status --short` | Sin archivos inesperados; solo los borrados de A1 |
| A5 | Commit: `chore(cleanup): drop the 0-byte root pengu_runtime.c and stale caches` | `git show --stat` muestra exactamente 1 borrado rastreado |

#### Bloque B — Documentación (≈2 horas)

| Paso | Acción | Verificación |
|------|--------|--------------|
| B1 | Crear `docs/archive/` y `docs/archive/README.md` | El README declara que son históricos y no normativos |
| B2 | `git mv` de los 7 documentos históricos a `docs/archive/` | `ls *.md \| wc -l` baja de 20 a 13 |
| B3 | `git mv PENGU_BUILD.md docs/` y `git mv README_RELEASE.md docs/` | `ls PENGU_BUILD.md README_RELEASE.md` falla |
| B4 | `grep -rn` de cada nombre movido en `.md`/`.yml`/`.py` y actualizar enlaces | `grep -rn "PENGU_BUILD\|README_RELEASE\|Plan\.md\|roadmap\.md" --include="*.md" --include="*.yml" \| grep -v docs/archive` → solo rutas nuevas |
| B5 | Crear `docs/README.md` (índice) | Lista cada documento vivo con una frase de propósito |
| B6 | Verificar que la suite sigue verde | `pytest tests/ -q -p no:cacheprovider --timeout=900` → mismas cifras |
| B7 | Commit: `docs(cleanup): archive process documents, move build docs into docs/` | — |

#### Bloque C — Código muerto (≈3 horas)

| Paso | Acción | Verificación |
|------|--------|--------------|
| C1 | Eliminar `pengu_bind.py:1567-1617` (`main()` + argparse) | `grep -c "def main" pengu_bind.py` → 0; `python pengu_project.py bind <header>` sigue funcionando |
| C2 | Añadir `Set` al import de tipos en `pengu_infer.py`; añadir `Tree` en `pengu_project.py` | `pyflakes pengu_parser/pengu_infer.py pengu_project.py \| grep -c "undefined name"` → 0 |
| C3 | Eliminar las 10 variables locales sin usar y los 4 `f` sin placeholder | `pyflakes pengu_parser/*.py pengu_lsp/*.py *.py \| wc -l` baja de 132 a ~118 |
| C4 | Añadir docstring al shim `pengu_dce.py` | El docstring menciona `pengu_parser.pengu_dce` |
| C5 | `pytest tests/test_dce_tcc_pch.py tests/test_cli_tools.py -q` | Verde |
| C6 | Commit: `chore(cleanup): drop dead argparse in pengu_bind, fix pyflakes noise` | — |

#### Bloque D — `.gitignore` (≈1 hora)

| Paso | Acción | Verificación |
|------|--------|--------------|
| D1 | Aplicar el diff de §2.1 | `git diff .gitignore` muestra solo adiciones |
| D2 | Verificar que nada rastreado queda ignorado | `git ls-files \| git check-ignore --stdin --no-index` → vacío |
| D3 | Verificar el árbol | `git status --short` limpio |
| D4 | Commit: `chore(cleanup): cover clangd, coverage, coverage-C and packaging artefacts` | — |

#### Bloque E — Decisiones pendientes (≈1 hora, pueden requerir input)

| Paso | Acción | Verificación |
|------|--------|--------------|
| E1 | `grep -rn "c_bind_stubs"` → decidir borrar o documentar (§1.5) | Si 0 referencias **y** no lo usa `regen_std_bindings.py`: borrar; si no, añadir `README.md` |
| E2 | Verificar si `migrate_manual_bindings.py` ya cumplió su propósito | Si sí: `git mv` a `docs/archive/` o `scripts/` |
| E3 | Verificar que `pengu_folder.py` no se menciona en ningún doc | `grep -rn "pengu_folder" --include="*.md" --include="*.py" . \| grep -v extern` → 0; si aparece, corregir la mención |
| E4 | Mover `regen_std_bindings.py` y `migrate_manual_bindings.py` a `scripts/` si E2 lo confirma | `grep -rn "regen_std_bindings\|migrate_manual_bindings" --include="*.yml" --include="*.md" \| grep -v scripts/` → solo rutas nuevas |
| E5 | Commit: `chore(cleanup): consolidate maintenance scripts under scripts/` | — |

#### Bloque F — Cierre de la Fase 0 (≈15 min, suite completa)

| Paso | Acción | Verificación |
|------|--------|--------------|
| F1 | Suite completa | `pytest tests/ -q -p no:cacheprovider --timeout=900` → **2074 passed, 12 skipped, 2 xfailed, 1 xpassed** (idéntico a la línea base) |
| F2 | Verificar el CLI | `pengu -V`, `pengu doctor`, `pengu check -c <proyecto>`, `pengu build`, `pengu test`, `pengu doc` |
| F3 | Verificar los workflows localmente | Añadir el test de §5.4 (`tests/test_no_import_cycles.py`) y correrlo |
| F4 | Comprobar los números de §0 | `git ls-files \| wc -l` decrece en ≥9; `ls *.md \| wc -l` → 13 |
| F5 | Commit final: `chore(cleanup): phase 0 complete — repository hygiene` | — |

### §7.2 Criterios de aborto (rollback)

| Situación | Acción |
|-----------|--------|
| La suite de tests **baja** en passed o sube en failed respecto a la línea base | `git revert` del último commit del bloque y revisar |
| `pengu <sub>` falla para cualquier subcomando tras un movimiento | `git revert` del bloque B/E |
| `git ls-files \| git check-ignore --stdin --no-index` devuelve algo no vacío | Revisar la regla de `.gitignore` añadida; no commitear hasta que esté corregido |
| Aparece una referencia rota a un documento movido | `grep -rn` exhaustivo y corregir antes de commitear |
| Cualquier duda sobre `c_bind_stubs/` o `migrate_manual_bindings.py` | **No borrar.** Documentar y diferir la decisión |

### §7.3 Lo que **no** se hace en la Fase 0

Explícitamente fuera de alcance, aunque aparezca en este documento:

| Item | Motivo | Dónde se hace |
|------|--------|---------------|
| Dividir `pengu_project.py` (5207 líneas) | Requiere el test de contrato de CLI; riesgo de mezclar refactor con fixes | 1.1 (Propuesta B) |
| Dividir los 3 archivos grandes del compilador | Riesgo G6 del roadmap: prohibido antes de cerrar bloqueantes | 1.1+ |
| Consolidar las reglas `guard_*`/`*_no_cast` del grammar | Requiere cambiar el parser y verificar la semántica | Fase 2 |
| Aplicar el style guide a la stdlib | Depende de decisiones de API (bounds, loom/tally) | Fase 6-7 |
| Fusionar `LANGUAGE.md` con su versión española | La cobertura bilingüe es un activo | Fase 7 (política, no fusión) |
| Refactorizar los 5 módulos que calculan `ROOT_DIR` | Ningún movimiento los toca en la Fase 0 | Solo si se hace la Propuesta B |

---

## §8. Resumen ejecutivo del plan de limpieza

| Bloque | Duración | Archivos afectados | Riesgo |
|--------|----------|-------------------|--------|
| A — Higiene sin riesgo | 2 h | 1 borrado rastreado + 8 cachés | **Nulo** |
| B — Documentación | 2 h | 9 movidos + 2 nuevos | **Bajo** (solo enlaces) |
| C — Código muerto | 3 h | 4 archivos, ~120 líneas | **Bajo** (verificado por pyflakes y tests) |
| D — `.gitignore` | 1 h | 1 archivo, ~25 líneas | **Nulo** (verificado con `check-ignore`) |
| E — Decisiones | 1 h | 2-3 archivos | **Medio** (requiere decisión humana) |
| F — Cierre | 15 min + 15 min de suite | 1 test nuevo | **Nulo** |
| **Total** | **~1 día de trabajo** | 15 archivos, 0 líneas de lógica del compilador | **Bajo** |

**Lo más importante de este plan es lo que NO propone:**

- **No** se borra `pengu_dce.py` (es un shim en uso).
- **No** se borra `c_bind_stubs/` sin verificación.
- **No** se mueve ningún módulo Python (evitar `ROOT_DIR` roto).
- **No** se refactoriza `pengu_project.py` (se difiere a 1.1).
- **No** se tocan los headers de terceros en `std_c/`.
- **No** se fusionan los documentos bilingües.
- **No** se activa ninguna regla de `.gitignore` sobre archivos rastreados.

**El hallazgo central de la auditoría de limpieza es que el repositorio está en mucho mejor estado
del que el enunciado suponía:** el `.gitignore` es completo, `extern/`/`build/`/`scratch/`/
`tests_std/` están correctamente gestionados o no existen, `pengu_runtime_original.h` fue
efectivamente eliminado, y **no hay ni un solo ciclo de importación**. El trabajo real se reduce a
sacar 9 documentos de la raíz, borrar un archivo rastreado de 0 bytes, limpiar cachés de Python y
eliminar ~120 líneas de código muerto verificable. Todo eso cabe en **un día** y no toca una sola
línea de la lógica del compilador — que es exactamente la propiedad que hace que este plan sea seguro.

---

## §9. Apéndice — Referencias cruzadas

| Hallazgo de la auditoría | Sección de este plan |
|-------------------------|---------------------|
| `pengu_runtime.c` raíz de 0 bytes (AUDIT §5, §19.6) | §1.1, §7.1-A1 |
| 7 documentos de proceso en la raíz (AUDIT §13.5) | §1.2, §7.1-B2 |
| `pengu_bind.main()` duplicado (AUDIT §6.9, §19.6) | §1.4, §7.1-C1 |
| `organize_imports_action` sin conectar (AUDIT §7.4) | §1.4 (**conectar**, no borrar) |
| CodeLens inerte (AUDIT §7.3) | §1.4 (**conectar o eliminar**) |
| 4 `undefined name` de pyflakes, 1 real (AUDIT §19.2) | §1.4, §7.1-C2 |
| 10 variables locales muertas + 4 f-strings (AUDIT §19) | §1.4, §7.1-C3 |
| 101 imports sin usar (AUDIT §19) | §1.4 (**tras activar ruff**, Fase 8) |
| `pengu_folder.py` inexistente (AUDIT §12.1) | §4.1, §7.1-E3 |
| `pengu_dce.py` shim **no** es código muerto (AUDIT §12.1) | §1.6, §6.2 |
| `pengu_project.py` de 5207 líneas (AUDIT §12.2, §19.4) | §3.3 (Propuesta B, 1.1) |
| Reglas `guard_*`/`*_no_cast` duplicadas (AUDIT §1.4) | §1.4 (**Fase 2**), §7.3 |
| 0 ciclos de importación (AUDIT §19.5) | §5 |
| `extern/`, `build/`, `scratch/`, `tests_std/` correctamente gestionados (AUDIT §12) | §0.1 |
| 3 módulos huérfanos de stdlib (AUDIT §8) | §4.4 (**no borrar**, decidir en Fase 6) |
| `docs/` infrapoblado (AUDIT §12.3) | §3.2 (Propuesta A) |
| 68 TODO en headers de terceros (AUDIT §19) | §1.6 (**no tocar**) |

