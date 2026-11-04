# std.web

> Source: `std/web.pengu`

std.web — the browser/Emscripten bridge shared by every web module.

Thin, typed wrappers over the parts of the Emscripten runtime that every
WebAssembly build has, with no extra `emcc` flags:

- `console_log`, `console_warn`, `console_error`, `console_trace`
- `set_main_loop`, `cancel_main_loop`, `pause_main_loop`, `resume_main_loop`
- `now_ms` (high-resolution monotonic milliseconds)
- `set_timeout`, `clear_timeout`
- `eval_js` (escape hatch; needs `unsafe-eval` in a CSP)
- `IS_WASM`

Scope rule:

- always available with a plain `emcc` build -> here
- needs `-sASYNCIFY`, `-sFETCH=1`, `-lwebsocket.js`, `-sUSE_SDL=2`,
  `-lidbfs.js`, ... -> a satellite binding such as `std.web.js`

`emscripten_sleep` is deliberately absent (it needs `-sASYNCIFY`);
`set_timeout`/`clear_timeout` cover "run something later" without flags.

Native builds: importing this module is always valid. Console functions write
to stderr, `now_ms` reads the monotonic clock, and Web-only entry points
(`set_main_loop`, `eval_js`, timers) call `spark.panic` with a clear message.
Guard on `IS_WASM` when one source must serve both targets.

## Example

```pengu
weave frame into void:
    calling web.console_log with "frame"

weave main into int:
    calling web.set_main_loop with frame, 0, true
    return 0
```

See `docs/WASM.md` for the build flags and the full module map.

---

### `WEB_VERSION`

> **WEB_VERSION** : string

 Version of this module (independent semver, per LANGUAGE.md §19.0).

### `IS_WASM`

> **IS_WASM** : bool

 False: this binary is a native build, not WebAssembly.

### `console_log`

> **console_log**(msg: string) -> void

 Writes `msg` to stderr.

### `console_warn`

> **console_warn**(msg: string) -> void

 Writes `msg` to stderr.

### `console_error`

> **console_error**(msg: string) -> void

 Writes `msg` to stderr.

### `console_trace`

> **console_trace**(msg: string) -> void

 Writes `msg` to stderr (no stack trace natively).

### `native_monotonic_ms`

> **native_monotonic_ms**() -> f64

 Monotonic clock in milliseconds.

### `now_ms`

> **now_ms**() -> f64

 Milliseconds from the monotonic clock.

### `eval_js`

> **eval_js**(code: string) -> void

 Fails: there is no JavaScript engine.

### `set_main_loop`

> **set_main_loop**(cb: ref to weave with  into void, fps: int, simulate_infinite_loop: bool) -> void

 Fails: a native binary has no browser main loop.

### `cancel_main_loop`

> **cancel_main_loop**() -> void

 Fails: a native binary has no browser main loop.

### `pause_main_loop`

> **pause_main_loop**() -> void

 Fails: a native binary has no browser main loop.

### `resume_main_loop`

> **resume_main_loop**() -> void

 Fails: a native binary has no browser main loop.

### `set_timeout`

> **set_timeout**(cb: weave with arg: ref to void into void, ms: f64, arg: ref to void) -> int

 Fails: there is no JS event loop to schedule into.

### `clear_timeout`

> **clear_timeout**(timeout_id: int) -> void

 Fails for the same reason as `set_timeout`.

