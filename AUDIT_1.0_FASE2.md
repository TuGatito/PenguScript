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

### §3.3 Items no iniciados

| Item | Estado | Por qué |
|------|--------|---------|
| **2.4** (reducción) | ⏸️ intentado y revertido | §3.2 |
| **2.4** (reglas duplicadas `guard_*`/`*_no_cast`) | ⏸️ pendiente | Requiere 2.4 resuelto primero |
| **2.5** (unificar sintaxis de rangos + W nuevo) | ⏸️ pendiente | Requiere decidir la sintaxis canónica (C3) antes de implementar |
| **2.6** (`frozen` en `ref to`) | ⏸️ pendiente | Cambio semántico que necesita medición propia |
| **2.11** (W0001 de `transmute`) | ⏸️ pendiente | W0001 sigue emitiendo 4 avisos en la stdlib; el análisis no se inició |

`W0001` sigue presente y es el mayor resto de ruido de la stdlib:

```
[W0001] transmute from 'int' (4 bytes) to 'ref to byte' (8 bytes) h...
[W0001] transmute from 'int' (4 bytes) to 'ref to char' (8 bytes) h...
[W0001] transmute from 'int' (4 bytes) to 'ref to void' (8 bytes) h...
[W0001] transmute is unsafe, use 'to' for safe conversions
```

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
