# std.web.websocket

> Source: `std/web/websocket.pengu`

std.web.websocket — typed WebSocket client.

WebAssembly-only. Open a socket, then send or close it. Callbacks are driven
by the JS event loop; keep the runtime alive with `std.web.set_main_loop`.
Callback strings are borrowed for the duration of the call.

```pengu
weave on_open with text as string into void:
    calling spark.println with "open"

weave on_message with text as string into void:
    calling spark.println with "message: {text}"

weave on_close with text as string into void:
    calling spark.println with "close: {text}"

weave on_error with text as string into void:
    calling spark.println with "error: {text}"

var s as result of websocket.Socket to js.JsError is calling websocket.open with "wss://example.com/ws", on_open, on_message, on_close, on_error
```

The four callbacks are one-shot or connection-scoped: the bridge releases
their slots when the socket closes or fails. Do not retain the `Socket` after
`close`; a new `open` creates a new id.

---

### `WEBSOCKET_VERSION`

> **WEBSOCKET_VERSION** : string

_Undocumented._

### `CONNECTING`

> **CONNECTING** : int

 State values returned by `state`.

### `OPEN`

> **OPEN** : int

_Undocumented._

### `CLOSING`

> **CLOSING** : int

_Undocumented._

### `CLOSED`

> **CLOSED** : int

_Undocumented._

### `Socket`

> rune Socket

```pengu
    _id as int
```

 A live WebSocket connection.

### `_native_error`

> **_native_error**() -> JsError

_Undocumented._

### `open`

> **open**(url: string, on_open: weave with text: string into void, on_message: weave with text: string into void, on_close: weave with text: string into void, on_error: weave with text: string into void) -> result of Socket to JsError

_Undocumented._

### `send`

> **send**(s: ref to Socket, text: string) -> result of bool to JsError

_Undocumented._

### `close`

> **close**(s: ref to Socket, code: int, reason: string) -> result of bool to JsError

_Undocumented._

### `state`

> **state**(s: ref to Socket) -> int

_Undocumented._

### `count`

> **count**() -> int

_Undocumented._

