# WebAssembly with PenguScript (`--target wasm32-unknown-emscripten`)

> **Status:** implemented and exercised by CI (the `WebAssembly (Emscripten)` job in
> [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)). Supplementary, not normative: when
> this text and the source disagree, [`pengu_project.py`](../pengu_project.py) wins.
>
> **Scope of this release:** `wasm32-unknown-emscripten` only. **WASI is not supported** — a
> `wasm32-wasi` target is recognized so it can be refused with a clear message instead of silently
> building for the host.

PenguScript does not generate machine code: `pengu build` emits one C translation unit and invokes
a C compiler. WebAssembly support therefore means *using Emscripten as that compiler* and teaching
the CLI the target's naming, linking, runtime-archive and execution rules. Read
[`docs/CROSS_COMPILATION.md`](CROSS_COMPILATION.md) first for the general model — this document
covers only what differs.

---

## 1. Install the Emscripten SDK

Emscripten is not vendored. Install it once, in userspace:

```bash
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh          # fish: source ./emsdk_env.fish
```

`source ./emsdk_env.sh` must be run in **every shell** that builds for wasm — it is what puts
`emcc` and `emar` on `PATH`. Verify with:

```bash
emcc --version
pengu doctor
```

If `emcc` is missing, `pengu build --target wasm32-unknown-emscripten` stops with these same
instructions rather than failing later inside a linker.

---

## 2. Build the runtime for wasm

The shipped `libpengu_runtime.a` is host-built, and a wasm object and a host object are not
interchangeable. Build the wasm one **once**:

```bash
python build_runtime.py --target emscripten
# -> build/wasm/lib/libpengu_runtime.a
# -> build/wasm/include/pengu_runtime.h
```

A few things worth knowing:

* This does **not** replace or touch `build/lib/`: the host and wasm archives coexist, so one
  checkout can build for both targets. `--target native` is still the default.
* `--target wasi` exits with status 2 and a message saying so.
* `emar` is required, not just `emcc`: `ar` cannot write an archive of wasm members.
* The wasm archive is compiled with `-pthread` unconditionally. That is what makes Emscripten emit
  the atomics/shared-memory target features, and members that disagree on them cannot be linked
  together.

The CLI looks for the wasm archive in this order (see `_wasm_runtime_lib_dirs`):

1. `$PENGU_LIB_DIR`, when set — an **override**, not one more search path;
2. `$PENGU_RUNTIME_CROSS/lib` and `$PENGU_RUNTIME_CROSS`;
3. `build/wasm/lib` next to the source checkout, or next to the installed
   `pengu` executable (`<exe>/build/wasm/lib`, `<exe>/runtime/wasm/lib`);
4. the same paths under the PyInstaller extraction root.

The host `build/lib` is deliberately **not** in that list.

### 2.1.1 Native libraries from a project or binding

The same host/wasm separation applies to the libraries a project links:

| Target | Project archive | Binding archive |
|---|---|---|
| native | `lib/libfoo.a` | `lib/<binding>/lib/libfoo.a` |
| wasm | `lib/wasm/libfoo.a` | `lib/<binding>/lib/wasm/libfoo.a` |

An `emscripten` build searches only the `wasm` directories, so a host
`libraylib.a` cannot be picked by mistake; a native build searches only the
host directories. A binding that needs a raw option the linker cannot express
as an archive declares it next to `link`:

```pengu
when wasm:
    link "raylib"
    ldflag "-sUSE_GLFW=3"
```

`ldflag` is documented in [`LANGUAGE.md` §14.2](../LANGUAGE.md#142-include-link-ldflag-insignia-declare).

---

## 3. Build and run

```bash
# Executable: app.html + app.js + app.wasm
pengu build --target wasm32-unknown-emscripten

# Alias, identical meaning
pengu build --target wasm

# Build and execute. Node runs the generated app.js and its exit status is
# forwarded; without Node the path to the .html page is printed instead.
pengu run --target wasm32-unknown-emscripten

# Standalone script (no project needed)
pengu run --target wasm my_script.pengu

# Integrated unit tests, same runner (exit status is the test result)
pengu test --target wasm32-unknown-emscripten
```

A static archive of wasm objects is selected through the manifest (`output = "static"`), not a flag:
the output kind has always come from `pengu.toml` / `pengu.yaml`.

`--target` is also a manifest key, so it can live in `pengu.toml` / `pengu.yaml`:

```toml
[build]
target = "wasm32-unknown-emscripten"
```

`--target wasm32-unknown-emscripten` also changes the compile-time environment: `when os == ...`
sees `emscripten`, not the build host's OS.

### Artifacts

| `output` | Artifact | Notes |
|---|---|---|
| `exe` (default) | `app.html` + `app.js` + `app.wasm` | Open the `.html` in a browser, or `node app.js` |
| `static` | `app.a` | Real wasm objects, archived with `emar`; link it into another wasm bundle |
| `obj` | `app.o` | A single wasm object |
| `c` | `bundle.c` | Unchanged — the generated C, for any toolchain |
| `shared` | — | **Refused.** See [§6](#6-what-does-not-work) |

```bash
node build/app.js            # headless run; exit status is the program's
python -m http.server        # then open http://localhost:8000/build/app.html
```

> **The three files travel together.** `app.html` loads `app.js` with a
> `<script src="app.js">` tag and `app.js` fetches `app.wasm`, so copying the
> `.html` alone gives a blank page. Deploy the whole `build/` output (or the
> three files side by side) and serve them over HTTP — `file://` blocks the
> `.wasm` fetch in most browsers.

---

## 4. `filum` (threads) in wasm

Threading is real, and it is opt-in at the compiler level. `pengu` adds `-pthread` to a wasm build
**exactly when the program imports `std.filum`** — the same import that switches the
`PENGU_ENABLE_THREADS` gate on in the bundle, so the two can never disagree.

What that buys you:

* `pengu_c_filum_go` creates a real Web Worker (Emscripten's pthreads), not a coroutine.
* `Mutex`, `WaitGroup`, `Cond`, `AtomicInt` and `ChanInt`/`ChanString`/`ChanFloat`/`ChanBool`
  synchronize across those threads via `SharedArrayBuffer` and wasm atomics.
* `goroutine_id` returns a distinct id per running thread.

What it costs you:

* **`SharedArrayBuffer` requires cross-origin isolation in a browser.** Serve the page with:

  ```http
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: require-corp
  ```

  Without both headers the browser refuses to construct the shared memory and the module fails to
  instantiate. Node is not affected.
* `-pthread` also implies `-s PTHREAD_POOL_SIZE=4` (pre-spawned Workers, faster startup). A program
  that needs more concurrent goroutines than that is fine — Emscripten spawns extra Workers on
  demand; the pool is only a warm-up.
* Emscripten warns `-pthread + ALLOW_MEMORY_GROWTH may run non-wasm code slowly` on every threaded
  link. It is informational.

### `exec` / `spawn` do not work

There is no process to spawn in WebAssembly. `pengu_c_exec` and `pengu_c_spawn` are guarded by
`#if PENGU_EMSCRIPTEN`: they write `[PENGU] exec no soportado en wasm` to stderr and return `-1`.
This is deliberate — Emscripten's `system()` is a stub whose return status a caller could misread
as success. In `PenguScript`:

```pengu
import std.rites

var rc as int is calling rites.run_shell with "echo hi"
# rc == -1 on wasm; the real exit status on the host
```

Everything else in `std.rites`, and the whole of the core runtime (strings, lists, maps,
maybe/result, `std.archivum`'s file API over Emscripten's virtual FS, time, math), works unchanged.

---

## 4b. `std.web` — the Web/Emscripten bridge

Without it, every wasm project re-declares the same `emscripten.h` functions by hand, with no
type checking and no docs. `std.web` is that plumbing, and nothing more:

| | |
|---|---|
| Console | `console_log`, `console_warn`, `console_error`, `console_trace` |
| Main loop | `set_main_loop`, `cancel_main_loop`, `pause_main_loop`, `resume_main_loop` |
| Time | `now_ms` (high-resolution monotonic milliseconds) |
| JavaScript | `eval_js` |
| Deferred work | `set_timeout`, `clear_timeout` |
| Constant | `IS_WASM` |

One source, both targets:

```pengu
import std.spark
import std.web

weave frames into int:
    static var n as int is 0
    set n is n + 1
    return n

weave tick into void:
    calling web.console_log with "tick"
    if (calling frames) >= 3:
        calling web.cancel_main_loop

weave main into int:
    if web.IS_WASM:
        calling web.console_log with "hello from wasm"
        # fps 0 => requestAnimationFrame; false => set_main_loop returns
        calling web.set_main_loop with tick, 0, false
    else:
        calling spark.println with "hello from native"
    return 0
```

Native builds are not an afterthought: the module compiles there too, so shared code needs no
`when` of its own. `console_*` write to stderr, `now_ms` reads the runtime's monotonic clock
(`pengu_c_time_monotonic`), `IS_WASM` is `false`, and the genuinely Web-only entry points
(`set_main_loop`, `eval_js`, `set_timeout`, …) call `spark.panic` with an actionable message rather
than failing to link.

Because `when wasm:` folds **before** code generation, a native build contains no Emscripten code
at all, and DCE drops the wasm helpers a program never calls — a program that only calls
`web.now_ms` emits `emscripten_get_now` and nothing else. Both facts are asserted in
`tests/wasm/test_std_web.py`.

### What is deliberately *not* in `std.web`

The scope rule is "works with a plain `emcc` build, no extra flags". Anything needing a linker
setting is a satellite binding, so the module never silently depends on one:

| API | Why not | Where it belongs |
|---|---|---|
| `emscripten_sleep` (async sleep) | needs `-sASYNCIFY` | a satellite, or declare it yourself |
| `fetch` (with progress) | needs `-sFETCH=1` | `pengu-fetch` |
| WebSocket | needs `-lwebsocket.js` | `pengu-websocket` |
| Canvas 2D / WebGL / WebGPU | large thematic API | `pengu-canvas`, `pengu-webgl`, … |
| IndexedDB (`IDBFS`) | needs `-lidbfs.js` | `pengu-idbfs` |
| SDL (`-sUSE_SDL=2`) | needs the port | `pengu-sdl` |

`set_timeout` covers the common "run this later" need with **no** flags, which is why it is here and
`emscripten_sleep` is not. For a blocking-style sleep you must add `-sASYNCIFY` yourself and declare
`emscripten_sleep` in your own project; the module will not pretend to support something that
aborts at runtime.

### Why not `EM_ASM`

`EM_ASM` is the usual way to reach JavaScript from C, but Emscripten rejects it under `-std=c11`
("EM_ASM does not work in -std=c* modes") — and `-std=c11` is what this project's manifests and
`build_runtime.py` select. `std.web` therefore goes through real C APIs (`emscripten/console.h`,
`emscripten/eventloop.h`), which compile in strict ISO C mode. If you want raw JS, `eval_js` runs a
JavaScript string through `emscripten_run_script` without any macro trickery.

---

## 5. Known sharp edges

### 5.1 `static var` with a non-constant initializer is not thread-safe

The generator lowers a dynamic `static var` to:

```c
static FileThing thing;
static bool thing_initialized = false;
if (!thing_initialized) { thing = <init>; thing_initialized = true; }
```

Two threads racing the first use each run `<init>`, so each allocates its own handle and the loser's
handle is orphaned. On wasm this shows up as a **hang**, because `main` and a spawned worker end up
holding *different* channels. This is a pre-existing limitation (native threads behave the same
way), not a wasm-specific one, and it is not fixed in this release: a correct fix needs a
once-init primitive in the emitted C with a per-platform implementation.

**Until then, initialize such a handle from one thread before spawning.** The stress test does this
explicitly — see the `TOUCH` op and the "initialise every resource from ONE thread, before
spawning" block in [`tests/wasm/filum_stress.pengu`](../tests/wasm/filum_stress.pengu).

### 5.2 LeakSanitizer cannot see `filum` handle leaks

LSAN decides "leaked" by scanning memory for pointers, and glibc keeps initialized
`pthread_mutex_t` / `pthread_cond_t` objects in internal lists — so a leaked channel, mutex, wait
group, once or cond looks *still reachable* and LSAN stays silent. Measured on this runtime:

| Handle | `clang -fsanitize=address` reports the leak? |
|---|---|
| `pengu_c_filum_atomic_int_new` (plain `malloc`) | ✅ yes |
| `pengu_c_filum_chan_new` | ❌ no |
| `pengu_c_filum_mutex_new` | ❌ no |
| `pengu_c_filum_wait_group_new` | ❌ no |
| `pengu_c_filum_once_new` | ❌ no |
| `pengu_c_filum_cond_new` | ❌ no |

A clean ASan run therefore proves much less than it appears to.
[`tests/wasm/filum_handles_leakcheck.c`](../tests/wasm/filum_handles_leakcheck.c) closes the gap:
the linker routes `malloc`/`calloc`/`realloc`/`free` through `--wrap` shims that count live blocks,
and the program asserts the count returns to its baseline after every handle is released. It runs
on both targets and is self-checking (`./leakcheck selftest` deliberately leaks one handle and
requires the counter to notice).

#### Running the sanitizers yourself

```bash
# Native: ASan + UBSan + LSan.  PENGU_DEV_CC is REQUIRED -- script mode prefers
# the bundled TCC, and TCC silently ignores -fsanitize=... so the run would look
# clean while being completely uninstrumented.
PENGU_DEV_CC=clang \
PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all" \
PENGU_LDFLAGS="-fsanitize=address,undefined" \
  pengu run tests/wasm/filum_stress.pengu

# Wasm: `-s EXIT_RUNTIME=1` is REQUIRED, not optional.  LeakSanitizer reports
# from an atexit hook, and EXIT_RUNTIME=0 (the default here, see §5.5) never
# tears the runtime down -- so LSan stays silent and a leaky program still exits
# 0.  Measured: the same leaky program is reported clean without it and
# "LeakSanitizer: detected memory leaks" with it.
PENGU_CFLAGS="-fsanitize=address -fno-omit-frame-pointer" \
PENGU_LDFLAGS="-fsanitize=address -s EXIT_RUNTIME=1" \
  pengu run --target wasm tests/wasm/filum_stress.pengu
```

Both commands are regression-tested, and so is the claim that they are *load-bearing*:
`tests/wasm/test_wasm_target.py` runs a deliberately leaky program through each and requires the
sanitizer to report it. Without that, a "no leaks" assertion could pass against an uninstrumented
build and prove nothing — which is exactly what happened during development.

> **`maybe T` is an owned heap cell.** `some val` boxes the payload, so a value received from a
> channel leaks unless it is released. This bit the stress test itself: it leaked one 4-byte cell
> per received message (1200 of them) until every `recv` result was `banish`ed. See the `banish m`
> comment in its channel accessors.

### 5.3 Wasm `SHARED` output is refused

An Emscripten "shared library" is a `SIDE_MODULE`: it needs `-fPIC` on **every** input, including
the runtime archive, plus a matching `MAIN_MODULE` consumer that supplies libc. The runtime archive
is not built with `-fPIC`, so producing one now would emit a `.wasm` that cannot load. The build
stops with an explicit message instead. Use `static` (an archive another bundle can link) or the
default executable output.

### 5.4 Interactive stdin is not implemented

`emcc -o app.html` uses [`pengu_wasm_shell.html`](../pengu_wasm_shell.html) (via `--shell-file`),
which renders stdout/stderr in a dark terminal page. It does not feed a text input back to the
program, and neither does Emscripten's own `shell.html`, so a program that reads stdin sees EOF. To
use the stock Emscripten page instead:

```bash
PENGU_WASM_SHELL=default pengu build --target wasm32-unknown-emscripten
```

Any other value of `PENGU_WASM_SHELL` is treated as a path to a custom shell file.

### 5.5 `EXIT_RUNTIME=0`

Emscripten is invoked with `-s EXIT_RUNTIME=0`, which is a deliberate trade-off
between two cosmetic messages — neither affects output or exit status:

| Program | `EXIT_RUNTIME=0` (used) | `EXIT_RUNTIME=1` |
|---|---|---|
| returns from `main`, no threads | silent | silent |
| returns from `main`, **with threads** | silent | `received "N" command from terminated worker` once per goroutine (Node only) |
| calls `exit()` / panics | `program exited (with status: N), but keepRuntimeAlive() is set …` | silent |

The worker message is the reason for the choice. With `EXIT_RUNTIME=1`, Emscripten
tears the runtime down the instant `main` returns, and because
`pengu_c_filum_go` detaches its threads, Node then complains about every Worker it
terminates — on the **success** path of every concurrent program. The
`keepRuntimeAlive()` notice only appears when a program exits *explicitly*
(`rites.exit`, a failed `assert`, a panic), which is already a failure path.

We do not use `emscripten_force_exit` to silence it: that skips the stdio flush
that `exit()` performs, so a program that printed diagnostics and then panicked
would lose them — a real bug traded for a cosmetic win.

If you prefer the other trade-off (for a leak-checked ASan run, say), pass it
back explicitly:

```bash
PENGU_LDFLAGS="-fsanitize=address -s EXIT_RUNTIME=1" pengu build --target wasm32-unknown-emscripten
```

---

## 6. What does not work

| Feature | Status |
|---|---|
| WASI (`wasm32-wasi`) | Not in this release. Recognized and refused with a message. |
| `rites.exec` / `rites.spawn` | Return `-1` and a stderr diagnostic. No process to spawn. |
| POSIX sockets | Out of scope, even though Emscripten emulates some TCP. |
| `shared` output | Refused; see [§5.3](#53-wasm-shared-output-is-refused). |
| SIMD (`-msimd128`) | Out of scope. Pass it yourself via `PENGU_CFLAGS` if you need it. |
| Web Workers via `WASM_WORKERS` | Not used; classic `pthread` (`-pthread`) is. |
| Compiling the *compiler* (Lark/Python) to wasm | Out of scope. `pengu` itself stays native. |
| Interactive stdin | Not implemented; see [§5.4](#54-interactive-stdin-is-not-implemented). |

---

## 7. Verifying a build

```bash
# 1. The runtime archive really contains wasm objects (not a host archive).
mkdir -p /tmp/check && cd /tmp/check
emar x "$OLDPWD/build/wasm/lib/libpengu_runtime.a"
for f in *.o; do head -c 4 "$f" | xxd; done     # expect: 0061 736d  -> \0asm

# 2. The program runs headlessly, with the right exit status.
node build/app.js ; echo "exit=$?"

# 3. A threaded build really is threaded: the stress test fails loudly if all
#    goroutines report the same OS thread id.
pengu run --target wasm tests/wasm/filum_stress.pengu   # expect: filum_stress: OK

# 4. Handle lifecycle, deterministically (LSAN cannot see these; see §5.2).
pytest tests/wasm/ -q
```

`tests/wasm/` splits itself by cost: the `smoke`-marked tests need no emcc, Node or wasm runtime
and run in the CI smoke job; the `slow` ones skip cleanly when any of the three is missing.

---

## 8. Troubleshooting

### `'emcc' not found in PATH`

`source ./emsdk_env.sh` was not run in this shell, or emsdk was never installed. See
[§1](#1-install-the-emscripten-sdk). `pengu doctor` reports whether `emcc` is visible.

### `The WebAssembly runtime archive libpengu_runtime.a was not found`

The wasm runtime has not been built (or `PENGU_LIB_DIR` points somewhere that holds only the host
archive). Run:

```bash
python build_runtime.py --target emscripten
```

### `Error: shared libraries are not supported ...`

`output = "shared"` in the manifest with a wasm target. See [§5.3](#53-wasm-shared-output-is-refused).

### `Error: the target 'wasm32-wasi' (WASI) is not supported yet`

Expected. Use `--target wasm32-unknown-emscripten`.

### `emcc: error: unable to find library -lpengu_runtime`

The wasm archive is missing from every searched directory. Same fix as above; note that the host
`build/lib/libpengu_runtime.a` will never satisfy a wasm link, by design.

### `[PANIC] std.web.<fn> requires a wasm build (...)`

A native binary called a Web-only entry point (`set_main_loop`, `eval_js`, `set_timeout`, …). Guard
it with `if web.IS_WASM:` or `when wasm:` — see [§4b](#4b-stdweb--the-webemscripten-bridge). The
console functions and `now_ms` work on both targets and need no guard.

### The page loads but nothing happens, or the module fails to instantiate

If the program imports `std.filum`, the page needs cross-origin isolation
(`Cross-Origin-Opener-Policy: same-origin` **and** `Cross-Origin-Embedder-Policy: require-corp`).
See [§4](#4-filum-threads-in-wasm).

### `received "N" command from terminated worker`

Only possible if `-s EXIT_RUNTIME=1` was added by hand. Harmless, and explained in
[§5.5](#55-exit_runtime0).

### `program exited (with status: N), but keepRuntimeAlive() is set …`

Expected when a program exits explicitly (a panic, a failed `assert`, `rites.exit`) — see
[§5.5](#55-exit_runtime0). The exit status is correct. It does not appear for a program that
simply returns from `main`.

### The build hangs with goroutines that never finish

Almost certainly the `static var` race in [§5.1](#51-static-var-with-a-non-constant-initializer-is-not-thread-safe):
initialize shared handles from one thread before spawning.

### `Aborted(...)` / `RuntimeError: memory access out of bounds` inside a call

Rebuild the runtime for wasm. A wasm bundle linked against a stale `build/wasm/lib` archive (for
example one built before a runtime change) trips the ABI pin at link time, but a hand-built archive
can slip through.
