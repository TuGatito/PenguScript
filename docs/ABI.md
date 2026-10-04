# PenguScript Runtime ABI

> The versioning policy for `PENGU_ABI_VERSION`. The canonical layout table lives
> in [`../pengu_runtime.h`](../pengu_runtime.h) (`ABI v1 — frozen at PenguScript
> 0.16.0`), which is the normative artifact; this document defines *when the
> number moves*, the header defines *what the number currently means*.

## What it is

`PENGU_ABI_VERSION` (currently **1**) is the version of the **binary layout of the
runtime containers** shared between two separately compiled artifacts:

1. the C bundle that `pengu_codegen.py` emits for a program (`bundle.c`), and
2. a prebuilt `build/lib/libpengu_runtime.a` compiled at some earlier point.

The version covers the structs the generated code embeds *by value* or indexes by
field, and the signatures of every exported `pengu_*` function the bundle calls:

| Struct | Role |
|---|---|
| `PenguString` | owned/borrowed string (`data`, `len`, `is_owned`) |
| `PenguSlice` | typed view (`data`, `len`, `elem_size`) |
| `PenguList` | growable list (+ `elem_cleanup` / `elem_clone`) |
| `PenguMap` | hash map (+ key/value sizes, cleanup and clone hooks) |
| `PenguMaybe` | optional (`is_present`, `value`) |
| `PenguResult` | fallible result (`is_ok`, `ok_val`, `err_val`) |
| `PenguRange` | `start` / `end` iteration pair |

The generated bundle and the archive must therefore be built against the **same**
`pengu_runtime.h`. If they are not, a mismatch does not fail loudly on its own: the
bundle reinterprets struct fields at the wrong offsets and corrupts memory far from
the real cause. Version pinning exists to turn that silent corruption into a build
error.

## What bumps the version

- Adding, removing, or reordering **any field** of the structs above.
- Adding a field **even at the end** of a struct: that changes `sizeof`, so an
  array of the struct is laid out differently and a bundle compiled against v1
  would write out of bounds against an older archive.
- Changing the **type or width** of a field, or its alignment.
- Changing the **signature of any exported `pengu_*` function** — parameters,
  return type, or calling convention (this includes changing a macro that
  generates those signatures).
- Changing the value or the meaning of an enum/flag constant that the bundle
  passes to an exported function.

## What does *not* bump the version

- **Adding new functions** to the runtime. Old bundles never reference them, so
  the old and new archives remain interchangeable in that direction.
- Changing the **body** of an existing function without touching its signature.
- Changes confined to `pengu_parser/pengu_runtime.c` that do not alter anything
  declared in `pengu_runtime.h`.
- Changes in the **codegen** that do not emit new runtime symbols or change how
  existing symbols are called.
- Documentation, comments, diagnostics, or added `@note`s.

Changing a struct is a two-step operation: bump `PENGU_ABI_VERSION` in
`pengu_runtime.h`, bump `PENGU_EXPECTED_ABI_VERSION` in
`pengu_parser/pengu_codegen.py`, and update the size/offset table in the header
plus `tests/abi/test_abi_layout.c`.

## How it is verified

There are two complementary checks, and neither is sufficient alone.

### 1. Compile time — bundle against header

The generated bundle carries an assertion against the `pengu_runtime.h` it was
generated next to:

```c
_Static_assert(PENGU_ABI_VERSION == 1,
               "pengu_runtime.h ABI mismatch: bundle expects v1");
```

This catches a bundle produced by a codegen that expects one version being built
against a header that declares another. It says nothing about the archive,
because it never looks at it.

### 2. Link time — bundle against archive

The runtime exports the version as a real object-file symbol:

```c
/* pengu_parser/pengu_runtime.c */
int pengu_abi_version(void) { return PENGU_ABI_VERSION; }
```

`pengu_runtime.c` is the only translation unit inside
`build/lib/libpengu_runtime.a`, so the symbol exists **only** in the archive —
not in the header, and not inline in the bundle. Any link that references it
therefore fails with `undefined reference to pengu_abi_version` when handed an
archive that predates it, instead of silently reinterpreting struct fields at the
wrong offsets.

The verification is:

```bash
# the archive really exports it
nm build/lib/libpengu_runtime.a | grep pengu_abi_version
# → T pengu_abi_version

# the exported value agrees with the header
python -m pytest tests/test_abi_version.py -q
```

`tests/test_abi_version.py` measures the archive with `nm`, links and runs a C
harness that compares the symbol's value against `PENGU_ABI_VERSION`, and checks
that a consumer referencing the symbol cannot link against a simulated pre-3.5
archive.

### What is *not* enforced (yet)

The generated bundle does **not** reference `pengu_abi_version()` on its own. It
did in an earlier revision of this item, which made the reference mandatory for
every bundle — but the CLI only adds `-lpengu_runtime` when the project asks for
it (`pengu.toml` `links`), and a fresh `pengu init` project builds header-only
with no archive at all. The unconditional reference therefore broke `pengu build`
on every fresh project with `undefined reference to pengu_abi_version`.

So today the link-time check fires for any consumer that *does* link the archive
and references the symbol — including the test harness and any program using
runtime facilities — but it is not automatically forced by codegen. Making the
reference mandatory requires the CLI to link `libpengu_runtime.a` unconditionally,
which is Phase 4 work in `pengu_project.py`. Until then, treat `pengu_abi_version()`
as the *available* verification hook rather than an automatic gate.

## See also

- [`../SECURITY.md`](../SECURITY.md) — "Runtime ABI pinning" in the security model.
- [`../pengu_runtime.h`](../pengu_runtime.h) — the authoritative layout table.
- [`../tests/abi/test_abi_layout.c`](../tests/abi/test_abi_layout.c) — the
  `sizeof`/`offsetof` gate.
- [`../tests/test_abi_version.py`](../tests/test_abi_version.py) — the
  symbol/version gate.
