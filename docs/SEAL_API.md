# `std.seal` — frozen public API contract

> **Status: frozen.** This is the API that the remaining migration chunks
> (`precis`, `invoke`, `ffi`, …) are built against. Changing a signature here is
> a breaking change and must bump `SEAL_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/seal.pengu`](../std/seal.pengu).
> Bugs fixed in this revision: [`BUGS_FIXED_CHUNK7.md`](BUGS_FIXED_CHUNK7.md).

`seal` owns checksums, cryptographic digests, HMACs, key derivation and
compression. It imports `std.spark`, `std.oracle`, `std.scrolls` and
`std.archivum`, declares the `pengu_c_seal_*` runtime bridges and then sets
`insignia seal_`. `include` directives pull the mbedTLS private digest headers
and `zlib.h` into the bundle at file scope (the runtime *header* only declares
the seal bridges).

## Which digests are safe

| Family | Collision resistance | Use |
|---|---|---|
| SHA-256, SHA-384, SHA-512, SHA3-*, BLAKE2b, BLAKE2s | secure | signatures, MACs, KDFs |
| SHA-224 | secure (reduced output) | interop with legacy protocols |
| MD5, SHA-1 | **broken** | checksums and interop only, never new signatures |
| CRC-32 | not a hash | accidental-corruption detection only |

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every parameter | borrowed, read-only | never `banish` |
| scalar returns (`u32`) | plain value | never `banish` |
| `string` returns (digests, MACs, compressed streams, derived keys) | freshly allocated | `banish` |
| `maybe T` returns (`gzip`, `unzip`, `*_file`, `crc32_file`) | owns its payload | `banish` on the payload after unpacking |
| `HashState` / `HmacState` | owns its internal buffer | `banish` the rune |
| `ResultString` returns (`try_gzip` / `try_unzip`) | legacy wrapper | as `std.oracle` documents |

## Constants

| Constant | Type | Value | Meaning |
|---|---|---|---|
| `SEAL_VERSION` | `string` | `"2.1.0"` | Revision of the **seal API**. |
| `CRC32_POLYNOMIAL` | `int` | `3988292384` | IEEE 802.3 polynomial (`0xEDB88320`). |
| `HASH_STATE_BYTES` | `int` | `512` | Bytes reserved per streaming state. |
| `ALG_MD5` … `ALG_BLAKE2S` | `int` | `0` … `11` | Algorithm ids (see the table below). |
| `OP_INIT`, `OP_INIT_SIZE`, `OP_UPDATE`, `OP_FINAL_HEX`, `OP_FINAL_RAW`, `OP_FILE_HEX` | `int` | `0`, `5`, `1`, `2`, `3`, `4` | Engine opcodes (private contract). |

| Id | `ALG_*` | Digest bytes | HMAC block |
|---|---|---|---|
| 0 | `ALG_MD5` | 16 | 64 |
| 1 | `ALG_SHA1` | 20 | 64 |
| 2 | `ALG_SHA256` | 32 | 64 |
| 3 | `ALG_SHA512` | 64 | 128 |
| 4 | `ALG_SHA224` | 28 | 64 |
| 5 | `ALG_SHA384` | 48 | 128 |
| 6 | `ALG_SHA3_224` | 28 | 144 |
| 7 | `ALG_SHA3_256` | 32 | 136 |
| 8 | `ALG_SHA3_384` | 48 | 104 |
| 9 | `ALG_SHA3_512` | 64 | 72 |
| 10 | `ALG_BLAKE2B` | 64 (1–64) | 128 |
| 11 | `ALG_BLAKE2S` | 32 (1–32) | 64 |

## Native runtime declarations

| Declaration | Signature |
|---|---|
| `pengu_c_seal_crc32` | `(string) -> u32` |
| `pengu_c_seal_md5` / `_sha1` / `_sha256` / `_sha512` | `(string) -> string` |
| `pengu_c_seal_gzip` / `_unzip` | `(string) -> maybe string` |
| `pengu_c_seal_zlib_compress` / `_zlib_decompress` | `(string) -> maybe string` |
| `pengu_c_seal_hash_file` | `(string, string) -> maybe string` |

`pengu_runtime.h` and `pengu_runtime.c` are **unchanged** by this chunk: the new
algorithms live in `seal.pengu` as `antiquus` engines.

## Internal C blocks (`antiquus`)

| Block | Purpose |
|---|---|
| `_blob_new`, `_concat_parts`, `_xor_bytes` | binary buffers, O(n) join, byte XOR |
| `_sha2_op` | MD5, SHA-1, SHA-224/256/384/512: init/update/final/hex/raw/file |
| `_sha3_op` | Keccak-f[1600] engine for SHA3-224/256/384/512 |
| `_blake2_op` | parameterised BLAKE2b/BLAKE2s engine, including digest size |
| `_salsa20_8` | Salsa20/8 core, used by scrypt |
| `_gzip_level`, `_zlib_compress_level` | `deflateInit2` with an explicit level |
| `_crc32_update`, `_crc32_file` | incremental CRC-32 and 64 KiB file streaming |
| `_random_bytes` | OS CSPRNG (`/dev/urandom`, `rand_s`), fails closed |

## CRC-32

| Symbol | Signature | Semantics |
|---|---|---|
| `crc32` | `(string) -> u32` | full unsigned IEEE checksum, equal to `zlib.crc32` |
| `crc32_update` | `(u32, string) -> u32` | continues a checksum (`crc32(a+b) == crc32_update(crc32_update(0,a),b)`) |
| `crc32_file` | `(string) -> maybe u32` | streamed in 64 KiB chunks |

## Digests

| Symbol | Signature | Semantics |
|---|---|---|
| `md5`, `sha1`, `sha256`, `sha512` | `(string) -> string` | runtime bridges (frozen, fastest) |
| `sha224`, `sha384` | `(string) -> string` | SHA-2 completion |
| `sha3_224`, `sha3_256`, `sha3_384`, `sha3_512` | `(string) -> string` | SHA-3 |
| `blake2b` | `(string, int = 64) -> string` | BLAKE2b with a `1..64` digest size (`""` outside) |
| `blake2s` | `(string, int = 32) -> string` | BLAKE2s with a `1..32` digest size (`""` outside) |
| `md5_file`, `sha1_file`, `sha256_file`, `sha512_file` | `(string) -> maybe string` | runtime file streaming |
| `sha224_file`, `sha384_file`, `sha3_*_file`, `blake2b_file`, `blake2s_file` | `(string) -> maybe string` | 64 KiB engine streaming |
| `hash_stream` | `(string, string) -> string` | dispatch by name; `""` for an unknown name |

## HMAC (RFC 2104)

| Symbol | Signature | Semantics |
|---|---|---|
| `hmac_sha256`, `hmac_sha256_hex` | `(string, string) -> string` | 64 hex characters |
| `hmac_sha1` | `(string, string) -> string` | 40 hex characters |
| `hmac_md5` | `(string, string) -> string` | 32 hex characters |
| `hmac_sha384` | `(string, string) -> string` | 96 hex characters |
| `hmac_sha512` | `(string, string) -> string` | 128 hex characters |
| `hmac_sha3_256`, `hmac_sha3_512` | `(string, string) -> string` | SHA-3 keyed MACs |

A key longer than the algorithm's block size is hashed first; keys and messages
may contain NULs.

## Key derivation

| Symbol | Signature | Semantics |
|---|---|---|
| `pbkdf2_hmac_sha256` | `(string, string, int, int) -> string` | PBKDF2, returns hex; `""` when `iterations < 1` or `key_len <= 0` |
| `pbkdf2_hmac_sha512` | `(string, string, int, int) -> string` | same, SHA-512 |
| `hkdf_sha256` | `(string, string, string, int) -> string` | RFC 5869; an empty salt means a zero salt of digest length |
| `scrypt` | `(string, string, int, int, int, int) -> string` | RFC 7914, returns hex; `n` a power of two, `1..64` for `r`/`p`, working set capped at 1 MiB |

## Verification

| Symbol | Signature | Semantics |
|---|---|---|
| `const_time_eq` | `(string, string) -> bool` | constant-time, length-checked first |
| `digest_compare` | `(string, string) -> bool` | case-insensitive constant-time comparison |
| `verify_hash` | `(string, string, string) -> bool` | algorithm by name; `false` for an unknown name or a wrong-length digest |
| `verify_hash_file` | `(string, string, string) -> bool` | streamed |
| `verify_hmac_sha256`, `verify_sha256`, `verify_sha512`, `verify_sha1`, `verify_md5` | `(string, string) -> bool` (HMAC: `(string, string, string)`) | case-insensitive wrappers |
| `hash_algos` | `() -> list of string` | the twelve supported names |
| `is_valid_hash_alg` | `(string) -> bool` | case-insensitive |
| `hash_length` | `(string) -> int` | hex length, `0` for an unknown name |

## Compression

| Symbol | Signature | Semantics |
|---|---|---|
| `gzip` / `unzip` | `(string) -> maybe string` | RFC 1952 at the default level; the inflater accepts gzip or zlib |
| `gzip_level` | `(string, int) -> maybe string` | level `1..9`, `0` stores, anything else default |
| `zlib_compress` / `zlib_decompress` | `(string) -> maybe string` | RFC 1950 |
| `zlib_compress_level` | `(string, int) -> maybe string` | explicit level |
| `zlib_decompress_auto` | `(string) -> maybe string` | accepts either wrapper |
| `gzip_file`, `unzip_file` | `(string, string) -> bool` | file → file |
| `gzip_file_to_bytes`, `unzip_file_to_bytes` | `(string) -> maybe string` | file → memory |
| `zlib_compress_file`, `zlib_decompress_file` | `(string) -> maybe string` | file → memory |
| `try_gzip`, `try_unzip` | `(string) -> ResultString` | legacy wrapper (`## @deprecated`) |
| `try_gzip_native`, `try_unzip_native` | `(string) -> result of string to string` | native result |

## Streaming

| Symbol | Signature | Semantics |
|---|---|---|
| `HashState` (rune) | `_state`, `_alg` | one engine buffer, mutated in place |
| `HashState.new_md5`, `new_sha1`, `new_sha224`, `new_sha256`, `new_sha384`, `new_sha512`, `new_sha3_224`, `new_sha3_256`, `new_sha3_384`, `new_sha3_512`, `new_blake2b`, `new_blake2s` | `() -> HashState` (ritual) | constructors |
| `h.update` | `(string) -> void` | absorbs a chunk |
| `h.finalize` / `h.finalize_raw` | `() -> string` | closes the state; hex or raw bytes |
| `h.algorithm` | `() -> string` | the algorithm name |
| `hash_update` | `(ref to HashState, string) -> void` | module-level spelling |
| `hash_finalize` / `hash_finalize_raw` | `(ref to HashState) -> string` | module-level spelling |
| `HmacState` (rune) | `_key`, `_alg`, `_parts` | buffers the message, folds once |
| `HmacState.new_md5`, `new_sha1`, `new_sha256`, `new_sha384`, `new_sha512`, `new_sha3_256`, `new_sha3_512` | `(string) -> HmacState` (ritual) | keyed constructors |
| `m.update` / `m.finalize` / `m.algorithm` | as `HashState` | |

## Randomness

| Symbol | Signature | Semantics |
|---|---|---|
| `random_bytes` | `(int) -> string` | OS CSPRNG; `""` (fail closed) when the entropy source is unavailable |
| `random_token_hex` | `(int) -> string` | the same bytes as `2n` lowercase hex characters |

## Hex helpers

| Symbol | Signature | Semantics |
|---|---|---|
| `_hex_to_bytes` | `(string) -> maybe string` | rejects odd lengths and non-hex digits |
| `hex_to_bytes` | `(string) -> maybe string` | public alias |
| `_hex_to_bytes_lenient` | `(string) -> string` | the 2.0.0 behaviour (`## @deprecated`) |

## Enchantments (`enchanting string`)

| Method | Semantics |
|---|---|
| `to_md5`, `to_sha1`, `to_sha224`, `to_sha256`, `to_sha384`, `to_sha512` | hex digests |
| `to_sha3_256`, `to_blake2b` | hex digests |
| `to_crc32` | IEEE checksum as `u32` |
| `to_gzip` / `from_gzip`, `to_zlib` / `from_zlib` | compression |

## Documented deviations

1. **HMAC uses one Pengu implementation over a raw-digest engine.** The pads are
   real bytes and the concatenation is O(n); a caller cannot observe a
   difference from a C implementation except that it is portable.
2. **SHA-224/384 and SHA-3/BLAKE2 live in `seal.pengu`, not in the runtime.** The
   brief permits either; embedding them as `antiquus` keeps `pengu_runtime.h`
   binary-compatible and byte-identical.
3. **`scrypt` caps the working set at 1 MiB** (`128*r*p <= 1048576`) and rejects
   larger parameters with `""`. A future revision may add a `maxmem` parameter;
   adding one now would change the frozen signature.
4. **`pbkdf2_*`, `hkdf_*` and `scrypt` return hex**, not raw bytes, so their
   results are directly comparable with Python's `.hex()`. The raw forms are
   private (`_pbkdf2_raw`, `_hkdf_raw`).
5. **`verify_hash` is case-insensitive.** The brief asked for it; Python's
   `hmac.compare_digest` does not normalise, so this is intentionally more
   forgiving than the reference.
6. **`try_gzip` / `try_unzip` keep their legacy `ResultString` signature** (the
   frozen contract) while `try_gzip_native` / `try_unzip_native` return the
   native `result of string to string`.
7. **Randomness fails closed.** An unavailable CSPRNG yields `""`; the module
   never falls back to `rand()`.
