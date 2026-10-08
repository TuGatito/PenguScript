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

## Bare-language vs stdlib cases

The first four cases (`hello_world`, `fib_40`, `string_ops`, `list_ops`)
deliberately import nothing: they measure the bare language and carry C/Rust/Zig
baselines. The **stdlib-bound** cases import `std` and have no foreign baseline,
because the comparison that matters is stdlib-versus-raw-language, not
Pengu-versus-C. They are listed in `STDLIB_CASES` in `run_bench.py` and cover
distinct tiers of the library:

| Case | Module exercised | Tier |
| --- | --- | --- |
| `stdlib_ops` | `std.tally`, `std.spark` | reductions + terminal I/O |
| `scrolls_ops` | `std.scrolls` | string search / slice / case / split-join |
| `atlas_ops` | `std.atlas` | hash-map build, probe, sorted keys |
| `cipher_ops` | `std.cipher`, `std.seal` | Base64 codec + C digest bridge |
| `loom_ops` | `std.loom` | generic sequence algorithms |
| `arithmancy_ops` | `std.arithmancy` | C math bridge + pure number theory |

`tests/gates/test_benchmarks.py` enforces that at least six cases import `std`, that
they cover at least six distinct modules, and that every bench file on disk is
registered in the harness.

The published table and the analysis live in [`BENCHMARKS.md`](../BENCHMARKS.md).

Toolchain-level timings (`pengu run` cache hit, cold build, `bundle.c` size) are
a different harness: [`scripts/bench.sh`](../scripts/bench.sh).
