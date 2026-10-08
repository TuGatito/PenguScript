# Conformance corpus

This directory is **data, not code**. 95% of the test suite belongs here.

A **case** is a `.pengu` file with a sibling `.expected` file, and optionally a
`.exit` file:

```
_smoke/hello.pengu       the case: exactly one `test` block
_smoke/hello.expected    the stdout it must produce
_smoke/hello.exit        the exit code it must produce (optional, default 0)
```

A `.pengu` file with **no** sibling `.expected` is a *support module*: it is
compiled into the bundle so cases can share helpers, but it is not itself a case.

## The rules

1. **Exactly one `test` block per case**, and its name **must be the case id**:
   the path relative to this directory, without `.pengu`.

   ```pengu
   # tests/conformance/basics/hello.pengu
   test "basics/hello":
       ...
   ```

   The runner compiles every case into one binary, then asks that binary for its
   test list (`--list`) and maps name -> index. A name that does not match its
   path is a loud failure, never a silent mix-up between two cases. Selection is
   by index, not by name, because a corpus of 5000 cases repeats names like
   `basic` constantly.

2. **Adding a feature = adding files here.** No existing test file changes.

3. **Compare stdout and exit code, never generated C.** A case is judged by what
   it does, not by what the compiler emitted. Snapshots of generated C live only
   in `tests/test_snapshots_c.py`, and only when the runtime cannot detect the
   regression.

4. **Platform differences go in `_manifest.json`, not in the source.** Declare
   `"platforms": ["linux"]` and the runner skips the case elsewhere. Do not
   scatter `pytest.skip()` calls through the corpus.

## Adding a case

1. Create `tests/conformance/<feature>/<name>.pengu` with a single `test` block
   named `<feature>/<name>`.
2. Record the expected stdout in `<name>.expected` (LF newlines).
3. Record the exit code in `<name>.exit` if it is not `0`.
4. Add an entry to `_manifest.json` with `feature` and `platforms`.
5. Run it:

   ```bash
   pytest tests/test_conformance.py -m conformance -q
   PENGU_TEST_FILTER='<feature>/<name>' pytest tests/test_conformance.py -m conformance
   ```

   To learn what a case actually produces, run the bundle directly:
   `PENGU_TEST_JSON_FILE=/tmp/out.jsonl pytest ...` writes one JSON object per case.

## Why a bundle and not one program per case

Compiling each program separately is what made the old suite take 34 minutes:
the cost was per *invocation* (interpreter + import + Lark tables + codegen + the
C compiler), not per assertion. One binary holding every case, re-executed once
per case via `--only-index N`, costs ~5 ms per case instead of seconds.

`--only-index` also buys real isolation: a case that aborts (bounds check, panic,
divide by zero) kills only its own process, so the remaining cases still run and
still report. That is not true of a single `--test` run, which stops at the first
failure. Measured numbers and the experiment behind this design are in
`tests/_inventory.md` §9.2 and §10.

## Migrating an existing `weave main` program

Most of the pre-existing corpus (`tests/compliance`, `tests/std_programs`, ...)
is written as a standalone `weave main into int:` program. Those **cannot** be
bundled — two `main`s cannot coexist in one binary. To bring one over:

1. Run it once and capture stdout -> `<name>.expected`, exit code -> `<name>.exit`.
2. Rewrite `weave main into int:` as `test "<feature>/<name>":` and drop the
   trailing `return 0` (a test body is void).
3. Keep any helper `weave`s at the top level of the same file.

## Two constraints the corpus has to respect

**1. A case's path is a module path.** The runner imports every case by its path,
so directories and file names must be valid PenguScript identifiers: no leading
digit, no `-`, no `.`. `compliance/001-hello` is *not* importable — the bundle
fails with `unexpected '001'`. Use `compliance/s001_hello`.

**2. Cases share one symbol namespace.** A bundle is a single compilation unit and
PenguScript resolves the symbols of its modules in one namespace, so two cases
that both declare a top-level `Point` cannot be compiled together, and a *local*
named like another case's global can break that case's generic inference. The
runner copes by splitting the corpus into collision-free groups
(`group_cases` in `tests/test_conformance.py`) and compiling one bundle per group,
but that costs compiles and is a workaround, not a fix.

Practical consequences:

- A case that declares **nothing** at top level (just one `test` block using `std`)
  can share a bundle with anything. The `_smoke/` tier is kept to exactly that, so
  `--smoke` stays a single compile — `test_the_smoke_tier_is_a_single_bundle`
  enforces it.
- A case *may* declare helpers, runes and omens; it just may not collide, and it
  may drag its group's size down. Prefixing top-level names with the case's slug
  (`s019_add`) is the cheap way to stay collision-free.
- **Migrating a corpus written as standalone `weave main` programs is blocked on
  this**, not on the rewrite: `tools/migrate_main_to_case.py` converts them
  correctly, but the converted cases then collide. See `tests/_inventory.md` §14.
