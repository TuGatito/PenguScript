# std.consortium

> Source: `std/consortium.pengu`

std.consortium — shared ownership by reference count.

`Rc of T` keeps a value on the heap with a counter. Copying the handle is
free (one increment); the value is destroyed when the last owner goes away,
and the block is released when the last `Weak` stops looking.

## When to use it
Use `Rc` when **several** parts of a program must observe the same value and
you cannot tell which one dies last: a document shared by two views, a node
referenced by a parent and by a cache, an asset handed to several scenes.
Use `Arc` when the owners live on different threads (`filum.start`).
Use `WeakRc`/`WeakArc` to break a cycle: a child points at its parent
without keeping it alive.

## When not to use it
Do not use `Rc` for a value with a single owner: `derive Drop` (layer 1) is
faster and makes the ownership visible in the type. Do not use `Rc` to
silence a borrow error that `banish` would model exactly. Do not put a
`Rc` inside a hot inner loop as a poor man's allocator: the counter is
shared cache traffic.

## The cost is in the type
`Rc` copies implicitly because the copy is one non-atomic increment.
`Arc` is move-only: a copy is an atomic operation and must be spelled
`.clone()`. `make_mut` is explicit because it may clone the payload.

## Example: a shared tree node
```pengu
import std.consortium
import std.spark

rune Node:
    value as int

weave main into int:
    var root as Rc of Node is calling Rc.new with Node { value is 7 }
    var alias as Rc of Node is root          # one increment
    calling spark.println with "{(calling alias.get)->value}"
    return 0
```

## Implementation
Every handle is one pointer to the payload. The counter lives in a header
immediately before it:
`{ strong, weak, magic, drop, clone, size }`. `pengu_rc_release` runs the
destructor when `strong` reaches zero and frees the block when `weak` does.
`tools/build_runtime.sh` recompiles the runtime after changing the header.

---

### `Rc`

> rune Rc

```pengu
    ptr as ref to void
```

 Single-threaded reference-counted handle. Copying is implicit and cheap.

### `WeakRc`

> rune WeakRc

```pengu
    ptr as ref to void
```

 Non-owning handle for `Rc`. Copying is implicit; it never keeps `T` alive.

### `Arc`

> rune Arc

```pengu
    ptr as ref to void
```

 Multi-threaded reference-counted handle. Move-only: copy with `.clone()`.

### `WeakArc`

> rune WeakArc

```pengu
    ptr as ref to void
```

 Non-owning handle for `Arc`.

### `consortium_rc_strong`

> **consortium_rc_strong**(p: ref to frozen void) -> int

_Undocumented._

### `consortium_rc_weak`

> **consortium_rc_weak**(p: ref to frozen void) -> int

_Undocumented._

### `consortium_rc_upgrade`

> **consortium_rc_upgrade**(p: ref to frozen void) -> ref to void

_Undocumented._

### `consortium_rc_alive`

> **consortium_rc_alive**(p: ref to frozen void) -> bool

_Undocumented._

### `consortium_arc_strong`

> **consortium_arc_strong**(p: ref to frozen void) -> int

_Undocumented._

### `consortium_arc_weak`

> **consortium_arc_weak**(p: ref to frozen void) -> int

_Undocumented._

### `consortium_arc_upgrade`

> **consortium_arc_upgrade**(p: ref to frozen void) -> ref to void

_Undocumented._

### `consortium_arc_alive`

> **consortium_arc_alive**(p: ref to frozen void) -> bool

_Undocumented._

### `consortium_rc_retain`

> **consortium_rc_retain**(p: ref to void) -> ref to void

_Undocumented._

### `consortium_rc_weak_new`

> **consortium_rc_weak_new**(p: ref to void) -> ref to void

_Undocumented._

### `consortium_rc_make_mut`

> **consortium_rc_make_mut**(p: ref to void) -> ref to void

_Undocumented._

### `consortium_arc_retain`

> **consortium_arc_retain**(p: ref to void) -> ref to void

_Undocumented._

### `consortium_arc_weak_new`

> **consortium_arc_weak_new**(p: ref to void) -> ref to void

_Undocumented._

### `consortium_arc_make_mut`

> **consortium_arc_make_mut**(p: ref to void) -> ref to void

_Undocumented._

### `new`

> **new**(value: T) -> Rc__T

 Allocates `value` inside a new reference count (strong = 1).

 The compiler lowers this call to `pengu_rc_new` with the destructor and
 the deep copy of `T`, so the body below is only a type-check placeholder.

### `get`

> **get**() -> ref to frozen T

 The value, without handing out ownership.

### `get_mut`

> **get_mut**() -> maybe ref to T

 The value for writing, only when this is the only owner.

### `make_mut`

> **make_mut**() -> ref to T

 The value for writing, cloning the payload first if it is shared.

### `strong_count`

> **strong_count**() -> int

 Number of strong owners (including this one).

### `weak_count`

> **weak_count**() -> int

 Number of weak observers.

### `downgrade`

> **downgrade**() -> WeakRc__T

 A non-owning handle to the same value.

### `clone`

> **clone**() -> Rc__T

 One more strong owner.

### `upgrade`

> **upgrade**() -> maybe Rc__T

 The value as a new strong owner, or `none` if it already died.

### `is_alive`

> **is_alive**() -> bool

 Whether the value is still alive.

