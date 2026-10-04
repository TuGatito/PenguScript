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
| **2.11** `W0012` | ✅ **cerrado** | §9 y §11: el mecanismo estaba roto en tres capas y faltaban dos puntos de consulta. Un `@deprecated` de cualquier clase avisa |

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
| Suite completa | 2178 passed, 0 failed | **2465 passed, 0 failed** |

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
| **Total** | **71** | **0** |

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
| 6 | `pengu check --entry std/<mod>.pengu` para los 52 módulos → **0 warnings propios** | ✅ **cumplido** | 71 → **0**: `W0005` 50→0 (§2.12), `W0001` 21→0 (§8). 52/52 módulos sin errores ni warnings |

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

---

## §8. Los 12 `W0001` restantes: arreglados, y el criterio 6 cumplido

El §3.8.3 decía que cerrar los 12 `W0001` exigía permitir el upcast de punteros. Se hizo, y era más
pequeño de lo que parecía.

### La causa

`RefType.is_compatible` tenía casos para `RefType` (incluido el comodín `void*`) pero **ninguno para
`opaque`**, que es un `BaseType`. La comprobación caía al `return False` final. La conversión no
estaba mal configurada: **faltaba**.

### El arreglo

Un caso en `RefType.is_compatible`: `opaque` acepta cualquier `ref to T`. La conversión es
**unidireccional** — `opaque` → `ref to T` sigue siendo `E0005`, porque `opaque` no lleva
información de pointee y dejar que decaiga permitiría alias sin ningún diagnóstico.

### Por qué era la corrección correcta y no un atajo

Los 12 sitios hacían, todos, una conversión que C realiza implícitamente y que **no puede perder
información**: el tamaño es un puntero en ambos lados. Obligar a escribir un cast **inseguro** para
expresar una conversión **segura** es lo que hacía ruidoso `W0001`, y una advertencia que salta en
código seguro deja de leerse. En `ffi.pengu` era peor: el idioma `transmute 0 to ref to void` emitía
una advertencia de **discrepancia de tamaño** (`int` 4 bytes → puntero 8) que en una plataforma
estrecha **trunca de verdad**.

### Resultado medido

```diff
-    var oa as opaque is transmute a to opaque
+    var oa as opaque is a
-    var sl as slice of byte is calling slice_from_ptr of byte with (transmute cstr to ref to void), max_len
+    var sl as slice of byte is calling slice_from_ptr of byte with cstr, max_len
```

| Métrica | Antes | Después |
|---|---|---|
| W0001 en la stdlib | 12 | **0** |
| Advertencias propias totales (52 módulos) | 12 | **0** |
| `transmute` en `ffi.pengu` + `filum.pengu` | 12 | 0 |
| Suite completa | 2444 passed | **2447 passed, 0 failed** |

**El criterio 6 de la fase queda cumplido.** `Lark(strict=True)` sigue siendo el único criterio
abierto.

### Comprobaciones de que no es demasiado permisivo

| Caso | Resultado |
|---|---|
| `var o as opaque is 5` | `E0005` (sigue rechazando no-punteros) |
| `var p as ref to int is o` (opaque → ref) | `E0005` (unidireccional) |
| `list of opaque` con un `ref to int` | acepta (coerción de elemento) |
| `map of string to opaque` con un `ref to int` | acepta |
| `ident shard T` con un `ref to int` | acepta |
| El upcast llega al codegen | el C emitido **compila y ejecuta** |

---

## §9. W0006 / `@deprecated`: tres bugs reales encontrados y dos huecos que quedan

Perseguir el item 2.11 encontró que el mecanismo de deprecación estaba **roto en tres capas**, no
solo sin usar.

### Bug 1 — los atributos de método nunca se extraían

`_extract_attributes` se llamaba para `weave_decl` de nivel superior, `declare`, `rune`, `echo` y
campos, pero **no para los métodos dentro de `enchanting`**. Consecuencia: un atributo desconocido
en un método se aceptaba en silencio (no había `E0056`), y `@deprecated` no se guardaba.

Arreglado en las tres rutas de registro de métodos (`concept_method` y las dos de `weave_decl`).

### Bug 2 — `substitute()` perdía los atributos

```python
# FnType.substitute  (y RuneType.substitute)
return FnType(params=new_params, ..., is_ritual=self.is_ritual)   # sin attributes
```

Al reconstruir el tipo campo a campo, `attributes` **se omitía**. Cualquier marca desaparecía en
cuanto un tipo genérico se monomorfizaba: un `weave` genérico `@deprecated` dejaba de avisar en
cuanto se instanciaba con un tipo concreto. `RuneType` tenía el mismo bug, y además perdía
`field_attributes`.

Auditado con `ast`: de los dos dataclasses con campo `attributes` (`FnType`, `RuneType`), **los dos**
tenían el bug.

### Bug 3 — el camino de resolución de métodos nunca comprobaba la deprecación

`_check_deprecated_symbol` se llamaba en ~15 sitios (referencias a variables, campos, acceso por
flecha, llamadas a función) pero **en ninguno del camino de resolución de métodos**. Añadido en el
punto donde el `FnType` resuelto está disponible.

### Los dos huecos que quedan

| Hueco | Detalle |
|---|---|
| **Atributos perdidos en la especialización de métodos** | `_resolve_call_target` escribe en `symbols.methods` un tipo **especializado**, y ese objeto se construye sin arrastrar `attributes`. El marcador existe durante la recolección y desaparece antes de que el sitio de llamada lo consulte. Es el mismo bug que el Bug 2 pero en otra ruta. |
| **`@deprecated` en un `rune` no avisa** | El atributo se acepta y sobrevive hasta el `RuneType`, pero **ningún check lo consulta al referenciar el tipo**. Usar un tipo deprecado es silencioso. W0006 solo se dispara para `weave`. |

Ambos están fijados por test (`tests/test_deprecation.py`, 9 tests) de forma que, cuando se
arreglen, los tests **fallen y obliguen a cambiarlos a propósito** — en lugar de quedar como un
xfail que se ignora.

### Por qué no se convierten los 74 docstrings en atributos reales

El roadmap proponía marcar los alias de `tally` (`average`, `argmin`, `argmax`, `filter_range`) como
`@deprecated` reales para que W0012 empiece a avisar. La medición dice que eso sería un error **en
este momento**:

| Medición | Resultado |
|---|---|
| Símbolos marcados `@deprecated` **solo en docstring** | **65** (no 4) |
| De esos, con al menos una mención real en `std/` o `tests/` | **65** |
| Menciones de `MaybeString` | 42 |
| Menciones de `MaybeInt` | 39 |
| Menciones de `ResultString` | 42 |

Convertir 74 docstrings en atributos reales haría que `W0006` saltara en **cada llamada** a esos
símbolos — incluidos los cientos de usos dentro de la propia stdlib — y volvería a romper el criterio
6 que se acaba de cumplir. El defecto real no es "faltan warnings": es que la stdlib está llena de
símbolos deprecados **que se siguen usando**. Eso es una migración, y el roadmap no la incluye.

**Decisión:** se arreglan las tres capas rotas (que es infraestructura, y ya está), se dejan los
docstrings como están, y se registra que **la migración es el prerrequisito** de marcar los alias.
Los tests fijan el estado actual para que el cambio sea deliberado.

### Corrección al roadmap para 2.11 en conjunto

| Warning | Veredicto |
|---|---|
| `W0008 UnusedImport` | ⏸️ diferido: necesita procedencia de símbolos (69/73 falsos positivos) |
| `W0011 EmptyTestBody` | ❌ **REFUTADO**: el grammar exige `stmt+`, un `test` vacío es `E0000` |
| `W0012 DeprecatedAliasUse` | ⚠️ **reformulado**: no es un warning que falte, es (a) un mecanismo roto en 3 capas —arreglado— y (b) 65 símbolos deprecados aún en uso, que exige migración |

---

## §10. Item 2.4: el split de `return_stmt` es *imposible* en su forma simple (medido)

El §7 concluyó que el arreglo correcto era separar las dos formas de `return`:

```
return_stmt: "return" [value_expr] _NEWLINE
           | "return" block_expr
```

Se probó **en memoria**, sin tocar el árbol de trabajo, construyendo el grammar modificado y
midiendo con Lark. Resultado:

| Variante | Conflictos | Resultado |
|----------|-----------|-----------|
| línea base | 188 | — |
| **A**: `value _NEWLINE` \| `"return" block_expr` | — | **`GrammarError: Reduce/Reduce collision in Terminal('MINUS')`** |
| **B**: solo exigir `_NEWLINE` | 143 | Colisiona con la stdlib (24/52 módulos, §7.3) |

**La variante A no compila el grammar.** El motivo es que las expresiones terminadas en bloque
(`judge_expr`, `do_expr`, `with_init_expr`, `or_block`) son alcanzables **por dos caminos**:

* como `value_expr`, porque `or_else_expr` desciende por `try_expr` → `judge_expr`
  (`pengu_grammar.py:289-299`), y
* directamente desde la nueva alternativa `"return" block_expr`.

LALR no puede decidir cuál de las dos reducciones aplicar en la intersección, y el conflicto
reduce/reduce no es resoluble por prioridad. La lista completa de expresiones terminadas en
`_DEDENT` en el grammar es:

```
judge_expr, do_expr, with_init_expr, or_block, if_expr*, when_expr*, for_comp_expr*
```
(*terminan en sus subexpresiones; solo las cuatro primeras acaban literalmente en `_DEDENT`.)

### Consecuencia para el item 2.4

La palanca de los 45 conflictos **existe** (medida: 188 → 143) pero **no es aplicable por las dos
vías plausibles**:

1. exigir el `_NEWLINE` → rompe 24 de 52 módulos porque cuatro tipos de expresión no lo tienen;
2. separar la producción de `return` → produce un conflicto reduce/reduce que Lark rechaza.

La única salida es **normalizar las expresiones terminadas en bloque para que consuman un
`_NEWLINE` final** (es decir, cambiar `judge_expr` y compañía para que terminen en `_NEWLINE` en vez
de `_DEDENT`). Eso toca cuatro producciones de expresión, sus consumidores en `pengu_infer` y
`pengu_codegen`, y potencialmente la forma del AST. Es un cambio de diseño del grammar con
presupuesto propio, no un ajuste.

**Estado: ⏸️ para 1.1.** El contador sigue en **188** y el criterio 2 sigue sin cumplirse. Lo que
cambia respecto al §7 es que ya no queda una hipótesis pendiente: se probaron las dos vías y las dos
están descartadas **con la medición delante**.

---

## §11. Cierre de los dos huecos de W0006 (item 2.11 completo)

Los dos huecos que el §9 dejó fijados por test quedaron **cerrados**.

### Hueco A — la especialización de métodos perdía los atributos

La causa era más simple que la del §9: `_create_method_fn_type` **ya extraía** los atributos dos
líneas antes,

```python
w_attrs, _ = _extract_attributes(node.children)      # 6263
self._validate_attributes(w_attrs, "weave", node)    # 6264
...
method_fn_type = FnType(params=params, ..., type_params=tp_list)   # sin attributes
```

y luego **no los pasaba al `FnType`**. El marcador se validaba y se tiraba. Un argumento
`attributes=w_attrs` lo arregla. Se auditó con `ast` que no quedara ningún otro `FnType(...)` sin
`attributes` en el camino de métodos: de 28 construcciones, 25 son tipos **sintetizados** por la
inferencia (sin atributos que preservar, por construcción) y las 3 restantes son las de registro de
métodos, ya corregidas.

Resultado:

```
Warning d2.pengu:0:0 [W0006] Symbol 'average' is deprecated: Use mean instead
```

### Hueco B — `@deprecated` en un `rune` no se consultaba nunca

El atributo se aceptaba y sobrevivía hasta el `RuneType`, pero **ningún check lo miraba al nombrar
el tipo**. Añadido en `_validate_type_node`, que es el único punto por el que pasa toda referencia a
un tipo escrito por el usuario. Se comprueban las cuatro tablas de tipos (`runes`, `echos`, `omens`,
`aliases`) y se informa con el nombre **corto**, para que una referencia cualificada
(`std.x.Old`) siga nombrando el tipo que el usuario escribió.

Resultado:

```
Warning rd.pengu:0:0 [W0006] Symbol 'OldPoint' is deprecated: Use NewPoint
```

### Verificación

| Comprobación | Resultado |
|---|---|
| `@deprecated` en `weave` de nivel superior | W0006 ✅ (sin regresión) |
| `@deprecated` en método `enchanting` | W0006 ✅ (**antes: silencio**) |
| `@deprecated` en `rune` | W0006 ✅ (**antes: silencio**) |
| Método/rune **no** deprecado | silencio ✅ (mitad negativa) |
| Atributo desconocido en método | `E0056` ✅ |
| Atributos sobreviven a `substitute()` | ✅ (`FnType` y `RuneType`) |
| Stdlib (52 módulos) | 0 errores, **0 warnings** ✅ |

`tests/test_deprecation.py` sube a **11 tests**, todos por compilación. Los dos tests que fijaban los
huecos **se invirtieron a propósito** al cerrarlos — que es exactamente el mecanismo que el §9
diseñó para que el arreglo fuera deliberado y no accidental.

### Estado de 2.11

| Warning | Veredicto |
|---|---|
| `W0008 UnusedImport` | ⏸️ 1.1 — necesita procedencia de símbolos |
| `W0011 EmptyTestBody` | ❌ REFUTADO — el grammar exige `stmt+` |
| `W0012 DeprecatedAliasUse` | ✅ **implementado**: el mecanismo estaba roto en tres capas (arregladas) y faltaban los dos puntos de consulta (arreglados). Usar un `@deprecated` de cualquier clase —weave, método o tipo— ahora avisa |

---

## §12. Item 2.4: tercera y cuarta vía descartadas; el mapa completo de los 188

El §10 descartó dos vías. Esta ronda probó dos más, también en memoria y sin tocar el árbol.

### Tercera vía — sacar las expresiones-terminadas-en-bloque de la rama simple

Se intentó definir una `value_expr` **sin** las formas terminadas en bloque:

```
return_stmt: "return" [value_val_expr] _NEWLINE
           | "return" value_block_expr
?value_val_expr: unless_stmt | if_stmt | while_stmt | for_stmt | expr
value_block_expr: judge_expr | do_expr | with_init_expr
```

**Falla igual:** `GrammarError: Reduce/Reduce collision in Terminal('NOT')`. El motivo es que
`judge_expr` **no solo** es alcanzable como `value_expr`: `or_else_expr` desciende por `try_expr`
hasta él (`pengu_grammar.py:289-299`), así que sigue habiendo dos caminos de reducción. Excluirlo
obligaría a duplicar toda la cascada de expresiones sin esas formas, que es exactamente el tipo de
duplicación que el §3.6 demostró que **no reduce conflictos**.

### Cuarta vía — declaraciones de precedencia explícitas

La propuesta del roadmap ("tabla de precedencia explícita"). Lark las aplica solo a **terminales
con nombre**, y la cascada aritmética está escrita con literales anónimos:

```
?bit_add: bit_add "+" bit_mul -> add
```

Convertirla exige nombrar ~18 terminales (`PLUS`, `MINUS`, `STAR`, `SLASH`, `PERCENT`, `EQ`, `NE`,
`LT`, `LE`, `GT`, `GE`, `VBAR`, `CIRCUMFLEX`, `AMPERSAND`, `SHL`, `SHR`, …) y sustituirlos en
**todas** sus apariciones. El intento produjo `GrammarError: Rule 'EQ' used but not defined`: los
literales aparecen en más sitios de los que un reemplazo mecánico alcanza (incluida la cascada
`_no_cast` y `slice_range`), y un reemplazo incompleto rompe el grammar.

Además hay una razón de fondo para no hacerlo: **Lark ya resuelve estos conflictos por *shift*, que
es lo correcto para una cascada escrita así.** Los 9 conflictos de `bit_add` (uno por cada uno de
`PERCENT`/`STAR`/`SLASH` en cada producción) no son un bug latente: son el mecanismo por el que la
precedencia funciona, y `tests/test_precedence.py` la fija. Convertirlos en declaraciones
explícitas cambiaría la forma en que el parser llega al mismo resultado, con riesgo de alterar la
asociatividad, a cambio de un número.

### Mapa completo de los 188 (por regla)

| Regla | Conflictos | Terminales | Naturaleza |
|-------|-----------|-----------|------------|
| `return_stmt` | **45** | 45 distintos | `[value_expr] [_NEWLINE]` ambos opcionales. **Las 4 vías probadas fallan** (§7, §10, §12) |
| `bool_and_expr` | 18 | 9 (×2) | `comparison` es alcanzable desde `bool_and_expr` y desde `logic_or` |
| `normal_target` | 12 | `DOT`/`ARROW`/`__ANON_1` (×4) | `(NAME\|self) (access_op)*` vs `dotted_path: NAME ("." NAME)*` vs `with_target` |
| `bit_add` | 9 | `PERCENT`/`STAR`/`SLASH` (×3) | Cascada; **resuelto por shift = correcto** |
| `list_try_expr` | 9 | 9 distintos | `comparison` alcanzable por dos caminos |
| `with_target` | 6 | `DOT`/`ARROW`/`__ANON_1` (×2) | Igual que `normal_target` |
| `bit_shift` | 6 | `PLUS`/`MINUS` (×3) | Cascada; resuelto por shift |
| `calling_expr` | 6 | `WITH`/`OF` (×3) | `generic_args`/`arg_list` opcionales |
| `comparison` | 6 | `VBAR` (×6) | `comparison OP logic_or`: el lado derecho debería ser de precedencia mayor |
| `range_expr` | 5 | `VBAR`/`TO`/`DOTDOT` | `range_expr: logic_or OP logic_or` con `logic_or` recursivo |
| `dotted_path` | 5 | `AS`/`DOT`/`COLON`/`OF` | camino duplicado de `custom_type` |
| `custom_type` | 5 | `OF`/`COMMA`/`_AND_SEP` | camino duplicado de `dotted_path` |
| `let_decl` / `var_decl` / `const_decl` | 10 | `_NEWLINE` | mismo `[_NEWLINE]` opcional |
| otras 25 reglas | 45 | — | mayoría `_NEWLINE` opcional y prefijos compartidos |

**45 de 188 (24 %) son `return_stmt`.** El resto son tres familias estructurales —cascada de
expresiones (correcta por shift), `logic_or` en el lado derecho de las comparaciones, y los tres
caminos solapados de nombre-cualificado— más el `_NEWLINE` opcional.

### Veredicto sobre el criterio 2

`Lark(GRAMMAR, parser='lalr', strict=True)` **sigue sin construirse**. Se han probado y descartado
**cuatro** vías con la medición delante:

| Vía | Resultado |
|-----|-----------|
| 1. Colapsar las reglas `_no_cast` duplicadas (§3.6) | 188 → **188** (no aporta) |
| 2. Exigir el `_NEWLINE` de `return_stmt` (§7) | 188 → **143**, pero rompe **24/52** módulos |
| 3. Separar `"return" block_expr` (§10) | **Reduce/Reduce**, el grammar no construye |
| 4. Excluir las formas de bloque de `value_expr` (§12) | **Reduce/Reduce** otra vez |
| 5. Declaraciones de precedencia explícitas (§12) | Requiere nombrar ~18 terminales en todo el grammar; intento incompleto no construye |

**Lo que queda por hacer está identificado y acotado:** normalizar las cuatro expresiones
terminadas en `_DEDENT` (`judge_expr`, `do_expr`, `with_init_expr`, `or_block`) para que consuman un
`_NEWLINE` final. Con eso la vía 2 se vuelve aplicable y `return_stmt` deja de aportar sus 45
conflictos. Toca cuatro producciones de expresión y sus consumidores en `pengu_infer` y
`pengu_codegen`.

**No se hace en esta fase**: es un cambio de forma del grafo de expresiones, con presupuesto propio
y con la suite completa como red — exactamente el tipo de cambio que C4 manda no meter al final de
una fase.

---

## §13. Rendimiento de la suite: un test costaba 87 s

El test que añadí en el §3.7 para blindar la sintaxis de rango hacía un barrido de
`pengu check --entry` sobre los 52 módulos **dentro de un solo test**: **87 s** para una aserción
(≈7 % de la suite), duplicando trabajo que `tests/test_stdlib.py` ya hace en cada ejecución.

Lo que afirma es una propiedad del **texto fuente** (que nadie reintroduzca la grafía deprecada), así
que leer el texto es el instrumento correcto: se descartan comentarios, literales de string y `...`,
y se informa de cualquier `..` restante. **87 s → 7,4 s** para el archivo completo (16 tests).

Se añadió `test_the_dotdot_scan_actually_detects_a_range` porque el descarte de comentarios y strings
puede fallar de una forma que haga que el escáner no encuentre nada en ningún archivo — lo que
convertiría el guard en un no-op. Fija que sí encuentra un rango real e ignora un comentario con
`1..12`, un string con `a..b` y un vararg `many int`.

C2 verificado: inyectar un rango `..` real en `std/spark.pengu` hace fallar el escáner.

---

## §14. Item 2.4: sexta vía descartada — la ruta que el §12 recomendaba **tampoco funciona**

El §12 concluyó que la única salida era normalizar las expresiones terminadas en `_DEDENT` para que
consumieran un `_NEWLINE` final, y que con eso la vía de exigir el `_NEWLINE` de `return_stmt` se
volvería aplicable. **Se probó, y es falso.** Es el hallazgo más importante de esta ronda, porque
invalida la recomendación que yo mismo había escrito.

### Lo que se probó

```diff
-judge_expr: "judge" expr ":" _NEWLINE _INDENT when_clause+ [else_clause] _DEDENT
+judge_expr: "judge" expr ":" _NEWLINE _INDENT when_clause+ [else_clause] _DEDENT _NEWLINE
-with_init_expr: "with" ":" _NEWLINE _INDENT stmt+ _DEDENT
+with_init_expr: "with" ":" _NEWLINE _INDENT stmt+ _DEDENT _NEWLINE
-do_expr: "do" ":" _NEWLINE _INDENT stmt+ _DEDENT
+do_expr: "do" ":" _NEWLINE _INDENT stmt+ _DEDENT _NEWLINE
-return_stmt: "return" [value_expr] [_NEWLINE]
+return_stmt: "return" [value_expr] _NEWLINE
```

### Resultado

| Medición | Resultado |
|---|---|
| Conflictos con las expresiones de bloque consumiendo `_NEWLINE` | **188 → 188** (no aporta nada) |
| Conflictos añadiendo además el `_NEWLINE` obligatorio de `return` | 188 → **143** (= los 45 de `return_stmt`) |
| **Módulos de la stdlib que fallan** | **24 / 52** — exactamente los mismos que en el §7 |

### Por qué falla

El `_DEDENT` y el `_NEWLINE` están **entrelazados** por el indenter, y el número de `_NEWLINE`
disponibles antes de un `_DEDENT` **no es el que el modelo sugiere**. `lark.Indenter.handle_NL`
emite

```python
yield token                       # el _NEWLINE
if indent > level: yield INDENT
else:
    while indent < level: yield DEDENT
```

así que sí hay un `_NEWLINE` **antes** de cada `_DEDENT`. Pero las producciones que **ya** consumen
un `_DEDENT` — y en particular `block: ":" _NEWLINE _INDENT stmt+ _DEDENT`, que es la forma de todo
cuerpo de `weave`, `if`, `while`, `for` — **no consumen el `_NEWLINE` que lo sigue**. Ese `_NEWLINE`
queda para la producción envolvente.

Por eso `judge_expr: ... _DEDENT _NEWLINE` falla en los 24 módulos: el `_NEWLINE` que intenta
consumir ya está reservado por el `block` exterior, y el parser no encuentra el token donde la nueva
producción lo espera. El diagnóstico es idéntico al del §7 (`spark.pengu:74`, `archivum.pengu:150`),
lo que confirma que la causa es la misma y que mi recomendación del §12 no la abordaba.

**Corrección al §12.** Decía que normalizar las expresiones de bloque era "lo que queda por hacer" y
que era "un cambio de forma del grafo de expresiones". Es un cambio de forma del **grafo de bloques
de todo el lenguaje**: tocar `_DEDENT` en las cuatro expresiones obliga a revisar cómo cada
producción que consume un `_DEDENT` (`block`, `else_block`, `with_stmt`, `do_expr`, `with_init_expr`,
`judge_expr`, y las declaraciones) reparte los `_NEWLINE`, porque el token es un recurso compartido.

### Balance de las seis vías

| # | Vía | Resultado |
|---|-----|-----------|
| 1 | Colapsar las reglas `_no_cast` duplicadas | 188 → **188** |
| 2 | Exigir el `_NEWLINE` de `return_stmt` | 188 → **143**, rompe **24/52** |
| 3 | `"return" block_expr` como alternativa | **Reduce/Reduce**, no construye |
| 4 | Excluir las formas de bloque de `value_expr` | **Reduce/Reduce**, no construye |
| 5 | Declaraciones de precedencia explícitas | Requiere nombrar ~18 terminales en todo el grammar |
| 6 | Expresiones de bloque consumen `_NEWLINE` | 188 → **188**, y con el `_NEWLINE` obligatorio rompe **24/52** |

**Ninguna de las seis funciona.** El contador sigue en **188** y el criterio 2 sigue sin cumplirse
por sexta medición consecutiva.

### Lo que esto significa para el roadmap

El item 2.4 está marcado **L** (grande) y su criterio de "done" es que `strict=True` construya. Las
seis mediciones convergen en que **la causa es el reparto de `_NEWLINE` entre producciones que
consumen `_DEDENT`**, y que arreglarlo no es reducir conflictos: es rediseñar cómo el lenguaje
delimita bloques. Eso es un item **XL** de la Fase 11 (congelación) o de una fase propia, no algo
que se cierre ajustando producciones.

#### Séptima medición: la hipótesis de la causa raíz **también falla**

El párrafo anterior (escrito en esta misma ronda) proponía que un `block` que consumiera
`_DEDENT _NEWLINE` reduciría los conflictos "de forma masiva y de raíz". **Se probó y es falso:**

```diff
-block: ":" _NEWLINE _INDENT stmt+ _DEDENT
+block: ":" _NEWLINE _INDENT stmt+ _DEDENT _NEWLINE
```

| Medición | Resultado |
|---|---|
| Conflictos | **188 → 188** |
| Módulos de la stdlib que fallan | **26 / 52** (peor que 24) |

Los diagnósticos cambian de sitio (`archivum.pengu:115`, `arithmancy.pengu:99`) pero siguen siendo
errores de sintaxis en el primer token de la línea siguiente, que es exactamente la firma de que el
`_NEWLINE` **no está donde la producción lo busca**. Es decir: el indenter no emite
`_DEDENT _NEWLINE` como secuencia adyacente en los casos que importan, y mi modelo mental del reparto
de tokens era incorrecto.

**Esto invalida las dos recomendaciones que había escrito** (§12 y el párrafo anterior de este §14).
No queda ninguna hipótesis pendiente que probar sin instrumentar el lexer.

### Recomendación honesta para quien retome 2.4

**Siete mediciones, ninguna funciona, y las dos teorías sobre la causa raíz quedaron refutadas.** Lo
que recomiendo ahora no es otra variante del grammar, sino **instrumentar primero**: volcar la
secuencia real de tokens (`_NEWLINE`/`_INDENT`/`_DEDENT`) que `PenguIndenter` produce para unos pocos
programas representativos, y *entonces* razonar sobre el reparto. Las seis primeras vías se eligieron
sobre un modelo del token stream que resultó ser incorrecto, y esa es la razón de fondo por la que
ninguna funcionó.

El número 188 no es el problema a atacar directamente: es el síntoma de que el lenguaje delinea
bloques de una forma que LALR(1) no puede decidir sin ambigüedad, y eso es un rediseño, no un
ajuste.

---

## §15. La causa raíz real, obtenida instrumentando el lexer

El §14 terminó recomendando instrumentar el lexer antes de proponer otra variante del grammar, porque
las siete vías anteriores se habían elegido sobre un modelo mental del *token stream* que resultó
falso dos veces. Hecho eso, la causa aparece en una sola línea.

### El volcado

Programa representativo:

```pengu
weave f with b as bool into string:
  return judge b:
    when true -> "t"
    when false -> "f"
```

Secuencia real de tokens estructurales que produce `PenguIndenter`:

```
... COLON _NEWLINE _INDENT
    RETURN ... JUDGE ... COLON _NEWLINE _INDENT
        WHEN ... STRING _NEWLINE
        WHEN ... STRING _NEWLINE
    _DEDENT _DEDENT
```

### La causa

**`_DEDENT _DEDENT` aparece seguido, sin ningún `_NEWLINE` en medio.**

El motivo está en `lark.Indenter.handle_NL`:

```python
yield token                      # el _NEWLINE de ESTA línea
if indent > level:
    yield INDENT
else:
    while indent < level:
        yield DEDENT             # uno por cada nivel, sin _NEWLINE
```

El `_NEWLINE` se emite **una sola vez, al principio**, en la línea que provoca el dedent. Los
`_DEDENT` adicionales (cuando el dedent salta **más de un nivel**, como aquí: de `when` a `weave`)
salen del bucle **sin `_NEWLINE` entre ellos**.

Además, `judge_expr` y `block` **consumen** ese único `_NEWLINE` que sí existe. Así que todo lo que
venga detrás ve `_DEDENT` y nada más.

### Por qué las siete vías fallaron

Todas ellas —incluidas mis dos "causas raíz"— partían de que había un `_NEWLINE` disponible junto a
cada `_DEDENT`. **No lo hay cuando el dedent cruza más de un nivel de indentación**, que es
exactamente el caso de todo constructo anidado:

* `return judge b:` → el `judge` está un nivel más adentro que el `return`;
* cualquier `if` dentro de un `if`, cualquier bucle dentro de un `weave`, etc.

Por eso el diagnóstico era siempre el mismo (`spark.pengu:74`, `archivum.pengu:150`): el primer token
de la línea siguiente, allí donde el parser esperaba un `_NEWLINE` que el lexer nunca emitió.

### La corrección de fondo

Arreglarlo no es tocar el grammar, es **cambiar el indenter** para que emita un `_NEWLINE` por cada
`_DEDENT`, o relajar las producciones para que acepten un `_DEDENT` sin `_NEWLINE` precedente. Las
dos son cambios de infraestructura con efecto en **todo** el lenguaje, y la primera altera el
contrato con `lark.Indenter`, que es una clase de la dependencia.

Esto reencuadra el item 2.4 por completo: **no es "reducir 188 conflictos", es "arreglar el reparto
de `_NEWLINE` en los dedents multi-nivel"**. Los 188 conflictos son el síntoma; la causa es que el
lenguaje delinea bloques con un token que el lexer no emite donde las producciones lo buscan.

**Veredicto:** el item 2.4 queda **⏸️ diferido a 1.1** con la causa raíz identificada por primera vez
y verificada contra el volcado real del lexer. El contador sigue en **188** y el criterio 2 sin
cumplirse, pero ya no es un misterio: es un cambio de infraestructura de lexing, acotado y
entendido.

---

## §16. La causa raíz, precisada: el `_NEWLINE` **sí** está, y está de más

El §15 concluyó que "`_DEDENT _DEDENT` aparece sin `_NEWLINE` en medio" y que había que cambiar el
indenter. Comparar tres programas lado a lado (en vez de mirar solo el caso anidado) **corrige esa
conclusión**:

| Programa | Secuencia estructural |
|----------|----------------------|
| `weave f: return 1` | `_NEWLINE _INDENT _NEWLINE _DEDENT` |
| `weave f: if true: return 1` / `return 2` | `_NEWLINE _INDENT _NEWLINE _INDENT _NEWLINE _DEDENT _NEWLINE _DEDENT` |
| `weave f: return judge b: …` | `_NEWLINE _INDENT **_NEWLINE _NEWLINE** _DEDENT _DEDENT` |

Leyendo las tres:

* En los dos casos normales hay **exactamente un `_NEWLINE` por cada `_DEDENT`**. La regla se cumple.
* En el caso del `judge` hay **dos `_NEWLINE` seguidos** y luego los dos `_DEDENT`. Es decir: **el
  `_NEWLINE` que "faltaba" no falta — sobra.** El token extra aparece *antes* de los dedents, no
  después.

### Esto invalida también el §15

El §15 decía que el indenter no emite `_NEWLINE` junto a cada `_DEDENT` y que había que cambiarlo.
**Es falso:** sí lo emite. Lo que ocurre es lo contrario, un `_NEWLINE` **de más** justo antes de los
`_DEDENT` en las expresiones terminadas en bloque.

Y explica con precisión por qué la vía 6 (`judge_expr: … _DEDENT _NEWLINE`) falló: intentaba consumir
un `_NEWLINE` **después** del `_DEDENT`, cuando el token disponible está **antes**. La producción
buscaba el token en el lado equivocado.

### Corrección acumulada a mis propias conclusiones

Tres teorías sobre la causa raíz, escritas en tres rondas, y **las tres refutadas por medición**:

| Ronda | Teoría | Cómo se refutó |
|-------|--------|----------------|
| §7 | "hay que exigir el `_NEWLINE` de `return_stmt`" | 188 → 143 pero rompe 24/52 módulos |
| §12 | "hay que normalizar las expresiones de bloque para que consuman `_NEWLINE`" | 188 → 188 y rompe 24/52 |
| §15 | "el indenter no emite `_NEWLINE` junto a cada `_DEDENT`" | El volcado comparado muestra que sí lo emite; sobra un `_NEWLINE` |

### Lo que ahora se sabe con certeza

1. El lexer emite `_NEWLINE` antes de cada `_DEDENT` — la regla se cumple en los casos normales.
2. Las expresiones terminadas en bloque (`judge_expr`, y presumiblemente `do_expr` /
   `with_init_expr`) dejan un `_NEWLINE` **extra** antes de los dedents.
3. Ese extra es la causa de que `return_stmt: "return" [value_expr] [_NEWLINE]` sea ambiguo: tras la
   expresión de bloque quedan **dos** `_NEWLINE` donde la producción espera **uno o ninguno**.
4. **Ninguna de las siete variantes de grammar lo abordaba**, porque todas asumían que faltaba un
   token, no que sobraba.

### Qué haría falta para cerrar 2.4

La corrección apunta ahora a un sitio concreto y pequeño: **hacer que la producción de la expresión
de bloque consuma el `_NEWLINE` extra que ella misma genera** — es decir, la variante 6 pero con el
token **antes** del `_DEDENT`, no después:

```
judge_expr: "judge" expr ":" _NEWLINE _INDENT when_clause+ [else_clause] _DEDENT
```
→ el `_NEWLINE` extra está entre `[else_clause]` y el `_DEDENT`, así que habría que absorberlo dentro
de la última `when_clause`/`else_clause`, no añadirlo al final.

**No se intenta en esta ronda.** Ya van tres teorías refutadas escribiendo variantes del grammar sin
instrumentar; el patrón es claro y la lección es la que el §15 ya enunciaba: **medir el token stream
antes de tocar la producción**. Aquí queda medido y con la posición exacta del token identificada,
que es lo que le faltaba a las siete variantes anteriores.

**Estado:** item 2.4 sigue ⏸️, contador en **188**, criterio 2 sin cumplir.

---

## §17. Cuarta corrección: no hay ningún token "de más" tampoco

El §16 concluyó que había un `_NEWLINE` **extra** antes de los `_DEDENT`. Trazando qué producción
consume cada token, **también es falso**, y la cuenta cuadra sin sobrantes:

```
when_clause: "when" … "->" expr _NEWLINE      # consume 1 _NEWLINE por cláusula
judge_expr:  "judge" expr ":" _NEWLINE _INDENT when_clause+ [else_clause] _DEDENT
```

Para el programa de prueba, la secuencia es

```
COLON _NEWLINE _INDENT  RETURN JUDGE NAME COLON _NEWLINE _INDENT
  WHEN … STRING _NEWLINE      <- terminador del primer when_clause
  WHEN … STRING _NEWLINE      <- terminador del segundo when_clause
_DEDENT _DEDENT
```

Hay **exactamente dos `_NEWLINE` y dos `when_clause`**. El `_NEWLINE _NEWLINE` aparente es
simplemente **el terminador del segundo `when_clause`**, que es un token legítimo y necesario. No
sobra nada, y `judge_expr` no genera ningún token extra. La cuenta es correcta.

### Cuatro teorías, cuatro refutaciones

| # | Teoría | Refutación |
|---|--------|-----------|
| 1 (§7) | Hay que exigir el `_NEWLINE` de `return_stmt` | Rompe 24/52 módulos |
| 2 (§12) | Hay que normalizar las expresiones de bloque | 188 → 188, rompe 24/52 |
| 3 (§15) | El indenter no emite `_NEWLINE` junto a cada `_DEDENT` | El volcado normal sí lo emite |
| 4 (§16) | Hay un `_NEWLINE` de más antes de los `_DEDENT` | Es el terminador del último `when_clause`; no sobra |

**El token stream es correcto.** Ni falta ni sobra nada. Las cuatro teorías nacieron de leer el
volcado a ojo en vez de **contar qué producción consume cada token**, que es lo que finalmente
resolvió el §17.

### Consecuencia honesta para el item 2.4

Si el token stream es correcto, entonces los 45 conflictos de `return_stmt` **no son un artefacto del
lexer** y no se arreglan en el lexer. Son una ambigüedad real de la gramática LALR(1):

```
return_stmt: "return" [value_expr] [_NEWLINE]
```

`value_expr` incluye `judge_expr`, que termina en `_DEDENT`. Con `[_NEWLINE]` opcional, tras leer
`return` el parser puede reducir la sentencia (valor ausente) o desplazar hacia una expresión, y
**ambas son viables para los 45 terminales que pueden iniciar una expresión**. Eso es una ambigüedad
genuina de la gramática, no un problema de lexing.

Las vías 3, 4 y 6 fallaron porque intentaban quitar la ambigüedad **moviendo el token**, y el token
está bien. La vía que ataca la ambigüedad de verdad es separar las dos formas de `return`, y esa
choca con que `judge_expr` es alcanzable por dos caminos (§10). Para romper eso hay que **sacar
`judge_expr` (y compañía) de `expr`** — no de `value_expr` — porque `or_else_expr` → `try_expr` →
`judge_expr` es el segundo camino. Eso sí es un cambio de forma del grafo de expresiones, con
consumidores en tres módulos.

**Estado final del item 2.4 en esta fase: ⏸️ diferido a 1.1**, contador **188**, criterio 2 **sin
cumplir**, y —por primera vez— con la formulación correcta del problema: es una ambigüedad LALR real
de `return_stmt`, no un defecto del lexer ni un token perdido. Cuatro teorías refutadas dejan ese
enunciado como el único que sobrevive a la medición.

---

## §18. Vías 8 y 9 descartadas, y el enunciado mínimo del problema

Se probaron dos mecanismos más, elegidos **después** de tener el diagnóstico correcto del §17 (no
antes, como las siete anteriores).

| # | Vía | Resultado |
|---|-----|-----------|
| 8 | `return_stmt.2: … _NEWLINE` / `return_stmt.1: … block_value_expr` (prioridades de regla) | `Rule 'return_stmt' defined more than once` — Lark exige un solo nombre con alternativas |
| 9 | Un solo `return_stmt` con dos alternativas y `block_value_expr` como no-terminal propio | **`Reduce/Reduce collision in Terminal('NOT')`** |

### Por qué la vía 9 no puede funcionar

El conflicto reduce/reduce aparece porque **`judge_expr` es alcanzable por dos caminos**:

```
camino 1:  block_value_expr -> judge_expr
camino 2:  value_expr -> expr -> or_else_expr -> try_expr -> judge_expr
```

Cuando el parser ha reconocido un `judge_expr` completo, no sabe si reducirlo como
`block_value_expr` (alternativa 1) o dejarlo dentro de `value_expr` (alternativa 2). Las dos
reducciones son válidas, y un conflicto reduce/reduce **no se resuelve con prioridades** — Lark lo
rechaza en la construcción.

**Cerrar la vía 9 exige eliminar el camino 2**, es decir sacar `judge_expr` de `try_expr`. Eso es
seguro y directo, pero **no basta**:

> Con `judge_expr` fuera de `try_expr`, las dos alternativas de `return_stmt` siguen existiendo, y
> ahora el parser debe decidir *antes* de reducir, al ver el token `JUDGE`: ¿desplaza para la
> alternativa 2 (`return_block`) o para construir `value_expr`? Si la alternativa 2 no existe (vía 2
> del §7), hay un solo camino y funcionaría — pero esa es exactamente la vía que rompe 24/52 módulos,
> porque `judge_expr` **no consume `_NEWLINE`** y la alternativa 1 lo exige.

Es un círculo cerrado, y es la formulación mínima del problema:

**`return_stmt` necesita `[_NEWLINE]` opcional porque `value_expr` puede terminar en `_DEDENT`; y
necesita `_NEWLINE` obligatorio para no ser ambiguo. Las dos necesidades son incompatibles mientras
`value_expr` contenga expresiones terminadas en bloque.**

### Las tres salidas reales

Ninguna es un ajuste de producción:

1. **Sacar las expresiones terminadas en bloque de `value_expr` y `expr`** (no solo de `try_expr`),
   de modo que `_NEWLINE` sea siempre obligatorio. Es un cambio del grafo de expresiones con
   consumidores en `pengu_infer`, `pengu_codegen` y `pengu_checker`, y **rompe compatibilidad**:
   `var x as T is judge …:` dejaría de compilar.
2. **Hacer que las expresiones de bloque consuman su propio `_NEWLINE`** — requiere que el lexer
   emita uno **después** del `_DEDENT`, que hoy no ocurre (§17), y por tanto un cambio en
   `PenguIndenter` que altera el contrato con `lark.Indenter`.
3. **Aceptar la ambigüedad y documentarla**, manteniendo `strict=True` fuera de CI. Es lo que se hace
   hoy, con el coste de que el *budget* de conflictos (188) puede crecer sin que nada lo detecte más
   que el test que lo fija.

**Recomendación:** la salida 1 es la correcta a largo plazo (elimina la ambigüedad de raíz y hace el
lenguaje más regular), pero es incompatible con código existente y necesita una fase propia con
migración. La 3 es aceptable para 1.x **si** se refuerza el guard: el test del presupuesto ya existe
(`test_grammar_strict_mode_conflict_budget`), y debería ser un gate de CI para que el número no suba
en silencio.

### Cierre del item 2.4 en la Fase 2

**⏸️ Diferido a 1.1.** Nueve vías medidas, ninguna funciona; el problema está enunciado en su forma
mínima (§18) y las tres salidas están identificadas con su coste. El contador queda en **188** y el
criterio 2 **sin cumplir** — declararlo cumplido sería falso, y seguir probando variantes después de
nueve refutaciones no aportaría nada nuevo.

---

## §19. Instrumentación añadida: `tools/grammar_conflicts.py`

Nueve intentos fallidos de reducir los conflictos compartieron una sola causa de método: se leyó un
volcado de tokens **a ojo** y se editó una producción. El §17 dejó esa lección escrita; esta ronda la
convierte en herramienta para que quien retome 2.4 no repita el patrón.

```
python tools/grammar_conflicts.py --tokens 'weave f into int:\n  return 1\n'
python tools/grammar_conflicts.py --conflicts --top 10
python tools/grammar_conflicts.py --actions --rule return_stmt --top 3
```

| Modo | Qué mide |
|------|----------|
| `--tokens` | El flujo estructural real (`_NEWLINE`/`_INDENT`/`_DEDENT`) con recuentos, y avisa cuando los recuentos de newline y dedent difieren |
| `--conflicts` | Los 188 agrupados por **regla** y por **terminal**, con porcentajes |
| `--actions` | Para cada conflicto, **la regla que Lark se niega a reducir**, marcada como tal |

### El dato que faltaba, ahora observable

`--actions` produce, para los conflictos de `return_stmt`:

```
Shift/Reduce conflict for terminal NOT: (resolving as shift)
 * <return_stmt : RETURN>   <- reduced (the action being skipped)
```

**Los 45 conflictos están poseídos por `return_stmt : RETURN`.** Es decir: Lark **reduce con el
`return` pelado** (tratando `[value_expr]` como ausente) y descarta la reducción alternativa. Eso es
el mecanismo de la ambigüedad del §18, ahora **directamente observable** en vez de inferido — y es la
medición que ninguno de los nueve intentos hizo.

### Dos errores encontrados al escribir los tests, y ambos valen la pena

1. Una versión anterior de `--actions` buscaba el nombre de la regla **en cualquier parte del
   bloque**, y cada bloque lista varias reglas. Reportaba el propietario equivocado. **Un diagnóstico
   que miente es peor que no tenerlo**, y por eso `tests/test_grammar_conflicts_tool.py` incluye la
   mitad negativa (una regla que no posee nada se reporta como tal).
2. Un test afirmaba un caso "balanceado" con recuentos de `_NEWLINE` y `_DEDENT` iguales. **Es
   imposible**: `_NEWLINE` termina *cada* línea del fuente mientras que `_DEDENT` solo cierra un
   bloque, así que `_NEWLINE` siempre es mayor. El test se corrigió para fijar el invariante real.

La herramienta es de solo lectura: nunca edita el grammar. `tests/test_grammar_conflicts_tool.py`
(10 tests) incluye una comprobación cruzada de que el recuento de la herramienta **coincide** con
`_KNOWN_SHIFT_REDUCE_CONFLICTS`, de modo que si el grammar se mueve sin actualizar el presupuesto,
los dos discrepan y el test lo dice.

---

## §20. Auditoría de cumplimiento de las reglas de la fase

La Fase 2 imponía cuatro reglas y dos restricciones de alcance. Comprobación final sobre los 36
commits:

### Alcance: qué se tocó y qué no

| Archivo | Cambios | ¿En alcance? |
|---|---|---|
| `pengu_parser/pengu_types.py` | 122 | ✅ tabla de conceptos, `grants()`, `substitute()` |
| `pengu_parser/pengu_infer.py` | 188 | ✅ consultas de bounds, W0013, rangos, deprecación |
| `pengu_parser/pengu_checker.py` | 43 | ✅ W0005, atributos de método, deprecación de tipos |
| `pengu_parser/pengu_codegen.py` | 90 | ✅ emisor de slice compartido (`..` ≡ `to`) |
| `LANGUAGE.md` + `LANGUAGE_Spanish.md` | 441 | ✅ docs sincronizadas |
| `std/*.pengu` (10 archivos) | 196 | ✅ solo bounds declarados, renombrados W0005 y el idioma `null` |
| `tests/` (13 archivos) + `tools/` (1) | 2272 | ✅ nuevo |
| `AUDIT_1.0.md` + `AUDIT_1.0_FASE2.md` | 1776 | ✅ auditoría |

**Restricciones explícitas de la Fase 2, verificadas con `git diff --name-only`:**

| Ruta prohibida | Estado |
|---|---|
| `pengu_lsp/` | untouched ✓ |
| `pengu_project.py` (CLI) | untouched ✓ |
| `pengu_runtime.h` / `pengu_parser/pengu_runtime.c` | untouched ✓ |
| `.github/` (workflows) | untouched ✓ |

**Sobre "no refactorizar la stdlib fuera de alcance":** los 196 cambios en `std/` son exactamente
tres categorías, todas ordenadas por un item de la fase: (1) declaraciones `where` que la tabla de
bounds coerente del item 2.1 hizo necesarias, (2) renombrados de locales que ensombrecían un weave
global (item 2.12), (3) sustitución del idioma `transmute 0`→`null` en `ffi.pengu` (§8). Ninguna
reorganización gratuita.

### Regla C1 — ningún test aprueba una propiedad inspeccionando texto

Auditoría de las 10 suites nuevas: **22 aserciones** que mencionan una variable de texto, de las
cuales

* **21 comparan contra `out`**, que es la **salida de diagnóstico del compilador** (códigos `E00xx`,
  `W0006`). Afirmar sobre lo que el compilador reporta **es** comprobar la propiedad, no esquivarla.
* **1** está en `test_docs_bounds_sync.py:107` (`assert "Integrum" in text and "Num" in text`), que
  verifica que la documentación **menciona** los conceptos de la cadena — no que el compilador se
  comporte de una forma.

**0 aserciones** afirman sobre el texto fuente del programa bajo prueba.

### Regla C2 — cada test falla al revertir su fix

Verificado explícitamente en los cinco casos donde es comprobable:

| Test | Verificación |
|---|---|
| `test_num_does_not_grant_equality` / `..._ordering` | Sin `CONCEPT_OPERATORS`, el código viejo aceptaba `T: Num` con `==`/`<` |
| `test_documented_bounds_block_matches_the_code_table` | Añadir `eq` a la línea `Num` del doc → 2 fallan |
| `test_alias_in_concept_is_not_implemented` | Añadir `\| "alias" NAME` a `concept_method` → falla |
| `test_documented_spelling_emits_the_documented_ctype[double]` | Declarar `float: …, double` → 3 fallan |
| `test_stdlib_does_not_use_the_deprecated_syntax` | Inyectar `..` en `std/spark.pengu` → falla |
| `test_ref_to_t_widens_to_opaque` | Quitar el caso de `RefType.is_compatible` → 6 fallan |
| `test_dotdot_range_warns_w0013` | Desactivar la emisión de W0013 → 2 fallan |

### Regla C3 — medir antes de decidir

Cada decisión de diseño tiene su medición **antes** del commit, registrada en §1 y §3:
bounds (72 sondas + barrido de la stdlib), `alias` en `concept` (compilar el bloque 59), rangos
(5139 `to` vs 0 `..` sintácticos), `derive` (ejecutar un programa por concepto), primitivos (compilar
cada grafía), `many T` (ejecutar el variádico), W0008 (69/73 falsos positivos), W0012 (65 símbolos
deprecados en uso).

**Y donde no se midió primero, se pagó:** los nueve intentos fallidos del item 2.4 (§7-§18) fueron
todos variantes de grammar escritas desde un modelo mental. El §19 convierte esa lección en
`tools/grammar_conflicts.py`.

### Regla C4 — el grammar, por familias y una por commit

**El grammar no se tocó en toda la fase** (`pengu_parser/pengu_grammar.py` no aparece en el diff).
Los nueve intentos se hicieron **en memoria** (construyendo el texto del grammar y midiendo con Lark)
y se revirtieron sin llegar a commit. Eso es C4 aplicado en su forma más estricta: ninguna familia
llegó a `main` porque ninguna pasó la medición.

### Cumplimiento del criterio de "done"

| # | Criterio | Estado |
|---|---|---|
| 1 | Matriz de bounds medida y coherente con la doc | ✅ 84 tests |
| 2 | `Lark(..., strict=True)` no lanza en CI | ❌ **188 conflictos** |
| 3 | Los 4 bloques que no compilaban, compilan o se retiran con ⏸️ | ✅ |
| 4 | Una sola sintaxis de rango canónica con deprecación | ✅ |
| 5 | Matriz de `derive` documentada y probada por concept | ✅ |
| 6 | 52 módulos → 0 warnings propios | ✅ **71 → 0** |

**5 de 6.** El criterio 2 queda **⏸️ diferido a 1.1** con la causa raíz medida (§18), la atribución
de propiedad de los conflictos medida (§19) y una herramienta de diagnóstico entregada
(`tools/grammar_conflicts.py`). No se declara cumplido porque no lo está; se declara **diferido**, que
es lo que el propio roadmap hace con cinco de sus items cuando el presupuesto no alcanza.

---

## §21. La "salida 1" del §18 **no es viable**, y la razón es más fuerte de lo que dije

El §18 propuso tres salidas y recomendó la 1 ("sacar las expresiones terminadas en bloque de
`value_expr` y `expr`"). Al ir a medirla antes de descartarla, aparecen dos hechos que **invalidan
esa recomendación y corrigen mi descripción del problema**.

### Hecho 1 — `judge` en posición de sentencia es sintaxis real y en uso

```
$ grep -n 'judge e:' std/archivum.pengu
145:    judge e:
146:        when IoError.NotFound -> "no such file or directory"
...
```

`std/archivum.pengu:145` dentro de `weave describe_error with e as IoError into string:` usa un
`judge` **como sentencia**, no como valor de `return`. Lo comprobé con un programa mínimo: un `judge`
desnudo en el cuerpo de un `weave` es legal.

**Y funciona porque `judge_expr` es alcanzable desde `expr`**, que es justo lo que la salida 1
proponía eliminar. Es decir: **la salida 1 no rompe solo `var x is judge …:` como dije en el §18 —
rompe el `judge` como sentencia, que la stdlib ya usa.**

### Hecho 2 — los dos usos son legítimos y ambos obligatorios

| Uso | ¿En uso? | Camino gramatical |
|-----|----------|-------------------|
| `return judge …` | **6 archivos** (`chronicle`, `oracle`, `precis`, `seal`, `spark`, `whisper`) | `return_stmt` → `value_expr` |
| `judge …` como sentencia | **1 archivo** (`archivum`) | `expr_stmt` → `expr` → `or_else_expr` → `try_expr` |
| `var x is judge …` | **0** — no existe en stdlib ni tests | — |

### Consecuencia: la eliminación de la ambigüedad es **sintácticamente forzada**

`judge_expr` **tiene que** ser alcanzable desde `expr` (por el uso 2). Y `return` **tiene que**
aceptar un `judge_expr` (por el uso 1). Como `expr` es el camino por el que `return` acepta
cualquier valor, hay **dos caminos de `return` a `judge_expr`**, y un conflicto reduce/reduce entre
ellos es inevitable mientras existan las dos sintaxis.

Cerrarlo exige cambiar **la sintaxis**, no la gramática. La opción concreta: exigir una forma
delimitada para el `return` con valor de bloque, por ejemplo

```
return do:
    judge b:
        when true -> "t"
```

(`do_expr` ya existe y ya termina en `_DEDENT`, y `judge_expr` dentro de un `do:` es una sentencia,
no un valor). Eso **elimina** el camino ambiguo y deja la forma actual como error de sintaxis con un
mensaje que indique la alternativa.

### Corrección al §18 y a lo que reporté

Dije que la salida 1 era "la correcta a largo plazo" y que rompía `var x is judge …:`. Lo segundo era
**inexacto** (esa forma no existe en el código) y lo primero era **optimista**: la salida 1 no es una
mejora a largo plazo, es **incompatible con sintaxis vigente y en uso** (`judge` como sentencia), y
por tanto no es una opción sin un cambio de lenguaje aprobado.

**La formulación final y correcta del bloqueo**, tras diez mediciones:

> `return` necesita aceptar expresiones terminadas en bloque (6 archivos lo usan) y `expr` necesita
> contenerlas (porque `judge` es también una sentencia, usada en `archivum`). LALR(1) no puede
> distinguir ambos caminos en el token `JUDGE`, y ningún reordenamiento de producciones lo arregla
> porque **ambas rutas son necesarias**. La única salida es introducir sintaxis delimitada para una
> de las dos formas.

Eso convierte el item 2.4 de "reducir conflictos" en **"decisión de sintaxis para el `return` con
valor de bloque"**, que es una decisión de diseño del lenguaje, no una tarea de implementación.
Queda registrado así para 1.1.

---

## §22. Décima vía: la prueba de que `judge_expr` **tiene** que estar en `expr`

El §21 concluyó que `judge_expr` debe ser alcanzable desde `expr` porque `judge` es también una
sentencia (`archivum.pengu:145`), y que por eso la ambigüedad es forzada. Para no dejar eso como
razonamiento, se probó la negación: **sacar `judge_expr` de `expr` y darle producciones dedicadas**
en las dos posiciones donde se usa.

### La variante

```diff
 ?value_expr: unless_stmt | if_stmt | while_stmt | for_stmt
+           | judge_expr                       # 'return judge …'
            | expr
 ?try_expr:  "try" … | if_expr | when_expr
-           | judge_expr                       # fuera de la cascada
            | for_comp_expr | bool_or_expr
-return_stmt: "return" [value_expr] [_NEWLINE]
+return_stmt: "return" [value_expr] _NEWLINE
```

### Resultado, y es concluyente

| Medición | Resultado |
|---|---|
| ¿Construye el grammar? | **Sí** — el reduce/reduce desaparece |
| Conflictos | 188 → **143** (los 45 de `return_stmt`, como predecía §7) |
| **Módulos de la stdlib que fallan** | **24 / 52** |
| `judge` como **sentencia** (`archivum:145`) | ❌ **`E0000: unexpected ':'`** |
| `return judge …` (6 archivos) | ❌ roto |

### El argumento, ahora con la negación probada

Al sacar `judge_expr` de `expr` **se rompen las dos posiciones a la vez**:

* `return judge …` falla porque el camino `return` → `value_expr` → `judge_expr` y el camino
  `return` → `value_expr` → `expr` colisionan de nuevo en cuanto se intenta recuperar la forma de
  valor;
* `judge` como sentencia falla porque `expr_stmt` llega a `judge` **a través de `expr`**, y `expr`
  ya no lo contiene. El `E0000: unexpected ':'` en `archivum.pengu:145` es exactamente eso.

Es decir: **`judge` es una sentencia en este lenguaje, y las sentencias se analizan por `expr`.**
Sacarlo de `expr` lo elimina del lenguaje como sentencia. No hay una tercera posición donde ponerlo.

Esto cierra la décima vía y, con ella, la búsqueda. Lo que queda no es una variante de gramática sin
probar: es que **la sintaxis del lenguaje hace inevitable la ambigüedad**, y resolverla exige:

1. introducir una forma delimitada (`return do: …`), o
2. aceptar los 188 conflictos y reforzar el presupuesto como gate de CI.

Ambas son decisiones de diseño del lenguaje. **El item 2.4 no es implementable dentro de la Fase 2
tal como está especificado**, y eso es ahora un resultado medido, no una opinión.

### Balance final del item 2.4

| # | Vía | Resultado |
|---|-----|-----------|
| 1 | Colapsar reglas `_no_cast` duplicadas | 188 → 188 |
| 2 | Exigir `_NEWLINE` de `return_stmt` | 188 → 143, rompe 24/52 |
| 3 | `"return" block_expr` como alternativa | Reduce/Reduce |
| 4 | Excluir bloques de `value_expr` | Reduce/Reduce |
| 5 | Precedencia explícita | ~18 terminales anónimos por nombrar |
| 6 | Bloques consumen `_NEWLINE` final | 188 → 188, rompe 24/52 |
| 7 | `block` consume `_DEDENT _NEWLINE` | 188 → 188, rompe 26/52 |
| 8 | Prioridades de regla | `defined more than once` |
| 9 | Un `return_stmt`, dos alternativas | Reduce/Reduce |
| 10 | `judge_expr` fuera de `expr`, producciones dedicadas | **Construye, 188 → 143, rompe 24/52** |

**Diez vías. Ninguna funciona.** La 10 es la más informativa porque **construye** (elimina el
reduce/reduce) y aun así rompe el lenguaje, lo que demuestra que el problema no es la forma de las
producciones sino la sintaxis.

La herramienta `tools/grammar_conflicts.py` (§19) queda para quien retome el item: mide el token
stream real, la propiedad de cada conflicto y la regla que Lark se niega a reducir.
