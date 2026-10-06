# Compliance corpus — expected results

One canonical program per section of [`LANGUAGE.md`](../../LANGUAGE.md),
driven through the real toolchain (`pengu check` -> `pengu build` -> execute).

**54 programs**, each pinning a distinct LANGUAGE.md section. Every program exits with the code below (`expects_rc`).

The machine-readable source of truth is [`corpus.json`](corpus.json); this
file is the human-readable rendering of the same mapping.

## How to run

```console
$ python tests/compliance/run_all.py            # compile + execute everything
$ python tests/compliance/run_all.py --list     # show this mapping
$ python tests/compliance/run_all.py --only 016 # one program
$ pytest tests/test_compliance_corpus.py -q     # the pytest gate
```

`run_all.py` exits non-zero as soon as any program fails to check, fails to
build, or exits with a code different from `expects_rc`.

## Program map

| Program | LANGUAGE.md § | Section title | expects_rc | Pins |
|---|---|---|---|---|
| [`001-hello.pengu`](001-hello.pengu) | §2 | Quick start | 0 | the `weave main into int` entry point and the builtin `print` lowering. |
| [`002-identifiers-visibility.pengu`](002-identifiers-visibility.pengu) | §3.3 | Identifiers & visibility | 0 | leading-underscore module-privacy, the `_` discard binding, reserved `main`. |
| [`003-primitive-types.pengu`](003-primitive-types.pengu) | §4.1 | Primitive types | 0 | every accepted spelling maps to its documented canonical C width (`size of`). |
| [`004-runtime-containers.pengu`](004-runtime-containers.pengu) | §4.2 | Runtime containers | 0 | string / slice / list / map / maybe / result / range runtime containers. |
| [`005-declarations.pengu`](005-declarations.pengu) | §5.1 | Declarations | 0 | explicit/inferred bindings, zero-init arrays, destructuring, const and static var. |
| [`006-scope.pengu`](006-scope.pengu) | §5.2 | Scope | 0 | indentation-delimited lexical scopes and inner-name shadowing. |
| [`007-borrowed-modifier.pengu`](007-borrowed-modifier.pengu) | §5.4 | The `borrowed` modifier | 0 | `var borrowed` / `let borrowed` locals are non-owning (never auto-banished). |
| [`008-arithmetic-bitwise.pengu`](008-arithmetic-bitwise.pengu) | §6.2 | Arithmetic & bitwise | 0 | operator precedence, integer bitwise ops, short-circuit and/or, compound `set`. |
| [`009-comparison-membership.pengu`](009-comparison-membership.pengu) | §6.3 | Comparison, membership & word tests | 0 | `in`/`not in` on char, string, map and range; `is present`/`is true`; `null`. |
| [`010-address-deref-size.pengu`](010-address-deref-size.pengu) | §6.4 | Address, dereference & size | 0 | `sigil of`, `essence of` (read and `set` target), `size of`, `transmute`. |
| [`011-char-byte-primitives.pengu`](011-char-byte-primitives.pengu) | §6.5 | Character & byte primitives | 0 | `ord`, `chr`, and `bytes of` over both string and `array of byte`. |
| [`012-maybe-null-context.pengu`](012-maybe-null-context.pengu) | §6.6 | `maybe` constructors & `null` context | 0 | `some` boxing, `maybe none`, typed `null`, and the presence check. |
| [`013-if-unless.pengu`](013-if-unless.pengu) | §7.1 | `if` / `unless` (statements) and `if`-expressions | 0 | statement if/unless, the value-position `then/else`, safe `if v as T is m`. |
| [`014-while.pengu`](014-while.pengu) | §7.2 | `while` | 0 | indentation-scoped while loops and single-line `while c: stmt`. |
| [`015-for-loops.pengu`](015-for-loops.pengu) | §7.3 | `for` | 0 | range loops (incl. negative step), for-in over list/string/map, comprehensions. |
| [`016-judge.pengu`](016-judge.pengu) | §7.4 | `judge` — pattern matching | 0 | omen/int/bool subjects, payload extraction (`with f`), guards, `else ->`. |
| [`017-break-continue-return.pengu`](017-break-continue-return.pengu) | §7.5 | `break` / `continue` / `return` | 0 | break/continue inside loops, early `return`, and bare `return` in `void`. |
| [`018-block-expressions.pengu`](018-block-expressions.pengu) | §7.6 | Block expressions: `do:`, value-position `if` / `unless`, and loops | 0 | `do:` values, value-position if/unless, and collecting value-position loops. |
| [`019-weave-functions.pengu`](019-weave-functions.pengu) | §8.1 | `weave` — functions | 0 | default parameter values, named arguments, implicit return, `inline` weave. |
| [`020-declare-extern-c.pengu`](020-declare-extern-c.pengu) | §8.2 | `declare` — external C functions | 0 | `declare` prototypes bound to real C symbols (inc. a fn-pointer param) + `many T`. |
| [`021-function-pointers.pengu`](021-function-pointers.pengu) | §8.3 | Function pointers & callbacks | 0 | function decay to `ref to weave`, calls through a pointer, fn-type alias. |
| [`022-lambdas.pengu`](022-lambdas.pengu) | §8.4 | Lambdas | 0 | `lambda` syntax with typed params, inferred return, lambdas as fn values. |
| [`023-ritual-methods.pengu`](023-ritual-methods.pengu) | §8.5 | `ritual` methods (static) | 0 | `ritual` associated functions called on the type, instance methods via `self`. |
| [`024-rune-structs.pengu`](024-rune-structs.pengu) | §9.1 | `rune` — structs | 0 | rune fields, `with`/block construction, pointer-arrow access, destructuring. |
| [`025-cyclus-recursion.pengu`](025-cyclus-recursion.pengu) | §9.1.1 | `cyclus` — self-referential types | 0 | a `cyclus` recursive rune whose cycle is broken by pointer indirection. |
| [`026-derive-concepts.pengu`](026-derive-concepts.pengu) | §9.1.2 | `derive` — automatic concept implementations | 0 | `derive Par, Ordo, Vinculum` enabling ==, <, and use as a map key. |
| [`027-echo-unions.pengu`](027-echo-unions.pengu) | §9.2 | `echo` — unions | 0 | an `echo` lowers to a C union whose fields share storage. |
| [`028-omen.pengu`](028-omen.pengu) | §9.3 | `omen` — enums, string-valued omens & algebraic sum types | 0 | numeric enum, `with string:` omen, and a tagged algebraic omen with payloads. |
| [`029-seal-alias-opaque.pengu`](029-seal-alias-opaque.pengu) | §9.4 | `seal`, `alias`, `opaque` | 0 | nominal seal (explicit `to` casts), transparent alias, opaque handle behind ref. |
| [`030-frozen.pengu`](030-frozen.pengu) | §9.5 | `frozen` — read-only qualification | 0 | `frozen T` values, `ref to frozen T` pointees, and mutable-to-frozen flow. |
| [`031-enchanting-methods.pengu`](031-enchanting-methods.pengu) | §10.1 | `enchanting` — métodos sobre tipos | 0 | self-> instance methods, ritual statics, and enchanting a built-in container. |
| [`032-concept-bind.pengu`](032-concept-bind.pengu) | §10.3 | `bind` — implementación del contrato | 0 | exhaustive `bind` of a concept (instance + ritual method) and a `where` bound. |
| [`033-builtin-concepts.pengu`](033-builtin-concepts.pengu) | §10.9 | Built-in concepts | 0 | Num / Integrum / Par / Ordo bounds decide which operators generic code may use. |
| [`034-shard-generics.pengu`](034-shard-generics.pengu) | §11.1 | `shard` fundamentals | 0 | generic rune/weave monomorphization, nesting, `of T` explicit arguments. |
| [`035-donum-defaults.pengu`](035-donum-defaults.pengu) | §11.4 | `donum T` — default values | 0 | `donum T` lowers to the zero/default value of a defaultable type. |
| [`036-iterating-generics.pengu`](036-iterating-generics.pengu) | §11.5 | Iterating generics | 0 | `for x in list of T` inside generic code, plus concrete map/string iteration. |
| [`037-derive-generic.pengu`](037-derive-generic.pengu) | §11.6 | `derive` on generic types | 0 | `derive Par, Ordo` on a generic rune; substitution site checks the bound. |
| [`038-optionals-errors.pengu`](038-optionals-errors.pengu) | §12 | Optionals & errors | 0 | maybe/result containers, `or else`, `or return`, `or:` + `error`, `try`. |
| [`039-pointer-indexing.pengu`](039-pointer-indexing.pengu) | §13.1 | Indexing through pointers and borrowing C buffers | 0 | reads and writes through `ref to T` with `at`; fixed arrays decay to pointers. |
| [`040-auto-banish.pengu`](040-auto-banish.pengu) | §13.4 | Scope-Owned Locals (Auto-Banish) | 0 | fresh heap locals (string/list/map) are released deterministically per scope. |
| [`041-container-deep-copy.pengu`](041-container-deep-copy.pengu) | §13.5 | Container ownership & deep copy | 0 | owning containers deep-copy into their slots; the source keeps its own buffer. |
| [`042-imports-modules.pengu`](042-imports-modules.pengu) | §14.1 | Imports & modules | 0 | `import std.<module>`, an aliased import (`as`), and cross-module calls. |
| [`043-include-link-insignia.pengu`](043-include-link-insignia.pengu) | §14.2 | `include`, `link`, `insignia`, `declare` | 0 | `include` a C header, `link` its library, `declare` symbols, `insignia` prefixing. |
| [`044-char-opaque-bytes.pengu`](044-char-opaque-bytes.pengu) | §14.3 | `ref to char`, `opaque`, `.d.pengu`, and `bytes of` | 0 | C-string interop via `ref to char`, opaque handles behind `ref to`, `bytes of`. |
| [`045-literals.pengu`](045-literals.pengu) | §15.1 | Numbers, characters, booleans, null | 0 | decimal/hex/binary/underscored integers, float forms, char escapes, typed null. |
| [`046-strings.pengu`](046-strings.pengu) | §15.2 | Strings | 0 | `{expr}` interpolation, raw and triple-quoted literals, explicit conversions. |
| [`047-arrays-lists-slices-maps.pengu`](047-arrays-lists-slices-maps.pengu) | §15.3 | Arrays, lists, slices, maps | 0 | const-sized arrays, bracket literals, multidimensional arrays, slices, maps. |
| [`048-indentation-literals.pengu`](048-indentation-literals.pengu) | §15.4 | Indentation literals | 0 | block-indented array, map and struct literals. |
| [`049-ranges-membership.pengu`](049-ranges-membership.pengu) | §15.5 | Ranges & membership | 0 | `a to b` half-open ranges in iteration and `in` membership tests. |
| [`050-when-conditional-compilation.pengu`](050-when-conditional-compilation.pengu) | §16 | Conditional compilation (`when`) | 0 | top-level when/else-when, statement when, expression when, and `defined`. |
| [`051-unit-tests.pengu`](051-unit-tests.pengu) | §17 | Unit tests (`test`) | 0 | `test` blocks are semantically checked in every build mode (not only `--test`). |
| [`052-with-builders.pengu`](052-with-builders.pengu) | §18 | Block-style construction (`with:` expressions) | 0 | `with:` builders, nested builders with inferred targets, `with target:` edits. |
| [`053-with-collections.pengu`](053-with-collections.pengu) | §18.2 | `with` scopes on collections (`list` and `map`) | 0 | leading-dot built-in methods inside `with list:` / `with map:` scopes. |
| [`054-standard-library.pengu`](054-standard-library.pengu) | §19 | Standard library | 0 | pure std modules (spark, scrolls, arithmancy, oracle) called from one program. |
