# std.web.file

> Source: `std/web/file.pengu`

std.web.file — browser file picking, reading and downloads.

WebAssembly-only. Reading is asynchronous and takes a raw `JsValue` callback
pair; turn the payload into text with `text_from`. `save_text` triggers a
normal browser download and is synchronous.

```pengu
weave on_text with value as js.JsValue into void:
    var t as result of string to js.JsError is calling file.text_from with value
    if t.is_ok:
        calling std.web.console_log with t.value
        banish t.value

calling file.pick_text with "text/*", on_text, on_error
```

---

### `Value`

> alias Value

_Undocumented._

### `FILE_VERSION`

> **FILE_VERSION** : string

_Undocumented._

### `pick_text`

> **pick_text**(accept: string, on_ok: weave with value: Value into void, on_err: weave with value: Value into void) -> result of bool to JsError

_Undocumented._

### `read_text`

> **read_text**(handle: JsValue, on_ok: weave with value: Value into void, on_err: weave with value: Value into void) -> result of bool to JsError

_Undocumented._

### `read_data_url`

> **read_data_url**(handle: JsValue, on_ok: weave with value: Value into void, on_err: weave with value: Value into void) -> result of bool to JsError

_Undocumented._

### `save_text`

> **save_text**(text: string, name: string, mime: string) -> result of bool to JsError

_Undocumented._

### `text_from`

> **text_from**(value: JsValue) -> result of string to JsError

_Undocumented._

### `error_from`

> **error_from**(value: JsValue) -> JsError

_Undocumented._

