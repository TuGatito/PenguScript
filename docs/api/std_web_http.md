# std.web.http

> Source: `std/web/http.pengu`

std.web.http — HTTP requests from WebAssembly.

This module is the `fetch`-based HTTP client for browser and worker builds.
The bridge delivers each response as an opaque `JsValue`; call
`response_from` to turn it into a `Response`, then `free` it.

```pengu
weave on_ok with value as js.JsValue into void:
    var r as result of http.Response to js.JsError is calling http.response_from with value
    if r.is_ok:
        if r.value.ok:
            calling spark.println with "{r.value.status} {r.value.body}"
        calling http.free with (sigil of r.value)

weave on_err with value as js.JsValue into void:
    var e as js.JsError is calling http.error_from with value
    calling spark.println with "{e.name}: {e.message}"
    banish e.name
    banish e.message
    banish e.stack

calling http.get with "https://example.com/data", on_ok, on_err
```

Requests send `credentials: "same-origin"`. Cross-origin cookies require an
explicit CORS policy on the server; this module never opts into
`include` implicitly.

Callbacks receive **borrowed** `JsValue` handles. The bridge releases them
when the callback returns, so copy anything you need into PenguScript values
(`response_from`, `error_from`) inside the callback.

---

### `JsError`

> alias JsError

_Undocumented._

### `Value`

> alias Value

_Undocumented._

### `HTTP_VERSION`

> **HTTP_VERSION** : string

_Undocumented._

### `Header`

> rune Header

```pengu
    name as string
    value as string
```

 One request header. The caller owns the strings.

### `Response`

> rune Response

```pengu
    status as int
    status_text as string
    ok as bool
    url as string
    redirected as bool
    body as string
    _headers as JsValue
```

 An HTTP response. `_headers` is owned; release it with `free`.

### `request`

> **request**(method: string, url: string, headers: list of Header, body: string, on_ok: weave with value: Value into void, on_err: weave with value: Value into void, timeout_ms: int) -> result of bool to JsError

_Undocumented._

### `get`

> **get**(url: string, on_ok: weave with value: Value into void, on_err: weave with value: Value into void, timeout_ms: int) -> result of bool to JsError

_Undocumented._

### `post`

> **post**(url: string, body: string, on_ok: weave with value: Value into void, on_err: weave with value: Value into void, timeout_ms: int) -> result of bool to JsError

_Undocumented._

### `put`

> **put**(url: string, body: string, on_ok: weave with value: Value into void, on_err: weave with value: Value into void, timeout_ms: int) -> result of bool to JsError

_Undocumented._

### `delete`

> **delete**(url: string, on_ok: weave with value: Value into void, on_err: weave with value: Value into void, timeout_ms: int) -> result of bool to JsError

_Undocumented._

### `response_from`

> **response_from**(value: JsValue) -> result of Response to JsError

_Undocumented._

### `error_from`

> **error_from**(value: JsValue) -> JsError

_Undocumented._

### `header`

> **header**(r: ref to Response, name: string) -> result of maybe string to JsError

_Undocumented._

### `json`

> **json**(r: ref to Response) -> result of JsValue to JsError

_Undocumented._

### `post_json`

> **post_json**(url: string, value: JsValue, on_ok: weave with value: Value into void, on_err: weave with value: Value into void, timeout_ms: int) -> result of bool to JsError

_Undocumented._

### `free`

> **free**(r: ref to Response) -> void

_Undocumented._

