# std.compressus

> Source: `std/compressus.pengu`

std/compressus.pengu — gzip, zlib and raw deflate with explicit ownership.

`std.compressus` wraps the vendored `std_c/miniz.h` + `std_c/miniz.c`
(miniz 3.1.2, public domain / Unlicense) and adds the one thing miniz does
not implement: the **gzip** container (RFC 1952). The result is a small,
dependency-free compression module that reads and writes the same bytes as
Python's `gzip`/`zlib`, Zig's `std.compress` and Odin's `core:compress`.

## Formats

| Format | Magic | Checksum | Use it for |
|---|---|---|---|
| `Gzip` | `1f 8b` | CRC-32 + ISIZE trailer | files (`.gz`), HTTP `Content-Encoding: gzip`, `pengu add` tarballs |
| `Zlib` | `78 xx` | Adler-32 trailer | protocols that specify zlib (some HTTP, PNG `IDAT`) |
| `RawDeflate` | none | none | streams that already carry framing/length (ZIP members, WebSocket permessage-deflate) |

Every format is a **byte-exact** standard: gzip output opens with `gzip -d`
and `gzip.decompress`, zlib output opens with `zlib.decompress`, and both are
verified by `tests/compat/test_compressus_vs_python.py`.

## Quick start

```pengu
import std.compressus
import std.spark

weave main into int:
    var packed as result of string to CompressError is calling compressus.gzip_compress with "hello", CompressionLevel.Best
    defer banish packed
    if not packed.is_ok:
        calling spark.println with (calling packed.error.message)
        return 1
    var blob as string is packed.value          # borrowed view
    var plain as result of string to CompressError is calling compressus.gzip_decompress with blob
    defer banish plain
    if plain.is_ok:
        calling spark.println with plain.value  # "hello"
    return 0
```

## Ownership (read this once)

- Every weave returns a `result`. **A `result` owns its payload.** Release
  the whole result with `banish result`, and never `banish result.value` or
  `result.error` separately — that frees the same buffer twice.
- `result.value` / `result.error` are **borrowed views**. Use them while the
  result is alive.
- `CompressError` derives `Nexus`, so `banish` on a result whose payload is
  an error releases the reason strings and the variant box.
- `CompressError.message` returns an **owned** string; `banish` it.
- The file helpers return the number of bytes written and own nothing else.

```pengu
var r as result of string to CompressError is calling compressus.gzip_compress with data, CompressionLevel.Best
if not r.is_ok:
    return 1
var out as string is r.value       # borrowed: do NOT banish
# ... use out ...
banish r                           # releases out and the result box
```

## One-shot vs file helpers

The one-shot weaves (`gzip_compress`, `gzip_decompress`, ...) work on a whole
`string` in memory. The file helpers read the complete file, call the
one-shot weave and write the complete result; they are convenience wrappers,
**not** a streaming API, so peak memory is roughly the sum of the input and
the output. For files above ~100 MB, compress in chunks at the application
level or wait for the streaming API (see `docs/COMPRESSUS.md`).

## Errors

| Variant | Meaning |
|---|---|
| `InvalidInput` | the caller passed something impossible (a NUL in a gzip filename, `Auto` to a compressor, or an input whose output would exceed the 32-bit `string` length) |
| `Corrupt` | the compressed bytes are malformed, truncated or fail their checksum |
| `TrailingData` | a valid stream ended before the input did; `extra_bytes` says how many bytes are left |
| `UnsupportedFormat` | auto-detection did not recognise the magic; `magic` is the first four bytes, little-endian |
| `AllocationFailed` | an allocation failed |
| `FileError` | a file could not be read or written; `reason` names the path |
| `Internal` | an unexpected miniz status; `code` is the raw `MZ_*` value |

None of these panics: invalid bytes are a normal runtime condition, so every
weave returns `error` instead. A null `ref` passed to an internal bridge is a
programming bug and may still crash, exactly like the rest of the stdlib.

## Complexity

| Operation | Cost |
|---|---|
| `gzip_compress`, `zlib_compress`, `deflate_compress` | O(n) + one output allocation |
| `gzip_decompress`, `zlib_decompress`, `inflate_decompress` | O(n) + one growable output buffer |
| `detect_format` | O(1) |
| `crc32`, `adler32` | O(n), no allocation |
| file helpers | O(file size) read + the one-shot cost + O(output) write |

## Smart linking

`std/compressus.d.pengu` says `link "miniz"`, so `-lminiz` reaches the linker
**only** when `std.compressus` is imported. A program that never compresses
neither includes `miniz_bind.h` nor links a single miniz symbol.
`tests/build/test_smart_linking.py` proves all of that with `bundle.c`, the
`--verbose` link line and `nm`.

See `docs/COMPRESSUS.md` for the format details, the gzip framing walkthrough
and the comparison with Python, Zig and Odin.

## Why miniz, and why not a system zlib

miniz is one translation unit with no external dependency, so it builds
identically on Linux, macOS, Windows and Emscripten and a PenguScript program
never depends on a host `zlib` ABI (which differs between `zlib`, `zlib-ng`,
Chromium's bundled copy and Windows' `zlib1.dll`). It is public domain, which
keeps the toolchain license simple. Its output is standard deflate: the tests
compare it with Python byte for byte where the standard fixes the bytes.

---

### `COMPRESSUS_VERSION`

> **COMPRESSUS_VERSION** : string

 Compressus module version.

### `GZIP_HEADER_SIZE`

> **GZIP_HEADER_SIZE** : int

 Size of the fixed part of a gzip header, in bytes (RFC 1952 §2.3).

### `GZIP_TRAILER_SIZE`

> **GZIP_TRAILER_SIZE** : int

 Size of a gzip trailer: CRC-32 and ISIZE, four bytes each (RFC 1952 §2.3.1).

### `GZIP_MIN_SIZE`

> **GZIP_MIN_SIZE** : int

 Smallest possible gzip stream: 10-byte header, the two-byte empty deflate
 block (`03 00`) and the 8-byte trailer. `gzip -d` accepts it.

### `GZIP_MAGIC_0`

> **GZIP_MAGIC_0** : int

 First gzip magic byte (`0x1f`).

### `GZIP_MAGIC_1`

> **GZIP_MAGIC_1** : int

 Second gzip magic byte (`0x8b`).

### `GZIP_METHOD_DEFLATE`

> **GZIP_METHOD_DEFLATE** : int

 The only compression method gzip defines (`CM = 8`, deflate).

### `GZIP_FLAG_FEXTRA`

> **GZIP_FLAG_FEXTRA** : int

 `FLG` bit 2: an `FEXTRA` field follows the fixed header.

### `GZIP_FLAG_FNAME`

> **GZIP_FLAG_FNAME** : int

 `FLG` bit 3: an `FNAME` field follows (the original file name).

### `GZIP_FLAG_FCOMMENT`

> **GZIP_FLAG_FCOMMENT** : int

 `FLG` bit 4: an `FCOMMENT` field follows.

### `GZIP_FLAG_FHCRC`

> **GZIP_FLAG_FHCRC** : int

 `FLG` bit 1: an `FHCRC` field follows (low 16 bits of the header CRC-32).

### `GZIP_FLAG_RESERVED`

> **GZIP_FLAG_RESERVED** : int

 Bits 5-7 of `FLG` are reserved; RFC 1952 requires them to be zero.

### `CompressionLevel`

> omen CompressionLevel

```pengu
    None
    Fastest
    Default
    Better
    Best
    Uber
```

 How hard the compressor works.

 Higher levels produce smaller output and take longer. The names map to the
 zlib/miniz scale; `Default` is a concrete *6* (never miniz's `-1` sentinel,
 so two calls with the same level are byte-identical).

### `CompressionFormat`

> omen CompressionFormat

```pengu
    Gzip
    Zlib
    RawDeflate
    Auto
```

 The container format around a deflate stream.

### `CompressError`

> omen CompressError

```pengu
    InvalidInput with reason as string
    Corrupt with reason as string
    TrailingData with extra_bytes as int
    UnsupportedFormat with magic as u32
    AllocationFailed
    FileError with reason as string
    Internal with code as int, reason as string
```

 What went wrong while compressing, decompressing or reading/writing a file.

 ## Memoria
 Derives `Nexus`, so releasing a `result` that carries an error releases the
 `reason` string. `message` returns an owned description; `banish` it.

### `message`

> **message**() -> string

 A human-readable description of the failure.

 ## Retorno
 An **owned** string; release it with `banish`.

 ## Ejemplo
 ```pengu
 var e as CompressError is r.error
 var text as string is calling e.message
 calling spark.println with text
 banish text
 ```

### `_byte_at`

> **_byte_at**(s: string, i: int) -> int

 Returns the byte value at `i`, or 0 when `i` is out of bounds.

 ## Motivo
 `(calling scrolls.substring with s, i, i + 1)` allocates a one-byte string
 for every inspected byte. Header parsing inspects a dozen bytes per member;
 `.data`/`.len` allocates nothing.

 ## Memoria
 Reads only; allocates nothing.

### `_crc32_range`

> **_crc32_range**(data: string, offset: int, length: int, seed: u32) -> u32

 CRC-32 of `length` bytes starting at `offset`, continuing `seed`.

 ## Memoria
 Reads only; allocates nothing. Out-of-range slices return `seed` unchanged.

### `_adler32_range`

> **_adler32_range**(data: string, offset: int, length: int, seed: u32) -> u32

 Adler-32 of `length` bytes starting at `offset`, continuing `seed`.

 ## Memoria
 Reads only; allocates nothing. Out-of-range slices return `seed` unchanged.

### `_deflate_raw`

> **_deflate_raw**(data: string, level: int, status: ref to int) -> string

 Compresses `data` as a **raw** deflate stream (RFC 1951) at `level`.

 ## Motivo
 `tdefl_compress_mem_to_heap` takes the flag word built from
 `(level, -15, TDEFL_DEFAULT_MAX_PROBES)`, which selects raw deflate and one
 exact-size allocation. Doing the same through the streaming API would need an
 `mz_stream` the binding deliberately does not expose.

 ## Memoria
 The returned `PenguString` owns an SDS copy of the block miniz allocated; the
 intermediate block is released with `mz_free`. `status`
 receives `MZ_OK` or a negative `MZ_*` code.

### `_deflate_zlib`

> **_deflate_zlib**(data: string, level: int, status: ref to int) -> string

 Compresses `data` as a **zlib** stream (RFC 1950) at `level`.

 ## Motivo
 `mz_compress2` computes the zlib header, the deflate body and the Adler-32
 trailer in one call. Reimplementing the Adler-32 trailer here would duplicate
 a checksum miniz already emits and verifies.

 ## Memoria
 Reserves exactly `mz_compressBound(n)` bytes in an SDS buffer; the returned
 string owns it. `status` receives `MZ_OK` or a negative `MZ_*` code.

### `_gzip_compress`

> **_gzip_compress**(data: string, level: int, filename: string, status: ref to int) -> string

 Compresses `data` as a **gzip** stream (RFC 1952) at `level`.

 ## Motivo
 miniz has no gzip support. This block emits the 10-byte fixed header (plus an
 `FNAME` field when `filename` is non-empty), the raw deflate body and the
 CRC-32/ISIZE trailer in **one** allocation: concatenating three PenguScript
 strings would copy the body twice and allocate two temporaries.

 `MTIME` is always zero, so the same input and level produce the same bytes on
 any machine and at any time. `OS` is `0xff` ("unknown"), which every reader
 accepts. `XFL` follows gzip's convention (`2` for level 9, `4` for level 1,
 `0` otherwise); no reader depends on it.

 ## Memoria
 Reserves the exact output size in an SDS buffer; the returned string owns it.
 The temporary deflate block is released with `mz_free` before returning.
 `status` receives `MZ_OK` or a negative `MZ_*` code.

### `_inflate_at`

> **_inflate_at**(data: string, offset: int, window_bits: int, consumed: ref to int, status: ref to int) -> string

 Inflates `data[offset..]` with `window_bits` (`15` = zlib, `-15` = raw).

 ## Motivo
 The size of a deflate stream's output is not stored anywhere: it must be
 discovered by inflating. This block grows the output buffer geometrically
 with `realloc` and stops on `MZ_STREAM_END`, on a hard error, or when the
 input is exhausted before the end of the stream (truncation).

 `consumed` receives the number of **input** bytes the stream used (the offset
 of the trailer in a gzip member). `status` receives `MZ_OK` on success or a
 negative `MZ_*` code; `MZ_BUF_ERROR` means "the input ended mid-stream".

 ## Memoria
 Allocates one growable buffer that the returned string owns. `data` is read
 only. The temporary `mz_stream` is ended on every path.

### `_level_code`

> **_level_code**(level: CompressionLevel) -> int

 Maps a `CompressionLevel` to the integer miniz expects.

 `Default` is **6**, not miniz's `-1` sentinel: a concrete level keeps the
 output byte-identical between calls, which `tests/stdlib/test_compressus.py`
 asserts.

### `_le32`

> **_le32**(data: string, at: int) -> u32

 Reads a little-endian 32-bit integer at `at`. Out-of-range bytes read as 0.

 ## Memoria
 Reads only; allocates nothing.

### `_take_ok_string`

> **_take_ok_string**(r: ref to result of string to CompressError) -> string

 Moves the success payload out of a `result of string to CompressError`.

 ## Motivo
 `result.value` is a borrowed view: releasing the result releases the string
 too. `decompress_auto` has to return the plain bytes *and* release the inner
 result's box, so it moves the payload out first and then banishes an empty
 result. Doing that from PenguScript would need a copy.

 ## Memoria
 Transfers ownership of the string to the caller and leaves the result box
 empty (`ok_val == NULL`, `is_ok == false`), so a later `banish` on it is a
 no-op. Returns a non-owning `""` when `r` is not a successful result.

### `_take_error`

> **_take_error**(r: ref to result of string to CompressError) -> CompressError

 Moves the error payload out of a `result of string to CompressError`.

 ## Motivo
 `result.error` is a borrowed view: releasing the result frees the reason
 string it points at. Every failure path in this module has to return the
 error *and* release the inner result's box, so it moves the payload out
 first. Doing that from PenguScript would copy the struct but not the string
 it owns, leaving a dangling `reason`.

 ## Memoria
 Transfers ownership of the `CompressError` (including its reason string) to
 the caller and leaves the result box empty, so a later `banish` on it is a
 no-op.

### `_error_from_status`

> **_error_from_status**(status: int, context: string) -> CompressError

 Maps a miniz status to a `CompressError`.

 `context` names the operation for the `Internal` fallback, so an unexpected
 status still says *where* it happened.

### `_gzip_header_len`

> **_gzip_header_len**(data: string, at: int) -> int

 Returns the offset of the first byte after the gzip header that starts at
 `at`, or a negative code describing why the header is unusable.

 Codes: `-1` not gzip (bad magic), `-2` truncated header, `-3` unsupported
 compression method, `-4` reserved `FLG` bits set, `-5` `FHCRC` mismatch.

 The parser walks every optional field RFC 1952 defines — `FEXTRA`, `FNAME`,
 `FCOMMENT` and `FHCRC` — so a stream produced by any conforming writer
 (including one with an original filename) is accepted.

 ## Memoria
 Reads only; allocates nothing.

### `_format_code`

> **_format_code**(format: CompressionFormat) -> int

 Maps a `CompressionFormat` to a small integer, for comparisons.

 Omens are compared with `judge`, not with `is`; the code keeps
 `decompress_auto` flat instead of nesting two judges per branch.

### `_gzip_header_error`

> **_gzip_header_error**(code: int, data: string, at: int, member: int) -> CompressError

 Maps a `_gzip_header_len` failure code to the error the public API returns.

### `gzip_compress`

> **gzip_compress**(data: string, level: CompressionLevel) -> result of string to CompressError

 Compresses `data` as a gzip stream (RFC 1952), with `MTIME` zero.

 The output opens with `gzip -d` and with Python's `gzip.decompress`. Because
 `MTIME` is always zero, compressing the same bytes at the same level is
 deterministic.

 ## Parámetros
 - `data`: bytes to compress. Borrowed.
 - `level`: how hard to work. See `CompressionLevel`.

 ## Retorno
 `ok` with an **owned** gzip string (release the result with `banish`), or
 `err CompressError`.

 ## Ejemplo
 ```pengu
 var r as result of string to CompressError is calling compressus.gzip_compress with "hello", CompressionLevel.Best
 defer banish r
 if r.is_ok:
     calling archivum.write_bytes with "hello.gz", r.value
 ```

### `gzip_compress_named`

> **gzip_compress_named**(data: string, filename: string, level: CompressionLevel) -> result of string to CompressError

 Compresses `data` as a gzip stream that records `filename` in the `FNAME`
 header field.

 `FNAME` is metadata only: it is the original file name, not a path, and no
 reader is required to use it. Pass `""` for a stream with no `FNAME` field —
 that is exactly what `gzip_compress` does. A filename containing a NUL byte
 cannot be represented (the field is NUL-terminated) and is rejected with
 `InvalidInput`.

 ## Parámetros
 - `data`: bytes to compress. Borrowed.
 - `filename`: original name to record, or `""`. Borrowed.
 - `level`: how hard to work.

 ## Retorno
 `ok` with an **owned** gzip string, or `err CompressError`.

 ## Ejemplo
 ```pengu
 var r as result of string to CompressError is calling compressus.gzip_compress_named with payload, "notes.txt", CompressionLevel.Default
 defer banish r
 ```

### `gzip_decompress`

> **gzip_decompress**(data: string) -> result of string to CompressError

 Decompresses one or more concatenated gzip members.

 Multi-member streams (two `.gz` files concatenated with `cat`) decompress to
 the concatenation of their payloads, exactly like `gzip -d` and Python's
 `gzip.decompress`. Each member's CRC-32 and ISIZE are verified; a mismatch is
 `Corrupt`, not silently accepted.

 ## Parámetros
 - `data`: the gzip bytes. Borrowed.

 ## Retorno
 `ok` with the **owned** plain bytes (release the result with `banish`), or
 `err CompressError`:
 - `Corrupt` for a truncated header, a bad checksum or a truncated body;
 - `UnsupportedFormat` when `data` does not start with the gzip magic;
 - `TrailingData` when a valid member is followed by bytes that are not
   another gzip member.

 ## Ejemplo
 ```pengu
 var r as result of string to CompressError is calling compressus.gzip_decompress with blob
 defer banish r
 ```

### `zlib_compress`

> **zlib_compress**(data: string, level: CompressionLevel) -> result of string to CompressError

 Compresses `data` as a zlib stream (RFC 1950).

 The output is what Python's `zlib.decompress` expects and what a zlib-aware
 HTTP server accepts. miniz computes the Adler-32 trailer.

 ## Parámetros
 - `data`: bytes to compress. Borrowed.
 - `level`: how hard to work.

 ## Retorno
 `ok` with an **owned** zlib string, or `err CompressError`.

 ## Ejemplo
 ```pengu
 var r as result of string to CompressError is calling compressus.zlib_compress with "hello", CompressionLevel.Best
 defer banish r
 ```

### `zlib_decompress`

> **zlib_decompress**(data: string) -> result of string to CompressError

 Decompresses a zlib stream (RFC 1950).

 The Adler-32 trailer is verified by miniz. Bytes after the end of the stream
 are `TrailingData`, never silently ignored.

 ## Parámetros
 - `data`: the zlib bytes. Borrowed.

 ## Retorno
 `ok` with the **owned** plain bytes, or `err CompressError`.

 ## Ejemplo
 ```pengu
 var r as result of string to CompressError is calling compressus.zlib_decompress with blob
 defer banish r
 ```

### `deflate_compress`

> **deflate_compress**(data: string, level: CompressionLevel) -> result of string to CompressError

 Compresses `data` as a **raw** deflate stream (RFC 1951).

 There is no header and no checksum: use it only when the surrounding protocol
 already frames the stream and protects its integrity (a ZIP member, a
 WebSocket `permessage-deflate` frame, a length-prefixed record).

 ## Parámetros
 - `data`: bytes to compress. Borrowed.
 - `level`: how hard to work.

 ## Retorno
 `ok` with an **owned** deflate string, or `err CompressError`.

 ## Ejemplo
 ```pengu
 var r as result of string to CompressError is calling compressus.deflate_compress with "hello", CompressionLevel.Fastest
 defer banish r
 ```

### `inflate_decompress`

> **inflate_decompress**(data: string) -> result of string to CompressError

 Decompresses a **raw** deflate stream (RFC 1951).

 Empty input is the empty string: this weaves answers "what does this stream
 decompress to", and an absent stream carries no bytes. A truncated or corrupt
 stream is `Corrupt`, and bytes after the end of the stream are
 `TrailingData`.

 ## Parámetros
 - `data`: the raw deflate bytes. Borrowed.

 ## Retorno
 `ok` with the **owned** plain bytes, or `err CompressError`.

 ## Ejemplo
 ```pengu
 var r as result of string to CompressError is calling compressus.inflate_decompress with blob
 defer banish r
 ```

### `detect_format`

> **detect_format**(data: string) -> maybe CompressionFormat

 Detects the container format from the first bytes.

 Recognises the gzip magic (`1f 8b`) and a structurally valid zlib header
 (`CM = 8`, `CINFO <= 7`, `FCHECK` consistent). Raw deflate has no magic and
 is **not** detected: pass `CompressionFormat.RawDeflate` explicitly.

 ## Parámetros
 - `data`: the bytes to inspect. Borrowed; only the first two are read.

 ## Retorno
 `some CompressionFormat` or `maybe none`.

 ## Ejemplo
 ```pengu
 var f as maybe CompressionFormat is calling compressus.detect_format with blob
 if f is present:
     calling spark.println with "known format"
 ```

### `_format_pair`

> **_format_pair**(text: string, format: CompressionFormat) -> (string, CompressionFormat)

 Packs a `string` and its format into the tuple `decompress_auto` returns.

 ## Memoria
 Moves `text` into the tuple; the caller owns it through the result.

### `decompress_auto`

> **decompress_auto**(data: string) -> result of (string, CompressionFormat) to CompressError

 Decompresses `data` in whichever format `detect_format` recognises.

 Raw deflate is not auto-detected; use `inflate_decompress` when the protocol
 says the bytes are raw.

 ## Parámetros
 - `data`: the compressed bytes. Borrowed.

 ## Retorno
 `ok (plain, format)` with the owned plain bytes and the detected format, or
 `err CompressError`. An unrecognised magic is `UnsupportedFormat` with the
 first four bytes (little-endian) in `magic`.

 ## Ejemplo
 ```pengu
 var r as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_auto with blob
 defer banish r
 if r.is_ok:
     var pair as (string, CompressionFormat) is r.value
     var plain as string is pair.0
 ```

### `decompress_as`

> **decompress_as**(data: string, format: CompressionFormat) -> result of (string, CompressionFormat) to CompressError

 Decompresses `data` as an explicit format, with `Auto` as the detecting
 choice.

 This is the uniform entry point for code that already knows the format (a
 protocol field, a file extension, a manifest): `Gzip`, `Zlib` and
 `RawDeflate` dispatch to the matching decompressor, and `Auto` calls
 `decompress_auto`. The returned tuple always says which decoder actually ran.

 ## Parámetros
 - `data`: the compressed bytes. Borrowed.
 - `format`: the container, or `CompressionFormat.Auto`.

 ## Retorno
 `ok (plain, format)` with the **owned** plain bytes, or `err CompressError`.

 ## Ejemplo
 ```pengu
 var r as result of (string, CompressionFormat) to CompressError is calling compressus.decompress_as with blob, CompressionFormat.Auto
 defer banish r
 if r.is_ok:
     let (plain, fmt) is r.value
 ```

### `crc32`

> **crc32**(data: string) -> u32

 CRC-32 (ISO 3309 / ITU-T V.42) of `data`, the checksum gzip stores.

 `crc32("")` is `0`. The result matches Python's `zlib.crc32(data)` and
 `crc32` from `binascii`.

 ## Parámetros
 - `data`: the bytes to checksum. Borrowed.

 ## Retorno
 The 32-bit checksum.

 ## Ejemplo
 ```pengu
 var c as u32 is calling compressus.crc32 with "hello"
 ```

### `crc32_continue`

> **crc32_continue**(initial: u32, data: string) -> u32

 CRC-32 of `data` continuing a previous checksum.

 `crc32_continue(crc32(a), b) == crc32(a + b)`, so a large file can be
 checksummed chunk by chunk without keeping it in memory. Start with `0`.

 ## Parámetros
 - `initial`: the previous checksum, or `0` to start.
 - `data`: the next bytes. Borrowed.

 ## Retorno
 The updated 32-bit checksum.

 ## Ejemplo
 ```pengu
 var c as u32 is 0
 set c is calling compressus.crc32_continue with c, chunk_a
 set c is calling compressus.crc32_continue with c, chunk_b
 ```

### `adler32`

> **adler32**(data: string) -> u32

 Adler-32 (RFC 1950) of `data`, the checksum zlib stores.

 `adler32("")` is `1`. The result matches Python's `zlib.adler32(data)`.

 ## Parámetros
 - `data`: the bytes to checksum. Borrowed.

 ## Retorno
 The 32-bit checksum.

 ## Ejemplo
 ```pengu
 var a as u32 is calling compressus.adler32 with "hello"
 ```

### `adler32_continue`

> **adler32_continue**(initial: u32, data: string) -> u32

 Adler-32 of `data` continuing a previous checksum.

 `adler32_continue(adler32(a), b) == adler32(a + b)`. Start with `1`.

 ## Parámetros
 - `initial`: the previous checksum, or `1` to start.
 - `data`: the next bytes. Borrowed.

 ## Retorno
 The updated 32-bit checksum.

 ## Ejemplo
 ```pengu
 var a as u32 is 1
 set a is calling compressus.adler32_continue with a, chunk
 ```

### `gzip_compress_file`

> **gzip_compress_file**(input_path: string, output_path: string, level: CompressionLevel) -> result of int to CompressError

 Reads `input_path`, compresses it as gzip and writes `output_path`.

 The whole file is read into memory and the whole result is written at once;
 see the module note on large files.

 ## Parámetros
 - `input_path`: file to read. Borrowed.
 - `output_path`: file to create or truncate. Borrowed.
 - `level`: how hard to work.

 ## Retorno
 `ok` with the number of **compressed** bytes written, `err CompressError`
 (`FileError` when either file cannot be opened).

 ## Ejemplo
 ```pengu
 var r as result of int to CompressError is calling compressus.gzip_compress_file with "notes.txt", "notes.txt.gz", CompressionLevel.Best
 ```

### `gzip_decompress_file`

> **gzip_decompress_file**(input_path: string, output_path: string) -> result of int to CompressError

 Reads `input_path` as gzip and writes the plain bytes to `output_path`.

 ## Parámetros
 - `input_path`: gzip file to read. Borrowed.
 - `output_path`: file to create or truncate. Borrowed.

 ## Retorno
 `ok` with the number of **decompressed** bytes written, or `err`.

 ## Ejemplo
 ```pengu
 var r as result of int to CompressError is calling compressus.gzip_decompress_file with "notes.txt.gz", "notes.txt"
 ```

### `gzip_read_file`

> **gzip_read_file**(path: string) -> result of string to CompressError

 Reads a gzip file and returns its decompressed contents.

 ## Parámetros
 - `path`: the `.gz` file. Borrowed.

 ## Retorno
 `ok` with the **owned** plain bytes, or `err`.

 ## Ejemplo
 ```pengu
 var r as result of string to CompressError is calling compressus.gzip_read_file with "notes.txt.gz"
 ```

### `gzip_write_file`

> **gzip_write_file**(path: string, data: string, level: CompressionLevel) -> result of void to CompressError

 Compresses `data` as gzip and writes it to `path`.

 ## Parámetros
 - `path`: file to create or truncate. Borrowed.
 - `data`: bytes to compress. Borrowed.
 - `level`: how hard to work.

 ## Retorno
 `ok` with nothing, or `err`.

 ## Ejemplo
 ```pengu
 var r as result of void to CompressError is calling compressus.gzip_write_file with "notes.txt.gz", "hello", CompressionLevel.Best
 ```

### `zlib_compress_file`

> **zlib_compress_file**(input_path: string, output_path: string, level: CompressionLevel) -> result of int to CompressError

 Reads `input_path`, compresses it as zlib and writes `output_path`.

 ## Parámetros
 - `input_path`: file to read. Borrowed.
 - `output_path`: file to create or truncate. Borrowed.
 - `level`: how hard to work.

 ## Retorno
 `ok` with the number of **compressed** bytes written, or `err`.

 ## Ejemplo
 ```pengu
 var r as result of int to CompressError is calling compressus.zlib_compress_file with "a.bin", "a.zlib", CompressionLevel.Best
 ```

### `zlib_decompress_file`

> **zlib_decompress_file**(input_path: string, output_path: string) -> result of int to CompressError

 Reads `input_path` as zlib and writes the plain bytes to `output_path`.

 ## Parámetros
 - `input_path`: zlib file to read. Borrowed.
 - `output_path`: file to create or truncate. Borrowed.

 ## Retorno
 `ok` with the number of **decompressed** bytes written, or `err`.

 ## Ejemplo
 ```pengu
 var r as result of int to CompressError is calling compressus.zlib_decompress_file with "a.zlib", "a.bin"
 ```

