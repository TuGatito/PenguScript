# Contributing to PenguScript

Thanks for considering a contribution. PenguScript is a Python-implemented
compiler for the PenguScript language that emits C99/C11 and links a C runtime.
This guide covers how the project is built, tested, documented and released, and
the review rules a change must satisfy.

Current version: **0.16.0**, in **beta** — usable, not yet production-ready. Read
[`AUDIT_1.0.md`](AUDIT_1.0.md) (the verified assessment) and
[`ROADMAP_2.0.md`](ROADMAP_2.0.md) (the live plan) before proposing large changes.

## Contents

[1 Welcome/scope](#1-welcome-and-scope) · [2 Setup](#2-getting-set-up) · [3 Tests](#3-running-the-tests) · [4 No text gates](#4-the-no-text-gates-rule) · [5 Style](#5-style)
[6 Regression tests](#6-tests-that-must-fail-when-the-change-is-reverted) · [7 Diagnostics](#7-adding-a-diagnostic--error-code) · [8 Docs](#8-documentation-duties) · [9 Release](#9-release-process) · [10 Commits/PRs](#10-commit-and-pr-conventions)

## 1. Welcome and scope

This guide is for people fixing bugs or adding features to the compiler, CLI, LSP
or `std/`; writing `std_c/` bindings and C-library integrations; or improving
documentation, tests and CI. It does not replace the normative references:
[`LANGUAGE.md`](LANGUAGE.md) (the language), [`CHEATSHEET.md`](CHEATSHEET.md)
(syntax and C translation) and [`docs/PENGU_BUILD.md`](docs/PENGU_BUILD.md)
(build tooling).

**Language policy.** The repository is bilingual, but **English is canonical**.
The Spanish documents ([`LANGUAGE_Spanish.md`](LANGUAGE_Spanish.md),
[`PenguScriptGuideSpanish.md`](PenguScriptGuideSpanish.md)) are translations kept
for reach; when a Spanish text and its English counterpart disagree, the English
text wins and a contribution is judged against it. New documents, comments,
identifiers and diagnostics are written in English. Translations are welcome, but
a translation must not silently change meaning.

## 2. Getting set up

System packages (compilers, CMake/Ninja, `pkg-config`, and the headers the runtime
links against) are listed per platform in
[`README.md`](README.md#building-the-runtime-from-source). The repository itself:

```bash
git clone https://github.com/pengus-lang/penguscript.git
cd penguscript

# Python virtual environment + toolchain dependencies
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Build the C runtime and the bundled static libraries into build/
python build_runtime.py
```

[`requirements.txt`](requirements.txt) pins `lark` (grammar), `pyyaml`,
`pygls`/`lsprotocol` (LSP), `pycparser`, `pyinstaller`, `pytest`,
`pytest-timeout`, `tomli` (Python < 3.11) and **`ruff`**, used by the gate in §3.
The runtime build is idempotent:

```bash
python build_runtime.py            # download externs if needed, build everything
python build_runtime.py --rebuild  # force a clean rebuild
python extern_manifest.py          # only fetch/extract the external sources
```

It produces `build/lib/libpengu_runtime.a` plus the external libraries, and the
headers in `build/include/` (including the precompiled `pengu_runtime.h.gch`).
Tests needing a library use `requires_lib`/`requires_runtime` and skip cleanly on a
fresh checkout, but a contribution should be validated with the runtime built.
[`docs/PENGU_BUILD.md`](docs/PENGU_BUILD.md) has the artefact list and the
portable/FHS release layouts. In a source checkout the CLI is
`python pengu_project.py <command>`; a release ships the same code as the
`pengu`/`pengu.exe` executable, and this guide uses the source form.

## 3. Running the tests

Run from the repository root — the tests import `tests.conftest`.

```bash
# The full suite exactly as CI runs it
python -m pytest tests -q -p no:cacheprovider --timeout=600

# The shorter form quoted by the release checklist
python -m pytest tests -q

# One file, one test by node id, or a keyword filter
python -m pytest tests/test_error_codes_uniqueness.py -q -p no:cacheprovider
python -m pytest tests/test_error_codes_uniqueness.py::test_error_class_default_codes_are_unique -q
python -m pytest tests -q -k "strict_c99 or msvc"
```

`--timeout` comes from `pytest-timeout`. CI is stricter: each phase job runs its
subset with `-x` (stop at the first failure), e.g.
`python -m pytest tests/test_grammar_strict.py tests/test_audit_regressions.py -q -p no:cacheprovider --timeout=600 -x`
— see [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for the exact file lists.

Before pushing, also run the cheap gates CI runs:

```bash
python scripts/smoke.py                                                          # end-to-end toolchain smoke test
python pengu_project.py fmt --check std/                                         # formatting gate
python -m ruff check --select F821,E9 --exclude extern,build,vscode-extension .  # undefined names / syntax
```

`ruff` with `F821` as an error is not cosmetic: an undefined name can be a compiler
crash (blocker B6: `pengu_infer.py` referenced `node` instead of `target_node`).

### Test helpers and markers

`tests/conftest.py` provides plain helpers (imported with
`from tests.conftest import ...`) and skip markers — deliberately **not**
`@pytest.fixture`s, so they work in module-level setup too:

| Helper / marker | What it does |
|---|---|
| `check`, `check_ok`, `check_error(src, contains=…)` | Parse/check; `check_error` asserts failure and that the message mentions `contains` (e.g. `"E0012"`). |
| `gen_bundle`, `bundle_project` | Return generated C; the latter resolves `import std.…` through the real builder. |
| `compile_run(source)` | Temp project → bundle → compile → **run**; returns the `CompletedProcess`. |
| `check_c_syntax`, `strip_bounds_checks` | `gcc/clang -fsyntax-only -std=c11` on generated C; normalise bounds-check wrappers before shape assertions. |
| `have_lib`, `have_tool`, `have_std_module` | Probes: `lib<name>.a` exists, tool on `PATH`, `std/<name>.pengu` exists. |
| `requires_lib(name)`, `requires_runtime`, `requires_cc`, `requires_leakcheck` | Skip markers for optional libraries, the runtime archive, a C compiler, the leak interposer. |

Useful environment variables: `PENGU_CFLAGS` / `PENGU_LDFLAGS` (injected into
every compiled test program — this is how the sanitizer job works),
`PENGU_TEST_VALGRIND=1`, `PENGU_NO_LEAKCHECK=1`, `PENGU_CACHE=0`. Reuse
`compile_run`/`gen_bundle` instead of shelling out yourself: the sanitizer job
([`.github/workflows/sanitizers.yml`](.github/workflows/sanitizers.yml)) relies on
every test inheriting those flags through `conftest.py`.

## 4. The "no text gates" rule

> **Rule:** no gate may approve a property by inspecting **text**; it must
> **compile**, **execute** or **measure**.
>
> Original wording in [`AUDIT_1.0.md`](AUDIT_1.0.md) §15.2: *"ningún gate puede
> aprobar una propiedad inspeccionando **texto**; debe **compilar**, **ejecutar**
> o **medir**."*

For new work: if a test concludes that a feature *works* from `"foo" in generated_c`
or from grepping a source file, it is a text gate. Prefer **compile** (feed the C
to a real compiler, not a substring check), **execute** (build, run, assert on
observable behaviour), or **measure** (count or time the real artefact, e.g. parse
the AST or run `ruff`).

### Why: the seven false-green gates

§15.2 documented how 0.16.0 shipped with open blockers behind a green suite. Line
numbers are the audit's and may have drifted. Reproduced in English:

| Gate | What it believed it proved | What it really proved | Bug it let through |
|---|---|---|---|
| `tests/test_cli_strict_c99.py:50` | "strict C is portable" | Absence of two strings (`__extension__`, `__auto_type`) in a text | §4.1 — 13 hard `gcc` errors |
| `tests/test_c99_portability.py` (5 tests) | Same | Compiles a 20-line program with **no imports** | §4.1 |
| `tests/test_error_codes_uniqueness.py` | "the error codes are unique" | Only `kwargs.setdefault` defaults; ignores 24 raw emissions | §2.3 — `E0035` with 4 meanings |
| `tests/test_attributes_msvc.py:39` | "MSVC works" | Compares **generated text** | §5.1 — the runtime does not compile with MSVC |
| `.github/workflows/ci.yml` (`CC_BIN="gcc"`) | "Windows = MSVC" | MinGW `gcc` | §5.1 |
| `.github/workflows/sanitizers.yml` (ASan step) | "the leak stays visible without breaking CI" | Runs the suite twice, the second time **without** the `--deselect` | §11.3 — red job |
| `tests/test_ci_workflows.py` (tag→release invariant) | "the tag→release handoff works" | The literal `v*` exists in the triggers | §14.6 |

The four historical offenders are `tests/test_cli_strict_c99.py:50`,
`tests/test_c99_portability.py`, `tests/test_error_codes_uniqueness.py` and
`tests/test_attributes_msvc.py:39`. **Phase 8 / item 8.1 (B10)** in
[`ROADMAP_2.0.md`](ROADMAP_2.0.md) converts them so each compiles, analyses or
measures (item 8.18 shares the harness via `tests/conftest.py`). The Phase 8 exit
criterion: **no test verifies a property by inspecting text.**

## 5. Style

[`PenguScriptGuideEnglish.md`](PenguScriptGuideEnglish.md) is the **normative**
style guide for `std.*` and user modules; [`LANGUAGE.md`](LANGUAGE.md) is
normative for what is legal. Read the guide the way you would read PEP 8 for
Python; the summary below is orientation, not a substitute.

**Layout.** PenguScript is indentation-sensitive. This repository pins **4 spaces
per level** in [`.pengufmt.toml`](.pengufmt.toml) (and
[`std/.pengufmt.toml`](std/.pengufmt.toml)); `pengu fmt` reads the nearest config,
so `python pengu_project.py fmt --check std/` is the gate. If a document (e.g.
`LANGUAGE.md` §20.7) still says "2-space", the pinned config wins; `--indent N` /
`--tabs` override it per invocation, and `## @generated` files are skipped.

**Bindings and constants.** `const` is top-level only (inside a weave is `E0001`).
`let` is an immutable binding, `var` mutable. **Top-level `var`/`let` is forbidden
(`E0002`):** for module state use a `static var` inside an accessor `weave` (guide
§8.3); for a fixed value use `const`.

**Strings.** `+` does not concatenate strings (`E0005`) — use interpolation `"{expr}"`.
Building a string with `+=` in a loop is an anti-pattern and O(n²); prefer a join.

**Expressions over statements.** If an operation computes a value, express it as an
expression — `if`-value blocks instead of `var` + `set`, comprehensions
(`for x in xs then x * x`, with `when` to filter) instead of loops with `push`,
`do:` to isolate a multi-step computation, `judge` instead of long `if`/`else`
chains, and `with:` to build or mutate a value field by field:

```pengu
let label is if score >= 100 then "winner" else "keep going"
let squares is for x in nums then x * x
let evens is for x in nums when x % 2 == 0 then x
```

Naming follows the guide: `snake_case` for weaves/values/files, `PascalCase` for
types, `SCREAMING_SNAKE_CASE` for exported constants, a leading `_` for module/rune
privacy (`E0043` when crossed). Public symbols carry `##` docstrings (guide §3.1, §11).

## 6. Tests that must fail when the change is reverted

**Every fix ships with a regression test that fails if you revert the fix.** This
is the project's standard, stated in [`AUDIT_1.0_FASE7.md`](AUDIT_1.0_FASE7.md)
("todo fix trae un test que **falla al revertir**") and applied throughout the phase
work; the FASE 1 job comment in
[`.github/workflows/ci.yml`](.github/workflows/ci.yml) records that each suite was
verified this way. Before opening a PR:

```bash
python -m pytest tests/test_your_area.py::test_your_regression -q   # 1. passes with the fix
git stash push -- <files-you-changed>
python -m pytest tests/test_your_area.py::test_your_regression -q   # 2. must FAIL without it
git stash pop
```

A test that stays green without the fix is a false green (§4) — replace it with one
that compiles, executes or measures. If a fix is genuinely not testable, say so in
the PR instead of adding a decorative assertion.

## 7. Adding a diagnostic / error code

The catalogue lives in [`pengu_parser/pengu_errors.py`](pengu_parser/pengu_errors.py).
A diagnostic is a class with a distinct default code:

```python
class VarLetTopLevelError(SemanticError):
    """E0002: var/let declared at top-level."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("code", "E0002")
        super().__init__(*args, **kwargs)
```

1. **Pick a fresh code.** Errors are `Exxxx` (`E0000`–`E0058`), warnings `Wxxxx`
   (`W0001`–`W0013`). Two unrelated diagnostics must not share a code — audit
   finding §2.3 was `E0035` covering four conditions.
2. **Define it in `pengu_parser/pengu_errors.py`** with `kwargs.setdefault("code", …)`
   so it is discoverable by class, and raise it through the normal
   checker/inferrer paths.
3. **Regenerate the documentation** — do not hand-edit the tables. The catalogue
   is generated from the sources:

   ```bash
   python tools/gen_error_catalog.py --write   # rewrites docs/error_catalog.json + LANGUAGE.md §22.2/§22.3
   python tools/gen_error_catalog.py --check   # CI gate: non-zero when either artefact has drifted
   ```

   `--write` renders the machine-readable `docs/error_catalog.json` and the
   human-readable tables in `LANGUAGE.md` (and `LANGUAGE_Spanish.md`) between the
   `BEGIN/END GENERATED DIAGNOSTIC CATALOG` markers; the docstring of the class is
   what supplies the explanation. Update `README.md`'s diagnostics list too if the
   code is user-facing.
4. **Let the cross-checks run:** `tests/test_error_catalog_sync.py` fails when the
   JSON, the Markdown tables or the code drift apart (and guards against the five
   phantom classes returning); `tests/test_error_codes_uniqueness.py` fails if two
   error classes default to the same code (the one documented exception is `E0000`,
   shared by `SemanticError` and `ParseError`);
   `tests/test_runtime_hardening.py::test_every_raised_code_is_documented` fails
   when any `code="Exxxx"` emitted in `pengu_parser/` is missing from `LANGUAGE.md`,
   and `::test_warning_codes_are_documented` does the same for warnings.

## 8. Documentation duties

[`docs/README.md`](docs/README.md) is the index and the rule book. Normative
documents live in the repository root: `LANGUAGE.md`/`LANGUAGE_Spanish.md`,
`CHEATSHEET.md`, the English/Spanish style guides, `README.md`, `CHANGELOG.md`,
`SECURITY.md`, `BENCHMARKS.md`, `RELEASE_CHECKLIST.md`, `ROADMAP_2.0.md` and
`AUDIT_1.0.md` — each linked from [`docs/README.md`](docs/README.md).
**Non-normative, supplementary** documents go under `docs/`: build/release guides,
performance and fuzzing methodology, ABI policy, deprecations, and the archived
process documents in `docs/archive/`. Rule of thumb: a document about **using the
language** belongs in the root next to `LANGUAGE.md`; one about **building,
releasing, measuring or fuzzing** belongs in `docs/`; a shipped progress log or
plan belongs in `docs/archive/`.

When behaviour changes, update every document that claims otherwise, and prefer a
test that cross-checks the claim — the project already has several
(`tests/test_cheatsheet_catalog.py`, `tests/test_std_deprecations_doc.py`,
`tests/test_runtime_hardening.py`).

**Changelog.** Every user-visible change gets an entry in
[`CHANGELOG.md`](CHANGELOG.md) under the current **`## [Unreleased] …`** section, in
the existing categories (e.g. `### 🐛 Corregido`), in the established style: what
was wrong, what the fix is, the files involved, and the measurement that proves it.
Do not add a new version heading for unreleased work — §9 covers that.

## 9. Release process

[`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) is normative and two-part: what the
**toolchain** must prove automatically, and what the **author** must do by hand.
Read it before a release; this is orientation only.

```bash
python -m pytest tests -q                  # full suite, 0 failures
python scripts/smoke.py                    # end-to-end toolchain smoke test
python pengu_project.py fmt --check std/   # 0 files to reformat
python scripts/bench.sh --repeat 5         # refresh BENCHMARKS.md on the release machine
python make_release.py                     # package the standalone distribution
```

Each has a job in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) or a
sibling workflow, alongside the strict-grammar/LALR gate, the ABI layout matrix,
the per-phase gates (FASE 1–7), the sanitizer matrix (ASan/UBSan/Valgrind in
[`.github/workflows/sanitizers.yml`](.github/workflows/sanitizers.yml)), `pengu verify`
and the nightly fuzz/bench jobs. Two caveats from the checklist itself:

- **`--strict-c99` is *not* a portability release gate in 0.16.0.** Measured: 34 of
  61 programs in `tests/std_programs/` fail `gcc -std=c99 -pedantic-errors`; it is
  deferred to 1.1 (item 3.2/B5) — see `AUDIT_1.0_FASE3.md` §6–§7.
- The **manual half** (accounts, Discussions, tag signing, announcements) is
  author-only, not agent work.

Release mechanics touch version constants that tests cross-check (e.g.
`tests/test_std_versioning.py`), and `scripts/release_version.py` is the single source
of truth that both `ci.yml` (tagging) and `release.yml` (publishing) call.

## 10. Commit and PR conventions

The format is by practice — there is no commit-msg hook or CI check on the message.
`git log --oneline` shows two forms:

```text
fase6: 6.9 — decode_base64 rechaza '=' fuera de la posición final
fix(cli): --cc tcc finds the shipped TCC (4.12 / L7)
docs(roadmap): close out Phase 4 (16 closed, 4.14 partial)
feat(fmt): pin 4-space style with .pengufmt.toml, fix flag precedence (4.3)
```

- **Roadmap work** uses `faseN: <item> — <one-line summary>`, with the evidence
  (measurement, test name, before/after numbers) in the body. The summary language
  has been mixed Spanish/English historically; English is preferred for new
  commits, since English is canonical.
- **Everything else** uses a Conventional-Commits-style prefix — `feat`, `fix`,
  `docs`, `test`, `chore`, `refactor`, `perf`, `revert` — with a subsystem scope
  (`cli`, `codegen`, `fmt`, `bind`, `runtime`, `docs`, …).
- **One commit per roadmap item.** [`AUDIT_1.0_FASE6.md`](AUDIT_1.0_FASE6.md) states
  the rule ("Un commit por item") and [`AUDIT_1.0_FASE7.md`](AUDIT_1.0_FASE7.md)
  repeats it ("un commit por item; todo fix trae un test que falla al revertir").
  Keep one item, its test, its `CHANGELOG.md` entry and any roadmap/audit update in
  the same commit.

For a pull request: make CI green (`python -m pytest tests -q`,
`python scripts/smoke.py`, `python pengu_project.py fmt --check std/` and the
`ruff F821,E9` gate), state the roadmap/audit item (or the bug) the PR closes, and
include the **evidence** — the regression test that fails on revert and the
measurement behind any performance or correctness claim. The working rule is to
**measure the premise before implementing**: a claim without a command or a test
behind it will be sent back. Do not mix unrelated cleanups into a feature or fix.
