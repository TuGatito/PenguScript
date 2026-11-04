# std.bitset

> Source: `std/bitset.pengu`

std/bitset.pengu — a fixed-length dense bit set.

A `BitSet` stores `bit_len` bits in `ceil(bit_len / 8)` bytes and offers
constant-time single-bit access, word-at-a-time bulk operations and the set
algebra (`and`, `or`, `xor`, `and_not`, `not`) that a dense integer set needs.
It is the right tool for membership over a bounded universe: visited flags in
a graph, seen-bytes tables, occupancy maps, sieve composites, Bloom filters.

For a **sparse** set (a handful of values out of a huge universe) use
`map of int to int`: allocating `bit_len / 8` bytes would be wasteful.

## Invariants
- `bit_len` is fixed at construction; every operation respects it.
- Bits `bit_len .. byte_len * 8 - 1` (the padding of the last byte) are
  **always zero**. Constructors, `not`, `not_in_place` and every binary
  operation re-apply the mask, so `count_ones` never counts padding.
- `_data` is owned by the bitset and released by `banish` (`derive Nexus`).

## Example: Sieve of Eratosthenes
```pengu
import std.bitset
import std.spark

weave main into int:
    var n as int is 50
    var composite as BitSet is calling BitSet.new with (n + 1)
    defer banish composite
    var p as int is 2
    while p * p <= n:
        if not (calling composite.get with p):
            var m as int is p * p
            while m <= n:
                calling composite.set with m
                set m is m + p
        set p is p + 1
    var i as int is 2
    while i <= n:
        if not (calling composite.get with i):
            calling spark.println with "{i}"
        set i is i + 1
    return 0
```

## Complexity
| Operation | Cost |
|---|---|
| `get`, `set`, `clear`, `toggle`, `set_to` | O(1) |
| `count_ones`, `count_zeros`, `equals`, `copy`, `and/or/xor/and_not`, `not` | O(bit_len / 8) |
| `set_all`, `clear_all`, `toggle_all` | O(bit_len / 8) |
| `find_first_*`, `find_next_*` | O(bit_len) worst case, O(1) in the common case |
| `iter_set` | O(bit_len) plus the result list |
| `to_bytes` | O(1), non-owning |

---

### `BITSET_VERSION`

> **BITSET_VERSION** : string

 BitSet module version.

### `BitSet`

> rune BitSet

```pengu
    _data as string
    _bit_len as int
    _byte_len as int
```

 A dense bit vector of fixed length `bit_len`.

 Fields are private: use the methods, which enforce the bounds and the
 padding-zero invariant.

 ## Memoria
 `_data` is an owned byte buffer of `_byte_len` bytes. `banish bitset`
 releases it through `derive Nexus`.

### `_bitset_alloc`

> **_bitset_alloc**(n: int) -> string

 Allocates a zeroed byte buffer of `n` bytes and returns it as an owned string.

 ## Motivo
 The bitset buffer must be owned by a `PenguString` header so `derive Nexus`
 frees it with `banish`. A zero-length buffer still owns one byte, which keeps
 `banish` and `to_bytes` valid for an empty bitset.

 ## Memoria
 Returns one owned allocation (at least one byte); the caller releases it with
 `banish` (the bitset does it through `Nexus`).

### `_bitset_ptr`

> **_bitset_ptr**(data: ref to string) -> ref to u8

 Returns a writable byte pointer to the bitset storage.

 ## Motivo
 `PenguString` bytes are immutable in PenguScript; the bit operations need a
 writable view of the same allocation.

 ## Memoria
 Borrows the buffer; no allocation and no ownership transfer.

### `_bitset_slice`

> **_bitset_slice**(data: string, n: int) -> slice of u8

 Returns a non-owning `slice of byte` view of `n` bytes.

 ## Motivo
 `to_bytes` must expose the storage as a slice without copying and without
 handing over the buffer.

 ## Memoria
 No allocation; the slice aliases the bitset buffer and is invalidated by
 `banish`.

### `_bitset_copy_from`

> **_bitset_copy_from**(data: ref to string, src: slice of u8, n: int) -> void

 Copies `n` bytes from `src` into the bitset storage.

 ## Motivo
 `from_bytes` must copy a `PenguSlice` whose element type is `byte`; the
 `memcpy` is the whole operation.

 ## Memoria
 Writes only; the source slice is borrowed.

### `new`

> **new**(bit_len: int) -> BitSet

 Creates a bitset of `bit_len` bits, all zero.

 `bit_len == 0` is valid: `byte_len == 0`, `count_ones == 0` and every
 indexed operation panics (there is no valid index).

 ## Parámetros
 - `bit_len`: number of bits; must be `>= 0`.

 ## Retorno
 A `BitSet` with `_byte_len == ceil(bit_len / 8)`.

 ## Memoria
 Allocates one buffer owned by the bitset. Release the bitset with
 `banish`. Panics on a negative length.

 ## Ejemplo
 ```pengu
 var bs as BitSet is calling BitSet.new with 64
 defer banish bs
 ```

### `filled`

> **filled**(bit_len: int) -> BitSet

 Creates a bitset of `bit_len` bits with every useful bit set to one.

 The padding bits of the last byte stay zero, so `count_ones == bit_len`.

 ## Parámetros
 - `bit_len`: number of bits; must be `>= 0`.

 ## Retorno
 A `BitSet` full of ones.

 ## Memoria
 Allocates one buffer owned by the bitset; release with `banish`.

 ## Ejemplo
 ```pengu
 var bs as BitSet is calling BitSet.filled with 9
 # count_ones == 9, the last byte's padding is 0
 ```

### `from_bytes`

> **from_bytes**(data: slice of u8, bit_len: int) -> BitSet

 Creates a bitset from `data`, copying `ceil(bit_len / 8)` bytes.

 `data` must contain at least `ceil(bit_len / 8)` bytes; extra trailing
 bytes are ignored. Padding bits in the last copied byte are masked to
 zero, so the padding-zero invariant holds even for a caller-supplied
 buffer with garbage in the unused high bits.

 ## Parámetros
 - `data`: a non-owning byte slice; borrowed.
 - `bit_len`: number of useful bits; must be `>= 0`.

 ## Retorno
 A new `BitSet` that owns its own copy.

 ## Memoria
 Allocates one buffer owned by the bitset; release with `banish`. `data`
 is borrowed and never freed. Panics when the slice is too short.

 ## Ejemplo
 ```pengu
 var raw as array of byte with size 2 is [255, 1]
 var view as slice of byte is raw at 0 to 2
 var bs as BitSet is calling BitSet.from_bytes with view, 9
 defer banish bs
 ```

### `set`

> **set**(i: int) -> void

 Sets bit `i` to one.

 ## Parámetros
 - `i`: bit index in `[0, bit_len)`.

 ## Retorno
 Nothing. Panics when `i` is out of range.

 ## Memoria
 Writes in place; O(1), no allocation.

 ## Ejemplo
 ```pengu
 calling bs.set with 3
 ```

### `clear`

> **clear**(i: int) -> void

 Clears bit `i` to zero.

 ## Parámetros
 - `i`: bit index in `[0, bit_len)`.

 ## Retorno
 Nothing. Panics when `i` is out of range.

 ## Memoria
 Writes in place; O(1), no allocation.

### `toggle`

> **toggle**(i: int) -> void

 Flips bit `i`.

 ## Parámetros
 - `i`: bit index in `[0, bit_len)`.

 ## Retorno
 Nothing. Panics when `i` is out of range.

 ## Memoria
 Writes in place; O(1), no allocation.

### `set_to`

> **set_to**(i: int, v: bool) -> void

 Sets bit `i` to `v` (`true` = one, `false` = zero).

 ## Parámetros
 - `i`: bit index in `[0, bit_len)`.
 - `v`: the value to write.

 ## Retorno
 Nothing. Panics when `i` is out of range.

 ## Memoria
 Writes in place; O(1), no allocation.

### `get`

> **get**(i: int) -> bool

 Returns bit `i`.

 ## Parámetros
 - `i`: bit index in `[0, bit_len)`.

 ## Retorno
 `true` when the bit is one.

 ## Memoria
 O(1), no allocation. Panics when `i` is out of range.

 ## Ejemplo
 ```pengu
 if calling bs.get with 3:
     calling spark.println with "set"
 ```

### `set_all`

> **set_all**() -> void

 Sets every useful bit to one; padding stays zero.

 ## Memoria
 O(byte_len), no allocation.

### `clear_all`

> **clear_all**() -> void

 Clears every bit.

 ## Memoria
 O(byte_len), no allocation.

### `toggle_all`

> **toggle_all**() -> void

 Flips every useful bit; padding stays zero.

 ## Memoria
 O(byte_len), no allocation.

### `bit_len`

> **bit_len**() -> int

 Returns the fixed number of bits.

 ## Memoria
 O(1), no allocation.

### `count_ones`

> **count_ones**() -> int

 Returns the number of one bits.

 ## Memoria
 O(byte_len), no allocation. Uses branch-free SWAR popcount per byte, so
 it is also O(1) in space and never touches the padding bits (they are
 already zero by invariant).

### `count_zeros`

> **count_zeros**() -> int

 Returns the number of zero bits (`bit_len - count_ones`).

 ## Memoria
 O(byte_len), no allocation.

### `is_empty`

> **is_empty**() -> bool

 True when no bit is set.

 ## Memoria
 O(byte_len), no allocation.

### `is_full`

> **is_full**() -> bool

 True when every useful bit is set (`count_ones == bit_len`).

 For `bit_len == 0` this is `true` (vacuously full).

 ## Memoria
 O(byte_len), no allocation.

### `any`

> **any**() -> bool

 True when at least one bit is set. Alias of `not is_empty`.

 ## Memoria
 O(byte_len), no allocation.

### `all`

> **all**() -> bool

 True when every useful bit is set. Alias of `is_full`.

 ## Memoria
 O(byte_len), no allocation.

### `and_with`

> **and_with**(other: ref to BitSet) -> BitSet

 Returns `self AND other` as a new bitset.

 ## Parámetros
 - `other`: a bitset of exactly the same `bit_len`. Mismatched lengths
   panic.

 ## Memoria
 Allocates one new bitset; release it with `banish`.

### `or_with`

> **or_with**(other: ref to BitSet) -> BitSet

 Returns `self OR other` as a new bitset.

 ## Parámetros
 - `other`: a bitset of exactly the same `bit_len`.

 ## Memoria
 Allocates one new bitset; release it with `banish`.

### `xor_with`

> **xor_with**(other: ref to BitSet) -> BitSet

 Returns `self XOR other` as a new bitset.

 ## Parámetros
 - `other`: a bitset of exactly the same `bit_len`.

 ## Memoria
 Allocates one new bitset; release it with `banish`.

### `and_not_with`

> **and_not_with**(other: ref to BitSet) -> BitSet

 Returns `self AND NOT other` as a new bitset.

 ## Parámetros
 - `other`: a bitset of exactly the same `bit_len`.

 ## Memoria
 Allocates one new bitset; release it with `banish`.

### `not`

> **not**() -> BitSet

 Returns the complement of `self` as a new bitset.

 Only the useful bits are inverted; the padding of the last byte is zero in
 the result, so `count_ones` is exact.

 ## Memoria
 Allocates one new bitset; release it with `banish`.

### `and_in_place`

> **and_in_place**(other: ref to BitSet) -> void

 `self = self AND other`, in place.

 ## Parámetros
 - `other`: a bitset of exactly the same `bit_len`.

 ## Memoria
 Writes in place; no allocation.

### `or_in_place`

> **or_in_place**(other: ref to BitSet) -> void

 `self = self OR other`, in place.

 ## Parámetros
 - `other`: a bitset of exactly the same `bit_len`.

 ## Memoria
 Writes in place; no allocation.

### `xor_in_place`

> **xor_in_place**(other: ref to BitSet) -> void

 `self = self XOR other`, in place.

 ## Parámetros
 - `other`: a bitset of exactly the same `bit_len`.

 ## Memoria
 Writes in place; no allocation.

### `and_not_in_place`

> **and_not_in_place**(other: ref to BitSet) -> void

 `self = self AND NOT other`, in place.

 ## Parámetros
 - `other`: a bitset of exactly the same `bit_len`.

 ## Memoria
 Writes in place; no allocation.

### `not_in_place`

> **not_in_place**() -> void

 Inverts every useful bit in place; padding stays zero.

 ## Memoria
 Writes in place; no allocation.

### `find_first_set`

> **find_first_set**() -> maybe int

 Returns the index of the first one bit, or `none`.

 ## Retorno
 `some i` with the smallest set index, or `none` when empty.

 ## Memoria
 O(bit_len) worst case, no allocation.

 ## Ejemplo
 ```pengu
 var first as maybe int is calling bs.find_first_set
 ```

### `find_first_clear`

> **find_first_clear**() -> maybe int

 Returns the index of the first zero bit, or `none` when full.

 Padding bits are never considered: a bitset with `bit_len == 9` and all
 nine useful bits set returns `none`, not index 9.

 ## Memoria
 O(bit_len) worst case, no allocation.

### `find_next_set`

> **find_next_set**(from: int) -> maybe int

 Returns the first set bit with index `>= from`, or `none`.

 ## Parámetros
 - `from`: starting index. `from >= bit_len` returns `none`; negative
   values panic.

 ## Memoria
 O(bit_len) worst case, no allocation.

### `find_next_clear`

> **find_next_clear**(from: int) -> maybe int

 Returns the first clear bit with index `>= from`, or `none`.

 ## Parámetros
 - `from`: starting index. `from >= bit_len` returns `none`; negative
   values panic.

 ## Memoria
 O(bit_len) worst case, no allocation.

### `equals`

> **equals**(other: ref to BitSet) -> bool

 Compares two bitsets byte for byte.

 Bitsets of different `bit_len` are never equal (this does **not** panic;
 it is a value comparison, unlike the binary operators).

 ## Memoria
 O(byte_len), no allocation.

### `copy`

> **copy**() -> BitSet

 Returns an independent copy.

 ## Memoria
 Allocates one new bitset; release it with `banish`.

### `iter_set`

> **iter_set**() -> list of int

 Returns a new `list of int` with every set index in ascending order.

 ## Memoria
 Allocates the list (and its buffer); release it with `banish`.

 ## Ejemplo
 ```pengu
 var set_bits as list of int is calling bs.iter_set
 defer banish set_bits
 ```

### `to_bytes`

> **to_bytes**() -> slice of u8

 Returns a non-owning byte view of the internal buffer.

 The view has `byte_len` bytes. **Do not `banish` it**, and do not keep it
 after `banish bitset` or any in-place operation: it aliases the bitset
 storage.

 ## Memoria
 O(1), no allocation, no ownership transfer.

### `_check_index`

> **_check_index**(i: int) -> void

 Panics when `i` is outside `[0, bit_len)`.

 ## Motivo
 One bounds check shared by every single-bit method keeps the diagnostic
 identical everywhere.

 ## Memoria
 O(1), no allocation.

### `_check_same_len`

> **_check_same_len**(other: ref to BitSet) -> void

 Panics when `other` has a different `bit_len`.

 ## Motivo
 Set algebra between differently sized universes is a caller bug, not a
 value result (use `equals` for the non-panicking comparison).

 ## Memoria
 O(1), no allocation.

### `_write_bit`

> **_write_bit**(i: int, v: bool) -> void

 Writes one bit without the bounds check.

 ## Motivo
 `set`, `clear` and `set_to` share the read-modify-write sequence.

 ## Memoria
 Writes in place; O(1), no allocation.

### `_mask_padding`

> **_mask_padding**() -> void

 Zeroes the padding bits of the last byte.

 ## Motivo
 `count_ones`, `equals` and `to_bytes` rely on the padding-zero invariant;
 every constructor and bulk operation funnels through this helper.

 ## Memoria
 Writes one byte at most; O(1), no allocation.

