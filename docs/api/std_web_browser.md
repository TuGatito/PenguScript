# std.web.browser

> Source: `std/web/browser.pengu`

std.web.browser — window-level browser APIs.

WebAssembly-only. Geometry, scrolling, viewport metrics, simple dialogs,
safe navigation and window event subscriptions. Event callbacks receive the
raw event handle as `js.JsValue`; use `std.web.event` to read it.

```pengu
weave on_resize with ev as js.JsValue into void:
    var w as result of browser.inner_width to js.JsError is calling browser.inner_width
    if w.is_ok:
        calling std.web.console_log with "width {w.value}"
```

Window listeners are `dom.Listener` values. Always pair `on_*` with
`dom.off` (or `browser.off`) so the callback slot and retained window handle
are released.

---

### `BROWSER_VERSION`

> **BROWSER_VERSION** : string

_Undocumented._

### `inner_width`

> **inner_width**() -> result of f64 to JsError

_Undocumented._

### `inner_height`

> **inner_height**() -> result of f64 to JsError

_Undocumented._

### `scroll_x`

> **scroll_x**() -> result of f64 to JsError

_Undocumented._

### `scroll_y`

> **scroll_y**() -> result of f64 to JsError

_Undocumented._

### `device_pixel_ratio`

> **device_pixel_ratio**() -> result of f64 to JsError

_Undocumented._

### `alert`

> **alert**(message: string) -> result of bool to JsError

_Undocumented._

### `confirm`

> **confirm**(message: string) -> result of bool to JsError

_Undocumented._

### `prompt`

> **prompt**(message: string, default_text: string) -> result of maybe string to JsError

_Undocumented._

### `open_url`

> **open_url**(url: string) -> result of bool to JsError

_Undocumented._

### `reload`

> **reload**() -> result of bool to JsError

_Undocumented._

### `scroll_to`

> **scroll_to**(x: f64, y: f64) -> result of bool to JsError

_Undocumented._

### `scroll_by`

> **scroll_by**(x: f64, y: f64) -> result of bool to JsError

_Undocumented._

### `match_media`

> **match_media**(query: string) -> result of bool to JsError

_Undocumented._

### `on_resize`

> **on_resize**(cb: weave with ev: JsValue into void) -> result of Listener to JsError

_Undocumented._

### `on_scroll`

> **on_scroll**(cb: weave with ev: JsValue into void) -> result of Listener to JsError

_Undocumented._

### `on_visibility`

> **on_visibility**(cb: weave with ev: JsValue into void) -> result of Listener to JsError

_Undocumented._

### `visibility_state`

> **visibility_state**() -> result of string to JsError

_Undocumented._

### `off`

> **off**(l: ref to Listener) -> void

_Undocumented._

