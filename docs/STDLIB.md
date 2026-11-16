# STDLIB.md — Biblioteca estándar de PenguScript

**Versión:** `0.3.0` (mapa completo; módulos de auto-hospedaje añadidos)
**Estado:** especificación de superficie; los módulos marcados **CORE** se implementan primero para probar el compilador.
**Convención de nombres:** cada módulo lleva un nombre latino que evoca su función (`integrum` = entero, `floatem` = flotante, `verbum` = palabra, `capsa` = caja, `tabula` = tabla, `fasciculus` = conjunto, `numerus` = número, `fluxus` = flujo, `via` = camino, `exsecutor` = ejecutor, `ambitus` = entorno, `tempus` = tiempo, `nexus` = conexión, `vinculum` = vínculo, `frenum` = freno, `cellula` = célula, `somnium` = sueño, `proba` = prueba, `opera` = obras, `funis` = cuerda, `structura` = estructura; `libra` = balanza/TOML, `iason` = JSON, `digestum` = resumen/hash, `versio` = versión, `terminus` = límite/terminal, `globus` = esfera/glob, `archivum` = archivo, `rete` = red). La magia está en el nombre; la descripción está en los métodos. Los módulos de formato/protocolo conservan un alias funcional (`std.toml`, `std.json`, `std.digest`, `std.semver`, `std.term`, `std.glob`, `std.archive`, `std.net`) para que el código de aplicación no dependa del nombre latino.

**Criterio de cobertura:** la superficie se auditó contra Python 3.12, Rust 1.85, Kotlin 2.x, Go 1.22 y V 0.4. Incluye los métodos que un programa de aplicación usa de verdad; no copia APIs exóticas de plataforma ni traits de iteradores de Rust. Las operaciones de cada tipo se agrupan por familia (consulta, transformación, mutación, conversión) para que el mapa sea comparable entre lenguajes.

**Regla de encadenamiento:** los métodos de transformación que no consumen el receptor (`@` o `@mut`) devuelven `Self`, `&Self` o `&mut Self`; los de consulta devuelven su valor (`Bool`, `Usize`, `Option[...]`). Los métodos `@own` consumen el valor y no se encadenan después de ellos.

---

## Índice

1. [Sección CORE](#core)
2. [`integrum` — Int](#integrum)
3. [`floatem` — Float](#floatem)
4. [`littera` — Char](#littera)
5. [`verbum` — String / Str](#verbum)
6. [`capsa` — Vec](#capsa)
7. [`tabula` — Map](#tabula)
8. [`fasciculus` — Set](#fasciculus)
9. [`numerus` — Matemáticas](#numerus)
10. [`fluxus` — IO](#fluxus)
11. [`via` — FS](#via)
12. [`exsecutor` — Process](#exsecutor)
13. [`ambitus` — Env](#ambitus)
14. [`tempus` — Time](#tempus)
15. [`nexus` — FFI](#nexus)
16. [`vinculum` — Rc / Arc](#vinculum)
17. [`frenum` — Sync](#frenum)
18. [`cellula` — Cell / RefCell](#cellula)
19. [`somnium` — Async (diferido)](#somnium)
20. [`proba` — Test](#proba)
21. [`opera` — Ops](#opera)
22. [`funis` — Iter](#funis)
23. [`structura` — Colecciones avanzadas](#structura)
24. [`libra` — TOML](#libra)
25. [`iason` — JSON](#iason)
26. [`digestum` — Hash y checksums](#digestum)
27. [`versio` — SemVer](#versio)
28. [`terminus` — Terminal](#terminus)
29. [`globus` — Glob](#globus)
30. [`archivum` — Archivos tar/zip](#archivum)
31. [`rete` — Red, TLS y HTTP](#rete)
32. [Notas de implementación](#implementacion)

---

<a id="core"></a>
## 1. Sección CORE

Estos módulos y métodos son **indispensables** para que el lenguaje compile y ejecute programas reales. Se implementan primero, en este orden:

1. `integrum` (Int): operaciones básicas, `abs`, `pow`, `min`, `max`, `clamp`, `to_float`.
2. `floatem` (Float): aritmética, `sqrt`, `pow`, `abs`, `floor`, `ceil`, `round`, `sin`, `cos`, `tan`, `clamp`, `lerp`.
3. `verbum` (String/Str): `len`, `is_empty`, `chars`, `trim`, `split`, `contains`, `starts_with`, `ends_with`, `replace`, `parse`, `to_string`.
4. `capsa` (Vec): `new`, `with_capacity`, `push`, `pop`, `get`, `insert`, `remove`, `len`, `is_empty`, `iter`, `sort`, `contains`, `retain`.
5. `tabula` (Map): `new`, `insert`, `get`, `get_mut`, `remove`, `contains_key`, `len`, `iter`.
6. `fasciculus` (Set): `new`, `insert`, `contains`, `remove`, `len`, `iter`.
7. `fluxus` (IO): `print`, `println`, `format`, `read_line`, `stdin`, `stdout`, `stderr`.
8. `numerus` (Math): constantes `PI`, `E`, `TAU`; `sqrt`, `pow`, `sin`, `cos`, `tan`, `abs`, `floor`, `ceil`, `round`, `min`, `max`, `clamp`.
9. `proba` (Test): `assert`, `assert_eq`, `assert_ne`, `panic`.

### 1.1 CORE de auto-hospedaje (H3/H4)

Estos módulos no bloquean el compilador inicial, pero sí el CLI auto-hospedado:

1. `libra` (TOML): `parse`, `stringify`, `TomlTable.get`, `TomlTable.insert`.
2. `iason` (JSON): `parse`, `stringify`, `JsonObject.get`.
3. `digestum` (hash): `sha256`, `Sha256`, `sha256_hex`.
4. `versio` (SemVer): `Version.parse`, `VersionReq.parse`, `VersionReq.matches`.
5. `terminus` (terminal): `is_tty`, `size`, `enable_raw_mode`, `read_key`.
6. `globus` (glob): `glob`, `glob_in`.
7. `archivum` (archivos): `list`, `extract`, `create`, `ArchiveWriter.add_file`, `finish`.
8. `rete` (red): `TcpListener.bind`, `TcpStream.connect`, `TcpStream.read/write`, `TlsStream.connect`, `HttpClient.get`.
9. ~~`via.walk` (FS): recorrido recursivo para `globus`, `archivum` y el CLI.~~ Hecho en T1
   (`WalkOptions` + `walk`/`walk_files`/`walk_dirs`).
10. ~~`exsecutor` (Process): `which` y `Child.wait_with_output`.~~ Hecho en T3, junto con
    `Stdio` y la redirección de los tres flujos.

Todo lo demás puede diferirse sin bloquear un “hello world” y un CLI básico.

---

<a id="integrum"></a>
## 2. `integrum` — Int

**Archivo:** `std/integrum.pengu`
**Implementación:** `ritual Int` en `std` (permitido por D35). Núcleo: métodos intrínsecos del compilador.

> **Nota de implementación (A1).** En las firmas, `UInt` es el entero sin signo del
> ancho de `Int`, es decir `U32`; el nombre `UInt` sigue reservado como alias
> documental hasta que la sintaxis de alias de `std` lo cubra (fase A2). Las
> constantes `Int.MIN/MAX/BITS` y las funciones asociadas
> `Int.from_str`/`Int.from_str_radix` ya están implementadas.

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `abs` | `(@own) -> Int` | Valor absoluto; panic si es `MIN`. | ✅ |
| `pow` | `(@own, exp: UInt) -> Int` | Potencia entera; panic si desborda. | ✅ |
| `min` | `(@own, other: Int) -> Int` | Mínimo. | ✅ |
| `max` | `(@own, other: Int) -> Int` | Máximo. | ✅ |
| `clamp` | `(@own, lo: Int, hi: Int) -> Int` | Restringe al rango `[lo, hi]`. | ✅ |
| `signum` | `(@own) -> Int` | `-1`, `0` o `1`. | |
| `is_even` | `(@own) -> Bool` | Par. | |
| `is_odd` | `(@own) -> Bool` | Impar. | |
| `is_power_of_two` | `(@own) -> Bool` | Potencia de dos. | |
| `div_ceil` | `(@own, other: Int) -> Int` | División hacia arriba. | |
| `unsigned_abs` | `(@own) -> UInt` | Valor absoluto como `UInt`. | |
| `is_positive` | `(@own) -> Bool` | `> 0`. | |
| `is_negative` | `(@own) -> Bool` | `< 0`. | |
| `to_octal` | `(@) -> String` | Representación octal. | |
| `to_radix` | `(@, radix: UInt) -> String` | Representación en base 2..=36. | |
| `from_str_radix` | `(s: &Str, radix: UInt) -> Option[Int]` | Parseo en base explícita. | ✅ |
| `div_euclid` | `(@own, other: Int) -> Int` | División euclidiana. | |
| `rem_euclid` | `(@own, other: Int) -> Int` | Resto euclidiano. | |
| `abs_diff` | `(@own, other: Int) -> UInt` | Diferencia absoluta sin desbordar. | |
| `checked_div` | `(@own, other: Int) -> Option[Int]` | División con comprobación. | |
| `checked_rem` | `(@own, other: Int) -> Option[Int]` | Resto con comprobación. | |
| `checked_neg` | `(@own) -> Option[Int]` | Negación con comprobación. | |
| `checked_abs` | `(@own) -> Option[Int]` | Valor absoluto con comprobación. | |
| `checked_pow` | `(@own, exp: UInt) -> Option[Int]` | Potencia con comprobación. | |
| `wrapping_div` | `(@own, other: Int) -> Int` | División envolvente. | |
| `wrapping_rem` | `(@own, other: Int) -> Int` | Resto envolvente. | |
| `wrapping_neg` | `(@own) -> Int` | Negación envolvente. | |
| `wrapping_pow` | `(@own, exp: UInt) -> Int` | Potencia envolvente. | |
| `saturating_div` | `(@own, other: Int) -> Int` | División saturada. | |
| `saturating_pow` | `(@own, exp: UInt) -> Int` | Potencia saturada. | |
| `overflowing_add` | `(@own, other: Int) -> (Int, Bool)` | Suma y bandera de desbordamiento. | |
| `overflowing_sub` | `(@own, other: Int) -> (Int, Bool)` | Resta y bandera. | |
| `overflowing_mul` | `(@own, other: Int) -> (Int, Bool)` | Producto y bandera. | |
| `overflowing_neg` | `(@own) -> (Int, Bool)` | Negación y bandera. | |
| `count_ones` | `(@own) -> UInt` | Bits en 1. | |
| `count_zeros` | `(@own) -> UInt` | Bits en 0. | |
| `leading_zeros` | `(@own) -> UInt` | Ceros iniciales. | |
| `trailing_zeros` | `(@own) -> UInt` | Ceros finales. | |
| `rotate_left` | `(@own, n: UInt) -> Int` | Rotación a la izquierda. | |
| `rotate_right` | `(@own, n: UInt) -> Int` | Rotación a la derecha. | |
| `swap_bytes` | `(@own) -> Int` | Intercambia bytes. | |
| `reverse_bits` | `(@own) -> Int` | Invierte bits. | |
| `next_power_of_two` | `(@own) -> Int` | Siguiente potencia de 2. | |
| `checked_next_power_of_two` | `(@own) -> Option[Int]` | Siguiente potencia o `none`. | |
| `ilog2` | `(@own) -> UInt` | Logaritmo base 2 entero. | |
| `ilog10` | `(@own) -> UInt` | Logaritmo base 10 entero. | |
| `BITS` | `sigil` | Ancho en bits. | ✅ |
| `to_float` | `(@own) -> Float` | Conversión a `Float`. | ✅ |
| `to_string` | `(@) -> String` | Representación decimal. | ✅ |
| `to_hex` | `(@) -> String` | Representación hexadecimal. | |
| `to_binary` | `(@) -> String` | Representación binaria. | |
| `checked_add` | `(@own, other: Int) -> Option[Int]` | Suma con comprobación. | |
| `checked_sub` | `(@own, other: Int) -> Option[Int]` | Resta con comprobación. | |
| `checked_mul` | `(@own, other: Int) -> Option[Int]` | Producto con comprobación. | |
| `wrapping_add` | `(@own, other: Int) -> Int` | Suma envolvente. | |
| `wrapping_sub` | `(@own, other: Int) -> Int` | Resta envolvente. | |
| `wrapping_mul` | `(@own, other: Int) -> Int` | Producto envolvente. | |
| `saturating_add` | `(@own, other: Int) -> Int` | Suma saturada. | |
| `saturating_sub` | `(@own, other: Int) -> Int` | Resta saturada. | |
| `saturating_mul` | `(@own, other: Int) -> Int` | Producto saturado. | |
| `gcd` | `(@own, other: Int) -> Int` | Máximo común divisor. | |
| `lcm` | `(@own, other: Int) -> Int` | Mínimo común múltiplo. | |
| `factorial` | `(@own) -> Int` | Factorial; panic si desborda. | |
| `digits` | `(@own) -> Vec[U8]` | Dígitos decimales. | |
| `from_str` | `(s: &Str) -> Option[Int]` | Parseo; `none` si no es válido. | ✅ |
| `MIN` / `MAX` | `sigil` | Límites del tipo. | ✅ |

**Encadenamiento:** `42.abs().to_string().len()` funciona porque `abs` devuelve `Int`, `to_string` devuelve `String` y `len` es de `verbum`.

---

<a id="floatem"></a>
## 3. `floatem` — Float

**Archivo:** `std/floatem.pengu`
**Implementación:** `ritual Float` en `std`. Núcleo: intrínsecos.

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `abs` | `(@own) -> Float` | Valor absoluto. | ✅ |
| `sqrt` | `(@own) -> Float` | Raíz cuadrada. | ✅ |
| `pow` | `(@own, exp: Float) -> Float` | Potencia. | ✅ |
| `powi` | `(@own, exp: Int) -> Float` | Potencia entera. | |
| `sin` / `cos` / `tan` | `(@own) -> Float` | Trigonometría (radianes). | ✅ |
| `asin` / `acos` / `atan` | `(@own) -> Float` | Inversas. | |
| `atan2` | `(@own, x: Float) -> Float` | Ángulo de `(x, y)`. | |
| `sinh` / `cosh` / `tanh` | `(@own) -> Float` | Hiperbólicas. | |
| `floor` | `(@own) -> Float` | Suelo. | ✅ |
| `ceil` | `(@own) -> Float` | Techo. | ✅ |
| `round` | `(@own) -> Float` | Redondeo al más cercano. | ✅ |
| `trunc` | `(@own) -> Float` | Parte entera. | |
| `fract` | `(@own) -> Float` | Parte fraccionaria. | |
| `min` / `max` | `(@own, other: Float) -> Float` | Mínimo / máximo. | ✅ |
| `clamp` | `(@own, lo: Float, hi: Float) -> Float` | Restringe. | ✅ |
| `lerp` | `(@own, other: Float, t: Float) -> Float` | Interpolación lineal: `self + (other - self) * t`. | ✅ |
| `smoothstep` | `(@own, edge0: Float, edge1: Float) -> Float` | Suavizado de Hermite. | |
| `is_nan` | `(@own) -> Bool` | `NaN`. | |
| `is_infinite` | `(@own) -> Bool` | Infinito. | |
| `is_finite` | `(@own) -> Bool` | Finito. | |
| `is_sign_positive` | `(@own) -> Bool` | Signo positivo (incluye `+0.0`). | |
| `is_sign_negative` | `(@own) -> Bool` | Signo negativo (incluye `-0.0`). | |
| `classify` | `(@own) -> FloatClass` | `NaN`, `Infinite`, `Zero`, `Subnormal`, `Normal`. | |
| `to_bits` | `(@own) -> U64` | Representación IEEE 754. | |
| `from_bits` | `(bits: U64) -> Float` | Reconstruye desde bits. | ✅ |
| `next_up` | `(@own) -> Float` | Siguiente valor representable. | |
| `next_down` | `(@own) -> Float` | Valor representable anterior. | |
| `round_ties_even` | `(@own) -> Float` | Redondeo bancario. | |
| `exp` | `(@own) -> Float` | `e^self`. | |
| `exp2` | `(@own) -> Float` | `2^self`. | |
| `ln` | `(@own) -> Float` | Logaritmo natural. | |
| `log2` | `(@own) -> Float` | Logaritmo base 2. | |
| `log10` | `(@own) -> Float` | Logaritmo base 10. | |
| `log` | `(@own, base: Float) -> Float` | Logaritmo en base arbitraria. | |
| `ln_1p` | `(@own) -> Float` | `ln(1 + self)` preciso. | |
| `exp_m1` | `(@own) -> Float` | `e^self - 1` preciso. | |
| `cbrt` | `(@own) -> Float` | Raíz cúbica. | |
| `hypot` | `(@own, other: Float) -> Float` | `sqrt(self² + other²)` sin desbordar. | |
| `recip` | `(@own) -> Float` | `1 / self`. | |
| `signum` | `(@own) -> Float` | `-1.0`, `0.0` o `1.0`. | |
| `copysign` | `(@own, sign: Float) -> Float` | Magnitud propia, signo de `sign`. | |
| `mul_add` | `(@own, a: Float, b: Float) -> Float` | `self * a + b` con una sola operación. | |
| `sin_cos` | `(@own) -> (Float, Float)` | Seno y coseno a la vez. | |
| `asinh` | `(@own) -> Float` | Seno hiperbólico inverso. | |
| `acosh` | `(@own) -> Float` | Coseno hiperbólico inverso. | |
| `atanh` | `(@own) -> Float` | Tangente hiperbólica inversa. | |
| `EPSILON` | `sigil` | Diferencia mínima representable. | ✅ |
| `MIN` / `MAX` | `sigil` | Valores finitos mínimo/máximo. | ✅ |
| `MIN_POSITIVE` | `sigil` | Menor positivo normal. | ✅ |
| `to_radians` | `(@own) -> Float` | Grados → radianes. | |
| `to_degrees` | `(@own) -> Float` | Radianes → grados. | |
| `to_int` | `(@own) -> Int` | Trunca a entero. | ✅ |
| `to_string` | `(@) -> String` | Representación decimal. | ✅ |
| `total_cmp` | `(@, other: &Float) -> Ordering` | Orden total (maneja `NaN`). | |
| `NAN` / `INFINITY` / `NEG_INFINITY` | `sigil` | Constantes. | ✅ |
| `from_str` | `(s: &Str) -> Option[Float]` | Parseo; `none` si no es válido. | ✅ |

`FloatClass` es un `enchanting` de `std.floatem`: `NaN`, `Infinite`, `Zero`, `Subnormal`, `Normal`.

> **Nota de implementación (A1–A2).** Las constantes asociadas
> (`Float.EPSILON`, `Float.MAX`, …), las funciones asociadas
> (`Float.from_str`, `Float.from_bits`) y las variantes calificadas
> (`FloatClass.NaN` en expresión y en patrón) ya están implementadas.
> `classify` devuelve `FloatClass.NaN`/`Infinite`/`Zero`/`Subnormal`/`Normal`, y
> un `match` sobre el resultado es exhaustivo sin `else`.

**Encadenamiento:** `(3.0).sqrt().lerp(4.0, 0.5).to_int()`.

---

<a id="littera"></a>
## 4. `littera` — Char

**Archivo:** `std/littera.pengu`
**Implementación:** `ritual Char` en `std`.

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `is_ascii` | `(@own) -> Bool` | ASCII. | |
| `is_alphabetic` | `(@own) -> Bool` | Letra Unicode. | |
| `is_numeric` | `(@own) -> Bool` | Dígito Unicode. | |
| `is_alphanumeric` | `(@own) -> Bool` | Letra o dígito. | |
| `is_whitespace` | `(@own) -> Bool` | Espacio. | |
| `is_uppercase` | `(@own) -> Bool` | Mayúscula. | |
| `is_lowercase` | `(@own) -> Bool` | Minúscula. | |
| `to_uppercase` | `(@own) -> Char` | Mayúscula. | |
| `to_lowercase` | `(@own) -> Char` | Minúscula. | |
| `to_digit` | `(@own, radix: UInt) -> Option[UInt]` | Valor numérico. | |
| `to_string` | `(@) -> String` | String de un carácter. | ✅ |
| `len_utf8` | `(@own) -> Usize` | Bytes UTF-8. | |
| `len_utf16` | `(@own) -> Usize` | Unidades UTF-16. | |
| `encode_utf8` | `(@own, buf: &mut [U8]) -> Usize` | Codifica en un buffer. | |
| `escape_default` | `(@own) -> String` | Escape legible para depuración. | |
| `escape_unicode` | `(@own) -> String` | Escape `\u{...}`. | |
| `is_control` | `(@own) -> Bool` | Carácter de control. | |
| `is_punctuation` | `(@own) -> Bool` | Puntuación Unicode. | |
| `is_symbol` | `(@own) -> Bool` | Símbolo Unicode. | |
| `is_math` | `(@own) -> Bool` | Símbolo matemático. | |
| `is_currency` | `(@own) -> Bool` | Símbolo monetario. | |
| `is_ascii_digit` | `(@own) -> Bool` | Dígito ASCII. | |
| `is_ascii_alphabetic` | `(@own) -> Bool` | Letra ASCII. | |
| `is_ascii_alphanumeric` | `(@own) -> Bool` | Letra o dígito ASCII. | |
| `is_ascii_whitespace` | `(@own) -> Bool` | Espacio ASCII. | |
| `is_ascii_control` | `(@own) -> Bool` | Control ASCII. | |
| `is_ascii_punctuation` | `(@own) -> Bool` | Puntuación ASCII. | |
| `is_ascii_hexdigit` | `(@own) -> Bool` | Dígito hexadecimal ASCII. | |
| `is_ascii_graphic` | `(@own) -> Bool` | ASCII imprimible no espacio. | |
| `is_ascii_uppercase` | `(@own) -> Bool` | Mayúscula ASCII. | |
| `is_ascii_lowercase` | `(@own) -> Bool` | Minúscula ASCII. | |
| `to_ascii_uppercase` | `(@own) -> Char` | Mayúscula ASCII. | |
| `to_ascii_lowercase` | `(@own) -> Char` | Minúscula ASCII. | |
| `eq_ignore_ascii_case` | `(@own, other: Char) -> Bool` | Igualdad sin distinguir mayúsculas. | |
| `from_u32` | `(code: U32) -> Option[Char]` | Desde escalar Unicode. | ✅ |
| `from_digit` | `(digit: U32, radix: UInt) -> Option[Char]` | Desde dígito en base. | ✅ |

> **Nota de implementación (A1).** `Char.from_u32` y `Char.from_digit` ya están
> implementadas como funciones asociadas. `encode_utf8` sigue diferido porque
> necesita un slice mutable (`&mut [U8]`), pendiente de la fase A5.

---

<a id="veritas"></a>
## 4.1. `veritas` — Bool

**Archivo:** `std/veritas.pengu`
**Implementación:** `ritual Bool` en `std`.

| Método | Firma | Descripción |
|---|---|---|
| `switch` | `(@own) -> Bool` | Negación como método (`not @`). |
| `to_int` | `(@own) -> Int` | `1` si es `true`, `0` si no. |
| `to_string` | `(@) -> String` | `"true"` / `"false"`. |
| `xor` | `(@own, other: Bool) -> Bool` | O exclusivo. |
| `implies` | `(@own, other: Bool) -> Bool` | Implicación lógica (`not @ or other`). |
| `nand` | `(@own, other: Bool) -> Bool` | `not (@ and other)`. |
| `nor` | `(@own, other: Bool) -> Bool` | `not (@ or other)`. |
| `then_int` | `(@own, when_true: Int, when_false: Int) -> Int` | Elige un entero. |
| `to_float` | `(@own) -> Float` | `1.0` / `0.0`. |

> **Nota de implementación (S1).** `to_string` es intrínseco (`b_to_string`)
> porque un literal `"true"` es `Str` y el retorno declarado es `String`: la
> coerción `Str → String` todavía no existe (riesgo R1 del plan). El resto de
> métodos son cuerpo Pengu puro.

---

<a id="verbum"></a>
## 5. `verbum` — String / Str

**Archivo:** `std/verbum.pengu`
**Implementación:** `ritual Str` (vista) y `ritual String` (owned) en `std`. `String` delega en `Str` cuando es posible.

### 5.1 `Str` (vista prestada)

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `len` | `(@) -> Usize` | Longitud en bytes. | ✅ |
| `is_empty` | `(@) -> Bool` | Vacío. | ✅ |
| `chars` | `(@) -> Iter[Char]` | Iterador de caracteres. | ✅ |
| `bytes` | `(@) -> Iter[U8]` | Iterador de bytes. | ✅ |
| `char_indices` | `(@) -> Iter[(Usize, Char)]` | Índice + carácter. | ✅ |
| `trim` | `(@) -> Str` | Sin espacios al inicio/fin. | ✅ |
| `trim_start` | `(@) -> Str` | Sin espacios al inicio. | |
| `trim_end` | `(@) -> Str` | Sin espacios al final. | |
| `split` | `(@, sep: &Str) -> Vec[Str]` | Divide por separador. | ✅ |
| `split_whitespace` | `(@) -> Vec[Str]` | Divide por espacios. | ✅ |
| `lines` | `(@) -> Vec[Str]` | Líneas. | |
| `starts_with` | `(@, prefix: &Str) -> Bool` | Prefijo. | ✅ |
| `ends_with` | `(@, suffix: &Str) -> Bool` | Sufijo. | ✅ |
| `contains` | `(@, pat: &Str) -> Bool` | Subcadena. | ✅ |
| `find` | `(@, pat: &Str) -> Option[Usize]` | Posición de la primera aparición. | |
| `rfind` | `(@, pat: &Str) -> Option[Usize]` | Última aparición. | |
| `replace` | `(@, from: &Str, to: &Str) -> String` | Reemplazo. | ✅ |
| `to_lowercase` | `(@) -> String` | Minúsculas. | ✅ |
| `to_uppercase` | `(@) -> String` | Mayúsculas. | ✅ |
| `parse[T]` | `(@) -> Result[T, ParseError]` | Parseo genérico. | ✅ |
| `get` | `(@, range: Range[Usize]) -> Option[Str]` | Subcadena por bytes. | ✅ |
| `chars_count` | `(@) -> Usize` | Número de caracteres. | |
| `splitn` | `(@, n: Usize, sep: &Str) -> Vec[Str]` | Divide como máximo en `n` partes. | |
| `rsplit` | `(@, sep: &Str) -> Vec[Str]` | Divide desde el final. | |
| `rsplitn` | `(@, n: Usize, sep: &Str) -> Vec[Str]` | Divide desde el final, máximo `n`. | |
| `split_terminator` | `(@, sep: &Str) -> Vec[Str]` | Como `split`, sin el vacío final. | |
| `split_ascii_whitespace` | `(@) -> Vec[Str]` | Divide por espacios ASCII. | |
| `matches` | `(@, pat: &Str) -> Iter[Str]` | Apariciones solapadas no. | |
| `match_indices` | `(@, pat: &Str) -> Iter[(Usize, Str)]` | Posición y aparición. | |
| `replacen` | `(@, from: &Str, to: &Str, n: Usize) -> String` | Reemplaza como máximo `n`. | |
| `strip_prefix` | `(@, prefix: &Str) -> Option[Str]` | Quita prefijo si existe. | |
| `strip_suffix` | `(@, suffix: &Str) -> Option[Str]` | Quita sufijo si existe. | |
| `trim_matches` | `(@, ch: Char) -> Str` | Recorta el carácter en ambos extremos. | |
| `trim_start_matches` | `(@, ch: Char) -> Str` | Recorta al inicio. | |
| `trim_end_matches` | `(@, ch: Char) -> Str` | Recorta al final. | |
| `is_char_boundary` | `(@, index: Usize) -> Bool` | Índice cae en frontera UTF-8. | |
| `as_bytes` | `(@) -> Vec[U8]` | Bytes UTF-8 (copia: no hay slices en la superficie). | ✅ |
| `to_ascii_lowercase` | `(@) -> String` | Minúsculas solo ASCII. | |
| `to_ascii_uppercase` | `(@) -> String` | Mayúsculas solo ASCII. | |
| `eq_ignore_ascii_case` | `(@, other: &Str) -> Bool` | Igualdad ASCII sin mayúsculas. | |
| `capitalize` | `(@) -> String` | Primera letra mayúscula, resto minúsculas. | |
| `title` | `(@) -> String` | Capitaliza cada palabra. | |
| `center` | `(@, width: Usize, fill: Char) -> String` | Centra en `width`. | |
| `ljust` | `(@, width: Usize, fill: Char) -> String` | Alinea a la izquierda. | |
| `rjust` | `(@, width: Usize, fill: Char) -> String` | Alinea a la derecha. | |
| `zfill` | `(@, width: Usize) -> String` | Rellena con ceros a la izquierda. | |
| `partition` | `(@, sep: &Str) -> (Str, Str, Str)` | Antes, separador y después. | |
| `rpartition` | `(@, sep: &Str) -> (Str, Str, Str)` | Partición desde el final. | |
| `splitlines` | `(@) -> Vec[Str]` | Líneas sin terminadores. | |
| `isalpha` | `(@) -> Bool` | Solo letras. | |
| `isdigit` | `(@) -> Bool` | Solo dígitos. | |
| `isalnum` | `(@) -> Bool` | Letras o dígitos. | |
| `isspace` | `(@) -> Bool` | Solo espacios. | |
| `islower` | `(@) -> Bool` | Tiene minúsculas y ninguna mayúscula. | |
| `isupper` | `(@) -> Bool` | Tiene mayúsculas y ninguna minúscula. | |
| `istitle` | `(@) -> Bool` | Formato título. | |
| `starts_with_ignore_case` | `(@, prefix: &Str) -> Bool` | Prefijo sin distinguir mayúsculas. | |
| `to_string` | `(@) -> String` | Copia owned. | ✅ |

### 5.2 `String` (owned)

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `new` | `() -> String` | Vacío. | ✅ |
| `with_capacity` | `(n: Usize) -> String` | Capacidad reservada. | |
| `from` | `(s: &Str) -> String` | Copia. | ✅ |
| `push` | `(@mut, c: Char)` | Añade carácter. | ✅ |
| `push_str` | `(@mut, s: &Str)` | Añade string. | ✅ |
| `pop` | `(@mut) -> Option[Char]` | Quita último carácter. | |
| `clear` | `(@mut)` | Vacía. | |
| `insert` | `(@mut, idx: Usize, c: Char)` | Inserta carácter. | |
| `insert_str` | `(@mut, idx: Usize, s: &Str)` | Inserta string. | |
| `remove` | `(@mut, idx: Usize) -> Char` | Quita carácter. | |
| `truncate` | `(@mut, new_len: Usize)` | Trunca. | |
| `as_str` | `(@) -> &Str` | Vista. | ✅ |
| `into_bytes` | `(@own) -> Vec[U8]` | Bytes. | |
| `from_utf8` | `(bytes: Vec[U8]) -> Result[String, FromUtf8Error]` | Desde bytes. | |
| `repeat` | `(@, n: Usize) -> String` | Repite. | |
| `reserve` | `(@mut, additional: Usize)` | Reserva capacidad. | |
| `shrink_to_fit` | `(@mut)` | Ajusta capacidad. | |
| `capacity` | `(@) -> Usize` | Capacidad actual. | |
| `as_bytes` | `(@) -> Vec[U8]` | Bytes UTF-8 (copia: no hay slices en la superficie). | ✅ |
| `split_at` | `(@, mid: Usize) -> (Str, Str)` | Divide en dos vistas. | ✅ |
| `split_off` | `(@mut, at: Usize) -> String` | Divide y devuelve la cola. | |
| `drain` | `(@mut, range: Range[Usize]) -> Drain[Char]` | Extrae un rango. | |
| `replace_range` | `(@mut, range: Range[Usize], replace_with: &Str)` | Reemplaza un rango. | |
| `retain` | `(@mut, f: (Char) -> Bool)` | Conserva caracteres que cumplen. | |
| `from_utf8_lossy` | `(bytes: &[U8]) -> String` | Decodifica reemplazando inválidos. | |
| `extend` | `(@mut, other: &Str)` | Añade otro string. | |

**Encadenamiento:** `"  hola, mundo  ".trim().split(",").len()`.

**Nota de implementación (S2, A6).** `std/verbum.pengu` implementa 53 métodos de
`Str` y 22 de `String` como intrínsecos `abi "pengu"` (`s_*`/`str_*`): en esta
fase no hay `funis` (S7) para iterar `chars()`, así que la clase dominante es
intrínseca en lugar de cuerpo puro. `get(range)`, `split_at`, `replace_range` y
`as_bytes` ya usan `Range[Usize]` (los límites se escriben `0_usize..4_usize`).
Desde S7 `chars`, `bytes` y `char_indices` devuelven un `Iter[…]` (ver §22).
Siguen diferidos por necesitar tipos que aún no existen: `matches`/`match_indices`
(iterador de `Str` con vida ligada al origen), `parse[T]` (genérico de método),
`split_at`/`get(range)` sobre `Range` no contiguo, `String.from_utf8*`,
`String.drain` y `String.retain`.

---

<a id="capsa"></a>
### 5.3 `optio` — `Option[T]` y `Result[T, E]`

**Archivo:** `std/optio.pengu`
**Estado:** parcial en S5. `Option[T]` y `Result[T, E]` son tipos integrados; hasta S5 no
tenían **ningún** método declarado, así que ni siquiera `is_some()` compilaba. Este módulo
declara los métodos cuyo nombre y firma coinciden con un método de Rust, de forma que el
backend los pasa directamente (clase T3, cuerpo `panic("passthrough")`).

| Elemento | Firma | Descripción |
|---|---|---|
| `Option.is_some` | `(@) -> Bool` | Tiene valor. |
| `Option.is_none` | `(@) -> Bool` | Está vacío. |
| `Option.unwrap_or` | `(@, fallback: T) -> T` | Valor o sustituto. |
| `Option.unwrap_or_default` | `(@) -> T` | Valor o `T.default()`. |
| `Option.take` | `(@mut) -> Option[T]` | Extrae y deja `none`. |
| `Option.replace` | `(@mut, value: T) -> Option[T]` | Sustituye y devuelve el anterior. |
| `Result.is_ok` | `(@) -> Bool` | Es `ok`. |
| `Result.is_err` | `(@) -> Bool` | Es `err`. |
| `Result.unwrap_or` | `(@, fallback: T) -> T` | Valor o sustituto. |
| `Result.unwrap_or_default` | `(@) -> T` | Valor o `T.default()`. |

`map`, `and_then`, `ok_or`, `unwrap`, `expect`, `or_with`/`and_with` y el resto de la
superficie de Rust quedan para S7 (limitación N34): necesitan un trait de extensión en el
prelude (`impl<T> Option<T>` es `E0116` en Rust) y, varios de ellos, un parámetro de tipo
propio del método. Para consumir un `Option`/`Result` hoy se usa `match` con los patrones
`some(v)` / `none` / `ok(v)` / `err(e)`, que sí funcionan desde S5.

---

## 6. `capsa` — Vec

**Archivo:** `std/capsa.pengu`
**Implementación:** `ritual[T] Vec[T]` en `std`. Paso directo a `Vec` de Rust.

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `new` | `() -> Vec[T]` | Vacío. | ✅ |
| `with_capacity` | `(n: Usize) -> Vec[T]` | Capacidad. | ✅ |
| `push` | `(@mut, value: T)` | Añade al final. | ✅ |
| `pop` | `(@mut) -> Option[T]` | Quita del final. | ✅ |
| `get` | `(@, index: Usize) -> Option[&T]` | Acceso seguro. | ✅ |
| `get_mut` | `(@mut, index: Usize) -> Option[&mut T]` | Acceso mutable seguro. | ✅ |
| `insert` | `(@mut, index: Usize, value: T)` | Inserta en posición. | ✅ |
| `remove` | `(@mut, index: Usize) -> T` | Quita en posición. | ✅ |
| `len` | `(@) -> Usize` | Longitud. | ✅ |
| `is_empty` | `(@) -> Bool` | Vacío. | ✅ |
| `clear` | `(@mut)` | Vacía. | |
| `truncate` | `(@mut, len: Usize)` | Trunca. | |
| `reserve` | `(@mut, additional: Usize)` | Reserva. | |
| `capacity` | `(@) -> Usize` | Capacidad. | |
| `shrink_to_fit` | `(@mut)` | Ajusta capacidad. | |
| `first` | `(@) -> Option[&T]` | Primer elemento. | |
| `last` | `(@) -> Option[&T]` | Último elemento. | |
| `iter` | `(@) -> Iter[&T]` | Iterador. | ✅ |
| `iter_mut` | `(@mut) -> Iter[&mut T]` | Iterador mutable. | |
| `into_iter` | `(@own) -> Iter[T]` | Iterador que consume. | |
| `sort` | `(@mut)` | Ordena (requiere `Ord`). | ✅ |
| `sort_by` | `(@mut, cmp: (T, T) -> Ordering)` | Ordena con comparador. | |
| `sort_by_key` | `(@mut, key: (T) -> K)` | Ordena por clave. | |
| `contains` | `(@, value: &T) -> Bool` | Contiene (requiere `Eq`). | ✅ |
| `first_mut` | `(@mut) -> Option[&mut T]` | Primer elemento mutable. | |
| `last_mut` | `(@mut) -> Option[&mut T]` | Último elemento mutable. | |
| `as_slice` | `(@) -> &[T]` | Vista como slice. | |
| `as_mut_slice` | `(@mut) -> &mut [T]` | Vista mutable. | |
| `into_boxed_slice` | `(@own) -> Box[[T]]` | Convierte en slice boxed. | |
| `swap` | `(@mut, a: Usize, b: Usize)` | Intercambia dos posiciones. | |
| `swap_remove` | `(@mut, index: Usize) -> T` | Quita intercambiando con el último. | |
| `resize` | `(@mut, new_len: Usize, value: T)` | Redimensiona rellenando. | |
| `resize_with` | `(@mut, new_len: Usize, f: () -> T)` | Redimensiona generando valores. | |
| `fill` | `(@mut, value: T)` | Rellena todo. | |
| `drain` | `(@mut, range: Range[Usize]) -> Drain[T]` | Extrae un rango. | |
| `splice` | `(@mut, range: Range[Usize], replace_with: Vec[T]) -> Splice[T]` | Reemplaza un rango. | |
| `split_off` | `(@mut, at: Usize) -> Vec[T]` | Divide y devuelve la cola. | |
| `append` | `(@mut, other: &mut Vec[T])` | Mueve todos los elementos. | |
| `sort_unstable` | `(@mut)` | Ordena sin estabilidad. | |
| `sort_unstable_by` | `(@mut, cmp: (T, T) -> Ordering)` | Ordena con comparador. | |
| `sort_unstable_by_key` | `(@mut, key: (T) -> K)` | Ordena por clave. | |
| `binary_search_by` | `(@, cmp: (T) -> Ordering) -> Result[Usize, Usize]` | Búsqueda binaria con comparador. | |
| `binary_search_by_key` | `(@, key: &K, f: (T) -> K) -> Result[Usize, Usize]` | Búsqueda por clave. | |
| `dedup_by` | `(@mut, same_bucket: (T, T) -> Bool)` | Deduplica con comparador. | |
| `dedup_by_key` | `(@mut, key: (T) -> K)` | Deduplica por clave. | |
| `rotate_left` | `(@mut, mid: Usize)` | Rota a la izquierda. | |
| `rotate_right` | `(@mut, mid: Usize)` | Rota a la derecha. | |
| `is_sorted` | `(@) -> Bool` | Está ordenado. | |
| `is_sorted_by` | `(@, cmp: (T, T) -> Ordering) -> Bool` | Ordenado según comparador. | |
| `is_sorted_by_key` | `(@, key: (T) -> K) -> Bool` | Ordenado por clave. | |
| `partition_point` | `(@, pred: (T) -> Bool) -> Usize` | Punto de partición binario. | |
| `starts_with` | `(@, prefix: &[T]) -> Bool` | Prefijo. | |
| `ends_with` | `(@, suffix: &[T]) -> Bool` | Sufijo. | |
| `concat` | `(@) -> Vec[T]` | Concatena `Vec[Vec[T]]`. | |
| `retain` | `(@mut, f: (T) -> Bool)` | Conserva los que cumplen. | ✅ |
| `dedup` | `(@mut)` | Elimina duplicados consecutivos. | |
| `binary_search` | `(@, value: &T) -> Result[Usize, Usize]` | Búsqueda binaria. | |
| `reverse` | `(@mut)` | Invierte. | |
| `extend` | `(@mut, other: Vec[T])` | Extiende. | |
| `split_at` | `(@, mid: Usize) -> (&[T], &[T])` | Divide. | |
| `chunks` | `(@, size: Usize) -> Iter[&[T]]` | Tramos. | |
| `windows` | `(@, size: Usize) -> Iter[&[T]]` | Ventanas. | |
| `join` | `(@, sep: &Str) -> String` | Une strings (requiere `T: Show`). | |
| ~~`sum`~~ | — | Se usa `xs.iter().sum()` (§22). | |
| ~~`product`~~ | — | Se usa `xs.iter().product()` (pendiente). | |
| ~~`min` / `max`~~ | — | Se usan `xs.iter().min()` / `.max()` (§22). | |
| `clone` | `(@) -> Vec[T]` | Copia profunda. | ✅ |
| `to_string` | `(@) -> String` | Representación (requiere `Show`). | |

**Nota de implementación (S3).** `std/capsa.pengu` implementa 55 métodos como
**paso directo** al `Vec` de Rust: el cuerpo es un marcador `panic("passthrough")`
que el backend nunca emite y la llamada se traduce a `(vec).metodo(args)` o a un
ayudante genérico del runtime (`vec_sum`, `vec_join`, `vec_sort_by`…). Cero
indirección: el coste y la semántica son exactamente los de Rust. Los callbacks
reciben `T` por valor (como en esta tabla) y el runtime los adapta al `&T` de
Rust copiando (`T: Clone`); para `Int`, `Float`, `Char`, `Bool` y punteros la
copia es gratuita. Se difieren a S7: `iter`, `iter_mut`, `into_iter`, `drain`,
`splice`, `chunks`, `windows`. Se difieren por necesitar genéricos de método
(`K` además de `T`): `sort_by_key`, `sort_unstable_by_key`, `is_sorted_by_key`,
`dedup_by_key`, `binary_search_by_key`.

Los comparadores de `sort_by`, `sort_unstable_by`, `max_by`, `min_by`, etc.
devuelven `Ordering` y hoy se pueden escribir con lambdas (fase A3):

```pengu
bind xs = Vec[3, 1, 4, 2]
xs.sort_by((a: Int, b: Int) =>
    if a < b then
        Less
    elseif a > b then
        Greater
    else
        Equal
)
```

`Less`, `Equal` y `Greater` son valores de `Ordering` (fase A2). Dentro de los
paréntesis de la llamada las líneas son continuación, así que también vale la
forma de una línea:
`xs.sort_by((a: Int, b: Int) => if a < b then Less elseif a > b then Greater else Equal)`.

---

<a id="tabula"></a>
## 7. `tabula` — Map

**Archivo:** `std/tabula.pengu`
**Implementación:** `ritual[K, V] Map[K, V]` en `std`. Claves: `K: Eq + Hash`.
Paso directo a `HashMap` de Rust.

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `new` | `() -> Map[K, V]` | Vacío. | ✅ |
| `with_capacity` | `(n: Usize) -> Map[K, V]` | Capacidad. | |
| `insert` | `(@mut, key: K, value: V) -> Option[V]` | Inserta. | ✅ |
| `get` | `(@, key: &K) -> Option[&V]` | Acceso. | ✅ |
| `get_mut` | `(@mut, key: &K) -> Option[&mut V]` | Acceso mutable. | ✅ |
| `remove` | `(@mut, key: &K) -> Option[V]` | Quita. | ✅ |
| `contains_key` | `(@, key: &K) -> Bool` | Contiene clave. | ✅ |
| `len` | `(@) -> Usize` | Número de pares. | ✅ |
| `is_empty` | `(@) -> Bool` | Vacío. | ✅ |
| `clear` | `(@mut)` | Vacía. | |
| `capacity` | `(@) -> Usize` | Capacidad. | |
| `reserve` | `(@mut, additional: Usize)` | Reserva capacidad. | |
| `shrink_to_fit` | `(@mut)` | Ajusta capacidad. | |
| `retain` | `(@mut, f: (K, &V) -> Bool)` | Conserva pares que cumplen. | |
| `drain` | `(@mut) -> Iter[(K, V)]` | Extrae todos los pares. | |
| `remove_entry` | `(@mut, key: &K) -> Option[(K, V)]` | Quita y devuelve clave/valor. | |
| `get_key_value` | `(@, key: &K) -> Option[(&K, &V)]` | Clave y valor. | |
| `get_or_insert` | `(@mut, key: K, default: V) -> &mut V` | Inserta si falta. | |
| `get_or_insert_with` | `(@mut, key: K, f: () -> V) -> &mut V` | Inserta si falta, con closure. | |
| `keys` | `(@) -> Iter[&K]` | Claves. | |
| `values` | `(@) -> Iter[&V]` | Valores. | |
| `values_mut` | `(@mut) -> Iter[&mut V]` | Valores mutables. | |
| `iter` | `(@) -> Iter[(&K, &V)]` | Pares. | ✅ |
| `iter_mut` | `(@mut) -> Iter[(&K, &mut V)]` | Pares mutables. | |
| `entry` | `(@mut, key: K) -> Entry[K, V]` | Entrada para `or_insert`. | |
| `extend` | `(@mut, other: Map[K, V])` | Extiende. | |
| `clone` | `(@) -> Map[K, V]` | Copia profunda (requiere `K: Clone, V: Clone`). | |

**Nota de implementación (S3).** `std/tabula.pengu` implementa 20 métodos como
paso directo a `HashMap` (más `to_string`, que muestra `{clave: valor}` con las
entradas ordenadas). `retain` recibe `(K, V)` —la spec decía `(K, &V)`— porque
`&V` no es utilizable sin auto-deref en esta fase; el runtime copia clave y
valor (`K: Clone, V: Clone`). Se difieren a S7 (necesitan `Iter[T]`/`Entry`):
`drain`, `keys`, `values`, `values_mut`, `iter`, `iter_mut`, `entry`.

### 7.1 `Entry`

| Método | Firma | Descripción |
|---|---|---|
| `key` | `(@) -> &K` | Clave de la entrada. |
| `or_insert` | `(@own, default: V) -> &mut V` | Inserta si falta. |
| `or_insert_with` | `(@own, f: () -> V) -> &mut V` | Inserta si falta, con closure. |
| `or_default` | `(@own) -> &mut V` | Inserta `V.default()` si falta. |
| `and_modify` | `(@own, f: (&mut V) -> Unit) -> Entry[K, V]` | Modifica si existe. |

---

<a id="fasciculus"></a>
## 8. `fasciculus` — Set

**Archivo:** `std/fasciculus.pengu`
**Implementación:** `ritual Set[T]` en `std`. `T: Eq + Hash`.

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `new` | `() -> Set[T]` | Vacío. | ✅ |
| `with_capacity` | `(n: Usize) -> Set[T]` | Capacidad. | |
| `insert` | `(@mut, value: T) -> Bool` | Inserta; `true` si era nuevo. | ✅ |
| `contains` | `(@, value: &T) -> Bool` | Contiene. | ✅ |
| `remove` | `(@mut, value: &T) -> Bool` | Quita. | ✅ |
| `len` | `(@) -> Usize` | Tamaño. | ✅ |
| `is_empty` | `(@) -> Bool` | Vacío. | ✅ |
| `clear` | `(@mut)` | Vacía. | |
| `iter` | `(@) -> Iter[&T]` | Iterador. | ✅ |
| `get` | `(@, value: &T) -> Option[&T]` | Referencia al elemento. | |
| `take` | `(@mut, value: &T) -> Option[T]` | Quita y devuelve el elemento. | |
| `replace` | `(@mut, value: T) -> Option[T]` | Inserta y devuelve el anterior. | |
| `drain` | `(@mut) -> Iter[T]` | Extrae todos los elementos. | |
| `retain` | `(@mut, f: (T) -> Bool)` | Conserva los que cumplen. | |
| `extend` | `(@mut, other: Set[T])` | Añade otro set. | |
| `symmetric_difference` | `(@, other: &Set[T]) -> Set[T]` | Diferencia simétrica. | |
| `is_disjoint` | `(@, other: &Set[T]) -> Bool` | Sin elementos comunes. | |
| `difference_update` | `(@mut, other: &Set[T])` | Quita los de `other`. | |
| `intersection_update` | `(@mut, other: &Set[T])` | Conserva la intersección. | |
| `symmetric_difference_update` | `(@mut, other: &Set[T])` | Deja la diferencia simétrica. | |
| `union` | `(@, other: &Set[T]) -> Set[T]` | Unión. | |
| `intersection` | `(@, other: &Set[T]) -> Set[T]` | Intersección. | |
| `difference` | `(@, other: &Set[T]) -> Set[T]` | Diferencia. | |
| `is_subset` | `(@, other: &Set[T]) -> Bool` | Subconjunto. | |
| `is_superset` | `(@, other: &Set[T]) -> Bool` | Superconjunto. | |
| `clone` | `(@) -> Set[T]` | Copia. | |

**Nota de implementación (S3).** `std/fasciculus.pengu` implementa 25 métodos
como paso directo a `HashSet`. Las operaciones de conjunto (`union`,
`intersection`, `difference`, `symmetric_difference` y sus `*_update`) se
resuelven con ayudantes genéricos porque `HashSet` de Rust las expone como
operadores o como métodos aún inestables en la versión mínima (1.85); se
implementan con `retain` y los operadores `|`, `&`, `-`, `^` sobre referencias.
`retain` recibe `(T) -> Bool` y copia (`T: Clone`). Se difieren a S7: `iter`,
`drain`.

---

<a id="numerus"></a>
## 9. `numerus` — Matemáticas

**Archivo:** `std/numerus.pengu`
**Implementación:** funciones libres en `std.numerus`; constantes en `sigil`.

### 9.1 Constantes

| Nombre | Tipo | Valor |
|---|---|---|
| `PI` | `Float` | `3.141592653589793` |
| `E` | `Float` | `2.718281828459045` |
| `TAU` | `Float` | `6.283185307179586` |
| `INFINITY` | `Float` | `inf` |
| `NEG_INFINITY` | `Float` | `-inf` |
| `NAN` | `Float` | `NaN` |

### 9.2 Funciones

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `abs` | `(x: Float) -> Float` | Valor absoluto. | ✅ |
| `sqrt` | `(x: Float) -> Float` | Raíz cuadrada. | ✅ |
| `cbrt` | `(x: Float) -> Float` | Raíz cúbica. | |
| `pow` | `(x: Float, y: Float) -> Float` | Potencia. | ✅ |
| `exp` | `(x: Float) -> Float` | `e^x`. | |
| `ln` | `(x: Float) -> Float` | Logaritmo natural. | |
| `log10` / `log2` | `(x: Float) -> Float` | Logaritmos. | |
| `sin` / `cos` / `tan` | `(x: Float) -> Float` | Trigonometría. | ✅ |
| `asin` / `acos` / `atan` | `(x: Float) -> Float` | Inversas. | |
| `atan2` | `(y: Float, x: Float) -> Float` | Ángulo. | |
| `sinh` / `cosh` / `tanh` | `(x: Float) -> Float` | Hiperbólicas. | |
| `floor` / `ceil` / `round` | `(x: Float) -> Float` | Redondeo. | ✅ |
| `trunc` | `(x: Float) -> Float` | Parte entera. | |
| `fract` | `(x: Float) -> Float` | Parte fraccionaria. | |
| `min` / `max` | `(a: Float, b: Float) -> Float` | Mínimo / máximo. | ✅ |
| `clamp` | `(x: Float, lo: Float, hi: Float) -> Float` | Restringe. | ✅ |
| `lerp` | `(a: Float, b: Float, t: Float) -> Float` | Interpolación lineal. | ✅ |
| `smoothstep` | `(edge0: Float, edge1: Float, x: Float) -> Float` | Suavizado. | |
| `to_radians` / `to_degrees` | `(x: Float) -> Float` | Conversión. | |
| `gcd` / `lcm` | `(a: Int, b: Int) -> Int` | MCD / MCM. | |
| `factorial` | `(n: Int) -> Int` | Factorial. | |
| `comb` / `perm` | `(n: Int, k: Int) -> Int` | Combinaciones / permutaciones. | |
| `is_nan` / `is_infinite` / `is_finite` | `(x: Float) -> Bool` | Clasificación. | |
| `signum` | `(x: Float) -> Float` | `-1.0`, `0.0`, `1.0`. | |
| `copysign` | `(x: Float, y: Float) -> Float` | Signo de `y`, magnitud de `x`. | |
| `hypot` | `(x: Float, y: Float) -> Float` | `sqrt(x² + y²)`. | |
| `exp2` | `(x: Float) -> Float` | `2^x`. | |
| `ln_1p` | `(x: Float) -> Float` | `ln(1 + x)` preciso. | |
| `exp_m1` | `(x: Float) -> Float` | `e^x - 1` preciso. | |
| `log` | `(x: Float, base: Float) -> Float` | Logaritmo en base arbitraria. | |
| `log1p` | `(x: Float) -> Float` | `ln(1 + x)`; alias de `ln_1p`. | |
| `recip` | `(x: Float) -> Float` | `1 / x`. | |
| `mul_add` | `(a: Float, b: Float, c: Float) -> Float` | `a * b + c` con una operación. | |
| `sin_cos` | `(x: Float) -> (Float, Float)` | Seno y coseno. | |
| `asinh` / `acosh` / `atanh` | `(x: Float) -> Float` | Hiperbólicas inversas. | |
| `fmod` | `(x: Float, y: Float) -> Float` | Resto con signo de `x`. | |
| `remainder` | `(x: Float, y: Float) -> Float` | Resto IEEE. | |
| `modf` | `(x: Float) -> (Float, Float)` | Parte entera y fraccionaria. | |
| `frexp` | `(x: Float) -> (Float, Int)` | Mantisa y exponente. | |
| `ldexp` | `(x: Float, exp: Int) -> Float` | `x * 2^exp`. | |
| `nextafter` | `(x: Float, y: Float) -> Float` | Siguiente valor hacia `y`. | |
| `isclose` | `(a: Float, b: Float, rel_tol: Float, abs_tol: Float) -> Bool` | Comparación aproximada. | |
| `isqrt` | `(n: UInt) -> UInt` | Raíz cuadrada entera. | |
| `prod` | `(values: &[Int]) -> Int` | Producto de una secuencia. | |
| `dist` | `(a: (Float, Float), b: (Float, Float)) -> Float` | Distancia euclidiana; alias de `distance`. | |
| `degrees` / `radians` | `(x: Float) -> Float` | Conversión angular. | |
| `erf` / `erfc` | `(x: Float) -> Float` | Función error y complementaria. | |
| `gamma` / `lgamma` | `(x: Float) -> Float` | Gamma y log-gamma. | |
| `EPSILON` | `sigil` | Épsilon de `Float`. | |
| `MIN` / `MAX` | `sigil` | Límites finitos. | |
| `distance` | `(a: (Float, Float), b: (Float, Float)) -> Float` | Distancia euclidiana 2D. | |
| `angle_between` | `(a: (Float, Float), b: (Float, Float)) -> Float` | Ángulo entre vectores 2D. | |
| `normalize` | `(v: (Float, Float)) -> (Float, Float)` | Vector unitario 2D. | |
| `dot` | `(a: (Float, Float), b: (Float, Float)) -> Float` | Producto punto 2D. | |
| `cross` | `(a: (Float, Float), b: (Float, Float)) -> Float` | Producto cruz 2D (escalar). | |

**Nota:** los vectores 3D y cuaterniones se pueden agregar más adelante; este mapa cubre lo esencial para físicas 2D y videojuegos.

**Nota de implementación (S4).** `std/numerus.pengu` implementa las 9
constantes `sigil` y 65 funciones libres. La clase de cada una:

- **Intrínseco `abi "pengu"`** (43): las que dependen de `libm` o de bits del
  `f64` — `sqrt`, `cbrt`, `pow`, `exp`, `exp2`, `exp_m1`, `ln`, `ln_1p`,
  `log10`, `log2`, trigonométricas e hiperbólicas, `floor`, `ceil`, `round`,
  `trunc`, `fract`, `copysign`, `hypot`, `mul_add`, `sin_cos`, `fmod`,
  `remainder`, `modf`, `frexp`, `ldexp`, `nextafter`, `erf`, `erfc`, `gamma`,
  `lgamma`, `isqrt`. `erf`/`erfc` usan la aproximación de Abramowitz–Stegun
  7.1.26 y `gamma` usa Lanczos g=7 (9 coeficientes), porque Rust no las trae.
- **Cuerpo PenguScript puro** (22): `abs`, `min`, `max`, `clamp`, `lerp`,
  `smoothstep`, `to_radians`, `to_degrees`, `degrees`, `radians`, `signum`,
  `log`, `log1p`, `recip`, `isclose`, `gcd`, `lcm`, `factorial`, `comb`,
  `perm`, `distance`, `dist`, `dot`, `cross`, `angle_between`, `normalize`,
  `is_nan`/`is_infinite`/`is_finite` (delegando en los métodos de `Float`).

Todas las funciones y las constantes llevan `unveil` (los ítems de un `scroll`
son privados por defecto). `sigil` no admite llamadas a funciones, así que
`INFINITY`, `NEG_INFINITY` y `NAN` se escriben como divisiones constantes
(`1.0 / 0.0`, `-1.0 / 0.0`, `0.0 / 0.0`).

Los vectores 2D viajan como tuplas `(Float, Float)`; no hay tipo `Vec2` en la
superficie.


---

<a id="fluxus"></a>
## 10. `fluxus` — IO

**Archivo:** `std/fluxus.pengu`
**Implementación:** funciones intrínsecas del compilador (`print`, `println`, `format`) y `pact Reader`/`Writer` para streams.

### 10.1 Funciones

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `print` | `[T: Show](value: T)` | Escribe sin salto. | ✅ |
| `println` | `[T: Show](value: T)` | Escribe con salto. | ✅ |
| `format` | `(template: &Str) -> String` | Interpolación resuelta por el compilador. | ✅ |
| `read_line` | `() -> Result[String, IoError]` | Lee una línea de stdin. | ✅ |
| `stdin` | `() -> Stdin` | Lector de stdin (concreto). | ✅ |
| `stdout` | `() -> Stdout` | Escritor de stdout (concreto). | ✅ |
| `stderr` | `() -> Stderr` | Escritor de stderr (concreto). | ✅ |
| `eprint` | `[T: Show](value: T)` | Escribe en stderr sin salto. | |
| `eprintln` | `[T: Show](value: T)` | Escribe en stderr con salto. | |
| `flush` | `() -> Result[(), IoError]` | Vacía stdout. | |
| `read_to_string` | `[R: Reader](reader: &mut R) -> Result[String, IoError]` | Lee todo. | |
| `read_to_end` | `[R: Reader](reader: &mut R, buf: &mut Vec[U8]) -> Result[Usize, IoError]` | Lee hasta EOF. | |
| `write_all` | `[W: Writer](writer: &mut W, buf: &[U8]) -> Result[(), IoError]` | Escribe todo. | |
| `copy` | `[R: Reader, W: Writer](reader: &mut R, writer: &mut W) -> Result[U64, IoError]` | Copia hasta EOF. | |

### 10.2 `Reader`

`pact Reader`:
| Método | Firma | Descripción |
|---|---|---|
| `read` | `(@mut, buf: &mut [U8]) -> Result[Usize, IoError]` | Lee bytes. |
| `read_to_string` | `(@mut, buf: &mut String) -> Result[Usize, IoError]` | Lee a string. |
| `read_line` | `(@mut) -> Result[String, IoError]` | Lee línea. |
| `read_to_end` | `(@mut, buf: &mut Vec[U8]) -> Result[Usize, IoError]` | Lee hasta EOF. |
| `read_exact` | `(@mut, buf: &mut [U8]) -> Result[(), IoError]` | Lee exactamente el buffer. |
| `bytes` | `(@mut) -> Iter[Result[U8, IoError]]` | Bytes. |
| `lines` | `(@mut) -> Iter[Result[String, IoError]]` | Líneas. |

### 10.3 `Writer`

`pact Writer`:
| Método | Firma | Descripción |
|---|---|---|
| `write` | `(@mut, buf: &[U8]) -> Result[Usize, IoError]` | Escribe bytes. |
| `write_str` | `(@mut, s: &Str) -> Result[(), IoError]` | Escribe string. |
| `flush` | `(@mut) -> Result[(), IoError]` | Vacía buffer. |
| `write_all` | `(@mut, buf: &[U8]) -> Result[(), IoError]` | Escribe todo. |
| `write_fmt` | `(@mut, template: &Str) -> Result[(), IoError]` | Escribe interpolación. |

### 10.4 Buffered

| Tipo | Firma | Descripción |
|---|---|---|
| `BufReader[T]` | `rune BufReader[T]` | Lector con buffer. |
| `BufReader.new` | `(inner: T) -> BufReader[T]` | Crea. |
| `BufReader.with_capacity` | `(capacity: Usize, inner: T) -> BufReader[T]` | Crea con capacidad. |
| `BufReader.into_inner` | `(@own) -> T` | Devuelve el lector interno. |
| `BufReader.buffer` | `(@) -> &[U8]` | Buffer pendiente. |
| `BufReader.read` | `(@mut, buf: &mut [U8]) -> Result[Usize, IoError]` | Lee. |
| `BufReader.read_line` | `(@mut) -> Result[String, IoError]` | Lee línea. |
| `BufReader.lines` | `(@mut) -> Iter[Result[String, IoError]]` | Líneas. |
| `BufWriter[T]` | `rune BufWriter[T]` | Escritor con buffer. |
| `BufWriter.new` | `(inner: T) -> BufWriter[T]` | Crea. |
| `BufWriter.with_capacity` | `(capacity: Usize, inner: T) -> BufWriter[T]` | Crea con capacidad. |
| `BufWriter.into_inner` | `(@own) -> Result[T, IntoInnerError]` | Devuelve el escritor interno. |
| `BufWriter.flush` | `(@mut) -> Result[(), IoError]` | Vacía el buffer. |
| `BufWriter.write` | `(@mut, buf: &[U8]) -> Result[Usize, IoError]` | Escribe. |
| `BufWriter.write_all` | `(@mut, buf: &[U8]) -> Result[(), IoError]` | Escribe todo. |

### 10.5 Standard streams

| Tipo | Firma | Descripción |
|---|---|---|
| `Stdin` | `rune` opaco | Lector de stdin. |
| `Stdout` | `rune` opaco | Escritor de stdout. |
| `Stderr` | `rune` opaco | Escritor de stderr. |
| `Stdin.read_line` | `(@mut) -> Result[String, IoError]` | Lee línea. |
| `Stdin.read` | `(@mut, buf: &mut [U8]) -> Result[Usize, IoError]` | Lee bytes. |
| `Stdout.write` | `(@mut, buf: &[U8]) -> Result[Usize, IoError]` | Escribe bytes. |
| `Stdout.flush` | `(@mut) -> Result[(), IoError]` | Vacía. |
| `Stderr.write` | `(@mut, buf: &[U8]) -> Result[Usize, IoError]` | Escribe bytes. |
| `Stderr.flush` | `(@mut) -> Result[(), IoError]` | Vacía. |

`Stdin`/`Stdout`/`Stderr` y `File` implementan `Reader`/`Writer`; por eso se pueden pasar a funciones genéricas como `read_to_string[R: Reader]`. `BufReader[T]` requiere `T: Reader` y `BufWriter[T]` requiere `T: Writer`; el backend verifica el bound.

---


**Nota de implementación (S4).** `std/fluxus.pengu` implementa:

- `rune IoError` con el campo `message: String` (público por `unveil`).
- `read_line() -> Result[String, IoError]`, `read_stdin_to_string()`,
  `write_stdout(text)`, `write_stderr(text)`, `flush_stdout()`,
  `flush_stderr()`.
- `pact Reader` (`read`, `read_to_string`, `read_line`) y `pact Writer`
  (`write`, `write_str`, `flush`), declarados para que `via` los implemente.

`print`, `println`, `eprint`, `eprintln` y `format` siguen siendo primitivas
del lenguaje; no hacen falta importaciones.

**Diferido a S5:** los tipos opacos `Stdin`/`Stdout`/`Stderr`, `BufReader[T]`,
`BufWriter[T]`, `read_to_end`, `write_all`, `copy` y las implementaciones de
`Reader`/`Writer`. Necesitan `via` (ficheros) y genéricos de `rune`, que llegan
con la fase de sistema.

---

<a id="via"></a>
## 11. `via` — FS

**Archivo:** `std/via.pengu`
**Estado:** implementado en S5. Las rutas son `&Str` (no hay todavía tipo `Path` opaco;
ver limitación A5 en `scratch/LIMITATIONS_AUDIT.md`), así que las firmas usan texto.

Tipos implementados: `unveil rune IoError { message: String }`, `unveil rune FileInfo { len: U64,
is_file: Bool, is_dir: Bool, is_symlink: Bool, readonly: Bool, modified_ms: Option[Int] }`,
`unveil rune File { handle: U64 }` y `unveil rune DirEntry { path: String, is_dir: Bool }`.
Los cuatro implementan `Show` con `unveil ritual X for Show` (los runes no derivan `Show`).

| Elemento | Firma | Descripción | CORE |
|---|---|---|---|
| `exists` | `(path: &Str) -> Bool` | Existe (sigue enlaces). | ✅ |
| `metadata` | `(path: &Str) -> Result[FileInfo, IoError]` | Metadatos sin seguir el enlace final. | ✅ |
| `read_to_string` | `(path: &Str) -> Result[String, IoError]` | Lee archivo como texto. | ✅ |
| `read_bytes` | `(path: &Str) -> Result[Vec[U8], IoError]` | Lee bytes. | ✅ |
| `write_string` | `(path: &Str, contents: &Str) -> Result[Unit, IoError]` | Escribe texto (trunca). | ✅ |
| `write_bytes` | `(path: &Str, contents: Vec[U8]) -> Result[Unit, IoError]` | Escribe bytes. | ✅ |
| `append_string` | `(path: &Str, contents: &Str) -> Result[Unit, IoError]` | Añade texto. | ✅ |
| `create_dir` | `(path: &Str) -> Result[Unit, IoError]` | Crea un directorio. | ✅ |
| `create_dir_all` | `(path: &Str) -> Result[Unit, IoError]` | Crea el árbol de directorios. | ✅ |
| `remove_file` | `(path: &Str) -> Result[Unit, IoError]` | Borra archivo. | ✅ |
| `remove_dir` | `(path: &Str) -> Result[Unit, IoError]` | Borra directorio vacío. | ✅ |
| `remove_dir_all` | `(path: &Str) -> Result[Unit, IoError]` | Borra directorio recursivo. | ✅ |
| `rename` | `(from: &Str, to: &Str) -> Result[Unit, IoError]` | Renombra/mueve. | ✅ |
| `copy` | `(from: &Str, to: &Str) -> Result[U64, IoError]` | Copia y devuelve bytes. | ✅ |
| `canonicalize` | `(path: &Str) -> Result[String, IoError]` | Ruta absoluta resuelta. | ✅ |
| `read_link` | `(path: &Str) -> Result[String, IoError]` | Destino de un enlace. | ✅ |
| `symlink` | `(original: &Str, link: &Str) -> Result[Unit, IoError]` | Enlace simbólico. | ✅ |
| `hard_link` | `(original: &Str, link: &Str) -> Result[Unit, IoError]` | Enlace duro. | ✅ |
| `is_file` / `is_dir` / `is_symlink` | `(path: &Str) -> Bool` | Consultas de tipo. | ✅ |
| `set_readonly` | `(path: &Str, readonly: Bool) -> Result[Unit, IoError]` | Permisos de solo lectura. | ✅ |
| `read_dir` | `(path: &Str) -> Result[Vec[DirEntry], IoError]` | Entradas de un directorio. | ✅ |
| `walk_names` | `(root: &Str) -> Result[Vec[String], IoError]` | Rutas bajo `root` (ordenadas). | ✅ |
| `walk_files` | `(root: &Str) -> Result[Vec[String], IoError]` | Solo archivos. | ✅ |
| `walk_dirs` | `(root: &Str) -> Result[Vec[String], IoError>` | Solo directorios. | ✅ |
| `current_dir` | `() -> Result[String, IoError]` | Directorio actual. | ✅ |
| `set_current_dir` | `(path: &Str) -> Result[Unit, IoError]` | Cambia el directorio actual. | ✅ |
| `temp_dir` | `() -> String` | Directorio temporal. | ✅ |
| `which` | `(program: &Str) -> Option[String]` | Busca en `PATH`. | ✅ |
| `join` | `(a: &Str, b: &Str) -> String` | Une rutas. | ✅ |
| `parent` | `(path: &Str) -> Option[String]` | Directorio padre. | ✅ |
| `file_name` | `(path: &Str) -> Option[String]` | Último componente. | ✅ |
| `file_stem` | `(path: &Str) -> Option[String]` | Nombre sin extensión. | ✅ |
| `extension` | `(path: &Str) -> Option[String]` | Extensión. | ✅ |
| `is_absolute` | `(path: &Str) -> Bool` | Ruta absoluta. | ✅ |
| `File.open` | `(path: &Str) -> Result[File, IoError]` | Abre para leer. | ✅ |
| `File.create` | `(path: &Str) -> Result[File, IoError]` | Crea/trunca para escribir. | ✅ |
| `File.append` | `(path: &Str) -> Result[File, IoError]` | Abre para añadir. | ✅ |
| `File.read_to_string` | `(@mut) -> Result[String, IoError]` | Lee todo el archivo. | ✅ |
| `File.read_to_end` | `(@mut) -> Result[Vec[U8], IoError]` | Lee bytes. | ✅ |
| `File.write_str` | `(@mut, text: &Str) -> Result[Unit, IoError]` | Escribe texto. | ✅ |
| `File.write_all` | `(@mut, data: Vec[U8]) -> Result[Unit, IoError]` | Escribe bytes. | ✅ |
| `File.flush` | `(@mut) -> Result[Unit, IoError]` | Vacía el buffer. | ✅ |
| `File.seek` | `(@mut, position: U64) -> Result[U64, IoError]` | Posiciona. | ✅ |
| `File.seek_from_end` | `(@mut, offset: U64) -> Result<U64, IoError>` | Posiciona desde el final. | ✅ |
| `File.set_len` | `(@mut, len: U64) -> Result[Unit, IoError]` | Trunca/expande. | ✅ |
| `File.metadata` | `(@) -> Result[FileInfo, IoError]` | Metadatos. | ✅ |
| `File.close` | `(@own)` | Cierra el descriptor. | ✅ |
| `File.open_with` | `(path: &Str, options: OpenOptions) -> Result[File, IoError]` | Abre con opciones. | ✅ |
| `File.read_bytes` | `(@mut, count: U64) -> Result[Vec[U8], IoError]` | Lee hasta `count` bytes. | ✅ |
| `File.write_bytes` | `(@mut, data: Vec[U8]) -> Result[Usize, IoError]` | Escribe bytes y devuelve cuántos. | ✅ |
| `File.sync_all` / `sync_data` | `(@mut) -> Result[Unit, IoError]` | Sincroniza con el disco. | ✅ |
| `File.try_clone` | `(@) -> Result[File, IoError]` | Duplica el descriptor. | ✅ |
| `File.modified_ms` | `(@) -> Result[Option[I64], IoError]` | Última modificación (ms desde la época). | ✅ |
| `OpenOptions.new` | `() -> OpenOptions` | Opciones de apertura. | ✅ |
| `OpenOptions.read` / `write` / `append` / `create` / `truncate` | `(@mut, allow: Bool) -> &mut OpenOptions` | Ajusta una bandera y devuelve el receptor para encadenar. | ✅ |
| `OpenOptions.open` | `(@, path: &Str) -> Result[File, IoError]` | Abre con las banderas dadas. | ✅ |

El registro de descriptores vive en el runtime (`VIA_FILES: Mutex<Vec<Option<std::fs::File>>>`)
porque el lenguaje aún no tiene tipos opacos; `File` guarda un `U64` y `close` libera la entrada.

**Nota (T1).** Además de la tabla anterior, `via` expone rutas y recorrido configurable:

| Elemento | Firma | Descripción | CORE |
|---|---|---|---|
| `Path.new` | `(text: &Str) -> Path` | Construye una ruta. | ✅ |
| `Path.join` | `(@, other: Path) -> PathBuf` | Une (el argumento se mueve). | ✅ |
| `Path.parent` | `(@) -> Option[Path]` | Padre. | ✅ |
| `Path.file_name` / `extension` / `file_stem` | `(@) -> Option[String]` | Componentes. | ✅ |
| `Path.is_absolute` / `is_relative` | `(@) -> Bool` | Absoluta/relativa. | ✅ |
| `Path.exists` / `is_file` / `is_dir` / `is_symlink` | `(@) -> Bool` | Consultas. | ✅ |
| `Path.starts_with` | `(@, base: Path) -> Bool` | Prefijo. | ✅ |
| `Path.ends_with` | `(@, suffix: &Str) -> Bool` | Sufijo. | ✅ |
| `Path.strip_prefix` | `(@, base: Path) -> Option[Path]` | Quita prefijo. | ✅ |
| `Path.components` | `(@) -> Vec[String]` | Componentes. | ✅ |
| `Path.display` / `to_string_lossy` / `to_string` | `(@) -> String` | Texto. | ✅ |
| `Path.as_path` / `input.metadata` / `read_to_string` … | varias | Atajos de FS sobre la ruta. | ✅ |
| `PathBuf.new` / `from_path` | `(…) -> PathBuf` | Construcción. | ✅ |
| `PathBuf.push` / `push_path` | `(@mut, …) -> Unit` | Añade componente. | ✅ |
| `PathBuf.pop` | `(@mut) -> Bool` | Quita el último (devuelve si hubo). | ✅ |
| `PathBuf.set_extension` | `(@mut, ext: &Str) -> Bool` | Cambia extensión. | ✅ |
| `PathBuf.with_extension` | `(@, ext: &Str) -> PathBuf` | Copia con otra extensión. | ✅ |
| `WalkOptions.new` | `() -> WalkOptions` | Opciones de recorrido. | ✅ |
| `WalkOptions.follow_links` / `include_hidden` / `max_depth` | `(@mut, …) -> Unit` | Configuración. | ✅ |
| `WalkOptions.walk` / `walk_files` / `walk_dirs` | `(@, root: &Str) -> Result[Vec[DirEntry], IoError]` | Recorrido ordenado; detecta ciclos si sigue enlaces. | ✅ |
| `walk_with` | `(root: &Str, options: WalkOptions, mode: Int) -> Result[Vec[DirEntry], IoError]` | Recorrido con modo (0 todo, 1 ficheros, 2 directorios). | ✅ |
| `DirEntry.file_name` / `is_file` / `is_symlink` / `len` | varias | Datos de la entrada. | ✅ |
| `DirEntry.file_type` / `metadata` | `(@) -> …` | Tipo y metadatos. | ✅ |
| `FileType.is_file` / `is_dir` / `is_symlink` | `(@) -> Bool` | Tipo. | ✅ |
| `Permissions.readonly` | `(@) -> Bool` | Solo lectura. | ✅ |
| `file_type` / `permissions` / `set_permissions` | `(path: &Str, …)` | Vistas y cambios de metadatos. | ✅ |
| `modified_ms` / `created_ms` / `accessed_ms` | `(path: &Str) -> Result[Option[I64], IoError]` | Marcas en milisegundos desde la época Unix. | ✅ |

`Path`/`PathBuf` guardan el texto y delegan en el runtime: el lenguaje no tiene
prestatarios implícitos, así que las mutaciones (`pop`, `set_extension`) devuelven
un `Bool` en vez de encadenar. La ruta se **mueve** al pasarla a `join`,
`starts_with` o `strip_prefix`; hay variantes con texto si se quiere conservar.

---

<a id="exsecutor"></a>
## 12. `exsecutor` — Process

**Archivo:** `std/exsecutor.pengu`
**Estado:** completo en T3 (S5b + T3). Acepta `Stdio` para redirigir los tres flujos.

Tipos: `unveil rune ExsecutorError { message: String }`, `unveil rune ExitStatus { code: Option[Int],
success: Bool }`, `unveil rune Output { status: ExitStatus, stdout: Vec[U8], stderr: Vec[U8] }`,
`unveil rune Command { program: String, args: Vec[String], cwd: Option[String], envs: Vec[String],
clear_env: Bool, stdin_mode: Int, stdout_mode: Int, stderr_mode: Int }`,
`unveil rune Stdio { mode: Int }` y `unveil rune Child { handle: U64 }`. Todos implementan `Show`.

`ExitStatus`, `Output` y `Command` exponen sus datos como **campos** (`out.status.success`,
`out.stdout`), no como métodos.

| Elemento | Firma | Descripción | CORE |
|---|---|---|---|
| `run` | `(program: &Str) -> Result[Output, ExsecutorError]` | Ejecuta y captura. | ✅ |
| `run_args` | `(program: &Str, args: Vec[String]) -> Result[Output, ExsecutorError]` | Ejecuta con argumentos. | ✅ |
| `status` | `(program: &Str) -> Result[ExitStatus, ExsecutorError]` | Ejecuta y espera. | ✅ |
| `status_args` | `(program: &Str, args: Vec[String]) -> Result[ExitStatus, ExsecutorError]` | Igual con argumentos. | ✅ |
| `which` | `(program: &Str) -> Option[String]` | Busca en `PATH`. | ✅ |
| `exit` | `(code: Int) -> Unit` | Termina el proceso. | ✅ |
| `args` | `() -> Vec[String]` | Argumentos (igual que `ambitus::args`). | ✅ |
| `Stdio.stdio_piped` | `() -> Stdio` | Conecta el flujo a un pipe. | ✅ |
| `Stdio.stdio_inherit` | `() -> Stdio` | Hereda el flujo del padre. | ✅ |
| `Stdio.stdio_discard` | `() -> Stdio` | Descarta el flujo (`/dev/null`). | ✅ |
| `Command.new` | `(program: &Str) -> Command` | Crea un comando (flujos por defecto). | ✅ |
| `Command.arg` | `(@mut, value: &Str) -> Unit` | Añade un argumento. | ✅ |
| `Command.args` | `(@mut, values: Vec[String]) -> Unit` | Añade varios. | ✅ |
| `Command.env` | `(@mut, key: &Str, value: &Str) -> Unit` | Variable de entorno. | ✅ |
| `Command.envs` | `(@mut, values: Vec[String]) -> Unit` | Variables en pares clave/valor. | ✅ |
| `Command.env_remove` | `(@mut, key: &Str) -> Unit` | Quita una variable. | ✅ |
| `Command.env_clear` | `(@mut) -> Unit` | Limpia el entorno heredado. | ✅ |
| `Command.current_dir` | `(@mut, path: &Str) -> Unit` | Directorio de trabajo. | ✅ |
| `Command.stdin` / `stdout` / `stderr` | `(@mut, stdio: Stdio) -> Unit` | Redirige el flujo. | ✅ |
| `Command.get_program` | `(@) -> String` | Programa configurado. | ✅ |
| `Command.get_args` | `(@) -> Vec[String]` | Argumentos configurados. | ✅ |
| `Command.get_envs` | `(@) -> Vec[String]` | Entorno configurado. | ✅ |
| `Command.get_current_dir` | `(@) -> Option[String]` | Directorio configurado. | ✅ |
| `Command.program_name` | `(@) -> String` | Alias de `get_program`. | ✅ |
| `Command.run` | `(@own) -> Result[Output, ExsecutorError]` | Ejecuta y captura. | ✅ |
| `Command.status` | `(@own) -> Result[ExitStatus, ExsecutorError]` | Ejecuta y espera. | ✅ |
| `Command.spawn` | `(@own) -> Result[Child, ExsecutorError]` | Lanza sin esperar. | ✅ |
| `Child.wait` | `(@mut) -> Result[ExitStatus, ExsecutorError]` | Espera a que termine. | ✅ |
| `Child.try_wait` | `(@mut) -> Result[Option[ExitStatus], ExsecutorError]` | Espera sin bloquear. | ✅ |
| `Child.kill` | `(@mut) -> Result[Unit, ExsecutorError]` | Mata el proceso. | ✅ |
| `Child.process_id` | `(@) -> Result[U64, ExsecutorError]` | PID del hijo (`id` es nombre reservado por la mono). | ✅ |
| `Child.write_stdin` | `(@mut, data: Vec[U8]) -> Result[U64, ExsecutorError]` | Escribe en el pipe de entrada. | ✅ |
| `Child.close_stdin` | `(@mut) -> Result[Unit, ExsecutorError]` | Cierra la entrada (envía EOF). | ✅ |
| `Child.read_stdout` | `(@mut, count: U64) -> Result[Vec[U8], ExsecutorError]` | Lee hasta `count` bytes. | ✅ |
| `Child.read_stderr` | `(@mut, count: U64) -> Result[Vec[U8], ExsecutorError]` | Igual sobre `stderr`. | ✅ |
| `Child.wait_with_output` | `(@mut) -> Result[Output, ExsecutorError]` | Lee los pipes restantes y espera. | ✅ |

Ejemplo (patrón `cat` con pipes):

```pengu
summon std::exsecutor

grimoire
    morph cmd = exsecutor::Command.new("cat")
    cmd.stdin(exsecutor::Stdio.stdio_piped())
    cmd.stdout(exsecutor::Stdio.stdio_piped())
    match cmd.spawn()
        when ok(child) then
            child.write_stdin(Vec[104_u8, 111_u8, 108_u8, 97_u8])
            child.close_stdin()
            match child.wait_with_output()
                when ok(salida) then print(salida.stdout.len())
                when err(e) then print(e.message)
        when err(e) then print(e.message)
```

Notas de implementación: el modo `0` de `Stdio` significa «lo que decida Rust» (los flujos se
redirigen a pipe en `run`/`status` y se heredan en `spawn`); `1` pipe, `2` descarte y `3` herencia.
Los pipes viven en una tabla global `EXSEC_CHILDREN` junto al `Child`; leer o escribir mientras el
proceso está bloqueado mantiene el mutex (no hay hilos todavía).

---

<a id="ambitus"></a>
## 13. `ambitus` — Env

**Archivo:** `std/ambitus.pengu`
**Estado:** implementado en S5. `VarError { message: String }` implementa `Show`.

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `var` | `(key: &Str) -> Result[String, VarError]` | Lee una variable. | ✅ |
| `set_var` | `(key: &Str, value: &Str) -> Unit` | Escribe una variable. | ✅ |
| `remove_var` | `(key: &Str) -> Unit` | Borra una variable. | ✅ |
| `vars` | `() -> Vec[String]` | Todas, como `"CLAVE=valor"` ordenadas. | ✅ |
| `var_os` | `(key: &Str) -> Option[String]` | Variable como `Option` (pérdida `lossy` si no es UTF-8). | ✅ |
| `args` | `() -> Vec[String]` | Argumentos del programa. | ✅ |
| `args_os` | `() -> Vec[String]` | Argumentos sin decodificar (pérdida `lossy`). | ✅ |
| `current_dir` | `() -> Result[String, VarError]` | Directorio actual. | ✅ |
| `set_current_dir` | `(path: &Str) -> Result[Unit, VarError]` | Cambia el directorio. | ✅ |
| `temp_dir` | `() -> String` | Directorio temporal. | ✅ |
| `home_dir` | `() -> Option[String]` | Home (`HOME`/`USERPROFILE`). | ✅ |
| `current_exe` | `() -> Result[String, VarError]` | Ruta del ejecutable. | ✅ |
| `join_paths` | `(parts: Vec[String]) -> Result[String, VarError]` | Une con el separador del sistema. | ✅ |
| `split_paths` | `(paths: &Str) -> Vec[String]` | Separa una lista de rutas. | ✅ |
| `os` | `() -> String` | `"linux"`, `"macos"`, `"windows"`… | ✅ |
| `arch` | `() -> String` | `"x86_64"`, `"aarch64"`… | ✅ |
| `family` | `() -> String` | `"unix"`, `"windows"`, `"wasm"`. | ✅ |
| `exe_suffix` | `() -> String` | Sufijo de ejecutable (`.exe` en Windows). | ✅ |
| `dll_prefix` / `dll_suffix` | `() -> String` | Prefijo/sufijo de biblioteca dinámica. | ✅ |

**Nota:** `set_var`/`remove_var` mutan el entorno del proceso, que en Rust 2024 es `unsafe`
porque otros hilos podrían leerlo. El lenguaje aún no tiene hilos, así que el runtime las
ejecuta en un bloque `unsafe` interno documentado.

---

<a id="tempus"></a>
## 14. `tempus` — Time

**Archivo:** `std/tempus.pengu`
**Estado:** implementado en S5 con resolución de milisegundos (`Duration` guarda `millis: Int`),
lo que evita depender de conversiones `Int`↔`U64` que el lenguaje aún no tiene.

Tipos: `unveil rune Duration { millis: Int }`, `unveil rune Instant { micros: Int }`,
`unveil rune SystemTime { millis: Int }` y
`unveil rune SystemTimeError { message: String, duration_millis: Int }`.
Los cuatro implementan `Show`.

| Elemento | Firma | Descripción | CORE |
|---|---|---|---|
| `now` | `() -> SystemTime` | Tiempo del sistema. | ✅ |
| `now_micros` | `() -> Int` | Microsegundos desde la época Unix. | ✅ |
| `monotonic_micros` | `() -> Int` | Microsegundos monótonos desde el arranque. | ✅ |
| `sleep_ms` | `(millis: Int) -> Unit` | Duerme el hilo. | ✅ |
| `sleep_nanos` | `(nanos: U64) -> Unit` | Duerme con precisión de nanosegundos. | ✅ |
| `unix_epoch` | `() -> SystemTime` | Época Unix. | ✅ |
| `duration_secs` | `(seconds: Int) -> Duration` | Azúcar de `Duration.from_secs`. | ✅ |
| `duration_millis` | `(millis: Int) -> Duration` | Azúcar de `Duration.from_millis`. | ✅ |
| `Duration.from_secs` | `(seconds: Int) -> Duration` | Segundos. | ✅ |
| `Duration.from_millis` | `(millis: Int) -> Duration` | Milisegundos. | ✅ |
| `Duration.from_micros` | `(micros: Int) -> Duration` | Microsegundos (truncados). | ✅ |
| `Duration.from_secs_f64` / `from_secs_f32` | `(secs: Float) -> Duration` | Segundos en coma flotante. | ✅ |
| `Duration.as_secs_f64` / `as_secs_f32` | `(@) -> Float` | Segundos en coma flotante. | ✅ |
| `Duration.subsec_micros` / `subsec_nanos` | `(@) -> Int` | Fracción de segundo. | ✅ |
| `Duration.mul_f64` / `div_f64` | `(@, factor: Float) -> Duration` | Escala la duración. | ✅ |
| `SystemTimeError.duration` | `(@) -> Duration` | Cuánto se adelantó el instante. | ✅ |
| `Duration.from_nanos` | `(nanos: Int) -> Duration` | Nanosegundos (truncados). | ✅ |
| `Duration.as_secs` | `(@) -> Int` | Segundos enteros. | ✅ |
| `Duration.as_millis` | `(@) -> Int` | Milisegundos. | ✅ |
| `Duration.as_micros` | `(@) -> Int` | Microsegundos. | ✅ |
| `Duration.as_nanos` | `(@) -> Int` | Nanosegundos. | ✅ |
| `Duration.secs` | `(@) -> Int` | Segundos enteros (alias). | ✅ |
| `Duration.subsec_millis` | `(@) -> Int` | Milisegundos fraccionarios. | ✅ |
| `Duration.is_zero` | `(@) -> Bool` | Es cero. | ✅ |
| `Duration.checked_add` | `(@, other: Duration) -> Option[Duration]` | Suma comprobada. | ✅ |
| `Duration.checked_sub` | `(@, other: Duration) -> Option[Duration]` | Resta comprobada. | ✅ |
| `Duration.saturating_add` | `(@, other: Duration) -> Duration` | Suma saturada. | ✅ |
| `Duration.saturating_sub` | `(@, other: Duration) -> Duration` | Resta saturada. | ✅ |
| `Instant.now` | `() -> Instant` | Instante actual monótono. | ✅ |
| `Instant.elapsed` | `(@) -> Duration` | Tiempo transcurrido. | ✅ |
| `Instant.duration_since` | `(@, earlier: Instant) -> Duration` | Diferencia. | ✅ |
| `Instant.checked_add` | `(@, duration: Duration) -> Instant` | Suma. | ✅ |
| `SystemTime.now` | `() -> SystemTime` | Tiempo del sistema. | ✅ |
| `SystemTime.duration_since` | `(@, earlier: SystemTime) -> Result[Duration, SystemTimeError]` | Diferencia. | ✅ |
| `SystemTime.elapsed` | `(@) -> Result[Duration, SystemTimeError]` | Tiempo desde entonces. | ✅ |
| `SystemTime.checked_add` | `(@, duration: Duration) -> SystemTime` | Suma. | ✅ |
| `SystemTime.checked_sub` | `(@, duration: Duration) -> SystemTime` | Resta. | ✅ |

Diferidos a S7: `Duration.from_secs_f64/f32`, `as_secs_f64/f32`, `mul_f64`, `div_f64`,
`subsec_micros/nanos` y `SystemTimeError.duration` (necesitan `Float` o división exacta).

---


## 15. `nexus` — FFI seguro

**Archivo:** `std/nexus.pengu`
**Estado:** ✅ S6. `CString` y `CStr` son **tipos integrados** del lenguaje y el backend los
mapea a `std::ffi::CString` / `std::ffi::CStr`. En v1 no hay punteros crudos ni `unsafe`
(§16 de `docs/LANGUAGE.md`), así que `Ptr[T]`, `from_raw`/`into_raw`/`as_ptr` quedan fuera
por diseño (N38). La llamada a C sí existe: se declara `foreign "C"` y se invoca dentro de un
bloque `curse`; este módulo pone la parte segura de las cadenas.

Los errores se colapsan a `none`/`false` (no hay `NulError`/`IntoStringError`/`Utf8Error` en
la superficie).

**`CString` (propiedad)**

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `cstring_new` | `(text: &Str) -> Option[CString]` | Crea con NUL final; `none` si hay NUL intermedio. | ✅ |
| `cstring_from_bytes` | `(bytes: Vec[U8]) -> Option[CString]` | Igual desde bytes; añade el NUL si falta. | ✅ |
| `cstring_into_string` | `(value: CString) -> Option[String]` | Consume y valida UTF-8. | ✅ |
| `cstring_to_str` | `(value: &CString) -> Option[String]` | Copia validando UTF-8. | ✅ |
| `cstring_to_string_lossy` | `(value: &CString) -> String` | Copia sustituyendo UTF-8 inválido por U+FFFD. | ✅ |
| `cstring_as_bytes` | `(value: &CString) -> Vec[U8]` | Bytes sin el NUL final. | ✅ |
| `cstring_len` | `(value: &CString) -> Usize` | Longitud sin el NUL. | ✅ |
| `cstring_is_empty` | `(value: &CString) -> Bool` | Está vacía. | ✅ |
| `cstring_clone` | `(value: &CString) -> CString` | Copia propia. | ✅ |
| `cstring_as_c_str` | `(value: &CString) -> CStr` | Vista prestada sin copiar; es lo que consume una función C. | ✅ |

**`CStr` (vista prestada de una cadena terminada en NUL)**

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `cstr_to_str` | `(value: &CStr) -> Option[String]` | Copia validando UTF-8. | ✅ |
| `cstr_to_string_lossy` | `(value: &CStr) -> String` | Copia sustituyendo UTF-8 inválido. | ✅ |
| `cstr_as_bytes` | `(value: &CStr) -> Vec[U8]` | Bytes sin el NUL final. | ✅ |
| `cstr_len` | `(value: &CStr) -> Usize` | Longitud sin el NUL. | ✅ |
| `cstr_is_empty` | `(value: &CStr) -> Bool` | Está vacía. | ✅ |
| `cstr_equals_str` | `(value: &CStr, text: &Str) -> Bool` | Compara con un `Str` sin asignar. | ✅ |
| `cstr_to_cstring` | `(value: &CStr) -> CString` | Copia a cadena propia. | ✅ |

Ejemplo completo (declaración C, función `curse` y uso de la vista):

```pengu
summon std::ffi

foreign "C"
    strlen = (text: &CStr) -> Usize
    toupper = (c: Int) -> Int

-- SAFETY: la cadena pertenece al llamador y no se libera durante la llamada.
c_len = (text: &Str) -> Usize
    bind value = match ffi.cstring_new(text)
        when some(cs) then cs
        when none then
            return 0_usize
    curse
        strlen(ffi.cstring_as_c_str(&value))

describe = (text: &CStr) -> String
    ffi.cstr_to_string_lossy(text)

grimoire
    print(c_len("abcde"))              -- 5
    bind owned = match ffi.cstring_new("hola")
        when some(v) then v
        when none then
            return
    curse
        print(toupper(97))                                  -- 65
        print(ffi.cstr_len(ffi.cstring_as_c_str(&owned)))   -- 4
        print(describe(ffi.cstring_as_c_str(&owned)))       -- hola
```

**Limitación conocida (documentada en `scratch/LIMITATIONS_AUDIT.md`, N55):** una vista
`CStr` **no puede guardarse en un `bind`** y usarse en sentencias posteriores: el state
machine mueve la `CString` dueña al siguiente bloque y el préstamo no sobrevive
(`error[E0597]: borrowed value does not live long enough`). Por eso `cstring_as_c_str(...)` se
usa como **temporal dentro de la misma expresión o bloque `curse`**. Las conversiones que
copian (`cstring_to_str`, `cstring_to_string_lossy`, `cstr_to_cstring`) no tienen ese
problema.

Pendiente para v2 (requiere `Ptr[T]` y verificación de seguridad de punteros):
`CStr.from_ptr`, `CString.as_ptr`, `into_raw`/`from_raw`.

---


## 16. `vinculum` — Rc / Arc

**Archivo:** `std/vinculum.pengu`
**Implementación:** `rune Rc[T]`, `rune Arc[T]`, `rune Weak[T]`.

| Elemento | Firma | Descripción | CORE |
|---|---|---|---|
| `Rc.new` | `(value: T) -> Rc[T]` | Crea. | ✅ |
| `Rc.clone` | `(@) -> Rc[T]` | Incrementa conteo. | ✅ |
| `Rc.strong_count` | `(@) -> Usize` | Dueños. | |
| `Rc.weak_count` | `(@) -> Usize` | Débiles. | |
| `Rc.downgrade` | `(@) -> Weak[T]` | Crea débil. | |
| `Rc.ptr_eq` | `(@, other: &Rc[T]) -> Bool` | Misma asignación. | |
| `Rc.get_mut` | `(@mut) -> Option[&mut T]` | Acceso mutable si es único. | |
| `Rc.make_mut` | `(@mut) -> &mut T` | Clona si hay más dueños. | |
| `Rc.try_unwrap` | `(@own) -> Result[T, Rc[T]]` | Extrae si es único. | |
| `Rc.into_raw` | `(@own) -> Ptr[T]` | Transfiere la propiedad. | |
| `Rc.from_raw` | `(ptr: Ptr[T]) -> Rc[T]` | Recupera desde `into_raw`. | |
| `Rc.increment_strong_count` | `(ptr: Ptr[T])` | Incrementa el conteo. | |
| `Rc.decrement_strong_count` | `(ptr: Ptr[T])` | Decrementa el conteo. | |
| `Weak.new` | `() -> Weak[T]` | Débil vacío. | |
| `Weak.upgrade` | `(@) -> Option[Rc[T]]` | Recupera. | |
| `Weak.strong_count` | `(@) -> Usize` | Dueños. | |
| `Weak.weak_count` | `(@) -> Usize` | Débiles. | |
| `Weak.ptr_eq` | `(@, other: &Weak[T]) -> Bool` | Misma asignación. | |
| `Arc.new` | `(value: T) -> Arc[T]` | Crea. | ✅ |
| `Arc.clone` | `(@) -> Arc[T]` | Incrementa. | ✅ |
| `Arc.strong_count` | `(@) -> Usize` | Dueños. | |
| `Arc.downgrade` | `(@) -> Weak[T]` | Crea débil. | |
| `Weak.upgrade` | `(@) -> Option[Arc[T]]` | Recupera. | |
| `Arc.get_mut` | `(@mut) -> Option[&mut T]` | Acceso mutable si es único. | |
| `Arc.make_mut` | `(@mut) -> &mut T` | Clona si hay más dueños. | |
| `Arc.try_unwrap` | `(@own) -> Result[T, Arc[T]]` | Extrae si es único. | |
| `Arc.ptr_eq` | `(@, other: &Arc[T]) -> Bool` | Misma asignación. | |

**Nota:** `Rc`/`Arc` no están en la prelude; se importan con `summon std::vinculum`.

---

<a id="frenum"></a>
## 17. `frenum` — Sync

**Archivo:** `std/frenum.pengu`
**Implementación:** `rune Mutex[T]`, `rune RwLock[T]`, `rune OnceLock[T]`.

| Elemento | Firma | Descripción | CORE |
|---|---|---|---|
| `Mutex.new` | `(value: T) -> Mutex[T]` | Crea. | ✅ |
| `Mutex.lock` | `(@mut) -> LockResult[MutexGuard[T]]` | Bloquea. | ✅ |
| `MutexGuard` | `rune` | Guarda RAII. | ✅ |
| `Mutex.try_lock` | `(@mut) -> TryLockResult[MutexGuard[T]]` | Intenta bloquear. | |
| `Mutex.into_inner` | `(@own) -> LockResult[T]` | Extrae el valor. | |
| `Mutex.get_mut` | `(@mut) -> LockResult[&mut T]` | Acceso sin bloquear. | |
| `Mutex.is_poisoned` | `(@) -> Bool` | Estado de envenenamiento. | |
| `Mutex.clear_poison` | `(@mut)` | Limpia el veneno. | |
| `RwLock.new` | `(value: T) -> RwLock[T]` | Crea. | |
| `RwLock.read` | `(@) -> LockResult[RwLockReadGuard[T]]` | Lectura. | |
| `RwLock.write` | `(@mut) -> LockResult[RwLockWriteGuard[T]]` | Escritura. | |
| `RwLock.try_read` | `(@) -> TryLockResult[RwLockReadGuard[T]]` | Intenta lectura. | |
| `RwLock.try_write` | `(@mut) -> TryLockResult[RwLockWriteGuard[T]]` | Intenta escritura. | |
| `RwLock.into_inner` | `(@own) -> LockResult[T]` | Extrae el valor. | |
| `RwLock.get_mut` | `(@mut) -> LockResult[&mut T]` | Acceso sin bloquear. | |
| `OnceLock.new` | `() -> OnceLock[T]` | Crea. | |
| `OnceLock.set` | `(@mut, value: T) -> Result[(), T]` | Inicializa una vez. | |
| `OnceLock.get` | `(@) -> Option[&T]` | Lee. | |
| `OnceLock.get_or_init` | `(@mut, f: () -> T) -> &T` | Inicializa si falta. | |
| `OnceLock.get_or_try_init` | `(@mut, f: () -> Result[T, E]) -> Result[&T, E]` | Inicializa o propaga error. | |
| `OnceLock.take` | `(@mut) -> Option[T]` | Extrae el valor. | |

**Nota:** `Mutex`/`RwLock` requieren que `T: Send` en el backend, pero `Send`/`Sync` no son visibles en la superficie (la restricción la aplica el backend).

---

<a id="cellula"></a>
## 18. `cellula` — Cell / RefCell

**Archivo:** `std/cellula.pengu`
**Implementación:** `rune Cell[T]`, `rune RefCell[T]`.

| Elemento | Firma | Descripción | CORE |
|---|---|---|---|
| `Cell.new` | `(value: T) -> Cell[T]` | Crea. | |
| `Cell.get` | `(@) -> T` | Copia (requiere `T: Copy`). | |
| `Cell.set` | `(@, value: T)` | Reemplaza. | |
| `Cell.replace` | `(@, value: T) -> T` | Reemplaza y devuelve anterior. | |
| `Cell.take` | `(@) -> T` | Extrae y deja el valor por defecto. | |
| `Cell.swap` | `(@, other: &Cell[T])` | Intercambia contenidos. | |
| `Cell.update` | `(@, f: (T) -> T)` | Actualiza con una función. | |
| `Cell.as_ptr` | `(@) -> Ptr[T]` | Puntero interno. | |
| `Cell.into_inner` | `(@own) -> T` | Extrae el valor. | |
| `RefCell.new` | `(value: T) -> RefCell[T]` | Crea. | |
| `RefCell.borrow` | `(@) -> Ref[T]` | Préstamo compartido (runtime). | |
| `RefCell.borrow_mut` | `(@) -> RefMut[T]` | Préstamo mutable (runtime). | |
| `RefCell.try_borrow` | `(@) -> Result[Ref[T], BorrowError]` | Intenta. | |
| `RefCell.try_borrow_mut` | `(@) -> Result[RefMut[T], BorrowMutError]` | Intenta. | |
| `RefCell.replace` | `(@, value: T) -> T` | Reemplaza y devuelve anterior. | |
| `RefCell.swap` | `(@, other: &RefCell[T])` | Intercambia contenidos. | |
| `RefCell.take` | `(@) -> T` | Extrae y deja el valor por defecto. | |
| `RefCell.into_inner` | `(@own) -> T` | Extrae el valor. | |
| `Ref.clone` | `(@) -> Ref[T]` | Clona el préstamo. | |
| `Ref.map` | `(@, f: (&T) -> &U) -> Ref[U]` | Proyecta el préstamo. | |
| `RefMut.map` | `(@, f: (&mut T) -> &mut U) -> RefMut[U]` | Proyecta el préstamo mutable. | |

**Nota:** `RefCell` puede hacer panic en runtime si se solapan préstamos; el linter puede advertir.

---

<a id="somnium"></a>
## 19. `somnium` — Async (diferido)

**Archivo:** `std/somnium.pengu`
**Estado:** **Diferido**; no es CORE. El núcleo es síncrono. Se documenta para el mapa, pero no se implementa en la primera fase.

| Elemento | Firma | Descripción |
|---|---|---|
| `Future[T]` | `pact` | Cálculo asíncrono. |
| `poll` | `(@mut, cx: &mut Context) -> Poll[T]` | Sondea. |
| `Poll` | `enchanting` | `Ready(T)` / `Pending`. |
| `spawn` | `(f: () -> Future[T]) -> JoinHandle[T]` | Lanza tarea. |
| `block_on` | `(f: Future[T]) -> T` | Ejecuta hasta completar. |
| `sleep` | `(duration: Duration) -> Future[()]` | Duerme asíncrono. |

**Nota:** la implementación real requiere un executor y `Pin`/`Waker`, que la spec no expone. Se implementará en un módulo aparte o se delegará a un runtime externo.

---

<a id="proba"></a>
## 20. `proba` — Test

**Archivo:** `std/proba.pengu`

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `assert` | `(condition: Bool, message: &Str)` | Panic si es falso. | ✅ |
| `assert_eq` | `(actual: T, expected: T)` | Igualdad (requiere `Debug + PartialEq`). | ✅ |
| `assert_ne` | `(actual: T, unexpected: T)` | Desigualdad. | ✅ |
| `panic` | `(message: &Str) -> Never` | Aborta. | ✅ |
| `should_panic` | atributo `@@test(should_panic: "...")` | Test que debe fallar. | ✅ |
| `assert_eq_msg` | `(actual: T, expected: T, message: &Str)` | Igualdad con mensaje. | |
| `assert_ne_msg` | `(actual: T, unexpected: T, message: &Str)` | Desigualdad con mensaje. | |
| `assert_approx_eq` | `(actual: Float, expected: Float, tolerance: Float)` | Igualdad numérica aproximada. | |
| `debug_assert` | `(condition: Bool, message: &Str)` | Assert solo en debug. | |
| `debug_assert_eq` | `(actual: T, expected: T)` | Igualdad solo en debug. | |
| `fail` | `(message: &Str) -> Never` | Falla el test. | |

**Nota de implementación (S4).** `std/proba.pengu` implementa las aserciones
como intrínsecos `abi "pengu"`: `assert`, `assert_eq`, `assert_ne`,
`assert_eq_msg`, `assert_ne_msg`, `assert_approx_eq`, `debug_assert`,
`debug_assert_eq` y `fail`. El mensaje se construye en el backend con el trait
`Show` del runtime, así que las aserciones funcionan con cualquier tipo sin
bounds en la superficie (`assert_eq = [T](actual: T, expected: T) -> Unit`).

`panic(message)` y `fail(message)` devuelven `Never`. `should_panic` es el
atributo `@@test(should_panic: "...")`, no una función: los tests se declaran
con `@@test` y el runner ya los ejecuta.


---

<a id="opera"></a>
## 21. `opera` — Ops

**Archivo:** `std/opera.pengu`
**Implementación:** `pact Add`, `Sub`, `Mul`, `Div`, `Rem`, `Neg`, `Eq`, `Ord`. Se importan con `summon std::opera::Add`.

| Pact | Método | Firma |
|---|---|---|
| `Add` | `add` | `(@own, other: Self) -> Self` |
| `Sub` | `sub` | `(@own, other: Self) -> Self` |
| `Mul` | `mul` | `(@own, other: Self) -> Self` |
| `Div` | `div` | `(@own, other: Self) -> Self` |
| `Rem` | `rem` | `(@own, other: Self) -> Self` |
| `Neg` | `neg` | `(@own) -> Self` |
| `Eq` | `eq` | `(@, other: &Self) -> Bool` |
| `Ord` | `cmp` | `(@, other: &Self) -> Ordering` |

> **Nota de implementación (S1).** Los ocho pactos viven en
> `std/opera.pengu`. Un operador sobre un tipo de usuario se baja a la llamada
> del pacto (`std::opera::Add::add(a, b)`), no al operador de Rust: así hay una
> sola definición de operadores en el lenguaje y no se depende de los traits de
> `std::ops`. El pacto `Show` sigue siendo el único de la prelude; estos se
> importan con `summon`.

---

<a id="funis"></a>
## 22. `funis` — Iter

**Archivo:** `std/funis.pengu` (declarativo) + backend
**Estado:** ✅ S7a. Implementado sobre `Iterator` de Rust. En PenguScript un `Iter[T]` es el
valor que devuelven `Vec.iter()`, `Vec.map(…)`, `Map.iter()`, `Set.iter()`, `Str.chars()`, etc.;
no hay todavía un `rune Iter[T]` propio (N36), así que el checker resuelve
los métodos con la tabla de `Ty::Iterator` y el backend emite el adaptador homónimo de Rust.

`iter()` recorre **por valor** (`clone().into_iter()` en el Rust generado): el contenedor
sigue siendo utilizable después. `into_iter()` lo consume. Los adaptadores que devuelven un
iterador nuevo se envuelven en `Box::new(…)`, así que un `Iter[T]` se puede guardar en un
`bind`:

```pengu
bind it = xs.iter().filter((x: Int) => x % 2 == 0)
print(it.map((x: Int) => x * 10).collect())
```

`std/funis.pengu` es **declarativo**: mientras no exista un `rune Iter[T]` (N36) no puede
aportar métodos propios, así que la superficie vive en el checker (`Ty::Iterator`). El
archivo documenta los adaptadores para que `summon std::funis` sea válido y para que la
tabla de abajo tenga un único origen de verdad.

`summon std::iter` es opcional (los métodos están disponibles sin importar); sirve para
declarar de dónde viene la superficie. El módulo `std/funis.pengu` es solo documentación: la
superficie no se puede declarar en PenguScript hasta que `Iter[T]` sea un tipo nominal.

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `map` | `(@, f: (T) -> U) -> Iter[U]` | Transforma. | ✅ |
| `filter` | `(@, f: (T) -> Bool) -> Iter[T]` | Filtra. | ✅ |
| `fold` | `(@, init: U, f: (U, T) -> U) -> U` | Acumula. | ✅ |
| `collect` | `(@) -> Vec[T]` | Materializa. | ✅ |
| `count` | `(@) -> Usize` | Cuenta. | ✅ |
| `any` | `(@, f: (T) -> Bool) -> Bool` | Algún elemento. | ✅ |
| `all` | `(@, f: (T) -> Bool) -> Bool` | Todos. | ✅ |
| `find` | `(@, f: (T) -> Bool) -> Option[T]` | Primer match. | ✅ |
| `position` | `(@, f: (T) -> Bool) -> Option[Usize]` | Posición del primer match. | ✅ |
| `take` | `(@, n: Usize) -> Iter[T]` | Primeros `n`. | ✅ |
| `skip` | `(@, n: Usize) -> Iter[T]` | Omite `n`. | ✅ |
| `step_by` | `(@, step: Usize) -> Iter[T]` | Cada `step`. | ✅ |
| `rev` | `(@) -> Iter[T]` | Invierte (doble extremo). | ✅ |
| `enumerate` | `(@) -> Iter[(Usize, T)]` | Índice + valor. | ✅ |
| `zip` | `(@, other: Iter[U]) -> Iter[(T, U)]` | Empareja. | ✅ |
| `nth` | `(@, n: Usize) -> Option[T]` | Enésimo elemento. | ✅ |
| `last` | `(@) -> Option[T]` | Último. | ✅ |
| `sum` | `(@) -> T` | Suma (numéricos). | ✅ |
| `max` / `min` | `(@) -> Option[T]` | Extremos (`Ord`). | ✅ |

| `filter_map` | `(@, f: (T) -> Option[U]) -> Iter[U]` | Transforma y descarta. | ✅ |
| `flat_map` | `(@, f: (T) -> Vec[U]) -> Iter[U]` | Aplana lo que devuelve el cierre. | ✅ |
| `flatten` | `(@) -> Iter[U]` | Aplana un iterador de iterables. | ✅ |
| `chain` | `(@, other: Iter[T]) -> Iter[T]` | Concatena. | ✅ |
| `take_while` | `(@, f: (T) -> Bool) -> Iter[T]` | Mientras se cumpla. | ✅ |
| `skip_while` | `(@, f: (T) -> Bool) -> Iter[T]` | Salta mientras se cumpla. | ✅ |
| `reduce` | `(@, f: (T, T) -> T) -> Option[T]` | Acumula sin valor inicial. | ✅ |
| `product` | `(@) -> T` | Producto (numéricos). | ✅ |
| `for_each` | `(@, f: (T) -> Unit) -> Unit` | Ejecuta por elemento. | ✅ |
| `inspect` | `(@, f: (T) -> Unit) -> Iter[T]` | Observa sin consumir. | ✅ |
| `fuse` | `(@) -> Iter[T]` | Termina tras el primer `none`. | ✅ |
| `max_by` / `min_by` | `(@, f: (T, T) -> Ordering) -> Option[T]` | Extremos con comparador. | ✅ |

Notas de implementación (S7):

- `flat_map` recibe un cierre que devuelve `Vec[U]` (en Rust es `IntoIterator`).
- `rev` **materializa** el iterador (`collect::<Vec<_>>().into_iter().rev()`): `Box<dyn
  Iterator>` no implementa `DoubleEndedIterator`. Mismo resultado, coste O(n) de memoria.
- `take_while`, `skip_while`, `inspect` y `max_by`/`min_by` reciben `&T` en Rust y el backend
  copia con `T: Clone`.
- Pendientes con motivo: `peekable` (necesita un `rune Peekable[T]`), `cycle` (el iterador
  debe ser `Clone`, y `Box<dyn Iterator>` no lo es) y `try_*` (falta un pacto de conversión).
  Todos necesitan el `rune Iter[T]` propio (N36).

`Str` también produce iteradores desde S7: `chars() -> Iter[Char]`, `bytes() -> Iter[U8]` y
`char_indices() -> Iter[(Usize, Char)]` (ver §5).

Ejemplos:

```pengu
bind xs = Vec[1, 2, 3, 4, 5]
print(xs.iter().filter((x: Int) => x % 2 == 0).map((x: Int) => x * 10).collect())
print(xs.iter().sum())                     -- 15; el Vec sigue vivo
print(xs.iter().rev().take(2).collect())   -- [5, 4]
```

---


## 23. `structura` — Colecciones avanzadas

**Archivo:** `std/structura.pengu`
**Estado:** ✅ pila, cola y cola doble (C2). Los contenedores ordenados quedan
bloqueados por N67.

### 23.1 Por qué son funciones libres

El backend no puede emitir todavía el `impl` de un `ritual` genérico con
funciones asociadas: Rust no admite dos `new` en impls distintos y la plantilla
`impl<T> Pila<T>` choca con el `enum __State` interno de cada método (N62). La
superficie se ofrece, por tanto, con **funciones libres genéricas** que el
monomorfizador instancia (`pila_push__Int`, `pila_push__Str`, …). El patrón es:

```pengu
morph xs: Vec[Int] = Vec.new()
xs = std::structura::pila_push(xs, 1)
match std::structura::pila_pop(xs)
    when some(v) then print(v)
    when none then print("vacia")
```

El contenedor es un `Vec[T]` normal, así que `xs.len()`, `xs[index]`, `for` y los
métodos de `capsa` siguen disponibles.

### 23.2 Pila (LIFO)

| Función | Firma | Descripción |
|---|---|---|
| `pila_push` | `[T](Vec[T], T) -> Vec[T]` | Apila al final. |
| `pila_pop` | `[T](Vec[T]) -> Option[T]` | Desapila; `none` si está vacía. |
| `pila_clear` | `[T](Vec[T]) -> Vec[T]` | Vacía conservando la capacidad. |

### 23.3 Cola (FIFO)

| Función | Firma | Descripción |
|---|---|---|
| `cola_push` | `[T](Vec[T], T) -> Vec[T]` | Encola al final. |
| `cola_pop` | `[T](Vec[T]) -> Option[T]` | Desencola del principio; `none` si está vacía. |

### 23.4 Cola doble

| Función | Firma | Descripción |
|---|---|---|
| `duplex_push_front` | `[T](Vec[T], T) -> Vec[T]` | Inserta al principio. |
| `duplex_push_back` | `[T](Vec[T], T) -> Vec[T]` | Inserta al final. |
| `duplex_pop_front` | `[T](Vec[T]) -> Option[T]` | Extrae del principio. |
| `duplex_pop_back` | `[T](Vec[T]) -> Option[T]` | Extrae del final. |

### 23.5 Pendiente (N67)

`VecDeque`, `BTreeMap`, `BTreeSet`, `BinaryHeap` y `LinkedList` necesitan
comparar o clonar valores genéricos: `==` exige el bound `Eq` y no se puede pasar
un `T` por valor dos veces sin moverlo, y sacar un elemento de un `Vec` por índice
exige `Copy`. Llegan cuando los bounds admitan `Clone`/`Copy`. Mientras tanto,
`tabula` (Map) y `fasciculus` (Set) cubren el caso con claves `Str`, y los
adaptadores de `funis` (§22) cubren el recorrido ordenado de un `Vec` ya ordenado.

## 24. `libra` — TOML

**Archivo:** `std/libra.pengu`
**Estado:** implementado en S8b con un documento **aplanado**: cada hoja queda como
`clave.punteada -> texto` con su tipo (`string`, `integer`, `float`, `bool`, `array`). Es
deliberado: un árbol recursivo no se puede compartir con `iason` (los módulos de `std` no se
importan entre sí, N42) y para configuración el acceso por clave es lo que se usa.

| Función / método | Firma | Descripción | CORE |
|---|---|---|---|
| `parse` | `(text: &Str) -> Result[Table, LibraError]` | Parsea TOML. | ✅ |
| `parse_file` | `(path: &Str) -> Result[Table, LibraError]` | Lee y parsea. | ✅ |
| `table.get` | `(@, key: &Str) -> Option[String]` | Texto de la clave. | ✅ |
| `table.get_int` | `(@, key: &Str) -> Option[Int]` | Entero. | ✅ |
| `table.get_float` | `(@, key: &Str) -> Option[Float]` | Flotante. | ✅ |
| `table.get_bool` | `(@, key: &Str) -> Option[Bool]` | Booleano. | ✅ |
| `table.get_array` | `(@, key: &Str) -> Option[Vec[String]]` | Elementos de un array. | ✅ |
| `table.has` | `(@, key: &Str) -> Bool` | ¿Existe? | ✅ |
| `table.kind_of` | `(@, key: &Str) -> Option[String]` | Tipo declarado. | ✅ |
| `table.keys_of` | `(@, prefix: &Str) -> Vec[String]` | Claves bajo un prefijo. | ✅ |
| `table.len` | `(@) -> Usize` | Número de hojas. | ✅ |

Soporta comentarios `#`, tablas `[seccion]` y arrays de tablas `[[seccion]]` (se aplanan
con un índice por instancia: `seccion.0.campo`, `seccion.1.campo`), claves punteadas, tablas
en línea (`{ a = 1, b = "x" }`, anidadas incluidas, aplanadas como `clave.a`), cadenas
básicas y literales (con `"""`), enteros, flotantes, booleanos, arrays de escalares y
fechas/horas (se conservan como texto y `kind_of` devuelve `date`, `time` o `datetime`).

`get` devuelve el array formateado (`"1, 2, 3"`) y `get_array` sus elementos por separado.
Los valores de un array se guardan con un separador interno, así que un elemento puede
contener comas.

```pengu
bind features = config.get_array("deps.serde.features").unwrap_or(Vec.new())
```

```pengu
match std::libra::parse_file("config.toml")
    when ok(config) then
        bind port = config.get_int("server.port").unwrap_or(8080)
        print("escuchando en #{port}")
    when err(e) then
        print(e)
```

---


## 25. `iason` — JSON

**Archivo:** `std/iason.pengu`
**Estado:** implementado en S8. `Json` es un `rune` plano: `kind` dice el tipo de nodo y
cada etiqueta usa unos campos (`flag`, `integer`, `number`, `text`), con `items` para los
hijos y `keys` para las claves del objeto (en el mismo orden). Los árboles recursivos se
pueden declarar porque la recursión pasa por `Vec`.

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `parse` | `(text: &Str) -> Result[Json, IasonError]` | Parser completo (escapes, `\uXXXX`, números). | ✅ |
| `to_string` | `(value: &Json) -> String` | Serializa compacto. | ✅ |
| `pretty` | `(value: &Json, indent: Int) -> String` | Serializa con sangría (`2` típico). | ✅ |
| `null_value` | `() -> Json` | Nodo nulo. | ✅ |
| `bool_value` | `(value: Bool) -> Json` | Nodo booleano. | ✅ |
| `int_value` | `(value: Int) -> Json` | Nodo entero. | ✅ |
| `float_value` | `(value: Float) -> Json` | Nodo real. | ✅ |
| `string_value` | `(value: &Str) -> Json` | Nodo cadena. | ✅ |
| `array_value` | `(items: Vec[Json]) -> Json` | Nodo array. | ✅ |
| `object_value` | `(keys: Vec[String], items: Vec[Json]) -> Json` | Nodo objeto. | ✅ |

Métodos de `Json`: `kind_of`, `is_null`, `is_bool`, `is_number`, `is_int`, `is_float`,
`is_string`, `is_array`, `is_object`, `as_bool`, `as_int`, `as_float`, `as_string`, `len`,
`at`, `get`, `get_path`, `has`, `keys_of`, `items_of`, `equals`, `push`, `insert`, `set`,
`remove`, `to_string`, `pretty_string`, `copy`.

- `get_path("a.b.0")` recorre objeto/array por ruta punteada.
- `equals(&other)` compara en profundidad: en los objetos el orden de las claves no
  importa; `int` y `float` son tipos distintos (`1` ≠ `1.0`).
- `push(&item)` añade a un array; `insert(&key, &item)` añade a un objeto; `set` inserta o
  reemplaza; `remove(&key)` devuelve `true` si existía. Son `@mut`, así que el `Json` debe
  estar en un `morph`.

Los parámetros de tipo `&Json` se pasan con `&` en la llamada (`doc.equals(&other)`).

```pengu
match std::iason::parse("{\"nombre\": \"ana\", \"edad\": 30}")
    when ok(v) then
        match v.get("nombre")
            when some(n) then
                print(n.as_string())
            when none then
                print("sin nombre")
    when err(e) then
        print(e.message)
```

`Json` no implementa el pacto `Eq` (los pactos de `std.opera` son para tipos del usuario):
para comparar hay `equals`. `IasonError.offset` se rellena con la posición del fallo.

---


## 26. `digestum` — Hash y checksums

**Archivo:** `std/digestum.pengu`
**Estado:** implementado en S8 (Rust puro en el runtime, sin dependencias). Las funciones
de texto son atajos que codifican UTF-8 y delegan en `str.as_bytes()`.

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `sha256` | `(data: Vec[U8]) -> Vec[U8]` | SHA-256 (32 bytes). | ✅ |
| `sha256_hex` | `(data: Vec[U8]) -> String` | SHA-256 en hexadecimal. | ✅ |
| `sha512` / `sha512_hex` | `(data: Vec[U8]) -> Vec[U8]` / `String` | SHA-512 (64 bytes) y hexadecimal. | ✅ |
| `hmac_sha256` | `(key: Vec[U8], data: Vec[U8]) -> Vec[U8]` | HMAC-SHA-256 (RFC 2104). | ✅ |
| `constant_time_eq` | `(left: Vec[U8], right: Vec[U8]) -> Bool` | Compara sin filtrar el prefijo común. | ✅ |
| `sha1` / `sha1_hex` | `(data: Vec[U8]) -> Vec[U8]` / `String` | SHA-1 (20 bytes) y hexadecimal. | ✅ |
| `crc32` | `(data: Vec[U8]) -> U32` | CRC-32 (IEEE). | ✅ |
| `fnv1a` | `(data: Vec[U8]) -> U64` | FNV-1a de 64 bits. | ✅ |
| `hex` | `(data: Vec[U8]) -> String` | Codifica en hexadecimal. | ✅ |
| `unhex` | `(text: &Str) -> Option[Vec[U8]]` | Decodifica; `none` si no es hexadecimal. | ✅ |
| `sha256_text` | `(text: &Str) -> String` | SHA-256 de una cadena. | ✅ |
| `sha512_text` | `(text: &Str) -> String` | SHA-512 de una cadena. | ✅ |
| `hmac_sha256_text` | `(key: &Str, text: &Str) -> String` | HMAC-SHA-256 en hexadecimal. | ✅ |
| `sha1_text` | `(text: &Str) -> String` | SHA-1 de una cadena. | ✅ |
| `crc32_text` | `(text: &Str) -> U32` | CRC-32 de una cadena. | ✅ |
| `fnv1a_text` | `(text: &Str) -> U64` | FNV-1a de una cadena. | ✅ |

Las implementaciones están verificadas contra vectores conocidos
(`sha256("abc") = ba7816bf…`, `sha512("abc") = ddaf35a1…`, HMAC con RFC 4231). No hay API
de hash incremental (`Digest.update`): haría falta un tipo opaco con estado, como los de
`exsecutor`.

---


## 27. `versio` — SemVer

**Archivo:** `std/versio.pengu`
**Estado:** implementado en S8. `Version` guarda `major`, `minor`, `patch`, `pre` y `build`
(cadena vacía = ausente). La precedencia sigue SemVer 2.0.0: por números, una versión con
pre-release es menor que la misma sin ella, y los identificadores de pre-release se
comparan campo a campo (numérico si ambos son numéricos).

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `parse` | `(text: &Str) -> Result[Version, SemverError]` | Parser estricto. | ✅ |
| `version` | `(major: Int, minor: Int, patch: Int) -> Version` | Constructor sin pre/build. | ✅ |

Métodos de `Version`: `major_value`, `minor_value`, `patch_value`, `prerelease`,
`build_metadata`, `is_prerelease`, `is_stable`, `compare`, `lt`, `le`, `gt`, `ge`,
`eq_version`, `satisfies`, `with_pre`, `with_build`, `without_pre`, `increment_major`,
`increment_minor`, `increment_patch`, `to_string`.

`compare` devuelve `Ordering` (`Less`/`Equal`/`Greater`), así que `sort_by` funciona
directamente:

```pengu
bind mut versions = Vec.new()
for text in Vec[String.from("1.10.0"), String.from("1.9.0"), String.from("1.9.0-rc.1")]
    match std::versio::parse(text.as_str())
        when ok(v) then
            versions.push(v)
        when err(e) then
            print(e.message)
versions.sort_by((a: Version, b: Version) => a.compare(&b))
print(versions)
```

`satisfies` acepta: `*`, `x.y.z` exacto, `x.y`/`1.x`/`1.2.x` (comodín de cola), `^`, `~`,
`>=`, `<=`, `>`, `<`, `=`, conjunciones separadas por espacios (`>=1.0.0 <2.0.0`) y uniones
con `||` (`^1.2 || ^2.0`). Una versión incompleta con operador se rellena con ceros
(`^1.2` = `^1.2.0`).

---


## 28. `terminus` — Terminal

**Archivo:** `std/terminus.pengu`
**Estado:** implementado en S9. Los estilos son constantes `Str` con las secuencias ANSI
(`\u{1b}[…`), así que combinarlos no cuesta nada; la detección de terminal vive en el
runtime.

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `is_terminal` | `() -> Bool` | ¿La salida es una terminal? | ✅ |
| `width` | `() -> Usize` | Ancho (`COLUMNS`, si no 80). | ✅ |
| `supports_color` | `() -> Bool` | Respeta `NO_COLOR` y `TERM=dumb`. | ✅ |
| `style` | `(text: &Str, code: &Str) -> String` | Aplica un código y `RESET`. | ✅ |
| `rgb` | `(text: &Str, r: U8, g: U8, b: U8) -> String` | Color 24 bits. | ✅ |
| `red`/`green`/`yellow`/`blue`/`magenta`/`cyan`/`white` | `(text: &Str) -> String` | Colores básicos. | ✅ |
| `dim`/`bold`/`underline` | `(text: &Str) -> String` | Estilos. | ✅ |

Constantes: `RESET`, `BOLD`, `DIM`, `ITALIC`, `UNDERLINE`, `BLINK`, `REVERSE`, `HIDDEN`,
`STRIKETHROUGH`, los ocho colores básicos y los ocho brillantes (`BLACK`…`BRIGHT_WHITE`).

```pengu
if std::terminus::supports_color() then
    print(std::terminus::red("error") + ": algo falló")
```

Control de pantalla y progreso (S9):

| Función | Firma | Descripción |
|---|---|---|
| `clear_screen` | `() -> Unit` | Borra y lleva el cursor a (1, 1). |
| `move_cursor` | `(row: Usize, column: Usize) -> Unit` | Posiciona el cursor (base 1). |
| `hide_cursor` / `show_cursor` | `() -> Unit` | Oculta o restaura el cursor. |
| `cursor_up` / `cursor_down` | `(n: Usize) -> Unit` | Mueve `n` filas. |
| `cursor_left` / `cursor_right` | `(n: Usize) -> Unit` | Mueve `n` columnas. |
| `progress_bar` | `(done: Usize, total: Usize, width: Usize) -> String` | `[####------]  42%`. |
| `read_key` | `() -> Option[Char]` | Primer carácter de la entrada (ver N63). |

`read_key` no pone el terminal en modo crudo: sin `termios` hay que pulsar Intro y
devuelve el primer carácter de la línea.

---


## 29. `globus` — Glob

**Archivo:** `std/globus.pengu`
**Estado:** implementado en S9. Sintaxis: `*` (no cruza `/`), `**` (cruza), `?`, `[abc]`,
`[a-z]`, `[!abc]` y `{a,b}`.

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `matches` | `(pattern: &Str, path: &Str) -> Bool` | ¿Casa el patrón? | ✅ |
| `find` | `(pattern: &Str, root: &Str) -> Vec[String]` | Rutas bajo `root` que casan, ordenadas. | ✅ |
| `find_in` | `(pattern: &Str) -> Vec[String]` | Igual desde `.`. | ✅ |
| `all_files` | `() -> Vec[String]` | `**/*`. | ✅ |
| `rust_files` | `(root: &Str) -> Vec[String]` | `**/*.rs`. | ✅ |

```pengu
for path in std::globus::find("src/**/*.pengu", ".")
    print(path)
```

Recorrido configurable (S9):

| Función | Firma | Descripción |
|---|---|---|
| `find_with` | `(pattern: &Str, root: &Str, max_depth: Int, include_hidden: Bool, follow_links: Bool) -> Vec[String]` | Como `find`, con profundidad (`-1` sin límite), ocultos y enlaces simbólicos. |

---


## 30. `archivum` — Archivos tar/zip

**Archivo:** `std/archivum.pengu`
**Estado:** `tar` (ustar) implementado en S9b, sin dependencias y compatible con `tar -tf`
del sistema. `zip` y `tar.gz` necesitan deflate y quedan para S9c.

| Función | Firma | Descripción | CORE |
|---|---|---|---|
| `create` | `(archive: &Str, base: &Str, paths: Vec[String]) -> Result[Unit, ArchivumError]` | Crea un tar con rutas relativas a `base`. | ✅ |
| `extract` | `(archive: &Str, dest: &Str) -> Result[Vec[String], ArchivumError]` | Extrae; devuelve las rutas. | ✅ |
| `entries` | `(archive: &Str) -> Result[Vec[String], ArchivumError]` | Lista entradas. | ✅ |
| `pack` | `(archive: &Str, base: &Str) -> Result[Unit, ArchivumError]` | Empaqueta todo lo que hay bajo `base`. | ✅ |
| `unpack_count` | `(archive: &Str, dest: &Str) -> Result[Usize, ArchivumError]` | Extrae y cuenta. | ✅ |

Los directorios se guardan con `/` final (`sub/`). La extracción rechaza rutas con `..`.

```pengu
match std::archivum::pack("copia.tar", "/home/ana/proyecto")
    when ok(_) then print("empaquetado")
    when err(e) then print(e)
```

Formatos comprimidos (S9c):

| Función | Firma | Descripción |
|---|---|---|
| `create_targz` | `(archive: &Str, base: &Str, paths: Vec[String]) -> Result[Unit, ArchivumError]` | `tar.gz` (gzip + tar). |
| `entries_targz` | `(archive: &Str) -> Result[Vec[String], ArchivumError]` | Lista el `tar.gz`. |
| `extract_targz` | `(archive: &Str, dest: &Str) -> Result[Vec[String], ArchivumError]` | Extrae el `tar.gz`. |
| `create_zip` | `(archive: &Str, base: &Str, paths: Vec[String]) -> Result[Unit, ArchivumError]` | Crea un `zip` (entradas almacenadas). |
| `entries_zip` | `(archive: &Str) -> Result[Vec[String], ArchivumError]` | Lista el `zip`. |
| `extract_zip` | `(archive: &Str, dest: &Str) -> Result[Vec[String], ArchivumError]` | Extrae el `zip` (almacenado o deflate). |
| `compress_gz` | `(data: Vec[U8]) -> Vec[U8]` | Comprime en gzip. |
| `decompress_gz` | `(data: Vec[U8]) -> Result[Vec[U8], ArchivumError]` | Descomprime gzip; comprueba CRC y longitud. |

El gzip propio usa bloques deflate *stored* (formato válido y rápido, sin ratio); el
lector sí implementa inflate completo (bloques fijos y dinámicos), así que acepta
cualquier `.gz` y `.zip` generado por otras herramientas. Verificado con `unzip -t`,
`gzip -t` y `tar -tzf`.

Pendiente: `zstd`, `zip` con deflate comprimido al escribir y entradas con permisos
extendidos.

---


## 31. `rete` — Red, TLS y HTTP

**Archivo:** `std/rete.pengu`
**Estado:** TCP implementado en S10. La API es **bloqueante** (el lenguaje aún no tiene
hilos ni `async`); los sockets viven en registros globales del runtime y se identifican por
un `handle`. TLS y HTTP quedan para S10b: necesitan una capa de transporte genérica.

Runes: `ReteError { message }`, `PeerAddr { host: String, port: Int }`,
`TcpListener { handle: U64 }`, `TcpStream { handle: U64 }` (todos con `Show`).

| Función / método | Firma | Descripción | CORE |
|---|---|---|---|
| `TcpListener.listen` | `(host: &Str, port: Int) -> Result[TcpListener, ReteError]` | Escucha; `0` = puerto libre. | ✅ |
| `listener.local_addr` | `(@) -> Result[PeerAddr, ReteError]` | Dirección asignada. | ✅ |
| `listener.accept` | `(@own) -> Result[(TcpStream, PeerAddr), ReteError]` | Acepta una conexión. | ✅ |
| `listener.close` | `(@own) -> Unit` | Cierra el listener. | ✅ |
| `TcpStream.connect` | `(host: &Str, port: Int) -> Result[TcpStream, ReteError]` | Conecta. | ✅ |
| `stream.peer_addr` | `(@) -> Result[PeerAddr, ReteError]` | Dirección del par. | ✅ |
| `stream.read` | `(@mut, count: Usize) -> Result[Vec[U8], ReteError]` | Lee hasta `count` bytes. | ✅ |
| `stream.read_to_string` | `(@mut) -> Result[String, ReteError]` | Lee hasta EOF. | ✅ |
| `stream.write` / `write_str` | `(@mut, …) -> Result[Usize, ReteError]` | Escribe; devuelve bytes. | ✅ |
| `stream.flush` | `(@mut) -> Result[Unit, ReteError]` | Vacía el buffer. | ✅ |
| `stream.set_read_timeout` | `(@mut, millis: Int) -> Result[Unit, ReteError]` | Timeout de lectura. | ✅ |
| `stream.shutdown` | `(@own) -> Unit` | Cierra el socket. | ✅ |

```pengu
match std::rete::TcpListener.listen("127.0.0.1", 8080)
    when ok(listener) then
        match listener.accept()
            when ok(pair) then
                bind (stream, peer) = pair
                print("conectado #{peer}")
                stream.write_str("hola\n")
                stream.shutdown()
            when err(e) then
                print(e.message)
    when err(e) then
        print(e.message)
```

Pendiente (S10b): `UdpSocket`, TLS (`TlsStream`, necesita un backend de certificados),
`HttpRequest`/`HttpResponse` y un servidor HTTP mínimo. `TcpListener.listen` se llamó
`bind` en el diseño original, pero `bind` es palabra clave del lenguaje (N47).

---


## 32. Notas de implementación


1. **Módulos CORE:** `integrum`, `floatem`, `verbum`, `capsa`, `tabula`, `fasciculus`, `fluxus`, `numerus`, `proba` son obligatorios para la primera implementación del compilador.
2. **`std` escrita en PenguScript vs `.d.pengu`:** los métodos que requieren intrinsics (`sqrt`, `sin`, `push`, `lock`) se declaran en `.d.pengu` con `abi "pengu"` y el backend los resuelve a Rust. Los métodos que se pueden escribir en PenguScript puro (`trim`, `split`, `lerp`) se implementan en `.pengu` para dogfooding.
3. **Encadenamiento:** los métodos de transformación que no consumen (`@`, `@mut`) devuelven `Self`, `&Self` o `&mut Self`; los de consulta devuelven su valor (`Bool`, `Usize`, `Option[...]`). Los métodos `@own` consumen y no se encadenan después.
4. **Sin `Send`/`Sync` visibles:** `frenum` y `vinculum` existen pero no exponen esos traits; el backend aplica las restricciones.
5. **Sin `dyn`:** `Iter[T]` es un `rune` opaco, no un trait object. `collect` se resuelve en tiempo de compilación.
6. **Sin tipos asociados:** `Iterator` no es un pact; es un `rune` con métodos. `Entry` de `tabula` es un `rune` con métodos.
7. **Nombres mágicos:** cada módulo usa un nombre latino; los métodos mantienen nombres descriptivos en inglés (`push`, `split`, `sqrt`) para que el código se lea sin diccionario.

---

### 32.1 Aliases y módulos diferidos

La spec usa nombres funcionales (`std.int`, `std.string`, `std.io`); el mapa usa nombres latinos. La tabla fija la correspondencia:

| Nombre de spec | Módulo del mapa | Estado |
La columna de estado refleja el código de `std/` en este repositorio, no el objetivo a
largo plazo: ✅ implementado y probado, 🚧 parcial, ⬜ planificado (fase indicada en
`scratch/LIMITATIONS_AUDIT.md` §3).

|---|---|---|
| `std.int` | `integrum` | ✅ |
| `std.option` / `std.result` | `optio` | 🚧 (solo métodos homónimos de Rust; ver N34) |
| `std.string` | `verbum` | ✅ |
| `std.collections` | `capsa` + `tabula` + `fasciculus` + `structura` | 🚧 (pila/cola/cola doble; ordenados en N67) |
| `std.math` | `numerus` | ✅ |
| `std.io` | `fluxus` | ✅ |
| `std.fs` | `via` | ✅ |
| `std.fs.walk` | `via.walk` | ✅ |
| `std.process` | `exsecutor` | ✅ |
| `std.env` | `ambitus` | ✅ |
| `std.time` | `tempus` | ✅ |
| `std.ffi` | `nexus` | ✅ (`CString` + `CStr`; sin punteros crudos, N38) |
| `std.rc` | `vinculum` | ⬜ (S9b: necesita refcount/opacos) |
| `std.sync` | `frenum` | ⬜ (S9b: el lenguaje no tiene hilos) |
| `std.cell` | `cellula` | ✅ (S9: celdas `String` por clave, N46) |
| `std.test` | `proba` | ✅ |
| `std.ops` | `opera` | ✅ |
| `std.iter` | `funis` | 🚧 (S7: 20 adaptadores; resto con `rune Iter[T]`, N36) |
| `std.toml` | `libra` | ✅ (S8b: documento aplanado, N42) |
| `std.json` | `iason` | ✅ (S8) |
| `std.digest` | `digestum` | ✅ (S8) |
| `std.semver` | `versio` | ✅ (S8) |
| `std.term` | `terminus` | ✅ (S9) |
| `std.glob` | `globus` | ✅ (S9) |
| `std.archive` | `archivum` | 🚧 (S9b: `tar` ustar; `zip`/`tar.gz` en S9c) |
| `std.net` | `rete` | ✅ (S10: TCP bloqueante) |
| `std.tls` / `std.http` | `rete` | ⬜ (S10b) |
| `std.async` | `somnium` | Diferido |
| `std.concurrent` | — | Diferido; el núcleo no expone hilos/atomics. |
| `std.borrow` | — | Diferido; `Cow` no está en 0.6.0. |
| `std.build` | — | Diferido; los build scripts no están en 0.6.0. |
| `std.meta` | — | No existe en v1; no hay macros de usuario. |

**Fin del mapa.** Cualquier módulo no listado aquí no existe en `0.6.0`; si se necesita, va a `structura` o a un crate externo.