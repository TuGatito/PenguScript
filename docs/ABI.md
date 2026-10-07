# PenguScript Runtime ABI

> The versioning policy for `PENGU_ABI_VERSION`. The canonical layout table lives
> in [`../pengu_runtime.h`](../pengu_runtime.h) (`ABI v2 — frozen at PenguScript
> 1.0.0`), which is the normative artifact; this document defines *when the
> number moves*, the header defines *what the number currently means*.

## What it is

`PENGU_ABI_VERSION` (currently **2**) is the version of the **binary layout of the
runtime containers** shared between two separately compiled artifacts:

1. the C bundle that the `pengu_codegen` package emits for a program (`bundle.c`), and
2. a prebuilt `build/lib/libpengu_runtime.a` compiled at some earlier point.

The version covers the structs the generated code embeds *by value* or indexes by
field, and the signatures of every exported `pengu_*` function the bundle calls:

| Struct | Role |
|---|---|
| `PenguString` | string buffer (`data`, `len`, `is_owned`); `is_owned == 1` marks a heap buffer you can `banish`, `0` a literal or non-owning view |
| `PenguSlice` | typed view (`data`, `len`, `elem_size`) |
| `PenguList` | growable list, **24 bytes**: `data`=0 `len`=8 `cap`=12 `elem_size`=16 (no element callbacks) |
| `PenguMap` | hash map, **32 bytes**: `entries`=0 `len`=8 `cap`=12 `key_size`=16 `val_size`=24 (no cleanup/clone hooks) |
| `PenguMaybe` | optional (`is_present`, `value`) |
| `PenguResult` | fallible result (`is_ok`, `ok_val`, `err_val`) |
| `PenguRange` | `start` / `end` iteration pair |

**v2 (manual memory management):** `PenguList` and `PenguMap` dropped their element
cleanup/clone callbacks, shrinking from 40 to 24 bytes and from 64 to 32 bytes
respectively. Storing an element is now always a `memcpy` and releasing a container
frees only the container's own buffer — see LANGUAGE.md §13.5. Every v1 bundle that
embedded the old structs by value must be recompiled.

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
`pengu_parser/pengu_codegen/_base.py`, and update the size/offset table in the header
plus `tests/abi/test_abi_layout.c`.

## How it is verified

There are two complementary checks, and neither is sufficient alone.

### 1. Compile time — bundle against header

The generated bundle carries an assertion against the `pengu_runtime.h` it was
generated next to:

```c
_Static_assert(PENGU_ABI_VERSION == 2,
               "pengu_runtime.h ABI mismatch: bundle expects v2");
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

### The reference is forced by codegen

Every generated bundle carries a pin, so the archive cannot be dropped by the
linker and a stale `libpengu_runtime.a` fails at link time:

```c
/* emitted once per bundle by pengu_parser/pengu_codegen/bundle.py */
extern int pengu_abi_version(void);
#if defined(__GNUC__) || defined(__clang__)
__attribute__((used))
#endif
static int (*const _pengu_abi_pin)(void) = pengu_abi_version;
```

`pengu build` also links `libpengu_runtime.a` unconditionally (item 4.17),
whether or not `pengu.toml` lists it. Measured end to end:

```bash
$ pengu init ok && cd ok && pengu build
$ nm build/ok | grep pengu_abi_version
0000000000000a10 T pengu_abi_version          # debug and release (survives -O2/-O3)

# an archive built without the symbol makes the link fail, naming it
$ pengu build
/usr/bin/ld: build/bundle.c:10:(.data.rel.ro+0x0): referencia a `pengu_abi_version' sin definir
```

Without the pin, adding `-lpengu_runtime` is a no-op: the archive has no
referenced symbols, so the linker drops it. Measured before the pin landed:
`nm build/ok | grep -c ' T pengu_'` → `0` with the flag on the command line.

#### Compiler scope of the guarantee

The "a stale `.a` fails at link" property is verified under **gcc** and
**clang**, which are the release compilers. It is **not verifiable under tcc**:
tcc writes a **stripped** executable, so `nm` reports no runtime symbols at all
— not even for a program whose `main` calls runtime functions (measured with tcc
0.9.28rc). tcc is the fast development compiler, not a release compiler. If a
future tcc stops stripping, `tests/test_build_runtime_link.py::test_tcc_output_is_stripped_so_nm_cannot_verify_the_pin`
fails and this section has to be revisited.

## See also

- [`../SECURITY.md`](../SECURITY.md) — "Runtime ABI pinning" in the security model.
- [`../pengu_runtime.h`](../pengu_runtime.h) — the authoritative layout table.
- [`../tests/abi/test_abi_layout.c`](../tests/abi/test_abi_layout.c) — the
  `sizeof`/`offsetof` gate.
- [`../tests/test_abi_version.py`](../tests/test_abi_version.py) — the
  symbol/version gate.
