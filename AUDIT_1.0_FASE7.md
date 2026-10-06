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
**Commit:** `fase7(item 7.1): generar §22.2/§22.3 desde el código`

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

**Resultado:** ⏳ en implementación (la evidencia se registra al cerrar)

**Evidencia:** _(pendiente)_

**Test:** `tests/test_error_codes_uniqueness.py::test_no_new_shared_condition_families` (ratchet
sobre el catálogo generado) + `::test_static_var_placement_has_its_own_code` y similares.
**Commit:** _(ver roadmap)_

---

## Hallazgos nuevos de la Fase 7 (no estaban en el roadmap)

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
