# Benchmarks

Honest, reproducible measurements of the PenguScript toolchain and runtime.
Everything on this page was produced by the harness in [`benches/`](benches/) —
no aspirational numbers, and targets that the project does not meet are called
out as such.

Measured on **2026-10-07** at `c8e07d9` (PenguScript `1.0.0-rc1`), best of 3, on
the reference environment below. `tests/test_release_claims.py` fails if this
page loses its date: a benchmark table without one cannot be told from a stale
one, and the previous revision of this file was 6.7× wrong about binary size for
exactly that reason (see §Binary size).

## How to reproduce

```bash
python build_runtime.py                 # one-time: build the runtime archives
python benches/run_bench.py             # best of 3, human-readable
python benches/run_bench.py --repeat 5 --csv benches/results/local.csv
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

| Case | Pengu build | Pengu run | Pengu size | C run | C size | vs C | Rust run | Rust size |
|---|---|---|---|---|---|---|---|---|
| `hello_world` | 614 ms | 5.4 ms | **659.5 KiB** | 0.57 ms | 14.1 KiB | 9.5× | 0.8 ms | 328.9 KiB |
| `fib_40` (n=32) | 435 ms | 19.5 ms | **667.5 KiB** | 5.30 ms | 14.1 KiB | 3.7× | 9.1 ms | 329.0 KiB |
| `string_ops` | 477 ms | 13.5 ms | **663.5 KiB** | 3.25 ms | 14.1 KiB | 4.2× | 3.4 ms | 330.9 KiB |
| `list_ops` | 374 ms | 6.8 ms | **659.5 KiB** | 1.23 ms | 14.2 KiB | 5.5× | — | — |

`hello_world`'s 5.4 ms is essentially process startup; the interesting numbers are
the CPU-bound ones. The `vs C` ratio for `hello_world` is dominated by that
startup cost and is not a compute comparison.

The stdlib-bound cases (no C/Rust baseline on purpose: the useful comparison is
stdlib-versus-raw-language, not Pengu-versus-C) are measured by the same harness:

| Case (imports `std`) | Pengu build | Pengu run | Pengu size |
|---|---|---|---|
| `stdlib_ops` | 1.61 s | 6.9 ms | 663.5 KiB |
| `scrolls_ops` | 1.82 s | 66.7 ms | 679.5 KiB |
| `atlas_ops` | 3.64 s | 12.7 ms | 675.5 KiB |
| `cipher_ops` | 5.54 s | 80.2 ms | 671.5 KiB |
| `loom_ops` | 3.18 s | 5.8 ms | 671.5 KiB |
| `arithmancy_ops` | 944 ms | 6.5 ms | 663.5 KiB |

### Binary size: measured, not asserted

The roadmap's original target was `< 65 KB`. The real figure is **659–668 KiB**
for the bare-language programs: `bundle.c` is tiny (2.3 KB for hello world), but
every build links the runtime archive **plus its dependency set** —
`-lpengu_runtime -lpcre2-8 -lxml2 -lcurl -lmbedcrypto -lmicrohttpd -lz` (item
4.17, so a stale archive fails at link time instead of corrupting memory). Those
libraries are statically pulled in: `nm` on the stripped hello-world binary shows
`pcre2_compile`, `mbedtls_sha256`, `zlibVersion` and `MHD_start_daemon`.

For reference the Rust equivalents are **~329 KiB**, so PenguScript is ~2.0×
*smaller* — not the ~3.5× this page claimed before, and the 65 KB target is
**not met** by a factor of ~10. An earlier revision measured 98–102 KiB because
the dependency archives were not present in `build/lib` at the time, so the
linker pulled only `libpengu_runtime.a`; the number was not reproducible on a
release machine. It is now.

### The frame-trace finding (actionable)

`fib_40` is 3.7× slower than C, which is far outside the roadmap's ±5% target.
The cause is measurable: PenguScript pushes/pops a frame entry on **every**
function call for the crash stack trace that Phase 5 relies on. Disabling it:

```bash
PENGU_CFLAGS="-DPENGU_FRAME_TRACE=0" pengu build --profile release
```

| `fib_40` (n=32) | run |
|---|---|
| frame trace **on** (default) | 13.9 ms |
| frame trace **off** | **7.9 ms** |
| C `-O3` | 5.3 ms |

So the diagnostics cost **~1.8×** on call-heavy code, and without them PenguScript
lands at **1.5× C** instead of 3.7×. The default stays **on** — losing the stack
trace on a bounds panic is a worse trade for a memory-safe language — but the
knob exists and is documented. A future release could make the trace debug-only,
or replace the per-call push with a cheaper ring buffer.

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
| Stripped binary, hello world | `< 65 KB` | **not met** (659.5 KiB measured; the target is off by ~10×, see above) |
| Run time vs C `-O3` | ±5% | **not met** (3.7×–9.5×; 1.5× with frame trace off) |
| Build of a small project | — | met (0.37–0.61 s for the bare-language cases) |

Publishing the real numbers is the point: the compiler emits plain C and the
runtime is small, but the per-call frame instrumentation dominates CPU-bound
code and the statically linked dependency set dominates binary size. Both are
known, measured, documented trade-offs rather than surprises.

## Continuous measurement

[`.github/workflows/nightly.yml`](.github/workflows/nightly.yml) (job `bench`) runs
the harness nightly and on demand, uploading the CSV as an artifact. Benchmarks
never block a pull request: they are noisy on shared CI runners.
