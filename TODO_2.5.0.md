# TODO after 2.5.0

Items found while implementing `judge` over `rune` (2.5.0) that are real but
larger than that change should carry. None of them is caused by, or specific
to, `judge over rune`: a `judge over` expression allocates nothing and a
program built only from one is clean under ASan/UBSan/LeakSanitizer.

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
