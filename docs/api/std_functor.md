# std.functor

> Source: `std/functor.pengu`

---

### `FUNCTOR_VERSION`

> **FUNCTOR_VERSION** : string

 The version of the functor module.

### `Fn0`

> rune Fn0

```pengu
    fn_ptr as ref to weave with ctx: ref to void into R
    ctx as ref to void
```

 A thick function of no arguments: `fn_ptr(ctx) -> R`.

 `ctx` is the borrowed context; `fn_ptr` has been reinterpreted to receive it
 as `ref to void` (see `make_fn0`). Treat both fields as read-only.

### `Fn1`

> rune Fn1

```pengu
    fn_ptr as ref to weave with ctx: ref to void, a: A into R
    ctx as ref to void
```

 A thick function of one argument: `fn_ptr(ctx, a) -> R`.

 `ctx` is the borrowed context; `fn_ptr` has been reinterpreted to receive it
 as `ref to void` (see `make_fn1`). Treat both fields as read-only.

### `Fn2`

> rune Fn2

```pengu
    fn_ptr as ref to weave with ctx: ref to void, a: A, b: B into R
    ctx as ref to void
```

 A thick function of two arguments: `fn_ptr(ctx, a, b) -> R`.

 `ctx` is the borrowed context; `fn_ptr` has been reinterpreted to receive it
 as `ref to void` (see `make_fn2`). Treat both fields as read-only.

### `Fn3`

> rune Fn3

```pengu
    fn_ptr as ref to weave with ctx: ref to void, a: A, b: B, c: C into R
    ctx as ref to void
```

 A thick function of three arguments: `fn_ptr(ctx, a, b, c) -> R`.

 `ctx` is the borrowed context; `fn_ptr` has been reinterpreted to receive it
 as `ref to void` (see `make_fn3`). Treat both fields as read-only.

### `make_fn0`

> **make_fn0**(f: weave with c: ref to C into R, ctx: ref to C) -> Fn0__R

 Builds an `Fn0` from a function and a context.

 ## Parámetros
 - `f`: the function to store. Its first parameter is the typed context
   (`c as ref to C`); any additional parameters become the call arguments.
 - `ctx`: the context passed to `f` on every call. It is **borrowed**: this
   module never frees it.

 ## Retorno
 An `Fn0` (two pointers) that calls `f(ctx)`.

 ## Seguridad
 `f` is `transmute`d to the equivalent signature with `ref to void` as its
 first parameter. In strict C99, calling through an incompatible
 function-pointer type is technically undefined behaviour, but this is the
 standard Zig/Odin pattern and works on every real ABI. The reinterpretation
 happens here, once; `call` never casts.

 ## Tiempos de vida
 `ctx` must outlive the `Fn0` and every call made through it.

 ## Memoria
 No aloca memoria. The returned `Fn0` lives wherever the caller stores it.

 ## Ejemplo
 ```pengu
 var counter as int is 0
 var f as functor.Fn0 of int is calling functor.make_fn0 with read_counter, (sigil of counter)
 calling f.call    # reads counter
 ```

### `make_fn1`

> **make_fn1**(f: weave with c: ref to C, a: A into R, ctx: ref to C) -> Fn1__A__R

 Builds an `Fn1` from a function and a context.

 ## Parámetros
 - `f`: the function to store. Its first parameter is the typed context
   (`c as ref to C`); the second is the call argument.
 - `ctx`: the context passed to `f` on every call. It is **borrowed**: this
   module never frees it.

 ## Retorno
 An `Fn1` (two pointers) that calls `f(ctx, a)`.

 ## Seguridad
 `f` is `transmute`d to the equivalent signature with `ref to void` as its
 first parameter. In strict C99, calling through an incompatible
 function-pointer type is technically undefined behaviour, but this is the
 standard Zig/Odin pattern and works on every real ABI. The reinterpretation
 happens here, once; `call` never casts.

 ## Tiempos de vida
 `ctx` must outlive the `Fn1` and every call made through it.

 ## Memoria
 No aloca memoria. The returned `Fn1` lives wherever the caller stores it.

 ## Ejemplo
 ```pengu
 rune Multiplier:
     factor as int

 weave apply with m as ref to Multiplier, x as int into int:
     return m->factor * x

 var m as Multiplier is with factor is 3
 var f as functor.Fn1 of int, int is calling functor.make_fn1 with apply, (sigil of m)
 calling f.call with 5      # 15
 ```

### `make_fn2`

> **make_fn2**(f: weave with c: ref to C, a: A, b: B into R, ctx: ref to C) -> Fn2__A__B__R

 Builds an `Fn2` from a function and a context.

 ## Parámetros
 - `f`: the function to store. Its first parameter is the typed context
   (`c as ref to C`); the next two are the call arguments.
 - `ctx`: the context passed to `f` on every call. It is **borrowed**: this
   module never frees it.

 ## Retorno
 An `Fn2` (two pointers) that calls `f(ctx, a, b)`.

 ## Seguridad
 `f` is `transmute`d to the equivalent signature with `ref to void` as its
 first parameter. In strict C99, calling through an incompatible
 function-pointer type is technically undefined behaviour, but this is the
 standard Zig/Odin pattern and works on every real ABI. The reinterpretation
 happens here, once; `call` never casts.

 ## Tiempos de vida
 `ctx` must outlive the `Fn2` and every call made through it.

 ## Memoria
 No aloca memoria. The returned `Fn2` lives wherever the caller stores it.

 ## Ejemplo
 ```pengu
 var f as functor.Fn2 of int, int, int is calling functor.make_fn2 with add, (sigil of base)
 calling f.call with 2, 3      # base + 5
 ```

### `make_fn3`

> **make_fn3**(f: weave with c: ref to C, a: A, b: B, c2: C2 into R, ctx: ref to C) -> Fn3__A__B__C2__R

 Builds an `Fn3` from a function and a context.

 The third argument type is named `C2` internally because `C` already names
 the context type (`ctx as ref to C`). This is a spelling detail of the
 declaration only; callers write `functor.Fn3 of A, B, C2, R` with their own
 names.

 ## Parámetros
 - `f`: the function to store. Its first parameter is the typed context
   (`c as ref to C`); the next three are the call arguments.
 - `ctx`: the context passed to `f` on every call. It is **borrowed**: this
   module never frees it.

 ## Retorno
 An `Fn3` (two pointers) that calls `f(ctx, a, b, c2)`.

 ## Seguridad
 `f` is `transmute`d to the equivalent signature with `ref to void` as its
 first parameter. In strict C99, calling through an incompatible
 function-pointer type is technically undefined behaviour, but this is the
 standard Zig/Odin pattern and works on every real ABI. The reinterpretation
 happens here, once; `call` never casts.

 ## Tiempos de vida
 `ctx` must outlive the `Fn3` and every call made through it.

 ## Memoria
 No aloca memoria. The returned `Fn3` lives wherever the caller stores it.

 ## Ejemplo
 ```pengu
 var f as functor.Fn3 of int, int, int, int is calling functor.make_fn3 with sum3, (sigil of base)
 calling f.call with 1, 2, 3
 ```

### `call`

> **call**() -> R

 Calls the stored function with the stored context and returns its result.

 ## Retorno
 Whatever `fn_ptr` returns.

 ## Memoria
 No aloca memoria; the context is passed through unchanged.

 ## Ejemplo
 ```pengu
 calling f.call
 ```

### `is_null`

> **is_null**() -> bool

 Returns `true` when the `Fn0` holds no function.

 A `Fn0` built by `make_fn0` is never null (the function argument must be
 a real function); this is for values that crossed `donum` or were
 initialised field by field.

### `call_or`

> **call_or**(fallback: R) -> R

 Calls the stored function, or returns `fallback` when it is null.

 ## Memoria
 No aloca memoria. `fallback` is returned by value.

### `_Multiplier`

> rune _Multiplier

```pengu
    factor as int
```

 A three-times multiplier used by the constructor and call tests.

### `_LengthCtx`

> rune _LengthCtx

```pengu
    expected as string
```

 A context that owns the expected text, for the `string` argument test.

### `_Holder`

> rune _Holder

```pengu
    f as Fn1__int__int
```

 A rune that stores a `Fn1`: the "callback as a field" case.

### `_expect_int`

> **_expect_int**(actual: int, expected: int, label: string) -> void

 Panics with `label` when `actual` and `expected` differ.

### `_expect`

> **_expect**(cond: bool, label: string) -> void

 Panics with `label` when `cond` is false.

### `_multiply`

> **_multiply**(m: ref to _Multiplier, x: int) -> int

 `(ref to _Multiplier, int) -> int`, the canonical context function.

### `_factor10`

> **_factor10**(m: ref to _Multiplier) -> int

 `(ref to _Multiplier) -> int`, the zero-argument case.

### `_multiply_sum`

> **_multiply_sum**(m: ref to _Multiplier, x: int, y: int) -> int

 `(ref to _Multiplier, int, int) -> int`, the two-argument case.

### `_multiply_sum3`

> **_multiply_sum3**(m: ref to _Multiplier, x: int, y: int, z: int) -> int

 `(ref to _Multiplier, int, int, int) -> int`, the three-argument case.

### `_sum_factors`

> **_sum_factors**(m: ref to _Multiplier, other: ref to _Multiplier) -> int

 `(ref to _Multiplier, ref to _Multiplier) -> int`, the `ref to rune` argument case.

### `_string_len_is`

> **_string_len_is**(c: ref to _LengthCtx, s: string) -> bool

 `(ref to _LengthCtx, string) -> bool`, the `string` argument case.

### `_add_offset`

> **_add_offset**(offset: ref to int, x: int) -> int

 `(ref to int, int) -> int`, the plain-value context case.

### `_twice`

> **_twice**(c: ref to void, x: int) -> int

 `(ref to void, int) -> int`: ignores its context, for the null-context test.

### `_run_it`

> **_run_it**(f: Fn1__int__int, a: int) -> int

 Passes a `Fn1` to another function: the "callback as a parameter" case.

### `"make_fn0 calls the function with the context"`

> test "make_fn0 calls the function with the context"

 Zero-argument constructor and call.

### `"make_fn1 calls the function with the context and the argument"`

> test "make_fn1 calls the function with the context and the argument"

 One-argument constructor and call, with a rune context.

### `"make_fn1 carries a string argument"`

> test "make_fn1 carries a string argument"

 A string argument.

### `"make_fn1 carries a reference argument"`

> test "make_fn1 carries a reference argument"

 A `ref to rune` argument.

### `"make_fn1 accepts a plain-value context"`

> test "make_fn1 accepts a plain-value context"

 A plain-value context (ref to int rather than ref to rune).

### `"make_fn2 calls the function with two arguments"`

> test "make_fn2 calls the function with two arguments"

 Two-argument constructor and call.

### `"make_fn3 calls the function with three arguments"`

> test "make_fn3 calls the function with three arguments"

 Three-argument constructor and call.

### `"a Fn1 can be stored in a rune field"`

> test "a Fn1 can be stored in a rune field"

 Storing a Fn1 in another rune.

### `"a Fn1 can be passed to another function"`

> test "a Fn1 can be passed to another function"

 Passing a Fn1 to another function.

### `"a Fn1 accepts a null context"`

> test "a Fn1 accepts a null context"

 A null context for a function that ignores it.

### `"is_null is false and call_or uses the function"`

> test "is_null is false and call_or uses the function"

 is_null and call_or on a real Fn.

### `"a donum Fn1 is null and call_or returns the fallback"`

> test "a donum Fn1 is null and call_or returns the fallback"

 is_null and call_or on a null Fn built field by field.

### `"functor version is 3.0.1"`

> test "functor version is 3.0.1"

 The version marker follows the toolchain release.

