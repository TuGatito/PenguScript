# std.littera

> Source: `std/littera.pengu`

std/littera.pengu — the letter: methods on the `char` primitive.

`littera` dota de métodos a `char` mediante un bloque `enchanting char:` que
clasifica el carácter según clases ASCII (dígito, letra, espacio,
puntuación, …) y lo convierte entre mayúscula y minúscula. Todo es
**PenguScript puro**: sin `declare` a `<ctype.h>`, sin `antiquus`, sin
locale. El comportamiento es idéntico en Linux, macOS y Windows.

## Alcance
`char` es un byte, pero sus **literales** están restringidos por el checker
al rango ASCII de 7 bits (`'\x80'` es `E0057`). Un *valor* `char` sí puede
contener 0x80–0xFF cuando proviene de un `byte` o de un buffer de C, así que
`is_ascii` sigue siendo útil y los predicados usan el byte sin signo
(`ord self`, 0–255) para no depender de si `char` es `signed` en la
plataforma.

## Diferencias con `<ctype.h>`
- `is_space` es **solo** el carácter `' '`. Para el conjunto completo
  (`'\t'`, `'\n'`, `'\r'`, `'\f'`, `'\v'`) usa `is_whitespace`.
- `to_upper`/`to_lower` solo mueven `'a'..'z'` ↔ `'A'..'Z'`; cualquier otro
  carácter se devuelve sin cambios.
- Ningún predicado depende del locale: la clasificación es la del locale
  "C" de C, pero calculada en PenguScript.
- `to_int` es `ord self`, es decir el byte **sin signo** (0–255). No uses
  `(self to int)`: en C `char` es `signed` en x86 y `unsigned` en ARM, así
  que ese cast no es portable para bytes altos.

## Memoria
Ningún método asigna memoria del heap. No hay nada que liberar con `banish`.

## Ejemplo
```pengu
import std.spark
import std.littera

weave main into int:
    var c as char is 'a'
    var upper as char is calling c.to_upper
    calling spark.println with "{upper}"          # A
    var d as char is '7'
    calling spark.println with "{calling d.digit_value}"   # 7
    return 0
```

---

### `LITTERA_VERSION`

> **LITTERA_VERSION** : string

 Littera module version.

### `is_digit`

> **is_digit**() -> bool

 Devuelve `true` si `self` es un dígito decimal ASCII (`'0'..'9'`).

 ## Ejemplo
 ```pengu
 var d as char is '5'
 var a as char is 'a'
 calling spark.println with "{calling d.is_digit}"   # true
 calling spark.println with "{calling a.is_digit}"   # false
 ```

### `is_alpha`

> **is_alpha**() -> bool

 Devuelve `true` si `self` es una letra ASCII (`'a'..'z'` o `'A'..'Z'`).

### `is_alnum`

> **is_alnum**() -> bool

 Devuelve `true` si `self` es una letra o un dígito ASCII.

### `is_upper`

> **is_upper**() -> bool

 Devuelve `true` si `self` es una letra mayúscula ASCII (`'A'..'Z'`).

### `is_lower`

> **is_lower**() -> bool

 Devuelve `true` si `self` es una letra minúscula ASCII (`'a'..'z'`).

### `is_space`

> **is_space**() -> bool

 Devuelve `true` si `self` es **exactamente** el carácter espacio `' '`.

 Para el conjunto completo (`'\t'`, `'\n'`, `'\r'`, `'\f'`, `'\v'`),
 usa `is_whitespace`.

### `is_whitespace`

> **is_whitespace**() -> bool

 Devuelve `true` si `self` es un espacio en blanco ASCII: `' '`, `'\t'`,
 `'\n'`, `'\r'`, `'\f'` o `'\v'` (el conjunto de `isspace` en locale "C").

### `is_control`

> **is_control**() -> bool

 Devuelve `true` si `self` es un carácter de control ASCII (0x00–0x1F o
 0x7F DEL).

### `is_printable`

> **is_printable**() -> bool

 Devuelve `true` si `self` es un carácter ASCII imprimible: del espacio
 `' '` (0x20) a la tilde `'~'` (0x7E).

### `is_punctuation`

> **is_punctuation**() -> bool

 Devuelve `true` si `self` es un signo de puntuación ASCII: imprimible,
 pero ni letra, ni dígito, ni espacio (el conjunto de `ispunct` en
 locale "C").

 Incluye ``! " # $ % & ' ( ) * + , - . / : ; < = > ? @ [ \ ] ^ _ ` { | } ~``.

### `is_hex_digit`

> **is_hex_digit**() -> bool

 Devuelve `true` si `self` es un dígito hexadecimal ASCII (`'0'..'9'`,
 `'a'..'f'` o `'A'..'F'`).

### `is_ascii`

> **is_ascii**() -> bool

 Devuelve `true` si `self` está en el rango ASCII (0x00–0x7F).

 Un valor `char` puede venir de un `byte` o de un buffer de C y contener
 0x80–0xFF; este predicado lo detecta.

### `to_upper`

> **to_upper**() -> char

_Undocumented._

### `to_lower`

> **to_lower**() -> char

_Undocumented._

### `to_int`

> **to_int**() -> int

 Devuelve el valor del byte de `self` como `int` sin signo (0–255).

 Equivale a `ord self`, pero es encadenable. Es **portable**: no usa
 `(self to int)`, que daría un valor negativo para 0x80–0xFF en las
 plataformas donde `char` es `signed`.

 ## Ejemplo
 ```pengu
 var c as char is 'A'
 calling spark.println with "{calling c.to_int}"   # 65
 ```

### `digit_value`

> **digit_value**() -> int

 Devuelve el valor numérico de `self` cuando es un dígito decimal o
 hexadecimal: `0..9` para `'0'..'9'`, `10..15` para `'a'..'f'` y
 `'A'..'F'`. Devuelve `-1` si `self` no es un dígito reconocido.

 ## Ejemplo
 ```pengu
 var a as char is 'a'
 var z as char is 'z'
 calling spark.println with "{calling a.digit_value}"   # 10
 calling spark.println with "{calling z.digit_value}"   # -1
 ```

 ## Uso típico
 Base para parsear un número desde un texto:
 ```pengu
 var acc as int is 0
 var ch as char is '7'
 var d as int is calling ch.digit_value
 if d >= 0:
     set acc is acc * 10 + d
 ```

### `_t_true`

> **_t_true**(got: bool) -> void

 Helper de test: falla salvo que `got` sea `true`.

### `_t_false`

> **_t_false**(got: bool) -> void

 Helper de test: falla salvo que `got` sea `false`.

### `_t_int`

> **_t_int**(got: int, want: int) -> void

 Helper de test: igualdad exacta de `int`.

### `_t_char`

> **_t_char**(got: char, want: char) -> void

 Helper de test: igualdad de `char` comparada por su byte.

### `"is_digit accepts the decimal range and its edges"`

> test "is_digit accepts the decimal range and its edges"

_Undocumented._

### `"is_alpha covers both cases and their edges"`

> test "is_alpha covers both cases and their edges"

_Undocumented._

### `"is_alnum unions letters and digits"`

> test "is_alnum unions letters and digits"

_Undocumented._

### `"is_upper covers the uppercase range and its edges"`

> test "is_upper covers the uppercase range and its edges"

_Undocumented._

### `"is_lower covers the lowercase range and its edges"`

> test "is_lower covers the lowercase range and its edges"

_Undocumented._

### `"is_space is only the space character"`

> test "is_space is only the space character"

_Undocumented._

### `"is_whitespace covers the six C isspace characters"`

> test "is_whitespace covers the six C isspace characters"

_Undocumented._

### `"is_control detects the control ranges"`

> test "is_control detects the control ranges"

_Undocumented._

### `"is_printable spans space to tilde"`

> test "is_printable spans space to tilde"

_Undocumented._

### `"is_punctuation excludes alphanumerics and space"`

> test "is_punctuation excludes alphanumerics and space"

_Undocumented._

### `"is_hex_digit covers digits and both letter cases"`

> test "is_hex_digit covers digits and both letter cases"

_Undocumented._

### `"is_ascii is true for the 7-bit range"`

> test "is_ascii is true for the 7-bit range"

_Undocumented._

### `"is_ascii is false for a high byte cast from byte"`

> test "is_ascii is false for a high byte cast from byte"

_Undocumented._

### `"to_upper shifts lowercase letters"`

> test "to_upper shifts lowercase letters"

_Undocumented._

### `"to_upper leaves non-lowercase characters alone"`

> test "to_upper leaves non-lowercase characters alone"

_Undocumented._

### `"to_lower shifts uppercase letters"`

> test "to_lower shifts uppercase letters"

_Undocumented._

### `"to_lower leaves non-uppercase characters alone"`

> test "to_lower leaves non-uppercase characters alone"

_Undocumented._

### `"to_upper and to_lower round-trip"`

> test "to_upper and to_lower round-trip"

_Undocumented._

### `"to_int returns the ASCII code"`

> test "to_int returns the ASCII code"

_Undocumented._

### `"to_int is the unsigned byte, portable for high bytes"`

> test "to_int is the unsigned byte, portable for high bytes"

_Undocumented._

### `"to_int agrees with ord"`

> test "to_int agrees with ord"

_Undocumented._

### `"digit_value on the decimal digits"`

> test "digit_value on the decimal digits"

_Undocumented._

### `"digit_value on the hexadecimal letters"`

> test "digit_value on the hexadecimal letters"

_Undocumented._

### `"digit_value is -1 for anything else"`

> test "digit_value is -1 for anything else"

_Undocumented._

### `"digit_value spans 0..9 and 10..15 contiguously"`

> test "digit_value spans 0..9 and 10..15 contiguously"

_Undocumented._

### `"the classification predicates are mutually consistent on a sample"`

> test "the classification predicates are mutually consistent on a sample"

_Undocumented._

### `"to_upper mutates the receiver"`

> test "to_upper mutates the receiver"

 --- In-place mutation vs the pure `get_` form -------------------------------

 `@mutates` gives `to_upper`/`to_lower` two spellings: `calling c.to_upper`
 rewrites `c`, `calling c.get_to_upper` returns the value and leaves `c` alone.

### `"get_to_upper returns without mutating"`

> test "get_to_upper returns without mutating"

_Undocumented._

### `"to_lower mutates the receiver"`

> test "to_lower mutates the receiver"

_Undocumented._

### `"get_to_lower returns without mutating"`

> test "get_to_lower returns without mutating"

_Undocumented._

### `"a non-alphabetic byte is unchanged by either form"`

> test "a non-alphabetic byte is unchanged by either form"

_Undocumented._

### `"chained case mutations on one receiver"`

> test "chained case mutations on one receiver"

_Undocumented._

