# The compliance corpus, migrated

> **This corpus defines the compatibility of PenguScript 1.x.** A language change
> that makes one of these cases stop compiling or stop exiting with its recorded
> code is a **compatibility break**, not a bug in the corpus: per
> [`LANGUAGE.md` §23](../../../LANGUAGE.md) it needs a MAJOR release, or the case
> changes together with a `MIGRATION.md` entry.

This is the executable half of the 1.x compatibility contract; `MIGRATION.md` is
the prose half.

## What changed, and what did not

These were 53 standalone programs under `tests/compliance/`, one per numbered
section of `LANGUAGE.md`, each driven through the real toolchain by
`tests/compliance/run_all.py`: `pengu check` → `pengu build` → execute.

They are conformance cases now. Each program's entry point became
`test "<case id>":`, and its recorded behaviour — the stdout and exit code the
original produced, captured by **running** it, never by trusting the prose that
described it — lives beside it as `.expected` and `.exit`.

That trades 53 separate `check`+`build`+`run` cycles for **one build per
collision-free group** plus one cheap spawn per case: the whole corpus runs in
about nine seconds. The guarantees are unchanged, and one of them is checked
directly:

| Guarantee | Where it lives now |
|---|---|
| Every case pins a real, numbered `LANGUAGE.md` section, with that document's own title | `tests/test_compliance_corpus.py` |
| Every case compiles and exits with its recorded code | `tests/test_conformance.py` (the batch runner) |
| The corpus runs under gcc and under clang (roadmap 10.3) | the `compliance` job of `.github/workflows/ci.yml`, via `PENGU_TEST_CC` |

The case ids were sanitised — a case's path *is* a module path, so
`compliance/001-hello` (leading digit, hyphen) is not importable and became
`compliance/s001_hello`. The original file, section and title are recorded per
case in `_manifest.json` (`migrated-from`, `section`, `title`), which is the
machine-readable source of truth that `corpus.json` and `EXPECTED.md` used to be.

## How to run

```console
$ pengu selftest --test 'compliance/s016_judge'      # one case
$ pengu selftest --test 'compliance/'                # the whole corpus
$ pytest tests/test_conformance.py -m conformance -q  # same thing, without the CLI
$ pytest tests/test_compliance_corpus.py -q           # the documentation gate only
$ PENGU_TEST_CC=clang pytest tests/test_conformance.py -m conformance -q
```
