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

**Efecto en las cuentas de la auditoría:** `LANGUAGE.md` pasa de 105 a **104** bloques `pengu`, y los
que compilan de 33 a **34** (33 %). El defecto documental nº 4 de `AUDIT_1.0.md` §13.1 (bloque 59)
queda **cerrado**, y se añade un **quinto ❌ REFUTADO** (§18.1 nº 24).

