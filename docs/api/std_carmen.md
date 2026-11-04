# std.carmen

> Source: `std/carmen.pengu`

std/carmen.pengu — fixed-layout binary records: pack and unpack by formula.

`carmen` is PenguScript's answer to Python's `struct`: a compact formula
string describes the layout of a binary record (`>I4sH` = big-endian u32,
four bytes, u16) and the module reads or writes it without a schema class,
a code generator or a C dependency. Every protocol with fixed offsets —
TCP frame headers, PNG chunks, ELF headers, ZIP central directories, glTF
chunks — becomes one formula plus one call.

The name is Latin for *song* / *ritual formula*: the formula string is the
incantation that turns bytes into values and back.

## Quick start
```pengu
import std.carmen

weave main into int:
    var header as result of string to carmen.CarmenError is
        calling carmen.pack with ">I4sH",
            [(calling carmen.unsigned with 1),
             (calling carmen.text with "abcd"),
             (calling carmen.unsigned with 2)]
    if not header.is_ok:
        var why as string is calling header.error.message
        calling print with "cannot pack: {why}\n"
        banish why
        return 1
    defer banish header.value
    var back as result of list of carmen.CarmenValue to carmen.CarmenError is
        calling carmen.unpack with ">I4sH", header.value
    if not back.is_ok:
        return 1
    defer banish back.value
    return 0
```

## Layers
| Layer | API | Use it when |
|---|---|---|
| Formula | `seal`, `calcsize`, `pack`, `unpack`, `unpack_named`, `explain` | the layout is data, not a type |
| Cursor | `CarmenReader`, `CarmenWriter` | the record is streamed, partial or variable-length |
| Insight | `layout`, `explain` | a parser misbehaves and you need to see offsets |

## Formula grammar
A formula is a strict superset of Python's `struct` format:
```
format := prefix? item*
item   := prefix | field
prefix := '@' | '=' | '<' | '>' | '!'
field  := named | plain
named  := '{' identifier ':' count? code '}'
plain  := count? code
```
- `@` native order **and** native alignment (the default), `=` native order
  with standard alignment, `<` little, `>`/`!` big. A prefix may appear
  again mid-formula to switch order for the following fields.
- Codes: `x c b B ? h H i I l L q Q n N e f d s p P` (Python) plus `z`
  (NUL-padded text, count required), `v`/`V` (little-endian u16/u32).
- `{name:spec}` names a field for `layout`, `unpack_named` and `explain`.
  Because `{}` interpolates in PenguScript, write named formulas as raw
  strings: `r"{width:I}{height:I}"`.
- Repeats produce one value each: `4B` yields four `Unsigned` values, while
  `4s` yields one four-byte `Text`. A named repeat yields `flags`, `flags#1`,
  `flags#2`, … so no value is lost.

## Python compatibility
For every formula that uses only Python codes and prefixes, `carmen`
produces byte-identical output to CPython's `struct` on the same platform,
including native `long`/pointer sizes, alignment rules, `s`/`p` truncation,
zero counts and out-of-range errors. Divergences are deliberate and small:
malformed input is a `CarmenError` value (Python raises), `n`/`N`/`P` are
rejected outside native mode, and `v`/`V`/`z`/named fields are extensions.

## Ownership
| Value | Owns | Release with |
|---|---|---|
| `string` from `pack` / `explain` | its bytes | `banish` |
| `list of CarmenValue` from `unpack` | the list and every `Text` | `banish` |
| `Carmen` from `seal` | formula and field list | `banish` |
| `CarmenReader` | nothing (borrows the data) | nothing |
| `CarmenWriter` | its growing buffer | `banish` |

A `CarmenReader` must not outlive the `string` it reads, and `view`/`sub`
results must not outlive either.

## Complexity
| Operation | Cost |
|---|---|
| `seal`, `calcsize`, `layout` | O(len formula) |
| `pack` | O(len formula + size) |
| `unpack` | O(len formula + values) |
| `reader.read_*` | O(1) plus one result box |
| `writer.write_*` | O(1) amortised |
| `explain` | O(size) |

## Error table
| Variant | Meaning |
|---|---|
| `BadFormat` | malformed formula (missing count, bad name, …) |
| `UnknownCode` | a code that is not in the grammar |
| `Truncated` | the buffer is shorter than the formula needs |
| `TrailingBytes` | `unpack` received more bytes than the formula uses |
| `ValueCountMismatch` | `pack` got the wrong number of values |
| `ValueKindMismatch` | a value has the wrong variant for its field |
| `ValueOutOfRange` | a value does not fit the field's width |
| `UnnamedField` | a name was attached to a padding field |
| `DuplicateName` | the same field name appears twice |
| `BufferTooSmall` | `pack_into` target has no room |
| `OffsetOutOfRange` | `unpack_from` offset is outside the buffer |
| `MissingTerminator` | `read_cstr` found no NUL before the end |
| `Unaligned` | a byte read started mid-byte in the bit cursor |

---

### `CARMEN_VERSION`

> **CARMEN_VERSION** : string

 Carmen module version.

### `_carmen_alloc`

> **_carmen_alloc**(n: int) -> string

 Allocates `n` zeroed bytes as a raw owned `string`.

 ## Memory
 One allocation; release with `banish`.

### `_carmen_ptr`

> **_carmen_ptr**(data: ref to string) -> ref to u8

 Writable pointer to a raw byte buffer.

 ## Memory
 Borrows; no allocation.

### `_carmen_copy_range`

> **_carmen_copy_range**(data: string, off: int, n: int) -> string

 Owned copy of `n` bytes starting at `off`.

 ## Memory
 One allocation; release with `banish`.

### `_carmen_view`

> **_carmen_view**(data: string, off: int, n: int) -> slice of u8

 Borrowed `slice of byte` over `n` bytes at `off`.

 ## Memory
 No allocation; the slice aliases `data`.

### `_carmen_long_size`

> **_carmen_long_size**() -> int

 `sizeof(long)` of the C compiler that will run the program.

### `_carmen_long_align`

> **_carmen_long_align**() -> int

 `_Alignof(long)` of the C compiler that will run the program.

### `_carmen_ptr_size`

> **_carmen_ptr_size**() -> int

 `sizeof(void *)` of the target platform.

### `_carmen_ptr_align`

> **_carmen_ptr_align**() -> int

 `_Alignof(void *)` of the target platform.

### `_carmen_reserve`

> **_carmen_reserve**(data: ref to string, len: int, cap: ref to int, need: int) -> void

 Appends `n` bytes at `off` of `src` to a writer buffer, growing it.

 ## Memory
 May `realloc`; aborts on OOM like `std.builder`.

### `_carmen_take`

> **_carmen_take**(data: ref to string, len: int) -> string

 Returns the writer buffer as an owned `string` of `len` bytes.

 ## Memory
 Transfers the buffer; the writer fields must be reset by the caller.

### `Endianness`

> omen Endianness

```pengu
    Native
    Little
    Big
```

 Byte order of a field, a formula or a cursor.

 `Native` is only used while resolving prefixes; fields always store the
 resolved `Little` or `Big` order.

### `endian_name`

> **endian_name**(e: Endianness) -> string

 Human name of an order.

 ## Example
 ```pengu
 calling carmen.endian_name with carmen.Endianness.Big   # "big"
 ```

### `native_order`

> **native_order**() -> Endianness

 Resolves the host byte order.

 ## Memory
 O(1); no allocation.

### `CarmenValue`

> omen CarmenValue

```pengu
    Signed with value as i64
    Unsigned with value as u64
    Real with value as f64
    Truth with value as bool
    Text with value as string
```

 One value read from, or written to, a binary record.

 A tagged union instead of a single `i64`: the wire distinguishes signed from
 unsigned and a `u32` field must not silently accept `-1`.

### `signed`

> **signed**(v: i64) -> CarmenValue

 Wraps a signed integer.

### `unsigned`

> **unsigned**(v: u64) -> CarmenValue

 Wraps an unsigned integer.

### `real`

> **real**(v: f64) -> CarmenValue

 Wraps a floating point number.

### `truth`

> **truth**(v: bool) -> CarmenValue

 Wraps a boolean.

### `text`

> **text**(v: string) -> CarmenValue

 Wraps a text value.

### `is_signed`

> **is_signed**() -> bool

 True when the value is a signed integer.

### `is_unsigned`

> **is_unsigned**() -> bool

 True when the value is an unsigned integer.

### `is_real`

> **is_real**() -> bool

 True when the value is a float.

### `is_truth`

> **is_truth**() -> bool

 True when the value is a boolean.

### `is_text`

> **is_text**() -> bool

 True when the value is text.

### `as_signed`

> **as_signed**() -> maybe i64

 The signed payload, when the value is signed.

### `as_unsigned`

> **as_unsigned**() -> maybe u64

 The unsigned payload, when the value is unsigned.

### `as_real`

> **as_real**() -> maybe f64

 The float payload, when the value is real.

### `as_truth`

> **as_truth**() -> maybe bool

 The boolean payload, when the value is a truth value.

### `as_text`

> **as_text**() -> maybe string

 The text payload, when the value is text.

### `type_name`

> **type_name**() -> string

 Name of the variant, for diagnostics.

### `_carmen_dup`

> **_carmen_dup**(s: string) -> string

 Owned copy of a string.

 ## Memory
 One allocation; release with `banish`.

### `CarmenError`

> omen CarmenError

```pengu
    BadFormat with reason as string, position as int
    UnknownCode with code as char, position as int
    Truncated with need as int, have as int
    TrailingBytes with extra as int
    ValueCountMismatch with expected as int, got as int
    ValueKindMismatch with index as int, expected as string
    ValueOutOfRange with index as int, detail as string
    UnnamedField with position as int
    DuplicateName with name as string
    BufferTooSmall with need as int, capacity as int
    OffsetOutOfRange with offset as int, length as int
    MissingTerminator with position as int
    Unaligned with position as int
```

 Everything that can go wrong while reading, writing or compiling a formula.

 Malformed bytes are normal input here, so every failure is a value; `carmen`
 never panics on user data.

### `message`

> **message**() -> string

 One English sentence describing the failure.

### `is_python_compatible`

> **is_python_compatible**(fmt: string) -> bool

 True when the formula uses only Python codes and prefixes.

 ## Memory
 O(len formula).

### `_is_space`

> **_is_space**(c: char) -> bool

 ----------------------------------------------------------------------------
 Character classes
 ----------------------------------------------------------------------------

### `_is_digit`

> **_is_digit**(c: char) -> bool

_Undocumented._

### `_is_ident_start`

> **_is_ident_start**(c: char) -> bool

_Undocumented._

### `_is_ident_char`

> **_is_ident_char**(c: char) -> bool

_Undocumented._

### `_is_code`

> **_is_code**(c: char) -> bool

 True when `c` is a formula code.

### `_code_class`

> **_code_class**(c: char) -> int

 0 = padding, 1 = signed, 2 = unsigned, 3 = float, 4 = text, 5 = char, 6 = bool.

### `_elem_size`

> **_elem_size**(c: char, native: bool) -> int

 Size in bytes of one element of `c`; 1 for text/padding (the count is the size).

### `_elem_align`

> **_elem_align**(c: char) -> int

 Native alignment of one element of `c`.

### `_align_up`

> **_align_up**(off: int, a: int) -> int

 Rounds `off` up to the next multiple of `a`.

### `_native_only`

> **_native_only**(c: char) -> bool

 True when `c` may only be used in native mode.

### `_bad`

> **_bad**(reason: string, position: int) -> CarmenError

 ----------------------------------------------------------------------------
 Error constructors (keep call sites short)
 ----------------------------------------------------------------------------

### `_unknown`

> **_unknown**(code: char, position: int) -> CarmenError

_Undocumented._

### `_truncated`

> **_truncated**(need: int, have: int) -> CarmenError

_Undocumented._

### `_count_mismatch`

> **_count_mismatch**(expected: int, got: int) -> CarmenError

_Undocumented._

### `_kind_mismatch`

> **_kind_mismatch**(index: int, expected: string) -> CarmenError

_Undocumented._

### `_out_of_range`

> **_out_of_range**(index: int, detail: string) -> CarmenError

_Undocumented._

### `_duplicate`

> **_duplicate**(name: string) -> CarmenError

_Undocumented._

### `CarmenField`

> rune CarmenField

```pengu
    name as string
    code as char
    offset as int
    size as int
    alignment as int
    index as int
    order as Endianness
```

 One element of a compiled formula.

### `Carmen`

> rune Carmen

```pengu
    _fmt as string
    _fields as list of CarmenField
    _size as int
    _order as Endianness
    _native as bool
```

 A compiled formula. Compile once, reuse for many records.

### `size`

> **size**() -> int

 Total record size in bytes.

### `format`

> **format**() -> string

 Formula string this handle was compiled from.

### `order`

> **order**() -> Endianness

 Default byte order.

### `is_native`

> **is_native**() -> bool

 True when the formula starts in native mode.

### `value_count`

> **value_count**() -> int

 Number of values the formula consumes.

### `fields`

> **fields**() -> list of CarmenField

 Copies every field, duplicating names.

### `seal`

> **seal**(fmt: string) -> result of Carmen to CarmenError

 Compiles `fmt` into a reusable handle.

 ## Example
 `let h is calling carmen.seal with ">I4sH"`

 ## Complexity
 O(len fmt).

### `calcsize`

> **calcsize**(fmt: string) -> result of int to CarmenError

 Size in bytes of the record described by `fmt`.

 ## Example
 `let n is calling carmen.calcsize with ">I4sH"` → `10`

### `layout`

> **layout**(fmt: string) -> result of list of CarmenField to CarmenError

 Fields of `fmt`, with offsets, sizes and alignments.

 ## Example
 `let fs is calling carmen.layout with "<2sI"` → two fields at offsets 0 and 2

### `_is_little`

> **_is_little**(e: Endianness) -> bool

 True when `e` means little-endian on this platform.

### `_native_is_little`

> **_native_is_little**() -> bool

_Undocumented._

### `_get_u`

> **_get_u**(data: string, off: int, n: int, e: Endianness) -> u64

 Reads `n` bytes at `off` as an unsigned integer.

### `_put_u`

> **_put_u**(data: ref to string, off: int, n: int, v: u64, e: Endianness) -> void

 Writes the low `n` bytes of `v` at `off`.

### `_f32_from_bits`

> **_f32_from_bits**(b: u32) -> float

_Undocumented._

### `_f32_bits`

> **_f32_bits**(f: float) -> u32

_Undocumented._

### `_f64_from_bits`

> **_f64_from_bits**(b: u64) -> f64

_Undocumented._

### `_f64_bits`

> **_f64_bits**(f: f64) -> u64

_Undocumented._

### `_half_to_f32`

> **_half_to_f32**(h: u16) -> float

 Converts a half-precision bit pattern to a 32-bit float.

### `_f32_to_half`

> **_f32_to_half**(f: float, idx: int) -> result of u16 to CarmenError

 Converts a 32-bit float to a half-precision bit pattern.

 ## Errors
 Finite values outside ±65504 produce `ValueOutOfRange`.

### `_signed_max`

> **_signed_max**(size: int) -> i64

 ----------------------------------------------------------------------------
 Value coercion
 ----------------------------------------------------------------------------

### `_signed_min`

> **_signed_min**(size: int) -> i64

_Undocumented._

### `_unsigned_max`

> **_unsigned_max**(size: int) -> u64

_Undocumented._

### `_as_i64`

> **_as_i64**(v: CarmenValue, idx: int) -> result of i64 to CarmenError

 Extracts an integer (any width) from a value.

### `_as_u64`

> **_as_u64**(v: CarmenValue, idx: int) -> result of u64 to CarmenError

_Undocumented._

### `_as_f64`

> **_as_f64**(v: CarmenValue, idx: int) -> result of f64 to CarmenError

_Undocumented._

### `_as_text`

> **_as_text**(v: CarmenValue, idx: int) -> result of string to CarmenError

_Undocumented._

### `_copy_to`

> **_copy_to**(src: string, dst: ref to u8, off: int) -> void

 Copies `src` into a byte buffer at `off`.

### `_pack_text`

> **_pack_text**(f: CarmenField, v: CarmenValue, out: ref to string, idx: int) -> result of void to CarmenError

_Undocumented._

### `_pack_field`

> **_pack_field**(f: CarmenField, v: CarmenValue, out: ref to string, idx: int) -> result of void to CarmenError

_Undocumented._

### `_unpack_field`

> **_unpack_field**(f: CarmenField, data: string) -> result of CarmenValue to CarmenError

 ----------------------------------------------------------------------------
 Decoding
 ----------------------------------------------------------------------------

### `_take_error_void`

> **_take_error_void**(r: ref to result of void to CarmenError) -> CarmenError

 ----------------------------------------------------------------------------
 Record decode/encode
 ----------------------------------------------------------------------------

### `_take_error_value`

> **_take_error_value**(r: ref to result of CarmenValue to CarmenError) -> CarmenError

_Undocumented._

### `_decode_all`

> **_decode_all**(h: Carmen, data: string) -> result of list of CarmenValue to CarmenError

_Undocumented._

### `pack`

> **pack**(fmt: string, values: list of CarmenValue) -> result of string to CarmenError

 Packs `values` into a new byte string using `fmt`.

 ## Example
 `calling carmen.pack with ">I4sH", [calling carmen.unsigned with 1, calling carmen.text with "abcd", calling carmen.unsigned with 2]`

 ## Errors
 `ValueCountMismatch`, `ValueKindMismatch`, `ValueOutOfRange`.

### `pack_into`

> **pack_into**(fmt: string, buffer: ref to u8, capacity: int, offset: int, values: list of CarmenValue) -> result of int to CarmenError

 Packs `values` into `buffer` at `offset`, returning the number of bytes
 written.

 ## Errors
 `BufferTooSmall` when `offset + size` exceeds `capacity`.

### `unpack`

> **unpack**(fmt: string, data: string) -> result of list of CarmenValue to CarmenError

 Unpacks exactly one record; the buffer must be exactly the record size.

 ## Errors
 `Truncated` or `TrailingBytes`.

### `unpack_from`

> **unpack_from**(fmt: string, data: string, offset: int) -> result of list of CarmenValue to CarmenError

 Unpacks one record starting at `offset`; bytes after the record are ignored.

 ## Errors
 `OffsetOutOfRange` or `Truncated`.

### `CarmenWriter`

> rune CarmenWriter

```pengu
    _data as string
    _len as int
    _cap as int
    _order as Endianness
    _bit as int
```

 Grows a byte buffer and appends encoded values to it.

 The writer owns its buffer; `to_string` copies it, `take_string` transfers
 it.

### `new_writer`

> **new_writer**() -> CarmenWriter

 Creates an empty writer with a 256-byte buffer.

 ## Example
 `var w as carmen.CarmenWriter is calling carmen.new_writer`

### `new_writer_with`

> **new_writer_with**(cap: int) -> CarmenWriter

 Creates an empty writer with at least `cap` bytes of buffer.

### `new_writer_endian`

> **new_writer_endian**(e: Endianness) -> CarmenWriter

 Creates an empty writer that starts in `e`.

### `with_endian`

> **with_endian**(e: Endianness) -> void

 Selects the byte order for following writes.

### `length`

> **length**() -> int

 Bytes appended so far.

### `capacity`

> **capacity**() -> int

 Bytes of buffer currently reserved.

### `_ensure`

> **_ensure**(need: int) -> void

_Undocumented._

### `write_raw`

> **write_raw**(s: string) -> void

 Appends the raw bytes of `s`.

### `write_cstr`

> **write_cstr**(s: string) -> void

 Appends a NUL-terminated copy of `s`.

### `write_fixed`

> **write_fixed**(s: string, n: int) -> void

 Appends `s` truncated or NUL-padded to exactly `n` bytes.

### `write_bits`

> **write_bits**(v: u64, n: int) -> void

 Appends `n` bits (1..64) MSB-first.

 Bits share a byte: after `write_bits 3, 5` the next `write_bits 5, 3`
 fills the same byte. Call `align_bits` before a byte-aligned write.

### `align_bits`

> **align_bits**() -> void

 Pads the current partial bit byte so the next write starts aligned.

### `write_pascal`

> **write_pascal**(s: string, n: int) -> void

 Appends a Pascal string of exactly `n` bytes (length byte + text).

### `pad`

> **pad**(n: int) -> void

 Appends `n` zero bytes.

### `align`

> **align**(a: int) -> void

 Appends zero bytes until the length is a multiple of `a`.

### `write_bool`

> **write_bool**(v: bool) -> void

 Appends a boolean as one byte.

### `write_char`

> **write_char**(c: char) -> void

 Appends one character.

### `write_u8`

> **write_u8**(v: u64) -> void

 Appends an unsigned 8-bit integer.

### `write_u16`

> **write_u16**(v: u64) -> void

 Appends an unsigned 16-bit integer.

### `write_u32`

> **write_u32**(v: u64) -> void

 Appends an unsigned 32-bit integer.

### `write_u64`

> **write_u64**(v: u64) -> void

 Appends an unsigned 64-bit integer.

### `write_i8`

> **write_i8**(v: i64) -> void

 Appends a signed 8-bit integer.

### `write_i16`

> **write_i16**(v: i64) -> void

 Appends a signed 16-bit integer.

### `write_i32`

> **write_i32**(v: i64) -> void

 Appends a signed 32-bit integer.

### `write_i64`

> **write_i64**(v: i64) -> void

 Appends a signed 64-bit integer.

### `write_f32`

> **write_f32**(v: float) -> void

 Appends a 32-bit float.

### `write_f64`

> **write_f64**(v: f64) -> void

 Appends a 64-bit float.

### `write_f16`

> **write_f16**(v: f64) -> result of void to CarmenError

 Appends a half-precision float.

 ## Errors
 Finite values outside ±65504 produce `ValueOutOfRange`.

### `write_varint`

> **write_varint**(v: u64) -> void

 Appends an unsigned LEB128 varint.

### `write_zigzag`

> **write_zigzag**(v: i64) -> void

 Appends a ZigZag + LEB128 signed varint.

### `write_record`

> **write_record**(fmt: string, values: list of CarmenValue) -> result of void to CarmenError

 Appends the record produced by `pack` for `fmt` and `values`.

### `to_string`

> **to_string**() -> string

 Copies the buffer into a new owned string.

### `take_string`

> **take_string**() -> string

 Transfers the buffer into an owned string and resets the writer.

### `clear`

> **clear**() -> void

 Discards every byte, keeping the buffer.

### `reserve`

> **reserve**(n: int) -> void

 Grows the buffer to at least `n` bytes.

### `CarmenReader`

> rune CarmenReader

```pengu
    _data as string
    _offset as int
    _end as int
    _bit as int
    _order as Endianness
```

 Reads values from an existing byte string with a moving cursor.

 The reader borrows its data; do not `banish` the source while a reader or a
 `view`/`sub` result is alive.

### `new_reader`

> **new_reader**(data: string) -> CarmenReader

 Creates a reader over `data` starting at byte 0.

 ## Example
 `var r as carmen.CarmenReader is calling carmen.new_reader with blob`

### `new_reader_at`

> **new_reader_at**(data: string, offset: int) -> CarmenReader

 Creates a reader over `data` starting at `offset`.

### `new_reader_endian`

> **new_reader_endian**(data: string, e: Endianness) -> CarmenReader

 Creates a reader over `data` that starts in `e`.

### `offset`

> **offset**() -> int

 Current byte offset.

### `remaining`

> **remaining**() -> int

 Bytes left before the end of the window.

### `at_end`

> **at_end**() -> bool

 True when the cursor reached the end of the window.

### `seek`

> **seek**(pos: int) -> void

 Moves the cursor to `pos` (clamped to the window).

### `skip`

> **skip**(n: int) -> int

 Skips `n` bytes; returns the number actually skipped.

### `has`

> **has**(n: int) -> bool

 True when there are at least `n` bytes left.

### `_take_u`

> **_take_u**(n: int) -> result of u64 to CarmenError

_Undocumented._

### `read_u8`

> **read_u8**() -> result of u64 to CarmenError

 Reads an unsigned 8-bit integer.

### `read_u16`

> **read_u16**() -> result of u64 to CarmenError

 Reads an unsigned 16-bit integer.

### `read_u32`

> **read_u32**() -> result of u64 to CarmenError

 Reads an unsigned 32-bit integer.

### `read_u64`

> **read_u64**() -> result of u64 to CarmenError

 Reads an unsigned 64-bit integer.

### `_take_i`

> **_take_i**(n: int, bits: int) -> result of i64 to CarmenError

_Undocumented._

### `read_i8`

> **read_i8**() -> result of i64 to CarmenError

 Reads a signed 8-bit integer.

### `read_i16`

> **read_i16**() -> result of i64 to CarmenError

 Reads a signed 16-bit integer.

### `read_i32`

> **read_i32**() -> result of i64 to CarmenError

 Reads a signed 32-bit integer.

### `read_i64`

> **read_i64**() -> result of i64 to CarmenError

 Reads a signed 64-bit integer.

### `read_f32`

> **read_f32**() -> result of f64 to CarmenError

 Reads a 32-bit float.

### `read_f64`

> **read_f64**() -> result of f64 to CarmenError

 Reads a 64-bit float.

### `read_f16`

> **read_f16**() -> result of f64 to CarmenError

 Reads a half-precision float.

### `read_bool`

> **read_bool**() -> result of bool to CarmenError

 Reads a boolean byte.

### `read_char`

> **read_char**() -> result of char to CarmenError

 Reads one character.

### `read_bytes`

> **read_bytes**(n: int) -> result of string to CarmenError

 Reads `n` bytes as an owned string.

### `read_cstr`

> **read_cstr**() -> result of string to CarmenError

 Reads bytes up to the next NUL, which is consumed but not returned.

### `read_pascal`

> **read_pascal**(n: int) -> result of string to CarmenError

 Reads a Pascal string of `n` total bytes (length byte + text).

### `read_varint`

> **read_varint**() -> result of u64 to CarmenError

 Reads an unsigned LEB128 varint.

### `read_zigzag`

> **read_zigzag**() -> result of i64 to CarmenError

 Reads a ZigZag + LEB128 signed varint.

### `read_bits`

> **read_bits**(n: int) -> result of u64 to CarmenError

 Reads `n` bits (MSB first) as an unsigned integer.

### `view`

> **view**(n: int) -> result of slice of u8 to CarmenError

 Consumes `n` bytes and returns a borrowed slice of them.

### `sub`

> **sub**(n: int) -> result of CarmenReader to CarmenError

 Consumes `n` bytes and returns a reader window over them.

### `expect`

> **expect**(s: string) -> result of void to CarmenError

 Requires the next bytes to equal `s`.

### `peek_u8`

> **peek_u8**() -> result of u64 to CarmenError

 Reads the next byte without moving the cursor.

### `peek_u16`

> **peek_u16**() -> result of u64 to CarmenError

 Reads the next 16-bit integer without moving the cursor.

### `peek_u32`

> **peek_u32**() -> result of u64 to CarmenError

 Reads the next 32-bit integer without moving the cursor.

### `peek_u64`

> **peek_u64**(n: int) -> result of u64 to CarmenError

 Reads `n` bytes as a `u64` without moving the cursor.

### `read_record`

> **read_record**(fmt: string) -> result of list of CarmenValue to CarmenError

 Reads the next record described by `fmt`.

 The cursor advances by `calcsize(fmt)`.

### `validate`

> **validate**(fmt: string) -> result of int to CarmenError

 Validates `fmt`, returning the record size or a `CarmenError`.

 ## Example
 `var n as int is (calling carmen.validate with ">I4sH").value`

### `hex`

> **hex**(s: string) -> string

 Returns a lowercase hexadecimal rendering of the bytes of `s`.

 ## Example
 `calling carmen.hex with "AB"` → `"4142"`

### `_field_label`

> **_field_label**(f: CarmenField) -> string

_Undocumented._

### `explain`

> **explain**(fmt: string) -> result of string to CarmenError

 Renders a human-readable layout table for `fmt`.

 Columns: index, byte offset, size, alignment, code and field name.

 ## Example
 ```pengu
 var t as string is (calling carmen.explain with ">I4sH").value
 calling print with t
 banish t
 ```

### `describe`

> **describe**(fmt: string, data: string) -> result of string to CarmenError

 Renders an annotated hexadecimal dump of `data` according to `fmt`.

 One line per field: offset, size, code, name and the field bytes in hex.

### `unpack_named`

> **unpack_named**(fmt: string, data: string) -> result of map of string to CarmenValue to CarmenError

 Unpacks `fmt` into a map keyed by the declared field names.

 Every value-producing field must be named; padding fields are ignored.
 Repeated names become `name`, `name#1`, `name#2`, …

 ## Errors
 `UnnamedField` when a value field has no name.

 ## Memoria
 The map owns the values; release it with `banish`.

### `iter_unpack`

> **iter_unpack**(fmt: string, data: string) -> result of list of list of CarmenValue to CarmenError

 Unpacks a buffer holding a whole number of records.

 ## Errors
 `BadFormat` when `calcsize(fmt)` is zero or does not divide the buffer.

