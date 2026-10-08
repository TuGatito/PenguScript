# Test-suite performance

Measured on the development machine (Linux, 36 cores, 31 GB RAM, gcc 16 + clang +
TCC 0.9.28rc, CPython 3.14.7, pytest 9.1.1). Reproduce with:

```bash
pytest tests -q -p no:cacheprovider --durations=10          # serial
pytest tests -q -n auto -p no:cacheprovider --durations=10  # parallel
pengu selftest --smoke                                      # the fast tier
```

Full reasoning and the phase-by-phase record live in
[`_inventory.md`](_inventory.md); this file is the scoreboard.

## Before and after

| Metric | Before | After | Target |
|---|---|---|---|
| Full suite, serial | 2059 s (34:19) | 2222 s (37:01) | — |
| Full suite, `-n auto` (36 cores) | — | **186 s (3:06)** | <90 s |
| `pengu selftest --smoke` (units + corpus, runtime present) | did not exist | 4.8 s | <3 s |
| …the units-only tier CI runs (no runtime) | did not exist | **1.4 s** | <3 s |
| One conformance case (marginal) | — | **~6 ms** | <10 ms |
| `pengu selftest --affected` | did not exist | **5.0 s** | <15 s |
| `pengu selftest --test <case>` | did not exist | **0.7 s** | — |
| Root `tests/*.py` | 233 | **12** (frozen, ratcheted, capped by a guard) | ≤15 |
| Conformance cases | 0 | **93** (53 from `tests/compliance`, 37 from `tests/std_programs`, 3 smoke) | ≥400 |
| Compiled programs | ~750 tests compile C individually | 4 bundles for the 56-case corpus | one bundle |
| The 53-program compliance corpus | 53 × (`check`+`build`+`run`) via `run_all.py` | **one build per group, ~9 s total** | — |
| The 85-case corpus, cache warm | 85 × build | **2.0 s** (10 batch builds are 83.7 s of the 85 s cold; the 85 case spawns are 0.5 s) | — |

The suite is green throughout, and the counts reconcile test-by-test.
The counts reconcile test-by-test (3504 at the start, plus the tests added while
making the suite parallel-safe and building the guardrails), so no test is
silently skipped or masked.

## Read the serial row honestly

Serial is **37:01 now against 34:19 before**: it got ~8 % *slower*, not faster. The
new conformance tests account for a few seconds; the rest is environment drift —
this file was written after roughly a dozen full-suite runs on the same machine,
with `build/` grown from 149 MB to 161 MB. The parallel row is the one that
matters and it is measured on the same session. If the serial number is used
anywhere as a baseline, re-measure it on a cold machine first; do not present the
8 % as either a cost or a saving.

## Where the time actually is

The suite is now **throughput-bound, not latency-bound**. That is the single most
useful thing to know about it.

The documentation gates used to be four monoliths: one test compiling every
documented block (~141 s of *setup*), and three tests sweeping every block of three
documents (~157 s). Under `pytest-xdist` a single test cannot be divided, so the
whole suite could never finish faster than the slowest one — `-n auto` bought
nothing against them. They are now parametrised one block per test:

| Gate | Before (one test each) | After (per block) |
|---|---|---|
| `test_doc_blocks.py` | 141.2 s setup | **20 s** across 201 tests |
| `test_frontend_no_crash.py` | 64.8 + 56.2 + 36.4 s | **27 s** across 337 tests |
| `test_api_docs.py` | 147.9 s setup | **49 s** (4-process pool inside the fixture) |

That removed the latency bound and took the suite from 294 s to 241 s. What is left
is the sum of the work, and the work is the problem: 36 workers × 241 s ≈ 8700
core-seconds of aggregate effort. **`<90 s` needs ≲3200 — that is, removing about
60 % of the work, not reorganising it.**

Where that work is: roughly 750 tests still compile C individually. The old cost
model was per *invocation* — Python startup, importing the compiler, building Lark
tables, and invoking the C compiler once per test — and 71 % of the old 34 minutes
was that long tail, never the 30 slowest tests. The batch model removes exactly
that, and it is now proven: the 53-program compliance corpus compiles four bundles
instead of 53 binaries and runs in ~9 s.

## Adding a test in 30 seconds

```bash
cat > tests/conformance/basics/hello.pengu <<'EOF'
import std.spark

test "basics/hello":
    calling spark.println with "hello"
EOF
printf 'hello\n' > tests/conformance/basics/hello.expected

python tools/gen_conformance_deps.py
pengu selftest --test 'basics/hello'      # ~0.7 s
```

Add `"basics/hello": {"feature": "basics", "platforms": ["linux","macos","windows"]}`
to `tests/conformance/_manifest.json` and you are done: no existing file changed, no
`pytest` import, no compile of your own. `pytest tests/test_test_policy.py tests/test_conformance.py -q`
confirms the guardrails still hold. Full contract:
[`conformance/README.md`](conformance/README.md) and
[`../AGENT_TESTING.md`](../AGENT_TESTING.md).

## What is still slow, and why

1. **The documentation gates** (#1–#5 above, ~362 s). Compile doc blocks in one
   batch the way the corpus does.
2. **`-n auto` on a 4-core runner is ~4× the 36-core number**, so CI should land
   around 9–10 minutes. That is an estimate, not a measurement.
3. **`<90 s` is not reachable by parallelism alone** — see above: the suite is
   throughput-bound, so it needs work *removed*. That path is open: the 53-program
   compliance corpus was migrated and runs in ~9 s, and the runner now supports
   per-case build profiles (`"profiles": ["debug", "release"]` in the manifest) so a
   program that was asserted in both was migrated without losing release coverage.
   What remains is doing it for the other corpora and for the programs currently
   embedded in `tests/test_*.py`.
4. **A bundle per collision-free group**, not one bundle: 4 groups for 56 cases.
   Grouping is what makes independent programs coexist despite sharing one Pengu
   symbol namespace, so per-module scoping in the compiler is now an optimisation
   rather than a prerequisite (`_inventory.md` §16.2 corrects §14 on this).
