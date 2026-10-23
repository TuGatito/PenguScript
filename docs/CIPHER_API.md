# `std.cipher` — frozen public API contract

> **Status: frozen.** This is the API that the remaining migration chunks
> (`precis`, `invoke`, `ffi`, …) are built against. Changing a signature here is
> a breaking change and must bump `CIPHER_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/cipher.pengu`](../std/cipher.pengu).
> Bugs fixed in this revision: [`BUGS_FIXED_CHUNK7.md`](BUGS_FIXED_CHUNK7.md).

`cipher` owns byte encodings and JSON: Base64 (standard/URL/unpadded), Hex,
Base32, Base85 (RFC 1924), Z85 (ZeroMQ), Base58 (Bitcoin), RFC 3986
percent-encoding, CRC-32, string escaping, the legacy flat JSON surface and the
generic `CipherJsonValue` tree. It imports `std.spark`, `std.archivum`,
`std.scrolls` and `std.oracle`, and declares one runtime bridge
(`pengu_map_keys_string`) before setting `insignia cipher_`.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every parameter | borrowed, read-only | never `banish` |
| scalar returns (`int`, `bool`, `u32`) | plain value | never `banish` |
| `string` returns (encoders, serializers, escapes, …) | freshly allocated | `banish` |
| `maybe T` returns (`decode_*`, `parse_*`) | owns its payload | `banish` on the payload after unpacking |
| `list` / `map` returns (`parse_json_array`, `json_value_items`, …) | freshly allocated | `banish` |
| `CipherJsonValue` returns (`parse_json_value`, `json_value_*`) | freshly allocated tree | `banish` |

## Constants

| Constant | Type | Value | Meaning |
|---|---|---|---|
| `CIPHER_VERSION` | `string` | `"2.1.0"` | Revision of the **cipher API**. |
| `HEX_DIGITS` | `string` | `0123456789abcdef` | Lowercase hex digits. |
| `HEX_UPPER` | `string` | `0123456789ABCDEF` | Uppercase hex digits (percent-encoding). |

`BASE85_ALPHABET` and `Z85_ALPHABET` are no longer constants: both alphabets
contain `{`, which a PenguScript string literal cannot carry, so they are
assembled once by the cached private weaves `_base85_alphabet` / `_z85_alphabet`.

## Native runtime declarations

| Declaration | Signature |
|---|---|
| `pengu_map_keys_string` | `(ref to map of string to string) -> list of string` |

## Internal C blocks (`antiquus`)

| Block | Signature | Purpose |
|---|---|---|
| `_concat_parts` | `(list of string) -> string` | O(n) binary-safe join (BUG-C1) |
| `_zero_bytes` | `(int) -> string` | owned zeroed binary buffer |
| `_b64_encode_raw` / `_b64_decode_raw` | `(string, bool, bool) -> string` / `(string, bool) -> maybe string` | linear Base64 (BUG-C1/C14/C15) |
| `_hex_encode_raw` / `_hex_decode_raw` | `(string) -> string` / `(string) -> maybe string` | linear Hex |
| `_b32_encode_raw` / `_b32_decode_raw` | `(string) -> string` / `(string) -> maybe string` | linear Base32 (BUG-C19) |
| `_json_escape_raw` | `(string) -> string` | linear JSON escaping |
| `_utf8_validate` / `_utf8_valid_seq` / `_utf8_seq_len` / `_utf8_encode_cp` | — | UTF-8 validation and encoding (BUG-C2/C4) |
| `_crc32_raw` | `(string) -> u32` | table-less IEEE CRC-32 |

## Base64

| Symbol | Signature | Semantics |
|---|---|---|
| `cb64_char` | `(int) -> string` | 6-bit value → alphabet character; `=` outside `0..63` |
| `cb64_val` | `(string) -> int` | one character → `0..63`, `-1` for `=`, `-2` otherwise (rejects multi-character input) |
| `encode_base64` | `(string) -> string` | standard alphabet, padded |
| `encode_base64_bytes` | `(string) -> string` | alias of `encode_base64` |
| `decode_base64` | `(string) -> maybe string` | standard alphabet; padding must close the stream |
| `is_base64` | `(string) -> bool` | `decode_base64` succeeded |
| `encode_base64_url` | `(string) -> string` | URL alphabet (`-`/`_`), unpadded |
| `decode_base64_url` | `(string) -> maybe string` | accepts both alphabets, padded or not; `len % 4 == 1` is `none` |
| `encode_base64_nopad` / `encode_base64_unpadded` | `(string) -> string` | standard alphabet, padding stripped |
| `decode_base64_nopad` / `decode_base64_unpadded` | `(string) -> maybe string` | standard alphabet, padding restored |
| `base64_length` | `(int) -> int` | `4*ceil(n/3)`, `0` for `n <= 0` |

## Hex and Base32

| Symbol | Signature | Semantics |
|---|---|---|
| `_hex_val` | `(string) -> int` | one hex digit → `0..15`, else `-1` |
| `encode_hex` | `(string) -> string` | lowercase hex |
| `decode_hex` | `(string) -> maybe string` | rejects odd length and non-hex digits |
| `_b32_char` / `_b32_val` | `(int) -> string` / `(string) -> int` | Base32 alphabet |
| `encode_base32` | `(string) -> string` | uppercase, padded, RFC 4648 |
| `decode_base32` | `(string) -> maybe string` | case-insensitive; padding must close the stream; unused tail bits must be zero |

## Base85, Z85 and Base58

| Symbol | Signature | Semantics |
|---|---|---|
| `encode_base85` | `(string) -> string` | RFC 1924; partial groups zero-padded then truncated (`base64.b85encode`) |
| `decode_base85` | `(string) -> maybe string` | missing digits refilled with the alphabet's last character (`~`), as CPython does; `len % 5 == 1` is `none` |
| `encode_base85_z85` | `(string) -> string` | ZeroMQ Z85; `""` when the length is not a multiple of four |
| `decode_base85_z85` | `(string) -> maybe string` | length must be a multiple of five |
| `encode_base58` | `(string) -> string` | Bitcoin Base58; leading zero bytes become leading `1` |
| `decode_base58` | `(string) -> maybe string` | leading `1`s become zero bytes |

## URL encoding and CRC-32

| Symbol | Signature | Semantics |
|---|---|---|
| `encode_url` | `(string) -> string` | keeps `A–Z a–z 0–9 - _ . ~`; everything else is `%XX` with **uppercase** hex (`urllib.parse.quote(s, safe="")`) |
| `decode_url` | `(string) -> maybe string` | `+` stays a literal plus; a truncated or non-hex `%` escape is `none` |
| `crc32_hex` | `(string) -> string` | IEEE 802.3 CRC-32 as 8 lowercase hex digits |

## JSON strings

| Symbol | Signature | Semantics |
|---|---|---|
| `json_escape` | `(string) -> string` | RFC 8259 escaping; bytes ≥ `0x80` pass through (valid UTF-8) |
| `json_unescape` | `(string) -> string` | lenient 2.0.0 decoding; surrogate pairs combined; unknown escapes kept |
| `json_skip_ws` | `(string, ref to int) -> void` | advance past JSON whitespace |
| `json_read_str` | `(string, ref to int) -> string` | lenient quoted-string reader (2.0.0 contract) |
| `json_read_value` | `(string, ref to int) -> string` | raw value text; a composite **keeps both delimiters** |
| `json_is_literal` | `(string) -> bool` | `{…}`, `[…]`, a number, or `true`/`false`/`null` |

## Legacy flat JSON

| Symbol | Signature | Semantics |
|---|---|---|
| `parse_json` | `(string) -> maybe map of string to string` | one JSON object; values are raw JSON text (strings unquoted); strict |
| `stringify_json` | `(map of string to string) -> maybe string` | compact, **sorted keys** |
| `pretty_json` | `(map of string to string, int = 2) -> maybe string` | indented, sorted keys |
| `parse_value` | `(string) -> maybe string` | one value, whole input validated |
| `stringify_value` | `(string) -> maybe string` | identity passthrough |
| `parse_json_array` | `(string) -> maybe list of string` | one JSON array; strict |
| `stringify_json_array` | `(list of string) -> maybe string` | compact array |
| `read_json_array_file` | `(string) -> maybe list of string` | file → array |
| `json_get` / `json_get_or` / `json_has` | see §Typed getters | flat access |
| `json_get_int` | `(map, string) -> maybe int` | `spark.parse_int` |
| `json_get_float` | `(map, string) -> maybe float` | strict, bounded JSON number (32-bit float) |
| `json_get_bool` | `(map, string) -> maybe bool` | exact `true`/`false` |
| `json_get_string` | `(map, string) -> maybe string` | raw text |
| `json_deep_clone` | `(map) -> map` | copy of the flat map (values are immutable strings) |
| `json_merge` | `(map, map) -> map` | `b` wins |
| `json_path` | `(map, string) -> maybe string` | `user.name`, `users[0].name`; final string unquoted, other values as compact JSON |
| `json_parse_at` | `(map, string) -> maybe map` | traverse then parse as an object |
| `is_valid_json` | `(string) -> bool` | valid object or array |
| `is_valid_json_value` | `(string) -> bool` | any single valid value |
| `read_json_file` / `write_json_file` / `write_json_file_pretty` | file helpers | via `std.archivum` |

## Generic `CipherJsonValue`

| Symbol | Signature | Semantics |
|---|---|---|
| `CipherJsonValue` (omen) | `JvNull`, `JvBool with value`, `JvInt with value`, `JvFloat with value`, `JvString with value`, `JvArray with node`, `JvObject with node` | the `json.loads` tree |
| `JsonArrayNode` / `JsonObjectNode` (rune) | `items as list of CipherJsonValue` / `pairs as map of string to CipherJsonValue` | recursive payload wrappers (see G-2) |
| `parse_json_value` | `(string) -> maybe CipherJsonValue` | strict parser, UTF-8 checked, surrogate-aware |
| `parse_json_to_map` / `parse_json_to_list` | `(string) -> maybe map of string to CipherJsonValue` / `… list of CipherJsonValue` | typed roots |
| `stringify_json_value` | `(CipherJsonValue) -> string` | compact, sorted keys |
| `stringify_json_value_pretty` | `(CipherJsonValue, int = 2) -> string` | indented |
| `json_dumps_canonical` | `(CipherJsonValue) -> string` | compact, sorted keys (RFC 8785 shape; 32-bit numbers) |
| `json_value_type` | `(CipherJsonValue) -> string` | `"null"`, `"bool"`, `"int"`, `"float"`, `"string"`, `"array"`, `"object"` |
| `json_value_to_string` | `(CipherJsonValue) -> string` | scalar text / compact JSON |
| `json_value_get` | `(CipherJsonValue, string) -> maybe CipherJsonValue` | object member |
| `json_value_at` | `(CipherJsonValue, int) -> maybe CipherJsonValue` | array element (negative counts from the end) |
| `json_value_as_int` / `_as_float` / `_as_string` / `_as_bool` | `(CipherJsonValue) -> maybe T` | coercion (see `docs/BUGS_FIXED_CHUNK7.md` for the exact table) |
| `json_value_len` | `(CipherJsonValue) -> int` | array/object length, string byte length, `0` for scalars |
| `json_value_items` / `json_value_pairs` | `(CipherJsonValue) -> maybe list of CipherJsonValue` / `… map of string to CipherJsonValue` | fresh copies |
| `json_value_is_null` / `_is_bool` / `_is_int` / `_is_float` / `_is_string` / `_is_array` / `_is_object` | `(CipherJsonValue) -> bool` | predicates |
| `json_value_deep_clone` | `(CipherJsonValue) -> CipherJsonValue` | independent copy |
| `json_value_equal` | `(CipherJsonValue, CipherJsonValue) -> bool` | deep equality; `int`/`float` compare numerically |
| `json_value_merge` | `(CipherJsonValue, CipherJsonValue) -> CipherJsonValue` | shallow object merge |
| `json_value_merge_patch` | `(CipherJsonValue, CipherJsonValue) -> CipherJsonValue` | RFC 7396 |
| `json_pointer_get` | `(CipherJsonValue, string) -> maybe CipherJsonValue` | RFC 6901 |
| `json_patch` | `(CipherJsonValue, CipherJsonValue) -> result of CipherJsonValue to string` | RFC 6902 (`add`, `remove`, `replace`, `move`, `copy`, `test`) |

## Typed serializers

| Symbol | Signature | Semantics |
|---|---|---|
| `stringify_json_map_int` / `_float` / `_bool` | `(map of string to T) -> string` | compact object, sorted keys |

## Enchantments (`enchanting string`)

| Method | Semantics |
|---|---|
| `to_base64` / `from_base64`, `to_base64_url` | Base64 round-trips |
| `to_hex` / `from_hex`, `to_base32` / `from_base32` | Hex and Base32 round-trips |
| `to_base85` / `from_base85`, `to_base58` / `from_base58` | Base85 and Base58 round-trips |
| `to_url` / `from_url` | percent-encoding |
| `to_crc32_hex` | IEEE CRC-32 as hex |

## Documented deviations

1. **`CipherJsonValue` variant names are `Jv*`.** The frozen `JsonKind` omen already
   owns `JsonNull`, `JsonBool`, `JsonString`, `JsonArray` and `JsonObject`, and
   omen variants live in a single global namespace (compiler finding G-3 in the
   bug doc). Renaming the *legacy* names would break the frozen contract, so the
   new omen uses the `Jv` prefix.
2. **Object members are serialized in sorted key order.** A PenguScript `map`
   cannot remember insertion order, so the module sorts; Python preserves
   insertion order. Serialization is therefore deterministic and byte-stable,
   but not insertion-ordered.
3. **`NaN` / `Infinity` are rejected.** RFC 8259 does not define them; Python's
   `json.loads` accepts them by default (`allow_nan=True`). Use `seal` or a
   sentinel string instead.
4. **Numbers are 32-bit.** `float` is `f32`: values outside ±3.4e38 saturate to
   infinity, `json_value_len` counts a string's *bytes*, and `_parse_json_float`
   clamps the exponent to 60 steps (constant time).
5. **`decode_base64_url` accepts the standard alphabet too.** Preserved from
   2.0.0 and documented; the decoder still rejects every character outside both
   alphabets.
6. **`crc32_hex` lives here, not in `seal`.** `cipher` must not pull mbedTLS, so
   the checksum has its own table-less C implementation. It matches
   `zlib.crc32(data) & 0xffffffff`.
