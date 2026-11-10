# std.web.dom

> Source: `std/web/dom.pengu`

std.web.dom — DOM access for WebAssembly applications.

`Element` owns one JavaScript handle. Release it with `free` when the element
is no longer needed; `query` and `create` return owned elements. A
`Listener` owns the element reference and the callback, so `off` (or
`free_listener`) releases both.

`query` returns `maybe Element`: a missing selector is absence, not an error.
That distinction is what makes routing and form handling predictable.

`set_attr` applies `std.web.security.is_safe_url` to `href`, `src`, `action`,
`formaction`, `poster`, and `cite`. Use `set_attr_unsafe` only for values you
built yourself from a trusted allowlist.

---

### `DOM_VERSION`

> **DOM_VERSION** : string

_Undocumented._

### `EventArg`

> alias EventArg

_Undocumented._

### `Element`

> rune Element

```pengu
    _v as JsValue
```

 An element handle. Private field: use the module functions.

### `Listener`

> rune Listener

```pengu
    _element as JsValue
    _event as string
    _callback as JsCallback
```

 A registered event listener. `off` frees it.

### `Rect`

> rune Rect

```pengu
    x as f64
    y as f64
    width as f64
    height as f64
```

 A layout rectangle in CSS pixels.

### `wrap`

> **wrap**(v: JsValue) -> result of Element to JsError

_Undocumented._

### `document`

> **document**() -> result of Element to JsError

_Undocumented._

### `window`

> **window**() -> result of Element to JsError

_Undocumented._

### `body`

> **body**() -> result of Element to JsError

_Undocumented._

### `head`

> **head**() -> result of Element to JsError

_Undocumented._

### `query`

> **query**(selector: string) -> result of maybe Element to JsError

_Undocumented._

### `query_required`

> **query_required**(selector: string) -> result of Element to JsError

_Undocumented._

### `query_all`

> **query_all**(selector: string) -> result of list of Element to JsError

_Undocumented._

### `create`

> **create**(tag: string) -> result of Element to JsError

_Undocumented._

### `create_text`

> **create_text**(text: string) -> result of Element to JsError

_Undocumented._

### `free`

> **free**(e: ref to Element) -> void

_Undocumented._

### `create_fragment`

> **create_fragment**() -> result of Element to JsError

_Undocumented._

### `create_comment`

> **create_comment**(text: string) -> result of Element to JsError

_Undocumented._

### `template_content`

> **template_content**(e: Element) -> result of maybe Element to JsError

_Undocumented._

### `parent`

> **parent**(e: Element) -> result of maybe Element to JsError

_Undocumented._

### `children`

> **children**(e: Element) -> result of list of Element to JsError

_Undocumented._

### `closest`

> **closest**(e: Element, selector: string) -> result of maybe Element to JsError

_Undocumented._

### `query_all_under`

> **query_all_under**(root: Element, selector: string) -> result of list of Element to JsError

_Undocumented._

### `matches`

> **matches**(e: Element, selector: string) -> result of bool to JsError

_Undocumented._

### `append_fragment`

> **append_fragment**(parent: Element, frag: Element) -> result of bool to JsError

_Undocumented._

### `clone`

> **clone**(e: Element) -> result of Element to JsError

_Undocumented._

### `text`

> **text**(e: Element) -> result of string to JsError

_Undocumented._

### `set_text`

> **set_text**(e: Element, text: string) -> result of bool to JsError

_Undocumented._

### `html`

> **html**(e: Element) -> result of string to JsError

_Undocumented._

### `set_html_unsafe`

> **set_html_unsafe**(e: Element, text: string) -> result of bool to JsError

_Undocumented._

### `get_attr`

> **get_attr**(e: Element, name: string) -> result of maybe string to JsError

_Undocumented._

### `attribute_names`

> **attribute_names**(e: Element) -> result of list of string to JsError

_Undocumented._

### `set_attr`

> **set_attr**(e: Element, name: string, value: string) -> result of bool to JsError

_Undocumented._

### `set_attr_unsafe`

> **set_attr_unsafe**(e: Element, name: string, value: string) -> result of bool to JsError

_Undocumented._

### `remove_attr`

> **remove_attr**(e: Element, name: string) -> result of bool to JsError

_Undocumented._

### `has_attr`

> **has_attr**(e: Element, name: string) -> result of bool to JsError

_Undocumented._

### `add_class`

> **add_class**(e: Element, name: string) -> result of bool to JsError

_Undocumented._

### `remove_class`

> **remove_class**(e: Element, name: string) -> result of bool to JsError

_Undocumented._

### `toggle_class`

> **toggle_class**(e: Element, name: string) -> result of bool to JsError

_Undocumented._

### `has_class`

> **has_class**(e: Element, name: string) -> result of bool to JsError

_Undocumented._

### `style`

> **style**(e: Element, name: string) -> result of maybe string to JsError

_Undocumented._

### `set_style`

> **set_style**(e: Element, name: string, value: string) -> result of bool to JsError

_Undocumented._

### `dataset`

> **dataset**(e: Element, name: string) -> result of maybe string to JsError

_Undocumented._

### `set_dataset`

> **set_dataset**(e: Element, name: string, value: string) -> result of bool to JsError

_Undocumented._

### `insert_before`

> **insert_before**(parent: Element, child: Element, reference: maybe Element) -> result of bool to JsError

_Undocumented._

### `append`

> **append**(parent: Element, child: Element) -> result of bool to JsError

_Undocumented._

### `prepend`

> **prepend**(parent: Element, child: Element) -> result of bool to JsError

_Undocumented._

### `remove`

> **remove**(e: Element) -> result of bool to JsError

_Undocumented._

### `replace_with`

> **replace_with**(e: Element, other: Element) -> result of bool to JsError

_Undocumented._

### `on`

> **on**(e: Element, event_name: string, cb: weave with ev: EventArg into void) -> result of Listener to JsError

_Undocumented._

### `once`

> **once**(e: Element, event_name: string, cb: weave with ev: EventArg into void) -> result of Listener to JsError

_Undocumented._

### `off`

> **off**(l: ref to Listener) -> result of bool to JsError

_Undocumented._

### `free_listener`

> **free_listener**(l: ref to Listener) -> void

_Undocumented._

### `value`

> **value**(e: Element) -> result of maybe string to JsError

_Undocumented._

### `set_value`

> **set_value**(e: Element, value: string) -> result of bool to JsError

_Undocumented._

### `checked`

> **checked**(e: Element) -> bool

_Undocumented._

### `set_checked`

> **set_checked**(e: Element, checked: bool) -> result of bool to JsError

_Undocumented._

### `focus`

> **focus**(e: Element) -> result of bool to JsError

_Undocumented._

### `blur`

> **blur**(e: Element) -> result of bool to JsError

_Undocumented._

### `click`

> **click**(e: Element) -> result of bool to JsError

_Undocumented._

### `rect`

> **rect**(e: Element) -> result of Rect to JsError

_Undocumented._

### `client_width`

> **client_width**(e: Element) -> result of int to JsError

_Undocumented._

### `client_height`

> **client_height**(e: Element) -> result of int to JsError

_Undocumented._

### `offset_width`

> **offset_width**(e: Element) -> result of int to JsError

_Undocumented._

### `offset_height`

> **offset_height**(e: Element) -> result of int to JsError

_Undocumented._

### `scroll_into_view`

> **scroll_into_view**(e: Element) -> result of bool to JsError

_Undocumented._

### `form_data`

> **form_data**(e: Element) -> result of JsValue to JsError

_Undocumented._

### `is_connected`

> **is_connected**(e: Element) -> bool

_Undocumented._

### `tag_name`

> **tag_name**(e: Element) -> result of string to JsError

_Undocumented._

### `raw`

> **raw**(e: Element) -> JsValue

_Undocumented._

