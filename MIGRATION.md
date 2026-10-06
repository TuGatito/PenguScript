# Migrating a PenguScript project between versions

This guide tells you what to change when you move a project from one PenguScript
release to another, and how to verify the move. It is deliberately short: the
language has exactly **one** breaking change in its history so far, and it landed
in `0.10.0`.

> **Current version: 0.16.0** (read from [`VERSION`](VERSION)). See
> [`CHANGELOG.md`](CHANGELOG.md) for the full history and
> [`LANGUAGE.md` §23](LANGUAGE.md) for the stability policy that governs it.

## 1. The stability contract

- **Additive changes ship in minor releases.** New modules, new `weave`s, new
  optional parameters and new diagnostics do not require a migration.
- **Removals and signature changes require a major release**, and a symbol must
  first be deprecated for **two releases** (`LANGUAGE.md` §23.3). Deprecated
  symbols emit `W0006`; `pengu build --deny-deprecated` turns that into an error,
  which is the recommended gate for a project that is about to upgrade.
- Every `@deprecated` symbol in the standard library, with its replacement and
  its retirement version, is listed in [`docs/DEPRECATIONS.md`](docs/DEPRECATIONS.md).
  That table is cross-checked against the sources by
  `tests/test_std_deprecations_doc.py`, so it cannot silently go stale.

## 2. Breaking changes by version

| Version | Breaking change | Action |
|---|---|---|
| `0.10.0` | `and` stops being a list separator next to expressions | replace it with `,` — see §3 |
| `0.11.0` – `0.16.0` | **none** | nothing to do |

There are no other breaking entries in the changelog. If you find one that is not
in this table, that is a documentation bug — see §6.

## 3. `0.10.0`: `and` → `,` in expression lists

`and` (and `or`) used to separate elements wherever a comma was allowed. Since
`0.10.0` they are the boolean operators, so the separator role was removed from
`arg_list`, `param_list`, `struct_init`, `array_lit`, `map_lit` and `indent_row`.

| Before | After |
|---|---|
| `calling f with 1 and 2` | `calling f with 1, 2` |
| `weave g with x as int and y as int` | `weave g with x as int, y as int` |
| `declare d with a as int and b as int` | `declare d with a as int, b as int` |
| `with x is 1 and y is 2` | `with x is 1, y is 2` |
| `1 and 2 and 3` (indented row) | `1, 2, 3` |

**`and` is still correct as a boolean operator, and still a separator in pure
name/type lists.** Both of these keep working and should *not* be rewritten:

```pengu
# boolean conjunction — correct, leave it alone
let ok is a and b

# pure name/type lists — 'and' is still accepted ('shard T and U')
rune Box shard T and U:
    first as T
    second as U
```

The compiler reports the two cases differently, which is what makes the migration
safe to do by hand:

| Code | Case | Message |
|---|---|---|
| `E0000` | a list where no expression can follow | `'and' is no longer a separator: use ','` |
| `E0005` | ambiguous after a call with arguments | `Ambiguous 'and' after a call with arguments` |

So: if you see `E0000 … use ','`, rewrite that `and` as a comma. If you see
`E0005 Ambiguous 'and'`, decide whether you meant a conjunction or a separator —
the compiler cannot know, and neither can an automated rewriter.

## 4. Verifying an upgrade

```bash
pengu check                 # 0 errors and no new warnings
pengu test                  # the project's own test blocks still pass
pengu build --deny-deprecated   # no deprecated symbol is still in use
pengu fmt --check src/      # formatting is unchanged (exit 1 if it would change)
pengu build --locked        # the dependency lockfile is still satisfied
```

`pengu build --frozen` is the CI form: it refuses to update `pengu.lock` at all,
so a dependency that moved cannot slip in unnoticed.

## 5. `pengu migrate` (not yet available)

An automated rewriter — `pengu migrate --from <v> --to <v>` — is **not** part of
1.0. It is deferred to 1.1 (roadmap item 4.14b) for a measured reason: the only
candidate rewrite is the `and` separator above, and the ambiguous `E0005` case
cannot be resolved without full type information, while a *safe* rewriter has no
corpus to be validated against (`tests/migration/` does not exist). Shipping a
rewriter that silently turns a boolean conjunction into a comma would be worse
than no rewriter.

This document is the input that item needs. When `pengu migrate` lands, each
section above becomes one rule it applies, and the table in §2 becomes its
supported version range.

## 6. Reporting a migration problem

If an upgrade breaks code in a way this guide does not describe, that is a
documentation bug: open an issue with the failing snippet and the release you came
from. A breaking change that is not in §2 means the changelog and this guide have
diverged — `tests/test_migration_doc.py` exists to catch exactly that, and it is
cheaper to fix it here than in your project.
