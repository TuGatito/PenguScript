# PenguScript performance guide

This document explains every optimisation in the toolchain, the measured effect
on the reference machine, and how to disable each one when a bug report needs
the "old" behaviour.

Everything is designed around one rule: **a `pengu run` should feel like running
a script, not like building a project.**

Reproduce every number below with:

```bash
python build_runtime.py          # once
PENGU_TCC=/path/to/tcc scripts/bench.sh --repeat 5
```

The script resets the caches *before every iteration*, so "best of N" is a
genuine cold/warm measurement instead of a warm run that followed a cold one.

## 0. Reference machine

| | |
|---|---|
| OS / CPU | Linux x86_64 (glibc 2.44), 36 hardware threads, warm page cache |
| Python | 3.14.7 (`.venv`) |
| C compiler | gcc (GCC) 16.2.1 |
| TCC | 0.9.28rc 2026-09-26, built from source with `pengu_tcc.ensure_tcc()` |

## 1. Where the time went

Profiling a plain `pengu run hello.pengu` (before this work, i.e. with
`PENGU_CACHE=0 PENGU_NO_DCE=1 PENGU_NO_TCC=1 PENGU_DEV_CC=gcc`) gives:

| Phase | Time | What it is |
|---|---:|---|
| Python start-up + imports | ~135 ms | interpreter, Lark, checker, codegen |
| **Lark LALR table construction** | **~3.5 s** | pure-Python grammar analysis on every process start |
| `pkg-config` probing | ~130 ms | four packages, probed ~12× per build |
| import graph resolution | ~50 ms | parses the entry's imports (cached after the first run) |
| parse + semantic check | ~2 ms | the actual compiler front end (65-line bundle) |
| codegen | ~1 ms | C emission |
| C compiler + link | 20 ms (TCC) / ~400 ms (gcc) | one translation unit |
| running the program | ~7 ms | the binary itself |

Two things dominated: the LALR tables (rebuilt from scratch in every invocation
because `PenguParser` lives in a fresh Python process) and `pkg-config`, which
was re-spawned for every flag lookup.

## 2. Parser table cache (`pengu_cache.py`)

Lark can pickle its analysed tables. The parser now passes
`cache=<cache>/parser/grammar-<sha256>.lark`, and Lark validates the cache with a
sha256 over the grammar text, the options and the Lark/Python versions, so
editing `pengu_grammar.py` invalidates it automatically.

| | Before | After |
|---|---:|---:|
| parser start-up (cold, tables built) | 3.9 s | 3.9 s |
| parser start-up (warm) | 3.9 s | **~0.25 s** |

*Disable*: `PENGU_CACHE=0` (also skips the other caches).

## 3. Compiled-script cache

`pengu run script.pengu` hashes the **contents** of the script, of every module
it imports, the runtime header, the toolchain version, the compiler and the
build flags (`-D`, links, cflags, profile, `--no-dce`) and stores the linked
binary in

```
<cache>/scripts/<key>/app            # 'app.exe' on Windows
```

On a hit the compiler is not invoked at all.  The platform suffix matters:
Windows ``CreateProcess`` appends ``.exe`` to an extension-less image name, so a
file called plain ``app`` would never execute there. On a miss the program is built in a
throw-away directory, the binary is copied into the cache, and the directory is
removed (so the project's `build/` is never touched).

The import graph itself is cached too (`<cache>/imports/<entry-hash>.json`) with
a content digest per module, which turns the import-resolution step into a few
milliseconds while still detecting any edit.

| `hello.pengu` | Before | After |
|---|---:|---:|
| very first run ever (tables + binary) | 3.88 s | 4.16 s (gcc) / 3.80 s (TCC) |
| first run of a script (tables already cached) | 3.88 s | **0.85 s** (gcc) / **0.66 s** (TCC) |
| second run (binary cache hit) | 3.88 s | **0.19 s** |
| `build/` created in CWD | yes | **no** |

The "very first run ever" number is unchanged on purpose: spending ~3.5 s once
to analyse the grammar is unavoidable, and every later invocation reuses the
pickled tables. The realistic first-run case is the second row.

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

### The cache-hit floor

A cache hit costs `pengu` **192 ms** wall, of which 135 ms is the bare CLI
start-up (`pengu gc`) — Python interpreter, imports, argparse. The incremental
cost of a hit over *any* `pengu` invocation is therefore ~55 ms (hash the script
and its imports, `exec` the binary). A sub-30 ms cache hit would require a
resident daemon or a native launcher; see "Known limitations".

## 4. TinyCC (`pengu_tcc.py`)

TCC compiles the generated bundle in **~19 ms** where gcc needs ~400 ms; the
difference is visible on the cache-miss path (655 ms vs 850 ms for a first run
once the parser tables are cached). It is bundled in the release archives and
built by CI, and `find_tcc()` looks in this order:

1. `<bundle>/tcc/tcc` (PyInstaller `sys._MEIPASS`),
2. `<checkout>/tcc/tcc` (unpacked release next to the sources),
3. `$PENGU_TCC`,
4. `PATH`.

`pick_dev_compiler()` prefers it for development builds (`pengu run`) and falls
back to the configured compiler.

* `PENGU_DEV_CC` forces a compiler (`PENGU_DEV_CC=gcc pengu run x.pengu`).
* `PENGU_NO_TCC=1` disables TCC discovery.
* Releases bundle TCC via `make_release.py` (`--add-binary`) and the
  `release.yml` workflow (built from source on Linux/macOS, downloaded from
  `PENGU_TCC_URL` — default `FitzRoyX/tinycc` — on Windows).
* If TCC is missing the toolchain simply uses the configured `cc`.

**Fallback.** TCC is fast but not a complete C11 implementation. If it fails to
compile a bundle, `PenguBuilder.compile()` retries once with the project's
configured compiler and normal flags, and says so on stderr:

```
[pengu] development compiler failed; retrying with gcc
```

The retry is wired to `builder.fallback_cc`, which `pengu run`/`pengu time` set
to the project compiler before swapping in the development one.

**Link line.** TCC's built-in linker driver rejects `-Wl,--start-group`, so the
GNU-ld archive group is emitted for gcc/clang but **not** for TCC (nor MSVC nor
Apple's ld64). Without this, every TCC build failed the link and fell back to
gcc, silently doubling the cache-miss time.

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
* a prunable weave is kept when its name, its C name or the module-qualified
  spelling stripped of its module prefix (`spark_println` → `println`) appears
  in the roots' bodies, transitively,
* references are collected from the AST **and** from interpolated strings
  (which are re-parsed later, so `"{calling cb64_char with v}"` keeps
  `cb64_char`),
* generic templates and their monomorphized instances are never pruned, and the
  original weave order is preserved (specialization names carry counters),
* only weave bodies/prototypes are dropped: runes, omens, constants, `declare`s
  and C declarations are always emitted.

**What counts as prunable** is anchored to a root, not to a path component: a
module is prunable when it lives directly under `std/` or `lib/` of the
repository or of the project's `base_dir`. A user project that merely *lives* in
a directory called `lib` (`/home/me/lib/proj/…`) keeps every weave, and
`.d.pengu` bindings are never pruned.

**Alias fix.** The reference matcher used to strip *any* suffix, so a weave named
`unused_vendor` inside `lib/vendor/pengu/vendor.pengu` was kept by its own last
segment `vendor`, which appears in every call site as the module alias — nothing
inside `lib/` bindings was ever pruned. Only the module's own prefix (plus
multi-token suffixes for modules whose insignia differs from their file name) is
stripped now.

| Bundle | Before | After |
|---|---:|---:|
| `hello.pengu` (uses only `println`) | 432 lines / 19.4 KB | **65 lines / 2.3 KB** (-84%) |

`pengu expand script.pengu` prints the resulting bundle, `--verbose` reports the
reduction (`[pengu] DCE: dropped 33 unused std weave(s) … 35 -> 2 weaves (-94%)`),
`pengu time` prints the pruned count, and the bundle itself is self-describing:

```c
/* Dead-code elimination: pruned 33 of 35 std/lib weave(s), 35 -> 2 */
...
/* Dead-code elimination: disabled (PENGU_NO_DCE) */   // with --no-dce
```

`PENGU_NO_DCE=1` / `--no-dce` disable the pass (also useful for bug reports).
`--no-dce` is part of the script cache key, so an A/B comparison never reuses the
other mode's binary; in project mode it reaches `build_project` through
`pengu run --no-dce` as well.

## 7. Precompiled header (opt-in)

`build_runtime.py` compiles a **shared** `build/include/pengu_runtime.h.gch`
(best effort), and `PenguBuilder._runtime_pch_exists()` finds it through
`pengu_paths.runtime_include_dirs()`; when present it is put first in the include
path instead of regenerating a throw-away PCH per build. The generated fallback
(`_ensure_runtime_pch`) still exists for projects without one and is keyed by a
signature of the `-I`/`-D` flags, so a flag change rebuilds it.

Measured on the reference machine the gain is **not measurable**, so it stays
**off by default**:

| `pengu run hello.pengu --keep --no-cache` (gcc) | Time |
|---|---:|
| `--no-pch` | 638 ms |
| `--pch` | 649 ms (+2%, i.e. noise) |

Two reasons:

1. gcc start-up plus the 14-library link dominate the ~400 ms compile; parsing
   the header is a small part of it.
2. gcc only uses a `.gch` when the `-I`/`-D` set matches the one it was built
   with. `gcc -H` on a default `debug` build shows the shared `.gch` is found but
   **not used** (`x …pengu_runtime.h.gch`) because the build adds `-DDEBUG`,
   `-DWITH_GZFILEOP` and `-I/usr/include/libxml2`, which `build_runtime.py`
   cannot predict. When flags do match, the prebuilt file is used as-is and costs
   nothing.

```
pengu build --pch        # opt in (e.g. header-bound builds, slow filesystems)
pengu run x.pengu --pch
```

It is skipped entirely for TCC/MSVC, and a failed PCH never fails the build.

## 8. pkg-config memoisation (`pengu_paths.py`)

A single build asked `pkg-config` for the same four packages (libxml-2.0,
libcurl, libmicrohttpd, mbedtls) from three places — ~12 subprocesses, ~250 ms on
the reference machine, a third of a TCC build. `_pkg_config_cached` memoizes the
probe per (pkg-config path, args) for the life of the process:

| | Before | After |
|---|---:|---:|
| `PenguBuilder.build_compile_commands()` (first call) | 320 ms | **201 ms** |
| same call repeated in-process (TCC → gcc fallback) | 320 ms | **3 ms** |

The resolved `pkg-config` path is part of the cache key, so a different
toolchain cannot read another one's results. `PKG_CONFIG_PATH` changes within a
process are not tracked: call `pengu_paths.clear_pkg_config_cache()` when
mutating it in-process.

## 9. Ergonomics

| Command | Purpose |
|---|---|
| `pengu doctor [--json]` | compiler (+`--version`)/TCC/runtime/std/cache health report, plus the shared `pch (shared)` path |
| `pengu gc [--all] [--max-age N]` | collect unused cached scripts |
| `pengu expand <script> [-o FILE]` | print the generated `bundle.c` |
| `pengu time <script> [--no-dce]` | per-phase timings (imports, DCE, check, codegen, cc, run) + pruned weave count |
| `pengu eval "<expr>"` | one-liner, compiled through the cache |
| `pengu watch <script>` | re-run on changes (script + imports) |

Global flags: `--quiet`, `--no-color` (also `NO_COLOR=1`), `--verbose`.
C compiler diagnostics are remapped to `file.pengu:line:col [cc] error: …` lines
with `remap_c_diagnostics()`.

## 10. Measured results (summary)

Linux x86_64, Python 3.14.7, gcc 16.2.1, TCC 0.9.28rc, best of 5.
"Before" is emulated with the documented kill switches
(`PENGU_CACHE=0 PENGU_NO_DCE=1 PENGU_NO_TCC=1 PENGU_DEV_CC=gcc`).

| Scenario | Before | After | Δ |
|---|---:|---:|---:|
| `hello.pengu` — very first run ever | 3.88 s | 4.16 s (gcc) / 3.80 s (TCC) | ±0 (noise) |
| `hello.pengu` — first run, parser tables cached | 3.88 s | **0.85 s** (gcc) / **0.66 s** (TCC) | **-78% / -83%** |
| `hello.pengu` — second run (binary cache hit) | 3.88 s | **0.19 s** | **-95%** |
| `hello.pengu` — CLI start-up floor (`pengu gc`) | — | 0.135 s | — |
| `compute.pengu` — compiled binary, 10M-iteration loop (`pengu time`, run phase) | ~33 ms | 33.4 ms | 0% |
| `compute.pengu` — compile + run (forced each time) | ~1.2 s | 0.62 s | -48% |
| `bundle.c` lines (`hello.pengu`, only `println`) | 432 | **65** | **-84%** |
| LALR table construction per process | 3.9 s | **~0.25 s** | **-94%** |
| `build_compile_commands()` (pkg-config probes) | 320 ms | 201 ms | -37% |
| C compile + link of the bundle (TCC vs gcc) | ~400 ms (gcc) | **19 ms** (TCC) | **-95%** |
| second compile with PCH vs without | 638 ms | 649 ms | 0% (kept opt-in) |

## 11. How to measure

```bash
# everything at once (resets the caches before every iteration)
PENGU_TCC=/path/to/tcc scripts/bench.sh --repeat 5

# cold + warm script runs by hand
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

The regression tests for all of this live in `tests/compiler/test_run_cache.py`,
`tests/compiler/test_run_cleanup.py`, `tests/compiler/test_dce.py`, `tests/compiler/test_pch.py`,
`tests/codegen/test_tcc_integration.py` and `tests/compiler/test_dce_tcc_pch.py`.

## 12. Known limitations

* **Cache-hit latency floor.** A hit still pays the full Python interpreter and
  import start-up (~135 ms). The sub-30 ms target would need a resident daemon or
  a native launcher.
* **Packaged PCH is silently ignored when flags differ.** `build_runtime.py`
  cannot know a project's `-D`/`-I` set; if they differ from the ones it used,
  gcc ignores the shipped `.gch` and parses the header normally (no error, no
  gain). That is why PCH remains opt-in.
* **TCC fallback and the cache key.** When TCC fails and gcc produces the
  binary, it is stored under the key computed for TCC. The binary is correct and
  the next run is a hit, but a *fixed* TCC will not be retried until the entry is
  invalidated (`pengu gc`/`pengu run --no-cache`).
* **`PKG_CONFIG_PATH` is not part of the pkg-config cache key** (see §8).
* **DCE is name-based.** A weave reachable only through a mechanism that leaves
  no identifier in the AST (a string built at runtime and looked up dynamically)
  could in principle be pruned. Runes, omens, constants, `declare`s and bindings
  are never pruned, and user modules are always fully emitted, which keeps the
  surface small.
* **Leak checking is Linux/glibc only.** The bundled interposer
  (`tests/leakcheck.c`) is an `LD_PRELOAD` shim that needs `<link.h>`,
  `dl_iterate_phdr` and `__libc_malloc`; macOS and Windows have none of those.
  `@requires_leakcheck` (see `tests/conftest.py`) skips those tests there — or
  uses `valgrind` when it exists — instead of failing on a build error that says
  nothing about the compiler. `PENGU_NO_LEAKCHECK=1` forces the skip path.
* **Known codegen leak (xfail).** An owned string *temporary* passed as a call
  argument is never released: `calling spark.println with (n to string)` lowers to
  `spark_println((pengu_to_string(n)))` with no matching `pengu_banish_string`.
  The same applies to `chr`, interpolations and call results used as arguments,
  so fixing it means teaching the codegen to release expression temporaries (a
  feature). Two leak programs are `xfail(strict=False)` (the interposer's
  conservative marking hides the block on some runs, so a strict marker would
  flake) and `test_call_argument_string_temporary_is_released` is a
  `xfail(strict=True)` deterministic pin: when the compiler is fixed it XPASSes
  and CI asks for the markers to be removed.
* **Pre-existing leak-test flakiness.** Two leak tests fail on the reference
  machine *without* any of this work:
  `tests/codegen/test_generics_suite.py::test_generics_no_memory_leaks[test_map_of_string_to_list]`
  (deterministic, 2 bytes) and
  `tests/compiler/test_string_composition_suite.py::test_string_composition_no_memory_leaks[leak_binary_interp]`
  (intermittent: 7/20 failures on the pristine `[0.15.0]` tree, 11/20 with this
  work — within binomial noise at n=20). Both are 2-byte losses reported by the
  `LD_PRELOAD` leakcheck harness (valgrind was not installed here), so they are
  unrelated to DCE/perf and should be tracked separately.
