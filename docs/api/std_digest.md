# std.digest

> Source: `std/digest.pengu`

std/digest.pengu — cryptographic and non-cryptographic digests.

`std.cipher` covers CRC-32 and encodings; the compiler's cache, lockfile and
TCC verification need SHA-256, which CRC-32 cannot replace.  This module is
intentionally small and dependency-free: the block function is embedded C
(the same policy as `std.cipher`), the public surface is PenguScript, and the
only allocation is the returned string.

## Example
```pengu
import std.digest
import std.spark

weave main into int:
    let h as string is calling digest.sha256_hex with "abc"
    calling spark.println with h
    banish h
    return 0
```

## Memory
`sha256_hex`, `sha256_raw` and `fnv1a64` return owned strings where
applicable.  `sha256_file` returns a `maybe string` whose payload is owned.
Release strings with `banish`; integers need no release.

## Design notes
- **Raw + hex.** `sha256_raw` returns the 32-byte digest (binary-safe, so it
  can be embedded in a cache key); `sha256_hex` is the lowercase-hex view.
- **File hashing reuses the byte path.** `sha256_file` reads through
  `std.archivum.read_bytes`, which is already binary-safe, so there is one
  SHA-256 implementation rather than a second streaming one.
- **FNV-1a is 64-bit.** It is for hash tables and non-security cache shards;
  never use it where SHA-256 is required.

---

### `DIGEST_VERSION`

> **DIGEST_VERSION** : string

 std/digest.pengu — cryptographic and non-cryptographic digests.

 `std.cipher` covers CRC-32 and encodings; the compiler's cache, lockfile and
 TCC verification need SHA-256, which CRC-32 cannot replace.  This module is
 intentionally small and dependency-free: the block function is embedded C
 (the same policy as `std.cipher`), the public surface is PenguScript, and the
 only allocation is the returned string.

 ## Example
 ```pengu
 import std.digest
 import std.spark

 weave main into int:
     let h as string is calling digest.sha256_hex with "abc"
     calling spark.println with h
     banish h
     return 0
 ```

 ## Memory
 `sha256_hex`, `sha256_raw` and `fnv1a64` return owned strings where
 applicable.  `sha256_file` returns a `maybe string` whose payload is owned.
 Release strings with `banish`; integers need no release.

 ## Design notes
 - **Raw + hex.** `sha256_raw` returns the 32-byte digest (binary-safe, so it
   can be embedded in a cache key); `sha256_hex` is the lowercase-hex view.
 - **File hashing reuses the byte path.** `sha256_file` reads through
   `std.archivum.read_bytes`, which is already binary-safe, so there is one
   SHA-256 implementation rather than a second streaming one.
 - **FNV-1a is 64-bit.** It is for hash tables and non-security cache shards;
   never use it where SHA-256 is required.

### `sha256_raw`

> **sha256_raw**(data: string) -> string

 Returns the 32 raw SHA-256 bytes of `data`.

 ## Memoria
 The returned string owns a 32-byte buffer; release it with `banish`.

### `_digest_hex_of_raw`

> **_digest_hex_of_raw**(raw: string) -> string

 Returns the lowercase hexadecimal SHA-256 digest of `data`.

 ## Memoria
 The returned string owns its buffer; release it with `banish`.

### `sha256_hex`

> **sha256_hex**(data: string) -> string

_Undocumented._

### `HMAC_BLOCK`

> **HMAC_BLOCK** : int

 HMAC block size in bytes (RFC 2104; SHA-256 uses 64).

### `HMAC_IPAD`

> **HMAC_IPAD** : int

 Inner padding byte for HMAC (`0x36`).

### `HMAC_OPAD`

> **HMAC_OPAD** : int

 Outer padding byte for HMAC (`0x5c`).

### `hmac_sha256_raw`

> **hmac_sha256_raw**(key: string, message: string) -> string

 Returns the raw 32-byte HMAC-SHA-256 of `message` under `key` (RFC 2104).

 ## Memoria
 The returned string owns a 32-byte buffer; release it with `banish`.

### `hmac_sha256_hex`

> **hmac_sha256_hex**(key: string, message: string) -> string

 Returns the lowercase hexadecimal HMAC-SHA-256 of `message` under `key`.

 ## Memoria
 The returned string owns its buffer; release it with `banish`.

### `sha256_file`

> **sha256_file**(path: string) -> maybe string

 Returns the SHA-256 hex digest of the file at `path`.

 ## Retorno
 `some hex` when the file can be read, `maybe none` otherwise.

 ## Memoria
 The payload is owned; release it with `banish`.

### `DIGEST_HEX`

> **DIGEST_HEX** : string

 Lowercase hexadecimal digits, indexed by nibble value.

### `_digest_hex_digit`

> **_digest_hex_digit**(n: int) -> string

 Maps a nibble (0-15) to its lowercase hex character.

### `_sha256_raw`

> **_sha256_raw**(data: string) -> string

 One-shot SHA-256 of a PenguString's exact bytes (embedded NULs included).

 ## Motivo
 The block function needs 32-bit rotate/shift arithmetic, endian-safe message
 padding and a fixed K table.  Expressing that in PenguScript would require
 explicit 64-bit masking around every addition; C already has the unsigned
 wraparound semantics SHA-256 is defined over.

 ## Memoria
 Allocates a temporary padded message and the 32-byte result; the temporary
 is freed before returning and the result is owned by the caller.

### `fnv1a64`

> **fnv1a64**(data: string) -> u64

 Returns the 64-bit FNV-1a hash of `data`.

 ## Memoria
 Allocates nothing; the hash is a plain `u64`.

### `_fnv1a64`

> **_fnv1a64**(data: string) -> u64

_Undocumented._

