# std.petitio

> Source: `std/petitio.pengu`

std/petitio.pengu — a high-level HTTP client with a `requests`-shaped API.

`std.petitio` (Latin *petitio*, "a request") is PenguScript's HTTP client.
It is an explicit, `result`-returning wrapper over **libcurl**:
GET/POST/PUT/DELETE/HEAD/PATCH/OPTIONS, custom headers, JSON and
form-urlencoded bodies, multipart/form-data, query strings, URL parsing,
total and connect timeouts, redirect control, TLS verification, Basic /
Digest / negotiated authentication, Bearer tokens, HTTP and SOCKS proxies,
HTTP/1.0, HTTP/1.1 and HTTP/2 (ALPN or prior knowledge), streaming downloads
to a file or a callback, concurrent batches with `fetch_many`, per-response
body caps, sessions with cookies (including `Expires`), and a `Response` that
can parse JSON.

## Why libcurl and not naett

`naett` (single header, MIT) was evaluated first. Its public API cannot
express what this module promises: `naettTimeout` is a *connect* timeout only,
redirects are hard-wired on with no limit, there is no cookie control, no TLS
toggle, no proxy, no multipart, and duplicate response headers (every
`Set-Cookie` after the first) are lost. Its Linux backend is libcurl anyway, so
it never removed the dependency — and the vendored copy did not compile under
this repository's `-std=c99 -Wall -Wextra -Werror` gate. libcurl (`curl`
licence, MIT-like) is preinstalled on Linux, macOS and every CI image used
here, and exposes every knob documented below. See `docs/PETITIO.md`
§"Why libcurl" for the full comparison.

## Quick start
```pengu
import std.petitio
import std.spark

---

### `PETITIO_VERSION`

> **PETITIO_VERSION** : string

 Petitio module version (the stdlib release that ships it).

### `PETITIO_DEFAULT_MAX_REDIRECTS`

> **PETITIO_DEFAULT_MAX_REDIRECTS** : int

 Redirect limit used by `Request.new` and by the one-shot helpers, matching
 Python's `requests`.

### `PETITIO_DEFAULT_TIMEOUT_SEC`

> **PETITIO_DEFAULT_TIMEOUT_SEC** : f64

 Default total timeout in seconds. `0.0` means "no deadline", like `requests`.

### `PETITIO_DEFAULT_USER_AGENT`

> **PETITIO_DEFAULT_USER_AGENT** : string

 `User-Agent` sent when the request does not set one.

### `PETITIO_JSON_CONTENT_TYPE`

> **PETITIO_JSON_CONTENT_TYPE** : string

 Content type `json_body` installs when the request has not set one.

### `PETITIO_FORM_CONTENT_TYPE`

> **PETITIO_FORM_CONTENT_TYPE** : string

 Content type `form_body` installs when the request has not set one.

### `PETITIO_BINARY_CONTENT_TYPE`

> **PETITIO_BINARY_CONTENT_TYPE** : string

 Content type `multipart_file` installs when the part has none.

### `HttpError`

> omen HttpError

```pengu
    ConnectionFailed with reason as string
    Timeout with seconds as f64
    TooManyRedirects with count as int
    InvalidUrl with url as string
    TlsError with reason as string
    ProtocolError with reason as string
    BodyTooLarge with max_bytes as i64
    HttpOutOfMemory
    Unsupported with reason as string
    HttpIoError with reason as string
    Cancelled
    HttpStatus with status as int
```

 Why an HTTP operation failed.

 ## Memoria
 Variants that carry a `string` own it (`HttpError derive Nexus`): extract the
 error from a result and `banish` it to release the message.

### `message`

> **message**() -> string

 A human-readable description of the failure.

 ## Retorno
 An owned string with the variant and its payload, e.g.
 `"connection failed: Could not connect to server"`. `banish` it.

 ## Ejemplo
 ```pengu
 var e as HttpError is r.error
 calling spark.println with (calling e.message)
 banish e
 ```

### `FormPart`

> rune FormPart

```pengu
    name as string
    value as string
    filename as string
    content_type as string
```

 One part of a `multipart/form-data` body.

 ## Memoria
 Owns all four strings; `banish part` releases them. A `Request` owns its
 parts, so `banish req` releases them through the derived `Nexus`.

### `HttpVersion`

> omen HttpVersion

```pengu
    Http10
    Http11
    Http2
    Http2PriorKnowledge
    Http3
```

 The HTTP protocol version requested from the server.

 ## Memoria
 A plain C enum: no heap, nothing to release.

### `AuthMode`

> omen AuthMode

```pengu
    NoAuth
    BasicAuth
    DigestAuth
    AnyAuth
```

 How a request authenticates with `basic_user` / `basic_password`.

 ## Memoria
 A plain C enum: no heap, nothing to release.

### `Request`

> rune Request

```pengu
    method as string
    url as string
    headers as map of string to string
    body as string
    has_body as bool
    timeout_sec as f64
    connect_timeout_sec as f64
    follow_redirects as bool
    max_redirects as int
    verify_tls as bool
    http_version as HttpVersion
    max_body_bytes as i64
    basic_user as string
    basic_password as string
    auth_mode as AuthMode
    bearer_token as string
    proxy as string
    proxy_credentials as string
    parts as list of FormPart
```

 A configurable HTTP request.

 Build it with `Request.new`, mutate it with the builder methods, send it with
 `send`, then release it with `banish req`.

 ## Memoria
 `Request derive Nexus` releases `url`, `body`, `method`, every header key and
 value, the auth/proxy strings and every `FormPart` in `parts`.

### `Response`

> rune Response

```pengu
    status as int
    headers as map of string to string
    body as string
    url as string
    elapsed_sec as f64
    bytes_written as i64
    http_version as HttpVersion
    redirected as bool
    cookies as map of string to string
    cleared_cookies as list of string
```

 An HTTP response, as received (after redirects).

 ## Memoria
 `Response derive Nexus` releases `body`, `url`, every header key/value and
 every cookie key/value, plus the private list of cleared cookie names.

### `Session`

> rune Session

```pengu
    _default_headers as map of string to string
    _cookies as map of string to string
```

 A set of default headers and cookies applied to many requests, with cookie
 persistence.

 ## Memoria
 `Session derive Nexus` releases both maps and every string inside them.

### `UrlParts`

> rune UrlParts

```pengu
    scheme as string
    userinfo as string
    host as string
    port as int
    path as string
    query as string
    fragment as string
```

 The pieces of an absolute URL.

 ## Memoria
 Owns every field; `banish parts` releases them.

### `take_response`

> **take_response**(r: ref to result of Response to HttpError) -> Response

 Moves the successful `Response` out of `r`, leaving `r` safe to `banish`.

 ## Parámetros
 - `r`: a result. The box is consumed; `r.is_ok` becomes `false`.

 ## Retorno
 The owned `Response` (release it with `banish`). When `r` is an error, an
 empty `Response` is returned (status `0`, empty maps) and the error stays in
 the box for `banish r` to release.

 ## Ejemplo
 ```pengu
 var r as result of Response to HttpError is calling petitio.get with url
 if not r.is_ok:
     var e as HttpError is calling petitio.take_error with (sigil of r)
     calling spark.println with (calling e.message)
     banish e
     banish r
     return 1
 var resp as Response is calling petitio.take_response with (sigil of r)
 defer banish r
 defer banish resp
 ```

### `_take_response`

> **_take_response**(r: ref to result of Response to HttpError) -> Response

_Undocumented._

### `take_error`

> **take_error**(r: ref to result of T to HttpError) -> HttpError

 Moves the `HttpError` out of `r`, leaving `r` safe to `banish`.

 ## Parámetros
 - `r`: a result. The box is consumed; `r` no longer carries the error.

 ## Retorno
 The owned `HttpError` (release it with `banish`). When `r` is `ok`, a
 placeholder error is returned whose `message` is meaningless; only call this
 after checking `r.is_ok`.

### `_take_error`

> **_take_error**(r: ref to result of T to HttpError) -> HttpError

 The C half of `take_error` (see `_take_response` for the ownership why).

### `_copy`

> **_copy**(s: string) -> string

 An owned copy of `s` (one allocation). The caller `banish`es it.

### `_lower_byte`

> **_lower_byte**(b: int) -> int

 The ASCII lower-case byte of `b`; every other byte is returned unchanged.

### `_is_token_byte`

> **_is_token_byte**(b: int) -> bool

 `true` when `b` is an RFC 7230 token byte (`tchar`).

### `_is_token`

> **_is_token**(s: string) -> bool

 `true` when `s` is a non-empty RFC 7230 token (used for methods, header
 names and cookie names).

### `_has_control_byte`

> **_has_control_byte**(s: string) -> bool

 `true` when `s` contains a byte that would corrupt a header or cookie line:
 CR, LF or NUL.

 CR/LF would inject a second line; NUL truncates the value when the C bridge
 copies it into libcurl's NUL-terminated header list, silently changing the
 request. Both are rejected before they reach the wire.

### `_find_ci`

> **_find_ci**(haystack: string, needle: string) -> int

 The byte offset of the first case-insensitive occurrence of `needle` in
 `haystack`, or `-1`.

 Used for `Set-Cookie` attribute names, which are case-insensitive while the
 *values* (dates, paths) must keep their original case for `curl_getdate`.

### `_require_clean`

> **_require_clean**(value: string, what: string) -> void

 Panics when `value` contains CR, LF or NUL, naming `what`.

 The C bridge hands URLs, credentials, proxy URLs and multipart file names to
 libcurl as NUL-terminated strings, so a control byte would silently truncate
 or split them. Rejecting it at the builder keeps the failure at the call that
 made the mistake.

### `_is_unreserved`

> **_is_unreserved**(b: int) -> bool

 `true` when `b` may appear unescaped in a percent-encoded string
 (RFC 3986 `unreserved`: `A-Z a-z 0-9 - . _ ~`).

### `_hex_digit`

> **_hex_digit**(nibble: int) -> char

 The value of one upper-case hex digit.

### `_hex_value`

> **_hex_value**(b: int) -> int

 The numeric value of a hex digit, or -1 when `b` is not one.

### `_seconds_to_ms`

> **_seconds_to_ms**(seconds: f64) -> i64

 Converts a non-negative seconds value to whole milliseconds.

### `_flag`

> **_flag**(value: bool) -> int

 `1` for `true`, `0` for `false`.

### `_put_owned`

> **_put_owned**(m: ref to map of string to string, key: string, value: string) -> void

 Inserts `key` → `value` into `m`, taking ownership of both.

 ## Memoria
 The map copies the `PenguString` headers and adopts the buffers. When the key
 already exists, the old value and the old key buffer are released and the new
 pair is inserted at a fresh slot: overwriting in place would drop the old
 value's buffer (`pengu_map_put` never frees it) and passing a map-owned key
 back to `put` is unsafe across a rehash.

 ## Invariante de iteración
 `m.remove` only tomb-stones the slot (it never grows or rehashes the table),
 and the `put` that can rehash runs **after** the loop has exited, so mutating
 the map from inside the `for` cannot invalidate the iterator. The loop breaks
 immediately after the match for the same reason.

### `_remove_owned`

> **_remove_owned**(m: ref to map of string to string, key: string) -> bool

 Removes `key` from `m` and releases the stored key and value.

 ## Retorno
 `true` when the key was present.

### `_has_key`

> **_has_key**(m: ref to map of string to string, key: string) -> bool

 `true` when `m` has `key` (exact byte match; header keys are lower-case).

### `_set_header`

> **_set_header**(m: ref to map of string to string, name: string, value: string) -> void

 Validates `name`/`value` and stores them in `m` under a lower-case key.

 ## Panics
 When `name` is not an RFC 7230 token, or `name`/`value` contains CR or LF.
 A header that could inject a second header line is a bug in the caller, never
 a network condition.

### `new`

> **new**(method: string, url: string) -> Request

 Creates a request with every default filled in.

 ## Parámetros
 - `method`: the HTTP method. Token-validated and upper-cased.
 - `url`: the absolute URL. Copied; the caller keeps its string.

 ## Retorno
 A fresh `Request`: follows up to `PETITIO_DEFAULT_MAX_REDIRECTS`
 redirects, verifies TLS, has no timeout and no body.

 ## Panics
 When `method` is not an RFC 7230 token, or `url` contains CR, LF or NUL.

 ## Ejemplo
 ```pengu
 var req as Request is calling Request.new with "POST", "https://api.example.com/items"
 defer banish req
 calling req.header with "Accept", "application/json"
 ```

### `header`

> **header**(name: string, value: string) -> void

 Sets a request header, replacing any previous value for that name.

 Header names are case-insensitive: `Content-Type` and `content-type` are
 the same header, stored under the lower-case spelling.

 ## Panics
 When the name is not an RFC 7230 token, or either part contains CR/LF.

### `remove_header`

> **remove_header**(name: string) -> bool

 Removes a request header. Returns `true` when it was present.

### `has_header`

> **has_header**(name: string) -> bool

 `true` when the request sets `name` (case-insensitive).

### `text_body`

> **text_body**(s: string) -> void

 Sets a plain text body.

 The body is sent as-is; no `Content-Type` is added. Use `json_body` or
 `form_body` when the payload needs one.

### `json_body`

> **json_body**(v: JsonValue) -> void

 Serializes `v` as JSON and installs it as the body plus
 `Content-Type: application/json`.

 The content type is always set, so call `header` **after** this method to
 use a vendor media type (`application/vnd.api+json`, …).

 ## Ejemplo
 ```pengu
 var obj as JsonValue is calling JsonValue.object
 calling obj.put_string with "name", "pengu"
 calling req.json_body with obj
 banish obj
 ```

### `form_body`

> **form_body**(fields: map of string to string) -> void

 Encodes `fields` as `application/x-www-form-urlencoded` and installs the
 result as the body plus the matching `Content-Type`.

 Like `json_body`, the content type is always set; call `header` afterwards
 to override it.

### `bytes_body`

> **bytes_body**(data: string) -> void

 Sets a byte-exact body (binary data is allowed).

### `timeout`

> **timeout**(seconds: f64) -> void

 Sets the total deadline, in seconds. `0.0` disables it.

### `connect_timeout`

> **connect_timeout**(seconds: f64) -> void

 Sets the connect deadline, in seconds. `0.0` disables it.

### `no_redirects`

> **no_redirects**() -> void

 Stops at the first 3xx response instead of following it.

### `max_redirects`

> **max_redirects**(count: int) -> void

 Follows redirects, up to `count`. `count` must be positive.

### `insecure`

> **insecure**() -> void

 Disables TLS certificate and hostname verification.

 ## Advertencia
 This makes the connection trivially interceptable. Use it only against a
 test endpoint you control.

### `http_version`

> **http_version**(version: HttpVersion) -> void

 Requests a specific HTTP protocol version.

 ## Parámetros
 - `version`: `Http11` (default), `Http2` (ALPN negotiation, falls back to
   HTTP/1.1) or `Http2PriorKnowledge` (force HTTP/2, no fallback).

 ## Ejemplo
 ```pengu
 calling req.http_version with HttpVersion.Http2
 ```

### `auth_basic`

> **auth_basic**(user: string, password: string) -> void

 Sends HTTP Basic credentials (RFC 7617).

 ## Panics
 When `user` or `password` contains CR, LF or NUL.

 ## Advertencia
 Basic sends the password on every request; over plain HTTP that is
 readable by anyone on the path. Use HTTPS.

### `auth_digest`

> **auth_digest**(user: string, password: string) -> void

 Sends HTTP Digest credentials (RFC 7616).

 libcurl answers the server's `401` challenge and retries with a hashed
 response, so the password never crosses the wire. The server must offer
 Digest; if it does not, the request fails with the server's `401` status.

 ## Panics
 When `user` or `password` contains CR, LF or NUL.

 ## Advertencia
 Digest over plain HTTP still lets an attacker capture and replay the
 exchange. Use HTTPS.

### `auth_any`

> **auth_any**(user: string, password: string) -> void

 Negotiates the authentication scheme with the server.

 libcurl uses the strongest scheme the server offers (Digest when
 available, Basic otherwise).

 ## Panics
 When `user` or `password` contains CR, LF or NUL.

### `auth_bearer`

> **auth_bearer**(token: string) -> void

 Sends `Authorization: Bearer <token>`.

 An `Authorization` header set explicitly with `header` wins.

### `socks_proxy`

> **socks_proxy**(url: string, credentials: string) -> void

 Routes the request through a SOCKS5 proxy, resolving DNS **on the proxy**.

 Equivalent to `proxy("socks5h://" + url, credentials)`. The `h` matters:
 `socks5h` sends the host name to the proxy instead of resolving it
 locally, so the proxy (not your machine) sees the destination and no DNS
 query leaks. A URL that already carries a scheme (`socks5://`,
 `socks5h://`, `http://`) is used as given.

 ## Parámetros
 - `url`: `"host:port"` (for example `"127.0.0.1:1080"`).
 - `credentials`: `"user:password"`, or `""` for an open proxy.

 ## Panics
 When `url` or `credentials` contains CR, LF or NUL.

 ## Ejemplo
 ```pengu
 calling req.socks_proxy with "127.0.0.1:1080", ""
 ```

### `proxy`

> **proxy**(proxy: string, credentials: string) -> void

 Routes the request through `proxy` (`"http://host:port"`), optionally
 authenticated with `"user:password"`.

 ## Panics
 When `proxy` or `credentials` contains CR, LF or NUL.

### `max_body_bytes`

> **max_body_bytes**(limit: i64) -> void

 Caps the response body. Exceeding it fails with
 `HttpError.BodyTooLarge` and the transfer is aborted.

### `multipart_field`

> **multipart_field**(name: string, value: string) -> void

 Adds a `multipart/form-data` text field.

### `multipart_bytes`

> **multipart_bytes**(name: string, data: string, filename: string, content_type: string) -> void

 Adds a `multipart/form-data` part with explicit file name and type.

 ## Parámetros
 - `name`: the form field name.
 - `data`: the part bytes (copied; binary is allowed).
 - `filename`: the `filename` parameter, or `""` for none.
 - `content_type`: the part type, or `""` to let libcurl omit it.

### `multipart_file`

> **multipart_file**(name: string, path: string) -> bool

 Adds a file as a `multipart/form-data` part, read into memory now.

 ## Retorno
 `true` when the file was read and the part added; `false` when `path`
 could not be read (a runtime condition, so it does not panic).

 ## Memoria
 The file contents are copied into the request; the file handle is closed
 by `std.archivum` before this returns.

### `send`

> **send**() -> result of Response to HttpError

 Sends the request and waits for the response.

 ## Retorno
 `ok Response` (owned; `banish` it) or `err HttpError`. The request stays
 usable and can be sent again.

 ## Ejemplo
 ```pengu
 var r as result of Response to HttpError is calling req.send
 defer banish r
 if not r.is_ok:
     return 1
 var resp as Response is r.value          # borrowed copy: do not banish
 calling spark.println_int with resp.status
 ```

### `send_to_file`

> **send_to_file**(path: string) -> result of Response to HttpError

 Sends the request and writes the body to `path`, without buffering it.

 ## Parámetros
 - `path`: destination file, overwritten when it exists. Its parent
   directory must exist.

 ## Retorno
 `ok Response` with `body == ""` and `bytes_written` set, or
 `err HttpError.HttpIoError` when the file cannot be opened or written and
 `err HttpError.BodyTooLarge` when `max_body_bytes` is exceeded.

 ## Memoria
 The `Response` is owned; the `Request` stays reusable. The file is closed
 before this returns.

 ## Ejemplo
 ```pengu
 var req as Request is calling Request.new with "GET", "https://example.com/big.bin"
 calling req.max_body_bytes with 128 * 1024 * 1024
 var r as result of Response to HttpError is calling req.send_to_file with "big.bin"
 defer banish r
 ```

### `send_stream`

> **send_stream**(cb: ref to weave with chunk: string, user: ref to void into bool, user: ref to void) -> result of Response to HttpError

 Sends the request and hands every body chunk to `cb`.

 ## Parámetros
 - `cb`: `weave chunk as string, user as ref to void into bool`. Return
   `true` to continue, `false` to abort (`err HttpError.Cancelled`).
 - `user`: opaque context forwarded to `cb` (a `sigil of` a local is the
   usual choice).

 ## Advertencia
 `chunk` is a **borrowed view** of libcurl's buffer. It is valid only
 during the call: do not store it, do not `banish` it and do not let it
 escape into a `defer`.

 ## Retorno
 `ok Response` with `body == ""` and `bytes_written` set, `err Cancelled`
 when `cb` returned `false`, or the usual transport errors.

 ## Ejemplo
 ```pengu
 weave count with chunk as string, user as ref to void into bool:
     var total as ref to i64 is transmute user to ref to i64
     set essence of total is (essence of total) + (chunk length to i64)
     return true

 var total as i64 is 0
 var r as result of Response to HttpError is calling req.send_stream with count, (sigil of total)
 ```

### `is_ok`

> **is_ok**() -> bool

 `true` for a 2xx status.

### `is_redirect`

> **is_redirect**() -> bool

 `true` for a 3xx status (only observable with `no_redirects`).

### `is_client_error`

> **is_client_error**() -> bool

 `true` for a 4xx status.

### `is_server_error`

> **is_server_error**() -> bool

 `true` for a 5xx status.

### `text`

> **text**() -> string

 An owned copy of the body.

 ## Memoria
 One allocation; `banish` it. `Response.body` is the same bytes without a
 copy.

### `json`

> **json**() -> result of JsonValue to JsonError

 Parses the body as JSON.

 ## Retorno
 `ok JsonValue` (owned) or the parser's `JsonError`.

### `raise_for_status`

> **raise_for_status**() -> result of void to HttpError

 Fails with `HttpError.HttpStatus` when the status is 4xx or 5xx.

 ## Retorno
 `ok 0`, or `err HttpStatus`.

### `url_encode`

> **url_encode**(s: string) -> string

 Percent-encodes `s` for use in a URL path or query value.

 Every byte outside RFC 3986's `unreserved` set (`A-Z a-z 0-9 - . _ ~`) becomes
 `%XX` with upper-case hex digits. Space becomes `%20`, never `+`, so the
 result round-trips through `url_decode`.

 Encoding is **byte-exact**: the string's UTF-8 bytes are encoded one by one,
 so `"ñ"` (two bytes) becomes `%C3%B1` and never a single percent escape. The
 output depends only on those bytes: no locale, no Unicode normalization.

 ## Memoria
 Returns an owned string; `banish` it.

 ## Ejemplo
 ```pengu
 var q as string is calling petitio.url_encode with "a b&c"
 defer banish q                     # "a%20b%26c"
 ```

### `url_decode`

> **url_decode**(s: string) -> string

 Decodes every `%XX` sequence in `s`.

 `+` is left as `+` (it is only a space in `application/x-www-form-urlencoded`,
 not in a URL). A malformed or truncated escape is copied verbatim, so decoding
 never fails and never loses bytes.

 ## Memoria
 Returns an owned string; `banish` it.

 ## Ejemplo
 ```pengu
 var t as string is calling petitio.url_decode with "a%20b%26c"   # "a b&c"
 defer banish t
 ```

### `build_query_string`

> **build_query_string**(params: map of string to string) -> string

 Builds `key=value&...` with both sides percent-encoded.

 Keys are sorted byte-wise first, so the same map always yields the same
 query string — the property cache keys and request signatures need. The
 leading `?` is **not** included.

 ## Memoria
 Returns an owned string; `banish` it.

 ## Ejemplo
 ```pengu
 var params as map of string to string is map of string to string
 calling params.put with "q", "pengu script"
 var qs as string is calling petitio.build_query_string with params
 defer banish qs                    # "q=pengu%20script"
 banish params
 ```

### `with_query`

> **with_query**(url: string, params: map of string to string) -> string

 Appends `params` to `url`, using `?` or `&` as needed.

 ## Memoria
 Returns an owned string; `banish` it.

### `parse_url`

> **parse_url**(url: string) -> result of UrlParts to string

 Splits an absolute `http`/`https` URL into its parts.

 ## Parámetros
 - `url`: an absolute URL. IPv6 hosts may be bracketed (`[::1]:8080`).

 ## Retorno
 `ok UrlParts` (owned; `banish` it) or `err message` describing the first
 structural problem (a borrowed literal, so nothing to release).

 ## Detalles
 The default port is **not** filled in: `port` is `0` when the URL omits it.
 The query is returned without `?` and the fragment without `#`. The path is
 `"/"` when the URL has none.

 ## Ejemplo
 ```pengu
 var parsed as result of UrlParts to string is calling petitio.parse_url with "https://example.com:8443/a?b=1#c"
 defer banish parsed                       # owns the UrlParts payload
 if not parsed.is_ok:
     return 1
 var parts as UrlParts is parsed.value     # borrowed copy: do not banish
 calling spark.println with parts.host      # example.com
 calling spark.println_int with parts.port  # 8443
 ```

### `_error_from_code`

> **_error_from_code**(code: int, reason: string, request: ref to Request) -> HttpError

 Maps a `PETITIO_*` code to the matching `HttpError` variant.

### `_response_from_c`

> **_response_from_c**(raw: ref to petitio_response, request: ref to Request) -> Response

 Copies the fields of a C response into an owned `Response`.

### `_http_version_code`

> **_http_version_code**(version: HttpVersion) -> int

 The C request code for `HttpVersion` (0 = 1.1, 1 = ALPN, 2 = prior
 knowledge, 3 = 1.0). `Http3` has no request code; the builder rejects it.

### `_http_version_from_code`

> **_http_version_from_code**(code: int) -> HttpVersion

 The `HttpVersion` for the C response code (0 = 1.0, 2 = 2, 4 = 3, rest = 1.1).

### `_auth_mode_code`

> **_auth_mode_code**(mode: AuthMode) -> int

 The C code for `AuthMode` (0 = none, 1 = Basic, 2 = Digest, 3 = any).

### `_no_headers`

> **_no_headers**() -> map of string to string

 An empty header map, for the helpers that take no overlay.

### `_build_handle`

> **_build_handle**(request: ref to Request, overlay_headers: ref to map of string to string, cookies: ref to map of string to string) -> ref to petitio_request

 Builds and configures the C request, merging `overlay_headers` (session
 defaults, never overriding a request header) and `cookies` (one `Cookie`
 header). Returns NULL only on allocation failure; the caller owns the handle.

### `_perform`

> **_perform**(request: ref to Request, overlay_headers: ref to map of string to string, cookies: ref to map of string to string) -> result of Response to HttpError

 Sends `request`, merging `overlay_headers` (session defaults, never
 overriding a request header) and `cookies` (as a `Cookie` header).

### `_cookie_name`

> **_cookie_name**(value: string) -> string

 The name of the first `name=value` pair in a `Set-Cookie` value (owned).

### `_cookie_value`

> **_cookie_value**(value: string) -> string

 The value of the first `name=value` pair in a `Set-Cookie` value (owned).

### `_cookie_cleared`

> **_cookie_cleared**(value: string) -> bool

 `true` when a `Set-Cookie` value clears the cookie.

 A cookie is cleared when `Max-Age` is zero **or negative** (RFC 6265 §5.2.2
 makes every non-positive delta expire immediately) or, when there is no
 `Max-Age`, when its `Expires` date is in the past (see
 `_cookie_expired_by_date`). `Max-Age` wins over `Expires` (§5.3): a one-hour
 `Max-Age` keeps the cookie even if `Expires` points at 1970.

 The attribute is parsed as a number (`Max-Age=0`, `max-age=-1`), not by
 substring: `Max-Age=01` is a one-second cookie and must not clear anything.

### `_cookie_expired_by_date`

> **_cookie_expired_by_date**(value: string) -> bool

 `true` when the `Expires` attribute of a `Set-Cookie` value is in the past.

 The date is parsed by libcurl (`curl_getdate`), which accepts every format
 RFC 7231 allows. A missing or unparseable `Expires` does not expire anything:
 only an explicit date at or before "now" clears the cookie.

 ## Memoria
 Allocates one lowercase copy and one date substring, both released here.

### `_free_strings`

> **_free_strings**(items: list of string) -> void

 Releases every string of an owned `list of string`, then the list buffer.

 `banish list` frees only the element buffer (`PenguList` never recurses), so
 a list returned by `scrolls.split` needs one release per element too.

### `set_header`

> **set_header**(name: string, value: string) -> void

 Sets a default header. A request that sets the same name overrides it.

 ## Panics
 When the name is not an RFC 7230 token, or either part contains CR/LF.

### `set_cookie`

> **set_cookie**(name: string, value: string) -> void

 Stores a cookie that every subsequent request sends.

 ## Panics
 When `name` is not an RFC 7230 token, or `name`/`value` contains ';' or a
 line break (either would corrupt the `Cookie` header).

### `remove_cookie`

> **remove_cookie**(name: string) -> bool

 Forgets one cookie. Returns `true` when it was present.

### `clear_cookies`

> **clear_cookies**() -> void

 Forgets every cookie.

 ## Detalles
 The loop removes one cookie per iteration and verifies that the map
 actually shrank. If `_remove_owned` ever failed (a corrupt map, an OOM in
 a key copy), an unguarded `while` would spin forever; the loop breaks
 instead and leaves the remaining entries in place.

### `load_cookies_from_file`

> **load_cookies_from_file**(path: string) -> result of int to HttpError

 Loads cookies from a Netscape-format cookie file.

 The jar is a name → value store: the domain, path, secure flag and expiry
 columns are ignored (the wrapper does not scope cookies per host). A file
 written by curl or by `save_cookies_to_file` loads; cookies already in the
 session with the same name are replaced.

 ## Parámetros
 - `path`: file to read. Missing or unreadable files are an error.

 ## Retorno
 `ok n` with the number of cookies loaded, or `err HttpIoError`.

### `save_cookies_to_file`

> **save_cookies_to_file**(path: string) -> result of void to HttpError

 Writes the current cookies as a Netscape-format cookie file.

 The domain, path, secure and expiry columns are placeholders (`.`,
 `TRUE`, `/`, `FALSE`, `0`): the jar keeps only names and values, so the
 file round-trips through `load_cookies_from_file` but does not describe
 host scoping.

 ## Retorno
 `ok 0`, or `err HttpIoError` when the file cannot be written.

### `cookie_count`

> **cookie_count**() -> int

 The number of stored cookies.

### `has_cookie`

> **has_cookie**(name: string) -> bool

 `true` when the session stores `name`.

### `cookie`

> **cookie**(name: string) -> string

 The value stored for cookie `name`, or `""`.

 ## Memoria
 An owned copy; `banish` it. `has_cookie` distinguishes a missing cookie
 from one whose value is empty.

### `request`

> **request**(req: ref to Request) -> result of Response to HttpError

 Sends `req` with the session's headers and cookies, and updates the
 cookie jar from the response.

 ## Detalles
 A header set on the request always wins over the session default (the
 merge is name-by-name). An explicit `Cookie` header on the request
 replaces the session's cookies for that call; the jar is still updated
 from the response.

### `get`

> **get**(url: string) -> result of Response to HttpError

 `GET url` through the session.

### `post_json`

> **post_json**(url: string, v: JsonValue) -> result of Response to HttpError

 `POST url` with a JSON body, through the session.

### `post_form`

> **post_form**(url: string, fields: map of string to string) -> result of Response to HttpError

 `POST url` with a form-urlencoded body, through the session.

### `request_async`

> **request_async**(req: ref to Request, loop: ref to EventLoop) -> result of Response to HttpError

 Async version of `request`: the transfer runs on the loop's dispatcher
 and the cookie merge happens back on the loop thread.

### `get_async`

> **get_async**(url: string, loop: ref to EventLoop) -> result of Response to HttpError

 `GET url` through the session, without blocking the loop.

### `post_json_async`

> **post_json_async**(url: string, v: JsonValue, loop: ref to EventLoop) -> result of Response to HttpError

 `POST url` with a JSON body, through the session, without blocking.

### `post_form_async`

> **post_form_async**(url: string, fields: map of string to string, loop: ref to EventLoop) -> result of Response to HttpError

 `POST url` with a form body, through the session, without blocking.

### `head`

> **head**(url: string) -> result of Response to HttpError

 `HEAD url` with default settings.

### `delete`

> **delete**(url: string) -> result of Response to HttpError

 `DELETE url` with default settings.

### `options`

> **options**(url: string) -> result of Response to HttpError

 `OPTIONS url` with default settings.

### `post`

> **post**(url: string) -> result of Response to HttpError

 `POST url` with an empty body.

### `put_json`

> **put_json**(url: string, v: JsonValue) -> result of Response to HttpError

 `PUT url` with a JSON body.

### `patch_json`

> **patch_json**(url: string, v: JsonValue) -> result of Response to HttpError

 `PATCH url` with a JSON body.

### `post_text`

> **post_text**(url: string, body: string, content_type: string) -> result of Response to HttpError

 `POST url` with a plain text body and an explicit content type.

### `default_user_agent`

> **default_user_agent**() -> string

 The `User-Agent` this module sends when a request does not set one.

### `fetch_many`

> **fetch_many**(requests: list of Request) -> list of result of Response to HttpError

 Sends every request in `requests` concurrently on one thread.

 ## Detalles
 libcurl's `multi` engine multiplexes the transfers: HTTP/2 requests share one
 connection, HTTP/1.1 ones are spread over the engine's connections. There are
 no threads and no async machinery; the call blocks until every transfer has
 finished. The result order matches the input order, so `results at i`
 describes `requests at i`.

 ## Propiedad
 The input `Request` structs stay owned by the caller: `banish` them after the
 call. The C handles built from them are owned and released by `fetch_many`.
 This is a `Request`-level API: a `Session`'s default headers and cookies are
 **not** applied, so copy them into each request when you need them.
 The returned list is owned and each `result` inside is independent; release
 them with `banish` (an `ok` result owns its `Response`, an `error` owns its
 message).

 ## Retorno
 `list of result of Response to HttpError`, one per input, in order. A request
 whose handle could not be built yields `err HttpOutOfMemory`.

 ## Ejemplo
 ```pengu
 var reqs as list of Request is list of Request
 calling reqs.push with (calling Request.new with "GET", "https://example.com/a")
 calling reqs.push with (calling Request.new with "GET", "https://example.com/b")
 var results as list of result of Response to HttpError is calling fetch_many with reqs
 for r in results:
     if r.is_ok:
         calling spark.println_int with r.value.status
     banish r
 banish results
 for req in reqs:
     banish req
 banish reqs
 ```

### `libcurl_version`

> **libcurl_version**() -> string

 The libcurl runtime version this build links against (e.g. `"8.22.0"`).

 ## Retorno
 An owned version string; `banish` it. Useful in bug reports and in a startup
 banner that names the transport.

 ## Ejemplo
 ```pengu
 var version as string is calling petitio.libcurl_version
 calling spark.println with version
 banish version
 ```

### `_expect`

> **_expect**(cond: bool, label: string) -> void

 Panics with `label` when `cond` is false.

### `_expect_int`

> **_expect_int**(actual: int, expected: int, label: string) -> void

 Panics with `label` when `actual != expected`.

### `_expect_str`

> **_expect_str**(actual: string, expected: string, label: string) -> void

 Panics with `label` when the two strings differ.

### `"Max-Age zero and negative clear the cookie"`

> test "Max-Age zero and negative clear the cookie"

_Undocumented._

### `"a positive Max-Age keeps the cookie"`

> test "a positive Max-Age keeps the cookie"

_Undocumented._

### `"a cookie without Max-Age or Expires stays"`

> test "a cookie without Max-Age or Expires stays"

_Undocumented._

### `"Expires in the past clears the cookie"`

> test "Expires in the past clears the cookie"

_Undocumented._

### `"Expires in the future keeps the cookie"`

> test "Expires in the future keeps the cookie"

_Undocumented._

### `"Max-Age wins over Expires (RFC 6265 5.3)"`

> test "Max-Age wins over Expires (RFC 6265 5.3)"

_Undocumented._

### `"an unparseable Expires does not clear"`

> test "an unparseable Expires does not clear"

_Undocumented._

### `"cookie name/value extraction"`

> test "cookie name/value extraction"

_Undocumented._

### `"url_encode and url_decode round-trip"`

> test "url_encode and url_decode round-trip"

_Undocumented._

### `"build_query_string sorts and encodes"`

> test "build_query_string sorts and encodes"

_Undocumented._

### `"parse_url splits an absolute URL"`

> test "parse_url splits an absolute URL"

_Undocumented._

### `"control bytes and tokens"`

> test "control bytes and tokens"

_Undocumented._

### `"Request defaults and header replacement"`

> test "Request defaults and header replacement"

_Undocumented._

### `"http_version defaults to HTTP/1.1 and is settable"`

> test "http_version defaults to HTTP/1.1 and is settable"

_Undocumented._

### `"the response protocol code maps back to an HttpVersion"`

> test "the response protocol code maps back to an HttpVersion"

_Undocumented._

### `"authentication modes are selected by their builders"`

> test "authentication modes are selected by their builders"

_Undocumented._

### `"socks_proxy prefixes socks5h and keeps an explicit scheme"`

> test "socks_proxy prefixes socks5h and keeps an explicit scheme"

_Undocumented._

### `"streaming error variants carry a message"`

> test "streaming error variants carry a message"

_Undocumented._

### `"fetch_many on an empty list returns an empty list"`

> test "fetch_many on an empty list returns an empty list"

_Undocumented._

### `"Session cookie jar operations"`

> test "Session cookie jar operations"

_Undocumented._

### `"cookie files round-trip through the Netscape format"`

> test "cookie files round-trip through the Netscape format"

_Undocumented._

### `"loading a missing cookie file is an error"`

> test "loading a missing cookie file is an error"

_Undocumented._

### `"take_response and take_error leave the result banish-safe"`

> test "take_response and take_error leave the result banish-safe"

_Undocumented._

### `_empty_response`

> **_empty_response**() -> Response

 A zeroed `Response`, used by the move tests.

### `DispatchJob`

> rune DispatchJob

```pengu
    req as Request
    handle as ref to petitio_request
    out as result of Response to HttpError
    task as i64
    token as i64
    index as int
    done as bool
```

_Undocumented._

### `PetitioDispatcher`

> rune PetitioDispatcher

```pengu
    mutex as Mutex
    cond as Cond
    jobs as list of ref to DispatchJob
    stopping as bool
    next as i64
    handle as opaque
    thread as Thread
```

_Undocumented._

### `_outcome_from_c`

> **_outcome_from_c**(raw: ref to petitio_response, request: ref to Request) -> result of Response to HttpError

 Maps a C response to the public result. Does not free `raw`.

### `_petitio_dispatcher_main`

> **_petitio_dispatcher_main**(d: ref to PetitioDispatcher) -> void

_Undocumented._

### `_petitio_dispatcher_loop`

> **_petitio_dispatcher_loop**(d: ref to PetitioDispatcher) -> void

_Undocumented._

### `_petitio_dispatcher_batch`

> **_petitio_dispatcher_batch**(d: ref to PetitioDispatcher, batch: list of ref to DispatchJob) -> void

_Undocumented._

### `_petitio_dispatcher_free`

> **_petitio_dispatcher_free**(a: opaque) -> void

_Undocumented._

### `_petitio_dispatcher_get`

> **_petitio_dispatcher_get**(loop: ref to EventLoop) -> ref to PetitioDispatcher

_Undocumented._

### `_dispatch_handle`

> **_dispatch_handle**(loop: ref to EventLoop, req: Request, handle: ref to petitio_request) -> result of Response to HttpError

 Enqueues one already-built C handle on this loop's dispatcher and waits for
 its completion. `req` is copied into the job so it stays valid while the
 calling coroutine is suspended or after the caller's frame is abandoned.

### `_petitio_async_noop`

> **_petitio_async_noop**(box: ref to void) -> void

_Undocumented._

### `SendFileJob`

> rune SendFileJob

```pengu
    req as ref to Request
    path as string
    out as result of Response to HttpError
```

_Undocumented._

### `_petitio_send_file_worker`

> **_petitio_send_file_worker**(ctx: ref to void) -> void

_Undocumented._

### `send_async`

> **send_async**(self: ref to Request, loop: ref to EventLoop) -> result of Response to HttpError

 Async `Request.send`: suspends the calling reactor task. The loop's
 dispatcher owns the libcurl multi engine; one helper thread serves every
 in-flight request on that loop.

### `send_to_file_async`

> **send_to_file_async**(self: ref to Request, loop: ref to EventLoop, path: string) -> result of Response to HttpError

 Async `Request.send_to_file`.

### `build_request`

> **build_request**(method: string, url: string) -> Request

 Builds a `Request` through the module, avoiding an ambiguous qualified
 `Request.new` call from outside petitio.

### `session_new`

> **session_new**() -> Session

 Builds a `Session` through the module (avoids the qualified `Session.new`
 ambiguity from outside petitio).

### `fetch_many_async`

> **fetch_many_async**(loop: ref to EventLoop, requests: list of Request) -> list of result of Response to HttpError

 Async `fetch_many`: submits every request to the loop's dispatcher. The
 transfers run concurrently in one multi engine on the dispatcher thread.

