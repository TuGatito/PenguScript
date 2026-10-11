# `std.scrolls` — frozen public API contract

> **Status: frozen.** Chunk 2 of the Pengunic 2.0 migration. Every symbol below
> is public and must keep its signature; adding a new one is fine, changing or
> removing one is a breaking change.
>
> Module revision: **`2.0.0`** (`SCROLLS_VERSION`).
> Source: [`std/scrolls.pengu`](../std/scrolls.pengu).

`scrolls` is the string layer of the standard library. Every operation exists
twice, with the same semantics: as a method on `string`
(`calling s.trim`) and as a module function (`calling scrolls.trim with s`).
`join` is a module function only. `parse_int` / `parse_float` are methods only:
as module functions their names would collide with the compiler intrinsics
`pengu_parse_int` / `pengu_parse_float` emitted under `insignia pengu_`.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every method / function returning `string` | new owned `string` | `banish` / `defer banish` |
| every method / function returning `list of string` or `list of int` | new owned list | `banish` / `defer banish` |
| `substring`, `char_at` | new owned `string` (a copy, not a view) | `banish` |

The receiver and every parameter are borrowed: nothing mutates `self` and
nothing frees an argument. Returned strings are copies, so a result never aliases
the receiver.

## ASCII and bytes

The module is ASCII and byte-oriented. `len`, every index, `chars`, `bytes`,
`substring`, `char_at`, `reverse` and `truncate` count **bytes**, not UTF-8 code
points. A multi-byte character is seen as several bytes, and `char_at` /
`reverse` can split it. Case conversion (`lower`, `upper`, `capitalize`, `title`,
`swap_case`) only touches ASCII `A-Z`/`a-z`; other bytes pass through untouched.

`compare` is a byte-wise ordering (memcmp semantics), then length.

## Methods on `string`

### Length and iteration

| Method | Signature | Semantics |
|---|---|---|
| `len` | `() -> int` | Byte length. |
| `is_empty` | `() -> bool` | `len == 0`. |
| `chars` | `() -> list of string` | One single-byte `string` per byte. |
| `bytes` | `() -> list of int` | The byte code (0–255) of each byte. |

### Search

| Method | Signature | Semantics |
|---|---|---|
| `contains` | `(sub: string) -> bool` | `sub` occurs anywhere. Empty `sub` is true. |
| `starts_with` | `(prefix: string) -> bool` | True when the string begins with `prefix`; empty prefix is true. |
| `ends_with` | `(suffix: string) -> bool` | True when the string ends with `suffix`; empty suffix is true. |
| `starts_with_any` | `(prefixes: list of string) -> bool` | True when any prefix matches; empty list is false. |
| `ends_with_any` | `(suffixes: list of string) -> bool` | True when any suffix matches; empty list is false. |
| `index_of` | `(sub: string) -> int` | First index of `sub`, or `-1`. Empty `sub` returns 0. |
| `last_index_of` | `(sub: string) -> int` | Last index of `sub`, or `-1`. Empty `sub` returns `len`. |
| `find`* | `(sub: string) -> int` | Deprecated alias of `index_of`. |
| `rfind`* | `(sub: string) -> int` | Deprecated alias of `last_index_of`. |
| `count` | `(sub: string) -> int` | Non-overlapping occurrences; 0 for an empty or longer `sub`. |
| `count_matches`* | `(sub: string) -> int` | Deprecated alias of `count`. |

### Slicing

| Method | Signature | Semantics |
|---|---|---|
| `substring` | `(start_pos: int, end_pos: int) -> string` | `[start_pos, end_pos)` in bytes; empty when the range is empty. |
| `char_at` | `(idx: int) -> string` | The byte at `idx` as a one-byte string. |
| `reverse` | `() -> string` | Bytes in reverse order. |

### Case

| Method | Signature | Semantics |
|---|---|---|
| `lower` | `() -> string` | ASCII `A-Z` → `a-z`. |
| `upper` | `() -> string` | ASCII `a-z` → `A-Z`. |
| `to_lower`* | `() -> string` | Deprecated alias of `lower`. |
| `to_upper`* | `() -> string` | Deprecated alias of `upper`. |
| `capitalize` | `() -> string` | First byte upper, rest lower; `""` stays `""`. |
| `title` | `() -> string` | First letter of each whitespace-separated word upper, rest lower; spacing preserved. |
| `title_case`* | `() -> string` | Deprecated alias of `title`. |
| `swap_case` | `() -> string` | Each ASCII letter's case flipped; other bytes unchanged. |
| `to_snake_case` | `() -> string` | CamelCase/PascalCase split on case boundaries, separators normalized to `_`, runs collapsed. |
| `to_kebab_case` | `() -> string` | `to_snake_case` with `_` → `-`. |
| `snake_case` | `() -> string` | Short form of `to_snake_case`. |
| `kebab_case` | `() -> string` | Short form of `to_kebab_case`. |
| `pascal_case` | `() -> string` | Each `snake_case` word capitalized, joined; `""` stays `""`. |

### Classification

| Method | Signature | Semantics |
|---|---|---|
| `is_alpha` | `() -> bool` | Every byte is an ASCII letter; `""` is false. |
| `is_digit` | `() -> bool` | Every byte is an ASCII digit; `""` is false. |
| `is_alnum` | `() -> bool` | Every byte is an ASCII letter or digit; `""` is false. |
| `is_lower` | `() -> bool` | No uppercase and at least one lowercase. |
| `is_upper` | `() -> bool` | No lowercase and at least one uppercase. |
| `is_palindrome` | `() -> bool` | Reads the same forwards and backwards; length 0/1 is true. |

### Whitespace

| Method | Signature | Semantics |
|---|---|---|
| `trim` | `() -> string` | Strip ASCII whitespace from both ends. |
| `strip` | `() -> string` | Alias of `trim`. |
| `trim_start` | `() -> string` | Strip leading ASCII whitespace. |
| `trim_end` | `() -> string` | Strip trailing ASCII whitespace. |
| `lstrip`* | `() -> string` | Deprecated alias of `trim_start`. |
| `rstrip`* | `() -> string` | Deprecated alias of `trim_end`. |
| `is_space` | `() -> bool` | Non-empty and all ASCII whitespace; `""` is false. |
| `is_whitespace`* | `() -> bool` | Deprecated alias of `is_space`. |
| `is_blank` | `() -> bool` | Empty or all ASCII whitespace. |
| `split_whitespace` | `() -> list of string` | Split on runs of ASCII whitespace, ignoring the ends. |
| `words` | `() -> list of string` | Short form of `split_whitespace`. |
| `split_lines` | `() -> list of string` | Split on `\n`, keeping a trailing `\r`; `""` gives an empty list. |
| `lines` | `() -> list of string` | Like `split_lines` but each trailing `\r` is removed. |
| `line_count` | `() -> int` | Number of `\n`-separated lines. |
| `word_count` | `() -> int` | Number of whitespace-separated words. |

### Replace and split

| Method | Signature | Semantics |
|---|---|---|
| `replace` | `(from_str: string, to_str: string) -> string` | First occurrence replaced. Empty `from_str` inserts `to_str` at the front (legacy). |
| `replace_all` | `(from_str: string, to_str: string) -> string` | All non-overlapping occurrences replaced. Empty `from_str` returns a copy. |
| `split` | `(delim: string) -> list of string` | Split on every `delim`. Empty `delim` returns one element with the whole string. |
| `splitn` | `(delim: string, n: int) -> list of string` | At most `n` parts; the last keeps the remaining delimiters. `n <= 0` returns the whole string as one part. |
| `rsplit` | `(delim: string) -> list of string` | Split scanning from the right, preserving left-to-right order. |
| `partition` | `(sep: string) -> list of string` | `[before, sep, after]`; `[self, "", ""]` when `sep` is missing or empty. |
| `repeat` | `(count: int) -> string` | `count` copies concatenated; `count <= 0` or empty gives `""`. |
| `repeat_join` | `(count: int, sep: string) -> string` | `count` copies joined by `sep`. |

### Alignment

| Method | Signature | Semantics |
|---|---|---|
| `ljust` | `(width: int, pad_char: string is " ") -> string` | Pad on the right to `width`; truncates to `width` when the fill overshoots. |
| `rjust` | `(width: int, pad_char: string is " ") -> string` | Pad on the left to `width`; truncates from the left when needed. |
| `pad_left`* | `(width: int, pad_char: string is " ") -> string` | Deprecated alias of `rjust`. |
| `pad_right`* | `(width: int, pad_char: string is " ") -> string` | Deprecated alias of `ljust`. |
| `zfill` | `(width: int) -> string` | Zero-pad on the left to `width`, preserving a leading `+`/`-`. |
| `center` | `(width: int, pad_char: string is " ") -> string` | Centre in `width`; on odd padding the left gets the smaller half. |

### Prefix and suffix removal, comparison, truncation, parsing

| Method | Signature | Semantics |
|---|---|---|
| `removeprefix` | `(prefix: string) -> string` | Drop `prefix` when present, else a copy. |
| `removesuffix` | `(suffix: string) -> string` | Drop `suffix` when present, else a copy. |
| `compare` | `(other: string) -> int` | `-1` / `0` / `1`, byte-wise then by length. |
| `truncate` | `(max_len: int, suffix: string) -> string` | Cut to `max_len` bytes, appending `suffix` when it fits; `max_len <= len(suffix)` cuts without it. |
| `ellipsis` | `(max_len: int) -> string` | `truncate` with `"..."`. |
| `parse_int` | `() -> maybe int` | Delegates to `spark.parse_int`: optional whitespace and sign, no overflow. |
| `parse_float` | `() -> maybe float` | Digit-by-digit decimal; no exponents. |
| `is_numeric` | `() -> bool` | Exact numeric literal: optional sign, at most one `.`, at least one digit. |

## Module functions

Every method above whose name does not start with `_` also exists as a module
function with the receiver as first parameter `s`, except `parse_int` /
`parse_float` (methods only) and `join` (module only).

| Function | Signature |
|---|---|
| `len` | `(s: string) -> int` |
| `is_empty` | `(s: string) -> bool` |
| `chars` | `(s: string) -> list of string` |
| `bytes` | `(s: string) -> list of int` |
| `contains` | `(s: string, sub: string) -> bool` |
| `starts_with` | `(s: string, prefix: string) -> bool` |
| `ends_with` | `(s: string, suffix: string) -> bool` |
| `starts_with_any` | `(s: string, prefixes: list of string) -> bool` |
| `ends_with_any` | `(s: string, suffixes: list of string) -> bool` |
| `index_of` | `(s: string, sub: string) -> int` |
| `last_index_of` | `(s: string, sub: string) -> int` |
| `find`* | `(s: string, sub: string) -> int` |
| `rfind`* | `(s: string, sub: string) -> int` |
| `count` | `(s: string, sub: string) -> int` |
| `count_matches`* | `(s: string, sub: string) -> int` |
| `substring` | `(s: string, start_pos: int, end_pos: int) -> string` |
| `char_at` | `(s: string, idx: int) -> string` |
| `reverse` | `(s: string) -> string` |
| `lower` / `upper` | `(s: string) -> string` |
| `to_lower`* / `to_upper`* | `(s: string) -> string` |
| `capitalize` / `title` / `title_case`* | `(s: string) -> string` |
| `swap_case` | `(s: string) -> string` |
| `to_snake_case` / `to_kebab_case` / `snake_case` / `kebab_case` / `pascal_case` | `(s: string) -> string` |
| `is_alpha` / `is_digit` / `is_alnum` / `is_lower` / `is_upper` / `is_palindrome` | `(s: string) -> bool` |
| `trim` / `strip` / `trim_start` / `trim_end` | `(s: string) -> string` |
| `lstrip`* / `rstrip`* | `(s: string) -> string` |
| `is_space` / `is_whitespace`* / `is_blank` | `(s: string) -> bool` |
| `split_whitespace` / `words` / `split_lines` / `lines` | `(s: string) -> list of string` |
| `line_count` / `word_count` | `(s: string) -> int` |
| `replace` / `replace_all` | `(s: string, from_str: string, to_str: string) -> string` |
| `split` | `(s: string, delim: string) -> list of string` |
| `splitn` | `(s: string, delim: string, n: int) -> list of string` |
| `rsplit` | `(s: string, delim: string) -> list of string` |
| `partition` | `(s: string, sep: string) -> list of string` |
| `repeat` | `(s: string, count: int) -> string` |
| `repeat_join` | `(s: string, count: int, sep: string) -> string` |
| `ljust` / `rjust` | `(s: string, width: int, pad_char: string is " ") -> string` |
| `pad_left`* / `pad_right`* | `(s: string, width: int, pad_char: string is " ") -> string` |
| `zfill` | `(s: string, width: int) -> string` |
| `center` | `(s: string, width: int, pad_char: string is " ") -> string` |
| `removeprefix` / `removesuffix` | `(s: string, affix: string) -> string` |
| `compare` | `(a: string, b: string) -> int` |
| `truncate` | `(s: string, max_len: int, suffix: string) -> string` |
| `ellipsis` | `(s: string, max_len: int) -> string` |
| `is_numeric` | `(s: string) -> bool` |
| `join` | `(parts: list of string, sep: string) -> string` |

`*` = deprecated. The deprecated aliases carry the **docstring** marker
`## @deprecated Use X instead.` and therefore do **not** emit `W0006`; the
inventory with replacement and retirement version lives in
[`DEPRECATIONS.md`](DEPRECATIONS.md).

## C bridges (`antiquus`, internal)

Chunk 2 moved the string helpers that only `scrolls` used out of
`pengu_runtime.h` and into this module. They are not part of the frozen public
surface; they exist so DCE can prune them and so the algorithm lives next to its
only consumer.

| Bridge | Signature | Origin |
|---|---|---|
| `_char_is_space` | `(ch: string) -> bool` | new C block; replaced a Pengu `ord`-based weave |
| `_char_is_digit` | `(ch: string) -> bool` | new C block; replaced a Pengu weave |
| `_char_is_upper` | `(ch: string) -> bool` | new C block; replaced a Pengu weave |
| `_char_is_lower` | `(ch: string) -> bool` | new C block; replaced a Pengu weave |
| `_char_is_alpha` | `(ch: string) -> bool` | new C block; replaced a Pengu weave |
| `_char_is_alnum` | `(ch: string) -> bool` | new C block; replaced a Pengu weave |
| `pengu_string_contains` | `(a: string, b: string) -> bool` | moved from `pengu_runtime.h` |
| `pengu_string_starts_with` | `(a: string, prefix: string) -> bool` | moved |
| `pengu_string_ends_with` | `(a: string, suffix: string) -> bool` | moved |
| `pengu_string_index_of` | `(a: string, sub: string) -> int` | moved |
| `pengu_string_last_index_of` | `(a: string, sub: string) -> int` | moved |
| `pengu_string_replace` | `(s: string, from: string, to: string) -> string` | moved (drives `replace_all`) |
| `pengu_string_repeat` | `(s: string, times: int) -> string` | moved |
| `pengu_string_reverse` | `(s: string) -> string` | moved |

No duplication rule: the Pengu weaves `_index_of_from`, `_last_index_of_from`,
`_has_prefix_at` and the six `_char_is_*` weaves were **deleted**; their callers
now use the C blocks (or `pengu__find_sub`, which stays in the header because
`pengu_string_split` and the glob matcher use it).

## Compatibility

* Every pre-2.0 public symbol keeps its name and signature. The deprecated
  aliases still work.
* `starts_with_any`, `ends_with_any`, `splitn`, `rsplit` and `strip` are the
  only additions.
* Behavior is unchanged: the C blocks were copied verbatim from the runtime, and
  `replace_all` / `repeat` / `reverse` now use the same code path the runtime
  used.
