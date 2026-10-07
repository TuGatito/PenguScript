# AUDIT 1.0 — FASE 8 (ROADMAP 2.0): Completar tests

> Documento de auditoría **no normativo** (español, como el resto de los audits).
> Los tests, el código y los commits están en inglés.
> Regla que gobierna la fase (Anexo C, C1): **ningún gate aprueba una propiedad
> inspeccionando texto**. Un gate compila, ejecuta o mide.

- **Estado de la fase:** **15 items cerrados** (uno de ellos, 8.11, cerrado
  *retirando* la afirmación en vez de dejarla sin gate), **2 parciales con
  medición** (8.2: el job de sanitizers no puede estar verde porque las fugas son
  de la stdlib; 8.12: el `.exe` real no es verificable sin MinGW) y **ninguna
  premisa del roadmap sobrevivió intacta**: las de 8.1, 8.2, 8.4, 8.6, 8.8, 8.9 y
  8.16 estaban obsoletas o incompletas, y cada refutación está medida abajo.
- **Items nuevos abiertos durante la fase:** 8.19–8.23 (hallazgos F8-N2, F8-N4,
  F8-N6, F8-N7, F8-N9), todos con programa de reproducción.
- **Commit base de la fase:** `32e10fa` (cierre de Fase 7).
- **Máquina de medición:** Linux x86_64, GCC 15, 36 núcleos, `gcc`/`clang`
  presentes, **sin** `x86_64-w64-mingw32-gcc` (hay `wine`), sin `valgrind`.

## Resumen de estado

| # | Item | Estado | Evidencia |
|---|------|--------|-----------|
| 8.1 | Convertir los 4 gates de texto (B10) | ✅ premisa refutada; F8-N3/N4/N4a | commits `49cb5ba`, `1a27357`, `7dd19a8`; clasificación medida de los 56 programas de std |
| 8.2 | Job de sanitizers verde (B9) | ⏸️ **parcial, premisa refutada** | commit `df2ffc0`; medido: 6/6 fallos en los 3 archivos legacy y **164 marcas de fallo al 92 %** del suite bajo ASan |
| 8.3 | `ruff` con `F821,E9` como error (A11) | ✅ | commit `68a5f5b`; `ruff check --select F821,E9 .` → 0 |
| 8.4 | Corpus de compliance (A13) | ✅ **54 programas** (pedido: 50) | commit `eff1288`; `pytest tests/test_compliance_corpus.py` → 60 passed |
| 8.5 | Corpus de migración (A13) | ✅ (alcance medido: ≥0.10.0) | commits `66d35e3`, `d3b0b19`; `pytest tests/test_migration_corpus.py` → 21 passed |
| 8.6 | `pytest-cov` con umbral | ✅ **80.20 % medido**, umbral 80 | commits `73cda9a`, `bf9e782` |
| 8.7 | Property-based testing (M13) | ✅ 7 propiedades, 8 passed / 1 xfailed | commit `647bca2`; hallazgo F8-N9 |
| 8.8 | Contrato de CLI | ✅ 27 subcomandos (no 25) + 5 violaciones halladas | commit `1bf99a9`; 122 passed, 5 xfailed |
| 8.9 | Cada `code="Exxxx"` alcanzable | ✅ 73/73 (69 con programa + 4 exentos) | commit `0595f07`; 133 passed, 4 xfailed |
| 8.10 | Estrés a 10 000 líneas | ✅ | commit `7ae14c8`; check 6.51 s, build 7.15 s sobre 10 003 líneas |
| 8.11 | Job real de MSVC **o** retirar la afirmación | ✅ **retirada** (opción B) | commit `960cc19` |
| 8.12 | `cross-compile.yml` | ⏸️ workflow entregado; `.exe` real no verificable aquí | commit `dca109f` |
| 8.13 | Workflows de los corpus | ✅ | commit `dca109f` |
| 8.14 | `codeql.yml` | ✅ | commit `dca109f` |
| 8.15 | Actions fijadas a SHA | ✅ | commit `dca109f`; `grep -rn 'uses:.*@v[0-9]' .github/` → 0 |
| 8.16 | `nightly.yml` con presupuesto realista | ✅ + hallazgo F8-N5 | commit `dca109f` |
| 8.17 | Tests flaky | ✅ los 3, medidos antes y después | commits `b3d8f3c`, `57323eb`, `e0ad36b` |
| 8.18 | Fixtures de compilación C | ✅ | commit `520a793` |

---

## 8.3 — `ruff` con `F821,E9` como error (bloqueante A11)

**Premisa verificada primero.** El roadmap pedía añadir `ruff` a
`requirements.txt`, crear `pyproject.toml` y añadir el paso a CI. Medición:
`requirements.txt` **ya** traía `ruff>=0.6` y `ci.yml:75` **ya** ejecutaba
`ruff check --select F821,E9`. Lo que faltaba era la configuración declarativa.

**Qué se hizo.** `pyproject.toml` con `[tool.ruff]`, `[tool.ruff.lint]
select = ["F821","E9"]` y exclusiones de terceros. La lista de selección es el
contrato del repo, no una preferencia de estilo: un nombre indefinido en este
código es un crash latente del compilador (así se coló B6).

**Evidencia.**
```
$ python -m ruff check --select F821,E9 --exclude extern,build,vscode-extension .
All checks passed!
$ python -m ruff check .        # lee pyproject.toml
All checks passed!
```

**C2.** El gate no necesita test propio: `ruff` es el oráculo. Lo que sí se
verificó es que el `select` mínimo permite activarlo en HEAD **sin** un solo
`# noqa`.

---

## 8.2 — Job de sanitizers (bloqueante B9) — ⏸️ PARCIAL, PREMISA REFUTADA

**La premisa del roadmap es falsa en dos direcciones, y está medido.**

La premisa era: *"solo el primer paso hereda el `--deselect`; los otros dos no;
con heredarlo, el job pasa"*. Se corrigió lo primero (es real) y se refutó lo
segundo.

**(a) El bug de propagación es real.** El node id estaba inline en el primer
`pytest tests`; el tercer paso ("ASan/UBSan on the std programs") re-ejecuta el
archivo que *contiene* el leak y valgrind hacía lo mismo. Ahora vive **una sola
vez** en el `env` del workflow (`PENGU_SANITIZER_DESELECT`) y los 4 pasos de
pytest lo consumen. Test nuevo:
`tests/test_known_issues.py::test_every_sanitizer_pytest_step_deselects_the_known_leak`
(parsea el YAML y falla si un paso futuro lo olvida; **verificado revirtiendo el
bloque `env`** → `1 failed`).

**(b) Deselectar `test_std_backward_compat` NO alcanza.** Medición con los flags
del job (`PENGU_CFLAGS=-fsanitize=address,undefined`, `ASAN_OPTIONS` con
`detect_leaks=1:abort_on_error=1`):

```
$ pytest tests/test_std_backward_compat.py tests/test_std_data_backward_compat.py \
         tests/test_std_util_backward_compat.py -q
6 failed in 96.92s      # los 6 (2 perfiles x 3 archivos), no 1
```

Las trazas de LeakSanitizer apuntan a **código de la stdlib**, no al modelo de
auto-banish:

```
Direct leak of 576 byte(s) allocated from:
    #1 pengu_list_new           pengu_runtime.h:1816
    #2 invoke_new_parser        ../../std/invoke.pengu:105
Direct leak of 512 byte(s) allocated from:
    #1 pengu_map_new_owned      pengu_runtime.h:2270
    #3 Parser_parse_impl        ../../std/invoke.pengu:292
```

**(c) El suite completo bajo ASan tampoco puede estar verde.** Con los 3 archivos
anteriores **deseleccionados**, la enumeración de las fugas restantes del suite
completo bajo ASan produjo **164 marcas de fallo al 92 %** de la corrida (se
interrumpió ahí: el número ya era concluyente). Es decir: no es "un test
conocido", es una clase de fuga repartida por la stdlib.

**Decisión (con el criterio del briefing).** El fix real (liberar los temporales
de la stdlib / del codegen) es un cambio de propiedad de memoria en `std/*.pengu`
y `pengu_codegen.py`: es un item propio, no un ajuste de CI. Se abre como
**item 8.19** para 1.1 con esta medición. Lo que se entrega en 8.2 es:

1. el bug de propagación corregido (era real y hacía ruido), con un test que falla
   si un paso futuro lo olvida;
2. el deselect ampliado a **los tres** archivos medidos;
3. el job partido en **los dos contratos que sí puede sostener**, en vez de una
   lista de deselectos más larga que lo que comprueba:

| Paso | Contrato | `detect_leaks` | Medición |
|---|---|---|---|
| `Memory safety across the suite (ASan + UBSan)` | Use-after-free, overflow, UB en todo el suite | **0** (declarado) | Primera corrida: **16 failed, 3253 passed, 46 xfailed, 1 xpassed**. Los 16 se resolvieron en dos clases (13 no pueden sostener su premisa bajo instrumentación y ahora llevan `requires_no_sanitizer_reason(...)`; **3 son el hallazgo real F8-N10**). Verificación final en §"Mediciones finales" |
| `Leak freedom on the auto-banish model` | Cero fugas en el subconjunto verificado | **1** | **4 passed, 1 xfailed** (el xfail es el leak rastreado) |
| `Memory safety on the std legacy-compat programs` | Sin errores de memoria en los programas cuyo leak está rastreado | **0** | **6 passed** |
| valgrind job | El mismo subconjunto con el segundo detector | — | **no medido aquí** (no hay valgrind en la máquina); el paso ya no selecciona ficheros totalmente deseleccionados |

El silencio del veredicto de fuga en el primer paso es **declarado**, no escondido:
`tests/test_known_issues.py::test_the_leak_verdict_is_only_disabled_when_it_is_declared`
exige que existan los dos contratos, que el workflow nombre el item 8.19 que lo
justifica y que nadie apague el veredicto desde el `env` del job (donde el lector
no vería qué paso renuncia a qué).

**Criterio de reapertura:** cuando 8.19 cierre las fugas de la stdlib debe poder
correrse el suite completo con `detect_leaks=1` y `--deselect` vacío; el test de
propagación obliga a tocar el workflow para quitar la variable, y el test de los
dos contratos obliga a borrar la rama `detect_leaks=0`.

---

## 8.1 — Los 4 gates de texto (bloqueante B10)

### Premisa refutada #1: `tests/test_error_codes_uniqueness.py` ya estaba convertido

El roadmap lo listaba como gate de texto pendiente. **Medición:** la segunda mitad
del archivo (Fase 7, item 7.2) ya recorre las emisiones crudas con
`tools.gen_error_catalog.extract_error_emissions()` (AST de los emisores) y
`test_the_split_is_real_not_cosmetic` compila tres programas con
`check_error(...)`. No quedaba nada que convertir; se documenta como ya cerrado.

### Gate 1 y 2: `test_cli_strict_c99.py` y `test_c99_portability.py`

Sustituido `assert "__extension__" not in bundle` por compilación real. El
hallazgo clave es que **`-pedantic-errors` a secas no basta**: `__extension__`
existe precisamente para silenciar `-pedantic`, así que el bundle GNU pasa
`-pedantic-errors` sin una queja. Medido sobre el bundle por defecto del programa
de prueba: **0 errores con el keyword, 9 sin él**. El gate usa
`-D__extension__=` para neutralizarlo y así poder afirmar que el modo estricto no
depende de una extensión GNU. El half "el bundle por defecto debe ser rechazado"
es el guardia de no-vacuidad.

**Clasificación medida de los 56 `tests/std_programs/test_*.pengu` con
`--strict-c99`** (comando y conteos al final; `-fmax-errors=1` para clasificar):

| Clase | N | Qué significa |
|---|---|---|
| **CLEAN** | **23** | compilan con `-std=c99 -pedantic-errors` **y ejecutan** con rc 0 → afirmados, verdes |
| **STRICT_MISCOMPILES** | **1** | compila limpio y **se comporta distinto al ejecutar** (F8-N4a) |
| **B5_STATEMENT_EXPRESSIONS** | **14** | solo bloqueados por `({ ... })` (B5 / roadmap 3.3) → `xfail(strict=True)` |
| **STRICT_CODEGEN_UNDECLARED** | **18** | el bundle es **C inválido** (F8-N4) → `xfail(strict=True)` |

Los `xfail` son `strict=True`: cuando B5 o F8-N4 se arreglen, esas filas pasan a
`xpass` y el archivo falla hasta promoverlas a aserciones.

### Gate 4: `test_attributes_msvc.py` → `test_attributes_msvc_text.py` + gate real

Renombrado (es un test de texto legítimo del mapeador de dialecto) y añadido
`tests/test_attributes_msvc_native.py`, que **invoca un compilador que entiende
sintaxis MSVC**: `clang -fdeclspec -fms-extensions` en cualquier runner, y
`cl.exe /Zs` cuando existe.

**El gate nuevo encontró un bug real en la primera ejecución (F8-N3):**

```
error: expected ';' at end of declaration list
   39 |   int32_t head __declspec(align(8));
```

El mapeador MSVC sustituía el *texto* del atributo pero conservaba la *posición*
GNU (post-declarador), que `cl.exe`/clang-MS rechazan. Arreglado en
`pengu_codegen.py` (el `__declspec` precede al declarador, también para campos
array). El archivo incluye un **control negativo**: reintroduce la emisión previa
y exige que el compilador la rechace, así que el gate no puede volverse vacío y la
regla C2 queda automatizada.

**Resultado:** `test_attributes_msvc_native.py` + `test_attributes_msvc_text.py` →
**5 passed, 1 skipped** (el `cl.exe` real, ausente aquí).

### Criterio `grep -rn 'not in bundle\|not in result' tests/`

Los 4 gates nombrados por B10 compilan o ejecutan. La medida pasa de **7** a **3**
coincidencias, y las 3 que quedan están clasificadas:

| Archivo | Qué afirma | Por qué se queda |
|---|---|---|
| `test_compiler_features.py:1235` | `c->inc` no aparece en el bundle | **Motivo medido**, no comodidad: un valor `ref to T` no se puede construir en un programa dirigido por `main` (el lenguaje no tiene operador de dirección, un `id` no se convierte implícitamente — `Argument 'c' of 'bump' expects 'ref to Counter', got 'Counter'` — y el único asignador es un import de std), así que la emisión se fija por texto y el lado runtime lo cubren las suites que pasan refs entre weaves |
| `test_lsp_phase5.py:87` | `b_uri not in result.changes` | Salida **estructurada** de una operación LSP (no es código generado) |
| `test_stdlib.py:237` | marcadores ausentes en `stdout` | Marcadores de la stdlib, no del compilador |

Las otras dos coincidencias que existían al empezar la fase sí se convirtieron:
las dos comprobaciones de `TestEnchantingMethodCalls::test_enchanting_method_call_value`
pasaron a compilar **y ejecutar** (el programa sólo construye e imprime "Juan" si
la llamada bajó a `Persona_present(&p)`), y `test_run_cache.py:167` pasó a
aserciones por líneas exactas (8.17③).

---

## 8.4 — Corpus de compliance: **54 programas** (pedido: 50)

`tests/compliance/NNN-slug.pengu`, uno por sección de `LANGUAGE.md` (§2 … §19),
más `run_all.py` (check → build → ejecutar → comparar rc; exit 0 solo si todos
pasan), `corpus.json` (mapa `{file, section, title, expects_rc, pins}`),
`EXPECTED.md` y `tests/test_compliance_corpus.py`.

**Evidencia.**
```
$ python tests/compliance/run_all.py          → 54/54 passed, exit 0
$ python tests/compliance/run_all.py --check-corpus → corpus ok, exit 0
$ pytest tests/test_compliance_corpus.py -q   → 60 passed in 96.13s
```
El gate de integridad ata cada sección del corpus a una sección **real** de
`LANGUAGE.md` (título incluido), así que un programa no puede inventarse su
sección, y `corpus ↔ disco` es 1:1.

---

## 8.5 — Corpus de migración

`tests/migration/<version>/<programa>.pengu` + `EXPECTED.json` + `README.md` +
`tests/test_migration_corpus.py`. **10 programas en 8 líneas de versión**
(0.10.0, 0.10.1, 0.11.0, 0.12.0, 0.13.0, 0.14.0, 0.15.0, 0.16.0).

**Lo que debe fallar, falla con el código documentado** (medido):
`legacy-and-separator.pengu` → `E0000` ("`and` is no longer a separator"),
`ambiguous-and-after-call.pengu` → `E0005` (ambiguo tras una llamada con
argumentos). Los otros 8 compilan, construyen y devuelven el rc documentado.

**Alcance medido y diferido.** `CHANGELOG.md` lista **35** versiones publicadas
(0.3.0 … 0.16.0). La cobertura se afirma por **línea menor desde 0.10.0** porque
`MIGRATION.md` §2 (la tabla normativa) empieza ahí, el contrato de estabilidad
prohíbe que un patch introduzca sintaxis nueva (14 programas `0.13.x` idénticos
serían teatro) y la sintaxis pre-0.10 **no está documentada en ningún documento
normativo actual** — programas "históricos" para 0.3.0–0.9.1 no serían
verificables por nada. El hueco queda escrito en `tests/migration/README.md`.

**Evidencia:** `pytest tests/test_migration_corpus.py -q` → **21 passed**.

---

## 8.6 — Cobertura medida con umbral no decreciente

`.coveragerc` mide el **producto** (`pengu_parser`, `pengu_lsp` y el tooling de
raíz) y excluye `tests/`, `extern/`, `tools/`, `scripts/` y los generadores, para
que el número hable del código que se publica y no del suite. El paso de CI corre
**el suite completo bajo `--cov`** (una sola pasada, no dos) y `pytest-cov`
aplica `fail_under` del fichero.

**Medición (comando al final):**
```
TOTAL                          19235   3808   80.20%
Required test coverage of 50.0% reached. Total coverage: 80.20%
```
**Umbral fijado en 80** (0.2 puntos por debajo de lo medido, para que una
colección que difiera por un pelo no convierta el ratchet en una moneda al aire) y
`RECORDED_FLOOR = 80.0` en `tests/test_ci_workflows.py`, con la comprobación
`floor >= RECORDED_FLOOR`: subir cobertura es un cambio deliberado de dos líneas
(el `.coveragerc` y la constante) y bajarla no puede pasar por accidente.

Cobertura por archivo (los 4 grandes, `--cov-report=term-missing`):
`pengu_parser/pengu_checker.py` 85.82 %, `pengu_parser/pengu_codegen.py` 78.65 %,
`pengu_parser/pengu_infer.py` 77.90 %, `pengu_lsp/server.py` 80.90 %,
`pengu_project.py` 78.06 %.

También comprobado que el mecanismo *muerde*: con `fail_under = 99` sobre un
suite al 85 % el run acaba en `ERROR: Coverage failure` (sonda ejecutada).

---

## 8.7 — Property-based testing (M13)

`tests/test_properties.py` implementa las **7 propiedades de AUDIT §11.5**:

| # | Propiedad | Generador | Oráculo |
|---|-----------|-----------|---------|
| 1 | Round-trip de literales | AST de expresiones recursivo (literales con escapes, unarios, 16 binarios; todo nodo compuesto parentizado) | igualdad estructural del AST tras `render → parse_expr → decode` |
| 2 | **Idempotencia del fmt** | programas válidos compuestos, renderizados con indentación 1/2/3/5 espacios o tab (nunca la canónica) | `fmt(fmt(x)) == fmt(x)` sobre la salida completa + `fmt(x) != x` por ejemplo (anti-vacuidad) |
| 3 | **Preservación de semántica del fmt** | el mismo generador + 6 programas con error semántico a mano | diagnósticos canónicos idénticos (código+mensaje, posiciones normalizadas); si el programa es limpio, además `gen_bundle(fmt(x)) == gen_bundle(x)` byte a byte |
| 4 | Round-trip de contenedores | n ∈ [0,1000] × {int, float, string, bool} | el programa compilado sale 0 **solo si** `len == n` |
| 5 | Aritmética de enteros | 1..6 ternas `a op b`, `a,b ∈ [-2³¹, 2³¹-1]`, op ∈ `+ - * / %` (÷0 y `INT32_MIN/-1` excluidos) | stdout del programa Pengu vs un programa C real con `int32_t` (`-O1 -fwrapv`), perfil release |
| 6 | `transmute`/`to` no cambian el valor | valores de cada tipo primitivo | el programa afirma `v to T == v and transmute v to T == v` → exit 0 |
| 7 | Determinismo del compilador | programas válidos | igualdad byte a byte del bundle: 2× en proceso, 2× en subproceso con `PYTHONHASHSEED` distinto, con DCE y con `PENGU_NO_DCE=1`, y 2× en el mismo directorio (ruta de la caché) |

Más un guardia explícito de no-vacuidad (`test_generator_corpus_is_non_trivial`):
60 sorteos deben dar ≥20 round-trips y ≥10 renderizados distintos (medido: 55-58
distintos, 60/60 válidos), así que un generador roto **falla** en vez de hacer la
propiedad vacua.

**Evidencia:** `pytest tests/test_properties.py -q` → **8 passed, 1 xfailed** en 3
corridas idénticas (21.03 / 21.37 / 21.74 s).

**Contraejemplo hallado (F8-N9).** `PenguBuilder.compute_config_hash()` **no**
incluye `PENGU_NO_DCE`, así que dos builds con artefactos distintos comparten
clave de caché: medido, 3254 bytes (DCE on) y 16047 bytes (DCE off) con la misma
clave `8c5f7a759af9810d`; el rebuild en el mismo directorio devuelve
`is_cached=True` con el bundle obsoleto. Queda pinado con `xfail(strict=True)`
(`test_dce_flag_is_part_of_the_build_cache_key`).

---

## 8.8 — Contrato de CLI: **27** subcomandos, no 25

**Premisa refutada.** El roadmap decía 25; la lista real medida por introspección
de `create_cli_parser()` (`_SubParsersAction.choices`) es de **27** (incluye
`new` y `doc` respecto de las cuentas viejas). La tabla de tests se ata a esa
introspección, así que un subcomando nuevo rompe el suite hasta tener fila.

**Cobertura:** 27 filas de éxito con **efecto estructurado** (ficheros, JSON
parseado, valor exacto de `eval`, CSV, C generado), 10 de posicional ausente
(rc 2), 26 de flag desconocido (rc 2; `run` es la excepción documentada porque
reenvía), 15 de entrada inexistente y 10 de valor inválido.

**Evidencia:** `pytest tests/test_cli_contract.py -q` → **122 passed, 5 xfailed**
(`strict=True`). Aislamiento: fixture autouse que apunta
`HOME`/`XDG_CACHE_HOME`/`PENGU_CACHE_DIR` a `tmp_path`.

---

## 8.9 — Cada código alcanzable

`tests/test_error_reachability.py` contra `docs/error_catalog.json`: **73 códigos**
(62 errores + 9 warnings + 2 de proyecto) → **69 con programa mínimo** y **4
exentos** (`xfail(strict=True)`): `W0000` (fallback de infraestructura, sin
emisor), `W0003` (`reserved` en el catálogo) y `E0061`/`E0062` (capa de
proyecto/lockfile, ya cubiertos por `test_lockfile.py`/`test_phase6_bugfixes.py`).
Los códigos de error se afirman sobre el campo estructurado
`PenguError.code`, nunca sobre prosa. Un test falla si el catálogo gana un código
sin programa ni exención.

**Evidencia:** `pytest tests/test_compliance_corpus.py tests/test_error_reachability.py -q`
→ **133 passed, 4 xfailed**; y en solitario **73 passed, 4 xfailed**.

---

## 8.10 — Estrés a 10 000 líneas

`tests/test_scale.py` **reutiliza** `tests/test_lsp_stability.py::_generate_10k`
(no lo duplica, como pedía el briefing) y mide el CLI:

```
[scale] pengu check 10003 lines -> rc=0 in 6.51s
[scale] pengu build 10003 lines -> rc=0 in 7.15s
```

Con techo explícito (180 s / 600 s) y el tiempo impreso, así que una regresión
aparece como número y no como timeout.

---

## 8.11 — MSVC: **afirmación retirada** (opción B)

**Medición.** `windows-latest` corre MinGW (`ci.yml` fija `CC_BIN="gcc"`), no hay
`cl.exe` en ningún job y `pengu_parser/pengu_runtime.c` incluye
PCRE2/libxml2/zlib/mbedTLS/libcurl/libmicrohttpd, cuyo build MSVC no existe
(`docs/CROSS_COMPILATION.md` §9 ya lo documentaba). La casilla de
`RELEASE_CHECKLIST.md:13` afirmaba "gcc/clang, **MSVC**, MinGW" sin ningún job
que lo respaldara.

**Qué se hizo.** Se retiró la afirmación y se sustituyó por el estado real: el
*dialecto* MSVC sí se comprueba con un compilador real (`clang -fdeclspec`, y
`cl.exe /Zs` si existe), pero **ningún job enlaza un binario MSVC**. Un job de
MSVC no se añade "para que esté verde": exigiría el stack completo cross-built.

---

## 8.12 — `cross-compile.yml` — ⏸️ workflow entregado, `.exe` real no verificable aquí

**Medición que acota el item.** En esta máquina **no hay**
`x86_64-w64-mingw32-gcc` (sí `wine`), y un programa PenguScript mínimo **no enlaza
sin la runtime**: el único símbolo que falta es `pengu_abi_version`
(`pengu_parser/pengu_runtime.c:69`), y ese archivo incluye el stack de terceros.
Es exactamente el límite que `docs/CROSS_COMPILATION.md` §7.3/§9 ya documentaba.

El workflow hace lo que **sí** es verificable y lo declara por escrito:

1. instala `gcc-mingw-w64-x86-64` + `wine64` y corre `tests/test_cross_compile.py`
   (el test opt-in de MinGW deja de saltarse, que ya es una mejora medible);
2. genera el bundle con `--target x86_64-w64-mingw32`;
3. lo compila a un **objeto PE real** con `-c` (no necesita runtime);
4. enlaza un `.exe` con un shim MinGW de 3 líneas que aporta `pengu_abi_version`
   — el resto de la runtime es `static inline` en la cabecera;
5. valida la cabecera con `file` (`PE32+`) y **ejecuta** el `.exe` con `wine`,
   exigiendo rc = 6 (la suma de `[1,2,3]`).

**No se afirma** que un programa que use el archivo de runtime (strings,
contenedores, FFI) cross-compile: eso necesita el stack cross-built y queda
diferido a 1.1. **Criterio de reapertura:** un runner con `mingw-w64` + la runtime
cross-built; entonces el shim desaparece y el paso 4 usa `PENGU_RUNTIME_CROSS`.

**Honestidad sobre la verificación:** este workflow **no se ha podido ejecutar
aquí** (falta el compilador). El YAML está validado e invariantes-testado
(`test_cross_compile_workflow_produces_and_runs_a_pe`), pero su verde en CI es una
predicción, no una medición — y así queda escrito.

---

## 8.13 — Workflows de los corpus

`compliance.yml` con dos jobs (`compliance`, `migration`) que usan
`./.github/actions/setup-pengu` (runtime cacheado) y corren
`run_all.py` + el gate de pytest. En jobs propios y no en `ci.yml` para que un
fallo nombre el corpus.

---

## 8.14 — `codeql.yml`

Analiza **`python`** (compilador, LSP, tooling) y **`c-cpp`** (la runtime), ambos
con `build-mode: none` — los bundles generados son salida de test y no se
analizan: el SAST cubre lo que escribió una persona. Suite
`security-extended` (la que añade las consultas de memoria/taint que la default
omite). `security-events: write` solo en el job de análisis.

---

## 8.15 — Actions fijadas a SHA

Las 6 actions (y la composite) pasaron de tag móvil a SHA de commit de 40 hex con
comentario de versión:

```
actions/checkout@11d5960a326750d5838078e36cf38b85af677262            # v4.4.0
actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065        # v5.6.0
actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020          # v4.4.0
actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02     # v4.6.2
actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830               # v4.3.0
actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093   # v4.3.0
github/codeql-action/*@1190a975f95ce23525efb6a3fc21ea29567c1b52      # v3.38.2
```

Los SHAs se resolvieron con `git ls-remote` (mapeando el tag `vX.*` exacto, no a
ojo) y hay un test parametrizado sobre **todos** los workflows que falla si
alguno vuelve a un tag móvil. `grep -rn 'uses:.*@v[0-9]' .github/` → **0**.

---

## 8.16 — `nightly.yml` con presupuesto realista + hallazgo F8-N5

`nightly.yml` divide el fuzz en **5 harnesses × 4 shards**, con el presupuesto
acotado a 6 h por harness (clamp en shell a 21600 s, seeds distintas por shard,
presupuesto dividido con `total / SHARDS`) y `timeout-minutes` por debajo del
techo de la plataforma.

**Hallazgo F8-N5.** `fuzz.yml` declaraba `timeout-minutes: 780` (**13 h**) y un
presupuesto por defecto de 12 h, con un comentario que afirmaba cubrir 12 h "con
margen" — imposible: GitHub mata un job a las 6 h. No era una política, era un
número en un fichero. Corregido (350 min y 21600 s con clamp) y cubierto por un
invariante **global**:

- `test_no_job_timeout_exceeds_the_platform_ceiling`, parametrizado sobre **todos**
  los workflows;
- `ALL_WORKFLOWS` pasó de lista escrita a mano a `sorted(glob("*.yml"))` — la
  lista a mano es justo lo que dejó que `fuzz.yml` escapara del invariante.

La parte documental (`docs/FUZZING.md:69`, `RELEASE_CHECKLIST.md:27`) sigue
asignada al item 9.5.

---

## 8.17 — Tests flaky: los 3, con medición antes y después

Regla del item: dos corridas consecutivas del suite deben dar la **misma** tupla.

### ① `test_string_composition_suite.py::test_string_composition_no_memory_leaks[leak_binary_interp]`

**Medición antes** (12 corridas del archivo): `xfail` 1 vez, **`xpass` 3 veces** y
con `strict=True` un **fallo intermitente** (`1 failed, 6 passed`). **Causa raíz:**
no es el compilador, es el detector. `tests/leakcheck.c` marca un bloque como
alcanzable si **cualquier** palabra de la pila o de un segmento escribible todavía
parece un puntero a él, así que un temporal muerto de 2 bytes a veces "está vivo".

**Decisión: fix (no xfail).** El veredicto no puede ser esa moneda al aire. Para
los programas con fuga conocida, rc 42 (fuga) y rc 0 son **ambos** el resultado
documentado, y la aserción pasa a ser esa disyunción explícita; cualquier **otra**
fuga o modo de fallo sigue fallando, y la fuga sigue clavada por el pin
determinista `test_call_argument_string_temporary_is_released` (`strict=True`).

**Medición después:** 12/12 corridas → `29 passed, 1 xfailed`, **0 xpassed**.

### ② `test_deps_commands.py::test_add_upgrade_remove_end_to_end` — bug real del producto (F8-N1)

**Medición antes:** 3 de 6 corridas **fallan** (~50 %).
**Causa raíz medida:** `_dep_cache_key(source, branch)` sólo tenía el *string* del
origen. Para una ruta local el string no es una identidad: la caché
`~/.cache/pengu/deps/<hash>` devolvía el snapshot viejo, y `pengu upgrade` moría
con `git fetch failed … would overwrite existing tag`. El propio test lo
demostraba: el repo git se recrea en cada corrida con un commit nuevo y el mismo
tag `v1.0.0`, y el número de directorio temporal de pytest se reutiliza.

**Fix real:** la clave incorpora el `HEAD` resuelto de una fuente local
(`_local_source_revision`), así que la caché sigue siendo caché (mismo HEAD →
hit) y deja de servir un estado viejo.

**Medición después:** 6/6 corridas pasan. **C2 verificado:** revirtiendo
`_local_source_revision` el test nuevo
(`test_changed_local_source_is_not_served_from_a_stale_cache`) **falla** — se
ejecutó la reversión y se comprobó.

### ③ `test_run_cache.py::test_script_arguments_are_forwarded`

**Medición antes:** 1 de 5 corridas del archivo falla (~20 %) y en aislamiento
10/10 pasan — es decir, sólo se veía en contexto.
**Causa raíz medida, capturando la salida real:** la aserción era
`assert "2" in res.stdout`, una **subcadena de toda la transcripción del CLI**:
pasaba cuando cualquier línea de progreso contenía un "2" y fallaba cuando no.
Además codificaba mal el contrato: `std.rites.get_args` documenta el índice 0 como
el nombre del programa, así que **2 argumentos reenviados dan `args.len == 3`**
(la corrida fallida imprimía `3`, y el test lo llamaba error).

**Fix:** aserción sobre líneas exactas de salida (`ARGC:3`, `ARG1:one`,
`ARG2:two`) más la comprobación de que el separador `--` no se reenvía.
**C2 verificado por mutación:** descartando los args reenviados en `main()`, el
test nuevo **falla** (`rc=1`) mientras que el `"2" in stdout` viejo **seguía
pasando** — es la demostración de que el gate viejo enmascaraba el fallo.
**Medición después:** además del archivo en aislamiento, el test pasa en las dos
corridas completas del suite (C y D), que son la medición que impone el item.

---

## 8.18 — Fixtures reutilizables de compilación C

`tests/conftest.py` gana `CToolchain` + `c_toolchain` (session), `compile_c` y
`run_c` (function), con `std`/`pedantic`/`syntax_only`/`cc`/`extra`. Es el
conocimiento que cada suite re-derivaba a mano (compilador, `-std`, `-I`/`-L`,
tail de librerías) en un solo sitio. `tests/test_c99_portability.py` y
`tests/test_attributes_msvc_native.py` las consumen: es lo que permitió que el
gate de MSVC invocara `clang` con `-fdeclspec` sin construir argv a mano.

---

## Hallazgos de la fase (numerados, con su medición)

| ID | Hallazgo | Estado |
|----|----------|--------|
| **F8-N1** | La caché global de dependencias se indexaba por *string* de origen: una fuente local cambiada devolvía el snapshot viejo y `pengu upgrade` moría con "would overwrite existing tag" | ✅ arreglado (8.17②) |
| **F8-N3** | El dialecto MSVC emitía `int32_t head __declspec(align(8));` (posición GNU), rechazado por MSVC | ✅ arreglado (8.1) |
| **F8-N4** | `--strict-c99` emite **C inválido** para 18 de los 56 programas de std (13+ errores duros: `'k' undeclared` de una comprehension mal hoisteada), con o sin `-pedantic-errors` | ⏸️ xfail(strict) + item 1.1 |
| **F8-N4a** | `--strict-c99` **miscompila**: `test_loom_extended` compila limpio y aborta en runtime (`Index out of bounds: 1 (length 1)` en `std/loom.pengu:347`), mientras el build por defecto sale rc 0 | ⏸️ xfail(strict) + item 1.1 |
| **F8-N5** | `fuzz.yml` declaraba `timeout-minutes: 780` (13 h) y 12 h de presupuesto: GitHub mata el job a las 6 h | ✅ arreglado (8.16) |
| **F8-N6** | Regla C4: un parámetro `array of int` **sin tamaño** (el ejemplo de `LANGUAGE.md` §5.0) hace que el CLI imprima un **Traceback de Python** en vez de un diagnóstico (el error se lanza en codegen) | ❌ pin `xfail(strict)` en `test_phase8_findings.py` |
| **F8-N7** | Regla C4 + contrato: `pengu time <inexistente>` y `pengu fmt <inexistente>` lanzan **Traceback**; `build`, `test` y `doc` con `--entry` inexistente devuelven **rc 0** y construyen la entrada por defecto en silencio | ❌ pin `xfail(strict)` en `test_cli_contract.py` |
| **F8-N8** | El "BUG A" reportado por el autor de 8.4 (comparar `error` dentro de un `or:` → check limpio y build roto) **no se reproduce**: medido en dos formas, ambas construyen; la variante que falla lo hace en `check` con el `TypeMismatchError` correcto | ❌ refutado, gate positivo |
| **F8-N2** | La stdlib fuga en LeakSanitizer (traza en `std/invoke.pengu`): el job de sanitizers **no puede** estar verde deseleccionando un test | ⏸️ item 8.19 (1.1) |
| **F8-N10** | **Bug real de memoria**: pasar un array a una función C variádica deja una referencia colgante a un temporal de pila. ASan: `stack-use-after-scope ... in sum_args` (`tests/compliance/020-declare-extern-c.pengu:17`) y `... in sum` (`variadic_arr_rt.pengu:5`). Sin instrumentación el programa devuelve el valor correcto, así que el suite llevaba años verde | ❌ pin `xfail(strict)` en `test_phase8_findings.py` + item 8.24 (1.1) |

---

## Mediciones (comandos reproducibles)

```bash
# 8.3
python -m ruff check --select F821,E9 --exclude extern,build,vscode-extension .

# 8.2 — el paso 3 del job, sin el deselect (pre-fix):
PENGU_CFLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' \
PENGU_LDFLAGS='-fsanitize=address,undefined' \
ASAN_OPTIONS='detect_leaks=1:abort_on_error=1:halt_on_error=1' \
python -m pytest tests/test_std_backward_compat.py tests/test_std_data_backward_compat.py \
                 tests/test_std_util_backward_compat.py -q
# → 6 failed in 96.92s   (no 1)

# 8.1 — clasificación de los 56 programas de std con --strict-c99 (paralelizable):
for p in tests/std_programs/test_*.pengu; do
  python -m pengu_project build --entry "$p" --output "/tmp/$(basename $p .pengu).c" --strict-c99
  gcc -std=c99 -pedantic-errors -fsyntax-only -fmax-errors=10000 \
      -Wno-error=implicit-function-declaration -Wno-error=implicit-int \
      -Wno-error=int-conversion "/tmp/$(basename $p .pengu).c" -I. -Ibuild -Ibuild/include
done
# → 23 limpias (y ejecutan rc 0), 14 solo B5, 18 con 13 errores duros, 1 miscompilada

# 8.15
grep -rn 'uses:.*@v[0-9]' .github/          # → 0 líneas

# 8.17 — antes/después (los tres)
for i in $(seq 1 12); do pytest tests/test_string_composition_suite.py -q; done
for i in $(seq 1 6);  do pytest tests/test_deps_commands.py::test_add_upgrade_remove_end_to_end -q; done
for i in $(seq 1 5);  do pytest tests/test_run_cache.py -q; done
```

---

## Pendiente / diferido con medición

| Item | Por qué se difiere | Medición que lo justifica | Criterio de reapertura |
|------|--------------------|---------------------------|------------------------|
| **8.2 (job verde)** | Las fugas están en la stdlib, no en un test | 6/6 fallos en los 3 archivos con fugas y **164 marcas de fallo al 92 %** del suite completo bajo ASan | Cerrar 8.19 (fugas de stdlib); entonces el `--deselect` se vacía y el test de propagación obliga a tocar el workflow |
| **8.12 (`.exe` real)** | No hay `x86_64-w64-mingw32-gcc` aquí y la runtime no es cross-buildable (`pengu_runtime.c` incluye PCRE2/libxml2/zlib/mbedTLS/curl/microhttpd) | `which x86_64-w64-mingw32-gcc` → no existe; el bundle mínimo falla al enlazar solo por `pengu_abi_version` | Un runner con MinGW + runtime cross-built; el shim del workflow desaparece |
| **8.1 (los 32 programas bloqueados)** | B5 (roadmap 3.3) y F8-N4 están diferidos a 1.1 | 14 con statement-expressions, 18 con C inválido, 1 miscompilado | `xfail(strict=True)`: al arreglarlos pasan a `xpass` y el archivo falla |
| **8.5 (versiones <0.10.0)** | La sintaxis no está documentada en ningún documento normativo | `CHANGELOG.md` lista 35 versiones; `MIGRATION.md` §2 empieza en 0.10.0 | Aparece documentación normativa de la sintaxis pre-0.10 |
| **8.19 (nuevo, 1.1)** | Fugas de memoria de la stdlib bajo LeakSanitizer: es un cambio de propiedad de memoria en `std/*.pengu`/`pengu_codegen.py`, no un ajuste de CI | Trazas en `std/invoke.pengu:105/292` (`pengu_list_new`, `pengu_map_new_owned`); 164 fallos en el suite bajo ASan | Cualquier corrida de sanitizers sin `--deselect` |

## Mediciones finales de reproducibilidad

Corrida de cobertura (run B) y corrida limpia (run C) sobre el estado final del
árbol; la tupla es `(failed, passed, skipped, xfailed, xpassed)`:

| Corrida | Comando | Tupla | Tiempo |
|---|---|---|---|
| B (con cobertura, estado previo al `fmt`) | `pytest tests -q --cov --cov-config=.coveragerc --cov-report=term-missing --cov-report=xml:coverage.xml` | **1 failed**, 3274 passed, 25 skipped, 46 xfailed, **0 xpassed** | 34:51 |
| C (limpia) | `pytest tests -q -p no:cacheprovider --timeout=1200` | **0 failed**, 3275 passed, 25 skipped, 46 xfailed, **0 xpassed** | 34:29 |
| D (limpia, repetición) | idéntico a C | **0 failed**, 3275 passed, 25 skipped, 46 xfailed, **0 xpassed** | 34:34 |

**C y D son la misma tupla** `(0, 3275, 25, 46, 0)`, corridas consecutivas sobre
el mismo árbol congelado: el criterio de reproducibilidad del item 8.17 queda
medido, no argumentado.

El único fallo de la corrida B lo produjo el propio gate de formato del repo
(`test_fmt_config_precedence.py::test_repository_sources_are_clean_under_pengu_fmt`
→ 10 programas del corpus de migración sin formatear): el gate hizo su trabajo
sobre los ficheros nuevos de la fase. Se corrigió con `pengu fmt tests/migration`
y las 10 corridas de migración siguen pasando; de ahí que C tenga 3275 passed
(el +1 es exactamente ese test) y 0 failed.

**Criterio "0 xpassed":** cumplido en las tres corridas. El único `xpass` que
existía al empezar la fase era el del detector de fugas (item 8.17①), y su causa
está explicada arriba.

**Nota de rigor sobre las corridas:** entre B y C sólo cambiaron los 10 programas
`.pengu` del corpus de migración (formateados) — ningún fichero de test ni de
código. Entre C y D no cambia nada del árbol: D es la repetición exigida por el
item 8.17 sobre el estado final congelado.
