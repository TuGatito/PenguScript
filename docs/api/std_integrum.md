# std.integrum

> Source: `std/integrum.pengu`

std/integrum.pengu — the integer: methods that only make sense on whole
numbers, over the `Integrum` concept.

`integrum` dota de métodos a **todos** los primitivos enteros de PenguScript
(`int`, `i8`–`i64`, `u8`–`u64`, `usize`, `isize`, `byte`) mediante un único
bloque `enchanting shard T where T: Integrum:`. El compilador monomorfiza
cada método por tipo concreto en tiempo de compilación (`int_is_even`,
`i64_gcd`, `u32_bit_count`, …), así que no hay vtables, boxing ni coste en
runtime.

## Alcance
`integrum` cubre **solo** lo que tiene sentido en enteros: paridad,
primalidad, bits, MCD/MCM, divisiones euclidianas y representaciones
(`to_hex`, `to_bin`, `to_oct`). Los métodos universales (`abs`, `signum`,
`clamp`, `pow_int`, `min_with`, `max_with`, `twice`, `half`, `round`) viven
en `std.numerus`; como `Integrum` implica `Num` (y concede igualdad y orden,
LANGUAGE.md §11.3), esos métodos siguen disponibles dentro de un cuerpo
acotado por `Integrum`. Los métodos exclusivos de flotantes viven en
`std.fractio`.

## Delegación
`integrum` importa `std.numerus` y delega en él siempre que necesita el
valor absoluto (`gcd`, `lcm`, `to_hex`, `to_bin`, `to_oct` usan
`calling self.abs`) en lugar de duplicar el `if self < donum T: return -self`.
Este módulo es la **fuente de verdad** de la teoría de números entera: las
funciones `is_prime`, `gcd`, `lcm` y `is_power_of_two` de `std.arithmancy`
son ahora wrappers de una línea sobre estos métodos. `arithmancy`
`next_power_of_two` **no** delega: su contrato es "la menor potencia de dos
`>= n`", mientras que el de aquí es "estrictamente mayor" (`4` → `8`).

## Memoria
Solo `to_hex`, `to_bin` y `to_oct` asignan memoria del heap: devuelven un
`string` nuevo que el llamador debe liberar con `banish` (o `defer banish`).
El resto de métodos no asigna memoria.

## Precondiciones
- `is_multiple_of`, `lcm`, `div_rem`, `div_floor`, `mod_floor`: `other != 0`
  (división por cero). No paniquean; el comportamiento es el de C.
- `is_prime`, `next_prime`, `prev_prime`: el algoritmo es O(√n) por división
  por tentativa con la optimización 6k±1. Viable hasta ~10^12; para
  criptografía con `u64` grande, usa una librería de primalidad dedicada.
- `factorial`: el resultado debe caber en `T`. En perfiles de depuración el
  desbordamiento **con signo** aborta (`-ftrapv`); en release envuelve según
  la aritmética de C. Límites seguros: `5!` cabe en `u8`, `7!` en `i16`,
  `12!` en `i32`, `20!` en `i64`.
- `next_power_of_two`: si `self` ya es la mayor potencia representable, el
  desplazamiento envuelve a 0.
- `to_hex`/`to_bin`/`to_oct`: en tipos con signo el resultado es
  signo-y-magnitud (`-255.to_hex` es `"-ff"`); para el valor mínimo de `T`
  (`INT_MIN`) la magnitud no es representable y el resultado es indefinido.

## Ejemplo
```pengu
import std.spark
import std.integrum

weave main into int:
    var n as int is 12
    calling spark.println with "{calling n.is_even}"       # true
    calling spark.println with "{calling n.gcd with 18}"   # 6
    var h as string is calling n.to_hex                    # "c"
    calling spark.println with h
    banish h
    return 0
```

---

### `INTEGRUM_VERSION`

> **INTEGRUM_VERSION** : string

 Integrum module version.

### `_integrum_hex_digit`

> **_integrum_hex_digit**(d: int) -> string

 Helper privado: un dígito hexadecimal (`0`–`15`) como `string`.

 Devuelve un `string` literal (`"a"`–`"f"`) o, para `0`–`9`, un interpolado
 **owned**. El llamador es responsable de liberarlo: `banish` es un no-op sobre
 el literal y libera el interpolado, así que `banish` sobre el resultado es
 correcto en ambos casos. (El runtime no libera nada por su cuenta: el modelo
 de memoria es manual.) Ver `to_hex`.

### `_is_prime_impl`

> **_is_prime_impl**() -> bool

 Helper privado: primalidad por división por tentativa 6k±1.

 No forma parte de la API pública (prefijo `_`); `is_prime`, `next_prime`
 y `prev_prime` lo usan para no triplicar el algoritmo.

### `is_even`

> **is_even**() -> bool

 Devuelve `true` si `self` es divisible por 2.

 ## Ejemplo
 ```pengu
 4.is_even       # true
 (-7).is_even    # false
 ```

### `is_odd`

> **is_odd**() -> bool

 Devuelve `true` si `self` no es divisible por 2.

 ## Ejemplo
 ```pengu
 4.is_odd        # false
 (-7).is_odd     # true
 ```

### `is_power_of_two`

> **is_power_of_two**() -> bool

 Devuelve `true` si `self` es una potencia de 2 (1, 2, 4, 8, …).

 `0.is_power_of_two` es `false`. El truco `(n & (n - 1)) == 0` lo hace
 O(1).

 ## Ejemplo
 ```pengu
 1.is_power_of_two    # true
 8.is_power_of_two    # true
 6.is_power_of_two    # false
 ```

### `is_multiple_of`

> **is_multiple_of**(other: T) -> bool

 Devuelve `true` si `self` es múltiplo de `other` (o sea, `self % other == 0`).

 ## Precondiciones
 `other != 0`. El comportamiento es indefinido si se viola.

 ## Ejemplo
 ```pengu
 var n as int is 12
 calling n.is_multiple_of with 4    # true
 calling n.is_multiple_of with 5    # false
 var z as int is 0
 calling z.is_multiple_of with 7    # true
 ```

### `is_prime`

> **is_prime**() -> bool

 Devuelve `true` si `self` es primo (mayor que 1 y sin divisores propios).

 ## Complejidad
 O(√n) por división por tentativa con la optimización 6k±1. Viable en la
 práctica hasta ~10^12; para criptografía usa primalidad probabilística.

 ## Ejemplo
 ```pengu
 2.is_prime      # true
 17.is_prime     # true
 18.is_prime     # false
 ```

### `bit_count`

> **bit_count**() -> int

 Cuenta los bits puestos a 1 (popcount) del ancho completo de `T`.

 Para tipos con signo se usa la representación en complemento a dos, así
 que el bit de signo cuenta: `(-1).bit_count` es el ancho de `T`. El
 recorrido está acotado por el ancho, de modo que un valor negativo no
 buclea (un desplazamiento aritmético a la derecha nunca llega a 0).

 ## Ejemplo
 ```pengu
 0b1011.bit_count    # 3
 255.bit_count       # 8
 ```

### `bit_length`

> **bit_length**() -> int

 Devuelve el número de bits necesarios para representar `self` (el índice
 del bit más alto con valor 1, más uno).

 `0.bit_length == 0`, `1.bit_length == 1`, `255.bit_length == 8`. En
 complemento a dos un valor negativo tiene el bit de signo puesto, así que
 su longitud es el ancho de `T`: `(-1).bit_length == 32` en un `int`.

 ## Ejemplo
 ```pengu
 1.bit_length      # 1
 255.bit_length    # 8
 256.bit_length    # 9
 ```

### `leading_zeros`

> **leading_zeros**() -> int

 Cuenta los bits a cero más significativos (por encima del bit más alto
 con valor 1), usando el ancho completo de `T`.

 `0.leading_zeros == (size of T) * 8`; siempre se cumple
 `leading_zeros + bit_length == ancho`.

 ## Ejemplo
 ```pengu
 # En un int de 32 bits:
 1.leading_zeros      # 31
 255.leading_zeros    # 24
 ```

### `trailing_zeros`

> **trailing_zeros**() -> int

 Cuenta los bits a cero menos significativos (por debajo del bit más bajo
 con valor 1), usando el ancho completo de `T`.

 `0.trailing_zeros == (size of T) * 8`.

 ## Ejemplo
 ```pengu
 8.trailing_zeros     # 3
 12.trailing_zeros    # 2
 ```

### `next_power_of_two`

> **next_power_of_two**() -> T

_Undocumented._

### `prev_power_of_two`

> **prev_power_of_two**() -> T

_Undocumented._

### `div_rem`

> **div_rem**(other: T) -> (T, T)

 Devuelve una tupla `(cociente, resto)` de la división entera, calculando
 la división una sola vez.

 ## Precondiciones
 `other != 0`.

 ## Ejemplo
 ```pengu
 var n as int is 17
 let (q, r) is calling n.div_rem with 5
 # q == 3, r == 2
 ```

### `div_floor`

> **div_floor**(other: T) -> T

_Undocumented._

### `mod_floor`

> **mod_floor**(other: T) -> T

_Undocumented._

### `gcd`

> **gcd**(other: T) -> T

_Undocumented._

### `lcm`

> **lcm**(other: T) -> T

_Undocumented._

### `next_prime`

> **next_prime**() -> T

_Undocumented._

### `prev_prime`

> **prev_prime**() -> T

_Undocumented._

### `factorial`

> **factorial**() -> T

_Undocumented._

### `to_hex`

> **to_hex**() -> string

 Convierte `self` a hexadecimal **sin prefijo `0x`**, en minúsculas.

 ## Memoria
 Asigna un `string` nuevo en el heap. **Libéralo con `banish`**.

 ## Precondiciones
 Para tipos con signo, `self` distinto del mínimo de `T` (`INT_MIN`).

 ## Ejemplo
 ```pengu
 var n as int is 255
 var h as string is calling n.to_hex
 calling spark.println with h          # "ff"
 banish h
 ```

### `to_bin`

> **to_bin**() -> string

 Convierte `self` a binario **sin prefijo `0b`**.

 ## Memoria
 Asigna un `string` nuevo. **Libéralo con `banish`**.

 ## Precondiciones
 Para tipos con signo, `self` distinto del mínimo de `T`.

 ## Ejemplo
 ```pengu
 var n as int is 5
 var b as string is calling n.to_bin
 calling spark.println with b          # "101"
 banish b
 ```

### `to_oct`

> **to_oct**() -> string

 Convierte `self` a octal **sin prefijo `0o`**.

 ## Memoria
 Asigna un `string` nuevo. **Libéralo con `banish`**.

 ## Precondiciones
 Para tipos con signo, `self` distinto del mínimo de `T`.

 ## Ejemplo
 ```pengu
 var n as int is 8
 var o as string is calling n.to_oct
 calling spark.println with o          # "10"
 banish o
 ```

### `_t_int`

> **_t_int**(got: int, want: int) -> void

 Helper de test: compara dos `int` con el nombre del módulo ya resuelto.

### `_t_bool`

> **_t_bool**(got: bool, want: bool) -> void

 Helper de test: compara dos `bool`.

### `_t_str`

> **_t_str**(got: string, want: string) -> void

 Helper de test: compara dos `string`.

### `"is_even covers the four quadrants"`

> test "is_even covers the four quadrants"

_Undocumented._

### `"is_even works for narrow and wide receivers"`

> test "is_even works for narrow and wide receivers"

_Undocumented._

### `"is_odd is the complement of is_even"`

> test "is_odd is the complement of is_even"

_Undocumented._

### `"is_power_of_two accepts the powers and rejects the rest"`

> test "is_power_of_two accepts the powers and rejects the rest"

_Undocumented._

### `"is_power_of_two rejects zero and negatives"`

> test "is_power_of_two rejects zero and negatives"

_Undocumented._

### `"is_multiple_of handles exact, inexact and zero dividends"`

> test "is_multiple_of handles exact, inexact and zero dividends"

_Undocumented._

### `"is_prime on the small cases"`

> test "is_prime on the small cases"

_Undocumented._

### `"is_prime around a large prime"`

> test "is_prime around a large prime"

_Undocumented._

### `"bit_count counts the set bits"`

> test "bit_count counts the set bits"

_Undocumented._

### `"bit_count counts the sign bits of a negative"`

> test "bit_count counts the sign bits of a negative"

_Undocumented._

### `"bit_length reports the width of the value"`

> test "bit_length reports the width of the value"

_Undocumented._

### `"bit_length uses two's complement for negatives"`

> test "bit_length uses two's complement for negatives"

_Undocumented._

### `"leading_zeros complements bit_length"`

> test "leading_zeros complements bit_length"

_Undocumented._

### `"leading_zeros and bit_length add up to the width"`

> test "leading_zeros and bit_length add up to the width"

_Undocumented._

### `"trailing_zeros counts the low zero bits"`

> test "trailing_zeros counts the low zero bits"

_Undocumented._

### `"next_power_of_two rounds strictly up"`

> test "next_power_of_two rounds strictly up"

_Undocumented._

### `"prev_power_of_two rounds down inclusively"`

> test "prev_power_of_two rounds down inclusively"

_Undocumented._

### `"div_rem returns quotient and remainder"`

> test "div_rem returns quotient and remainder"

_Undocumented._

### `"div_rem holds the Euclidean identity"`

> test "div_rem holds the Euclidean identity"

_Undocumented._

### `"div_floor rounds toward minus infinity"`

> test "div_floor rounds toward minus infinity"

_Undocumented._

### `"mod_floor takes the sign of the divisor"`

> test "mod_floor takes the sign of the divisor"

_Undocumented._

### `"gcd of the classic pair"`

> test "gcd of the classic pair"

_Undocumented._

### `"gcd with zero and coprimes"`

> test "gcd with zero and coprimes"

_Undocumented._

### `"gcd is non-negative for negative inputs"`

> test "gcd is non-negative for negative inputs"

_Undocumented._

### `"lcm of the classic pair"`

> test "lcm of the classic pair"

_Undocumented._

### `"lcm with zero is zero"`

> test "lcm with zero is zero"

_Undocumented._

### `"lcm is non-negative for negative inputs"`

> test "lcm is non-negative for negative inputs"

_Undocumented._

### `"next_prime finds the following prime"`

> test "next_prime finds the following prime"

_Undocumented._

### `"prev_prime finds the preceding prime"`

> test "prev_prime finds the preceding prime"

_Undocumented._

### `"factorial on the small cases"`

> test "factorial on the small cases"

_Undocumented._

### `"factorial works on a wide receiver"`

> test "factorial works on a wide receiver"

_Undocumented._

### `"to_hex on the boundaries"`

> test "to_hex on the boundaries"

_Undocumented._

### `"to_hex is sign and magnitude for negatives"`

> test "to_hex is sign and magnitude for negatives"

_Undocumented._

### `"to_bin on the boundaries"`

> test "to_bin on the boundaries"

_Undocumented._

### `"to_oct on the boundaries"`

> test "to_oct on the boundaries"

_Undocumented._

### `"integrum composes with numerus on the same receiver"`

> test "integrum composes with numerus on the same receiver"

_Undocumented._

### `"is_prime survives the square root of a 32-bit maximum"`

> test "is_prime survives the square root of a 32-bit maximum"

_Undocumented._

### `"is_prime still rejects its neighbours"`

> test "is_prime still rejects its neighbours"

_Undocumented._

### `"next_power_of_two mutates the receiver"`

> test "next_power_of_two mutates the receiver"

 --- In-place mutation vs the pure `get_` form -------------------------------

### `"get_next_power_of_two returns without mutating"`

> test "get_next_power_of_two returns without mutating"

_Undocumented._

### `"prev_power_of_two mutates the receiver"`

> test "prev_power_of_two mutates the receiver"

_Undocumented._

### `"get_prev_power_of_two returns without mutating"`

> test "get_prev_power_of_two returns without mutating"

_Undocumented._

### `"div_floor mutates the receiver"`

> test "div_floor mutates the receiver"

_Undocumented._

### `"get_div_floor returns without mutating"`

> test "get_div_floor returns without mutating"

_Undocumented._

### `"mod_floor mutates the receiver"`

> test "mod_floor mutates the receiver"

_Undocumented._

### `"get_mod_floor returns without mutating"`

> test "get_mod_floor returns without mutating"

_Undocumented._

### `"gcd mutates the receiver"`

> test "gcd mutates the receiver"

_Undocumented._

### `"get_gcd returns without mutating"`

> test "get_gcd returns without mutating"

_Undocumented._

### `"lcm mutates the receiver"`

> test "lcm mutates the receiver"

_Undocumented._

### `"get_lcm returns without mutating"`

> test "get_lcm returns without mutating"

_Undocumented._

### `"next_prime mutates the receiver"`

> test "next_prime mutates the receiver"

_Undocumented._

### `"get_next_prime returns without mutating"`

> test "get_next_prime returns without mutating"

_Undocumented._

### `"prev_prime mutates the receiver"`

> test "prev_prime mutates the receiver"

_Undocumented._

### `"get_prev_prime returns without mutating"`

> test "get_prev_prime returns without mutating"

_Undocumented._

### `"factorial mutates the receiver"`

> test "factorial mutates the receiver"

_Undocumented._

### `"get_factorial returns without mutating"`

> test "get_factorial returns without mutating"

_Undocumented._

### `"chained mutations on one receiver"`

> test "chained mutations on one receiver"

_Undocumented._

