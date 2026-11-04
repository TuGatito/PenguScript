# std.net

> Source: `std/net.pengu`

std.net.pengu — blocking TCP sockets for long-lived tools (LSP `--tcp`).

The LSP transport needs a listening socket, accepted connections and
byte-exact reads/writes.  This module exposes exactly that surface: a plain
`Socket` rune holding the OS descriptor and free functions for the
operations, so no heap object hides behind the handle.

## Example
```pengu
import std.net
import std.io

weave main into int:
    let server as result of net.Socket to string is calling net.listen with "127.0.0.1", 0
    if server is ok:
        let conn as result of net.Socket to string is calling net.accept with (sigil of server.value)
        if conn is ok:
            let frame as string is calling net.read with (sigil of conn.value), 4096
            calling net.close with (sigil of conn.value)
            banish frame
        calling net.close with (sigil of server.value)
    return 0
```

## Memory
`listen`/`accept`/`connect` return a `result` whose payload is a value rune;
a failed result owns its error string and must be released with `banish`
(or matched with `or:`).  `read` returns an owned string; `write` borrows its
argument.  A `Socket` is just an integer descriptor: `net.close` is the only
resource release and is idempotent.

## Design notes
- **POSIX first.** Linux/macOS use BSD sockets.  Windows builds expose the
  same API but return an `err_of` “not available” result instead of failing
  to compile; the LSP stdio transport is the portable path.
- **Blocking by design.** The server loop is one connection per thread or one
  blocking read; the LSP does not need non-blocking I/O for its framing.
- **Descriptors are `i64`.** A Windows `SOCKET` is pointer-sized, so a 32-bit
  `int` would truncate it.  `i64` keeps the ABI correct on every platform.
- **Negative errno.** The C bridge returns `-errno`; the wrappers turn that
  into a human-readable `err(...)` string with `strerror`.

---

### `NET_VERSION`

> **NET_VERSION** : string

 std.net.pengu — blocking TCP sockets for long-lived tools (LSP `--tcp`).

 The LSP transport needs a listening socket, accepted connections and
 byte-exact reads/writes.  This module exposes exactly that surface: a plain
 `Socket` rune holding the OS descriptor and free functions for the
 operations, so no heap object hides behind the handle.

 ## Example
 ```pengu
 import std.net
 import std.io

 weave main into int:
     let server as result of net.Socket to string is calling net.listen with "127.0.0.1", 0
     if server is ok:
         let conn as result of net.Socket to string is calling net.accept with (sigil of server.value)
         if conn is ok:
             let frame as string is calling net.read with (sigil of conn.value), 4096
             calling net.close with (sigil of conn.value)
             banish frame
         calling net.close with (sigil of server.value)
     return 0
 ```

 ## Memory
 `listen`/`accept`/`connect` return a `result` whose payload is a value rune;
 a failed result owns its error string and must be released with `banish`
 (or matched with `or:`).  `read` returns an owned string; `write` borrows its
 argument.  A `Socket` is just an integer descriptor: `net.close` is the only
 resource release and is idempotent.

 ## Design notes
 - **POSIX first.** Linux/macOS use BSD sockets.  Windows builds expose the
   same API but return an `err_of` “not available” result instead of failing
   to compile; the LSP stdio transport is the portable path.
 - **Blocking by design.** The server loop is one connection per thread or one
   blocking read; the LSP does not need non-blocking I/O for its framing.
 - **Descriptors are `i64`.** A Windows `SOCKET` is pointer-sized, so a 32-bit
   `int` would truncate it.  `i64` keeps the ABI correct on every platform.
 - **Negative errno.** The C bridge returns `-errno`; the wrappers turn that
   into a human-readable `err(...)` string with `strerror`.

### `Socket`

> rune Socket

```pengu
    fd as i64
```

 A live TCP connection or listening socket.

 `fd` is a negative sentinel when closed.  Copying the rune copies the
 descriptor, so only one owner should call `close`.

### `is_open`

> **is_open**(s: ref to Socket) -> bool

 True when the handle has not been closed.

### `close`

> **close**(s: ref to Socket) -> void

 Closes `s` and marks it closed.  Safe to call twice.

### `_net_error_text`

> **_net_error_text**(code: int) -> string

 ----------------------------------------------------------------------------
 Error text
 ----------------------------------------------------------------------------

### `_net_strerror`

> **_net_strerror**(code: int) -> string

_Undocumented._

### `listen`

> **listen**(host: string, port: int) -> result of Socket to string

 Creates a TCP listening socket bound to `host`:`port`.

 `port` 0 asks the OS for an ephemeral port (useful in tests).  The result is
 a `result of Socket to string`: `ok(socket)` or `err(message)`.

### `accept`

> **accept**(s: ref to Socket) -> result of Socket to string

 Accepts one pending connection on `s`.

### `connect`

> **connect**(host: string, port: int) -> result of Socket to string

 Connects to `host`:`port`.

### `read`

> **read**(s: ref to Socket, max_bytes: int) -> string

 Reads up to `max_bytes` bytes from `s`.

 Returns an owned string; a closed connection or error yields an empty string
 (use `read_exact` when a short read must be reported).

### `read_exact`

> **read_exact**(s: ref to Socket, n: int) -> maybe string

 Reads exactly `n` bytes from `s`.

 Returns `some bytes` only when all requested bytes arrived before EOF.

### `write`

> **write**(s: ref to Socket, data: string) -> int

 Writes every byte of `data` to `s`.

 Returns the number of bytes written, or a negative value on error.

### `_net_listen`

> **_net_listen**(host: string, port: int) -> i64

 ----------------------------------------------------------------------------
 POSIX C bridges
 ----------------------------------------------------------------------------

### `_net_accept`

> **_net_accept**(fd: i64) -> i64

_Undocumented._

### `_net_connect`

> **_net_connect**(host: string, port: int) -> i64

_Undocumented._

### `_net_read`

> **_net_read**(fd: i64, max_bytes: int) -> string

_Undocumented._

### `_net_read_exact`

> **_net_read_exact**(fd: i64, n: int) -> maybe string

_Undocumented._

### `_net_write`

> **_net_write**(fd: i64, data: string) -> int

_Undocumented._

### `_net_close`

> **_net_close**(fd: i64) -> void

_Undocumented._

