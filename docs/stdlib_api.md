<!-- Generado por scripts/gen_stdlib_docs.ts a partir de std/. No editar a mano. -->

# Referencia de la biblioteca estándar

Firmas exactas de cada módulo de `std/`, tomadas del parser del compilador.
Los módulos previstos para 0.2.0 no aparecen aquí porque todavía no existen.

## `std/array`

Realm: `array`.

Métodos (enchantings):

- `enchanting array<T>` — `is_empty() -> bool`, `first() -> T?`, `last() -> T?`, `index_of(buscado: T) -> size_t?`, `contains(buscado: T) -> bool`, `to_vector() -> vector<T>`, `reversed() -> vector<T>`, `slice(inicio: size_t, largo: size_t) -> vector<T>`, `join(separador: string) -> string`, `min() -> T?`, `max() -> T?`, `find_if(predicado: function<(T) -> bool>) -> T?`, `any(predicado: function<(T) -> bool>) -> bool`, `all(predicado: function<(T) -> bool>) -> bool`, `none(predicado: function<(T) -> bool>) -> bool`

## `std/assert`

Realm: `assert`.

Intrínsecos (`declare`): `that`, `fail`.

## `std/char`

Realm: `char`.

Métodos (enchantings):

- `enchanting char` — `code() -> int`, `is_digit() -> bool`, `is_alpha() -> bool`, `is_alphanumeric() -> bool`, `is_space() -> bool`, `is_upper() -> bool`, `is_lower() -> bool`, `is_ascii() -> bool`, `is_hex_digit() -> bool`, `is_control() -> bool`, `is_punctuation() -> bool`, `digit_value() -> int`, `hex_value() -> int`, `to_upper() -> char`, `to_lower() -> char`

Intrínsecos (`declare`): `to_upper_raw`, `to_lower_raw`.

## `std/cli`

Análisis de argumentos de línea de órdenes.  El programa describe sus banderas con `cli::flag` (interruptor sin valor) y `cli::option` (con valor); `cli::parse` recibe la lista y `argv` y devuelve un `Parsed` con valores, interruptores y posicionales. Si algo no cuadra, `Parsed` trae `ok = false` y un mensaje listo para imprimir.


Runes:

- `rune Flag` — campos: `nombre: string`, `corto: string`, `toma_valor: bool`, `descripcion: string` · constructor `Flag(nombre: string, corto: string, toma_valor: bool, descripcion: string)`
- `rune Parsed` — campos: `ok: bool`, `mensaje: string`, `valores: map<string, string>`, `interruptores: set<string>`, `posicionales: vector<string>` · constructor `Parsed(ok: bool, mensaje: string, valores: map<string, string>, interruptores: set<string>, posicionales: vector<string>)`

Métodos (enchantings):

- `enchanting Parsed` — `is_ok() -> bool`, `error() -> string`, `has(nombre: string) -> bool`, `get(nombre: string) -> string?`, `value_or(nombre: string, respaldo: string) -> string`, `positional(indice: size_t) -> string?`, `rest() -> vector<string>`, `to_string() -> string`

Funciones:

- `flag(nombre: string, descripcion: string = "") -> Flag`
- `option(nombre: string, descripcion: string = "") -> Flag`
- `short_flag(nombre: string, corto: string, descripcion: string = "") -> Flag`
- `short_option(nombre: string, corto: string, descripcion: string = "") -> Flag`
- `buscar_larga(banderas: ref<vector<Flag>>, nombre: string) -> Flag?`
- `buscar_corta(banderas: ref<vector<Flag>>, corto: string) -> Flag?`
- `error_de(mensaje: string) -> Parsed`
- `parse(banderas: ref<vector<Flag>>, argv: ref<vector<string>>) -> Parsed`
- `usage(programa: string, banderas: ref<vector<Flag>>) -> string`

## `std/color`

Color RGBA en coma flotante (0.0 a 1.0) con conversiones a bytes y hex.  Los componentes quedan sin recortar para poder sumar luz y hacer blending; `clamped()` devuelve una copia válida para pintar.


Runes:

- `rune Color` — campos: `r: double`, `g: double`, `b: double`, `a: double` · constructor `Color(r: double, g: double, b: double, a: double)`

Métodos (enchantings):

- `enchanting Color` — `clamped() -> Color`, `with_alpha(alpha: double) -> Color`, `is_opaque() -> bool`, `is_transparent() -> bool`, `luminance() -> double`, `inverted() -> Color`, `scale(factor: double) -> Color`, `lerp(hacia: Color, t: double) -> Color`, `red8() -> int`, `green8() -> int`, `blue8() -> int`, `alpha8() -> int`, `channel_hex(valor: int) -> string`, `to_rgb8() -> (int, int, int)`, `to_rgba8() -> (int, int, int, int)`, `to_hex() -> string`, `to_hex_rgba() -> string`, `to_hsv() -> (double, double, double)`, `operator(otro: ref<Color>) -> bool`, `to_string() -> string`

Funciones:

- `rgb(r: double, g: double, b: double) -> Color`
- `rgba(r: double, g: double, b: double, a: double) -> Color`
- `byte_a_double(valor: int) -> double`
- `from_rgb8(r: int, g: int, b: int) -> Color`
- `from_hex(valor: int) -> Color`
- `from_hsv(tono: double, saturacion: double, brillo: double) -> Color`
- `white() -> Color`
- `black() -> Color`
- `transparent() -> Color`

## `std/console`

Colores y control del terminal con secuencias ANSI.  Todas las funciones de estilo devuelven el código como `string`, así que se combinan con `+` o con `paint`. `strip` los quita, útil para medir el ancho visible o para escribir en un archivo.


Funciones:

- `esc() -> string`
- `reset() -> string`
- `bold() -> string`
- `dim() -> string`
- `italic() -> string`
- `underline() -> string`
- `blink() -> string`
- `reverse() -> string`
- `hidden() -> string`
- `black() -> string`
- `red() -> string`
- `green() -> string`
- `yellow() -> string`
- `blue() -> string`
- `magenta() -> string`
- `cyan() -> string`
- `white() -> string`
- `bright_black() -> string`
- `bright_red() -> string`
- `bright_green() -> string`
- `bright_yellow() -> string`
- `bright_blue() -> string`
- `bright_magenta() -> string`
- `bright_cyan() -> string`
- `bright_white() -> string`
- `on_black() -> string`
- `on_red() -> string`
- `on_green() -> string`
- `on_yellow() -> string`
- `on_blue() -> string`
- `on_magenta() -> string`
- `on_cyan() -> string`
- `on_white() -> string`
- `fg_256(tono: int) -> string`
- `bg_256(tono: int) -> string`
- `fg_rgb(rojo: int, verde: int, azul: int) -> string`
- `bg_rgb(rojo: int, verde: int, azul: int) -> string`
- `paint(texto: string, codigo: string) -> string`
- `paint_256(texto: string, tono: int) -> string`
- `paint_rgb(texto: string, rojo: int, verde: int, azul: int) -> string`
- `strip(texto: string) -> string`
- `clear() -> string`
- `clear_line() -> string`
- `home() -> string`
- `move_to(fila: int, columna: int) -> string`
- `move_up(filas: int) -> string`
- `move_down(filas: int) -> string`
- `move_right(columnas: int) -> string`
- `move_left(columnas: int) -> string`
- `hide_cursor() -> string`
- `show_cursor() -> string`
- `save_cursor() -> string`
- `restore_cursor() -> string`

Intrínsecos (`declare`): `esc_raw`, `strip_raw`.

## `std/crypto`

Criptografía (F8).  SHA-256 en hexadecimal; suficiente para huellas de integridad. Los hashes con clave (HMAC) y las firmas quedan fuera de 0.1.0.

Realm: `crypto`.

Funciones:

- `sha256(texto: string) -> string`
- `sha256_hex(texto: string) -> string`

Intrínsecos (`declare`): `sha256_raw`.

## `std/deque`

Realm: `deque`.

Métodos (enchantings):

- `enchanting deque<T>` — `is_empty() -> bool`, `first() -> T?`, `last() -> T?`, `get_or(indice: size_t, alternativa: T) -> T`, `index_of(buscado: T) -> size_t?`, `contains(buscado: T) -> bool`, `to_vector() -> vector<T>`, `join(separador: string) -> string`

## `std/double`

Realm: `double`.

Métodos (enchantings):

- `enchanting double` — `abs() -> double`, `min(otro: double) -> double`, `max(otro: double) -> double`, `clamp(minimo: double, maximo: double) -> double`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `between(minimo: double, maximo: double) -> bool`, `sqrt() -> double`, `cbrt() -> double`, `pow(exponente: double) -> double`, `exp() -> double`, `ln() -> double`, `log2() -> double`, `log10() -> double`, `floor() -> double`, `ceil() -> double`, `round() -> double`, `trunc() -> double`, `fract() -> double`, `round_to(decimales: int) -> double`, `hypot(otro: double) -> double`, `is_finite() -> bool`, `is_infinite() -> bool`, `is_nan() -> bool`, `is_sign_negative() -> bool`, `signum() -> double`, `lerp(hacia: double, t: double) -> double`, `approx_eq(otro: double, epsilon: double = 1e-9) -> bool`, `to_radians() -> double`, `to_degrees() -> double`, `to_fixed(decimales: int) -> string`, `to_scientific(decimales: int) -> string`, `to_int() -> int?`, `to_float() -> float?`, `to_long_double() -> long double`

## `std/easing`

Curvas de interpolación para animaciones.  Todas reciben un `t` normalizado (0.0 a 1.0) y devuelven un valor normalizado; no recortan `t` para permitir rebotes y elasticidad.


Funciones:

- `linear(t: double) -> double`
- `clamp_unit(t: double) -> double`
- `ping_pong(t: double) -> double`
- `steps(t: double, pasos: int) -> double`
- `smoothstep(borde0: double, borde1: double, x: double) -> double`
- `smootherstep(borde0: double, borde1: double, x: double) -> double`
- `quadratic_in(t: double) -> double`
- `quadratic_out(t: double) -> double`
- `quadratic_in_out(t: double) -> double`
- `cubic_in(t: double) -> double`
- `cubic_out(t: double) -> double`
- `cubic_in_out(t: double) -> double`
- `quartic_in(t: double) -> double`
- `quartic_out(t: double) -> double`
- `quartic_in_out(t: double) -> double`
- `quintic_in(t: double) -> double`
- `quintic_out(t: double) -> double`
- `sine_in(t: double) -> double`
- `sine_out(t: double) -> double`
- `sine_in_out(t: double) -> double`
- `exponential_in(t: double) -> double`
- `exponential_out(t: double) -> double`
- `exponential_in_out(t: double) -> double`
- `circular_in(t: double) -> double`
- `circular_out(t: double) -> double`
- `circular_in_out(t: double) -> double`
- `back_in(t: double) -> double`
- `back_out(t: double) -> double`
- `back_in_out(t: double) -> double`
- `bounce_out(t: double) -> double`
- `bounce_in(t: double) -> double`
- `bounce_in_out(t: double) -> double`
- `elastic_out(t: double) -> double`
- `elastic_in(t: double) -> double`
- `elastic_in_out(t: double) -> double`

## `std/encoding`

Codificación de texto: base64, hexadecimal, URL y bytes UTF-8.  Las funciones trabajan con `string` (texto ya descodificado) y con `vector<byte>` cuando el contenido puede no ser válido como UTF-8.


Funciones:

- `base64(texto: string) -> string`
- `base64_decode(texto: string) -> string?`
- `hex(texto: string) -> string`
- `hex_decode(texto: string) -> string?`
- `url_encode(texto: string) -> string`
- `url_decode(texto: string) -> string?`
- `bytes(texto: string) -> vector<byte>`
- `from_bytes(datos: vector<byte>) -> string?`
- `is_utf8(texto: string) -> bool`
- `base64_bytes(datos: vector<byte>) -> string`
- `base64_to_bytes(texto: string) -> vector<byte>?`
- `hex_bytes(datos: vector<byte>) -> string`
- `hex_to_bytes(texto: string) -> vector<byte>?`

Intrínsecos (`declare`): `base64_raw`, `base64_decode_raw`, `hex_raw`, `hex_decode_raw`, `url_raw`, `url_decode_raw`, `bytes_raw`, `bytes_text_raw`, `from_bytes_raw`, `is_utf8_raw`.

## `std/ffi`

Buffers de C: cadenas mutables para las funciones que escriben en `char*`.  Un `CString` guarda el texto en un `vector<char>` terminado en NUL, así que se puede pasar a una función C con `ptr()` y volver a leer con `text()`.

Realm: `ffi`.

Runes:

- `rune CString` — campos: `datos: vector<char>`

Métodos (enchantings):

- `enchanting CString` — `mut ptr() -> raw<char>`, `text() -> string`, `len() -> size_t`, `capacity() -> size_t`, `is_empty() -> bool`, `mut clear() -> void`, `mut set(texto: string) -> void`, `to_string() -> string`

Funciones:

- `cstring(texto: string, capacidad: size_t = …) -> CString`
- `read(texto: raw<char>) -> string`
- `write(texto: raw<char>, valor: string) -> void`

Intrínsecos (`declare`): `ptr_raw`, `text_raw`, `from_text_raw`, `read_raw`, `write_raw`.

## `std/file`

Archivos con manejador (F8).  `File` guarda un puntero de `std::FILE` como `int64_t`. Si `open` falla devuelve `none`; los métodos de lectura/escritura devuelven `T?` o `bool`, nunca abortan el proceso. Cierra siempre con `close`.

Realm: `file`.

Runes:

- `rune File` — campos: `manejador: int64_t`, `ruta: string`, `modo: string`, `abierto: bool` · constructor `File(manejador: int64_t, ruta: string, modo: string, abierto: bool)`

Métodos (enchantings):

- `enchanting File` — `is_open() -> bool`, `path() -> string`, `mode() -> string`, `mut close() -> bool`, `mut read_all() -> string?`, `mut read_line() -> string?`, `mut write(texto: string) -> bool`, `mut write_line(texto: string) -> bool`, `mut flush() -> bool`, `mut is_eof() -> bool`, `to_string() -> string`

Funciones:

- `open(ruta: string, modo: string = "r") -> File?`
- `create(ruta: string) -> File?`
- `append(ruta: string) -> File?`
- `read_text(ruta: string) -> string?`
- `write_text(ruta: string, texto: string) -> bool`
- `append_text(ruta: string, texto: string) -> bool`

Intrínsecos (`declare`): `open_raw`, `close_raw`, `read_all_raw`, `read_line_raw`, `write_raw`, `flush_raw`, `eof_raw`.

## `std/float`

Realm: `float`.

Métodos (enchantings):

- `enchanting float` — `abs() -> float`, `min(otro: float) -> float`, `max(otro: float) -> float`, `clamp(minimo: float, maximo: float) -> float`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `between(minimo: float, maximo: float) -> bool`, `sqrt() -> float`, `cbrt() -> float`, `pow(exponente: float) -> float`, `exp() -> float`, `ln() -> float`, `log2() -> float`, `log10() -> float`, `floor() -> float`, `ceil() -> float`, `round() -> float`, `trunc() -> float`, `fract() -> float`, `round_to(decimales: int) -> float`, `hypot(otro: float) -> float`, `is_finite() -> bool`, `is_infinite() -> bool`, `is_nan() -> bool`, `is_sign_negative() -> bool`, `signum() -> float`, `lerp(hacia: float, t: float) -> float`, `approx_eq(otro: float, epsilon: float) -> bool`, `to_fixed(decimales: int) -> string`, `to_scientific(decimales: int) -> string`, `to_double() -> double`, `to_int() -> int?`

Intrínsecos (`declare`): `sqrt`, `cbrt`, `pow`, `exp`, `ln`, `log2`, `log10`, `floor`, `ceil`, `round`, `trunc`, `hypot`, `is_finite`, `is_infinite`, `is_nan`, `is_sign_negative`, `to_fixed`, `to_scientific`.

## `std/format`

Realm: `format`.

Funciones:

- `format(...partes: any) -> string`
- `hex(valor: int) -> string`
- `bin(valor: int) -> string`
- `oct(valor: int) -> string`
- `pad_left(texto: string, ancho: size_t) -> string`
- `pad_left_with(texto: string, ancho: size_t, relleno: char) -> string`
- `pad_right(texto: string, ancho: size_t) -> string`
- `pad_right_with(texto: string, ancho: size_t, relleno: char) -> string`
- `center(texto: string, ancho: size_t) -> string`
- `center_with(texto: string, ancho: size_t, relleno: char) -> string`
- `join(partes: ref<vector<string>>, separador: string) -> string`
- `separated(valor: int, separador: string) -> string`
- `template(texto: string, ...partes: any) -> string`

Intrínsecos (`declare`): `format_values`, `fixed`, `scientific`, `radix`, `template_values`.

## `std/fs`

Realm: `fs`.

Funciones:

- `read_lines(ruta: string) -> vector<string>?`
- `write_lines(ruta: string, lineas: ref<vector<string>>) -> bool`
- `append_line(ruta: string, linea: string) -> bool`
- `read_or(ruta: string, respaldo: string) -> string`
- `write_new(ruta: string, contenido: string) -> bool`
- `remove_if_exists(ruta: string) -> bool`
- `ensure_dir(ruta: string) -> bool`

Intrínsecos (`declare`): `read_to_string`, `read_bytes`, `write_string`, `write_bytes`, `append_string`, `exists`, `is_file`, `is_dir`, `remove`, `create_dir`, `list_dir`, `file_size`, `rename`, `copy`, `canonicalize`.

## `std/geometry`

Geometría para juegos: vectores, rectángulos y transformaciones.  Los runes no tienen métodos estáticos, así que los constructores con nombre propio son funciones libres (`geometry::zero_vec2()`). El tipo se nombra cualificado desde otros módulos (`geometry::Vec2`).


Runes:

- `rune Vec2` — campos: `x: double`, `y: double` · constructor `Vec2(x: double, y: double)`
- `rune Vec3` — campos: `x: double`, `y: double`, `z: double` · constructor `Vec3(x: double, y: double, z: double)`
- `rune Rect` — campos: `x: double`, `y: double`, `width: double`, `height: double` · constructor `Rect(x: double, y: double, width: double, height: double)`
- `rune Transform2D` — campos: `position: Vec2`, `rotation: double`, `scale: Vec2` · constructor `Transform2D(position: Vec2, rotation: double, scale: Vec2)`

Métodos (enchantings):

- `enchanting Vec2` — `length_squared() -> double`, `length() -> double`, `dot(otro: Vec2) -> double`, `cross(otro: Vec2) -> double`, `normalized() -> Vec2`, `distance_to(otro: Vec2) -> double`, `direction_to(otro: Vec2) -> Vec2`, `lerp(hacia: Vec2, t: double) -> Vec2`, `angle() -> double`, `rotated(radianes: double) -> Vec2`, `perpendicular() -> Vec2`, `abs() -> Vec2`, `clamp_length(maximo: double) -> Vec2`, `is_zero() -> bool`, `equals(otro: Vec2, epsilon: double = 1e-9) -> bool`, `mut add(otro: ref<Vec2>) -> void`, `mut scale(factor: double) -> void`, `mut move_towards(objetivo: Vec2, paso: double) -> void`, `operator(otro: ref<Vec2>) -> Vec2`, `operator(otro: ref<Vec2>) -> Vec2`, `operator(escala: double) -> Vec2`, `operator(escala: double) -> Vec2`, `operator(otro: ref<Vec2>) -> bool`, `operator(otro: ref<Vec2>) -> Ordering`, `to_string() -> string`
- `enchanting Vec3` — `length_squared() -> double`, `length() -> double`, `dot(otro: Vec3) -> double`, `cross(otro: Vec3) -> Vec3`, `normalized() -> Vec3`, `distance_to(otro: Vec3) -> double`, `lerp(hacia: Vec3, t: double) -> Vec3`, `is_zero() -> bool`, `operator(otro: Vec3) -> Vec3`, `operator(otro: Vec3) -> Vec3`, `operator(escala: double) -> Vec3`, `operator(otro: Vec3) -> bool`, `to_string() -> string`
- `enchanting Rect` — `right() -> double`, `bottom() -> double`, `center() -> Vec2`, `area() -> double`, `is_empty() -> bool`, `contains(punto: Vec2) -> bool`, `contains_rect(otro: Rect) -> bool`, `intersects(otro: Rect) -> bool`, `intersection(otro: Rect) -> Rect?`, `union(otro: Rect) -> Rect`, `expanded(margen: double) -> Rect`, `translated(dx: double, dy: double) -> Rect`, `overlaps(punto: Vec2) -> bool`, `to_string() -> string`
- `enchanting Transform2D` — `apply(punto: Vec2) -> Vec2`, `apply_direction(direccion: Vec2) -> Vec2`, `inverse_apply(punto: Vec2) -> Vec2`, `to_string() -> string`

Funciones:

- `vec2(x: double, y: double) -> Vec2`
- `zero_vec2() -> Vec2`
- `unit_vec2(x: double, y: double) -> Vec2`
- `vec3(x: double, y: double, z: double) -> Vec3`
- `zero_vec3() -> Vec3`
- `rect(x: double, y: double, width: double, height: double) -> Rect`
- `rect_from_center(centro: Vec2, width: double, height: double) -> Rect`
- `transform_identity() -> Transform2D`
- `transform_at(posicion: Vec2) -> Transform2D`

## `std/hash`

Huellas de texto: FNV-1a, djb2, CRC-32 y Adler-32.  Sirven para tablas hash propias, cachés y comparaciones rápidas. No son criptográficas: para eso llegará `std/crypto`.


Funciones:

- `fnv1a32(texto: string) -> uint32_t`
- `fnv1a64(texto: string) -> uint64_t`
- `djb2(texto: string) -> uint32_t`
- `crc32(texto: string) -> uint32_t`
- `adler32(texto: string) -> uint32_t`
- `hex32(valor: uint32_t) -> string`
- `hex64(valor: uint64_t) -> string`
- `fnv1a32_hex(texto: string) -> string`
- `fnv1a64_hex(texto: string) -> string`
- `crc32_hex(texto: string) -> string`

Intrínsecos (`declare`): `fnv1a32_raw`, `fnv1a64_raw`, `djb2_raw`, `crc32_raw`, `adler32_raw`, `hex32_raw`, `hex64_raw`.

## `std/int`

Realm: `int`.

Métodos (enchantings):

- `enchanting int` — `abs() -> int`, `min(otro: int) -> int`, `max(otro: int) -> int`, `clamp(minimo: int, maximo: int) -> int`, `is_even() -> bool`, `is_odd() -> bool`, `sign() -> int`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `between(minimo: int, maximo: int) -> bool`, `div_floor(otro: int) -> int`, `div_ceil(otro: int) -> int`, `mod_floor(otro: int) -> int`, `mod_euclid(otro: int) -> int`, `pow(exponente: int) -> int`, `wrap(minimo: int, maximo: int) -> int`, `next_multiple_of(paso: int) -> int`, `abs_diff(otro: int) -> int`, `digits() -> size_t`, `is_power_of_two() -> bool`, `to_double() -> double`, `to_float() -> float`, `to_int64() -> int64_t`, `to_size() -> size_t`, `to_radix(base: int) -> string`

## `std/integers`

Realm: `integers`.

Métodos (enchantings):

- `enchanting int8_t` — `abs() -> int8_t`, `min(otro: int8_t) -> int8_t`, `max(otro: int8_t) -> int8_t`, `clamp(minimo: int8_t, maximo: int8_t) -> int8_t`, `sign() -> int`, `is_even() -> bool`, `is_odd() -> bool`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `min_value() -> int8_t`, `max_value() -> int8_t`, `to_int() -> int?`, `to_int64() -> int64_t?`, `to_uint64() -> uint64_t?`, `to_double() -> double`, `to_size() -> size_t?`
- `enchanting int16_t` — `abs() -> int16_t`, `min(otro: int16_t) -> int16_t`, `max(otro: int16_t) -> int16_t`, `clamp(minimo: int16_t, maximo: int16_t) -> int16_t`, `sign() -> int`, `is_even() -> bool`, `is_odd() -> bool`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `min_value() -> int16_t`, `max_value() -> int16_t`, `to_int() -> int?`, `to_int64() -> int64_t?`, `to_uint64() -> uint64_t?`, `to_double() -> double`, `to_size() -> size_t?`
- `enchanting int32_t` — `abs() -> int32_t`, `min(otro: int32_t) -> int32_t`, `max(otro: int32_t) -> int32_t`, `clamp(minimo: int32_t, maximo: int32_t) -> int32_t`, `sign() -> int`, `is_even() -> bool`, `is_odd() -> bool`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `min_value() -> int32_t`, `max_value() -> int32_t`, `to_int() -> int?`, `to_int64() -> int64_t?`, `to_uint64() -> uint64_t?`, `to_double() -> double`, `to_size() -> size_t?`
- `enchanting int64_t` — `abs() -> int64_t`, `min(otro: int64_t) -> int64_t`, `max(otro: int64_t) -> int64_t`, `clamp(minimo: int64_t, maximo: int64_t) -> int64_t`, `sign() -> int`, `is_even() -> bool`, `is_odd() -> bool`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `min_value() -> int64_t`, `max_value() -> int64_t`, `to_int() -> int?`, `to_int64() -> int64_t?`, `to_uint64() -> uint64_t?`, `to_double() -> double`, `to_size() -> size_t?`
- `enchanting uint8_t` — `min(otro: uint8_t) -> uint8_t`, `max(otro: uint8_t) -> uint8_t`, `clamp(minimo: uint8_t, maximo: uint8_t) -> uint8_t`, `is_even() -> bool`, `is_odd() -> bool`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `min_value() -> uint8_t`, `max_value() -> uint8_t`, `to_int() -> int?`, `to_int64() -> int64_t?`, `to_uint64() -> uint64_t?`, `to_double() -> double`, `to_size() -> size_t?`
- `enchanting uint16_t` — `min(otro: uint16_t) -> uint16_t`, `max(otro: uint16_t) -> uint16_t`, `clamp(minimo: uint16_t, maximo: uint16_t) -> uint16_t`, `is_even() -> bool`, `is_odd() -> bool`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `min_value() -> uint16_t`, `max_value() -> uint16_t`, `to_int() -> int?`, `to_int64() -> int64_t?`, `to_uint64() -> uint64_t?`, `to_double() -> double`, `to_size() -> size_t?`
- `enchanting uint32_t` — `min(otro: uint32_t) -> uint32_t`, `max(otro: uint32_t) -> uint32_t`, `clamp(minimo: uint32_t, maximo: uint32_t) -> uint32_t`, `is_even() -> bool`, `is_odd() -> bool`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `min_value() -> uint32_t`, `max_value() -> uint32_t`, `to_int() -> int?`, `to_int64() -> int64_t?`, `to_uint64() -> uint64_t?`, `to_double() -> double`, `to_size() -> size_t?`
- `enchanting uint64_t` — `min(otro: uint64_t) -> uint64_t`, `max(otro: uint64_t) -> uint64_t`, `clamp(minimo: uint64_t, maximo: uint64_t) -> uint64_t`, `is_even() -> bool`, `is_odd() -> bool`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `min_value() -> uint64_t`, `max_value() -> uint64_t`, `to_int() -> int?`, `to_int64() -> int64_t?`, `to_uint64() -> uint64_t?`, `to_double() -> double`, `to_size() -> size_t?`

Intrínsecos (`declare`): `int8_max`, `int8_min`, `int16_max`, `int16_min`, `int32_max`, `int32_min`, `int64_max`, `int64_min`, `uint8_max`, `uint8_min`, `uint16_max`, `uint16_min`, `uint32_max`, `uint32_min`, `uint64_max`, `uint64_min`.

## `std/io`

Realm: `io`.

Funciones:

- `println(...partes: any) -> void`
- `print(...partes: any) -> void`
- `eprintln(...partes: any) -> void`
- `eprint(...partes: any) -> void`
- `read_line_trimmed() -> string`

Intrínsecos (`declare`): `write_values`, `eprint_values`, `read_line`, `read_all`, `flush`, `is_terminal`, `read_char`.

## `std/iter`

Realm: `iter`.

Funciones:

- `map(items: ref<vector<T>>, f: function<(T) -> U>) -> vector<U>`
- `filter(items: ref<vector<T>>, f: function<(T) -> bool>) -> vector<T>`
- `fold(items: ref<vector<T>>, inicial: A, f: function<(A, T) -> A>) -> A`
- `count_if(items: ref<vector<T>>, f: function<(T) -> bool>) -> size_t`
- `any(items: ref<vector<T>>, f: function<(T) -> bool>) -> bool`
- `all(items: ref<vector<T>>, f: function<(T) -> bool>) -> bool`
- `none_of(items: ref<vector<T>>, f: function<(T) -> bool>) -> bool`
- `find(items: ref<vector<T>>, f: function<(T) -> bool>) -> T?`
- `position(items: ref<vector<T>>, f: function<(T) -> bool>) -> size_t?`
- `zip(a: ref<vector<A>>, b: ref<vector<B>>) -> vector<pair<A, B>>`
- `enumerate(items: ref<vector<T>>) -> vector<pair<size_t, T>>`
- `take(items: ref<vector<T>>, cantidad: size_t) -> vector<T>`
- `skip(items: ref<vector<T>>, cantidad: size_t) -> vector<T>`
- `chain(a: ref<vector<T>>, b: ref<vector<T>>) -> vector<T>`
- `flatten(items: ref<vector<vector<T>>>) -> vector<T>`

## `std/json`

Realm: `json`.

Omens:

- `omen Value` — Null; Bool(bool); Number(double); Text(string); Array(vector<Value>); Object(vector<string>, vector<Value>)

Runes:

- `rune JsonParser` — campos: `texto: string`, `indice: size_t`, `error: string` · constructor `JsonParser(texto: string)`

Métodos (enchantings):

- `enchanting JsonParser` — `mut fallo(mensaje: string) -> void`, `terminado() -> bool`, `actual() -> char`, `mut avanza() -> void`, `mut saltar() -> void`, `mut esperar(caracter: char) -> bool`, `digito_hex(caracter: char) -> int`, `mut leer_hex4() -> int?`, `mut parse_string() -> string?`, `mut cerrar_numero(inicio: size_t) -> double?`, `mut parse_number() -> double?`, `mut parse_literal(texto: string, resultado: Value) -> Value?`, `mut parse_value() -> Value?`, `mut parse_array() -> Value?`, `mut parse_object() -> Value?`

Funciones:

- `null_value() -> Value`
- `bool_value(valor: bool) -> Value`
- `number_value(valor: double) -> Value`
- `int_value(valor: int) -> Value`
- `text_value(valor: string) -> Value`
- `array_value(elementos: vector<Value>) -> Value`
- `object_empty() -> Value`
- `object_value(claves: vector<string>, valores: vector<Value>) -> Value`
- `array_empty() -> Value`
- `is_null(valor: Value) -> bool`
- `as_bool(valor: Value) -> bool?`
- `as_number(valor: Value) -> double?`
- `as_int(valor: Value) -> int?`
- `as_text(valor: Value) -> string?`
- `as_array(valor: Value) -> vector<Value>?`
- `length(valor: Value) -> size_t`
- `keys(valor: Value) -> vector<string>`
- `has(valor: Value, clave: string) -> bool`
- `get(valor: Value, clave: string) -> Value?`
- `at(valor: Value, indice: size_t) -> Value?`
- `escaped_text(texto: string) -> string`
- `write_number(numero: double) -> string`
- `write_value(valor: Value) -> string`
- `stringify(valor: Value) -> string`
- `indent(nivel: int, sangria: int) -> string`
- `write_pretty(valor: Value, sangria: int, nivel: int) -> string`
- `pretty(valor: Value, sangria: int = 2) -> string`
- `parse(texto: string) -> Value?`
- `error(texto: string) -> string?`

Intrínsecos (`declare`): `code_char_raw`.

## `std/log`

Realm: `log`.

Omens:

- `omen Level` — Debug; Info; Warn; Error

Métodos (enchantings):

- `enchanting Level` — `name() -> string`, `to_int() -> int`

Funciones:

- `debug(...partes: any) -> void`
- `info(...partes: any) -> void`
- `warn(...partes: any) -> void`
- `error(...partes: any) -> void`
- `set_level(nivel: Level) -> void`
- `level() -> Level`
- `enabled(nivel: Level) -> bool`
- `timestamped(activo: bool) -> void`

Intrínsecos (`declare`): `log_values`, `set_level_raw`, `level_raw`, `enabled_raw`, `timestamped_raw`.

## `std/long_double`

Realm: `long_double`.

Métodos (enchantings):

- `enchanting long double` — `abs() -> long double`, `min(otro: long double) -> long double`, `max(otro: long double) -> long double`, `clamp(minimo: long double, maximo: long double) -> long double`, `is_positive() -> bool`, `is_negative() -> bool`, `is_zero() -> bool`, `between(minimo: long double, maximo: long double) -> bool`, `sqrt() -> long double`, `cbrt() -> long double`, `pow(exponente: long double) -> long double`, `exp() -> long double`, `ln() -> long double`, `log2() -> long double`, `log10() -> long double`, `floor() -> long double`, `ceil() -> long double`, `round() -> long double`, `trunc() -> long double`, `fract() -> long double`, `round_to(decimales: int) -> long double`, `hypot(otro: long double) -> long double`, `is_finite() -> bool`, `is_infinite() -> bool`, `is_nan() -> bool`, `is_sign_negative() -> bool`, `signum() -> long double`, `lerp(hacia: long double, t: long double) -> long double`, `approx_eq(otro: long double, epsilon: long double = 1e-6) -> bool`, `to_fixed(decimales: int) -> string`, `to_scientific(decimales: int) -> string`, `to_double() -> double?`, `to_float() -> float?`, `to_int() -> int?`

Intrínsecos (`declare`): `sqrt`, `cbrt`, `pow`, `exp`, `ln`, `log2`, `log10`, `floor`, `ceil`, `round`, `trunc`, `hypot`, `is_finite`, `is_infinite`, `is_nan`, `is_sign_negative`, `to_fixed`, `to_scientific`.

## `std/map`

Realm: `map`.

Métodos (enchantings):

- `enchanting map<K, V>` — `is_empty() -> bool`, `contains_key(clave: K) -> bool`, `keys_list() -> vector<K>`, `values_list() -> vector<V>`, `mut get_or_insert(clave: K, alternativa: V) -> V`, `mut update(clave: K, cambiar: function<(V) -> V>) -> bool`, `entries() -> vector<pair<K, V>>`, `first_key() -> K?`, `last_key() -> K?`, `mut merge(otro: ref<map<K, V>>) -> void`, `mut retain(predicado: function<(K, V) -> bool>) -> void`

## `std/math`

Realm: `math`.

Constantes:

- `pi: double`
- `e: double`
- `tau: double`
- `phi: double`
- `sqrt2: double`
- `ln2: double`
- `ln10: double`
- `radians_per_degree: double`
- `degrees_per_radian: double`

Funciones:

- `lerp(a: double, b: double, t: double) -> double`
- `inverse_lerp(a: double, b: double, value: double) -> double`
- `remap(value: double, in_low: double, in_high: double, out_low: double, out_high: double) -> double`
- `clamp01(value: double) -> double`
- `sign(value: double) -> double`
- `smoothstep(edge0: double, edge1: double, x: double) -> double`
- `smootherstep(edge0: double, edge1: double, x: double) -> double`
- `deg_to_rad(grados: double) -> double`
- `rad_to_deg(radianes: double) -> double`
- `wrap(value: double, low: double, high: double) -> double`
- `wrap_angle(angulo: double) -> double`
- `lerp_angle(a: double, b: double, t: double) -> double`
- `move_towards(actual: double, objetivo: double, paso: double) -> double`
- `damp(actual: double, objetivo: double, lambda: double, dt: double) -> double`
- `approx_eq(a: double, b: double, epsilon: double = 1e-9) -> bool`
- `min3(a: double, b: double, c: double) -> double`
- `max3(a: double, b: double, c: double) -> double`
- `average(a: double, b: double) -> double`
- `ipow(base: int, exponente: int) -> int`
- `is_power_of_two(value: int) -> bool`
- `next_power_of_two(value: int) -> int`
- `align_up(value: int, align: int) -> int`

Intrínsecos (`declare`): `abs`, `sqrt`, `cbrt`, `floor`, `ceil`, `round`, `trunc`, `nearbyint`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`, `exp`, `exp2`, `expm1`, `ln`, `log2`, `log10`, `log1p`, `pow`, `hypot`, `fmod`, `remainder`, `fdim`, `fmax`, `fmin`, `copysign`, `fma`, `min`, `max`, `clamp`, `signbit`, `is_finite`, `is_infinite`, `is_nan`, `infinite`, `not_a_number`, `gcd`, `lcm`.

## `std/memory`

Realm: `memory`.

Métodos (enchantings):

- `enchanting unique<T>` — `get() -> ref<T>`, `mut set(valor: T) -> void`
- `enchanting shared<T>` — `get() -> ref<T>`, `mut set(valor: T) -> void`
- `enchanting weak<T>` — `is_alive() -> bool`

## `std/noise`

Ruido de valor determinista: sirve para terreno, texturas y temblores.  Es una función pura de (coordenada, semilla): la misma entrada da siempre el mismo resultado, sin estado global. El ruido fractal suma varias octavas y normaliza el resultado a 0..1.


Funciones:

- `hash(x: double, y: double, semilla: int) -> double`
- `suavizar(t: double) -> double`
- `mezclar(a: double, b: double, t: double) -> double`
- `value_1d(x: double, semilla: int = 0) -> double`
- `value_2d(x: double, y: double, semilla: int = 0) -> double`
- `signed_2d(x: double, y: double, semilla: int = 0) -> double`
- `fractal_2d(x: double, y: double, octavas: int, semilla: int = 0, lacunaridad: double = 2.0, ganancia: double = 0.5) -> double`
- `turbulence_2d(x: double, y: double, octavas: int, semilla: int = 0, lacunaridad: double = 2.0, ganancia: double = 0.5) -> double`
- `ridged_2d(x: double, y: double, octavas: int, semilla: int = 0) -> double`

## `std/optional`

Realm: `optional`.

Métodos (enchantings):

- `enchanting T?` — `is_empty() -> bool`, `or_else(alternativa: T) -> T`, `filter(predicado: function<(T) -> bool>) -> T?`, `to_vector() -> vector<T>`, `map(transformar: function<(T) -> T>) -> T?`, `and_then(siguiente: function<(T) -> T?>) -> T?`, `or_else_get(alternativa: function<() -> T>) -> T`, `zip(otro: T?) -> pair<T, T>?`, `any(predicado: function<(T) -> bool>) -> bool`

## `std/ordering`

Realm: `ordering`.

Métodos (enchantings):

- `enchanting Ordering` — `then(otro: Ordering) -> Ordering`, `to_int() -> int`, `then_with(siguiente: function<() -> Ordering>) -> Ordering`

## `std/os`

Realm: `os`.

Funciones:

- `env_or(nombre: string, respaldo: string) -> string`
- `has_env(nombre: string) -> bool`

Intrínsecos (`declare`): `args`, `get_env`, `set_env`, `exit`, `pid`, `home_dir`, `temp_dir`, `current_dir`, `platform`, `arch`, `cpu_count`.

## `std/pair`

Realm: `pair`.

Métodos (enchantings):

- `enchanting pair<A, B>` — `swap() -> pair<B, A>`, `to_tuple() -> (A, B)`

## `std/path`

Realm: `path`.

Constantes:

- `separator: string`

Funciones:

- `is_absolute(ruta: string) -> bool`
- `join(base: string, resto: string) -> string`
- `join_all(partes: ref<vector<string>>) -> string`
- `file_name(ruta: string) -> string?`
- `extension(ruta: string) -> string?`
- `stem(ruta: string) -> string?`
- `parent_dir(ruta: string) -> string?`
- `with_extension(ruta: string, nueva: string) -> string`
- `normalize(ruta: string) -> string`
- `components(ruta: string) -> vector<string>`

## `std/physics`

Cuerpos rígidos muy sencillos: integración, gravedad y rebotes.  Es física de juego, no simulación: sin rotación ni fricción real, con amortiguación y rebote configurables. Todo se mide en unidades del juego (píxeles, metros) por segundo.


Runes:

- `rune Body` — campos: `position: geometry::Vec2`, `velocity: geometry::Vec2`, `mass: double`, `restitution: double` · constructor `Body(position: geometry::Vec2, velocity: geometry::Vec2, mass: double, restitution: double)`

Métodos (enchantings):

- `enchanting Body` — `speed() -> double`, `is_moving() -> bool`, `momentum() -> geometry::Vec2`, `kinetic_energy() -> double`, `mut apply_force(fuerza: geometry::Vec2, dt: double) -> void`, `mut apply_impulse(impulso: geometry::Vec2) -> void`, `mut apply_gravity(gravedad: geometry::Vec2, dt: double) -> void`, `mut integrate(dt: double) -> void`, `mut damp(coeficiente: double, dt: double) -> void`, `mut bounce_floor(suelo: double, restitucion: double) -> void`, `mut bounce_bounds(ancho: double, alto: double, restitucion: double) -> void`, `mut stop() -> void`, `to_string() -> string`

Funciones:

- `body(posicion: geometry::Vec2, velocidad: geometry::Vec2, masa: double, restitucion: double) -> Body`
- `body_at(posicion: geometry::Vec2) -> Body`
- `body_moving(posicion: geometry::Vec2, velocidad: geometry::Vec2) -> Body`
- `gravity_force(masa: double, gravedad: geometry::Vec2) -> geometry::Vec2`
- `step(cuerpo: Body, gravedad: geometry::Vec2, amortiguacion: double, dt: double) -> Body`

## `std/process`

Procesos del sistema (F8).  `run`/`status` ejecutan una orden con el shell y devuelven el código de salida; `output` captura la salida estándar. `exit` termina el proceso.

Realm: `process`.

Funciones:

- `run(comando: string) -> int`
- `status(comando: string) -> bool`
- `output(comando: string) -> string`
- `exit(codigo: int) -> void`

Intrínsecos (`declare`): `run_raw`, `output_raw`, `status_raw`, `exit_raw`.

## `std/random`

Realm: `random`.

Funciones:

- `chance(probabilidad: double) -> bool`
- `int_range(desde: int, hasta: int) -> int`
- `seed_from_time() -> void`

Intrínsecos (`declare`): `int`, `float`, `bool`, `seed`, `float_range`.

## `std/result`

Realm: `result`.

Runes:

- `rune Result` — campos: `dato: T?`, `fallo: E?` · constructor `Result(dato: T?, fallo: E?)`

Métodos (enchantings):

- `enchanting Result` — `is_ok() -> bool`, `is_err() -> bool`, `value_or(respaldo: T) -> T`, `value() -> T`, `error_or(respaldo: E) -> E`, `error() -> E`, `expect(mensaje: string) -> T`, `to_string() -> string`

Funciones:

- `ok(dato: T) -> Result<T, E>`
- `err(fallo: E) -> Result<T, E>`
- `map(resultado: Result<T, E>, f: function<(T) -> U>) -> Result<U, E>`
- `map_err(resultado: Result<T, E>, f: function<(E) -> U>) -> Result<T, U>`
- `and_then(resultado: Result<T, E>, f: function<(T) -> Result<U, E>>) -> Result<U, E>`
- `from_optional(valor: T?, fallo: E) -> Result<T, E>`

## `std/set`

Realm: `set`.

Métodos (enchantings):

- `enchanting set<T>` — `is_empty() -> bool`, `contains(valor: T) -> bool`, `to_vector() -> vector<T>`, `union(otro: ref<set<T>>) -> set<T>`, `intersection(otro: ref<set<T>>) -> set<T>`, `difference(otro: ref<set<T>>) -> set<T>`, `symmetric_difference(otro: ref<set<T>>) -> set<T>`, `is_subset(otro: ref<set<T>>) -> bool`, `is_superset(otro: ref<set<T>>) -> bool`, `is_disjoint(otro: ref<set<T>>) -> bool`, `mut insert_all(otro: ref<set<T>>) -> void`, `mut remove_all(otro: ref<set<T>>) -> void`, `mut extend(valores: ref<vector<T>>) -> void`, `mut retain(predicado: function<(T) -> bool>) -> void`, `first() -> T?`, `last() -> T?`, `map(transformar: function<(T) -> T>) -> set<T>`, `filter(predicado: function<(T) -> bool>) -> set<T>`, `to_sorted_vector() -> vector<T>`

## `std/sort`

Realm: `sort`.

Funciones:

- `insertion_sort(mut items: ref<vector<T>>) -> void`
- `is_sorted(items: ref<vector<T>>) -> bool`
- `binary_search_sorted(items: ref<vector<T>>, buscado: T) -> size_t?`
- `sorted_copy(items: ref<vector<T>>) -> vector<T>`

## `std/string`

Realm: `string`.

Métodos (enchantings):

- `enchanting string` — `compare(otro: string) -> int`, `to_upper() -> string`, `to_lower() -> string`, `compare_ignore_case(otro: string) -> int`, `is_empty() -> bool`, `starts_with(prefijo: string) -> bool`, `ends_with(sufijo: string) -> bool`, `contains(buscado: string) -> bool`, `find(buscado: string) -> size_t?`, `rfind(buscado: string) -> size_t?`, `find_from(buscado: string, desde: size_t) -> size_t?`, `count(buscado: string) -> size_t`, `trim() -> string`, `trim_start() -> string`, `trim_end() -> string`, `trim_start_matches(c: char) -> string`, `trim_end_matches(c: char) -> string`, `trim_matches(c: char) -> string`, `capitalize() -> string`, `decapitalize() -> string`, `title_case() -> string`, `replace(viejo: string, nuevo: string) -> string`, `replace_first(viejo: string, nuevo: string) -> string`, `remove_prefix(prefijo: string) -> string`, `remove_suffix(sufijo: string) -> string`, `split(separador: string) -> vector<string>`, `split_whitespace() -> vector<string>`, `split_lines() -> vector<string>`, `chars() -> vector<char>`, `bytes() -> vector<uint8_t>`, `char_count() -> size_t`, `get(i: size_t) -> char?`, `mut pop() -> char?`, `repeat(veces: int) -> string`, `pad_start_with(ancho: size_t, relleno: char) -> string`, `pad_start(ancho: size_t) -> string`, `pad_end_with(ancho: size_t, relleno: char) -> string`, `pad_end(ancho: size_t) -> string`, `pad_center_with(ancho: size_t, relleno: char) -> string`, `pad_center(ancho: size_t) -> string`, `reverse() -> string`, `insert_at(i: size_t, texto: string) -> string`, `remove_range(inicio: size_t, largo: size_t) -> string`, `truncate(largo: size_t) -> string`, `substring(inicio: size_t, fin: size_t) -> string`, `is_ascii() -> bool`, `is_alphabetic() -> bool`, `is_numeric() -> bool`, `is_alphanumeric() -> bool`, `is_whitespace() -> bool`, `is_upper() -> bool`, `is_lower() -> bool`, `to_int() -> int?`, `to_double() -> double?`, `to_bool() -> bool?`, `escape() -> string`, `unescape() -> string`

Intrínsecos (`declare`): `find_raw`, `rfind_raw`, `find_from_raw`, `trim_raw`, `to_upper_raw`, `to_lower_raw`, `split_raw`, `split_whitespace_raw`, `replace_first_raw`, `reverse_raw`, `char_count_raw`, `parse_int_raw`, `parse_double_raw`, `bytes_raw`.

## `std/test`

Realm: `test`.

Funciones:

- `is_true(valor: bool, mensaje: string = "se esperaba true") -> void`
- `is_false(valor: bool, mensaje: string = "se esperaba false") -> void`
- `equal(actual: T, esperado: T, mensaje: string = "los valores no coinciden") -> void`
- `not_equal(actual: T, esperado: T, mensaje: string = "los valores coinciden") -> void`
- `is_some(valor: T?, mensaje: string = "se esperaba un valor") -> void`
- `is_none(valor: T?, mensaje: string = "se esperaba none") -> void`

## `std/time`

Realm: `time`.

Runes:

- `rune Duration` — campos: `millis: int64_t` · constructor `Duration(millis: int64_t)`
- `rune DateTime` — campos: `millis: int64_t`, `year: int`, `month: int`, `day: int`, `hour: int`, `minute: int`, `second: int` · constructor `DateTime(millis: int64_t, year: int, month: int, day: int, hour: int, minute: int, second: int)`
- `rune Instant` — campos: `millis: int64_t` · constructor `Instant(millis: int64_t)`

Métodos (enchantings):

- `enchanting Duration` — `as_millis() -> int64_t`, `as_seconds() -> double`, `as_seconds_int() -> int64_t`, `as_minutes() -> double`, `is_zero() -> bool`, `is_negative() -> bool`, `abs() -> Duration`, `scaled(factor: double) -> Duration`, `add(otra: Duration) -> Duration`, `sub(otra: Duration) -> Duration`, `to_string() -> string`, `operator(otra: Duration) -> Duration`, `operator(otra: Duration) -> Duration`, `operator(factor: int64_t) -> Duration`, `operator(otra: Duration) -> Ordering`, `operator(otra: Duration) -> bool`
- `enchanting DateTime` — `to_string() -> string`, `as_millis() -> int64_t`
- `enchanting Instant` — `as_millis() -> int64_t`, `as_seconds() -> double`, `add(duracion: Duration) -> Instant`, `sub(duracion: Duration) -> Instant`, `elapsed() -> Duration`, `until(otro: Instant) -> Duration`, `to_string() -> string`, `to_datetime() -> DateTime`, `operator(otro: Instant) -> Duration`, `operator(otro: Instant) -> Ordering`

Funciones:

- `datetime_from_millis(millis: int64_t) -> DateTime`
- `datetime_now() -> DateTime`
- `duration_from_millis(millis: int64_t) -> Duration`
- `duration_from_seconds(segundos: int64_t) -> Duration`
- `duration_from_double_seconds(segundos: double) -> Duration`
- `duration_from_minutes(minutos: int64_t) -> Duration`
- `duration_from_hours(horas: int64_t) -> Duration`
- `duration_from_days(dias: int64_t) -> Duration`
- `duration_zero() -> Duration`
- `instant_now() -> Instant`
- `instant_from_millis(millis: int64_t) -> Instant`

Intrínsecos (`declare`): `now_millis`, `now_nanos`, `now_seconds`, `monotonic_millis`, `monotonic_nanos`, `sleep_millis`, `parts`, `format_datetime`.

## `std/tuple`

Realm: `tuple`.

Métodos (enchantings):

- `enchanting (A, B)` — `len() -> size_t`, `swap() -> (B, A)`, `to_pair() -> pair<A, B>`
- `enchanting (A, B, C)` — `len() -> size_t`, `first() -> A`, `second() -> B`, `third() -> C`

## `std/vector`

Realm: `vector`.

Métodos (enchantings):

- `enchanting vector<T>` — `is_empty() -> bool`, `first() -> T?`, `last() -> T?`, `index_of(buscado: T) -> size_t?`, `contains(buscado: T) -> bool`, `join(separador: string) -> string`, `mut reverse() -> void`, `mut sort() -> void`, `get_or(indice: size_t, alternativa: T) -> T`, `first_or(alternativa: T) -> T`, `last_or(alternativa: T) -> T`, `mut remove(valor: T) -> bool`, `mut remove_all(valor: T) -> size_t`, `mut extend(otro: ref<vector<T>>) -> void`, `mut retain(predicado: function<(T) -> bool>) -> void`, `mut fill(valor: T) -> void`, `mut swap(i: size_t, j: size_t) -> void`, `mut rotate_left(n: size_t) -> void`, `mut rotate_right(n: size_t) -> void`, `any(predicado: function<(T) -> bool>) -> bool`, `all(predicado: function<(T) -> bool>) -> bool`, `none(predicado: function<(T) -> bool>) -> bool`, `count_if(predicado: function<(T) -> bool>) -> size_t`, `find_if(predicado: function<(T) -> bool>) -> T?`, `position_if(predicado: function<(T) -> bool>) -> size_t?`, `fold(combinar: function<(T, T) -> T>, inicial: T) -> T`, `map(transformar: function<(T) -> T>) -> vector<T>`, `filter(predicado: function<(T) -> bool>) -> vector<T>`, `mut transform(transformar: function<(T) -> T>) -> void`, `min() -> T?`, `max() -> T?`, `is_sorted() -> bool`, `mut sort_by(comparar: function<(T, T) -> int>) -> void`, `sorted() -> vector<T>`, `sorted_by(comparar: function<(T, T) -> int>) -> vector<T>`, `mut dedup() -> void`, `binary_search(valor: T) -> size_t?`, `take(n: size_t) -> vector<T>`, `skip(n: size_t) -> vector<T>`, `slice(inicio: size_t, largo: size_t) -> vector<T>`, `chunks(tamano: size_t) -> vector<vector<T>>`, `windows(tamano: size_t) -> vector<vector<T>>`, `enumerate() -> vector<pair<size_t, T>>`
