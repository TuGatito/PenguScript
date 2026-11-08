# The PenguScript Standard Library

All 70 modules of `std/` in `psc` 0.51.0: what each one is for, when to reach for
it, when to reach for something else, and where its generated API lives.

It is the *catalogue* document of the documentation set:

| Document | Answers |
| --- | --- |
| [LANGUAGE.md](LANGUAGE.md) | How do I write this construct, and what does it become in C? |
| [PENGUNIC.md](PENGUNIC.md) | How do I write PenguScript that is safe, idiomatic and fast? |
| **STDLIB.md** (this file) | Which standard module do I use, and where is its API? |

Spanish: [STDLIB.es.md](STDLIB.es.md).

Every module links to a page in [`docs/api/`](api/), generated from the module's
own `##` comments by `psc doc --include-std`.

<!-- toc -->
- [0. How to use this catalogue](#0-how-to-use-this-catalogue)
- [1. The shape of the standard library](#1-the-shape-of-the-standard-library)
- [2. Choosing a module by task](#2-choosing-a-module-by-task)
- [3. Core and memory](#3-core-and-memory)
  - [`std.spark` — process I/O, conversions and control](#stdspark-process-io-conversions-and-control)
  - [`std.memoria` — raw heap blocks](#stdmemoria-raw-heap-blocks)
  - [`std.consortium` — shared ownership by reference count](#stdconsortium-shared-ownership-by-reference-count)
  - [`std.oracle` — `maybe` and `result`](#stdoracle-maybe-and-result)
  - [`std.builder` — `StringBuilder`](#stdbuilder-stringbuilder)
  - [`std.arena` — bump allocator](#stdarena-bump-allocator)
  - [`std.functor` — functions with context](#stdfunctor-functions-with-context)
  - [`std.sourcemap` — byte offsets ↔ line/column](#stdsourcemap-byte-offsets-linecolumn)
  - [`std.bitset` — fixed-length dense bit set](#stdbitset-fixed-length-dense-bit-set)
  - [`std.diagnostic` — spans, labels and renderers](#stddiagnostic-spans-labels-and-renderers)
- [4. Text and numbers](#4-text-and-numbers)
  - [`std.scrolls` — strings, byte-oriented](#stdscrolls-strings-byte-oriented)
  - [`std.lingua` — UTF-8 over codepoints](#stdlingua-utf-8-over-codepoints)
  - [`std.littera` — methods on `char`](#stdlittera-methods-on-char)
  - [`std.logica` — methods on `bool`](#stdlogica-methods-on-bool)
  - [`std.integrum` — methods on integers](#stdintegrum-methods-on-integers)
  - [`std.fractio` — methods on floats](#stdfractio-methods-on-floats)
  - [`std.numerus` — methods on every number](#stdnumerus-methods-on-every-number)
  - [`std.arithmancy` — vectors, matrices, quaternions](#stdarithmancy-vectors-matrices-quaternions)
  - [`std.lot` — pseudo-random numbers](#stdlot-pseudo-random-numbers)
- [5. Collections](#5-collections)
  - [`std.loom` — list algorithms, safe family](#stdloom-list-algorithms-safe-family)
  - [`std.tally` — list algorithms, concrete family](#stdtally-list-algorithms-concrete-family)
  - [`std.atlas` — maps](#stdatlas-maps)
  - [`std.coven` — sets](#stdcoven-sets)
  - [`std.ordinal` — CC-backed containers](#stdordinal-cc-backed-containers)
- [6. Formats and encodings](#6-formats-and-encodings)
  - [`std.json` — strict JSON (RFC 8259)](#stdjson-strict-json-rfc-8259)
  - [`std.cipher` — encodings and checksums](#stdcipher-encodings-and-checksums)
  - [`std.carmen` — fixed-layout binary records](#stdcarmen-fixed-layout-binary-records)
  - [`std.toml` — TOML 1.0](#stdtoml-toml-10)
  - [`std.yaml` — the legacy manifest subset](#stdyaml-the-legacy-manifest-subset)
  - [`std.ledger` — CSV and TSV](#stdledger-csv-and-tsv)
  - [`std.compressus` — gzip, zlib, deflate](#stdcompressus-gzip-zlib-deflate)
  - [`std.digest` — SHA-256 and friends](#stddigest-sha-256-and-friends)
  - [`std.regulus` — small regular expressions](#stdregulus-small-regular-expressions)
- [7. System, time and diagnostics](#7-system-time-and-diagnostics)
  - [`std.archivum` — the file system](#stdarchivum-the-file-system)
  - [`std.compass` — paths](#stdcompass-paths)
  - [`std.rites` — the operating system](#stdrites-the-operating-system)
  - [`std.invoke` — typed command-line parsing](#stdinvoke-typed-command-line-parsing)
  - [`std.io` — byte-exact standard I/O](#stdio-byte-exact-standard-io)
  - [`std.net` — TCP sockets](#stdnet-tcp-sockets)
  - [`std.chronicle` — clocks and calendars](#stdchronicle-clocks-and-calendars)
  - [`std.chrono` — instants and durations (vaqt)](#stdchrono-instants-and-durations-vaqt)
  - [`std.whisper` — leveled logging](#stdwhisper-leveled-logging)
- [8. Testing](#8-testing)
  - [`std.ward` — assertions for tests and guards](#stdward-assertions-for-tests-and-guards)
  - [`std.trial` — suites and reporting](#stdtrial-suites-and-reporting)
- [9. Concurrency](#9-concurrency)
  - [`std.filum` — threads and synchronization](#stdfilum-threads-and-synchronization)
  - [`std.coro` — stackful coroutines](#stdcoro-stackful-coroutines)
  - [`std.reactor` — explicit event loop](#stdreactor-explicit-event-loop)
- [10. Network services](#10-network-services)
  - [`std.petitio` — HTTP client](#stdpetitio-http-client)
  - [`std.jsonrpc` — JSON-RPC 2.0](#stdjsonrpc-json-rpc-20)
- [11. Interop and native code](#11-interop-and-native-code)
  - [`std.ffi` — C buffers and strings](#stdffi-c-buffers-and-strings)
  - [`std.ffi_call` — libffi dynamic calls (optional)](#stdffi_call-libffi-dynamic-calls-optional)
  - [`std.dynlib` — dynamic library loading](#stddynlib-dynamic-library-loading)
  - [`std.secrets` — libsodium primitives (optional)](#stdsecrets-libsodium-primitives-optional)
- [12. WebAssembly](#12-webassembly)
  - [`std.web` — the browser bridge](#stdweb-the-browser-bridge)
  - [`std.web.js` — JavaScript interop](#stdwebjs-javascript-interop)
  - [`std.web.dom` — elements and listeners](#stdwebdom-elements-and-listeners)
  - [`std.web.event` — typed event accessors](#stdwebevent-typed-event-accessors)
  - [`std.web.canvas` — Canvas 2D](#stdwebcanvas-canvas-2d)
  - [`std.web.browser` — window APIs](#stdwebbrowser-window-apis)
  - [`std.web.location` — `window.location`](#stdweblocation-windowlocation)
  - [`std.web.history` — `window.history`](#stdwebhistory-windowhistory)
  - [`std.web.router` — hash routing](#stdwebrouter-hash-routing)
  - [`std.web.http` — `fetch`](#stdwebhttp-fetch)
  - [`std.web.websocket` — typed WebSocket client](#stdwebwebsocket-typed-websocket-client)
  - [`std.web.storage` — localStorage and sessionStorage](#stdwebstorage-localstorage-and-sessionstorage)
  - [`std.web.file` — picking, reading, downloading](#stdwebfile-picking-reading-downloading)
  - [`std.web.clipboard` — system clipboard](#stdwebclipboard-system-clipboard)
  - [`std.web.crypto` — browser cryptography](#stdwebcrypto-browser-cryptography)
  - [`std.web.url` — URL parsing and encoding (also native)](#stdweburl-url-parsing-and-encoding-also-native)
  - [`std.web.security` — defensive string helpers (also native)](#stdwebsecurity-defensive-string-helpers-also-native)
- [13. Optional and native dependencies](#13-optional-and-native-dependencies)
  - [Internal binding files](#internal-binding-files)
- [14. The complete index](#14-the-complete-index)
- [Appendix A — Import cheat sheet](#appendix-a-import-cheat-sheet)
- [Appendix B — Ownership when calling the standard library](#appendix-b-ownership-when-calling-the-standard-library)
  - [Copy-on-write containers](#copy-on-write-containers)
- [Appendix C — Naming conventions in the standard library](#appendix-c-naming-conventions-in-the-standard-library)
<!-- /toc -->

Every module that ships with `psc` 0.51.0: what it is for, when to reach for
it, and where its generated API lives.

## 0. How to use this catalogue

The standard library is documented twice, on purpose:

| Layer | Answers | Where |
| --- | --- | --- |
| **This catalogue** | Which module do I use, and why? When should I *not* use it? | `docs/STDLIB.md` |
| **Generated API** | What is the exact signature of `scrolls.substring`? | [`docs/api/std_scrolls.md`](api/std_scrolls.md) |

The generated pages are produced by `psc doc --include-std` from the `##`
comments in `std/*.pengu`; they are regenerated by `tools/docs/gen_api.sh` and
checked in CI. This catalogue is hand-written and links to them.

Every entry has the same shape:

```
### `std.name` — one line
**Use it when** …
**Avoid it when** …
**Highlights** the five function names you will type most
**API** [link to the generated page] · [source]
```

**Version.** This catalogue describes `psc` 0.51.0 and the `std/` tree in the
same commit. A module version constant (`TRIAL_VERSION`, `CARMEN_VERSION`, …)
is the module's own API version, not the compiler's.

**Importing.** Standard modules are imported explicitly:

```pengu
import std.json
import std.scrolls
```

`std.*` modules are always resolvable, are never vendored into `lib/`, and are
pruned by the dead-code eliminator when unused: importing a module you do not
call costs nothing in the binary. Import what you read.

**Reading an entry.** "Use it when" is the positive case; "Avoid it when" names
the module you probably want instead. When a module has an optional native
dependency (`libcurl`, `libffi`, `libsodium`, `dl`), the entry says so.

## 1. The shape of the standard library

The library is layered: everything rests on a small core, and specialised
modules never pull the whole world in.

```
spark            process I/O, parsing, panic, exit
├── memoria      raw heap blocks
├── oracle       maybe / result
├── scrolls      strings (bytes)
│   └── lingua   UTF-8 over codepoints
├── builder      StringBuilder
├── arena        bump allocator
├── ordinal      CC-backed containers
├── loom/tally   list algorithms
├── atlas/coven  maps and sets
└── …
```

| Layer | Modules | You will use it |
| --- | --- | --- |
| Core | `spark`, `memoria`, `oracle`, `builder` | always |
| Text | `scrolls`, `lingua`, `littera`, `logica` | constantly |
| Numbers | `integrum`, `fractio`, `numerus`, `arithmancy`, `lot` | often |
| Collections | `loom`, `tally`, `atlas`, `coven`, `ordinal`, `bitset` | often |
| Memory helpers | `arena`, `functor` | sometimes |
| Formats | `json`, `cipher`, `carmen`, `toml`, `yaml`, `ledger`, `compressus`, `digest`, `regulus` | often |
| System | `archivum`, `compass`, `rites`, `invoke`, `io`, `net`, `chronicle`, `chrono`, `whisper`, `diagnostic`, `sourcemap`, `dynlib` | often |
| Concurrency | `filum` | sometimes |
| Testing | `ward`, `trial` | in every project |
| Interop | `ffi`, `ffi_call`, `dynlib`, `secrets` | at the edges |
| Services | `petitio`, `net`, `jsonrpc` | for tools and servers |
| WebAssembly | `web` + `std/web/*` (16 modules) | browser builds only |

**Rule of thumb.** If a module is in the "Core" or "Text" layer, import it
freely. If it is in "Interop" or "Services", read its "Avoid it when" first: it
may bring a native dependency.

## 2. Choosing a module by task

| I need to… | Use | Not |
| --- | --- | --- |
| print, parse an int, exit | `std.spark` | — |
| build a string in a loop | `std.builder` | `+` in a loop |
| split, trim, replace, compare strings | `std.scrolls` | hand-written loops |
| count characters, not bytes | `std.lingua` | `s.len` on UTF-8 |
| classify a `char` | `std.littera` | ranges written by hand |
| do math on all numeric types | `std.numerus` | one function per type |
| do integer-only math | `std.integrum` | `numerus` when you need `%` |
| do float-only math | `std.fractio` | `numerus` |
| vectors, matrices, quaternions | `std.arithmancy` | hand-rolled structs |
| random numbers | `std.lot` | `time()` seeded ad hoc |
| iterate, chunk, zip, fold | `std.loom` | index loops |
| reduce, search, sort a list | `std.tally` | `loom` for int-only paths |
| map / set | `std.atlas`, `std.coven` | parallel lists |
| ordered map, linked list | `std.ordinal` | sorting a map each time |
| membership over a bounded range | `std.bitset` | `map of int to bool` |
| allocate many short-lived objects | `std.arena` | one `alloc` each |
| pass a callback with context | `std.functor` | a global |
| JSON | `std.json` | `std.cipher.parse_json` (legacy, flat) |
| TOML / YAML / CSV | `std.toml`, `std.yaml`, `std.ledger` | regex |
| binary records | `std.carmen` | manual byte offsets |
| base64, hex, CRC-32 | `std.cipher` | hand-written tables |
| gzip / zlib / deflate | `std.compressus` | shelling out to `gzip` |
| SHA-256 | `std.digest` | CRC-32 |
| regular expressions | `std.regulus` | string splitting |
| files, directories, walking | `std.archivum` | `system("ls")` |
| paths | `std.compass` | string concatenation |
| environment, argv, exec | `std.rites` | `getenv` through FFI |
| typed CLI flags | `std.invoke` | parsing `argv` by hand |
| read exactly N bytes | `std.io` | `std.spark.input` |
| TCP sockets and async I/O | `std.net` + `std.reactor` | FFI to `socket()` |
| HTTP client | `std.petitio` | `net` + hand-written HTTP |
| JSON-RPC 2.0 | `std.jsonrpc` | hand-rolled framing |
| time and dates | `std.chronicle` | `time()` through FFI |
| nanoseconds, ISO 8601 | `std.chrono` | `chronicle` floats |
| logging | `std.whisper` | `print` with prefixes |
| source positions | `std.sourcemap` | counting newlines |
| compiler-style errors | `std.diagnostic` | ad-hoc strings |
| tests | `std.ward` + `std.trial` | `assert` from `spark` |
| mutexes, atomics, channels | `std.filum` | — |
| cooperative coroutines | `std.coro` + `std.reactor` | threads + state |
| call a C library | `std.ffi` | `antiquus` everywhere |
| call a function by name at runtime | `std.ffi_call` | `dynlib` alone |
| load a `.so`/`.dll` | `std.dynlib` | — |
| random bytes, wipe memory | `std.secrets` | `std.lot` |
| DOM, canvas, fetch in the browser | `std.web.*` | — |

## 3. Core and memory

### `std.spark` — process I/O, conversions and control

**Use it when** you need the console (`print`, `println`, `eprint`), a scalar to
text conversion (`str_int`, `str_float`), a parse (`parse_int`, `parse_float`),
an integer range (`range`), a panicking assertion at a true invariant, or
`exit`.

**Avoid it when** the output is a data stream: `print` is line-oriented and
formats values; use `std.io` for bytes and `std.whisper` for logs.

**Highlights** `print`, `println`, `eprintln`, `flush`, `parse_int`, `panic`,
`exit`.

**API** [`api/std_spark.md`](api/std_spark.md) · [source](../std/spark.pengu)

### `std.memoria` — raw heap blocks

**Use it when** you are implementing a container, a buffer protocol or a
binding, and need `alloc`, `alloc_array`, `resize_array`, `copy`, `fill`,
`zero`, `swap` or `compare` over untyped memory.

**Avoid it when** a value type already covers the case: `list`, `map`,
`StringBuilder` and `arena` own their memory and free it with one `banish`.

**Highlights** `alloc of T`, `alloc_array of T with n`, `copy`, `zero`,
`resize_array`.

**API** [`api/std_memoria.md`](api/std_memoria.md) · [source](../std/memoria.pengu)

### `std.consortium` — shared ownership by reference count

**Use it when** several parts of a program must observe the same value and you
cannot tell which one dies last: `Rc of T` (single thread, implicit cheap copy),
`Arc of T` (crosses threads, `.clone()` is the only copy), `WeakRc`/`WeakArc`
to break cycles. `get` hands out `ref to frozen T`; mutation goes through
`get_mut` (exclusivity) or `make_mut` (copy-on-write).

**Avoid it when** the value has one owner: `derive Drop` (layer 1) is faster and
the cost stays visible in the type. Do not use `Rc` inside a hot loop as an
allocator, and do not reach for `Arc` when the threads can exchange a plain
value.

**Highlights** `Rc.new`, `Rc.get`, `Rc.get_mut`, `Rc.make_mut`, `downgrade`,
`WeakRc.upgrade`, `Arc.clone`, `strong_count`, `weak_count`.

**API** [`api/std_consortium.md`](api/std_consortium.md) · [source](../std/consortium.pengu)

### `std.oracle` — `maybe` and `result`

**Use it when** a computation can be absent (`maybe T`) or fail with a reason
(`result of T to E`), and you want the full toolbox: builders (`some_of`,
`none_of`, `ok_of`, `err_of`), inspection (`is_present`, `is_ok`, `is_err`),
transformation (`map`, `and_then`, `map_err`), recovery (`unwrap_or`,
`unwrap_or_else`) and conversion.

**Avoid it when** the absence is impossible by construction: return `T`.

**Highlights** `some_of`, `none_of`, `ok_of`, `err_of`, `unwrap_or`.

**API** [`api/std_oracle.md`](api/std_oracle.md) · [source](../std/oracle.pengu)

### `std.builder` — `StringBuilder`

**Use it when** a string is assembled from more than two pieces, especially in a
loop: `append`, `append_int`, `append_char`, `append_slice`, `finish`.

**Avoid it when** you are joining a list you already have: `scrolls.join` is
shorter and equally linear.

**Highlights** `new`, `append`, `append_int`, `append_char`, `finish`.

**API** [`api/std_builder.md`](api/std_builder.md) · [source](../std/builder.pengu)

### `std.arena` — bump allocator

**Use it when** you build a large object graph with one lifetime (a request, a
frame, a parse tree) and want to free it all at once: `Arena.new`,
`arena_alloc of T`, `reset`, `free`.

**Avoid it when** objects have independent lifetimes, or one object outlives the
arena: the arena frees everything together.

**Highlights** `Arena.new`, `arena_alloc of T`, `arena_alloc_one`, `reset`.

**API** [`api/std_arena.md`](api/std_arena.md) · [source](../std/arena.pengu)

### `std.functor` — functions with context

**Use it when** a callback must remember state and a `concept` would be
overkill: `Fn0`–`Fn3` carry a function pointer plus an explicit context, with
`make_fn0`–`make_fn3` and `call`.

**Avoid it when** the callback is stateless: pass the function pointer.

**Highlights** `Fn1`, `make_fn1`, `call`.

**API** [`api/std_functor.md`](api/std_functor.md) · [source](../std/functor.pengu)

### `std.sourcemap` — byte offsets ↔ line/column

**Use it when** you report positions in source text: diagnostics, stack traces,
LSP responses, formatters. `SourceMap` indexes line starts once and answers both
directions.

**Avoid it when** you only ever print one position: counting newlines is cheaper.

**Highlights** `SourceMap.from_source`, `position_at`, `offset_of`.

**API** [`api/std_sourcemap.md`](api/std_sourcemap.md) · [source](../std/sourcemap.pengu)

### `std.bitset` — fixed-length dense bit set

**Use it when** membership is over a bounded integer universe (visited flags,
feature masks, dependency closure) and you want O(1) per bit and word-at-a-time
set algebra (`and_with`, `or_with`, `xor_with`, `and_not_with`, `not`).

**Avoid it when** the universe is sparse or unbounded: use `std.coven`.

**Highlights** `BitSet.new`, `set`, `get`, `count_ones`, `and_with`.

**API** [`api/std_bitset.md`](api/std_bitset.md) · [source](../std/bitset.pengu)

### `std.diagnostic` — spans, labels and renderers

**Use it when** you build a tool that reports problems in source text and you
want the familiar shape: severity, code, message, primary and secondary spans,
and a renderer with carets.

**Avoid it when** the message has no source location: `whisper` or `spark`.

**Highlights** `Diagnostic`, `Span`, `Label`, `Severity`, `render`.

**API** [`api/std_diagnostic.md`](api/std_diagnostic.md) · [source](../std/diagnostic.pengu)

## 4. Text and numbers

### `std.scrolls` — strings, byte-oriented

**Use it when** the text is ASCII, or you are slicing bytes on purpose: `len`,
`substring`, `split`, `join`, `trim`, `strip`, `replace`, `index_of`,
`starts_with`, `lower`, `upper`, `pad_left`, case conversion
(`to_snake_case`, `pascal_case`, …) and ASCII classification.

**Avoid it when** the text is UTF-8 and you care about characters: `len` counts
bytes, `char_at` returns one byte and `reverse` reverses bytes. Use
`std.lingua` for codepoints.

**Highlights** `substring`, `split`, `join`, `trim`, `replace`, `starts_with`.

**API** [`api/std_scrolls.md`](api/std_scrolls.md) · [source](../std/scrolls.pengu)

### `std.lingua` — UTF-8 over codepoints

**Use it when** user-visible text must be measured or traversed in characters:
`codepoint_count`, `codepoint_at`, `next_codepoint`, `prev_codepoint`, `encode`,
`decode`, `validate`, `grapheme_count`, and the `Codepoint` seal.

**Avoid it when** the input is known ASCII and hot: the byte functions in
`std.scrolls` are cheaper.

**Highlights** `codepoint_count`, `codepoint_at`, `next_codepoint`, `validate`.

**API** [`api/std_lingua.md`](api/std_lingua.md) · [source](../std/lingua.pengu)

### `std.littera` — methods on `char`

**Use it when** you classify or convert a single ASCII character: `is_digit`,
`is_alpha`, `is_alnum`, `is_space`, `is_hex_digit`, `is_printable`, `to_lower`,
`to_upper`, `digit_value`, `to_int`.

**Avoid it when** the character may be multi-byte: that is a codepoint, not a
`char`.

**Highlights** `is_digit`, `is_alpha`, `to_lower`, `to_upper`, `digit_value`.

**API** [`api/std_littera.md`](api/std_littera.md) · [source](../std/littera.pengu)

### `std.logica` — methods on `bool`

**Use it when** a boolean expression reads better as a named connective:
`and_with`, `or_with`, `xor`, `nand`, `nor`, `implies`, `iff`, `toggle`,
`to_int`.

**Avoid it when** the operator is already clear: `a and b` beats
`a.and_with with b`.

**Highlights** `xor`, `implies`, `toggle`, `to_int`.

**API** [`api/std_logica.md`](api/std_logica.md) · [source](../std/logica.pengu)

### `std.integrum` — methods on integers

**Use it when** the computation is integer-only: `is_even`, `is_odd`,
`is_prime`, `gcd`, `lcm`, `factorial`, `bit_count`, `bit_length`,
`leading_zeros`, `trailing_zeros`, `div_floor`, `mod_floor`, `div_rem`,
`next_power_of_two`, `to_hex`, `to_bin`, `to_oct`.

**Avoid it when** the value is floating point: `std.fractio`.

**Highlights** `is_even`, `gcd`, `div_floor`, `to_hex`, `bit_count`.

**API** [`api/std_integrum.md`](api/std_integrum.md) · [source](../std/integrum.pengu)

### `std.fractio` — methods on floats

**Use it when** the computation is floating point: `sqrt`, `cbrt`, `pow`,
`exp`, `ln`, `log2`, `log10`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`,
`atan2`, `hypot`, `degrees`, `radians`, `lerp`, `approx_eq`, `is_nan`,
`is_finite`, `is_infinite`.

**Avoid it when** exact decimal arithmetic matters: no binary float is exact;
scale to integers and use `std.integrum`.

**Highlights** `sqrt`, `pow`, `approx_eq`, `is_nan`, `lerp`.

**API** [`api/std_fractio.md`](api/std_fractio.md) · [source](../std/fractio.pengu)

### `std.numerus` — methods on every number

**Use it when** the code must work for both integers and floats through the
`Num` concept: `abs`, `min_with`, `max_with`, `clamp`, `signum`, `round`,
`floor`, `ceil`, `truncate`, `square`, `cube`, `pow_int`, `is_zero`,
`is_between`, `to_i64`, `to_f64`.

**Avoid it when** you need integer-only operations (`%`, bit tricks): those are
on `std.integrum`.

**Highlights** `abs`, `clamp`, `min_with`, `max_with`, `round`.

**API** [`api/std_numerus.md`](api/std_numerus.md) · [source](../std/numerus.pengu)

### `std.arithmancy` — vectors, matrices, quaternions

**Use it when** you do geometry or graphics: `Vec2`, `Vec3`, `Vec4`, `Mat4`,
`Quat`, with `dot`, `cross`, `normalize`, `length`, `distance`, `lerp`,
`reflect`, `mat4_perspective`, `mat4_look_at`, `mat4_rotate`, `quat_from_euler`,
`quat_from_axis_angle`, `slerp`.

**Avoid it when** a single scalar operation is enough: `std.fractio`.

**Highlights** `Vec3`, `Mat4`, `Quat`, `dot`, `normalize`, `mat4_perspective`.

**API** [`api/std_arithmancy.md`](api/std_arithmancy.md) · [source](../std/arithmancy.pengu)

### `std.lot` — pseudo-random numbers

**Use it when** you need randomness or sampling: `rand_int`, `rand_float`,
`rand_bool`, `rand_range`, `rand_bytes`, `rand_normal`, `rand_exp`,
`rand_poisson`, `choice`, `choice_weighted`, `permutation`, `rand_password`.
The generator is PCG32 and the seed is explicit.

**Avoid it when** the bytes must be cryptographically secure: `std.secrets`
(libsodium) or `std.web.crypto` in the browser. `lot` is reproducible, not
secret.

**Highlights** `rand_int`, `rand_float`, `rand_bytes`, `choice`, `rand_range`.

**API** [`api/std_lot.md`](api/std_lot.md) · [source](../std/lot.pengu)

## 5. Collections

### `std.loom` — list algorithms, safe family

**Use it when** you transform a list and want a `maybe`/`list` answer instead of
a sentinel: generation (`range`, `repeat`, `unfold_range`), slicing (`take`,
`skip`, `chunks`, `windows`, `pairwise`), combination (`chain`, `zip_with`,
`enumerate`, `interleave`, `intersperse`, `rotate`), folds (`fold`, `scan_left`,
`sum`, `product_num`, `min_max`, `mean`, `running_*`), `map`, `filter`,
`flat_map`, `find_first`, `any_ctx`, `all_ctx`.

**Avoid it when** the list is `list of int` and you want the compact concrete
API: `std.tally` has 15 names in common with different signatures — they are not
interchangeable.

**Highlights** `map`, `filter`, `fold`, `chunks`, `zip_with`, `enumerate`.

**API** [`api/std_loom.md`](api/std_loom.md) · [source](../std/loom.pengu)

### `std.tally` — list algorithms, concrete family

**Use it when** the list holds `int` (or a type with the required bounds) and you
want the direct, allocation-light API: `sum`, `average`, `max_val`, `min_val`,
`argmax`, `argmin`, `sort`, `dedup`, `contains`, `count_of`, `frequencies`,
`group_count`, `chunk`, `flatten`, `is_sorted_*`.

**Avoid it when** you need `maybe` answers or floats: `std.tally` collapses to a
sentinel (`0`, `""`, `false`) and truncates to `int`. Use `std.loom`.

**Highlights** `sum`, `average`, `sort`, `contains`, `frequencies`.

**API** [`api/std_tally.md`](api/std_tally.md) · [source](../std/tally.pengu)

### `std.atlas` — maps

**Use it when** you key values by string or int: `get_safe`, `get_or`,
`has_key`, `put`, `remove`, `entries`, `keys`, `values`, `count`,
`filter_entries`, `from_pairs`, `from_lists`, plus the generic
`map of K to V` methods.

**Avoid it when** the keys are a small dense integer range: `std.bitset`, or
`list` indexed directly.

**Highlights** `get_safe`, `get_or`, `has_key`, `entries`, `from_pairs`.

**API** [`api/std_atlas.md`](api/std_atlas.md) · [source](../std/atlas.pengu)

### `std.coven` — sets

**Use it when** membership and uniqueness matter: `SetString`, `SetInt` and the
generic `Set of T`, with `add`, `contains`, `remove`, `union`, `intersect`,
`difference`, `symmetric_difference`, `is_subset`, `is_superset`,
`is_disjoint`.

**Avoid it when** the universe is a bounded integer range: `std.bitset` is
denser and faster.

**Highlights** `add`, `contains`, `union`, `intersect`, `to_list`.

**API** [`api/std_coven.md`](api/std_coven.md) · [source](../std/coven.pengu)

### `std.ordinal` — CC-backed containers

**Use it when** you need a container the built-ins do not provide:
`LinkedList of T`, `UnorderedSet of T`, `OrderedSet of T`, `OrderedMap of K and
V` — with `push_back`, `push_front`, `pop_front`, `put`, `get`, `has`,
`remove`, `keys`, `values`, `size`.

**Avoid it when** `list`, `map` or `Set` already fits: the CC containers exist
for the cases where ordering or node stability is the point.

**Highlights** `new_linked_list`, `new_ordered_map`, `push_back`, `put`, `get`.

**API** [`api/std_ordinal.md`](api/std_ordinal.md) · [source](../std/ordinal.pengu)

## 6. Formats and encodings

### `std.json` — strict JSON (RFC 8259)

**Use it when** you parse or produce JSON and need a real DOM: `parse`,
`stringify`, `JsonValue` with `as_object`, `as_array`, `as_string`, `as_int`,
`as_float`, `as_bool`, `get`, `at`, insertion-order preservation, JSON Pointer
(RFC 6901), deep merge and schema validation.

**Avoid it when** the document is a flat `{"key": "value"}` map and you want the
0.14-era shortcut: `std.cipher.parse_json` returns `map of string to string` and
loses types.

**Highlights** `parse`, `stringify`, `as_object`, `as_string`, `get`.

**Ownership** `JsonValue.clone` is a deep, independent copy and
`JsonValue.free` releases the whole tree (both walk nested arrays and objects);
`free_values`/`free_entries` release a list produced by `as_array`/`as_object`.
A `result of JsonValue to JsonError` still owns its boxed payload: `banish` it
when you take the value out.

**Deriving instead of walking** for a typed DTO, `derive Json` generates the codec
in C with no dependency on this module — see
[LANGUAGE.md §9.7.1](LANGUAGE.md#971-derive-json). Use `std.json` when the shape
is not known at compile time.

**API** [`api/std_json.md`](api/std_json.md) · [source](../std/json.pengu)

### `std.cipher` — encodings and checksums

**Use it when** you move bytes as text or verify integrity: `encode_base64`,
`decode_base64` (standard, URL-safe, unpadded), `encode_hex`, `decode_hex`,
Base32/Base58/Base85/Z85, `encode_url`, `decode_url`, `crc32`.

**Avoid it when** you need a cryptographic digest: `std.digest` (SHA-256). CRC-32
detects accidents, not attacks.

**Highlights** `encode_base64`, `decode_base64`, `encode_hex`, `crc32`,
`encode_url`.

**API** [`api/std_cipher.md`](api/std_cipher.md) · [source](../std/cipher.pengu)

### `std.carmen` — fixed-layout binary records

**Use it when** a binary format has fixed offsets and you want it described, not
hand-coded: a formula string (`>I4sH`) plus `CarmenWriter`/`CarmenReader`,
`calcsize`, `format`, endianness, native and Python-compatible modes.

**Avoid it when** the format is self-describing or nested: `std.json` or
`std.toml`.

**Highlights** `CarmenWriter`, `CarmenReader`, `calcsize`, `format`.

**API** [`api/std_carmen.md`](api/std_carmen.md) · [source](../std/carmen.pengu)

### `std.toml` — TOML 1.0

**Use it when** you read or write configuration and manifests: `parse`,
`parse_file`, `stringify`, `get`, `get_int`, `get_bool`, `get_float`,
`get_array`, `keys_with_prefix`, over `TomlEntry` dotted keys.

**Avoid it when** the data is already JSON: converting costs more than it saves.

**Highlights** `parse`, `parse_file`, `get_int`, `stringify`.

**API** [`api/std_toml.md`](api/std_toml.md) · [source](../std/toml.pengu)

### `std.yaml` — the legacy manifest subset

**Use it when** you must read `pengu.yaml`/`pengu.yml`-style files: `parse`,
`parse_file`, `get`, `get_array`. It implements exactly the indentation-walker
subset the old compiler accepted, not full YAML.

**Avoid it when** you control the format: TOML (`std.toml`) is the canonical
manifest format and is a real parser.

**Highlights** `parse`, `parse_file`, `get`.

**API** [`api/std_yaml.md`](api/std_yaml.md) · [source](../std/yaml.pengu)

### `std.ledger` — CSV and TSV

**Use it when** you exchange tabular text: `parse_csv`, `parse_tsv`, `read_csv`,
`read_tsv`, `to_csv_string`, `CsvTable` with `row_count`, `column_count`,
`column`, `row_as_map`, `transpose`, quoting modes (RFC 4180, backslash, none).

**Avoid it when** the file is a database export with nested types: normalise to
JSON first.

**Highlights** `parse_csv`, `read_csv`, `row_as_map`, `to_csv_string`.

**API** [`api/std_ledger.md`](api/std_ledger.md) · [source](../std/ledger.pengu)

### `std.compressus` — gzip, zlib, deflate

**Use it when** you compress or decompress bytes: `gzip_compress`,
`gzip_decompress`, `zlib_compress`, `zlib_decompress`, `deflate_compress`,
`inflate_decompress`, `detect_format`, file variants, `crc32`, `adler32`. The
wrapper adds the gzip container (RFC 1952) over vendored miniz.

**Avoid it when** the bytes are already compressed (images, video): recompressing
costs CPU and gains nothing. Prefer `output = "static"`/`small` profiling before
adding compression to a binary.

**Highlights** `gzip_compress`, `gzip_decompress`, `deflate_compress`,
`detect_format`.

**API** [`api/std_compressus.md`](api/std_compressus.md) · [source](../std/compressus.pengu)

### `std.digest` — SHA-256 and friends

**Use it when** you need a cryptographic digest: `sha256_hex`, `sha256_raw`,
`sha256_file`, `hmac_sha256_hex`, `hmac_sha256_raw`, or the cheap `fnv1a64` for
hash tables.

**Avoid it when** you only need error detection: `std.cipher.crc32`.

**Highlights** `sha256_hex`, `sha256_raw`, `sha256_file`, `hmac_sha256_hex`.

**API** [`api/std_digest.md`](api/std_digest.md) · [source](../std/digest.pengu)

### `std.regulus` — small regular expressions

**Use it when** you match a short, well-understood pattern: `Regex`,
`find_first`, `match`, `is_match`, `matches`, `match_at`, `replace_first`,
`replace_all`, `split`, `escape`. The engine is deliberately not PCRE: no
backtracking surprises, one compiled block per pattern.

**Avoid it when** the input is structured data: regexes for JSON, HTML or email
are a category error. Use `std.json`, a DOM, or a validator.

**Highlights** `find_first`, `replace_all`, `split`, `escape`.

**API** [`api/std_regulus.md`](api/std_regulus.md) · [source](../std/regulus.pengu)

## 7. System, time and diagnostics

### `std.archivum` — the file system

**Use it when** you read, write, inspect or walk files: `read_text`,
`read_bytes`, `write_text`, `append_file`, `delete_file`, `exists`, `is_file`, `is_dir`,
`file_size`, `create_dir`, `remove_dir`, `read_dir`, `copy_file`, `copy_tree`,
`find_files`, `find_dirs`, `glob`, `dir_size`, and the `*_result` variants that
say *why* an operation failed. Inside a `std.reactor` worker,
`read_text_async`, `write_text_async`, `read_bytes_async`, `write_bytes_async`,
`append_file_async`, `delete_file_async`, `exists_async`, `create_dir_async`,
`remove_dir_async`, `read_dir_async`, `copy_file_async` and `file_size_async`
run the work on the loop pool without blocking the other tasks.

**Avoid it when** the operation is about a path, not the file system: that is
`std.compass`, which is pure and testable.

**Highlights** `read_text`, `write_text`, `exists`, `read_file_result`,
`find_files`.

**API** [`api/std_archivum.md`](api/std_archivum.md) · [source](../std/archivum.pengu)

### `std.compass` — paths

**Use it when** you join, split or normalise a path: `join`, `basename`,
`dirname`, `ext`, `stem`, `normalize`, `absolute`, `relative_to`, `components`,
`expand_user`, `cwd`, `matches`, and the `Path` rune.

**Avoid it when** you need to touch the disk: `std.archivum`.

**Highlights** `join`, `basename`, `dirname`, `normalize`, `absolute`.

**API** [`api/std_compass.md`](api/std_compass.md) · [source](../std/compass.pengu)

### `std.rites` — the operating system

**Use it when** you need the process environment: `getenv`, `has_env`,
`get_args`, `arg_at_or`, `get_flag_value`, `parse_flags`, `exec`, `exec_ok`,
`home_dir`, `config_dir`, `cache_dir`, `data_dir`, `getpid`, `hostname`,
`is_windows`, `is_linux`, `is_macos`, `chdir`, `expand_env`.

**Avoid it when** you parse a typed command line: `std.invoke` handles flags,
defaults and usage.

**Highlights** `getenv`, `get_args`, `exec`, `home_dir`, `is_windows`.

**API** [`api/std_rites.md`](api/std_rites.md) · [source](../std/rites.pengu)

### `std.invoke` — typed command-line parsing

**Use it when** a CLI has flags, options, positionals or subcommands:
`new_parser`, `add_flag`, `add_option`, `add_option_int`, `add_option_bool`,
`add_positional`, `add_subcommand`, `parse`, `get_int`, `get_bool`, `get_or`,
`usage_string`, `full_help`.

**Avoid it when** the program takes one argument: `rites.get_args`.

**Highlights** `new_parser`, `add_flag`, `add_option`, `parse`, `get_int`.

**API** [`api/std_invoke.md`](api/std_invoke.md) · [source](../std/invoke.pengu)

### `std.io` — byte-exact standard I/O

**Use it when** a protocol needs exact bytes: `read_stdin_exact`,
`read_stdin_all`, `read_stdin_line`, `write_stdout`, `write_stderr`,
`flush_stdout`, `is_tty` — without losing embedded NULs or adding newlines.

**Avoid it when** the text is human-facing lines: `std.spark.print`.

**Highlights** `read_stdin_exact`, `read_stdin_all`, `write_stdout`, `is_tty`.

**API** [`api/std_io.md`](api/std_io.md) · [source](../std/io.pengu)

### `std.net` — TCP sockets

**Use it when** you implement a server or client protocol over TCP: `listen`,
`accept`, `connect`, `read`, `read_exact`, `write`, `close`, `is_open`, over a
plain `Socket` rune holding the descriptor.

**Avoid it when** you speak HTTP: `std.petitio` (client) or a purpose-built
server. Re-implementing HTTP framing is how bugs get shipped.

Inside a `std.reactor` worker, `accept_async`, `connect_async`, `read_async`,
`read_exact_async` and `write_async` have the same return types as their
synchronous counterparts and suspend the coroutine until the descriptor is
ready. The sockets must be non-blocking: `set_nonblocking` marks them,
`is_nonblocking` reports it, and `accept_async` / `connect_async` return
non-blocking sockets. A `*_async` call that receives a blocking socket panics
instead of silently blocking the loop. `connect_async` resolves DNS
blockingly (documented limitation); `local_port` returns a listener's ephemeral
port.

**Highlights** `listen`, `accept`, `connect`, `read_exact`, `write`,
`accept_async`, `read_async`, `write_async`.

**API** [`api/std_net.md`](api/std_net.md) · [source](../std/net.pengu)

### `std.chronicle` — clocks and calendars

**Use it when** you need ordinary time: `time`, `monotonic`, `now_ms`,
`sleep_ms`, `DateTime`, `datetime_utc`, `datetime_local`, `format`,
`from_iso`, `add_days`, `days_between`, `is_weekend`, `start_of_day`,
`end_of_month`, `diff_seconds`, `elapsed_ms`.

**Avoid it when** you need nanoseconds or true calendar arithmetic: `std.chrono`
(`Instant`/`Duration`, ISO 8601 round-trips). `chronicle` timestamps are
`float`, and `float` is 32-bit, so resolution at modern epochs is coarse.

**Highlights** `time`, `monotonic`, `sleep_ms`, `DateTime`, `format`.

**API** [`api/std_chronicle.md`](api/std_chronicle.md) · [source](../std/chronicle.pengu)

### `std.chrono` — instants and durations (vaqt)

**Use it when** precision matters: `Instant`, `Duration`, `now`, `to_iso`,
`parse_iso`, `plus_days`, `add_duration`, `to_unix_nano`, `weekday`,
`format_datetime`. Backed by the vendored vaqt library; opt-in.

**Avoid it when** `chronicle` already covers the case: `chrono` adds a native
dependency and a bigger API for the same wall clock.

**Highlights** `Instant`, `Duration`, `now`, `to_iso`, `to_unix_nano`.

**API** [`api/std_chrono.md`](api/std_chrono.md) · [source](../std/chrono.pengu)

### `std.whisper` — leveled logging

**Use it when** the program needs logs a human or a machine will read:
`debug`, `info`, `warn`, `error`, `fatal`, `log`, `log_json` (JSON lines),
`named_logger` (child loggers), `set_level` through the default logger, ANSI
colours, timestamps and file/stderr redirection.

**Avoid it when** the output is the program's actual result: logs go to stderr,
results go to stdout.

**Highlights** `info`, `error`, `log_json`, `named_logger`, `flush`.

**API** [`api/std_whisper.md`](api/std_whisper.md) · [source](../std/whisper.pengu)

## 8. Testing

### `std.ward` — assertions for tests and guards

**Use it when** a test must stop on the first wrong value: `assert`,
`assert_msg`, `assert_true`, `assert_false`, `assert_eq_int`,
`assert_eq_string`, `assert_eq_bool`, `assert_eq_float` (with epsilon),
`assert_ne_*`, `assert_gt_*`, `assert_ge_*`, `assert_lt_*`, `assert_le_*`,
`assert_in_range_*`, list and map variants, `assert_maybe_present`,
`assert_maybe_none`, `assert_ok_*`, `assert_err_*`.

**Avoid it when** the condition is a production invariant: `spark.assert` or an
explicit `result`. `ward` is a test dependency.

**Highlights** `assert`, `assert_eq_int`, `assert_eq_string`, `assert_eq_float`.

**API** [`api/std_ward.md`](api/std_ward.md) · [source](../std/ward.pengu)

### `std.trial` — suites and reporting

**Use it when** a test binary grows past a handful of `test` blocks: `TestSuite`,
`new_suite`, `test_case`, `test`, `summary`. Re-exports the common `ward`
assertions so a test file needs one import.

**Avoid it when** the project has one or two tests: bare `test` blocks are
enough and `psc test` already runs them.

**Highlights** `new_suite`, `test_case`, `test`, `summary`.

**API** [`api/std_trial.md`](api/std_trial.md) · [source](../std/trial.pengu)

## 9. Concurrency

### `std.filum` — threads and synchronization

**Use it when** you need to run work on another thread, or coordinate threads:
`filum.start` / `start0` / `start2` / `start3` return a `Thread`; `join` returns
`result of void to ThreadError`, `detach` lets it run, and `free` releases the
handle. `Thread` is a copyable handle (an id, not a raw pointer), so passing it
to a supervisor is safe.

Arguments move into the worker: owning values (`string`, `list`, `map`,
`maybe`, `result`, runes) must be local bindings and are unusable afterwards;
scalars are copied. A `ref to T` is accepted only when `T` is declared
`@shared`; the compiler checks that boundary, but not the locking inside `T`.

TLS (`Tls`, `tls_set`, `tls_get`), a worker `Pool` (`submit`, `wait`, `free`),
`parallel_for`, and the coordination primitives remain available: `Mutex`,
`WaitGroup`, `Once`, `Cond`, `AtomicInt`, and typed channels (`ChanInt`,
`ChanString`, `ChanFloat`, `ChanBool`, `Chan`) with `send` → `bool` and
`recv` → `maybe`.

**Avoid it when** you need a result back from the worker: `Thread` is
`into void`; send the result through a channel or a shared structure. To wait
without blocking a reactor task, use `Thread.is_finished` and
`reactor.await_thread`; `std.filum` has no coroutine-suspending channels (those
belong to `std.coro`/`std.reactor`).

**Highlights** `start`, `Thread.join`, `Thread.is_finished`, `@shared`, `Tls`, `Pool`,
`parallel_for`, `Mutex`, `chan_int`.

**API** [`api/std_filum.md`](api/std_filum.md) · [source](../std/filum.pengu)

### `std.coro` — stackful coroutines

**Use it when** you need to suspend a task and resume it later without creating
another thread: generators, lazy iterators, cooperative producers/consumers, or
a state machine written linearly.

```pengu
import std.coro

weave step with out as ref to int into void:
    set essence of out is 1
    calling coro.yield
    set essence of out is 2

weave main into int:
    var n as int is 0
    var co as coro.Coroutine is calling coro.start with step, (sigil of n)
    calling co.resume
    calling co.resume
    calling co.free
    return n
```

`start`/`start0` create the coroutine suspended and move the owning argument;
`resume` returns `CoroutineState.suspended` or `.finished`; `status` reads the
state without running; `yield` suspends the current coroutine; `free` releases a
finished one and `abandon` discards a suspended one. The coroutine lives on the
thread that created it, so a `ref to T` does not need `@shared`. The stack is
64 KiB and recycled from an arena. `std.coro` has no scheduler: the scheduling
policy is explicit and lives in `std.reactor` (`EventLoop`); there is also no
`async`/`await` syntax. The stdlib `*_async` variants are ordinary functions
that suspend the current coroutine and must be called from a loop task.

**Avoid it when** you need real parallelism (use `std.filum`), or when the work
must outlive its owner. It is not available on wasm: it needs Emscripten
fibers/Asyncify.

**Highlights** `start`, `start0`, `resume`, `yield`, `CoroutineState`,
`abandon`.

**API** [`api/std_coro.md`](api/std_coro.md) · [source](../std/coro.pengu)

### `std.reactor` — explicit event loop

**Use it when** you coordinate I/O and blocking work without one thread per
task: `EventLoop.new`, `spawn`, `run`, `stop`, `close`, `park_read`,
`park_write`, `sleep_ms`, `await_token`, `offload` and `await_thread`. The
worker receives the loop and a `ref to A` to a loop-owned copy of its argument:

```pengu
import std.reactor

weave worker with loop as ref to reactor.EventLoop, n as ref to int into void:
    calling loop.sleep_ms with 10

weave main into int:
    var loop as reactor.EventLoop is calling reactor.EventLoop.new
    calling loop.spawn with worker, 0
    calling loop.run
    calling loop.close
    return 0
```

The loop is explicit: `run` calls `epoll_wait`/`poll`, wakes ready tasks and
`resume`s them; there is no hidden scheduler or implicit `await`. `spawn` does
not run the worker inline: it starts on the next pass. `offload` sends blocking
work to the loop pool and returns a token consumed by `await_token`; a task may have several offloads in flight, each identified by its token. `close` must be called outside a coroutine,
abandons suspended tasks and does not close user descriptors.
`new`/`spawn`/`run`/`stop`/`close` belong to the owner thread.

**Avoid it when** the work is pure CPU (use `std.filum` and its `Pool`) or the
protocol is HTTP (`std.petitio`). On Windows the reactor uses `WSAEventSelect` +
`WSAWaitForMultipleEvents` with a wake event; there is no fake backend.

**Highlights** `EventLoop.new`, `spawn`, `run`, `park_read`, `sleep_ms`,
`offload`, `await_token`.

**API** [`api/std_reactor.md`](api/std_reactor.md) · [source](../std/reactor.pengu)

## 10. Network services


### `std.petitio` — HTTP client

**Use it when** the program speaks HTTP: `get`, `post`, `put`, `delete`, `head`,
`patch`, `options`, `fetch_many`, custom headers, JSON and form bodies,
multipart, query strings, cookies, timeouts, auth (`auth_basic`, `auth_bearer`,
`auth_digest`), and `result`-typed errors (`HttpError`).

**Avoid it when** the transport is not HTTP (raw TCP: `std.net`) or the client
must live in the browser (`std.web.http`, which uses `fetch`).

Inside a `std.reactor` worker, `get_async`, `send_async`,
`send_to_file_async` and `fetch_many_async` suspend the coroutine. `send_async`,
`fetch_many_async` and `Session.request_async` use one dispatcher per loop: a
single `curl_multi` thread serves every in-flight request (`fetch_many_async`
runs them concurrently, not serially). `send_to_file_async` still uses the loop
pool. `Session` also has `request_async`, `get_async`, `post_json_async`
and `post_form_async`, which merge cookies back on the loop thread. `Request`
values do not cross threads: they are built and consumed on the loop thread.

**Highlights** `get`, `post`, `Request`, `Response`, `HttpError`, `auth_bearer`,
`get_async`, `fetch_many_async`, `Session.get_async`.

**API** [`api/std_petitio.md`](api/std_petitio.md) · [source](../std/petitio.pengu)

### `std.jsonrpc` — JSON-RPC 2.0

**Use it when** you implement JSON-RPC: `encode_request`, `encode_notification`,
`encode_response_ok`, `encode_response_error`, `decode_message`, batch support,
the five standard error codes, and LSP `Content-Length` framing
(`encode_framed`, `decode_framed`).

**Avoid it when** the protocol is plain JSON over HTTP: `std.json` plus
`std.petitio`.

**Highlights** `encode_request`, `decode_message`, `encode_framed`,
`decode_framed`.

**API** [`api/std_jsonrpc.md`](api/std_jsonrpc.md) · [source](../std/jsonrpc.pengu)

## 11. Interop and native code

### `std.ffi` — C buffers and strings

**Use it when** a `declare`d C function takes or returns `char *`, `void *`, a
length-prefixed buffer or a `T *` array and you must convert to and from
PenguScript values: `cstr_from_string` (borrowed, must be freed with
`cstr_free`), `bytes_from_string`, `is_null`, `ptr_add`, `ptr_offset`,
`size_of`, `alignment_of`, `slice_from_ptr`, `list_from_ptr`,
`map_from_ptr`, and the typed `list_of_*_from_ptr` family.

**Avoid it when** a plain `ref to char` parameter accepts a string literal: the
literal converts automatically, no bridge needed.

**Highlights** `cstr_from_string`, `cstr_free`, `is_null`, `size_of`,
`slice_from_ptr`.

**API** [`api/std_ffi.md`](api/std_ffi.md) · [source](../std/ffi.pengu)

### `std.ffi_call` — libffi dynamic calls (optional)

**Use it when** the signature is only known at runtime: `FfiSignature`,
`signature`, `call`, `ret_size`, `release`. Links `-lffi` only when imported.

**Avoid it when** the signature is known at compile time: `declare` is faster,
type-checked and needs no dependency.

**Highlights** `FfiSignature`, `signature`, `call`.

**API** [`api/std_ffi_call.md`](api/std_ffi_call.md) · [source](../std/ffi_call.pengu)

### `std.dynlib` — dynamic library loading

**Use it when** a plugin or an optional dependency is loaded at runtime:
`Library`, `open`, `symbol`, `close`. Portability is handled (`dlopen` on POSIX,
`LoadLibraryA` on Windows).

**Avoid it when** the library is a build dependency: `link "name"` plus
`declare` is checked at build time and prunes correctly.

**Highlights** `Library`, `open`, `symbol`, `close`.

**API** [`api/std_dynlib.md`](api/std_dynlib.md) · [source](../std/dynlib.pengu)

### `std.secrets` — libsodium primitives (optional)

**Use it when** you need secrets, not randomness: `init`, `random_bytes`,
`sha256_raw`, `wipe` (secure zeroing) and `compare` (constant-time). Requires
`links = ["sodium"]`.

**Avoid it when** libsodium is not linked, or the bytes are not secret: `std.lot`
is reproducible and dependency-free.

**Highlights** `init`, `random_bytes`, `wipe`, `compare`.

**API** [`api/std_secrets.md`](api/std_secrets.md) · [source](../std/secrets.pengu)

## 12. WebAssembly

Everything in this section requires `--target wasm` and an Emscripten toolchain.
`std.web.url` and `std.web.security` are the exception: they are pure
PenguScript and also run in native builds.

Protect browser-only code with `when wasm:`; the inactive branch is removed
before C is emitted.

```pengu
import std.web.dom
import std.web.event

when wasm:
    weave mount into void:
        let root as dom.Element is calling dom.create with "div"
        calling dom.set_text with root, "hello"
```

### `std.web` — the browser bridge

**Use it when** you need the pieces every wasm build has: `console_log`,
`console_warn`, `console_error`, `console_trace`, `set_main_loop` (keeps the
runtime alive for callbacks), and the shared handle type.

**Avoid it when** a specialised module covers the area: `std.web.dom` for
elements, `std.web.http` for requests.

**Highlights** `console_log`, `console_error`, `set_main_loop`.

**API** [`api/std_web.md`](api/std_web.md) · [source](../std/web.pengu)

### `std.web.js` — JavaScript interop

**Use it when** you must call into JavaScript directly: `JsValue` handles,
`global`, `get`, `call_method`, `call`, `eval`, `import_module`, `from_string`,
`from_int`, `from_f64`, `array`, `object`, `retain`, `release`. Handles are
owned: release what you create, retain what you keep past a callback.

**Avoid it when** the operation has a typed wrapper (`dom`, `canvas`, `http`):
typed wrappers carry the ownership rules.

**Highlights** `JsValue`, `global`, `call_method`, `retain`, `release`.

**API** [`api/std_web_js.md`](api/std_web_js.md) · [source](../std/web/js.pengu)

### `std.web.dom` — elements and listeners

**Use it when** you build or mutate UI: `document`, `body`, `query`, `create`,
`create_text`, `append`, `set_text`, `html`, `on`, `off`, `Listener`,
`add_class`, `has_class`, `set_attr`, `get_attr`, `form_data`, `click`,
`focus`, `free`.

**Avoid it when** you need drawing: `std.web.canvas`.

**Highlights** `query`, `create`, `set_text`, `on`, `add_class`.

**API** [`api/std_web_dom.md`](api/std_web_dom.md) · [source](../std/web/dom.pengu)

### `std.web.event` — typed event accessors

**Use it when** a `dom.on` callback must read the event: `key`, `code`,
`client_x`, `client_y`, `page_x`, `page_y`, `button`, `target`,
`current_target`, `prevent_default`, `stop_propagation`, `is_shift`,
`is_ctrl`, `is_alt`, `is_meta`, `data`, `clipboard_text`.

**Avoid it when** you only need the fact that the event fired.

**Highlights** `key`, `target`, `prevent_default`, `stop_propagation`.

**API** [`api/std_web_event.md`](api/std_web_event.md) · [source](../std/web/event.pengu)

### `std.web.canvas` — Canvas 2D

**Use it when** you draw: `context2d`, `fill_rect`, `clear_rect`, `begin_path`,
`move_to`, `line_to`, `arc`, `fill`, `stroke`, `fill_text`, `measure_text`,
`draw_image`, `get_image_data`, `fit_display`. Every method returns a `result`;
a missing element or a browser exception becomes `JsError`.

**Avoid it when** the output is DOM structure: `std.web.dom`.

**Highlights** `context2d`, `fill_rect`, `fill_text`, `draw_image`.

**API** [`api/std_web_canvas.md`](api/std_web_canvas.md) · [source](../std/web/canvas.pengu)

### `std.web.browser` — window APIs

**Use it when** you need window-level behaviour: `inner_width`, `inner_height`,
`device_pixel_ratio`, `scroll_to`, `scroll_by`, `scroll_x`, `scroll_y`,
`open_url`, `reload`, `alert`, `confirm`, `prompt`, `match_media`,
`visibility_state`, `on_resize`, `on_scroll`, `on_visibility`.

**Avoid it when** the URL change must be routed: `std.web.router`.

**Highlights** `inner_width`, `scroll_to`, `open_url`, `on_resize`.

**API** [`api/std_web_browser.md`](api/std_web_browser.md) · [source](../std/web/browser.pengu)

### `std.web.location` — `window.location`

**Use it when** you read or change the address: `href`, `origin`, `protocol`,
`host`, `hostname`, `port`, `pathname`, `search`, `hash`, `assign`, `replace`,
`reload`, `set_hash`, `search_params`. `assign`/`replace` reject schemes outside
the security allow-list.

**Avoid it when** you parse a URL you already have as a string: `std.web.url`.

**Highlights** `href`, `hash`, `search`, `assign`, `set_hash`.

**API** [`api/std_web_location.md`](api/std_web_location.md) · [source](../std/web/location.pengu)

### `std.web.history` — `window.history`

**Use it when** the app manages navigation state: `push_state`, `replace_state`,
`state`, `back`, `forward`, `go`, `length`, `on_pop`.

**Avoid it when** routes are hash-based and declarative: `std.web.router`.

**Highlights** `push_state`, `state`, `back`, `on_pop`.

**API** [`api/std_web_history.md`](api/std_web_history.md) · [source](../std/web/history.pengu)

### `std.web.router` — hash routing

**Use it when** a single-page app needs routes: `on_change`, `navigate`,
`match`, `current_path`, `param`, `off`, `free_params`. Patterns support
literals, `:name` captures and a trailing `*`.

**Avoid it when** the app has one screen.

**Highlights** `on_change`, `match`, `navigate`, `param`.

**API** [`api/std_web_router.md`](api/std_web_router.md) · [source](../std/web/router.pengu)

### `std.web.http` — `fetch`

**Use it when** the browser must call an HTTP API: `request`, `get`, `post`,
`post_json`, `put`, `delete`, `json`, `header`, `Response`, `response_from`,
`free`. Asynchronous: the bridge delivers the response through a callback.

**Avoid it when** the code also runs natively: `std.petitio` covers both sides
of the wire on the server.

**Highlights** `get`, `post_json`, `json`, `response_from`.

**API** [`api/std_web_http.md`](api/std_web_http.md) · [source](../std/web/http.pengu)

### `std.web.websocket` — typed WebSocket client

**Use it when** the app needs a live channel: `open`, `send`, `close`, `state`,
`count`. Keep the runtime alive with `set_main_loop`.

**Avoid it when** polling is enough: `std.web.http`.

**Highlights** `open`, `send`, `close`, `state`.

**API** [`api/std_web_websocket.md`](api/std_web_websocket.md) · [source](../std/web/websocket.pengu)

### `std.web.storage` — localStorage and sessionStorage

**Use it when** you persist small values in the browser: `local_get`,
`local_set`, `local_remove`, `local_keys`, `local_clear`, the `_json` variants,
and the `session_*` mirror. Missing keys return `none`.

**Avoid it when** the data is large or structured: IndexedDB through
`std.web.js`.

**Highlights** `local_get`, `local_set`, `local_keys`, `session_set`.

**API** [`api/std_web_storage.md`](api/std_web_storage.md) · [source](../std/web/storage.pengu)

### `std.web.file` — picking, reading, downloading

**Use it when** the user selects or saves a file: `pick_text`, `read_text`,
`read_data_url`, `save_text`, `text_from`. Reading is asynchronous; `save_text`
triggers a normal download.

**Avoid it when** the bytes are already in memory.

**Highlights** `pick_text`, `read_text`, `save_text`.

**API** [`api/std_web_file.md`](api/std_web_file.md) · [source](../std/web/file.pengu)

### `std.web.clipboard` — system clipboard

**Use it when** you copy or paste text: `read`, `write`. Both directions are
asynchronous and permission-gated by the browser.

**Avoid it when** the text is inside the page: `dom.set_text`.

**Highlights** `read`, `write`.

**API** [`api/std_web_clipboard.md`](api/std_web_clipboard.md) · [source](../std/web/clipboard.pengu)

### `std.web.crypto` — browser cryptography

**Use it when** the browser must generate or hash secrets: `random_bytes`,
`random_int`, `uuid_v4`, `sha256_hex`, `hmac_sha256_hex`. Randomness comes from
`crypto.getRandomValues`, never `Math.random`; digests are asynchronous.

**Avoid it when** the code runs natively: `std.secrets` or `std.digest`.

**Highlights** `random_bytes`, `uuid_v4`, `sha256_hex`, `hmac_sha256_hex`.

**API** [`api/std_web_crypto.md`](api/std_web_crypto.md) · [source](../std/web/crypto.pengu)

### `std.web.url` — URL parsing and encoding (also native)

**Use it when** you parse or build a URL: `parse`, `to_string`, `origin`,
`params`, `param`, `query_get`, `query_set`, `query_remove`, `encode_component`,
`decode_component`, `with_path`, `with_query`, `Url`.

**Avoid it when** you need to navigate: `std.web.location`.

**Highlights** `parse`, `to_string`, `encode_component`, `query_get`.

**API** [`api/std_web_url.md`](api/std_web_url.md) · [source](../std/web/url.pengu)

### `std.web.security` — defensive string helpers (also native)

**Use it when** user text reaches HTML, a URL or an attribute: `escape_html`,
`is_safe_url` (rejects `javascript:`, `vbscript:`, control characters and
executable `data:` URLs), `starts_with_ignore_case`, `ends_with_ignore_case`.

**Avoid it when** the value never leaves the program.

**Highlights** `escape_html`, `is_safe_url`.

**API** [`api/std_web_security.md`](api/std_web_security.md) · [source](../std/web/security.pengu)

## 13. Optional and native dependencies

Most of the standard library is pure PenguScript. A few modules bind native code,
and only those bring a linker dependency — and only when imported, because the
dead-code eliminator removes the `declare`s of an unused module.

| Module | Native dependency | How it is enabled |
| --- | --- | --- |
| `std.petitio` | libcurl | `links = ["curl"]` in `pengu.toml` |
| `std.secrets` | libsodium | `links = ["sodium"]` in `pengu.toml` |
| `std.ffi_call` | libffi | `links = ["ffi"]` in `pengu.toml` |
| `std.dynlib` | `dl` (POSIX) / `kernel32` (Windows) | automatic |
| `std.chrono` | vaqt | vendored in `std_c/vaqt/` |
| `std.compressus` | miniz 3.1.2 | vendored in `std_c/miniz/` |
| `std.lingua` | utf8.h | vendored header in `std_c/` |
| `std.regulus` | tiny-regex-c | vendored in `std_c/re.c` |
| `std.ffi` | none (runtime helpers) | automatic |

**Vendored** means the source ships in `std_c/` and is compiled into the
program; **linked** means the system must provide the library.

### Internal binding files

Four modules keep their C declarations in a separate `.d.pengu`:

| Wrapper (import this) | Declaration file (do not import) |
| --- | --- |
| `std.compressus` | `std/compressus.d.pengu` |
| `std.lingua` | `std/lingua.d.pengu` |
| `std.petitio` | `std/petitio.d.pengu` |
| `std.regulus` | `std/regulus.d.pengu` |

The declaration file only contains `include`, `link`, `declare` and layout
types. The wrapper owns the public API, the error model and the ownership rules.
Importing the `.d` file directly skips all of that.

## 14. The complete index

All 70 modules, alphabetically. The layer matches section 1; the API column goes
to the page generated by `psc doc --include-std`.

| Module | Layer | What it gives you | API |
| --- | --- | --- | --- |
| `std.archivum` | System | read, write, copy, walk files and directories | [`std_archivum`](api/std_archivum.md) |
| `std.arena` | Core | bump allocator for object graphs with one lifetime | [`std_arena`](api/std_arena.md) |
| `std.arithmancy` | Numbers | `Vec2`/`Vec3`/`Vec4`, `Mat4`, `Quat`, geometry helpers | [`std_arithmancy`](api/std_arithmancy.md) |
| `std.atlas` | Collections | maps: `get_safe`, `put`, `entries`, filtering | [`std_atlas`](api/std_atlas.md) |
| `std.bitset` | Collections | dense fixed-length bit set and set algebra | [`std_bitset`](api/std_bitset.md) |
| `std.builder` | Core | `StringBuilder`: linear string assembly | [`std_builder`](api/std_builder.md) |
| `std.carmen` | Formats | fixed-layout binary records described by a formula | [`std_carmen`](api/std_carmen.md) |
| `std.chronicle` | System | wall clock, calendars, `DateTime`, durations | [`std_chronicle`](api/std_chronicle.md) |
| `std.chrono` | System | `Instant`/`Duration` with nanosecond precision (vaqt) | [`std_chrono`](api/std_chrono.md) |
| `std.cipher` | Formats | Base64/Hex/Base32/Base58/Base85, URL encoding, CRC-32 | [`std_cipher`](api/std_cipher.md) |
| `std.compass` | System | path join/split/normalise, `Path` rune | [`std_compass`](api/std_compass.md) |
| `std.compressus` | Formats | gzip, zlib and raw deflate | [`std_compressus`](api/std_compressus.md) |
| `std.consortium` | Core | shared ownership: `Rc`, `Arc`, `Weak` with reference counts | [`std_consortium`](api/std_consortium.md) |
| `std.coven` | Collections | sets: membership, union, intersect | [`std_coven`](api/std_coven.md) |
| `std.diagnostic` | Core | spans, labels and compiler-style rendering | [`std_diagnostic`](api/std_diagnostic.md) |
| `std.digest` | Formats | SHA-256, HMAC-SHA-256, FNV-1a | [`std_digest`](api/std_digest.md) |
| `std.dynlib` | Interop | `dlopen`/`LoadLibrary` plugin loading | [`std_dynlib`](api/std_dynlib.md) |
| `std.ffi` | Interop | C string, buffer and pointer conversions | [`std_ffi`](api/std_ffi.md) |
| `std.ffi_call` | Interop | libffi dynamic calls (optional) | [`std_ffi_call`](api/std_ffi_call.md) |
| `std.filum` | Concurrency | threads, `Mutex`, `WaitGroup`, `Once`, `Cond`, atomics, channels | [`std_filum`](api/std_filum.md) |
| `std.coro` | Concurrency | `Coroutine`, `start`, `resume`, `yield`, `current`, `abandon` | [`std_coro`](api/std_coro.md) |
| `std.reactor` | Concurrency | `EventLoop`, `spawn`, `run`, `park_*`, `offload` | [`std_reactor`](api/std_reactor.md) |
| `std.fractio` | Numbers | float methods: `sqrt`, `pow`, trigonometry | [`std_fractio`](api/std_fractio.md) |
| `std.functor` | Core | `Fn0`–`Fn3`: function pointer plus context | [`std_functor`](api/std_functor.md) |
| `std.integrum` | Numbers | integer methods: gcd, primes, bits, radix | [`std_integrum`](api/std_integrum.md) |
| `std.invoke` | System | typed CLI parser: flags, options, subcommands | [`std_invoke`](api/std_invoke.md) |
| `std.io` | System | byte-exact stdin/stdout | [`std_io`](api/std_io.md) |
| `std.json` | Formats | strict JSON parser, DOM, JSON Pointer | [`std_json`](api/std_json.md) |
| `std.jsonrpc` | Services | JSON-RPC 2.0 messages, batches, LSP framing | [`std_jsonrpc`](api/std_jsonrpc.md) |
| `std.ledger` | Formats | CSV and TSV tables | [`std_ledger`](api/std_ledger.md) |
| `std.lingua` | Text | UTF-8 codepoints, validation, grapheme count | [`std_lingua`](api/std_lingua.md) |
| `std.littera` | Text | `char` classification and case conversion | [`std_littera`](api/std_littera.md) |
| `std.logica` | Text | `bool` connectives: `xor`, `implies`, `nand` | [`std_logica`](api/std_logica.md) |
| `std.loom` | Collections | safe list algorithms returning `maybe`/`list` | [`std_loom`](api/std_loom.md) |
| `std.lot` | Numbers | PCG32 randomness, distributions, sampling | [`std_lot`](api/std_lot.md) |
| `std.memoria` | Core | raw heap blocks: `alloc`, `copy`, `resize_array` | [`std_memoria`](api/std_memoria.md) |
| `std.net` | System | TCP sockets and `*_async` variants | [`std_net`](api/std_net.md) |
| `std.numerus` | Numbers | numeric methods over the `Num` concept | [`std_numerus`](api/std_numerus.md) |
| `std.oracle` | Core | `maybe`/`result` toolbox | [`std_oracle`](api/std_oracle.md) |
| `std.ordinal` | Collections | `LinkedList`, `OrderedMap`/`OrderedSet`, `UnorderedSet` | [`std_ordinal`](api/std_ordinal.md) |
| `std.petitio` | Services | HTTP client on libcurl | [`std_petitio`](api/std_petitio.md) |
| `std.regulus` | Formats | small, explicit regular expressions | [`std_regulus`](api/std_regulus.md) |
| `std.rites` | System | environment, argv, `exec`, platform detection | [`std_rites`](api/std_rites.md) |
| `std.scrolls` | Text | byte-oriented strings: split, trim, replace, join | [`std_scrolls`](api/std_scrolls.md) |
| `std.secrets` | Interop | libsodium randomness and secure wipe (optional) | [`std_secrets`](api/std_secrets.md) |
| `std.sourcemap` | Core | byte offset ↔ line/column | [`std_sourcemap`](api/std_sourcemap.md) |
| `std.spark` | Core | console I/O, parsing, `panic`, `exit` | [`std_spark`](api/std_spark.md) |
| `std.tally` | Collections | concrete list algorithms for `list of int` | [`std_tally`](api/std_tally.md) |
| `std.toml` | Formats | TOML 1.0 parse and stringify | [`std_toml`](api/std_toml.md) |
| `std.trial` | Testing | test suites and summaries | [`std_trial`](api/std_trial.md) |
| `std.ward` | Testing | assertions with informative messages | [`std_ward`](api/std_ward.md) |
| `std.web` | WebAssembly | console, main loop, shared browser bridge | [`std_web`](api/std_web.md) |
| `std.whisper` | System | leveled logging, JSON lines, child loggers | [`std_whisper`](api/std_whisper.md) |
| `std.yaml` | Formats | legacy manifest subset | [`std_yaml`](api/std_yaml.md) |
| `std.web.browser` | WebAssembly | window geometry, scrolling, dialogs | [`std_web_browser`](api/std_web_browser.md) |
| `std.web.canvas` | WebAssembly | Canvas 2D drawing | [`std_web_canvas`](api/std_web_canvas.md) |
| `std.web.clipboard` | WebAssembly | clipboard read and write | [`std_web_clipboard`](api/std_web_clipboard.md) |
| `std.web.crypto` | WebAssembly | CSPRNG, UUID v4, SHA-256, HMAC | [`std_web_crypto`](api/std_web_crypto.md) |
| `std.web.dom` | WebAssembly | elements, attributes, listeners | [`std_web_dom`](api/std_web_dom.md) |
| `std.web.event` | WebAssembly | typed event accessors | [`std_web_event`](api/std_web_event.md) |
| `std.web.file` | WebAssembly | file pick, read and download | [`std_web_file`](api/std_web_file.md) |
| `std.web.history` | WebAssembly | history push/replace/pop | [`std_web_history`](api/std_web_history.md) |
| `std.web.http` | WebAssembly | `fetch`-based HTTP | [`std_web_http`](api/std_web_http.md) |
| `std.web.js` | WebAssembly | `JsValue` handles and JavaScript calls | [`std_web_js`](api/std_web_js.md) |
| `std.web.location` | WebAssembly | `window.location` | [`std_web_location`](api/std_web_location.md) |
| `std.web.router` | WebAssembly | hash routing | [`std_web_router`](api/std_web_router.md) |
| `std.web.security` | WebAssembly | `escape_html`, `is_safe_url` (also native) | [`std_web_security`](api/std_web_security.md) |
| `std.web.storage` | WebAssembly | localStorage and sessionStorage | [`std_web_storage`](api/std_web_storage.md) |
| `std.web.url` | WebAssembly | URL parse, build, encode (also native) | [`std_web_url`](api/std_web_url.md) |
| `std.web.websocket` | WebAssembly | WebSocket client | [`std_web_websocket`](api/std_web_websocket.md) |
## Appendix A — Import cheat sheet

```pengu-fragment
# Core
import std.spark
import std.memoria
import std.oracle
import std.builder
import std.arena
import std.functor
import std.bitset
import std.sourcemap
import std.diagnostic

# Text and numbers
import std.scrolls
import std.lingua
import std.littera
import std.logica
import std.integrum
import std.fractio
import std.numerus
import std.arithmancy
import std.lot

# Collections
import std.loom
import std.tally
import std.atlas
import std.coven
import std.ordinal

# Formats
import std.json
import std.cipher
import std.carmen
import std.toml
import std.yaml
import std.ledger
import std.compressus
import std.digest
import std.regulus

# System
import std.archivum
import std.compass
import std.rites
import std.invoke
import std.io
import std.net
import std.chronicle
import std.chrono
import std.whisper

# Testing and concurrency
import std.ward
import std.trial
import std.filum

# Services and interop
import std.petitio
import std.jsonrpc
import std.ffi
import std.ffi_call
import std.dynlib
import std.secrets

# WebAssembly
import std.web
import std.web.dom
import std.web.event
import std.web.http
import std.web.js
```

## Appendix B — Ownership when calling the standard library

The generated page for each symbol carries an ownership note in its `##` text.
The conventions are consistent:

| The function returns | Who frees it |
| --- | --- |
| `string` built from parts | the caller, with `banish` |
| `list of T`, `map`, `Set` | the caller; free elements first if they are `string` |
| `maybe T` / `result of T to E` | the caller owns the payload when present |
| a `*_view`, `bytes_view`, `source`, `html`, a `dom` handle borrowed by an event | nobody — it is a view or a borrowed handle |
| a handle (`JsValue`, `Element`, `Listener`, `Socket`) | the caller, with the matching `free`/`close`/`off` |

When a function takes ownership, its name or its `##` note says so
(`take_*`, `consume_*`, `_owned`). When in doubt, read the note on the generated
page before writing the `banish`.

### Copy-on-write containers

`string`, `list of T` and `map of K to V` are copy-on-write since 0.52. Copying
a binding is O(1): both bindings share one buffer with a counter, and the first
mutation clones it (`ensure_unique`). Three methods make that visible:

| Method | On | What it does |
| --- | --- | --- |
| `is_shared` | `list`, `map`, `string` | `true` when another binding shares the buffer |
| `ref_count` | `list`, `map`, `string` | number of bindings sharing the buffer |
| `make_unique` | `list`, `map`, `string` | clones now, so the next mutation is in place |

Copy-then-mutate inside a loop is the one pattern where COW costs more than
plain copies; `psc check --lint=cow` flags it (`W0008`, informational).
A pristine container still has no automatic destructor: `banish` it when you
are done, exactly as before.

## Appendix C — Naming conventions in the standard library

| Pattern | Meaning |
| --- | --- |
| `get_*` | may fail; returns `maybe` |
| `get_or` | takes a fallback |
| `*_safe` | bounds-checked, returns `maybe` |
| `*_result` | returns `result` with an error omen |
| `is_*`, `has_*` | predicates, `bool` |
| `to_*` | conversion that may lose information |
| `*_view` | borrowed view, never free |
| `*_owned` | an owned copy; the caller frees |
| `*_file` | reads or writes a path instead of a buffer |
| `*_raw` | bytes instead of an encoded string |
