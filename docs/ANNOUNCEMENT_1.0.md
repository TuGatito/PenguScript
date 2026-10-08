# PenguScript 1.0.0

**What 1.0 is:** the first release whose public surface — language, ABI, CLI,
stdlib, LSP and diagnostics, as listed in [`FREEZE.md`](FREEZE.md) — is frozen for
1.x, and whose compatibility claim is checked by programs that **compile and
execute**, not by prose.

That is the whole claim. Everything below is either the exact command that
verifies it or an explicit statement of what is *not* covered.

---

## What 1.0 is not

**Not features that 1.0 deliberately does not include.** These are design
decisions, not omissions ([`AUDIT_1.0.md`](../AUDIT_1.0.md) §20.6,
[`ROADMAP_1.1.md`](../ROADMAP_1.1.md)):

| Not in 1.0 | Why it waits |
|---|---|
| Borrow checking (lifetimes) | An analysis change, not a syntax change; doing it before 1.0 would have invalidated code that is valid today |
| `async` / `await` | With deterministic manual memory management and no GC, an async runtime is months of work and the stdlib has no demand for it |
| Closures with capture | Breaks the design decision to emit top-level `static` C functions; needs struct + function, a whole language feature |
| AST macros | Huge surface, incompatibility risk; `when` / `comptime` / `shard` cover the common cases |
| Dynamic dispatch / vtables | Contradicts the "zero runtime overhead" claim of `concept`; needs its own document |
| Reflection / RTTI | Would break the pure-C model and the zero-size property of concepts |
| Full dependency backtracking | No measured failure: the current resolver handles the 52 stdlib modules and local deps |
| `Result` everywhere in the stdlib | The two-track API (`write_file` + `write_file_result`) works; forcing the migration would break 174 std tests with no deprecation window |
| WASM playground | Requires a WASM target that does not exist |
| Associated types (`alias Item` in `concept`) | The work is done today with `shard T and U`; the example was withdrawn from the docs until it exists |
| `pengu repl` | `pengu eval` covers the point need; a real REPL needs incremental compiler state |

**Not zero known defects.** 1.0 is a release with a frozen surface and a green
suite; it is not a claim that every measured gap is closed. These are pinned with
`xfail(strict=True)` and listed with their measurements in
[`ROADMAP_1.1.md`](../ROADMAP_1.1.md):

- stdlib leaks under LeakSanitizer (`std/invoke.pengu:105/292`), which is why the
  full ASan suite is not claimed green;
- `--strict-c99` emits invalid C for 18 of the 56 std programs and miscompiles 1
  (`'k' undeclared`; `std/loom.pengu:347` aborts) while the default build is fine;
- `array of T` with no size makes `check` pass and `build` raise a Python
  traceback (rule C4 — this one is a bug, not a design choice);
- `pengu time` / `pengu fmt` on a missing file raise a traceback, and
  `build` / `test` / `doc --entry <missing>` exit 0;
- `compute_config_hash()` ignores `PENGU_NO_DCE`, so the cache can serve a stale
  bundle;
- passing an array to a C variadic is `stack-use-after-scope` under ASan;
- 7 of the 16 pinned dependency `sha256`s point at GitHub `/archive/refs/tags/…`,
  which GitHub may regenerate.

---

## Compilers: what was actually run

| Compiler | Version here | Compliance corpus | Status |
|---|---|---|---|
| **gcc** | 16.2.1 | **54/54** (check + build + execute) | ✅ supported |
| **clang** | 23.1.1 | **54/54** (check + build + execute) | ✅ supported |
| **tcc** | not installed | not run | ⏸️ not claimed here |
| **MSVC** | — | — | ❌ **retired** (Phase 8, item 8.11) |

Reproduce the two rows that were measured:

```console
$ python tests/compliance/run_all.py --cc gcc
$ python tests/compliance/run_all.py --cc clang
```

MSVC is not a supported compiler: the *dialect* is checked
(`clang -fdeclspec -fms-extensions`, and `cl.exe /Zs` where it exists), but no job
links an MSVC binary, because the dependency stack (PCRE2, libxml2, zlib, mbedTLS,
libcurl, libmicrohttpd) has no MSVC build. The old "MSVC supported" claim in
`RELEASE_CHECKLIST.md` is marked ❌ and stays that way
(`tests/test_release_claims.py` fails if it is restated). tcc remains the
development compiler and writes stripped executables, so the ABI symbol pin cannot
be inspected there ([`ABI.md`](ABI.md)).

## Sanitizers and fuzzing: the measured scope, not the promise

- **ASan/UBSan** run as a CI matrix (`workflow: .github/workflows/nightly.yml`,
  job `sanitizers`).
  Phase 8 split it into the two contracts it can actually keep, and that split is
  the honest scope: **memory safety** over the whole suite with the leak verdict
  **off** (`detect_leaks=0`, declared in the workflow — use-after-free, overflow,
  misaligned access and UB stay fatal, but this is *not* a claim of leak-freedom),
  and **leak freedom** (`detect_leaks=1`) over the subset that is verified clean.
  "No leaks across the whole stdlib" is **not** claimed: the measured leak surface
  is 164 failure marks at 92 % of the suite, with traces in `std/invoke.pengu`.
- **Fuzzing** runs nightly, up to **6 hours per harness** in a single job
  (`workflow: .github/workflows/nightly.yml`, job `fuzz`). A single 72-hour job is
  impossible — GitHub kills a job at 6 hours — and the documents that promised it
  were corrected in Phase 9 (F9-N6). No unbounded-duration claim is made.

## macOS: signature yes, notarization no

The macOS artifact is **ad-hoc signed** and `codesign --verify --strict` is a gate.
It is **not notarized** and the project does **not** claim `spctl --assess` passes:
there is no Apple developer account, so there is no `notarytool`
(F9-N8/F9-N9). `release.yml`'s `verify` job publishes the real `spctl` output for
the record instead of asserting it. Details in [`RELEASE.md`](RELEASE.md) §macOS.

## Reproducibility

```console
$ python make_release.py --layout portable --print-hashes
$ python make_release.py --layout portable --print-hashes
```

`make_release.py` pins `SOURCE_DATE_EPOCH`, exports `PYTHONHASHSEED=0` and writes
archives itself with sorted entries and a constant mtime. The three artifacts it
produces are the frozen compiler (`pengu`), the runtime archives under `runtime/`
(including the `runtime/*.a` → `lib/pengu/*.a` mapping the FHS layout relies on,
checked in F9-N7), and `pengus-1.0.0.vsix`.

Measured on this tree (2026-10-07, gcc 16.2.1, Python 3.14), **two runs** of the
command above; `--print-hashes` lists 229 files in total:

| Artifact | SHA-256 (both runs) | Reproducible |
|---|---|---|
| `pengu` (frozen compiler) | `062bbd1c087e0b7b0f31bb750400bed2f3f2ee4a20ea4c8b748d7c374c3dad5a` | ✅ identical |
| `runtime/libpengu_runtime.a` | `cc547c0a1a71079b8d300f830a95bb6373532d9ed1f4001fe2279c20ccd0505b` | ✅ identical |
| `runtime/include/pengu_runtime.h` | `db43d61cbfda967d57829f9837142d9956a8ce6afe93cfa7ad620d9c79309313` | ✅ identical |
| `VERSION` | `92521fc3cbd964bdc9f584a991b89fddaa5754ed1cc96d6d42445338669c1305` | ✅ identical |
| `pengus-1.0.0.vsix` | `12e7108b…` run 1, `0af4fae1…` run 2 | ❌ differs (zip timestamps written by `vsce`) |
| `runtime/include/pengu_runtime.h.gch` | `7722efa5…` run 1, `77b8b4f8…` run 2 | ❌ differs (gcc precompiled header) |

**227 of 229 files were byte-identical; 2 were not.** The release does not claim
the whole tree is bit-reproducible, because it is not: the VS Code extension is
packaged by `vsce` (a zip, which records entry times) and the shipped
precompiled header is written by gcc. What *is* gated is that re-archiving the
same tree is byte-identical (`make_archive`, sorted entries + constant mtime,
`tests/tooling/test_reproducible_release.py`), and that everything derived from the
sources — the frozen compiler, the runtime archives, `std/`, `VERSION` — matches
run to run. Closing those last two is tracked as a 1.1 candidate in
[`ROADMAP_1.1.md`](../ROADMAP_1.1.md).

The PyInstaller binary is not certified byte-reproducible **across machines** (it
embeds interpreter paths); on this machine it was identical run to run. See
[`RELEASE.md`](RELEASE.md) §Reproducibility.

## The compatibility contract, and how to check it

```console
$ pytest tests/test_compliance_corpus.py -q   # 54 programs: check, build, execute
$ pytest tests/test_migration_corpus.py -q    # 11 programs, one per version line
$ pytest tests/tooling/test_freeze_manifest.py -q     # the frozen surface vs the tree
$ pytest tests/test_release_claims.py -q      # every release claim has a gate
$ pengu -V                                    # pengu 1.0.0
```

The migration corpus contains **9 programs that pass and 2 that fail on
purpose**: the pre-`0.10.0` `and`-as-separator forms, which the compiler must
reject with `E0000`/`E0005`. "All programs pass" would be the wrong claim, and the
release does not make it ([`MIGRATION.md`](../MIGRATION.md) §2).

From a source checkout the CLI is `python -m pengu_project`; `pengu` is the
console script and the frozen binary.

---

## Publication

The tag is a **human** step. This environment has **no signing key**
(`git config user.signingkey` is empty), so the release could not be tagged here;
11.3 is recorded as ⏸️ human in [`AUDIT_1.0_FASE11.md`](../AUDIT_1.0_FASE11.md).

Exact commands for the person with write access:

```bash
git tag -s v1.0.0 -m "PenguScript 1.0.0"
git push origin v1.0.0
```

`ci.yml`'s `auto-tag` job creates an **annotated** tag when the changelog is
promoted, and dispatches `release.yml` **only when it created the tag itself** (a
push made with `GITHUB_TOKEN` does not start a workflow run, so the dispatch is
explicit and needs `actions: write`). A signed, human-pushed tag already triggers
`release.yml` through its `push: tags` trigger — the dispatch is an addition, and
the two cannot publish twice. `release.yml`'s `verify` job then downloads the
published artifacts and runs them
(`pengu -V` must match the tag). The invariants are gated by
`tests/tooling/test_release_handoff.py`; the full sequence is in [`RELEASE.md`](RELEASE.md)
§2.

No GPG signature is produced for the artifacts: no release key exists
([`SECURITY.md`](../SECURITY.md) §Release integrity), and the checklist says so
rather than promising one. Every artifact ships with `SHA256SUMS.txt`.
