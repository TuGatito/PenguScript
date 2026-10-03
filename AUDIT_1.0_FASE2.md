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

### §1.2 Item 2.3 — `alias` en `concept`: **pendiente de decisión tras medir**

*(Se completa más abajo, al ejecutar el item.)*

