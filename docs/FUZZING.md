# Fuzzing PenguScript

Continuous fuzzing is part of the 1.0 quality bar (roadmap §5.5): the compiler
front end, the code/binding generators and the auxiliary parsers must never crash
on hostile input. A crash here is a memory-safety or robustness bug, not a
missing diagnostic.

## Harnesses

| Harness | Target | Seeds |
|---|---|---|
| `fuzz_parser.py` | lexer + LALR parser | `tests/std_programs/*.pengu`, `tests/*.pengu`, `std/*.pengu` |
| `fuzz_bind.py` | C header → binding generator | generated headers + real headers from `std_c/`, `build/include/`, `extern/` |
| `fuzz_semver.py` | `pengu_semver` version/constraint parsing | constraint literals |
| `fuzz_lock.py` | `pengu.lock` TOML read/write round trip | lockfiles |
| `fuzz_lsp.py` | language server document handlers | malformed documents and out-of-range positions |

Every harness follows the same contract: the target may either succeed or fail
with a **declared** error (`PenguError`, `SemVerError`, `LockError`,
`HeaderParseError`, `ValueError`, `TypeError`). Any other exception — including
`IndexError`, `KeyError` and `AttributeError` — is a crash and fails the run.

## Running

The harnesses work in two modes.

**Smoke mode (no extra dependencies).** Deterministic: the seed corpus plus
seeded mutations. This is what CI runs on every pull request.

```bash
python scripts/fuzz/fuzz_parser.py        # atheris absent -> smoke mode
PENGU_FUZZ_SMOKE=1 python scripts/fuzz/fuzz_lock.py
```

**Coverage-guided mode.** Install [`atheris`](https://github.com/google/atheris)
and the harness switches automatically:

```bash
pip install atheris
python scripts/fuzz/fuzz_parser.py -max_total_time=3600 -rss_limit_mb=4096
```

`atheris` finds new coverage on its own; the seed corpus only bootstraps it.

## Reproducing a finding

A smoke-mode crash writes the offending input to `build/fuzz_crashes/<harness>_<n>.bin`.
Replay it with the harness target directly:

```bash
python - <<'PY'
import sys; sys.path.insert(0, "scripts/fuzz")
from fuzz_parser import target
target(open("build/fuzz_crashes/parser_3.bin", "rb").read())
PY
```

With atheris, run the same command with `-runs=0 <crash-file>` to confirm, then
minimise it (`-minimize_crash=1`) before adding it to the corpus.

## CI schedule

`.github/workflows/fuzz.yml` runs:

| Trigger | Budget |
|---|---|
| Pull request | 5 minutes per harness |
| Nightly (`02:00` UTC) | 1 hour per harness |
| Release branch / manual | 72 hours per harness |

Failures upload the crash corpus and the atheris logs as workflow artifacts.

## Adding a regression

Every minimised finding is committed to `tests/fuzz_corpus/` and exercised by
`tests/test_fuzz_harnesses.py`, so a fixed crash cannot come back unnoticed.

## Disclosure

A crash that is also a security issue (memory corruption, code execution) follows
[`SECURITY.md`](../SECURITY.md): report it privately, do not open a public issue.
Robustness-only crashes (a wrong diagnostic, a slow path) can be filed as normal
bugs with the minimised input attached.
