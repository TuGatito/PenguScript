# std.regulus

> Source: `std/regulus.pengu`

std/regulus.pengu — small, explicit regular expressions.

`std.regulus` wraps `std_c/re.h` + `std_c/re.c` (kokke/tiny-regex-c, public
domain). It is deliberately **not** PCRE: the engine is a few hundred lines,
has no backtracking surprises, allocates one compiled block per pattern, and
keeps the whole feature set visible in the grammar below. That is the right
trade for configuration validation, log filtering, simple tokenizers and the
future `pengu bind` / `pengu doc` tooling. For lookaround, backreferences,
`\p{...}` or Unicode case folding, install a PCRE-based satellite.

## Supported syntax (the complete list)
| Syntax | Meaning |
|---|---|
| `.` | any byte (including `\n`; `RE_DOT_MATCHES_NEWLINE` is 1) |
| `^` | beginning of the text |
| `$` | end of the text |
| `*` | zero or more, greedy |
| `+` | one or more, greedy |
| `?` | zero or one |
| `[abc]` | one byte in the set |
| `[a-z]` | one byte in the range |
| `[^abc]` | one byte **not** in the set (upstream marks this experimental) |
| `\d` `\D` | digit / non-digit (`[0-9]`) |
| `\w` `\W` | word / non-word (`[a-zA-Z0-9_]`) |
| `\s` `\S` | whitespace / non-whitespace |
| `\x` | the literal byte `x` (escapes a metacharacter) |

`(...)`, `|`, `{n,m}`, lookaround, backreferences, `(?:...)`, inline flags
and Unicode properties are **not** supported. Parentheses and `|` are
ordinary characters in this engine, not grouping operators. Matching is
byte-oriented and search-based: `is_match` asks "does the pattern occur
anywhere", exactly like Python's `re.search`, not `re.fullmatch`.

## Example
```pengu
import std.regulus
import std.spark

weave main into int:
    var cr as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
    if not cr.is_ok:
        return 1
    var rx as Regex is cr.value
    defer banish rx
    if calling rx.is_match with "abc123":
        var m as maybe Match is calling rx.match with "abc123def456"
        if m is present:
            calling spark.println_int with m.value.start
            calling spark.println_int with m.value.end
    return 0
```

## Ownership (read this once)
`Regex.compile` returns a `result`, and a `result` **owns its payload**.
`r.value` is a borrowed view of the compiled `Regex`: use it while `r` is
alive, then release the whole result with `banish r`. Do **not** also
`banish rx` — that double-frees the compiled block (LANGUAGE.md §13).

```pengu
var cr as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
if not cr.is_ok:
    return 1
var rx as Regex is cr.value
# ... use rx ...
banish cr              # releases pattern, compiled block and result box
```

- `Regex.compile` copies the pattern and owns one compiled block; `banish`
  on the result releases both through the derived `Nexus`.
- `Match` is copied, not allocated.
- `matches` returns an owned list; `replace_*` return owned strings;
  `split` returns an owned list of owned strings. Those lists/strings are
  **not** inside a result, so release them directly with `banish`.

## Complexity
| Operation | Cost |
|---|---|
| `compile` | O(pattern length), one allocation |
| `is_match`, `match`, `match_at` | O(text length) search, one temporary copy |
| `matches` | O(text length × matches) worst case, one list |
| `replace_first`, `replace_all`, `split` | O(text length) + output |
| `escape` | O(literal length) |

The temporary copy exists because `re_matchp` takes a NUL-terminated string
while a PenguScript `string` is a length-bound byte buffer. The copy is
bounded by `s.length`, so embedded NULs never cause an over-read; matching
itself stops at the first NUL, which is documented in `docs/REGULUS.md`.

---

### `REGULUS_VERSION`

> **REGULUS_VERSION** : string

 Regulus module version.

### `REGULUS_MAX_PATTERN`

> **REGULUS_MAX_PATTERN** : int

 Longest accepted pattern, in bytes.

 `tiny-regex-c` compiles into a fixed 30-slot program; this conservative
 bound rejects a pattern before the corner cases of that encoding can bite.
 Longer patterns are reported as `RegexError.PatternTooLong`.

### `REGULUS_MAX_SYMBOLS`

> **REGULUS_MAX_SYMBOLS** : int

 Maximum number of compiled symbols in one pattern (upstream limit).

### `REGULUS_MAX_CHAR_CLASS_BYTES`

> **REGULUS_MAX_CHAR_CLASS_BYTES** : int

 Maximum number of bytes across all character classes in one pattern
 (upstream limit).

### `Regex`

> rune Regex

```pengu
    _pattern as string
    _compiled as string
```

 A compiled regular expression.

 ## Memoria
 Owns `_pattern` and the compiled block behind `_compiled`. `banish regex`
 releases both through the derived `Nexus`. A `Regex` is immutable after
 compilation, so it can be shared by reference between functions.

### `Match`

> rune Match

```pengu
    start as int
    end as int
```

 A successful match, as a half-open byte range `[start, end)`.

 `start` and `end` are byte offsets, not codepoint indices. For ASCII patterns
 and text the distinction does not matter; for multibyte text, feed them to
 `std.lingua` when a codepoint range is needed.

### `RegexError`

> omen RegexError

```pengu
    PatternTooLong
    InvalidSyntax with position as int
    RegexOutOfMemory
```

 Why compilation failed.

### `_regulus_compile`

> **_regulus_compile**(pattern: string, err_out: ref to int) -> string

 Compiles `pattern` into an owned block.

 Returns a `PenguString` header whose `data` is the compiled program and whose
 `is_owned` is 2 (raw block, released with `free` by `banish`). `err_out`
 receives 0 on success, 1 for invalid syntax, 2 for an over-long pattern or 3
 for OOM. A `string` header is used instead of `ref to byte` because
 `derive Nexus` already knows how to release an owned `string`, and the
 pointer is owned by the `re` library, not by SDS.

### `_regulus_compiled_ptr`

> **_regulus_compiled_ptr**(compiled: string) -> ref to u8

 Returns the byte pointer of a compiled `Regex`.

### `_regulus_match`

> **_regulus_match**(compiled: string, text: string, start: int, out_len: ref to int) -> int

 Searches for a match at or after `start`.

 Returns the absolute byte offset of the match, or -1. `out_len` receives the
 match length in bytes. The text is copied into a bounded, NUL-terminated
 temporary because the engine's API is C-string based.

### `_regulus_syntax_position`

> **_regulus_syntax_position**(pattern: string) -> int

 Returns the byte offset of the first structural error in `pattern`, or 0.

 The engine does not report positions, so this small scan covers the two
 malformed shapes it rejects (an unterminated `[` and a trailing `\`).

### `_append_range`

> **_append_range**(sb: ref to StringBuilder, s: string, start: int, end: int) -> void

 Appends `s[start..end)` to `sb`, copying through an owned temporary.

### `_is_meta_byte`

> **_is_meta_byte**(b: int) -> bool

 `true` when `b` is a regular-expression metacharacter that `escape` must
 quote: `. [ ] { } ( ) * + ? ^ $ | \ -`.

### `compile`

> **compile**(pattern: string) -> result of Regex to RegexError

 Compiles `pattern`.

 ## Parámetros
 - `pattern`: the pattern text. Copied; the caller keeps ownership.

 ## Retorno
 `ok Regex` (owned by the result; release the result with `banish`) or
 `err RegexError`.

 ## Ejemplo
 ```pengu
 var cr as result of Regex to RegexError is calling Regex.compile with "[a-z]+"
 if cr.is_ok:
     var rx as Regex is cr.value
     # ... use rx ...
     banish cr
 ```

### `pattern`

> **pattern**() -> string

 Returns the pattern text. Borrowed; do not `banish` it.

### `is_match`

> **is_match**(s: string) -> bool

 `true` when the pattern occurs anywhere in `s`.

 ## Memoria
 O(s.length), one bounded temporary copy, no result allocation.

### `match`

> **match**(s: string) -> maybe Match

 Returns the first match, or `maybe none`.

 ## Ejemplo
 ```pengu
 var m as maybe Match is calling rx.match with "abc123"
 ```

### `match_at`

> **match_at**(s: string, start: int) -> maybe Match

 Returns the first match starting at or after `start`, or `maybe none`.

 `start < 0` or `start > s.length` returns `maybe none`.

### `matches`

> **matches**(s: string) -> list of Match

 Returns every non-overlapping match, in order.

 A zero-length match advances one byte so the loop always terminates;
 `matches` on an empty pattern therefore yields one empty match per byte
 plus one at the end, like Python's `re.finditer`.

 ## Memoria
 Allocates one list; `banish` releases it.

### `replace_first`

> **replace_first**(s: string, replacement: string) -> string

 Replaces the first match with `replacement`.

 The replacement is literal text, not a backreference template: this
 engine has no capture groups, so `$1` / `\1` would be copied verbatim.
 Returns an owned copy of `s` when there is no match.

### `replace_all`

> **replace_all**(s: string, replacement: string) -> string

 Replaces every non-overlapping match with `replacement`.

 ## Ejemplo
 ```pengu
 calling rx.replace_all with "abc123def456", "N"   # "abcNdefN"
 ```

### `split`

> **split**(s: string) -> list of string

 Splits `s` at every non-overlapping match.

 The separator is not included. A leading/trailing separator produces an
 empty field, matching the usual split semantics; no match returns a
 one-element list holding a copy of `s`.

 ## Ejemplo
 ```pengu
 var parts as list of string is calling rx.split with "a b  c"
 # ["a", "b", "c"] for pattern "\s+"
 ```

### `escape`

> **escape**(literal: string) -> string

 Escapes the metacharacters in `literal` so it matches itself.

 ## Parámetros
 - `literal`: the text to quote. Borrowed.

 ## Retorno
 An owned string; release it with `banish`.

 ## Ejemplo
 ```pengu
 var quoted as string is calling regulus.escape with "a.b*c"   # "a\\.b\\*c"
 ```

### `find_first`

> **find_first**(pattern: string, s: string) -> result of maybe Match to RegexError

 Compiles `pattern` and returns its first match in `s`.

 ## Retorno
 `ok (maybe Match)`, or `err RegexError` when the pattern is invalid.

