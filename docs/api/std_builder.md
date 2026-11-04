# std.builder

> Source: `std/builder.pengu`

std/builder.pengu — `StringBuilder`, an amortised-O(1) text accumulator.

`StringBuilder` is the canonical way to assemble a string piece by piece
without the quadratic cost of `out = "{out}{piece}"`. It owns one contiguous
byte buffer, grows it with the usual 2x amortised strategy, and releases that
buffer when the builder is banished.

## Why not just interpolation?
`"{a}{b}{c}"` is perfect for a fixed number of pieces: it allocates exactly
once. A builder is for a *loop*, a recursive traversal or a generator whose
piece count is not known when the code is written. Appending `n` pieces to a
builder costs one `memcpy` over the final length; concatenating them with
interpolation costs O(n²) bytes copied.

## Ownership
The builder owns its buffer. `finish` **transfers** that buffer to the
returned `string` (no copy, O(1)); `to_string` **copies** it and leaves the
builder usable. The returned string of both methods is owned and must be
released with `banish` (or `defer banish`).

```pengu
import std.builder

weave main into int:
    var sb as StringBuilder is calling StringBuilder.new
    defer banish sb
    calling sb.append with "Hola, "
    calling sb.append with "mundo"
    var s as string is calling sb.finish
    defer banish s
    calling spark.println with s       # Hola, mundo
    return 0
```

`banish sb` releases the internal buffer. After `finish` the builder is
empty, so banishing it is a safe no-op.

## Implementation note: the backing field is a `string`
The public shape of a builder is `{ pointer, len, cap }`, but the buffer is
stored as an owned `PenguString` rather than a bare `ref to byte`. That is
deliberate: `derive Nexus` on a rune frees `string`, `list` and `map` fields,
so `banish builder` releases the buffer without a custom destructor (which
the language does not provide). The buffer is an SDS allocation: `_data.len`
and the SDS header mirror `_len`, while `_cap` is a lower bound on the
capacity (`sdsalloc` may be larger). The `antiquus` helpers write bytes
through the `PenguString` header (`memcpy`, `memmove`, `snprintf`,
`sdsMakeRoomFor`, `sdsRemoveFreeSpace`) and reset the header on `finish`. No
language-level operation on a `string` is mutable, so there is no pure
alternative that preserves O(1) append.

## Complexity
| Operation | Cost |
|---|---|
| `append`, `append_char`, `append_slice` | O(n) bytes copied, amortised O(1) growth |
| `append_int`, `append_i64`, `append_float`, `append_f64` | O(digits), no temporary string |
| `insert` | O(len - pos) bytes moved |
| `reverse` | O(len) |
| `finish` | O(1), no copy |
| `to_string`, `substring` | O(copied bytes) |
| `len`, `capacity`, `is_empty`, `char_at`, `byte_at` | O(1) |
| `bytes_view` | O(1), non-owning |

---

### `BUILDER_VERSION`

> **BUILDER_VERSION** : string

 Builder module version.

### `BUILDER_DEFAULT_CAPACITY`

> **BUILDER_DEFAULT_CAPACITY** : int

 Capacity of a builder created with `StringBuilder.new`.

### `StringBuilder`

> rune StringBuilder

```pengu
    _data as string
    _len as int
    _cap as int
```

 A growable byte buffer for assembling text.

 The fields are private: use `append`/`insert`/`finish` instead of touching
 the buffer. `_data` owns the SDS allocation, `_len` is the number of bytes in
 use and `_cap` is a lower bound on the usable capacity. SDS always keeps a
 NUL terminator after the used bytes.

 ## Memoria
 The builder owns `_data`. Release the whole builder with `banish` (or
 `defer banish`); `finish` transfers the buffer away and resets the builder.

### `_builder_alloc`

> **_builder_alloc**(cap: int) -> string

 Allocates an owned SDS buffer with at least `cap` usable bytes.

 ## Motivo
 A `PenguString` header with `is_owned == 1` is what lets the derived
 `Nexus` free the builder buffer. SDS owns the allocation and supplies the
 NUL slot; only C can attach that pointer to the header.

 ## Memoria
 Returns one owned SDS allocation; the caller stores it in
 `StringBuilder._data`. The buffer is NUL-terminated at index 0.

### `_builder_resize`

> **_builder_resize**(buf: ref to string, old_cap: int, new_cap: int) -> void

 Grows or shrinks the buffer to `new_cap` usable bytes, preserving contents.

 ## Motivo
 SDS owns the allocation: growth is `sdsMakeRoomFor` and shrinking is
 `sdsRemoveFreeSpace`, both of which update the SDS header that `banish`
 uses. Reattaching that pointer to a `PenguString` header needs C access.

 ## Memoria
 May reallocate `_data`; the old pointer is invalid afterwards. On OOM the
 old buffer is kept untouched.

### `_builder_copy`

> **_builder_copy**(dst: ref to string, off: int, src: ref to frozen u8, n: int) -> void

 Copies `n` bytes at `src` into `dst` starting at `off`, then NUL-terminates.

 ## Motivo
 The builder writes into a `PenguString`'s storage; PenguScript strings are
 immutable, so there is no pure write path.

 ## Memoria
 Writes only; allocates nothing. `src` is borrowed.

### `_builder_copy_slice`

> **_builder_copy_slice**(dst: ref to string, off: int, src: slice of u8) -> void

 Copies a `slice of byte` into `dst` at `off`, then NUL-terminates.

 ## Motivo
 A slice is a `PenguSlice` fat pointer; `memcpy` over `.data`/`.len` is the
 only way to append it without indexing byte by byte.

 ## Memoria
 Writes only; the slice is borrowed and never freed.

### `_builder_copy_repeat`

> **_builder_copy_repeat**(dst: ref to string, off: int, src: ref to frozen u8, n: int, times: int) -> void

 Copies `src[0..n]` `times` times into `dst` at `off`, then NUL-terminates.

 ## Motivo
 One C loop avoids `times` calls back into PenguScript and keeps the
 operation linear in the copied bytes.

 ## Memoria
 Writes only; allocates nothing.

### `_builder_insert`

> **_builder_insert**(dst: ref to string, pos: int, len: int, src: ref to frozen u8, n: int) -> void

 Inserts `n` bytes at `pos`, shifting the tail (including the NUL) right.

 ## Motivo
 `memmove` with overlap and a single NUL fix-up is exactly what an insert is;
 expressing it as a byte loop would be slower and no clearer.

 ## Memoria
 Writes in place; the buffer must already have room for `n` more bytes.

### `_builder_fill`

> **_builder_fill**(dst: ref to string, off: int, value: int, n: int) -> void

 Fills `n` bytes at `off` with `value`, then NUL-terminates.

 ## Motivo
 `memset` is the fastest way to append spaces or zeroes; a PenguScript loop
 would be O(n) interpreted byte writes.

 ## Memoria
 Writes only; allocates nothing.

### `_builder_format_i64`

> **_builder_format_i64**(dst: ref to string, off: int, value: i64) -> int

 Formats `value` as signed decimal into `dst` at `off` and returns the digits.

 ## Motivo
 `snprintf("%lld")` gives the exact same representation as `to string`
 without allocating a temporary `PenguString`.

 ## Memoria
 Writes into the builder buffer; allocates nothing.

### `_builder_format_f64`

> **_builder_format_f64**(dst: ref to string, off: int, value: f64) -> int

 Formats `value` with `%g` into `dst` at `off` and returns the bytes written.

 ## Motivo
 `%g` is the language-wide float rendering (`"{x}"`, `x to string` and
 `print x` all use it), so a builder must produce the same text.

 ## Memoria
 Writes into the builder buffer; allocates nothing.

### `_builder_store_char`

> **_builder_store_char**(dst: ref to string, off: int, c: char) -> void

 Writes one `char` at `off` without touching the next byte.

 ## Motivo
 A `char` is one byte; this keeps `append_char` and `set_char_at`
 allocation-free and avoids routing through `chr` (which would allocate a
 one-byte string). The caller is responsible for the NUL invariant, because
 `set_char_at` must not clobber the byte that follows it.

 ## Memoria
 Writes only; allocates nothing.

### `_builder_terminate`

> **_builder_terminate**(dst: ref to string, off: int) -> void

 Writes a NUL at `off` (the builder's terminator invariant).

 ## Motivo
 Keeping the terminator in one helper makes `append_char` and `truncate`
 impossible to get subtly wrong.

 ## Memoria
 Writes only; allocates nothing.

### `_builder_byte_at`

> **_builder_byte_at**(dst: string, i: int, len: int) -> u8

 Returns the byte at `i` from a builder buffer of `len` bytes.

 ## Motivo
 `byte_at` must not allocate; indexing a `string` yields a one-byte string,
 not a `byte`. The explicit `len` is the builder's `_len` (the `string`
 header intentionally keeps `len == 0`).

 ## Memoria
 Reads only; returns a value.

### `_builder_char_at`

> **_builder_char_at**(dst: string, i: int, len: int) -> char

 Returns the `char` at `i` from a builder buffer of `len` bytes.

 ## Motivo
 Same as `_builder_byte_at`, but the public `char_at` returns `char`.

 ## Memoria
 Reads only; returns a value.

### `_builder_reverse`

> **_builder_reverse**(dst: ref to string, len: int) -> void

 Reverses the first `len` bytes of `dst` in place.

 ## Motivo
 A two-pointer swap loop is the canonical O(n) reverse; C keeps it branch-free
 and avoids one PenguScript call per byte.

 ## Memoria
 Writes in place; allocates nothing. The NUL at `data[len]` is preserved.

### `_builder_take`

> **_builder_take**(buf: ref to string, len: int) -> string

 Transfers the builder buffer into a new owned `PenguString` and empties it.

 ## Motivo
 `finish` must hand over the exact allocation without copying. Only C can
 move the `data` pointer between two `PenguString` headers atomically.

 ## Memoria
 The returned string owns the buffer (`is_owned == 1`). The builder is left
 with `data == NULL`, so a later `banish builder` is a safe no-op.

### `_builder_copy_out`

> **_builder_copy_out**(buf: string, len: int) -> string

 Copies the first `len` bytes into a new owned `PenguString`.

 ## Motivo
 `to_string` and `substring` need a fresh buffer with an explicit length;
 `pengu_string_copy` would not let us bound the source to `len`.

 ## Memoria
 Allocates one owned buffer; the caller releases the result with `banish`.

### `_builder_copy_range`

> **_builder_copy_range**(buf: string, start: int, end: int) -> string

 Copies the byte range `[start, end)` into a new owned `PenguString`.

 ## Motivo
 `substring` needs a bounded copy; slicing a `PenguString` in PenguScript
 would allocate through a runtime path that assumes the whole string.

 ## Memoria
 Allocates one owned buffer; the caller releases the result with `banish`.

### `_builder_view`

> **_builder_view**(buf: string, len: int) -> slice of u8

 Returns a non-owning `slice of byte` view over the first `len` bytes.

 ## Motivo
 `bytes_view` is a borrow; the slice must point at the builder buffer without
 copying and without taking ownership.

 ## Memoria
 Does not allocate. The view is invalidated by any operation that grows,
 shrinks or releases the builder.

### `_builder_release`

> **_builder_release**(buf: ref to string) -> void

 Releases the builder buffer and clears its header.

 ## Motivo
 `reset` frees and resets; `pengu_banish_string` already does that safely,
 but exposing it through one helper keeps the field invariant in one place.

 ## Memoria
 Frees the owned buffer; the builder keeps a null, non-owning header.

### `new`

> **new**() -> StringBuilder

 Creates an empty builder with `BUILDER_DEFAULT_CAPACITY` bytes reserved.

 ## Memoria
 Allocates one buffer owned by the builder. Release the builder with
 `banish`.

 ## Ejemplo
 ```pengu
 var sb as StringBuilder is calling StringBuilder.new
 defer banish sb
 ```

### `with_capacity`

> **with_capacity**(cap: int) -> StringBuilder

 Creates an empty builder with at least `cap` bytes reserved.

 ## Parámetros
 - `cap`: usable bytes to reserve. `0` is valid and allocates only the NUL
   slot; the first `append` grows the buffer. A negative capacity panics.

 ## Memoria
 Allocates one buffer owned by the builder. Release with `banish`.

 ## Ejemplo
 ```pengu
 var sb as StringBuilder is calling StringBuilder.with_capacity with 1024
 defer banish sb
 ```

### `from_string`

> **from_string**(s: string) -> StringBuilder

 Creates a builder initialised with a copy of `s`.

 ## Memoria
 Allocates a buffer of exactly `s.length` bytes (plus the NUL slot). `s`
 is borrowed and may be released immediately after the call.

 ## Ejemplo
 ```pengu
 var sb as StringBuilder is calling StringBuilder.from_string with "abc"
 defer banish sb
 ```

### `append`

> **append**(s: string) -> void

 Appends a copy of `s` at the end of the builder.

 Appending the empty string is a no-op: it never reallocates and never
 changes `len`.

 ## Parámetros
 - `s`: the text to append. Borrowed; the builder copies its bytes.

 ## Retorno
 Nothing; the builder grows in place.

 ## Memoria
 May reallocate the internal buffer. `s` is never retained.

 ## Ejemplo
 ```pengu
 calling sb.append with "hola"
 ```

### `append_char`

> **append_char**(c: char) -> void

 Appends one byte as a character.

 ## Parámetros
 - `c`: the character to append.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer; does not allocate a temporary string.

 ## Ejemplo
 ```pengu
 calling sb.append_char with '!'
 ```

### `append_int`

> **append_int**(n: int) -> void

 Appends the decimal representation of `n` (same text as `n to string`).

 ## Parámetros
 - `n`: any `int`, including `INT_MIN` and `0`.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer. Unlike `append` of `n to string`, it
 does **not** allocate a temporary string.

 ## Ejemplo
 ```pengu
 calling sb.append_int with -42       # appends "-42"
 ```

### `append_i64`

> **append_i64**(n: i64) -> void

 Appends the decimal representation of the 64-bit integer `n`.

 ## Parámetros
 - `n`: any `i64`, including `INT64_MIN` and `0`.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer; allocates no temporary string.

 ## Ejemplo
 ```pengu
 calling sb.append_i64 with 9223372036854775807
 ```

### `append_float`

> **append_float**(f: float) -> void

 Appends a `float` using the language-wide `%g` format.

 `NaN` uses the platform `%g` spelling (`nan`, or `-nan` when the sign
 bit is set, as it is for `0.0 / 0.0` on glibc), positive infinity renders
 as `inf`, negative infinity as `-inf`, and `-0.0` as `-0` — exactly like
 `"{x}"` and `x to string`, because both go through the same `%g`.

 ## Parámetros
 - `f`: the value to format.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer; allocates no temporary string.

 ## Ejemplo
 ```pengu
 calling sb.append_float with 1.5      # appends "1.5"
 ```

### `append_f64`

> **append_f64**(f: f64) -> void

 Appends a `f64` using the language-wide `%g` format.

 ## Parámetros
 - `f`: the value to format.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer; allocates no temporary string.

 ## Ejemplo
 ```pengu
 calling sb.append_f64 with 3.141592653589793
 ```

### `append_bool`

> **append_bool**(b: bool) -> void

 Appends `"true"` or `"false"`.

 ## Parámetros
 - `b`: the boolean to render.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer; the literals are borrowed.

 ## Ejemplo
 ```pengu
 calling sb.append_bool with true       # appends "true"
 ```

### `append_bytes`

> **append_bytes**(b: slice of u8) -> void

 Appends every byte of a byte slice.

 ## Parámetros
 - `b`: a non-owning slice of bytes. It may be empty.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer. `b` is borrowed and never released.

 ## Ejemplo
 ```pengu
 calling sb.append_bytes with payload
 ```

### `append_slice`

> **append_slice**(b: ref to frozen u8, n: int) -> void

 Appends `n` bytes from a raw pointer.

 ## Parámetros
 - `b`: pointer to the first byte. May be `null` only when `n == 0`.
 - `n`: number of bytes to copy. Negative or zero is a no-op.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer. The source is borrowed.

 ## Ejemplo
 ```pengu
 calling sb.append_slice with raw, 4
 ```

### `append_repeat`

> **append_repeat**(s: string, times: int) -> void

 Appends `s` exactly `times` times.

 `times <= 0` or `s == ""` is a no-op, including `times > 0` with an empty
 `s`. The operation reserves the final size once, so it is linear in the
 bytes copied (never quadratic in `times`).

 ## Parámetros
 - `s`: the unit to repeat. Borrowed.
 - `times`: how many copies to append.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer once. Panics if the result would not
 fit in an `int` (more than `INT_MAX` bytes).

 ## Ejemplo
 ```pengu
 calling sb.append_repeat with "-", 10   # appends "----------"
 ```

### `append_spaces`

> **append_spaces**(n: int) -> void

 Appends `n` ASCII spaces.

 ## Parámetros
 - `n`: number of spaces. Negative or zero is a no-op.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer.

 ## Ejemplo
 ```pengu
 calling sb.append_spaces with 4          # appends "    "
 ```

### `insert_at`

> **insert_at**(pos: int, s: string) -> void

 Inserts a copy of `s` at byte position `pos`.

 `pos == len` appends; `pos < 0` or `pos > len` panics.

 ## Parámetros
 - `pos`: byte offset in `[0, len]`.
 - `s`: text to insert. Empty `s` is a no-op.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate the internal buffer; `s` is borrowed.

 ## Ejemplo
 ```pengu
 calling sb.insert_at with 0, ">> "
 ```

### `insert`

> **insert**(pos: int, s: string) -> void

 Alias of `insert_at`, for callers that spell the method `insert`.

 ## Parámetros
 - `pos`: byte offset in `[0, len]`.
 - `s`: text to insert. Empty `s` is a no-op.

 ## Retorno
 Nothing. Panics when `pos` is out of range.

 ## Memoria
 May reallocate the internal buffer; `s` is borrowed.

 ## Ejemplo
 ```pengu
 calling sb.insert with 0, ">> "
 ```

### `set_char_at`

> **set_char_at**(pos: int, c: char) -> void

 Overwrites the byte at `pos` with `c`.

 ## Parámetros
 - `pos`: byte offset in `[0, len)`.
 - `c`: the replacement byte.

 ## Retorno
 Nothing. Panics when `pos` is outside the current length.

 ## Memoria
 Writes in place; never reallocates.

 ## Ejemplo
 ```pengu
 calling sb.set_char_at with 0, 'H'
 ```

### `truncate`

> **truncate**(new_len: int) -> void

 Shortens the builder to `new_len` bytes.

 `new_len >= len` is a no-op (tolerance is deliberate: callers that clamp
 their own index should not need a second check). `new_len < 0` panics.

 ## Parámetros
 - `new_len`: the new length in bytes.

 ## Retorno
 Nothing.

 ## Memoria
 Never reallocates; capacity is preserved.

 ## Ejemplo
 ```pengu
 calling sb.truncate with 5
 ```

### `reverse`

> **reverse**() -> void

 Reverses the bytes of the builder in place.

 Byte-oriented, not grapheme-oriented: `"ñ"` (two UTF-8 bytes) reverses to
 two invalid bytes. That is the same contract as `mem.reverse` and it is
 what a lexer, a CSV writer or a byte-protocol encoder needs.

 ## Retorno
 Nothing.

 ## Memoria
 Writes in place; never reallocates.

 ## Ejemplo
 ```pengu
 calling sb.reverse       # "abc" -> "cba"
 ```

### `len`

> **len**() -> int

 Returns the number of bytes currently in the builder.

 ## Retorno
 A non-negative `int` in `[0, capacity]`.

 ## Memoria
 O(1), no allocation.

### `capacity`

> **capacity**() -> int

 Returns the number of bytes the buffer can hold without growing.

 `capacity >= len` always holds. A fresh builder has
 `BUILDER_DEFAULT_CAPACITY`; after `finish` or `reset` it is `0`.

 ## Retorno
 A non-negative `int`.

 ## Memoria
 O(1), no allocation.

### `is_empty`

> **is_empty**() -> bool

 True when the builder holds no bytes.

 ## Retorno
 `len == 0`.

 ## Memoria
 O(1), no allocation.

### `char_at`

> **char_at**(i: int) -> char

 Returns the byte at `i` as a `char`.

 ## Parámetros
 - `i`: byte offset in `[0, len)`.

 ## Retorno
 The byte as a `char`. Panics when `i` is out of range.

 ## Memoria
 O(1), no allocation.

### `byte_at`

> **byte_at**(i: int) -> u8

 Returns the byte at `i`.

 ## Parámetros
 - `i`: byte offset in `[0, len)`.

 ## Retorno
 The `byte`. Panics when `i` is out of range.

 ## Memoria
 O(1), no allocation.

### `bytes_view`

> **bytes_view**() -> slice of u8

 Returns a non-owning byte view over the current contents.

 ## Retorno
 A `slice of byte` that aliases the builder buffer. **Do not `banish` it**
 and do not keep it across a mutating call: `append`, `insert`,
 `shrink_to_fit`, `reset` and `finish` invalidate the view.

 ## Memoria
 O(1), no allocation, no ownership transfer.

 ## Ejemplo
 ```pengu
 vary view as slice of byte is calling sb.bytes_view
 ```

### `substring`

> **substring**(start: int, end: int) -> string

 Returns a new owned copy of the bytes in `[start, end)`.

 `start < 0` panics; `end > len` is clamped to `len`; `start > end`
 panics. `start == end` returns an owned empty string.

 ## Parámetros
 - `start`: inclusive byte offset.
 - `end`: exclusive byte offset.

 ## Retorno
 A new **owned** string; release it with `banish`.

 ## Memoria
 Allocates one buffer; the builder is untouched.

 ## Ejemplo
 ```pengu
 var head as string is calling sb.substring with 0, 5
 defer banish head
 ```

### `reserve`

> **reserve**(additional: int) -> void

 Ensures capacity for at least `additional` more bytes.

 Growth doubles the current capacity (or jumps to the exact need when
 that is larger), which gives amortised O(1) appends.

 ## Parámetros
 - `additional`: bytes to reserve beyond `len`. `<= 0` is a no-op.

 ## Retorno
 Nothing. `capacity` is at least `len + additional` afterwards.

 ## Memoria
 May reallocate the buffer; the old pointer is invalid.

 ## Ejemplo
 ```pengu
 calling sb.reserve with 1024
 ```

### `shrink_to_fit`

> **shrink_to_fit**() -> void

 Shrinks the buffer to exactly `len` bytes.

 After this call `capacity == len` (or both are `0` for an empty
 builder). Useful before handing a long-lived builder to `to_string`.

 ## Retorno
 Nothing.

 ## Memoria
 May reallocate (usually to a smaller block).

 ## Ejemplo
 ```pengu
 calling sb.shrink_to_fit
 ```

### `clear`

> **clear**() -> void

 Empties the builder but keeps its buffer and capacity.

 ## Retorno
 Nothing.

 ## Memoria
 Never reallocates and never releases; the buffer is reused.

 ## Ejemplo
 ```pengu
 calling sb.clear
 ```

### `reset`

> **reset**() -> void

 Empties the builder and releases its buffer.

 After `reset` the builder is usable again (`len == 0`, `cap == 0`); the
 next `append` allocates a fresh buffer.

 ## Retorno
 Nothing.

 ## Memoria
 Frees the internal buffer. `StringBuilder` itself is a stack value, so it
 does not need a second release; `banish builder` afterwards is a no-op.

 ## Ejemplo
 ```pengu
 calling sb.reset
 ```

### `finish`

> **finish**() -> string

 Transfers the internal buffer to a new owned string and empties the
 builder.

 This is the fast path: no bytes are copied. After `finish` the builder
 has `len == 0`, `cap == 0` and no buffer, so it is safe to `banish` it
 and safe to reuse it (the next append allocates).

 ## Retorno
 A new **owned** string (`is_owned == 1`). Release it with `banish`.

 ## Memoria
 Transfers ownership of the buffer. The caller now owns it.

 ## Ejemplo
 ```pengu
 var s as string is calling sb.finish
 defer banish s
 ```

### `to_string`

> **to_string**() -> string

 Returns a new owned copy of the contents, leaving the builder usable.

 Prefer this over `finish` when the builder has to keep accumulating. It
 costs one copy; `finish` costs none.

 ## Retorno
 A new **owned** string. Release it with `banish`.

 ## Memoria
 Allocates one buffer; the builder and its capacity are untouched.

 ## Ejemplo
 ```pengu
 var snapshot as string is calling sb.to_string
 defer banish snapshot
 ```

