# std.logica

> Source: `std/logica.pengu`

std/logica.pengu — the logic: methods on the `bool` primitive.

`logica` dota de métodos a `bool` mediante un bloque `enchanting bool:` que
expone las conectivas de la lógica clásica (conjunción, disyunción,
negación, XOR, NAND, NOR, implicación material y bicondicional) y la
conversión a entero. Todo es **PenguScript puro**: sin `declare`, sin
`antiquus`, sin C.

## Alcance
Los operadores del lenguaje (`and`, `or`, `not`) cubren la mayoría de los
casos. `logica` añade:
- las conectivas derivadas que no son operador (`xor`, `nand`, `nor`,
  `implies`, `iff`),
- una versión **encadenable** de las básicas (`toggle`, `and_with`,
  `or_with`),
- `to_int`, para acumular contadores en un bucle.

## Nota sobre `implies`
La implicación material `a implies b` es `(not a) or b`: solo es `false`
cuando `a` es `true` y `b` es `false`. Para cualquier otro par devuelve
`true`, incluso con `a` falsa. Es contraintuitiva para quien lee `implies`
como causalidad; la tabla de verdad está en el docstring del método.

## Memoria
Ningún método asigna memoria del heap. No hay nada que liberar con `banish`.

## Ejemplo
```pengu
import std.spark
import std.logica

weave main into int:
    var ready as bool is true
    var armed as bool is false
    var blocked as bool is calling ready.implies with armed
    if blocked:
        calling spark.println with "not reached"
    else:
        calling spark.println with "ready but not armed"
    calling spark.println with "{calling ready.to_int}"      # 1
    return 0
```

Con esto queda cerrada la serie de módulos de primitivos: `std.numerus`
(`Num`), `std.integrum` (`Integrum`), `std.fractio` (`Real`),
`std.littera` (`char`) y `std.logica` (`bool`).

---

### `LOGICA_VERSION`

> **LOGICA_VERSION** : string

 Logica module version.

### `to_int`

> **to_int**() -> int

 Devuelve `1` si `self` es `true` y `0` si es `false`.

 ## Uso típico
 Acumular un contador a partir de predicados:
 ```pengu
 var count as int is 0
 var flag as bool is true
 set count is count + calling flag.to_int
 ```

 ## Nota de implementación
 Se escribe `if self: return 1` y no `return self to int`: el checker
 acepta casts que el backend C no sabe emitir (el caso `string -> int`
 se corrigió en la Fase 3.4), y un `if` explícito no depende de esa ruta.

### `toggle`

> **toggle**() -> bool

_Undocumented._

### `and_with`

> **and_with**(other: bool) -> bool

_Undocumented._

### `or_with`

> **or_with**(other: bool) -> bool

_Undocumented._

### `xor`

> **xor**(other: bool) -> bool

_Undocumented._

### `iff`

> **iff**(other: bool) -> bool

_Undocumented._

### `nand`

> **nand**(other: bool) -> bool

_Undocumented._

### `nor`

> **nor**(other: bool) -> bool

_Undocumented._

### `implies`

> **implies**(other: bool) -> bool

_Undocumented._

### `_t_true`

> **_t_true**(got: bool) -> void

 Helper de test: falla salvo que `got` sea `true`.

### `_t_false`

> **_t_false**(got: bool) -> void

 Helper de test: falla salvo que `got` sea `false`.

### `_t_int`

> **_t_int**(got: int, want: int) -> void

 Helper de test: igualdad exacta de `int`.

### `"to_int maps true to one"`

> test "to_int maps true to one"

_Undocumented._

### `"to_int maps false to zero"`

> test "to_int maps false to zero"

_Undocumented._

### `"to_int accumulates a counter"`

> test "to_int accumulates a counter"

_Undocumented._

### `"toggle flips true"`

> test "toggle flips true"

_Undocumented._

### `"toggle flips false"`

> test "toggle flips false"

_Undocumented._

### `"toggle twice is the identity"`

> test "toggle twice is the identity"

_Undocumented._

### `"and_with over the four pairs"`

> test "and_with over the four pairs"

_Undocumented._

### `"or_with over the four pairs"`

> test "or_with over the four pairs"

_Undocumented._

### `"xor is true exactly when the operands differ"`

> test "xor is true exactly when the operands differ"

_Undocumented._

### `"iff is true exactly when the operands agree"`

> test "iff is true exactly when the operands agree"

_Undocumented._

### `"nand is the negation of and"`

> test "nand is the negation of and"

_Undocumented._

### `"nor is the negation of or"`

> test "nor is the negation of or"

_Undocumented._

### `"implies is false only for true implies false"`

> test "implies is false only for true implies false"

_Undocumented._

### `"implies is true for the other three pairs"`

> test "implies is true for the other three pairs"

_Undocumented._

### `"implies equals not-or"`

> test "implies equals not-or"

_Undocumented._

### `"implies is reflexive"`

> test "implies is reflexive"

_Undocumented._

### `"iff equals both implications"`

> test "iff equals both implications"

_Undocumented._

### `"xor equals not iff"`

> test "xor equals not iff"

_Undocumented._

### `"nand equals not and"`

> test "nand equals not and"

_Undocumented._

### `"nor equals not or"`

> test "nor equals not or"

_Undocumented._

### `"xor is associative"`

> test "xor is associative"

_Undocumented._

### `"and_with distributes over or_with"`

> test "and_with distributes over or_with"

_Undocumented._

### `"de morgan: not (a and b) equals (not a) or (not b)"`

> test "de morgan: not (a and b) equals (not a) or (not b)"

_Undocumented._

### `"the predicates compose into a permission check"`

> test "the predicates compose into a permission check"

_Undocumented._

### `"and_with and or_with are idempotent"`

> test "and_with and or_with are idempotent"

_Undocumented._

### `"and_with and or_with commute"`

> test "and_with and or_with commute"

_Undocumented._

### `"the identity elements behave"`

> test "the identity elements behave"

_Undocumented._

### `"toggle mutates the receiver"`

> test "toggle mutates the receiver"

 --- In-place mutation vs the pure `get_` form -------------------------------

 `@mutates` gives every method above two spellings: `calling v.<name>` rewrites
 `v`, and `calling v.get_<name>` returns the value leaving `v` alone.  One test
 per spelling, per method.

### `"get_toggle returns without mutating"`

> test "get_toggle returns without mutating"

_Undocumented._

### `"and_with mutates the receiver"`

> test "and_with mutates the receiver"

_Undocumented._

### `"get_and_with returns without mutating"`

> test "get_and_with returns without mutating"

_Undocumented._

### `"or_with mutates the receiver"`

> test "or_with mutates the receiver"

_Undocumented._

### `"get_or_with returns without mutating"`

> test "get_or_with returns without mutating"

_Undocumented._

### `"xor mutates the receiver"`

> test "xor mutates the receiver"

_Undocumented._

### `"get_xor returns without mutating"`

> test "get_xor returns without mutating"

_Undocumented._

### `"iff mutates the receiver"`

> test "iff mutates the receiver"

_Undocumented._

### `"get_iff returns without mutating"`

> test "get_iff returns without mutating"

_Undocumented._

### `"nand mutates the receiver"`

> test "nand mutates the receiver"

_Undocumented._

### `"get_nand returns without mutating"`

> test "get_nand returns without mutating"

_Undocumented._

### `"nor mutates the receiver"`

> test "nor mutates the receiver"

_Undocumented._

### `"get_nor returns without mutating"`

> test "get_nor returns without mutating"

_Undocumented._

### `"implies mutates the receiver"`

> test "implies mutates the receiver"

_Undocumented._

### `"get_implies returns without mutating"`

> test "get_implies returns without mutating"

_Undocumented._

### `"chained boolean mutations on one receiver"`

> test "chained boolean mutations on one receiver"

_Undocumented._

