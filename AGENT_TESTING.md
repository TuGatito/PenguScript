# AGENT_TESTING.md — testing rules for agents

Read this file before you touch anything under `tests/`. If you are adding tests,
follow it exactly; the rules are machine-checked by `tests/test_test_policy.py`, so
breaking one produces a failing test rather than a code-review argument.

## The one idea

Compile **once**, run **N** times.

The suite used to take 34 minutes because the cost was per *invocation* — Python
startup, importing the compiler, building Lark tables, and above all invoking the C
compiler — once per test. A conformance case costs ~6 ms once the bundle exists.
Everything below follows from that.

## Structure

```
tests/conformance/            <- behaviour. DATA, not code.
  README.md                     the case format, in detail
  _manifest.json                per-case metadata (feature, platforms, profiles, flags)
  _deps.json                    GENERATED: what can affect what (--affected)
  _smoke/                       the cheap tier that `--smoke` runs
  <feature>/                    one directory per language feature
tests/<area>/                 unit / integration / snapshot tests, by area
  compiler/ cli/ codegen/ runtime/ stdlib/ lsp/ tooling/ docs/
  grammar/ features/ regression/ gates/
tests/                        the root holds ONLY cross-cutting gates (max 15):
  test_conformance.py           the one batch runner
  test_test_policy.py           the meta-guard for these rules
  test_compliance_corpus.py     the LANGUAGE.md coverage gate
  test_ci_workflows.py          CI invariants
  test_migration_corpus.py      the migration corpus runner
  test_known_issues.py          documented findings (sanitizer contract)
  test_error_catalog_sync.py    error-code table sync
  test_snapshots_c.py           the justified home for generated-C snapshots
  test_release_claims.py        release claims vs gates
  test_version.py test_semver.py test_pengu_paths.py test_manifest_toml.py
tests/_test_policy_baseline.json  GENERATED: frozen shape of the suite
tools/gen_conformance_deps.py GENERATED _deps.json
tools/gen_test_policy_baseline.py  GENERATED the baseline
tools/pytest_jsonl.py         the JSONL reporter behind `--json`
```

**Where a test goes.** Behaviour that can be judged by running a program belongs
in `tests/conformance/` as a case. Anything else belongs in the area package it
describes. The root is for gates that span the whole suite, and
`test_the_root_test_set_stays_small` fails if a fifteenth-plus file lands there.

**Two things follow from the layout, and both are load-bearing:**

* a test file's `REPO` is `Path(__file__).resolve().parents[2]`, because a file in
  `tests/<area>/` is two levels below the repository root (it used to be one);
* the policy scans (allowlists, `time.sleep`, generated-C readers) are
  **recursive** over `tests/`, while only the *root count* is non-recursive.

## Adding a test for a new feature

1. Create the case:

   ```
   tests/conformance/<feature>/<name>.pengu
   ```

   with exactly **one** `test` block, named after its own path (the path relative to
   `tests/conformance/`, without `.pengu`):

   ```pengu
   # tests/conformance/basics/hello.pengu
   import std.spark

   test "basics/hello":
       calling spark.println with "hello"
   ```

2. Record what it must do:

   ```
   tests/conformance/basics/hello.expected   # its stdout
   tests/conformance/basics/hello.exit       # its exit code (optional, default 0)
   ```

3. Declare it in `_manifest.json` (an entry keyed by the case id, with `feature`
   and `platforms`).

4. Regenerate the graph, and run just your case:

   ```bash
   python tools/gen_conformance_deps.py
   pengu selftest --test 'basics/hello'
   ```

5. Run the meta-guard before you push:

   ```bash
   pytest tests/test_test_policy.py tests/test_conformance.py -q
   ```

Steps 4 and 5 are not optional: `test_deps_graph_is_up_to_date` and
`test_the_baseline_is_not_hand_edited` fail if the generated files lag behind the
tree, which is the point — a stale graph makes `--affected` silently wrong.

**Zero changes to the other root test files.** That is the whole design.

## Commands

```bash
pengu selftest                     # full suite, parallel (~4:37 on 36 cores)
pengu selftest --smoke             # fast tier, ~2.5 s
pengu selftest --affected          # only what HEAD's changes can affect
pengu selftest --affected origin/main
pengu selftest --test 'basics/hello'   # one corpus case
pengu selftest --json              # one JSON object per test on stdout
pengu selftest -n 0                # serial (debugging a flake)
pytest tests -n auto               # equivalent, without the CLI
```

`--json` writes JSONL to stdout and pytest's own output to stderr, so
`pengu selftest --json > results.jsonl` always parses:

```json
{"name": "tests/test_semver.py::test_parse", "status": "pass", "duration_ms": 0.4}
{"name": "tests/conformance.py::test_conformance_case[basics/hello]", "status": "fail", "duration_ms": 6.1, "message": "..."}
```

`pengu test` is **not** this command. It is a language feature: it compiles *your*
project in `--test` mode and runs its integrated `test` blocks. `pengu selftest`
runs this repository's suite.

## Hard rules

Each rule names the test that enforces it.

1. **An end-to-end test never reads the generated C.** Compile it and compare stdout
   and exit code. `test_only_allowlisted_files_read_generated_c`.
2. **A unit test never uses `subprocess`.** If it needs one, it is integration, and
   it belongs behind the `conformance` marker. `test_the_smoke_tier_spawns_nothing`.
3. **A snapshot of generated C only when the runtime cannot detect the regression**,
   and say so in a comment. `test_only_allowlisted_files_read_generated_c`.
4. **Adding a feature adds files to the corpus.** It must not modify existing tests.
   `test_root_test_files_match_the_frozen_baseline`.
5. **A new root test file is a failure.** Put the case in `tests/conformance/`.
   `test_root_test_files_match_the_frozen_baseline`.
6. **One test file, one concept.** No `test_parser_01.py` / `test_parser_02.py`.
7. **No test sleeps.** Force the ordering explicitly (`os.utime`) instead of waiting
   for it. `test_only_allowlisted_files_sleep`.
8. **No test may depend on `hash()` order** (`PYTHONHASHSEED` varies between runs).
9. **No test writes outside `build/` or `tmp_path`.**
10. **No test assumes a platform** unless it says so — and it says so in
    `_manifest.json` (`"platforms"`), never with a scattered `pytest.skip`.

Two of these are ratchets, the same idiom as `fail_under` in `.coveragerc`: the
allowlists in `tests/_test_policy_baseline.json` may only **shrink**. If you make a
file stop reading generated C, regenerate the baseline and let the diff show it.

## Constraints on the corpus

Two things the batch model cannot absorb, both discovered the hard way
(`tests/_inventory.md` §14). Both have tests.

**A case's path is a module path.** The runner imports every case by its path, so
directory and file names must be valid PenguScript identifiers: no leading digit,
no `-`. `compliance/001-hello` fails to bundle with `unexpected '001'`; use
`s001_hello`.

**Every case shares one symbol namespace.** A bundle is a single compilation unit,
so two cases that declare the same top-level name cannot be compiled together, and
a case that imports a `std` module declaring `count` cannot share a bundle with a
case that declares its own `count`. The runner handles this: it splits the corpus
into collision-free groups — accounting for each case's *import closure*, not just
its own declarations — and compiles one bundle per group (`group_cases`). So:

- a case *may* declare helpers, runes and omens; it just may not collide;
- keep top-level declarations out of a case if you can, because that is what makes
  the `_smoke/` tier a single compile
  (`test_the_smoke_tier_is_a_single_bundle` fails if that stops being true);
- the grouping is verified by `test_real_corpus_groups_are_collision_free`, so a
  collision that would break a build is reported as a grouping bug instead.

Migrating the existing standalone `weave main` programs **works**: the 53-program
compliance corpus is `tests/conformance/compliance/` and runs in ~9 s. Two things
made it work, and both were bugs rather than missing features — a codegen bug that
emitted invalid C for destructuring when another module declared a same-named
local (`_inventory.md` §15), and the import-closure grouping. See §16 for the
recipe and the retired runner.

## Cross-platform

Linux, macOS and Windows all run the full suite; a change that is green on one and
red on another is a broken change, not a flake to re-run.

- **Paths**: `pathlib`, never string concatenation with `/` or `\`.
- **Newlines**: compare `.expected` after normalising CRLF to LF — the runner does
  this for you, so write `.expected` with LF.
- **Compiler**: TCC when staged (`pengu_tcc.find_tcc()`, which is *not* on `PATH`),
  else gcc/clang/cc. Do not call `shutil.which("tcc")`; it returns `None` for the
  repository's staged TCC.
- **Shell**: do not assume `bash`, `sh`, or any POSIX command in a test.
- **Platform-only cases**: declare `"platforms": ["linux"]` in `_manifest.json`.

## If a test fails in CI but passes locally

Work through this in order:

1. **Platform?** Then it belongs in `_manifest.json` (`platforms`) or behind an
   explicit marker. A `pytest.skip()` inline is not an answer.
2. **Compiler?** Declare it, and check whether the case is meaningful for every
   compiler before widening the gate.
3. **Timing?** The suite must be deterministic. A `time.sleep` is a guess; a
   `@pytest.mark.timeout(N)` calibrated on an idle machine is the same guess wearing
   a hat — that is why the `test_std_*` family shares
   `STD_PROGRAM_BUILD_TIMEOUT` instead of a literal 30.
4. **Shared state?** This is the most common cause and the hardest to see. In this
   repository parallel execution has already exposed: a test renaming the shared
   `build/lib/libpengu_runtime.a` away, a process-global `release_unsafe` flag
   leaking between tests, and a test asserting on the contents of the shared `/tmp`.
   If a test passes alone and fails in the suite, suspect global state, not the code
   under test.
5. **Case-sensitive filesystem?** Windows and macOS differ from Linux here.

## Regenerating the generated files

```bash
python tools/gen_conformance_deps.py           # tests/conformance/_deps.json
python tools/gen_test_policy_baseline.py       # tests/_test_policy_baseline.json
```

Both support `--check` (CI-friendly: exit non-zero if stale). Both are deterministic,
so a no-op run is a no-op diff. **Never hand-edit either file** — a test asserts it
equals what the generator produces.

## What is still pending

Being explicit, so nobody mistakes the current state for the target:

| Item | Now | Target |
|---|---|---|
| root `tests/*.py` | **12** (frozen, and capped at 15 by a guard) | ≤15 |
| corpus cases | 93 | ≥400 |
| `pytest` full | ~4:37 (36 cores) | <90 s |
| compiled programs | ~750 tests compile C individually | one bundle + cheap spawns |
| coverage floor | `fail_under = 80` in `.coveragerc` | must not go down |

The 190 existing `.pengu` programs under `tests/compliance`, `tests/std_programs`,
`tests/test_generics`, `tests/migration`, `tests/test_manual_memory` and
`tests/test_string_composition` are written as standalone `weave main into int:`
programs. Two `main`s cannot coexist in one binary, so each needs a mechanical
rewrite to `test "<id>":` before it can join the bundle.
`tests/conformance/README.md` has the recipe.

The blocker for deleting unit tests is the coverage ratchet: `.coveragerc` sets
`fail_under = 80` and `tests/test_ci_workflows.py` fails if it drops. Deleting tests
lowers measured coverage, so deletions must be paid for with new coverage or the
floor must be consciously renegotiated.

## Do not

- Do not add `assert "..." in bundle_c` anywhere new.
- Do not use `subprocess` in a unit test.
- Do not mock the compiler. Needing a mock means the test is aimed at the wrong layer.
- Do not scatter `pytest.skip()`. Declare platform needs in `_manifest.json`.
- Do not hand-edit a generated file.
- Do not "fix" a red test by loosening its assertion. If a change to the compiler
  breaks an old test, that is a **finding**: either the behaviour changed on purpose
  (update the test and say why) or the test was pinning an implementation detail
  (move it to the corpus, where behaviour is what is measured).
