# std.ffi_call

> Source: `std/ffi_call.pengu`

std/ffi_call.pengu — optional libffi-backed dynamic calls.

This module is a satellite-style surface: it links `-lffi` only when
imported.  It complements `std.ffi` (buffer/string conversion) and
`std.dynlib` (symbol lookup).  The generated compiler/runtime never depends
on libffi unless this module is in the program.

Type codes accepted by `FfiSignature`:
  0 void, 1 i8, 2 u8, 3 i16, 4 u16, 5 i32, 6 u32,
  7 i64, 8 u64, 9 f32, 10 f64, 11 pointer, 12 C string, 13 bool.

## Memory
`signature` allocates an opaque `FfiSignature`; release it with `release`.
`call` writes into the caller-provided output; no allocation is retained.

---

### `FFI_CALL_VERSION`

> **FFI_CALL_VERSION** : string

_Undocumented._

### `FfiSignature`

> rune FfiSignature

```pengu
    _sig as opaque
```

_Undocumented._

### `ccx_ffi_sig_new`

> **ccx_ffi_sig_new**(ret: int, args: list of int) -> opaque

_Undocumented._

### `ccx_ffi_sig_free`

> **ccx_ffi_sig_free**(sig: opaque) -> void

_Undocumented._

### `ccx_ffi_call`

> **ccx_ffi_call**(sig: opaque, fn: ref to void, args: list of ref to void, out: ref to void) -> bool

_Undocumented._

### `ccx_ffi_ret_size`

> **ccx_ffi_ret_size**(sig: opaque) -> int

_Undocumented._

### `signature`

> **signature**(ret: int, args: list of int) -> result of FfiSignature to string

 Builds a call signature. The result owns the signature on success.

### `call`

> **call**(fn: ref to void, sig: ref to FfiSignature, args: list of ref to void, out: ref to void) -> bool

 Calls `fn` with `args` (each element is a pointer to the argument value) and
 stores the return value in `out`. The caller owns the signature and output.

### `ret_size`

> **ret_size**(sig: ref to FfiSignature) -> int

_Undocumented._

### `release`

> **release**() -> void

_Undocumented._

