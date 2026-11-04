# std.web.history

> Source: `std/web/history.pengu`

std.web.history — the `window.history` object.

WebAssembly-only. `push_state`/`replace_state` store a caller-provided
`JsValue` (use `js.object` or `js.parse_json`); the history entry keeps a
retained reference and `state` returns a new owned handle.

```pengu
var s as result of js.JsValue to js.JsError is calling js.parse_json with "{\"page\":1}"
if s.is_ok:
    var r as result of bool to js.JsError is calling history.push_state with s.value, "", "/page/1"
```

---

### `HISTORY_VERSION`

> **HISTORY_VERSION** : string

_Undocumented._

### `length`

> **length**() -> result of int to JsError

_Undocumented._

### `state`

> **state**() -> result of JsValue to JsError

_Undocumented._

### `push_state`

> **push_state**(value: JsValue, title: string, target: string) -> result of bool to JsError

_Undocumented._

### `replace_state`

> **replace_state**(value: JsValue, title: string, target: string) -> result of bool to JsError

_Undocumented._

### `back`

> **back**() -> result of bool to JsError

_Undocumented._

### `forward`

> **forward**() -> result of bool to JsError

_Undocumented._

### `go`

> **go**(delta: int) -> result of bool to JsError

_Undocumented._

### `on_pop`

> **on_pop**(cb: weave with ev: JsValue into void) -> result of Listener to JsError

_Undocumented._

### `off`

> **off**(l: ref to Listener) -> void

_Undocumented._

