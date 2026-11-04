# std.secrets

> Source: `std/secrets.pengu`

std/secrets.pengu — optional libsodium-backed secure primitives.

Import this module only when the project links libsodium
(`links = ["sodium"]` in `pengu.toml`).  It provides cryptographically
secure random bytes, SHA-256 and secure memory wiping; for TLS/HTTP use
`std.petitio` (libcurl) or a dedicated mbedTLS satellite.

## Memory
`random_bytes` returns an owned string; `sha256_raw` returns owned bytes;
`wipe` mutates the caller's buffer and allocates nothing.

---

### `SECRETS_VERSION`

> **SECRETS_VERSION** : string

_Undocumented._

### `ccx_sodium_init`

> **ccx_sodium_init**() -> bool

_Undocumented._

### `ccx_sodium_random`

> **ccx_sodium_random**(bytes: list of u8, n: int) -> bool

_Undocumented._

### `ccx_sodium_list_string`

> **ccx_sodium_list_string**(bytes: list of u8, n: int) -> string

_Undocumented._

### `ccx_sodium_sha256`

> **ccx_sodium_sha256**(data: string) -> string

_Undocumented._

### `ccx_sodium_wipe`

> **ccx_sodium_wipe**(p: ref to void, n: int) -> void

_Undocumented._

### `ccx_sodium_compare`

> **ccx_sodium_compare**(a: ref to void, b: ref to void, n: int) -> int

_Undocumented._

### `init`

> **init**() -> bool

 Initializes libsodium once. `random_bytes`/`sha256_raw` call it implicitly.

### `random_bytes`

> **random_bytes**(n: int) -> string

 Returns `n` cryptographically secure random bytes as an owned string.

### `sha256_raw`

> **sha256_raw**(data: string) -> string

 SHA-256 raw bytes, owned.

### `wipe`

> **wipe**(p: ref to void, n: int) -> void

 Overwrites `n` bytes at `p` with zeros through sodium_memzero.

### `compare`

> **compare**(a: ref to void, b: ref to void, n: int) -> int

 Constant-time comparison; 0 means equal.

### `bytes_to_string`

> **bytes_to_string**(data: ref to u8, n: int) -> string

_Undocumented._

