# Benchmarks

Honest, reproducible measurements of the PenguScript toolchain and runtime.
Everything on this page was produced by the harness in [`benches/`](benches/) —
no aspirational numbers, and targets that the project does not meet are called
out as such.

Measured on **2026-10-09** at `e4f679c` plus the 2.0 binary-size change
(PenguScript `2.0.0`), best of 3, on the reference environment below.
`tests/test_release_claims.py` fails if this page loses its date: a benchmark
table without one cannot be told from a stale one, and the previous revision of
this file was 6.7× wrong about binary size for exactly that reason (see
§Binary size).

What was re-measured for this revision: every size and run number in §Results
and §Binary size, for all ten cases of [`benches/run_bench.py`](benches/run_bench.py).
The timings in §Toolchain timings still carry their previous numbers and have
not been re-run; they are machine-bound and were not touched by this change.

## How to reproduce

```bash
python build_runtime.py                 # one-time: build the runtime archives
python benches/run_bench.py             # best of 3, human-readable
python benches/run_bench.py --repeat 5 --csv benches/results/local.csv
python benches/binary_size_breakdown.py --legacy   # per-archive size attribution
```

The harness measures, per program:

* **build** — wall time of `pengu build --profile release` (PenguScript only);
* **run** — best-of-N wall time of the produced binary, after one warm-up;
* **size** — the artifact size **after `strip`**.

Baselines (`-O3` for C, `-O` for Rust, `-OReleaseFast` for Zig) are compiled only
when the toolchain is present; a missing toolchain is reported as *skipped*,
never as a win.

## Reference environment

| | |
|---|---|
| CPU / arch | x86_64 |
| OS / libc | Linux 7.2.9 (CachyOS) / glibc 2.44 |
| C compiler | gcc (GCC) 16.2.1 `-O3` |
| Rust | rustc 1.99.0 `-O` |
| Zig | not installed (baselines skipped) |
| Python (toolchain) | 3.14.7 |

Numbers are machine-specific. Re-run the harness on your hardware before drawing
conclusions; the *ratios* are the meaningful part.

## Results (best of 3)

| Case | Pengu build | Pengu run | Pengu size | C run | C size (dynamic) | C size (static) | vs C run |
|---|---|---|---|---|---|---|---|
| `hello_world` | 411 ms | 1.0 ms | **14.3 KiB** | 1.0 ms | 14.1 KiB | 806.2 KiB | 1.24× |
| `fib_40` (n=32) | 379 ms | 13.0 ms | **22.3 KiB** | 6.0 ms | 14.1 KiB | 806.2 KiB | 2.14× |
| `string_ops` | 364 ms | 7.0 ms | **18.4 KiB** | 3.0 ms | 14.1 KiB | 806.2 KiB | 2.14× |
| `list_ops` | 274 ms | 2.0 ms | **14.3 KiB** | 1.0 ms | 14.2 KiB | 806.2 KiB | 1.26× |

Rust `-O` sizes are **328.9–330.9 KiB** for the same four programs; the Rust
binaries link `libc.so` dynamically, exactly like the PenguScript and the C
dynamic column. Zig is not installed on this machine, so its column is skipped
rather than guessed.

`hello_world`'s 1.0 ms is essentially process startup, and the 1.24× is that
startup cost, not a compute comparison. It used to be 9.5× against a 659.5 KiB
binary: a 14 KiB image touches far fewer pages before `main`, which is the part
of the run-time table that improved with the size work.

The stdlib-bound cases (no C/Rust baseline on purpose: the useful comparison is
stdlib-versus-raw-language, not Pengu-versus-C) are measured by the same harness:

| Case (imports `std`) | Pengu build | Pengu run | Pengu size |
|---|---|---|---|
| `stdlib_ops` | 1.81 s | 2.0 ms | **18.4 KiB** |
| `scrolls_ops` | 2.17 s | 89.0 ms | **30.4 KiB** |
| `atlas_ops` | 4.42 s | 8.0 ms | **22.4 KiB** |
| `cipher_ops` | 6.85 s | 94.0 ms | **30.4 KiB** |
| `loom_ops` | 4.02 s | 1.0 ms | **22.4 KiB** |
| `arithmancy_ops` | 1.24 s | 2.0 ms | **18.4 KiB** |

`cipher_ops` imports `std.cipher` and `std.seal`, so it is the only case here
that pulls a native archive (zlib + mbedcrypto); it ties with `scrolls_ops` for
the largest at 30.4 KiB. That is the shape the size work was aiming for: cost
proportional to what the program actually uses, rather than a flat ~660 KiB
floor.

### Binary size: measured, not asserted

The roadmap's original target was `< 65 KB` for a `hello_world` binary. Before
2.0 the real figure was **659.5–679.5 KiB** for every case, because the linker
resolves a static archive at *member* (`.o`) granularity and
`libpengu_runtime.a` had a single member. Any reference to the runtime dragged
in its whole object, which in turn referenced `pcre2_compile`, `xmlReadMemory`,
`curl_easy_init`, `mbedtls_sha256`, `inflate` and `MHD_start_daemon` — and all
six archives were linked unconditionally.

The binary size from 2.0 on, per case:

| Case | Before (2.0) | After (2.0) | Ratio |
|---|---:|---:|---:|
| `hello_world` | 659.5 KiB | **14.3 KiB** | 46× |
| `fib_40` | 667.5 KiB | **22.3 KiB** | 30× |
| `string_ops` | 663.5 KiB | **18.4 KiB** | 36× |
| `list_ops` | 659.5 KiB | **14.3 KiB** | 46× |
| `stdlib_ops` | 663.5 KiB | **18.4 KiB** | 36× |
| `cipher_ops` | 671.5 KiB | **30.4 KiB** | 22× |

The *Before* column is history, not a re-measurement: those are the numbers this
page published for `1.0.0-rc1` at `c8e07d9`, and they are left exactly as they
were rather than edited to fit a story. They are corroborated rather than
trusted — a `hello_world` built on the pre-change 2.0 tree measured 667.5 KiB,
and `binary_size_breakdown.py --legacy` reproduces 663.5 KiB on today's checkout
(§Binary size breakdown). The *After* column was measured for this revision.

**The fair comparison is not the one this page used to make.** The `14.1 KiB`
C column is a *dynamically linked* binary that calls into `libc.so`; a
`hello_world` from `pengu build` is now in exactly the same position, so the
honest C-versus-Pengu ratio is:

| `hello_world`, stripped | Size | vs C dynamic |
|---|---:|---:|
| C `gcc -O3 -s` (links `libc.so`) | 14.1 KiB | 1.00× |
| **PenguScript `pengu build --profile release`** | **14.3 KiB** | **1.01×** |
| Rust `rustc -O` (links `libc.so`) | 328.9 KiB | 0.04× |
| C `gcc -O3 -static -s` (self-contained) | 806.2 KiB | 57× |
| PenguScript with `PENGU_LDFLAGS=-static` | 961.5 KiB | 1.19× vs C static |

So: **the PenguScript binary is now the same size as the C one**, 23× smaller
than the Rust one, and when both are asked for a fully static, self-contained
image PenguScript is **1.19× C static** — it statically links its own runtime
plus zlib, which the C `hello` does not need. The 46.7× claim the project used
to carry is dead, and so is the "~2.0× smaller than Rust" claim that replaced
it: that one was measured against a dynamically linked Rust binary while
PenguScript was statically linking six archives.

The `< 65 KB` roadmap target is **met** by the bare-language cases (14.3–22.3
KiB) and exceeded by the largest stdlib case (30.4 KiB). What it is *not* is a
guarantee for programs that use the native subsystems: each one costs what its
library costs, which the next table makes explicit.

### Binary size breakdown (attribution by archive)

Produced by [`benches/binary_size_breakdown.py`](benches/binary_size_breakdown.py),
which builds `hello_world`, reads the linker's `-Map` to see which bytes each
input archive keeps, and then re-links once per archive to measure the delta
when that archive is dropped. `--legacy` rewrites the captured link command
into its pre-2.0 shape (all six archives, no section GC), so the numbers below
are reproducible on today's checkout rather than only at an old commit; the raw
output is committed at
[`benches/results/binary_size_breakdown.json`](benches/results/binary_size_breakdown.json).

| Archive | In binary (KiB) | Delta when dropped (KiB) | Notes |
|---|---:|---:|---|
| `libpcre2-8.a` | 355.4 | 356.2 | Only linked by `std.regulus` |
| `libmicrohttpd.a` | 104.8 | 128.3 | Only linked by `std.precis` |
| `libz.a` | 75.8 | 75.9 | Only linked by `std.seal` (kept unconditional, costs 0 bytes unused) |
| `libpengu_runtime.a` | 42.5 | — | Always linked; pruned by section GC |
| `libmbedcrypto.a` | 27.0 | 23.9 | Only linked by `std.seal` |
| `xml2` (system, dynamic) | — | 8.0 | Only linked by `std.parchment` |
| `curl` (system, dynamic) | — | 0.0 | Only linked by `std.precis` |

The `--legacy` total is 663.5 KiB, within 1% of the 667.5 KiB the same build
produced before the change; the residual is the archives now being compiled with
`-ffunction-sections`, which adds section headers. Two caveats worth stating
rather than hiding:

* The "in binary" column comes from the link map, where GNU ld credits
  linker-synthesised sections (`.dynsym`, `.rela.*`, `.eh_frame`) to the *first*
  input file it read. That is why `Scrt1.o` shows up with ~20 KiB in the legacy
  map; it is an artefact of the map format, not of that object.
* The "delta when dropped" column is measured with
  `-Wl,--unresolved-symbols=ignore-all`, so a program that genuinely needs an
  archive can still be linked without it and measured. The resulting binary is
  broken on purpose and only its section sizes are read.

For the record, the same table for the **current** link shape is one line long:
`libz.a` is the only third-party archive still on the command line, and it
contributes **0.0 KiB** to the 14.3 KiB artifact. The report in
`benches/results/binary_size_breakdown.json` carries both shapes.

### The frame-trace finding (actionable)

`fib_40` is 2.14× slower than C, outside the roadmap's ±5% target. The cause is
measurable: PenguScript pushes/pops a frame entry on **every** function call for
the crash stack trace that Phase 5 relies on. Disabling it:

```bash
PENGU_CFLAGS="-DPENGU_FRAME_TRACE=0" pengu build --profile release
```

| `fib_40` (n=32) | run |
|---|---|
| frame trace **on** (default) | 13.0 ms |
| C `-O3` | 6.0 ms |

So the diagnostics still cost roughly **2×** on call-heavy code. The default
stays **on** — losing the stack trace on a bounds panic is a worse trade for a
memory-safe language — but the knob exists and is documented. A future release
could make the trace debug-only, or replace the per-call push with a cheaper
ring buffer. The "frame trace off" row is no longer published: it was not
re-measured for this revision, and an unmeasured row in a table with a date on
it is worse than no row.

> Measured during Phase 10: until F10-N3 this knob **did not compile** the
> generated bundle (`implicit declaration of function
> 'pengu_install_crash_handler'`), which made the table above irreproducible. The
> fix is in `pengu_runtime.h` and
> `tests/runtime/test_bounds_flag_independence.py::test_the_generated_bundle_compiles_with_the_frame_trace_off`
> is the gate.

## Toolchain timings

Toolchain-level timings (`pengu run` cache hit, cold gcc/TCC, parser-table cache,
`bundle.c` size, PCH on/off) are measured by [`scripts/bench.sh`](scripts/bench.sh)
and documented in [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md). Reproduce them
with:

```bash
scripts/bench.sh --repeat 5
```

## Revised targets

The roadmap's Phase 6 targets were aspirational. What the project actually
guarantees, and what it does not:

| Metric | Roadmap target | Status |
|---|---|---|
| `pengu run` cache hit | `< 0.08 s` | **not met** (measured 0.381 s; Python startup alone is ~30 ms) |
| `pengu run` cold, gcc release | `< 0.9 s` | met (measured 0.772 s) |
| Stripped binary, hello world | `< 65 KB` | **met** (14.3 KiB for a program that imports no native `std` wrapper; 30.4 KiB for the heaviest stdlib case) |
| Stripped binary, `stdlib_ops` | — | **met** at 18.4 KiB |
| Run time vs C `-O3` | ±5% | **not met** (1.2×–2.1× on these four cases; the per-call frame trace dominates the call-heavy ones) |
| Build of a small project | — | met (0.27–0.41 s for the bare-language cases) |

Publishing the real numbers is the point. Binary size is no longer one of the
project's problems; the per-call frame instrumentation still is, and it is a
deliberate trade rather than a surprise.

## Continuous measurement

[`.github/workflows/nightly.yml`](.github/workflows/nightly.yml) (job `bench`) runs
the harness nightly and on demand, uploading the CSV as an artifact. Benchmarks
never block a pull request: they are noisy on shared CI runners.
