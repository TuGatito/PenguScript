# std.web.url

> Source: `std/web/url.pengu`

std.web.url — URL parsing, building and percent encoding.

Pure PenguScript; works in native and wasm builds. The parser handles the
common hierarchical forms (`scheme://userinfo@host:port/path?query#fragment`)
and relative references. It is intentionally strict about malformed input and
never evaluates or resolves a URL.

```pengu
var u as result of url.Url to string is calling url.parse with "/docs?q=pengu"
if u.is_ok:
    var q as maybe string is calling url.query_get with u.value.query, "q"
```

`decode_component` rejects malformed percent escapes instead of silently
dropping them. `encode_component` encodes every byte outside the RFC 3986
unreserved set.

---

### `URL_VERSION`

> **URL_VERSION** : string

_Undocumented._

### `Url`

> rune Url

```pengu
    scheme as string
    userinfo as string
    host as string
    port as string
    path as string
    query as string
    fragment as string
```

 A parsed absolute or relative URL reference.

### `Param`

> rune Param

```pengu
    name as string
    value as string
```

 One decoded query parameter.

### `parse`

> **parse**(raw: string) -> result of Url to string

 Parses `raw` into its components. Relative references keep an empty scheme
 and host. Returns the offending text in the error message.

### `to_string`

> **to_string**(u: Url) -> string

 Builds a URL string. Empty components are omitted.

### `origin`

> **origin**(u: Url) -> string

 `scheme://host[:port]`, or the input's prefix when there is no authority.

### `with_path`

> **with_path**(u: Url, path: string) -> Url

 Replaces the path component.

### `with_query`

> **with_query**(u: Url, query: string) -> Url

 Replaces the query component (without `?`).

### `encode_component`

> **encode_component**(text: string) -> string

 Percent-encodes one component. Unreserved characters are left as-is.

### `decode_component`

> **decode_component**(text: string) -> result of string to string

 Decodes percent escapes. `+` is left untouched; use `query_get` for forms.

### `params`

> **params**(query: string) -> list of Param

 Splits a query string into decoded parameters. Malformed pairs are skipped.

### `query_get`

> **query_get**(query: string, name: string) -> maybe string

 Returns the first value of `name`, decoded.

### `query_set`

> **query_set**(query: string, name: string, value: string) -> string

 Returns `query` with `name=value` set (replacing the first occurrence).

### `query_remove`

> **query_remove**(query: string, name: string) -> string

 Returns `query` without `name`.

### `_slice`

> **_slice**(text: string, start: int, end: int) -> string

 Slices `text` from `start` (inclusive) to `end` (exclusive).

### `_is_scheme`

> **_is_scheme**(text: string) -> bool

 True for `[A-Za-z][A-Za-z0-9+.-]*`.

### `_is_unreserved`

> **_is_unreserved**(c: int) -> bool

 True for RFC 3986 unreserved bytes.

### `_hex`

> **_hex**(c: int) -> string

 Two uppercase hex digits.

### `_hex_value`

> **_hex_value**(ch: string) -> int

 Value of one hex digit, or -1.

### `_utf8_char`

> **_utf8_char**(code: int) -> string

 Decodes one UTF-8 code point as a string.

### `_byte_char`

> **_byte_char**(code: int) -> string

 Builds a one-byte string without going through char literals.

### `_decode_form`

> **_decode_form**(text: string) -> result of string to string

 Decodes form data: `+` becomes a space before percent decoding.

### `_free_parts`

> **_free_parts**(parts: list of string) -> void

 Releases the strings in a split list.

