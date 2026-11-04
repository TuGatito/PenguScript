# std.fractio

> Source: `std/fractio.pengu`

std/fractio.pengu — the fraction: methods that only make sense on
floating-point values, over the `Real` concept.

`fractio` dota de métodos a `float`, `f32`, `f64` y `double`. La
clasificación IEEE 754, la aproximación y las utilidades puras viven en un
único bloque `enchanting shard T where T: Real:`; los transcendentales, que
llaman a `libm`, viven en dos bloques concretos (`enchanting float:` y
`enchanting f64:`) porque C expone símbolos distintos por ancho (`sqrtf`
frente a `sqrt`). El compilador monomorfiza cada método por tipo concreto
(`float_is_nan`, `f64_sqrt`, …), así que no hay vtables, boxing ni coste en
runtime más allá de la llamada a `libm`.

## Alcance
`fractio` cubre **solo** lo que tiene sentido en flotantes: clasificación
IEEE 754 (`is_nan`, `is_finite`, `is_infinite`, `is_positive_infinity`,
`is_negative_infinity`), comparación con tolerancia (`approx_eq`),
interpolación (`lerp`), utilidades (`reciprocal`, `copysign`, `degrees`,
`radians`) y transcendentales (`sqrt`, `cbrt`, `sin`, `cos`, `tan`, `asin`,
`acos`, `atan`, `atan2`, `exp`, `ln`, `log2`, `log10`, `pow`, `hypot`).
Los métodos universales (`abs`, `signum`, `clamp`, `round`, `pow_int`, …)
viven en `std.numerus`; los exclusivos de enteros, en `std.integrum`.
`Real` implica `Num`, así que un programa que importe ambos tiene todo.

## Delegación
Este módulo es la **fuente de verdad** de la matemática de punto flotante:
los transcendentales de `std.arithmancy` (`sqrt`, `pow`, `sin`, `cos`,
`tan`, `asin`, `acos`, `atan`, `atan2`, `exp`, `log`, `log10`, `log2`,
`hypot`, `lerp`, `deg_to_rad`, `rad_to_deg`) son ahora wrappers de una línea
sobre estos métodos. `arithmancy.approx_eq` **no** delega: usa `<=` y éste
`<`, así que difieren justo cuando `|a - b| == eps`.
`fractio` **no** importa `std.numerus`: no necesita ningún método universal
(las dos magnitudes que calcula, en `approx_eq` y `copysign`, son tres líneas
cada una) y un módulo hoja de matemáticas gana más quedándose sin
dependencias cruzadas que ahorrándose esos dos bucles. Un programa que
importe ambos sigue teniendo `abs`, `clamp`, `pow_int`, … porque `Real`
implica `Num` (`LANGUAGE.md` §11.3).

## Memoria
Ningún método de este módulo asigna memoria del heap. No hay nada que
liberar con `banish`.

## Precondiciones
Ninguna función panickea: el comportamiento en los casos límite es el de
C99 (`<math.h>`), con NaN e Inf propagados según IEEE 754.
- `sqrt`, `ln`, `log2`, `log10`: dominio `self >= 0` (`> 0` para los
  logaritmos). Fuera del dominio devuelven NaN (`ln(0)` devuelve -Inf).
- `asin`, `acos`: dominio `[-1, 1]`; fuera devuelven NaN.
- `reciprocal`: `self != 0`; con `0.0` devuelve ±Inf según el signo del cero.
- `approx_eq` usa tolerancia **absoluta**. Para magnitudes grandes escala
  `eps` con `|self|` (`1e20 * 1e-9`), no lo dejes fijo.

## Nota de implementación
Los `declare` nombran los símbolos **reales** de `libm` (`sqrtf`, `sqrt`, …):
`pengu_runtime.h` ya incluye `<math.h>`, así que sus prototipos están
disponibles y no hace falta una capa `pengu_c_*` por ancho. Los literales
numéricos de un cuerpo `T: Real` se escriben `(1.0 to T)`: un literal `int`
no es convertible a `T: Real` (`int` no implementa `Real`), un literal
flotante sí.

## Ejemplo
```pengu
import std.spark
import std.fractio

weave main into int:
    var x as f64 is 4.0
    var y as f64 is calling x.sqrt
    calling spark.println with "{y}"          # 2
    var neg as f64 is -1.0
    var bad as f64 is calling neg.sqrt
    if calling bad.is_nan:
        calling spark.println with "NaN"      # NaN
    return 0
```

---

### `FRACTIO_VERSION`

> **FRACTIO_VERSION** : string

 Fractio module version.

### `sqrtf`

> **sqrtf**(x: f32) -> f32

 ----------------------------------------------------------------------------
 libm declarations (symbols are the real C99 ones; <math.h> is already
 included by pengu_runtime.h, and the bundle links -lm)
 ----------------------------------------------------------------------------

### `sqrt`

> **sqrt**(x: f64) -> f64

_Undocumented._

### `cbrtf`

> **cbrtf**(x: f32) -> f32

_Undocumented._

### `cbrt`

> **cbrt**(x: f64) -> f64

_Undocumented._

### `sinf`

> **sinf**(x: f32) -> f32

_Undocumented._

### `sin`

> **sin**(x: f64) -> f64

_Undocumented._

### `cosf`

> **cosf**(x: f32) -> f32

_Undocumented._

### `cos`

> **cos**(x: f64) -> f64

_Undocumented._

### `tanf`

> **tanf**(x: f32) -> f32

_Undocumented._

### `tan`

> **tan**(x: f64) -> f64

_Undocumented._

### `asinf`

> **asinf**(x: f32) -> f32

_Undocumented._

### `asin`

> **asin**(x: f64) -> f64

_Undocumented._

### `acosf`

> **acosf**(x: f32) -> f32

_Undocumented._

### `acos`

> **acos**(x: f64) -> f64

_Undocumented._

### `atanf`

> **atanf**(x: f32) -> f32

_Undocumented._

### `atan`

> **atan**(x: f64) -> f64

_Undocumented._

### `atan2f`

> **atan2f**(y: f32, x: f32) -> f32

_Undocumented._

### `atan2`

> **atan2**(y: f64, x: f64) -> f64

_Undocumented._

### `expf`

> **expf**(x: f32) -> f32

_Undocumented._

### `exp`

> **exp**(x: f64) -> f64

_Undocumented._

### `logf`

> **logf**(x: f32) -> f32

_Undocumented._

### `log`

> **log**(x: f64) -> f64

_Undocumented._

### `log2f`

> **log2f**(x: f32) -> f32

_Undocumented._

### `log2`

> **log2**(x: f64) -> f64

_Undocumented._

### `log10f`

> **log10f**(x: f32) -> f32

_Undocumented._

### `log10`

> **log10**(x: f64) -> f64

_Undocumented._

### `powf`

> **powf**(base: f32, exponent: f32) -> f32

_Undocumented._

### `pow`

> **pow**(base: f64, exponent: f64) -> f64

_Undocumented._

### `hypotf`

> **hypotf**(x: f32, y: f32) -> f32

_Undocumented._

### `hypot`

> **hypot**(x: f64, y: f64) -> f64

_Undocumented._

### `is_nan`

> **is_nan**() -> bool

 Devuelve `true` si `self` es NaN (Not a Number).

 Funciona sin `libm`: `NaN != NaN` es siempre `true` por IEEE 754.

 ## Ejemplo
 ```pengu
 var x as f64 is 1.0
 var neg as f64 is -1.0
 var bad as f64 is calling neg.sqrt
 calling spark.println with "{calling bad.is_nan}"   # true
 ```

### `is_infinite`

> **is_infinite**() -> bool

 Devuelve `true` si `self` es +Inf o -Inf.

 Implementación puramente PenguScript: para un valor finito `x`,
 `|x| - |x| == 0`; para `±Inf`, `Inf - Inf` es NaN y `NaN != 0` es
 `true`. NaN se descarta primero para no confundirse con infinito.

### `is_finite`

> **is_finite**() -> bool

 Devuelve `true` si `self` es finito (ni NaN ni ±Inf).

### `is_positive_infinity`

> **is_positive_infinity**() -> bool

 Devuelve `true` si `self` es exactamente `+Inf`.

### `is_negative_infinity`

> **is_negative_infinity**() -> bool

 Devuelve `true` si `self` es exactamente `-Inf`.

### `approx_eq`

> **approx_eq**(other: T, eps: T) -> bool

 Devuelve `true` si `|self - other| < eps`.

 ## Semántica
 La tolerancia `eps` es **absoluta**, no relativa. Para magnitudes
 grandes, escala `eps` con `|self|`: comparar `1e20` con `1e20 + 1`
 necesita `eps` proporcional, no `1e-9`.

 ## Ejemplo
 ```pengu
 var a as f64 is 0.1 + 0.2
 var b as f64 is 0.3
 calling spark.println with "{calling a.approx_eq with b, 1e-9}"   # true
 ```

### `reciprocal`

> **reciprocal**() -> T

_Undocumented._

### `lerp`

> **lerp**(other: T, t: T) -> T

_Undocumented._

### `copysign`

> **copysign**(sign_source: T) -> T

_Undocumented._

### `degrees`

> **degrees**() -> T

_Undocumented._

### `radians`

> **radians**() -> T

_Undocumented._

### `ln`

> **ln**() -> float

_Undocumented._

### `_t_true`

> **_t_true**(got: bool) -> void

 Helper de test: falla salvo que `got` sea `true`.

### `_t_false`

> **_t_false**(got: bool) -> void

 Helper de test: falla salvo que `got` sea `false`.

### `_t_f64`

> **_t_f64**(got: f64, want: f64) -> void

 Helper de test: igualdad exacta de `f64`.

### `_t_close`

> **_t_close**(got: f64, want: f64, eps: f64) -> void

 Helper de test: igualdad aproximada de `f64` dentro de `eps` absoluto.

### `_t_nan`

> **_t_nan**(got: f64) -> void

 Helper de test: `NaN` de `f64`.

### `"is_nan detects NaN from sqrt of a negative"`

> test "is_nan detects NaN from sqrt of a negative"

_Undocumented._

### `"is_nan is false for ordinary values"`

> test "is_nan is false for ordinary values"

_Undocumented._

### `"is_finite is true for ordinary values"`

> test "is_finite is true for ordinary values"

_Undocumented._

### `"is_finite is false for Inf and NaN"`

> test "is_finite is false for Inf and NaN"

_Undocumented._

### `"is_infinite detects positive infinity"`

> test "is_infinite detects positive infinity"

_Undocumented._

### `"is_infinite detects negative infinity"`

> test "is_infinite detects negative infinity"

_Undocumented._

### `"is_infinite is false for finite values and NaN"`

> test "is_infinite is false for finite values and NaN"

_Undocumented._

### `"is_positive_infinity distinguishes the sign"`

> test "is_positive_infinity distinguishes the sign"

_Undocumented._

### `"is_negative_infinity distinguishes the sign"`

> test "is_negative_infinity distinguishes the sign"

_Undocumented._

### `"approx_eq accepts exact and near values"`

> test "approx_eq accepts exact and near values"

_Undocumented._

### `"approx_eq rejects values outside eps"`

> test "approx_eq rejects values outside eps"

_Undocumented._

### `"approx_eq works with negatives"`

> test "approx_eq works with negatives"

_Undocumented._

### `"reciprocal inverts the value"`

> test "reciprocal inverts the value"

_Undocumented._

### `"reciprocal of zero is infinity"`

> test "reciprocal of zero is infinity"

_Undocumented._

### `"lerp interpolates at the endpoints and the middle"`

> test "lerp interpolates at the endpoints and the middle"

_Undocumented._

### `"lerp extrapolates outside the unit interval"`

> test "lerp extrapolates outside the unit interval"

_Undocumented._

### `"copysign keeps the magnitude and takes the sign"`

> test "copysign keeps the magnitude and takes the sign"

_Undocumented._

### `"degrees turns pi into 180"`

> test "degrees turns pi into 180"

_Undocumented._

### `"radians turns 180 into pi"`

> test "radians turns 180 into pi"

_Undocumented._

### `"sqrt of a perfect square is exact"`

> test "sqrt of a perfect square is exact"

_Undocumented._

### `"sqrt of a negative is NaN"`

> test "sqrt of a negative is NaN"

_Undocumented._

### `"cbrt handles both signs"`

> test "cbrt handles both signs"

_Undocumented._

### `"sin and cos at the cardinal angles"`

> test "sin and cos at the cardinal angles"

_Undocumented._

### `"tan at zero and pi/4"`

> test "tan at zero and pi/4"

_Undocumented._

### `"asin and acos at the domain edges"`

> test "asin and acos at the domain edges"

_Undocumented._

### `"asin outside the domain is NaN"`

> test "asin outside the domain is NaN"

_Undocumented._

### `"atan and atan2 in the first quadrant"`

> test "atan and atan2 in the first quadrant"

_Undocumented._

### `"exp at zero and one"`

> test "exp at zero and one"

_Undocumented._

### `"ln is the inverse of exp"`

> test "ln is the inverse of exp"

_Undocumented._

### `"ln of zero is negative infinity"`

> test "ln of zero is negative infinity"

_Undocumented._

### `"ln of a negative is NaN"`

> test "ln of a negative is NaN"

_Undocumented._

### `"log2 and log10 on the powers of their base"`

> test "log2 and log10 on the powers of their base"

_Undocumented._

### `"pow raises to a real exponent"`

> test "pow raises to a real exponent"

_Undocumented._

### `"hypot is the Pythagorean length"`

> test "hypot is the Pythagorean length"

_Undocumented._

### `"the transcendental methods are monomorphized per width"`

> test "the transcendental methods are monomorphized per width"

_Undocumented._

### `"float and f32 aliases reach the same methods"`

> test "float and f32 aliases reach the same methods"

_Undocumented._

### `"fractio and numerus compose when both are imported elsewhere"`

> test "fractio and numerus compose when both are imported elsewhere"

_Undocumented._

### `"reciprocal mutates the receiver (float)"`

> test "reciprocal mutates the receiver (float)"

 --- In-place mutation vs the pure `get_` form -------------------------------

 Every method above is `@mutates`: `calling x.sqrt` rewrites `x`, while
 `calling x.get_sqrt` returns the value and leaves `x` alone.  Floats are
 compared with `_t_close`, which carries a tolerance.

### `"get_reciprocal returns without mutating (float)"`

> test "get_reciprocal returns without mutating (float)"

_Undocumented._

### `"lerp mutates the receiver (float)"`

> test "lerp mutates the receiver (float)"

_Undocumented._

### `"get_lerp returns without mutating (float)"`

> test "get_lerp returns without mutating (float)"

_Undocumented._

### `"copysign mutates the receiver (float)"`

> test "copysign mutates the receiver (float)"

_Undocumented._

### `"get_copysign returns without mutating (float)"`

> test "get_copysign returns without mutating (float)"

_Undocumented._

### `"degrees mutates the receiver (float)"`

> test "degrees mutates the receiver (float)"

_Undocumented._

### `"get_degrees returns without mutating (float)"`

> test "get_degrees returns without mutating (float)"

_Undocumented._

### `"radians mutates the receiver (float)"`

> test "radians mutates the receiver (float)"

_Undocumented._

### `"get_radians returns without mutating (float)"`

> test "get_radians returns without mutating (float)"

_Undocumented._

### `"sqrt mutates the receiver (float)"`

> test "sqrt mutates the receiver (float)"

_Undocumented._

### `"get_sqrt returns without mutating (float)"`

> test "get_sqrt returns without mutating (float)"

_Undocumented._

### `"cbrt mutates the receiver (float)"`

> test "cbrt mutates the receiver (float)"

_Undocumented._

### `"get_cbrt returns without mutating (float)"`

> test "get_cbrt returns without mutating (float)"

_Undocumented._

### `"sin mutates the receiver (float)"`

> test "sin mutates the receiver (float)"

_Undocumented._

### `"get_sin returns without mutating (float)"`

> test "get_sin returns without mutating (float)"

_Undocumented._

### `"cos mutates the receiver (float)"`

> test "cos mutates the receiver (float)"

_Undocumented._

### `"get_cos returns without mutating (float)"`

> test "get_cos returns without mutating (float)"

_Undocumented._

### `"tan mutates the receiver (float)"`

> test "tan mutates the receiver (float)"

_Undocumented._

### `"get_tan returns without mutating (float)"`

> test "get_tan returns without mutating (float)"

_Undocumented._

### `"asin mutates the receiver (float)"`

> test "asin mutates the receiver (float)"

_Undocumented._

### `"get_asin returns without mutating (float)"`

> test "get_asin returns without mutating (float)"

_Undocumented._

### `"acos mutates the receiver (float)"`

> test "acos mutates the receiver (float)"

_Undocumented._

### `"get_acos returns without mutating (float)"`

> test "get_acos returns without mutating (float)"

_Undocumented._

### `"atan mutates the receiver (float)"`

> test "atan mutates the receiver (float)"

_Undocumented._

### `"get_atan returns without mutating (float)"`

> test "get_atan returns without mutating (float)"

_Undocumented._

### `"atan2 mutates the receiver (float)"`

> test "atan2 mutates the receiver (float)"

_Undocumented._

### `"get_atan2 returns without mutating (float)"`

> test "get_atan2 returns without mutating (float)"

_Undocumented._

### `"exp mutates the receiver (float)"`

> test "exp mutates the receiver (float)"

_Undocumented._

### `"get_exp returns without mutating (float)"`

> test "get_exp returns without mutating (float)"

_Undocumented._

### `"ln mutates the receiver (float)"`

> test "ln mutates the receiver (float)"

_Undocumented._

### `"get_ln returns without mutating (float)"`

> test "get_ln returns without mutating (float)"

_Undocumented._

### `"log2 mutates the receiver (float)"`

> test "log2 mutates the receiver (float)"

_Undocumented._

### `"get_log2 returns without mutating (float)"`

> test "get_log2 returns without mutating (float)"

_Undocumented._

### `"log10 mutates the receiver (float)"`

> test "log10 mutates the receiver (float)"

_Undocumented._

### `"get_log10 returns without mutating (float)"`

> test "get_log10 returns without mutating (float)"

_Undocumented._

### `"pow mutates the receiver (float)"`

> test "pow mutates the receiver (float)"

_Undocumented._

### `"get_pow returns without mutating (float)"`

> test "get_pow returns without mutating (float)"

_Undocumented._

### `"hypot mutates the receiver (float)"`

> test "hypot mutates the receiver (float)"

_Undocumented._

### `"get_hypot returns without mutating (float)"`

> test "get_hypot returns without mutating (float)"

_Undocumented._

### `"sqrt mutates the receiver (f64)"`

> test "sqrt mutates the receiver (f64)"

_Undocumented._

### `"get_sqrt returns without mutating (f64)"`

> test "get_sqrt returns without mutating (f64)"

_Undocumented._

### `"cbrt mutates the receiver (f64)"`

> test "cbrt mutates the receiver (f64)"

_Undocumented._

### `"get_cbrt returns without mutating (f64)"`

> test "get_cbrt returns without mutating (f64)"

_Undocumented._

### `"sin mutates the receiver (f64)"`

> test "sin mutates the receiver (f64)"

_Undocumented._

### `"get_sin returns without mutating (f64)"`

> test "get_sin returns without mutating (f64)"

_Undocumented._

### `"cos mutates the receiver (f64)"`

> test "cos mutates the receiver (f64)"

_Undocumented._

### `"get_cos returns without mutating (f64)"`

> test "get_cos returns without mutating (f64)"

_Undocumented._

### `"tan mutates the receiver (f64)"`

> test "tan mutates the receiver (f64)"

_Undocumented._

### `"get_tan returns without mutating (f64)"`

> test "get_tan returns without mutating (f64)"

_Undocumented._

### `"asin mutates the receiver (f64)"`

> test "asin mutates the receiver (f64)"

_Undocumented._

### `"get_asin returns without mutating (f64)"`

> test "get_asin returns without mutating (f64)"

_Undocumented._

### `"acos mutates the receiver (f64)"`

> test "acos mutates the receiver (f64)"

_Undocumented._

### `"get_acos returns without mutating (f64)"`

> test "get_acos returns without mutating (f64)"

_Undocumented._

### `"atan mutates the receiver (f64)"`

> test "atan mutates the receiver (f64)"

_Undocumented._

### `"get_atan returns without mutating (f64)"`

> test "get_atan returns without mutating (f64)"

_Undocumented._

### `"atan2 mutates the receiver (f64)"`

> test "atan2 mutates the receiver (f64)"

_Undocumented._

### `"get_atan2 returns without mutating (f64)"`

> test "get_atan2 returns without mutating (f64)"

_Undocumented._

### `"exp mutates the receiver (f64)"`

> test "exp mutates the receiver (f64)"

_Undocumented._

### `"get_exp returns without mutating (f64)"`

> test "get_exp returns without mutating (f64)"

_Undocumented._

### `"ln mutates the receiver (f64)"`

> test "ln mutates the receiver (f64)"

_Undocumented._

### `"get_ln returns without mutating (f64)"`

> test "get_ln returns without mutating (f64)"

_Undocumented._

### `"log2 mutates the receiver (f64)"`

> test "log2 mutates the receiver (f64)"

_Undocumented._

### `"get_log2 returns without mutating (f64)"`

> test "get_log2 returns without mutating (f64)"

_Undocumented._

### `"log10 mutates the receiver (f64)"`

> test "log10 mutates the receiver (f64)"

_Undocumented._

### `"get_log10 returns without mutating (f64)"`

> test "get_log10 returns without mutating (f64)"

_Undocumented._

### `"pow mutates the receiver (f64)"`

> test "pow mutates the receiver (f64)"

_Undocumented._

### `"get_pow returns without mutating (f64)"`

> test "get_pow returns without mutating (f64)"

_Undocumented._

### `"hypot mutates the receiver (f64)"`

> test "hypot mutates the receiver (f64)"

_Undocumented._

### `"get_hypot returns without mutating (f64)"`

> test "get_hypot returns without mutating (f64)"

_Undocumented._

### `"chained mutations on one float receiver"`

> test "chained mutations on one float receiver"

_Undocumented._

