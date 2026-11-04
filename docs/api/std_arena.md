# std.arena

> Source: `std/arena.pengu`

std/arena.pengu — a bump allocator for temporary object graphs.

An arena reserves large blocks and hands out slices of them with one pointer
addition per allocation. Individual allocations are never freed: `reset`
releases every block except the first (the fast path for a per-frame or
per-request graph) and `free` releases all of them.

## When to use an arena
Use an arena when **many** objects share **one** lifetime: the AST of one
parse, the nodes of one document, the scratch graph of one frame, the
descriptors of one request. Freeing them one by one is not just slow, it is
error-prone; the arena turns `n` releases into one.

For a single object, `std.memoria.alloc` plus `banish` is the right tool. Do
not use an arena to hide ownership: it allocates, it does not manage.

## What `reset` and `free` do **not** do
They release memory only. They do **not** run destructors and they do **not**
free `PenguString` buffers, lists or maps stored *inside* arena memory. If a
value owns heap memory of its own, release that value before `reset`/`free`
(or keep the arena's contents POD). This is the same contract as
`zig.heap.ArenaAllocator` and `bumpalo`: an arena is a region, not a GC.

## Example: build a tree, free it at once
```pengu
import std.arena
import std.spark

rune Node:
    value as int
    next as ref to Node

weave main into int:
    var a as Arena is calling Arena.new
    defer calling a.free
    var head as ref to Node is calling arena_alloc_one of Node with (sigil of a)
    set head->value is 1
    set head->next is calling arena_alloc_one of Node with (sigil of a)
    set head->next->value is 2
    calling spark.println with "{(head->value) + (head->next->value)}"
    return 0
```

## Implementation
Blocks are stored as owned `PenguString` headers (`_blocks`), so the
bookkeeping lists are freed by `derive Nexus` when the arena is banished and
each block is a single `free` under the hood. Block payloads are **not**
reachable from `Nexus`, because `PenguList` does not release its elements;
that is why `free` exists and why this module documents it explicitly. The
`antiquus` bridges below only allocate a block, expose its address and cast
pointers; the allocator logic itself is PenguScript.

## Complexity
| Operation | Cost |
|---|---|
| `alloc` / `alloc_aligned` | O(1) amortised (one new block occasionally) |
| `alloc_str` / `alloc_cstr` | O(length) copy + O(1) allocation |
| `reset` | O(number of blocks) frees, keeps the first block |
| `free` | O(number of blocks) frees |
| `total_allocated` / `block_count` / `block_size` | O(1) |

---

### `ARENA_VERSION`

> **ARENA_VERSION** : string

 Arena module version.

### `ARENA_DEFAULT_BLOCK_SIZE`

> **ARENA_DEFAULT_BLOCK_SIZE** : usize

 Block size used by `Arena.new` (4 KiB).

### `ARENA_DEFAULT_ALIGNMENT`

> **ARENA_DEFAULT_ALIGNMENT** : usize

 Default alignment used by `Arena.alloc`, in bytes.

 16 is the strictest alignment of `max_align_t` on the mainstream 64-bit
 targets (x86_64, ARM64) and is a safe superset on 32-bit ones. Use
 `alloc_aligned` when a type needs more (page alignment, SIMD).

### `Arena`

> rune Arena

```pengu
    _blocks as list of string
    _block_sizes as list of usize
    _current_block as int
    _current_offset as usize
    _block_size as usize
    _total_allocated as usize
```

 A bump allocator made of one or more blocks.

 All fields are private. The arena owns every block; the objects allocated
 **inside** a block are the caller's responsibility (the arena only owns the
 raw bytes).

 ## Memoria
 `_blocks` holds one owned `string` per block. `banish arena` releases the
 two bookkeeping lists, **not** the blocks: call `free` first, or use
 `defer calling a.free`. `free` is idempotent and leaves the arena reusable.

### `_arena_block_alloc`

> **_arena_block_alloc**(size: usize) -> string

 Allocates one zeroed block of `size` bytes and returns it as an owned string.

 ## Motivo
 A block must be owned by a `PenguString` header so it can be released with
 `pengu_banish_string` and so `free` can store it in a `list of string`
 without a raw-pointer list (which the current codegen cannot index).

 ## Memoria
 Returns one owned allocation of at least `size` bytes (1 for `size == 0`).

### `_arena_block_addr`

> **_arena_block_addr**(b: string) -> usize

 Returns the base address of a block.

 ## Motivo
 Alignment is computed on the *absolute* address, not on an offset, because
 `malloc` does not promise more than `max_align_t`.

 ## Memoria
 Reads only; returns an integer address.

### `_arena_block_at`

> **_arena_block_at**(b: string, off: usize) -> ref to u8

 Returns `b.data + off` as a writable byte pointer.

 ## Motivo
 The allocator needs to hand out a pointer into a block; PenguScript has no
 pointer arithmetic operator.

 ## Memoria
 Returns a borrowed pointer into the block. It is valid until `reset`/`free`.

### `_arena_as_cstr`

> **_arena_as_cstr**(p: ref to u8) -> ref to frozen char

 Casts a byte pointer to a read-only C string pointer.

 ## Motivo
 `alloc_cstr` must return `ref to frozen char`; the byte block is already
 NUL-terminated, so only the pointee type changes.

 ## Memoria
 Returns a borrowed view; no allocation and no ownership transfer.

### `_arena_align_up`

> **_arena_align_up**(value: usize, alignment: usize) -> usize

 Rounds `value` up to the next multiple of `alignment`.

 ## Motivo
 Used by the allocator for both offsets and absolute addresses. Kept private
 and pure so there is exactly one rounding rule.

 ## Memoria
 Computes only; allocates nothing.

### `new`

> **new**() -> Arena

 Creates an arena with `ARENA_DEFAULT_BLOCK_SIZE`-byte blocks.

 No block is allocated until the first `alloc`, so a fresh arena costs only
 the two empty lists.

 ## Memoria
 Allocates the two bookkeeping lists (empty). Release the arena with
 `free` and then `banish` (or `defer calling a.free`).

 ## Ejemplo
 ```pengu
 var a as Arena is calling Arena.new
 defer calling a.free
 ```

### `with_block_size`

> **with_block_size**(bs: usize) -> Arena

 Creates an arena whose normal blocks are `bs` bytes.

 ## Parámetros
 - `bs`: block size in bytes; must be greater than zero. A block is
   allocated only on demand, and a request larger than `bs` gets its own
   oversized block.

 ## Memoria
 Same as `new`; no block is allocated eagerly.

 ## Ejemplo
 ```pengu
 var a as Arena is calling Arena.with_block_size with 65536
 defer calling a.free
 ```

### `alloc`

> **alloc**(size: usize) -> ref to u8

 Allocates `size` bytes with `ARENA_DEFAULT_ALIGNMENT` alignment.

 `alloc(0)` returns a valid, aligned pointer and reserves no useful bytes
 (the standard bump-allocator contract), so it is safe to call in a loop.

 ## Parámetros
 - `size`: bytes to reserve.

 ## Retorno
 A pointer into the current block, valid until `reset`/`free`.

 ## Memoria
 May allocate a new block (via `pengu_memoria_alloc`, which follows the
 runtime OOM policy). The returned memory is zeroed and is **not**
 individually freeable.

 ## Ejemplo
 ```pengu
 var p as ref to byte is calling a.alloc with 128
 ```

### `alloc_aligned`

> **alloc_aligned**(size: usize, alignment: usize) -> ref to u8

 Allocates `size` bytes aligned to `alignment`.

 The pointer is aligned on the absolute address, even when the block itself
 was not allocated with that alignment: the allocator skips the padding
 bytes it needs.

 ## Parámetros
 - `size`: bytes to reserve.
 - `alignment`: a power of two greater than zero. `0` and non-powers of two
   panic.

 ## Retorno
 An aligned pointer valid until `reset`/`free`.

 ## Memoria
 May allocate a new block, including an oversized one when `size` or the
 alignment padding does not fit in the normal block.

 ## Ejemplo
 ```pengu
 var page as ref to byte is calling a.alloc_aligned with 4096, 4096
 ```

### `alloc_str`

> **alloc_str**(s: string) -> ref to u8

 Copies `s` into the arena and returns a pointer to the copy.

 `alloc_str("")` returns a valid pointer (zero bytes reserved). The copy is
 byte-exact: embedded NULs survive and no terminator is appended.

 ## Parámetros
 - `s`: the text to copy. Borrowed; the arena never retains it.

 ## Retorno
 A pointer to `s.length` bytes inside the arena.

 ## Memoria
 Allocates `s.length` bytes in the arena (not individually freeable).

 ## Ejemplo
 ```pengu
 var p as ref to byte is calling a.alloc_str with "hola"
 ```

### `alloc_cstr`

> **alloc_cstr**(s: string) -> ref to frozen char

 Copies `s` into the arena and returns a NUL-terminated C string.

 ## Parámetros
 - `s`: the text to copy. Embedded NULs are preserved; a final NUL is
   appended after `s.length` bytes.

 ## Retorno
 A `ref to frozen char` valid until `reset`/`free`.

 ## Memoria
 Allocates `s.length + 1` bytes in the arena.

 ## Ejemplo
 ```pengu
 var c as ref to frozen char is calling a.alloc_cstr with "hola"
 ```

### `total_allocated`

> **total_allocated**() -> usize

 Returns the number of **useful** bytes handed out since construction or
 the last `reset`.

 Block overhead, alignment padding and capacity are deliberately excluded:
 this is the number a caller can reason about, not the allocator's
 footprint.

 ## Retorno
 A `usize` in `[0, sum of block sizes]`.

 ## Memoria
 O(1), no allocation.

### `block_count`

> **block_count**() -> int

 Returns the number of blocks currently held by the arena.

 ## Retorno
 `0` before the first allocation, then one per block (including oversized
 ones).

 ## Memoria
 O(1), no allocation.

### `block_size`

> **block_size**() -> usize

 Returns the normal block size configured for this arena.

 Individual blocks can be larger (oversized allocations); use
 `block_count` and `total_allocated` for the live footprint.

 ## Retorno
 The block size passed to `with_block_size`, or the default.

 ## Memoria
 O(1), no allocation.

### `reset`

> **reset**() -> void

 Releases every block **except the first** and makes the arena reusable.

 This is the fast reset: the next `alloc` reuses the first block from
 offset `0`. The first block is kept because it is the one the arena would
 allocate again immediately, and because keeping it makes the first
 allocation after a reset free of syscalls.

 ## Retorno
 Nothing.

 ## Memoria
 Frees all but one block. Does **not** run destructors for objects stored
 in arena memory; release owned payloads first if they need it.

 ## Ejemplo
 ```pengu
 for frame in 0 to 60:
     calling a.reset
     var node as ref to Node is calling arena_alloc_one of Node with (sigil of a)
 ```

### `free`

> **free**() -> void

 Releases every block and empties the arena.

 After `free` the arena contains no blocks and `total_allocated == 0`. It
 is safe to reuse it (the lists keep their element size) and safe to call
 `free` again; this is intentionally friendlier than the "use after free
 is UB" contract of a raw `free`.

 ## Retorno
 Nothing.

 ## Memoria
 Frees every block and clears both bookkeeping lists. `banish arena`
 afterwards is safe and frees the list buffers only.

 ## Ejemplo
 ```pengu
 defer calling a.free
 ```

### `arena_alloc`

> **arena_alloc**(a: ref to Arena, n: int) -> ref to T

 Allocates `n` values of type `T` in `a` and returns them zeroed.

 The bytes come from the arena, so they are not individually freeable: release
 them with `a.reset` or `a.free`. `T` may be any fixed-size type; there is no
 per-element destructor call.

 ## Parámetros
 - `a`: the arena. Must outlive the returned pointer.
 - `n`: number of elements. `0` returns a valid pointer.

 ## Retorno
 `a` pointer to `n * sizeof(T)` bytes, aligned to `ARENA_DEFAULT_ALIGNMENT`.

 ## Memoria
 Bump-allocates inside `a`; nothing is registered for individual release.

 ## Ejemplo
 ```pengu
 var nodes as ref to Node is calling arena_alloc of Node with (sigil of a), 8
 ```

### `arena_alloc_one`

> **arena_alloc_one**(a: ref to Arena) -> ref to T

 Allocates one zeroed value of type `T` in `a`.

 Shorthand for `arena_alloc of T` with `n == 1`.

 ## Parámetros
 - `a`: the arena. Must outlive the returned pointer.

 ## Retorno
 A pointer to one zeroed `T`.

 ## Memoria
 Bump-allocates inside `a`; release it with `a.reset` or `a.free`.

 ## Ejemplo
 ```pengu
 var node as ref to Node is calling arena_alloc_one of Node with (sigil of a)
 ```

