# STDLIB — inventario de superficie

Acompaña a [`scratch/STDLIB_PLAN.md`](STDLIB_PLAN.md).
Normativo: `docs/STDLIB.md` 0.3.0. Este archivo registra **solo lo que falta o
cambia** respecto de ese doc, más el reparto de clases de implementación.

## Leyenda

| Columna | Significado |
|---|---|
| `clase` | `P` = cuerpo Pengu puro · `I` = intrínseco `abi "pengu"` · `D` = paso directo a método Rust (se declara como intrínseco trivial) |
| `origen` | qué lenguaje justifica el método: `Rs` Rust, `Py` Python 3.12, `Go` Go 1.22, `Kt` Kotlin, `V` V |
| `estado` | ⬜ pendiente · 🔄 en curso · ✅ hecho · 🚫 descartado (con razón) |

Regla: **una fila = un método**. La fase no se cierra hasta que todas sus filas
estén ✅ o 🚫.

---

> **Estado (S4).** Cerrados `integrum` (63), `floatem` (57), `littera` (33),
> `opera` (8 pactos), `veritas` (9), `verbum` (50 `Str` + 22 `String`),
> `capsa` (55), `tabula` (20), `fasciculus` (25), `numerus` (9 `sigil` + 65
> funciones), `fluxus` (6 funciones + `IoError` + `Reader`/`Writer`) y `proba`
> (9 aserciones).
> De `integrum` faltan `from_str`, `from_str_radix`, `MIN`, `MAX` y `BITS`; de
> `floatem`, las constantes (`EPSILON`, `MIN`, `MAX`, `MIN_POSITIVE`, `NAN`,
> `INFINITY`, `NEG_INFINITY`) y `from_str`; de `verbum`, lo que depende de
> `funis`/`Range`: `chars`, `bytes`, `char_indices`, `matches`,
> `match_indices`, `parse[T]`, `get`, `as_bytes`, `from_utf8*`, `drain`,
> `retain`. Sigue en diseño desde `capsa` (S3).

## Anexo A — Deltas por módulo

### `bool` (S1)

El doc no lo lista como módulo propio. Se crea `std/bool.pengu`.

| método | firma | clase | origen | estado |
|---|---|---|---|---|
| `switch` | `(@own) -> Bool` | P | doc §12 | ⬜ |
| `then` | `(@own, f: [Unit] -> T) -> Option[T]` | P | Rs | ⬜ |
| `and_then` | `(@own, f: [Bool] -> Bool) -> Bool` | P | Rs | ⬜ |
| `not` | `(@own) -> Bool` | P | Kt | ⬜ |
| `to_int` | `(@own) -> Int` | P | Py | ⬜ |
| `to_str` | `(@own) -> Str` | P | Py | ⬜ |

### `integrum` (S1) — doc ~60, +18

Añadir a `docs/STDLIB.md` §2:

| método | firma | clase | origen | estado |
|---|---|---|---|---|
| `leading_ones` | `(@own) -> Int` | I | Rs | ⬜ |
| `trailing_ones` | `(@own) -> Int` | I | Rs | ⬜ |
| `checked_neg` | `(@own) -> Option[Int]` | P | Rs | ⬜ |
| `checked_pow` | `(@own, exp: U32) -> Option[Int]` | P | Rs | ⬜ |
| `checked_div_euclid` | `(@own, rhs: Int) -> Option[Int]` | P | Rs | ⬜ |
| `checked_rem_euclid` | `(@own, rhs: Int) -> Option[Int]` | P | Rs | ⬜ |
| `div_euclid` | `(@own, rhs: Int) -> Int` | P | Rs | ⬜ |
| `rem_euclid` | `(@own, rhs: Int) -> Int` | P | Rs | ⬜ |
| `abs_diff` | `(@own, other: Int) -> U32` | P | Rs | ⬜ |
| `signum` | `(@own) -> Int` | P | Rs | ⬜ |
| `is_positive` | `(@own) -> Bool` | P | Rs | ⬜ |
| `is_negative` | `(@own) -> Bool` | P | Rs | ⬜ |
| `next_multiple_of` | `(@own, rhs: Int) -> Int` | P | Rs | ⬜ |
| `to_be_bytes` | `(@own) -> [U8; 4]` | I | Rs | ⬜ |
| `to_le_bytes` | `(@own) -> [U8; 4]` | I | Rs | ⬜ |
| `to_ne_bytes` | `(@own) -> [U8; 4]` | I | Rs | ⬜ |
| `from_be_bytes` | `(bytes: &[U8; 4]) -> Int` | I | Rs | ⬜ |
| `from_le_bytes` | `(bytes: &[U8; 4]) -> Int` | I | Rs | ⬜ |
| `bit_length` | `(@own) -> Int` | P | Py | ⬜ |
| `to_float` | `(@own) -> Float` | I | — | ⬜ |
| `to_string` | `(@own) -> String` | P | — | ⬜ |

Nota: `wrapping_pow`, `saturating_pow`, `overflowing_pow`, `wrapping_neg`,
`wrapping_div`, `saturating_div`, `overflowing_div`, `wrapping_rem`,
`overflowing_rem` también entran (el doc solo cubre `add/sub/mul`).

### `floatem` (S1) — doc ~55, +12

| método | firma | clase | origen | estado |
|---|---|---|---|---|
| `hypot` | `(@own, other: Float) -> Float` | I | Rs | ⬜ |
| `copysign` | `(@own, sign: Float) -> Float` | I | Rs | ⬜ |
| `rem_euclid` | `(@own, rhs: Float) -> Float` | I | Rs | ⬜ |
| `div_euclid` | `(@own, rhs: Float) -> Float` | I | Rs | ⬜ |
| `recip` | `(@own) -> Float` | I | Rs | ⬜ |
| `to_degrees` | `(@own) -> Float` | P | Rs | ⬜ |
| `to_radians` | `(@own) -> Float` | P | Rs | ⬜ |
| `round_ties_even` | `(@own) -> Float` | I | Rs | ⬜ |
| `signum` | `(@own) -> Float` | P | Rs | ⬜ |
| `is_normal` | `(@own) -> Bool` | I | Rs | ⬜ |
| `is_integer` | `(@own) -> Bool` | P | Py | ⬜ |
| `as_integer_ratio` | `(@own) -> (Int, Int)` | P | Py | ⬜ |
| `to_hex` | `(@own) -> String` | I | Py | ⬜ |
| `from_hex` | `(s: &Str) -> Option[Float]` | P | Py | ⬜ |
| `to_int` | `(@own) -> Int` | I | — | ⬜ |

`to_bits`/`from_bits`: dependen del ancho de `Int` (hoy `i32`). Decisión en S1:
devuelven `I64` (`std.int`) o se aplazan a S8.

### `littera` (S1) — doc ~37, +6

| método | firma | clase | origen | estado |
|---|---|---|---|---|
| `is_alphanumeric` | `(@own) -> Bool` | I | Rs | ⬜ |
| `is_control` | `(@own) -> Bool` | I | Rs | ⬜ |
| `to_ascii_uppercase` | `(@own) -> Char` | P | Rs | ⬜ |
| `to_ascii_lowercase` | `(@own) -> Char` | P | Rs | ⬜ |
| `successor` | `(@own) -> Option[Char]` | P | Rs | ⬜ |
| `predecessor` | `(@own) -> Option[Char]` | P | Rs | ⬜ |

### `verbum` (S2) — doc ~80, +34

Núcleo del lenguaje y el módulo más grande. Añadir a `Str`:

| método | firma | clase | origen | estado |
|---|---|---|---|---|
| `count` | `(@, needle: &Str) -> Int` | D | Py/Go | ⬜ |
| `casefold` | `(@) -> String` | I | Py | ⬜ |
| `expandtabs` | `(@, tabsize: Int) -> String` | P | Py | ⬜ |
| `swapcase` | `(@) -> String` | P | Py | ⬜ |
| `isidentifier` | `(@) -> Bool` | P | Py | ⬜ |
| `isprintable` | `(@) -> Bool` | I | Py | ⬜ |
| `isdecimal` | `(@) -> Bool` | P | Py | ⬜ |
| `translate` | `(@, table: &Map[Char, Str]) -> String` | P | Py | ⬜ |
| `split_once` | `(@, sep: &Str) -> Option[(&Str, &Str)]` | D | Rs/Go | ⬜ |
| `rsplit_once` | `(@, sep: &Str) -> Option[(&Str, &Str)]` | D | Rs | ⬜ |
| `split_inclusive` | `(@, sep: &Str) -> Vec[&Str]` | P | Rs | ⬜ |
| `split_at` | `(@, mid: Int) -> (&Str, &Str)` | I | Rs | ⬜ |
| `char_indices` | `(@) -> Vec[(Int, Char)]` | P | Rs | ⬜ |
| `bytes` | `(@) -> Vec[U8]` | I | Rs | ⬜ |
| `is_char_boundary` | `(@, index: Int) -> Bool` | I | Rs | ⬜ |
| `repeat` | `(@, n: Int) -> String` | D | Rs/Go | ⬜ |
| `escape_debug` | `(@) -> String` | P | Rs | ⬜ |
| `encode_utf16` | `(@) -> Vec[U16]` | I | Rs | ⬜ |
| `cut` | `(@, sep: &Str) -> Option[(&Str, &Str)]` | P | Go | ⬜ |
| `cut_prefix` | `(@, prefix: &Str) -> Option[&Str]` | P | Go | ⬜ |
| `cut_suffix` | `(@, suffix: &Str) -> Option[&Str]` | P | Go | ⬜ |
| `index_any` | `(@, set: &Str) -> Option[Int]` | P | Go | ⬜ |
| `contains_any` | `(@, set: &Str) -> Bool` | P | Go | ⬜ |
| `fields` | `(@) -> Vec[&Str]` | D | Go | ⬜ |
| `replace_all` | `(@, from: &Str, to: &Str) -> String` | D | Go | ⬜ |
| `to_title` | `(@) -> String` | P | Go | ⬜ |
| `equal_fold` | `(@, other: &Str) -> Bool` | P | Go | ⬜ |
| `if_empty` | `(@, fallback: &Str) -> &Str` | P | Kt | ⬜ |
| `if_blank` | `(@, fallback: &Str) -> &Str` | P | Kt | ⬜ |
| `substring_before` | `(@, delim: &Str) -> &Str` | P | Kt | ⬜ |
| `substring_after` | `(@, delim: &Str) -> &Str` | P | Kt | ⬜ |
| `common_prefix_with` | `(@, other: &Str) -> Str` | P | Kt | ⬜ |
| `common_suffix_with` | `(@, other: &Str) -> Str` | P | Kt | ⬜ |
| `chunked` | `(@, size: Int) -> Vec[&Str]` | P | Kt | ⬜ |
| `windowed` | `(@, size: Int, step: Int) -> Vec[&Str]` | P | Kt | ⬜ |
| `trim_indent` | `(@) -> String` | P | Kt | ⬜ |
| `trim_margin` | `(@, margin: &Str) -> String` | P | Kt | ⬜ |
| `parse_int` | `(@) -> Result[Int, ParseError]` | I | Rs | ⬜ |
| `parse_float` | `(@) -> Result[Float, ParseError]` | I | Rs | ⬜ |

En `String` (owned) añadir `push_str`, `insert_str`, `replace_range`, `drain`,
`as_str`, `capacity`, `reserve`, `shrink_to_fit`, `from_str`, `into_bytes`.

Pendiente de decisión S2: `split`/`trim`/`get` devuelven `&Str`; si el borrow
checker no lo soporta sin lifetimes escritas, se devuelve `String` y se anota el
coste. Afecta a ~40 firmas.

### `capsa` (S3) — doc ~80, +16

| método | firma | clase | origen | estado |
|---|---|---|---|---|
| `resize_with` | `(@mut, len: Int, f: [Unit] -> T)` | P | Rs | ⬜ |
| `retain_mut` | `(@mut, f: [&mut T] -> Bool)` | I | Rs | ⬜ |
| `extend_from_within` | `(@mut, range: Range[Int])` | I | Rs | ⬜ |
| `chunk_by` | `(@, f: [&T] -> K) -> Vec[&[T]]` | I | Rs | ⬜ |
| `chunks_exact` | `(@, n: Int) -> Vec[&[T]]` | P | Rs | ⬜ |
| `rchunks` | `(@, n: Int) -> Vec[&[T]]` | P | Rs | ⬜ |
| `dedup_by_key` | `(@mut, f: [&T] -> K)` | P | Rs | ⬜ |
| `binary_search_by` | `(@, f: [&T] -> Ordering) -> Result[Int, Int]` | P | Rs | ⬜ |
| `select_nth_unstable` | `(@mut, n: Int)` | I | Rs | ⬜ |
| `as_slice` | `(@) -> &[T]` | I | Rs | ⬜ |
| `as_mut_slice` | `(@mut) -> &mut [T]` | I | Rs | ⬜ |
| `first_mut` | `(@mut) -> Option[&mut T]` | P | Rs | ⬜ |
| `last_mut` | `(@mut) -> Option[&mut T]` | P | Rs | ⬜ |
| `swap` | `(@mut, a: Int, b: Int)` | I | Rs | ⬜ |
| `fill` | `(@mut, value: T)` | I | Rs | ⬜ |
| `repeat` | `(@, n: Int) -> Vec[T]` | P | Rs | ⬜ |
| `concat` | `(@) -> Vec[T]` (T = Vec) | P | Rs | ⬜ |

### `tabula` (S3) — doc ~30, +6

| método | firma | clase | origen | estado |
|---|---|---|---|---|
| `get_key_value` | `(@, k: &K) -> Option[(&K, &V)]` | D | Rs | ⬜ |
| `into_keys` | `(@own) -> Vec[K]` | P | Rs | ⬜ |
| `into_values` | `(@own) -> Vec[V]` | P | Rs | ⬜ |
| `drain` | `(@mut) -> Vec[(K, V)]` | I | Rs | ⬜ |
| `retain` | `(@mut, f: [&K, &V] -> Bool)` | I | Rs | ⬜ |
| `capacity`/`reserve`/`shrink_to_fit` | `(@) -> Int` / `(@mut, n: Int)` | I | Rs | ⬜ |

`Entry` ya está en el doc (`or_insert`, `or_insert_with`, `or_default`,
`and_modify`). Añadir `key()` y `value()`, y documentar el límite de §6/S3: sin
lifetimes escritas no puede devolver `&mut V`; `or_insert` devuelve `V` (copia) o
se usa `and_modify`.

### `fasciculus` (S3) — doc ~25, +6

`replace`, `get`, `take`, `retain`, `drain`, `iter`, `into_iter`, `capacity`,
`reserve`, `shrink_to_fit`, `extend`, `insert`, `remove`, `clear`, `is_empty`,
`is_disjoint`, `is_subset`, `is_superset`.

### `numerus` (S4) — doc ~60, +20

Añadir: `hypot`, `copysign`, `lerp`, `inverse_lerp`, `remap`, `smoothstep`,
`smootherstep`, `clamp01`, `sign`, `wrap`, `ping_pong`, `move_towards`,
`next_power_of_two`, `prev_power_of_two`, `is_power_of_two`, `div_ceil`,
`div_floor`, `mod_floor`, `saturate`, `mean`, `variance`, `stddev`, `median`,
`erf_inv`, `beta`, `nth_root`.

### `fluxus` (S4) — doc ~20, +8

`eprint`/`eprintln`, `read_to_string`, `write`, `write_line`, `flush`,
`BufReader::lines`, `BufWriter::with_capacity`, `stdin/stdout/stderr` como
`Reader`/`Writer`.

### `via` (S5) — doc ~100, +14

`read_dir`, `read_link`, `symlink_metadata`, `set_permissions`,
`Permissions::readonly`, `Path::{components, iter, ancestors, strip_prefix,
with_extension, file_stem, parent, is_absolute, starts_with, display}`,
`Metadata::{is_symlink, modified, accessed, created}`,
`WalkOptions::{max_depth, follow_links, same_file_system}`.

### `exsecutor` (S5) — doc ~30, +6

`env_remove`, `env_clear`, `try_wait`, `signal`, `Stdio::null`,
`Output::{status, stdout, stderr}`, `which`.

### `ambitus` (S5) — doc ~18, +2

`set_current_dir`, `args_os`/`vars_os` (si `OsStr` existe en S6).

### `tempus` (S5) — doc ~45, +10

`Duration::{checked_add, checked_sub, saturating_mul, mul, div, is_zero, MAX,
MIN, ZERO}`, `Instant::{checked_duration_since, saturating_duration_since}`,
`SystemTime::{checked_add, checked_sub, elapsed}`, `sleep`.

### `nexus` (S6) — doc ~20, +14

`CStr::{to_bytes, to_string_lossy}`, `CString::{as_c_str, into_raw, from_raw,
into_bytes}`, `CChar`, `Ptr::{null, is_null, cast}`, `OsStr`, `OsString`,
`OsStr::{to_str, to_string_lossy}`, `OsString::{into_string, as_os_str}`.

### `funis` (S7) — doc ~50, +30

Adaptadores: `filter_map`, `flat_map`, `flatten`, `zip`, `enumerate`, `chain`,
`take_while`, `skip_while`, `step_by`, `rev`, `peekable`, `scan`, `inspect`,
`cycle`, `fuse`, `by_ref`. Terminales: `count`, `last`, `nth`, `position`,
`find`, `find_map`, `any`, `all`, `max_by`, `min_by`, `max_by_key`, `min_by_key`,
`sum`, `product`, `reduce`, `for_each`, `partition`, `unzip`, `join`, `is_sorted`.
Constructores: `empty`, `once`, `repeat`, `repeat_n`, `successors`, `from_iter`,
`lines`, `chars`, `split`.

### `structura` (S7) — 5 tipos

`VecDeque` (~30), `BTreeMap` (~30), `BTreeSet` (~25), `BinaryHeap` (~15),
`LinkedList` (~30). Cada tipo con la misma cobertura que su par de `capsa`/
`tabula`/`fasciculus`, sin duplicar semántica.

### `libra` (S8) — doc ~25, +15

`Toml::{parse, parse_str, stringify, to_string}`, `TomlTable::{get_mut, remove,
contains_key, keys, values, iter, len, is_empty}`, `TomlValue::{is_*, as_*}`,
`TomlKind`, `TomlError::{line, column, message}`, `TomlString` (escapes),
`TomlDatetime::{OffsetDateTime, LocalDateTime, LocalDate, LocalTime}`.

### `iason` (S8) — doc ~25, +15

`Json::{parse, parse_str, stringify, pretty}`, `JsonObject::{get_mut, remove,
contains_key, keys, values, iter, len}`, `JsonValue::{is_*, as_*}`, `JsonNumber`
(`as_i64`, `as_f64`), `JsonError::{line, column, message}`.

### `digestum` (S8) — +6

`sha1`, `sha512_256`, `md5`, `hmac_sha512`, `hex_decode`, `base64_encode`,
`base64_decode`, `crc32`, y streaming (`Sha256::{update, finalize, digest}`).
`sha1` es requisito real: los objetos de git son SHA-1.

### `versio` (S8) — doc ~15, +10

`Version::{parse, cmp, major, minor, patch, pre, build, to_string}`,
`VersionReq::{parse, matches}`, `Comparator`, `ComparatorOp` (Exact, Greater,
GreaterEq, Less, LessEq, Tilde, Caret, Wildcard).

### `terminus` (S9) — doc ~30, +12

`strip_ansi`, `visible_width`, `cursor_up/down/left/right`, `save`/`restore`,
`alternate_screen`, `hyperlink`, `TermSize::{rows, cols}`.

### `globus` (S9) — +4

`GlobOptions::{case_insensitive, dot, literal_separator}`, `glob_iter`,
`matches_path`.

### `archivum` (S9) — doc ~15, +8

`ArchiveWriter::{add_file, add_dir, finish}`, `ArchiveEntry::{mode, is_dir}`,
`ExtractOptions::{overwrite, preserve_permissions}`, `ArchiveError::kind`.

### `rete` (S10, diferido) — doc ~40, +10

`TcpListener::{incoming, local_addr, set_nonblocking}`,
`TcpStream::{read, write, shutdown, peer_addr, set_nodelay, set_read_timeout}`,
`UdpSocket::{send_to, recv_from}`, `IpAddr::{parse, is_ipv4, is_ipv6}`,
`HttpClient::{get, post}`. **No entra en el camino crítico.**

---

## Anexo B — Protocolo de investigación de APIs

Para cada módulo, antes de escribir código:

1. **Barrido de fuentes** (una sesión por módulo, 30 min):
   - Rust: `https://doc.rust-lang.org/std/` y `core/` (índice por tipo).
   - Python 3.12: `https://docs.python.org/3/library/stdtypes.html` (str, list,
     dict, set) y `string`, `math`, `os`, `pathlib`, `datetime`.
   - Go: `https://pkg.go.dev/strings`, `os`, `path/filepath`, `sort`, `time`.
   - Kotlin: `https://kotlinlang.org/api/core/kotlin-stdlib/` (String, collections).
   - V: `https://modules.vlang.io/`.
2. **Tabla de tres columnas**: método extranjero → equivalente Pengu → ¿existe ya
   en `docs/STDLIB.md`? Lo que no exista y sea expresable entra como delta.
3. **Filtro de descarte** (razón obligatoria en `estado = 🚫`):
   - requiere `unsafe`/punteros en superficie;
   - requiere `dyn`/tipos asociados;
   - requiere lifetimes escritas por el usuario;
   - es una API de plataforma que el lenguaje prohíbe (`fork`, señales, hilos
     crudos);
   - duplica semántica de otro método (se documenta el alias, no se implementa).
4. **Registro**: cada método aceptado entra en el Anexo A con firma, clase y
   origen. Cada descarte entra en una tabla de descartes al final del módulo.
5. **Cierre**: la matriz de conformidad del módulo debe dar 100 % ✅/🚫.

Fuentes ya consultadas para este inventario:
[Rust `core::str`](https://static.rust-lang.org/doc/stable/core/str/index.html#structs),
[CPython `string-methods`](https://chromium.googlesource.com/external/github.com/python/cpython/+/6b38daa80dc0b63a089ac4557e25abe1f76b95af/Lib/pydoc_topics.py),
[Go `strings`](https://mintlify.wiki/golang/go/api/strings),
[Kotlin standard-api](https://github.com/goforj/str/blob/main/docs/standard-api.md).
