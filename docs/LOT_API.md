# `std.lot` — frozen public API contract

> **Status: frozen.** This is the API that Chunk 7 (`filum`, `celeris`) and the
> remaining migration chunks are built against. Changing a signature here is a
> breaking change and must bump `LOT_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/lot.pengu`](../std/lot.pengu).
> Bugs fixed in this revision: [`BUGS_FIXED_CHUNK6.md`](BUGS_FIXED_CHUNK6.md).

`lot` owns randomness: seeding, uniform draws, ranges, the common probability
distributions, sampling/shuffling, generic (`shard T`) collection helpers and
random string/byte token generation. It imports `std.spark` (panic) and
`std.arithmancy` (the maths behind the distributions). It is **not**
cryptographically secure.

The module declares the C bridges and then sets `insignia lot_`, so the bridges
keep their exact `pengu_c_*` runtime names while every module symbol is emitted as
`lot_*`. Three `antiquus` blocks (`_mtx`, `_lock`, `_unlock`) take a process-wide
mutex from the runtime's portable thread layer; the `_mtx` accessor carries
`@export("lot__mtx")` so dead-code elimination keeps it (raw C calls it).

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every parameter (`items`, `weights`, `charset`, `n`, `k`, `shape`, …) | borrowed, read-only | never `banish` |
| scalar returns (`int`, `float`, `bool`) | plain value | never `banish` |
| `maybe T` returns (`choice`, `choice_weighted`, `rand_choice_shard`) | value; owns nothing | never `banish` |
| `list of T` returns (`shuffle`, `sample`, `rand_bytes`, `rand_choose_n`, …) | freshly allocated | `banish` |
| `string` returns (`rand_alpha`, `rand_bytes_hex`, `rand_base64`, `rand_uuid4`, …) | freshly allocated | `banish` |

No returned container aliases an argument, and no argument is retained after the
call. Result containers are always fresh copies.

## Constants

| Constant | Type | Value | Meaning |
|---|---|---|---|
| `LOT_VERSION` | `string` | `"2.1.0"` | Revision of the **lot API**. |
| `LOT_EPSILON` | `float` | `1e-9` | Clamp used by `_unit_open`. |
| `LOT_INT_MAX` | `int` | `2147483647` | `INT_MAX`, used by the weighted chooser. |
| `BASE64_ALPHABET` | `string` | RFC 4648 table | Alphabet used by `_b64_char`. |

## Native runtime declarations (internal C bridges)

Byte-identical to 2.0.0; they are the runtime contract, not the PenguScript API.

| Declaration | Signature |
|---|---|
| `pengu_c_srand` | `(int) -> void` |
| `pengu_c_rand` | `() -> int` |
| `pengu_c_rand_max` | `() -> int` |
| `pengu_c_rand_double` | `() -> float` |
| `pengu_c_rand_range` | `(int, int) -> int` |
| `pengu_c_rand_range_float` | `(float, float) -> float` |
| `pengu_c_rand_normal` | `(float, float) -> float` |
| `pengu_c_rand_exp` | `(float) -> float` |
| `pengu_c_rand_bool` | `(float) -> bool` |
| `pengu_c_rand_poisson` | `(float) -> int` |
| `pengu_c_time` | `() -> float` |
| `pengu_c_getpid` | `() -> int` |

## Seeding and raw draws

| Symbol | Signature | Semantics |
|---|---|---|
| `seed` | `(s: int) -> void` | Seeds the process-global C PRNG. Negative values are reinterpreted modulo 2^32, as in C. |
| `seed_from_time` | `() -> void` | Seeds from the wall clock (whole seconds). |
| `seed_from_pid` | `() -> void` | Seeds from the process id. |
| `rand_int` | `() -> int` | One raw draw, clamped to `[0, RAND_MAX]`. |
| `rand_max` | `() -> int` | C `RAND_MAX`. |
| `rand_float` | `() -> float` | Uniform in `[0.0, 1.0)`. |

## Ranges

| Symbol | Signature | Semantics |
|---|---|---|
| `rand_range` | `(min_val: int, max_val: int) -> int` | Uniform in `[lo, hi]`, inclusive; returns `lo` when `lo >= hi`. |
| `rand_range_float` | `(min_val: float, max_val: float) -> float` | Uniform in `[lo, hi)`; returns `lo` when `lo >= hi`. |

## Continuous and discrete distributions

| Symbol | Signature | Semantics |
|---|---|---|
| `rand_normal` | `(mean: float, stddev: float) -> float` | Box–Muller normal; `stddev <= 0` returns `mean`. |
| `rand_exp` | `(rate: float) -> float` | Exponential, mean `1/rate`; `rate <= 0` returns `0.0`. |
| `rand_bool` | `(probability: float = 0.5) -> bool` | True with `probability`. |
| `rand_poisson` | `(rate: float) -> int` | Poisson count; `rate <= 0` returns `0`. |
| `rand_lognormal` | `(mu: float, sigma: float) -> float` | `exp(Normal(mu, sigma))`; `sigma <= 0` returns `exp(mu)`. |
| `rand_weibull` | `(shape: float, scale: float) -> float` | Weibull; `shape <= 0` or `scale <= 0` returns `0.0`. |
| `rand_triangular` | `(lo: float, mode: float, hi: float) -> float` | Triangular in `[lo, hi]`; an out-of-range `mode` or `hi <= lo` returns `lo`. |
| `rand_gamma` | `(shape: float, scale: float) -> float` | Marsaglia–Tsang (+ Ahrens–Dieter for `shape < 1`); `shape <= 0` or `scale <= 0` returns `0.0`. Can only return an accepted sample. |
| `rand_beta` | `(a: float, b: float) -> float` | Beta in `[0, 1]`; `a <= 0` or `b <= 0` returns `0.0`. |
| `rand_vonmises` | `(mu: float, kappa: float) -> float` | Circular normal, normalised to `[0, 2π)`; `kappa <= 1e-6` is uniform. |
| `rand_pareto` | `(alpha: float) -> float` | Pareto `>= 1.0`; `alpha <= 0` returns `0.0`. |
| `rand_cauchy` | `(x0: float, gamma: float) -> float` | Cauchy; `gamma <= 0` returns `x0`. |
| `rand_chi_squared` | `(k: int) -> float` | `Gamma(k/2, 2)`; `k <= 0` returns `0.0`. |

## Aliases and ergonomic helpers

| Symbol | Signature | Semantics |
|---|---|---|
| `rand_between` | `(lo: int, hi: int) -> int` | Alias of `rand_range`. |
| `rand_uniform` | `(lo: float, hi: float) -> float` | Alias of `rand_range_float`. |
| `rand_gauss` | `(mean: float, stddev: float) -> float` | Alias of `rand_normal`. |
| `rand_bool_with` | `(p: float) -> bool` | Alias of `rand_bool`. |
| `rand_coin` | `() -> bool` | Fair coin (`rand_bool(0.5)`). |
| `rand_bit` | `() -> int` | `0` or `1`. |
| `rand_sign` | `() -> int` | `-1` or `1`. |

## List sampling and combinatorics

Every `list of T` result is a freshly allocated copy; the input is never mutated.

| Symbol | Signature | Semantics |
|---|---|---|
| `shuffle` | `(items: list of int) -> list of int` | Fisher–Yates copy. |
| `shuffle_string` | `(items: list of string) -> list of string` | Fisher–Yates copy. |
| `choice` | `(items: list of int) -> maybe int` | Uniform pick; `maybe none` when empty. |
| `choice_string` | `(items: list of string) -> maybe string` | Uniform pick; `maybe none` when empty. |
| `choice_weighted` | `(items: list of int, weights: list of int) -> maybe int` | Weighted pick; `maybe none` when empty, mismatched or all weights `<= 0`. Overflow-safe. |
| `choice_weighted_string` | `(items: list of string, weights: list of int) -> maybe string` | Idem for strings. |
| `sample` | `(items: list of int, k: int) -> list of int` | `k` distinct elements; clamps `k` to the list length. |
| `sample_with_replacement` | `(items: list of int, k: int) -> list of int` | `k` draws, repeats allowed. |
| `sample_string` | `(items: list of string, k: int) -> list of string` | `k` distinct strings. |
| `permutation` | `(n: int) -> list of int` | `0 .. n-1` in random order. |
| `rand_choice_n` | `(items: list of int, k: int) -> list of int` | `k` draws with replacement (`random.choices`). |
| `rand_choice_n_string` | `(items: list of string, k: int) -> list of string` | Idem for strings. |
| `rand_sample_weighted` | `(items: list of int, weights: list of int, k: int) -> list of int` | `k` distinct elements drawn proportionally to `weights`, without replacement. |

### Generic (`shard T`) forms

| Symbol | Signature | Semantics |
|---|---|---|
| `rand_choice_shard` | `shard T (items: list of T) -> maybe T` | Generic `choice`. |
| `rand_shuffle_shard` | `shard T (items: list of T) -> list of T` | Generic Fisher–Yates copy. |
| `rand_sample_shard` | `shard T (items: list of T, k: int) -> list of T` | Generic sample without replacement. |
| `rand_permutation_shard` | `shard T (items: list of T) -> list of T` | Permutation of a list (alias of `rand_shuffle_shard`). |

## Random strings, bytes and tokens

| Symbol | Signature | Semantics |
|---|---|---|
| `rand_from_charset` | `(charset: string, n: int) -> string` | `n` characters sampled from `charset`; `""` when `n <= 0` or the charset is empty. |
| `rand_alpha` | `(n: int) -> string` | `n` letters `a-z`, `A-Z`. |
| `rand_digit_string` | `(n: int) -> string` | `n` digits `0-9`. |
| `rand_alnum_string` | `(n: int) -> string` | `n` alphanumerics. |
| `rand_hex_string` | `(n: int) -> string` | `n` lowercase hex **characters**. |
| `password_symbols` | `() -> string` | `r"!@#$%^&*()-_=+[]{}|;:,.<>?"`. |
| `rand_password` | `(n: int, include_symbols: bool = false) -> string` | `n` characters from the alphanumeric alphabet, plus `password_symbols` when requested. |
| `rand_bytes` | `(n: int) -> list of int` | `n` real bytes, each in `[0, 255]`. |
| `rand_bytes_string` | `(n: int) -> string` | The same bytes packed into a `string` of length `n` (may contain `NUL`). |
| `rand_bytes_hex` | `(n: int) -> string` | Lowercase hex of `n` real bytes; length `2n`. |
| `rand_hex_upper` | `(n: int) -> string` | Uppercase hex of `n` real bytes; length `2n`. |
| `rand_base64` | `(n: int) -> string` | Standard base64 (with `=`) of `n` real bytes; length `4*ceil(n/3)`. |
| `rand_uuid4` | `() -> string` | RFC 4122 v4 UUID (`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`). |

> `rand_hex_string(n)` samples `n` hex **characters**; `rand_bytes_hex(n)` and
> `rand_hex_upper(n)` encode `n` **bytes** and are twice as long. This
> distinction is deliberate and is part of the frozen contract.

## Internal helpers (private, `_`-prefixed)

These are `E0043`-private: they are listed so the module's own tests and the next
maintainer can see them, not as callable API.

| Symbol | Signature | Purpose |
|---|---|---|
| `_unit_open` | `() -> float` | Uniform in the open interval `(0.0, 1.0)`. |
| `_gamma_mt` | `(shape: float, scale: float, max_iter: int) -> maybe float` | One bounded Marsaglia–Tsang pass; `maybe none` on exhaustion. |
| `_weighted_index` | `(weights: list of int, count: int) -> int` | Overflow-safe weighted index, `-1` when no weight is positive. |
| `_hex_digit` / `_hex_digit_upper` | `(v: int) -> string` | One lowercase/uppercase hex digit. |
| `_bytes_hex` | `(data: list of int, upper: bool) -> string` | Hex-encode a byte list. |
| `_b64_char` | `(idx: int) -> string` | One base64 character. |
| `_base64_encode` | `(data: list of int) -> string` | Standard base64 with padding. |
| `_password_charset` | `() -> string` | Alphanumerics plus `password_symbols`. |
| `_mtx` / `_lock` / `_unlock` | see source | Portable process-wide PRNG mutex. |

## Thread-safety contract

Every bridge call that reads or writes the shared generator runs inside
`_lock` / `_unlock`, so **concurrent single draws are atomic**. A compound
operation that must observe a frozen sequence (`seed` followed by several draws)
still has to be serialised by the caller, because the lock is released between
two separate calls. `seed` re-seeds the whole process.

## Reproducibility contract

`seed(N)` reproduces a sequence exactly **within one C library**. glibc, musl and
the MSVC CRT implement `rand()` differently, so the same seed draws different
numbers on another platform. No test pins a literal draw.

## Security contract

`lot` is **not** cryptographically secure. `rand_bytes`, `rand_base64` and
`rand_uuid4` are *random*, not *secret*. Never derive passwords, session tokens
or keys from this module; use `std.seal` for that.
