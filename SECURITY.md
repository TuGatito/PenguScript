# Security Policy

PenguScript compiles and links third-party code by design (C bindings via
`pengu bind`, dependencies via `pengu add`), so the project takes supply-chain
and memory-safety reports seriously. This document states what is covered, how
to report a problem, and what to expect afterwards.

## Supported versions

| Version | Supported |
|---|---|
| `1.x` (from `1.0.0`) | ✅ security fixes |
| `0.16.x` | ⛔ end of support — superseded by `1.0.0` |
| `< 0.16` | ❌ |

## Scope

In scope:

- **Compiler front end** — lexer, LALR parser, checker, type inference.
- **Code generator** — emitted C (`bundle.c`) and the runtime header.
- **Runtime** — `pengu_runtime.h` and the prebuilt `libpengu_*.a` archives.
- **Toolchain** — `pengu bind`, `pengu add`, `pengu lock`/`pengu verify`,
  `pengu vendor`, the dependency resolver and the language server.
- **Build-time execution** — anything PenguScript runs on your behalf
  (`gcc -E` for bindings, dependency `build.py`/`build.sh`/`Makefile`).

Out of scope:

- Vulnerabilities in vendored third-party C libraries themselves (report them
  upstream; we will track the bump).
- Denial of service from compiling a malicious *program* with a trusted
  toolchain (compilers are not sandboxes for the code they compile).
- Issues that require an already-compromised machine or a malicious user with
  write access to your project.

## Reporting a vulnerability

**Do not open a public issue.** Use either channel:

1. **GitHub Security Advisories** — *Security* tab → *Report a vulnerability*
   (preferred: gives us a private fork to prepare the fix).
2. **Email** — `security@penguscript.dev` with the subject `[SECURITY]`.

Include: affected version (`pengu version`), platform/toolchain, a minimal
reproducer (a `.pengu` file or a header + the exact command), and the impact you
believe it has. ❌ **PGP-encrypted reports are not offered yet**: no release key
exists, so there is no fingerprint to encrypt to (see §Release integrity). Until
one is published, use the two channels above.

## Disclosure timeline

- **Acknowledgement** within **72 hours**.
- **Triage and severity** (CVSS 3.1) within **7 days**.
- **Embargo**: up to **90 days** from acknowledgement, or until a fix is
  released — whichever comes first. We will credit you unless you ask otherwise.
- **Coordinated disclosure**: we publish a GitHub Security Advisory and a
  `CHANGELOG.md` entry with the fix.

## Patch SLAs

| Severity | Fix target |
|---|---|
| Critical (RCE, memory corruption in the runtime, code execution via a binding) | **7 days** |
| High (sandbox escape, supply-chain integrity bypass) | **30 days** |
| Medium / Low | **90 days** |

## Secure-by-default measures

PenguScript already ships several mitigations; reports that bypass them are
prioritised. Every one carries a gate — a test or a workflow that fails if the
mitigation is removed — because a security claim without one is decoration.
`tests/test_release_claims.py::test_every_secure_by_default_claim_names_a_gate`
enforces the last column.

| Mitigation | Gate |
|---|---|
| **Bounds checking is always on** in every profile; `unsafe:` blocks and `--release-unsafe` are explicit opt-outs (and `unsafe:` emits `W0007`). | `tests/runtime/test_bounds_policy.py` |
| **Integer overflow is defined**: `-ftrapv` in debug, `-fwrapv` in release; only `--release-unsafe` restores C's undefined behaviour. | `tests/runtime/test_overflow_policy.py` |
| **Runtime ABI pinning**: the generated bundle `_Static_assert`s `PENGU_ABI_VERSION` against the `pengu_runtime.h` it was generated next to, so a bundle and header that disagree fail at compile time instead of corrupting memory. The runtime additionally exports `pengu_abi_version()`, and every bundle references it — `pengu build` links `libpengu_runtime.a` unconditionally and `pengu_abi_version` is pinned with `__attribute__((used))` — so an archive built against a different ABI fails at link with `undefined reference to pengu_abi_version` instead of silently reinterpreting struct fields. The property is verified under **gcc** and **clang**; **tcc** writes stripped executables, so the symbol cannot be inspected there and no hard link failure is guaranteed — tcc is the development compiler, not a release one. See [`docs/ABI.md`](docs/ABI.md) for the exact scope. | `tests/runtime/test_abi_version.py`, `tests/runtime/test_abi_layout.py` |
| **Lockfile integrity**: `pengu.lock` records the exact commit and a SHA-256 of every dependency's content tree; `--locked`/`--frozen` verify it and `pengu verify` re-checks an existing checkout. | `tests/cli/test_lockfile.py` |
| **Dependency build scripts require trust**: `build.py`/`build.sh`/`Makefile` run only with `--trust`, `PENGU_TRUST_ALL=1`, or an interactive confirmation; otherwise they are skipped with a warning. | `tests/regression/test_phase5_bugfixes.py`, `tests/tooling/test_supply_chain.py` |
| **Binding preprocessor sandbox**: headers are treated as untrusted input. Absolute and directory-escaping `#include`s are refused, and on Linux the preprocessor runs under `bwrap` with only the toolchain and the needed directories visible, read-only and without network. `PENGU_NO_SANDBOX=1` / `PENGU_ALLOW_ABSOLUTE_INCLUDES=1` opt out (at your own risk). | `tests/tooling/test_supply_chain.py` |

## Release integrity

Every published artifact ships with a `SHA256SUMS.txt` produced by
[`.github/workflows/release.yml`](.github/workflows/release.yml) ("Collect assets
and write SHA256SUMS"), so a download can be verified without trusting TLS. The
macOS binary carries a **verified ad-hoc** signature (`codesign --verify
--strict`); it is **not** notarized and the project does **not** claim it passes
`spctl --assess` (there is no Apple developer account — `docs/RELEASE.md`
§macOS).

❌ **GPG signing of the release artifacts is not performed today, and is not
claimed here.** No release key exists and no fingerprint is published; producing
and publishing one is a `manual:` item in `RELEASE_CHECKLIST.md` §2. The earlier
revision of this document promised "signed" artifacts; that claim is withdrawn
rather than left unverifiable.
