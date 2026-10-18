# Migrating a PenguScript project between versions

This guide tells you what to change when you move a project from one PenguScript
release to another, and how to verify the move. It is deliberately short: the
**core language** has exactly **two** breaking syntax/semantics changes in its
history, and they landed in `0.10.0` and `1.0.0`. The only other break is the
**ecosystem-only** extraction of the external C bindings described in §0: the
compiler and runtime are additive, but programs that imported a binding now need
its satellite repository.

> **Current version: 2.10.0** (read from [`VERSION`](VERSION)). See
> [`CHANGELOG.md`](CHANGELOG.md) for the full history and
> [`LANGUAGE.md` §23](LANGUAGE.md) for the stability policy that governs it.

## 2.9.0 → 2.10.0: diagnostics, JSON and JSON-RPC

This release is purely additive. Import `std.json`, `std.diagnostic` and/or
`std.jsonrpc` when you need them. Two ownership rules are worth reading before
you do:

* every query that returns a `JsonValue` (`get`, `at`, `pointer`, ...) returns a
  deep copy you must `banish`; a `list of JsonValue` is released with
  `free_values` (and `free_strings`/`free_entries` for the other containers);
* `parse_in_arena` returns an arena-backed tree: `banish arena` releases it and
  banishing the value is a safe no-op.

No API was removed or renamed. The compiler fixes for recursive `Nexus`,
container-aware `Par`, multi-field variant construction and with-target field
resolution are visible only where they used to reject or miscompile valid code.

## 2.7.0 → 2.9.0: the four fundamental modules

This release is **purely additive** for the language and the existing stdlib.
After moving a project:

* existing `import`s and programs need no changes;
* import `std.builder`, `std.arena`, `std.sourcemap` and/or `std.bitset` when
  you want the new tools (see `LANGUAGE.md` §19.1.2);
* remember the arena lifecycle: `defer banish arena` releases the bookkeeping,
  `defer calling arena.free` releases the blocks. The examples show both;
* `(n to usize)` and `(n to size_t)` now work (they used to report `E0004`), so
  code that worked around the missing cast with an annotated local can be
  simplified but does not have to be.

No API was removed or renamed.

## 2.7.0 → 2.8.0: thick functions and context pipelines (additive)

2.8.0 adds two standard-library modules and changes no language syntax or
semantics. Existing programs keep compiling and behaving identically.

* **`std/functor.pengu`** — `Fn0<R>`, `Fn1<A,R>`, `Fn2<A,B,R>` and
  `Fn3<A,B,C,R>`: a function pointer plus a borrowed context, with `make_fn0` …
  `make_fn3`, `call`, `is_null` and `call_or`. This is the explicit answer to
  "I need a closure": the context is a value you pass, not an environment the
  compiler captures. Nothing allocates; the context must outlive the `Fn`.
* **`std/loom.pengu`** — `map_ctx`, `filter_ctx`, `fold_ctx`, `for_each_ctx`,
  `zip_with_ctx`, `find_first_ctx`, `any_ctx`, `all_ctx`, `partition_ctx` and
  `filter_map_ctx`. Each takes the callback's context as an argument, so a
  pipeline step can carry configuration without a lambda or a closure.
* **No language change.** Lambdas still do not capture (`LANGUAGE.md` §8.4.1
  now explains why, and lists the five explicit replacement patterns).

Two compiler bugs found while building the modules are fixed: a struct field of
function-pointer type emitted an invalid declarator (`R (*)(A) name;` instead of
`R (*name)(A);`), and a partial `with`/`donum` initializer of a rune with a
`list`/`map`/`slice` field zeroed the container instead of giving it a usable
empty default. A module can also opt out of a specific warning it deliberately
triggers with `# pengu: allow-warnings W0001` (used by `std.functor` for its
thick-function cast).

## 2.6.0 → 2.7.0: debt release — patterns, ownership, module privacy

Four changes are **not** purely additive; each has a one-line consequence:

* **Private fields are private to their module.** `rune R: _hidden as int` is now
  readable from the file that declares `R` (and from an `enchanting` block for
  `R`), where 2.6.0 rejected it — that is a fix. It is still `E0043` from any
  other module, so a program that reached into another module's `_field` was
  already failing; it keeps failing. The old checker heuristic (any file under
  `std/` could reach any other std file's privates) is gone.
* **`break`/`continue` inside a `lambda` body now fails** (`E0007`/`E0004`).
  It used to pass the checker and then emit a C `break` in a function with no
  loop — a compile error at best. A loop *inside* the lambda is unaffected.
* **`donum` of a container is an empty container**, not `E0049`: `list`, `map`,
  `slice` and `maybe` are defaultable. `result` is still not (it has no neutral
  value). A rune with a `list` field is now `Donum` too, so code that relied on
  the rejection must drop its workaround.
* **A `string` temporary created for a call is released by the caller** after the
  call returns (the parameter borrows it). See `LANGUAGE.md` §19. If a callee
  *returns* the borrowed buffer, the release is skipped (pointer comparison), so
  a pass-through helper keeps working; if the callee returns a container that may
  hold it, nothing is released (the old behaviour).

Everything else is additive: `judge` or-patterns and nested patterns (`when A | B`,
`when Binary with left as Literal`), `with opt as some` / `res as err` field
states, `pair as (a, b)` tuple destructuring, an indented `else ->` body, and
`(void)name;` casts for unused bindings so the generated C stays clean under
`-Wextra`.

## 2.5.0 → 2.6.0: labels, `type of` and automatic `Donum` are additive

Nothing to change. All three additions accept programs that did not compile
before and change no existing spelling:

* `outer: for …` plus `break outer` / `continue outer` — bare `break` /
  `continue` keep their meaning, and an identifier followed by `:` before a loop
  was a syntax error before this release, so no existing program can be
  reinterpreted.
* `type of expr` — a compile-time operator yielding the canonical type name.
  `type` and `size` stay ordinary identifiers (`size of` improved: `var size as
  int` followed by `return size` used to be unparsable).
* A `rune`/`echo` whose fields are all defaultable now implements `Donum`, so a
  `donum T` that used to be `E0049` compiles. `derive Donum` is *rejected* with a
  clear message — if a 2.5.0 program carried it (it could not: it was already
  `E0005`), remove the clause.
* `else: <short statement>` on one line is now accepted, matching `if c: break`.
  Additive: it was a syntax error.

One behaviour to know: `donum` on `char` and `byte` now works, like `i8`/`u8`.

## 2.4.0 → 2.5.0: `judge` over `rune` is additive

Nothing to change. `judge <rune> over <discriminant>:` is a new form; the plain
`judge` keeps its spelling and semantics, and `over` stays a valid identifier
outside a `judge` header. The one behaviour worth knowing is a **fix**, not a
break: a `rune` field whose type is an `omen` can now be initialised
(`with kind is Kind.A`) and matched (`judge r.sub:`), where it previously failed
with a spurious `E0005`. A plain `omen` now also implements `Par`, so
`rune X derive Par` accepts a plain-omen field.

## 2.3.0 → 2.4.0: mutating methods in the primitive modules

This entry covers both halves of the release: the toolchain (three `@mutates`
compiler fixes) and the **module** releases that ride with it.  `std.numerus`, `std.integrum`, `std.fractio`, `std.littera` and
`std.logica` go to **2.1.0**: every method that returned the receiver's own type
now mutates the receiver and returns `void`, with `get_<name>` as the pure form.
This is the same split `std.scrolls` took in 2.3.0, now applied through
`@mutates`.

### Pattern

```pengu
# Before (2.3.0)
let y as int is calling x.abs
calling ward.assert_eq_int with (calling x.clamp with 0, 10), 10

# After (2.4.0)
let y as int is calling x.get_abs
calling x.clamp with 0, 10
calling ward.assert_eq_int with x, 10
```

A bare mutating call is a **statement**; using it where a value is required is
`E0066`.  A mutating call on a binding that cannot be assigned is `E0006` -- the
same rule as `set x is ...`.

### Method table

| Module | Mutating (statement) | Pure form |
|---|---|---|
| `numerus` | `abs`, `signum`, `negated`, `twice`, `half`, `square`, `cube`, `truncate`, `floor`, `ceil`, `round` | `get_<name>` |
| `numerus` | `min_with`, `max_with`, `clamp`, `pow_int` | `get_<name>` |
| `integrum` | `next_power_of_two`, `prev_power_of_two`, `next_prime`, `prev_prime`, `factorial` | `get_<name>` |
| `integrum` | `div_floor`, `mod_floor`, `gcd`, `lcm` | `get_<name>` |
| `fractio` | `reciprocal`, `degrees`, `radians`, `sqrt`, `cbrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `exp`, `ln`, `log2`, `log10` | `get_<name>` |
| `fractio` | `lerp`, `copysign`, `atan2`, `pow`, `hypot` | `get_<name>` |
| `littera` | `to_upper`, `to_lower` | `get_to_upper`, `get_to_lower` |
| `logica` | `toggle`, `and_with`, `or_with`, `xor`, `iff`, `nand`, `nor`, `implies` | `get_<name>` |

Every one of those names also has a `get_` spelling; the second and fourth rows
are simply the methods that take an argument.

### Unchanged

- Predicates and conversions (`is_even`, `is_prime`, `is_nan`, `approx_eq`,
  `to_int`, `to_hex`, `div_rem`, ...) still return a value and take no part in the
  split.
- The `char` methods of `std.littera` are a different type from the `string`
  methods of `std.scrolls`; the two were already independent.
- Module-level functions that only delegate (`arithmancy.abs_i`,
  `arithmancy.sqrt`, ...) are **not** mutating: they take their operand as an
  argument, so they have no receiver to write back to.

### Chaining

Mutations on one receiver are written as consecutive statements:

```pengu
calling x.clamp with -30, 30
calling x.abs
calling x.twice
```

A chain (`calling x.get_abs.get_twice`) is the pure spelling and does **not**
touch `x`; a mutating link cannot appear inside a chain because it returns
nothing.

## 2.2.x → 2.3.0

### `std.scrolls`: methods that return `string` now mutate in place

From 2.3.0 the 36 `std.scrolls` methods that returned a `string` mutate the
receiver and return `void`, matching the `@mutates` rule of
[`LANGUAGE.md` §10.1](LANGUAGE.md). This is what lets a string be transformed by
a sequence of statements instead of a chain of temporaries:

```pengu
# Before (2.2.x)
var s as string is "  hola  "
let t as string is calling s.trim
calling spark.println with t

# After (2.3.0)
var s as string is "  hola  "
calling s.trim                       # s == "hola"
calling spark.println with s
```

To obtain the value **without** mutating the receiver, use the `get_*` variant:

```pengu
var s as string is "  hola  "
let t as string is calling s.get_trim   # s untouched
```

### Method table

Every affected method keeps its name for the mutating form and gains a `get_`
spelling for the pure one:

| Method (mutates) | Pure form | Method (mutates) | Pure form |
|---|---|---|---|
| `substring` | `get_substring` | `replace` | `get_replace` |
| `char_at` | `get_char_at` | `replace_all` | `get_replace_all` |
| `reverse` | `get_reverse` | `repeat` | `get_repeat` |
| `lower` | `get_lower` | `repeat_join` | `get_repeat_join` |
| `upper` | `get_upper` | `ljust` | `get_ljust` |
| `to_lower` | `get_to_lower` | `rjust` | `get_rjust` |
| `to_upper` | `get_to_upper` | `pad_left` | `get_pad_left` |
| `capitalize` | `get_capitalize` | `pad_right` | `get_pad_right` |
| `title` | `get_title` | `zfill` | `get_zfill` |
| `title_case` | `get_title_case` | `center` | `get_center` |
| `swap_case` | `get_swap_case` | `removeprefix` | `get_removeprefix` |
| `to_snake_case` | `get_to_snake_case` | `removesuffix` | `get_removesuffix` |
| `to_kebab_case` | `get_to_kebab_case` | `truncate` | `get_truncate` |
| `snake_case` | `get_snake_case` | `ellipsis` | `get_ellipsis` |
| `kebab_case` | `get_kebab_case` | `trim` | `get_trim` |
| `pascal_case` | `get_pascal_case` | `strip` | `get_strip` |
| `trim_start` | `get_trim_start` | `trim_end` | `get_trim_end` |
| `lstrip` | `get_lstrip` | `rstrip` | `get_rstrip` |

### What to change

Wherever the old result was **used**, ask for the pure form:

```pengu
# Before
var clean as string is calling raw.trim
return calling raw.trim.substring with 0, 2

# After
var clean as string is calling raw.get_trim
return calling raw.get_trim.get_substring with 0, 2
```

Where the old call was a **statement whose result was discarded**, the new
behaviour is usually what you wanted: `calling s.trim` now actually trims `s`.

Chaining consumes a value, so a chain must use the `get_` links throughout — the
mutating form returns nothing and cannot appear mid-chain. Calling a bare
`@mutates` method where a value is required is `E0066`.

### What does *not* change

- The **module-level functional forms** are still pure: `calling scrolls.trim
  with s` keeps returning a new `string`.
- Methods that answer with a `list of string` (`split`, `splitn`, `rsplit`,
  `split_whitespace`, `words`, `lines`, `partition`, `chars`) are untouched, and
  their elements are still non-owning views into the receiver.
- `std.littera`'s `char.to_upper`/`char.to_lower` and `std.tally`'s list helpers
  are different methods on different types and are unaffected.
- `std.numerus`, `std.integrum`, `std.fractio`, `std.littera` and `std.logica`
  are **not** part of this release; their methods still return their value.

`std.scrolls` spells the two forms out explicitly rather than using `@mutates`,
so the mutating body can release the buffer it replaces; the call-site semantics
are identical.

## 0. Phase 1 (Unreleased): external bindings moved to satellite repositories

PenguScript's compiler repository now ships only the **pure-PenguScript** standard
library. Every binding that wrapped an external C library moved out to its own
satellite repository, installed per project. This is a **breaking change for the
ecosystem, not for the language**: the runtime ABI, the syntax and the 21 pure
modules are untouched, but a project that imported a removed binding no longer
compiles until the matching satellite is installed.

### 0.1 Which `.pengu` files stop compiling

Any program whose source — or whose dependency graph — contains an
`import std.<name>` for one of these modules stops compiling:

- **25 C declaration bindings** (`.d.pengu`): `raylib`, `raymath`, `rlgl`,
  `rlights`, `raygui`, `sqlite3`, `webui`, `miniaudio`, `tomlum`, `yaml`,
  `uuid`, `xxhash`, `xlsxio`, `imago`, `typis`, `scriptor`, `perlinum`,
  `stb_image_resize2`, `stb_herringbone_wang_tile`, `nanosvg`, `nanosvgrast`,
  `minicoro`, `datastructura`, `fenestra`, `pactum`.
- **4 native-wrapping pure modules** (`.pengu`): `regulus` (PCRE2),
  `parchment` (libxml2), `seal` (mbedtls + zlib) and `xlsx` (wraps `xlsxio`).

(`std.precis` and `std.celeris` were already out of the tree before this phase;
their satellites exist all the same.)

Concretely, the compiler now reports the import as an unknown module. Nothing
else about the file changes: the syntax, the type system and the runtime calls
are the same.

### 0.2 How to migrate

1. Find the satellite repository for each removed module in
   [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md).
2. Add it to the project and refresh the dependency graph:

   ```bash
   cd my_project
   pengu add https://github.com/pengu-lang/pengu-raylib
   pengu update
   ```

   `pengu add` prints a clear "already installed; refreshing" note when the
   dependency is already present, so re-running it is safe.
3. Keep the `import std.<name>` line as it is: the satellite installs the module
   under the same `std.` path. Re-run `pengu check` (or `pengu build`) to confirm.

For a raylib game that used the old `game` template, the template itself was
removed; start from `exe` (or `cli`) and add the binding:

```bash
pengu new exe my_game
cd my_game
pengu add https://github.com/pengu-lang/pengu-raylib
```

### 0.3 What does **not** change

- The **21 pure modules** that remain in `std/`: `spark`, `scrolls`, `oracle`,
  `compass`, `archivum`, `cipher`, `chronicle`, `lot`, `arithmancy`, `rites`,
  `whisper`, `ward`, `trial`, `tally`, `atlas`, `coven`, `filum`, `loom`,
  `invoke`, `ffi` and `ledger`.
- The **core runtime**: `libpengu_runtime.a` links only libc/libm/pthreads and
  the runtime ABI is unchanged, so a project that imports no removed binding
  rebuilds byte-for-byte as before.
- Existing programs that do **not** import a removed binding: they compile and
  run without any edit.
- The `pengu` CLI verbs you already use (`init`, `new`, `build`, `run`, `check`,
  `test`, `fmt`, `doc`, `assets`, `clean`, `lsp`); `pengu add` and `pengu update`
  gain the satellite workflow.

The full satellite table is in
[`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md).

## 1. The stability contract

- **Additive changes ship in minor releases.** New modules, new `weave`s, new
  optional parameters and new diagnostics do not require a migration.
- **Removals and signature changes require a major release**, and a symbol must
  first be deprecated for **two releases** (`LANGUAGE.md` §23.3). Deprecated
  symbols emit `W0006`; `pengu build --deny-deprecated` turns that into an error,
  which is the recommended gate for a project that is about to upgrade.
- Every `@deprecated` symbol in the standard library, with its replacement and
  its retirement version, is listed in [`docs/DEPRECATIONS.md`](docs/DEPRECATIONS.md).
  That table is cross-checked against the sources by the documentation gate in
  [`tests/docs/`](tests/docs/), so it cannot silently go stale.

## 2. Breaking changes by version

| Version | Breaking change | Action |
|---|---|---|
| `0.10.0` | `and` stops being a list separator next to expressions | replace it with `,` — see §3 |
| `0.11.0` – `0.16.0` | **none** | nothing to do |
| `1.0.0` | the implicit ownership model is removed; memory is manual | delete `borrowed`, add explicit `banish`/`defer banish` — see §4 |
| `1.1.0` | **none** — additive only | nothing to do; new syntax is opt-in |
| `2.0.0` | **none** — additive only | nothing to do; `antiquus` is a *soft* keyword, so identifiers named `antiquus` keep compiling. The major number records a change to the language's safety contract (a `.pengu` source can now emit C that the checker does not verify), not a syntax break |
| `Unreleased` (Phase 1) | external C bindings leave `std/` for satellite repositories | install each satellite with `pengu add <url>` — see §0 and [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md) |

There are no other breaking entries in the changelog. If you find one that is not
in this table, that is a documentation bug — see §7.

Every row here has an executable counterpart in
[`tests/migration/`](tests/migration/README.md) (`EXPECTED.json`), which runs the
before-form and asserts it fails with the documented code; the current surface is
pinned separately by [`tests/test_compliance_corpus.py`](tests/test_compliance_corpus.py).

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
written, and [`tests/test_compliance_corpus.py`](tests/test_compliance_corpus.py)
holds the canonical program per section of `LANGUAGE.md`. Both are normative for
compatibility: a change that breaks one of them needs a MAJOR release and an
entry in §2 of this guide, not a quiet edit to the corpus.

Each section above becomes one rule `pengu migrate` applies, and the table in §2
becomes its supported version range.

## 7. Reporting a migration problem

If an upgrade breaks code in a way this guide does not describe, that is a
documentation bug: open an issue with the failing snippet and the release you came
from. A breaking change that is not in §2 means the changelog and this guide have
diverged — `tests/docs/test_migration_doc.py` exists to catch exactly that, and it is
cheaper to fix it here than in your project.
