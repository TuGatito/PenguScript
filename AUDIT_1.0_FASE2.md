# 🐧 AUDITORÍA 1.0 — FASE 2: COMPLETAR 1.0 DEL LENGUAJE

> **Alcance:** `ROADMAP_2.0.md` Fase 2, items 2.1–2.12, más los extras.
> **Punto de partida:** `0.16.0`, commit `dd52c15` (Fase 1 cerrada).
> **Reglas aplicadas:** **C1** (ningún test aprueba una propiedad inspeccionando texto), **C2** (todo
> test falla al revertir su fix), **C3** (las decisiones se miden y documentan antes de implementar),
> **C4** (el grammar es infraestructura: una familia de conflictos por commit).

---

## §1. Decisiones de diseño (Regla C3)

Las decisiones se registran aquí **antes** de implementarlas, con la medición que las respalda.

### §1.1 Item 2.1 — Jerarquía de bounds: **Opción B (cadena monótona)**

#### Medición (ejecutada, no asumida)

Script reproducible sobre el `PenguChecker` real, 12 operadores × 6 bounds = 72 sondas:

```
op         None       Num  Integrum       Par      Ordo  Vinculum
+         E0049        OK        OK     E0049     E0049     E0049
-         E0049        OK        OK     E0049     E0049     E0049
*         E0049        OK        OK     E0049     E0049     E0049
/         E0049        OK        OK     E0049     E0049     E0049
%         E0049     E0049        OK     E0049     E0049     E0049
==        E0049        OK        OK        OK     E0049     E0049
!=        E0049        OK        OK        OK     E0049     E0049
<         E0049        OK        OK     E0049        OK     E0049
>         E0049        OK        OK     E0049        OK     E0049
&         E0049     E0049        OK     E0049     E0049     E0049
|         E0049     E0049        OK     E0049     E0049     E0049
<<        E0049     E0049        OK     E0049     E0049     E0049

bound concedido:  Num -> [+ - * / == != < >]
                  Integrum -> [+ - * / % == != < > & | <<]
                  Par -> [== !=]
                  Ordo -> [< >]
                  Vinculum -> []
```

#### Diagnóstico: el culpable es **una sola línea**

`pengu_types.py:213-215`:

```python
def is_numeric(self) -> bool:
    # 'Integrum' refines 'Num': integers are numeric.
    return "Num" in self.bounds or "Integrum" in self.bounds
```

Las comprobaciones de operador consultan `is_numeric()` **además del bound correcto**
(`pengu_infer.py:3289` para `==`, `:3301` para `<`). Como `Num` satisface `is_numeric()`, esas
ramas se saltan el `E0049` y `Par`/`Ordo` quedan **inertes**.

#### Impacto medido sobre los 52 módulos de la stdlib

Barrido de todos los `where <V>: <bound>` de `std/`:

| Bound usado en stdlib | Sitios |
|-----------------------|--------|
| `K: Par, V: Par` | 4 |
| `T: Num, T: Ordo` | 1 |
| `T: Par` | 4 |
| `T: Ordo` | 1 |
| `T: Num` | 4 |
| `T: Integrum` | 1 |
| `T: Donum` | 1 |

Y para los 4 sitios con `T: Num`: **ninguno compara un valor de tipo `T`**. Los tres usos de `>` que
aparecían en un primer barrido eran sobre el índice concreto `i as int`, no sobre `T`. **Un regex
demasiado amplio produjo un falso positivo que la inspección del cuerpo desmintió** — el mismo
patrón de error que la Fase 0 y la Fase 1 ya documentaron.

#### Decisión: **Opción B — cadena monótona estricta**

| Criterio | Opción A (retículo) | **Opción B (elegida)** |
|----------|--------------------|------------------------|
| Coincide con `LANGUAGE.md` | ❌ No: la tabla documental ya asigna `Par` a `==` y `Ordo` a `<` | ✅ **Sí** |
| Bounds con significado | ❌ `Par`/`Ordo` inertes | ✅ Cada uno concede algo distinto |
| Monótona (añadir bound no quita capacidad) | ✅ | ✅ |
| Rompe código de `std/` | No | **No** (medido: 0 sitios afectados) |
| Rompe los 105 ejemplos de `LANGUAGE.md` | No | Por verificar (item 2.2) |

**Justificación:** la documentación ya define la cadena (`Num` → aritmética, `Par` → igualdad,
`Ordo` → orden); el código era el que se desviaba. La Opción B es **la corrección que hace que el
código cumpla la documentación**, y la medición demuestra que es gratis para la stdlib. La Opción A
habría exigido reescribir la documentación para justificar bounds sin semántica.

**Implementación:** una tabla única `CONCEPT_OPERATORS` en `pengu_types.py`; los 5 sitios de
`pengu_infer.py` que hoy consultan `is_numeric()` la consultan a ella. Ningún `is_compatible` cambia.

#### Efecto observable (el que hace visible el fix)

```pengu
# Antes (incoherente): T: Num concede '<' pero T: Par no lo concede.
weave f shard T where T: Num with a as T, b as T into bool:
  return a < b          # OK  -> pero 'Num' no implica orden en la tabla
weave g shard T where T: Par with a as T, b as T into bool:
  return a < b          # E0049 -> y 'Num' sí lo concedía
```

Tras el fix, `T: Num` **rechaza** `a < b` (falta `Ordo`) y lo acepta con `where T: Num and T: Ordo`,
que es exactamente el patrón que la documentación ya usa. **Ya no hay ninguna forma de que añadir un
bound quite una capacidad.**

---

### §1.2 Item 2.3 — `alias` en `concept`: **Opción B (retirar el ejemplo)**

#### Medición

| Comprobación | Resultado |
|--------------|-----------|
| ¿El grammar tiene producción para `alias` en `concept_method`? | **No**: `concept_method: weave_modifier* "weave" ...` es la única alternativa (`pengu_grammar.py:93`) |
| ¿Qué produce el bloque 59 al compilarlo? | `E0000 Syntax error: unexpected 'alias' at line 2, column 5` |
| ¿Qué dice `LANGUAGE.md` §11.7? | *"The syntax for declaring the associated type (`alias Item`) **is accepted for forward compatibility**"* |
| ¿Qué falta para implementarlo? | Producción nueva en el grammar **+** resolución de `Self.Item` en monomorfización (no implementada) **+** soporte en `_resolve_call_target` para bounds con tipos asociados |
| ¿Hay un caso de uso real hoy? | **No**: el trabajo se hace con `shard T and U`; los 52 módulos de la stdlib y los `tests/` no lo necesitan |

#### Decisión: **Opción B** — retirar el ejemplo y declarar la feature ⏸️ diferida

**El hallazgo real no era el del roadmap.** El roadmap decía "el ejemplo documenta algo que no
existe". La medición encontró algo peor: **§11.7 afirmaba explícitamente que la sintaxis *se acepta*
por compatibilidad futura.** Eso es una afirmación **falsa** —el parser la rechaza— y es peor que un
ejemplo obsoleto, porque un lector puede escribirla confiando en que compila.

**Alternativas consideradas:**

| Alternativa | Coste | Por qué se descartó |
|-------------|-------|---------------------|
| **A — Implementar** | L (grammar + monomorfización + bounds + tests) | No hay caso de uso; la resolución de `Self.Item` en monomorfización es un cambio profundo en el sistema de tipos, y la Fase 2 ya tiene el item 2.4 (188 conflictos del grammar). Implementar a medias sería peor que no tenerlo |
| **B — Retirar (elegida)** | S | Corrige una afirmación falsa, no rompe nada (nadie podía usarlo), y deja la feature correctamente marcada como ⏸️ con la justificación técnica |
| **C — Dejar el ejemplo y solo marcarlo ⏸️** | S | Insuficiente: el bloque seguiría siendo un ejemplo ```pengu que no compila, y §11.7 seguiría afirmando que se acepta |

**Implementación:**
1. §11.7 de `LANGUAGE.md` y de `LANGUAGE_Spanish.md` reescrita: el esquema **ya no** es un bloque
   `pengu` (es documentación de la forma prevista, no código que compile), y el texto declara la
   feature **⏸️ diferida a 1.1** con la razón.
2. `tests/test_audit_regressions.py::test_alias_in_concept_is_not_implemented`: un **tripwire** que
   falla si alguien añade la producción del grammar. El mensaje del test explica que, si eso ocurre,
   hay que implementar también la resolución de `Self.Item` y actualizar la doc — en lugar de enviar
   media feature.
3. Un test que verifica que **la alternativa documentada sí funciona**:
   `shard Self and Item` con un `bind` real compila. Documentar un workaround que no compila sería
   el mismo error en otro sitio.

**Efecto en las cuentas de la auditoría:** `LANGUAGE.md` pasa de **104** a **105** bloques `pengu` (se retira el 59 y se añade un
ejemplo de la cadena de bounds en §10.9), y los que compilan de 33 a **35** (33 %). El defecto documental nº 4 de `AUDIT_1.0.md` §13.1 (bloque 59)
queda **cerrado**, y se añade un **quinto ❌ REFUTADO** (§18.1 nº 24).


---

## §2. Hallazgos que cambian lo que dice la documentación

Cada uno está **medido**, no leído. Los que contradicen `LANGUAGE.md` llevaron a
corregir el documento (y su gemelo español) en el mismo commit.

### §2.1 ❌ REFUTADO — `alias` en `concept` "se acepta por compatibilidad futura"

`LANGUAGE.md` §11.7 afirmaba que la sintaxis `alias Item` dentro de un `concept` **se acepta** y
solo falta resolver `Self.Item`. Lo primero es falso:

```
$ pengu check assoc.pengu
assoc.pengu:2:5 [E0000] Syntax error: unexpected 'alias' at line 2, column 5
```

`concept_method` en `pengu_grammar.py:93` acepta únicamente firmas `weave`. La sección se reescribió
para marcar la feature como **⏸️ diferida a 1.1** y el comportamiento actual está fijado por un
*tripwire*.

**Cómo se encontró:** el roadmap decía "el ejemplo documenta algo que no existe". Al compilarlo
apareció la afirmación falsa, que es un defecto peor: el ejemplo obsoleto se ignora, la promesa de
que compila se cree.

### §2.2 ❌ REFUTADO — `float` es de 64 bits y mapea a `double`

La tabla de §4.1 decía `float`/`f64`/`double` → `double`, 64 bits. Medido compilando cada grafía:

| Grafía | C emitido |
|--------|-----------|
| `float` | `float` (32 bits) |
| `f32` | `float` (32 bits) |
| `f64` | `double` (64 bits) |
| `double` | `double` (64 bits) |

Un lector que escribiera `float` esperando doble precisión obtenía simple **en silencio**. La tabla
ahora es canónica por tipo C y está verificada por test.

### §2.3 ❌ REFUTADO — `isize` es "`ssize_t`-ish"

Decía `usize`/`isize` → "`size_t`/`ssize_t`-ish". `isize` emite **`intptr_t`**. Y `ssize_t` no es
escribible: `CTypeMapper.to_c_type` tenía una rama para él que la gramática nunca podía alcanzar.
La rama muerta se eliminó.

### §2.4 ❌ REFUTADO — `ssize_t` estaba en el codegen

Consecuencia del anterior: era una rama inalcanzable. Eliminada en el mismo commit que el §2.3.

### §2.5 ⚠️ `many T` funciona, pero no como decía la tabla

La tabla de conceptos decía que `many T` solo es válido en `declare`. Es **al revés**:

| Forma | ¿Aceptada? | Diagnóstico |
|-------|-----------|-------------|
| `many T` en `weave` | ✅ | funciona de extremo a extremo |
| `many T` en `declare` | ❌ | `E0005 'many' parameters are not allowed in 'declare' statements` |
| `...` en `declare` | ✅ | varargs crudos de C |
| `...` en `weave` | ❌ | error de sintaxis |
| `f(...xs)` (spread en la llamada) | ❌ | `E0000` — **no implementado** |

Verificado ejecutando: el sitio de llamada empaqueta los argumentos en un array temporal y los pasa
como `PenguSlice`, así que dentro del cuerpo `xs` es una secuencia indexable normal.

### §2.6 ⏸️ Identificadores solo ASCII (no documentado)

`日本語`, `café`, `Ω` como nombre son `E0000`. La restricción es **léxica** (aplica a `const`,
`weave`, campos, parámetros y tipos). Es asimétrico con el resto del toolchain: BOM UTF-8, CRLF y
literales de string Unicode completo funcionan. No estaba escrito en ninguna parte.

---

## §3. Alcance completado y alcance no completado

### §3.1 Items cerrados

| Item | Qué se hizo | Commit | Verificación |
|------|-------------|--------|--------------|
| **2.1** | Jerarquía de bounds: cadena monótona con tabla única `CONCEPT_OPERATORS` | `daf399e` | 84 tests; matriz 12 ops × 5 bounds medida |
| **2.2** | Documentar la cadena + bloque legible por máquina, sincronizado por test | `a5b691c` | 7 tests; C2 verificado |
| **2.3** | Retirar la afirmación falsa de `alias` en `concept`; tripwire | `2058220` | 2 tests; tripwire verificado |
| **2.4b** | Test de precedencia/asociatividad como contrato previo al grammar | `b9807e4` | 99 tests |
| **2.5** | `to` canónica; `..` deprecada con W0013 y ahora hace slice | `d13ec35` | 15 tests; C2 verificado |
| **2.6** | Ya satisfecho: `frozen ref to T` → azúcar de `ref to frozen T`, documentado y con test de identidad estructural | (preexistente) | `test_frozen.py` |
| **2.7** | Semántica real de `many T` y del spread (no implementado) | `87192b5` | 12 tests |
| **2.8** | Matriz de `derive` medida | `588afb4` | 14 tests |
| **2.9** | Identificadores ASCII documentados | `87192b5` | (mismo commit que 2.7) |
| **2.10** | Tabla de primitivos canónica y verificada; 3 defectos corregidos | `3bddc4e` | 30 tests |
| **2.12** | W0005: 50 → 0 (supresión en `test` + renombrado de 20 locales) | `160a174`, `1ab64bc` | 52/52 stdlib sin errores ni warnings |

### §3.2 Item 2.4 (reducción de conflictos del grammar): **intentado y revertido**

**No se redujo el número de conflictos. Sigue en 188, y el presupuesto sigue en 188.** Esto es un
resultado, no un olvido, y la evidencia importa más que el número.

**Qué se intentó.** La familia más prometedora era hacer izquierda-recursiva la lista de parámetros
de un tipo función, que es la forma canónica de eliminar el conflicto de repetición:

```diff
-fn_param_list: fn_param (("," | _AND_SEP) fn_param)*
+fn_param_list: fn_param_list ("," | _AND_SEP) fn_param
+             | fn_param
```

**Qué pasó.** El contador de conflictos bajó de 188 a 186 (por eso el presupuesto se bajó a 186 en
el mismo cambio). Pero la suite del stdlib se rompió:

```
$ pengu check --entry std/tally.pengu
std/tally.pengu:862:25 [E0005] Function expects between 1 and 1 arguments, but received 2
```

y con ella **11 de los 52 módulos**. La causa:

```pengu
weave zip_with shard T and U and V with xs as list of T, ys as list of U,
      f as weave with a as T, b as U into V into list of V:
    ...
    for k in idxs then (calling f with (xs at k), (ys at k))
```

`f` es un tipo función de **dos** parámetros. Con la regla izquierda-recursiva el `,` que separa `a`
y `b` **dentro** del tipo de `f` se consume como separador de la lista de parámetros **exterior**, y
`f` queda tipado con un solo parámetro. Es exactamente el riesgo de ambigüedad de comas anidadas que
hace peligrosa esta familia.

**Por qué la suite de tests no lo detectó.** `b9807e4` (el test de precedencia) y la suite completa
**pasaron** con el grammar roto. La cobertura existente ejercita tipos función de varios parámetros
en `declare` y en `alias`, pero **no un `weave` genérico implementado cuyo parámetro sea un tipo
función de dos parámetros** — que es precisamente lo que usa la stdlib. El fallo lo encontró el
barrido de `pengu check --entry std/*.pengu`, no `pytest`.

> **Hallazgo para la Fase 6.** `tests/` no verifica que la stdlib compile como stdlib. Un cambio en
> el grammar puede romper 11 módulos con la suite en verde. Esto debería ser un gate de CI
> (verificar los 52 módulos), y no lo es.

**Decisión (regla C4).** Revertido por completo. La familia de precedencia-asociatividad no se puede
tocar sin resolver antes la ambigüedad de las comas anidadas en tipos función, y eso es un cambio de
diseño del grammar, no una refactorización. Se documenta y se deja al 1.1.

**Alternativa que sí funcionaría, para el 1.1.** El patrón correcto es *factorizar* la lista de
parámetros con un terminador explícito en lugar de hacerla izquierda-recursiva, o tipar el tipo
función con paréntesis obligatorios (`weave with (a as T, b as U) into V`), que elimina la
ambigüedad de raíz y además mejora la legibilidad. Ambas son cambios de sintaxis y necesitan
decisión de diseño (regla C3), no solo de grammar.

### §3.3 Items no completados y veredicto medido

| Item | Estado | Razón medida |
|------|--------|--------------|
| **2.4** (reducción) | ⏸️ intentado y revertido | §3.2 y §3.6: `return_stmt` posee 45 de los 188 conflictos; quitarlos exige quitar el `_NEWLINE` opcional de toda la familia de sentencias |
| **2.4** (reglas duplicadas) | ❌ **medido: no aporta** | §3.6: colapsar los 5 niveles `_no_cast` duplicados dio **188 → 188** |
| **2.8** (parte `Forma`/`Iterabilis`/`Donum`) | ✅ **cerrado** | Verificado: los tres se **rechazan** con `E0005`, no son derivables. Matriz documentada y con test |
| **2.11** `W0008` | ⏸️ diferido a 1.1 | §3.8.2: necesita procedencia de símbolos; 69/73 falsos positivos |
| **2.11** `W0011` | ❌ **REFUTADO** | §3.8.2: el grammar exige `stmt+`; un `test` vacío es `E0000` |
| **2.11** `W0012` | ⏸️ diferido a 1.1 | §3.8.2: `@deprecated`/`W0006` funcionan; la stdlib solo tiene docstrings |

`W0001` sigue presente y es el mayor resto de ruido de la stdlib:

```
[W0001] transmute from 'int' (4 bytes) to 'ref to byte' (8 bytes) h...
[W0001] transmute from 'int' (4 bytes) to 'ref to char' (8 bytes) h...
[W0001] transmute from 'int' (4 bytes) to 'ref to void' (8 bytes) h...
[W0001] transmute is unsafe, use 'to' for safe conversions
```

### §3.4 Hallazgo nuevo: las dos referencias del lenguaje están desincronizadas

Al arreglar el bloque `prim-c-map` que faltaba en la versión española (item 2.10) se midió la
simetría estructural de las dos referencias comparando sus encabezados numerados:

| | `LANGUAGE.md` | `LANGUAGE_Spanish.md` |
|---|---|---|
| Encabezados totales | 201 | **185** |
| Secciones numeradas | 131 | **117** |

**La versión española va 14 secciones por detrás.** Faltan, entre otras:

```
§2        §5.0      §19.0     §20.2.1  §20.2.2  §20.2.3  §20.2.4  §20.2.5
§23.1     §23.2    §23.3     §23.4    §23.5
```

Esto es **preexistente**, no lo introdujo la Fase 2. Pero explica por qué el defecto del §2.1 pudo
pasar: la regla de bilingualidad se aplica a lo que se escribe, no detecta lo que nunca se tradujo.
Cerrar la brecha es una tarea de traducción, no de código, y corresponde a la Fase 7 (documentación);
se registra aquí porque el primer paso es saber cuánto falta y exactamente qué.

**Lección de método:** un test de sincronización con el nombre del archivo escrito a mano verifica un
archivo, no una propiedad. El test de §2.10 tenía `Path(...) / "LANGUAGE.md"` en duro y por eso el
bloque que faltaba en español pasó desapercibido hasta una comprobación manual posterior. Ahora
parametriza sobre las dos referencias.

### §3.5 Hallazgo nuevo: el test del leak conocido es **inestable**

La suite completa de la Fase 2 terminó en **2426 passed, 0 failed** pero con **1 xpassed**, donde la
línea base no tenía ninguno. Perseguirlo dio un resultado más interesante que un test roto:

```
tests/test_string_composition_suite.py::test_string_composition_no_memory_leaks[leak_binary_interp]

run 1: 1 xpassed      run 4: 1 xpassed
run 2: 1 xfailed      run 5: 1 xpassed
run 3: 1 xfailed
```

El mismo test, sin cambios de por medio, **pasa 3 de 5 veces y falla 2 de 5**. Está marcado
`xfail(strict=False)`, así que no rompe la build — pero el marcador existe para documentar un leak
**conocido y estable**: `"a '(value to string)' temporary passed as a call argument is never
released"`. Que el detector lo vea solo a veces significa que **el leak depende del timing o de la
ruta de ejecución**, no de que el compilador gestione o no el temporal.

**Por qué importa más que un fallo normal.** El propio archivo dice qué hacer cuando el test XPASSa:

> *"Strict xfail: as soon as the compiler owns its expression temporaries this test XPASSes and CI
> asks for the marker (and the two leak xfails) to be removed."*

Es decir, el XPASS es **la señal de "el leak se arregló"**. Con un detector inestable esa señal es un
falso positivo el 60 % de las veces, así que el marcador no se puede quitar con confianza ni
mantener como está sin saber qué se está midiendo.

**No se toca en la Fase 2.** Ponerlo `strict=True` lo volvería un fallo intermitente en CI (peor que
el estado actual), y quitarlo afirmaría que el leak está arreglado, que no está demostrado. La acción
correcta es determinar si la causa es el detector (`tests/leakcheck.c`) o la ruta de código, y eso
pertenece a la Fase 6 (determinismo de la suite), junto con los otros tests inestables ya
registrados en el item 1.14.

**Conteo de tests inestables conocidos: 3** (los dos del item 1.14 más este).

---

## §4. Verificación

### §4.1 Estado final medido

| Métrica | Antes de la Fase 2 | Después |
|---------|--------------------|---------|
| Conflictos shift/reduce del grammar | 188 | **188** (sin cambio; ver §3.2) |
| Módulos de la stdlib que fallan `pengu check` | 0 | **0 / 52** |
| W0005 en la stdlib | 50 | **0** |
| Bloques `pengu` de `LANGUAGE.md` que compilan | 33 / 104 | **35 / 105** (se retiró el 59, se añadió 1 ejemplo) |
| Afirmaciones documentales refutadas (§18.1) | 23 | **24** |
| Tests nuevos de la Fase 2 | – | **+252** en 6 archivos |
| Suite completa | 2178 passed, 0 failed | **2426 passed, 0 failed**, 1 xpassed inestable (§3.5) |

### §4.2 Regla C2 (cada test falla al revertir su fix)

Verificado explícitamente en los tres casos donde es comprobable:

| Test | Cómo se verificó |
|------|------------------|
| `test_num_does_not_grant_equality` / `..._ordering` | Sin la tabla `CONCEPT_OPERATORS`, ambas comprueban que el código viejo **aceptaba** `T: Num` con `==`/`<` |
| `test_documented_bounds_block_matches_the_code_table` | Añadir `eq` a la línea `Num` del doc → 2 tests fallan |
| `test_alias_in_concept_is_not_implemented` | Añadir `\| "alias" NAME _NEWLINE` a `concept_method` → el tripwire falla |
| `test_documented_spelling_emits_the_documented_ctype[double]` | Declarar `float: float, f32, double` → 3 tests fallan |

### §4.3 Regla C1 (ningún test aprueba una propiedad inspeccionando texto)

Los 252 tests nuevos de la Fase 2 (`test_precedence.py` 99, `test_concept_bounds_matrix.py` 84, `test_docs_primitive_types.py` 36, `test_derive_matrix.py` 14, `test_variadics_and_identifiers.py` 12, `test_docs_bounds_sync.py` 7):
- **compilan** el programa y afirman sobre el **código de diagnóstico** (`E0005`, `E0049`, `E0000`),
  o
- **ejecutan** el programa y comparan enteros, o
- comparan **estructuras** (el árbol sintáctico, la tabla de mappings extraída por `ast`).

Ninguno hace `assert "algo" in source` ni lee el mensaje de un warning como sustituto de una
propiedad. El caso más cercano —`test_derive_imago_emits_a_clone_callback`— afirma sobre el **C
emitido** (`_pengu_clone_I`), que es una salida del compilador, no una afirmación documental.

### §4.4 Verificación de la stdlib

Barrido de los 52 módulos con `pengu check --entry`, ejecutado tras **cada** cambio a `std/`:

```
modules with errors : 0 / 52
W0005               : 0
```

`tests/test_stdlib.py` (31 tests) y `tests/test_stdlib_programs.py` en verde.

---

## §5. Lecciones de método (para las fases siguientes)

1. **Un regex no es una medición.** Tres veces en esta fase un barrido por regex produjo un falso
   positivo o negativo que la compilación desmintió:
   * `>` sobre el índice entero `i` se leyó como comparación sobre `T`;
   * los métodos anidados en bloques `enchanting` no se visitaban, así que 12 sitios reales de
     E0049 quedaron invisibles;
   * el número de W0005 dependía del punto de entrada, así que "29" y "20" eran ambos correctos y
     ambos engañosos.
   **Medir con el compilador, no con `grep`.**

2. **Un parche masivo necesita autoverificación por unidad.** El renombrado de los 20 locales de
   W0005 produjo 11 módulos rotos en el primer intento y 2 más en el segundo. Lo que funcionó fue
   re-verificar el módulo después de **cada** edición y revertirla si rompía algo. Sin ese guard, el
   resultado era peor que el problema.

3. **Un local puede colisionar con un campo de la misma rune y con un local hermano del siguiente
   `weave`.** El ámbito del renombrado es el cuerpo del `weave`, no "el resto del archivo".

4. **Un cambio de grammar puede romper la stdlib con la suite en verde.** §3.2. El gate que lo
   detecta es compilar los 52 módulos, y no existe en CI.

5. **El roadmap puede quedarse corto describiendo el defecto.** En 2.3 el roadmap decía "ejemplo
   obsoleto"; la realidad era "afirmación falsa de que compila". Vale la pena compilar siempre la
   afirmación antes de decidir el arreglo.
### §3.6 Item 2.4: dos mediciones más, y por qué sigue en 188

Tras el revert de §3.2 se midió **qué regla posee cada conflicto**, que es la vista accionable (antes
solo se había medido por terminal):

| Regla | Conflictos |
|-------|-----------|
| `return_stmt` | **45** |
| `bool_and_expr` | 18 |
| `normal_target` | 12 |
| `bit_add` | 9 |
| `list_try_expr` | 9 |
| `with_target` | 6 |
| `bit_shift` | 6 |
| `calling_expr` | 6 |
| `comparison` | 6 |
| `range_expr` | 5 |
| `dotted_path` | 5 |
| `custom_type` | 5 |
| (otras 26 reglas) | 60 |

**Total: 188 conflictos repartidos en 38 reglas.** La familia dominante no es la cascada de
expresiones, es **`return_stmt`**:

```
return_stmt: "return" [value_expr] [_NEWLINE]
```

Los 45 conflictos son con los terminales que pueden **iniciar** una expresión (`INT`, `LPAR`,
`CALLING`, `TRY`, `IF`, `NOT`, `-`, …) más `_NEWLINE`. La causa es estructural: con el `[_NEWLINE]`
final opcional, tras leer `return` el parser puede

* **reducir** `return_stmt` ya (tratando `[value_expr]` y `[_NEWLINE]` como ausentes), o
* **desplazar** para empezar una `value_expr`.

Ambas opciones son viables para todo terminal que pueda comenzar una expresión, y el `_NEWLINE`
opcional añade el mismo problema en el otro extremo. `simple_stmt` tiene la forma gemela
(`"return" [expr] -> return_simple`), así que cualquier arreglo tiene que tocar las dos.

**Qué haría falta.** El `_NEWLINE` final opcional es la raíz, en toda su familia (`return_stmt`,
`expr_stmt`, `var_decl`, `let_decl`, `const_decl` — 11 conflictos de `_NEWLINE` en total). Quitarlo
obliga a que el bloque consuma el separador, lo que es un cambio de forma del grammar con efecto en
todas las sentencias: es exactamente el tipo de cambio que C4 manda hacer por familias y con la
suite verificada por commit, y no cabe en el presupuesto de esta fase junto con 2.1–2.12.

**Segunda medición: la cascada `_no_cast` duplicada.** El bloque
`logic_or_no_cast`/`logic_and_no_cast`/`bit_xor_no_cast`/`bit_shift_no_cast`/`bit_add_no_cast`
duplica cinco niveles de la cascada canónica. Se sustituyó por una versión que reutiliza los niveles
canónicos (`bit_add` hacia abajo) y conserva `unary_no_cast`/`bit_mul_no_cast`, que sí hacen falta
porque `transmute X to T` no puede dejar que `X` se coma el cast:

```diff
-?expr_no_cast: logic_or_no_cast (("=="|"!="|"<="|">="|"<"|">") logic_or_no_cast)*
-?logic_or_no_cast: ... ?logic_and_no_cast ... ?bit_xor_no_cast ... ?bit_shift_no_cast ... ?bit_add_no_cast ...
+?expr_no_cast: bit_and_no_cast (("=="|"!="|"<="|">="|"<"|">") bit_and_no_cast)*
+?bit_and_no_cast: bit_and_no_cast "&" bit_mul_no_cast -> bitwise_and | bit_mul_no_cast
```

**Resultado: 188 → 188.** Los 5 niveles duplicados **no contribuían ni un conflicto**, y los 13 AST
de referencia quedaron idénticos. El cambio se revirtió por no aportar nada: reducir reglas sin
reducir conflictos es refactorización sin beneficio, y el coste de mantener la divergencia es real.
Esto desmiente la hipótesis del roadmap de que "colapsar las 29 reglas duplicadas" bajaría el
contador: **el contador lo dominan `return_stmt` y `bool_and_expr`, no las reglas duplicadas.**

> **Corrección al roadmap.** El item 2.4 dice "tabla de precedencia explícita + colapsar las 29
> reglas duplicadas", y presenta ambas como la vía para que `strict=True` construya. La medición
> dice que la tabla de precedencia no es la palanca principal (el parser ya resuelve por *shift* de
> forma consistente, y el test de precedencia de `b9807e4` lo fija) y que las reglas duplicadas no
> aportan conflictos. La palanca real es **el `_NEWLINE` opcional de las sentencias**, empezando por
> `return_stmt` (45 conflictos, 24 % del total).

---

## §3.7 Item 2.5: decisión de la sintaxis de rango (C3)

### Medición

| Comprobación | Resultado |
|---|---|
| `to` en `std/` | **5139** usos |
| `..` **sintáctico** en `std/` | **0** (las 191 apariciones textuales son comentarios tipo `1..12`, strings, o `...`) |
| `..` en `LANGUAGE.md` | 1, etiquetado *"alternate range syntax"* |
| `for i in 1..5` | ✅ compila |
| `xs at 0..2` | ❌ **`E0005`**: infiere `range of int`, no un slice |
| `xs at 0 to 2` | ✅ compila |

### Diagnóstico

El defecto real no era "hay dos sintaxis". Era que **la sintaxis alterna solo era alterna en algunas
posiciones**: `..` funcionaba en `for ... in` pero no en un slice, donde producía un `range of int`
en lugar de un slice. Un usuario que leyera "alternate range syntax" y escribiera `xs at 0..2`
obtenía un error de tipos.

### Decisión

**`to` es canónica**; `..` sigue funcionando durante 1.x y emite **`W0013 RangeSyntaxDeprecated`**,
que es lo que permite eliminarla en 2.0 sin romper en silencio.

| Alternativa | Coste | Por qué se descartó |
|---|---|---|
| **A — Retirar `..` ya** | S | Rompe la promesa de compatibilidad de 1.x sin aviso previo |
| **B — Deprecar con W0013 (elegida)** | S | Coste cero para la stdlib (0 usos), aviso explícito, ruta de salida en 2.0 |
| **C — Canonizar `..`** | M | Obligaría a reescribir 5139 usos de `to` en la stdlib, sin beneficio |

### Implementación

- **`W0013` se emite en `pengu_infer`, en `range_dotdot`.** Esa regla se alcanza desde *todas* las
  posiciones de rango (`in`, `at`, y expresión desnuda), así que un solo punto de emisión cubre
  todas sin duplicar el diagnóstico. Un primer intento lo puso en el checker y en el inferrer a la
  vez; el checker se retiró para no emitirlo dos veces.
- **`..` ahora sí hace slice.** El grammar liga `at` más fuerte que `..`, así que `xs at 0..2` se
  parsea como `range_dotdot(at_expr(xs, 0), .., 2)`. Tanto `pengu_infer` como `pengu_codegen`
  reconocen esa forma y la tratan como el mismo slice que produce `to`. El codegen comparte **un solo
  emisor** (`_emit_slice_at`) entre las dos sintaxis, así que no pueden divergir.
- **Un intento previo se revirtió:** añadir `..` a la producción `slice_range`. No arreglaba nada
  (seguía produciendo un nodo `range_dotdot`) y además añadía conflictos shift/reduce.

### Dos bugs que encontró el propio test

1. La comprobación de límites del slice miraba **solo el bound final**, así que `xs at 1.5..2`
   pasaba. Ahora recorre todos los operandos de la cadena `at`.
2. El test de equivalencia afirmaba sobre un código de salida que **nunca observaba el resultado del
   bucle** (la comprobación estaba en otro `weave`). Reescrito para comprobar dentro de `main`.

Ambos son ejemplos de la misma regla: un test que no puede fallar no verifica nada.

### Semántica medida

Los rangos son **semiabiertos**: `0 to 5` itera 5 veces y `1 to 5` suma 1+2+3+4 = **10**, no 15. La
primera versión del test asumía 15 y falló por la razón correcta; ahora hay un test dedicado a fijar
la semiepertura en las dos sintaxis.

### Estado

`tests/test_range_syntax.py` (nuevo, 15 tests). C2 verificado: desactivar la emisión de W0013 hace
fallar 2 tests. Docs: fila `W0013` en §22.3 de **ambas** referencias. La versión española del catálogo
de advertencias estaba parada en `W0004` — le faltaban `W0005`/`W0006`/`W0007` enteras; se añaden en
el mismo commit para no repetir la deriva del §3.4.

---

## §3.8 Items 2.6, 2.11: qué es implementable y qué no

### §3.8.1 Item 2.6 — `frozen ref to T` vs `ref to frozen T`: **ya hecho y ya verificado**

El roadmap pedía "una forma documentada; la otra emite error o warning". La medición dice que el
trabajo **ya estaba hecho** y verificado por un test existente:

| Comprobación | Resultado |
|---|---|
| `frozen ref to int` → C | `const int32_t*` |
| `ref to frozen int` → C | `const int32_t*` |
| ¿Son el mismo tipo normalizado? | **Sí** — `RefType(FrozenType(int))` en ambos casos |
| ¿Está documentado? | Sí, `LANGUAGE.md` §9.5 y la tabla de tipos: *"`frozen ref to int` — alias de `ref to frozen int`"* |
| ¿Hay test? | Sí: `tests/test_frozen.py::test_frozen_ref_normalises_to_ref_to_frozen` compara **identidad estructural** (`sweet == canonical`), no texto |
| ¿`frozen` sigue siendo palabra clave blanda? | Sí — `var frozen as int` compila |

**Conclusión:** se elige la forma canónica **`ref to frozen T`** (la que califica el *pointee*, que es
lo que `const` significa en C) y `frozen ref to T` queda como azúcar documentada y verificada. No hay
nada que implementar; el item se cierra como **ya satisfecho**, con la evidencia anterior.

### §3.8.2 Item 2.11 — los tres warnings: **ninguno es implementable como se especificó**

Los tres se midieron antes de escribir código, y los tres chocan con algo estructural.

#### `W0011 EmptyTestBody` — ⛔ **inalcanzable por el grammar**

El roadmap dice que *"`test "name":` con cuerpo vacío pasa silenciosamente"*. **Es falso.** La
producción es

```
test_decl: "test" (string_token | NAME) ":" _NEWLINE _INDENT stmt+ _DEDENT
```

con `stmt+`, es decir **al menos una sentencia**. Un cuerpo vacío (o con solo un comentario) es un
error de sintaxis:

```
$ pengu check t.pengu
t.pengu:3:14 [E0000] Syntax error at line 3, column 14
```

No hay estado "cuerpo vacío" que avisar. Implementarlo requeriría **relajar el grammar** (`stmt*`)
para crear la condición que el warning reporta — es decir, añadir un error para luego avisar de él.
Eso es exactamente lo contrario de lo que pide la Fase 2 ("coherente y honesto con lo documentado").

**Corrección al roadmap:** la afirmación de que un `test` vacío "pasa silenciosamente" es
**❌ REFUTADA**. El bloque `test` vacío nunca compiló.

#### `W0008 UnusedImport` — ⛔ **requiere procedencia de símbolos, que no existe**

Medición ingenua sobre la stdlib (¿se menciona el nombre del módulo en otro sitio del archivo?):

```
total imports en std/: 73
sin mención textual del nombre del módulo: 69
```

**69 de 73.** Pero son **falsos positivos**: la stdlib importa un módulo y llama a sus weaves **sin
cualificar**. `archivum` importa `std.spark` y usa `calling println`, no `calling spark.println`.

La causa es arquitectónica: todos los módulos se recogen en **una tabla de símbolos compartida**, y
no se registra de qué módulo vino cada símbolo. Sin esa procedencia, "¿se usó este import?" no tiene
respuesta: el nombre desnudo podría venir de cualquier módulo o del propio archivo.

Un W0008 con esa tasa de falsos positivos sería peor que no tenerlo — es la misma trampa que el
roadmap propone como *"M"* y que en realidad necesita:
1. registrar la procedencia en `Symbol` al recolectar cada módulo,
2. contar referencias resueltas por módulo y por archivo,
3. resolver los casos de re-exportación y de uso solo en posición de tipo.

Es un cambio de la tabla de símbolos, no un `warning` nuevo. **Diferido a 1.1**, y registrado como el
motivo por el que el criterio "0 warnings propios" de la fase **no puede** incluir W0008 hoy.

#### `W0012 DeprecatedAliasUse` — ⚠️ **el mecanismo existe, pero la stdlib nunca lo usa**

El roadmap describe los alias de `tally` (`average`, `argmin`, `argmax`, `filter_range`) como
*"alias `@deprecated` sin warning efectivo en la práctica"*. La medición precisa el problema: **no son
alias `@deprecated` en absoluto.** Lo que tienen es un **docstring**:

```pengu
    ## @deprecated Use `mean` instead.
    ##
    ## Alias de `mean`.
    weave average into T:
```

La anotación real `@deprecated("...")` **sí funciona**:

```
$ pengu check at.pengu
  Warning at.pengu:0:0 [W0006] Symbol 'old_way' is deprecated: Use new_way instead
```

El defecto es una **divergencia entre lo que el docstring afirma y lo que el símbolo declara**: el
comentario dice `@deprecated`, el atributo no está. Un lector (o un editor) ve la promesa; el
compilador no tiene nada que emitir.

**No se implementa en esta fase, y a propósito.** Convertir esos docstrings en atributos `@deprecated`
reales hace que `W0006` empiece a dispararse en **cada llamada** a esos alias — incluidos los tests y
la propia stdlib, que hoy los usa. Eso convierte un defecto documental en ~N nuevos warnings y hace
fallar el criterio 6 de la fase ("0 warnings propios") sin haber arreglado nada de fondo: los alias
seguirían existiendo y el código que los llama seguiría necesitando migrarse.

La acción correcta tiene dos pasos y el segundo es una migración, no un warning: (1) decidir si los
alias se quedan (entonces se marcan y se migran sus llamadas), o (2) se retiran (entonces el problema
desaparece). **Diferido a 1.1.**

### Resumen de 2.11

| Warning | Estado | Razón |
|---|---|---|
| `W0008 UnusedImport` | ⏸️ diferido a 1.1 | Necesita procedencia de símbolos; 69/73 falsos positivos con el enfoque directo |
| `W0011 EmptyTestBody` | ❌ **REFUTADO** | El grammar exige `stmt+`; un `test` vacío es `E0000`, nunca pasó en silencio |
| `W0012 DeprecatedAliasUse` | ⏸️ diferido a 1.1 | El mecanismo (`@deprecated`/`W0006`) funciona; la stdlib solo tiene docstrings. Activarlo es una migración, no un warning |

### §3.8.3 El presupuesto de warnings propios: 50 → 12, y por qué no llega a 0

El criterio de "done" de la fase pide `stderr` con **0 warnings propios** en los 52 módulos. El
recuento medido:

| Warning | Antes de la Fase 2 | Después |
|---|---|---|
| `W0005` (shadowing) | 50 | **0** (item 2.12) |
| `W0001` (`transmute` inseguro) | 21 | **12** |
| `W0013` (rango `..`) | — | **0** (la stdlib usa siempre `to`) |
| **Total** | **71** | **12** |

Los 12 `W0001` restantes están en `std/ffi.pengu` (4) y `std/filum.pengu` (8), y **todos** son
conversiones de puntero a `opaque` o a `ref to void`.

#### Lo que sí se arregló: el idioma de NULL

`ffi.pengu` construía punteros NULL con `transmute 0 to ref to X` y los comparaba con
`(transmute p to opaque) == nil`. Eso disparaba `W0001` — incluidas **tres advertencias de
discrepancia de tamaño** (`int` 4 bytes → puntero 8 bytes) que apuntaban a un problema real: en una
plataforma donde el puntero no sea tan ancho como el tipo del cero literal, la conversión **trunca**.

`null` es la forma correcta, no emite warning y dice lo mismo:

```diff
-    return transmute 0 to ref to void
+    return null
-    var nil as opaque is transmute 0 to opaque
-    if (transmute cstr to opaque) == nil or max_len <= 0:
+    if cstr == null or max_len <= 0:
```

`W0001`: 21 → 12. Los tests de `ffi` y `stdlib` siguen en verde.

#### Por qué los 12 restantes no se pueden quitar hoy

Cada uno es una conversión que el lenguaje **exige** escribir de forma explícita:

```pengu
var oa as opaque is transmute a to opaque          # ref to T  -> opaque
var sl as slice of byte is calling slice_from_ptr of byte with (transmute cstr to ref to void) , max_len
```

Convertir `ref to T` en `opaque` o en `ref to void` **no cambia el tamaño ni la representación**: es
una conversión de puntero a puntero, siempre segura. Que necesite `transmute` es lo que obliga a
escribir un cast inseguro para expresar algo seguro — y por eso `W0001` avisa.

La corrección de fondo es **permitir la conversión implícita de cualquier `ref to T` a `opaque` y a
`ref to void`** (upcast de puntero, como en C). Con eso los 12 `transmute` desaparecen, `W0001`
queda reservado para discrepancias de tamaño **reales**, y el criterio de 0 warnings se cumple solo.

**No se hace en esta fase**, y la razón es la misma que en 2.11: es un cambio del sistema de tipos
con efecto en la resolución de sobrecargas y en la inferencia, no un arreglo de la stdlib. Meterlo
al final de la Fase 2, sin presupuesto para medir su impacto, es exactamente el tipo de cambio que
C3 y C4 existen para evitar.

**Veredicto honesto del criterio 6:** no se cumple al 100 %. Se pasa de **71 a 12** warnings propios
(−83 %), los 12 restantes están localizados, explicados, y su arreglo está identificado y acotado.
Declarar el criterio "cumplido" sería falso; declararlo "imposible" también. Lo correcto es lo que
dice la tabla.

---

## §6. Criterio de "done" de la Fase 2 — evaluación honesta

El roadmap fija seis criterios. Estado medido de cada uno:

| # | Criterio del roadmap | Estado | Evidencia |
|---|----------------------|--------|-----------|
| 1 | Matriz de bounds medida y coherente con la documentación (test paramétrico de 30 pares) | ✅ **cumplido** | `tests/test_concept_bounds_matrix.py`: 84 tests, matriz 12×5; `LANGUAGE.md` §10.9 y `LANGUAGE_Spanish.md` con bloque `bounds-ops` que el test lee |
| 2 | `Lark(..., strict=True)` no lanza en CI | ❌ **no cumplido** | Sigue en 188 conflictos. Es el único criterio que **no** se cumple, y el §3.2/§3.6 documenta por qué y qué haría falta |
| 3 | Los 4 ejemplos documentales que no compilaban (bloques 15, 28, 59, 94) compilan **o** han sido retirados con marca ⏸️ | ✅ **cumplido** | 15, 28 y 94 compilan (Fase 1, B7); el 59 se retiró y §11.7 lo marca ⏸️ con la razón |
| 4 | Una sola sintaxis de rango canónica, con deprecación de la otra | ✅ **cumplido** | `to` canónica; `..` emite `W0013` y además ahora **funciona** en slices; 15 tests |
| 5 | Matriz de `derive` documentada y probada por concept | ✅ **cumplido** | `tests/test_derive_matrix.py`: 14 tests; los 5 derivables verificados por ejecución, los 3 no derivables rechazados con `E0005` |
| 6 | `pengu check --entry std/<mod>.pengu` para los 52 módulos → **0 warnings propios** | ⚠️ **parcial: 71 → 12 (−83 %)** | `W0005` 50→0; `W0001` 21→12. Los 12 restantes están localizados y explicados en §3.8.3 |

### Los dos criterios abiertos, y qué los cierra

**Criterio 2 (`strict=True`).** No es cuestión de esfuerzo sino de alcance. La palanca real está
medida (§3.6): `return_stmt` posee 45 de los 188 conflictos, y su causa es el `_NEWLINE` final
**opcional** compartido por toda la familia de sentencias. Quitarlo es un cambio de forma del
grafo de sentencias, no una tabla de precedencia. El roadmap atribuye la reducción a "tabla de
precedencia + colapsar las 29 reglas duplicadas", y la medición **refuta ambas**: la tabla ya
resuelve por *shift* de forma consistente (y `tests/test_precedence.py` lo fija), y colapsar los 5
niveles `_no_cast` duplicados dio **188 → 188**.

Lo que cierra el criterio es un cambio de familia `_NEWLINE` con la suite verificada por commit,
con el presupuesto de un item **L** propio. Se deja para 1.1 con la medición hecha, que es la parte
cara.

**Criterio 6 (0 warnings).** Los 12 `W0001` restantes son conversiones `ref to T` → `opaque` /
`ref to void`, que son seguras y que el lenguaje obliga a escribir con `transmute`. Quitarlos exige
**permitir el upcast de punteros implícitamente**, un cambio del sistema de tipos (§3.8.3). Con eso
`W0001` queda reservado para discrepancias de tamaño reales y el criterio se cumple solo.

### Lo que la fase sí entrega

- **2.1** bounds coherentes, en **un solo sitio**, con la matriz medida y fijada por test.
- **2.2** documentación de bounds sincronizada y **verificada por test** contra la tabla del código.
- **2.3** una afirmación falsa de la documentación retirada, con *tripwire* contra su reaparición.
- **2.4b** la precedencia y asociatividad fijadas **antes** de tocar el grammar (99 tests).
- **2.5** una sintaxis de rango canónica, con deprecación y con el bug real (`..` no hacía slice)
  arreglado.
- **2.6** verificado: ya estaba hecho, y con test de identidad estructural.
- **2.7** semántica real de `many T` documentada (y el spread declarado ⏸️).
- **2.8** matriz de `derive` medida, documentada y probada.
- **2.9** los identificadores ASCII documentados.
- **2.10** la tabla de primitivos hecha canónica y verificada; **tres defectos corregidos**
  (`float` de 32 bits, `isize` → `intptr_t`, `ssize_t` rama muerta).
- **2.12** `W0005` de 50 a 0.
- **5 afirmaciones documentales más refutadas** compilándolas, no leyéndolas.
- **+270 tests** nuevos, todos por compilación o ejecución (regla C1).

Y lo que deja **honestamente abierto**: 2.4 (con la medición que lo desbloquea), 2.11 `W0008` y
`W0012`, y los 12 `W0001`, cada uno con la razón medida de por qué no cabe aquí.

---

## §7. Item 2.4: la causa raíz encontrada, medida, y por qué no se aplica aún

Después de §3.2 y §3.6 quedaba una hipótesis sin probar: que el `_NEWLINE` **final opcional** de las
sentencias fuera la causa, y que bastara volverlo obligatorio. Se probó, y el resultado es el
hallazgo más útil de todo el item.

### §7.1 El lexer sí emite `_NEWLINE` antes de `_DEDENT`

`PenguIndenter` se apoya en `lark.Indenter.handle_NL`, que hace:

```python
yield token                      # el _NEWLINE, SIEMPRE primero
indent = ...
if indent > self.indent_level[-1]:
    yield Token.new_borrow_pos(self.INDENT_type, ...)
else:
    while indent < self.indent_level[-1]:
        self.indent_level.pop()
        yield Token.new_borrow_pos(self.DEDENT_type, ...)
```

El `_NEWLINE` se emite **antes** de cualquier `_DEDENT`. Eso hacía plausible que el `[...]` fuera
innecesario en todas las sentencias. **Es cierto para la mayoría, pero no para todas.**

### §7.2 Medición regla por regla

Cada cambio aplicado **en aislamiento**, contando conflictos y comprobando las formas de riesgo:

| Regla | `[_NEWLINE]` → `_NEWLINE` | Conflictos | ¿Rompe la stdlib? |
|---|---|---|---|
| `return_stmt` | −45 | **188 → 143** | ⚠️ **Sí** (24 de 52 módulos) |
| `expr_stmt` | ±0 | 188 | — |
| `set_stmt` | ±0 | 188 | — |
| `var_decl` / `let_decl` / `const_decl` | ±0 | 188 | — |

**`return_stmt` es el único que aporta, y aporta mucho**: −45 conflictos, exactamente los 45 que §3.6
le había atribuido. Los demás no aportan nada, lo cual desmiente la idea de que "el `_NEWLINE`
opcional de la familia de sentencias" fuera un bloque homogéneo.

### §7.3 El caso que lo bloquea: `return` con una expresión multilínea

Con `return_stmt: "return" [value_expr] _NEWLINE`, esto deja de parsear:

```pengu
weave bool_to_string with b as bool into string:
    return judge b:
        when true -> "true"
        when false -> "false"
```

```
std/spark.pengu:74:30 [E0000] Syntax error at line 74, column 30
```

**24 de los 52 módulos** fallan, todos por la misma razón. La causa es precisa: `judge_expr` es una
expresión **terminada en bloque**:

```
judge_expr: "judge" expr ":" _NEWLINE _INDENT when_clause+ [else_clause] _DEDENT
```

Termina en `_DEDENT`, y **no consume un `_NEWLINE` después** (el `_DEDENT` ya lo precede). Así que
`return <expresión-terminada-en-bloque>` no tiene `_NEWLINE` final que consumir, y volverlo
obligatorio lo rompe.

> **Por qué el corpus de tests no lo detectó al principio.** Las pruebas de precedencia y el primer
> barrido de `std/` con el cambio aplicado **sí** lo detectaron (24 módulos), pero el test aislado que
> hice antes de aplicarlo usó `return judge b:` y **falló igual** — es decir, la comprobación funcionó.
> Lo que falló fue mi lectura inicial de §7.2 como "seguro": el −45 es real, pero el cambio **no es
> aplicable tal cual**.

### §7.4 El arreglo correcto, para 1.1

La solución no es aflojar el `_NEWLINE`, sino **separar las dos formas de `return`**, porque tienen
finales distintos:

```
return_stmt: "return" [value_expr] _NEWLINE      # expresión simple: termina en _NEWLINE
           | "return" block_expr                 # expresión terminada en bloque: termina en _DEDENT
```

donde `block_expr` es `judge_expr` (y cualquier futura expresión terminada en `_DEDENT`). Con eso el
parser sabe **antes** de consumir el separador cuál de las dos formas está leyendo, y los 45
conflictos desaparecen sin tocar la semántica.

**Lo que falta para hacerlo:** identificar el conjunto exacto de expresiones terminadas en bloque
(hoy `judge_expr`; hay que verificar `do_expr`, `when_expr` y las lambdas multilínea), y medir el
efecto en `simple_stmt`, que tiene la forma gemela. Es un cambio de la forma del grafo de sentencias
con presupuesto propio, no el ajuste de una línea que parecía.

**Estado:** ⏸️ para 1.1, con la causa raíz identificada y el arreglo especificado. El contador sigue
en **188**, y el criterio 2 de la fase sigue sin cumplirse. Se deja medido y no aplicado: entregar un
grammar que rompe 24 de 52 módulos para presumir de un número menor sería exactamente lo contrario de
lo que pide esta fase.
