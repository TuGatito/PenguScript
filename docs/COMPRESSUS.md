# `std.compressus` — gzip, zlib and raw deflate

`std.compressus` compresses and decompresses the three formats the world
actually exchanges: **gzip** (RFC 1952, `.gz` files and HTTP
`Content-Encoding: gzip`), **zlib** (RFC 1950, PNG `IDAT`, many HTTP bodies) and
**raw deflate** (RFC 1951, the payload of protocols that already carry framing).

It wraps [miniz 3.1.2](../std_c/miniz.h), Rich Geldreich's public-domain
single-file deflate/inflate library, vendored in
[`std_c/miniz.h`](../std_c/miniz.h) + [`std_c/miniz.c`](../std_c/miniz.c). miniz
implements RFC 1950 and RFC 1951; the **gzip container is implemented by this
module** on top of raw deflate, because miniz has no RFC 1952 support. That
framing is the part most likely to be wrong in a hand-rolled wrapper, so it is
documented byte by byte in §6 and covered by the Python compatibility suite.

---

## 1. Why miniz

| Property | miniz | system zlib |
|---|---|---|
| Distribution | one `.h` + one `.c`, vendored here | a host package, a different ABI per distro |
| License | public domain / Unlicense | zlib licence |
| Build | `-std=c99 -Wall -Wextra -Werror`, no config | pkg-config, `-lz`, header version checks |
| Cross-platform | Linux, macOS, Windows, Emscripten, same bytes | the host's build, possibly `zlib-ng` or Chromium's copy |
| Formats | zlib + raw deflate (+ zip, compiled out here) | zlib + raw deflate + gzip |
| Speed | roughly zlib-compatible | zlib-compatible |

The important property is **reproducibility**: a PenguScript program never
depends on which `zlib` the host happens to ship, on its ABI, or on whether it
is patched. The archive is built once by `build_runtime.py` and linked only when
the module is imported (§9). The public-domain licence keeps the toolchain's
licence story simple.

The vendored files are **unmodified upstream**. All configuration lives in
[`std_c/miniz_bind.h`](../std_c/miniz_bind.h), a small shim that defines four
macros and then includes `miniz.h`:

| Macro | Effect |
|---|---|
| `MINIZ_NO_ZLIB_COMPATIBLE_NAMES` | drops the `deflate`/`inflate`/`crc32`/... aliases |
| `MINIZ_NO_ARCHIVE_APIS` | compiles out the ZIP reader/writer |
| `MINIZ_NO_STDIO` | compiles out `stdio.h` use |
| `MINIZ_NO_TIME` | compiles out `time.h` use |

`MINIZ_NO_ZLIB_COMPATIBLE_NAMES` is not optional. Under `-std=c99`/`-std=c11`
GCC defines `__STRICT_ANSI__`, so miniz's `MZ_FORCEINLINE` expands to nothing
and every `static` alias becomes an unused function; `-Wall -Wextra -Werror`
would reject every bundle that imports `std.compressus`. The other three keep
the archive small and avoid POSIX `ftello`/`fseeko`, which a strict C99 build
cannot see. `build_runtime.py` passes the same macro set to the `miniz.c`
translation unit (`STD_C_DEFINES`), so the archive and its consumers cannot
disagree.

---

## 2. Formats: which one to use

| Format | Magic | Integrity | Use it for |
|---|---|---|---|
| `Gzip` | `1f 8b` | CRC-32 + ISIZE trailer | files (`.gz`), HTTP `Content-Encoding: gzip`, `pengu add` tarballs |
| `Zlib` | `78 xx` | Adler-32 trailer | protocols that specify zlib (some HTTP, PNG `IDAT`) |
| `RawDeflate` | none | none | ZIP members, WebSocket `permessage-deflate`, length-prefixed records |

* **gzip** adds a 10-byte header (plus optional name/comment/extra fields) and
  an 8-byte trailer. It is self-describing and is what `gzip -d`, Python's
  `gzip.decompress`, browsers and every archive tool understand.
* **zlib** is the smaller framing: a two-byte header and a four-byte big-endian
  Adler-32. Use it when a specification says "zlib" or "deflate with an
  Adler-32".
* **raw deflate** has no magic and no checksum. Use it only when the surrounding
  protocol already provides both; `decompress_auto` deliberately does not guess
  it.

`CompressionLevel` maps to the zlib scale: `None` (0), `Fastest` (1),
`Default` (6), `Better` (7), `Best` (9) and miniz's `Uber` (10). `Default` is a
concrete 6, never miniz's `-1` sentinel, so two calls with the same level emit
the same bytes.

---

## 3. One-shot API

All one-shot functions take a `string` and return a `result` that **owns its
payload**:

```pengu
import std.compressus
import std.spark

weave main into int:
    var data as string is "the quick brown fox jumps over the lazy dog"

    var packed as result of string to CompressError is calling compressus.gzip_compress with data, CompressionLevel.Best
    defer banish packed
    if not packed.is_ok:
        var e as CompressError is packed.error
        var why as string is calling e.message
        calling spark.eprintln with why
        banish why
        return 1
    var blob as string is packed.value          # borrowed view

    var plain as result of string to CompressError is calling compressus.gzip_decompress with blob
    defer banish plain
    if plain.is_ok:
        calling spark.println with plain.value  # the original text
    return 0
```

| Function | Returns |
|---|---|
| `gzip_compress(data, level)` | `result of string to CompressError` |
| `gzip_compress_named(data, filename, level)` | gzip with the `FNAME` header field |
| `gzip_decompress(data)` | plain bytes; accepts multi-member gzip |
| `zlib_compress(data, level)` | zlib stream |
| `zlib_decompress(data)` | plain bytes; verifies Adler-32 |
| `deflate_compress(data, level)` | raw deflate |
| `inflate_decompress(data)` | plain bytes; empty input is the empty string |
| `detect_format(data)` | `maybe CompressionFormat` |
| `decompress_auto(data)` | `result of (string, CompressionFormat) to CompressError` |
| `decompress_as(data, format)` | explicit `Gzip`/`Zlib`/`RawDeflate`, or `Auto` for detection |

### Ownership

A `result` owns its payload. `result.value` and `result.error` are **borrowed
views**; never `banish` them separately. Release the whole result:

```pengu
var r as result of string to CompressError is calling compressus.gzip_compress with data, CompressionLevel.Best
if not r.is_ok:
    return 1
var out as string is r.value        # borrowed: do NOT banish
# ... use out ...
banish r                            # releases out and the result box
```

`CompressError` derives `Nexus`, so `banish r` also releases a `reason` string
when the result is an error. `CompressError.message` returns an **owned** string;
`banish` it.

### Errors

| Variant | Meaning |
|---|---|
| `InvalidInput` | impossible caller input: a NUL in a gzip filename, `CompressionFormat.Auto` to a compressor, or output above the 32-bit `string` limit |
| `Corrupt` | malformed, truncated, or checksum-failing bytes |
| `TrailingData` | a valid stream ended before the input did; `extra_bytes` says how much is left |
| `UnsupportedFormat` | auto-detection did not recognise the magic; `magic` is the first four bytes, little-endian |
| `AllocationFailed` | an allocation failed (named this way because `HttpError`/`RegexError` already use `OutOfMemory`, and variant names are unique across a compilation) |
| `FileError` | a file could not be read or written (named this way because `HttpError` already uses `IoError`) |
| `Internal` | an unexpected miniz status; `code` is the raw `MZ_*` value |

No invalid input panics: bytes are a runtime condition, so every function
returns `error`. A null `ref` passed to an internal bridge is a programming bug
and may crash, like the rest of the standard library.

---

## 4. File API

The file helpers read the whole file, call the one-shot function and write the
whole result. They are **convenience wrappers, not streaming**: peak memory is
roughly input + output.

| Function | Returns |
|---|---|
| `gzip_compress_file(input, output, level)` | `result of int` — compressed bytes written |
| `gzip_decompress_file(input, output)` | `result of int` — plain bytes written |
| `gzip_read_file(path)` | `result of string` — decompressed contents |
| `gzip_write_file(path, data, level)` | `result of void` |
| `zlib_compress_file(input, output, level)` | `result of int` |
| `zlib_decompress_file(input, output)` | `result of int` |

```pengu
var r as result of int to CompressError is calling compressus.gzip_compress_file with "notes.txt", "notes.txt.gz", CompressionLevel.Best
defer banish r
if not r.is_ok:
    return 1
calling spark.println_int with r.value
```

A missing or unreadable file is `FileError`; a corrupt `.gz` is `Corrupt`.
`gzip_read_file` returns the owned plain bytes, which is the right call for
`pengu add`-sized downloads.

---

## 5. Streaming API

**⏸️ Deferred to 2.14.1.** The 2.14.0 release ships the one-shot, file and hash
APIs. A real incremental `Compressor`/`Decompressor` is a state machine over
`mz_deflate`/`mz_inflate` with gzip header/trailer state that must survive chunk
boundaries, and it deserves its own compatibility suite rather than a rushed
implementation. The planned surface is:

```pengu
rune Compressor:
    weave ritual new with format as CompressionFormat, level as CompressionLevel into result of Compressor to CompressError
    weave write with data as string into result of string to CompressError
    weave finish into result of string to CompressError
    weave free into void

rune Decompressor:
    weave ritual new with format as CompressionFormat into result of Decompressor to CompressError
    weave write with data as string into result of string to CompressError
    weave finish into result of string to CompressError
    weave free into void
```

Until then, for a file larger than memory, compress it in application-level
chunks with separate gzip members (concatenating `.gz` members is legal, and
`gzip_decompress` reads them all):

```text
# Pseudocode: one member per 8 MiB chunk.
out = new StringBuilder
while (chunk = read_next_chunk()):
    piece = gzip_compress(chunk, CompressionLevel.Default)
    out.append(piece.value)
    banish piece
    banish chunk
write_bytes("big.tar.gz", out.finish())
```

This is exactly what `gzip -c` does not do for a single member, but it is what
`cat part1.gz part2.gz` produces, and every reader accepts it. It is documented
so nobody invents an incompatible private framing.

---

## 6. Gzip framing

miniz emits and reads raw deflate. `std.compressus` adds the RFC 1952 container.

### Header (10 bytes, plus optional fields)

```text
offset  size  value
0       2     1f 8b            magic
2       1     08               CM = deflate
3       1     FLG              flags
4       4     00 00 00 00      MTIME, little-endian (always 0 here)
8       1     XFL              extra flags: 2 for level 9, 4 for level 1, else 0
9       1     ff               OS: unknown
```

`MTIME` is always zero, so compressing the same bytes at the same level is
deterministic on every machine and at every time. `OS = 0xff` ("unknown") is
accepted by every reader; it avoids claiming the producer's operating system.
`XFL` follows gzip's convention but no reader depends on it.

`FLG` bits implemented by the **reader**:

| Bit | Field | Handling |
|---|---|---|
| `0x04` | `FEXTRA` | an `XLEN` little-endian length and that many bytes are skipped |
| `0x08` | `FNAME` | a NUL-terminated original file name is skipped (and produced by `gzip_compress_named`) |
| `0x10` | `FCOMMENT` | a NUL-terminated comment is skipped |
| `0x02` | `FHCRC` | the low 16 bits of the header CRC-32 are **verified** |
| `0xe0` | reserved | a non-zero value is `Corrupt` |

A filename containing a NUL cannot be represented (the field is
NUL-terminated) and is rejected with `InvalidInput`.

### Trailer (8 bytes)

```text
0  4  CRC-32 of the uncompressed data, little-endian
4  4  ISIZE = uncompressed size mod 2^32, little-endian
```

The reader verifies both. A CRC or ISIZE mismatch is `Corrupt`, never a silent
success.

### Multi-member

Concatenating `.gz` files (`cat a.gz b.gz`) is valid gzip: each member has its
own header, body and trailer. `gzip_decompress` walks the members, concatenates
their payloads and verifies each checksum, exactly like `gzip -d` and Python's
`gzip.decompress`. After the last member, remaining bytes that do not start
another gzip member are `TrailingData` with the count.

### Empty input

`gzip_compress("")` is a complete 20-byte stream: a 10-byte header, the
two-byte empty deflate block `03 00`, and an 8-byte trailer with CRC 0 and
ISIZE 0. `gzip -d` and Python accept it.

---

## 7. Hashes

| Function | Notes |
|---|---|
| `crc32(data)` | CRC-32 (ISO 3309), gzip's checksum; `crc32("") == 0` |
| `crc32_continue(initial, data)` | continue a previous CRC; start with `0` |
| `adler32(data)` | Adler-32 (RFC 1950), zlib's checksum; `adler32("") == 1` |
| `adler32_continue(initial, data)` | continue a previous Adler; start with `1` |

`crc32_continue(crc32(a), b) == crc32(a + b)`, so a large file can be checked
chunk by chunk. The values match Python's `zlib.crc32` / `zlib.adler32` and
`binascii.crc32`. They are the checksums needed for `pengu.lock` entries and
for building or verifying a gzip trailer by hand.

---

## 8. Format detection

`detect_format` recognises the gzip magic (`1f 8b`) and a structurally valid
zlib header (`CM = 8`, `CINFO <= 7`, `FCHECK` consistent). It returns
`maybe CompressionFormat`.

Raw deflate has **no magic**. Detection cannot distinguish it from arbitrary
bytes, so `decompress_auto` never guesses raw: a stream that is not gzip or zlib
is `UnsupportedFormat`. (A random two-byte prefix can satisfy the zlib header
test; that is a property of the format, not a bug. `tests/compat` compares
detection with the same structural test in Python rather than pretending
otherwise.)

---

## 9. Smart linking

`std/compressus.d.pengu` contains:

```pengu
include "miniz_bind.h"
link "miniz"
```

`build_runtime.py` compiles `std_c/miniz.c` into `build/lib/libminiz.a` with the
configured macro set. A program that does not import `std.compressus` never
includes `miniz_bind.h`, never receives `-lminiz`, and contains no miniz symbol.
`tests/build/test_smart_linking.py` proves all three pieces of evidence for
seven programs:

| Program | `miniz_bind.h` | `-lminiz` | `mz_*` symbol |
|---|---|---|---|
| `hello` | no | no | no |
| `lingua` | no | no | no |
| `regulus` | no | no | no |
| `both` (lingua + regulus) | no | no | no |
| `petitio` | no | no | no |
| `compressus` | yes | yes | yes |
| `all_std_c` (lingua + petitio + compressus) | yes | yes | yes |

`--gc-sections` then drops the wrapper entry points the program does not call,
which is the second half of the contract.

---

## 10. Comparison with Python, Zig and Odin

| Operation | `std.compressus` | Python | Zig `std.compress` | Odin `core:compress` |
|---|---|---|---|---|
| gzip compress | `gzip_compress(data, level)` | `gzip.compress(data)` | `flate.gzip.compress` | `gzip.compress` |
| gzip decompress | `gzip_decompress(data)` | `gzip.decompress(data)` | `flate.gzip.decompress` | `gzip.decompress` |
| zlib compress | `zlib_compress(data, level)` | `zlib.compress(data)` | `flate.zlib.compress` | `zlib.compress` |
| zlib decompress | `zlib_decompress(data)` | `zlib.decompress(data)` | `flate.zlib.decompress` | `zlib.decompress` |
| raw deflate | `deflate_compress(data, level)` | `zlib.compress(data)[2:-4]` | `flate.deflate.compress` | `flate.compress` |
| checksums | `crc32`, `adler32`, `*_continue` | `zlib.crc32`, `zlib.adler32` | `std.hash.Crc32` | `crc32`, `adler32` |
| multi-member gzip | yes | yes | yes | yes |
| errors | `result`, never panics | exceptions | error unions | error unions |
| streaming | ⏸️ 2.14.1 | `GzipFile`, `compressobj` | `Compressor`/`Decompressor` | incremental |

The byte formats are identical, so interoperability is testable and tested:
`tests/compat/test_compressus_vs_python.py` checks 50 byte strings in both
directions for all three formats, plus multi-member gzip, detection and both
checksums. The one deliberate behavioural difference is strictness: Python's
`zlib.decompress` ignores trailing bytes, while `std.compressus` reports
`TrailingData`. Silent trailing data is a footgun (it hides a truncated
concatenation or a protocol bug), so the module is explicit about it.

---

## 11. Regenerating the binding

The raw binding is [`std/compressus.d.pengu`](../std/compressus.d.pengu). It is
**hand-written**, for one concrete reason: `pengu bind std_c/miniz.h` does not
digest the header. The preprocessed translation unit under GCC 16 contains

```c
typedef __typeof__(nullptr) nullptr_t;
```

from `<stddef.h>`, which pycparser rejects. miniz is also a single-header
library with dozens of macros, function-like macros and struct-heavy
`mz_zip_*` declarations that are out of scope here.

To try again (and to diff against this file when pycparser learns the typedef):

```bash
pengu bind std_c/miniz.h --output /tmp/miniz.d.pengu \
    --include-paths std_c/ --system-includes
```

When regenerating by hand, follow the type mapping `pengu bind` documents
(`unsigned long`/`mz_ulong` → `u64`, `size_t` → `usize`, `unsigned char *` →
`ref to byte`) and keep only the surface the wrapper uses. The ZIP and PNG APIs
are compiled out by `miniz_bind.h` and must not appear.

`std/compressus.d.pengu` is the companion of `std/compressus.pengu`: importing
the wrapper loads it implicitly, which is what emits the `include` and `link`
lines. Importing the `.d.pengu` directly is not part of the public API.

---

## 12. Limitations

* **No ZIP archives.** miniz's `mz_zip_*` API is compiled out. Reading and
  writing `.zip` needs its own binding and a different abstraction (entries,
  central directory, per-entry methods); it is a candidate for `std.zip` in a
  later release.
* **No Zstandard, Brotli, LZ4, LZMA or bzip2.** Each is a different library and
  a different format. They are satellite modules, not part of this one.
* **No streaming yet.** See §5. One-shot and file helpers are complete; a
  100 MB file is read into memory.
* **One-shot input is bounded by the language's 32-bit `string` length.**
  `gzip_compress` cannot accept more than ~2 GiB in one call; the defensive
  guards report `InvalidInput` rather than truncating.
* **`CompressionFormat.Auto` is a decompression hint only.** Passing it to a
  compressor is `InvalidInput`; raw deflate is never auto-detected.
* **`MTIME` is always zero.** Reproducible output is worth more than recording
  the wall clock; callers that need a timestamp can post-process the header.

---

## 13. Testing

| Gate | What it proves |
|---|---|
| `tests/compat/test_compressus_vs_python.py` | 50 byte strings × 3 formats, both directions, multi-member, detection, CRC-32/Adler-32 against CPython |
| `tests/stdlib/test_compressus.py` | every level, sizes 0–1 MiB, determinism, error taxonomy, file helpers, named gzip, multi-member, owned-error paths |
| fuzz corpus in `tests/compat/test_compressus_vs_python.py` | 120 random/malformed/truncated inputs fed to all four decompressors: an `ok` or an `error`, never a panic; every input round-trips and matches `zlib`'s checksums |
| `tests/conformance/compliance/compressus_*.pengu` | 11 complete programs: raw binding, gzip basic/empty/large/binary, zlib, raw deflate, auto-detect, files, hashes, multi-member |
| `tests/build/test_smart_linking.py` | the archive, header and symbols follow the import (7-program matrix) |
| `tests/stdlib/audit/test_compressus_ownership.py` | 100-iteration churn under ASan + UBSan + LeakSanitizer, including every error path and the `_take_*` moves |
| `tests/compiler/test_ord_and_casts.py` | the `to usize`/`to i8` cast fix that this module uncovered |

Valgrind is not installed on every developer box; the ASan/UBSan/LSan gate is
the equivalent (and stricter) check and is what the repository's other audit
tests use.
