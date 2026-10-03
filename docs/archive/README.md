# Archived documents

> **These documents are historical and NON-NORMATIVE.**

They record how PenguScript got to where it is: phase progress logs, readiness
snapshots and plans that have since shipped or been superseded. They are kept for
provenance — they explain *why* past decisions were made — but they describe the
project **as it was at the time of writing, not as it is now**.

Do **not** treat anything here as a statement about the current toolchain. In
particular, the version numbers, test counts, file paths and feature claims in
these documents have all drifted since they were written.

## For the current state, read instead

| Question | Read |
|---|---|
| What does the language do? | [`../../LANGUAGE.md`](../../LANGUAGE.md) |
| What is the syntax? | [`../../CHEATSHEET.md`](../../CHEATSHEET.md) |
| How should code be written? | [`../../PenguScriptGuideEnglish.md`](../../PenguScriptGuideEnglish.md) |
| What is the version and its history? | [`../../VERSION`](../../VERSION), [`../../CHANGELOG.md`](../../CHANGELOG.md) |
| What is left to do? | [`../../ROADMAP_2.0.md`](../../ROADMAP_2.0.md) |
| What was found broken, with evidence? | [`../../AUDIT_1.0.md`](../../AUDIT_1.0.md) |
| How is it built and released? | [`../PENGU_BUILD.md`](../PENGU_BUILD.md), [`../README_RELEASE.md`](../README_RELEASE.md) |

## Contents

| File | What it was | Superseded by |
|---|---|---|
| `AUDIT_RESPONSE.md` | The project's response to an earlier external audit | [`../../AUDIT_1.0.md`](../../AUDIT_1.0.md) |
| `PRODUCTION_READINESS.md` | A production-readiness snapshot for an earlier release | [`../../RELEASE_CHECKLIST.md`](../../RELEASE_CHECKLIST.md) |
| `P1_PROGRESS.md` | Progress log for phase P1 | `CHANGELOG.md` |
| `P2_PROGRESS.md` | Progress log for phase P2 | `CHANGELOG.md` |
| `CRITICALS_PROGRESS.md` | Tracker for the critical/optional findings of an earlier audit | [`../../AUDIT_1.0.md`](../../AUDIT_1.0.md) |
| `Plan.md` | An early development plan | [`../../ROADMAP_2.0.md`](../../ROADMAP_2.0.md) |
| `roadmap.md` | An early, short roadmap | [`../../ROADMAP_1.0.0.md`](../../ROADMAP_1.0.0.md), [`../../ROADMAP_2.0.md`](../../ROADMAP_2.0.md) |

## Why keep them instead of deleting

They preserve the reasoning behind decisions that are otherwise invisible in the
code — for example why certain syntax was removed, or which bugs were chased in
which order. Deleting them would destroy that `git`-visible context for no gain
beyond a shorter directory listing.
