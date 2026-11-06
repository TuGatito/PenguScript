# std.filum

> Source: `std/filum.pengu`

---

### `FILUM_VERSION`

> **FILUM_VERSION** : string

 Version constant for std.filum module.

### `Mutex`

> rune Mutex

```pengu
    _ptr as opaque
```

_Undocumented._

### `WaitGroup`

> rune WaitGroup

```pengu
    _ptr as opaque
```

_Undocumented._

### `Once`

> rune Once

```pengu
    _ptr as opaque
```

_Undocumented._

### `Cond`

> rune Cond

```pengu
    _ptr as opaque
```

_Undocumented._

### `AtomicInt`

> rune AtomicInt

```pengu
    _ptr as opaque
```

_Undocumented._

### `Chan`

> rune Chan

```pengu
    _ptr as opaque
    buffered as bool
    cap as int
```

_Undocumented._

### `ChanInt`

> rune ChanInt

```pengu
    _ptr as opaque
    buffered as bool
    cap as int
```

_Undocumented._

### `ChanString`

> rune ChanString

```pengu
    _ptr as opaque
    buffered as bool
    cap as int
```

_Undocumented._

### `ChanFloat`

> rune ChanFloat

```pengu
    _ptr as opaque
    buffered as bool
    cap as int
```

_Undocumented._

### `ChanBool`

> rune ChanBool

```pengu
    _ptr as opaque
    buffered as bool
    cap as int
```

_Undocumented._

### `Thread`

> rune Thread

```pengu
    _id as i64
    _err as int
```

_Undocumented._

### `ThreadError`

> rune ThreadError

```pengu
    code as int
    sys_code as int
```

 Error returned by thread operations.

### `SpawnBox`

> rune SpawnBox

```pengu
    fn as ref to weave with a: A into void
    arg as A
```

 Box used by `start` to carry the worker and its argument to the new thread.

### `pengu_c_filum_go`

> **pengu_c_filum_go**(f: opaque) -> void

 Runtime: launches f on a new goroutine and returns immediately.

### `pengu_c_filum_box_new`

> **pengu_c_filum_box_new**(size: int) -> ref to void

 First-class threads (0.30.0).

### `pengu_c_filum_box_free`

> **pengu_c_filum_box_free**(p: ref to void) -> void

_Undocumented._

### `pengu_c_filum_thread_start`

> **pengu_c_filum_thread_start**(run: ref to weave with ctx: ref to void into void, box: ref to void, err: ref to int) -> i64

_Undocumented._

### `pengu_c_filum_thread_is_finished`

> **pengu_c_filum_thread_is_finished**(id: i64) -> int

_Undocumented._

### `pengu_c_filum_thread_join`

> **pengu_c_filum_thread_join**(id: i64, sys: ref to int) -> int

_Undocumented._

### `pengu_c_filum_thread_detach`

> **pengu_c_filum_thread_detach**(id: i64, sys: ref to int) -> int

_Undocumented._

### `pengu_c_filum_thread_abandon`

> **pengu_c_filum_thread_abandon**(id: i64) -> void

_Undocumented._

### `pengu_c_filum_thread_exists`

> **pengu_c_filum_thread_exists**(id: i64) -> bool

_Undocumented._

### `pengu_c_filum_thread_id`

> **pengu_c_filum_thread_id**(id: i64) -> i64

_Undocumented._

### `pengu_c_filum_thread_name`

> **pengu_c_filum_thread_name**(id: i64) -> string

_Undocumented._

### `pengu_c_filum_thread_set_name`

> **pengu_c_filum_thread_set_name**(id: i64, name: string) -> int

_Undocumented._

### `pengu_c_filum_tls_new`

> **pengu_c_filum_tls_new**() -> opaque

_Undocumented._

### `pengu_c_filum_tls_free`

> **pengu_c_filum_tls_free**(t: opaque) -> void

_Undocumented._

### `pengu_c_filum_tls_set`

> **pengu_c_filum_tls_set**(t: opaque, value: ref to void) -> void

_Undocumented._

### `pengu_c_filum_tls_get`

> **pengu_c_filum_tls_get**(t: opaque) -> ref to void

_Undocumented._

### `pengu_c_filum_pool_new`

> **pengu_c_filum_pool_new**(workers: int) -> opaque

_Undocumented._

### `pengu_c_filum_pool_submit`

> **pengu_c_filum_pool_submit**(p: opaque, fn: ref to weave with ctx: ref to void into void, ctx: ref to void) -> void

_Undocumented._

### `pengu_c_filum_pool_wait`

> **pengu_c_filum_pool_wait**(p: opaque) -> void

_Undocumented._

### `pengu_c_filum_pool_free`

> **pengu_c_filum_pool_free**(p: opaque) -> void

_Undocumented._

### `pengu_c_filum_parallel_for`

> **pengu_c_filum_parallel_for**(n: int, body: ref to weave with ctx: ref to void, i: int into void, ctx: ref to void, workers: int) -> void

_Undocumented._

### `pengu_c_filum_chan_new`

> **pengu_c_filum_chan_new**(elem_size: usize, cap: int) -> opaque

 Runtime: creates a channel for elements of size elem_size with capacity cap
 (0 = unbuffered). Memory: the caller owns the returned handle and must
 release it with pengu_c_filum_chan_free.

### `pengu_c_filum_chan_send`

> **pengu_c_filum_chan_send**(c: opaque, value: opaque) -> bool

 Runtime: sends a value into channel c; true when accepted, false when c is
 closed.

### `pengu_c_filum_chan_recv`

> **pengu_c_filum_chan_recv**(c: opaque, out: opaque) -> bool

 Runtime: receives a value from channel c into out; true when a value was
 received, false when c is closed and drained.

### `pengu_c_filum_chan_close`

> **pengu_c_filum_chan_close**(c: opaque) -> void

 Runtime: closes channel c; queued values remain receivable.

### `pengu_c_filum_chan_len`

> **pengu_c_filum_chan_len**(c: opaque) -> int

 Runtime: number of values currently buffered in channel c.

### `pengu_c_filum_chan_cap`

> **pengu_c_filum_chan_cap**(c: opaque) -> int

 Runtime: capacity of channel c (0 when unbuffered).

### `pengu_c_filum_mutex_new`

> **pengu_c_filum_mutex_new**() -> opaque

 Runtime: allocates a native mutex. Memory: the caller owns the returned
 handle and must release it with pengu_c_filum_mutex_free.

### `pengu_c_filum_mutex_lock`

> **pengu_c_filum_mutex_lock**(m: opaque) -> void

 Runtime: locks the mutex, blocking until it is available.

### `pengu_c_filum_mutex_unlock`

> **pengu_c_filum_mutex_unlock**(m: opaque) -> void

 Runtime: unlocks the mutex; the caller must currently hold the lock.

### `pengu_c_filum_mutex_try_lock`

> **pengu_c_filum_mutex_try_lock**(m: opaque) -> bool

 Runtime: attempts a non-blocking lock on the mutex; true when acquired.

### `pengu_c_filum_wait_group_new`

> **pengu_c_filum_wait_group_new**() -> opaque

 Runtime: allocates a wait group. Memory: the caller owns the returned
 handle and must release it with pengu_c_filum_wait_group_free.

### `pengu_c_filum_wait_group_add`

> **pengu_c_filum_wait_group_add**(wg: opaque, delta: int) -> void

 Runtime: adds delta to the wait-group counter.

### `pengu_c_filum_wait_group_done`

> **pengu_c_filum_wait_group_done**(wg: opaque) -> void

 Runtime: decrements the wait-group counter by one.

### `pengu_c_filum_wait_group_wait`

> **pengu_c_filum_wait_group_wait**(wg: opaque) -> void

 Runtime: blocks until the wait-group counter reaches zero.

### `pengu_c_filum_once_new`

> **pengu_c_filum_once_new**() -> opaque

 Runtime: allocates a once-guard. Memory: the caller owns the returned
 handle and must release it with pengu_c_filum_once_free.

### `pengu_c_filum_once_do`

> **pengu_c_filum_once_do**(o: opaque, f: opaque) -> void

 Runtime: runs callback f exactly once across all callers of the same guard.

### `pengu_c_filum_cond_new`

> **pengu_c_filum_cond_new**() -> opaque

 Runtime: allocates a condition variable. Memory: the caller owns the
 returned handle and must release it with pengu_c_filum_cond_free.

### `pengu_c_filum_cond_wait`

> **pengu_c_filum_cond_wait**(c: opaque, m: opaque) -> void

 Runtime: atomically releases mutex m and blocks until c is signaled;
 reacquires m before returning.

### `pengu_c_filum_cond_signal`

> **pengu_c_filum_cond_signal**(c: opaque) -> void

 Runtime: wakes one goroutine waiting on c.

### `pengu_c_filum_cond_broadcast`

> **pengu_c_filum_cond_broadcast**(c: opaque) -> void

 Runtime: wakes every goroutine waiting on c.

### `pengu_c_filum_atomic_int_new`

> **pengu_c_filum_atomic_int_new**(initial: int) -> opaque

 Runtime: allocates an atomic integer initialized to initial. Memory: the
 caller owns the returned handle and must release it with
 pengu_c_filum_atomic_int_free.

### `pengu_c_filum_atomic_int_load`

> **pengu_c_filum_atomic_int_load**(a: opaque) -> int

 Runtime: returns the current value of atomic integer a.

### `pengu_c_filum_atomic_int_store`

> **pengu_c_filum_atomic_int_store**(a: opaque, val: int) -> void

 Runtime: sets atomic integer a to val.

### `pengu_c_filum_atomic_int_add`

> **pengu_c_filum_atomic_int_add**(a: opaque, delta: int) -> int

 Runtime: atomically adds delta to a and returns the previous value.

### `pengu_c_filum_atomic_int_swap`

> **pengu_c_filum_atomic_int_swap**(a: opaque, new_val: int) -> int

 Runtime: atomically replaces the value of a with new_val and returns the
 previous value.

### `pengu_c_filum_atomic_int_compare_swap`

> **pengu_c_filum_atomic_int_compare_swap**(a: opaque, old_val: int, new_val: int) -> bool

 Runtime: sets a to new_val only when it currently equals old_val; true when
 the swap happened.

### `pengu_c_filum_sleep`

> **pengu_c_filum_sleep**(ms: int) -> void

 Runtime: suspends the calling goroutine for ms milliseconds.

### `pengu_c_filum_num_cpu`

> **pengu_c_filum_num_cpu**() -> int

 Runtime: number of logical CPUs available to the process.

### `pengu_c_filum_goroutine_id`

> **pengu_c_filum_goroutine_id**() -> int

 Runtime: identifier of the calling goroutine.

### `pengu_c_filum_mutex_free`

> **pengu_c_filum_mutex_free**(m: opaque) -> void

 Runtime: releases a mutex handle. Call exactly once; do not use the Mutex afterwards.

### `pengu_c_filum_wait_group_free`

> **pengu_c_filum_wait_group_free**(wg: opaque) -> void

 Runtime: releases a wait-group handle. Call exactly once; do not use the WaitGroup afterwards.

### `pengu_c_filum_once_free`

> **pengu_c_filum_once_free**(o: opaque) -> void

 Runtime: releases a once-guard handle. Call exactly once; do not use the Once afterwards.

### `pengu_c_filum_cond_free`

> **pengu_c_filum_cond_free**(c: opaque) -> void

 Runtime: releases a condition-variable handle. Call exactly once; do not use the Cond afterwards.

### `pengu_c_filum_atomic_int_free`

> **pengu_c_filum_atomic_int_free**(a: opaque) -> void

 Runtime: releases an atomic-integer handle. Call exactly once; do not use the AtomicInt afterwards.

### `pengu_c_filum_chan_free`

> **pengu_c_filum_chan_free**(c: opaque) -> void

 Runtime: releases a channel handle. Call exactly once; do not use the Chan afterwards.

### `pengu_string_copy`

> **pengu_string_copy**(s: string) -> string

 Runtime: creates an owned deep copy of s with its own heap buffer.

### `mutex`

> **mutex**() -> Mutex

 Allocates a new native mutex and returns the owning Mutex rune.
 Memory: Caller owns the returned Mutex; release it with free_mutex or m.free.

### `lock`

> **lock**(m: ref to Mutex) -> void

 Locks the mutex, blocking until it is available.
 Memory: Takes ref to Mutex.

### `unlock`

> **unlock**(m: ref to Mutex) -> void

 Unlocks the mutex; the caller must currently hold the lock.
 Memory: Takes ref to Mutex.

### `try_lock`

> **try_lock**(m: ref to Mutex) -> bool

 Attempts a non-blocking lock on the mutex; returns true when acquired.
 Memory: Takes ref to Mutex.

### `free`

> **free**() -> void

 Releases the native handle owned by this rune; do not use the value afterwards.

### `wait_group`

> **wait_group**() -> WaitGroup

 Allocates a new native wait group and returns the owning WaitGroup rune.
 Memory: Caller owns returned WaitGroup; release it with free_wait_group or wg.free.

### `add`

> **add**(wg: ref to WaitGroup, delta: int) -> void

 Adds delta to the wait-group counter; call before starting tracked work.

### `done`

> **done**(wg: ref to WaitGroup) -> void

 Decrements the wait-group counter by one; call when a tracked unit finishes.

### `wait`

> **wait**(wg: ref to WaitGroup) -> void

 Blocks until the wait-group counter reaches zero.

### `once`

> **once**() -> Once

 Allocates a new native once-guard and returns the owning Once rune.
 Memory: Caller owns returned Once; release it with free_once or o.free.

### `do_once`

> **do_once**(o: ref to Once, f: opaque) -> void

 Runs callback f exactly once across every goroutine sharing this Once.

### `do_action`

> **do_action**(f: opaque) -> void

 Runs callback f exactly once across every goroutine sharing this guard.

### `cond`

> **cond**() -> Cond

 Allocates a new native condition variable and returns the owning Cond rune.
 Memory: Caller owns returned Cond; release it with free_cond or c.free.

### `cond_wait`

> **cond_wait**(c: ref to Cond, m: ref to Mutex) -> void

 Atomically releases mutex m and blocks until the condition variable is signaled;
 reacquires m before returning.

### `signal`

> **signal**(c: ref to Cond) -> void

 Wakes one goroutine currently waiting on this condition variable.

### `broadcast`

> **broadcast**(c: ref to Cond) -> void

 Wakes every goroutine currently waiting on this condition variable.

### `wait_mutex`

> **wait_mutex**(m: ref to Mutex) -> void

 Atomically releases m and waits for a signal; reacquires m before returning.

### `atomic_int`

> **atomic_int**(initial: int) -> AtomicInt

 Allocates a native atomic integer with the given initial value (default 0)
 and returns the owning AtomicInt rune. Memory: free it with free_atomic_int or a.free.

### `load`

> **load**(a: ref to AtomicInt) -> int

 Returns the current value of the atomic integer (atomic read).

### `store`

> **store**(a: ref to AtomicInt, val: int) -> void

 Sets the atomic integer to val (atomic write).

### `add_atomic`

> **add_atomic**(a: ref to AtomicInt, delta: int) -> int

 Atomically adds delta to the atomic integer and returns its previous value.

### `sub_atomic`

> **sub_atomic**(a: ref to AtomicInt, delta: int) -> int

 Atomically subtracts delta from the atomic integer and returns its new value.
 NOTE: Named 'sub_atomic' (and 'add_atomic', 'reset_atomic') at the module level
 to avoid naming conflicts with arithmetic operations or other module reset functions.

### `swap`

> **swap**(a: ref to AtomicInt, new_val: int) -> int

 Atomically replaces the value with new_val and returns the previous value.

### `compare_swap`

> **compare_swap**(a: ref to AtomicInt, old_val: int, new_val: int) -> bool

 Sets the value to new_val only when it currently equals old_val; true when replaced.

### `inc`

> **inc**(a: ref to AtomicInt) -> int

 Atomically increments the atomic integer by one and returns the new value.

### `dec`

> **dec**(a: ref to AtomicInt) -> int

 Atomically decrements the atomic integer by one and returns the new value.

### `inc_and_get`

> **inc_and_get**(a: ref to AtomicInt) -> int

 Atomically increments the atomic integer by one and returns the new value. Alias of inc.

### `dec_and_get`

> **dec_and_get**(a: ref to AtomicInt) -> int

 Atomically decrements the atomic integer by one and returns the new value. Alias of dec.

### `get_and_set`

> **get_and_set**(a: ref to AtomicInt, new_val: int) -> int

 Atomically replaces the value with new_val and returns the previous value. Alias of swap.

### `is_zero`

> **is_zero**(a: ref to AtomicInt) -> bool

 Checks if the atomic integer currently equals zero.

### `reset_atomic`

> **reset_atomic**(a: ref to AtomicInt) -> void

 Resets the atomic integer value back to zero.
 NOTE: Named 'reset_atomic' at module level to avoid collision with other reset operations.

### `sub`

> **sub**(delta: int) -> int

 Atomically subtracts delta and returns the new value.

### `reset`

> **reset**() -> void

 Resets the atomic value to zero.

### `chan_int`

> **chan_int**(cap: int) -> ChanInt

 Allocates an unbuffered or buffered channel for `int` values.
 Memory: Caller owns returned ChanInt; release with free_chan_int or c.free.

### `free_chan_int`

> **free_chan_int**(c: ref to ChanInt) -> void

 Releases the native handle of a ChanInt; do not use the rune afterwards.

### `new`

> **new**() -> ChanInt

 Creates an unbuffered channel of `int` values.

### `with_capacity`

> **with_capacity**(cap: int) -> ChanInt

 Creates a buffered channel of `int` values with capacity `cap`.

### `send`

> **send**(v: int) -> bool

 Sends `v` into the channel. Blocks if buffered channel is full or unbuffered receiver is not ready.
 Returns true when sent, or false when the channel is closed.

### `recv`

> **recv**() -> maybe int

 Receives an `int` from the channel. Blocks until a value is available or channel is closed.
 Returns `some val` when received, or `maybe none` when closed and drained.

### `close`

> **close**() -> void

 Closes the channel. Buffered values remain receivable.

### `len`

> **len**() -> int

 Returns the number of elements currently buffered in the channel.

### `cap`

> **cap**() -> int

 Returns the channel's capacity (0 for unbuffered).

### `chan_string`

> **chan_string**(cap: int) -> ChanString

 Allocates an unbuffered or buffered channel for `string` values.
 Memory: Caller owns returned ChanString; release with free_chan_string or c.free.

### `free_chan_string`

> **free_chan_string**(c: ref to ChanString) -> void

 Releases the native handle of a ChanString; do not use the rune afterwards.

### `chan_float`

> **chan_float**(cap: int) -> ChanFloat

 Allocates an unbuffered or buffered channel for `float` values.
 Memory: Caller owns returned ChanFloat; release with free_chan_float or c.free.

### `free_chan_float`

> **free_chan_float**(c: ref to ChanFloat) -> void

 Releases the native handle of a ChanFloat; do not use the rune afterwards.

### `chan_bool`

> **chan_bool**(cap: int) -> ChanBool

 Allocates an unbuffered or buffered channel for `bool` values.
 Memory: Caller owns returned ChanBool; release with free_chan_bool or c.free.

### `free_chan_bool`

> **free_chan_bool**(c: ref to ChanBool) -> void

 Releases the native handle of a ChanBool; do not use the rune afterwards.

### `free_mutex`

> **free_mutex**(m: ref to Mutex) -> void

 Releases the native handle of a Mutex; do not use the rune afterwards.

### `free_wait_group`

> **free_wait_group**(wg: ref to WaitGroup) -> void

 Releases the native handle of a WaitGroup; do not use the rune afterwards.

### `free_once`

> **free_once**(o: ref to Once) -> void

 Releases the native handle of a Once; do not use the rune afterwards.

### `free_cond`

> **free_cond**(c: ref to Cond) -> void

 Releases the native handle of a Cond; do not use the rune afterwards.

### `free_atomic_int`

> **free_atomic_int**(a: ref to AtomicInt) -> void

 Releases the native handle of an AtomicInt; do not use the rune afterwards.

### `free_chan`

> **free_chan**(c: ref to Chan) -> void

 Releases the native handle of a Chan; do not use the rune afterwards.

### `run_box`

> **run_box**(raw: ref to void) -> void

 Runs `worker` on a new thread, passing `arg`. Ownership of an owning `arg`
 moves to the worker; the caller must not use it afterwards.

### `start`

> **start**(worker: ref to weave with a: A into void, arg: A) -> Thread

_Undocumented._

### `is_valid`

> **is_valid**(t: ref to Thread) -> bool

 True while the handle still refers to a thread the runtime knows about.

### `is_finished`

> **is_finished**(t: ref to Thread) -> bool

 Whether the thread has finished. Does not consume the handle; safe to poll
 from a reactor task with `reactor.await_thread`.

### `SpawnBox0`

> rune SpawnBox0

```pengu
    fn as ref to weave with  into void
```

 Caja para un worker sin argumentos.

### `SpawnBox2`

> rune SpawnBox2

```pengu
    fn as ref to weave with a: A, b: B into void
    a0 as A
    a1 as B
```

 Caja para un worker de dos argumentos.

### `SpawnBox3`

> rune SpawnBox3

```pengu
    fn as ref to weave with a: A, b: B, c: C into void
    a0 as A
    a1 as B
    a2 as C
```

 Caja para un worker de tres argumentos.

### `run_box0`

> **run_box0**(raw: ref to void) -> void

_Undocumented._

### `start0`

> **start0**(worker: ref to weave with  into void) -> Thread

_Undocumented._

### `run_box2`

> **run_box2**(raw: ref to void) -> void

_Undocumented._

### `start2`

> **start2**(worker: ref to weave with a: A, b: B into void, a: A, b: B) -> Thread

_Undocumented._

### `run_box3`

> **run_box3**(raw: ref to void) -> void

_Undocumented._

### `start3`

> **start3**(worker: ref to weave with a: A, b: B, c: C into void, a: A, b: B, c: C) -> Thread

_Undocumented._

### `Tls`

> rune Tls

```pengu
    _ptr as opaque
```

_Undocumented._

### `Pool`

> rune Pool

```pengu
    _ptr as opaque
```

_Undocumented._

### `tls`

> **tls**() -> Tls

 Crea una clave TLS.

### `tls_set`

> **tls_set**(t: ref to Tls, v: ref to T) -> void

 Asocia `v` al hilo actual bajo `t`.

### `tls_get`

> **tls_get**(t: ref to Tls) -> maybe ref to T

 Lee el valor TLS del hilo actual.

### `tls_free`

> **tls_free**(t: ref to Tls) -> void

 Libera la clave TLS (no los valores).

### `pool`

> **pool**(workers: int) -> Pool

 Crea un pool con `workers` hilos (0 = tantos como CPUs).

### `submit`

> **submit**(fn: ref to weave with ctx: ref to void into void, ctx: ref to void) -> void

 Encola `fn(ctx)`.

### `parallel_for`

> **parallel_for**(n: int, workers: int, body: ref to weave with ctx: ref to void, i: int into void, ctx: ref to void) -> void

 Ejecuta `body(ctx, i)` para i en [0, n) sobre un pool temporal.

### `join`

> **join**() -> result of void to ThreadError

_Undocumented._

### `detach`

> **detach**() -> result of void to ThreadError

 Releases the handle without waiting; the thread keeps running.

### `name`

> **name**() -> string

 Diagnostic name, empty when the handle is no longer valid.

### `set_name`

> **set_name**(name: string) -> result of void to ThreadError

 Sets the diagnostic name (at most 63 bytes).

### `id`

> **id**() -> i64

 OS thread id, or 0 when unavailable.

### `explain`

> **explain**(e: ref to ThreadError) -> string

 Human-readable explanation for a thread error.

### `sleep`

> **sleep**(ms: int) -> void

 Suspends the calling goroutine for ms milliseconds.

### `sleep_sec`

> **sleep_sec**(sec: float) -> void

 Suspends the calling goroutine/thread for sec seconds (millisecond resolution).

 Signature: sleep_sec(sec as float) into void
 Memory: No allocations.
 Edge cases: If `sec <= 0.0`, returns immediately without sleeping.

### `num_cpu`

> **num_cpu**() -> int

 Number of logical CPUs available to the process.

### `goroutine_id`

> **goroutine_id**() -> int

 Identifier of the calling goroutine.

