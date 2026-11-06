# std.reactor

> Source: `std/reactor.pengu`

---

### `REACTOR_VERSION`

> **REACTOR_VERSION** : string

 Revision of the `std.reactor` API.

### `TASK_READY`

> **TASK_READY** : int

 Task states. `ready` is a task that may be resumed in this pass; `fd` waits
 for readiness; `timer` sleeps; `offload` waits for a pool completion.

### `TASK_FD`

> **TASK_FD** : int

_Undocumented._

### `TASK_TIMER`

> **TASK_TIMER** : int

_Undocumented._

### `TASK_OFFLOAD`

> **TASK_OFFLOAD** : int

_Undocumented._

### `TASK_NEW`

> **TASK_NEW** : int

_Undocumented._

### `Task`

> rune Task

```pengu
    co as Coroutine
    token as i64
    state as int
    waiting as i64
    fd as int
    events as int
    pending as int
    done as bool
    job_box as ref to void
    job_token as i64
    job_free as ref to weave with box: ref to void into void
    arg_box as ref to void
```

 One coroutine spawned on a loop.

### `Timer`

> rune Timer

```pengu
    token as i64
    task as i64
    deadline_ms as int
```

 A pending `sleep_ms`.

### `SpawnJob`

> rune SpawnJob

```pengu
    worker as ref to weave with loop: ref to EventLoop, a: ref to void into void
    loop as ref to EventLoop
    arg as ref to void
```

 Argument bundle passed to the coroutine trampoline. The typed worker is
 erased to `ref to void`: the loop boxes a copy of the argument and the
 worker receives a `ref to A` to that copy. This keeps the trampoline
 non-generic, so a spawn never asks the compiler to instantiate a generic
 nominal inside another generic body.

### `EventLoop`

> rune EventLoop

```pengu
    _handle as opaque
    tasks as list of Task
    timers as list of Timer
    next_token as i64
    stopped as bool
    running as bool
    closed as bool
```

 A reactor with its own epoll/poll set and worker pool.

### `pengu_c_reactor_new`

> **pengu_c_reactor_new**(workers: int) -> ref to void

 ----------------------------------------------------------------------------
 C declarations
 ----------------------------------------------------------------------------

### `pengu_c_reactor_is_owner`

> **pengu_c_reactor_is_owner**(r: ref to void) -> int

_Undocumented._

### `pengu_c_reactor_free`

> **pengu_c_reactor_free**(r: ref to void) -> void

_Undocumented._

### `pengu_c_reactor_add`

> **pengu_c_reactor_add**(r: ref to void, fd: int, events: int, token: i64) -> int

_Undocumented._

### `pengu_c_reactor_del`

> **pengu_c_reactor_del**(r: ref to void, fd: int) -> int

_Undocumented._

### `pengu_c_reactor_wait`

> **pengu_c_reactor_wait**(r: ref to void, timeout_ms: int, tokens: ref to i64, cap: int) -> int

_Undocumented._

### `pengu_c_reactor_post`

> **pengu_c_reactor_post**(r: ref to void, task_id: i64, token: i64) -> int

_Undocumented._

### `pengu_c_reactor_take`

> **pengu_c_reactor_take**(r: ref to void, task_id: ref to i64, token: ref to i64) -> int

_Undocumented._

### `pengu_c_reactor_now_ms`

> **pengu_c_reactor_now_ms**() -> int

_Undocumented._

### `pengu_c_reactor_offload`

> **pengu_c_reactor_offload**(r: ref to void, fn: ref to weave with ctx: ref to void into void, ctx: ref to void, task_id: i64, token: i64) -> int

_Undocumented._

### `pengu_c_reactor_wake`

> **pengu_c_reactor_wake**(r: ref to void) -> void

_Undocumented._

### `pengu_c_box_copy`

> **pengu_c_box_copy**(src: ref to void, size: i64) -> ref to void

_Undocumented._

### `pengu_c_coro_box_new`

> **pengu_c_coro_box_new**(size: i64) -> ref to void

_Undocumented._

### `pengu_c_coro_box_free`

> **pengu_c_coro_box_free**(box: ref to void) -> void

_Undocumented._

### `pengu_c_coro_new`

> **pengu_c_coro_new**(run: ref to weave with raw: ref to void into void, box: ref to void) -> ref to void

_Undocumented._

### `_kick`

> **_kick**(raw: ref to void) -> void

_Undocumented._

### `new`

> **new**(workers: int) -> EventLoop

 Creates a loop. `workers` is the size of the offload pool (0 = CPU count).
 The loop belongs to the thread that creates it.

### `stop`

> **stop**() -> void

 Stops the loop after the current resume. Cooperative: call it from a task.

### `is_stopped`

> **is_stopped**() -> bool

 Whether `stop` was requested.

### `close`

> **close**() -> void

 Destroys the loop. Must run outside a coroutine and on the owner thread.
 Suspended tasks are abandoned, pending offload boxes are released and the
 worker pool is joined. Idempotent. User file descriptors are not closed.

### `pending`

> **pending**() -> int

 Number of pool completions already harvested but not consumed.

### `_find_task`

> **_find_task**(token: i64) -> int

 ----------------------------------------------------------------------------
 Task table
 ----------------------------------------------------------------------------

### `_find_task_by_co`

> **_find_task_by_co**(co: Coroutine) -> int

_Undocumented._

### `_remove_task`

> **_remove_task**(index: int) -> void

_Undocumented._

### `_remove_timer`

> **_remove_timer**(index: int) -> void

_Undocumented._

### `spawn`

> **spawn**(worker: ref to weave with loop: ref to EventLoop, a: ref to A into void, arg: A) -> i64

 Spawns `worker` as a coroutine on this loop. The worker receives the loop
 first, then `arg`. Returns the task id. The task starts in the next pass
 of `run`, never inline.
 Spawns `worker` as a coroutine on this loop. The worker receives the loop
 and a `ref to A` to a loop-owned copy of `arg`; the copy lives while the
 worker runs. Returns the task id.

### `park_read`

> **park_read**(fd: int) -> int

 Parks the current coroutine until `fd` is readable. Returns 0 on success or
 `-errno` if the registration failed.

### `park_write`

> **park_write**(fd: int) -> int

 Parks the current coroutine until `fd` is writable.

### `_park`

> **_park**(fd: int, events: int) -> int

_Undocumented._

### `sleep_ms`

> **sleep_ms**(ms: int) -> void

 Suspends the current task for at least `ms` milliseconds.

### `await_token`

> **await_token**(token: i64) -> void

 Waits for the completion of the offload whose token is `token`.

### `offload`

> **offload**(fn: ref to weave with ctx: ref to void into void, job_free: ref to weave with box: ref to void into void, ctx: ref to void) -> i64

 Sends `fn(ctx)` to the loop's pool. Returns the completion token to pass to
 `await_token`. One offload can be in flight per task. `job_free` releases
 `ctx` after the completion is consumed.

### `await_thread`

> **await_thread**(t: ref to Thread) -> void

 Waits for a `std.filum.Thread` without blocking the loop.

### `run`

> **run**() -> int

 Runs until no tasks and no timers remain, or until `stop`. Returns the
 number of live tasks at exit.

