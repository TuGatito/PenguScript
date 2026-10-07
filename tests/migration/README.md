# Migration corpus

> **This corpus defines the compatibility of PenguScript 1.x**, together with
> [`../compliance/README.md`](../compliance/README.md). The compliance corpus pins
> the language as it is **today**; this one pins the syntax of every version the
> project has **published**, so a future breaking change cannot land without an
> example of what it breaks and the migration step it needs.

The 1.0 roadmap (Phase 8, item 8.5). One program per published version **line**
from `0.10.0` on, written in that version's syntax, with the outcome
`MIGRATION.md` documents for it in `EXPECTED.json`.

## What it is for

Not as a regression suite for the current language — the project's stability
contract (`MIGRATION.md` §1) is that only `0.10.0` ever broke anything — but as
the input the deferred `pengu migrate` rewriter (roadmap 4.14b) will be validated
against. Two programs are therefore *expected to fail*: they are the pre-`0.10.0`
`and`-as-separator syntax, and the whole point is that the compiler refuses them
with the documented codes (`E0000`, `E0005`).

## Coverage and its boundary

`CHANGELOG.md` lists **36** published versions (`0.3.0` … `1.0.0`). Coverage here
is asserted per **minor line** from `0.10.0` and for every version that
`MIGRATION.md` §2 marks as breaking, because:

* `MIGRATION.md` — the normative migration table — starts at `0.10.0`;
* the project's stability contract forbids a patch release from introducing new
  surface syntax, so 14 near-identical `0.13.x` programs would be corpus theatre;
* the pre-`0.10.0` syntax is not documented in any current normative document, so
  "historical" programs for `0.3.0`–`0.9.1` could not be verified by anything.

The gap is recorded in `AUDIT_1.0_FASE8.md` (item 8.5) rather than filled with
programs nobody can check.

## Adding a program

1. Put it in `tests/migration/<version>/<name>.pengu` with a header comment naming
   the `MIGRATION.md` section it pins.
2. Add an entry to `EXPECTED.json`: `file`, `version`, `expects`
   (`ok` | `error`), `rc` (for `ok`) or `code` (for `error`), and `why`.
3. `python -m pytest tests/test_migration_corpus.py -q` — the coverage test fails
   if a documented breaking version has no failing program, and the
   file-vs-table test fails on an orphan in either direction.
