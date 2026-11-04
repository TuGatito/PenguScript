# std.web.event

> Source: `std/web/event.pengu`

std.web.event — typed accessors for DOM events.

`Event` is the same handle as `js.JsValue`; the alias exists so signatures
read as events and so `dom.on` can pass the callback payload through without
an adapter. Accessors copy the fields you ask for and leave the handle
borrowed: do not release it, and call `js.retain` before storing it.

Use `dom.wrap` on `event.target` when you need an `Element`.

---

### `EVENT_VERSION`

> **EVENT_VERSION** : string

_Undocumented._

### `Event`

> alias Event

_Undocumented._

### `kind`

> **kind**(e: Event) -> result of string to JsError

_Undocumented._

### `target`

> **target**(e: Event) -> result of JsValue to JsError

_Undocumented._

### `current_target`

> **current_target**(e: Event) -> result of JsValue to JsError

_Undocumented._

### `key`

> **key**(e: Event) -> result of maybe string to JsError

_Undocumented._

### `code`

> **code**(e: Event) -> result of maybe string to JsError

_Undocumented._

### `button`

> **button**(e: Event) -> result of int to JsError

_Undocumented._

### `client_x`

> **client_x**(e: Event) -> result of int to JsError

_Undocumented._

### `client_y`

> **client_y**(e: Event) -> result of int to JsError

_Undocumented._

### `page_x`

> **page_x**(e: Event) -> result of int to JsError

_Undocumented._

### `page_y`

> **page_y**(e: Event) -> result of int to JsError

_Undocumented._

### `delta_y`

> **delta_y**(e: Event) -> result of f64 to JsError

_Undocumented._

### `data`

> **data**(e: Event) -> result of maybe string to JsError

_Undocumented._

### `clipboard_text`

> **clipboard_text**(e: Event) -> result of maybe string to JsError

_Undocumented._

### `is_alt`

> **is_alt**(e: Event) -> bool

_Undocumented._

### `is_ctrl`

> **is_ctrl**(e: Event) -> bool

_Undocumented._

### `is_meta`

> **is_meta**(e: Event) -> bool

_Undocumented._

### `is_shift`

> **is_shift**(e: Event) -> bool

_Undocumented._

### `is_trusted`

> **is_trusted**(e: Event) -> bool

_Undocumented._

### `prevent_default`

> **prevent_default**(e: Event) -> result of bool to JsError

_Undocumented._

### `stop_propagation`

> **stop_propagation**(e: Event) -> result of bool to JsError

_Undocumented._

### `stop_immediate`

> **stop_immediate**(e: Event) -> result of bool to JsError

_Undocumented._

