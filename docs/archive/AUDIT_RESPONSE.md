# Compiler audit response — v0.14.x report (0.15.0 tree)

Status of every item in the audit, verified against the current checkout.
Legend: **fixed** (regression test added), **invalid** (claim did not reproduce),
**verified ok** (behaviour is correct as-is), **deferred** (real but out of scope
for this round, with the reason).

| # | Claim | Status | Notes |
|---|---|---|---|
| 1 | `_element_cleanup_fn`/`_element_clone_fn` use logical name | **fixed** | Both use `_derived_type_c_name`, so `_pengu_cleanup_my_Player` is referenced. |
| 2 | Method call sites use the logical name | **fixed** | Call sites read the emitted `c_name` from the collected weave (`_method_definition_c_name`). |
| 3 | Receiver bounds not checked at method call sites | **deferred** | Real: a `map of Blob to int` receiver accepts an `enchanting map of shard K where K: Hashable` method. Impact is a late monomorphization error, not a miscompile. Needs receiver-bound propagation into `_resolve_call_target`. |
| 4 | Monomorphized instances use `filepath="."` | **deferred** | Diagnostics/backtraces only; needs the instance's real source path threaded through `collect_declarations`. |
| 5 | `t_args` vs `type_params` skips method-level shards | **invalid** | `enchanting map of shard K to shard V: weave first_of shard T …` compiles, links and runs correctly (verified end to end). |
| 6 | Transitive monomorphization through `self.bag.method` | **deferred** | The scan only looks one access level deep; needs a general receiver-chain walk. |
| 7 | `subst_map` misses `m_p` in transitive calls | **deferred** | Same code path as #6. |
| 8 | `TypeParam.__eq__` ignores bounds | **deferred** | Two parameters with the same name but different bounds compare equal; only affects dict keys in exotic declarations. |
| 9 | `is_compatible(TypeParam)` asymmetry | **fixed** | `BaseType.is_compatible` now enforces *built-in* bounds; `return`, `var`/`let`, `maybe T`, container elements and fields all reject bound violations (`E0005`/`E0018`). `any`, `null`, unbounded `T` and `T`→`T` stay permissive; user-defined concepts stay with the checker (symbol table). |
| 10 | Signature/field type nodes never validated | **fixed** | New pass 1b validates params, return types, rune/echo fields and `declare` signatures (`E0022`). Generic declarations, `enchanting` blocks, `.d.pengu` files and files that `include` a C header are skipped (C typedefs like `va_list`). |
| 11 | Duplicate parameter names accepted | **fixed** | Rejected for weaves and methods (`E0005`). |
| 12 | `weave int` emits invalid C | **invalid** | `_c_ident` escapes every C keyword (`weave asm` → `int32_t _asm(...)`), so the emitted C is valid. Test added to pin the escaping. |
| 13 | Concrete method type params not collected as generic methods | **verified ok** | Covered by the generic-method registration added with the generics work. |
| 14 | `_unify_type` ignores bounds | **deferred** | Call arguments are checked by the generic-bound path (`E0032`); unification itself stays permissive. |
| 15 | `bind` never compares `is_ritual` | **fixed** | Ritual/instance mismatch is now `E0030`. |
| 16 | `_generated_instances` persists across builds | **deferred** | Shared-state concern for long-lived LSP processes; the builder creates a fresh symbol table per project. |
| 17 | Fragile `len(t_args) == len(type_params)` | **invalid** | See #5: method-level shards on generic receivers work. |
| 18 | `var_ref("T")` emits a bare `T` in C | **verified ok** | `donum T` and typed declarations substitute the parameter; a bare type name as a *value* is rejected by the checker. |
| 19 | `int("08", 0)` crashes the checker | **fixed** | `parse_int_literal` keeps base 10 for plain literals (0x still honoured). |
| 20 | Comptime `div` floors instead of truncating | **fixed** | `c_int_div` truncates toward zero, matching C. |
| 21 | Comptime `%` sign differs from C | **fixed** | `c_int_mod` follows the dividend's sign. |
| 22 | `SealType` string `+=` falls through to codegen | **verified ok** | Assignment of a `string` to a seal is already rejected; the compound path then reports a numeric-target `E0005`, never invalid C. |
| 23 | `_is_side_effect_free` gaps | **verified ok** | Only causes an extra temporary, never wrong code. |
| 24 | `array_lit` with `MapType` expected | **deferred** | Unreachable through normal typing; would need an explicit coercion path. |
| 25 | `print` always appends `\n` | **verified ok / deferred** | Builtin `print` is newline-terminating (like `spark.println`). Changing it is a user-visible break; it needs a language decision, not a silent fix. |
| 26 | `print` fallback emits `.data` for non-primitive types | **deferred** | The checker normally rejects unsupported `print` arguments; the fallback should be an explicit error. |
| 27 | `pengu_list_at` result not NULL-checked | **verified ok** | Documented out-of-range behaviour (bounds assertion in debug builds); `std` offers `at_safe`. |
| 28 | `slice_at_expr` bounds not validated | **deferred** | Design choice (slices are unchecked views, like C); a bounds check would change the zero-cost contract. |
| 29 | `for_in` over an rvalue emits `&f()` | **fixed** | Non-lvalue lists are bound to a `PenguList _iter` temporary first. |
| 30 | `for_range` counter is `int32_t` | **deferred** | Range bounds are `int32` today; widening needs range type inference. |
| 31 | `for_range` re-evaluates the end expression | **deferred** | Perf only (the expression is side-effect-checked); hoisting is a follow-up. |
| 32 | Interpolation truncates `i64`/`u64` | **fixed** | `%lld`/`%llu`/`%u` + matching casts; `int`/`u32` keep `(int32_t)`/`(uint32_t)`. |
| 33 | `pengu_string_format_ex` `%f` buffer overread | **fixed** | `snprintf`'s would-be length is no longer used as an append count; values that do not fit retry in a heap buffer. Runtime test added. |
| 34 | `f64` print | **verified ok** | `float`/`f32`/`f64` all use the `(double)` `%f` path. |
| 35 | Named arguments keep source order | **fixed** | All-named calls are reordered to declaration order (functions, methods, module-qualified); mixed/positional calls are untouched. |
| 36 | Destructured `let` from a list leaks the temporary | **fixed (POD)** | A destructured *rvalue* list with POD elements now releases the temporary; owning elements (strings) still keep their views valid, and a *borrowed* list is never freed. Full fix needs the call-result ownership model. |
| 37 | Escape analysis conservative for string fields | **fixed** | A string stored in a resolvable string field (`.field`, `with f is s`, `with:` builder) is copied **and** the source stays auto-banished. |
| 38 | `return x.field` leaves a dangling view | **fixed** | Returning a view (`at`, slice, field, `bytes of`) of a local now marks it as escaping, so it is not banished. |
| 39 | Imported-module errors swallowed | **fixed** | A module's own `PenguError` is surfaced (deduplicated) instead of an `undefined identifier` downstream. |
| 40 | `_check_const_decl` leaves `symbols.consts` stale | **deferred** | Pass 2 creates a new symbol; the dict keeps the pass-1 value (same value in practice). |
| 41 | Omen `Red is "RED"` silently ignored | **deferred** | Documented auto-naming; a warning would be better than an error. |
| 42 | `with_target` outside `with` emits `self.field` | **verified ok** | Unreachable (the checker rejects it) and only a message-quality issue. |
| 43 | `banish` on `ref to Rune derive Nexus` leaks fields | **fixed** | Emits `_pengu_cleanup_T(ptr); pengu_banish(ptr);`. |
| 44 | `%c`/`%d` promotions | **verified ok** | `char` is promoted to `int` per the C ABI. |
| 45 | `some` with unknown arg type assumes `int32_t` | **deferred** | Needs a checker requirement that the payload type be inferable. |
| 46 | `some expr` shallow-copies and never releases | **deferred** | Part of the `maybe`/ownership model: needs a `PenguMaybe` destructor contract. |
| 47 | `or_else`/`or_return`/`try` payload leaks | **deferred** | Same model as #46; `trace`-scoped cleanup exists but payload ownership does not. |
| 48 | Loop-value expressions with fresh elements leak | **deferred** | Same ownership model; the loop-value list is released, its fresh element temporaries are not. |
| 49 | `elem_size == sizeof(PenguString)` heuristic | **deferred** | Runtime heuristic; a 16-byte struct can be mistaken for a string. Mitigated by the explicit clone/cleanup callbacks registered by the compiler. |
| 50 | `return (x.field)` with auto-banished `x` | **fixed** | Same fix as #38. |
| 51 | Destructured `let` bindings not auto-banished | **deferred** | Coupled to #36's ownership model. |
| 52 | `banish` on a seal | **verified ok** | Correctly rejected with a helpful `E0008`. |
| 53 | `defer`/`errdefer` with `ref to Nexus` | **fixed** | Same code path as #43 (`_translate_banish_target`). |
| 54 | `archivum` recursive walk leaks sublists | **deferred** | Runtime code, needs a manual review + leak test; outside the compiler-core scope of this round. |
| 55 | `archivum` glob `match_str` lifetime | **verified ok** | `pengu_list_push` deep-copies; the view is not freed. |
| 56 | `pengu_to_string` returns the identity for `PenguString` | **verified ok** | Documented: the result aliases the argument. |
| 57 | `pengu_string_copy` declared but not defined | **invalid** | Defined in `pengu_parser/pengu_runtime.c` and exported (`nm` shows `T pengu_string_copy`). |
| 58 | `pengu_c_strptime` ignores `fmt` | **deferred** | Runtime limitation (hardcoded formats); documented. |
| 59 | `list_index_of` string heuristic | **deferred** | Same as #49. |
| 60 | `map_put` with tombstones | **deferred** | Needs a stress test to decide whether the resize invariant can be violated. |
| 61 | `pengu_input` truncates long lines | **deferred** | Documented 4096-byte line limit. |
| 62 | `%d` with `INT_MIN` | **verified ok** | 32-byte scratch is enough; large values use the heap path. |
| 63 | `strftime` truncates at 512 bytes | **deferred** | Documented; returns an empty string on overflow. |
| 64 | `extern char **environ` in POSIX path | **verified ok** | Portable on glibc/musl. |
| 65 | `%s` with `NULL` | **verified ok** | Skips the argument (glibc prints `(null)`); deliberate. |
| 66 | `archivum` `%.*s` with empty path | **verified ok** | Empty precision writes nothing. |
| 67 | Signature type nodes not validated | **fixed** | Same as #10. |
| 68 | `_make_error` snippet without source | **verified ok** | Only affects renderers that have no source loaded. |
| 69 | `main` uniqueness tracking | **verified ok** | Detected per build through the shared symbol table. |
| 70 | `weave main into bool` | **verified ok** | Allowed and handled. |
| 71 | `judge` with a redundant `else` | **deferred** | A `W0004` for dead `else` would be nice; not a correctness issue. |
| 72 | `for_range` step validation | **verified ok** | The inferrer rejects non-integer steps. |
| 73 | `static var` in a nested scope | **verified ok** | Intentional ("directly inside a weave body"); worth documenting. |
| 74 | `insignia` inside `when_top_decl` | **verified ok** | Processed through the recursive collection. |
| 75 | Omen variant/const value collisions | **verified ok** | Intentional and documented. |
| 76 | Duplicate `test` names | **deferred** | Both run; a duplicate-name warning would help. |
| 77 | `_collected_files` initialised late | **fixed** | Initialised at the top of `_collect_top_level`. |
| 78 | `resolve_imports` parser reuse | **verified ok** | `parse()` defaults to `start='start'`. |
| 79 | `strip_bom` | **verified ok** | Handles repeated BOMs. |
| 80 | `_strip_comments` `##`/`#` handling | **verified ok** | Verified by the lexer tests. |
| 81 | `_file_is_main` abspath per call | **deferred** | Perf micro-optimisation. |
| 82 | `_lookup_type_fn` scope walks | **deferred** | Perf micro-optimisation. |
| 83 | `bind X with Nexus` may reference a missing helper | **invalid** | `generate_derived_implementations` also emits helpers for `concept_bindings`, and `_element_cleanup_fn` resolves the C name; verified with a `bind Bag with Nexus` + `list of Bag` bundle. |
| 84 | `at_expr` on `self.field` uses the logical rune name | **fixed** | Runes now carry `c_name`, so the lookup key matches the registry. |
| 85 | Linear scan over module symbols for omen fields | **deferred** | Perf micro-optimisation. |
| 86 | `judge_expr` with an unresolved omen pattern | **deferred** | Falls back to a raw identifier; should be a diagnostic. |

# Compiler audit #5 response (ownership, codegen, inference)

| # | Claim | Status | Notes |
|---|---|---|---|
| 1 | `some expr` shallow-copies and the box outlives the source (UAF) | **fixed** | `some` now **deep-copies** an owning payload (`pengu_string_clone`/`pengu_list_clone`/`_pengu_auto_clone_*`), so the box never aliases the source, and the source keeps ownership (it is released normally). The escape analysis was updated to match: boxing an owning payload is no longer an escape. |
| 2 | `maybe`/`result` boxes are never released | **fixed (maybe)** | Typed auto-banish: a `maybe T` binding releases the payload it owns and then the box (`pengu_banish_string((PenguString*)m.value)`, `free(m.value)`); POD payloads still free the box. `pengu_banish_maybe`/`pengu_banish_result` were added to the runtime. `result` boxes are left alone on purpose: they are built by C/std helpers that own their payloads. |
| 3 | `pengu_to_string(s)` on a `string` can free the source buffer | **fixed** | `x to string` with a string operand is the identity (no temp, no release), and `_expr_allocates_string` returns False for it. The previous code aborted with `free(): invalid pointer` on a literal. |
| 4 | Array literal argument emits invalid C | **fixed** | A bare array literal in argument position becomes a C99 compound literal (`((int32_t[3]){ 1, 2, 3 })`), which decays to the parameter pointer. |
| 5 | `list of Rune` without `derive Nexus` leaks each element's fields | **fixed (user runes)** | Runes with heap-owning fields get **implicit Imago/Nexus** under a private helper namespace (`_pengu_auto_clone_*`/`_pengu_auto_cleanup_*`, so a user method named `clone`/`nexus` cannot clash) and `type_owns_heap` feeds the concept table, element callbacks and `banish`. std and `.d.pengu` runes are **excluded**: they manage their buffers with explicit `free_*` helpers, and deriving a destructor for them double-freed (caught by the parchment/regulus suites). |
| 6 | `list of maybe T` does not propagate cleanup | **partial** | The maybe element cleanup needs a generated callback; the box lifetime is fixed for bindings, and the container case is documented as the remaining gap. |
| 7 | Iterating a non-lvalue list leaks the materialized buffer | **fixed** | The `_iter_N` temporary is released after the loop. |
| 8 | `var s is calling make_string` is never auto-banished | **deferred (design)** | Needs an `owned`/`borrowed` contract on `weave`/`declare` (see #25). Documented. |
| 9 | `byte` interpolates with `%c` | **verified intentional** | The std library (regex, xml, parchment, regulus) composes text from byte values and the tests pin that behaviour; changing it broke 14 tests, so it was reverted and documented. |
| 10 | `ord` reads `data[0]` without checking `.len` | **fixed** | Both paths now guard on `data && len > 0`. |
| 11 | Comprehensions reject strings while `for-in` accepts them | **fixed** | The inferrer and the code generator handle string iteration (per-character fresh strings, released per iteration). |
| 12 | `defined(NAME)` in a runtime expression emits the bare identifier | **fixed** | The inferrer (and the statement dispatcher) reject it with E0039; `when`/`when_expr` still work. |
| 13 | Element callbacks ignore `ArrayType`/`MaybeType` | **partial** | Arrays are handled by the typed release helpers; maybe/result elements still need generated callbacks (#6). |
| 14 | `size of x` on a variable silently uses its type | **open** | Not addressed in this round. |
| 15 | Array destructuring yields a decayed pointer | **open** | Not addressed in this round. |
| 16 | `or:` discards the container without freeing it | **fixed (maybe)** | When the operand is a language-built maybe (`some`/`maybe none`/a call), the payload is *moved* into the result and only the box is freed; `result` and direct local references are left alone (C-owned / still referenced). |
| 17 | Mixed named arguments are not reordered | **verified ok** | The checker forbids a positional argument after a named one, so source order is already correct. |
| 18 | `byte`/`char` share the interpolation rule | **verified intentional** | See #9. |
| 19 | `_block_value_is_fresh_string` does not descend into `else if` chains | **open** | Conservative (no UAF), only a missed cleanup. |
| 20 | `to` with an `AnyType` target emits a `void*` cast | **open** | Not addressed in this round. |
| 21 | `judge` patterns against ranges/variables are unchecked | **open** | Not addressed in this round. |
| 22 | `when_expr` is re-evaluated per iteration | **verified ok** | The checker folds it before code generation; the emitted condition is a constant. |
| 23 | `or_else`/`try_expr` freshness is conservative | **fixed for maybe** | With the move semantics of #16 the ok value is owned; the fallback still decides the binding's ownership. |
| 24 | Missing ownership contract for maybe/result | **partially done** | The rule is now: *the creator of the box owns it; `some` deep-copies; `or:` moves the payload and frees the box; `result` boxes stay C-owned*. Documented here. |
| 25 | `_expr_allocates_string` is heuristic | **deferred (design)** | Same `owned`/`borrowed` contract as #8. |
| 26 | `banish` on a `ref to T` pointing to the stack | **open** | Needs the same ownership annotations. |
| 27 | Mixed `defer`/auto-banish ordering | **verified ok (documented)** | Auto-banish is emitted LIFO before the explicit `defer` block of the scope. |
| 28 | `error` is defined as `kind="var"` | **fixed** | It is a `let` now (assigning it was meaningless). |
| 29 | Fixed C identifier `error` may shadow a local | **verified ok** | The checker already scopes `error` to the `or:` block; the C declaration shadows the same name in the same region. |
| 30 | Compound-statement indentation for `list` literals | **verified ok** | Cosmetic only. |

## Verification (audit #5)

- `pytest tests/ -q` → **1495 passed, 10 skipped, 0 failed**
- `python scratch/check_std.py` → **27 ok, 0 failed**
- `tests/test_audit_fixes.py` → **137 tests** (audits #1–#5)

# Compiler audit #4 response (value blocks, nested escape, omen collisions)

| # | Claim | Status | Notes |
|---|---|---|---|
| 1 | `void` values in value blocks emit invalid C | **fixed** | A value block whose type is `void` emits its expression as a statement instead of `void _val_N = …`, and binding a `void` value (`var`/`let`/`static var x as void is …`) is rejected with E0005. |
| 2 | Loop-value fed by `if`/`unless` leaks one buffer per iteration | **fixed** | `_value_branch` forwards the block node to `val_node_out`, and the ownership test sees through value blocks: all branches fresh → the temporary is released after the copy; any borrowed branch → nothing is released (no bad free). |
| 3 | Nested `do:` chains defeat the escape analysis (UAF) | **fixed** | The escape analysis flattens nested value blocks (`do: do: y`, value-`if` branches) in both `_check_symbol_escape` and `_compute_auto_banished`, so the source is not banished while the outer value still borrows it. |
| 4 | Escape analysis ignores `else` branches of a value `if` | **fixed** | `else_block`/`when_else_*` are expanded to their children before the last-value lookup. |
| 5 | `.d.pengu` omen variants produce false E0046 | **fixed** | A declaration emits its variants under the *simple* C name, so the logical `Omen_variant` full name is not registered for `.d.pengu` omens (a user `const KeyboardKey_KEY_LEFT` is now accepted; a real PenguScript omen collision still reports E0046). |
| 6 | `_last_value_expr` misses a trailing value-`if` | **fixed** | A trailing `if`/`unless`/`do`/loop node *is* the block value (its rule name is enough — the inferred type may not be recorded yet). |
| 7 | Nested loop-values orphan the inner container | **fixed** | `_expr_owns_value` generalises the freshness test to list/map elements, so an inner loop value (or a collection literal) is released after the deep-copying push. Measured 0 lost allocations. |
| 8 | `banish xs at 0` accepted but bans a temporary | **invalid** | The parser produces `at_expr` and the checker rejects every non-lvalue banish target (E0008) before code generation: `banish xs at 0`, `banish (xs at 0)` and `banish "lit"` all error out. |
| 9 | `_normalize_banish_ident` does not unwrap parens | **verified ok** | It already strips balanced outer parentheses (a parenthesised loop/block value is matched). |
| 10 | Void `if` branches capture values | **fixed** | Covered by #1. |
| 11 | `_block_value_hands_out` misses loop values | **verified ok** | A loop value deep-copies each element, so it never hands a local's storage out; treating it as escaping would introduce leaks. |
| 12 | Insignia'd imported omens register a phantom full name | **fixed** | Only the emitted C name is registered in `full_names`. |
| 13 | `_value_block_stack` pop not in `finally` | **verified ok** | `_check_value_block` and `_translate_value_block_with_banish` both push/pop inside `try/finally`. |
| 14 | `_check_or_block` pops its scope outside `finally` | **fixed** | The `pop_scope` moved into the `finally` so an internal failure cannot leave the scope on the stack. |

## Verification (audit #4)

- `pytest tests/ -q` → **1482 passed, 10 skipped, 0 failed**
- `python scratch/check_std.py` → **27 ok, 0 failed**
- `tests/test_audit_fixes.py` → **124 tests** (audits #1–#4)

# Compiler audit #3 response

| # | Claim | Status | Notes |
|---|---|---|---|
| 1 | Value-block banish runs before the value is read | **fixed** | `_translate_value_block_with_banish` snapshots the value into a temp *before* the scope flush, so `do:`/`if`/`unless` values that read a local (`y.length`) see the real buffer. Regression test compiles and runs. |
| 2 | `alias` to a function pointer emits invalid C | **fixed** | `typedef void (*Name)(params);` via `CTypeMapper.to_c_decl`, not `to_c_type`. |
| 3 | Lambda parameters pollute the current scope | **fixed** | `_register_one_lambda` pushes/pops a `lambda` scope; the parameter names no longer land in the global scope. |
| 4 | Large integer literals truncate to `int32_t` | **fixed** | Out-of-range `int_lit`s infer as `i64` (`3000000000`, `0xFFFFFFFF`); small literals stay `int32_t`. |
| 5 | `enchanting` methods skip the implicit-return rules | **fixed** | Methods now use the same `_stmt_always_returns`/last-expression logic as `weave` (E0020). |
| 6 | `to` ranges accept non-integer operands | **fixed** | `_require_int_range_bounds` rejects string bounds with E0005 (`"a" to "z"` emitted `int64_t = PenguString`). |
| 7 | Destructuring with `insignia` loses field names | **fixed** | Fields resolve through the C-name-keyed `self.runes`/`self.echos`, so renamed bindings read the declared fields. |
| 8 | `derive Imago`/`Nexus` rejects/ignores `array of T` | **fixed** | `type_implements_builtin_concept` delegates to the element, and the (previously duplicated) plain-rune Imago/Nexus loops now use the shared field helpers, which clone/release arrays per element. |
| 9 | Duplicate `import` through `when` not detected | **fixed** | `file_imports` travels through the `when` recursion, and `symbols.imports` never appends a module twice (the scheduler processed it once per import). |
| 10 | Automatic inlining never wired | **fixed** | `_collect_weave` reads `symbol.is_inline`; automatic candidates emit `static inline` (a *plain* hint: `always_inline` on a recursive weave is a hard GCC error), while the explicit `inline` keyword keeps `__attribute__((always_inline))`. |
| 11 | `static var` loses its symbol before codegen | **fixed** | `_check_static_var_decl` stores `node._pengu_symbol` (as `var`/`let` do) and the code generator prefers it. |
| 12 | `let … or:` destructuring not validated | **fixed** | The real gap was broader: the `or:` *fallback value* was never compared with the success type (`maybe int or: "text"` was accepted). `_check_or_block` now validates it; returning/void fallbacks stay accepted. |
| 13 | `or_block` not recognised as fresh (leak) | **deferred (safety)** | Treating the `or:` result as owned crashed: `some "x"` boxes a *borrowed* pointer, so releasing the binding freed `.rodata` (`free(): invalid pointer`). Correct fix = the maybe/result payload ownership contract (already deferred from audit #1); a regression test now pins the safe behaviour. |
| 14 | Escape analysis ignores value-block expressions | **fixed** | The checker now tracks view-bound locals declared in value blocks and marks the source as escaping when the block value borrows it (`var sl is do: … xs at 0 to 2` no longer dangles). Scalar members (`s.len`) and locally-used views keep the source auto-banished, so no leaks are introduced. |
| 15 | `_line_marker("")` adds a blank line | **verified ok** | Both call sites are guarded with `if marker:`. |
| 16 | `let` drops `const` when `is_auto` | **verified ok (required)** | The auto-banish call takes the address of the binding (`pengu_banish_string(&x)`); a `const` binding would not compile. |
| 17 | Omen-variant collision on an unfolded binding const | **fixed** | A `pengu_bind`-generated const (`.d.pengu`, value not folded) re-declares its own variant and is no longer reported as a clash. |
| 18 | `_check_enchanting_method` ignores `simple_stmt` | **fixed** | Covered by the #5 rewrite (`stmt`/`simple_stmt` unwrapping). |
| 19 | Algebraic omen tag enum ignores `variant_values` | **verified ok** | The checker clears explicit values for payload variants, so `omen_values` is empty for algebraic omens; the tag enum and the `tag_of` mapping must stay identical, so changing only one is riskier than the hypothetical gain. |
| 20 | `judge_expr` switch hardcodes `int32_t` | **fixed** | Falls back to `__typeof__((subject))` instead of guessing `int32_t`. |

## Verification (audit #3)

- `pytest tests/ -q` → **1469 passed, 10 skipped, 0 failed**
- `python scratch/check_std.py` → **27 ok, 0 failed**
- `tests/test_generics/run_all.sh` + `run_valgrind.sh` → all pass / **14 passed**
- `tests/test_string_composition/run_all.sh` + `run_leakcheck.sh` → all pass / **7 passed**
- `tests/test_audit_fixes.py` → **111 tests** (audits #1–#3)

# Compiler audit #2 response (v0.15.x tree)

Status of the 22 findings of the second review.

| # | Claim | Status | Notes |
|---|---|---|---|
| 1 | Named args skipping a default shift positions | **fixed** | `_reorder_named_arg_nodes` now returns a *complete positional* list (skipped defaults are inlined) and the checker rejects unknown, duplicated and missing required named arguments. Verified for plain, method and module-qualified calls. |
| 2 | `let x is f() or: …` emits `const` + assignment | **fixed** | The `or:` branch of a `let` declares the binding non-const (the block assigns it). |
| 3 | `.length`/`.capacity` emit invalid C | **fixed** | Codegen maps `length→len`, `capacity→cap` (direct and chained access); the inferrer now rejects `capacity`/`cap` on `string`/`slice`. |
| 4 | `%=` does not require `Integrum` | **fixed** | `%=` has its own integer-only check (`E0005`). |
| 5 | `#` inside a triple-quoted string is stripped | **fixed** | `_strip_comments` is now a stateful scanner that tracks `"`/`'`/`"""`/raw strings and `{…}` across lines. |
| 6 | `#` inside a string nested in `{expr}` corrupts the literal | **fixed** | Same scanner; a `{` only opens an interpolation when a balanced `}` follows (mirrors `extract_string_parts`). |
| 7 | View bound to a local does not mark the source as escaping | **fixed** | Escape analysis propagates through view-bound locals: the source is left un-banished only when the view itself escapes (returned/stored), so locally-used views still release the source. |
| 8 | `for_comp` over an rvalue emits `&f()` | **fixed** | Non-lvalue iterables are bound to a `_iter` temporary, like the `for-in` statement. |
| 9 | `concept` method signatures not validated | **fixed** | `concept_decl`/`concept_method` join pass 1b. |
| 10 | Omen variant payloads not validated | **fixed** | `omen_field` is validated. |
| 11 | `_validate_declared_types` disabled by any `include` | **fixed** | Replaced by an include-aware heuristic: only names that look like C typedefs (uppercase, `_`-prefixed, `_t` suffix, known set: `va_list`, `FILE`, …) are skipped; a PenguScript typo is still reported. |
| 12 | Every `enchanting` treated as generic | **fixed** | Only blocks with `shard_params`, an inlined `shard_param_ref` (`enchanting list of shard T:`) or a parameterised target (`Box of T`) skip validation. |
| 13 | `set x is bytes of local`/`lst at 0` does not escape | **invalid** | Verified: both shapes already mark the source as escaping (the target slot does not copy). |
| 14 | `%=` permits floats (duplicate of #4) | **fixed** | See #4. |
| 15 | `some` with an uninferable payload silently uses `int32_t` | **fixed** | Raises a compiler error instead of guessing. |
| 16 | `pengu_to_string` has no `char*` `_Generic` entry | **fixed** | Added `char*`/`const char*`; runtime driver test added. |
| 17 | `chr_expr` fold comment contradictory | **fixed** | Comment clarified (a bare `chr n` is never folded; a parenthesised `(chr 65)` is). |
| 18 | `%` escaping in long literals | **verified ok** | Correct, only visually noisy. |
| 19 | Loop-value fresh elements leak | **fixed** | The push deep-copies when the element has a clone callback, so a fresh iteration temporary is released right after the push; borrowed values are left alone and a shallow push keeps the old exclusion. Measured 0 lost allocations. |
| 20 | `_MODULE_TREE_CACHE` mtime granularity | **verified ok / accepted** | The key is `(path, mtime_ns, size)`; a same-size same-mtime edit is LSP-only and would be caught by a rebuild. |
| 21 | `set x is f() or: …` payload not validated for `T: Num` | **verified ok** | The checker infers the `or:` result type and validated it before this review. |
| 22 | Implicit return of an `or_block` | **verified ok** | The inferrer returns the ok type; comparisons with the return type are correct. |

## Verification (audit #2)

- `pytest tests/ -q` → **1446 passed, 10 skipped, 0 failed**
- `python scratch/check_std.py` → **27 ok, 0 failed**
- `tests/test_generics/run_all.sh` + `run_valgrind.sh` → all pass / **14 passed**
- `tests/test_string_composition/run_all.sh` + `run_leakcheck.sh` → all pass / **7 passed**
- `tests/test_audit_fixes.py` → **88 tests** (audit #1 + audit #2)

## Additional fixes found while validating the audit

- **Build speed**: imported modules were re-parsed for every importing file
  (~200 parses per build). A bounded `(path, mtime, size)` tree cache cuts that
  to one parse per module; the `std_integration_backward_compat` release profile
  went from ~34 s to ~18 s. `when_top_decl` recursion also keeps the precomputed
  import order.
- **Named arguments** in module-qualified calls follow the same reordering path
  as plain calls and methods.

## Known limitations (unchanged by this round)

- Fresh string *arguments* and *call results* are still not owned by the caller
  (documented in `CHANGELOG.md`); the fix requires a fresh-return contract plus
  call-result ownership.
- `maybe`/`result` payloads and loop-value element temporaries are still not
  released (#46–#48): same ownership model.
- Runtime items (#54, #58–#63) and generator/perf micro-optimisations are out of
  scope here and need their own review round.

## Regressions tests

- `tests/test_audit_fixes.py` — 58 tests covering #9, #10, #11, #15, #19–#21,
  #29, #32, #33, #35–#39, #43, #77 and the invalid claims (#5, #12, #17).
- `tests/test_modules_bindings.py::TestInsigniaCEmission` — insignia + enchanting
  + container callbacks (#1, #2, #84).
- `tests/test_string_composition/leak_slot_field_copy.pengu` — owned-slot copy
  leak check (#37).
- `tests/test_runtime_strings.py` — byte-exact/overflow-safe formatter (#33).
