# std.web.location

> Source: `std/web/location.pengu`

std.web.location — the `window.location` object.

WebAssembly-only. Read URL components, navigate with `assign`/`replace`, or
parse `search` with `std.web.url`. `assign` and `replace` reject schemes
outside the `std.web.security` allow-list (`javascript:`, unknown schemes),
matching the policy used by `dom.set_attr` and `browser.open_url`.

```pengu
var path as result of string to js.JsError is calling location.pathname
if path.is_ok:
    calling std.web.console_log with path.value
```

---

### `LOCATION_VERSION`

> **LOCATION_VERSION** : string

_Undocumented._

### `href`

> **href**() -> result of string to JsError

_Undocumented._

### `origin`

> **origin**() -> result of string to JsError

_Undocumented._

### `protocol`

> **protocol**() -> result of string to JsError

_Undocumented._

### `host`

> **host**() -> result of string to JsError

_Undocumented._

### `hostname`

> **hostname**() -> result of string to JsError

_Undocumented._

### `port`

> **port**() -> result of string to JsError

_Undocumented._

### `pathname`

> **pathname**() -> result of string to JsError

_Undocumented._

### `search`

> **search**() -> result of string to JsError

_Undocumented._

### `hash`

> **hash**() -> result of string to JsError

_Undocumented._

### `search_params`

> **search_params**() -> result of list of Param to JsError

_Undocumented._

### `assign`

> **assign**(target: string) -> result of bool to JsError

_Undocumented._

### `replace`

> **replace**(target: string) -> result of bool to JsError

_Undocumented._

### `reload`

> **reload**() -> result of bool to JsError

_Undocumented._

### `set_hash`

> **set_hash**(fragment: string) -> result of bool to JsError

_Undocumented._

### `handle`

> **handle**() -> result of JsValue to JsError

_Undocumented._

