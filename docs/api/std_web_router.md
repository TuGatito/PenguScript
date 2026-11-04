# std.web.router

> Source: `std/web/router.pengu`

std.web.router — hash-based client-side routing.

WebAssembly-only. A route is a path pattern with literal segments, `:name`
captures and an optional trailing `*` wildcard. `match` returns the captured
`url.Param` list; `navigate` changes `location.hash`; `on_change` subscribes
to `hashchange` and returns a `dom.Listener`.

```pengu
var m as maybe list of url.Param is calling router.match with "/users/:id", "/users/42"
if m is present:
    var id as maybe string is calling router.param with m.value, "id"
```

The router does not render anything by itself; pair it with `dom` and a
`hashchange` listener to build a single-page application.

---

### `ROUTER_VERSION`

> **ROUTER_VERSION** : string

_Undocumented._

### `match`

> **match**(pattern: string, path: string) -> maybe list of Param

_Undocumented._

### `param`

> **param**(params: list of Param, name: string) -> maybe string

_Undocumented._

### `free_params`

> **free_params**(params: list of Param) -> void

_Undocumented._

### `current_path`

> **current_path**() -> result of string to JsError

_Undocumented._

### `navigate`

> **navigate**(path: string) -> result of bool to JsError

_Undocumented._

### `on_change`

> **on_change**(cb: weave with ev: JsValue into void) -> result of Listener to JsError

_Undocumented._

### `off`

> **off**(l: ref to Listener) -> void

_Undocumented._

