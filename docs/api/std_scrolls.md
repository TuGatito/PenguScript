# std.scrolls

> Source: `std/scrolls.pengu`

std/scrolls.pengu — string operations: querying, searching, slicing, trimming,
replacing, splitting, joining, padding, ASCII classification, comparison and
parsing.

Every operation exists twice: as a method (`calling s.trim`) and as a module
function (`calling scrolls.trim with s`) that delegates to the method.
`join` only exists as a module function; `parse_int`/`parse_float` only as
methods.

## Example
```pengu
import std.scrolls
import std.spark

weave main into int:
    let raw as string is "  Hello, World  "
    var clean as string is calling raw.get_trim
    var parts as list of string is calling clean.split with ", "
    var joined as string is calling scrolls.join with parts, "|"
    calling spark.println with joined
    return 0
```

## Memory
A `string` is an owned buffer behind a value header. Every method that returns
a `string` comes in **two spellings**:

- **`<name>` mutates the receiver in place.** `calling s.trim` computes the
  new text, releases the buffer `s` used to own and installs the new one; it
  returns nothing, so it is only valid as a statement. Nothing is left to
  release: the replacement already released what it replaced.
- **`get_<name>` is pure.** It returns a fresh owned `string` and leaves the
  receiver untouched. Release the result with `banish`.

```pengu
var s as string is "  Hello  "
calling s.trim                       # s is now "Hello"
var t as string is calling s.get_trim
banish t
```

The mutating form is `substring`, `char_at`, `reverse`, `lower`, `upper`,
`to_lower`, `to_upper`, `capitalize`, `title`, `title_case`, `swap_case`,
`to_snake_case`, `to_kebab_case`, `snake_case`, `kebab_case`, `pascal_case`,
`trim`, `strip`, `trim_start`, `trim_end`, `lstrip`, `rstrip`, `replace`,
`replace_all`, `repeat`, `repeat_join`, `ljust`, `rjust`, `pad_left`,
`pad_right`, `zfill`, `center`, `removeprefix`, `removesuffix`, `truncate`
and `ellipsis`; each has a matching `get_<name>`.

Parameters are never banished. A method that answers with a `list of string`
returns **views** — `split`, `splitn`, `rsplit`, `split_whitespace`, `words`,
`lines`, `partition` and `chars` return a fresh `list of string` whose
elements are non-owning views into the receiver (the runtime's
`pengu_string_split` contract). The receiver must outlive the list, and
`banish parts` releases everything: banishing a view is a no-op. Copy an
element with `pengu_string_copy` when it has to outlive the receiver.

A `list of string` the caller builds by hand owns only its element buffer, so
each element it allocated must be released individually before the list.
Nothing is ever released automatically: the compiler allocates and frees only
what the program spells out (LANGUAGE.md §13.4).

## ASCII and bytes
The module is ASCII-oriented and works at the byte level: `len`, the indices,
`chars`, `bytes` and the slices count bytes, not UTF-8 code points; a
multi-byte character appears as several bytes and `char_at` or `reverse` may
split it.

## Design notes
- **No `+` for strings** (E0005): the only composition is `"{expr}"`
  interpolation; `_concat` is the module's single accumulation point.
- **Documentation-only deprecation.** The toolchain *does* support the real
  `@deprecated("Use X instead")` attribute (it emits `W0006`, and
  `--deny-deprecated` promotes it to an error), but these aliases still use the
  `## @deprecated Use X instead.` docstring convention and therefore emit no
  warning. Turning them into real attributes would also require migrating the
  internal uses (`find`/`rfind` in `std.invoke`) and removing the
  aliases from the `test` blocks, because any use would trigger the warning. It
  is planned for 1.1; the inventory with replacements and retirement versions
  lives in `docs/DEPRECATIONS.md`.
- **Functional form.** Every method has its module `weave`, which only adds the
  `s` receiver and delegates; its contract is the method documented above.
- **C bridges.** The byte-level primitives of `string` live in `antiquus`
  blocks because they need `char *`/`.len` access the language does not expose.
  `pengu fmt` keeps every raw-string body at column 0, so those bodies never
  carry indentation.
- **Internal tests without `std.ward`** (`ward` imports `scrolls`, E0004): the
  `# --- Tests ---` section uses a private harness on top of `spark.panic`.
- **`compare`** returns -1/0/1 for the common prefix and falls back to length;
  `is_space` is false for "" (legacy) while `is_blank` is true.
- **`parse_int`** delegates to `spark.parse_int` (accepts whitespace, rejects
  overflow); **`parse_float`** computes digit by digit and rejects exponents.
  Neither has a functional form: `insignia pengu_` would emit them as the
  `pengu_parse_int`/`pengu_parse_float` intrinsics.

## Migration

The old names keep working as delegating aliases.

| Old | Canonical |
|---|---|
| `calling s.to_lower` / `s.to_upper` | `calling s.lower` / `s.upper` |
| `calling s.title_case` | `calling s.title` |
| `calling s.find` / `s.rfind` | `calling s.index_of` / `s.last_index_of` |
| `calling s.count_matches` | `calling s.count` |
| `calling s.lstrip` / `s.rstrip` | `calling s.trim_start` / `calling s.trim_end` |
| `calling s.is_whitespace` | `calling s.is_space` |
| `calling s.pad_left` / `s.pad_right` | `calling s.rjust` / `calling s.ljust` |

New: `words`, `lines`, `pascal_case`, `snake_case`, `kebab_case`, `is_blank`,
`is_numeric`, `parse_int`, `parse_float`, `repeat_join`, `strip`, `splitn`,
`rsplit`, `starts_with_any`, `ends_with_any`.

---

### `pengu__find_sub`

> **pengu__find_sub**(hay: string, needle: string, from_idx: int) -> int

 --- Runtime declarations -----------------------------------------------
 `pengu__find_sub` stays in `pengu_runtime.h` as a `static inline` helper, so it
 is *declared* here rather than redefined (an `antiquus _find_sub` would emit a
 second definition and collide). This declaration must come before
 `insignia pengu_`: the insignia prefixes every later top-level name, which
 would mangle the C symbol into `pengu_pengu__find_sub` and fail to link.

### `SCROLLS_VERSION`

> **SCROLLS_VERSION** : string

 --- Module directives --------------------------------------------------

### `_char_is_space`

> **_char_is_space**(ch: string) -> bool

 True when `ch` is exactly one ASCII whitespace byte: space, tab, LF, CR, VT or FF.

 ## Motivo
 The test reads the single raw byte of the `PenguString` (`ch.len != 1` rejects
 empty and multi-byte inputs without allocating a slice per call).

 ## Memoria
 Allocates nothing. `ch` is borrowed and never freed.

### `_char_is_digit`

> **_char_is_digit**(ch: string) -> bool

 True when `ch` is exactly one ASCII decimal digit (`0`-`9`).

 ## Motivo
 A range check on the raw byte is branch-free, allocation-free and cannot be
 confused by a multi-byte slice.

 ## Memoria
 Allocates nothing. `ch` is borrowed and never freed.

### `_char_is_upper`

> **_char_is_upper**(ch: string) -> bool

 True when `ch` is exactly one ASCII uppercase letter (`A`-`Z`).

 ## Motivo
 A byte range check replaces `ord` plus comparisons and rejects non-single-byte
 inputs explicitly.

 ## Memoria
 Allocates nothing. `ch` is borrowed and never freed.

### `_char_is_lower`

> **_char_is_lower**(ch: string) -> bool

 True when `ch` is exactly one ASCII lowercase letter (`a`-`z`).

 ## Motivo
 Same raw-byte range check as `_char_is_upper`, mirrored for the lower range.

 ## Memoria
 Allocates nothing. `ch` is borrowed and never freed.

### `_char_is_alpha`

> **_char_is_alpha**(ch: string) -> bool

 True when `ch` is exactly one ASCII letter (`A`-`Z` or `a`-`z`).

 ## Motivo
 Combining both byte ranges avoids two Pengu calls per character while keeping
 the classification byte-exact.

 ## Memoria
 Allocates nothing. `ch` is borrowed and never freed.

### `_char_is_alnum`

> **_char_is_alnum**(ch: string) -> bool

 True when `ch` is exactly one ASCII letter or digit.

 ## Motivo
 One byte dispatch for the alphanumeric class, used by the identifier-style
 helpers.

 ## Memoria
 Allocates nothing. `ch` is borrowed and never freed.

### `pengu_string_contains`

> **pengu_string_contains**(a: string, b: string) -> bool

 True when substring `b` occurs anywhere in `a`.

 ## Motivo
 The search runs through `pengu__find_sub`, a binary-exact, NUL-safe `memcmp`
 scan. A Pengu loop would rebuild one-byte slices for every candidate position
 and would not be O(n*m) in C.

 ## Memoria
 Allocates nothing. Both strings are borrowed and never freed.

### `pengu_string_starts_with`

> **pengu_string_starts_with**(a: string, prefix: string) -> bool

 True when `a` begins with `prefix` (an empty prefix always matches).

 ## Motivo
 Prefix comparison is a single `memcmp` over the shared length; the length guard
 rules out reading past the end of `a`.

 ## Memoria
 Allocates nothing. Both strings are borrowed and never freed.

### `pengu_string_ends_with`

> **pengu_string_ends_with**(a: string, suffix: string) -> bool

 True when `a` ends with `suffix` (an empty suffix always matches).

 ## Motivo
 The suffix is compared in place at `a.data + a.len - suffix.len`, which needs
 pointer arithmetic over the raw buffer.

 ## Memoria
 Allocates nothing. Both strings are borrowed and never freed.

### `pengu_string_index_of`

> **pengu_string_index_of**(a: string, sub: string) -> int

 Index of the first occurrence of `sub` in `a`, or -1.

 ## Motivo
 Delegates the scan to `pengu__find_sub` and normalises the legacy edges: an
 empty `sub` matches at 0, a `sub` longer than `a` never matches.

 ## Memoria
 Allocates nothing. Both strings are borrowed and never freed.

### `pengu_string_last_index_of`

> **pengu_string_last_index_of**(a: string, sub: string) -> int

 Index of the last occurrence of `sub` in `a`, or -1.

 ## Motivo
 The backward scan compares raw bytes with `memcmp`; an empty `sub` matches at
 `a.len`, preserving the documented legacy edge.

 ## Memoria
 Allocates nothing. Both strings are borrowed and never freed.

### `pengu_string_replace`

> **pengu_string_replace**(s: string, from: string, to: string) -> string

 Copy of `s` with every non-overlapping occurrence of `from` replaced by `to`.

 ## Motivo
 The replacement needs a pre-counted pass, a single SDS allocation of the exact final
 size and `memcpy` of the untouched spans; that is raw-buffer plumbing with an
 ownership flag the language does not expose.

 ## Memoria
 Returns a freshly allocated owned `PenguString`. Release it with `banish`.
 `s`, `from` and `to` are borrowed and never freed. On allocation failure or
 overflow it returns an empty string (never `NULL`).

### `pengu_string_repeat`

> **pengu_string_repeat**(s: string, times: int) -> string

 Copy of `s` repeated `times` times.

 ## Motivo
 A single SDS allocation of `s.len * times` bytes plus one repetition loop avoids
 building an intermediate `list of string` and concatenating it in Pengu.

 ## Memoria
 Returns a freshly allocated owned `PenguString`, or an empty string when
 `times <= 0`, `s` is empty or the size overflows. Release it with `banish`.

### `pengu_string_reverse`

> **pengu_string_reverse**(s: string) -> string

 Copy of `s` with its bytes in reverse order.

 ## Motivo
 Reversing writes byte by byte into a freshly allocated buffer; a Pengu version
 would allocate one single-byte string per position.

 ## Memoria
 Returns a freshly allocated owned `PenguString`, or an empty string when `s` is
 empty. Release it with `banish`. `s` is borrowed and never freed.

### `_ascii_case`

> **_ascii_case**(s: string, mode: int) -> string

 ASCII case mapping in one allocation.

 ## Motivo
 Doing this in Pengu requires one `char_at` allocation per byte plus a
 `list of string` plus `_concat`, so a single `calling s.upper` leaked O(n)
 temporary buffers. Here the whole result is one SDS allocation.

 ## Memoria
 Returns a freshly allocated owned string (empty string view for an empty
 input, which `banish` treats as a no-op). `s` is borrowed.
 `mode`: 0 = lower, 1 = upper, 2 = swap.

### `_ascii_all`

> **_ascii_all**(s: string, kind: int) -> bool

 ASCII classification of a whole string, allocation-free.

 ## Motivo
 The `for ch in s` form allocates a one-byte owning copy per iteration; a
 predicate that only inspects bytes must not allocate at all.

 ## Memoria
 Allocates nothing. `s` is borrowed.
 `kind`: 0 = is_alpha, 1 = is_digit, 2 = is_alnum, 3 = is_space,
 4 = is_lower, 5 = is_upper, 6 = is_blank.

### `_is_palindrome`

> **_is_palindrome**(s: string) -> bool

 Byte-level palindrome test, allocation-free.

 ## Motivo
 Slicing two one-byte strings per position allocated 2*n buffers per call.

 ## Memoria
 Allocates nothing. `s` is borrowed. The empty string is a palindrome.

### `_compare_bytes`

> **_compare_bytes**(a: string, b: string) -> int

 Byte-lexicographic comparison returning exactly -1, 0 or 1.

 ## Motivo
 `ord (sv at i)` allocated two one-byte strings per compared byte.

 ## Memoria
 Allocates nothing. `a` and `b` are borrowed.

### `_is_numeric_bytes`

> **_is_numeric_bytes**(s: string) -> bool

 True when every byte is a digit with at most one dot and one leading sign.

 ## Motivo
 The `for i, ch in sv` form allocated one owning copy per byte.

 ## Memoria
 Allocates nothing. `s` is borrowed.

### `_float_from_literal`

> **_float_from_literal**(s: string) -> float

 Decimal value of a valid numeric literal, allocation-free.

 ## Motivo
 The Pengu form allocated a one-byte string per digit and one more for the
 sign test.

 ## Memoria
 Allocates nothing. `s` is borrowed; exponents are not supported.

### `_trim_ascii`

> **_trim_ascii**(s: string, mode: int) -> string

 ASCII trim returning a fresh owned string.

 ## Motivo
 The Pengu form both allocated a one-byte string per inspected byte and
 leaked the intermediate of `trim` (`trim_start` then `trim_end`).

 ## Memoria
 Returns a freshly allocated owned copy (never a view, so the caller can
 `banish` it unconditionally). `s` is borrowed.
 `mode`: 0 = both ends, 1 = start only, 2 = end only.

### `_view`

> **_view**(s: string, start: int, end: int) -> string

 ASCII view of a byte range: no allocation, no ownership.

 ## Motivo
 `split`, `chars` and friends used to allocate one owning substring per
 element, so `banish` on the returned list leaked all of them. A view is what
 the runtime's own `pengu_string_split` already returns and what `banish`
 handles correctly (a view is a no-op).

 ## Memoria
 Allocates nothing and returns a non-owning view into `s`. The receiver must
 outlive every view taken from it; `banish` on a view is a no-op.

### `_title_ascii`

> **_title_ascii**(s: string) -> string

 `string.upper()` on the first byte of every whitespace-separated word.

 ## Motivo
 One SDS allocation instead of a `list of string` plus one owning byte per
 character.

 ## Memoria
 Returns a freshly allocated owned string. `s` is borrowed.

### `_capitalize_ascii`

> **_capitalize_ascii**(s: string) -> string

 `string.upper()` on the first byte, `string.lower()` on the rest.

 ## Motivo
 One SDS allocation instead of an owning byte per character plus a list.

 ## Memoria
 Returns a freshly allocated owned string (empty view for an empty input).

### `_identifier_case`

> **_identifier_case**(s: string, mode: int) -> string

 snake_case / kebab_case / PascalCase in one allocation.

 ## Motivo
 The Pengu versions built a `list of string` of owning one-byte strings and
 then leaked the list; the word-boundary heuristic also allocated a byte per
 inspected neighbour.

 ## Memoria
 Returns a freshly allocated owned string. `s` is borrowed.
 `mode`: 0 = snake_case, 1 = kebab_case, 2 = PascalCase.

### `_replace_first`

> **_replace_first**(s: string, from: string, to: string) -> string

 Replace the first occurrence of `from` with `to`, in one allocation.

 ## Motivo
 The Pengu form built two owning substring temporaries (`head`, `tail`) and
 then an interpolated result, leaking the first two on every call.

 ## Memoria
 Returns a freshly allocated owned copy of `s` (also when `from` does not
 occur or is empty). `s`, `from` and `to` are borrowed.

### `len`

> **len**() -> int

 --- Length and iteration -------------------------------------------
 Number of bytes in the string.

 ## Parámetros
 - None: the receiver is the string to measure.

 ## Retorno
 The byte length as an `int` (`"café"` is 5, not 4). Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling "abc".len    # 3
 ```

### `is_empty`

> **is_empty**() -> bool

 True when the string has zero bytes.

 ## Parámetros
 - None: the receiver is the string to test.

 ## Retorno
 `true` for the empty string, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling "".is_empty      # true
 calling "x".is_empty     # false
 ```

### `chars`

> **chars**() -> list of string

 List with each byte as a one-character string.

 ## Parámetros
 - None: the receiver is split byte by byte.

 ## Retorno
 A new owned `list of string`; release it with `banish`. A multi-byte UTF-8
 character becomes several one-byte elements.

 ## Ejemplo
 ```pengu
 calling "ab".chars    # ["a", "b"]
 ```

### `bytes`

> **bytes**() -> list of int

 List with the numeric code of each byte.

 ## Parámetros
 - None: the receiver is read byte by byte.

 ## Retorno
 A new owned `list of int` with the byte values (`ord`); release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling "AB".bytes    # [65, 66]
 ```

### `contains`

> **contains**(sub: string) -> bool

 --- Search ---------------------------------------------------------
 True when `sub` occurs anywhere in the string.

 ## Parámetros
 - `sub`: the substring to look for; may be empty.

 ## Retorno
 `true` when `sub` is found (an empty `sub` always matches).

 ## Ejemplo
 ```pengu
 calling "abc".contains with "bc"    # true
 ```

### `starts_with`

> **starts_with**(prefix: string) -> bool

 True when the string starts with `prefix`.

 ## Parámetros
 - `prefix`: the prefix to test; an empty prefix always matches.

 ## Retorno
 `true` when the first `prefix` bytes are equal to `prefix`.

 ## Ejemplo
 ```pengu
 calling "abc".starts_with with "ab"    # true
 ```

### `starts_with_any`

> **starts_with_any**(prefixes: list of string) -> bool

 True when any of `prefixes` matches the start of the string.

 ## Parámetros
 - `prefixes`: the candidate prefixes; an empty list never matches.

 ## Retorno
 `true` at the first matching prefix; `false` when the list is empty or none
 matches. Borrows the list and every element.

 ## Ejemplo
 ```pengu
 calling "abc".starts_with_any with ["x", "ab"]    # true
 ```

### `ends_with`

> **ends_with**(suffix: string) -> bool

 True when the string ends in `suffix`.

 ## Parámetros
 - `suffix`: the suffix to test; an empty suffix always matches.

 ## Retorno
 `true` when the last `suffix` bytes are equal to `suffix`.

 ## Ejemplo
 ```pengu
 calling "abc".ends_with with "bc"    # true
 ```

### `ends_with_any`

> **ends_with_any**(suffixes: list of string) -> bool

 True when any of `suffixes` matches the end of the string.

 ## Parámetros
 - `suffixes`: the candidate suffixes; an empty list never matches.

 ## Retorno
 `true` at the first matching suffix; `false` when the list is empty or none
 matches. Borrows the list and every element.

 ## Ejemplo
 ```pengu
 calling "abc".ends_with_any with ["x", "bc"]    # true
 ```

### `index_of`

> **index_of**(sub: string) -> int

 Index of the first occurrence of `sub`, or -1.

 ## Parámetros
 - `sub`: the substring to look for; may be empty.

 ## Retorno
 The 0-based byte index, `0` for an empty `sub`, or -1 when absent.

 ## Ejemplo
 ```pengu
 calling "abracadabra".index_of with "cad"    # 4
 ```

### `last_index_of`

> **last_index_of**(sub: string) -> int

 Index of the last occurrence of `sub`, or -1.

 ## Parámetros
 - `sub`: the substring to look for; may be empty.

 ## Retorno
 The 0-based byte index of the last match, the string length for an empty
 `sub`, or -1 when absent.

 ## Ejemplo
 ```pengu
 calling "abracadabra".last_index_of with "abra"    # 7
 ```

### `find`

> **find**(sub: string) -> int

 @deprecated Use index_of instead.

 ## Parámetros
 - `sub`: the substring to look for.

 ## Retorno
 Same as `index_of`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling "abc".find with "b"    # 1
 ```

### `rfind`

> **rfind**(sub: string) -> int

 @deprecated Use last_index_of instead.

 ## Parámetros
 - `sub`: the substring to look for.

 ## Retorno
 Same as `last_index_of`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling "abca".rfind with "a"    # 3
 ```

### `count`

> **count**(sub: string) -> int

 Count the **non-overlapping** occurrences of `sub`.

 ## Parámetros
 - `sub`: the substring to count; an empty `sub` is ignored.

 ## Retorno
 The number of non-overlapping matches (`"aaaa".count with "aa"` is 2).

 ## Ejemplo
 ```pengu
 calling "abracadabra".count with "a"    # 5
 ```

### `count_matches`

> **count_matches**(sub: string) -> int

 @deprecated Use count instead.

 ## Parámetros
 - `sub`: the substring to count.

 ## Retorno
 Same as `count`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling "aaaa".count_matches with "aa"    # 2
 ```

### `get_substring`

> **get_substring**(start_pos: int, end_pos: int) -> string

 --- Slicing --------------------------------------------------------
 Substring from `start_pos` (inclusive) to `end_pos` (exclusive).

 ## Parámetros
 - `start_pos`: first byte index to keep.
 - `end_pos`: byte index to stop at.

 ## Retorno
 A new owned string; release it with `banish`. The runtime clamps
 out-of-range indices, and `start_pos == end_pos` yields "".

 ## Ejemplo
 ```pengu
 calling "abcdef".substring with 1, 4    # "bcd"
 ```

### `get_char_at`

> **get_char_at**(idx: int) -> string

 The byte at `idx` as a one-character string.

 ## Parámetros
 - `idx`: the byte position to read.

 ## Retorno
 A new owned one-byte string (may split a UTF-8 character); release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling "abc".char_at with 1    # "b"
 ```

### `get_reverse`

> **get_reverse**() -> string

 Copy of the string with its bytes in reverse order.

 ## Parámetros
 - None: the receiver is reversed byte by byte.

 ## Retorno
 A new owned string; release it with `banish`. "" stays "".

 ## Ejemplo
 ```pengu
 calling "pengu".reverse    # "ugnep"
 ```

### `get_lower`

> **get_lower**() -> string

 --- Case -----------------------------------------------------------
 Copy with the ASCII letters A-Z lowered.

 ## Parámetros
 - None: the receiver is transformed byte by byte.

 ## Retorno
 A new owned string; non-ASCII bytes are copied unchanged.

 ## Ejemplo
 ```pengu
 calling "Hello!".lower    # "hello!"
 ```

### `get_upper`

> **get_upper**() -> string

 Copy with the ASCII letters a-z uppercased.

 ## Parámetros
 - None: the receiver is transformed byte by byte.

 ## Retorno
 A new owned string; non-ASCII bytes are copied unchanged.

 ## Ejemplo
 ```pengu
 calling "abc".upper    # "ABC"
 ```

### `get_to_lower`

> **get_to_lower**() -> string

 @deprecated Use lower instead.

 ## Parámetros
 - None: the receiver is transformed.

 ## Retorno
 Same as `lower`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling "AbC".to_lower    # "abc"
 ```

### `get_to_upper`

> **get_to_upper**() -> string

 @deprecated Use upper instead.

 ## Parámetros
 - None: the receiver is transformed.

 ## Retorno
 Same as `upper`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling "AbC".to_upper    # "ABC"
 ```

### `get_capitalize`

> **get_capitalize**() -> string

 Copy with the first letter uppercased and the rest lowercased.

 ## Parámetros
 - None: the receiver is capitalized as a whole.

 ## Retorno
 A new owned string; "" stays "" and a leading non-letter is untouched.

 ## Ejemplo
 ```pengu
 calling "hELLO".capitalize    # "Hello"
 ```

### `get_title`

> **get_title**() -> string

 Copy with the initial of every word uppercased and the rest lowercased.

 ## Parámetros
 - None: the receiver is title-cased word by word.

 ## Retorno
 A new owned string; the original spacing is preserved (a space byte starts
 a new word).

 ## Ejemplo
 ```pengu
 calling "hello world".title    # "Hello World"
 ```

### `get_title_case`

> **get_title_case**() -> string

 @deprecated Use title instead.

 ## Parámetros
 - None: the receiver is title-cased.

 ## Retorno
 Same as `title`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling "hello world".title_case    # "Hello World"
 ```

### `get_swap_case`

> **get_swap_case**() -> string

 Copy with every ASCII letter case-swapped.

 ## Parámetros
 - None: the receiver is transformed byte by byte.

 ## Retorno
 A new owned string; non-letters keep their byte.

 ## Ejemplo
 ```pengu
 calling "a1B".swap_case    # "A1b"
 ```

### `get_to_snake_case`

> **get_to_snake_case**() -> string

 Copy converted to `snake_case`.

 ## Parámetros
 - None: the receiver is split on `camelCase` boundaries and on the ` `,
   `-` and `_` separators.

 ## Retorno
 A new owned string in `snake_case`; repeated separators collapse and ""
 stays "".

 ## Ejemplo
 ```pengu
 calling "HTTPServer".to_snake_case    # "http_server"
 ```

### `get_to_kebab_case`

> **get_to_kebab_case**() -> string

 Copy converted to `kebab-case`.

 ## Parámetros
 - None: the receiver is run through `to_snake_case` first.

 ## Retorno
 A new owned string with `_` replaced by `-`.

 ## Ejemplo
 ```pengu
 calling "HelloWorld".to_kebab_case    # "hello-world"
 ```

### `get_snake_case`

> **get_snake_case**() -> string

 Short form of `to_snake_case`.

 ## Parámetros
 - None: the receiver is converted.

 ## Retorno
 The same string `to_snake_case` would return.

 ## Ejemplo
 ```pengu
 calling "helloWorld".snake_case    # "hello_world"
 ```

### `get_kebab_case`

> **get_kebab_case**() -> string

 Short form of `to_kebab_case`.

 ## Parámetros
 - None: the receiver is converted.

 ## Retorno
 The same string `to_kebab_case` would return.

 ## Ejemplo
 ```pengu
 calling "helloWorld".kebab_case    # "hello-world"
 ```

### `get_pascal_case`

> **get_pascal_case**() -> string

 Copy converted to `PascalCase`: every `snake_case` word capitalized.

 ## Parámetros
 - None: the receiver is run through `snake_case` first.

 ## Retorno
 A new owned string; "" stays "".

 ## Ejemplo
 ```pengu
 calling "hello_world".pascal_case    # "HelloWorld"
 ```

### `is_alpha`

> **is_alpha**() -> bool

 True when every byte is an ASCII letter and there is at least one.

 ## Parámetros
 - None: the receiver is classified.

 ## Retorno
 `false` for "" and `true` only for `[A-Za-z]+`.

 ## Ejemplo
 ```pengu
 calling "aB".is_alpha    # true
 calling "a1".is_alpha    # false
 ```

### `is_digit`

> **is_digit**() -> bool

 True when every byte is an ASCII digit and there is at least one.

 ## Parámetros
 - None: the receiver is classified.

 ## Retorno
 `false` for "" and `true` only for `[0-9]+`.

 ## Ejemplo
 ```pengu
 calling "123".is_digit    # true
 ```

### `is_alnum`

> **is_alnum**() -> bool

 True when every byte is an ASCII letter or digit and there is at least one.

 ## Parámetros
 - None: the receiver is classified.

 ## Retorno
 `false` for "" and `true` only for `[A-Za-z0-9]+`.

 ## Ejemplo
 ```pengu
 calling "a1".is_alnum    # true
 ```

### `is_lower`

> **is_lower**() -> bool

 True when there is no uppercase ASCII letter and at least one lowercase.

 ## Parámetros
 - None: the receiver is classified.

 ## Retorno
 `false` for `"A1"` and `"1"`; `true` for `"a1"`.

 ## Ejemplo
 ```pengu
 calling "a1".is_lower    # true
 ```

### `is_upper`

> **is_upper**() -> bool

 True when there is no lowercase ASCII letter and at least one uppercase.

 ## Parámetros
 - None: the receiver is classified.

 ## Retorno
 `false` for `"a1"` and `"1"`; `true` for `"A1"`.

 ## Ejemplo
 ```pengu
 calling "A1".is_upper    # true
 ```

### `is_palindrome`

> **is_palindrome**() -> bool

 True when the string reads the same forwards and backwards.

 ## Parámetros
 - None: the receiver is compared with its reverse.

 ## Retorno
 `true` for byte palindromes; the empty string and single bytes are
 palindromes.

 ## Ejemplo
 ```pengu
 calling "racecar".is_palindrome    # true
 ```

### `get_trim`

> **get_trim**() -> string

 --- Whitespace -----------------------------------------------------
 Copy without ASCII whitespace at either end.

 ## Parámetros
 - None: the receiver is trimmed on both sides.

 ## Retorno
 A new owned string; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling "  x  ".trim    # "x"
 ```

### `get_strip`

> **get_strip**() -> string

 Alias of `trim` (both ends).

 ## Parámetros
 - None: the receiver is trimmed on both sides.

 ## Retorno
 A new owned string; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling "  x  ".strip    # "x"
 ```

### `get_trim_start`

> **get_trim_start**() -> string

 Copy without ASCII whitespace at the start.

 ## Parámetros
 - None: only the leading whitespace is removed.

 ## Retorno
 A new owned string; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling "  x  ".trim_start    # "x  "
 ```

### `get_trim_end`

> **get_trim_end**() -> string

 Copy without ASCII whitespace at the end.

 ## Parámetros
 - None: only the trailing whitespace is removed.

 ## Retorno
 A new owned string; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling "  x  ".trim_end    # "  x"
 ```

### `get_lstrip`

> **get_lstrip**() -> string

 @deprecated Use trim_start instead.

 ## Parámetros
 - None: only the leading whitespace is removed.

 ## Retorno
 Same as `trim_start`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling " x".lstrip    # "x"
 ```

### `get_rstrip`

> **get_rstrip**() -> string

 @deprecated Use trim_end instead.

 ## Parámetros
 - None: only the trailing whitespace is removed.

 ## Retorno
 Same as `trim_end`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling "x ".rstrip    # "x"
 ```

### `is_space`

> **is_space**() -> bool

 True when the string is non-empty and every byte is ASCII whitespace.

 ## Parámetros
 - None: the receiver is classified.

 ## Retorno
 `false` for "" (legacy; see `is_blank`), `true` for `" \t"`.

 ## Ejemplo
 ```pengu
 calling "   ".is_space    # true
 ```

### `is_whitespace`

> **is_whitespace**() -> bool

 @deprecated Use is_space instead.

 ## Parámetros
 - None: the receiver is classified.

 ## Retorno
 Same as `is_space`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling "\t\n".is_whitespace    # true
 ```

### `is_blank`

> **is_blank**() -> bool

 True when the string is empty or every byte is ASCII whitespace.

 ## Parámetros
 - None: the receiver is classified.

 ## Retorno
 `true` for "" and for strings of only whitespace; `false` otherwise.

 ## Ejemplo
 ```pengu
 calling "".is_blank    # true
 ```

### `split_whitespace`

> **split_whitespace**() -> list of string

 List of words separated by runs of ASCII whitespace.

 ## Parámetros
 - None: the receiver is split on any run of whitespace.

 ## Retorno
 A new owned `list of string`; release it with `banish`. Leading and
 trailing whitespace is ignored, and "" or only whitespace yields [].

 ## Ejemplo
 ```pengu
 calling "  a  b ".split_whitespace    # ["a", "b"]
 ```

### `words`

> **words**() -> list of string

 Short name of `split_whitespace`.

 ## Parámetros
 - None: the receiver is split on whitespace runs.

 ## Retorno
 The same list `split_whitespace` would return.

 ## Ejemplo
 ```pengu
 calling "a\tb\nc".words    # ["a", "b", "c"]
 ```

### `split_lines`

> **split_lines**() -> list of string

 List of lines separated by `\n`.

 ## Parámetros
 - None: the receiver is split on LF, keeping any CR as a byte.

 ## Retorno
 A new owned `list of string`; "" yields [] and a trailing `\n` adds one
 empty line.

 ## Ejemplo
 ```pengu
 calling "a\r\nb".split_lines    # ["a\r", "b"]
 ```

### `line_count`

> **line_count**() -> int

 Number of `\n`-separated lines.

 ## Parámetros
 - None: the receiver is measured.

 ## Retorno
 0 for "" and 1 for a string without `\n`.

 ## Ejemplo
 ```pengu
 calling "a\nb".line_count    # 2
 ```

### `word_count`

> **word_count**() -> int

 Number of whitespace-separated words.

 ## Parámetros
 - None: the receiver is measured.

 ## Retorno
 The element count of `words`.

 ## Ejemplo
 ```pengu
 calling "a b".word_count    # 2
 ```

### `lines`

> **lines**() -> list of string

 List of lines with the trailing `\r` of each line removed (CRLF-safe).

 ## Parámetros
 - None: the receiver is split on `\n` and each line is suffix-trimmed.

 ## Retorno
 A new owned `list of string`; "" yields [] and a trailing `\n` adds one
 empty line.

 ## Ejemplo
 ```pengu
 calling "a\r\nb".lines    # ["a", "b"]
 ```

### `get_replace`

> **get_replace**(from_str: string, to_str: string) -> string

 --- Replacing and splitting ----------------------------------------
 Copy with the first occurrence of `from_str` replaced by `to_str`.

 ## Parámetros
 - `from_str`: the text to replace; may be empty.
 - `to_str`: the replacement text.

 ## Retorno
 A new owned string; release it with `banish`. An empty `from_str` inserts
 `to_str` at the start (legacy behaviour).

 ## Ejemplo
 ```pengu
 calling "cat, cat".replace with "cat", "dog"    # "dog, cat"
 ```

### `get_replace_all`

> **get_replace_all**(from_str: string, to_str: string) -> string

 Copy with **every** non-overlapping occurrence of `from_str` replaced.

 ## Parámetros
 - `from_str`: the text to replace; an empty `from_str` changes nothing.
 - `to_str`: the replacement text.

 ## Retorno
 A new owned string; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling "cat, cat".replace_all with "cat", "dog"    # "dog, dog"
 ```

### `split`

> **split**(delim: string) -> list of string

 Split on every occurrence of `delim`.

 ## Parámetros
 - `delim`: the separator; an empty `delim` keeps the whole string.

 ## Retorno
 A new owned `list of string`; release it with `banish`. An absent
 delimiter yields one element.

 ## Ejemplo
 ```pengu
 calling "a,,b".split with ","    # ["a", "", "b"]
 ```

### `splitn`

> **splitn**(delim: string, n: int) -> list of string

 Split into **at most** `n` parts on `delim`.

 ## Parámetros
 - `delim`: the separator; an empty `delim` keeps the whole string.
 - `n`: maximum number of parts; `n <= 0` performs no split at all.

 ## Retorno
 A new owned `list of string`; release it with `banish`. The last element
 keeps the remaining delimiters.

 ## Ejemplo
 ```pengu
 calling "a,b,c".splitn with ",", 2    # ["a", "b,c"]
 ```

### `rsplit`

> **rsplit**(delim: string) -> list of string

 Split on `delim` into the same parts `split` produces.

 ## Parámetros
 - `delim`: the separator; an empty `delim` keeps the whole string.

 ## Retorno
 A new owned `list of string` in left-to-right order; release it with
 `banish`. Without a part limit the result is identical to `split`'s; the
 name exists so code that reads a right-hand variant stays expressive.

 ## Ejemplo
 ```pengu
 calling "a:b:c".rsplit with ":"    # ["a", "b", "c"]
 ```

### `partition`

> **partition**(sep: string) -> list of string

 Split on the **first** occurrence of `sep`: `[before, sep, after]`.

 ## Parámetros
 - `sep`: the separator; when absent or empty no split happens.

 ## Retorno
 A new owned 3-element `list of string`; release it with `banish`. When
 `sep` is missing it returns `[self, "", ""]`.

 ## Ejemplo
 ```pengu
 calling "a=b=c".partition with "="    # ["a", "=", "b=c"]
 ```

### `get_repeat`

> **get_repeat**(count: int) -> string

 Copy repeated `count` times.

 ## Parámetros
 - `count`: the number of copies.

 ## Retorno
 A new owned string; release it with `banish`. `count <= 0` or an empty
 receiver yields "".

 ## Ejemplo
 ```pengu
 calling "ha".repeat with 3    # "hahaha"
 ```

### `get_repeat_join`

> **get_repeat_join**(count: int, sep: string) -> string

 Copy repeated `count` times and joined with `sep`.

 ## Parámetros
 - `count`: the number of copies.
 - `sep`: the text placed between copies.

 ## Retorno
 A new owned string; release it with `banish`. `count <= 0` or an empty
 receiver yields "".

 ## Ejemplo
 ```pengu
 calling "ab".repeat_join with 3, ", "    # "ab, ab, ab"
 ```

### `get_ljust`

> **get_ljust**(width: int, pad_char: string) -> string

 --- Alignment ------------------------------------------------------
 Left-align in `width`, padding on the right with `pad_char`.

 ## Parámetros
 - `width`: the target byte width.
 - `pad_char`: the padding text (default `" "`); empty means no padding.

 ## Retorno
 A new owned string; release it with `banish`. Values that already fit are
 returned unchanged and the result is truncated to `width`.

 ## Ejemplo
 ```pengu
 calling "ab".ljust with 4, "."    # "ab.."
 ```

### `get_rjust`

> **get_rjust**(width: int, pad_char: string) -> string

 Right-align in `width`, padding on the left with `pad_char`.

 ## Parámetros
 - `width`: the target byte width.
 - `pad_char`: the padding text (default `" "`); empty means no padding.

 ## Retorno
 A new owned string; release it with `banish`. Values that already fit are
 returned unchanged and the result is truncated to `width`.

 ## Ejemplo
 ```pengu
 calling "42".rjust with 5, "0"    # "00042"
 ```

### `get_pad_left`

> **get_pad_left**(width: int, pad_char: string) -> string

 @deprecated Use rjust instead.

 ## Parámetros
 - `width`: the target byte width.
 - `pad_char`: the padding text (default `" "`).

 ## Retorno
 Same as `rjust`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling "42".pad_left with 5, "0"    # "00042"
 ```

### `get_pad_right`

> **get_pad_right**(width: int, pad_char: string) -> string

 @deprecated Use ljust instead.

 ## Parámetros
 - `width`: the target byte width.
 - `pad_char`: the padding text (default `" "`).

 ## Retorno
 Same as `ljust`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 calling "ab".pad_right with 4, "."    # "ab.."
 ```

### `get_zfill`

> **get_zfill**(width: int) -> string

 Zero-pad on the left up to `width`, preserving a leading sign.

 ## Parámetros
 - `width`: the target byte width.

 ## Retorno
 A new owned string; release it with `banish`. `-`/`+` stays first and a
 value that already fits is returned unchanged.

 ## Ejemplo
 ```pengu
 calling "-42".zfill with 6    # "-00042"
 ```

### `get_center`

> **get_center**(width: int, pad_char: string) -> string

 Center in a field of `width`, padding both sides with `pad_char`.

 ## Parámetros
 - `width`: the target byte width.
 - `pad_char`: the padding text (default `" "`); empty means no padding.

 ## Retorno
 A new owned string; release it with `banish`. With an odd amount of
 padding the left side gets the smaller half (Python's rule).

 ## Ejemplo
 ```pengu
 calling "ab".center with 5, "-"    # "-ab--"
 ```

### `get_removeprefix`

> **get_removeprefix**(prefix: string) -> string

 --- Prefixes and suffixes ------------------------------------------
 Copy with `prefix` removed from the start when present.

 ## Parámetros
 - `prefix`: the prefix to strip; empty leaves the string unchanged.

 ## Retorno
 A new owned string; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling "Hello".removeprefix with "He"    # "llo"
 ```

### `get_removesuffix`

> **get_removesuffix**(suffix: string) -> string

 Copy with `suffix` removed from the end when present.

 ## Parámetros
 - `suffix`: the suffix to strip; empty leaves the string unchanged.

 ## Retorno
 A new owned string; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling "Hello".removesuffix with "lo"    # "Hel"
 ```

### `compare`

> **compare**(other: string) -> int

 --- Comparison -----------------------------------------------------
 Compare byte by byte against `other` and return -1, 0 or 1.

 ## Parámetros
 - `other`: the string to compare against.

 ## Retorno
 -1 when `self` sorts first, 1 when it sorts last, 0 when equal. Ties on the
 common prefix fall back to length. Comparison is byte-ordered, so uppercase
 sorts before lowercase.

 ## Ejemplo
 ```pengu
 calling "apple".compare with "banana"    # -1
 ```

### `get_truncate`

> **get_truncate**(max_len: int, suffix: string) -> string

 --- Truncation -----------------------------------------------------
 Cut to `max_len` bytes, appending `suffix` when anything was cut.

 ## Parámetros
 - `max_len`: the maximum result length in bytes.
 - `suffix`: the marker appended after a cut (e.g. `"..."`).

 ## Retorno
 A new owned string; `max_len <= len(suffix)` cuts without the marker and
 `max_len <= 0` yields "".

 ## Ejemplo
 ```pengu
 calling "Hello, World!".truncate with 10, "..."    # "Hello, ..."
 ```

### `get_ellipsis`

> **get_ellipsis**(max_len: int) -> string

 Cut to `max_len` bytes, appending "..." when anything was cut.

 ## Parámetros
 - `max_len`: the maximum result length in bytes.

 ## Retorno
 A new owned string; the short form of `truncate` with `"..."`.

 ## Ejemplo
 ```pengu
 calling "abcdef".ellipsis with 4    # "a..."
 ```

### `parse_int`

> **parse_int**() -> maybe int

 --- Parsing --------------------------------------------------------
 Interpret the string as an integer (optional whitespace and sign).

 ## Parámetros
 - None: the receiver is parsed in base 10.

 ## Retorno
 `some value`, or `none` for garbage or overflow. The boxed payload lives in
 a heap `maybe`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling " 42 ".parse_int    # some 42
 ```

### `is_numeric`

> **is_numeric**() -> bool

 True when the string is an exact numeric literal: optional sign and `.`.

 ## Parámetros
 - None: the receiver is validated.

 ## Retorno
 `true` for `[+-]?digits[.digits]?` with at least one digit; `false` for
 whitespace, exponents or repeated dots.

 ## Ejemplo
 ```pengu
 calling "-3.5".is_numeric    # true
 ```

### `parse_float`

> **parse_float**() -> maybe float

 Interpret the string as a decimal (optional whitespace, no exponents).

 ## Parámetros
 - None: the receiver is trimmed and then validated by `is_numeric`.

 ## Retorno
 `some value`, or `none` when `is_numeric` rejects it. The boxed payload
 lives in a heap `maybe`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling "3.5".parse_float    # some 3.5
 ```

### `substring`

> **substring**(start_pos: int, end_pos: int) -> void

 ------------------------------------------------------------------
 In-place mutating forms.

 Each one computes the new text with the pure 'get_<name>' form, frees
 the buffer the receiver used to own, and installs the new one.  The
 order matters: the new text is read from the OLD buffer, so it must be
 computed before 'banish old' releases it.
 ------------------------------------------------------------------
 In-place form of `get_substring`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_substring` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.substring with 0, 0
 ```

### `char_at`

> **char_at**(idx: int) -> void

 In-place form of `get_char_at`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_char_at` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.char_at with 0
 ```

### `reverse`

> **reverse**() -> void

 In-place form of `get_reverse`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_reverse` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.reverse
 ```

### `lower`

> **lower**() -> void

 In-place form of `get_lower`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_lower` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.lower
 ```

### `upper`

> **upper**() -> void

 In-place form of `get_upper`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_upper` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.upper
 ```

### `to_lower`

> **to_lower**() -> void

 In-place form of `get_to_lower`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_to_lower` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.to_lower
 ```

### `to_upper`

> **to_upper**() -> void

 In-place form of `get_to_upper`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_to_upper` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.to_upper
 ```

### `capitalize`

> **capitalize**() -> void

 In-place form of `get_capitalize`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_capitalize` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.capitalize
 ```

### `title`

> **title**() -> void

 In-place form of `get_title`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_title` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.title
 ```

### `title_case`

> **title_case**() -> void

 In-place form of `get_title_case`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_title_case` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.title_case
 ```

### `swap_case`

> **swap_case**() -> void

 In-place form of `get_swap_case`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_swap_case` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.swap_case
 ```

### `to_snake_case`

> **to_snake_case**() -> void

 In-place form of `get_to_snake_case`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_to_snake_case` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.to_snake_case
 ```

### `to_kebab_case`

> **to_kebab_case**() -> void

 In-place form of `get_to_kebab_case`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_to_kebab_case` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.to_kebab_case
 ```

### `snake_case`

> **snake_case**() -> void

 In-place form of `get_snake_case`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_snake_case` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.snake_case
 ```

### `kebab_case`

> **kebab_case**() -> void

 In-place form of `get_kebab_case`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_kebab_case` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.kebab_case
 ```

### `pascal_case`

> **pascal_case**() -> void

 In-place form of `get_pascal_case`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_pascal_case` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.pascal_case
 ```

### `trim`

> **trim**() -> void

 In-place form of `get_trim`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_trim` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.trim
 ```

### `strip`

> **strip**() -> void

 In-place form of `get_strip`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_strip` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.strip
 ```

### `trim_start`

> **trim_start**() -> void

 In-place form of `get_trim_start`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_trim_start` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.trim_start
 ```

### `trim_end`

> **trim_end**() -> void

 In-place form of `get_trim_end`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_trim_end` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.trim_end
 ```

### `lstrip`

> **lstrip**() -> void

 In-place form of `get_lstrip`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_lstrip` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.lstrip
 ```

### `rstrip`

> **rstrip**() -> void

 In-place form of `get_rstrip`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_rstrip` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.rstrip
 ```

### `replace`

> **replace**(from_str: string, to_str: string) -> void

 In-place form of `get_replace`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_replace` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.replace with "-", "-"
 ```

### `replace_all`

> **replace_all**(from_str: string, to_str: string) -> void

 In-place form of `get_replace_all`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_replace_all` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.replace_all with "-", "-"
 ```

### `repeat`

> **repeat**(count: int) -> void

 In-place form of `get_repeat`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_repeat` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.repeat with 0
 ```

### `repeat_join`

> **repeat_join**(count: int, sep: string) -> void

 In-place form of `get_repeat_join`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_repeat_join` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.repeat_join with 0, "-"
 ```

### `ljust`

> **ljust**(width: int, pad_char: string) -> void

 In-place form of `get_ljust`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_ljust` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.ljust with 0
 ```

### `rjust`

> **rjust**(width: int, pad_char: string) -> void

 In-place form of `get_rjust`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_rjust` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.rjust with 0
 ```

### `pad_left`

> **pad_left**(width: int, pad_char: string) -> void

 In-place form of `get_pad_left`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_pad_left` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.pad_left with 0
 ```

### `pad_right`

> **pad_right**(width: int, pad_char: string) -> void

 In-place form of `get_pad_right`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_pad_right` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.pad_right with 0
 ```

### `zfill`

> **zfill**(width: int) -> void

 In-place form of `get_zfill`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_zfill` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.zfill with 0
 ```

### `center`

> **center**(width: int, pad_char: string) -> void

 In-place form of `get_center`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_center` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.center with 0
 ```

### `removeprefix`

> **removeprefix**(prefix: string) -> void

 In-place form of `get_removeprefix`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_removeprefix` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.removeprefix with "-"
 ```

### `removesuffix`

> **removesuffix**(suffix: string) -> void

 In-place form of `get_removesuffix`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_removesuffix` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.removesuffix with "-"
 ```

### `truncate`

> **truncate**(max_len: int, suffix: string) -> void

 In-place form of `get_truncate`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_truncate` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.truncate with 0, "-"
 ```

### `ellipsis`

> **ellipsis**(max_len: int) -> void

 In-place form of `get_ellipsis`: computes the new text and installs it
 in the receiver, releasing the buffer it replaces.

 ## Retorno
 Nothing; the receiver is rewritten. Use `get_ellipsis` for the pure
 form that returns a new `string`.

 ## Memoria
 The old buffer is released; nothing is left for the caller to
 banish.

 ## Ejemplo
 ```pengu
 var s as string is "abc"
 calling s.ellipsis with 0
 ```

### `join`

> **join**(parts: list of string, sep: string) -> string

 Join the elements of `parts` with `sep` between them.

 ## Parámetros
 - `parts`: the pieces to join; an empty list yields "".
 - `sep`: the text placed between pieces.

 ## Retorno
 A new owned string; release it with `banish`. The empty pieces are preserved
 (`["", "x", ""]` joined with `"|"` is `"|x|"`).

 ## Ejemplo
 ```pengu
 calling scrolls.join with ["a", "b"], "-"    # "a-b"
 ```

### `_join_parts`

> **_join_parts**(parts: list of string, sep: string) -> string

 --- Private helpers ----------------------------------------------------
 Join `parts` with `sep` between elements (the real body of `join`).

 ## Parámetros
 - `parts`: the pieces to join.
 - `sep`: the text between pieces.

 ## Retorno
 A new owned string; the caller releases it with `banish`.

### `_concat`

> **_concat**(parts: list of string) -> string

 The module's single string accumulation point: concatenate `parts` as they are.

 ## Parámetros
 - `parts`: the pieces to concatenate, in order.

 ## Retorno
 A new owned string; the caller releases it with `banish`.

### `_lower_char`

> **_lower_char**(ch: string) -> string

 Copy of `ch` lowercased when it is an ASCII uppercase letter.

 ## Parámetros
 - `ch`: the one-byte string to transform.

 ## Retorno
 A new owned string; the caller releases it with `banish`.

### `_upper_char`

> **_upper_char**(ch: string) -> string

 Copy of `ch` uppercased when it is an ASCII lowercase letter.

 ## Parámetros
 - `ch`: the one-byte string to transform.

 ## Retorno
 A new owned string; the caller releases it with `banish`.

### `_swap_char`

> **_swap_char**(ch: string) -> string

 Copy of `ch` with its ASCII case swapped.

 ## Parámetros
 - `ch`: the one-byte string to transform.

 ## Retorno
 A new owned string; the caller releases it with `banish`.

### `_pad_left`

> **_pad_left**(s: string, count: int, pad_char: string) -> string

 Copy of `s` with `count` copies of `pad_char` in front.

 ## Parámetros
 - `s`: the base string.
 - `count`: how many copies of `pad_char` to prepend.
 - `pad_char`: the padding text.

 ## Retorno
 A new owned string; the caller releases it with `banish`.

### `_pad_right`

> **_pad_right**(s: string, count: int, pad_char: string) -> string

 Copy of `s` with `count` copies of `pad_char` behind.

 ## Parámetros
 - `s`: the base string.
 - `count`: how many copies of `pad_char` to append.
 - `pad_char`: the padding text.

 ## Retorno
 A new owned string; the caller releases it with `banish`.

### `_expect`

> **_expect**(cond: bool, label: string) -> void

 Private test harness: panic with `label` when `cond` is false.

 ## Parámetros
 - `cond`: the condition that must hold.
 - `label`: the message reported on failure.

 ## Retorno
 Nothing; it panics through `spark.panic` on failure.

### `_expect_eq_int`

> **_expect_eq_int**(actual: int, expected: int, label: string) -> void

 Private test harness: integer equality.

 ## Parámetros
 - `actual`: the observed value.
 - `expected`: the required value.
 - `label`: the message reported on failure.

 ## Retorno
 Nothing; it panics through `spark.panic` on mismatch.

### `_expect_eq_string`

> **_expect_eq_string**(actual: string, expected: string, label: string) -> void

 Private test harness: string equality.

 ## Parámetros
 - `actual`: the observed value.
 - `expected`: the required value.
 - `label`: the message reported on failure.

 ## Retorno
 Nothing; it panics through `spark.panic` on mismatch.

### `_expect_eq_bool`

> **_expect_eq_bool**(actual: bool, expected: bool, label: string) -> void

 Private test harness: boolean equality.

 ## Parámetros
 - `actual`: the observed value.
 - `expected`: the required value.
 - `label`: the message reported on failure.

 ## Retorno
 Nothing; it panics through `spark.panic` on mismatch.

### `"len counts bytes, also in UTF-8"`

> test "len counts bytes, also in UTF-8"

 Length and iteration

### `"is_empty distinguishes the empty string"`

> test "is_empty distinguishes the empty string"

_Undocumented._

### `"chars returns a one-byte string per element"`

> test "chars returns a one-byte string per element"

_Undocumented._

### `"bytes returns the ASCII codes"`

> test "bytes returns the ASCII codes"

_Undocumented._

### `"contains finds and discards substrings"`

> test "contains finds and discards substrings"

 Search

### `"starts_with accepts the empty prefix"`

> test "starts_with accepts the empty prefix"

_Undocumented._

### `"ends_with recognises suffixes"`

> test "ends_with recognises suffixes"

_Undocumented._

### `"index_of returns the first position"`

> test "index_of returns the first position"

_Undocumented._

### `"index_of returns -1 when it does not find"`

> test "index_of returns -1 when it does not find"

_Undocumented._

### `"last_index_of returns the last position"`

> test "last_index_of returns the last position"

_Undocumented._

### `"last_index_of with an empty sub returns the length"`

> test "last_index_of with an empty sub returns the length"

_Undocumented._

### `"count counts non-overlapping occurrences"`

> test "count counts non-overlapping occurrences"

_Undocumented._

### `"count ignores the empty sub and the longer sub"`

> test "count ignores the empty sub and the longer sub"

_Undocumented._

### `"find, rfind and count_matches still work"`

> test "find, rfind and count_matches still work"

_Undocumented._

### `"functional query forms"`

> test "functional query forms"

_Undocumented._

### `"functional position and count forms"`

> test "functional position and count forms"

_Undocumented._

### `"substring cuts the requested range"`

> test "substring cuts the requested range"

 Slicing

### `"char_at returns one byte as a string"`

> test "char_at returns one byte as a string"

_Undocumented._

### `"reverse flips the byte order"`

> test "reverse flips the byte order"

_Undocumented._

### `"reverse of the empty string is empty"`

> test "reverse of the empty string is empty"

_Undocumented._

### `"lower converts A-Z and leaves the rest alone"`

> test "lower converts A-Z and leaves the rest alone"

 Case

### `"upper converts a-z to uppercase"`

> test "upper converts a-z to uppercase"

_Undocumented._

### `"to_lower and to_upper still work"`

> test "to_lower and to_upper still work"

_Undocumented._

### `"lower leaves UTF-8 bytes untouched"`

> test "lower leaves UTF-8 bytes untouched"

_Undocumented._

### `"capitalize keeps only the first letter uppercase"`

> test "capitalize keeps only the first letter uppercase"

_Undocumented._

### `"capitalize of the empty string is empty"`

> test "capitalize of the empty string is empty"

_Undocumented._

### `"title capitalizes the initial of every word"`

> test "title capitalizes the initial of every word"

_Undocumented._

### `"title preserves the original spacing"`

> test "title preserves the original spacing"

_Undocumented._

### `"title_case still works"`

> test "title_case still works"

_Undocumented._

### `"swap_case flips the case of every letter"`

> test "swap_case flips the case of every letter"

_Undocumented._

### `"to_snake_case splits camelCase and PascalCase"`

> test "to_snake_case splits camelCase and PascalCase"

_Undocumented._

### `"to_snake_case normalises separators"`

> test "to_snake_case normalises separators"

_Undocumented._

### `"to_kebab_case uses dashes"`

> test "to_kebab_case uses dashes"

_Undocumented._

### `"snake_case and kebab_case are short forms"`

> test "snake_case and kebab_case are short forms"

_Undocumented._

### `"pascal_case capitalizes every word"`

> test "pascal_case capitalizes every word"

_Undocumented._

### `"is_alpha demands ASCII letters only"`

> test "is_alpha demands ASCII letters only"

_Undocumented._

### `"is_digit demands ASCII digits only"`

> test "is_digit demands ASCII digits only"

_Undocumented._

### `"is_alnum accepts letters and digits"`

> test "is_alnum accepts letters and digits"

_Undocumented._

### `"is_lower and is_upper ignore non-alphabetic bytes"`

> test "is_lower and is_upper ignore non-alphabetic bytes"

_Undocumented._

### `"is_palindrome detects palindromes"`

> test "is_palindrome detects palindromes"

_Undocumented._

### `"functional case forms"`

> test "functional case forms"

_Undocumented._

### `"functional style-conversion forms"`

> test "functional style-conversion forms"

_Undocumented._

### `"functional legacy case forms"`

> test "functional legacy case forms"

_Undocumented._

### `"trim removes ASCII whitespace from both ends"`

> test "trim removes ASCII whitespace from both ends"

 Whitespace

### `"strip is an alias of trim"`

> test "strip is an alias of trim"

_Undocumented._

### `"trim_start removes only the leading side"`

> test "trim_start removes only the leading side"

_Undocumented._

### `"trim_end removes only the trailing side"`

> test "trim_end removes only the trailing side"

_Undocumented._

### `"lstrip and rstrip still work"`

> test "lstrip and rstrip still work"

_Undocumented._

### `"is_space is false for the empty string"`

> test "is_space is false for the empty string"

_Undocumented._

### `"is_whitespace still works"`

> test "is_whitespace still works"

_Undocumented._

### `"is_blank is true for empty or whitespace-only"`

> test "is_blank is true for empty or whitespace-only"

_Undocumented._

### `"split_whitespace ignores repeated spaces"`

> test "split_whitespace ignores repeated spaces"

_Undocumented._

### `"words is the short form of split_whitespace"`

> test "words is the short form of split_whitespace"

_Undocumented._

### `"split_lines splits on LF and keeps the CR"`

> test "split_lines splits on LF and keeps the CR"

_Undocumented._

### `"lines drops the trailing CR of every line"`

> test "lines drops the trailing CR of every line"

_Undocumented._

### `"line_count counts LF-separated lines"`

> test "line_count counts LF-separated lines"

_Undocumented._

### `"word_count counts whitespace-separated words"`

> test "word_count counts whitespace-separated words"

_Undocumented._

### `"functional whitespace forms"`

> test "functional whitespace forms"

_Undocumented._

### `"functional whitespace-splitting forms"`

> test "functional whitespace-splitting forms"

_Undocumented._

### `"functional line and word count forms"`

> test "functional line and word count forms"

_Undocumented._

### `"replace substitutes only the first occurrence"`

> test "replace substitutes only the first occurrence"

 Replacing and splitting

### `"replace without a match leaves the string alone"`

> test "replace without a match leaves the string alone"

_Undocumented._

### `"replace with an empty from_str inserts at the start"`

> test "replace with an empty from_str inserts at the start"

_Undocumented._

### `"replace_all substitutes every occurrence"`

> test "replace_all substitutes every occurrence"

_Undocumented._

### `"replace_all with an empty from_str changes nothing"`

> test "replace_all with an empty from_str changes nothing"

_Undocumented._

### `"split divides on every delimiter"`

> test "split divides on every delimiter"

_Undocumented._

### `"split with an empty delimiter returns the whole string"`

> test "split with an empty delimiter returns the whole string"

_Undocumented._

### `"split with an absent delimiter returns one element"`

> test "split with an absent delimiter returns one element"

_Undocumented._

### `"split accepts multi-byte delimiters"`

> test "split accepts multi-byte delimiters"

_Undocumented._

### `"splitn keeps the remaining delimiters in the last part"`

> test "splitn keeps the remaining delimiters in the last part"

_Undocumented._

### `"splitn with n <= 0 does not split"`

> test "splitn with n <= 0 does not split"

_Undocumented._

### `"rsplit scans from the right and preserves the order"`

> test "rsplit scans from the right and preserves the order"

_Undocumented._

### `"rsplit keeps empty pieces and handles an empty delimiter"`

> test "rsplit keeps empty pieces and handles an empty delimiter"

_Undocumented._

### `"partition returns before, separator and after"`

> test "partition returns before, separator and after"

_Undocumented._

### `"partition without a separator returns the string and two empties"`

> test "partition without a separator returns the string and two empties"

_Undocumented._

### `"repeat repeats the string count times"`

> test "repeat repeats the string count times"

_Undocumented._

### `"repeat with a non-positive count is empty"`

> test "repeat with a non-positive count is empty"

_Undocumented._

### `"repeat_join joins the repetitions with the separator"`

> test "repeat_join joins the repetitions with the separator"

_Undocumented._

### `"functional replacement and splitting forms"`

> test "functional replacement and splitting forms"

_Undocumented._

### `"ljust pads on the right"`

> test "ljust pads on the right"

 Alignment

### `"ljust leaves what already fits and respects an empty pad_char"`

> test "ljust leaves what already fits and respects an empty pad_char"

_Undocumented._

### `"ljust truncates when a multi-character pad overflows"`

> test "ljust truncates when a multi-character pad overflows"

_Undocumented._

### `"rjust pads on the left"`

> test "rjust pads on the left"

_Undocumented._

### `"rjust truncates when a multi-character pad overflows"`

> test "rjust truncates when a multi-character pad overflows"

_Undocumented._

### `"pad_left and pad_right still work"`

> test "pad_left and pad_right still work"

_Undocumented._

### `"zfill pads with zeros on the left"`

> test "zfill pads with zeros on the left"

_Undocumented._

### `"zfill preserves the sign and leaves what already fits"`

> test "zfill preserves the sign and leaves what already fits"

_Undocumented._

### `"center spreads the padding on both sides"`

> test "center spreads the padding on both sides"

_Undocumented._

### `"center gives the smaller half to the left"`

> test "center gives the smaller half to the left"

_Undocumented._

### `"center with a multi-character pad does not truncate"`

> test "center with a multi-character pad does not truncate"

_Undocumented._

### `"functional alignment forms"`

> test "functional alignment forms"

_Undocumented._

### `"removeprefix drops the prefix when present"`

> test "removeprefix drops the prefix when present"

 Prefixes and suffixes

### `"removeprefix leaves the string alone when it does not match"`

> test "removeprefix leaves the string alone when it does not match"

_Undocumented._

### `"removesuffix drops the suffix when present"`

> test "removesuffix drops the suffix when present"

_Undocumented._

### `"removesuffix leaves the string alone when it does not match"`

> test "removesuffix leaves the string alone when it does not match"

_Undocumented._

### `"compare orders lexicographically by byte"`

> test "compare orders lexicographically by byte"

 Comparison

### `"compare uses the length as a tie-break"`

> test "compare uses the length as a tie-break"

_Undocumented._

### `"compare returns 0 for equal strings"`

> test "compare returns 0 for equal strings"

_Undocumented._

### `"compare distinguishes uppercase from lowercase"`

> test "compare distinguishes uppercase from lowercase"

_Undocumented._

### `"truncate appends the suffix when it cuts"`

> test "truncate appends the suffix when it cuts"

 Truncation

### `"truncate leaves what already fits"`

> test "truncate leaves what already fits"

_Undocumented._

### `"truncate with a small max_len cuts without the suffix"`

> test "truncate with a small max_len cuts without the suffix"

_Undocumented._

### `"ellipsis cuts adding an ellipsis"`

> test "ellipsis cuts adding an ellipsis"

_Undocumented._

### `"functional truncation and prefix forms"`

> test "functional truncation and prefix forms"

_Undocumented._

### `"parse_int reads integers with spaces and sign"`

> test "parse_int reads integers with spaces and sign"

 Parsing

### `"parse_int rejects garbage and overflow"`

> test "parse_int rejects garbage and overflow"

_Undocumented._

### `"parse_float computes the decimal value"`

> test "parse_float computes the decimal value"

_Undocumented._

### `"parse_float accepts a sign, a leading dot and spaces"`

> test "parse_float accepts a sign, a leading dot and spaces"

_Undocumented._

### `"parse_float rejects empty, garbage and exponents"`

> test "parse_float rejects empty, garbage and exponents"

_Undocumented._

### `"is_numeric accepts exact literals"`

> test "is_numeric accepts exact literals"

_Undocumented._

### `"is_numeric rejects spaces, exponents and garbage"`

> test "is_numeric rejects spaces, exponents and garbage"

_Undocumented._

### `"join connects the elements with the separator"`

> test "join connects the elements with the separator"

 join

### `"join of an empty list is empty"`

> test "join of an empty list is empty"

_Undocumented._

### `"join of one element adds no separator"`

> test "join of one element adds no separator"

_Undocumented._

### `"join preserves the empty elements"`

> test "join preserves the empty elements"

_Undocumented._

### `"functional length and slicing forms"`

> test "functional length and slicing forms"

 Functional forms and edges

### `"functional chars and bytes forms"`

> test "functional chars and bytes forms"

_Undocumented._

### `"the methods do not mutate the receiver"`

> test "the methods do not mutate the receiver"

_Undocumented._

### `"chars and bytes of the empty string are empty"`

> test "chars and bytes of the empty string are empty"

_Undocumented._

### `"the content predicates are false for the empty string"`

> test "the content predicates are false for the empty string"

_Undocumented._

### `"functional predicate forms"`

> test "functional predicate forms"

_Undocumented._

### `"to_snake_case separates letters from digits"`

> test "to_snake_case separates letters from digits"

_Undocumented._

### `"parse_int of the empty string is none"`

> test "parse_int of the empty string is none"

_Undocumented._

### `"index_of and last_index_of with an empty sub on empty"`

> test "index_of and last_index_of with an empty sub on empty"

_Undocumented._

### `"repeat_join with an empty separator"`

> test "repeat_join with an empty separator"

_Undocumented._

### `"lines with a trailing LF adds an empty line"`

> test "lines with a trailing LF adds an empty line"

_Undocumented._

### `"is_numeric rejects a lone sign"`

> test "is_numeric rejects a lone sign"

_Undocumented._

### `"compare with a common prefix and different lengths"`

> test "compare with a common prefix and different lengths"

_Undocumented._

### `"functional reverse and repetition forms"`

> test "functional reverse and repetition forms"

_Undocumented._

### `"starts_with_any matches any prefix"`

> test "starts_with_any matches any prefix"

 New in 2.0: strip, splitn, rsplit and the any-prefix/any-suffix predicates

### `"ends_with_any matches any suffix"`

> test "ends_with_any matches any suffix"

_Undocumented._

### `"starts_with_any and ends_with_any accept the empty pattern"`

> test "starts_with_any and ends_with_any accept the empty pattern"

_Undocumented._

### `"strip is the module alias of trim"`

> test "strip is the module alias of trim"

_Undocumented._

### `"splitn splits into at most n parts"`

> test "splitn splits into at most n parts"

_Undocumented._

### `"rsplit agrees with split on a simple string"`

> test "rsplit agrees with split on a simple string"

_Undocumented._

### `"mutating trim rewrites the receiver in place"`

> test "mutating trim rewrites the receiver in place"

_Undocumented._

### `"get_trim returns the value without mutating"`

> test "get_trim returns the value without mutating"

_Undocumented._

### `"mutating methods chain sequentially"`

> test "mutating methods chain sequentially"

_Undocumented._

### `"mutating replace forwards its arguments"`

> test "mutating replace forwards its arguments"

_Undocumented._

### `"mutating zfill and center pad in place"`

> test "mutating zfill and center pad in place"

_Undocumented._

### `"mutating substring shrinks the receiver"`

> test "mutating substring shrinks the receiver"

_Undocumented._

### `"mutating an owned buffer releases the buffer it replaces"`

> test "mutating an owned buffer releases the buffer it replaces"

_Undocumented._

