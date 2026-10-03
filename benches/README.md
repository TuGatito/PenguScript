# benches/

Reproducible benchmarks for the PenguScript runtime (roadmap 6.1).

```
python benches/run_bench.py                 # best of 3, human table
python benches/run_bench.py --repeat 5 --csv benches/results/local.csv
python benches/run_bench.py --only fib_40   # a single case
benches/run_bench.sh                        # POSIX wrapper for the above
```

* `*.pengu` — the PenguScript programs under test.
* `c/`, `rust/`, `zig/` — the same programs in C (`-O3`), Rust (`-O`) and Zig
  (`-OReleaseFast`). Baselines are skipped when the toolchain is missing.
* `results/` — CSV output (git-ignored except for `.gitkeep`).

The published table and the analysis live in [`BENCHMARKS.md`](../BENCHMARKS.md).

Toolchain-level timings (`pengu run` cache hit, cold build, `bundle.c` size) are
a different harness: [`scripts/bench.sh`](../scripts/bench.sh).
