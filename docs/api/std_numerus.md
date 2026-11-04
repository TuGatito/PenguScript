# std.numerus

> Source: `std/numerus.pengu`

std/numerus.pengu — the number: universal numeric methods over the `Num`
concept.

`numerus` dota de métodos a **todos** los primitivos numéricos de
PenguScript (`int`, `i8`–`i64`, `u8`–`u64`, `usize`, `isize`, `byte`,
`float`, `f32`, `f64`, `double`) mediante un único bloque
`enchanting shard T where T: Num and T: Ordo and T: Par:`. El compilador
monomorfiza cada método por tipo concreto en tiempo de compilación
(`int_abs`, `f64_clamp`, `u32_signum`, …), así que no hay vtables, ni
boxing, ni coste en runtime.

## `Num` y las comparaciones
En esta versión del lenguaje `Num` concede aritmética (`+`, `-`, `*`, `/`,
unario `-`) pero **no** orden ni igualdad: ésos son los conceptos
ortogonales `Ordo` (`<`, `<=`, `>`, `>=`) y `Par` (`==`, `!=`). Todo
primitivo numérico satisface los tres, así que el bound compuesto sigue
cubriendo exactamente los mismos 11 tipos canónicos con una sola
declaración (LANGUAGE.md §11.3).

## Delegación
Este módulo es la **fuente de verdad** de la aritmética escalar. Las
funciones escalares de `std.arithmancy` (`abs`/`abs_i`, `min`/`min_i`,
`max`/`max_i`, `clamp`/`clamp_i`, `sign`/`sign_i`, `to_int_round`/
`to_int_floor`/`to_int_ceil`) son ahora wrappers de una línea sobre estos
métodos.

Cuatro de ellos **no** se delegan desde `arithmancy`, y no por descuido:
`truncate`, `floor`, `ceil` y `round` pasan por `int` para redondear
(`self to int`), así que solo son exactos mientras `|self|` quepa en `int`.
Las versiones de `arithmancy` son las de C (`floorf`, `round`, …) y cubren
todo el dominio de `float`/`f64`; cambiar una por otra alteraría resultados
fuera de ese rango. `## Precondiciones` de cada método lo documenta.

## Alcance
`numerus` cubre lo que tiene sentido para **cualquier** tipo numérico
(enteros y flotantes). Los métodos exclusivos de enteros (`is_even`,
`is_odd`, `gcd`, `lcm`, `bit_count`) viven en `std.integrum`; los
exclusivos de flotantes (`sqrt`, `is_nan`, `approx_eq`, `sin`, `cos`) en
`std.fractio`. Las conversiones sin método (`x to int`) siguen siendo la
vía idiomática para cambiar de tipo; `to_f64`/`to_i64` sólo existen por
comodidad encadenable.

## Precondiciones
- `clamp with lo, hi` e `is_between with lo, hi` exigen `lo <= hi`. No
  paniquean (evitar importar `std.spark` sólo por eso); con `lo > hi` el
  resultado es el del algoritmo, que para `is_between` es siempre `false`.
- `pow_int with exp` exige `exp != INT_MIN` (la negación del exponente
  desbordaría). Los exponentes negativos sobre tipos enteros truncan hacia
  cero: `2.pow_int with -3` es `0`, no `0.125`.

## Memoria
Ningún método de este módulo asigna memoria del heap. No hay nada que
liberar con `banish`.

## Ejemplo
```pengu
import std.numerus

weave main into int:
    var edad as int is 200
    var corregida as int is calling edad.clamp with 0, 120
    var temp as f64 is -3.7
    var abs_temp as f64 is calling temp.abs
    return 0
```

---

### `NUMERUS_VERSION`

> **NUMERUS_VERSION** : string

 Numerus module version.

### `abs`

> **abs**() -> T

_Undocumented._

### `signum`

> **signum**() -> T

_Undocumented._

### `negated`

> **negated**() -> T

_Undocumented._

### `min_with`

> **min_with**(other: T) -> T

_Undocumented._

### `max_with`

> **max_with**(other: T) -> T

_Undocumented._

### `clamp`

> **clamp**(lo: T, hi: T) -> T

_Undocumented._

### `is_between`

> **is_between**(lo: T, hi: T) -> bool

 Devuelve `true` si `lo <= self <= hi` (rango cerrado).

 ## Precondiciones
 `lo <= hi`. Con `lo > hi` devuelve siempre `false`.

 ## Ejemplo
 ```pengu
 var v12 as int is 5
 calling v12.is_between with 0, 10    # true
 var v13 as int is 15
 calling v13.is_between with 0, 10   # false
 ```

### `is_zero`

> **is_zero**() -> bool

 Devuelve `true` si `self == donum T` (el cero de `T`).

 ## Ejemplo
 ```pengu
 var v14 as int is 0
 calling v14.is_zero      # true
 var v15 as f64 is 0.0
 calling v15.is_zero    # true
 ```

### `is_positive`

> **is_positive**() -> bool

 Devuelve `true` si `self > 0`. Siempre `false` para tipos sin signo
 cuando `self == 0`.

### `is_negative`

> **is_negative**() -> bool

 Devuelve `true` si `self < 0`. Siempre `false` para tipos sin signo.

### `is_non_negative`

> **is_non_negative**() -> bool

 Devuelve `true` si `self >= 0`. Siempre `true` para tipos sin signo.

### `is_non_positive`

> **is_non_positive**() -> bool

 Devuelve `true` si `self <= 0`.

### `twice`

> **twice**() -> T

_Undocumented._

### `half`

> **half**() -> T

_Undocumented._

### `square`

> **square**() -> T

_Undocumented._

### `cube`

> **cube**() -> T

_Undocumented._

### `pow_int`

> **pow_int**(exp: int) -> T

_Undocumented._

### `truncate`

> **truncate**() -> T

_Undocumented._

### `floor`

> **floor**() -> T

_Undocumented._

### `ceil`

> **ceil**() -> T

_Undocumented._

### `round`

> **round**() -> T

_Undocumented._

### `to_f64`

> **to_f64**() -> f64

 Convierte a `f64`. Siempre seguro (ensanchamiento para enteros y
 `f32`).

 ## Ejemplo
 ```pengu
 var v29 as int is 42
 calling v29.to_f64       # 42.0
 var v30 as f64 is 2.5
 calling v30.to_f64      # 2.5
 ```

### `to_i64`

> **to_i64**() -> i64

 Convierte a `i64`. En flotantes trunca hacia cero; en `u64` los
 valores mayores que `2^63 - 1` son indefinidos (comportamiento del
 cast del lenguaje).

 ## Ejemplo
 ```pengu
 var v31 as f64 is 2.9
 calling v31.to_i64      # 2
 var v32 as f64 is (-2.9)
 calling v32.to_i64   # -2
 ```

### `"abs leaves positives untouched"`

> test "abs leaves positives untouched"

 ----------------------------------------------------------------------------
 Tests
 ----------------------------------------------------------------------------

### `"abs flips negatives"`

> test "abs flips negatives"

_Undocumented._

### `"abs is the identity at zero"`

> test "abs is the identity at zero"

_Undocumented._

### `"abs works for wide and unsigned integers"`

> test "abs works for wide and unsigned integers"

_Undocumented._

### `"abs works for every float width"`

> test "abs works for every float width"

_Undocumented._

### `"signum reports the sign of each type"`

> test "signum reports the sign of each type"

_Undocumented._

### `"negated inverts the value"`

> test "negated inverts the value"

_Undocumented._

### `"min_with picks the smaller operand"`

> test "min_with picks the smaller operand"

_Undocumented._

### `"max_with picks the larger operand"`

> test "max_with picks the larger operand"

_Undocumented._

### `"clamp restricts below, inside and above"`

> test "clamp restricts below, inside and above"

_Undocumented._

### `"clamp keeps the inclusive boundaries"`

> test "clamp keeps the inclusive boundaries"

_Undocumented._

### `"clamp works on floats"`

> test "clamp works on floats"

_Undocumented._

### `"is_between accepts the closed range only"`

> test "is_between accepts the closed range only"

_Undocumented._

### `"is_between includes both edges"`

> test "is_between includes both edges"

_Undocumented._

### `"is_zero is true only at zero"`

> test "is_zero is true only at zero"

_Undocumented._

### `"is_positive distinguishes positive from zero and negative"`

> test "is_positive distinguishes positive from zero and negative"

_Undocumented._

### `"is_negative is false for unsigned types"`

> test "is_negative is false for unsigned types"

_Undocumented._

### `"is_non_negative is true for unsigned types"`

> test "is_non_negative is true for unsigned types"

_Undocumented._

### `"is_non_positive mirrors non-negative"`

> test "is_non_positive mirrors non-negative"

_Undocumented._

### `"twice doubles without losing the type"`

> test "twice doubles without losing the type"

_Undocumented._

### `"half truncates toward zero for integers"`

> test "half truncates toward zero for integers"

_Undocumented._

### `"half is exact for floats"`

> test "half is exact for floats"

_Undocumented._

### `"square keeps the sign of the input"`

> test "square keeps the sign of the input"

_Undocumented._

### `"cube keeps the sign of the input"`

> test "cube keeps the sign of the input"

_Undocumented._

### `"pow_int with a zero exponent is one"`

> test "pow_int with a zero exponent is one"

_Undocumented._

### `"pow_int with a positive exponent"`

> test "pow_int with a positive exponent"

_Undocumented._

### `"pow_int truncates for integer negative exponents"`

> test "pow_int truncates for integer negative exponents"

_Undocumented._

### `"pow_int is fractional for float negative exponents"`

> test "pow_int is fractional for float negative exponents"

_Undocumented._

### `"truncate drops the fractional part toward zero"`

> test "truncate drops the fractional part toward zero"

_Undocumented._

### `"truncate is the identity for integers"`

> test "truncate is the identity for integers"

_Undocumented._

### `"floor rounds toward negative infinity"`

> test "floor rounds toward negative infinity"

_Undocumented._

### `"ceil rounds toward positive infinity"`

> test "ceil rounds toward positive infinity"

_Undocumented._

### `"round uses half away from zero"`

> test "round uses half away from zero"

_Undocumented._

### `"round is symmetric for negatives"`

> test "round is symmetric for negatives"

_Undocumented._

### `"round is the identity for integers"`

> test "round is the identity for integers"

_Undocumented._

### `"to_f64 widens integers and floats"`

> test "to_f64 widens integers and floats"

_Undocumented._

### `"to_i64 truncates floats toward zero"`

> test "to_i64 truncates floats toward zero"

_Undocumented._

### `"methods chain across the module"`

> test "methods chain across the module"

_Undocumented._

### `"abs mutates the receiver"`

> test "abs mutates the receiver"

 --- In-place mutation vs the pure `get_` form -------------------------------

 Every method above is `@mutates`: `calling x.abs` rewrites `x`, while
 `calling x.get_abs` returns the value and leaves `x` alone.

### `"get_abs returns without mutating"`

> test "get_abs returns without mutating"

_Undocumented._

### `"signum mutates the receiver"`

> test "signum mutates the receiver"

_Undocumented._

### `"get_signum returns without mutating"`

> test "get_signum returns without mutating"

_Undocumented._

### `"negated mutates the receiver"`

> test "negated mutates the receiver"

_Undocumented._

### `"get_negated returns without mutating"`

> test "get_negated returns without mutating"

_Undocumented._

### `"min_with mutates the receiver"`

> test "min_with mutates the receiver"

_Undocumented._

### `"get_min_with returns without mutating"`

> test "get_min_with returns without mutating"

_Undocumented._

### `"max_with mutates the receiver"`

> test "max_with mutates the receiver"

_Undocumented._

### `"get_max_with returns without mutating"`

> test "get_max_with returns without mutating"

_Undocumented._

### `"clamp mutates the receiver"`

> test "clamp mutates the receiver"

_Undocumented._

### `"get_clamp returns without mutating"`

> test "get_clamp returns without mutating"

_Undocumented._

### `"twice mutates the receiver"`

> test "twice mutates the receiver"

_Undocumented._

### `"get_twice returns without mutating"`

> test "get_twice returns without mutating"

_Undocumented._

### `"half mutates the receiver"`

> test "half mutates the receiver"

_Undocumented._

### `"get_half returns without mutating"`

> test "get_half returns without mutating"

_Undocumented._

### `"square mutates the receiver"`

> test "square mutates the receiver"

_Undocumented._

### `"get_square returns without mutating"`

> test "get_square returns without mutating"

_Undocumented._

### `"cube mutates the receiver"`

> test "cube mutates the receiver"

_Undocumented._

### `"get_cube returns without mutating"`

> test "get_cube returns without mutating"

_Undocumented._

### `"pow_int mutates the receiver"`

> test "pow_int mutates the receiver"

_Undocumented._

### `"get_pow_int returns without mutating"`

> test "get_pow_int returns without mutating"

_Undocumented._

### `"truncate mutates the receiver"`

> test "truncate mutates the receiver"

_Undocumented._

### `"get_truncate returns without mutating"`

> test "get_truncate returns without mutating"

_Undocumented._

### `"floor mutates the receiver"`

> test "floor mutates the receiver"

_Undocumented._

### `"get_floor returns without mutating"`

> test "get_floor returns without mutating"

_Undocumented._

### `"ceil mutates the receiver"`

> test "ceil mutates the receiver"

_Undocumented._

### `"get_ceil returns without mutating"`

> test "get_ceil returns without mutating"

_Undocumented._

### `"round mutates the receiver"`

> test "round mutates the receiver"

_Undocumented._

### `"get_round returns without mutating"`

> test "get_round returns without mutating"

_Undocumented._

### `"chained mutations on one receiver"`

> test "chained mutations on one receiver"

_Undocumented._

