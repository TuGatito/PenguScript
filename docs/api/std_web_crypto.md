# std.web.crypto

> Source: `std/web/crypto.pengu`

std.web.crypto — CSPRNG, UUID v4, SHA-256 and HMAC-SHA-256.

WebAssembly-only. Randomness comes from `crypto.getRandomValues` (never
`Math.random`). Digests use `crypto.subtle` and therefore complete
asynchronously; pass a one-shot callback pair and read the hex string with
`text_from`.

```pengu
weave on_hash with value as js.JsValue into void:
    var hex as result of string to js.JsError is calling crypto.text_from with value
    if hex.is_ok:
        calling std.web.console_log with hex.value
        banish hex.value

calling crypto.sha256_hex with "abc", on_hash, on_error
```

`subtle` requires a secure context (HTTPS or `localhost`).

---

### `Value`

> alias Value

_Undocumented._

### `CRYPTO_VERSION`

> **CRYPTO_VERSION** : string

_Undocumented._

### `Bytes`

> alias Bytes

 Owned byte buffer returned by `random_bytes`.

### `random_bytes`

> **random_bytes**(count: int) -> result of Bytes to JsError

_Undocumented._

### `random_int`

> **random_int**(min: int, max: int) -> result of int to JsError

_Undocumented._

### `uuid_v4`

> **uuid_v4**() -> result of string to JsError

_Undocumented._

### `sha256_hex`

> **sha256_hex**(text: string, on_ok: weave with value: Value into void, on_err: weave with value: Value into void) -> result of bool to JsError

_Undocumented._

### `hmac_sha256_hex`

> **hmac_sha256_hex**(text: string, key: string, on_ok: weave with value: Value into void, on_err: weave with value: Value into void) -> result of bool to JsError

_Undocumented._

### `text_from`

> **text_from**(value: JsValue) -> result of string to JsError

_Undocumented._

### `error_from`

> **error_from**(value: JsValue) -> JsError

_Undocumented._

