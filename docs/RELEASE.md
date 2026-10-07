# Releasing PenguScript

The process, the gates that must be green, and what to do when one fails.
[`RELEASE_CHECKLIST.md`](../RELEASE_CHECKLIST.md) is the short, tickable form of
this document; this one explains the mechanism behind each line. The pipeline is
four workflows:

| Workflow | Role |
|---|---|
| `ci.yml` | Builds, tests and packages on Linux/macOS/Windows; `auto-tag` creates the tag and **dispatches** the release |
| `release.yml` | The **only** publisher: builds the artifacts, writes `SHA256SUMS.txt`, creates the GitHub Release |
| `release-verify.yml` | Downloads the *published* artifacts and executes them in the portable and FHS layouts |
| `nightly.yml`, `fuzz.yml`, `bench.yml`, `sanitizers.yml`, `compliance.yml`, `cross-compile.yml`, `codeql.yml` | The quality gates CI runs on every push |

## 0. One-time setup (not per release)

* Nothing to configure for the tag→release handoff: `ci.yml` uses the
  repository's `GITHUB_TOKEN` to `workflow_dispatch` `release.yml`, which is
  explicitly allowed even though a `GITHUB_TOKEN` push is not (roadmap item 9.6).
  No PAT, no GitHub App.
* **No Apple developer account is used.** The macOS artifact is *ad-hoc* signed
  and **not notarized**; see §macOS below. Do not add a notarization claim to the
  notes.

## 1. Preconditions

All of these must be green on the commit you are about to tag. They are the same
gates `RELEASE_CHECKLIST.md` lists, so this section does not repeat them; it only
says where to look.

```bash
pytest tests -q                     # the whole suite, the same command CI runs
python make_release.py              # packages, smoke-tests and archives locally
python scripts/extern_digests.py --check    # every dependency still has a pinned digest
python scripts/release_version.py           # prints the tag the CHANGELOG implies
```

`python make_release.py` re-verifies every external archive against its pinned
SHA-256 before extracting it (set `PENGU_EXTERN_FAST=1` to reuse an already
verified `extern/` while iterating; never in CI).

## 2. Cut the release

1. **Promote the changelog.** Move the entries you are shipping out of
   `## [Unreleased] — …` into a `## [1.0.0] - YYYY-MM-DD` section.
   `scripts/release_version.py` takes the *first* released heading and skips
   `[Unreleased]`; `ci.yml` and `release.yml` both call it, so they cannot
   disagree. If only `[Unreleased]` exists the script exits non-zero and the tag
   job fails (by design: it used to push `vUnreleased`).
2. **Bump the version.** `VERSION` is the single source of truth;
   `pengu_version.FALLBACK_VERSION` and the frozen bundle follow it.
   `` `pytest tests/test_version.py -q` `` is the gate.
3. **Merge to `main`.** `ci.yml` runs; if everything is green the `auto-tag` job
   creates `v<version>` (annotated), pushes it, and — only when *it* created the
   tag — dispatches `release.yml` with `version=v<version>`.
4. **`release.yml` publishes.** It checks out the tag, builds the three
   archives, verifies the changelog matches the tag, collects at least three
   assets, writes `SHA256SUMS.txt` and runs
   `gh release create --verify-tag`. Nothing else in the repository may publish a
   release.
5. **`release.yml` dispatches `release-verify.yml`** for the tag it just
   published (`release` events created with `GITHUB_TOKEN` do not start a run
   either).

## 3. What each gate proves

| Gate | Command / workflow | Proves |
|---|---|---|
| Test suite | `pytest tests -q` | no regressions |
| Packaging | `python make_release.py` | the frozen binary builds and smoke-tests on this machine |
| Dependency integrity | `python scripts/extern_digests.py --check`, `python extern_manifest.py --verify` | every archive hashes to the pinned SHA-256 before extraction |
| TCC integrity | `python pengu_tcc.py --stage build/tcc-dist` | the downloaded compiler matches `pengu_tcc.TCC_RELEASE_SHA256` |
| Reproducibility | `python make_release.py --archive-only --dist-dir pengucc_build --archive a.tar.gz` (twice) | the same tree produces the same archive bytes |
| Artifact execution | `workflow: .github/workflows/release-verify.yml` | the published artifact runs: `pengu -V` matches the tag, a project builds, `run` prints the greeting |
| Layouts | `workflow: .github/workflows/release-verify.yml` (`layout: portable` and `layout: fhs`) | `pengu_paths` finds the runtime from the unpacked dir and from an installed FHS prefix |
| macOS signature | `codesign --verify --strict` (in `release.yml`) | the artifact carries a valid ad-hoc signature |

### Reproducibility

`make_release.py` pins `SOURCE_DATE_EPOCH` (from the environment, else the commit
time of `HEAD`), exports `PYTHONHASHSEED=0` and writes the archives itself with
sorted entries, a constant mtime and normalized uid/gid and permissions. `tar -czf` and
`Compress-Archive` are no longer used: they embedded the build time.

```bash
python make_release.py --archive-only --dist-dir pengucc_build --archive a.tar.gz
python make_release.py --archive-only --dist-dir pengucc_build --archive b.tar.gz
sha256sum a.tar.gz b.tar.gz        # identical
```

What is *not* claimed: the PyInstaller binary itself is not certified
byte-reproducible across machines. The measurement and its cause are recorded in
`AUDIT_1.0_FASE9.md` item 9.8.

Also **not** claimed, and measured in Phase 11 (F11-N9): two independent builds of
the same commit do not produce an identical distribution *tree*. Of the 229 files
`--print-hashes` lists for the 1.0.0 portable layout, 227 matched run to run; the
two that did not are `pengus-<version>.vsix` (a zip, whose entry times `vsce`
writes) and `runtime/include/pengu_runtime.h.gch` (a gcc precompiled header).
Everything derived from the sources — the frozen compiler, the runtime archives,
`std/`, `VERSION` — matched. Closing those two is roadmap 1.1 candidate X.

## 4. Verify by hand (optional, 2 minutes)

```bash
gh release download v1.0.0 --pattern 'pengu-linux-x64.tar.gz'
tar xzf pengu-linux-x64.tar.gz
./pengu -V                 # 1.0.0
./pengu run hello.pengu    # Hello, world!
```

That is exactly what `release-verify.yml` automates.

## 5. If a gate fails

| Failure | What it means | What to do |
|---|---|---|
| `release_version.py` exits non-zero | only `[Unreleased]` sections exist | promote the changelog, then push again |
| `auto-tag` fails to push the tag | branch protection or a permissions change | check `permissions: contents: write` on the job; the tag must be pushed by CI or by hand |
| `release.yml` fails before publishing | a build or a test failed | nothing was published; fix and re-run the workflow (`workflow_dispatch` with an existing tag) |
| `gh release create` fails with "already exists" | that tag was published before | delete the release (`gh release delete <tag>`) or publish the next version |
| **`release-verify.yml` fails** | an artifact is published but does not run | **withdraw the release**: `gh release delete <tag> --yes`, `git push --delete origin <tag>`, fix, and re-tag. The verification exists precisely so this decision is not made blind |
| A digest mismatch (extern or TCC) | upstream changed, or a mirror is compromised | stop. Verify the new archive by hand, then re-pin with `python scripts/extern_digests.py --update` (extern) or a code change (TCC) in its own commit |

## 6. macOS

**Notarization is not performed and is not claimed.** There is no Apple
developer account, so there is no `notarytool` step; `release.yml` signs the
artifact *ad-hoc* (`codesign --sign - --force`) and gates on
`codesign --verify --strict`, which is the strongest property available without
an account.

Consequence, stated plainly: a `pengu` downloaded through a browser carries the
`com.apple.quarantine` attribute and Gatekeeper refuses to run it, because an
ad-hoc signature cannot satisfy notarization. `release-verify.yml` runs
`spctl --assess -vv` and publishes the output for the record; a rejection there is
expected and documented, not a bug.

Supported paths for macOS users:

```bash
xattr -d com.apple.quarantine pengu     # explicit override, after verifying SHA256SUMS.txt
```

or build from source (see `docs/PENGU_BUILD.md`), which is not quarantined.

If an Apple developer account ever becomes available, the change is local: add
`codesign --sign "Developer ID Application: …" --options runtime --timestamp`,
a `notarytool submit --wait` step and `xcrun stapler staple`, then promote the
`spctl` check in `release-verify.yml` from "recorded" to "required".

## 7. After the release

Announcements and channel upkeep live in
[`RELEASE_CHECKLIST.md`](../RELEASE_CHECKLIST.md) §2: they are human work, not
software claims, and are not gates.
