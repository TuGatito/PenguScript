# Generics test suite

End-to-end programs exercising PenguScript's generics: `shard` type parameters,
`where` bounds, `derive`, `cyclus`, `donum T` and the container ownership model
(`PenguElemCleanup` / `PenguElemClone`).

## Layout

| Pattern | Meaning |
|---|---|
| `test_*.pengu` | Compiles, links and must exit with status `0`. |
| `leak_*.pengu` | Runnable **and** leak-checked (the acceptance program for the escape-chain fix). |
| `ok_*.pengu` | Runnable positive cases (used by `gap2_set_typeparam_bounds/`). |
| `gap1_*/*.pengu` | Runnable + leak-checked regression set for the escape-analysis chain fix. |
| `fail_*.pengu` / `err_*.pengu` | Must be **rejected** by the checker. The first line carries `# EXPECTED: EXXXX` with the diagnostic code. |
| `run_all.sh` | Builds and runs every runnable program (recursively). |
| `run_valgrind.sh` | Leak-checks the ownership programs. |

Discovery is recursive, so the `gap1_*` / `gap2_*` directories are picked up
automatically by both the pytest suite and the shell runners.

## Running

Everything at once (recommended):

```bash
python -m pytest tests/test_generics_suite.py -q
```

Per program, using the compiler in this checkout:

```bash
python pengu_project.py run tests/test_generics/test_generic_identity.pengu
./tests/test_generics/run_all.sh          # loops over every runnable program
./tests/test_generics/run_valgrind.sh     # leak checks only
```

Set `PENGU=/path/to/pengu` to test an installed binary instead of the checkout,
and `PYTHON=/path/to/python` to pick the interpreter used by the scripts.

## Memory leaks

`run_valgrind.sh` (and the `no_memory_leaks` pytest selection) checks that the
programs with owning containers free everything:

* `leak_self_field_push.pengu` — the Gap 1 acceptance program: a string built
  inside an `enchanting` method and pushed through `self->items`, plus
  caller-owned locals passed to the method.
* `gap1_self_field_push/*.pengu` — every receiver-chain shape (`self->items`,
  `self.items`, `bag.items`, `bag->items`, `o->inner.items`, `with bag->items:`).
* `test_list_of_string_cleanup.pengu` — `list of string` releases each element.
* `test_map_of_string_to_list.pengu` — `map of string to list of int` releases
  keys, values and the nested lists.
* `test_list_of_box.pengu` — a list of runes with `derive Imago` deep-copies and
  releases each element.
* `test_derive_imago.pengu` / `test_derive_nexus.pengu` / `test_derive_omen.pengu`
  — derived deep copy and drop for structs and algebraic omens.
* `test_nested_list_leak.pengu` / `test_nested_map_leak.pengu` — pre-existing
  nested container programs.

If `valgrind` is not installed, the suite builds `tests/leakcheck.c`
(`LD_PRELOAD` malloc interposer with a conservative mark-and-sweep at exit) and
uses it instead; the run fails when any allocation is *definitely lost*.

## Notes on rejected programs

* `fail_bounds_missing.pengu` / `fail_bounds_mod_missing.pengu` — `E0049`:
  `+` needs `where T: Num`, `%` needs `where T: Integrum`.
* `fail_infinite_size*.pengu` — `E0050`: a field of the same type by value has
  infinite size; break it with `ref to`/`maybe ref to`.
* `fail_duplicate_bind.pengu` / `fail_conflicting_bind.pengu` — `E0047`: a type
  cannot bind the same concept twice, nor let two concepts provide the same
  method name.
* `fail_derive_echo.pengu` — `E0005`: `echo` compiles to an untagged C union, so
  `derive` is unsound there; use an algebraic `omen` or `bind`.

## Gap regression sets

* `gap1_self_field_push/` — the escape analysis must resolve **access chains**
  to the container type, so a fresh local string pushed through a rune field is
  still auto-banished. Without the fix `pengu_banish_string(&local)` disappears
  from the generated C and every program leaks the local's buffer.
* `gap2_set_typeparam_bounds/` — `set` into a `T`-typed target enforces T's
  bounds: `err_*.pengu` documents the rejected cases (`string`/`maybe` → `Num`,
  `float` → `Integrum`, list elements) and `ok_*.pengu` the accepted ones
  (int → `Num`, float → `Num`, `Integrum`, unbounded wildcard, `T` → `T`,
  `null`/`any`).

## Known issue: fresh call arguments

An inline freshly allocated argument (`calling f with "a{b}"`) is not released
by the caller, and a call result stored in a local (`var s as string is calling
f`) is not auto-banished. The programs above therefore build fresh strings in
**locals** and release them explicitly where it matters (or rely on the
auto-banish of `"…{expr}…"` initializers). Fixing the argument case requires a
*fresh-return contract* (a string-returning weave must return an owned buffer,
copying borrowed views), call-result ownership, and copies when a borrowed string
is stored into a static variable — otherwise `weave identity with s as string
into string: return s` hands back a buffer the caller then frees. Naively
banishing the temporary after the call produced `free(): invalid pointer` in
`std.invoke`, so it is intentionally left alone.

Note that owning slots are safe now: a string written into a struct field /
element / pointee is deep-copied (`pengu_string_copy`) unless it is a fresh
temporary being moved in, and interpolation temporaries are released. A rune
local that owns string fields must be `banish`ed (or stored in an owning
container) to release them — auto-banish only covers `string`, `list` and `map`
locals.
