# `std.carmen` — binary layouts with formulas

`std.carmen` is PenguScript's answer to Python's `struct`: it packs and unpacks
fixed-width binary records described by a short **formula** string, the way a
ritual formula fixes the shape of a spell. Every binary protocol — TCP frames,
PNG chunks, ELF headers, glTF accessors, ZIP central directories — is a list of
integers, floats and byte strings at fixed offsets. `std.carmen` reads and
writes exactly those, with explicit byte order, explicit alignment and typed
errors instead of ad-hoc byte arithmetic.

```pengu
import std.carmen

let h is calling carmen.seal with ">I4sH"
let record is calling carmen.pack with ">I4sH", [
    (calling carmen.unsigned with 1),
    (calling carmen.text with "abcd"),
    (calling carmen.unsigned with 2),
]
# record.value == "\x00\x00\x00\x01abcd\x00\x02"
```

The same formula is byte-identical to CPython's `struct.pack(">I4sH", 1, b"abcd", 2)`
on the same platform. Carmen keeps full compatibility with Python's format
language and adds four extensions (see [Formula grammar](#formula-grammar)).

## Why a dedicated module

- **No raw pointer math at call sites.** A formula is validated once and then
  reused; offsets, sizes and alignment are computed by the module.
- **Errors are values.** Truncated buffers, out-of-range integers, unterminated
  C strings and bad formulas come back as `result of … to CarmenError`, never as
  a panic or a silent truncation (Ruby and Perl truncate; Carmen follows
  Python and fails).
- **Introspection.** `layout`, `explain` and `describe` turn a formula into
  offsets and an annotated hex dump, which is what you want when a protocol
  field is off by two bytes.
- **Typed random access.** `CarmenReader` and `CarmenWriter` are cursors for
  streaming formats: read the header, branch on a tag, skip to a table.

## Layers

| Layer | Types | Use when |
|---|---|---|
| Formula (L1) | `seal`, `pack`, `unpack`, `pack_into`, `unpack_from`, `unpack_named`, `iter_unpack`, `calcsize`, `layout` | The record is fixed and you want the whole thing at once. |
| Cursor (L2) | `CarmenReader`, `CarmenWriter` | The record has variable-length sections or you stream field by field. |
| Bits (L2b) | `CarmenReader.read_bits`, `align_bits`, `CarmenWriter` bit cursor | Packed flags and bit fields. |
| Insight (L3) | `explain`, `describe`, `validate`, `hex` | Debugging a layout or documenting a protocol. |

## Formula grammar

```
format  := prefix? item*
item    := prefix | field
field   := named | plain
named   := '{' identifier ':' count? code '}'
plain   := count? code
count   := digits
prefix  := '@' | '=' | '<' | '>' | '!'
```

- **No prefix** means native mode (`@`): native byte order, native sizes and
  C alignment between members.
- `=`: native byte order, **standard** sizes, no alignment.
- `<` little-endian, `>` and `!` big-endian (network order). Standard sizes, no
  alignment.
- A prefix may appear **anywhere** in the formula to switch byte order for the
  rest of it; this is the mid-format endian switch extension.

### Codes

| Code | Python meaning | Size (standard) | Notes |
|---|---|---|---|
| `x` | pad byte | 1 | No value is produced or consumed. |
| `c` | one-byte bytes | 1 | Produces a one-character `Text`. |
| `b` / `B` | signed / unsigned byte | 1 | |
| `?` | boolean | 1 | Any non-zero byte is `true`. |
| `h` / `H` | signed / unsigned 16-bit | 2 | |
| `i` / `I` | signed / unsigned 32-bit | 4 | |
| `l` / `L` | signed / unsigned long | 4 | Native mode uses C `long` (8 on LP64). |
| `q` / `Q` | signed / unsigned 64-bit | 8 | |
| `n` / `N` | ssize_t / size_t | pointer size | Native mode only. |
| `e` | binary16 (half float) | 2 | IEEE 754, round-to-nearest-even. |
| `f` / `d` | float32 / float64 | 4 / 8 | |
| `s` | fixed bytes (count = length) | count | Zero-padded; truncates. Count defaults to 1. |
| `p` | Pascal string | count | First byte is the length (max 255, count ≤ 255). |
| `P` | void pointer | pointer size | Native mode only; `0` round-trips. |
| `z` | NUL-padded bytes **extension** | count | Unpack stops at the first NUL; count is required. |
| `v` / `V` | little-endian u16 / u32 **extension** | 2 / 4 | Byte-order fixed by the code, not the prefix. |

Counts repeat a code: `4h` is four `i16` values, `3x` is three pad bytes.
Naming repeat results is described below; `0s` and `0p` produce one empty
`Text`, every other zero count produces no value (Python does the same).

Named fields and the extensions are **Carmen-only**; `is_python_compatible`
returns `false` for a formula that uses them:

```pengu
carmen.is_python_compatible with ">I4sH"          # true
carmen.is_python_compatible with ">4z"            # false
carmen.is_python_compatible with r">{len:I}{tag:4s}"  # false
```

### Named fields

```pengu
let h is calling carmen.seal with r">{len:I}{tag:4s}{crc:I}"
let vals is calling carmen.unpack_named with r">{len:I}{tag:4s}{crc:I}", bytes
let len is vals.value at "len"
```

`unpack_named` returns a `map of string to CarmenValue`. A value-producing field
without a name is an `UnnamedField` error; duplicate names are a `DuplicateName`
error. Repeated named fields use `name`, `name#1`, `name#2`, … so no value is
lost (`layout`, `explain` and `unpack_named` share the convention). Writing
`{…}` inside a normal string literal would interpolate, so use a raw string
(`r"…"`) or escape the braces.

### Sizes and alignment

Standard mode (`=`, `<`, `>`, `!`) never pads. Native mode (`@`, default) pads
**between** fields only — never at the start or the end of the record, matching
CPython. A zero-count field still triggers its alignment in native mode, which
is how `@b0lh` keeps `l` at offset 4. `n`, `N` and `P` are rejected outside
native mode (`BadFormat`).

| Formula | `calcsize` |
|---|---|
| `@bhlq` | 24 |
| `=bhlq`, `<bhlq`, `>bhlq` | 15 |
| `@ci` | 8 |
| `@ic` | 5 |
| `@llh0l` | 24 |
| `=llh0l` | 10 |

## Values

`CarmenValue` is the dynamic value type used by formulas:

```pengu
omen CarmenValue derive Nexus:
    Signed with value as i64
    Unsigned with value as u64
    Real with value as f64
    Truth with value as bool
    Text with value as string

weave signed with v as i64 into CarmenValue
weave unsigned with v as u64 into CarmenValue
weave real with v as f64 into CarmenValue
weave truth with v as bool into CarmenValue
weave text with v as string into CarmenValue
```

Use the constructors; variant literals are not expressions in PenguScript. A
list of values must parenthesize each call because `with` is greedy:

```pengu
let values as list of CarmenValue is [
    (calling carmen.unsigned with 1),
    (calling carmen.text with "abcd"),
    (calling carmen.unsigned with 2),
]
```

`enchanting CarmenValue` exposes `is_signed`, `is_unsigned`, `is_real`,
`is_truth`, `is_text`, `as_signed`, `as_unsigned`, `as_real`, `as_truth`,
`as_text` and `type_name`. `as_text` returns an owned copy. `Signed` and
`Unsigned` are kept distinct: `pack` accepts a `Signed` value for `B` only when
it is within range, and reports `ValueOutOfRange` otherwise (Python raises
`struct.error`; Ruby silently truncates).

## Errors

`CarmenError` is an `omen`; `calling e.message` renders a human-readable line.

| Variant | Raised by |
|---|---|
| `BadFormat reason, position` | Structural problems: missing count for `z`, `p` count > 255, native-only code outside native mode, named `x`. |
| `UnknownCode code, position` | A character that is not part of the language. |
| `Truncated need, have` | `unpack`/`unpack_from` with too few bytes. |
| `TrailingBytes extra` | `unpack` with more bytes than the formula consumes. |
| `ValueCountMismatch expected, got` | `pack` with the wrong number of values. |
| `ValueKindMismatch index, expected` | A `Text` where `I` was expected, and so on. |
| `ValueOutOfRange index, detail` | Integer or half-float outside the field range. |
| `UnnamedField position` | `unpack_named` over an unnamed value field, or a named `x`. |
| `DuplicateName name` | The same field name twice. |
| `BufferTooSmall need, capacity` | `pack_into` into a shorter buffer. |
| `OffsetOutOfRange offset, length` | `unpack_from`/`pack_into` with an invalid window. |
| `MissingTerminator position` | `read_cstr`/`read_pascal` without a NUL in the remaining bytes. |
| `Unaligned position` | Reserved for strict alignment checks (currently unused). |

## Formula API (L1)

```pengu
weave seal with fmt as string into result of Carmen to CarmenError
weave calcsize with fmt as string into result of int to CarmenError
weave layout with fmt as string into result of list of CarmenField to CarmenError
weave pack with fmt as string, values as list of CarmenValue into result of string to CarmenError
weave pack_into with fmt as string, buffer as ref to byte, capacity as int, offset as int, values as list of CarmenValue into result of int to CarmenError
weave unpack with fmt as string, data as string into result of list of CarmenValue to CarmenError
weave unpack_from with fmt as string, data as string, offset as int into result of list of CarmenValue to CarmenError
weave unpack_named with fmt as string, data as string into result of map of string to CarmenValue to CarmenError
weave iter_unpack with fmt as string, data as string into result of list of list of CarmenValue to CarmenError
weave validate with fmt as string into result of int to CarmenError
weave explain with fmt as string into result of string to CarmenError
weave describe with fmt as string, data as string into result of string to CarmenError
weave hex with s as string into string
```

- `unpack` requires **exactly** `calcsize` bytes; `unpack_from` needs at least
  that many from `offset` and ignores the rest.
- `iter_unpack` splits a buffer into consecutive records and materializes the
  whole list (PenguScript has no generator syntax; `std.coro` covers the lazy
  pattern with explicit `resume`/`yield`). A zero-size formula or a length that
  is not a multiple of the record size is a `BadFormat`.
- `pack_into` writes at `offset` inside a caller-owned byte buffer and returns
  the number of bytes written; it never grows the buffer.
- `validate` returns the record size or the first `CarmenError`.
- `hex` renders bytes as lowercase hex without separators.

`Carmen` exposes `size`, `format`, `order`, `is_native`, `value_count` and
`fields`; `CarmenField` carries `name`, `code`, `offset`, `size`, `alignment`,
`index` (`-1` for padding) and `order`.

`layout` returns one `CarmenField` per element, including padding and each
repeated element:

```pengu
let fs is calling carmen.layout with "@bhlq"
# 0 offset 0  size 1  align 1 code b
# 1 offset 2  size 2  align 2 code h
# 2 offset 8  size 8  align 8 code l
# 3 offset 16 size 8  align 8 code q
```

`explain` prints the same information as TSV:

```
idx	offset	size	align	code	name
0	0	4	4	I	(value)
1	4	4	1	s	(value)
2	8	2	2	H	(value)
```

`describe` adds a hex column per field:

```
offset	size	code	name	hex
0	4	i	(value)	feffffff
4	4	s	(value)	61626300
8	2	H	(value)	0700
```

## Cursor API (L2)

### `CarmenReader`

```pengu
weave new_reader with data as string into CarmenReader
weave new_reader_at with data as string, offset as int into CarmenReader
weave new_reader_endian with data as string, e as Endianness into CarmenReader
```

The reader **borrows** `data`: do not banish the buffer while the reader is
alive. Methods:

| Group | Methods |
|---|---|
| Position | `order`, `with_endian`, `offset`, `remaining`, `at_end`, `seek`, `skip`, `align`, `align_bits`, `has` |
| Integers | `read_u8`, `read_u16`, `read_u32`, `read_u64`, `read_i8`, `read_i16`, `read_i32`, `read_i64` |
| Floating point | `read_f32`, `read_f64`, `read_f16` |
| Other scalars | `read_bool`, `read_char` |
| Text | `read_bytes n`, `read_cstr`, `read_pascal n` |
| Variable length | `read_varint`, `read_zigzag` |
| Bits | `read_bits n` |
| Views | `view n` (borrowed), `sub n` (bounded sub-reader) |
| Checks | `expect bytes`, `peek_u8`, `peek_u16`, `peek_u32`, `peek_u64` |
| Records | `read_record fmt` |

Every `read_*` returns `result of … to CarmenError`; a read past the end is
`Truncated`. `seek` and `skip` are bounds-checked. `align` advances to the next
multiple of `a`. `view` returns a borrowed byte slice without copying; `sub`
returns a reader limited to the next `n` bytes. `expect` compares and consumes,
which is the clean way to check a magic number:

```pengu
calling reader.expect with "\x89PNG\r\n\x1a\n"
```

`read_char` returns a `char`; `read_bytes` returns an owned `string` (binary
safe). For varints the encoding is unsigned LEB128; `read_zigzag` applies the
zigzag transform (used by protobuf `sint32`/`sint64`).

### `CarmenWriter`

```pengu
weave new_writer into CarmenWriter
weave new_writer_with with cap as int into CarmenWriter
weave new_writer_endian with e as Endianness into CarmenWriter
```

Methods: `order`, `with_endian`, `length`, `capacity`, `write_raw`,
`write_cstr`, `write_fixed s, n`, `write_pascal s, n`, `pad`, `align`,
`write_bool`, `write_char`, `write_u8`…`write_u64`, `write_i8`…`write_i64`,
`write_f32`, `write_f64`, `write_f16`, `write_varint`, `write_zigzag`,
`write_record`, `to_string`, `take_string`, `clear`, `reserve`.

`to_string` copies the buffer; `take_string` transfers ownership and resets the
writer to an empty buffer. The writer grows geometrically; `with_capacity`
avoids the first reallocations.

## Bits

Bit fields are not part of the formula language because they are not
byte-aligned and would break `calcsize`. They live in the cursor:

```pengu
var r as carmen.CarmenReader is calling carmen.new_reader with data
let version is calling r.read_bits with 3      # 5
let flags is calling r.read_bits with 5        # 5
let next is calling r.read_u8                  # 0x5C
```

`read_bits` takes 1–64 bits, MSB-first, and consumes whole bytes as needed.
`align_bits` drops the rest of the current byte. The writer side mirrors it:
`write_bits`, `align_bits` are part of the same cursor.

## Worked examples

### TCP-like binary frame

```pengu
import std.carmen
import std.net

let hdr is calling carmen.unpack_named with r">{seq:H}{flags:H}{length:I}{crc:I}", frame
if not hdr.is_ok:
    return calling err_of with hdr.error
let length is hdr.value at "length"
judge (length):
    when Unsigned with value ->
        # `value` is only trusted after checking the formula
        let body is calling carmen.unpack_from with ">4s", frame, 12
        ...
```

### PNG IHDR

```pengu
# width, height, bit depth, color type, compression, filter, interlace
let ihdr is calling carmen.unpack_named with ">IIBBBBB", chunk
```

### ELF64 header prefix

```pengu
# e_ident (16 bytes), e_type, e_machine, e_version, e_entry
let elf is calling carmen.unpack_named with "16sHHIQ", data
if elf.is_ok:
    judge (elf.value at "entry"):
        when Unsigned with value ->
            let entry is value
```

### ZIP central directory

```pengu
# signature, version made by, version needed, flags, method, time, date,
# crc, compressed size, uncompressed size, name length, extra length,
# comment length, disk, internal attrs, external attrs, local offset
let cd is calling carmen.unpack_named with ">IHHHHHHIIIHHHHHII", record
```

### Writing a glTF-style chunk

```pengu
var w as carmen.CarmenWriter is calling carmen.new_writer_endian with carmen.Endianness.Little
calling w.write_u32 with 0x46546C67   # magic "glTF"
calling w.write_u32 with 2
calling w.write_u32 with (payload.length to u64)
calling w.write_raw with payload
let out as string is calling w.take_string
```

### A typed decoder

```pengu
weave header_tuple with raw as string into (u32, string, u16):
    let vals is calling carmen.unpack with ">I4sH", raw
    # ... validate and convert ...
    return seq, tag, crc

weave decode_header with raw as string into result of (u32, string, u16) to CarmenError:
    let vals is calling carmen.unpack with ">I4sH", raw
    if not vals.is_ok:
        return calling err_of with vals.error
    let t is calling header_tuple with raw
    return calling ok_of with t
```

## Python compatibility

Carmen mirrors CPython's `struct` for the standard format language:

| Python | Carmen |
|---|---|
| `struct.pack(fmt, *v)` | `carmen.pack fmt, values` |
| `struct.pack_into(fmt, buf, off, *v)` | `carmen.pack_into fmt, buf, cap, off, values` |
| `struct.unpack(fmt, buf)` | `carmen.unpack fmt, data` |
| `struct.unpack_from(fmt, buf, off=0)` | `carmen.unpack_from fmt, data, off` |
| `struct.iter_unpack(fmt, buf)` | `carmen.iter_unpack fmt, data` |
| `struct.calcsize(fmt)` | `carmen.calcsize fmt` |
| `struct.Struct(fmt)` | `carmen.seal fmt` |

Differences:

- Carmen returns `result`; Python raises `struct.error`.
- Ruby/Perl truncate out-of-range integers; Carmen raises `ValueOutOfRange`
  like Python.
- There is **no global format cache**. `seal` is the explicit cache; free
  functions parse the formula each call. This keeps the module thread-safe and
  avoids hidden ownership of compiled formats.
- `P` round-trips as an integer pointer; do not use it for data that must be
  portable.
- `n`, `N`, `P` and native `l`/`L` sizes follow the C ABI, so a formula with
  those codes is intentionally platform-dependent — the same as Python.

## Memory and ownership

- `pack` returns an owned `string`; `banish` it.
- `unpack*` returns owned values; `Text` values own their bytes, `Carmen` and
  `CarmenReader` borrow their inputs.
- `Carmen.fields` deep-copies the names, so the list is safe after the handle is
  banished.
- `CarmenWriter.take_string` transfers the buffer; after that the writer keeps a
  small fresh buffer and can be reused.
- `sub`, `view` and readers alias the original buffer; the buffer must outlive
  them.

## Performance

- `pack`/`unpack` parse the formula per call (O(len fmt)); `seal` once and reuse
  the handle for hot paths.
- Bulk `unpack` is cheaper than N cursor `read_*` calls: cursor results are
  boxed `result` values, while the values in the returned list are stored
  inline.
- The writer grows geometrically; `with_capacity` avoids the first copies.

## Versioning

`CARMEN_VERSION` is `"1.0.0"`. Since 0.23.0 every standard module carries its
own version so its evolution is visible independently of the compiler release;
see §19.0 of `LANGUAGE.md`.

## Testing

`tests/conformance/compliance/carmen_formula.pengu` covers every code, the
half-float vectors, named fields, padding, endianness, readers, writers, bits
and the introspection helpers against golden bytes produced with CPython
3.14.8.
