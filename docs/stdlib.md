## Standard Library
---

Every stdlib module must be imported with `invoke`. There are no builtins. Each module is one or two files:

- **`<module>.d.pengu`** — declaration file. Signatures without bodies. The implementation is either a C++ primitive (FFI/intrinsic) or a `.pengu` file of the same name.
- **`<module>.pengu`** — implementation file. Pure PenguScript.

A module that has both uses the `.d.pengu` for its FFI/intrinsic layer and the `.pengu` for its safe public API. Users `invoke "<module>"` and get both realms merged.

All FFI is **centralized** in `std/sys` (OS syscalls) and `std/ffi` (C++ library bindings). No other `.d.pengu` declares C functions. This makes the OS surface auditable in one place.

### Estado en 0.1.0

Ya implementado y cubierto por pruebas:

| Archivo | Contenido |
|---------|-----------|
| `std/math.d.pengu` | `abs`, `sqrt`, `floor`, `ceil`, `round`, `sin`, `cos`, `tan`, `pow`, `min`, `max`, `clamp`, `pi`, `e`. |
| `std/fs.d.pengu` | `read_to_string`, `write_string`, `exists`, `is_dir`, `remove`, `create_dir`. |
| `std/time.d.pengu` | `now_millis`, `now_seconds`, `sleep_millis`. |
| `std/random.d.pengu` | `int`, `float`, `bool`. |
| `std/os.d.pengu` | `args`, `get_env`, `exit`. |
| `std/assert.d.pengu` | `that`, `fail`. |
| `std/io.pengu` | `println`, `print`, `eprintln`, `eprint` (variádicas `...partes: any`) sobre `write_values` / `eprint_values` / `read_line`. |
| `std/format.pengu` | `format(...partes: any) -> string` sobre `format_values`. |
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
| `std/vector.pengu` | `vector<T>`: `is_empty`, `first`, `last`, `index_of`, `contains`, `join`, `mut reverse`, `mut sort`. |
| `std/array.pengu` | `array<T, N>`: `is_empty`, `first`, `last`, `index_of`, `contains`. |
| `std/map.pengu` | `map<K, V>`: `is_empty`, `contains_key`, `keys_list`, `values_list`. |
| `std/set.pengu` | `set<T>`: `is_empty`, `contains`, `to_vector`, `union`. |
| `std/optional.pengu` | `T?`: `is_empty`, `or_else`, `filter`, `to_vector`. |
| `std/pair.pengu` | `pair<A, B>`: `swap`, `to_tuple`. |
| `std/tuple.pengu` | `tuple<A, B>` y `tuple<A, B, C>`: `len`, `swap`, `to_pair`, `third`. |
| `std/int.pengu` | `int`: `abs`, `min`, `max`, `clamp`, `is_even`, `is_odd`, `sign`, `to_double`. |
| `std/double.pengu` | `double`: `abs`, `min`, `max`, `clamp`, `to_int`. |
| `std/ordering.pengu` | `Ordering`: `then`. |

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