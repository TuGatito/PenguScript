# AUDIT 1.0 — FASE 7: Completar Style Guide y Docs

> **Estado:** en curso
> **Base:** `ROADMAP_2.0.md` § Fase 7 (14 items)
> **Regla de la fase:** medir la premisa antes de implementar; un commit por item;
> todo fix trae un test que **falla al revertir**; actualizar este audit y el roadmap.

---

## Estado de partida (medido antes de tocar nada)

Todas las mediciones se tomaron sobre el commit `355d946` (cierre de Fase 6),
con `VERSION` = `0.16.0`.

| Métrica | Valor medido | Comando |
|---|---|---|
| Bloques ```` ```pengu ```` en `LANGUAGE.md` | **101** | `python - <<'E'` contando fences (ver §Medición) |
| Bloques ```` ```pengu ```` en `LANGUAGE_Spanish.md` | **95** | ídem |
| Bloques ```` ```pengu ```` en las guías EN/ES | **72 / 72** | ídem |
| Bloques ```` ```pengu ```` en `CHEATSHEET.md` | **81** | ídem |
| Clases definidas en `pengu_errors.py` | **38** | `grep -c '^class ' pengu_parser/pengu_errors.py` |
| Clases de error con `code` propio | **36** | extracción AST de `kwargs.setdefault("code", …)` |
| Códigos `Exxxx` distintos emitidos en el proyecto | **59** (`E0000`–`E0058`) | AST: `code="EXXXX"` en todos los `.py` |
| Códigos `Exxxx` con clase dedicada | **35** | AST |
| Códigos `Exxxx` emitidos sólo en crudo (`SemanticError`, `code=…`) | **24** | AST |
| Pares `(código, mensaje)` distintos | **374** | extracción AST |
| Pares `(código, mensaje)` repetidos en ≥2 sitios | **29** | AST |
| Mensajes que aparecen bajo **más de un** código | **0** | AST — invariante ya satisfecha |
| Clases **fantasma** documentadas en §22.2 y ausentes del código | **5** | ver §7.1 |
| Códigos `Wxxxx` emitidos | **7** (`W0001`,`W0002`,`W0004`,`W0005`,`W0006`,`W0007`,`W0013`) + `W0000` de fallback | AST + `grep` |
| `tests/test_version.py` | **NO EXISTE** | `ls tests/test_version.py` → *No such file* |
| Deriva de versión | `LANGUAGE.md:2349,3548`, `LANGUAGE_Spanish.md:2295,3317`, `pengu_parser.py:92`, `pengu_lsp/__init__.py:1`, guías EN/ES §cabecera | `grep -rnP '0\.1[0-5]\.'` |
| `docs/ABI.md` | **EXISTE** (6 852 bytes) | `test -f docs/ABI.md` |
| `docs/README.md` | **EXISTE** (3 384 bytes) | ídem |
| `pengu_doc.py` | **EXISTE** (16 661 bytes) | `ls pengu_doc.py` |
| `tools/` | sólo `grammar_conflicts.py` | `ls tools/` |
| `pyproject.toml` | **NO EXISTE** | `ls pyproject.toml` |

### Script de medición de fences

```bash
python3 - <<'EOF'
import re, collections
for f in ['LANGUAGE.md','LANGUAGE_Spanish.md','CHEATSHEET.md','README.md',
          'PenguScriptGuideEnglish.md','PenguScriptGuideSpanish.md']:
    c = collections.Counter(re.findall(r'^```(\S*)\s*$', open(f, encoding='utf-8').read(), re.M))
    print(f, dict(c))
EOF
```

---

## Premisas del roadmap verificadas antes de empezar

| # | Premisa del roadmap | Veredicto de la medición |
|---|---|---|
| 7.1 | "las 5 clases fantasma desaparecen o se implementan" | ✅ **confirmada**: `DuplicateConstantError`, `AmbiguousStructInitError`, `StaticArrayError`, `ErrorLiteralContextError`, `DanglingSliceError` aparecen en §22.2 y **no existen** en el código |
| 7.1 | §22.2/§22.3 se pueden generar desde `pengu_errors.py` | ✅ **confirmada**: 36 clases con `code` + 24 códigos crudos = 59 códigos, todo extraíble por AST |
| 7.2 | "`E0035` cubre 4 condiciones" | ✅ **confirmada** (con matiz): cubre **4 condiciones no relacionadas** (colisión con nombre reservado de C, ubicación de `static var`, nombre de `test` inválido, colisión de campos en la emisión C). El audit §2.3 lista una 5ª fila (`main`) que **es falsa**: `main` ya usa `E0040` (`pengu_checker.py:2748`) |
| 7.2 | "Ningún `(código, mensaje)` duplicado" | ⚠️ **matizada**: 374 pares distintos, **29 repetidos en ≥2 sitios** — pero son el *mismo* diagnóstico emitido en dos rutas (checker + infer) por defensa en profundidad, no el bug de códigos compartidos. **0 mensajes** aparecen bajo códigos distintos. El bug real es el de 7.2 (`E0035`), no la duplicación de sitios |
| 7.3 | "una sola forma canónica de rango; la deprecada marcada" | pendiente de medición |
| 7.4 | "105 bloques de `LANGUAGE.md`" | ⚠️ **matizada**: hay **101** bloques ```` ```pengu ```` (el "105" del audit §12.3 contaba otra cosa). El audit §12.3 afirma además que **72 de 105 no pasan `pengu check`** |
| 7.5 | "`tests/test_version.py` extendido" | ❌ **parcialmente refutada**: el archivo **no existe**. El audit §13.4 afirma que existe ("Existe `tests/test_version.py` que verifica la coherencia de `VERSION`…"); es falso en `355d946`. Hay que **crearlo**, no extenderlo |
| 7.5 | "13 archivos con deriva" | ✅ **confirmada en orden de magnitud**: la lista de §13.4 (10 `.md` + `pengu_parser.py:92` + `pengu_lsp/__init__.py:1`) sigue vigente; el conteo exacto depende del patrón |
| 7.6 | "reglas nuevas de §10.5 aplicadas" | pendiente de medición |
| 7.7 | "las 5 reglas incumplibles de AUDIT §10.4" | ✅ **confirmada**: §10.4 lista exactamente 5 reglas |
| 7.8 | "cubrir 'ningún gate por texto' (AUDIT §15.2)" | ✅ **confirmada**: §15.2 documenta 7 gates verdes sobre código roto |
| 7.10 | "`docs/ABI.md` ya existe (Fase 3, item 3.11) — verificar y enlazar, no recrear" | ✅ **confirmada**: existe y `docs/README.md` ya lo lista |
| 7.12 | "`MIGRATION.md` alimentado por `pengu migrate` (Fase 4, diferido a 1.1)" | pendiente de medición |
| 7.13 | "los 1463 nombres públicos" | pendiente de medición |
| 7.14 | "CI verifica que el número de bloques `pengu` coincide entre los pares" | ⚠️ **refutada tal como está**: las guías EN/ES **sí** coinciden (72 / 72), pero `LANGUAGE.md` (101) y `LANGUAGE_Spanish.md` (95) **NO** — divergen en 6 bloques |

---

## Item por item

### 7.1 — Generar §22.2 y §22.3 desde el código

**Premisa del roadmap:** la tabla se genera; un test falla si el doc y el código divergen;
las 5 clases fantasma desaparecen o se implementan.

**Verificación previa:**

```bash
$ grep -c '^class ' pengu_parser/pengu_errors.py          # 38
$ grep -ohP 'E\d{4}' pengu_parser/pengu_errors.py | sort -u | wc -l   # 35
# 5 clases documentadas en §22.2 que NO existen en el código:
$ for c in DuplicateConstantError AmbiguousStructInitError StaticArrayError \
           ErrorLiteralContextError DanglingSliceError; do
    grep -rn "$c" pengu_parser/*.py *.py pengu_lsp/*.py; done
# (sin resultados)
```

**Decisión:** la opción honesta y barata que el propio roadmap propone en §Riesgos —
**documentar la realidad** en vez de inventar 5 clases. Las 5 filas fantasma de §22.2 pasan a
nombrar la clase que **realmente** emite ese código (`SemanticError` con `code="E00xx"`).
La generación se hace con extracción **AST** (no regex sobre texto) para que sea inmune a
reformateos y a mensajes multilínea.

**Resultado:** ✅ cerrado

**Evidencia:**

```bash
$ .venv/bin/python tools/gen_error_catalog.py --check
error catalog: 59 codes, 327 conditions, 9 warnings, in sync      # rc=0

$ .venv/bin/python -m pytest tests/test_error_catalog_sync.py -q
18 passed

# las 5 clases fantasma ya no aparecen en ninguno de los dos documentos
$ for c in DuplicateConstantError AmbiguousStructInitError StaticArrayError \
           ErrorLiteralContextError DanglingSliceError; do
    printf '%s: ' "$c"; grep -c "$c" LANGUAGE.md LANGUAGE_Spanish.md | tr '\n' ' '; echo; done
DuplicateConstantError: LANGUAGE.md:0 LANGUAGE_Spanish.md:0
… (las 5, 0 y 0)
```

**Falsificación (el test falla al revertir, comprobado):**

```bash
# 1) desincronizar un recuento en la tabla
$ sed -i 's/| 137 |/| 136 |/' LANGUAGE.md && pytest tests/test_error_catalog_sync.py -q
2 failed, 16 passed      # test_document_tables_match_the_catalog, test_check_mode_is_clean

# 2) emitir un código nuevo (E0058 -> E0099 en pengu_infer.py) sin regenerar
$ pytest tests/test_error_catalog_sync.py -q
6 failed, 12 passed
```

**Qué se hizo:**

1. `tools/gen_error_catalog.py` (nuevo): construye el catálogo **por AST** desde
   `pengu_parser/*.py`, `pengu_project.py`, `pengu_lsp/*.py`.
   - Extrae las clases de error y su `code=` por defecto, la explicación de la
     clase (docstring), y sus `help:`/`note:`.
   - Extrae las dos formas de emisión cruda del proyecto
     (`raise XError(msg, code=…)` y `self._make_error(SemanticError, msg, code=…)`)
     y anota la clase **real** que emite cada código.
   - Normaliza las interpolaciones a `{}`, lo que hace el catálogo estable frente
     a renombrados de locales y **colapsó diagnósticos que sólo diferían por el
     nombre del local** (p. ej. `Cannot cast '{src}' to '{tgt}'` emitido dos veces
     con `target_type`/`cast_target`). De 374 pares `(código, mensaje)` literales
     se pasa a **327 condiciones** canónicas.
   - `--write` regenera `docs/error_catalog.json` y la región §22.2/§22.3 de
     `LANGUAGE.md` **y** `LANGUAGE_Spanish.md` entre marcadores; `--check` es el
     gate.
2. `WARNING_CATALOG` en `pengu_parser/pengu_errors.py`: registro canónico de los
   códigos de advertencia. Hasta ahora los nombres (`UnsafeTransmuteWarning`, …)
   y la "práctica recomendada" existían **sólo en el documento**, que es el mismo
   tipo de dato fantasma que las 5 clases de error. Se añaden `W0000`
   (fallback de infraestructura) y `W0003` (reservado, nunca emitido).
3. §22.2/§22.3 de `LANGUAGE.md` y `LANGUAGE_Spanish.md` regeneradas. Las 5 clases
   fantasma desaparecen: los códigos sin clase dedicada (`E0010`–`E0013`,
   `E0015`–`E0020`, `E0025`, `E0035`–`E0040`, `E0045`, `E0046`, `E0049`,
   `E0051`, `E0053`–`E0055`, `E0058`) ahora nombran la clase que **realmente** los
   emite (`SemanticError`).
4. `docs/error_catalog.json` (nuevo): la forma legible por máquina del catálogo.
5. **Deriva colateral encontrada y corregida en `CHEATSHEET.md`** (misma clase de
   defecto: el doc afirma un código que el compilador no emite):

   | Afirmación previa de `CHEATSHEET.md` | Realidad medida |
   |---|---|
   | §10.4: un `seal` y su tipo subyacente no son intercambiables (`E0035`) | Es **`E0005`** (medido: `var raw as int is user_id` → `E0005`) |
   | §10.4: `set user_id is post_id` es "Compile error E0035" | **No se detecta** — ver hallazgo F7-N1 |
   | §20.4: "`E0035` seal mismatch" | **`E0035`** = el nombre colisiona con una palabra reservada o un identificador estándar de C |

**Test:** `tests/test_error_catalog_sync.py` — 18 casos: JSON vs código, tablas de
ambos documentos vs JSON, ausencia de las 5 clases fantasma, todo código emitido
está catalogado y todo código catalogado se emite, toda advertencia emitida está
registrada, y `--check` en verde.
**Commit:** `5fc0373`

---

### 7.2 — Eliminar la clase de bug de códigos compartidos

**Premisa del roadmap:** cada `(código, mensaje)` es único; `E0035` deja de cubrir 4 condiciones;
`test_error_codes_uniqueness.py` analiza también las emisiones crudas.

**Verificación previa:**

```bash
$ .venv/bin/python - <<'EOF'   # extracción AST de emisiones crudas (misma que la 7.1)
EOF
distinct messages: 374
messages under MORE THAN ONE code: 0        # la invariante fuerte YA se cumple
DUPLICATE (code,msg) sites: 29              # mismo diagnóstico en 2 rutas, benigno
```

`E0035`, medido, cubre exactamente 4 condiciones no relacionadas:

| Condición real | Nº de plantillas | Naturaleza |
|---|---|---|
| Nombre de tipo/función/constante choca con palabra reservada de C | 3 plantillas, 10 sitios | Colisión con C |
| `'static var' is only allowed directly inside a function body (weave).` | 1 | Ubicación de declaración |
| `Test name must be a non-empty string or identifier` | 1 | Nombre de test inválido |
| `Field '…' collides with field '…' in C code emission ('…')` | 1 | Colisión de campos entre sí |

**Resultado:** ✅ cerrado

**Evidencia:**

```bash
$ .venv/bin/python -c "..."   # condiciones por código, vía el catálogo generado de 7.1
E0035: 4   # antes 7
E0063: 1   # 'static var' fuera de un cuerpo de función
E0064: 1   # nombre de test vacío
E0065: 1   # colisión de campos entre sí en la emisión C

# comportamiento real, no sólo texto fuente:
$ static var dentro de un 'if' dentro de un weave
  -> [E0063] 'static var' is only allowed directly inside a function body (weave).
$ test "":
  -> [E0064] Test name must be a non-empty string or identifier
$ rune BadRune: FILE/_FILE
  -> [E0065] Field '_FILE' collides with field 'FILE' in C code emission ('_FILE')
$ rune int:            -> [E0035] Type name 'int' is a reserved C keyword or standard identifier
$ const FILE as int is 5 -> [E0035] Constant name 'FILE' is a reserved C keyword ...
$ weave printf ...     -> [E0035] Function name 'printf' is a reserved standard C function ...
```

**Falsificación (el gate falla al revertir, comprobado):** devolviendo el sitio de
`'static var'` a `SemanticError`/`E0035`:

```bash
$ pytest tests/test_error_codes_uniqueness.py -q
5 failed, 10 passed
# test_every_emitted_code_has_exactly_one_condition_family
# test_ratchet_is_not_padded
# test_e0035_covers_only_the_c_reserved_name_family
# test_displaced_conditions_have_their_own_code[E0063-…]
# test_the_split_is_real_not_cosmetic
```

**Qué se hizo:**

1. Tres clases nuevas en `pengu_parser/pengu_errors.py` con códigos nuevos, cada
   una documentando en su docstring **por qué** estaba compartiendo `E0035` y con
   qué condición:
   - `E0063 StaticVarPlacementError` — `'static var'` fuera de un cuerpo de weave.
   - `E0064 InvalidTestNameError` — `test` sin nombre utilizable.
   - `E0065 CFieldCollisionError` — dos campos *de usuario* colisionan en el
     identificador C (no es una colisión con C, que es lo que `E0035` significa).
2. Los 4 sitios de emisión en `pengu_checker.py` actualizados; `E0035` queda con
   su única familia ("el nombre choca con una palabra reservada o un identificador
   estándar de C"), 4 formas de mensaje en lugar de 7.
3. `tests/test_error_codes_uniqueness.py` extendido: la mitad nueva del archivo
   **camina el AST de todos los emisores** (no `kwargs.setdefault`) y aplica
   cuatro invariantes:
   - `test_every_emitted_code_has_exactly_one_condition_family`: ratchet
     `CONDITION_SHAPES` de 61 códigos; **ensanchar el significado de un código es
     un fallo de build** hasta bumpear la tabla a propósito.
   - `test_ratchet_is_not_padded`: un número obsoleto demasiado alto también falla
     (si no, ocultaría una condición eliminada).
   - `test_no_message_shape_is_emitted_under_two_codes`: `mensaje → código` debe
     ser una función. Medido: **0 violaciones** (la invariante fuerte ya se
     cumplía; el bug real era el inverso, un código con 4 condiciones).
   - `test_e0035_covers_only_the_c_reserved_name_family` y
     `test_the_split_is_real_not_cosmetic` (compila los 3 casos; no se conforma
     con el texto fuente).
4. `tests/test_regression_0_13_7.py::test_item9_c_ident_collision_detection`
   actualizado a `E0065` con el motivo del cambio (`FILE`/`_FILE` es una colisión
   entre campos de usuario, no con C).
5. Catálogo y documentos regenerados (`--write`); `§22.2` ya recoge `E0063`–`E0065`.

**Nota sobre el criterio del roadmap:** *"cada `(código, mensaje)` es único"* se
mide y **ya se cumplía** (0 mensajes bajo dos códigos); los 29 pares
`(código, mensaje)` repetidos son el mismo diagnóstico en dos rutas (checker e
infer) y **no** son el bug de códigos compartidos. El criterio se reinterpreta en
su forma útil, que es la que el audit §2.3 describe en prosa: *un código no puede
cubrir condiciones sin relación*, ahora con ratchet ejecutable.

**Test:** `tests/test_error_codes_uniqueness.py` (15 casos, 8 nuevos) +
`tests/test_error_catalog_sync.py`.
**Commit:** `7c44c13`

---

### 7.5 — Sincronizar versiones (`tests/test_version.py` extendido)

**Premisa del roadmap:** "`tests/test_version.py` extendido escanea los `.md` y docstrings; 0 deriva".

**Verificación previa — la premisa se cae en su primera mitad:**

```bash
$ ls tests/test_version.py
ls: no se puede acceder a 'tests/test_version.py': No such file or directory
```

**El archivo NO existe.** El audit §13.4 afirma *"Existe `tests/test_version.py` que verifica la
coherencia de `VERSION`, `FALLBACK_VERSION` y algunos puntos"* — es **falso** en `355d946`. No hay
nada que extender: hay que crearlo. `pengu_version.py:10-12` también afirma que "a unit test
asserts that the fallback, the file and the places that spell the version out stay in sync": esa
frase llevaba siendo falsa desde que se escribió.

**Segunda mitad de la premisa — "13 archivos con deriva":** medida, es una **sobreestimación**. El
recuento del audit §13.4 mezcla tres cosas distintas:

| Categoría | Archivos | Veredicto |
|---|---|---|
| Afirmación de versión **actual**, realmente desviada | `LANGUAGE.md` (4 sitios), `LANGUAGE_Spanish.md` (4), `PenguScriptGuideEnglish.md:3`, `PenguScriptGuideSpanish.md:3`, `pengu_parser/pengu_parser.py:95`, `docs/PENGU_BUILD.md:1` (`v0.6`), `docs/README_RELEASE.md:27,50`, `pengu_version.py:61,64`, `README.md:404` | **9 archivos** — deriva real |
| Mención **histórica** legítima | `docs/PERFORMANCE.md` (medición de 0.15.0), `docs/DEPRECATIONS.md` (versión que deprecó cada alias), `ROADMAP_1.0.0.md`, `docs/archive/AUDIT_RESPONSE.md`, `README.md:396,910` (qué release completó la stdlib), `CHEATSHEET.md` ("since 0.10.0") | **no es deriva** |
| **Refutado** | `pengu_lsp/__init__.py:1` | El audit decía *"PenguScript v0.6 Language Server Protocol Package"*; hoy el archivo **no contiene ninguna versión**: reexporta `from pengu_version import __version__` |

Así que "13 archivos" cuenta las menciones históricas como si fueran deriva. La cifra defendible es
**9 archivos con afirmaciones desviadas**.

**Resultado:** ✅ cerrado

**Evidencia:**

```bash
$ .venv/bin/python -m pytest tests/test_version.py -q
28 passed, 6 skipped

# las 9 afirmaciones desviadas corregidas a 0.16.0 (o a "previous release" donde
# el número era incidental), y docs/PENGU_BUILD.md: "v0.6" -> "v0.16.0"
$ grep -rn 'Version covered\|Versión cubierta' LANGUAGE.md LANGUAGE_Spanish.md \
      PenguScriptGuideEnglish.md PenguScriptGuideSpanish.md
LANGUAGE.md:3:> **Version covered:** PenguScript **0.16.0** … 
LANGUAGE_Spanish.md:3:> **Versión cubierta:** PenguScript **0.16.0** …
PenguScriptGuideEnglish.md:3:> **Covered version:** PenguScript **0.16.0**
PenguScriptGuideSpanish.md:3:> **Versión cubierta:** PenguScript **0.16.0**
```

**Falsificación (los gates fallan al revertir, comprobado):**

```bash
$ # guía EN vuelta a 0.14.x + FALLBACK_VERSION a 0.15.0
$ pytest tests/test_version.py -q
4 failed, 24 passed        # fallback, claim de la guía, y los dos ratchets de tokens
```

**Qué se hizo:**

1. `tests/test_version.py` (**creado**, 28 casos + 6 skip justificados):
   - **Maquinaria:** `VERSION` == `FALLBACK_VERSION` == `pengu_version.__version__` ==
     `__version_tag__` == `pengu_lsp.__version__`. El fallback es el que más
     importa: sólo se usa en builds congelados, así que su deriva es invisible
     hasta que se publica.
   - **12 afirmaciones de versión actual** parametrizadas (cabeceras de los 4
     documentos normativos, los 2 ejemplos `pengu.yaml`, el `e.g. PenguScript vX`,
     el "behavior at version", `docs/PENGU_BUILD.md`, los `.vsix` de
     `docs/README_RELEASE.md`), cada una comparada con `VERSION`. Se acepta la
     forma `0.16.x` como afirmación de la serie.
   - **Ratchet de tokens obsoletos** (`_STALE_RE` + `HISTORICAL`): cualquier
     `0.14.x`/`0.15.0`/`v0.6` en el conjunto escaneado falla hasta que alguien
     escriba **por qué** es histórico. `test_historical_allowlist_has_no_dead_entries`
     impide que la lista de excepciones se pudra en una amnistía general.
   - Deliberadamente **no** se escanea `pengu_project.py`: está lleno de literales
     numéricos (`time.sleep(0.15)`, duraciones de caché) que no son versiones, y un
     gate que da falsos positivos es un gate que la gente aprende a ignorar. Su
     superficie de versión es la plantilla `pengu.yaml`, que es la versión *del
     proyecto*, no la del toolchain.
   - Deliberadamente la regex **no** marca `0.9`, `0.85`, `0.4` ni `0.1.0` (medido:
     aparecen como tiempos de benchmark, llamadas a `time.sleep` y la versión por
     defecto de un proyecto nuevo).
2. Las 9 afirmaciones desviadas corregidas.
3. `pengu_version.py`: los ejemplos de docstring (`"0.10.0"`, `"v0.10.0"`) pasan a
   la versión actual; eran la única deriva dentro del propio módulo de versión.

**Test:** `tests/test_version.py` (archivo nuevo).
**Commit:** `fase7(item 7.5): tests/test_version.py — 9 archivos con deriva a 0.16.0`

---

### 7.3 — Documentar la sintaxis canónica de rango y `frozen`

_(pendiente)_

---

### 7.8 — `CONTRIBUTING.md`

**Premisa del roadmap:** cubre cómo correr los tests, el principio "ningún gate por
texto" (AUDIT §15.2), el estilo y el proceso de release.

**Verificación previa:**

```bash
$ test -f CONTRIBUTING.md
# (no existía)
$ sed -n '2942,2975p' AUDIT_1.0.md   # §15.2 lista 7 gates verdes sobre código roto
```

**Resultado:** ✅ cerrado — `CONTRIBUTING.md` (350 líneas, 10 secciones).

**Evidencia / verificación:**

- §4 reproduce la tabla de los **7 gates falsos-verdes** de §15.2 y enuncia la
  regla ("si aprueba una propiedad inspeccionando texto, no es un gate"), con los
  4 ofensores históricos y su conversión en Fase 8.
- §7 documenta el flujo de diagnóstico con el catálogo **generado** de 7.1
  (`tools/gen_error_catalog.py --write`, no editar a mano §22.2/§22.3).
- Todas las rutas y anclas de la doc resuelven (comprobado: 0 enlaces roMuertos de
  ruta; la ancla `README.md#building-the-runtime-from-source` corresponde al
  encabezado real `### Building the Runtime from Source`, `README.md:448`).
- **Refutación incorporada:** el brief de la fase decía que el estilo es de **2
  espacios** porque `pengu fmt` lo impone. Es **falso** (`F7-N2`): `.pengufmt.toml`
  y `std/.pengufmt.toml` fijan `tab_size = 4`, `_resolve_indent` devuelve 4 por
  defecto y `pengu fmt --check std/` da 0 archivos. `CONTRIBUTING.md` documenta 4
  espacios, que es lo medido.

**Test:** no aplica (documento); la verificación es la resolución de enlaces y la
inspección de las secciones exigidas.
**Commit:** `fase7(item 7.8): CONTRIBUTING.md`

---

### 7.9 — `docs/ARCHITECTURE.md`

**Premisa del roadmap:** mapa de fases (parse → collect → check → infer → codegen →
cache) con archivos y puntos de entrada.

**Resultado:** ✅ cerrado — `docs/ARCHITECTURE.md` (499 líneas).

**Evidencia / verificación:**

- Diagrama ASCII del pipeline, tabla `Etapa | Archivo(s) | Símbolo de entrada |
  Entrada | Salida | Fallos`, detalle por etapa, modelo de diagnóstico, caché e
  incrementalidad, frontera FFI, frontera runtime/ABI (enlaza `ABI.md`, no lo
  duplica) y guía "dónde tocar para cambiar qué".
- **Verificación por muestreo** de 14 símbolos de entrada en su archivo real:
  `PenguBuilder`, `.bundle()`, `.compile()`, `build_project`, `check_project`,
  `PenguParser`, `resolve_imports`, `_collect_top_level`, `TypeInferrer`,
  `generate_bundle`, `cache_root`, `BindGenerator`, `runtime_lib_dirs`,
  `PenguLanguageServer` → todos existen (1 ocurrencia cada uno salvo
  `PenguBuilder`, 10).
- **Corregido tras 7.2:** el documento afirmaba que `E0059`–`E0060` estaban *sin
  asignar* y que `E0061` era del lockfile y `E0062` de dependencias, con el rango
  del lenguaje acabando en `E0058`. Tras 7.2 eso era obsoleto; §4 ahora documenta
  `E0063`–`E0065` como lenguaje y `E0061`/`E0062` como capa de proyecto, y advierte
  explícitamente del **peligro de colisión entre capas** (`F7-N3`).
- El documento enuncia la convención correcta: **el nombre del símbolo, no el
  número de línea, es el contrato** (las líneas se desplazan con cada edición).

**Test:** verificación por muestreo (arriba) + resolución de enlaces (0 roto).
**Commit:** `fase7(item 7.9): docs/ARCHITECTURE.md`

---

### 7.10 — `docs/ABI.md` (verificar y enlazar, no recrear)

**Premisa del roadmap:** "**Ya existe** (Fase 3, item 3.11). Verifica y enlaza, no
recrees."

**Verificación previa:**

```bash
$ test -f docs/ABI.md && wc -c docs/ABI.md
6852 docs/ABI.md                                     # EXISTE
$ grep -n 'PENGU_ABI_VERSION' docs/ABI.md pengu_runtime.h | head -3
docs/ABI.md:10: `PENGU_ABI_VERSION` (currently **1**) …
pengu_runtime.h:58:#define PENGU_ABI_VERSION 1      # coincide
$ grep -n 'ABI.md' docs/README.md
19:| [`ABI.md`](ABI.md) | The runtime ABI policy … | No — authored |   # ya enlazado
$ grep -c 'def test' tests/test_abi_version.py tests/test_abi_layout.py
tests/test_abi_version.py:7
tests/test_abi_layout.py:1
$ ls tests/abi/
test_abi_layout.c
```

**Resultado:** ✅ **premisa confirmada y sustancialmente ya satisfecha** — es el
único item de la fase que no requería trabajo nuevo. El documento existe, su
afirmación de versión (`1`) coincide con `pengu_runtime.h:58`, está indexado en
`docs/README.md` y está cubierto por `tests/test_abi_version.py` (7 casos),
`tests/test_abi_layout.py` y el arnés C `tests/abi/test_abi_layout.c`.

**Entregado en su lugar:** `docs/README.md` pasa a indexar los tres documentos
nuevos de la fase (`ARCHITECTURE.md`, `CROSS_COMPILATION.md`, y el
`error_catalog.json` generado), de modo que ninguno queda huérfano; y
`docs/ARCHITECTURE.md` enlaza `ABI.md` en su sección de frontera runtime/ABI (sin
duplicar su contenido).

**Test:** no aplica (verificación + enlace); la coherencia del ABI ya la cubren los
tests existentes.
**Commit:** `fase7(item 7.10): indexar los documentos nuevos en docs/README.md`

---

### 7.11 — `docs/CROSS_COMPILATION.md`

**Premisa del roadmap:** basado en `LANGUAGE.md` §20.2.3.

**Verificación previa:** `LANGUAGE.md` §20.2.3 existe (línea 3325), documenta
`--target <triple>`, `--cc`, la detección automática y `PENGU_RUNTIME_CROSS`, y
declara que sólo Linux ⇄ Windows está soportado en 1.0.

**Resultado:** ✅ cerrado — `docs/CROSS_COMPILATION.md` (396 líneas).

**Evidencia / hallazgos verificados en el código** (no copiados de la doc):

| Hallazgo | Medición |
|---|---|
| Los triples se parsean en `parse_target_triple` (`pengu_project.py:217-245`) y **un triple desconocido cae silenciosamente al host** | `riscv64-unknown-elf` → `os=""` y construye para el host, sin `.exe` |
| `--target` **no** fija el contexto de `when os` | Un programa que devuelve 1 bajo `when os=="windows"` emitía `return 0` con sólo `--target`; con `-D os=windows` emitía `return 1` |
| Sólo el bundle C cruzado no necesita toolchain | `build --target x86_64-w64-mingw32 -o win_bundle.c` funciona sin MinGW |
| La pre-flight del runtime **no** mira `PENGU_RUNTIME_CROSS` | `_find_runtime_archive()` (`:2655`) busca sólo `runtime_lib_dirs()` del host, así que un `libpengu_runtime.a` del host debe seguir siendo localizable |
| `build_runtime.py` **no** tiene modo cruzado | Sólo `--rebuild`; `get_toolchain()` (`:89-96`) elige gcc/clang/cc del host |
| El único test de MinGW es `skipif` y **no produce ni ejecuta un `.exe`** | `tests/test_cross_compile.py:119-130`; no hay job de cross-compilación en CI |

Los tres primeros se documentan como **limitaciones honestas** con el comando que
las reproduce, porque son trampas reales para el usuario (un triple mal escrito
compila para el host sin avisar).

**Test:** no aplica (documento); los fallos de toolchain ausente se citan
literalmente desde `pengu_project.py:802-807` y `:2794-2805`.
**Commit:** `fase7(item 7.11): docs/CROSS_COMPILATION.md`

---

## Hallazgos nuevos de la Fase 7 (no estaban en el roadmap)

### F7-N3 — 🔴 El espacio de nombres `Exxxx` está compartido entre capas y nadie lo vigilaba

**Cómo se encontró:** al asignar códigos nuevos en 7.2 elegí `E0059`–`E0061` (el
siguiente hueco tras `E0058` del catálogo del lenguaje). `E0061` **ya estaba en
uso**: es el código del `pengu.lock` ausente/desactualizado bajo
`--locked`/`--frozen`, y hay tests que lo asertan.

**Medición:**

```bash
$ grep -rhoP 'E\d{4}' pengu_project.py pengu_lock.py pengu_semver.py | sort | uniq -c
      2 E0000        # ruido: docstrings/menciones
      3 E0061        # pengu_project.py:2110, :2126, :2244 (lockfile)
      1 E0062        # pengu_project.py:3800 (docstring)
$ grep -rn 'E0062' --include="*.py" . | grep -v __pycache__
./pengu_project.py:3800:    :class:`DependencyConflictError` (roadmap 4.2, error E0062).
```

Dos defectos distintos:

1. **Colisión de espacio de nombres.** El lenguaje emite `E0000`–`E0058` por el
   kwarg `code=`; la capa de proyecto (lockfile, resolución de dependencias) emite
   `E0061`/`E0062` como **cadenas** `"[Exxxx] …"`. Nada cruzaba las dos capas, así
   que reutilizar un código habría creado dos significados para el mismo número.
   Es la misma clase de bug que 7.2 cierra dentro del lenguaje, un nivel más
   arriba.
2. **`E0062` era fantasma.** El docstring de `pengu_project.py:3800` prometía ese
   código para `DependencyConflictError`, pero el mensaje de la excepción no lo
   contenía nunca: ningún usuario ni herramienta podía casar el diagnóstico.

**Impacto:** un código con dos significados inutiliza cualquier quick-fix guiado
por código, que es exactamente el argumento del audit §2.3 para el lenguaje.

**Decisión:** ✅ **corregido dentro de 7.2** (no diferido: es barato y es
precisamente la clase de defecto del item):
- Los tres códigos nuevos del lenguaje pasan a **`E0063`/`E0064`/`E0065`**,
  saltando el rango ya ocupado por la capa de proyecto.
- `DependencyConflictError` ahora emite su código:
  `[E0062] conflicting version requirements for dependency '…'`. No había ningún
  test que asertara el texto literal del mensaje (sólo `pytest.raises` del tipo),
  así que el cambio no rompe a nadie y el código pasa a ser real.
- `tools/gen_error_catalog.py` extrae también la capa de proyecto (cadenas
  `"[Exxxx] …"` y los dicts JSON con `"code": "Exxxx"`) y genera §22.3.1.
- `tests/test_error_catalog_sync.py::test_language_and_project_codes_are_disjoint`
  falla si las dos capas vuelven a solaparse. **Falsificado:** renumerando
  `E0065`→`E0061` → `5 failed`, incluido el test de disjunción.

**Lección para el roadmap:** el criterio de 7.2 ("ningún `(código, mensaje)`
duplicado") se queda corto: hay que exigir además que un código no cruce capas.

### F7-N1 — 🟠 El checker no hace cumplir la nominalidad de `seal` en 3 posiciones

**Cómo se encontró:** verificando la afirmación de `CHEATSHEET.md` §10.4 ("valores de
distintos `seal` no son intercambiables") al generar el catálogo (7.1).

**Medición** (`.venv/bin/python` + `tests.conftest.gen_bundle`, pipeline completo
parse→check→infer→codegen):

| Caso | Resultado medido |
|---|---|
| `set a is b` (`UserId` ← `PostId`) | **CLEAN** — no se detecta |
| `calling take with b` (argumento `UserId` ← `PostId`) | **CLEAN** — no se detecta |
| `a == b` (`UserId` == `PostId`) | **CLEAN** — no se detecta |
| `var a as UserId is b` | `E0005` ✅ |
| `return b` desde `weave … into UserId` | `E0020` ✅ |
| `calling xs.push with b` (`list of UserId`) | `E0018` ✅ |
| `var i as int is a` (quitar el sello) | `E0005` ✅ |
| `var a as UserId is 1` (poner el sello) | `E0005` ✅ |

**Impacto:** una garantía nominal se cumple en 5 posiciones y se salta en 3. El caso de uso
canónico (`seal UserId`/`seal PostId`, o divisas) puede mezclarse por asignación, por paso de
argumento y por comparación.

**Blast radius medido:** `grep -c '^seal ' std/*.pengu` → **0**. La stdlib no declara ningún
`seal`, así que corregirlo no puede romper los 52 módulos.

**Decisión:** ⏸️ **diferido a la Fase 8**. Es un cambio de semántica del checker, no de
documentación, y la Fase 7 es docs/style por carta; el roadmap indica explícitamente diferir lo
que "requiere decisiones de lenguaje que no son de esta fase". La Fase 8 es donde vive
"convertir todo gate de texto en un gate que compila/ejecuta/mide", que es exactamente el test
que este arreglo necesita (los 3 casos de arriba como casos de `check_error`).

**Entregado en su lugar:** `CHEATSHEET.md` §10.4 deja de afirmar la garantía universal y
documenta el hueco con nombre y alcance; así el defecto es visible para el usuario en vez de
quedar como una promesa falsa.

**Reapertura:** abrir un item de Fase 8 que añada los 3 casos a `tests/` y haga que el checker
compare sellos nominalmente en `set`, en el paso de argumentos y en `==`.

### F7-N2 — ✅ REFUTADA la regla "`pengu fmt` impone 2 espacios" de AUDIT §10.4

El audit §10.4 lista como regla incumplible *"Usa 4 espacios (implícito por los ejemplos)"*
porque *"`pengu fmt` impone 2 y `--indent 4` corrompe"*. **Es falso en `355d946`:**

| Evidencia | Valor |
|---|---|
| `.pengufmt.toml` | `[formatting] tab_size = 4` |
| `std/.pengufmt.toml` | `[formatting] tab_size = 4` |
| `pengu_project.py:2631` (`_resolve_indent`) | `return 4` — el **default** es 4 |
| `pengu_project.py:2627` | un `--indent` explícito gana, no corrompe |
| `python pengu_project.py fmt --check std/` | `0 file(s) would be reformatted` |
| commit | `c42776c feat(fmt): pin 4-space style with .pengufmt.toml` |

**Consecuencia para 7.7:** la regla "4 espacios" **no** hay que relajarla; ya se cumple y está
fijada por configuración. Lo que hay que corregir es la **documentación obsoleta que dice 2
espacios** (`LANGUAGE.md` §20.7, `CHEATSHEET.md`). Se resuelve en 7.3/7.7 con medición.


---

_(los items restantes se documentan a continuación a medida que se cierran)_
