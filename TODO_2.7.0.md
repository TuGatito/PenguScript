# TODO after 2.7.0

2.7.0 closed every item of `TODO_2.6.0.md` (the format-string temporary leak, the
`judge` pattern set, module-tracked rune privacy, unused-parameter cleanup,
`break`/`continue` in lambdas, semantic `Donum` for containers, cross-loop
temporary unwinding and label support in semantic tokens).  What follows are the
boundaries that release *chose* to keep, each with the reason, plus the leftovers
that a future release may want to revisit.  None of them is a bug: every case
below is documented behaviour with a test or a stated rationale.

## 1. `result` has no `donum` default (design decision)

`list`, `map`, `slice` and `maybe` have an allocation-free empty value; a
`result` does not.  Both payloads are heap pointers, so `(PenguResult){0}` would
hand out a NULL `.error`/`.value` (a crash on read) and a real one would have to
allocate — impossible in a static initialiser, and a surprising cost for a
zero-value operator.  `donum (result …)` is `E0049` pointing at
`calling ok_of` / `calling err_of`.

**If a future release wants it**: the shape is a `Donum::default()`-style
concept method (a real function, not an initialiser), because a *semantic*
default for a sum type has to pick a variant.  That is a design change, not a
patch.

## 2. Array/list patterns are deliberately not part of `judge`

`when X with items as [a, b]` is **not** syntax.  A list pattern hides a length
test plus per-element binds — O(n) work behind punctuation — and the language
already expresses it without hiding anything:

```pengu
when X with items if items.length == 2 ->
    let a is items at 0
    let b is items at 1
```

`judge` also has no `maybe`/`result` *subject* form for the same reason: an
optional is matched with `if v as T is m is present:` (§7.1) or unwrapped with
`or:`, which names the two states instead of inventing a third pattern language.
Nested patterns, or-patterns, `maybe`/`result` *field* states and tuple
destructuring ARE supported (§7.4.1).

## 3. A call whose result may hold the borrowed string does not release it

The caller releases a `string` temporary it built for a call when the result
cannot point at it: always for `void`/scalar results, and for a `string` result
only when the returned buffer differs from the argument.  A **reference, rune or
container** result may have stored the borrowed pointer (e.g.
`weave wrap with s as string into maybe string: return some s`), so nothing is
released — the old behaviour.  Releasing soundly there needs a lifetime model for
borrows, which is a much larger change than an ownership convention.

## 4. `strict_c99: true` cannot release a call temporary in value position

That mode forbids GNU statement expressions, so an expression-position call has
nowhere to put the `banish`.  A *statement*-position call is handled with a plain
block (2.7.0), which covers `calling spark.println with "{…}"`.  A value-position
call keeps the previous behaviour in that mode; the default mode (GNU statement
expressions) is complete.

## 5. `break` / `continue` inside a `do:` block nested in a loop

A `do:` block is inlined into the enclosing function, so `break` there targets
the enclosing loop — valid C and useful, but it can be surprising inside what
looks like a value block.  It is documented as a statement-context block
(`LANGUAGE.md` §7.6); a future release may decide to make it a boundary like a
lambda, which would be a breaking change.

## 6. Rune privacy is per *file*, not per logical module

A module's identity is the path of the file that declares its types.  Two files
in the same directory are two modules (a `std` file cannot read another `std`
file's privates), and one file is one module even if it is included from several
places.  That matches how imports name modules; a logical-module notion would need
a declaration in `pengu.yaml`.

## 7. `type of` reports the caller-visible name of a generic parameter

Inside `weave describe shard T with x as T into string`, `type of x` is `"T"` in
the generic body and the concrete name in each monomorphized instance (which is
what the code generator emits).  The LSP hover shows the same thing, so a hover
on a *generic* body cannot name the instantiation — by construction: one body,
many instances.
