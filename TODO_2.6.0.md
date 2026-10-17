# TODO after 2.6.0

Items found while implementing labels on `break`/`continue`, `type of expr`,
automatic `Donum` and the `with:` documentation sweep (2.6.0), plus the items
carried over from 2.5.0. None of them is caused by those changes: each is a
pre-existing limitation whose fix is larger than the feature that found it.

## 1. String temporaries passed to a borrow-only parameter leak

**Symptom.** Every `std.spark` helper that formats before printing leaks the
formatted string:

```pengu
import std.spark

weave main into int:
    calling spark.println_int with 41      # 3 bytes leaked (LeakSanitizer)
    return 0
```

```c
static inline void spark_print_int(int32_t value) {
  pengu_print(pengu_string_to_string(value));   /* never freed */
}
```

`std/spark.pengu`'s `print_int` / `println_int` / … are declared `with s as
string` (borrowed: "the caller keeps ownership") but are handed the result of
`value to string`, which allocates. The same shape appears in
`pengu_string_format_ex("{…}")` when the interpolation result is passed
straight to a call: the code generator never releases the format result.

**Minimal reproducer** (no `judge` involved):

```pengu
import std.spark

weave f with x as int into int:
    return x + 1

weave main into int:
    var a as int is 1
    var b as int is 2
    calling spark.println with "{calling f with a} {calling f with b}"
    return 0
```

LeakSanitizer reports one direct 64-byte leak from `pengu_string_format_ex`.
With a single `{…}` the pointer usually stays in a live stack slot, so LSan
calls it reachable — the buffer is still never freed.

**Why it is not fixed here.** The ownership rule the code generator implements
is documented in `pengu_parser/pengu_codegen/interpolate.py`: a *fresh*
temporary is released (`pengu_banish_string`), while a value read out of a
field, parameter or call result is not, because freeing it could free storage
the program still references. Extending that to "release the format result
once the call that borrowed it returns" needs a lifetime model for expression
temporaries (statement-expression temporaries, strict-C99 hoisting and
`defer` interaction included) — an API-level change, not a 2.5.x patch.

**Not a blocker for 2.5.0** because it predates it and no `judge over` path
adds to it.

## 2. `over` clause patterns are deliberately narrow

Deferred to a later release (documented as limitations in `LANGUAGE.md`
§7.4.1): nested patterns (`when Binary with left as Literal`), or-patterns,
tuple/array/list patterns, and `maybe`/`result` patterns. All are syntax
errors (`E0000`) today, so they cannot be accepted by accident.

## 3. Rune privacy has no module tracking

`judge ... over _field` / `with _field` are rejected even inside the module
that declares the rune, because `RuneType` carries no owning-module attribute;
`PenguChecker._owns_private_member` therefore falls back to the same rule the
`with target.field` path already used. Fixing it means recording the defining
module on every rune (and `echo`/`omen`) at collection time, which touches the
symbol table and the module loader.


## 4. A parameter used only in `type of` is unused in the generated C

**Symptom.** `weave describe shard T with x as T into string: return type of x`
emits a C function that never mentions `x`, so `-Wextra -Werror` reports
`unused parameter 'x'`. The language's own builds use `-Wall` (not `-Wextra`),
so this does not break `pengu build`, but the project's `-Werror` test gates have
to keep `type of` operands used elsewhere.

**Why it is not fixed here.** Silencing it means emitting `(void)x;` for every
parameter that the body never reads — an unused-parameter analysis in the codegen
(the AST scan is easy; the hard part is not regressing `defer` and keeping the
emitted C stable for the golden `bundle.c` files). Pre-existing for any weave that ignores a parameter, not specific to
`type of`: `weave f with q as int into int: return 0` has the same warning today.

## 5. `break` / `continue` inside a lambda body that encloses no loop

**Symptom.** A lambda is emitted as a separate top-level C function, but its
body is checked in the enclosing lexical scope, so `break`/`continue` (bare or
labeled) inside a lambda nested in a loop passes the checker and then emits a C
`break`/`goto` in a function with no such loop: `error: break statement not
within loop or switch`.

**Why it is not fixed here.** The fix is a scope boundary marker at the lambda
body (`in_loop=False`, fresh label namespace) in the checker — small, but it
changes diagnostics for code that compiles today only by accident, so it belongs
in a release that can test the lambda/capture surface as a whole. Pre-existing
for bare `break`; 2.6.0 inherits it for labeled jumps.

## 6. `donum` for the container types (semantic default, not `{0}`)

`list` / `map` / `slice` / `maybe` / `result` deliberately do not implement
`Donum` (2.6.0 documents why: `(PenguList){0}` has `elem_size == 0`). A useful
default for them is a *semantic* empty value — an empty `PenguList` with the
right `elem_size`, `pengu_maybe_none()` — which is an allocation-free helper per
element type, not a zero initialiser. That needs a `Donum::default()`-shaped
concept, so it is a design change rather than a patch.

## 7. A labeled jump that leaves an *enclosing* owning loop skips its release

**Symptom.** A `for v in <non-lvalue>` loop materializes the iterable and emits
`pengu_banish_list(&_iter_N);` after the loop. A `break`/`continue label` that
jumps out of an *inner* such loop to an outer labeled loop lands after that
release, so the materialized list leaks:

```pengu
outer: for i from 0 to 3:            # 48 bytes leaked (3 lists) under LSan
    for v in calling make_list:
        if v == 3:
            continue outer
```
A jump out of the loop that *owns* the iterable is already handled: its
`_break` anchor is emitted before the release, so the release runs (2.6.0).

**Why it is not fixed here.** Releasing the temporaries of every loop between
the jump and its target needs the code generator to keep a stack of active
owning loops and to emit their `banish` calls at each jump site. That is doable,
but it is a new codegen mechanism rather than a fix, and the language already
documents (and accepts) the same class of leak for an early `return`, which
"does not release, like every scope release". Under `-fsanitize=address,leak`
the `type of`, `donum` and same-loop-label paths are clean; only this
cross-loop case and the pre-existing format-string leak (item 1) show up.

## 8. Labels are not exposed to semantic tokens / document highlight

The LSP resolves labels for hover, definition, completion and rename
(`pengu_lsp/labels.py`), but a label still classifies as an ordinary `NAME` for
semantic tokens and `textDocument/documentHighlight` does not mark its jumps.
Both need the same enclosure computation `labels.py` already does; deferred
because neither was part of the 2.6.0 acceptance criteria.
