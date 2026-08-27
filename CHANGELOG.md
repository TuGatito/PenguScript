# Changelog - PenguScript v0.6

All notable changes, bug fixes, and performance optimizations applied to the PenguScript v0.6 compiler are documented in this file.

---

## [Bug Fixes (A - J)]

### Bug A: Conservative Escape Analysis (`pengu_checker.py`)
- **Issue**: Stack-allocated local variables escaped function boundaries when their addresses (`sigil of x`) were returned, assigned to struct fields, or passed into external function calls.
- **Fix**: Implemented conservative escape analysis in `_check_symbol_escape`. Variables whose addresses are referenced in return expressions, assigned to record fields, passed into function calls, or placed into collection inits are now correctly classified as escaping and allocated appropriately.

### Bug B: Array Size Compile-Time Constant Enforcement (`pengu_infer.py`)
- **Issue**: Dynamic variables were permitted as array sizes in `array of T with size N`, causing unwanted Variable Length Arrays (VLAs) in generated C99.
- **Fix**: Enforced that `array_init_expr` size operands must evaluate via constant folding to a positive integer literal at compile time. Dynamic expressions or non-positive dimensions now raise clear semantic errors.

### Bug C: Default Arguments in Generated C (`pengu_codegen.py`)
- **Issue**: Default parameter values were parsed and validated by the checker but omitted during code generation when calls omitted trailing positional arguments.
- **Fix**: Added signature tracking in `PenguCodegen.fn_info`. When a function call omits trailing parameters with defaults, the code generator automatically fills in the translated default expressions.

### Bug D: Redundant Import DFS Elimination (`pengu_checker.py`, `pengu_project.py`)
- **Issue**: `PenguChecker.check()` triggered redundant depth-first module traversals even when `PenguBuilder` had already computed the topological import order.
- **Fix**: Updated `PenguChecker.check()` and `_collect_top_level()` to accept a precomputed `import_order`, skipping redundant filesystem and AST DFS traversals.

### Bug E: String Interpolation Codegen with `pengu_string_format` (`pengu_runtime.h`, `pengu_codegen.py`)
- **Issue**: String literals containing `{expr}` expressions were outputted as plain C strings without runtime formatting.
- **Fix**: Implemented `pengu_string_format(const char* fmt, ...)` with `<stdarg.h>` and `vsnprintf` in `pengu_runtime.h`. Updated `PenguCodegen._translate_string_lit` to parse interpolated `{expr}` variables, deduce format specifiers (`%s`, `%d`, `%f`), and emit `pengu_string_format`.

### Bug F: `or:` Error Handling Blocks Codegen (`pengu_codegen.py`)
- **Issue**: `or:` blocks on `Result` and `Maybe` operations were not translated into control flow in variable declarations and statements.
- **Fix**: Added translation for `or_block` in `var_decl`, `let_decl`, and statement expressions, emitting `pengu_result_is_ok` / `pengu_maybe_is_present` error checks, binding the `error` string variable in scope, and executing the recovery block on error.

### Bug G: Bundle Caching & Configuration Hashing (`pengu_project.py`)
- **Issue**: Incremental compilation only compared source file `mtime` timestamps, failing to detect changes in compilation flags (`cflags`, `defines`, `includes`, `links`, profile).
- **Fix**: Added `.bundle_hash` caching storing the SHA-256 hash of all compilation configuration options. Cache invalidates automatically when flags, macros, or profiles change.

### Bug H: Transmute Byte Size Mismatch Warning (`pengu_infer.py`)
- **Issue**: `transmute` allowed reinterpreting between types of mismatched byte widths without warnings, risking memory corruption.
- **Fix**: Added type byte width estimation in `TypeInferrer._infer_transmute` and emitted descriptive compiler warnings when source and destination type sizes differ.

### Bug I: Receiver Pointer Passing Consistency (`pengu_codegen.py`)
- **Issue**: Method calls on enchanting receivers inconsistently mixed value and pointer access semantics.
- **Fix**: Ensured enchanting methods always receive `self` as a pointer (`T*`), passing `&obj` for value instances, `obj` for references, and using `->` member access consistently on `self`.

### Bug J: Sequential `#include` Resolution in Pass 2 (`pengu_checker.py`)
- **Issue**: Top-level C define symbols declared after `#include` directives could trigger errors if include tracking was evaluated out of order.
- **Fix**: Updated `_check_node` to update `has_includes` sequentially during AST traversal in Pass 2.

---

## [Performance Optimizations (1 - 6)]

### Opt 1: Comparison Constant Folding & Dead Branch Elimination (`pengu_infer.py`, `pengu_codegen.py`)
- Extended `ConstFolder` to fold comparison operations (`==`, `!=`, `<`, `<=`, `>`, `>=`) and `if_expr` ternaries.
- In `PenguCodegen._translate_stmt`, `if_stmt` and `unless_stmt` whose conditions fold to constants completely eliminate the dead branch from generated C code.

### Opt 2: Inlining Heuristic with AST Node Complexity (`pengu_checker.py`)
- Refined function inlining heuristic: functions with `<= 25` AST nodes containing no loops are automatically marked with `static inline __attribute__((always_inline))` in generated C.

### Opt 3: Topological Import Order Re-use (`pengu_checker.py`, `pengu_project.py`)
- Reused topological sort dependency order across type checking, declaration discovery, and code emission stages, eliminating duplicated parse tree visits.

### Opt 4: C `switch` Code Generation for Integer `judge` (`pengu_codegen.py`)
- When `judge` matches an integer expression against integer literal patterns, `PenguCodegen` now emits a C `switch` statement expression (`__extension__({ switch (...) { ... } })`) instead of chained ternary operators, enabling jump tables and compiler vectorization.

### Opt 5: C `restrict` Qualifier on Pointer Parameters (`pengu_codegen.py`)
- Pointer parameters (`RefType`) in generated C function definitions are now qualified with C99 `restrict` (`Type* restrict name`), informing the C compiler of disjoint memory regions for SIMD and register allocation optimizations.

### Opt 6: `memcpy` for Large Struct Assignments (`pengu_codegen.py`)
- Struct assignments (`set_stmt`) for runes with 3 or more fields (> 16 bytes) emit `memcpy(&(dst), &(src), sizeof(Rune))` for efficient block memory copying.
