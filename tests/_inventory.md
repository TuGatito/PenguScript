# Inventario de la suite de tests (Fase 0)

Medido en `main` @ `6968118` ("Compiling Fix"), árbol de trabajo limpio.
Máquina: Linux, 36 cores, 31 GB RAM, gcc + clang + cc.
Entorno: `.venv/bin/python` = CPython 3.14.7, pytest 9.1.1, pytest-xdist 3.8.0.

> **Corrección (verificación independiente, §9).** Este documento se midió dos veces,
> en paralelo, por dos sesiones distintas. Las cifras marcadas con ⚠️ abajo estaban
> infladas por coincidencias binarias en `tests/__pycache__/*.pyc`, y la afirmación
> "sin `tcc`" era **falsa**: TCC sí está staged y `pengu_tcc.find_tcc()` lo encuentra.
> Ver §9 para la lista completa de correcciones y la evidencia.

Nada de este documento implica cambios en el código: es solo medición.

---

## 1. Conteos

| Métrica | Valor |
|---|---|
| Archivos `.py` en `tests/` (recursivo) | **237** |
| Archivos `test_*.py` en `tests/` (raíz) | **233** |
| Archivos `.pengu` en `tests/` | **207** |
| Archivos `.pengu` en todo el repo | **324** |
| Tests recogidos (`--collect-only`) | **3573** |
| Líneas `def test_` en `tests/*.py` | 2447 |
| Archivos que usan `subprocess`/`Popen`/`check_output` | **96** ⚠️ (202 incluía 106 `.pyc`) |
| Sitios de llamada a `subprocess` | 338 |
| Archivos que leen C generado (`bundle_c`/`generated_c`) | **10** ⚠️ (151 estaba inflado) |
| Archivos con patrones `assert "..." in <c>` | 93 |
| Archivos que invocan un compilador C por nombre | 59 |
| Sitios `compile_run` / `compile_c` / `run_c` | **462** |
| Archivos sin `subprocess` ni helpers de compilación | 58 |

Estado del objetivo: `tests/*.py` debería bajar de **233 → ≤35 → ≤15**.
El corpus debería crecer de **207 → ≥400 → 5000** `.pengu`.

### Distribución del corpus `.pengu` ya existente

| Directorio | `.pengu` |
|---|---|
| `tests/std_programs/` | 61 |
| `tests/compliance/` | 53 |
| `tests/test_generics/` (+ subdirs) | 35 + 15 |
| `tests/test_string_composition/` | 22 |
| `tests/test_manual_memory/` | 9 |
| `tests/migration/` | 12 |

**Hallazgo:** ya existe un corpus de 207 programas con manifiesto JSON
(`tests/compliance/corpus.json`) y runner (`tests/compliance/run_all.py`).

---

## 2. Tiempo actual

```
.venv/bin/python -m pytest tests -q -p no:cacheprovider --timeout=1200 --durations=30
```

| Métrica | Valor |
|---|---|
| **Tiempo total (run contaminado)** | 2136.05 s = 35 min 36 s |
| **Tiempo total (run limpio, en solitario)** | **2059.04 s = 34 min 19 s** |
| Recogida (`--collect-only`) | 1.84 s |
| Resultado | 3504 passed, 23 skipped, 46 xfailed |
| Exit code | 0 (la suite está verde) |

No hubo contención real entre los dos runs: 36 cores con load ~1,9, y los dos
totales difieren solo un 3,6 %. **El baseline defendible es ~2059 s (34,3 min).**

⚠️ **El enunciado asumía ~15 min. La realidad es 35.6 min — 2.4× peor.**
Cualquier presupuesto basado en "15 min → 90 s" (10×) es en realidad
"35.6 min → 90 s" (24×).

Además, esta medida es **en caliente**: `build/` ya existía con 149 MB de
runtime y librerías precompiladas. Un checkout limpio es más lento.

---

## 3. Top 10 archivos/casos más lentos

De `--durations=30`:

| # | Segundos | Fase | Test |
|---|---|---|---|
| 1 | **130.48** | setup | `test_doc_blocks.py::test_every_marked_block_matches_reality` |
| 2 | 64.79 | call | `test_frontend_no_crash.py::…[LANGUAGE.md]` |
| 3 | 56.18 | call | `test_frontend_no_crash.py::…[LANGUAGE_Spanish.md]` |
| 4 | **49.78** | setup | `test_api_docs.py::test_the_reference_exists_and_covers_every_module` |
| 5 | 36.39 | call | `test_frontend_no_crash.py::…[CHEATSHEET.md]` |
| 6 | 21.40 | call | `test_lsp_stability.py::test_stability_13_requests_on_10k_lines` |
| 7 | 13.08 | call | `test_std_util_backward_compat.py::…[release]` |
| 8 | 12.39 | call | `test_docs_primitive_types.py::test_int_family_is_abi_identical` |
| 9 | 11.97 | call | `test_std_data_backward_compat.py::…[release]` |
| 10 | 11.70 | call | `test_std_invoke_extended.py::test_invoke_extended[release]` |

(Cifras del run limpio de 2059 s.)

Los 10 primeros suman **408 s = 19,8 %** del run limpio.
Los 30 primeros suman **≈590 s = 28,6 %** ⚠️ (el 40 % de antes era del run contaminado).

### Lectura de estos números

- **#1 y #4 son fixtures de módulo, no tests.** Compilan ~197 bloques de
  documentación y regeneran 27 páginas de API **en cada ejecución**, sin caché.
  Son gates de "el artefacto generado coincide con el compilador" disfrazados de
  test. 190 s de 2136 s.
- **#2/#3/#5 (166 s)** lanzan **un subprocess por bloque** de código en los
  `.md`. Tres documentos, ~200 bloques.
- **#6** es un test de estabilidad del LSP con 10 000 líneas.
- **#7–#10 y la cola `test_std_*[release]`** compilan en perfil **release**,
  que es mucho más caro que debug. Hay ~20 de estos a 8–13 s cada uno.

---

## 4. La causa real: coste por invocación, no por test

Medido en esta máquina:

| Operación | Tiempo |
|---|---|
| `.venv/bin/python -c "pass"` | 21 ms |
| `.venv/bin/python -c "import pengu_project"` | 163 ms |
| `.venv/bin/python pengu_project.py check t.pengu` | **413 ms** |
| `.venv/bin/python pengu_project.py build --entry t.pengu` | **799 ms** |

**Esto explica casi todo el presupuesto.** Con 3573 tests:

- 3573 × 413 ms ≈ **1476 s** — ya casi los 2136 s observados.
- 462 sitios `compile_run` × 799 ms ≈ **369 s**.

Es decir: **el 35 min no lo causan unos pocos tests lentos, sino que ~3500
casos paguen cada uno el arranque de un proceso nuevo: intérprete + import del
compilador + carga de tablas Lark + driver del compilador C.**

El top-30 solo cubre el 40 %. El 60 % restante (~1290 s) es una cola larga de
tests individualmente invisibles que **cada uno compila o chequea por su cuenta**.

El principio rector del enunciado — *compila una vez, ejecuta N veces* — es
exactamente el correcto, pero **el beneficio está en la cola larga, no en el
top 10**. Migrar solo los archivos lentos no baja de 15 min.

---

## 5. Configuración de pytest: no existe

- **No hay `pytest.ini`.** `pyproject.toml` **solo** contiene `[tool.ruff]`.
- **No hay sección `[tool.pytest.ini_options]`** en ningún sitio.
- Por tanto: `addopts` vacío, `--strict-markers` **desactivado**, timeouts solo
  por `@pytest.mark.timeout` explícito (21 usos).
- Marcadores usados realmente: `parametrize` (188), `skipif` (65),
  `timeout` (21), `xfail` (12).
- **El marcador `slow` no existe: 0 usos.** El docstring de
  `test_doc_blocks.py` afirma que el test "is marked with the repo's `slow`
  convention" — **es falso**; no hay tal convención ni marcador registrado.

`tests/conftest.py` (606 líneas) es el único punto compartido: helpers
`check`, `check_ok`, `gen_bundle`, `compile_run`, `bundle_project`, y fixtures
`c_toolchain` (session), `compile_c`, `run_c`.

---

## 6. Conflictos con el plan propuesto (⚠️ requieren decisión humana)

### 6.1 `pengu test` ya existe y NO es el runner de pytest

`pengu_project.py:5648` registra un subcomando `test` cuyo significado es:

> *"Compile and run the project's integrated unit tests"* — compila el proyecto
> `.pengu` a un ejecutable cuyo `main` corre cada bloque `test` del lenguaje.

Es decir, `pengu test` es una función **del lenguaje Pengu**, no de la suite de
tests de Python. Ya tiene: `--profile`, `--config`, `--entry`, `--cc`,
`--verbose`, `-D`, `--json`, `--watch`, `--strict-c99`, `--target-compiler`,
`--target`, `--locked`, `--frozen`, `--release-unsafe`, `--deny-deprecated`.

El plan de Fase 2 propone añadir `pengu test --affected`, `pengu test --smoke` y
`pengu test --test X` para lanzar **pytest**. Eso solaparía dos significados
incompatibles bajo el mismo verbo.

### 6.2 `pengu test --json` ya existe con otro contrato, y está testeado

El JSONL actual (`tests/cli/test_cli_test_json.py`, `tests/cli/test_cli_json_lines.py`)
emite:

```json
{"type": "diagnostic", ...}
{"type": "summary", "ok": false, ...}
```

El plan propone **el mismo flag** con otro esquema:

```json
{"name": "pipes/chain_basic", "status": "pass", "duration_ms": 8}
```

Añadirlo rompería dos archivos de test existentes y un contrato documentado en
`pengu_project.py` (bloque `"test": {...epilog...}`).

### 6.3 Ya existe un prototipo del corpus objetivo

`tests/compliance/` es ya la arquitectura de 3 niveles que pide el plan:

- `NNN-slug.pengu` — datos (53 programas),
- `corpus.json` — manifiesto (`file`, `section`, `title`, `expects_rc`, `pins`),
- `run_all.py` (359 líneas) — runner batch,
- `test_compliance_corpus.py` — envoltorio pytest fino.

**Pero su modelo de ejecución es justo el antipatrón que hay que eliminar:**
`test_compliance_program_compiles_and_runs` está parametrizado por programa
(53 casos) y cada uno hace `check` **+** `build` **+** ejecutar = 3 procesos.

Construir `tests/conformance/` **en paralelo** a `tests/compliance/` duplicaría
el concepto. Lo sensato es **extender/común** el que ya existe.

---

## 7. Viabilidad del objetivo <90 s

36 cores. Si los 2136 s se repartieran perfectamente: 2136 / 36 ≈ **60 s**.
Parece alcanzable, **pero hay dos bloqueadores duros**:

1. **Dos tests individuales superan por sí solos los 90 s:**
   - `test_doc_blocks.py` (**137.7 s** en un único caso),
   - `test_frontend_no_crash.py` (**166 s** repartidos en 3 casos de un mismo
     archivo).

   Con xdist, un test individual no se puede dividir entre workers (salvo
   `--dist load` por parámetro). Por tanto **el objetivo de 90 s exige
   obligatoriamente reducir o cachear estos dos**, no solo paralelizar.

2. **La cola larga paga 413 ms por test.** Aunque xdist reparta 3573 tests en
   36 workers (≈100 tests/worker × 0.413 s ≈ 41 s de solo *overhead de proceso*),
   el margen es estrecho y depende de que cada worker cargue el runtime una vez.
   Sin convertir la cola larga a **en proceso** (sin subprocess), xdist da ~60 s
   teóricos pero con mucha varianza en CI (runners de 2–4 cores, no 36).

3. **CI no es esta máquina.** `ubuntu-latest` da 4 cores; un objetivo de 90 s
   medido en 36 cores no se traslada. El plan pide "<90 s" y "CI <3 min" — son
   dos presupuestos distintos y conviene fijarlos por separado.

> **Medido en §10:** el reparto perfecto de 36 cores no se cumple. Con `-n auto`
> real el total es **271 s, no 60 s** — el paralelismo tiene techo por overhead y por
> los tests indivisibles. §10 tiene los números y las 19 incompatibilidades.

---

## 8. Resumen de riesgos

| Riesgo | Evidencia | Impacto |
|---|---|---|
| El baseline es 35.6 min, no 15 | medido | El plan infravalora el trabajo 2.4× |
| La cola larga domina (60 %) | 413 ms × 3573 | Migrar solo archivos lentos no basta |
| `pengu test` ya está ocupado | `pengu_project.py:5648` | Colisión de diseño en Fase 2 |
| `pengu test --json` ya tiene esquema | 2 archivos de test | Rompería contrato existente |
| `tests/compliance/` ya cubre parte del objetivo | 53 programas + runner | Riesgo de duplicar arquitectura |
| Sin `pytest.ini` / sin `xdist` | no existen | Fase 1 parte de cero, es correcto |
| Objetivo 90 s depende de 36 cores locales | 2 tests >90 s | No se traslada a CI de 4 cores |

---

*Generado por la Fase 0. Ningún archivo de test fue modificado.*

---

## 9. Verificación independiente y correcciones

Segunda medición, hecha en paralelo por otra sesión sobre el mismo árbol. No hubo
contención (36 cores, load ~1,9; los dos totales difieren un 3,6 %).

### 9.1 Correcciones a las cifras de arriba

| Afirmación previa | Corrección | Cómo se comprobó |
|---|---|---|
| "sin `tcc`" | **FALSO: TCC 0.9.28rc está disponible** | `pengu_tcc.find_tcc()` → `build/tcc-dist/tcc-dist/bin/tcc`; `tcc_available()` → `True`. No está en `PATH`, por eso `which tcc` falla. |
| 202 archivos con `subprocess` | **96** | 106 de los 202 eran `tests/__pycache__/*.pyc` (coincidencia binaria). |
| 151 archivos que leen C generado | **10** | Mismo artefacto de `__pycache__`. |
| Baseline 2136 s | **2059 s (run limpio)** | Ver §2. |
| Top 30 = 40 % | **28,6 %** | Suma directa de `--durations=30` del run limpio. |

**Consecuencia práctica de lo de TCC:** la Fase 1 del plan dice
`shutil.which("tcc")`. Eso devolvería `None` y el runner caería a gcc.
Hay que usar **`pengu_tcc.find_tcc()`**.

### 9.2 El runner batch "1 bundle, N tests" NO está soportado hoy (verificado)

Se ejecutó el experimento, no se dedujo leyendo código:

```pengu
test "alpha ok":
    var a as int is 1 + 1
test "beta fails":
    var b as int is 1 / 0
test "gamma ok":
    var c as int is 2 + 2
```

```
$ python pengu_project.py test --entry main.pengu --json
[PENGU CRASH] fatal signal (signal/code 8)
  at pengu_test_1 (main.pengu:3)
{"event":"start","total":3}
{"event":"test_start","name":"alpha ok"}
{"event":"test_pass","name":"alpha ok"}
{"event":"test_start","name":"beta fails"}
{"event": "end", "aborted": true, "exit_code": 136}
```

Lo que **sí** existe: el modo `--test` agrega todos los bloques `test` de todas las
unidades en **un solo binario** (`pengu_parser/pengu_codegen/tests_gen.py`). Ese
"compila una vez" ya está resuelto y es reutilizable.

Lo que **no** existe:

1. **Aislamiento.** Un test que falla aborta el proceso entero por señal fatal; los
   tests siguientes nunca corren. Hay **un solo exit code** agregado.
2. **Detección de fallo.** El runner generado imprime `test_pass` y `"failed":0`
   **incondicionalmente** (`tests_gen.py:110-125`). No hay aserciones ni `longjmp`.
   Solo se infiere el test que falló porque su `test_start` queda sin `test_pass`,
   y se pierde todo lo posterior.
3. **stdout por test.** Verificado con un test que imprime: la salida de los cuerpos
   no está delimitada por test; se acumula en el buffer y sale como un bloque.

**Conclusión de diseño.** Comparar stdout y exit *por test* exige aislamiento, y un
proceso da un stdout y un exit code. La vía portátil (Linux + macOS + Windows, sin
`fork()`) es **compilar una vez y re-ejecutar el mismo binario** con
`--only <name>` / `--list`: un spawn de un binario ya enlazado cuesta ~2–5 ms frente
a 0,5–14 s de compilar+enlazar. Eso es lo que hacen los objetivos <90 s y <10 ms/test.

### 9.3 Decisiones humanas ya tomadas (2026-10-07)

1. **`pengu test` NO se sobrecarga.** La suite del compilador va en un comando nuevo
   **`pengu selftest`**. `pengu test` y su contrato `--json`
   (`tests/cli/test_cli_test_json.py`) quedan intactos.
2. **Autorizado** añadir `--list` / `--only` al harness generado en
   `pengu_parser/pengu_codegen/tests_gen.py` (es la única vía al aislamiento por
   test sin `fork()`).
3. **Medir `pytest -n auto` antes** de comprometer la migración.
4. `pytest-xdist` 3.8.0 instalado en `.venv`.

### 9.4 Ranking por archivo (proxy de coste-C)

`--durations` da *tests*, no *archivos*; el tiempo por archivo exige `--durations=0`
sobre un run completo (otros 34 min). Proxy: `compile_run`×1,0 + `bundle_project`×0,8
+ `gen_bundle`×0,35 + `check_c_syntax`×0,5.

| C-units | tests | archivo |
|---|---|---|
| 49,1 | 203 | `test_compiler_core.py` |
| 41,2 | 107 | `test_audit_fixes.py` |
| 23,4 | 43 | `test_audit_v0150_fixes.py` |
| 17,0 | 85 | `test_compiler_features.py` |
| 16,3 | 26 | `test_memory_audit_v0150.py` |
| 14,0 | 26 | `test_ffi_libs.py` |
| 13,1 | 23 | `test_p1_features.py` |
| 12,8 | 15 | `test_regression_0_13_6.py` |
| 11,6 | 37 | `test_p2_features.py` |
| 10,8 | 16 | `test_compiler_bugfixes_v0150.py` |

Los 20 primeros archivos concentran ≈55 % del trabajo-C. Los grupos grandes y
repetitivos —`test_regression_0_1x_*`, `test_std_*_extended`,
`test_std_*_backward_compat`, `test_p0/p1/p2/p3_*`, `test_audit_*`— son donde la
Fase 3/4 espera encontrar los "60 % triviales o duplicados".

### 9.5 Restricciones aún no resueltas

- **Suelo de cobertura.** `.coveragerc` fija `fail_under = 80` y
  `tests/test_ci_workflows.py:446-458` (`RECORDED_FLOOR = 80.0`) falla si baja.
  La Fase 4 ("60 % → borrar") **romperá CI por cobertura**: borrar no es gratis.
  Requiere decisión antes de la Fase 4.
- **CI no ejecuta la suite como un comando.** `ci.yml` tiene ~9 pasos-gate que listan
  **47 archivos** con `-x`, más el run completo con `--cov`; y `compliance.yml`,
  `sanitizers.yml`, `release.yml` y `release-verify.yml` también invocan pytest.
  Reescribir CI a 3 jobs absorbe o elimina esos gates.
- **"CI full <90 s" mide lo que no toca.** El wall-clock de CI lo dominan
  `scripts/smoke.py`, `build_runtime.py` (minutos), `make_release.py`, la
  reproducibilidad del archivo y el job del VSIX, no pytest.
- `pytest.mark.slow` **no existe** (0 usos); el docstring de `test_doc_blocks.py`
  afirma lo contrario. `--strict-markers` está desactivado (no hay `pytest.ini`).
- `time.sleep` en 4 archivos (viola la regla dura 7); `pytest.skip()` condicional en
  27 archivos (viola el punto 4 de Fase 5).

---

## 10. Medición de `pytest-xdist` (leverage barato, ya ejecutado)

Instalado `pytest-xdist` 3.8.0 y medido dos veces la suite completa con `-n auto`
(36 workers en esta máquina):

| Run | Tiempo | Resultado |
|---|---|---|
| Serial (baseline) | **2059 s (34:19)** | 3504 passed, 23 skipped, 46 xfailed, **0 failed** |
| xdist `-n auto` (1ª) | **271,78 s (4:31)** | 19 failed, 3485 passed |
| xdist `-n auto` (2ª) | **270,50 s (4:30)** | 16 failed, 3488 passed |

**Aceleración: 7,6× — gratis, sin migrar un solo test.** Es el mayor ahorro por unidad
de esfuerzo disponible en todo el plan.

### 10.1 Los fallos bajo xdist son carreras, no bugs reales

Los 19 fallos se reprodujeron **en serie y los 646 tests de esos 10 archivos pasan
(0 fallos)**. Es decir: son incompatibilidades con la paralelización, no regresiones.

Además son **inestables**: el conjunto difiere entre los dos runs (10 comunes,
9 solo en el 1º, 6 solo en el 2º). Nunca se puede aceptar xdist en CI sin arreglarlos.

Clases identificadas por el mensaje de aserción:

1. **Caché de build compartida** (la mayoría):
   `test_p0_toolchain.py::TestBuildCache` (`assert cached is True`),
   `test_cli_tools.py::TestBuildRunProject`
   (`assert b.is_bundle_up_to_date(...)`),
   `test_assets.py::test_end_to_end_embed` (`assert is_cached2`).
   Todos afirman "la segunda compilación es un acierto de caché"; en paralelo otro
   worker calienta/expulsa la caché global.
2. **Estado global de directorio**: `test_run_cleanup.py`
   (`test_default_run_does_not_create_build_dir`) — `conftest.compile_run` crea sus
   temporales **dentro de `build/`** (`tempfile.mkdtemp(dir=BUILD_DIR)`), así que en
   paralelo `build/` ya existe cuando el test comprueba que no.
3. **Manejador de señales**: `test_crash_signals.py` — pasa aislado con `-n 12`,
   falla bajo carga completa.
4. **Contrato CLI / codegen flaky**: `test_cli_contract.py::test_contract_success[test]`,
   `test_compiler_core.py::TestLoopValueExpression`, `test_compiler_features.py`.

### 10.2 Qué NO resuelve xdist

- **No llega a <90 s por sí solo**: 4:31 en 36 cores.
- **CI no tiene 36 cores.** `ubuntu-latest` da ~4 cores → `-n auto` ≈ 2059/4 ≈
  **8,5 min**, no 4:31. El objetivo <90 s exige *además* colapsar los ~750 tests que
  tocan C y arreglar los gates de documentación (130 s + 166 s, indivisibles por
  worker).
- No reduce los **dos tests individuales >90 s** (`test_doc_blocks` 130 s,
  `test_frontend_no_crash` 166 s repartidos en 3 casos): un test no se reparte.

**Conclusión:** xdist es condición necesaria pero no suficiente. Debe entrar en Fase 1
(con los 19 tests hacerse xdist-safe) y el objetivo de 90 s sigue dependiendo del
runner batch de §9.2.

---

## 11. Fase 1 — resultado

### 11.1 Lo construido y verificado

| Pieza | Estado | Evidencia |
|---|---|---|
| `pytest-xdist` en `requirements.txt` | hecho | 3.8.0 instalado |
| `pytest.ini` (6 marcadores + `-ra --strict-markers`) | hecho | marcador no registrado → error de colección; 115 tests de contrato en verde |
| `--list` / `--only-index` / `--only` en el harness generado | hecho | aditivo: `int pengu_run_tests(void)` y `pengu_test_names[N]` intactos; 124 tests de contrato en verde |
| `tests/conformance/` (`README.md`, `_manifest.json`, `_smoke/` ×3) | hecho | 3 casos reales |
| `tests/test_conformance.py` (runner batch) | hecho | **3 casos en 0,68 s**; ~6 ms por caso |
| Regresión serial de todo lo tocado | verde | 323 passed, 1 skipped |

El runner batch compila UN bundle (TCC: 0,02 s) y **re-ejecuta el binario una vez por
caso** con `--only-index N`. Aislamiento real: un caso que aborta solo mata su propio
proceso. Presupuesto de smoke: **0,68 s** contra el objetivo <3 s; por caso, **~6 ms**
contra el objetivo <10 ms.

Comprobado con tests negativos (no basta con que pase en verde):
`.expected` corrupto → falla; `.exit` incorrecto → falla; nombre de test ≠ id → falla
con mensaje explícito; entrada obsoleta en el manifiesto → falla;
`platforms: ["windows"]` en Linux → skip.

### 11.2 Dos bugs de producto que la paralelización destapó

**B1 — La caché de build se invalidaba sola cuando un `include_dirs` es compartido.**
`is_bundle_up_to_date()` paseaba los `include_dirs` declarados buscando `.h` más
nuevos que el bundle. Los proyectos de prueba declaran `build/` como include dir, así
que **cada proyecto veía el `pengu_runtime.h` recién copiado por otro** como "más
nuevo que mi bundle" y descartaba su propia entrada válida. Arreglado en
`pengu_project.py`: un directorio que contiene `.bundle_hash` es un **directorio de
salida** de algún proyecto, así que sus headers son artefactos derivados, no entradas.
El paseo además se poda, así que es más barato. `TestBuildCache`: 2/6 fallos → 6/6
en 3 pasadas con `-n 8`.

**B2 — `set_release_unsafe()` es un global de proceso que nadie restaura.**
`_RELEASE_UNSAFE` vive en `pengu_parser/pengu_codegen/attributes.py` y
`tests/conftest.py:402` lo fija en cada `compile_run()` **sin restaurar el valor
anterior**. En serie el orden de ejecución lo tapa; con xdist el orden por worker
cambia, un test que puso `release_unsafe=True` se filtra al siguiente, y
`test_phase1_bounds` ve un bundle **sin** comprobaciones de límites. Es una
dependencia de orden latente: la suite serial es correcta *por casualidad*.

**Arreglado (raíz, no síntoma).** El fallo real estaba en el producto:
`PenguBuilder.bundle()` importaba `set_release_unsafe` **y no lo llamaba** —a
diferencia de `compile()`—, así que el codegen leía el global de proceso en vez de
`self.release_unsafe`. Dos builders con distinta configuración en un mismo proceso se
pisaban. Además `conftest.compile_run()` lo dejaba fijado y `gen_bundle()` lo
heredaba. Los tres puntos arreglados:
`pengu_project.py` (bundle fija el flag desde el builder),
`tests/conftest.py` (compile_run guarda/restaura; gen_bundle fija `False` y restaura), y
`tests/compiler/test_phase1_bounds.py` (ahora pide `release_unsafe=True` por configuración del
builder en vez de tocar el global — que es lo que el test decía comprobar).

### 11.3 Estado de los 19 tests xdist-unsafe: **19 → 0**

Cerrada. Dos pasadas consecutivas de la suite completa con `-n auto`:

| Run | Tiempo | Resultado |
|---|---|---|
| `-n auto` (1ª) | 277,19 s (4:37) | **3510 passed**, 23 skipped, 46 xfailed, 0 failed |
| `-n auto` (2ª) | 284,13 s (4:44) | **3510 passed**, 23 skipped, 46 xfailed, 0 failed |

Las tres causas, y cómo se cerró cada una:

1. **11 fallos por `ld: no se puede encontrar -lpengu_runtime`.** Localizado con un
   interposer que registra la pila en cualquier borrado de esa ruta:
   `tests/compiler/test_build_runtime_link.py::test_build_fails_cleanly_without_runtime_archive`
   **renombraba el `libpengu_runtime.a` real del checkout** para probar el pre-flight
   de "runtime ausente". En serie es inocuo; con xdist, durante ~1,5 s cualquier otro
   worker que enlazaba moría con `cannot find -lpengu_runtime` (medido: el archivo
   desaparece a los 21,4 s y reaparece a los 23,0 s del run). El propio docstring del
   módulo decía que el archivo *nunca* se movía y que `PENGU_LIB_DIR` bastaba —
   pero `runtime_lib_dirs()` era **aditivo**, así que el checkout se buscaba siempre y
   el mecanismo documentado no podía funcionar. Arreglado: `PENGU_LIB_DIR` es ahora un
   **override real** (`pengu_paths.py`) y el test lo usa con un directorio vacío. El
   archivo ya no se mueve nunca (checksum antes/después idéntico).
2. **4 fallos en `test_phase1_bounds.py`** — consecuencia de B2, arreglado arriba.
3. **`test_run_cleanup.py`** — afirmaba `set() == {'/tmp/pengu_run_...'}` sobre el
   `/tmp` **compartido**, así que medía lo que hacían los demás workers. Arreglado con
   un `TMPDIR` privado por test (`private_tmp`), y **verificado que no queda vacuo**:
   un poller observó `pengu_run_hello_084tg14i` aparecer dentro del TMPDIR privado.
4. **`test_std_invoke_extended[release]` y el resto de la familia `test_std_*`** —
   no era un bug sino un **timeout dependiente de la carga**: `@pytest.mark.timeout(30)`
   para compilaciones que tardan ~13 s en solitario y pasaban de 30 s con 35 compiladores
   concurrentes. Sustituido en los 18 sitios por
   `STD_PROGRAM_BUILD_TIMEOUT = 120` (una sola definición, documentada en
   `tests/conftest.py`). Es una guarda contra cuelgues, no una aserción de rendimiento:
   ninguno de esos tests mide tiempo.

### 11.4 Aritmética de no-regresión

Baseline serial: 3504 passed. Con los 6 tests nuevos: **3510 esperados**.
Run con xdist: 3494 passed + 16 failed = 3510. **No hay regresión serial**; los 16
son exclusivamente de paralelismo.

---

### 11.5 Hallazgo para la Fase 3: 190 de 207 programas no son embebibles

De los 207 `.pengu` del corpus actual, **190 están escritos como
`weave main into int:`** (compliance 53/53, std_programs 61/61, test_generics 43/50,
migration 12/12, test_manual_memory 9/9, test_string_composition 22/22). Solo 1 tiene
bloque `test`. Dos `main` no caben en un binario, así que **no entran en el modelo
batch tal cual**: cada uno necesita la conversión mecánica
`weave main into int:` → `test "<feature>/<nombre>":` (quitando el `return 0`), más
capturar su stdout/exit. Es trabajo mecánico pero real, y hay que presupuestarlo.

## 12. Fase 2 — `pengu selftest` y el grafo de dependencias

### 12.1 Lo construido

| Pieza | Qué hace |
|---|---|
| `pengu selftest` | La suite del **compilador**. Verbo nuevo: `pengu test` sigue siendo el del lenguaje (compila el proyecto del usuario y corre sus bloques `test`). |
| `--smoke` | El tier rápido: unidades puras + los casos `_smoke/` del corpus. |
| `--test REGEX` | Un caso concreto del corpus. |
| `--affected [BASE_REF]` | Sólo los casos que el cambio puede romper, según el grafo. |
| `--json` | JSONL en stdout, una línea por test: `{"name","status","duration_ms"}` (+`message` si falla). |
| `tools/gen_conformance_deps.py` | Genera `tests/conformance/_deps.json`. Determinista. `--check` para CI. |
| `tools/pytest_jsonl.py` | Plugin de pytest que escribe el JSONL. |

**Por qué un plugin y no un formato por stdout:** pytest es dueño de stdout, así
que un test no puede imprimir líneas parseables de forma fiable — se capturan y se
re-emiten cuando convenga. El plugin ve el resultado y la duración de *todos* los
tests (unidad, integración y conformidad) y los escribe en un archivo que el
llamante lee después. Eso también permite que `--json` funcione para la suite
entera, no sólo para el corpus.

### 12.2 Medido

| Comando | Objetivo | Medido |
|---|---|---|
| `pengu selftest --smoke` | <3 s | **2,68 s** (57 passed, 6 skipped, 3517 deselected) |
| `pengu selftest --test <caso>` | <10 ms/caso | **0,78 s** (1 caso + 3 meta-tests del corpus) |
| `pengu selftest --affected HEAD` | <15 s | **4,97 s** (3 casos afectados de 30 ficheros cambiados) |

### 12.3 Dos límites honestos del grafo

**1. Los cambios en el compilador seleccionan el 100%, no <60%.** El criterio
«cambiar `pengu_parser/pengu_grammar.py` corre <60% del corpus» **no es alcanzable
con un grafo estático, y no debería serlo**: todo caso se compila con la gramática,
así que cualquier cambio ahí *puede* romper cualquiera, y decir lo contrario sería
infra-seleccionar y enviar regresiones que CI nunca ejecutó. El grafo lo registra
como prefijo (`pengu_parser/`), que es la respuesta conservadora correcta.
El criterio «cambiar `std/scrolls.pengu` corre <5%» **sí** se cumple: son los casos
que lo importan, hoy 0 de 3.

Para afinar el 100% hace falta un grafo **medido**, no declarado: correr el corpus
bajo `coverage --cov-context=test` y registrar qué líneas ejecutó cada caso. Eso
convierte «puede afectar» en «afectó». Es el siguiente paso natural, no un
descuido.

**2. `--affected` filtra el corpus, no los tests de unidad.** No hay grafo para
los `tests/test_*.py` de la raíz, así que un cambio en `pengu_paths.py` selecciona
0 casos de conformidad aunque sí afecte a tests unitarios. La selección es
**del corpus**, y el comando lo dice en su salida. El mismo `--cov-context` cerraría
esto también.

### 12.4 Tres bugs que encontraron los propios meta-tests

Los tests añadidos en `test_conformance.py` no son decorativos; cada uno atrapó un
fallo real durante esta fase:

1. **`case_id.startswith("_")` saltaba todo `_smoke/*`.** `--affected` informaba
   «ningún caso afectado» incluso cambiando el compilador. Es *el mismo* footgun
   del prefijo `_` que ya hubo que arreglar en el lector de `_manifest.json`
   (§11.3): el corpus usa `_smoke/`, así que `_` es parte normal de un id. El
   idioma «`_` = metadato» está prohibido en este repo; sólo la clave exacta
   `_meta` lo es.
2. **`os.path.normpath("pengu_parser/")` borra la barra final**, así que la regla
   de prefijo nunca coincidía. Pasó desapercibido porque otras dependencias
   *exactas* (`pengu_project.py`, `tests/test_conformance.py`) sí coincidían y
   enmascaraban el resultado. Ahora la barra se comprueba sobre el valor crudo.
3. **`selftest` sin entrada en `_SUBCOMMAND_DOCS`** rompió el contrato de ayuda de
   CLI (`test_cli_help_contract.py`), que exige descripción, epílogo con códigos de
   salida y un ejemplo por subcomando. Arreglado añadiendo la entrada (y subiendo
   el conteo 27 → 28, que es un cambio consciente).

También se corrigieron dos fallos de `--json` que sólo aparecían al usarlo:
el plugin escribía desde el worker *y* desde el controlador (registros duplicados
bajo xdist), y el ruido de pytest caía en stdout, corrompiendo el JSONL. En modo
`--json` stdout es **sólo** JSONL y el ruido va a stderr.

### 12.5 Verificación

| Comprobación | Resultado |
|---|---|
| Suite completa con `-n auto` | **3519 passed**, 23 skipped, 46 xfailed, **0 failed**, 4:37 |
| Contrato CLI (`test_cli_contract` + `help_contract` + `freeze_manifest`) | 175 passed, 5 xfailed (los mismos de antes) |
| `pengu test` y su `--json` | intactos (`test_cli_test_json`, `test_cli_json_lines`: 10 passed) |
| `tools/gen_conformance_deps.py --check` | al día |
| Ruff F821/E9 | limpio |

3519 = 3510 (tras Fase 1) + 9 tests nuevos: 5 meta-tests del grafo en
`test_conformance.py` y 4 del contrato de `selftest`. La aritmética cuadra, así que
no hay tests enmascarados.

**Añadir `selftest` tocó 4 contratos congelados** (`docs/FREEZE.md`,
`SUBCOMMANDS`, `CONTRACT`, `_SUBCOMMAND_DOCS`). No es fricción accidental: el repo
congela su superficie de CLI a propósito, y cada uno de esos tests obliga a que
ampliarla sea un acto consciente y documentado. Los cuatro se actualizaron con
justificación.

---

## 13. Fase 5 — CI

### 13.1 Lo cambiado en `.github/workflows/ci.yml`

1. **Job `smoke` nuevo** (~3 s de pytest, sin compilar el runtime:
   `setup-pengu` con `build-runtime: 'false'`). Corre
   `pytest -m "smoke and not conformance"`.
   El `and not conformance` es necesario: el marcador `smoke` también cubre los
   casos `_smoke/` del corpus —porque `pengu selftest --smoke` debe correr ambos
   en local— y esos sí necesitan el runtime y un compilador C, lo que arruinaría
   el tiempo de respuesta. Verificado: la selección son 60 tests de 4 ficheros,
   y **ninguno de los 4 referencia `requires_runtime` ni `compile_run`**.
2. **`-n auto` en el paso de la suite completa** y en los **7 pasos-gate**
   (`FASE 1`–`FASE 7`). La suite completa es el coste dominante, pero los gates
   re-ejecutan ~47 ficheros que ya están en la suite, así que también había que
   paralelizarlos o pasaban a ser el cuello de botella.
3. **`auto-tag` ahora necesita `smoke`** además de `build` y `vscode-extension`:
   un smoke roto no debe etiquetar una release.
4. **Nada se eliminó.** Los 9 pasos-gate con nombre, la matriz de 3 OS, el layout
   ABI, la verificación del artefacto, la reproducibilidad y el job del VSIX
   siguen ahí.

### 13.2 Verificado antes de tocar el YAML

El riesgo real era la cobertura: si `pytest-cov` no agregase bien los workers, el
ratchet `fail_under=80` rompería CI en silencio.

| Comprobación | Resultado |
|---|---|
| Suite completa con `-n auto --cov` | **80,50 %**, «Required test coverage of 80.0% reached», 0 failed |
| Valor registrado en `AUDIT_1.0_FASE8.md` | 80,20 % (con `fail_under = 50` entonces) |
| Coste de la cobertura bajo xdist | 282 s vs 277 s sin ella (+5 s) |
| `test_ci_workflows.py` (invariantes de CI) | 105 passed |
| YAML | parsea; 4 jobs |
| Un gate real con `-n auto -x` | OK (`FASE 4`: 73 passed en 17 s) |

Paralelizar **no baja** el número de cobertura (80,50 % > 80,20 %): no cruza el
ratchet.

### 13.3 Estimación honesta del efecto en CI

- Medido en esta máquina (36 cores): **34 min 19 s → 4 min 37 s**.
- `ubuntu-latest` tiene ~4 cores, no 36. Por tanto la suite completa debería bajar
  a **~9–10 min** (≈2222 s / 4). **Es una estimación aritmética, no una medición**:
  no puedo ejecutar un runner de GitHub desde aquí. El primer run de CI dará el
  número real y conviene anotarlo entonces.
- El objetivo literal de la misión («full <90 s», «CI <3 min») **no se alcanza en
  esta fase y no puede alcanzarse sólo con CI**: exige las Fases 3 y 4 (migrar el
  corpus y colapsar los ~750 tests que compilan C). Paralelizar CI da el factor
  ~4–7 que sí está disponible hoy.

### 13.4 Desviaciones de la misión, con motivo

1. **No se reestructuró en 3 jobs.** La misión pide 3 jobs (smoke / full / cross)
   con el full en <90 s. Reorganizar los pasos no los hace más rápidos: la
   velocidad viene de `-n auto`, no del reparto en jobs. Reestructurar ahora
   habría movido pasos de sitio y **eliminado los gates FASE con nombre** —
   perdiendo atribución de fallos a cambio de nada medible. Se conservó todo y se
   añadió el job rápido.
2. **No se cacheó el bundle de conformance** (`actions/cache`). TCC compila el
   bundle del corpus en **~0,05 s**; `actions/cache` añadiría un modo de fallo
   mucho peor que el problema que resuelve: un bundle cacheado pero obsoleto hace
   que los tests **mientan en verde**, midiendo código viejo. Cuando el corpus
   crezca hasta que la compilación del bundle sea una fracción medible de CI,
   merecerá revisarse — con una clave derivada del contenido, no de mtimes.
3. **`test_snapshots_c.py` no existe todavía**: es un fichero del estado objetivo.
   Reducir los tests que leen C generado (hoy 10 ficheros) es trabajo de Fase 3/4.
4. **El corpus no necesita un job cross propio.** `tests/` incluye
   `tests/test_conformance.py`, así que la matriz de Windows y macOS **ya** ejecuta
   el runner batch y los casos `_smoke/`. Una diferencia por plataforma se declara
   en `_manifest.json` (`platforms`), nunca con un `pytest.skip` disperso.

### 13.5 Riesgo residual declarado

No puedo ejecutar Windows ni macOS desde esta máquina. Dos suposiciones quedan
pendientes de confirmar en el primer run de CI:

1. El job `smoke` asume que los 4 ficheros seleccionados no necesitan el runtime.
   La evidencia es fuerte (cero `requires_runtime`/`compile_run`, y los sondeos de
   `tests/conftest.py` al importar son comprobaciones de existencia de fichero),
   pero no es una ejecución sin runtime.
2. El runner batch y los casos `_smoke/` en Windows/macOS: los flags de compilación
   que usa `tests/test_conformance.py` están verificados con gcc y TCC en Linux,
   no en MinGW ni en clang de macOS.

---

## 14. Fase 3 — el hallazgo que bloquea el modelo batch a escala

**No se migró el corpus.** Se construyó y verificó la herramienta, se migraron los
53 programas de `tests/compliance`, y **se revirtió** al descubrir que el modelo
falla por una razón que la misión no anticipó. Dejar 52 casos en rojo habría sido
mucho peor que no migrar.

### 14.1 Qué se construyó y sí funciona

`tools/migrate_main_to_case.py` hace la conversión completa y correcta:

1. Ejecuta el programa `weave main` original y **captura su stdout y su exit code**
   (las expectativas se derivan ejecutando, no leyendo la prosa que las describe).
2. Reescribe `weave main into int:` → `test "<id>":` y elimina el `return 0` final.
3. Escribe `.pengu` / `.expected` / `.exit` y la entrada del manifiesto.

Verificado sobre los 53 programas: 53/53 encabezados reescritos, 53/53 `return`
final eliminado, helpers intactos. La conversión tardó 22 s.

Dos bugs reales que la validación previa atrapó antes de escribir nada:

- **El regex del `return` borraba el `return 0` equivocado.** `count=1` cogía el
  *primer* `return 0` del fichero, que en
  `020-declare-extern-c.pengu` pertenece a un **helper**: le quitaba el suyo y
  dejaba el del test (que es `void`). Anclado al final del fichero —el punto de
  entrada es siempre el último bloque— quedó correcto.
- **`compliance/001-hello` no es un módulo importable**: el runner importa cada
  caso por su ruta, y un identificador no puede empezar por dígito ni contener `-`.
  El bundle fallaba con `unexpected '001'`. Ahora los nombres se sanean a
  `s001_hello` y **la restricción está documentada en `AGENT_TESTING.md`**.

### 14.2 El bloqueo: los casos comparten un único espacio de nombres

Un bundle es **una** unidad de compilación, y PenguScript resuelve los símbolos de
sus módulos en **un solo espacio de nombres**. Desbloquear la migración consistió en
descubrir, uno tras otro, **cinco** obstáculos distintos. Los tres primeros están
resueltos en el runner; los dos últimos son la prueba de que hace falta tocar el
compilador.

**1. Colisión entre dos casos.** 7 símbolos declarados por más de un caso
(`Point` ×3, `add` ×4, `describe` ×3, `Number`, `Pair`, `Player`, `strlen`). El
fallo es *todo o nada*: una colisión deja **todos** los casos sin compilar, con un
error que no nombra ni los casos ni el arreglo:
`Omen variant name 'Point' of omen 'Shape' collides with the top-level symbol 'Point'`.

**2. Colisión contra un símbolo de `std`.** Ésta es la que costó horas y la que
demuestra por qué un análisis de nombres «de casos» no basta. `std/scrolls.pengu`
declara un `count` no genérico (línea 139, dentro de un bloque `enchanting`). Un caso
que declara su **propio** `count` genérico (`036-iterating-generics`) no puede
compartir bundle con un caso que **importa `std.scrolls`**
(`042-imports-modules`, `054-standard-library`), aunque ninguno de los dos mencione
al otro. El síntoma es
`Could not infer type parameter(s) T for generic function 'count'` señalando una
línea de un fichero que no participa, y **depende del orden de importación**: la
misma pareja compila en un orden y falla en el otro.

Diagnóstico inicial equivocado: atribuí esto a una *variable local* llamada `count`
en otro módulo. Lo desmintió un experimento de bisección — emparejar `s036` con cada
uno de los otros 52 casos aisló a dos culpables que **no contienen la palabra
`count`**; renombrar el genérico lo arreglaba, lo que apuntaba a una colisión de
nombres y no a shadowing. Arreglado en el runner: la agrupación ahora considera el
**cierre de imports** de cada caso (`imported_symbols`), no sólo lo que declara.

**3. `TCC` no soporta `__auto_type`** (extensión GNU que emite el codegen en los
envoltorios de comprobación de límites). Es un error duro, no un flag. Resuelto con
caída a gcc.

**4. El codegen produce C inválido al bundlear.** Con el checker ya satisfecho,
`gcc` rechaza el bundle:

```
corpus/compliance/s024_rune_structs.pengu:35: error: tipos incompatibles en la
inicialización del tipo 'int32_t' {también conocido como 'const int'} usando el
tipo 'PenguString'
```

Esto es lo grave, y es lo que cierra el debate: **bundlear programas independientes
no sólo puede dar un error, puede generar código silenciosamente incorrecto.** Una
colisión de nombres que el checker tolera hace que el codegen resuelva el tipo
equivocado. Un corpus que compile en verde y ejecute lo que no es no es un corpus,
es una trampa.

**Conclusión.** «5000 tests = 1 binario con 5000 funciones» **no es alcanzable sin
namespacing por módulo en el compilador** — que es la opción que se decidió
implementar. No es la vía «bonita»: es la única correcta, porque sin ella el
resultado puede ser incorrecto en silencio. El trabajo debe cubrir, como mínimo:

1. Que los símbolos de un módulo importado no colisionen con los de otro
   (el `SymbolTable` tiene hoy dicts planos por nombre: `runes`, `functions`,
   `omens`, `aliases`, `seals`, `concepts`, `consts` — ninguno tiene dimensión de
   módulo).
2. Que el **mangling** de genéricos instanciados incluya el módulo
   (`monomorphized_functions` está keyed por nombre manglado).
3. Que el codegen emita nombres C únicos por módulo, o reutilice `insignia`.

Medido: los 3 casos `_smoke/` (que no declaran símbolos top-level y sólo importan
`std.spark`) **sí** funcionan en un bundle, en ~0,7 s. El modelo es válido para
casos autocontenidos de ese tipo; no lo es para los ~190 programas existentes, que
declaran helpers, runas y omens.

### 14.3 Lo que sí queda de esta fase

Aunque la migración se revirtió, el trabajo dejó mejoras permanentes:

- **El runner agrupa en bundles libres de colisiones** (`group_cases`), y la
  agrupación considera el **cierre de imports** de cada caso, no sólo lo que
  declara. Antes, una sola colisión rompía el corpus entero con un error
  incomprensible; ahora se resuelve separando grupos (greedy, determinista).
  Medido sobre el corpus de prueba de 56 casos: 4 grupos (43/7/3/3).
- **Caída de compilador**: si TCC no puede compilar el bundle (no implementa
  `__auto_type`), el runner reintenta con gcc y reporta cuál usó. Sin eso, el
  corpus dependía de un compilador concreto.
- **El workdir temporal ya no se filtra cuando el build falla.** Lo destapó la
  limpieza final: `build/` tenía **159** directorios `pengu_conformance_*`
  acumulados, porque si `build_bundle` lanzaba una excepción el árbol temporal
  quedaba huérfano — y durante esta investigación falló muchas veces. Es
  exactamente lo que llena el disco de un runner de CI en lugar de fallar un test.
  Verificado forzando un fallo de compilación: 159 antes, 159 después.
- **4 tests nuevos que fijan la restricción en código**, no en prosa:
  `test_cases_that_share_a_symbol_are_not_bundled_together` (caracterización, a
  borrar si el compilador se arregla), `test_real_corpus_groups_are_collision_free`,
  `test_grouping_is_deterministic` y `test_the_smoke_tier_is_a_single_bundle`
  (que impide que un caso `_smoke/` futuro declare símbolos y ralentice el job).
- **La restricción de nombres documentada** en `AGENT_TESTING.md` y en el README
  del corpus: la ruta de un caso *es* una ruta de módulo, así que directorios y
  ficheros deben ser identificadores Pengu válidos.
- `tools/migrate_main_to_case.py` queda listo: el día que (a) o (b) existan,
  `python tools/migrate_main_to_case.py --compliance --apply` genera el corpus.

**Decidido (2026-10-07):** se implementa el **namespacing por módulo en el
compilador**. Tras descubrir que bundlear puede producir C inválido (§14.2 punto 4),
no es una preferencia de diseño sino el único camino correcto. La migración de los
~190 programas queda a la espera de ese trabajo; `tools/migrate_main_to_case.py` ya
está listo y verificado para ejecutarla en cuanto exista.

---

## 15. El bug de codegen que bloqueaba la migración (arreglado)

En §14.2 concluí que el modelo batch exigía namespacing por módulo en el
compilador. **Esa conclusión era en gran parte errónea**, y la causa real era un
bug concreto que la migración destapó.

### 15.1 Síntoma

Tras arreglar las colisiones de nombres por agrupación y la caída de compilador,
**43 de 56 casos seguían fallando**, todos con el mismo error de `gcc` sobre C
generado:

```
s024_rune_structs.pengu:35: error: tipos incompatibles en la inicialización
del tipo 'int32_t' usando el tipo 'PenguString'
```

### 15.2 Localización

Bisecando `s024` contra los otros 42 miembros de su grupo: `s024` solo compila,
`s024 + s036_iterating_generics` genera C inválido, y los otros **41 pares
compilan**. El C culpable:

```c
Player _destruct_16 = p;
const int32_t n = _destruct_16.name;   /* 'name' es string */
```

### 15.3 Causa

En `pengu_codegen/stmts.py`, la rama de destructuring de runas sacaba el tipo de
cada nombre **buscándolo en la tabla de símbolos global**, y sólo si eso fallaba
usaba el tipo del campo:

```python
sym = self.symbols.lookup(name)          # 'n' -> el `var n as int` de OTRO módulo
var_t = sym.type if sym else None        # int  <-- gana
if var_t is None and i < len(fields):
    var_t = f_dict.get(fields[i])        # string, pero ya no se consulta
```

`s036` declara `var n as int is 0` dentro de un `weave` genérico. `n` es un nombre
comunísimo, el lookup lo encontró, su tipo ganó sobre el del campo, y el emisor
declaró un campo `string` como `int32_t`. La instrumentación lo confirma:

```
name='n' i=0 fields=['name','hp','is_alive','_secret_id']
f_dict={'name':'string','hp':'int',...}  field_t=string  sym_t=int
```

**No es un artefacto de bundlear**: se reproduce con `pengu test` sobre un
proyecto normal de tres módulos, sin nada de esta infraestructura. Cualquier
proyecto donde un módulo declare un `weave` genérico con una local de nombre
común y otro módulo destructura un runa cuyo campo se llame igual fallaba con un
error de C que no nombra ni el módulo ni la causa.

### 15.4 Arreglo

Los nombres destructurados son **locales nuevos**: su tipo es el del campo del
runa en esa posición. El tipo del campo pasa a tener prioridad y el lookup global
queda sólo como último recurso.

Test de regresión en `tests/compiler/test_compiler_features.py`
(`TestDestructuringAcrossModules::test_destructuring_survives_a_name_clash_in_another_module`),
**verificado en ambos sentidos**: pasa con el arreglo y falla al revertirlo
(`1 failed in 1.10s`).

### 15.5 Hallazgo colateral: la caché no se invalida al cambiar el compilador

Costó un ciclo de depuración confundido: tras editar `pengu_parser/`, `pengu test`
**reutilizó el `build/bundle.c` cacheado** y ni el arreglo ni la instrumentación se
ejecutaron. `compute_config_hash`/`compute_sources_fingerprint` cubren el perfil,
los flags, las fuentes del *programa* y sus assets — **no la identidad del
compilador**. Para un `pengu` instalado da igual; editando este repositorio,
significa que `pengu build`/`test` pueden servir un bundle generado por código
anterior. La suite no se ve afectada porque `compile_run` construye en un
directorio temporal nuevo cada vez, que es lo que la hace fiable. **Sin arreglar**
(sería trabajo de producto: incluir un hash del compilador en la clave).

---

## 16. Fase 3 — el corpus de compliance, migrado y verde

El arreglo de §15 desbloqueó la migración. Estado: **56 casos pasan en ~9 s**
(53 programas de compliance + 3 de smoke), frente a los 53 ciclos
`check`+`build`+`run` que hacía `tests/compliance/run_all.py`.

### 16.1 Lo que se hizo

1. `tools/migrate_main_to_case.py` generó los 53 casos: capturó stdout y exit
   **ejecutando** cada programa original, reescribió `weave main into int:` →
   `test "compliance/sNNN_slug":` y eliminó el `return 0` final.
2. Los nombres se sanearon (`001-hello` → `s001_hello`) porque **la ruta de un caso
   es una ruta de módulo**: un identificador no puede empezar por dígito ni llevar
   `-`. El bundle fallaba con `unexpected '001'`.
3. Se retiró el corpus viejo: `tests/compliance/` (53 `.pengu`, `corpus.json`,
   `run_all.py`, `EXPECTED.md`) ya no existe. Sus garantías se conservaron:
   - la **cobertura de secciones de `LANGUAGE.md`** (incluida la normalización de
     `#` finales y el `setdefault` del parser original) vive en
     `tests/test_compliance_corpus.py`, reescrito;
   - la **declaración normativa de compatibilidad 1.x** ("un cambio que rompa uno
     de estos programas es una ruptura de compatibilidad, no un bug del corpus")
     se trasladó a `tests/conformance/compliance/README.md`;
   - la **matriz de compiladores** (gcc/clang, roadmap 10.3) pasó a
     `.github/workflows/compliance.yml` vía `PENGU_TEST_CC`.
4. `_manifest.json` es ahora la fuente de verdad legible por máquina que eran
   `corpus.json` + `EXPECTED.md`, con `section`, `title`, `pins` y
   `migrated-from` por caso.

### 16.2 Corrección a §14: la conclusión era demasiado pesimista

Con el bug de §15 arreglado, **agrupar por colisiones basta**: los 56 casos
conviven en 4 bundles y pasan. No hizo falta tocar el `SymbolTable` ni el
mangling. La afirmación de §14.2 de que el namespacing por módulo era «la única
vía correcta» era falsa: el C inválido no venía del espacio de nombres compartido
sino del bug de destructuring, y las colisiones de nombres se resuelven separando
grupos.

Lo que **sigue** siendo cierto:

- El namespacing por módulo seguiría siendo una mejora real (1 bundle en vez de N
  grupos, y capacidad de declarar dos veces el mismo nombre), pero es una
  **optimización, no un prerrequisito**. La decisión de implementarlo puede
  posponerse sin bloquear nada.
- El objetivo «full <90 s» sigue necesitando mover los ~750 tests que compilan C
  al corpus, y ahora esa vía **está abierta**: el modelo funciona.
- Quedan 137 programas en los otros corpus (`std_programs` 61, `test_generics` 50,
  `test_string_composition` 22, `migration` 12 —que NO deben migrarse, son entradas
  para un futuro reescritor—, `test_manual_memory` 9) más los que hoy viven dentro
  de archivos `test_*.py`.

### 16.3 Dos mediciones que evitaron adoptar una regresión

**`--dist loadfile`: medido y descartado.** Con 56 casos en un solo fichero, cada
worker de xdist construye sus propios bundles (el fichero de conformidad tarda
18 s con `-n auto` frente a 9 s en serie). `--dist loadfile` agruparía los casos en
un worker y reduce eso a 13 s, así que parecía una mejora obvia. **En la suite
completa es peor**: 313 s frente a 294 s, y además hace fallar
`test_runtime_hardening.py::test_oom_policy_can_be_disabled` —un test sensible a
los recursos, que pasa a compartir worker con tests más pesados—. Se mantiene la
distribución por defecto (`load`) y se deja constancia: la duplicación de bundles
bajo xdist queda como ineficiencia conocida (~9 s), y el arreglo correcto sería una
caché de bundles en disco compartida por los workers, con clave derivada del
contenido del grupo y del compilador — no de mtimes.

**Recuento de la suite.** `3531 passed, 23 skipped, 46 xfailed, 0 failed` en
293,97 s con `-n auto`. Baja respecto a los 3532 previos porque el wrapper viejo
`test_compliance_corpus.py` aportaba 53 tests parametrizados (uno por programa) y
el nuevo aporta 5, mientras que los 53 casos migrados y el test de regresión del
destructuring entran por otra vía. La aritmética neta es −1 test y el conjunto
sigue verde; conviene saberlo para no leer el cambio de total como una pérdida.

---

## 17. La suite estaba limitada por latencia; ahora lo está por trabajo

La ronda anterior dejó la suite en 294 s con `-n auto`, pero seguía habiendo un
techo que ningún `-n auto` podía mover: **cuatro monolitos**. Con xdist un test no
se divide, así que el reloj nunca podía bajar del test más lento — y el más lento
era `test_doc_blocks.py::test_every_marked_block_matches_reality` con **141 s de
setup**, compilando ~195 bloques de documentación en serie.

### 17.1 Partidos por bloque

| Gate | Antes | Ahora |
|---|---|---|
| `test_doc_blocks.py` | 141,2 s (1 test) | **20 s** en 201 tests |
| `test_frontend_no_crash.py` | 64,8 + 56,2 + 36,4 s | **27 s** en 337 tests |
| `test_api_docs.py` | 147,9 s de setup | **49 s** (pool de 4 procesos en el fixture) |

Dos decisiones de diseño detrás:

- **La regla no se duplica.** «Un bloque `pengu` compila; uno `fragment`/`invalid`
  no» se extrajo a `tools/check_doc_blocks.classify_failure`, que ahora usan *tanto*
  el CLI como los tests. Reescribir la regla dentro del test habría permitido que
  las dos versiones se separaran.
- **El pool de `gen_api_docs` es interno, no por test.** Los 9 tests de
  `test_api_docs.py` necesitan el mapa completo (`index.json` y `README.md` son
  agregados de los 27 módulos), así que partirlos por módulo habría exigido
  rediseñarlos. `_render_one` ya era una función pura por módulo, así que
  `build(workers=N)` los reparte en procesos — **verificado byte-idéntico** con 1 y
  con 4 workers (`process.map` preserva el orden, así que la salida no depende de
  quién termine antes).

Cada split añadió además un guardián barato contra un fallo silencioso: si el
escáner dejara de encontrar bloques, los ~200 tests se convertirían en no-ops
verdes, así que se afirma el recuento (`test_the_block_split_covers_the_documents`).

### 17.2 El resultado, y por qué no basta

**294 s → 241 s** (4:00) con 4031 tests, y la cota de latencia de 148 s ha
desaparecido. Pero el reloj apenas bajó, y eso es el hallazgo:

> 36 workers × 241 s ≈ **8700 core-segundos de trabajo agregado**. El objetivo
> `<90 s` necesita ≲3200: hay que **quitar ~60 % del trabajo**, no reordenarlo.

La suite pasó de estar limitada por latencia (un test lento) a estarlo por
**throughput** (suma de trabajo). Eso es un cambio de régimen, y hace que la
prioridad sea inequívoca: mover los ~750 tests que compilan C al corpus.

### 17.3 `--dist loadfile`, medido y descartado (segunda vez)

Con los monolitos ya partidos volvió a parecer buena idea (un fichero por worker
evitaría reconstruir fixtures). Medido: **311 s frente a 241 s**, y además un test
sensible a recursos (`test_runtime_hardening::test_oom_policy_can_be_disabled`) se
volvió inestable. Descartado con dos mediciones independientes en momentos
distintos. Se queda la distribución por defecto (`load`).

### 17.4 Perfiles por caso: migrar sin perder cobertura

Los `test_std_*_extended.py` compilan cada programa en **debug y release**, porque
la optimización expone otra clase de comportamiento indefinido. Migrarlos a un caso
de un solo perfil habría **perdido esa cobertura en silencio**, que es justo lo que
la misión prohíbe. Así que el runner ahora respeta `"profiles"` en el manifiesto:

```json
"std_programs/test_invoke_extended": {
  "feature": "std_programs",
  "platforms": ["linux", "macos", "windows"],
  "profiles": ["debug", "release"],
  "migrated-from": "tests/std_programs/test_invoke_extended.pengu"
}
```

Cada caso se ejecuta una vez por perfil declarado (por defecto, `debug`), con el
mismo `.expected`/`.exit`, y una sola construcción de bundle por (grupo, perfil).
Probado de punta a punta con `test_invoke_extended`: se migró, se borró
`tests/test_std_invoke_extended.py`, y el caso pasa en ambos perfiles en 15,2 s
frente a los ~25 s que tardaba el test anterior.

**Cobertura: 80,50 % → 80,80 %.** El borrado no costó cobertura, así que no hubo
que renegociar el suelo — el requisito sigue en 80 y ahora con más margen.

### 17.5 Estado y siguiente paso

La receta de migración está completa y probada: `migrate_main_to_case.py --source …
--id … --out … --profiles debug,release --apply`, borrar el test original,
regenerar los dos ficheros generados. Quedan por migrar los otros ~20 ficheros
`test_std_*_extended.py` (1 programa ↔ 1 test cada uno), `test_std_atlas_multitype`
(5) y los 61 programas de `tests/std_programs/` en total. Eso ataca los tres
objetivos a la vez: menos ficheros raíz (→ ≤15), más casos (→ ≥400) y menos
compilaciones individuales (→ <90 s).

---

## 18. Ronda 2: quitar la cota de latencia, y una carrera menos

### 18.1 Monolitos partidos (294 s → 239 s)

| Gate | Antes | Ahora |
|---|---|---|
| `test_doc_blocks.py` | 141,2 s (1 test) | **20 s** en 201 tests |
| `test_frontend_no_crash.py` | 64,8 + 56,2 + 36,4 s | **27 s** en 337 tests |
| `test_api_docs.py` | 147,9 s de setup | **49 s** (pool de 4 procesos) |

Y con ello el régimen de la suite cambia: **36 workers × 239 s ≈ 8600
core-segundos de trabajo agregado**, cuando `<90 s` necesita ≲3200. Ya no es un
problema de reparto sino de **cantidad**: hay que quitar ~60 % del trabajo, que son
los ~750 tests que compilan C por su cuenta.

### 18.2 Una carrera que sólo aparecía con carga

`test_runtime_hardening::test_oom_policy_can_be_disabled` fallaba de forma
intermitente (dos veces en runs distintos, con `load` y con `loadfile`). La causa
no era la carga en sí:

```python
c = REPO / "build" / "_oom_policy_check.c"     # el .c se escribe DENTRO de build/
...
#include "pengu_runtime.h"                      # include entre comillas
```

Un `#include "..."` se resuelve **relativo al fichero que incluye** antes de
consultar los `-I`. Como el `.c` estaba en `build/`, donde vive una **copia** de
`pengu_runtime.h` que otros tests reescriben con `shutil.copy2` (truncar y
escribir), el compilador leía esa copia *mientras otro worker la estaba
escribiendo*: `warning: pengu_runtime.h es más corto de lo esperado` y
`declaración implícita de pengu_sysig_alloc`. Cuantos más workers, más probable.

Arreglado escribiendo el sondeo en `tmp_path`: desde ahí el include entre comillas
cae a `-I REPO` y lee la cabecera canónica. Verificado bajo `-n auto`.

Es la tercera vez en esta misión que un test resulta no ser paralelo-seguro por
compartir un artefacto de `build/` (antes: el archivo `libpengu_runtime.a`
renombrado, y la afirmación sobre el `/tmp` compartido). El patrón es siempre el
mismo: **un fichero compartido tratado como si fuera privado.**

### 18.3 `--smoke`: el coste era la recolección, no los tests

`pengu selftest --smoke` tardaba 6,3 s. Medido: **2,76 s eran recolección de
pytest** — importar los 234 módulos de test para leer sus marcadores, aunque
luego se deseleccionen. Ahora `--smoke` pasa las rutas de los ficheros marcados
(descubiertas con el mismo AST que usa la guardia) más el runner del corpus, así
que la recolección baja a ~1,0 s y el total a 4,8 s.

El tier puro de unidades —el que corre el job `smoke` de CI, sin runtime— queda en
**1,4 s** (antes 3,16 s como filtro por marcador sobre `tests/`). El job de CI
ahora usa `pengu selftest --smoke` directamente; los casos `_smoke/` del corpus se
saltan solos porque el job no construye el runtime.

Lo que queda por encima de 3 s es la **construcción del bundle** (3,0 s) para los 3
casos del corpus, que pagan la importación en frío del compilador dentro del
proceso de pytest. Honestamente: `<3 s` se cumple para el tier de unidades y para
el job de CI, no para la combinación unidades+corpus con el runtime presente.

### 18.4 Perfiles por caso, y cobertura

Migrar `test_std_invoke_extended` exigía conservar su doble perfil (debug y
release). El runner ahora respeta `"profiles"` en el manifiesto y ejecuta el caso
una vez por perfil, con el mismo `.expected`/`.exit`, construyendo un bundle por
(grupo, perfil). El test original se borró.

**Cobertura 80,50 % → 80,80 %**, así que el borrado no costó cobertura y el suelo
de 80 sigue sin necesitar renegociación.

### 18.5 Errores míos en esta ronda, declarados

- Al instrumentar `build_bundle` para medir el coste del smoke, mi patrón de
  reemplazo coincidió en la línea equivocada y **rompió `tests/test_conformance.py`**
  (indentación del `for`). Detectado y reparado en el acto; el corpus volvió a
  verde en la misma comprobación. Lo menciono porque un fichero roto a medias es
  exactamente lo que no debe quedar en un árbol.
- Volví a medir `--dist loadfile` (311 s frente a 239 s) antes de descartarlo, en
  vez de fiarme de la medición anterior hecha con otra forma de la suite.

---

## 19. Un bug real del compilador, encontrado y arreglado (y la migración que desbloqueó)

La ronda 3 empezó reintentando la migración de los 23 `test_std_*_extended.py`.
**13 de 24 fallaron**, así que la revertí entera antes de borrar nada (el corpus
volvió a 57 casos verdes y los 23 tests siguieron intactos). La bisección del
grupo encontró el par mínimo: `test_whisper_extended` + `test_loom_extended`.

### 19.1 No era colisión de nombres: era dependencia de orden

```
[whisper]              OK
[loom]                 OK
[whisper, loom]        FALLA   TypeMismatchError: Could not infer type parameter(s) T
                               for generic function 'loom_running_sum'
[loom, whisper]        OK      ← el mismo par, al revés, compila
[hello, whisper, loom] FALLA
```

Eso descartó la hipótesis de «nombres top-level que chocan» (que la agrupación ya
cubre) y apuntó a estado compartido entre módulos.

### 19.2 Reproducción mínima, fuera de esta infraestructura

Tres ficheros en `tests/_repro/` (guardados ahí para que el hallazgo no dependa de
que alguien lo vuelva a derivar):

```pengu
# moda.pengu — f NO genérico
weave f with x as int into int:
    return x + 1
# modb.pengu — f genérico, mismo nombre simple
weave f shard T where T: Num with x as T into T:
    return x
# main.pengu — importa ambos y llama a moda.f con un int
```

```console
$ python pengu_project.py test --entry tests/_repro/main.pengu
  tests/_repro/main.pengu:5:5 [E0005] Could not infer type parameter(s) T for
  generic function 'moda_f'
```

`moda.f` recibe un `int` explícito: hay información de sobra para llamarla. El
compilador la trata como genérica y exige una `T` que la llamada no puede aportar.

### 19.3 Causa raíz: dos mitades que se sostienen mutuamente

1. **`pengu_checker.py` (bucle de importación).** Al importar un módulo se
   re-registraban *todos* los genéricos de su submódulo bajo
   `f"{bind_name}_{gname}"`. La tabla del submódulo también contiene los genéricos
   que *él* importó transitivamente, así que un genérico definido en `std/tally`
   quedaba registrado como `loom_running_sum` al importar `std/loom`. Se
   **inventaban** funciones que no existen.
2. **`pengu_infer.py` (call site).** Al llamar a `moda.f`, construía
   `fn_name = "moda_f"` y, si no estaba en la tabla pero el **nombre simple** `f`
   sí, copiaba ese genérico a `moda_f`. Como el nombre simple es de todos, `moda.f`
   heredaba el genérico de `modb`.

Ninguna de las dos mitades hace daño por separado; juntas convierten una llamada
perfectamente inferible en un error.

### 19.4 El arreglo

Se registra **quién define** cada genérico (`symbols.generic_function_owner`), la
propiedad se propaga por las importaciones, y las dos mitades pasan a exigir que el
genérico sea realmente del módulo en cuestión:

- el alias `{bind_name}_{gname}` sólo se crea si `owner == mod_file`;
- la adopción del nombre simple sólo ocurre si el genérico pertenece al módulo
  llamado.

No es el namespacing completo: es el arreglo estrecho que elimina la atribución
cruzada, y deja la puerta abierta a lo otro sin bloquear nada.

### 19.5 Verificación

- `tests/_repro/main.pengu` pasa (antes fallaba).
- Los 24 casos migrados pasan, y el **corpus completo: 80 casos en 74 s, 0 fugas**.
- Suite completa: **4009 passed, 0 failed**, cobertura **80,80 %** (el suelo de 80
  sigue sin necesitar renegociación).
- Tests de regresión en `tests/compiler/test_compiler_features.py`
  (`TestGenericsDoNotLeakAcrossModules`), **verificados en ambos sentidos**:
  revirtiendo la mitad del inferrer, `2 failed in 2.54s`; con el arreglo, `2 passed`.
  Cubren **los dos órdenes de importación**, porque el bug dependía de cuál fuera
  primero.

### 19.6 La migración que desbloqueó

Con el arreglo, los 23 programas migraron y pasaron:

| | Antes | Ahora |
|---|---|---|
| Casos del corpus | 57 | **80** |
| Ficheros de test raíz | 234 | **211** |
| Suite completa (`-n auto`) | 239 s | **227 s** |
| Cobertura | 80,80 % | 80,80 % |

Los 23 `test_std_*_extended.py` se borraron: su comportamiento —y más, porque el
caso compara el stdout **completo** y el código de salida, no una lista de
marcadores— vive ahora en el corpus, y se ejecuta en debug **y** release como antes
(`"profiles": ["debug", "release"]`).

Dos cosas que aprendí a hacer en esta ronda y conviene repetir: **verificar los
casos antes de borrar los tests viejos** (fue lo que permitió revertir limpiamente
los 13 fallos sin dejar el árbol rojo), y **guardar la reproducción mínima** en
`tests/_repro/` en cuanto aparece un bug, porque el valor del hallazgo no debe
depender de que alguien repita la bisección.

### 19.7 Error mío, declarado

La primera versión del test de regresión afirmaba `"All 2 test(s) passed."` cuando
el programa tiene **un** bloque `test` con dos aserciones dentro. El test fallaba
con el arreglo puesto; lo detecté al ejecutarlo y lo corregí antes de dar nada por
bueno. El programa compilaba y pasaba: era mi aserción la que estaba mal.

---

## 20. Un test que no podía fallar

La ronda 4 empezó midiendo de dónde sale el tiempo de verdad (agregado por
fichero, `--durations=0`): 5245 s, con `test_frontend_no_crash.py` (507 s) como
mayor consumidor, seguido de `test_conformance` (421), `test_cli_strict_c99` (412),
`test_cli_contract` (401) y `test_doc_blocks` (378). El patrón dominante era
**lanzar la CLI por entrada pequeña**: 378 spawns en un fichero, 195 en otro.

### 20.1 El hallazgo: la detección de crashes no detectaba crashes

`test_frontend_no_crash.py` lanzaba `python -m pengu_project check <fichero>` por
bloque y grepeaba la salida buscando `Traceback (most recent call last)`.

Inyecté un `RuntimeError` en `TypeInferrer.infer` y comprobé ambos caminos del CLI:

```
check_files   (pengu check <file>)   : contiene 'Traceback' = False
check_project (pengu check --entry)  : contiene 'Traceback' = False
     /tmp/blk.pengu:0:0 SIMULATED-B6-CRASH
```

**El marcador nunca aparece.** `check_sources_diagnostics` tiene un
`except Exception` (y `check_files` otro), y `_diagnostic_message` usa `str(exc)`,
nunca un traceback. Así que el barrido estaba verde pasara lo que pasara por el
front end: un test de resistencia a crashes **que no podía detectar la clase de bug
(B6) para la que se escribió**. Es peor que no tener test, porque anuncia una
cobertura que nadie tiene.

### 20.2 La firma correcta es estructural, no textual

Lo que distingue un error del intérprete tragado de un diagnóstico real es que el
primero llega a `_diagnostic_message` sin atributo `code`, así que sale con código
vacío y posición 0:0. Todo diagnóstico legítimo lleva uno.

Antes de afirmarlo lo **calibré**: los 286 bloques documentados producen 327
diagnósticos con 12 códigos distintos (E0002 ×144, E0004 ×78, E0000 ×61, …) y
**0 sin código**. Con eso, «ningún diagnóstico sin código» es una aserción real y
no una reformulación de «el compilador está descontento».

La prueba de no-vacuidad, en ambos sentidos: con el crash inyectado el test
**falla** (`1 failed in 0.72s`, y el informe nombra el crash); sin él, pasa. El
test anterior se quedaba verde en el mismo escenario.

### 20.3 Y de paso, el mayor consumidor de la suite

Los dos barridos masivos pasan a comprobar **en proceso**, así que ya no pagan
~0,36 s de arranque de intérprete e importación del compilador por entrada:

| Barrido | Antes | Ahora |
|---|---|---|
| `test_frontend_no_crash.py` | 157 s (3 monolitos) → 378 spawns | **58 s serial, 15 s en paralelo** |
| `test_doc_blocks.py` | 136 s serial | **49 s serial, 13 s en paralelo** |

La herramienta `tools/check_doc_blocks.py --check` sigue funcionando como CLI sobre
los documentos reales: `195 blocks verified, every marker matches reality` en 48 s
(antes ~2,5 min). Su `check_block` ya no lanza un hijo, así que el parámetro
`timeout` se acepta por compatibilidad y **ya no se aplica** (no hay proceso que
matar); queda dicho aquí porque es una pérdida real, pequeña, y no una omisión.

Al test de doc-blocks se le añadió la misma detección estructural: un diagnóstico
sin código en un bloque `pengu-fragment` habría pasado por «correctamente no
compila», que es la imagen especular del mismo agujero.

### 20.4 La aritmética, sin adornos

Quitar ~800 s de trabajo agregado bajó el reloj **de 227 s a 212 s**. No es un
error de medición: `reloj ≈ agregado / 36`, así que 800 s de agregado valen ~15 s
de reloj. Para llegar a `<90 s` hay que quitar del orden de **3800 s más**, y eso
es un programa de trabajo, no un ajuste.

La cobertura subió de 80,80 % a **81,01 %**, y conviene decir por qué: ejecutar en
proceso hace que la cobertura *mida* código que antes corría en un hijo y no se
atribuía al padre. Es un cambio de medición, no cobertura nueva, y no debería
contarse como una mejora de tests.

### 20.5 Migración: atlas multitype

Los 5 programas de `test_std_atlas_multitype.py` migraron con la receta probada
(debug y release) y el fichero se borró.

| | Antes | Ahora |
|---|---|---|
| Casos del corpus | 80 | **85** |
| Ficheros de test raíz | 211 | **210** |

### 20.6 Errores míos, declarados

- Añadí `F401` a la selección de `ruff` y salieron 416 errores que no eran míos: la
  selección del repositorio es `F821,E9`. Los 31 `F811` que aparecieron después son
  **preexistentes** en `pengu_lsp/server.py`, no de mi cambio.
- Al convertir `check_block` a proceso, la herramienta dejó de funcionar **como
  script** (`ModuleNotFoundError: pengu_project`): el hijo anterior heredaba la raíz
  por `cwd`. Lo detecté ejecutando el CLI de verdad, no sólo el test, y lo arreglé.

---

## 21. La estructura de coste del corpus, y por qué no puede crecer migrando programas grandes

### 21.1 Dónde está el coste (medido, no estimado)

| Parte | Coste |
|---|---|
| 10 builds de bundle (5 grupos × debug/release) | **83,7 s** |
| 85 spawns de caso | **0,5 s** (6 ms cada uno) |

El modelo batch hace exactamente lo que prometía: ejecutar un caso es ruido, construir
el bundle es todo. Y el coste está muy concentrado — el grupo 3 (21 casos) tarda
29,2 s + 27,5 s, mientras el grupo 0 (48 casos, el doble de grande) tarda 5,4 s + 4,9 s.

### 21.2 El intento de migrar `test_stdlib.py`: 41 de 115 fallan

Los 31 programas de `test_stdlib.py` migraron sin problema de forma individual, pero
al convivir en bundles **41 casos fallaron** y el corpus pasó de 78 s a **13:36**.
Causa, del compilador, no del runner:

```
std/scrolls.pengu:894: error: '__auto_type' undeclared
corpus/std_programs/scrolls.pengu:30:32: error: tipo incompatible
    para el argumento 1 de 'tally_is_empty'
```

El detector de colisiones del runner compara **nombres top-level de Pengu**, pero el C
colisiona en **nombres mangleados** (`tally_is_empty` de un caso contra la definición de
otro). Es una capa que la agrupación por nombres no puede ver, y agrupar más fino no
ayuda: más grupos significa más builds *y* más coste (§21.1). Revertido entero — los 31
ficheros de caso y sus entradas de manifiesto — con `test_stdlib.py` intacto.

Conclusión honesta para el objetivo: **el corpus no puede crecer a base de migrar
programas que arrastran grafos de `std` grandes**, hasta que el compilador namespace
símbolos por módulo. El corpus sí puede crecer con programas pequeños y autocontenidos,
que es lo que caracteriza a los 53 de compliance.

### 21.3 Un bug del runner que multiplicaba el coste de un caso malo

`_BundleCache` no cacheaba los **fallos**: cada caso de un grupo roto reintentaba la
compilación. Dos grupos rotos de ~25 casos cada uno a ~20 s por intento son los 13:36
observados, no los casos. Ahora el primer fallo se recuerda y el resto apunta a él en
vez de recompilar, con `test_a_broken_group_is_only_built_once` como guardia.

### 21.4 Caché de bundles compartida entre workers

Bajo xdist, **cada worker construye los grupos que toca**: es lo que inflaba
`test_conformance.py` a 528 s de trabajo agregado. Ahora hay una caché en disco
`build/_conformance_cache/` indexada por

* el contenido de los ficheros de caso del grupo,
* el perfil,
* el compilador,
* **y las fuentes del compilador y `pengu_runtime.h`**.

Ese último punto es deliberado: en §15.5 quedó documentado que la huella del proyecto
cubre el *programa* y su configuración, no el compilador, y que eso dejó un artefacto
obsoleto tras editar `pengu_parser/`. Una caché indexada sólo por las entradas del
programa habría repetido el error exacto.

| | Antes | Ahora |
|---|---|---|
| Corpus, caché fría | 85 s | 88 s |
| Corpus, caché caliente | 85 s | **2,0 s** |

### 21.5 Lo que la caché NO arregla, dicho claro

Una ejecución **fría con `-n auto` no mejora**: 217 s frente a 212 s. Los workers
arrancan a la vez, cada uno construye los grupos que necesita antes de que ninguno haya
publicado el resultado, y `os.replace` hace que gane el último. Precalentar en el
controlador de xdist tampoco es una victoria: serializaría 84 s en la ruta crítica antes
de repartir nada.

Así que la caché sirve donde sí sirve: iteración local (segunda ejecución en 2 s en vez
de 85 s) y CI con caché entre ejecuciones. Por eso `ci.yml` tiene ahora un paso
`actions/cache` sobre `build/_conformance_cache` con una clave rodante — las claves
internas son digests de contenido, así que una entrada restaurada y obsoleta simplemente
no se usa.

### 21.6 Errores míos, declarados

- Nombré la caché `_bundle_cache_key`, y **`bundle_c` es la subcadena que la guardia de
  la regla 1 lee como «este fichero inspecciona C generado»**. `test_conformance.py`
  pasó a ser un infractor y dos tests de política se pusieron rojos. Renombrado a
  `_groups_cache_key`; no inspecciona C generado, era mi nombre.
- Añadí soporte `into void` a la herramienta de migración (12 de los 31 programas lo
  usan) y `skip_under_sanitizers` al manifiesto (el job de sanitizers corre `pytest
  tests`, corpus incluido). Tras el revert **ninguno de los dos tiene usuario actual**;
  los dejo porque están verificados (el segundo con
  `test_a_case_can_declare_a_known_sanitizer_finding`) y la siguiente migración los
  necesita, pero conviene saber que hoy son capacidad sin uso.

---

## 22. Cuánto queda realmente por migrar: 89 tests, no 501

### 22.1 La corrección

Clasifiqué los 2446 tests raíz con una heurística («llama a `compile_run` y afirma
stdout») y salieron 501 candidatos. **Estaba mal**: contaba como convertibles los tests
que llaman a `gen_bundle` para **inspeccionar el C generado**, que el corpus no puede
expresar porque juzga comportamiento, no texto. La clasificación corregida:

| Clase | Tests | ¿Caso del corpus? |
|---|---|---|
| Compila, ejecuta y afirma stdout/exit | **89** | sí |
| Inspecciona C generado (`gen_bundle`, `_c`, snapshots) | 393 | **no** — el corpus no mira C |
| Diagnóstico en tiempo de compilación (`E00xx`, `check_error`) | 595 | **no** — el corpus sólo compila programas válidos |
| Unidad (parsing, LSP, CLI, formato, semver…) | 1369 | **no** |

Y el análisis destapó algo que cambia el modelo de coste: **`gen_bundle` está
memoizado** (1 ms en caliente frente a 229 ms el primero). Los 393 tests que inspeccionan
C ya son baratos; el coste restante es trabajo real de front-end sobre programas `std`
grandes y ~500 spawns de CLI.

### 22.2 Lo que esto significa para el objetivo

- **`≥400` casos**: migrando *todo* lo convertible se llega a ~175. Escribir 300 casos
  nuevos es la única vía, y exige decidir qué comportamiento del lenguaje cubren.
- **`≤15` ficheros raíz**: la migración quita un puñado; los ~2000 tests restantes
  (diagnóstico, C, unidad) tendrían que **fusionarse** en ~14 ficheros. Es una
  consolidación organizativa, no una migración: mismo trabajo, mismas aserciones,
  menos ficheros.
- **`<90 s`**: el agregado medido es ~4540 s y el reloj ~208-228 s. Para 90 s hacen
  falta ~2500 s menos, y lo que queda son compilaciones reales de programas `std` por
  la CLI (`test_cli_strict_c99` 386 s, `test_cli_contract` 384 s,
  `test_concept_bounds_matrix` 226 s, `test_stdlib` 225 s). No hay caché que las evite:
  cada una comprueba un programa distinto.

Ninguna de las tres se alcanza con más trabajo de infraestructura de tests. Son
renegociaciones del objetivo, y por eso se para y se pregunta (§22.4).

### 22.3 Lo que sí se hizo esta ronda

Migrados 8 programas de la familia backward-compat y del matrix de atlas, y borrados
sus 7 ficheros:

| | Antes | Ahora |
|---|---|---|
| Casos del corpus | 85 | **93** |
| Ficheros de test raíz | 210 | **203** |
| Suite completa (`-n auto`) | 212-228 s | **208,8 s** |
| Cobertura | 81,03 % | 81,00 % |

Los ids se renombraron a nombres legibles (`compat_backward_compat_0` →
`backward_compat`) porque el id de un caso es su nombre público: aparece en
`--test`, en el JSONL y en el informe.

### 22.4 Error mío, declarado

En el lote de migración volví a leer el manifiesto al final del script, **descartando
el arreglo de metadatos** que había hecho antes en el mismo script: `compat_data` quedó
apuntando a `build/_migrate_src.pengu` en vez de a su fichero de test real. Detectado y
corregido, pero es el segundo error de este tipo (leer-modificar-escribir dentro de un
script) y conviene arreglar el patrón, no el caso.

---

## 23. Dos agujeros en el job de sanitizers, destapados al retirar los backward-compat

### 23.1 El que yo mismo abrí

Al borrar los 7 ficheros backward-compat (§22) rompí `sanitizers.yml`, que los
invocaba por ruta en dos sitios (`PENGU_SANITIZER_DESELECT` y un paso dedicado). CI
habría fallado. Se detectó revisando las referencias ejecutables **antes** de dar la
ronda por buena, y se retargeteó a los ids del corpus:

```
tests/test_conformance.py::test_conformance_case[std_programs/backward_compat]
tests/test_conformance.py::test_conformance_case[std_programs/compat_data]
tests/test_conformance.py::test_conformance_case[std_programs/backward_compat_util]
```

El contrato de los sanitizers (`test_every_sanitizer_pytest_step_deselects_the_known_leak`
y `test_sanitizer_workflow_deselects_by_name_not_by_disabling_detection`) afirmaba el
nombre viejo; actualizado con él.

### 23.2 El de fondo: el corpus no estaba instrumentado

Investigando lo anterior apareció algo peor. El job de sanitizers corre
`pytest tests` —el corpus incluido— pero **el runner del corpus no leía
`PENGU_CFLAGS`/`PENGU_LDFLAGS`**, que es como el job inyecta `-fsanitize=address`.
Es decir: el corpus se compilaba sin instrumentar y el job salía verde. Un verde que
no cubría nada.

Al cablear los flags apareció la segunda mitad: `_pick_cc()` devuelve TCC por defecto y
**TCC ignora `-fsanitize` en silencio**. Medido: el bundle cacheado no enlazaba
libasan. Así que un run «instrumentado» seguía siendo un binario normal.

Arreglado en tres partes:

1. el enlace del bundle honra `PENGU_CFLAGS`/`PENGU_LDFLAGS`, igual que
   `conftest.compile_run`;
2. cuando hay flags de instrumentación se pide el compilador real (gcc/clang) en vez de
   TCC, porque TCC no instrumenta y no lo dice;
3. los flags entran en la **clave de la caché**, para que un run saneado no pueda
   servirse del build normal ni al revés.

Verificado: `libasan enlazada: True`, y el comando exacto del paso de CI pasa
(`2 passed, 1 deselected`) con el bundle realmente instrumentado.

### 23.3 El plan para `≤15` ficheros raíz, investigado

La vía elegida es **mover**, no fusionar. Fusionar 203 ficheros en 15 sombrea en
silencio los tests con el mismo nombre en dos ficheros (el último gana), así que
exigiría renombrar cientos de tests y cambiar sus ids. Mover no toca ni una aserción.

Los hechos que lo hacen viable, comprobados:

- `tests/__init__.py` **existe**, así que `tests` es un paquete: los ficheros movidos a
  `tests/<area>/` son `tests.<area>.<modulo>` y **no colisionan por nombre de módulo**
  (con `__init__.py` en cada área, que hay que crear);
- ya hay subdirectorios con tests (`tests/abi`, `tests/conformance`), así que es el
  patrón de la casa;
- `tools/gen_test_policy_baseline.py` usa `TESTS.glob("test_*.py")` **no recursivo**: el
  recuento de ficheros raíz baja solo, y la meta-guardia pasa a exigir el conjunto nuevo;
- `pytest.ini` no fija `testpaths`, así que la recolección sigue siendo `tests/` completa.

Lo que hay que tocar a la vez: ~20 pasos de `ci.yml` que invocan rutas concretas
(agrupados por área, así que las áreas pueden seguir los propios gates de CI),
`tools/gen_conformance_deps.py`, la base de política y las rutas citadas en
`AGENT_TESTING.md`. Es un cambio grande y **atómico**: a medio hacer deja CI roto, así
que se ejecuta en una ronda con presupuesto completo, verificando que el recuento de
tests recolectados y la cobertura no cambian.

---

## 24. `tests/*.py raíz ≤15`: hecho moviendo, no fusionando

### 24.1 Por qué mover y no fusionar

Fusionar 203 ficheros en 15 parece el camino obvio y es una trampa: al concatenar
módulos, **dos `def test_x` con el mismo nombre se sombrean** y el segundo gana. Los
tests desaparecerían sin que nada se ponga rojo — el peor fallo posible en este
trabajo. Evitarlo exige renombrar cientos de tests y cambiar sus ids.

Mover no toca ni una aserción. Los hechos que lo hacían viable, comprobados de
antemano: `tests/__init__.py` existe (así que `tests` es un paquete y los módulos
movidos son `tests.<área>.<x>`, sin colisiones de nombre), ya había subdirectorios con
tests, y el generador de política usa `glob` no recursivo, con lo que el recuento de
raíz baja solo.

### 24.2 Lo que se movió

191 ficheros a 12 paquetes de área; quedan **12 en la raíz** (el techo es 15):

| área | ficheros | | área | ficheros |
|---|---|---|---|---|
| `compiler/` | 43 | | `tooling/` | 15 |
| `cli/` | 23 | | `features/` | 13 |
| `regression/` | 21 | | `docs/` | 11 |
| `runtime/` | 18 | | `lsp/` | 8 |
| `codegen/` | 18 | | `gates/` | 4 |
| `stdlib/` | 13 | | `grammar/` | 4 |

### 24.3 Lo que se rompió al mover, y cómo se arregló

Mover un fichero un nivel más abajo rompe tres cosas, y las tres aparecieron en la
verificación:

1. **`REPO = Path(__file__).resolve().parent.parent`** (26 ficheros) pasó a apuntar a
   `tests/`. Corregido a `parents[2]`. Es el fallo más silencioso de los tres: algunos
   tests no reventaban, leían el árbol equivocado.
2. **Imports entre módulos de test** (`from tests.test_lsp import …`) apuntaban a
   módulos que ya no están en la raíz. Reescritos a `tests.lsp.test_lsp`.
3. **Rutas construidas con `Path`** (`TESTS / "test_ffi_libs.py"`), que mi primera
   reescritura —basada en el texto `tests/test_x.py`— no cazaba, y que sólo salieron al
   ejecutar la suite.

Además, dos dependencias de "raíz" que había que generalizar **antes** de mover:

- `pengu_project._selftest_smoke_targets` listaba `os.listdir(tests)`; ahora recorre el
  árbol. Sin eso, `--smoke` habría encontrado cero ficheros y corrido nada, en verde;
- `tools/gen_test_policy_baseline.py` usaba `glob` no recursivo también para las
  **reglas** (allowlists, `time.sleep`, lectores de C generado). Ahora las reglas son
  recursivas y sólo el *recuento de raíz* es no recursivo: si no, mover un fichero lo
  habría sacado del alcance de la meta-guardia sin decirlo.

### 24.4 Verificación

| | Antes | Ahora |
|---|---|---|
| Ficheros de test raíz | 203 | **12** (techo 15, con guardia) |
| Tests recolectados | 4071 | **4071** (idéntico) |
| Suite completa (`-n auto`) | 200 s | **216 s** |
| Cobertura | 81,00 % | **81,00 %** |
| `--smoke` | 1,6 s | **1,56 s** |
| `--affected HEAD` | — | **5,6 s** |

El recuento de tests es la prueba de que no se perdió ninguno: 4071 antes y después.
La cobertura no se movió, que es la otra mitad.

Añadida `test_the_root_test_set_stays_small`, que falla si el recuento pasa de 15 —
la base congelada fija el conjunto exacto, pero es un trinquete sobre *cambios*:
regenerarla grabaría 40 ficheros sin protestar. Verificada bajando el límite a 2
(`1 failed`).

### 24.5 Los documentos históricos no se tocaron

71 ficheros citaban rutas movidas, pero sólo 43 eran referencias **vivas**
(workflows, herramientas, tests, documentación de estado actual). Los `AUDIT_*.md`,
`CHANGELOG.md` y `docs/archive/*` **no se reescribieron**: describen lo que se midió
en su momento y las rutas eran correctas entonces. Reescribirlos habría falsificado el
registro para que pareciera coherente con hoy.

### 24.6 Verificación de CI ejecutando sus pasos de verdad

Ejecuté **los siete pasos `pytest` de `ci.yml`** con sus comandos reales (el de la
suite completa aparte). Seis pasaron a la primera y **uno falló**, lo que es
exactamente el motivo de hacerlo:

```
[FALLA] Safety & supply-chain gate (FASE 5)
FAILED tests/regression/test_phase5_bugfixes.py::test_bundle_abi_assert_is_c99_safe
```

Es **la misma carrera que arreglé en la ronda 4** (§18.2), en otro fichero: el test
escribía su sonda en `build/_abi_assert_check.c` y el C generado lleva
`#include "pengu_runtime.h"`. Un include entre comillas se resuelve **relativo al
fichero que incluye** antes que por `-I`, así que leía `build/pengu_runtime.h`, la copia
que otros tests reescriben con `shutil.copy2`; si uno estaba a mitad, la compilación
veía una cabecera truncada.

Que no lo viera la suite completa y sí el gate es informativo: el gate mete los tests
que compiten por ese fichero en los mismos pocos workers, así que la ventana se solapa.
**Un test puede ser verde en la suite y rojo en CI por cómo se reparte**, y la única
forma de saberlo es correr el gate.

Arreglado con `tmp_path` (desde ahí el include cae a `-I REPO`). Buscadas más
instancias del patrón: ninguna.

Resultado final: **7/7 gates verdes**.

---

## 25. La duplicación de bundles era el 24% de la suite

### 25.1 Lo que dijo la medición

Tras la consolidación volví a medir el agregado: **5075 s**, y el reparto no era el que
esperaba.

| fichero | agregado | % | n |
|---|---|---|---|
| `test_conformance.py` | **1207 s** | **23,8 %** | 110 |
| `cli/test_cli_strict_c99.py` | 433 s | 8,5 % | 59 |
| `cli/test_cli_contract.py` | 388 s | 7,6 % | 138 |
| `stdlib/test_stdlib.py` | 229 s | 4,5 % | 31 |
| `compiler/test_concept_bounds_matrix.py` | 228 s | 4,5 % | 87 |

El corpus era **el mayor consumidor de la suite por un factor de tres**, y no por los
casos: los 93 spawns cuestan ~0,5 s en total. Lo que costaba 1207 s era que **cada
worker reconstruía los grupos que tocaba**, cuando construir los diez bundles cuesta
84 s en total. Ciento veinte veces el trabajo necesario, repartido.

### 25.2 Por qué `--dist loadfile` no era la respuesta (y `loadgroup` sí)

La cura obvia —un fichero por worker— ya la había medido y descartado **dos veces**
(311 s y 313 s frente a 219 s), porque pone los barridos de documentación (241 y 156
tests) en un solo worker.

`--dist loadgroup` es la herramienta correcta: los tests marcados con
`pytest.mark.xdist_group(...)` van al **mismo** worker, y el resto se reparte como
siempre. Marcando los casos del corpus **un grupo por bundle de colisión**, cada bundle
se construye una vez y los barridos de documentación siguen repartiéndose.

| | antes | ahora |
|---|---|---|
| Corpus solo (`-n auto`) | 124 s | **77 s** |
| Suite completa (`-n auto`) | 219 s | **186 s** |

Está en `pytest.ini` (`addopts`), así que aplica también en CI. Verificado que no rompe
la ejecución en serie (sin `-n`) y que los 7 gates de CI siguen verdes.

### 25.3 Lo que NO mueve la aguja, medido

- **gcc frente a TCC**: 197 ms frente a 17 ms por compilación. Con ~750 compilaciones,
  son ~135 s de agregado (~4 s de reloj). Real, pero pequeño; no justifica cambiar el
  compilador que usa `compile_run` (que además es lo que permite usar sanitizers).
- **Número de workers**: `-n 24` dio 177 s y `-n auto` (36) 186 s. Dentro del ruido de
  una máquina compartida, así que no se fija: `auto` es lo correcto para los runners de
  4 núcleos de CI.

### 25.4 El suelo real de `<90 s`, con la aritmética

`reloj ≈ agregado / (workers × utilización)`. Con 36 workers y ~60 % de utilización,
90 s exigen un agregado de ~1900 s. Hoy es de ~4400 s tras esta ronda. **Hay que quitar
más de la mitad del trabajo**, y ya no queda trabajo *duplicado* que quitar: lo que
queda es la cola larga (~2000 s en ~200 ficheros) de tests que comprueban programas
distintos.

Las dos únicas vías que quedan son de otra naturaleza:

1. **una caché de front-end en el compilador** (parse+check memoizados por contenido),
   que es un cambio de producto, no de tests, y beneficiaría a toda la suite porque
   muchos tests re-comprueban los mismos módulos `std`;
2. **borrar tests**, que no es una opción.

Es la frontera donde hay que decidir, y por eso se reporta en vez de seguir.
