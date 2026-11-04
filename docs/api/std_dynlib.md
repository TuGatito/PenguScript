# std.dynlib

> Source: `std/dynlib.pengu`

std/dynlib.pengu — portable dynamic-library loading.

POSIX uses `dlopen`/`dlsym`/`dlclose`; Windows uses
`LoadLibraryA`/`GetProcAddress`/`FreeLibrary`.  Loading native code is a
capability: never pass a path or symbol controlled by untrusted input.

## Memory
`Library` owns one native handle; call `close` exactly once.

---

### `Library`

> rune Library

```pengu
    _handle as opaque
```

_Undocumented._

### `ccx_dyn_open`

> **ccx_dyn_open**(path: ref to frozen char) -> opaque

_Undocumented._

### `ccx_dyn_symbol`

> **ccx_dyn_symbol**(handle: opaque, name: ref to frozen char) -> ref to void

_Undocumented._

### `ccx_dyn_close`

> **ccx_dyn_close**(handle: opaque) -> void

_Undocumented._

### `open`

> **open**(path: string) -> result of Library to string

_Undocumented._

### `symbol`

> **symbol**(lib: ref to Library, name: string) -> result of ref to void to string

_Undocumented._

### `close`

> **close**(lib: ref to Library) -> void

_Undocumented._

### `ffi_cstr`

> **ffi_cstr**(s: string) -> ref to frozen char

 C string view helper; the pointer is valid for the duration of the call.

