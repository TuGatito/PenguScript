# `std.lingua` — UTF-8 text over codepoints

`std.lingua` is the explicitly-internationalised text module. It decodes the
UTF-8 bytes that a PenguScript `string` carries into Unicode scalar values,
validates them with an exact byte offset, and lets a program work in codepoints
instead of encoding bytes.

It wraps [`std_c/utf8.h`](../std_c/utf8.h), sheredom's public-domain
single-header UTF-8 library (`utf8.h` also carries the [Unlicense][unlicense]
text). The wrapper is the boundary: C decodes and encodes; PenguScript exposes a
typed, fallible API.

[unlicense]: https://unlicense.org/

---

## 1. Why `lingua` and not `scrolls`

`std.scrolls` operates on **bytes**, and that is the right default for
search/replace, prefix tests and byte-exact protocols. It is the wrong tool for
text a person reads:

| Operation | `scrolls` (bytes) | `lingua` (codepoints) |
|---|---|---|
| `"ñ".length` | `2` | `codepoint_count → 1` |
| `"😀".length` | `4` | `codepoint_count → 1` |
| reversing `"añ"` | `"ña"` only by accident of byte order | `decode` + reverse + `encode` |
| rejecting bad input | no notion of validity | `validate` with an offset |
| JavaScript length | not meaningful | `utf16_length` |

The distinction the language reference makes (§3.3) is deliberate: identifiers
are ASCII. **String literals, file contents, user input and diagnostics are
UTF-8**, and that is where `lingua` belongs.

---

## 2. The model: bytes, codepoints, graphemes

| Unit | Definition | API |
|---|---|---|
| **byte** | one `u8` of the encoding | `s.length`, `s.byte_at`, `bytes of s` |
| **codepoint** | one Unicode scalar value, `0..0x10FFFF` excluding `U+D800..U+DFFF` | `Codepoint`, `decode`, `encode` |
| **UTF-16 unit** | one `u16`; astral codepoints use a surrogate pair | `utf16_length`, `to_utf16` |
| **grapheme** | one user-perceived character (approximate here) | `grapheme_count` |

A `Codepoint` is a `seal` over `u32`:

```pengu
seal Codepoint as u32
```

The seal is not ceremony. A byte, a codepoint and a UTF-16 unit are all integers,
and mixing them is the classic text bug. Construction goes through validation:

```pengu
var r as result of Codepoint to LinguaError is calling lingua.from_u32 with 0x1F600
```

`from_u32(0xD800)` returns `err SurrogateCodepoint`; `from_u32(0x110000)` returns
`err CodepointOutOfRange`. A literal for a known-good constant can be cast
directly (`0x1F600 to Codepoint`).

---

## 3. Ownership: a `result` owns its payload

This is the one rule to read before using the module. A `result` boxes its
payload; `r.value` is a **borrowed view**. Release the whole result once:

```pengu
var decoded as result of list of Codepoint to LinguaError is calling lingua.decode with "año"
if not decoded.is_ok:
    return 1
var cps as list of Codepoint is decoded.value
# ... use cps ...
banish decoded          # releases the list AND the result box
```

Do **not** also `banish cps`: that is a double free (LANGUAGE.md §13). The same
holds for `encode`'s string. If you need the value after the result's lifetime,
copy it before banishing (a `string` with `pengu_string_copy`, a list element by
element, or rebuild it with `encode`/`decode`).

Every query (`is_valid`, `codepoint_count`, `is_letter`, …) returns a plain
value and allocates nothing, so there is no result to release.

---

## 4. API reference

### 4.1 Decoding

| Function | Result | Notes |
|---|---|---|
| `decode(s)` | `result of list of Codepoint to LinguaError` | empty string → `ok []` |
| `decode_prefix(s, max)` | `result of (list of Codepoint, int) to LinguaError` | `max <= 0` → `ok ([], 0)`; the int is bytes consumed |

```pengu
import std.spark
import std.lingua

weave main into int:
    var r as result of list of Codepoint to LinguaError is calling lingua.decode with "ñ😀"
    if not r.is_ok:
        calling spark.eprintln with "not UTF-8"
        return 1
    var cps as list of Codepoint is r.value
    calling spark.println_int with cps.len                 # 2
    calling spark.println_int with (cps at 0) to int       # 241
    calling spark.println_int with (cps at 1) to int       # 128512
    banish r
    return 0
```

### 4.2 Encoding

| Function | Result | Notes |
|---|---|---|
| `encode(cps)` | `result of string to LinguaError` | one allocation; owned by the result |
| `encode_one(cp, sb)` | `result of void to LinguaError` | appends to a `StringBuilder` |

`encode([])` is `ok ""`. `encode` rejects a codepoint outside the scalar range
with `err CodepointOutOfRange(index)`.

```pengu
var cps as list of Codepoint is list of Codepoint
calling cps.push with (0x1F600 to Codepoint)
var encoded as result of string to LinguaError is calling lingua.encode with cps
if encoded.is_ok:
    calling spark.println with encoded.value
banish encoded
banish cps
```

### 4.3 Validation

| Function | Result | Notes |
|---|---|---|
| `is_valid(s)` | `bool` | O(n), no allocation |
| `validate(s)` | `result of void to LinguaError` | first failure with its byte offset |
| `codepoint_count(s)` | `int` | `-1` when invalid |
| `utf16_length(s)` | `int` | `-1` when invalid; astral = 2 |

The `-1` sentinel keeps the hot path allocation-free. When the reason matters,
use `validate`; when the count matters and the input is untrusted, call
`is_valid` first or use `decode`.

### 4.4 Codepoint queries

| Function | True for |
|---|---|
| `is_ascii(cp)` | `U+0000..U+007F` |
| `is_bmp(cp)` | `U+0000..U+FFFF` |
| `is_letter(cp)` | approximate Unicode `L*` (see §6) |
| `is_digit(cp)` | ASCII and the common decimal blocks |
| `is_whitespace(cp)` | Unicode `White_Space` |
| `is_punctuation(cp)` | approximate Unicode `P*` |
| `is_symbol(cp)` | currency, arrows, math, dingbats, emoji |
| `is_control(cp)` | `Cc` (`U+0000..U+001F`, `U+007F..U+009F`) |
| `is_surrogate(cp)` | `U+D800..U+DFFF` (not a scalar value) |

### 4.5 Conversion

| Function | Result |
|---|---|
| `to_u32(cp)` | `u32` |
| `from_u32(v)` | `result of Codepoint to LinguaError` |
| `to_utf16(cp)` | `(u16, u16)` — `(unit, 0)` for BMP, `(high, low)` for astral |

### 4.6 Navigation

Offsets are **byte** offsets, not codepoint indices.

| Function | Result |
|---|---|
| `codepoint_at(s, byte_offset)` | `result of (Codepoint, int)` — `(cp, bytes_consumed)` |
| `byte_offset_of(s, codepoint_index)` | `result of int` — offset of the N-th codepoint |
| `next_codepoint(s, byte_offset)` | `result of (Codepoint, int)` — `(cp, offset_after)` |
| `prev_codepoint(s, byte_offset)` | `result of (Codepoint, int)` — `(cp, offset_start)` |

`prev_codepoint` is O(byte_offset); it walks from the start to check boundaries.

### 4.7 Graphemes

`grapheme_count(s)` counts approximate grapheme clusters: combining marks,
zero-width joiners (`U+200D`), variation selectors and emoji skin-tone modifiers
extend the preceding base. It is **not** UAX #29: regional-indicator flag pairs
count as two clusters, and emoji ZWJ sequences are counted by their base
codepoints. Returns `-1` for invalid input.

---

## 5. Complete examples

### 5.1 Count visible characters

```pengu
import std.spark
import std.lingua

weave main into int:
    var text as string is "año 😀"
    calling spark.println_int with (calling lingua.grapheme_count with text)
    return 0
```

### 5.2 Iterate by codepoint

```pengu
import std.spark
import std.lingua

weave main into int:
    var text as string is "añb"
    var off as int is 0
    while off < (text length):
        var step as result of (Codepoint, int) to LinguaError is calling lingua.next_codepoint with text, off
        if not step.is_ok:
            return 1
        let (cp, next_off) is step.value
        calling spark.println_int with (cp to u32) to int
        banish step
        set off is next_off
    return 0
```

### 5.3 Reject invalid user input

```pengu
import std.spark
import std.lingua

weave main into int:
    var input as string is calling spark.read_line
    var checked as result of void to LinguaError is calling lingua.validate with input
    if not checked.is_ok:
        var e as LinguaError is checked.error
        var offset as int is judge e:
            when InvalidByte with offset -> offset
            when TruncatedSequence with offset -> offset
            when OverlongEncoding with offset -> offset
            when SurrogateCodepoint with offset -> offset
            when CodepointOutOfRange with offset -> offset
            when IndexOutOfRange with index -> index
        calling spark.eprintln with "invalid UTF-8 at byte {offset}"
        banish checked
        return 1
    banish checked
    return 0
```

### 5.4 JavaScript/Win32 interop

```pengu
import std.spark
import std.lingua

weave main into int:
    calling spark.println_int with (calling lingua.utf16_length with "😀")   # 2
    calling spark.println_int with (calling lingua.utf16_length with "ñ")    # 1
    return 0
```

---

## 6. Error model

```pengu
omen LinguaError:
    InvalidByte with offset as int
    TruncatedSequence with offset as int
    OverlongEncoding with offset as int
    SurrogateCodepoint with offset as int
    CodepointOutOfRange with offset as int
    IndexOutOfRange with index as int
```

| Input | Result |
|---|---|
| `""` | `ok []` |
| `"ñ"` | `ok [Codepoint(0xF1)]` |
| `"😀"` | `ok [Codepoint(0x1F600)]` |
| `"\xFF"` | `err InvalidByte(0)` |
| `"\xC0\x80"` | `err OverlongEncoding(0)` |
| `"\xED\xA0\x80"` | `err SurrogateCodepoint(0)` |
| `"\xF4\x90\x80\x80"` | `err CodepointOutOfRange(0)` |
| `"\xE2\x82"` | `err TruncatedSequence(0)` |

`offset` always points at the **first byte of the invalid sequence**.

---

## 7. Limits (explicit, not hidden)

* **Classification is approximate.** `is_letter`, `is_digit`, `is_punctuation`,
  `is_symbol` and `is_whitespace` are range tables, not the Unicode Character
  Database. They cover ASCII, Latin-1 and Latin Extended, Greek, Cyrillic,
  Armenian, Hebrew, Arabic, Devanagari, Thai/Lao, Georgian, Hiragana, Katakana,
  Bopomofo, Hangul, CJK, the compatibility/fullwidth letter blocks, common
  punctuation and the emoji blocks. A newly assigned block is not recognised
  until the table grows; `docs` and the module source are the source of truth.
* **Graphemes are approximate.** See §4.7.
* **No normalisation** (NFC/NFD/NFKC/NFKD). `lingua` never changes the bytes it
  is given.
* **No case folding.** `utf8.h` exposes `utf8lwr`/`utf8upr` for simple mappings
  in its raw binding, but the wrapper does not promise locale- or
  Unicode-complete case conversion.
* **No locale.** Classification is deterministic on every platform.

For complete Unicode tables, normalisation or full case folding, use a satellite
(`pengu-icu` when it exists) rather than growing this module into an ICU clone.

---

## 8. Performance

| Operation | Time | Allocations |
|---|---|---|
| `is_valid`, `validate`, `codepoint_count`, `utf16_length`, `grapheme_count` | O(n) | 0 |
| `codepoint_at`, `next_codepoint` | O(1) + one sequence | 0 |
| `prev_codepoint`, `byte_offset_of` | O(offset) | 0 |
| `decode`, `decode_prefix` | O(n) | 1 list (+ result box) |
| `encode` | O(n) | 1 string (+ result box) |
| `encode_one` | O(1) | builder growth only |

`decode` does not copy the input: it validates each sequence with
`_lingua_scan` and pushes the scalar value. `encode` reserves through
`StringBuilder`.

---

## 9. Comparison

| Language | Module | Similarity | Difference |
|---|---|---|---|
| Julia | `utf8proc` | codepoint decode/encode, character categories | `lingua` has no normalisation or full category tables |
| Rust | `str` / `unicode-segmentation` | `chars()`, grapheme clusters | `lingua` returns a `result` with byte offsets; graphemes are approximate |
| Lua | `utf8` library (5.3) | `utf8.codepoint`, `utf8.len`, `utf8.char` | `lingua` also validates with typed errors and reports UTF-16 length |
| Go | `unicode/utf8` | `DecodeRune`, `RuneLen`, `Valid` | `lingua` uses a `seal` for codepoints and explicit `result` ownership |

---

## 10. Smart linking

`std/lingua.d.pengu` is the raw binding:

```pengu
include "utf8.h"
```

`std/lingua.pengu` is the wrapper. The build manager emits the `#include` only
when `std.lingua` is imported, so a program that never touches the module does
not see `utf8.h` at all. There is no archive to link: `utf8.h` is header-only.
`tests/build/test_smart_linking.py` checks the four import combinations.
