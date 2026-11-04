# std.web.storage

> Source: `std/web/storage.pengu`

std.web.storage — localStorage and sessionStorage helpers.

WebAssembly-only (the browser provides the Storage API). Values are strings;
missing keys return `none`. `keys` returns owned strings: banish every entry
and then banish the list.

```pengu
calling storage.local_set with "theme", "dark"
var theme as result of maybe string to js.JsError is calling storage.local_get with "theme"
if theme.is_ok and theme.value is present:
    calling spark.println with theme.value.value
```

Quota errors surface as `JsError` with name `QuotaExceededError`; they are not
swallowed.

---

### `STORAGE_VERSION`

> **STORAGE_VERSION** : string

_Undocumented._

### `LOCAL`

> **LOCAL** : int

 Storage area selector.

### `SESSION`

> **SESSION** : int

_Undocumented._

### `_native_error`

> **_native_error**() -> JsError

_Undocumented._

### `_fail_maybe`

> **_fail_maybe**() -> result of maybe string to JsError

_Undocumented._

### `_fail_bool`

> **_fail_bool**() -> result of bool to JsError

_Undocumented._

### `_fail_int`

> **_fail_int**() -> result of int to JsError

_Undocumented._

### `_fail_list`

> **_fail_list**() -> result of list of string to JsError

_Undocumented._

### `_fail_value`

> **_fail_value**() -> result of JsValue to JsError

_Undocumented._

### `local_get`

> **local_get**(key: string) -> result of maybe string to JsError

_Undocumented._

### `local_set`

> **local_set**(key: string, value: string) -> result of bool to JsError

_Undocumented._

### `local_remove`

> **local_remove**(key: string) -> result of bool to JsError

_Undocumented._

### `local_clear`

> **local_clear**() -> result of bool to JsError

_Undocumented._

### `local_length`

> **local_length**() -> result of int to JsError

_Undocumented._

### `local_key_at`

> **local_key_at**(index: int) -> result of maybe string to JsError

_Undocumented._

### `local_keys`

> **local_keys**() -> result of list of string to JsError

_Undocumented._

### `session_get`

> **session_get**(key: string) -> result of maybe string to JsError

_Undocumented._

### `session_set`

> **session_set**(key: string, value: string) -> result of bool to JsError

_Undocumented._

### `session_remove`

> **session_remove**(key: string) -> result of bool to JsError

_Undocumented._

### `session_clear`

> **session_clear**() -> result of bool to JsError

_Undocumented._

### `session_length`

> **session_length**() -> result of int to JsError

_Undocumented._

### `session_key_at`

> **session_key_at**(index: int) -> result of maybe string to JsError

_Undocumented._

### `session_keys`

> **session_keys**() -> result of list of string to JsError

_Undocumented._

### `get_json`

> **get_json**(area: int, key: string) -> result of JsValue to JsError

_Undocumented._

### `set_json`

> **set_json**(area: int, key: string, value: JsValue) -> result of bool to JsError

_Undocumented._

### `local_set_json`

> **local_set_json**(key: string, value: JsValue) -> result of bool to JsError

_Undocumented._

### `local_get_json`

> **local_get_json**(key: string) -> result of JsValue to JsError

_Undocumented._

### `session_set_json`

> **session_set_json**(key: string, value: JsValue) -> result of bool to JsError

_Undocumented._

### `session_get_json`

> **session_get_json**(key: string) -> result of JsValue to JsError

_Undocumented._

### `free_keys`

> **free_keys**(keys: list of string) -> void

_Undocumented._

