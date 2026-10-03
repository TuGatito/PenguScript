# Release Checklist — PenguScript 1.0.0

Two lists: what the **toolchain** must prove (automatable, mostly already gated in
CI) and what the **author** must do by hand (accounts, announcements). Keeping
them apart stops "publish to Hacker News" from being mistaken for a release
blocker.

## 1. Automated (CI must be green)

Every item below has a gate in `.github/workflows/ci.yml`; run `pytest tests` and
the gates locally before tagging.

- [ ] Full suite green on Linux, macOS and Windows (gcc/clang, MSVC, MinGW).
- [ ] `python -m pytest tests -q` — 0 failures.
- [ ] Strict grammar gate: Lark parses the corpus with `strict=True`, no LALR
      conflicts.
- [ ] C99 portability gate (`--strict-c99`) and ABI layout matrix.
- [ ] FASE 2 gate: `_Static_assert(PENGU_ABI_VERSION)` present in `bundle.c`.
- [ ] FASE 3 tooling gate (bind, assets, JSON diagnostics, LSP semantics, fmt,
      docs, cross-compilation).
- [ ] FASE 4 ecosystem gate (SemVer, lockfile, transitive deps, remove/upgrade,
      vendor/cache, TOML, templates, stdlib versioning).
- [ ] FASE 5 safety gate (bugs, bounds policy, overflow policy, deprecation,
      supply chain, runtime hardening, fuzz harnesses).
- [ ] `pengu fmt --check std/` reports 0 files to reformat.
- [ ] `python scripts/smoke.py` passes.
- [ ] Nightly fuzz job: 72 h without a crash on any harness
      (`.github/workflows/fuzz.yml`, budget configurable).
- [ ] Nightly benchmark job uploads a CSV (`.github/workflows/bench.yml`) —
      informational, never blocking.
- [ ] `python scripts/bench.sh --repeat 5` reproduced and `BENCHMARKS.md`
      refreshed with the release machine's numbers.
- [ ] ASan/UBSan matrix: no leaks and no undefined behaviour
      (`-fsanitize=address,undefined`).
- [ ] `pengu verify` passes on the project templates' dependency graphs.

## 2. Manual (author only — not agent work)

### Accounts and channels

- [ ] Create the Discord server (`#general`, `#help`, `#showcase`, `#dev`) and
      link it from `README.md`.
- [ ] Enable GitHub Discussions (Announcements, Q&A, Ideas, Showcase).
- [ ] Publish the security contact from `SECURITY.md` (email alias live,
      advisories enabled).

### Release mechanics

- [ ] Bump `VERSION` / `pengu_version.py` and move `CHANGELOG.md` out of
      `[Unreleased]`.
- [ ] Regenerate the stdlib version constants (`tests/test_std_versioning.py`
      enforces the sync).
- [ ] Tag `v1.0.0` and sign it (`git tag -s`).
- [ ] Build release artifacts and publish checksums + GPG signature
      (see `SECURITY.md` §Release integrity).
- [ ] Publish the GitHub release with the changelog excerpt.
- [ ] Create `1.0.0-rc1` first if the tag has not been through a bake period.

### Announcements (only after the final release)

- [ ] Update the `README.md` badge to `v1.0.0`.
- [ ] Add a `SECURITY.md` link to the `README.md` header.
- [ ] Post to r/ProgrammingLanguages, r/Zig, r/rust and the Discord.
- [ ] Post to Hacker News (final release only).
- [ ] Publish a short "what 1.0 means" note (what is guaranteed, what is not:
      see `BENCHMARKS.md` §Revised targets and `README.md` §What is not there yet).

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
