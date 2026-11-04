# std.web.security

> Source: `std/web/security.pengu`

std.web.security — defensive helpers for browser-facing strings.

These functions are pure: no JavaScript, no allocation beyond the strings
they return. They are deliberately conservative. `is_safe_url` rejects
`javascript:`, `vbscript:`, control characters, and every `data:` URL except
the raster image forms that cannot execute script. `escape_html` is the
correct tool when you must build markup; prefer `dom.set_text` otherwise.

`dom.set_attr` uses the same policy for URL-valued attributes, so callers
that already validated a URL do not need to repeat the check.

---

### `SECURITY_VERSION`

> **SECURITY_VERSION** : string

 std.web.security — defensive helpers for browser-facing strings.

 These functions are pure: no JavaScript, no allocation beyond the strings
 they return. They are deliberately conservative. `is_safe_url` rejects
 `javascript:`, `vbscript:`, control characters, and every `data:` URL except
 the raster image forms that cannot execute script. `escape_html` is the
 correct tool when you must build markup; prefer `dom.set_text` otherwise.

 `dom.set_attr` uses the same policy for URL-valued attributes, so callers
 that already validated a URL do not need to repeat the check.

### `is_safe_url`

> **is_safe_url**(url: string) -> bool

 True when `url` may be used as an `href`, `src`, or `action` without
 executing script. Relative URLs are allowed; unknown schemes are not.

### `escape_html`

> **escape_html**(text: string) -> string

 Escapes the five HTML-significant characters. The returned string is owned
 by the caller.

### `starts_with_ignore_case`

> **starts_with_ignore_case**(text: string, prefix: string) -> bool

 True when `text` starts with `prefix`, ignoring ASCII case.

### `ends_with_ignore_case`

> **ends_with_ignore_case**(text: string, suffix: string) -> bool

 True when `text` ends with `suffix`, ignoring ASCII case.

### `_lower_byte`

> **_lower_byte**(c: int) -> int

 Lowercases one ASCII byte; other bytes are returned unchanged.

### `_scheme_is`

> **_scheme_is**(text: string, start: int, length: int, expected: string) -> bool

 Compares a slice of `text` with `expected`, ignoring ASCII case.

### `_is_safe_data_image`

> **_is_safe_data_image**(text: string, start: int, end: int) -> bool

 Only raster image data URLs are allowed; SVG and HTML can execute script.

