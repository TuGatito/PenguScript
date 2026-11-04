# std.io

> Source: `std/io.pengu`

std/io.pengu — binary-safe standard I/O for stdio-driven tools.

`std.spark` covers line-oriented console input, but an LSP (or any protocol
with `Content-Length` framing) needs to read exactly N bytes without losing
embedded NULs, and needs to write a frame and flush it.  The methods here
keep the language's byte-oriented `string` representation: the returned
string's `length` is the number of bytes read, even when those bytes include
`\0`.

## Example
```pengu
import std.io
import std.spark

weave main into int:
    let header as string is calling io.read_stdin_line
    let body as maybe string is calling io.read_stdin_exact with 16
    if body is present:
        calling io.write_stdout with body.value
        calling io.flush_stdout
    return 0
```

## Memory
Every `string` returned by `read_*` is freshly allocated and owned by the
caller; release it with `banish`.  `write_*` borrows its argument and never
frees it.  A `maybe string` owns its payload only when present.

## Design notes
- **Byte counts, not characters.** The functions operate on `PenguString.len`
  bytes and never treat the buffer as NUL-terminated.  This is what makes a
  binary LSP frame (`Content-Length: 42\r\n\r\n{...}`) safe.
- **No hidden buffering layer.** Reads use `fread` on `stdin`, writes use
  `fwrite` on `stdout`/`stderr`, and `flush_*` exposes `fflush` so a client
  that waits for a response cannot deadlock.
- **`is_tty` is advisory.** It lets the CLI choose coloured diagnostics;
  redirected streams report false.

---

### `IO_VERSION`

> **IO_VERSION** : string

 std/io.pengu — binary-safe standard I/O for stdio-driven tools.

 `std.spark` covers line-oriented console input, but an LSP (or any protocol
 with `Content-Length` framing) needs to read exactly N bytes without losing
 embedded NULs, and needs to write a frame and flush it.  The methods here
 keep the language's byte-oriented `string` representation: the returned
 string's `length` is the number of bytes read, even when those bytes include
 `\0`.

 ## Example
 ```pengu
 import std.io
 import std.spark

 weave main into int:
     let header as string is calling io.read_stdin_line
     let body as maybe string is calling io.read_stdin_exact with 16
     if body is present:
         calling io.write_stdout with body.value
         calling io.flush_stdout
     return 0
 ```

 ## Memory
 Every `string` returned by `read_*` is freshly allocated and owned by the
 caller; release it with `banish`.  `write_*` borrows its argument and never
 frees it.  A `maybe string` owns its payload only when present.

 ## Design notes
 - **Byte counts, not characters.** The functions operate on `PenguString.len`
   bytes and never treat the buffer as NUL-terminated.  This is what makes a
   binary LSP frame (`Content-Length: 42\r\n\r\n{...}`) safe.
 - **No hidden buffering layer.** Reads use `fread` on `stdin`, writes use
   `fwrite` on `stdout`/`stderr`, and `flush_*` exposes `fflush` so a client
   that waits for a response cannot deadlock.
 - **`is_tty` is advisory.** It lets the CLI choose coloured diagnostics;
   redirected streams report false.

### `_io_from_bytes`

> **_io_from_bytes**(data: ref to u8, n: int) -> string

 Builds an owned PenguString from exactly `n` bytes, preserving embedded NULs.

 ## Motivo
 `pengu_string_new` uses `strlen`, which truncates a binary frame at the
 first NUL.  Constructing the three-field struct here is the only way to keep
 the exact length the caller read.

 ## Memoria
 The returned string owns a fresh `n`-byte buffer (plus the NUL terminator
 that makes accidental C-string use safe).  The caller releases it.

### `read_stdin`

> **read_stdin**(max_bytes: int) -> string

 Reads up to `max_bytes` bytes from stdin.

 ## Parámetros
 - `max_bytes`: upper bound (0 returns an empty string).

 ## Retorno
 An owned string with the bytes actually read; empty at EOF or on error.

 ## Memoria
 The caller releases the result with `banish`.

### `_io_read_stdin`

> **_io_read_stdin**(max_bytes: int) -> string

_Undocumented._

### `read_stdin_exact`

> **read_stdin_exact**(n: int) -> maybe string

 Reads exactly `n` bytes from stdin.

 ## Parámetros
 - `n`: exact byte count (must be > 0).

 ## Retorno
 `some bytes` when all `n` bytes arrived, `none` at EOF or on a short read.

 ## Memoria
 The payload is owned by the caller; release it with `banish`.

### `_io_read_stdin_exact`

> **_io_read_stdin_exact**(n: int) -> maybe string

_Undocumented._

### `read_stdin_all`

> **read_stdin_all**() -> string

 Reads stdin until EOF.

 ## Retorno
 An owned string with every byte read; empty when stdin is already at EOF.

 ## Memoria
 The caller releases the result with `banish`.

### `_io_read_stdin_all`

> **_io_read_stdin_all**() -> string

_Undocumented._

### `read_stdin_line`

> **read_stdin_line**() -> string

 Reads one line from stdin, without the trailing newline.

 Provided here so a client can use `std.io` alone; `std.spark.read_line` is
 the higher-level prompt-aware version.

### `_io_read_stdin_line`

> **_io_read_stdin_line**() -> string

_Undocumented._

### `write_stdout`

> **write_stdout**(data: string) -> bool

 Writes `data` to stdout.

 ## Retorno
 True when every byte was written, false otherwise.

 ## Memoria
 Borrows `data`; never frees it.

### `_io_write_stdout`

> **_io_write_stdout**(data: string) -> bool

_Undocumented._

### `write_stderr`

> **write_stderr**(data: string) -> bool

 Writes `data` to stderr.

 ## Retorno
 True when every byte was written, false otherwise.

 ## Memoria
 Borrows `data`; never frees it.

### `_io_write_stderr`

> **_io_write_stderr**(data: string) -> bool

_Undocumented._

### `flush_stdout`

> **flush_stdout**() -> void

 Flushes buffered stdout.

### `_io_flush_stdout`

> **_io_flush_stdout**() -> void

_Undocumented._

### `flush_stderr`

> **flush_stderr**() -> void

 Flushes buffered stderr.

### `_io_flush_stderr`

> **_io_flush_stderr**() -> void

_Undocumented._

### `is_tty`

> **is_tty**(fd: int) -> bool

 True when `fd` refers to a terminal.

 ## Parámetros
 - `fd`: 0 = stdin, 1 = stdout, 2 = stderr.

### `_io_is_tty`

> **_io_is_tty**(fd: int) -> bool

_Undocumented._

