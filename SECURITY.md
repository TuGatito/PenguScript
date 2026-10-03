# Security Policy

PenguScript compiles and links third-party code by design (C bindings via
`pengu bind`, dependencies via `pengu add`), so the project takes supply-chain
and memory-safety reports seriously. This document states what is covered, how
to report a problem, and what to expect afterwards.

## Supported versions

| Version | Supported |
|---|---|
| `1.x` (from `1.0.0`) | ✅ security fixes |
| `0.16.x` | ✅ security fixes until `1.0.0` is released |
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
believe it has. PGP-encrypted reports are welcome; the release key fingerprint is
published with each signed release.

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
prioritised:

- **Bounds checking is always on** in every profile; `unsafe:` blocks and
  `--release-unsafe` are explicit opt-outs (and `unsafe:` emits `W0007`).
- **Integer overflow is defined**: `-ftrapv` in debug, `-fwrapv` in release;
  only `--release-unsafe` restores C's undefined behaviour.
- **Runtime ABI pinning**: the generated bundle `_Static_assert`s
  `PENGU_ABI_VERSION`, so a stale `libpengu_runtime.a` fails at compile time
  instead of corrupting memory.
- **Lockfile integrity**: `pengu.lock` records the exact commit and a SHA-256 of
  every dependency's content tree; `--locked`/`--frozen` verify it and
  `pengu verify` re-checks an existing checkout.
- **Dependency build scripts require trust**: `build.py`/`build.sh`/`Makefile`
  run only with `--trust`, `PENGU_TRUST_ALL=1`, or an interactive confirmation;
  otherwise they are skipped with a warning.
- **Binding preprocessor sandbox**: headers are treated as untrusted input.
  Absolute and directory-escaping `#include`s are refused, and on Linux the
  preprocessor runs under `bwrap` with only the toolchain and the needed
  directories visible, read-only and without network.
  `PENGU_NO_SANDBOX=1` / `PENGU_ALLOW_ABSOLUTE_INCLUDES=1` opt out (at your own
  risk).

## Release integrity

From `1.0.0`, release artifacts are signed and ship with checksums; the
signature and the expected digests are published in the release notes.
