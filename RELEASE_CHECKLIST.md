# Release Checklist — PenguScript 1.0.0

Two lists: what the **toolchain** must prove (automatable, gated in CI) and what
the **author** must do by hand (accounts, announcements). Keeping them apart
stops "publish to Hacker News" from being mistaken for a release blocker.

**Every box in §1 carries a gate**: a `` `command` `` you can run, or a
`workflow: <file>` that runs it for you. `tests/test_release_claims.py` fails if
a box in §1 has neither, so a claim cannot be added without a way to check it.
Boxes in §2 are marked `manual:` — they are human actions, not claims about the
software. The full process is in [`docs/RELEASE.md`](docs/RELEASE.md).

## 1. Automated (CI must be green)

The commands below are the *local* form of gates that also run in
`workflow: .github/workflows/ci.yml`; `workflow: .github/workflows/release.yml`
re-runs the whole suite on the tag before publishing anything.

- [ ] Full test suite, 0 failures — `pytest tests -q`. On the tag this is
      `workflow: .github/workflows/release.yml` ("Run Test Suite").
- [ ] Compilers confirmed: gcc and clang on Linux/macOS, **MinGW** on Windows —
      `workflow: .github/workflows/ci.yml` (matrix `Windows x64` / `Linux x64` /
      `macOS (arm64)`). ❌ **MSVC is not a supported compiler and is not claimed
      here**: `pengu_parser/pengu_runtime.c` includes PCRE2/libxml2/zlib/mbedTLS/
      libcurl/libmicrohttpd, whose MSVC build does not exist, and no job links an
      MSVC binary. The MSVC *dialect* of the generated C is syntax-checked by
      `pytest tests/test_attributes_msvc_native.py -q`. See
      `docs/CROSS_COMPILATION.md` §9 and `AUDIT_1.0_FASE8.md` item 8.11.
- [ ] Strict grammar gate: Lark parses the corpus with `strict=True` and no LALR
      conflicts — `pytest tests/test_grammar_strict.py -q`.
- [ ] ABI layout matrix — `pytest tests/test_abi_layout.py -q` and the C
      `_Static_assert` check `workflow: .github/workflows/ci.yml`
      ("ABI layout matrix").
- [ ] Cross-compilation produces and **executes** a Windows `.exe` —
      `workflow: .github/workflows/cross-compile.yml`.
- [ ] ❌ **`--strict-c99` is NOT a portability gate** and is not claimed as one:
      it is not functional for programs that import `std` in 0.16.0. Measured:
      34 of 61 programs in `tests/std_programs/` fail
      `gcc -std=c99 -pedantic-errors` (16 index-hoisting, 15 statement
      expressions, 3 qualifiers/casts). ⏸️ **Deferred to 1.1** (item 3.2/B5). Re-measure with
      `pytest tests/test_cli_strict_c99.py -q` — see `AUDIT_1.0_FASE3.md` §6–§7.
- [ ] FASE 2 gate: `_Static_assert(PENGU_ABI_VERSION)` present in the generated
      `bundle.c` — `pytest tests/test_abi_version.py -q`.
- [ ] FASE 3 tooling gate (bind, assets, JSON diagnostics, LSP semantics, fmt,
      docs, cross-compilation) — `pytest tests/test_bind_phase3.py
      tests/test_assets.py tests/test_json_diagnostics.py
      tests/test_lsp_semantic_rename.py tests/test_fmt_phase3.py
      tests/test_doc_phase3.py tests/test_cross_compile.py -q`.
- [ ] FASE 4 ecosystem gate (SemVer, lockfile, transitive deps, remove/upgrade,
      vendor/cache, TOML, templates, stdlib versioning) —
      `pytest tests/test_semver.py tests/test_lockfile.py
      tests/test_transitive_deps.py tests/test_manifest_toml.py
      tests/test_std_versioning.py -q`.
- [ ] FASE 5 safety gate (bugs, bounds policy, overflow policy, deprecation,
      supply chain, runtime hardening, fuzz harnesses) —
      `pytest tests/test_phase5_bugfixes.py tests/test_bounds_policy.py
      tests/test_overflow_policy.py tests/test_deprecation_policy.py
      tests/test_supply_chain.py tests/test_runtime_hardening.py
      tests/test_fuzz_harnesses.py -q`.
- [ ] Compliance and migration corpora — `pytest
      tests/test_compliance_corpus.py tests/test_migration_corpus.py -q`, also
      `workflow: .github/workflows/compliance.yml`.
- [ ] Standard library formatting: 0 files to reformat —
      `python pengu_project.py fmt --check std/`.
- [ ] Toolchain smoke test (`run` + cache + `doctor`) —
      `python scripts/smoke.py`.
- [ ] Coverage ratchet not lowered — `pytest tests -q --cov
      --cov-config=.coveragerc` (floor in `.coveragerc`; enforced by
      `workflow: .github/workflows/ci.yml`).
- [ ] Nightly fuzz: 6 h per harness (4 shards × 90 min) with no crash —
      `workflow: .github/workflows/nightly.yml`. GitHub kills a job after 6 h, so
      "72 h in one job" is impossible and is not claimed (`docs/FUZZING.md`
      §CI schedule, audit §13.3, roadmap 9.5).
- [ ] Fuzz harnesses also run on pull requests — `python
      scripts/fuzz/fuzz_parser.py` (smoke mode), `workflow:
      .github/workflows/fuzz.yml`.
- [ ] Nightly benchmark CSV uploaded; informational only, never blocking —
      `workflow: .github/workflows/bench.yml`.
- [ ] Benchmarks reproduced on the release machine and `BENCHMARKS.md` refreshed —
      `bash scripts/bench.sh --repeat 5`.
- [ ] ASan/UBSan matrix: no leaks, no undefined behaviour —
      `workflow: .github/workflows/sanitizers.yml`.
- [ ] Static analysis clean — `workflow: .github/workflows/codeql.yml`.
- [ ] Lint gate: no undefined names — `python -m ruff check --select F821,E9
      --exclude extern,build,vscode-extension .`.
- [ ] Every external C library verified against its pinned SHA-256 before
      extraction — `python scripts/extern_digests.py --check` and
      `python extern_manifest.py --verify` (roadmap 9.1/9.4).
- [ ] TinyCC downloaded for the Windows artifact matches
      `pengu_tcc.TCC_RELEASE_SHA256` — `python pengu_tcc.py --stage
      build/tcc-dist` (roadmap 9.2/9.3).
- [ ] Packaging works and archives are reproducible — `python make_release.py`
      then `python make_release.py --archive-only --dist-dir pengucc_build
      --archive a.tar.gz` twice and `sha256sum a.tar.gz b.tar.gz` (roadmap 9.8).
- [ ] `pengu verify` passes on the project templates' dependency graphs —
      `python pengu_project.py verify --help` then `pengu verify` inside a
      `pengu new exe` template.
- [ ] The tag triggers the release and the release is verified — `workflow:
      .github/workflows/release.yml` (dispatch step) and `workflow:
      .github/workflows/release-verify.yml` (roadmap 9.6/9.7).
- [ ] Published artifacts run in both the portable and FHS layouts —
      `python scripts/verify_release_artifact.py --artifact <asset> --layout
      portable` and `--layout fhs` (roadmap 9.12).
- [ ] macOS artifact has a valid ad-hoc signature — `codesign --verify --strict
      pengu` (`workflow: .github/workflows/release.yml`). ❌ **Not notarized and
      not claimed to pass `spctl --assess`**: no Apple developer account exists
      (roadmap 9.9, `docs/RELEASE.md` §macOS).

## 2. Manual (author only — not agent work)

Every box below is an action, not a software claim; it has no gate by
construction and is marked `manual:`.

### Accounts and channels

- [ ] `manual:` Create the Discord server (`#general`, `#help`, `#showcase`,
      `#dev`) and link it from `README.md`.
- [ ] `manual:` Enable GitHub Discussions (Announcements, Q&A, Ideas, Showcase).
- [ ] `manual:` Publish the security contact from `SECURITY.md` (email alias
      live, advisories enabled).

### Release mechanics

- [ ] `manual:` Bump `VERSION` / `pengu_version.py` and move `CHANGELOG.md` out
      of `[Unreleased]` (the mechanical checks are `pytest tests/test_version.py
      -q` and `python scripts/release_version.py`).
- [ ] `manual:` Regenerate the stdlib version constants — `pytest
      tests/test_std_versioning.py -q` enforces the sync.
- [ ] `manual:` Tag `v1.0.0` and sign it — `git tag -s v1.0.0` (CI creates and
      pushes an unsigned tag when the changelog is promoted; a signed tag is a
      manual choice).
- [ ] `manual:` Build the release artifacts and publish checksums + GPG
      signature — see `SECURITY.md` §Release integrity.
- [ ] `manual:` Publish the GitHub release with the changelog excerpt.
- [ ] `manual:` Create `1.0.0-rc1` first if the tag has not been through a bake
      period.

### Announcements (only after the final release)

- [ ] `manual:` Update the `README.md` badge to `v1.0.0`.
- [ ] `manual:` Add a `SECURITY.md` link to the `README.md` header.
- [ ] `manual:` Post to r/ProgrammingLanguages, r/Zig, r/rust and the Discord.
- [ ] `manual:` Post to Hacker News (final release only).
- [ ] `manual:` Publish a short "what 1.0 means" note (what is guaranteed, what
      is not: see `BENCHMARKS.md` §Revised targets and `README.md` §What is not
      there yet).

## 3. Known limitations to state at release time

Being explicit here prevents over-promising:

- **Web playground / WASM**: out of scope for 1.0 (see `ROADMAP_1.0.0.md`
  §Fuera de scope para 1.0 for the technical justification).
- **Performance vs C**: 2.9×–7.3× depending on the workload; 1.8× on call-heavy
  code with `-DPENGU_FRAME_TRACE=0` (`BENCHMARKS.md`).
- **Binary size**: ~100 KiB for the benchmark programs, not the 65 KB once
  targeted.
- **`pengu run` cache hit**: above the 0.08 s target (Python startup dominates).
- **Full `Result` stdlib migration**: additive only so far (`std.archivum`);
  `precis`/`cipher` and the rest are still pending.
- **Complete dependency backtracking**: resolution is forward-only.
- **Standard library docs**: covered by a ratchet, not at 100%.
- **macOS notarization**: not performed; the artifact is ad-hoc signed and
  Gatekeeper will require `xattr -d com.apple.quarantine` (`docs/RELEASE.md`
  §macOS).
- **Reproducibility**: the archives are byte-reproducible; the PyInstaller
  binary is not certified reproducible across machines
  (`AUDIT_1.0_FASE9.md` item 9.8).
