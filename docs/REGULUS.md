# `std.regulus` — small, explicit regular expressions

`std.regulus` wraps [`std_c/re.h`](../std_c/re.h) and
[`std_c/re.c`](../std_c/re.c), kokke's public-domain
[`tiny-regex-c`](https://github.com/kokke/tiny-regex-c). It is deliberately a
small engine: a compiled pattern is a short program of 30 slots, matching is
byte-oriented, and the whole grammar fits in one table. That is the right trade
for configuration validation, log filtering, simple tokenizers and the future
`pengu bind` / `pengu doc` tooling. It is **not** PCRE, and pretending otherwise
is the main source of bugs with regular expressions.

---

## 1. Why `tiny-regex-c` and not PCRE

| Property | `tiny-regex-c` | PCRE2 |
|---|---|---|
| Size | a few hundred lines, ~16 KB archive | hundreds of kilobytes, large dependency |
| Compile time | microseconds | milliseconds |
| Memory | one small allocation per pattern | pattern + JIT + match state |
| Grammar | the table below | everything and the kitchen sink |
| Failure mode | `re_compile` returns `NULL` | rich error codes |
| Unicode | bytes only | full UTF-8/UCP modes |
| Backtracking | bounded by the tiny grammar | configurable limits |

PenguScript's philosophy is *explicit over hidden*. A small engine whose complete
grammar is documented removes the "why did this regex do that?" class of bug. A
program that needs lookaround, backreferences or Unicode properties should
install a PCRE-based satellite explicitly, not get it implicitly.

---

## 2. Supported syntax (the complete list)

| Syntax | Meaning |
|---|---|
| `.` | any byte, including `\n` (the vendored copy keeps `RE_DOT_MATCHES_NEWLINE` = 1) |
| `^` | beginning of the text |
| `$` | end of the text |
| `*` | zero or more, greedy |
| `+` | one or more, greedy |
| `?` | zero or one |
| `[abc]` | one byte in the set |
| `[a-z]` | one byte in the range |
| `[^abc]` | one byte **not** in the set (upstream marks this feature experimental) |
| `\d` `\D` | digit / non-digit (`[0-9]`) |
| `\w` `\W` | word / non-word (`[a-zA-Z0-9_]`) |
| `\s` `\S` | whitespace / non-whitespace (`\t \f \r \n \v` and space) |
| `\x` | the literal byte `x` (escapes a metacharacter) |

Matching is **search-based**: `is_match` asks "does the pattern occur anywhere",
exactly like Python's `re.search`, not `re.fullmatch`. Use `^...$` to require the
whole text.

An empty pattern matches at every position, including the end of the text. That
is why `matches("", "ab")` returns three empty matches and
`replace_all("", "ab", "-")` returns `"-a-b-"`, matching Python.

---

## 3. Syntax **not** supported

| Syntax | Status | Workaround |
|---|---|---|
| `{n,m}` | not supported | repeat the atom or use `std.scrolls` for length checks |
| `(...)` | **not grouping** — parentheses are literal bytes | write the concatenation explicitly |
| `\|` | **not alternation** — a literal byte | test two patterns with `or` |
| `(?:...)` | not supported | no workaround; use a PCRE satellite |
| lookahead / lookbehind | not supported | pre-filter with a second pattern |
| backreferences (`\1`) | not supported | no workaround |
| `\b` word boundary | not supported | `\s`/`^`/`$` combinations |
| `\p{L}` Unicode properties | not supported | `std.lingua.is_letter` |
| inline flags (`(?i)`) | not supported | lowercase both sides with `std.scrolls` |
| named groups | not supported | no workaround |
| multiline / dotall / Unicode modes | not supported | split lines first |

> The upstream header comments once advertised `|`, but the branch is commented
> out in `re.c`. This documentation describes the engine that actually ships.

### 3.1 Workarounds

| Goal | Instead of | Write |
|---|---|---|
| one of several words | `cat\|dog` | `is_match("cat") or is_match("dog")` |
| 2 to 4 digits | `[0-9]{2,4}` | `[0-9][0-9]` plus a length/`matches` check |
| optional group | `(ab)?` | two patterns, or `ab` / empty |
| case-insensitive | `(?i)abc` | `scrolls.lower` on both sides |
| word boundary | `\bword\b` | `(^|\s)word(\s|$)` is not available either; check the surrounding bytes with `scrolls` |
| Unicode letter | `\p{L}` | `lingua.is_letter` over decoded codepoints |

---

## 4. API reference

### 4.1 Types

```pengu
rune Regex derive Nexus:
    _pattern as string
    _compiled as string

rune Match derive Par:
    start as int      # byte offset, inclusive
    end as int        # byte offset, exclusive

omen RegexError:
    PatternTooLong
    InvalidSyntax with position as int
    RegexOutOfMemory
```

`Match` has **no capture groups**, because the engine has none. A pattern such as
`(ab)+` matches the literal bytes `(ab)+`, not a group. This is a documented
limitation, not a silent empty list.

### 4.2 Ownership: a `result` owns its payload

`Regex.compile` returns a `result`; `cr.value` is a borrowed view of the
compiled regex. Release the result, not the value:

```pengu
var cr as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
if not cr.is_ok:
    return 1
var rx as Regex is cr.value
# ... use rx ...
banish cr          # releases pattern, compiled block and result box
```

Do **not** also `banish rx`: that double-frees the compiled block
(LANGUAGE.md §13).

`matches` returns an owned list; `replace_first`/`replace_all` return owned
strings; `split` returns an owned list of owned strings. Those are **not** inside
a result, so release them directly.

### 4.3 Compilation

| Function | Result | Notes |
|---|---|---|
| `Regex.compile(pattern)` | `result of Regex to RegexError` | copies the pattern, allocates one compiled block |
| `rx.pattern` | `string` | borrowed view of the original pattern |

Limits: at most `REGULUS_MAX_PATTERN` (255) bytes, `REGULUS_MAX_SYMBOLS` (30)
compiled symbols, `REGULUS_MAX_CHAR_CLASS_BYTES` (40) bytes across all character
classes. A pattern that exceeds them is `err PatternTooLong`; it is never
silently truncated.

### 4.4 Matching

| Function | Result |
|---|---|
| `rx.is_match(s)` | `bool` |
| `rx.match(s)` | `maybe Match` |
| `rx.match_at(s, start)` | `maybe Match` starting at or after `start` |
| `rx.matches(s)` | `list of Match` (non-overlapping) |

`maybe Match` owns a box; release it with `banish m` after reading
`m.value.start` / `m.value.end` (do not banish `m.value`).

### 4.5 Replacement and split

| Function | Result |
|---|---|
| `rx.replace_first(s, replacement)` | owned `string` |
| `rx.replace_all(s, replacement)` | owned `string` |
| `rx.split(s)` | owned `list of string` |

The replacement is **literal text**. There are no capture groups, so `$1` and
`\1` are copied verbatim.

### 4.6 Escape

`regulus.escape(literal)` quotes `. [ ] { } ( ) * + ? ^ $ | \ -` so a literal
can be embedded in a pattern:

```pengu
var quoted as string is calling regulus.escape with "user.name+tag"
```

### 4.7 One-shot helpers

| Function | Result |
|---|---|
| `regulus.is_match(pattern, s)` | `result of bool to RegexError` |
| `regulus.find_first(pattern, s)` | `result of maybe Match to RegexError` |

These compile, match and release the regex internally.

---

## 5. Examples

### 5.1 Validate a date `YYYY-MM-DD`

```pengu
import std.spark
import std.regulus

weave main into int:
    var cr as result of Regex to RegexError is calling Regex.compile with "^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$"
    if not cr.is_ok:
        return 1
    var rx as Regex is cr.value
    calling spark.println_bool with (calling rx.is_match with "2026-10-18")   # true
    calling spark.println_bool with (calling rx.is_match with "2026-1-18")    # false
    banish cr
    return 0
```

This validates the shape, not the calendar. Use `std.chronicle` for the month
and day ranges.

### 5.2 Basic e-mail shape

```pengu
var cr as result of Regex to RegexError is calling Regex.compile with "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"
```

This is a shape check, not RFC 5322. Do not validate an address with a regex when
delivery is the real test; send a confirmation mail.

### 5.3 Find numbers in a text

```pengu
import std.spark
import std.regulus

weave main into int:
    var cr as result of Regex to RegexError is calling Regex.compile with "[0-9]+"
    if not cr.is_ok:
        return 1
    var rx as Regex is cr.value
    var found as list of Match is calling rx.matches with "a1 b22 c333"
    var i as int is 0
    while i < found.len:
        var m as Match is found at i
        calling spark.println_int with m.start
        calling spark.println_int with m.end
        set i is i + 1
    banish found
    banish cr
    return 0
```

### 5.4 Split a comma-separated line

```pengu
var cr as result of Regex to RegexError is calling Regex.compile with ","
var rx as Regex is cr.value
var fields as list of string is calling rx.split with "a,,b"
# ["a", "", "b"]
```

For real CSV, including quoted fields, use `std.ledger`; a regex cannot parse
CSV correctly.

### 5.5 Build a pattern from user input

```pengu
var quoted as string is calling regulus.escape with user_input
var pattern as string is "{quoted}$"
var cr as result of Regex to RegexError is calling Regex.compile with pattern
```

Never concatenate raw user input into a pattern.

---

## 6. Limits and error model

| Failure | `RegexError` |
|---|---|
| pattern longer than 255 bytes | `PatternTooLong` |
| compiled program over 30 symbols or 40 class bytes | `PatternTooLong` |
| unterminated `[` | `InvalidSyntax` with the byte position of `[` |
| trailing `\` | `InvalidSyntax` with the position of `\` |
| allocator failure | `RegexOutOfMemory` |

The error type has no message field: the engine has no diagnostics beyond the
position, and the wrapper does not invent one.

### 6.1 Byte-oriented, NUL-terminated matching

The engine's API takes a C string, so `std.regulus` copies the text into a
bounded, NUL-terminated temporary for each match. Consequences:

* matching is byte-oriented: a multibyte UTF-8 character is several bytes, and
  `.` matches one byte, not one codepoint;
* matching stops at the first embedded NUL;
* `Match.start` / `Match.end` are byte offsets. Feed them to `std.lingua` when a
  codepoint range is needed;
* `is_match` performs one allocation (the temporary) even though it returns a
  `bool`.

### 6.2 No capture groups

The engine has no capture groups. `Match` therefore exposes only the whole
match. A future PCRE satellite can add groups; `std.regulus` will not pretend to
have them.

---

## 7. When to use a PCRE satellite

Install `pengu-pcre` (when published) if you need any of:

* lookahead or lookbehind;
* backreferences;
* `{n,m}` quantifiers;
* alternation or real groups;
* inline flags or Unicode properties;
* capture-group extraction;
* Unicode-aware matching.

For everything else, `std.regulus` is smaller, faster to start and easier to
audit.

---

## 8. Performance

| Operation | Cost |
|---|---|
| `compile` | O(pattern), one allocation |
| `is_match`, `match`, `match_at` | O(text) search + one temporary copy |
| `matches` | O(text × matches) worst case, one list |
| `replace_first`, `replace_all`, `split` | O(text) + output |
| `escape` | O(literal) |

A regex is immutable after compilation. `Regex` is safe to share by reference
between functions; the compiled block contains no mutable state and
`re_matchp` does not write to it.

---

## 9. Comparison

| Language | Module | Similarity | Difference |
|---|---|---|---|
| Python | `re` | `search`, `finditer`, `sub`, `split` | `regulus` has no groups, lookaround, flags or Unicode classes |
| Rust | `regex` crate | compiled pattern, linear-time matching | `regulus` is a tiny backtracker, not a DFA; no captures |
| D | `std.regex` | compile + match + replace API | `std.regex` is Unicode-aware and much larger |
| C | `tiny-regex-c` | the same engine | `regulus` adds typed errors, ownership and smart linking |

---

## 10. The vendored changes to `tiny-regex-c`

The upstream library keeps its compiled program in two `static` arrays. That has
three consequences: two live patterns alias each other, `re_compile` cannot be
paired with a free, and `re_match` is not reentrant. The vendored copy adds a
small, documented API without changing the original three functions:

```c
re_t re_compile_dynamic(const char* pattern);
re_t re_compile_dynamic_ex(const char* pattern, int* error);
void re_free(re_t pattern);
```

`re_compile_dynamic` allocates one block that holds both the compiled program and
every character-class buffer; `regex_t.u.ccl` points into the same block, so a
single `free` releases everything. `re_match` now compiles into that block and
frees it, which makes it reentrant.

Two upstream behaviours were corrected because they made the wrapper unable to
keep its promises:

* an over-long pattern is rejected (`RE_COMPILE_TOO_LONG`) instead of being
  silently truncated to a shorter expression;
* a trailing `\` is `RE_COMPILE_SYNTAX` (the header documented it as invalid, but
  the branch was commented out), and an empty-capable pattern matches at
  end-of-text, so `replace_all("", …)` and `split` agree with Python.

The original `re_compile`, `re_matchp` and `re_match` signatures are unchanged.

---

## 11. Smart linking

`std/regulus.d.pengu` contains:

```pengu
include "re.h"
link "re"
```

`build_runtime.py` archives `std_c/re.c` into `build/lib/libre.a`. The `-lre`
flag reaches the link line **only when `std.regulus` is imported**; a program that
does not use regex never pays for the archive. `tests/build/test_smart_linking.py`
checks the four import combinations and inspects `<exe>` with `nm`.
