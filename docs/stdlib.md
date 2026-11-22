## Standard Library
---

Every stdlib module must be imported with `invoke`. There are no builtins. Each module is one or two files:

- **`<module>.d.pengu`** — declaration file. Signatures without bodies. The implementation is a C++ primitive (FFI/intrinsic).
- **`<module>.pengu`** — implementation file. Pure PenguScript, con sus propias primitivas declaradas con `declare`.

Un módulo se resuelve a **un solo archivo**: `<module>.pengu` si existe, si no `<module>.d.pengu`. Si necesitas primitivas y API segura en el mismo módulo, declara las primitivas con `declare` dentro del `.pengu` (es lo que hacen `std/math`, `std/io` o `std/char`).

Las primitivas declaradas con `declare` están centralizadas: el generador C++ solo emite la llamada al helper de `src/codegen/runtime_source.ts` o a la función de la librería estándar de C++ mapeada en `BUILTIN_FUNCTIONS`.

### Estado en 0.1.0

Ya implementado y cubierto por pruebas:

| Archivo | Contenido |
|---------|-----------|
| `std/math.pengu` | Constantes `pi`, `e`, `tau`, `phi`, `sqrt2`, `ln2`, `ln10`; trigonometría completa, `exp*`, `ln`, `log2`, `log10`, `cbrt`, `hypot`, `fmod`, `trunc`, `nearbyint`, `fdim`, `fmax`, `fmin`, `copysign`, `fma`, `signbit`, `is_finite`, `is_infinite`, `is_nan`, `infinite`, `not_a_number`, `gcd`, `lcm`; utilidades `lerp`, `inverse_lerp`, `remap`, `clamp01`, `smoothstep`, `smootherstep`, `deg_to_rad`, `rad_to_deg`, `wrap`, `wrap_angle`, `lerp_angle`, `move_towards`, `damp`, `approx_eq`, `sign`, `min3`, `max3`, `average`, `ipow`, `is_power_of_two`, `next_power_of_two`, `align_up`. |
| `std/char.pengu` | `char`: `is_digit`, `is_alpha`, `is_alphanumeric`, `is_space`, `is_upper`, `is_lower`, `is_ascii`, `is_hex_digit`, `is_control`, `is_punctuation`, `code`, `digit_value`, `hex_value`, `to_upper`, `to_lower`. |
| `std/integers.pengu` | `int8_t`…`uint64_t`: límites `max_value`/`min_value`, `abs`, `sign`, `min`, `max`, `clamp`, `is_even`, `is_odd`, `is_positive`, `is_negative`, `is_zero`, `to_int`, `to_int64`, `to_uint64`, `to_double`, `to_size` (archivo generado por `scripts/gen_integers.ts`). |
| `std/fs.d.pengu` | `read_to_string`, `write_string`, `exists`, `is_dir`, `remove`, `create_dir`. |
| `std/time.d.pengu` | `now_millis`, `now_seconds`, `sleep_millis`. |
| `std/random.d.pengu` | `int`, `float`, `bool`. |
| `std/os.d.pengu` | `args`, `get_env`, `exit`. |
| `std/assert.d.pengu` | `that`, `fail`. |
| `std/io.pengu` | `println`, `print`, `eprintln`, `eprint` (variádicas `...partes: any`) sobre `write_values` / `eprint_values` / `read_line`. |
| `std/format.pengu` | `format(...partes: any) -> string` sobre `format_values`; `fixed(valor, decimales)`, `scientific(valor, decimales)` y `radix(valor, base)`. |
| `std/log.pengu` | `debug`, `info`, `warn`, `error` sobre `log_values`. |

El bloque `declare` marca las funciones que implementa el runtime del compilador; el generador C++ no emite cuerpo para ellas, solo la llamada al helper correspondiente.

`std/io`, `std/format` y `std/log` ya son módulos PenguScript: declaran sus primitivas con `declare` (que reciben `vector<any>`) y ofrecen la API variádica en el propio lenguaje. Cada argumento `any` se empaqueta como `::pengu::Value`, que guarda su renderizador de `Display`.

### Enchanting de tipos incorporados

Estos módulos no exportan funciones libres: añaden métodos a los tipos
incorporados mediante bloques `enchanting`. Hay que importarlos de forma
explícita para que los métodos existan en el archivo:

| Archivo | Métodos que añade |
|---------|-------------------|
| `std/string.pengu` | `string`: `compare`, `is_empty`, `starts_with`, `ends_with`, `contains`, `find`, `trim`, `to_upper`, `to_lower`, `split`, `repeat`. |
| `std/vector.pengu` | `vector<T>`: `is_empty`, `first`, `last`, `index_of`, `contains`, `join`, `get_or`, `first_or`, `last_or`, `mut remove`, `mut remove_all`, `mut extend`, `mut retain`, `mut fill`, `mut swap`, `mut rotate_left`, `mut rotate_right`, `any`, `all`, `none`, `count_if`, `find_if`, `position_if`, `fold`, `map`, `filter`, `mut transform`, `min`, `max`, `is_sorted`, `mut sort_by`, `sorted`, `sorted_by`, `mut dedup`, `binary_search`, `take`, `skip`, `slice`, `chunks`, `windows`, `enumerate`, `sum`, `product`. |
| `std/array.pengu` | `array<T, N>`: `is_empty`, `first`, `last`, `index_of`, `contains`, `to_vector`, `reversed`, `slice`, `join`, `min`, `max`, `find_if`, `any`, `all`, `none`, `sum`, `product`. |
| `std/map.pengu` | `map<K, V>`: `is_empty`, `contains_key`, `keys_list`, `values_list`, `mut get_or_insert`, `mut update`, `entries`, `first_key`, `last_key`, `mut merge`, `mut retain`; builtins: `get`, `get_or`, `insert`, `insert_or_assign`, `remove`, `contains`, `keys`, `values`, `clear`. |
| `std/set.pengu` | `set<T>`: `is_empty`, `contains`, `to_vector`, `union`, `intersection`, `difference`, `symmetric_difference`, `is_subset`, `is_superset`, `is_disjoint`, `mut insert_all`, `mut remove_all`, `mut extend`, `mut retain`, `first`, `last`, `map`, `filter`, `to_sorted_vector`. |
| `std/optional.pengu` | `T?`: `is_empty`, `or_else`, `filter`, `to_vector`, `map`, `and_then`, `or_else_get`, `zip`, `any`. |
| `std/pair.pengu` | `pair<A, B>`: `swap`, `to_tuple`. |
| `std/tuple.pengu` | `tuple<A, B>` y `tuple<A, B, C>`: `len`, `swap`, `to_pair`, `first`, `second`, `third`. |
| `std/int.pengu` | `int`: `abs`, `min`, `max`, `clamp`, `is_even`, `is_odd`, `is_positive`, `is_negative`, `is_zero`, `sign`, `between`, `div_floor`, `div_ceil`, `mod_floor`, `mod_euclid`, `pow`, `wrap`, `next_multiple_of`, `abs_diff`, `digits`, `is_power_of_two`, `to_double`, `to_float`, `to_int64`, `to_size`, `to_radix`. |
| `std/double.pengu` | `double`: `abs`, `min`, `max`, `clamp`, `between`, `sqrt`, `cbrt`, `pow`, `exp`, `ln`, `log2`, `log10`, `floor`, `ceil`, `round`, `trunc`, `fract`, `round_to`, `hypot`, `is_finite`, `is_infinite`, `is_nan`, `is_sign_negative`, `signum`, `lerp`, `approx_eq`, `to_radians`, `to_degrees`, `to_fixed`, `to_scientific`, `to_int`, `to_float`, `to_long_double`. |
| `std/float.pengu` | `float`: la misma superficie que `double` (con `to_fixed`/`to_scientific` y conversiones propias). |
| `std/long_double.pengu` | `long double`: la misma superficie que `double`. |
| `std/ordering.pengu` | `Ordering`: `then`, `to_int`, `then_with`. |
| `std/deque.pengu` | `deque<T>`: doble extremo: `is_empty`, `first`, `last`, `get_or`, `index_of`, `contains`, `to_vector`, `join`; builtins: `push`, `push_front`, `pop`, `pop_front`, `insert_at`, `remove_at`, `clear`. |
| `std/memory.pengu` | `unique<T>`/`shared<T>`: `get`, `mut set`; `weak<T>`: `is_alive`. |

### Módulos previstos (fases F3–F9)

El plan `scratch/plan_stdlib.md` define el resto de la biblioteca. `std/sys` y `std/ffi` de las secciones siguientes son el diseño objetivo: todavía **no existen** como archivos y se implementarán en fases posteriores (texto, sistema, algoritmos, juegos, datos/CLI).

### Layer 0 — FFI

| Module | Files | Contents |
|--------|-------|----------|
| `std/sys` | `.d.pengu` | OS syscalls: `read`, `write`, `open`, `close`, `stat`, `lseek`, `mmap`, `munmap`, `exit`, `getpid`, `kill`, `signal`, `fork`, `execve`, `getenv`, `setenv`, `socket`, `bind`, `listen`, `accept`, `connect`. All `unsafe`. |
| `std/ffi` | `.d.pengu` | C++ library bindings, organized by realm: `cmath` (`sqrt`, `sin`, `cos`, `pow`, `log`, `exp`…), `cstring` (`memcpy`, `memset`, `strlen`, `strcmp`), `cstdlib` (`malloc`, `free`, `qsort`), `ctime` (`clock_gettime`, `time`). All `unsafe`. |

### Layer 1 — Intrinsics on built-in types

These modules declare the methods the compiler already knows how to emit for primitive and container types. They are **documented intrinsics**: the compiler knows the C++ translation, and the `.d.pengu` is the visible signature.

| Module | Files | Contents |
|--------|-------|----------|
| `std/core` | `.d.pengu` | Methods on `int`, `intN`, `uintN`, `float`, `double`, `bool`, `char`: `try_from`, `from`, `abs`, `min`, `max`, `is_nan`, `is_infinite`, `to_string`, `clamp`, `sign`. |
| `std/string` | `.d.pengu` + `.pengu` | `.d`: `find`, `rfind`, `split`, `replace`, `substr`, `trim`, `starts_with`, `ends_with`, `chars`, `bytes`, `to_lowercase`, `to_uppercase`. `.p`: `join`, `format`, `escape`, `align`. |
| `std/string_view` | `.d.pengu` | Methods on `string_view`: `substr`, `starts_with`, `ends_with`, `find`, `compare`, `to_string`. |
| `std/vector` | `.d.pengu` | `push`, `pop`, `pop_opt`, `insert`, `remove_at`, `clear`, `sort`, `reverse`, `contains`, `index_of`, `resize`, `reserve`, `capacity`, `shrink_to_fit`. |
| `std/array` | `.d.pengu` | `contains`, `index_of`, `reverse`, `sort`, `iter`. |
| `std/map` | `.d.pengu` | `get`, `get_or`, `get_all`, `insert`, `insert_all`, `remove`, `remove_all`, `key_count`, `keys`, `values`. |
| `std/set` | `.d.pengu` | `contains`, `insert`, `remove`, `union`, `intersection`, `difference`, `is_subset`, `is_superset`. |
| `std/optional` | `.d.pengu` + `.pengu` | `.d`: `has_value`, `value`, `value_or`, `reset`. `.p`: `map`, `and_then`, `or_else`, `ok_or`. |
| `std/memory` | `.d.pengu` | Methods on `unique<T>`, `shared<T>`, `weak<T>`: `get`, `release`, `reset`, `use_count`, `lock`, `expired`. |
| `std/ordering` | `.d.pengu` | Methods on `Ordering`: `is_lt`, `is_eq`, `is_gt`, `reverse`, `then`, `then_with`. |

### Layer 2 — Basic services (v0.1.0)

All `.pengu`, built on `std/sys` and `std/ffi`.

| Module | Files | Contents |
|--------|-------|----------|
| `std/io` | `.pengu` | `print`, `println`, `eprint`, `eprintln`, `read_line`, `read`, `write`, `flush`. `File` rune (`open`, `read`, `write`, `seek`, `close`). `BufReader`, `BufWriter`. |
| `std/fs` | `.pengu` | `read_file`, `write_file`, `append_file`, `remove`, `rename`, `copy`, `exists`, `is_file`, `is_dir`, `mkdir`, `rmdir`, `read_dir`, `list_dir`, `symlink`, `read_link`, `canonicalize`, `metadata`. |
| `std/path` | `.pengu` | `Path` rune: `join`, `parent`, `file_name`, `stem`, `extension`, `is_absolute`, `components`, `normalize`, `to_string`. |
| `std/math` | `.pengu` | `<cmath>` wrappers: `sqrt`, `pow`, `cbrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `log`, `log2`, `log10`, `exp`, `floor`, `ceil`, `round`, `trunc`, `abs`, `min`, `max`, `clamp`. Constants: `pi`, `e`, `inf`, `nan`. Integers: `gcd`, `lcm`, `factorial`. |
| `std/time` | `.pengu` | `Instant`, `Duration`, `SystemTime`. `now`, `elapsed`, `sleep`, `from_secs`, `from_millis`, `from_nanos`, `as_secs`, `as_millis`. |
| `std/os` | `.pengu` | `args`, `getenv`, `setenv`, `home_dir`, `current_dir`, `temp_dir`, `exit`, `pid`, `sleep`. `Platform` and `Arch` omens. |
| `std/random` | `.pengu` | `Rng` rune: `new`, `from_seed`, `next_u32`, `next_u64`, `next_f32`, `next_f64`, `gen_range`, `shuffle`, `choose`. |
| `std/error` | `.pengu` | `Error` rune (`message`, `code`, `source`). `Result<T, E>` omen (`Ok`, `Err`). `?` operator integration. |
| `std/assert` | `.pengu` | `assert`, `assert_eq`, `assert_ne`, `assert_throws`, `debug_assert`. |
| `std/iter` | `.pengu` | Free functions over sequences: `map`, `filter`, `enumerate`, `zip`, `chain`, `take`, `skip`, `chunks`, `windows`, `fold`, `reduce`, `any`, `all`, `count`, `sum`, `product`, `collect`. |
| `std/format` | `.pengu` | `pad_left`, `pad_right`, `pad_center`, `escape`, `align`, `number_with_separator`. |
| `std/mem` | `.pengu` | `size_of`, `align_of`, `swap`, `zeroed`, `uninitialized` (unsafe). |
| `std/log` | `.pengu` | `Level` omen, `Logger`, `log`, `info`, `warn`, `error`, `debug`. |

### Layer 3 — Advanced modules (v0.1.0)

All `.pengu`.

| Module | Files | Contents |
|--------|-------|----------|
| `std/sort` | `.pengu` | `merge_sort`, `quick_sort`, `radix_sort`, `binary_search`, `lower_bound`, `upper_bound`, `is_sorted`. |
| `std/encoding` | `.pengu` | `base64_encode`, `base64_decode`, `hex_encode`, `hex_decode`, `utf8_validate`, `url_encode`, `url_decode`. |
| `std/json` | `.pengu` | `Json` omen (`Null`, `Bool`, `Number`, `String`, `Array`, `Object`). `parse`, `stringify`, `to_json`, `from_json`. |
| `std/hash` | `.pengu` | `fnv1a_32`, `fnv1a_64`, `xxhash64`, `murmur3_32`, `murmur3_128`, `cityhash64`. |
| `std/console` | `.pengu` | ANSI colors (`Color` omen), `bold`, `dim`, `italic`, `underline`, `cursor_up`, `cursor_down`, `clear_screen`, `terminal_size`. |
| `std/debug` | `.pengu` | `stacktrace`, `backtrace`, `inspect` (dump any rune to string), `memory_stats`. |
| `std/test` | `.pengu` | `TestSuite`, `run_tests`, `expect`, `expect_eq`, `expect_err`. |

### Layer 4 — Concurrency and I/O (v0.1.0, optional)

All `.pengu`. Not required for the language to be usable, but part of a "complete" stdlib.

| Module | Files | Contents |
|--------|-------|----------|
| `std/atomic` | `.pengu` | `AtomicBool`, `AtomicInt`, `AtomicSize`. `load`, `store`, `swap`, `compare_exchange`, `fetch_add`, `fetch_sub`, `fetch_and`, `fetch_or`. |
| `std/sync` | `.pengu` | `Mutex<T>`, `RwLock<T>`, `Condvar`, `Once`, `Barrier`, `Semaphore`. |
| `std/thread` | `.pengu` | `Thread`, `spawn`, `join`, `sleep`, `current`, `thread_id`, `yield_now`, `available_parallelism`. |
| `std/channel` | `.pengu` | `Channel<T>`, `Sender<T>`, `Receiver<T>`. `send`, `recv`, `try_recv`, `close`, `select` (function taking a list of channels). |
| `std/net` | `.pengu` | `TcpListener`, `TcpStream`, `UdpSocket`, `Address`, `IpAddr` omen, `Port`. Uses `sys::socket`, `sys::bind`, `sys::listen`, `sys::accept`, `sys::connect`. |
| `std/regex` | `.pengu` | `Regex`, `Match`. `find`, `find_all`, `replace`, `split`, `captures`. Thompson NFA implementation in PenguScript. |
| `std/cli` | `.pengu` | `Args`, `Flag`, `Option`, `Subcommand`, `parse`. |
| `std/crypto` | `.pengu` | `sha256`, `sha512`, `md5`, `blake3`. |

### Future modules (post v0.1.0)

| Module | Contents |
|--------|----------|
| `std/bigint` | Arbitrary-precision integers |
| `std/decimal` | Arbitrary-precision decimals |
| `std/complex` | Complex numbers (currently available via `std/ffi::cmath`) |
| `std/matrix` | Linear algebra |
| `std/compress` | gzip, zlib, zstd |
| `std/http` | HTTP client/server |
| `std/sql` | Database abstraction |
| `std/uuid` | UUID generation and parsing |
| `std/toml`, `std/yaml`, `std/csv`, `std/xml` | Format parsers |
| `std/gui` | GUI bindings (out of scope) |