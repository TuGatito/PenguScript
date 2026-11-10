# std.web.js

> Source: `std/web/js.pengu`

std.web.js — JavaScript interop for WebAssembly builds.

`JsValue` is an opaque handle: `0` is `undefined`, `1` is `null`, and every
other value is registered on the JavaScript side. Handles are owned: call
`release` when you are done, or `retain` before storing one past the current
callback. A released handle is invalid, never silently reused.

`JsCallback` bundles the JavaScript function handle with its C slot id. Pass
the callback to `free_callback` when it is no longer registered anywhere;
`dom.on`/`dom.off` and `websocket.close` do that for you.

Callback payloads are borrowed for the duration of the callback. If a
callback wants to keep a `JsValue` argument, it must call `retain`; otherwise
the bridge releases its reference when the callback returns.

Every public operation returns a `result` whose error carries the JavaScript
exception name, message, and stack. JavaScript exceptions never escape
through the C ABI.

This module is the only bridge that needs the Emscripten JS library. Native
builds get `NotSupported` stubs so the same application code still compiles.

---

### `JS_VERSION`

> **JS_VERSION** : string

_Undocumented._

### `JsValue`

> seal JsValue

_Undocumented._

### `UNDEFINED`

> **UNDEFINED** : JsValue

_Undocumented._

### `NULL`

> **NULL** : JsValue

_Undocumented._

### `JsError`

> rune JsError

```pengu
    name as string
    message as string
    stack as string
```

 A JavaScript exception, or a bridge failure.

### `JsCallback`

> rune JsCallback

```pengu
    _value as JsValue
    _slot as int
```

 A registered callback. `_value` is the JavaScript function handle and
 `_slot` is its C slot id; both are invalidated by `free_callback`.

### `FetchHandle`

> rune FetchHandle

```pengu
    id as int
```

 Handle de una petición `fetch` abortable. El bridge lo invalida al terminar,
 fallar, agotar el timeout o abortar.

### `Stats`

> rune Stats

```pengu
    handles as int
    callbacks as int
    sockets as int
```

 Live bridge counters, useful in tests and leak checks.

### `IS_WASM`

> **IS_WASM** : bool

_Undocumented._

### `_native_error`

> **_native_error**() -> JsError

 Native builds cannot reach JavaScript.

### `eval`

> **eval**(code: string) -> result of JsValue to JsError

_Undocumented._

### `global`

> **global**() -> JsValue

_Undocumented._

### `get`

> **get**(obj: JsValue, name: string) -> result of JsValue to JsError

_Undocumented._

### `set`

> **set**(obj: JsValue, name: string, value: JsValue) -> result of bool to JsError

_Undocumented._

### `get_index`

> **get_index**(obj: JsValue, index: int) -> result of JsValue to JsError

_Undocumented._

### `set_index`

> **set_index**(obj: JsValue, index: int, value: JsValue) -> result of bool to JsError

_Undocumented._

### `call`

> **call**(fn: JsValue, this_v: JsValue, args: list of JsValue) -> result of JsValue to JsError

_Undocumented._

### `call_method`

> **call_method**(obj: JsValue, name: string, args: list of JsValue) -> result of JsValue to JsError

_Undocumented._

### `call_method_f64`

> **call_method_f64**(obj: JsValue, name: string, a: f64, b: f64, c: f64, d: f64, e: f64, f: f64, count: int) -> result of JsValue to JsError

_Undocumented._

### `call_method_text_f64`

> **call_method_text_f64**(obj: JsValue, name: string, text: string, a: f64, b: f64) -> result of JsValue to JsError

_Undocumented._

### `new`

> **new**(ctor: JsValue, args: list of JsValue) -> result of JsValue to JsError

_Undocumented._

### `typeof`

> **typeof**(v: JsValue) -> result of string to JsError

_Undocumented._

### `is_undefined`

> **is_undefined**(v: JsValue) -> bool

_Undocumented._

### `is_null`

> **is_null**(v: JsValue) -> bool

_Undocumented._

### `is_valid`

> **is_valid**(v: JsValue) -> bool

_Undocumented._

### `is_truthy`

> **is_truthy**(v: JsValue) -> bool

_Undocumented._

### `to_string`

> **to_string**(v: JsValue) -> result of string to JsError

_Undocumented._

### `to_f64`

> **to_f64**(v: JsValue) -> result of f64 to JsError

_Undocumented._

### `to_i64`

> **to_i64**(v: JsValue) -> result of i64 to JsError

_Undocumented._

### `to_bool`

> **to_bool**(v: JsValue) -> bool

_Undocumented._

### `string`

> **string**(s: string) -> result of JsValue to JsError

_Undocumented._

### `from_f64`

> **from_f64**(n: f64) -> result of JsValue to JsError

_Undocumented._

### `from_int`

> **from_int**(n: int) -> result of JsValue to JsError

_Undocumented._

### `from_string`

> **from_string**(v: JsValue) -> result of string to JsError

_Undocumented._

### `object`

> **object**() -> result of JsValue to JsError

_Undocumented._

### `array`

> **array**() -> result of JsValue to JsError

_Undocumented._

### `length`

> **length**(v: JsValue) -> result of int to JsError

_Undocumented._

### `release`

> **release**(v: JsValue) -> void

_Undocumented._

### `retain`

> **retain**(v: JsValue) -> result of JsValue to JsError

_Undocumented._

### `make_callback`

> **make_callback**(fn: weave with arg: JsValue into void) -> result of JsCallback to JsError

_Undocumented._

### `free_callback`

> **free_callback**(cb: JsCallback) -> void

_Undocumented._

### `callback_value`

> **callback_value**(cb: JsCallback) -> JsValue

_Undocumented._

### `call_callback`

> **call_callback**(cb: ref to JsCallback, this_v: JsValue, args: list of JsValue) -> result of JsValue to JsError

_Undocumented._

### `make_string_callback`

> **make_string_callback**(fn: weave with text: string into void) -> result of int to JsError

_Undocumented._

### `free_string_callback`

> **free_string_callback**(slot: int) -> void

_Undocumented._

### `promise_then`

> **promise_then**(p: JsValue, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

_Undocumented._

### `import_module`

> **import_module**(url: string) -> result of JsValue to JsError

_Undocumented._

### `fetch`

> **fetch**(method: string, url: string, headers: JsValue, body: JsValue, on_ok: weave with res: JsValue into void, on_err: weave with e: JsValue into void, timeout_ms: int) -> result of bool to JsError

_Undocumented._

### `fetch_request`

> **fetch_request**(method: string, url: string, headers: JsValue, body: JsValue, on_ok: weave with res: JsValue into void, on_err: weave with e: JsValue into void, timeout_ms: int) -> result of FetchHandle to JsError

_Undocumented._

### `abort_request`

> **abort_request**(h: FetchHandle) -> result of bool to JsError

_Undocumented._

### `sha256_hex`

> **sha256_hex**(text: string, on_ok: weave with value: JsValue into void, on_err: weave with value: JsValue into void) -> result of bool to JsError

_Undocumented._

### `hmac_sha256_hex`

> **hmac_sha256_hex**(text: string, key: string, on_ok: weave with value: JsValue into void, on_err: weave with value: JsValue into void) -> result of bool to JsError

_Undocumented._

### `file_pick_text`

> **file_pick_text**(accept: string, on_ok: weave with value: JsValue into void, on_err: weave with value: JsValue into void) -> result of bool to JsError

_Undocumented._

### `file_read_text`

> **file_read_text**(file: JsValue, on_ok: weave with value: JsValue into void, on_err: weave with value: JsValue into void) -> result of bool to JsError

_Undocumented._

### `file_read_data_url`

> **file_read_data_url**(file: JsValue, on_ok: weave with value: JsValue into void, on_err: weave with value: JsValue into void) -> result of bool to JsError

_Undocumented._

### `file_save_text`

> **file_save_text**(text: string, name: string, mime: string) -> result of bool to JsError

_Undocumented._

### `clipboard_write_text`

> **clipboard_write_text**(text: string, on_ok: weave with value: JsValue into void, on_err: weave with value: JsValue into void) -> result of bool to JsError

_Undocumented._

### `clipboard_read_text`

> **clipboard_read_text**(on_ok: weave with value: JsValue into void, on_err: weave with value: JsValue into void) -> result of bool to JsError

_Undocumented._

### `ws_open`

> **ws_open**(url: string, on_open: weave with text: string into void, on_message: weave with text: string into void, on_close: weave with text: string into void, on_error: weave with text: string into void) -> result of int to JsError

_Undocumented._

### `ws_send`

> **ws_send**(id: int, text: string) -> result of bool to JsError

_Undocumented._

### `ws_close`

> **ws_close**(id: int, code: int, reason: string) -> result of bool to JsError

_Undocumented._

### `ws_state`

> **ws_state**(id: int) -> int

_Undocumented._

### `ws_count`

> **ws_count**() -> int

_Undocumented._

### `canvas_call`

> **canvas_call**(ctx: JsValue, method: string, a: f64, b: f64, c: f64, d: f64) -> result of JsValue to JsError

_Undocumented._

### `canvas_text`

> **canvas_text**(ctx: JsValue, method: string, text: string, a: f64, b: f64) -> result of JsValue to JsError

_Undocumented._

### `keys`

> **keys**(v: JsValue) -> result of JsValue to JsError

_Undocumented._

### `random_bytes`

> **random_bytes**(count: int) -> result of JsValue to JsError

_Undocumented._

### `random_int`

> **random_int**(min: int, max: int) -> result of int to JsError

_Undocumented._

### `parse_json`

> **parse_json**(text: string) -> result of JsValue to JsError

_Undocumented._

### `stringify_json`

> **stringify_json**(v: JsValue) -> result of string to JsError

_Undocumented._

### `last_error`

> **last_error**() -> JsError

_Undocumented._

### `stats`

> **stats**() -> Stats

_Undocumented._

