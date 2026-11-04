# std.web.clipboard

> Source: `std/web/clipboard.pengu`

std.web.clipboard — read and write the system clipboard.

WebAssembly-only. The API is asynchronous and permission-gated by the
browser; both directions take a one-shot raw `JsValue` callback pair.

```pengu
weaving on_ok with value as js.JsValue into void:
    calling std.web.console_log with "copied"
calling clipboard.write with "hola", on_ok, on_error
```

Browsers require a secure context (HTTPS or `localhost`) and usually a user
gesture.

---

### `Value`

> alias Value

_Undocumented._

### `CLIPBOARD_VERSION`

> **CLIPBOARD_VERSION** : string

_Undocumented._

### `write`

> **write**(text: string, on_ok: weave with value: Value into void, on_err: weave with value: Value into void) -> result of bool to JsError

_Undocumented._

### `read`

> **read**(on_ok: weave with value: Value into void, on_err: weave with value: Value into void) -> result of bool to JsError

_Undocumented._

### `text_from`

> **text_from**(value: JsValue) -> result of string to JsError

_Undocumented._

### `error_from`

> **error_from**(value: JsValue) -> JsError

_Undocumented._

