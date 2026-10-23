# `std.petitio` — the HTTP client

`std.petitio` (Latin *petitio*, "a request") is PenguScript's high-level HTTP
client: an explicit, `result`-returning wrapper over **libcurl** with a
Python-`requests`-shaped API. It covers the everyday client surface — methods,
headers, JSON/form/multipart bodies, query strings, URL parsing, timeouts,
redirects, TLS toggles, Basic/Digest/negotiated auth, Bearer tokens, HTTP and
SOCKS proxies, HTTP/2, streaming downloads, concurrent batches, response body
caps, sessions with cookies (including `Expires`) and `Response.json()` — and it
costs nothing when you do not import it.

```pengu
import std.petitio
import std.spark

weave main into int:
    var r as result of Response to HttpError is calling petitio.get with "https://example.com/"
    defer banish r
    if not r.is_ok:
        return 1
    var resp as Response is r.value
    calling spark.println_int with resp.status
    calling spark.println with resp.body
    return 0
```

---

## 1. Why libcurl and not `naett`

`naett` (single header, MIT) was evaluated first and **rejected**. The comparison
is not a matter of taste: its public API cannot express the wrapper this module
promises.

| Capability | `naett` | libcurl |
|---|---|---|
| Methods, headers, body | ✅ | ✅ |
| Connect timeout | ✅ (`naettTimeout`) | ✅ |
| **Total timeout** | ❌ | ✅ `CURLOPT_TIMEOUT_MS` |
| **Redirect control** | ❌ always on, no limit, intermediate statuses invisible | ✅ `FOLLOWLOCATION` + `MAXREDIRS` |
| **TLS verification toggle** | ❌ | ✅ |
| **Cookies** | ❌ | ✅ (the wrapper keeps its own explicit jar) |
| **Proxy** | ❌ | ✅ |
| **Multipart** | ❌ | ✅ `curl_mime` |
| **HTTP/2** | ❌ no control | ✅ ALPN / prior knowledge / report |
| **Streaming downloads** | ❌ body only | ✅ file or callback sink |
| **Concurrent transfers** | ❌ one request at a time | ✅ `curl_multi` |
| Duplicate response headers (`Set-Cookie`) | ❌ one value per name | ✅ preserved in order |
| Protocol allow-list | ❌ | ✅ `PROTOCOLS_STR` |
| Single header | ✅ | ❌ (system library) |
| Linux backend | libcurl anyway | libcurl |
| Portable to Windows/macOS | ✅ (WinHTTP / NSURLSession) | ✅ (libcurl) |
| Compiles under `-std=c99 -Wall -Wextra -Werror` | ❌ (`strndup`, unused parameter) | ✅ (the bridge does) |

The decisive point is the Linux backend: `naett` *is* libcurl there, so it never
removed the dependency — it only hid the knobs. A `requests`-shaped client needs
those knobs (a total deadline and a redirect limit are table stakes), so the
module wraps libcurl directly with a small, warning-clean C bridge
(`std_c/petitio.c`) and one PenguScript wrapper (`std/petitio.pengu`).

### 1.1 The dependency

`libcurl` is a system library: preinstalled on Linux and macOS, available through
every package manager (`libcurl4-openssl-dev`, `curl-devel`, `brew install curl`)
on Windows. `pengu build` does **not** need libcurl unless the program imports
`std.petitio`:

* `build_runtime.py` archives `std_c/petitio.c` into `build/lib/libpetitio.a`
  when `curl/curl.h` is available, and *skips it with a clear message* when it is
  not — so a checkout without the headers can still build every other module;
* importing `std.petitio` adds `-lpetitio -lcurl` to that program's link line and
  nothing else;
* a program that never imports it links neither. `tests/build/test_smart_linking.py`
  proves this with the generated `bundle.c`, the `--verbose` link line and `nm`.

---

## 2. Types

| Type | Purpose |
|---|---|
| `Request` | A configurable request. Builder methods mutate it; `send` performs it. |
| `Response` | Status, headers, body, URL, elapsed time, cookies. |
| `Session` | Default headers + a cookie jar shared by many requests. |
| `FormPart` | One `multipart/form-data` part. |
| `HttpError` | Why an operation failed (`omen`), with a `message` method. |
| `UrlParts` | The components of an absolute URL. |
| `HttpVersion` | `Http10`, `Http11`, `Http2`, `Http2PriorKnowledge`, `Http3` (reported only). |
| `AuthMode` | `NoAuth`, `BasicAuth`, `DigestAuth`, `AnyAuth`. |

### 2.1 Ownership, once

PenguScript has manual memory management, and `std.petitio` follows it exactly:

* `Request`, `Response`, `Session` and `UrlParts` own every string, map and list
  they contain (`derive Nexus`). `banish req` / `banish resp` / `banish session`
  releases the whole object, including every string inside its maps.
* A `result of Response to HttpError` **owns its payload**. `r.value` and
  `r.error` give you a *copy* of that payload; releasing both the copy and the
  result frees the same buffers twice.
  * Borrow when the result and the value share a scope: `var resp as Response is
    r.value`, use it, then `banish r`. Do **not** `banish resp`.
  * Move when they must be released independently: `take_response` /
    `take_error` clear the box, so `banish resp` and `banish r` are both safe.
* Every string *getter* (`Response.text`, `Response.header`, `HttpError.message`,
  `Request` copies, URL helpers) returns an **owned** copy. `banish` it.
* `Response.header` returns `""` for an absent header; use `has_header` to tell
  an empty value apart from a missing one.
* `Response.body` is the same bytes as `text` without a copy; it lives and dies
  with the response.

```pengu
var r as result of Response to HttpError is calling petitio.get with url
defer banish r
if not r.is_ok:
    var failure as HttpError is calling petitio.take_error with (sigil of r)
    var why as string is calling failure.message
    calling spark.println with why
    banish why
    banish failure
    return 1
var resp as Response is calling petitio.take_response with (sigil of r)
defer banish resp
var body as string is calling resp.text
defer banish body
```

---

## 3. Requests

### 3.1 `Request.new`

```pengu
var req as Request is calling Request.new with "POST", "https://api.example.com/items"
defer banish req
```

Defaults: follows up to `PETITIO_DEFAULT_MAX_REDIRECTS` (30) redirects, verifies
TLS, has no timeout and no body. The method is upper-cased and must be an RFC
7230 token; `Request.new` panics on an invalid one.

### 3.2 Builder methods

| Method | Effect |
|---|---|
| `header(name, value)` | Sets a header. Names are case-insensitive and stored lower-case; a later call replaces the value. Panics on CR/LF or an invalid name. |
| `remove_header(name) -> bool` | Removes a header. |
| `has_header(name) -> bool` | Case-insensitive presence test. |
| `text_body(s)` | Raw body. |
| `json_body(v)` | `std.json.stringify(v)` + `Content-Type: application/json`. |
| `form_body(fields)` | `application/x-www-form-urlencoded` body + matching type. |
| `bytes_body(data)` | Byte-exact body (binary allowed). |
| `timeout(seconds)` | Total deadline (`0.0` = none). |
| `connect_timeout(seconds)` | Connect deadline (`0.0` = none). |
| `no_redirects` | Returns the first 3xx instead of following it. |
| `max_redirects(n)` | Follows redirects, up to `n`. |
| `insecure` | Disables TLS verification (testing only). |
| `http_version(version)` | `Http10`, `Http11` (default), `Http2` (ALPN, falls back) or `Http2PriorKnowledge` (forced). `Http3` panics: it is reported, not requested. |
| `auth_basic(user, password)` | HTTP Basic (RFC 7617). Sets `auth_mode` to `BasicAuth`. |
| `auth_digest(user, password)` | HTTP Digest (RFC 7616): libcurl answers the 401 challenge. |
| `auth_any(user, password)` | Lets libcurl negotiate the strongest scheme the server offers. |
| `auth_bearer(token)` | `Authorization: Bearer`. An explicit header wins. |
| `proxy(url, credentials)` | Routes through an HTTP proxy. |
| `socks_proxy(url, credentials)` | Routes through SOCKS5 with DNS resolved **on the proxy** (`socks5h://`); an explicit scheme is kept. |
| `max_body_bytes(n)` | Aborts with `BodyTooLarge` past `n` bytes (`0` = unlimited). |
| `multipart_field(name, value)` | Adds a text part. |
| `multipart_bytes(name, data, filename, type)` | Adds a byte part. |
| `multipart_file(name, path) -> bool` | Reads `path` and adds it as a part; `false` when unreadable. |
| `send() -> result of Response to HttpError` | Performs the request. The request stays reusable. |
| `send_to_file(path)` | Streams the body to disk; `body` stays empty and `bytes_written` reports the size. |
| `send_stream(cb, user)` | Hands every chunk to `cb`; returning `false` aborts with `Cancelled`. |

`json_body` and `form_body` always set the content type, because they replace the
body. Call `header("Content-Type", …)` **after** them to use a vendor media type.

### 3.3 Query strings

`build_query_string` percent-encodes both sides and **sorts the keys**, so the
same map always produces the same bytes (a property cache keys and request
signatures need). It does not include the leading `?`; `with_query` adds the
right separator.

```pengu
import std.petitio
var params as map of string to string is map of string to string
calling params.put with "q", "pengu script"
calling params.put with "page", "2"
var url as string is calling petitio.with_query with "https://example.com/search", params
defer banish url                       # ".../search?page=2&q=pengu%20script"
banish params
```

`url_encode` escapes everything outside RFC 3986's `unreserved` set with
upper-case hex (`%C3%B1`, never `%c3%b1`), and turns space into `%20`, never `+`.
`url_decode` reverses `%XX` and leaves `+` alone; malformed escapes are copied
verbatim, so decoding never fails and never loses bytes.

### 3.4 `parse_url`

```pengu
var parsed as result of UrlParts to string is calling petitio.parse_url with "https://user:pw@[::1]:8443/a?b=1#c"
defer banish parsed
if not parsed.is_ok:
    return 1
var parts as UrlParts is parsed.value
# scheme=https userinfo=user:pw host=[::1] port=8443 path=/a query=b=1 fragment=c
```

The default port is not filled in (`port == 0` when the URL omits it), the path is
`"/"` when absent, and the query/fragment exclude `?`/`#`. Structural problems
(no `://`, missing host, non-numeric or out-of-range port, unterminated IPv6)
return an error message instead of panicking.

---

## 4. Responses

| Member | Meaning |
|---|---|
| `status` | Final status code after redirects (`0` when no response line arrived). |
| `headers` | Final-response headers, lower-case keys, last value wins for duplicates. |
| `body` | Byte-exact body (libcurl decodes `Content-Encoding`). |
| `url` | Effective URL after redirects. |
| `elapsed_sec` | Wall-clock transfer time. |
| `bytes_written` | Bytes written: the body length in memory mode, the file/callback count when streaming. |
| `http_version` | The protocol the server actually spoke (`Http10`/`Http11`/`Http2`/`Http3`). |
| `redirected` | `true` when at least one redirect was followed. |
| `cookies` | Cookies the server set (name → value). |
| `cleared_cookies` | Names the server cleared with `Max-Age=0`. |
| `is_ok()` | 2xx. |
| `is_redirect()` | 3xx (observable with `no_redirects`). |
| `is_client_error()` | 4xx. |
| `is_server_error()` | 5xx. |
| `text()` | Owned copy of the body. |
| `json() -> result of JsonValue to JsonError` | Parses the body. |
| `header(name) -> string` | Owned copy, `""` when absent. |
| `has_header(name) -> bool` | Presence test, case-insensitive. |
| `raise_for_status() -> result of void to HttpError` | `err HttpStatus` for 4xx/5xx. |

`Response` carries every `Set-Cookie` line, not just the last one: the C bridge
keeps duplicate headers in receipt order, which is why a session can track more
than one cookie per response.

---

## 5. Sessions

```pengu
import std.json
import std.petitio
import std.spark

weave main into int:
    var session as Session is calling Session.new
    defer banish session
    calling session.set_header with "Accept", "application/json"
    calling session.set_cookie with "theme", "dark"

    var r as result of Response to HttpError is calling session.get with "https://httpbin.org/cookies"
    defer banish r
    if not r.is_ok:
        return 1
    var resp as Response is r.value
    calling spark.println with resp.body
    return 0
```

* A session header applies only to requests that do not set the same name; the
  request always wins.
* Cookies are sent as one `Cookie` header. If the request already sets `Cookie`,
  the session's jar is not sent for that call (the jar is still updated from the
  response).
* After every response the session stores `resp.cookies` and forgets the names in
  `resp.cleared_cookies`.
* **Expiry:** a non-positive `Max-Age` (`0`, `-1`, any negative) clears a
  cookie; when there is no `Max-Age`, an `Expires` date at or before "now" clears
  it. `Max-Age` wins over `Expires` (RFC 6265 §5.3). Dates are parsed by
  libcurl's `curl_getdate`, which accepts every RFC 7231 format.
* The jar is a **name → value store**: it does not scope cookies by domain or
  path. A file written by `save_cookies_to_file` round-trips through
  `load_cookies_from_file`, but domain/path/secure/expiry columns are
  placeholders and other tools may interpret them differently.
* `cookie(name)` returns an owned copy (`""` when absent) and `has_cookie`
  distinguishes a missing cookie from an empty value.

### 5.1 Cookie files

```pengu
import std.petitio

weave main into int:
    var session as Session is calling Session.new
    defer banish session
    var loaded as result of int to HttpError is calling session.load_cookies_from_file with "cookies.txt"
    defer banish loaded
    if not loaded.is_ok:
        return 1
    # ... use the session ...
    var saved as result of void to HttpError is calling session.save_cookies_to_file with "cookies.txt"
    banish saved
    return 0
```

The format is Netscape's, seven tab-separated columns: `domain`,
`include-subdomains`, `path`, `secure`, `expires`, `name`, `value`. Comment
lines (`#`) and blank lines are skipped; a line with fewer than seven fields is
ignored.

---

## 6. Errors

Every network operation returns `result … to HttpError`; none panics on a
transport failure.

| Variant | When |
|---|---|
| `ConnectionFailed(reason)` | DNS failure, refused/reset connection, mid-transfer error. |
| `Timeout(seconds)` | The total or connect deadline expired. |
| `TooManyRedirects(count)` | The redirect limit was reached. |
| `InvalidUrl(url)` | libcurl rejected the URL. |
| `TlsError(reason)` | Certificate/hostname verification or TLS negotiation failed. |
| `ProtocolError(reason)` | Malformed response or an option libcurl rejected. |
| `BodyTooLarge(max_bytes)` | The body exceeded `max_body_bytes`. |
| `HttpOutOfMemory` | An allocation failed. |
| `Unsupported(reason)` | The URL is not `http`/`https`. |
| `HttpIoError(reason)` | A streaming transfer could not open, write or read its file. |
| `Cancelled` | A `send_stream` callback returned `false`. |
| `HttpStatus(status)` | `raise_for_status` saw 4xx/5xx. |

`HttpError.message` returns an owned human-readable string. `HttpError` derives
`Nexus`, so `banish err` releases the reason it carries.

Malformed *program input* to a builder — a method with a space, a URL, credential,
proxy or multipart file name with CR, LF or NUL, a header with `:` in the name or
a control byte in the value, a cookie with `;`, `http_version(Http3)` —
**panics** with a message naming the value. That is a
bug in the caller, not a network condition: validate untrusted data before you put
it in a header. `multipart_file` is the exception; a missing file returns `false`.

---

## 7. One-shot helpers

```pengu
calling petitio.get with url
calling petitio.head with url
calling petitio.delete with url
calling petitio.options with url
calling petitio.post with url
calling petitio.post_json with url, json_value
calling petitio.post_form with url, fields
calling petitio.post_text with url, body, content_type
calling petitio.put_json with url, json_value
calling petitio.patch_json with url, json_value
```

Each creates a request, sends it and releases the request before returning, so
the only thing you own is the returned result.

### 7.1 `fetch_many`: concurrent requests without async

```pengu
import std.petitio
import std.spark

weave main into int:
    var requests as list of Request is list of Request
    calling requests.push with (calling Request.new with "GET", "https://example.com/a")
    calling requests.push with (calling Request.new with "GET", "https://example.com/b")
    var results as list of result of Response to HttpError is calling petitio.fetch_many with requests
    var i as int is 0
    while i < results.len:
        var r as result of Response to HttpError is results at i
        if r.is_ok:
            calling spark.println_int with r.value.status
        banish r
        set i is i + 1
    banish results
    for request in requests:
        banish request
    banish requests
    return 0
```

`fetch_many` drives libcurl's `multi` engine on **one thread**: HTTP/2 transfers
share a connection and HTTP/1.1 ones are spread over the engine's connections.
It blocks until every transfer finishes and returns results **in input order**; a
connection failure in one transfer does not abort the others. The input
`Request` structs stay owned by the caller (the C handles built from them are
released internally), which is why the example banishes them at the end.

---

## 8. Feature matrix

| Feature | Status |
|---|---|
| GET / POST / PUT / DELETE / HEAD / PATCH / OPTIONS and custom methods | ✅ |
| Custom headers, case-insensitive replacement | ✅ |
| JSON body, response `.json()` | ✅ |
| `application/x-www-form-urlencoded` body | ✅ |
| `multipart/form-data`, in memory and from a file | ✅ |
| Query strings, URL parsing, percent-coding | ✅ |
| Total and connect timeouts | ✅ |
| Redirect following with a limit, or none | ✅ |
| TLS verification toggle | ✅ |
| Basic, Digest and negotiated authentication, Bearer tokens | ✅ |
| HTTP proxies and SOCKS5 (`socks5h`) with credentials | ✅ |
| HTTP/1.0, HTTP/1.1, HTTP/2 over ALPN, HTTP/2 prior knowledge | ✅ |
| Cookies with `Max-Age` and `Expires` expiry | ✅ |
| Cookie files (Netscape format) | ✅ |
| Response body cap | ✅ |
| Streaming downloads to a file or a callback | ✅ |
| Concurrent requests without threads (`fetch_many`) | ✅ |
| HTTP/3 | ❌ reported by `Response.http_version`; not requestable |
| Connection-pool controls, streaming **uploads**, async/await | ❌ libcurl defaults only |
| Cookie domain/path scoping, `Public Suffix List` | ❌ name → value jar only |

### 8.1 Concurrency

`petitio_global_init` runs exactly once behind the platform's once primitive
(`pthread_once` / `InitOnceExecuteOnce`), and every `send` creates its own
libcurl handle, so *independent* requests from different threads are safe.

`fetch_many` is the **single-threaded** way to run N transfers at once: it uses
libcurl's `multi` engine, which multiplexes HTTP/2 streams on one connection and
spreads HTTP/1.1 requests over several connections. It does not need (or start)
threads, and it does not use `std.filum`.

A single `Request`, `Response` or `Session` is **not** safe for concurrent
mutation: the builder methods write plain fields and the maps are not locked.
Share a `Session` between threads only by serializing access (one mutex in the
caller); a per-thread session is the simple, correct choice.

### 8.2 Cookie expiry details

`Max-Age=<n>` is parsed as a number and wins over `Expires` when present
(RFC 6265 §5.3). A **non-positive** value clears the cookie: `Max-Age=0`,
`Max-Age=-1`, `Max-Age=-999` all delete it, while `Max-Age=01` is a one-second
cookie and does not.

Without `Max-Age`, `Expires=<HTTP-date>` is parsed by `curl_getdate` and compared
with the current time; an unparseable date expires nothing. The jar does not
scope cookies by domain or path, so the date is the only attribute that changes
its lifetime beyond an explicit `remove_cookie`.

---

## 9. Examples

### 9.1 Download a file

```pengu
import std.petitio
import std.spark

weave main into int:
    var req as Request is calling Request.new with "GET", "https://example.com/data.csv"
    defer banish req
    calling req.max_body_bytes with 256 * 1024 * 1024
    var r as result of Response to HttpError is calling req.send_to_file with "data.csv"
    defer banish r
    if not r.is_ok:
        var failure as HttpError is calling petitio.take_error with (sigil of r)
        var why as string is calling failure.message
        calling spark.eprintln with why
        banish why
        banish failure
        return 1
    var resp as Response is calling petitio.take_response with (sigil of r)
    calling spark.println with "downloaded {resp.bytes_written} bytes"
    banish resp
    return 0
```

`send_to_file` streams straight to disk: a multi-gigabyte body never sits in RAM.
For small payloads, `petitio.get(url).body` is simpler and `send_to_file` would
add a file for nothing. `max_body_bytes` is enforced by the write callback itself,
so a server that lies about `Content-Length` cannot fill the disk past the cap.

### 9.2 Consume a JSON API

```pengu
import std.json
import std.petitio
import std.spark

weave main into int:
    var req as Request is calling Request.new with "GET", "https://api.example.com/v1/items"
    defer banish req
    calling req.header with "Accept", "application/json"
    calling req.timeout with 5.0

    var r as result of Response to HttpError is calling req.send
    defer banish r
    if not r.is_ok:
        var failure as HttpError is calling petitio.take_error with (sigil of r)
        var why as string is calling failure.message
        calling spark.eprintln with why
        banish why
        banish failure
        return 1
    var resp as Response is calling petitio.take_response with (sigil of r)
    defer banish resp
    var parsed as result of JsonValue to json.JsonError is calling resp.json
    defer banish parsed
    if not parsed.is_ok:
        return 1
    var root as JsonValue is parsed.value
    calling spark.println_int with (calling root.array_len)
    return 0
```

### 9.3 Bearer authentication

```pengu
var req as Request is calling Request.new with "GET", "https://api.example.com/me"
defer banish req
calling req.auth_bearer with token
var r as result of Response to HttpError is calling req.send
```

### 9.4 Session with cookies

```pengu
var session as Session is calling Session.new
defer banish session
var login as result of Response to HttpError is calling session.post_json with "https://example.com/login", credentials
defer banish login
if not login.is_ok:
    return 1
var home as result of Response to HttpError is calling session.get with "https://example.com/"
defer banish home
```

### 9.5 Upload a file with multipart

```pengu
var req as Request is calling Request.new with "POST", "https://example.com/upload"
defer banish req
calling req.multipart_field with "description", "quarterly report"
if not (calling req.multipart_file with "file", "report.pdf"):
    return 1
var r as result of Response to HttpError is calling req.send
```

### 9.6 Proxy

```pengu
var req as Request is calling Request.new with "GET", "https://example.com/"
defer banish req
calling req.proxy with "http://127.0.0.1:8080", "user:password"
```

SOCKS5 with DNS resolved on the proxy (`socks5h`, so no query leaks locally):

```pengu
calling req.socks_proxy with "127.0.0.1:1080", ""
```

### 9.7 Streaming to a callback

```pengu
import std.petitio
import std.spark

rune Progress:
    chunks as int
    bytes as i64

weave on_chunk with chunk as string, user as ref to void into bool:
    var progress as ref to Progress is transmute user to ref to Progress
    set progress->chunks is progress->chunks + 1
    set progress->bytes is progress->bytes + (chunk length to i64)
    return true

weave main into int:
    var req as Request is calling Request.new with "GET", "https://example.com/big.bin"
    defer banish req
    var progress as Progress is with chunks is 0, bytes is 0
    var r as result of Response to HttpError is calling req.send_stream with on_chunk, (sigil of progress)
    defer banish r
    if not r.is_ok:
        return 1
    var resp as Response is calling petitio.take_response with (sigil of r)
    calling spark.println with "{progress.chunks} chunks, {progress.bytes} bytes"
    calling spark.println with "server wrote {resp.bytes_written}"
    banish resp
    return 0
```

`chunk` is a **borrowed view** of libcurl's buffer: valid only during the call.
Do not store it, banish it, or let it escape into a `defer`. Returning `false`
aborts with `HttpError.Cancelled` and `bytes_written` reports how much arrived
before the abort.

### 9.8 Concurrent requests

```pengu
var requests as list of Request is list of Request
calling requests.push with (calling Request.new with "GET", "https://example.com/a")
calling requests.push with (calling Request.new with "GET", "https://example.com/b")
var results as list of result of Response to HttpError is calling petitio.fetch_many with requests
# ... use results ...
banish results
for request in requests:
    banish request
banish requests
```

### 9.9 HTTP/2

```pengu
var req as Request is calling Request.new with "GET", "https://www.google.com/"
defer banish req
calling req.http_version with HttpVersion.Http2      # ALPN, falls back to 1.1
var r as result of Response to HttpError is calling req.send
# resp.http_version tells you what the server actually spoke.
```

### 9.10 Digest authentication

```pengu
var req as Request is calling Request.new with "GET", "https://httpbin.org/digest-auth/auth/user/pass/sha-256"
defer banish req
calling req.auth_digest with "user", "pass"
var r as result of Response to HttpError is calling req.send
```

libcurl sends the request, receives the `401` challenge, computes the digest and
retries. The password never travels in the clear (still: use HTTPS).

---

## 10. Smart linking

`std/petitio.d.pengu` declares the bridge and the two libraries it needs:

```text
include "petitio.h"
link "petitio"
link "curl"
```

Importing `std.petitio` is what pulls them in, and only for that program:

* `build_runtime.py` compiles `std_c/petitio.c` into `build/lib/libpetitio.a`
  (strict `-std=c99 -Wall -Wextra -Werror`), discovering `curl/curl.h` with a
  preprocessor probe and skipping the unit with an actionable message if it is
  missing;
* the generated `bundle.c` contains `#include "petitio.h"` only when the module
  is imported;
* the link line gains `-lpetitio -lcurl` only for that program;
* `-ffunction-sections` + `--gc-sections` then drop the bridge functions the
  program does not call, so even importing the module does not pay for the
  parts you do not use.

Verify it yourself:

```bash
python build_runtime.py
python -m pytest tests/build/test_smart_linking.py -v
```

The test builds five projects (no import, lingua, regulus, both, petitio) and
checks the bundle text, the verbose link line and `nm`.

---

## 11. Regenerating the binding

`std/petitio.d.pengu` is generated from `std_c/petitio.h` and then hand-tuned:

```bash
pengu bind std_c/petitio.h --output std/petitio.d.pengu \
    --cpp-flags="-DPETITIO_BIND=1" --links petitio curl
```

The `PETITIO_BIND` branch in the header replaces `pengu_runtime.h` with a
three-field `PenguString` declaration, because the binder's pycparser cannot
digest the GNU extensions inside the runtime header. After generating, apply the
documented edits (see the comment at the top of the `.d.pengu`): `PenguString`
→ `string`, `int64_t` → `i64`, `double` → `f64`, inline the generated
`petitio_stream_fn` alias at its one use site, and replace the generated
`omen petitio_error` with `const` declarations (the C header already defines the
enum).

The 2.13 bridge adds five exported groups to that surface: the protocol/auth
setters (`petitio_request_set_http_version`, `petitio_request_set_auth_mode`),
the streaming entry points (`petitio_request_perform_to_file`,
`petitio_request_perform_stream`), the multi engine (`petitio_multi_*`), the
HTTP-date parser (`petitio_parse_http_date`) and `petitio_response_bytes_written`.
The callback type is `bool (*)(PenguString, void *)`; the chunk is borrowed.

---

## 12. Comparison with Python's `requests`

| `requests` | `std.petitio` |
|---|---|
| `requests.get(url)` | `petitio.get(url)` |
| `requests.post(url, json=v)` | `petitio.post_json(url, v)` |
| `requests.post(url, data=fields)` | `petitio.post_form(url, fields)` |
| `requests.Session()` | `Session.new` |
| `session.headers.update(...)` | `session.set_header(...)` |
| `session.cookies.set(...)` | `session.set_cookie(...)` |
| `resp.status_code` | `resp.status` |
| `resp.headers["X"]` | `resp.header("X")` (owned copy) |
| `resp.text` | `resp.text()` (owned copy) |
| `resp.json()` | `resp.json()` (a `result`) |
| `resp.raise_for_status()` | `resp.raise_for_status()` (a `result`) |
| `timeout=5` | `req.timeout(5.0)` |
| `allow_redirects=False` | `req.no_redirects` |
| `verify=False` | `req.insecure` |
| `auth=("u", "p")` | `req.auth_basic("u", "p")` |
| `headers={"Authorization": "Bearer …"}` | `req.auth_bearer(token)` |
| `files={"f": open(...)}` | `req.multipart_file("f", path)` |
| `proxies={...}` | `req.proxy(url, credentials)` / `req.socks_proxy(...)` |
| `auth=HTTPDigestAuth(...)` | `req.auth_digest(user, password)` |
| `stream=True` + `iter_content()` | `req.send_stream(cb, user)` |
| `stream=True` + `resp.raw` to a file | `req.send_to_file(path)` |
| HTTP/2 (always negotiated by urllib3) | `req.http_version(HttpVersion.Http2)` |
| `grequests` / `aiohttp` for parallelism | `petitio.fetch_many(requests)` (single thread) |
| `http.cookiejar.MozillaCookieJar` | `Session.load_cookies_from_file` / `save_cookies_to_file` |
| exceptions: `requests.ConnectionError`, `Timeout`, … | `result` + `HttpError` variants |
| connection pooling between calls | libcurl keeps no handle between requests |

The two intentional differences are ownership and errors: PenguScript has no
garbage collector, so every returned string is explicitly released, and no
network failure is thrown — it is a value you decide what to do with.

---

## 13. Tests

| File | What it proves |
|---|---|
| `tests/stdlib/test_petitio.py` | Offline contract: URL codec, `parse_url`, builders, response queries, error model, `take_*`, protocol/auth modes, cookie files; the module's own 23 in-module tests; plus a Python guard that `HttpError` stays aligned with `enum petitio_error`. |
| `tests/compat/test_petitio_vs_requests.py` | Local `http.server` compared with `urllib.request` (and `requests` when installed): status, body, redirect, 404, cookies, `Expires`/`Max-Age`, form encoding, timeout, connection refused, body cap, streaming, `fetch_many` ordering. The live tests (httpbin, Google HTTP/2, badssl TLS, parallel timing) are opt-in with `PETITIO_LIVE=1`. |
| `tests/conformance/compliance/petitio_*.pengu` | Seven offline corpus programs run by the conformance harness. |
| `tests/build/test_smart_linking.py` | `-lpetitio -lcurl` only when imported, and unreferenced bridge functions are garbage-collected. |
| `tests/stdlib/audit/test_leaks_comprehensive.py` | `test_leaks_petitio_offline` and the `or else` box gate, clean under `-fsanitize=address` with `detect_leaks=1`. |

Network tests never touch the public internet: they start a throwaway server on
an ephemeral port, which keeps CI deterministic and offline.
