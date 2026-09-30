# PenguScript performance guide

This document explains every optimisation in the toolchain, the measured effect
on this repository's reference machine, and how to disable each one when a bug
report needs the "old" behaviour.

Everything is designed around one rule: **a `pengu run` should feel like running
a script, not like building a project.**

## 1. Where the time went

Profiling a plain `pengu run hello.pengu` (before this work) gave:

| Phase | Time | What it is |
|---|---:|---|
| Python start-up + imports | ~140 ms | interpreter, PyYAML, Lark, checker |
| **Lark LALR table construction** | **~2.8 s** | pure-Python grammar analysis on every process start |
| import graph resolution | ~160 ms | parses every imported module |
| parse + semantic check | ~100 ms | the actual compiler front end |
| codegen | ~8 ms | C emission |
| C compiler (gcc) + link | ~180 ms | one translation unit |
| running the program | ~10 ms | the binary itself |

The LALR tables dominated everything: they were rebuilt from scratch in every
invocation because `PenguParser` lives in a fresh Python process each time.

## 2. Parser table cache (`pengu_cache.py`)

`Lark` can pickle its analysed tables. The parser now passes
`cache=<cache>/parser/grammar-<sha256>.lark`, and Lark validates the cache with a
sha256 over the grammar text, the options and the Lark/Python versions, so
editing `pengu_grammar.py` invalidates it automatically.

| | Before | After |
|---|---:|---:|
| parser start-up (cold, tables built) | 2.99 s | 2.99 s |
| parser start-up (warm) | 2.99 s | **0.26 s** |

*Disable*: `PENGU_CACHE=0` (also skips the other caches).

## 3. Compiled-script cache

`pengu run script.pengu` now hashes the **contents** of the script, of every
module it imports, the runtime header, the toolchain version, the compiler and
the build flags (`-D`, links, cflags, profile), and stores the linked binary in

```
<cache>/scripts/<key>/app
```

On a hit the compiler is not invoked at all. On a miss the program is built in a
throw-away directory, the binary is copied into the cache, and the directory is
removed (so the project's `build/` is never touched).

The import graph itself is cached too (`<cache>/imports/<entry-hash>.json`) with
a content digest per module, which turns the ~160 ms resolution step into a few
milliseconds while still detecting any edit.

| `hello.pengu` | Before | After |
|---|---:|---:|
| first run (gcc, no TCC) | 3.41 s | **0.52 s** |
| second run (cache hit) | 3.00 s | **0.17 s** |
| `build/` created in CWD | yes | **no** |

### Flags

| Flag | Effect |
|---|---|
| *(default)* | content-hash cache, nothing written to `build/` |
| `--keep` | builds into `build/<name>_run/`, keeps `bundle.c` and the binary, always rebuilds |
| `--no-cache` | ignores the cache for this invocation (no read, no write) |
| `--clear-cache` | empties the script cache first |
| `--ephemeral` | throw-away temp dir, never populates the cache (CI) |
| `--` | everything after it goes to the script (`std.rites.get_args`) |

`PENGU_CACHE=0` disables every cache, `PENGU_CACHE_DIR` relocates the root
(default: `~/.cache/pengu`, `%LOCALAPPDATA%\pengu`, `~/Library/Caches/pengu`).
Read-only cache roots fall back to a temporary directory automatically.

## 4. TinyCC (`pengu_tcc.py`)

TCC compiles the bundle several times faster than gcc. `find_tcc()` looks in the
PyInstaller bundle (`sys._MEIPASS/tcc/tcc`), next to the checkout, in
`$PENGU_TCC` and finally in `PATH`. `pick_dev_compiler()` prefers it for
development builds (`pengu run`) and falls back to the configured compiler.

* `PENGU_DEV_CC` forces a compiler (`PENGU_DEV_CC=gcc pengu run x.pengu`).
* `PENGU_NO_TCC=1` disables TCC discovery.
* Releases bundle TCC via `make_release.py` (`--add-binary`) and the
  `release.yml` workflow (built from source on Linux/macOS, downloaded from
  `PENGU_TCC_URL` on Windows).
* If TCC is missing the toolchain simply uses the configured `cc`.

## 5. Development flags for `pengu run`

A script build is cached or discarded, never debugged, so `pengu run` adds
`-g0 -fno-plt -pipe -fno-ident -fno-asynchronous-unwind-tables` to the `debug`
profile (and drops `-g`). TCC only receives `-O0` (it rejects unknown options).
`pengu build --profile release` is untouched.

## 6. Dead-code elimination (`pengu_dce.py`)

Importing a std module used to emit every weave of it (and of its transitive
imports). DCE prunes the ones nothing reachable refers to:

* roots: every weave of a **non-std** module (user code, bindings, static
  libraries are always emitted), `main`, and the bodies of `test` blocks,
* a std/lib weave is kept when its name, its C name or any of the unqualified
  spellings used *inside its module* appears in the roots' bodies,
* references are collected from the AST **and** from interpolated strings
  (which are re-parsed later, so `"{calling cb64_char with v}"` keeps
  `cb64_char`),
* generic templates and their monomorphized instances are never pruned, and the
  original weave order is preserved (specialization names carry counters),
* only weave bodies/prototypes are dropped: runes, omens, constants and C
  declarations are always emitted.

| Bundle | Before | After |
|---|---:|---:|
| `hello.pengu` (uses only `println`) | 435 lines / 19.7 KB | **68 lines / 2.4 KB** (-84%) |

`pengu expand script.pengu` prints the resulting bundle, `PENGU_NO_DCE=1`
disables the pass (also useful for bug reports).

## 7. Precompiled header (opt-in)

`PenguBuilder._ensure_runtime_pch()` can precompile `pengu_runtime.h` into
`<build>/pch/pengu_runtime.h.gch` and put that directory first in the include
path. Measured on this repository the gain was **not** measurable (gcc start-up
plus the 14-library link dominate the ~180 ms compile), and the PCH costs
~115 ms to build in a throw-away directory, so it is **off by default**:

```
pengu build --pch        # opt in (e.g. header-bound builds, slow filesystems)
pengu run x.pengu --pch
```

It is skipped entirely for TCC/MSVC, and a failed PCH never fails the build.

## 8. Ergonomics

| Command | Purpose |
|---|---|
| `pengu doctor [--json]` | compiler/TCC/runtime/std/cache health report |
| `pengu gc [--all] [--max-age N]` | collect unused cached scripts |
| `pengu expand <script> [-o FILE]` | print the generated `bundle.c` |
| `pengu time <script>` | per-phase timings (imports, check, codegen, cc, run) |
| `pengu eval "<expr>"` | one-liner, compiled through the cache |
| `pengu watch <script>` | re-run on changes (script + imports) |

Global flags: `--quiet`, `--no-color` (also `NO_COLOR=1`), `--verbose`.
C compiler diagnostics are remapped to `file.pengu:line:col [cc] error: …` lines
with `remap_c_diagnostics()`.

## 8.1 Measured results (reference machine)

Fedora 44, x86_64, Python 3.14, gcc 16, warm page cache, no TCC installed
(TCC-dependent numbers are therefore reported as N/A).

| Scenario | Before | After | Δ |
|---|---:|---:|---:|
| `hello.pengu` — very first run ever (LALR tables + binary) | 3.41 s | 3.49 s | +2% |
| `hello.pengu` — first run of a script (tables cached already) | 3.41 s | **0.74 s** | **-78%** |
| `hello.pengu` — second run (binary cache hit) | 3.00 s | **0.17 s** | **-94%** |
| `hello.pengu` — first run with bundled TCC | N/A | N/A (tcc not installed here) | — |
| `compute.pengu` — compiled binary, 10M-iteration loop | ~32 ms | 32 ms | 0% |
| `bundle.c` lines (`hello.pengu`, only `println`) | 435 | **68** | **-84%** |
| LALR table construction per process | 2.99 s | **0.26 s** | **-91%** |
| import-graph resolution (2 modules) | 162 ms | 0.4 ms | -99.8% |
| C compile + link of the bundle | 182 ms | 180 ms | 0% |
| second compile with PCH vs without | 176 ms | 176 ms | 0% (kept opt-in) |

The "very first run ever" number is unchanged on purpose: spending ~2.8 s once
to analyse the grammar is unavoidable, and every later invocation reuses the
pickled tables. The realistic first-run case is the second row.

## 9. How to measure

```bash
# cold + warm script runs
rm -rf ~/.cache/pengu/scripts
time .venv/bin/python pengu_project.py run hello.pengu
time .venv/bin/python pengu_project.py run hello.pengu     # cache hit

# phase breakdown
.venv/bin/python pengu_project.py time hello.pengu

# bundle size before/after DCE
.venv/bin/python pengu_project.py expand hello.pengu -o /tmp/with_dce.c
PENGU_NO_DCE=1 .venv/bin/python pengu_project.py expand hello.pengu -o /tmp/without_dce.c
wc -l /tmp/with_dce.c /tmp/without_dce.c
```

The regression tests for all of this live in `tests/test_run_cache.py` and
`tests/test_dce_tcc_pch.py`.
