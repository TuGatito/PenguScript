# Reproductions of compiler bugs found by the conformance work

These are *not* tests and are not collected by pytest; they are the smallest
programs that reproduce a bug, kept so the finding does not depend on anyone
re-deriving it. The path prefix `_` keeps them out of the conformance discovery
walk (which only reads `tests/conformance/`, not `tests/_repro/`).

## `dupsym` — a generic in one module makes a same-named non-generic function in
## another module unusable (E0005), depending on import order

```
$ python pengu_project.py test --entry tests/_repro/main.pengu
  tests/_repro/main.pengu:5:5 [E0005] Could not infer type parameter(s) T for
  generic function 'moda_f'
```

`moda.pengu` declares `weave f with x as int into int` (not generic).
`modb.pengu` declares `weave f shard T where T: Num with x as T into T` (generic).
`main.pengu` imports both and calls `moda.f with 1` with an `int` argument --
enough information to call it. The compiler reports `moda_f` as *generic* and
demands a `T` that the call has no way to provide.

Root cause, located but **not fixed** (see `tests/_inventory.md` §19):
`pengu_parser/pengu_checker.py` re-registers every generic of an imported module
under `f"{bind_name}_{gname}"`. A sub-checker's `generic_functions` also contains
generics pulled in *transitively*, so a generic defined in one module gets
registered under the prefix of whichever module was being imported -- inventing
`moda_f`/`loom_running_sum` for generics that belong to `modb`/`tally`. That is
what makes an unrelated non-generic function resolve as generic.

It matters beyond this repository: `std/loom.pengu` declares a non-generic
`running_sum` and `std/tally.pengu` declares a generic one, so any program whose
import graph reaches both can hit it -- and bundling independent programs into one
compilation unit makes such graphs common.
