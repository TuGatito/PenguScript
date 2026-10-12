# Bugs fixed in Chunk 7 — `std/cipher` + `std/seal`

Chunk 7 of the Pengunic 2.0 migration re-verified and fixed **every** bug found
in `std/cipher.pengu` and `std/seal.pengu`. This file is the mandated record: one
entry per defect, with the symptom, the root cause, the impact, the fix and the
regression test that fails without the fix.

The list starts from the 44 bugs the brief already identified (C1–C24, S1–S20)
and adds the defects the audit found on top. Every brief number gets a verdict:
**fixed**, **verified (not a bug)**, or **documented deviation**. Bugs that need
a compiler or a closed-module change are collected in §4: §5.3 of the brief
forbids touching the compiler and every other `std/*.pengu`, so those are
**documented and worked around**, never ignored, and are handed to the next
chunk.

Regression tests live in three places:

* the internal `test "…"` blocks at the bottom of each module
  (`pengu test --entry std/cipher.pengu`, `pengu test --entry std/seal.pengu`);
* the self-contained end-to-end suites `tests/stdlib/test_cipher.py` and
  `tests/stdlib/test_seal.py`, which compile and run a throw-away program per
  case and assert its stdout/exit code.

Every entry names the test that pins it. Bugs whose fix is a *linear-time*
algorithm carry a timing assertion, because correctness alone would not catch
the regression.

---

## 1. `std/cipher` — encodings and JSON (`CIPHER_VERSION` `2.0.0` → `2.1.0`)

### BUG-C1: every encoder and decoder grew its result by string interpolation (O(n²))
- **Módulo:** std/cipher
- **Función:** `encode_base64`, `encode_base64_url`, `encode_base64_nopad`,
  `decode_base64`, `encode_hex`, `decode_hex`, `encode_base32`,
  `decode_base32`, `json_escape`, `json_unescape`, `json_read_str`,
  `json_read_value`, `parse_json`, `parse_json_array`, `stringify_json`,
  `stringify_json_array`, `pretty_json`
- **Síntoma:** `set out is "{out}{x}"` inside a loop copies the whole
  accumulator on every step. Measured on 2.0.0 with `encode_base64` (in-process
  `chronicle.monotonic`): 9 KiB → 77 ms, 18 KiB → 296 ms, 37 KiB → 928 ms,
  74 KiB → 3477 ms — a clean 4× cost per 2× input.
- **Causa raíz:** the only string-building primitive used was interpolation,
  which is a fresh allocation plus a full copy of the left operand.
- **Impacto:** any real payload (a file, an HTTP body, a JSON document) spent
  seconds to minutes in an encoder; the quadratic term dominated.
- **Fix aplicado:** the hot paths (Base64/Hex/Base32 encode and decode, JSON
  escaping, file-free `crc32_hex`) run in private `antiquus` C blocks that
  allocate the exact output size once and write into it. The remaining builders
  accumulate into a `list of string` and concatenate once with the O(n)
  `_concat_parts` helper. **`std.scrolls.join` is deliberately not used**: it is
  implemented with the same quadratic loop (out-of-scope finding G-6).
- **Test de regresión:** internal `test "BUG-C1: Base64 encodes a long input
  without quadratic blow-up"` and `test "BUG-C1: Hex and Base32 encode long
  inputs linearly"`, plus the timing assertion
  `tests/stdlib/test_cipher.py::test_bug_c1_encoding_a_large_input_is_linear`
  (256 KiB must finish in under 5 s; 2.0.0 would need about a minute).

### BUG-C2: `\uD83D\uDE00` decoded as two invalid characters (CESU-8)
- **Módulo:** std/cipher
- **Función:** `json_unescape`, `json_read_str`, the generic parser
- **Síntoma:** `json_unescape("\uD83D\uDE00")` produced six bytes
  (`ed a0 bd ed b8 80`) instead of the four-byte `U+1F600` (`f0 9f 98 80`).
- **Causa raíz:** each `\uXXXX` was encoded independently; no code combined a
  high surrogate (`D800–DBFF`) with the low surrogate that follows it.
- **Impacto:** any JSON string with an astral-plane character (emoji, historic
  scripts) round-tripped as invalid UTF-8 — Python and JavaScript both produce
  the single code point.
- **Fix aplicado:** `_scan_string_body` now detects a high surrogate, looks
  ahead for `\uDC00–\uDFFF`, and encodes the combined code point with
  `_utf8_encode_cp`. Under the strict parsers an unpaired surrogate is an error;
  the lenient `json_unescape` keeps the 2.0.0 CESU-8 behaviour for a lone one.
- **Test de regresión:** internal `test "BUG-C2: json_unescape combines a
  surrogate pair into one code point"` and `tests/stdlib/test_cipher.py::test_bug_c2_json_unescape_combines_surrogate_pairs`.

### BUG-C3: the `\uXXXX` three-byte formula "overflows" for code points ≥ 0x8000 — **verified, not a bug**
- **Módulo:** std/cipher
- **Función:** `json_read_str`, `json_unescape`
- **Síntoma (as filed):** `b1 = 224 + cp/4096` was said to overflow because
  `cp/4096 > 15`.
- **Veredicto:** for a 16-bit `cp` the quotient is at most `0xFFFF/4096 = 15`, so
  `b1 ∈ [224, 239]`, `b2 ∈ [128, 191]` and `b3 ∈ [128, 191]` — exactly the legal
  UTF-8 three-byte range. The formula is correct and the 2.0.0 result was right;
  the *real* nearby defects were BUG-C2 (no pair combining) and BUG-C6 (no
  rejection of unpaired surrogates), both fixed.
- **Test de regresión:** the surrogate tests above plus the internal
  `json_unescape` short-escape tests cover the three encodings.

### BUG-C4: the parsers accepted invalid UTF-8
- **Módulo:** std/cipher
- **Función:** `parse_json`, `parse_json_array`, `parse_value`, `parse_json_value`
- **Síntoma:** a JSON string containing a bare `0xFF` parsed successfully; Python
  raises `UnicodeDecodeError`.
- **Causa raíz:** the readers copied raw bytes without ever checking that they
  formed UTF-8 sequences.
- **Impacto:** a producer could hand the program text that is not valid UTF-8
  (RFC 8259 requires UTF-8) and get a "successfully parsed" result; downstream
  code then emitted invalid UTF-8.
- **Fix aplicado:** `_utf8_validate` gates every parser entry point and
  `_utf8_valid_seq` validates each sequence the string reader copies (rejecting
  overlong forms, surrogate halves and out-of-range lead bytes).
- **Test de regresión:** internal `test "BUG-C4: parse_json rejects unescaped
  control bytes and invalid UTF-8"`.

### BUG-C5: the parser accepted invalid tokens, trailing commas and trailing content
- **Módulo:** std/cipher
- **Función:** `parse_json`, `parse_json_array`, `parse_value`
- **Síntoma (measured on 2.0.0):** all of these were accepted —
  `{"a": tru}`, `{"a": 1,}`, `{"a":}`, `{"a": 1} trailing`, `{"a": 1 2 3}`.
  `parse_value("1 2 3")` returned `some "1"` and `is_valid_json_value("1 2 3")`
  was `true`.
- **Causa raíz:** the tokenizer stopped a number at the first delimiter without
  checking the token's grammar, the member loop accepted `}` immediately after a
  comma, and no parser checked that the cursor reached the end of the document.
- **Impacto:** malformed configuration and protocol documents were silently
  accepted with guessed values — the worst possible failure mode for a parser
  that feeds signatures, requests and config.
- **Fix aplicado:** `_read_number_strict` implements the RFC 8259 number
  grammar, `_read_literal_strict` matches `true`/`false`/`null` exactly, the
  object/array loops reject a member after a comma that is not a string, and
  every entry point requires the cursor to end at the document end.
- **Test de regresión:** internal `test "BUG-C5: parse_json rejects incomplete
  literals and trailing commas"` and
  `test "parse_value validates the whole input"`, plus
  `tests/stdlib/test_cipher.py::test_bug_c5_parse_json_is_strict`,
  `::test_bug_c5_parse_value_validates_the_whole_input` and
  `::test_parse_json_array_and_serializer`.

### BUG-C6: `\u` escapes were neither length-checked nor surrogate-checked
- **Módulo:** std/cipher
- **Función:** `json_read_str`, `json_unescape`
- **Síntoma (measured):** `"\uD83D"` alone produced the three CESU-8 bytes. A
  `\u` with fewer than four hex digits fell back to copying the letter `u`.
- **Causa raíz:** the escape branch checked only that four bytes existed and then
  hex-decoded them; nothing rejected a surrogate that is not part of a pair.
- **Impacto:** invalid UTF-8 could enter the tree; a truncated escape was
  silently reinterpreted.
- **Fix aplicado:** the strict readers reject a lone surrogate and a malformed
  `\u`; the lenient `json_unescape` keeps the documented 2.0.0 CESU-8 fallback.
  A `\uXXXX` followed by more hex digits is *not* a bug: `"\u004100"` is `"A00"`
  in Python too, and the strict parser agrees.
- **Test de regresión:** internal `test "json_unescape keeps lone surrogates as
  CESU-8 (lenient mode)"` and the strict-mode assertion in
  `tests/stdlib/test_cipher.py::test_parse_json_value_is_strict_and_surrogate_aware`.

### BUG-C7: trailing commas were accepted
- **Módulo:** std/cipher
- **Función:** `parse_json`, `parse_json_array`
- **Síntoma:** `{"a": 1,}` and `[1, 2,]` parsed.
- **Causa raíz:** the separator branch consumed the comma and looped without
  requiring a member to follow.
- **Impacto:** non-standard JSON entered the program; the same document is
  rejected by every other parser in the ecosystem.
- **Fix aplicado:** after a comma the next token must be a key/element; a closing
  bracket there is `none`.
- **Test de regresión:** `test_bug_c5_parse_json_is_strict` (cipher) and the
  array assertion in `test_parse_json_array_and_serializer`.

### BUG-C8: nested JSON lost its opening delimiter — plus no generic tree
- **Módulo:** std/cipher
- **Función:** `json_read_value`, `parse_json`
- **Síntoma (measured):** for `{"a": {"b": 1}}`, `parse_json` stored `"b": 1}`
  as the value of `a` — the leading `{` was dropped, so the stored raw text was
  **not valid JSON** and `json_is_literal` rejected it. Arrays had the same
  defect. There was also no `JsonValue` tree at all, so a caller could not read
  a nested field as anything but unparsed text.
- **Causa raíz:** the composite branch started copying *after* consuming the
  opening delimiter and never re-emitted it.
- **Impacto:** every nested-object access (`json_path`, `json_parse_at`,
  hand-rolled traversal) operated on corrupted text.
- **Fix aplicado:** the raw capture keeps both delimiters (and copies strings
  inside the composite verbatim), and the new generic `JsonValue` omen with
  `parse_json_value` / `stringify_json_value` provides real nested access. The
  legacy flat surface keeps its contract.
- **Test de regresión:** internal `test "BUG-C8: parse_json keeps the full braces
  of a nested object"` and
  `tests/stdlib/test_cipher.py::test_bug_c8_parse_json_keeps_nested_braces`.

### BUG-C9: `json_get_float` looped once per exponent unit
- **Módulo:** std/cipher
- **Función:** `json_get_float`
- **Síntoma:** `{"a": 1e1000000}` ran a one-million-iteration multiply loop.
- **Causa raíz:** the exponent was applied with `while e_idx < exp_val`.
- **Impacto:** a hostile or merely careless document pinned a core for seconds
  (and a larger exponent for minutes) — a trivial denial of service in any
  server that parses JSON.
- **Fix aplicado:** `_parse_json_float` owns a strict, bounded parser: it clamps
  the exponent to 60 multiplications, so `1e1000000` saturates to infinity in
  constant time. `json_get_float` also validates the whole token as a JSON
  number first (2.0.0 accepted `+1`, `1.` and `.5`, which JSON forbids).
- **Test de regresión:** internal `test "BUG-C9: json_get_float bounds the
  exponent"` and
  `tests/stdlib/test_cipher.py::test_bug_c9_json_get_float_bounds_the_exponent`.

### BUG-C10: `NaN` / `Infinity` — **verified, intentional deviation**
- **Módulo:** std/cipher
- **Función:** `parse_json_value`, `parse_json`, `json_get_float`
- **Síntoma (as filed):** the module does not accept `NaN` / `Infinity`.
- **Veredicto:** RFC 8259 §6 defines exactly three literals (`true`, `false`,
  `null`) and no `NaN`/`Infinity`; accepting them is a Python
  `allow_nan=True` extension. The strict parser rejects them by design, and the
  deviation is documented in `docs/CIPHER_API.md`. This is a deliberate
  standards-compliant choice, not a defect.
- **Test de regresión:** the strict-token tests above pin the rejection.

### BUG-C11: `cb64_char` and the other conversion helpers were undocumented
- **Módulo:** std/cipher
- **Función:** `cb64_char`, `cb64_val`, `_hex_val`, `_b32_char`, `_b32_val`
- **Síntoma:** public symbols with no canonical `## ## Parámetros` /
  `## ## Retorno` block; `cb64_char` also returned `"/"` for *any* out-of-range
  value.
- **Causa raíz:** the 0.15.0 helpers predate the docstring rule.
- **Impacto:** no contract for the public API; an out-of-range index produced a
  plausible-looking character instead of a detectable sentinel.
- **Fix aplicado:** canonical docstrings on all five; `cb64_char` returns `"="`
  for an out-of-range value (the documented 2.0.0 fallback is preserved for
  in-range values only) and rejects negatives.
- **Test de regresión:** internal `test "BUG-C12: _hex_val rejects
  multi-character input"` and `test "BUG-C13: cb64_val and _b32_val reject
  multi-character input"`.

### BUG-C12: `_hex_val` read only the first byte of a multi-byte argument
- **Módulo:** std/cipher
- **Función:** `_hex_val`
- **Síntoma:** `_hex_val("ab")` returned `10` (the value of `a`).
- **Causa raíz:** `ord c` on a longer string silently reads its first byte.
- **Impacto:** a caller that sliced wrongly got a wrong digit instead of an
  error — a decoder that guesses is a decoder that corrupts.
- **Fix aplicado:** the function rejects any argument that is not exactly one
  character (`-1`).
- **Test de regresión:** internal `test "BUG-C12: _hex_val rejects
  multi-character input"`.

### BUG-C13: `cb64_val` / `_b32_val` had the same first-byte defect
- **Módulo:** std/cipher
- **Función:** `cb64_val`, `_b32_val`
- **Síntoma:** `cb64_val("ab")` returned `26`; `cb64_val("")` called `ord` on an
  empty string (undefined).
- **Causa raíz:** same as BUG-C12, plus no empty-string guard.
- **Impacto:** silent mis-decoding and a potential crash for an empty slice.
- **Fix aplicado:** both reject anything that is not exactly one character.
- **Test de regresión:** internal `test "BUG-C13: cb64_val and _b32_val reject
  multi-character input"`.

### BUG-C14: the URL-safe Base64 spec — **verified, plus one real rejection added**
- **Módulo:** std/cipher
- **Función:** `decode_base64_url`
- **Síntoma (as filed):** "accepts any mix of alphabets".
- **Veredicto:** the decoder *did* reject out-of-alphabet characters (`AB*D` →
  `none`); accepting both the standard and the URL alphabet is the documented
  2.0.0 contract and is preserved. The audit did find an adjacent hole: a
  length of `4k+1` (for example `"AB-DE"`, after padding `"AB-DE==="`) was
  handed to the decoder instead of being rejected up front.
- **Fix aplicado:** `decode_base64_url` / `decode_base64_nopad` return `none`
  for `len % 4 == 1` before decoding.
- **Test de regresión:** internal `test "BUG-C14: decode_base64 rejects
  characters outside the alphabet"` and
  `tests/stdlib/test_cipher.py::test_bug_c14_decoders_validate_the_alphabet`.

### BUG-C15: `decode_base64` validated padding in a second pass over the input
- **Módulo:** std/cipher
- **Función:** `decode_base64`
- **Síntoma:** the whole string was scanned once to find the first `=` and count
  padding, then scanned again to decode.
- **Causa raíz:** padding bookkeeping was bolted onto a decoder that already had
  a quantum loop.
- **Impacto:** two passes and an extra interpolated copy of the cleaned input
  (which also made the *decode* quadratic).
- **Fix aplicado:** a single-pass C decoder that tracks the quad and the padding
  state together, rejects `=` anywhere but a trailing run of one or two, and
  requires the padded stream to end at the document end. The regression pin also
  covers `QQ==QQ==`, `====` and `Q===`.
- **Test de regresión:** internal `test "BUG-C15: decode_base64 rejects
  misplaced and excessive padding"` and
  `tests/stdlib/test_cipher.py::test_bug_c15_decode_base64_rejects_misplaced_padding`.

### BUG-C16 / BUG-C17 / BUG-C18: no generic JSON type, and serializers only accepted strings
- **Módulo:** std/cipher
- **Función:** whole JSON surface
- **Síntoma:** there was no `JsonValue`; `parse_json` could only return a flat
  `map of string to string`, `stringify_json` / `pretty_json` only accepted that
  same map, and a `list`, `int`, `float` or `bool` value had to be smuggled in as
  raw text.
- **Causa raíz:** the 0.15.0 design stored every member as its raw JSON text and
  never modelled the value algebraically.
- **Impacto:** no parity with Python's `json` for anything non-flat, and a
  serializer that could not express the values the parser produced.
- **Fix aplicado:** the `JsonValue` omen (`JvNull`, `JvBool`, `JvInt`, `JvFloat`,
  `JvString`, `JvArray`, `JvObject`) with `parse_json_value`,
  `parse_json_to_map`, `parse_json_to_list`, `stringify_json_value`,
  `stringify_json_value_pretty`, `json_dumps_canonical`, the accessor/coercion
  family and `json_value_deep_clone` / `json_value_merge`. Typed map serializers
  (`stringify_json_map_int` / `_float` / `_bool`) cover the flat case.
- **Test de regresión:** internal `test "parse_json_value builds the generic
  tree"`, `test "generic round-trip: parse then stringify is stable"` and the
  `tests/stdlib/test_cipher.py::test_parse_json_value_*` /
  `::test_generic_round_trip_and_canonical_form` cases.

### BUG-C19: `decode_base32` only checked `len % 8 == 0`
- **Módulo:** std/cipher
- **Función:** `decode_base32`
- **Síntoma (measured):** `"AA======AA======"` and `"AB======AA======"` both
  decoded to two bytes instead of being rejected: padding in the middle of the
  stream was treated as ordinary input.
- **Causa raíz:** the padding character decoded to `-1` and the quantum loop
  silently skipped the byte it should have signalled.
- **Impacto:** corrupted or truncated Base32 (a very common transmission error)
  produced wrong bytes with no error.
- **Fix aplicado:** the C decoder requires padding to close the stream, accepts
  only the four legal padded lengths (`2`, `4`, `5`, `7` data characters), and
  rejects non-zero bits in the discarded tail. The audit also caught a real
  extraction bug in the new decoder — a one-byte group took the low eight bits of
  the 10-bit accumulator instead of the high eight — which the round-trip test
  found and pinned.
- **Test de regresión:** internal `test "BUG-C19: decode_base32 rejects padding
  that does not close the string"`, `test "Base32 is case-insensitive and
  ignores whitespace"` and
  `tests/stdlib/test_cipher.py::test_base32_round_trip_for_every_length` (every
  length 0–20, which is what exposed the extraction bug).

### BUG-C20: no Base85 (and no Z85 or Base58)
- **Módulo:** std/cipher
- **Función:** new `encode_base85` / `decode_base85` / `encode_base85_z85` /
  `decode_base85_z85` / `encode_base58` / `decode_base58`
- **Síntoma:** Python's `base64.b85encode` had no counterpart.
- **Fix aplicado:** RFC 1924 Base85 and ZeroMQ Z85, both matching Python's
  partial-group rules byte for byte (a trailing group is zero-padded and
  truncated; the decoder refills the missing digits with the alphabet's last
  character, which is exactly what CPython's `_b85decode` does by appending
  `~`), plus Bitcoin Base58 with leading-zero handling. The audit caught a
  partial-group decode bug in the first draft (multiplying by `85^missing`
  without the `~` filler), which the parity test found.
- **Test de regresión:** internal `test "Base85 matches the RFC 1924 examples"`
  and `test "Z85 matches the ZeroMQ test vector"`, plus the parametrised
  `tests/stdlib/test_cipher.py::test_base85_matches_python` (compared against
  `base64.b85encode`) and `::test_base58_matches_a_reference_implementation`.

### BUG-C21: no percent-encoding
- **Módulo:** std/cipher
- **Función:** new `encode_url` / `decode_url` (+ the `to_url` / `from_url`
  enchantments)
- **Síntoma:** the encoding lived nowhere reachable without importing `precis`.
- **Fix aplicado:** RFC 3986 percent-encoding with the unreserved set kept and
  **uppercase** hex digits (matching `urllib.parse.quote`), and a decoder that
  rejects a truncated or non-hex `%` escape.
- **Test de regresión:**
  `tests/stdlib/test_cipher.py::test_url_encoding_matches_urllib`.

### BUG-C22: `json_deep_clone` / `json_merge` only copied one level
- **Módulo:** std/cipher
- **Función:** `json_deep_clone`, `json_merge`
- **Síntoma:** the flat map was copied but nested raw values were shared.
- **Veredicto parcial:** for the *legacy* flat surface the shared "values" are
  immutable strings, so the shallow copy was harmless and the functions now say
  so. The real gap was the generic tree, where a container child must not be
  aliased by a merge.
- **Fix aplicado:** `json_value_deep_clone` rebuilds every object and array, and
  `json_value_merge` / `json_value_merge_patch` build fresh containers so mutating
  the result cannot reach the input.
- **Test de regresión:** internal `test "json_value_deep_clone is independent and
  equal"` and
  `tests/stdlib/test_cipher.py::test_parse_json_to_map_and_deep_clone`.

### BUG-C23: `json_path` could not index arrays
- **Módulo:** std/cipher
- **Función:** `json_path`, `json_parse_at`
- **Síntoma:** `users[0].name` returned `none`; only dot-separated object keys
  worked. Combined with BUG-C8, a nested path returned corrupted text.
- **Causa raíz:** the path splitter only knew `.` and the traversal only knew
  maps.
- **Impacto:** no way to read an element of a JSON array through the documented
  navigation API.
- **Fix aplicado:** `_parse_path_segments` understands `name[index]` groups
  (without creating empty segments around them) and `json_path` traverses arrays
  and objects through the generic tree; `json_pointer_get` adds the RFC 6901
  spelling, and `json_patch` / `json_merge_patch` complete the RFC 6902 / 7396
  surface.
- **Test de regresión:** internal `test "BUG-C23: json_path walks arrays and
  keeps nested braces"`, `test "json_pointer_get resolves RFC 6901 pointers"`,
  `test "json_patch applies add, replace, remove and test"`,
  `test "json_merge_patch follows RFC 7396"`, plus
  `tests/stdlib/test_cipher.py::test_bug_c23_json_path_walks_arrays`,
  `::test_json_pointer_get_resolves_escapes_and_arrays`,
  `::test_json_patch_applies_operations`,
  `::test_json_patch_reports_failures` and
  `::test_json_merge_patch_follows_rfc_7396`.

### BUG-C24: serializers emitted members in hash order
- **Módulo:** std/cipher
- **Función:** `stringify_json`, `pretty_json`, all serializers
- **Síntoma (measured):** the same three-member map produced
  `{"c":3,"b":2,"a":1}` on one run and a different order on the next —
  `pengu_map_keys_string` returns hash order.
- **Causa raíz:** the serializers iterated the runtime's key list directly.
- **Impacto:** non-reproducible output: cache keys, signatures over serialized
  documents and golden-file tests all broke; Python has guaranteed insertion
  order since 3.7.
- **Fix aplicado:** every serializer sorts the keys (`_sorted_map_keys` /
  `_sort_keys_in_place`), so two runs are byte-identical; `json_dumps_canonical`
  documents the RFC 8785-shaped spelling. Insertion order is not representable
  in a PenguScript `map`, and the deviation is documented.
- **Test de regresión:** internal `test "BUG-C24: stringify_json sorts keys
  deterministically"`, `test "json_dumps_canonical sorts keys at every level"`
  and `tests/stdlib/test_cipher.py::test_bug_c24_stringify_json_sorts_keys`.

### Extra cipher defects found by the audit (not in the brief)
- **BUG-C25 (new): `parse_json` accepted an empty member value.**
  `{"a":}` produced a map with `a` mapped to `""`. *Fix:* the strict value reader
  rejects an empty token. *Test:* `test_bug_c5_parse_json_is_strict`.
- **BUG-C26 (new): `parse_json` accepted trailing content.**
  `{"a": 1} trailing` parsed. *Fix:* every entry point requires the cursor to
  end at the end of the document. *Test:* `test_bug_c5_parse_json_is_strict`.
- **BUG-C27 (new): unescaped control bytes were accepted inside strings.**
  `{"a": "x<0x01>y"}` parsed, although RFC 8259 §7 requires control characters
  to be escaped. *Fix:* the strict scanner rejects a raw byte below `0x20`.
  *Test:* internal `test "BUG-C4: parse_json rejects unescaped control bytes and
  invalid UTF-8"`.
- **BUG-C28 (new): `decode_base64_url` with `len % 4 == 1` attempted a decode.**
  *Fix:* rejected before decoding. *Test:* `test_bug_c14_decoders_validate_the_alphabet`.
- **BUG-C29 (new): the 2.0.0 module emitted `W0005` shadowing warnings.**
  Locals named `keys` shadowed a global function, so `pengu check` was not clean.
  *Fix:* renamed (`key_list`, `is_first`, `group_len`, …); the module now checks
  with zero warnings. *Test:* the gate itself.

---

## 2. `std/seal` — digests, MACs, KDFs and compression (`SEAL_VERSION` `2.0.0` → `2.1.0`)

### BUG-S1: `hmac_*` built its pads with string interpolation in a loop
- **Módulo:** std/seal
- **Función:** `hmac_sha256`, `hmac_sha1`, `hmac_md5`
- **Síntoma:** `k_ipad` and `k_opad` were grown one character at a time with
  `set k_ipad is "{k_ipad}{(chr (b ^ 54))}"`, twice per key byte, plus one
  interpolation per padding byte.
- **Causa raíz:** the same quadratic accumulator pattern as BUG-C1.
- **Impacto:** a 128-byte block cost thousands of copies; a long message made the
  inner concatenation quadratic as well.
- **Fix aplicado:** `_hmac_raw` composes the raw digest of any algorithm with one
  O(n) `_concat_parts` per half-MAC, and the key schedule builds a `list of
  string` in one pass. Every HMAC variant now shares that single implementation.
- **Test de regresión:** internal `test "BUG-S4: an over-long HMAC key is hashed
  first, whatever the block size"` and the per-algorithm parity test
  `tests/stdlib/test_seal.py::test_hmac_matches_python_for_every_algorithm`.

### BUG-S2: `chr 0` padding "may truncate" — **compiler finding, not an HMAC bug**
- **Módulo:** std/seal (root cause in the compiler)
- **Función:** `hmac_*`
- **Síntoma (as filed):** a NUL byte built with `chr 0` seemed to disappear.
- **Veredicto (measured):** `_hmac_raw` is binary-safe — a key and a message with
  embedded NULs match Python's `hmac` exactly. The disappearing byte comes from
  the compiler's constant folding: a *literal* `chr 0` inside an interpolated
  string is folded into the generated C format string and terminates it, so
  `"a{(chr 0)}b"` is `"ab"`. See out-of-scope finding **G-1**.
- **Impacto:** any module that builds binary data from constant `chr` calls
  silently loses bytes.
- **Fix aplicado:** the modules build binary strings from `int` *variables*
  (`_quote_char`, `nul_byte`, `_random_bytes`, the test fixtures), never from a
  constant `chr` in an interpolated position.
- **Test de regresión:** internal `test "BUG-S2: HMAC is binary-safe for keys and
  messages containing NULs"` and
  `tests/stdlib/test_seal.py::test_bug_s2_hmac_is_binary_safe`.

### BUG-S3: `_hex_to_bytes` accepted malformed hex and produced wrong bytes
- **Módulo:** std/seal
- **Función:** `_hex_to_bytes`
- **Síntoma:** `"abc"` (odd length) silently dropped the trailing nibble; `"zz"`
  mapped both invalid digits to zero. An invalid character was never reported.
- **Causa raíz:** the digit parser fell through to a `0` default and the loop
  condition `(i + 1) < len` ignored the last character.
- **Impacto:** a MAC or key comparison against wrongly decoded bytes could pass
  or fail for the wrong reason; a secret could be derived from the wrong key.
- **Fix aplicado:** `_hex_to_bytes` returns `maybe string` and rejects an odd
  length or a non-hex digit; `hex_to_bytes` is the public alias and
  `_hex_to_bytes_lenient` preserves the 2.0.0 behaviour with a `## @deprecated`
  marker.
- **Test de regresión:** internal `test "BUG-S3: _hex_to_bytes rejects malformed
  hex and the lenient spelling survives"` and
  `tests/stdlib/test_seal.py::test_bug_s3_hex_to_bytes_validates_its_input`.

### BUG-S4: the HMAC block size was hard-coded to 64
- **Módulo:** std/seal
- **Función:** `hmac_sha256`, `hmac_sha1`, `hmac_md5`
- **Síntoma:** `while k.len < 64` and `while j < 64` appear in every HMAC body.
  It is correct for the 64-byte algorithms and wrong for any 128-byte one
  (SHA-384/SHA-512), which therefore could not be added.
- **Causa raíz:** the constant was inlined instead of being derived from the
  algorithm.
- **Impacto:** adding HMAC-SHA-512 would have produced wrong digests for keys
  longer than 64 bytes with no compile-time or run-time signal.
- **Fix aplicado:** `_block_len(alg)` returns the RFC 2104 block size (64 for
  MD5/SHA-1/SHA-2 up to 256/BLAKE2s, 128 for SHA-384/512/BLAKE2b, the sponge
  rate for SHA-3) and `_hmac_raw` uses it.
- **Test de regresión:** `test_hmac_matches_python_for_every_algorithm` (which
  includes SHA-384/512 and SHA3-256/512) and
  `test_bug_s4_hmac_hashes_an_over_long_key_first`.

### BUG-S5: no HMAC-SHA-384, HMAC-SHA-512, HMAC-SHA3-256 or HMAC-SHA3-512
- **Módulo:** std/seal
- **Función:** new `hmac_sha384`, `hmac_sha512`, `hmac_sha3_256`,
  `hmac_sha3_512`
- **Síntoma:** only MD5/SHA-1/SHA-256 were available, so a modern protocol could
  not be implemented with the module.
- **Fix aplicado:** the four variants on top of `_hmac_raw`, all pinned against
  Python's `hmac`.
- **Test de regresión:** `test_hmac_matches_python_for_every_algorithm`.

### BUG-S6: `const_time_eq` used `ord` per byte — **verified, not a bug**
- **Módulo:** std/seal
- **Función:** `const_time_eq`
- **Síntoma (as filed):** the loop could be faster with `bytes of` or a C block.
- **Veredicto:** the comparison is already O(n), branch-free on content and
  length-checked first — the security property that matters. Replacing it with a
  C block would add an `antiquus` for no measurable gain (a 128-byte digest
  compares in a few hundred nanoseconds), and moving it changes nothing for a
  caller. It is left as the reviewed Pengu implementation.
- **Test de regresión:** the internal and external `const_time_eq` cases pin the
  behaviour; `digest_compare` builds on it.

### BUG-S7: `crc32_file` read the whole file into memory
- **Módulo:** std/seal
- **Función:** `crc32_file`
- **Síntoma:** the file was loaded through `archivum.read_file` and then
  checksummed, so a 4 GiB file needed 4 GiB of RAM.
- **Causa raíz:** the helper was written on top of the whole-file reader while
  the digest `*_file` family already streamed inside the runtime.
- **Impacto:** an OOM (or a very slow swap death) on exactly the files a checksum
  is for.
- **Fix aplicado:** `_crc32_file` streams the file in 64 KiB chunks with zlib's
  `crc32(seed, …)`, and every new algorithm's `*_file` helper streams the same
  way (`_sha2_op` / `_sha3_op` / `_blake2_op` `OP_FILE_HEX`).
- **Test de regresión:**
  `tests/stdlib/test_seal.py::test_crc32_file_streams_a_large_file` (300 000
  bytes) and `::test_file_digests_match_the_one_shot` (200 000 bytes across eight
  algorithms).

### BUG-S8: no streaming digest or MAC API
- **Módulo:** std/seal
- **Función:** new `HashState` and `HmacState` (+ `hash_update`, `hash_finalize`,
  `hash_finalize_raw`)
- **Síntoma:** every digest needed the whole input in memory; there was no
  `update`/`finalize` pair.
- **Causa raíz:** the 2.0.0 module only wrapped the runtime's one-shot bridges.
- **Impacto:** hashing a stream (a download, a socket, a generated document) was
  impossible without buffering it all.
- **Fix aplicado:** `HashState` owns a 512-byte engine buffer and mutates it in
  place through a `ref` (`OP_INIT` / `OP_UPDATE` / `OP_FINAL_HEX` /
  `OP_FINAL_RAW`), so an `update` allocates nothing. Constructors exist for all
  twelve algorithms. `HmacState` buffers the chunks and folds them once at
  `finalize`.
- **Test de regresión:** internal `test "HashState streaming equals the one-shot
  digest"`, `test "HashState raw output and the module-level spellings work"`,
  `test "HmacState streaming equals the one-shot MAC"`, plus
  `tests/stdlib/test_seal.py::test_hash_state_streams_like_the_one_shot`,
  `::test_hash_state_raw_and_module_level_wrappers` and
  `::test_hmac_state_streams_like_the_one_shot`.

### BUG-S9: SHA-224, SHA-384, SHA-3 and BLAKE2 were missing
- **Módulo:** std/seal
- **Función:** new `sha224`, `sha384`, `sha3_224/256/384/512`, `blake2b`,
  `blake2s` and their `_file` variants
- **Síntoma:** `hash_algos` listed four algorithms and the module could not
  produce a modern digest at all.
- **Causa raíz:** the runtime archive is built from `md5.c`, `sha1.c`,
  `sha256.c` and `sha512.c` only; mbedTLS's SHA-3 source is not compiled in and
  mbedTLS has no BLAKE2 at all. The 2.0.0 module had no way to reach the extra
  algorithms.
- **Fix aplicado:** SHA-224/384 reuse the linked SHA-2 contexts with mbedTLS's
  `is224` / `is384` starts; SHA-3 (Keccak-f[1600]) and BLAKE2b/BLAKE2s are
  embedded as `antiquus` engines in `seal.pengu`, so **`pengu_runtime.h` and
  `pengu_runtime.c` needed no change at all** (the brief's preferred
  "antiquus rather than runtime" route). BLAKE2 takes a configurable digest size
  through a size-aware init opcode.
- **Test de regresión:** internal `test "SHA-3 matches the published digests"`,
  `test "BLAKE2 matches the published digests, including custom digest sizes"`,
  `test "MD5, SHA-1 and the SHA-2 family match the published digests"`, plus the
  external `test_sha3_family_matches_python`,
  `::test_sha3_empty_input_matches_python`,
  `::test_blake2_matches_python_including_digest_sizes` and
  `::test_long_input_crosses_block_boundaries`.

### BUG-S10: gzip and zlib had no compression level
- **Módulo:** std/seal
- **Función:** new `gzip_level`, `zlib_compress_level` (+ `zlib_decompress_auto`)
- **Síntoma:** the runtime bridges are fixed at `Z_DEFAULT_COMPRESSION`, so a
  caller could not trade size for speed (or ask for `0`, store).
- **Causa raíz:** `declare` cannot express `deflateInit2`'s level parameter.
- **Impacto:** no control over the compression/CPU trade-off, which is exactly
  what a server or a packaging step needs.
- **Fix aplicado:** `_gzip_level` and `_zlib_compress_level` call
  `deflateInit2` with the requested level (and the gzip or zlib window bits);
  `zlib_decompress_auto` accepts either wrapper.
- **Test de regresión:** internal `test "gzip and zlib round-trip with every
  level"` and
  `tests/stdlib/test_seal.py::test_gzip_and_zlib_levels_round_trip` (all nine
  levels, both wrappers) and `::test_zlib_decompress_auto_accepts_both_wrappers`.

### BUG-S11 / BUG-S12: `verify_hash` was case-sensitive
- **Módulo:** std/seal
- **Función:** `verify_hash`, `verify_hash_file`, `verify_sha256`,
  `verify_sha512`, `verify_sha1`, `verify_md5`, `verify_hmac_sha256`
- **Síntoma:** an uppercase digest (the spelling `sha256sum` and most tools
  print) never verified.
- **Causa raíz:** `const_time_eq` compares bytes, and nothing normalised the case
  of a hexadecimal digest.
- **Impacto:** interoperability: a checksum copied from a tool's output was
  rejected as if it were wrong.
- **Fix aplicado:** `digest_compare` lowercases both sides (length-checked first,
  so the comparison stays constant-time in the bytes that matter) and every
  `verify_*` helper routes through it.
- **Test de regresión:** internal `test "BUG-S11: verify_hash is
  case-insensitive"` and `tests/stdlib/test_seal.py::test_bug_s11_verify_hash_is_case_insensitive`.

### BUG-S13: `try_gzip` / `try_unzip` returned the legacy `ResultString`
- **Módulo:** std/seal
- **Función:** `try_gzip`, `try_unzip` (+ new `try_gzip_native`,
  `try_unzip_native`)
- **Síntoma:** the failure path used the deprecated `ResultString` wrapper
  instead of the native `result of string to string`.
- **Causa raíz:** the functions predate the native `result` type.
- **Impacto:** inconsistent error handling with the rest of the migrated
  standard library.
- **Fix aplicado:** the native `try_gzip_native` / `try_unzip_native` variants
  are added; the legacy two keep their exact frozen signature and carry a
  `## @deprecated` marker (the brief's §6.2 requires them to keep working, and
  the C ABI/back-compat rule forbids changing their return type in place).
- **Test de regresión:** internal `test "BUG-S13: the legacy and native result
  wrappers agree"` and
  `tests/stdlib/test_seal.py::test_bug_s13_result_wrappers_agree`.

### BUG-S14: `hash_algos` / `is_valid_hash_alg` / `hash_length` knew four algorithms
- **Módulo:** std/seal
- **Función:** `hash_algos`, `is_valid_hash_alg`, `hash_length`
- **Síntoma:** the registry listed `md5`, `sha1`, `sha256`, `sha512` only, so a
  caller could not discover (or validate) the new digests.
- **Causa raíz:** the lists were literals, not derived from a single table.
- **Impacto:** a generic caller rejected a supported algorithm.
- **Fix aplicado:** one algorithm table (`_alg_from_string` / `_alg_name` /
  `_digest_len` / `_block_len`) drives the registry; `hash_algos` now lists
  twelve names, `hash_length` returns the right count for each and `hash_stream`
  dispatches by name.
- **Test de regresión:** internal `test "hash_algos, is_valid_hash_alg and
  hash_length agree"` and `test "hash_stream dispatches by name"`, plus
  `tests/stdlib/test_seal.py::test_hash_algorithm_registry` and
  `::test_hash_stream_dispatches_by_name`.

### BUG-S15: `gzip_file` / `unzip_file` fail silently
- **Módulo:** std/seal
- **Función:** `gzip_file`, `unzip_file`
- **Síntoma:** a failed read, compression or write returns `false` with no
  reason.
- **Veredicto:** the boolean contract is preserved (it is part of the frozen
  API). The audit confirmed there is no path that reports success while leaving
  a partial file, and the ergonomic need is covered by `try_gzip_native` /
  `try_unzip_native` for in-memory payloads and by `archivum.is_writable` when a
  caller wants to check the destination first. Adding a fourth return shape to
  the frozen pair was rejected as API churn.
- **Test de regresión:**
  `tests/stdlib/test_seal.py::test_gzip_file_helpers_round_trip` pins the success
  path and the written bytes.

### BUG-S16: no incremental CRC-32
- **Módulo:** std/seal
- **Función:** new `crc32_update`
- **Síntoma:** `crc32(a + b)` could not be computed from `crc32(a)` and `b`
  without concatenating the payload.
- **Fix aplicado:** `crc32_update(seed, data)` continues the zlib register;
  `_crc32_file` is built on it.
- **Test de regresión:** internal `test "CRC-32 matches zlib and composes
  incrementally"` and `tests/stdlib/test_seal.py::test_crc32_matches_zlib_and_composes`.

### BUG-S17: no streaming HMAC
- **Módulo:** std/seal
- **Función:** new `HmacState`
- **Síntoma:** a MAC over a stream required the whole message in memory.
- **Fix aplicado:** `HmacState` with constructors for the seven keyed digests,
  `update` and `finalize`, pinned against the one-shot functions.
- **Test de regresión:** internal `test "HmacState streaming equals the one-shot
  MAC"` and
  `tests/stdlib/test_seal.py::test_hmac_state_streams_like_the_one_shot`.

### BUG-S18: `hash_length` assumed `lower()` exists — **verified, not a bug**
- **Módulo:** std/seal
- **Función:** `hash_length`, `is_valid_hash_alg`
- **Síntoma (as filed):** `.lower()` might not exist if `scrolls` is not
  imported.
- **Veredicto:** the `enchanting string` block that defines `lower` lives in
  `std.scrolls`, which `seal` imports (and which `cipher` also imports for
  `compare` and `replace_all`). The call resolves in both modules; the internal
  tests exercise it. No change needed.
- **Test de regresión:** `test_hash_algorithm_registry` passes `"SHA3-256"` and
  `"sha512"` (mixed case).

### BUG-S19: `verify_hash` returned `true` for an unknown algorithm with an expected `""`
- **Módulo:** std/seal
- **Función:** `verify_hash`
- **Síntoma (measured on 2.0.0):** `verify_hash("hello", "nope", "")` was
  `true`, because the unknown type left `computed` as `""` and
  `const_time_eq("", "")` is `true`.
- **Causa raíz:** the dispatch fell through to an empty digest and the
  comparison had no "algorithm known" precondition.
- **Impacto:** **a security-relevant false positive**: a caller validating an
  untrusted `hash_type` string accepted anything when the expected digest was
  empty.
- **Fix aplicado:** `verify_hash` maps the name to an `ALG_*` id first, returns
  `false` for an unknown name, and pre-checks the expected length against the
  algorithm's hex length before comparing.
- **Test de regresión:** internal `test "BUG-S19: verify_hash rejects unknown
  algorithms and empty digests"` and
  `tests/stdlib/test_seal.py::test_bug_s19_verify_hash_rejects_unknown_algorithms`.

### BUG-S20: `_hex_to_bytes` returned a fragile binary string
- **Módulo:** std/seal
- **Función:** `_hex_to_bytes` and every binary intermediate
- **Síntoma:** the helper built a string that could contain NULs by
  interpolating it into a growing accumulator, so any future edit that used `+`
  or a `printf`-style path would silently truncate it.
- **Causa raíz:** binary data was carried in an accumulator built for text.
- **Impacto:** latent corruption of every key and MAC that flows through the
  helper.
- **Fix aplicado:** the helper now returns `maybe string` built with the C
  `_concat_parts` (length-based `memcpy`, NUL-safe), and the module's binary
  intermediates (HMAC pads, raw digests, scrypt blocks, random bytes) all use
  the same primitive.
- **Test de regresión:** `test_bug_s2_hmac_is_binary_safe`,
  `test_bug_s3_hex_to_bytes_validates_its_input` and the scrypt/PBKDF2 parity
  tests.

### Extra seal defects found by the audit (not in the brief)
- **BUG-S21 (new): `hash_length` and `verify_hash` disagreed on unknown names.**
  `hash_length("nope")` returned `0` while `is_valid_hash_alg("nope")` was
  `false`; both now derive from one table. *Test:*
  `test_hash_algorithm_registry`.
- **BUG-S22 (new): the module had no CSPRNG-backed randomness.**
  `random_bytes` did not exist; the only generator in the standard library is
  `std.lot`'s `rand()`, which chunk 6 documents as *not* cryptographically
  secure. The new `_random_bytes` reads the operating system CSPRNG
  (`/dev/urandom`, `rand_s` on Windows) and **fails closed** (returns `""`)
  rather than emitting weak bytes. *Test:* internal `test "random_bytes returns
  the requested length and fresh values"` and
  `tests/stdlib/test_seal.py::test_random_bytes_are_fresh_and_correctly_sized`.
- **BUG-S23 (new): a BLAKE2 digest size was not part of the parameter block.**
  The first draft of the new `blake2b`/`blake2s` ignored the requested
  `digest_size` when initialising the state, so a 32-byte BLAKE2b digest was the
  truncated 64-byte one. The Python parity test caught it; the engine now takes
  a size-aware init opcode and the parameter block is built from the real output
  length. *Test:* internal `test "BLAKE2 matches the published digests,
  including custom digest sizes"`.

---

## 3. Bugs the brief listed that were verified as **not** defects

| Brief | Verdict | Evidence |
|---|---|---|
| C3 `\uXXXX` "overflow" for cp ≥ 0x8000 | not a bug | the 16-bit quotient is ≤ 15; the three-byte range is exactly `[0xE0,0xEF]` |
| C10 `NaN`/`Infinity` rejected | intentional | RFC 8259 defines only `true`/`false`/`null`; documented deviation from Python's permissive mode |
| C14 URL-safe decoder accepts both alphabets | not a bug | out-of-alphabet characters were already rejected; the contract is documented |
| S6 `const_time_eq` uses `ord` | not a bug | already O(n) and branch-free on content; a C block would add nothing measurable |
| S15 `gzip_file` reports `false` | preserved contract | the frozen signature returns `bool`; native result variants cover payloads |
| S18 `hash_length` assumes `lower()` | not a bug | `lower` comes from the imported `std.scrolls`; both internal and external tests exercise it |

---

## 4. Out-of-scope findings (compiler / tooling / closed modules)

§5.3 of the brief forbids touching the compiler and every other `std/*.pengu`.
Each finding below is a real defect, is worked around inside this chunk, and is
handed to the next chunk. Documenting it is not ignoring it.

### G-1 (compiler): a constant `chr` inside an interpolated string is folded wrongly
- **Repro A (silent truncation):** `var s as string is "a{(chr 0)}b"` gives a
  two-byte string `ab`; the folded NUL terminates the generated C format string.
  `"a{x}b"` with `x` a variable behaves correctly, so only the *constant* form is
  affected.
- **Repro B (broken C):** `calling parts.push with (chr 34)` emits
  `pengu_string_from_cstr(")` — the constant emitter sees a string that starts
  with `"` and treats it as already quoted (and `chr 92` emits a bare `\`,
  because the C escape function does not escape backslashes).
- **Repro C (wrong bytes):** a constant `chr 200` is emitted as the two UTF-8
  bytes `c2 88`, not the single byte `0xc8`; the runtime `chr` produces one byte.
- **Workaround:** the modules never use a constant `chr` in a binary or
  quote-bearing position; they build the character from an `int` variable
  (`_quote_char`, `_backslash_char`, `nul_byte`, and the test fixtures).
- **Pinned by:** `tests/stdlib/test_cipher.py::test_bug_s2...`-adjacent fixtures
  and every binary-vector test (Base85/Z85/Base58, HMAC with NULs, file digests).

### G-2 (compiler): an `omen` cannot reference itself in a payload
- **Repro:** `omen Tree: Leaf with value as int` + `Node with kids as list of Tree`
  reports `Field 'kids' expected 'list of Tree', got 'list of Tree'` — the
  in-declaration reference resolves to a different `OmenType` instance than the
  finished omen. `ref to Tree` fails the same way; a recursive `rune` works.
- **Workaround:** `JsonValue`'s recursive payloads travel through the wrapper
  runes `JsonArrayNode` / `JsonObjectNode`, declared *after* the omen (their
  fields then resolve against the finished type). `json_value_items` /
  `json_value_pairs` hide the wrapper.
- **Pinned by:** `test "parse_json_value builds the generic tree"` and the whole
  `JsonValue` surface.

### G-3 (compiler): `Module.Variant` type-checks but emits an unmangled C symbol
- **Repro:** with `import std.cipher`, `k == cipher.JsonNumber` compiles but
  produces `error: 'JsonKind_JsonNumber' no se declaró aquí; ¿quiso decir
  'cipher_JsonKind_JsonNumber'?`.
- **Workaround:** spell the variant with its omen (`cipher.JsonKind.JsonNumber`)
  or use the short alias (`JsonNumber`); both emit the right symbol.
- **Pinned by:** `tests/stdlib/test_cipher.py::test_typed_getters_and_json_kind`.

### G-4 (compiler): a module-qualified ritual constructor is not resolved
- **Repro:** `calling seal.HashState.new_sha256` reports *"Type 'seal' has no
  method 'new_sha256'"*, while the exported type name works:
  `calling HashState.new_sha256`.
- **Workaround:** the documented spelling for an importer is the type name.
- **Pinned by:** `tests/stdlib/test_seal.py::test_hash_state_streams_like_the_one_shot`.

### G-5 (language): an instance method cannot be called with an explicit receiver
- **Repro:** `calling Box.bump with (sigil of b), 3` reports `E0034 ... cannot be
  called statically without an instance` unless the method is declared `ritual`.
- **Workaround:** the streaming API is offered both ways: the idiomatic
  `calling h.update with data` / `calling h.finalize` and the module-level
  `hash_update with (sigil of h), data` / `hash_finalize with (sigil of h)`.
- **Pinned by:** `test_hash_state_raw_and_module_level_wrappers`.

### G-6 (`std/scrolls`, closed): `join` / `_concat` is quadratic
- **Repro:** `scrolls._concat` builds its result with `set out is "{out}{part}"`;
  `join` delegates to it. The brief's "use `scrolls.join` to fix the O(n²)
  encoders" therefore **cannot** work.
- **Workaround:** both modules own a C `_concat_parts` that sums the lengths and
  `memcpy`s once. `std.scrolls` should grow the same primitive in a later chunk.
- **Pinned by:** the ``BUG-C1`` timing assertion.

### X-1 (`std/spark`, closed): `parse_float` boxes a `double` in a `maybe float`
- **Repro:** `if x as float is (calling spark.parse_float with "3.5")` prints `0`;
  the runtime boxes `sizeof(double)` bytes and the checker reads a 4-byte
  `float`, so every result is wrong (on a little-endian host it reads the low
  half of the double, which is zero for most values).
- **Impact:** any module that parses a float through `std.spark` is broken
  (`chronicle`'s `strptime` fraction, `lot`'s distribution helpers, user code).
  This is the most serious finding of the chunk and it is outside the chunk's
  scope.
- **Workaround:** `std.cipher` and `std.seal` own strict, bounded number parsers
  and never call `spark.parse_float`. A regression test in the cipher suite pins
  `json_get_float`'s correct behaviour, so the workaround cannot silently
  regress.
- **Hand-off:** fix `pengu_parse_float` in `std/spark.pengu` (allocate
  `sizeof(float)` and store `(float)val`) in the next compiler/module chunk.

### X-2 (`pengu fmt`): antiquus bodies must be flat at column 0
- **Repro:** a body whose C lines are indented (for example macro continuation
  lines) makes the formatter re-indent the `r"""` opener on every run; it never
  converges and `pengu fmt --check` keeps reporting the file.
- **Workaround:** every line inside `r"""…"""` starts at column 0 (the C
  preprocessor does not care), which makes `pengu fmt --check` clean and stable.
- **Pinned by:** the `pengu fmt --check` gate itself.

### X-3 (compiler): `omen` variant names share one global namespace (E0046)
- **Repro:** adding `omen JsonValue` with the brief's variant names collides with
  the frozen `omen JsonKind` (`JsonNull`, `JsonBool`, `JsonString`, `JsonArray`,
  `JsonObject`), so the file does not compile at all.
- **Workaround:** the new omen's variants are `JvNull`, `JvBool`, `JvInt`,
  `JvFloat`, `JvString`, `JvArray`, `JvObject`; the legacy `JsonKind` names are
  untouched (they are the frozen public surface). The deviation is documented in
  `docs/CIPHER_API.md`.
- **Pinned by:** the module compiling at all, plus the `JsonValue` tests.

---

## 5. Summary

| Module | Brief bugs | Verdict `fixed` | Verdict `not a bug / preserved` | Audit additions | Total entries |
|---|---|---|---|---|---|
| `std/cipher` | C1–C24 (24) | 22 (C14's real hole included) | 2 (C3, C10) | 5 (C25–C29) | 29 |
| `std/seal` | S1–S20 (20) | 16 | 4 (S2, S6, S15, S18) | 3 (S21–S23) | 23 |

**46 code fixes in total**: 38 from the brief's own list plus the 8 defects the
audit added (C25–C29, S21–S23).

Out-of-scope findings handed forward: **9** (G-1…G-6, X-1…X-3). The most
important is **X-1**: `std.spark.parse_float` returns zero for every input,
which breaks every float parser in the standard library.

Internal tests: `cipher` **43**, `seal` **24** (`pengu test --entry
std/{cipher,seal}.pengu`, all green). External suites:
`tests/stdlib/test_cipher.py` **44 cases**, `tests/stdlib/test_seal.py` **33
cases** (all green).
