# WebAssembly with PenguScript (`--target wasm`)

> **Status:** MVP (F0–F4). `wasm32-unknown-emscripten` is the only wasm target;
> WASI is recognized and refused. A native compiler is still the bootstrap;
> Emscripten (`emcc`/`emar`) is the C → wasm backend.
>
> This document describes the **current** implementation in `psc`. The old
> Python compiler (`pengu`) and `python build_runtime.py` are historical and
> are not used.

PenguScript emits one C11 translation unit and invokes a C compiler. For wasm,
the backend is **Emscripten**:

- `emcc` compiles and links the generated bundle;
- `emar` writes static archives of wasm objects (GNU `ar` cannot);
- `node` runs the generated `app.js` in CI and in `psc run`/`psc test`.

---

## 1. Install and activate Emscripten

Emscripten is not vendored. Install it once, in userspace:

```bash
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh          # every new shell that builds wasm
```

Verify:

```bash
emcc --version
emar --version
node --version
psc doctor --target wasm
```

If `emcc` is missing, `psc build --target wasm` stops with these installation
instructions instead of failing inside a linker.

---

## 2. Build the wasm runtime (once)

The shipped `libpengu_runtime.a` is host-built and **cannot** satisfy a wasm
link. Build the wasm one separately:

```bash
./tools/build_runtime_wasm.sh
# -> build/wasm/lib/libpengu_runtime.a
# -> build/wasm/lib/libminiz.a
# -> build/wasm/lib/libre.a
# -> build/wasm/include/pengu_runtime.h
```

This script does **not** touch `build/lib/`. The host and wasm archives coexist,
and the two search paths are deliberately disjoint.

The wasm archive is compiled with `-pthread` (that is what makes Emscripten emit
the atomics/shared-memory target features); the final link only passes
`-pthread` when the program imports `std.filum`.

---

## 3. Build and run

```bash
psc build --target wasm                       # build/app.html + app.js + app.wasm
psc build --target wasm32-unknown-emscripten  # same, full triple
psc run   --target wasm                       # builds, then runs node app.js
psc test  --target wasm                       # integrated tests through node
psc check --target wasm                       # checker + codegen, no emcc
psc emit-c --target wasm --out=bundle.c       # inspect the wasm-specific C
```

Aliases: `wasm`, `wasm32`, `emscripten` all mean
`wasm32-unknown-emscripten`. `wasm32-wasi`/`wasi` is recognized and rejected
with an explicit message.

`--target` can also live in the manifest:

```toml
[build]
target = "wasm32-unknown-emscripten"
```

### Artifacts

| `output` | Artifact | Notes |
|---|---|---|
| `exe` (default) | `app.html` + `app.js` + `app.wasm` | open the page, or `node app.js` |
| `static` | `libapp.a` | wasm objects archived with `emar` |
| `obj` | `app.o` | a single wasm object |
| `c` | `bundle.c` | generated C; no emcc needed |
| `shared` | — | **refused** (a side module needs `-fPIC` on every input) |

The three executable files travel together: `app.html` loads `app.js` and
`app.js` fetches `app.wasm`. Deploy the whole output directory and serve it
over HTTP; `file://` blocks the `.wasm` fetch in most browsers.

---

## 4. Compile-time environment

`--target wasm` (or the manifest key) changes the comptime environment before
code generation:

| Variable | Native | wasm |
|---|---|---|
| `os` | `linux`/`macos`/`windows` | `emscripten` |
| `arch` | `x64`/`arm64`/… | `wasm32` |
| `compiler` | `gcc`/`clang`/`tcc` | `emcc` |
| `wasm` | `false` | `true` |
| `wasm_target` | `""` | `emscripten` |
| `main` | `true` only in the entry module | same |
| `debug` | active profile | active profile |

`-D wasm` also makes `when wasm:` and `when defined(wasm)` true, but does not
invent a `wasm_target`. `-D os=...`/`-D compiler=...` override the target value
for that name.

```pengu
when wasm:
    include "emscripten.h"
    declare emscripten_get_now into f64
when not wasm:
    weave now_ms into f64:
        return 0.0
```

The inactive branch is removed before emission; it leaves no trace in
`bundle.c`.

---

## 5. `std.web` and the standard library

`std.web` is the flag-free Emscripten bridge: console (`console_log`,
`console_warn`, `console_error`, `console_trace`), main loop
(`set_main_loop`, `cancel_main_loop`, `pause_main_loop`,
`resume_main_loop`), high-resolution time (`now_ms`), `eval_js`, and
`set_timeout`/`clear_timeout`. Native builds get the same API; the Web-only
entry points `panic` with an actionable message, so shared code compiles on
both targets.

### Portability matrix (MVP)

| Module | wasm | Notes |
|---|---|---|
| `std.spark`, `std.scrolls`, `std.builder` | ✅ | pure PenguScript |
| `std.json`, `std.yaml`, `std.toml` | ✅ | pure / header-only C |
| `std.arithmancy`, `std.numerus`, `std.fractio` | ✅ | libc/libm |
| `std.atlas`, `std.arena`, `std.bitset`, `std.ordinal` | ✅ | containers |
| `std.diagnostic`, `std.sourcemap`, `std.chronicle`, `std.chrono` | ✅ | time/vaqt |
| `std.digest`, `std.cipher` | ✅ | own SHA-256 |
| `std.compressus`, `std.regulus`, `std.lingua` | ✅ | miniz / regex / UTF-8 |
| `std.archivum` | ⚠️ | MEMFS: use `/out.txt` or preloaded assets; no real disk |
| `std.io` | ⚠️ | stdin is not interactive; stdout/stderr work |
| `std.rites` | ⚠️ | env/args/cwd OK; `exec`/`spawn` return `-1`; `run_capture` is native-only |
| `std.filum` | ⚠️ | works with `-pthread`; browser needs COOP/COEP; `sleep` blocks |
| `std.net` | ❌ | browser sockets do not exist; use JS `fetch`/`WebSocket` (future `std.fetch`) |
| `std.dynlib`, `std.ffi_call`, `std.secrets`, `std.petitio` | ❌ | native libraries; rejected with an actionable diagnostic |

`psc build --target wasm` detects the ❌ modules before the linker and fails
with a PenguScript message such as:

```text
psc build: std.net is not available on wasm: browser sockets do not exist; use JS fetch/WebSocket through a binding (std.fetch is planned)
```

### Threads

If the program imports `std.filum`, the link adds `-pthread` and
`-sPTHREAD_POOL_SIZE=4`. Goroutines become real Web Workers
(`SharedArrayBuffer` + wasm atomics). In a browser, serve with:

```http
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

Node is not affected.

---

## 6. Assets

`std_c`/`psc assets` normally uses `.incbin` for large files. Emscripten's
assembler does not implement `.incbin`/`.section`/`.previous`, so for wasm:

```bash
psc assets --target wasm
```

forces the portable C byte-array fallback. The generated
`build/<module>_assets.c` is then linked into the wasm bundle. `psc build` on a
project picks it up automatically.

---

## 7. Flags emitted by `psc`

For a wasm `exe`, `psc` adds:

```text
-std=c11 -Wall
-DPENGU_ENABLE_THREADS=0|1
-O2 (release) / -g -O0 -sASSERTIONS=1 (debug)
-sWASM=1
-sALLOW_MEMORY_GROWTH=1
-sINITIAL_MEMORY=16MB
-sSTACK_SIZE=1MB
-sEXIT_RUNTIME=0
-sENVIRONMENT=web,node,worker
-sEXPORTED_RUNTIME_METHODS=ccall,cwrap,FS
--shell-file pengu_wasm_shell.html
-pthread -sPTHREAD_POOL_SIZE=4   # only with std.filum
```

`PENGU_WASM_SHELL=default` uses Emscripten's stock page. `--cc /path/to/emcc`
and `PSC_CC`/`PENGU_CC` override the detected compiler.

Environment overrides:

- `PENGU_RUNTIME_CROSS` — prefix with `lib/libpengu_runtime.a` for wasm;
- `PENGU_LIB_DIR` / `PENGU_INCLUDE_DIR` — explicit runtime paths;
- `PENGU_WASM_SHELL` — custom shell page.

`PENGU_CFLAGS`/`PENGU_LDFLAGS` are not wired into the self-hosted driver yet;
pass flags through `cflags`/`ldflags` in `pengu.toml` instead.

---

## 8. Troubleshooting

### `emcc not found in PATH`

The Emscripten SDK is not active in this shell. Run `source ./emsdk_env.sh` or
pass `--cc /path/to/emcc`. `psc doctor --target wasm` reports the three tools.

### `cannot find the WebAssembly runtime archive`

Run `./tools/build_runtime_wasm.sh` (and make sure `PENGU_LIB_DIR` does not
point at the host `build/lib`).

### `wasm-ld: undefined symbol: _exit` / `sigaction`

A stale `build/wasm` archive built by a different Emscripten version, or a
host `lib` leaking into `-L`. Rebuild the wasm runtime and check
`psc doctor --target wasm`; the wasm and host searches are disjoint.

### `Cannot find module 'ws'` (Node)

You imported `std.net`, which is unsupported on wasm. The driver should have
rejected it before linking; see the matrix above.

### Page loads but nothing happens / module fails to instantiate

If the program imports `std.filum`, the page needs cross-origin isolation
(COOP/COEP). Also serve the whole output directory, not only the `.html`.

### `program exited (with status: N), but keepRuntimeAlive() is set`

Expected when a program calls `exit()`/panics with `-sEXIT_RUNTIME=0`; the exit
status is correct. Programs that return from `main` are silent.

---

## 9. Verification

```bash
# 1. Build and run headlessly
psc run tests/wasm/std_web_smoke.pengu --target wasm --profile=release
node build/std_web_smoke.js

# 2. The static archive contains wasm objects
emar t build/libapp.a
mkdir -p /tmp/check && cd /tmp/check && emar x ../path/libapp.a
head -c4 app.o | od -An -tx1     # 00 61 73 6d

# 3. Full wasm smoke suite (skips when emcc/node are missing)
bash tests/wasm/run.sh
```

The CI job `WebAssembly (Emscripten)` in `.github/workflows/ci.yml` runs the
same steps on every push/PR.
