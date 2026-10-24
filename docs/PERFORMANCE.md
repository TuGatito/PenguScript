# PenguScript performance guide

This document explains every optimisation in the toolchain, the measured effect
on the reference machine, and how to disable each one when a bug report needs
the "old" behaviour.

Everything is designed around one rule: **a `pengu run` should feel like running
a script, not like building a project.**

Reproduce every number below with:

```bash
python build_runtime.py          # once: builds libpengu_runtime.a only (~1.4 s)
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
| `pkg-config` probing | ~130 ms | four packages, probed ~12× per build (historical: all four were external libraries that have since **moved to satellite repositories**, so a stock runtime build now probes nothing) |
| import graph resolution | ~50 ms | parses the entry's imports (cached after the first run) |
| parse + semantic check | ~2 ms | the actual compiler front end (65-line bundle) |
| codegen | ~1 ms | C emission |
| C compiler + link | 20 ms (TCC) / ~400 ms (gcc) | one translation unit |
| running the program | ~7 ms | the binary itself |

Two things dominated: the LALR tables (rebuilt from scratch in every invocation
because `PenguParser` lives in a fresh Python process) and `pkg-config`, which
was re-spawned for every flag lookup. That second cost came from the four
external libraries that have since **moved to satellite repositories**; the
memoisation is kept for projects that declare their own `pkg-config` packages
(§8).

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
2. `<exe_dir>/tcc/tcc` (portable install: TCC beside the `pengu` executable),
3. `<checkout>/tcc/tcc` (unpacked release next to the sources),
4. `$PENGU_TCC`,
5. `PATH`.

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

## 6. Dead-code elimination

Importing a std module used to emit every weave of it (and of its transitive
imports). DCE now runs in two layers:

1. **Conservative, name-based** (`pengu_parser/pengu_dce.py::prune_weaves`): the
   historical pass. It runs before code generation and only sees Pengu names in
   the AST. It is the fallback for `--test` (test bodies can call generic
   specializations that the exact pass does not translate) and the starting
   point for the exact pass.
2. **Exact reachability over the emitted C**
   (`pengu_codegen/bundle.py::_discover_reachable_weaves`): used by normal
   builds. It translates a root weave, scans the C it just produced for the real
   `c_name` of every call, function value, `@mutates` alias and concept method,
   translates every new dependency and repeats until the worklist is empty. The
   translated bodies are cached and emitted verbatim, so what the scanner saw is
   what the bundle contains.

**Roots** are the same for both layers:

* every weave of a **non-std** module (user code, bindings, static libraries are
  always emitted),
* `main` / `pengu_main` and every `@export("…")` symbol,
* in `--test` mode, the bodies of `test` blocks (via the name-based layer).

**What gets pruned.** Weave bodies and prototypes. In a normal build the exact
pass also drops unreachable monomorphized instances (the old pass kept every
specialization because its synthetic `filepath="."` made it a root), dead
`@mutates` aliases and callees reachable only through default arguments.

**Phase 4a — derived helpers (default).** `Par`, `Ordo`, `Vinculum`, `Imago`
and `Nexus` helpers are `static inline` functions of the bundle, so their only
possible callers are the bundle's own C. A helper block is kept only when a live
weave body, lambda, constant or another live block names one of its functions;
the field-type closure is followed (`Outer_eq` keeps `Inner_eq`). Blocks are
kept whole, so a concept used by a type stays together.

**Phase 4b — types and constants (`--prune-types`, opt-in).** Drops types and
constants no emitted C text names. Roots are live bodies, prototypes, lambdas,
kept constants and kept derived helpers; a type keeps everything its definition
needs (fields, container elements, alias/seal targets, tuple elements), and
simple-enum variants (`Color_Red`) seed their enum. Constants are closed over
other kept constants. This stays opt-in because a `c/` glue file can name a
Pengu type or constant the bundle never spells; `--test` and library builds keep
everything, and `--no-dce` overrides both phases.

**What counts as prunable** is anchored to a real `std/` directory, not only to
the checkout path: `resolved_std_roots()` asks `pengu_paths.std_dirs()`, so FHS
installs (`<prefix>/share/pengu/std`), `PENGU_STD_DIR` and wheels prune exactly
like a source checkout. A user project that merely *lives* in a directory called
`lib` (`/home/me/lib/proj/…`) keeps every weave, and `.d.pengu` bindings are
never pruned.

| Bundle | 2.16.5 | 2.18.0 default | 2.18.0 `--prune-types` |
|---|---:|---:|---:|
| `hello.pengu` (uses only `println`) | 3.7 KB | 3.7 KB | **3.5 KB** |
| `import std.json` (unused) | 142.2 KB | **8.1 KB** | **2.8 KB** |
| `cipher.encode_base64` (one call) | 581.7 KB | **11.4 KB** | **6.7 KB** |
| `import std.petitio` (unused) | 782.2 KB | **15.9 KB** | **4.4 KB** |
| `benches/stdlib_ops.pengu` (3 calls) | 568.9 KB | **10.8 KB** | **8.8 KB** |
| `benches/loom_ops.pengu` (6 calls) | 633.6 KB | **18.3 KB** | **13.3 KB** |

(With DCE disabled entirely, `hello.pengu` is 924 lines / 42.9 KB; the 2.16.5
figures are the old subtree-name pass with the already-minimal import.)

The remaining size after `--prune-types` is mostly runtime/ABI boilerplate and
the modules that are genuinely used; user modules are still fully emitted (a
separate, opt-in scoped tree-shaking phase).

`pengu expand script.pengu` prints the resulting bundle, `--verbose` reports the
weave reduction (`[pengu] DCE: dropped … weave(s)`), `pengu time` prints the
pruned count, and the bundle itself is self-describing:

```c
/* Dead-code elimination: pruned 1494 of 1500 module weave(s), 1500 -> 6 */
/* Dead-code elimination: pruned 20 of 20 derived helper block(s) */
/* Dead-code elimination (--prune-types): pruned 16 type(s), 22 constant(s) */
...
/* Dead-code elimination: disabled (PENGU_NO_DCE) */   // with --no-dce
```

`PENGU_NO_DCE=1` / `--no-dce` disable both exact layers (also useful for bug
reports). `--prune-types` / `PENGU_PRUNE_TYPES=1` enables phase 4b. Both are part
of the script cache key and of the project config hash, so an A/B comparison
never reuses the other mode's binary; in project mode they reach
`build_project` through `pengu run --no-dce` / `pengu build --prune-types`.

### 6.1 User-module tree shaking (`--dce-scope=user`)

By default every weave in a **user** module is a root: a project imports a
utility module and its whole public surface is emitted, even in an executable
where only `main` is called. `--dce-scope=user` (alias `--tree-shake-user`, env
`PENGU_DCE_SCOPE=user`) treats ordinary project modules like `std/`:

* roots are `main` / `pengu_main`, every `@export`, and the identifiers found in
  the project's `c/` glue sources (read before DCE decides);
* `.d.pengu` bindings stay unprunable (they are the C boundary);
* `--test`, `static`/`shared`/`obj` outputs and `--no-dce` keep everything —
  test bodies must reach any helper, and a library's public API is its product.

The flag is off by default and is part of the script cache key/config hash.

```pengu
# util.pengu: 40 helpers, only helper_used is called
import util
weave main into int:
    return calling util.helper_used with 1
```

With two dead helpers the bundle is 3.4 KB → **2.9 KB**; a 40-helper utility
module (only `helper_0` called) is **15.5 KB → 2.9 KB** (−82 %). The savings
depend on how many “public-looking” helpers a project carries. Do **not** enable it when
plugins are loaded with `dlopen` or symbols are resolved by name at runtime:
those are not visible to the DCE scan. Give such entry points `@export`.

### 6.2 `#line` directives (`--no-line-markers`)

`bundle.c` carries `#line` directives so a C compiler error points at the
`.pengu` source line instead of the generated file. They are on by default and
cost 4–26 % of the bundle (the share grows with the number of emitted
statements):

| Bundle | with `#line` | `--no-line-markers` | saved |
|---|---:|---:|---:|
| `hello.pengu` (`println`) | 3.7 KB | **3.3 KB** | -13 % |
| `cipher.encode_base64` (one call) | 11.4 KB | **10.3 KB** | -10 % |
| `import std.petitio` (unused) | 15.9 KB | **15.2 KB** | -4 % |
| `benches/stdlib_ops.pengu` | 10.8 KB | **8.0 KB** | -26 % |
| `benches/atlas_ops.pengu` | 16.7 KB | **12.4 KB** | -26 % |

Use `--no-line-markers` (or `PENGU_NO_LINE_MARKERS=1`) when the bundle is the
deliverable and C-level traceability matters less; the flag is part of the script
cache key and the project config hash. Keep it off for bug reports: the default
is what makes a C diagnostic name the `.pengu` file and line.

Native include/link pruning by live module remains conservative: a `c/` glue
file can use a binding without the bundle naming its C prefix, so `#include` and
`-l` entries are only removed when the module is clearly dead (a later phase).

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

1. gcc start-up plus the link dominate the ~400 ms compile; parsing the header
   is a small part of it. The link is now `libpengu_runtime.a` plus libc, libm
   and pthreads — no external archives.
2. gcc only uses a `.gch` when the `-I`/`-D` set matches the one it was built
   with. `gcc -H` on a default `debug` build shows the shared `.gch` is found but
   **not used** (`x …pengu_runtime.h.gch`) because the build adds `-DDEBUG`,
   which `build_runtime.py` cannot predict. When flags do match, the prebuilt
   file is used as-is and costs nothing.

```
pengu build --pch        # opt in (e.g. header-bound builds, slow filesystems)
pengu run x.pengu --pch
```

It is skipped entirely for TCC/MSVC, and a failed PCH never fails the build.

### 7.1 PCH and the `PENGU_ENABLE_*` feature gates

The runtime has exactly **one** feature gate left: `PENGU_ENABLE_THREADS`
(`std.filum`). The `PENGU_ENABLE_{REGEX,XML,NET,CRYPTO}` gates are gone with the
external libraries that needed them — those libraries **moved to satellite
repositories** and compile into their own archives, not into `pengu_runtime.h`.

The generated `bundle.c` still defines the gate before it includes the header,
and gcc validates the preprocessor state at the point of inclusion. A bundle that
does **not** import `std.filum` defines `PENGU_ENABLE_THREADS 0`, while the
shared `.gch` was compiled with the header's default of `1`, so the PCH is
**found but not usable** for it:

```
$ gcc -H -c build/bundle.c
x /…/build/include/pengu_runtime.h.gch
. bundle.c
$ gcc -Winvalid-pch -H -c build/bundle.c
warning: /…/pengu_runtime.h.gch: not used because 'PENGU_ENABLE_THREADS' is defined
```

Without `-Winvalid-pch` the warning is silent and gcc simply reparses the header —
the same "found but not used" behaviour §7 already documents for `-DDEBUG`.
`PenguBuilder` therefore does not offer the shared PCH to a bundle whose gate
differs from the header's default, and says so under `--verbose`:

```
[pengu] runtime PCH skipped: the bundle's PENGU_ENABLE_* gates differ from
the precompiled header's defaults
```

The rule is exact rather than a threshold: with a single gate, the shared PCH is
offered only to a program that imports `std.filum`. That is one more reason it
stays off by default, on top of the two in §7 — a build with no generated bundle
to inspect (a caller that only wants a command line) is left alone, and gcc
decides.

## 8. pkg-config memoisation (`pengu_paths.py`)

The `std` library no longer wraps any `pkg-config`-discoverable system package:
the four that used to be probed (libxml-2.0, libcurl, libmicrohttpd, mbedtls)
**moved to satellite repositories**. A stock `pengu run hello.pengu` therefore
asks `pkg-config` nothing, and the probe only fires for a project that declares
its own `pkg-config` packages.

The memoisation is kept for exactly that case. When those probes did run they
were issued from three places for the same package — ~12 subprocesses, ~250 ms on
the reference machine, a third of a TCC build — so `_pkg_config_cached` memoizes
the probe per (pkg-config path, args) for the life of the process:

| | Before | After |
|---|---:|---:|
| `PenguBuilder.build_compile_commands()` (first call) | 320 ms | **201 ms** |
| same call repeated in-process (TCC → gcc fallback) | 320 ms | **3 ms** |

(The `Before`/`After` numbers are historical: they were measured while the four
external packages were still probed by `std`.) `--verbose` prints the archive
list the decision produced.

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
| Stripped `hello_world` binary (`pengu build --profile release`) | 659.5 KiB | **14.3 KiB** | **-98%** |
| LALR table construction per process | 3.9 s | **~0.25 s** | **-94%** |
| `build_compile_commands()` (pkg-config probes; those packages are now satellite repositories, so this row is historical) | 320 ms | 201 ms | -37% |
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
  gain). That is why PCH remains opt-in. With a single feature gate left
  (`PENGU_ENABLE_THREADS`), a bundle that does not import `std.filum` is the
  common case that skips the shipped PCH.
* **TCC fallback and the cache key.** When TCC fails and gcc produces the
  binary, it is stored under the key computed for TCC. The binary is correct and
  the next run is a hit, but a *fixed* TCC will not be retried until the entry is
  invalidated (`pengu gc`/`pengu run --no-cache`).
* **`PKG_CONFIG_PATH` is not part of the pkg-config cache key** (see §8).
* **DCE sees the AST and the emitted C, not runtime strings.** A weave reachable
  only through a name built at runtime (or through a C macro/header the bundle
  never spells) could in principle be pruned. Normal builds use the exact
  C-symbol pass; `--test` uses the conservative name-based one. Runes, omens,
  constants, `declare`s and bindings are never pruned, user modules are always
  fully emitted, and `@export` is the documented root for FFI entry points, so
  the practical surface is small.
* **Test bundles keep every instance.** `--test` skips the exact pass because
  test bodies are not part of the discovery scan; the resulting bundle is larger
  than a production one, but it is not distributed.
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
