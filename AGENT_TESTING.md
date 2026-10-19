# Adding and running tests

The suite exists to catch regressions, not to occupy a coffee break. **The
default run must stay under 7 minutes on a normal developer machine; 10 minutes
is the hard ceiling.** If a change pushes it past that, fix the test — do not
delete coverage that is still earning its keep.

Measured on the reference 36-core box (2026-10-18, `VERSION` 2.13.0):

| Command | Wall time | Tests |
|---|---|---|
| `pytest tests/` (the default, parallel) | **3–4 min** (195–202 s measured) | 1201 collected, 1198 passed, 3 skipped |
| `pytest tests/ -n 0` (serial, for debugging) | ~53 min | same |
| `pengu selftest --smoke` | ~18 s | fast tier, no full rebuild |

The compiler is the cost driver: almost every end-to-end test shells out to
`pengu`, which parses the program, generates C and runs `gcc`. Optimise the
number of those invocations, not the assertions.

## Rules

1. **Parallel by default.** `pytest.ini` sets `-n auto --dist loadgroup`; plain
   `pytest tests/` is the fast path. Do not add a test that only passes when the
   workers are serialized. Pass `-n 0` locally when a failure needs a readable
   traceback and `-n 4`/`-n 8` on a small or memory-constrained box; never go
   back to serial as the default.
2. **One compilation, many assertions.** A stdlib test writes one program with
   twenty checks and asserts that no `FAIL` line appears, instead of compiling
   twenty programs (see `tests/stdlib/conftest.py`). The same rule applies to
   new compat and conformance tests.
3. **One CLI pass per conformance program.** `pengu run` already checks and
   builds internally; do not also call `pengu check` and `pengu build` for the
   same file. That triple pass used to be the most expensive thing in the
   corpus.
4. **Mark slow work.** Anything over a second gets `@pytest.mark.slow`, so
   `-m "not slow"` and `pengu selftest` can skip it. `-m smoke` is the tier with
   no subprocess at all.
5. **Group shared bundles.** If several cases build the same bundle, give them
   one `@pytest.mark.xdist_group("bundle-name")`; under `--dist loadgroup` that
   bundle is built once, not once per worker.
6. **Leak and sanitizer gates are opt-in.** The ASan runs
   (`PENGU_CFLAGS=... pytest tests/stdlib/audit/...`) and `PETITIO_LIVE=1` are
   manual/nightly gates, not part of the default budget.
7. **A test that cannot fail is debt.** If a test asserts something the compiler
   cannot get wrong (or duplicates another test exactly), delete it instead of
   paying for its compilation.

## Checking the budget

```bash
# Wall time plus the slowest tests, on the real parallel configuration.
pytest tests/ --durations=20

# The fast tier only.
pytest tests/ -m "not slow"

# One directory while iterating.
pytest tests/stdlib/test_petitio.py
```

`tests/tooling/test_test_config.py` fails if `pytest.ini` loses `-n auto` or
`--dist loadgroup`, which is how a serial (53-minute) run creeps back in.
