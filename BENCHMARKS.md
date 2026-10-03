# Benchmarks

Honest, reproducible measurements of the PenguScript toolchain and runtime.
Everything on this page was produced by the harness in [`benches/`](benches/) —
no aspirational numbers, and targets that the project does not meet are called
out as such.

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
| OS / libc | Linux 7.2.8 (CachyOS) / glibc 2.44 |
| C compiler | gcc 16.2.1 `-O3` |
| Rust | `rustc -O` |
| Zig | not installed (baselines skipped) |
| Python (toolchain) | 3.14.7 |

Numbers are machine-specific. Re-run the harness on your hardware before drawing
conclusions; the *ratios* are the meaningful part.

## Results (best of 3)

| Case | Pengu build | Pengu run | Pengu size | C run | C size | vs C | Rust run | Rust size |
|---|---|---|---|---|---|---|---|---|
| `hello_world` | 599 ms | 6 ms | **98.4 KiB** | 1 ms | 14.1 KiB | 7.3× | 2 ms | 355.1 KiB |
| `fib_40` (n=32) | 463 ms | 32 ms | **102.4 KiB** | 6 ms | 14.1 KiB | 5.5× | 13 ms | 355.1 KiB |
| `string_ops` | 409 ms | 12 ms | **102.4 KiB** | 4 ms | 14.1 KiB | 2.9× | 4 ms | 356.9 KiB |
| `list_ops` | 369 ms | 6 ms | **98.4 KiB** | 2 ms | 14.2 KiB | 4.2× | — | — |

`hello_world`'s 6 ms is essentially process startup; the interesting numbers are
the CPU-bound ones.

### Binary size: measured, not asserted

The roadmap's original target was `< 65 KB`. The real figure is **98–102 KiB**
for these programs: `bundle.c` is tiny (2.3 KB for hello world), but the static
`libpengu_runtime.a` pulls in the containers, strings, the frame stack and the
crash reporter. For reference, the Rust equivalents are **~355 KiB**, so
PenguScript is ~3.5× smaller — but the 65 KB target is **not met** and is not
claimed here.

### The frame-trace finding (actionable)

`fib_40` is 5.5× slower than C, which is far outside the roadmap's ±5% target.
The cause is measurable: PenguScript pushes/pops a frame entry on **every**
function call for the crash stack trace that Phase 5 relies on. Disabling it:

```bash
gcc build/bundle.c -o app -O2 -std=c11 -DPENGU_FRAME_TRACE=0 <link flags>
```

| `fib_40` (n=32) | run |
|---|---|
| frame trace **on** (default) | 60 ms |
| frame trace **off** | **11 ms** |
| C `-O3` | 6 ms |

So the diagnostics cost ~5.5×, and without them PenguScript lands at **1.8× C**
instead of 5.5×. The default stays **on** — losing the stack trace on a bounds
panic is a worse trade for a memory-safe language — but the knob exists and is
documented. A future release could make the trace debug-only, or replace the
per-call push with a cheaper ring buffer.

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
| `pengu run` cache hit | `< 0.08 s` | **not met** (Python startup alone is ~30 ms) |
| `pengu run` cold, gcc release | `< 0.9 s` | met (~0.85 s) |
| Stripped binary, hello world | `< 65 KB` | **not met** (98.4 KiB measured) |
| Run time vs C `-O3` | ±5% | **not met** (2.9×–7.3×; 1.8× with frame trace off) |
| Build of a small project | — | ~0.4–0.6 s |

Publishing the real numbers is the point: the compiler emits plain C and the
runtime is small, but the per-call frame instrumentation dominates CPU-bound
code, and that is a known, measured, documented trade-off rather than a surprise.

## Continuous measurement

[`.github/workflows/bench.yml`](.github/workflows/bench.yml) runs the harness
nightly and on demand, uploading the CSV as an artifact. Benchmarks never block
a pull request: they are noisy on shared CI runners.
