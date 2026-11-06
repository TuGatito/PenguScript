# std.coro

> Source: `std/coro.pengu`

---

### `CoroutineState`

> omen CoroutineState

```pengu
    suspended
    running
    finished
```

 State of a coroutine after `resume` or `status`.

### `Coroutine`

> rune Coroutine

```pengu
    _ptr as opaque
```

 Handle to a coroutine. The runtime owns the slot; do not copy it.

### `CoroBox`

> rune CoroBox

```pengu
    fn as ref to weave with a: A into void
    arg as A
```

 Box used by `start` to carry the worker and its argument.

### `CoroBox0`

> rune CoroBox0

```pengu
    fn as ref to weave with  into void
```

 Box used by `start0` for a worker with no arguments.

### `pengu_c_coro_box_new`

> **pengu_c_coro_box_new**(size: int) -> ref to void

 ----------------------------------------------------------------------------
 External C Declarations
 ----------------------------------------------------------------------------

### `pengu_c_coro_box_free`

> **pengu_c_coro_box_free**(box: ref to void) -> void

_Undocumented._

### `pengu_c_coro_new`

> **pengu_c_coro_new**(run: ref to weave with raw: ref to void into void, box: ref to void) -> ref to void

_Undocumented._

### `pengu_c_coro_resume`

> **pengu_c_coro_resume**(handle: ref to void) -> int

_Undocumented._

### `pengu_c_coro_yield`

> **pengu_c_coro_yield**() -> void

_Undocumented._

### `pengu_c_coro_status`

> **pengu_c_coro_status**(handle: ref to void) -> int

_Undocumented._

### `pengu_c_coro_free`

> **pengu_c_coro_free**(handle: ref to void) -> void

_Undocumented._

### `pengu_c_coro_abandon`

> **pengu_c_coro_abandon**(handle: ref to void) -> void

_Undocumented._

### `pengu_c_coro_current`

> **pengu_c_coro_current**() -> ref to void

_Undocumented._

### `run_box`

> **run_box**(raw: ref to void) -> void

 ----------------------------------------------------------------------------
 Helpers
 ----------------------------------------------------------------------------

### `run_box0`

> **run_box0**(raw: ref to void) -> void

_Undocumented._

### `start`

> **start**(worker: ref to weave with a: A into void, arg: A) -> Coroutine

_Undocumented._

### `start0`

> **start0**(worker: ref to weave with  into void) -> Coroutine

_Undocumented._

### `from_raw`

> **from_raw**(raw: ref to void) -> Coroutine

 Wraps a raw handle produced by `pengu_c_coro_new`. Internal to the runtime
 ecosystem: `std.reactor` starts its trampoline without the generic box.

### `current`

> **current**() -> Coroutine

 The coroutine running on this thread. Panics outside a coroutine.

### `is_running`

> **is_running**() -> bool

 Whether this thread is currently inside a coroutine. No panic.

### `yield`

> **yield**() -> void

 Suspends the current coroutine until its owner calls `resume`. Calling
 `yield` outside a coroutine is a runtime panic.

### `resume`

> **resume**() -> CoroutineState

 Resumes the coroutine until its next yield or until it returns.

### `status`

> **status**() -> CoroutineState

 Reads the current state without running the coroutine.

### `free`

> **free**() -> void

 Releases a finished coroutine. Panics if it is still suspended.

### `abandon`

> **abandon**() -> void

 Discards a suspended or finished coroutine. Any owned argument in the
 box is not released; the worker was responsible for it.

