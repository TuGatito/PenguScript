# Migrating a PenguScript project between versions

This guide tells you what to change when you move a project from one PenguScript
release to another, and how to verify the move. It is deliberately short: the
language has exactly **two** breaking changes in its history, and they landed in
`0.10.0` and `1.0.0`.

> **Current version: 1.0.0** (read from [`VERSION`](VERSION)). See
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
| `1.0.0` | the implicit ownership model is removed; memory is manual | delete `borrowed`, add explicit `banish`/`defer banish` — see §4 |

There are no other breaking entries in the changelog. If you find one that is not
in this table, that is a documentation bug — see §7.

Every row here has an executable counterpart in
[`tests/migration/`](tests/migration/README.md) (`EXPECTED.json`), which runs the
before-form and asserts it fails with the documented code; the current surface is
pinned separately by [`tests/compliance/`](tests/compliance/README.md).

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

## 4. `1.0.0`: from implicit ownership to manual memory

Until `0.16.0` the compiler tried to own memory for you: a local created from a
fresh expression was released at the end of its scope ("auto-banish"), a
`borrowed` binding opted out of that, escape analysis decided which locals could
live on the stack, and storing a value into a container or a struct field
deep-copied its heap payload.

All of that is gone. `1.0.0` keeps `banish`, `defer banish`, `errdefer`,
`ref to T`, `sigil of x`, `frozen` and `derive`, and removes everything the
compiler used to infer. The migration is mechanical once you know the four rules:

### 4.1 Delete every `borrowed`

`borrowed` no longer parses. A binding is simply a binding; what it *points at*
is now your business, exactly as with a C pointer.

| Before | After |
|---|---|
| `var borrowed v is src` | `let v is src` |
| `let borrowed v is src` | `let v is src` |
| `var borrowed x as int is 5` | `var x as int is 5` |

`var borrowed x is 1` now fails with `E0000` (a syntax error): the parser reads
`borrowed` as an ordinary name and then does not expect `x`.

### 4.2 Add the release you used to get for free

Nothing is released at scope exit any more, so any value you allocate and do not
return must be released explicitly. `defer banish` is the direct replacement for
the old auto-banish and keeps the LIFO ordering:

```pengu
weave main into int:
    var s is "hello {name}"     # owns a heap buffer
    defer banish s              # released when the scope exits
    calling print with s
    return 0
```

Releasing is a no-op on a string literal or any other non-owning view
(`PenguString.is_owned == 0`), so `defer banish s` is safe even when `s` might be
a literal.

### 4.3 Stop relying on copies on store

`list.push` and `map.put` `memcpy` the element; assigning to a rune field
`memcpy`s the field. Nothing clones a heap payload. Code that used to rely on the
copy now aliases the same buffer, so pick one of:

* release the container's elements by hand before releasing the container:

  ```pengu
  var i as int is 0
  while i < calling xs.len:
      banish (xs at i)        # release the element in place
      set i is i + 1
  banish xs                   # then the container's own buffer
  ```

* or keep the source alive and release it exactly once, through whichever of the
  two names you prefer. Releasing both is a double free.

`banish` on a container frees **only** the container's own buffer (`pengu_list`),
or its key/value blocks and entry table (`pengu_map`). It never touches the
elements.

### 4.4 Stop expecting an inferred destructor

A rune with a `string` or `list` field used to get a destructor for free. Now it
only gets one if you ask:

| Before | After |
|---|---|
| `rune Doc:` … `title as string` | `rune Doc derive Nexus:` … `title as string` |

With `derive Nexus`, `banish doc` runs the generated destructor and releases the
fields; without it, `banish doc` is `E0008` and you release the fields yourself
(`banish doc.title`). `derive Imago` is the matching opt-in for a deep copy.

### 4.5 Rebuild anything that was precompiled

The runtime ABI moved to **v2**: `PenguList` is 24 bytes (was 40) and `PenguMap`
32 (was 64), because the element cleanup/clone callbacks were removed. A
prebuilt `libpengu_runtime.a` will fail loudly — the generated bundle carries
`_Static_assert(PENGU_ABI_VERSION == 2, …)` and references `pengu_abi_version()`
— so rebuild the runtime (`python build_runtime.py`).

### 4.6 What did *not* change

`frozen` is still C's `const` (`E0006` when you write through it). `let` is still
immutability, not ownership. `banish` on a literal or temporary is still `E0008`.
Returning a `slice of` a stack array is still `E0051`. `some`/`ok`/`err` still
allocate a box for the payload — they just store its bytes instead of cloning it.

## 5. Verifying an upgrade

```bash
pengu check                 # 0 errors and no new warnings
pengu test                  # the project's own test blocks still pass
pengu build --deny-deprecated   # no deprecated symbol is still in use
pengu fmt --check src/      # formatting is unchanged (exit 1 if it would change)
pengu build --locked        # the dependency lockfile is still satisfied
```

`pengu build --frozen` is the CI form: it refuses to update `pengu.lock` at all,
so a dependency that moved cannot slip in unnoticed.

## 6. `pengu migrate` (not yet available)

An automated rewriter — `pengu migrate --from <v> --to <v>` — is **not** part of
1.0. It is deferred to 1.1 (roadmap item 4.14b) for a measured reason: the only
candidate rewrite is the `and` separator above, and the ambiguous `E0005` case
cannot be resolved without full type information. Shipping a rewriter that
silently turns a boolean conjunction into a comma would be worse than no
rewriter.

What it *did* need is now in the tree: [`tests/migration/`](tests/migration/README.md)
holds one program per published version line with the outcome this guide
documents for it (`EXPECTED.json`), so a rewriter can be validated the day it is
written, and [`tests/compliance/`](tests/compliance/README.md) holds the
canonical program per section of `LANGUAGE.md`. Both are normative for
compatibility: a change that breaks one of them needs a MAJOR release and an
entry in §2 of this guide, not a quiet edit to the corpus.

Each section above becomes one rule `pengu migrate` applies, and the table in §2
becomes its supported version range.

## 7. Reporting a migration problem

If an upgrade breaks code in a way this guide does not describe, that is a
documentation bug: open an issue with the failing snippet and the release you came
from. A breaking change that is not in §2 means the changelog and this guide have
diverged — `tests/test_migration_doc.py` exists to catch exactly that, and it is
cheaper to fix it here than in your project.
