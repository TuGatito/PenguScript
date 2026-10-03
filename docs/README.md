# PenguScript documentation index

This directory holds the **non-normative, supplementary** documentation: build and
release guides, performance and fuzzing methodology, and the archived process
documents from earlier phases.

> **Canonical sources live in the repository root.** For the language, the CLI and
> the standard library, read [`../LANGUAGE.md`](../LANGUAGE.md) and
> [`../CHEATSHEET.md`](../CHEATSHEET.md) first — those are normative.

## Live documents

| Document | What it covers | Regenerated? |
|---|---|---|
| [`PENGU_BUILD.md`](PENGU_BUILD.md) | Building the runtime and the external C dependencies; FHS vs portable layouts; the `pengu` project configuration surface | No — authored |
| [`README_RELEASE.md`](README_RELEASE.md) | The standalone `pengucc_build/` distribution: layout, install, uninstall, bundled TinyCC and PCH | **Yes** — written by `make_release.py` (`generate_release_readme`) |
| [`PERFORMANCE.md`](PERFORMANCE.md) | Performance methodology, measured numbers, cached-build behaviour, and the honestly-documented known leaks | No — authored |
| [`FUZZING.md`](FUZZING.md) | Fuzzing harnesses, corpora and run budgets | No — authored |

## Normative documents (repository root)

| Document | Why it is normative |
|---|---|
| [`../LANGUAGE.md`](../LANGUAGE.md) / [`../LANGUAGE_Spanish.md`](../LANGUAGE_Spanish.md) | The language reference: grammar, semantics, diagnostics catalogue, standard library |
| [`../CHEATSHEET.md`](../CHEATSHEET.md) | Full syntax and C-translation reference |
| [`../PenguScriptGuideEnglish.md`](../PenguScriptGuideEnglish.md) / [`../PenguScriptGuideSpanish.md`](../PenguScriptGuideSpanish.md) | The style guide that governs `std.*` and user modules |
| [`../README.md`](../README.md) | Project overview and entry point |
| [`../CHANGELOG.md`](../CHANGELOG.md) | Version history |
| [`../SECURITY.md`](../SECURITY.md) | Security model and reporting |
| [`../BENCHMARKS.md`](../BENCHMARKS.md) | Published benchmark results |
| [`../RELEASE_CHECKLIST.md`](../RELEASE_CHECKLIST.md) | The gates a release must pass |
| [`../ROADMAP_2.0.md`](../ROADMAP_2.0.md) | The live roadmap |
| [`../AUDIT_1.0.md`](../AUDIT_1.0.md) | The verified 1.0 audit that produced the roadmap |
| [`../CLEANUP_PLAN.md`](../CLEANUP_PLAN.md) | Repository cleanup plan |

## Archived documents

[`archive/`](archive/) holds historical, **non-normative** process documents from
earlier development phases (progress logs, readiness snapshots, superseded plans).
They are kept for provenance — they explain *why* past decisions were made — but
they describe the project as it was, **not as it is**. See
[`archive/README.md`](archive/README.md).

## Adding a document

1. If it describes **how to use the language**, it belongs in the root next to
   `LANGUAGE.md`.
2. If it describes **how to build, release, measure or fuzz**, it belongs here.
3. If it is a **progress log or a plan that has shipped**, it belongs in `archive/`.
