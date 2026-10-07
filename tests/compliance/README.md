# Compliance corpus

> **This corpus defines the compatibility of PenguScript 1.x.** A language change
> that makes one of these programs stop checking, stop building or stop exiting
> with its recorded code is a **compatibility break**, not a bug in the corpus:
> per [`LANGUAGE.md` §23](../../LANGUAGE.md) it needs a MAJOR release, or the
> program changes together with a `MIGRATION.md` entry.

One canonical program per documented section of [`LANGUAGE.md`](../../LANGUAGE.md),
driven through the real toolchain. The corpus is the normative, executable half of
the compatibility contract; `MIGRATION.md` is the prose half.

## What is verified

Every program is **compiled, built and executed** — never judged by inspecting its
source or the generated C (rule C1):

1. `pengu check --entry <program>` exits `0`;
2. `pengu build --entry <program>` exits `0`;
3. the produced binary exits with the `expects_rc` recorded in `corpus.json`.

The gate is:

```console
$ pytest tests/test_compliance_corpus.py -q   # the pytest gate
$ python tests/compliance/run_all.py          # compile + execute everything
$ python tests/compliance/run_all.py --list   # show the mapping
$ python tests/compliance/run_all.py --only 016
```

`run_all.py` exits non-zero as soon as any program fails, and the pytest module
cross-checks the corpus against the headings that really exist in `LANGUAGE.md`
and against the files on disk. A missing file, an orphan program or a section that
the document does not have is a failure — an empty corpus cannot pass.

## Files

| File | Role |
|---|---|
| [`corpus.json`](corpus.json) | The machine-readable source of truth: `file`, `section`, `title`, `expects_rc`, `pins`. |
| [`EXPECTED.md`](EXPECTED.md) | The human-readable rendering of the same mapping. Do not hand-edit it apart from regenerating it with the corpus. |
| [`run_all.py`](run_all.py) | The runner: check → build → execute, per program, in a throw-away directory. |
| `NNN-slug.pengu` | One program per section; each carries a `# LANGUAGE.md §N — title` header. |

## Coverage and its boundary

**53 programs**, each pinning a distinct `LANGUAGE.md` section. The boundary is
declared rather than implied:

- the corpus covers the **language surface** (§2–§19): syntax, semantics, types,
  generics, manual memory, FFI, literals, `when`, `test`, `with`, stdlib basics;
- it does **not** try to be a section-per-paragraph mirror of the reference, and
  it does not cover the toolchain chapters (§20 cross-compilation, §21 build &
  packages) — those are exercised by their own suites;
- it is deliberately **not** the full stdlib suite: `tests/std_programs/` and the
  `test_std_*` modules cover the 52 modules.

## Adding or changing a program

Rule C5 of the project: no syntax change lands without an entry here.

1. Add `NNN-slug.pengu` with the `# LANGUAGE.md §N — title` header and an
   `expects_rc` that the program really returns.
2. Add its entry to `corpus.json` (and refresh `EXPECTED.md`).
3. Run `pytest tests/test_compliance_corpus.py -q`. It fails if the program is not
   listed, if the listing has no file, or if the section does not exist in
   `LANGUAGE.md`.

The corpus is linked from [`LANGUAGE.md` §22.5](../../LANGUAGE.md) and referenced by
`tests/migration/README.md`; both corpora together are what a 1.x compatibility
claim is checked against.
