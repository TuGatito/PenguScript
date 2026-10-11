# `std.rites` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `RITES_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/rites.pengu`](../std/rites.pengu).

`rites` owns the operating-system face of a program: environment variables,
program arguments and flags, process identity and POSIX credentials, the working
directory and the standard per-user directories, platform/host detection,
executable search on `PATH`, and shell execution (blocking status plus captured
`stdout`/`stderr`). Its only import is `std.spark` (for `panic` and the number
parsers); it never imports `std.archivum` in Pengu — instead it `declare`s the
one runtime check it needs (`pengu_c_archivum_is_file`) to avoid the cycle
`archivum -> rites`.

Every result is a fresh allocation made by the C runtime or by the standard
library; no returned string aliases an OS-owned buffer and no argument is
retained. `getenv`, `getcwd`, `getpid`, `uname`, `hostname`, `get_args`, the
`*_dir` helpers and the capture family all own what they return, so release
strings with `banish` (list elements before the list).

## `pengu_runtime.h` gained no symbol

This revision adds **no** symbol to `pengu_runtime.h`. The new process/credential
helpers and the capture family are built entirely inside this module:

* `get_uid`, `get_gid`, `get_euid`, `get_egid` call the private `antiquus` body
  `_rites_id`, a one-line-per-call libc bridge (`getuid`/`getgid`/`geteuid`/
  `getegid`) guarded by `#ifdef _WIN32`.
* `run_capture`, `run_capture_lines`, `run_capture_stderr`, `run_capture_result`
  and `run_shell_capture` use the private `antiquus` bodies `_rites_capture`
  (`popen`/`pclose`) and `_rites_run_status`. The only dependency on libc is what
  `pengu_runtime.h` already `#include`s (`<stdio.h>` for the pipe pair,
  `<unistd.h>` for the credentials on POSIX).
* `getpid`, `getppid`, `getcwd`, `chdir`, `exit`, `exec`, `spawn`, `uname`,
  `hostname` and the environment primitives were already bound to existing
  `pengu_c_*` runtime helpers in 2.0.0 and are unchanged.

The module carries `insignia rites_` **after** the `declare` block: the
`pengu_c_*` declarations keep their exact runtime names, while the module's own
generated C symbols are prefixed so a bundle that links `std.rites` never
redeclares a libc symbol.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every parameter (`name`, `value`, `default`, `s`, `cmd`, `args`, `path`, `m`) | borrowed, read-only | never `banish` |
| scalar returns (`int`, `bool`) | plain value | never `banish` |
| `maybe string` / `maybe int` / `maybe float` / `maybe bool` | `some` owns its payload; `none` owns nothing | `banish` |
| `string` and every string inside a returned `list of string` / `map of string to string` | freshly allocated | `banish` each element, then the container |
| `result of string to string` (`run_capture_result`) | owns its payload | `banish` the result |
| `void` (`exit`, `exec_or_panic`) | no value | — |

## Constants

`RITES_VERSION as string is "2.1.0"` — the revision of the **rites API**, not of
the toolchain. It bumps only when a signature on this page changes.

## Native runtime declarations (internal C bridges)

These 17 `declare`s bind `static inline` helpers of `pengu_runtime.h`; they are
the runtime contract, not the PenguScript API. The three private `antiquus`
bodies (`_rites_capture`, `_rites_run_status`, `_rites_id`) are documented under
"Private helpers".

| Declaration | Signature |
|---|---|
| `pengu_c_getenv` | `(string) -> maybe string` |
| `pengu_c_setenv` | `(string, string, bool) -> bool` |
| `pengu_c_unsetenv` | `(string) -> bool` |
| `pengu_c_get_argc` | `() -> int` |
| `pengu_c_get_argv` | `(int) -> string` |
| `pengu_c_get_args` | `() -> list of string` |
| `pengu_c_getpid` | `() -> int` |
| `pengu_c_getppid` | `() -> int` |
| `pengu_c_getcwd` | `() -> maybe string` |
| `pengu_c_chdir` | `(string) -> bool` |
| `pengu_c_exit` | `(int) -> void` |
| `pengu_c_exec` | `(string, list of string) -> int` |
| `pengu_c_spawn` | `(string, list of string) -> int` |
| `pengu_c_uname` | `() -> string` |
| `pengu_c_hostname` | `() -> string` |
| `pengu_c_get_env_keys` | `() -> list of string` |
| `pengu_c_archivum_is_file` | `(string) -> bool` |

## Environment variables

| Symbol | Signature | Semantics |
|---|---|---|
| `getenv` | `(name: string) -> maybe string` | `some value` when set (an empty string is still present), `none` when unset or `name` is empty. |
| `setenv` | `(name: string, value: string, overwrite: bool is true) -> bool` | Sets a variable; `overwrite=false` keeps an existing value. |
| `unsetenv` | `(name: string) -> bool` | Removes a variable; a missing name is not an error. |
| `get_env_keys` | `() -> list of string` | Names of all currently set variables. |
| `getenv_or` | `(name: string, default: string is "") -> string` | Value, or `default` when unset. |
| `has_env` | `(name: string) -> bool` | True when the variable is currently set. |
| `getenv_int` | `(name: string) -> maybe int` | Parses through `spark.parse_int`; never panics. |
| `getenv_float` | `(name: string) -> maybe float` | Parses through `spark.parse_float`; never panics. |
| `getenv_bool` | `(name: string) -> maybe bool` | `1`/`true`/`TRUE`/`True`/`yes`/`YES`/`Yes` → true, the `0`/`false`/`no` spellings → false, else `none`. |
| `get_env_map` | `() -> map of string to string` | Owned snapshot of the whole environment. |
| `set_env_map` | `(m: map of string to string) -> int` | Sets every entry; returns the number of assignments. |
| `clear_env` | `() -> int` | Clears the process environment; returns the number removed. |
| `expand_env` | `(s: string) -> string` | `$NAME`, `${NAME}` and `%NAME%` are replaced; `$$`/`%%` are literal; unset names expand empty; unterminated forms are kept verbatim; single pass, non-recursive. |
| `env_substitute` | `(s: string) -> string` | Alias of `expand_env`. |

## Program arguments and flags

| Symbol | Signature | Semantics |
|---|---|---|
| `get_argc` | `() -> int` | Argument count including the program name at index 0. |
| `get_argv` | `(idx: int) -> string` | Copy of argument `idx` (0 = program name); out of range yields `""`. |
| `get_args` | `() -> list of string` | One owned copy per argument, from index 0 upward. |
| `arg_at_or` | `(idx: int, default: string is "") -> string` | Argument `idx`, or `default` when out of range. |
| `parse_flags` | `() -> map of string to string` | From `get_args()` (argv[0] skipped): `--key=value` → `key=value`, bare `--flag` → `flag="true"`; positional arguments are ignored. |
| `has_flag` | `(name: string) -> bool` | True when `--name` was passed (leading `--` omitted). |
| `get_flag_value` | `(name: string) -> maybe string` | `some value` for `--name`, `some "true"` for a bare `--name`, else `none`. |

## Process identity and credentials

| Symbol | Signature | Semantics |
|---|---|---|
| `getpid` | `() -> int` | Current process id. |
| `getppid` | `() -> int` | Parent process id; always 0 on Windows. |
| `get_uid` | `() -> maybe int` | Real user id (libc `getuid`); `none` on Windows. |
| `get_gid` | `() -> maybe int` | Real group id (libc `getgid`); `none` on Windows. |
| `get_euid` | `() -> maybe int` | Effective user id (libc `geteuid`); `none` on Windows. |
| `get_egid` | `() -> maybe int` | Effective group id (libc `getegid`); `none` on Windows. |
| `current_user` | `() -> maybe string` | `USER` (fallback `LOGNAME`) on POSIX, `USERNAME` on Windows; `none` when unset. |

## Working directory and standard directories

| Symbol | Signature | Semantics |
|---|---|---|
| `getcwd` | `() -> maybe string` | Current working directory; `none` when it cannot be determined. |
| `chdir` | `(path: string) -> bool` | Changes the current working directory. |
| `home_dir` | `() -> maybe string` | `HOME` on POSIX, `USERPROFILE` or `HOMEDRIVE`+`HOMEPATH` on Windows. |
| `temp_dir` | `() -> maybe string` | `TMPDIR`/`TEMP`/`TMP` (fallback `/tmp`) on POSIX, `TEMP`/`TMP` (fallback `C:\Temp`) on Windows; never `none`. |
| `config_dir` | `() -> maybe string` | `XDG_CONFIG_HOME` or `~/.config`; `%APPDATA%` on Windows. |
| `cache_dir` | `() -> maybe string` | `XDG_CACHE_HOME` or `~/.cache`; `%LOCALAPPDATA%` on Windows. |
| `data_dir` | `() -> maybe string` | `XDG_DATA_HOME` or `~/.local/share`; `%APPDATA%` on Windows. |

## Platform and host information

| Symbol | Signature | Semantics |
|---|---|---|
| `uname` | `() -> string` | `"Windows"`, `"Darwin"`, `"Linux"` or `"Unknown"`. |
| `hostname` | `() -> string` | Machine host name. |
| `os_arch` | `() -> string` | Host CPU architecture: `"x64"`, `"arm64"`, `"x86"`, `"arm"` or `"unknown"`. |
| `os_family` | `() -> string` | Alias of `uname`. |
| `is_windows` | `() -> bool` | Compile-time target predicate. |
| `is_unix` | `() -> bool` | True for every non-Windows target. |
| `is_macos` | `() -> bool` | Compile-time target predicate. |
| `is_linux` | `() -> bool` | Compile-time target predicate. |

## Executable search

| Symbol | Signature | Semantics |
|---|---|---|
| `which_all` | `(cmd: string) -> list of string` | Every `PATH` match, in PATH order; on Windows `.exe`/`.bat`/`.cmd` are also tried. POSIX checks regular-file existence only (no `X_OK`). |
| `which` | `(cmd: string) -> maybe string` | First `PATH` match, or `none`. |

## Process termination and shell execution

| Symbol | Signature | Semantics |
|---|---|---|
| `exit` | `(code: int) -> void` | Terminates the process immediately with `code`; never returns. |
| `exec` | `(cmd: string, args: list of string) -> int` | Blocking `system()`; raw shell status, `-1` on error. Arguments are joined unescaped. |
| `spawn` | `(cmd: string, args: list of string) -> int` | Currently identical to `exec` (blocking `system()`). |
| `exec_ok` | `(cmd: string, args: list of string) -> bool` | True when the shell status is exactly `0`. |
| `exec_or_panic` | `(cmd: string, args: list of string) -> void` | Panics with `Command execution failed with status: <status>` on a non-zero status. |
| `run_shell` | `(cmdline: string) -> int` | Raw command line through the platform shell; raw status, `-1` on error. |
| `shell_escape` | `(s: string) -> string` | POSIX: single-quoted with `'` → `'\''`; Windows: double-quoted with `"` escaped; empty input becomes `''`/`""`. |

## Output capture (new in 2.1.0)

The command line is built in Pengu: every element is passed through
`shell_escape` before `popen`. All five helpers block until the child exits;
stderr is not captured except by `run_capture_stderr`.

| Symbol | Signature | Semantics |
|---|---|---|
| `run_capture` | `(cmd: string, args: list of string) -> maybe string` | `some stdout` on exit 0; `none` on non-zero status, closed pipe or empty command. |
| `run_capture_result` | `(cmd: string, args: list of string) -> result of string to string` | `ok(stdout)` on exit 0, else `err("command exited with code <code>")`. |
| `run_capture_lines` | `(cmd: string, args: list of string) -> maybe list of string` | `some` lines with no trailing newlines (a trailing newline adds no empty entry); `none` on failure; empty output → `some []`. |
| `run_capture_stderr` | `(cmd: string, args: list of string) -> maybe string` | Same shape as `run_capture` but for `stderr`; POSIX runs a subshell redirect, Windows behaves as `run_capture`. |
| `run_shell_capture` | `(cmdline: string) -> maybe string` | `some stdout` for a caller-supplied raw shell line; `none` otherwise. |

## Migración (2.0.0 → 2.1.0)

2.1.0 is a documentation/style migration plus new capability; **nothing is
removed or renamed**. Every 2.0.0 symbol keeps its exact name, bounds and
signature, including the `pengu_c_*` declarations, `clear_env`, `getenv_or`,
`arg_at_or`, `parse_flags` and the aliases (`env_substitute`, `os_family`,
`spawn`).

| Added in 2.1.0 | Notes |
|---|---|
| `run_capture` | Closes the old `run_capture()` TODO; `some stdout` on exit 0. |
| `run_capture_result` | Native `result of string to string` with the exit code in the message. |
| `run_capture_lines` | `run_capture` split into lines. |
| `run_capture_stderr` | The `stderr` counterpart, via a POSIX subshell redirect. |
| `run_shell_capture` | Captured output for a raw command line. |
| `get_uid`, `get_gid`, `get_euid`, `get_egid` | Close the old `get_uid()`/`get_gid()` TODO; `maybe none` on Windows. |
| `insignia rites_` | Prefixes the module's own C symbols; the `pengu_c_*` declares keep their names. |
| `# --- Tests ---` | 49 internal `test` blocks; there were none in 2.0.0. |

**Still unsupported:** `set_uid`/`set_gid`, `fork`/`waitpid` and raw `pipe`
objects remain out of scope; they need runtime-level work, not a doc pass. No
symbol is deprecated in this revision.

## Internal tests

The internal `# --- Tests ---` suite holds **49 `test` blocks** over the private
`_rites_expect_*` harness (`spark.panic`; `std.ward` cannot be imported from a
library module). The tests call unambiguous `_rites_*` wrappers so they stay safe
in the shared namespace used when several bundled modules are type-checked
together.

## Private helpers (internal)

Not public API; do not call them.

| Symbol | Signature | Role |
|---|---|---|
| `_rites_capture` | `antiquus (cmdline: string, stream: string, err: ref to string) -> string` | `popen`/`pclose` capture; empty view on Windows/failure. |
| `_rites_run_status` | `antiquus (cmdline: string) -> int` | Shell exit status via `pclose`; `128 + signal` on signal termination, `-1` on Windows/error. |
| `_rites_id` | `antiquus (which: int) -> int` | `getuid`/`getgid`/`geteuid`/`getegid` selector; `-1` on Windows. |
| `_rites_build_cmdline` | `(cmd: string, args: list of string) -> string` | Joins `cmd` and the escaped `args`. |
| `_rites_shell_capture` | `(cmdline: string, err: ref to string) -> maybe string` | Wraps `_rites_capture`; `none` on failure or empty output. |
| `_rites_split_lines` | `(s: string) -> list of string` | Splits on `"\n"`, dropping a single trailing empty entry. |
| `_rites_contains` | `(s: string, needle: string) -> bool` | Byte-scan substring test. |
| `_rites_has_env` | `(name: string) -> bool` | Test wrapper for `has_env` under a unique name. |
| `_rites_getenv` | `(name: string) -> maybe string` | Test wrapper for `getenv`. |
| `_rites_setenv` | `(name: string, value: string, overwrite: bool) -> bool` | Test wrapper for `setenv`. |
| `_rites_unsetenv` | `(name: string) -> bool` | Test wrapper for `unsetenv`. |
| `_rites_expect_int` | `(got: int, want: int, label: string) -> void` | Test assertion via `spark.panic`. |
| `_rites_expect_str` | `(got: string, want: string, label: string) -> void` | Test assertion via `spark.panic`. |
| `_rites_expect_true` | `(cond: bool, label: string) -> void` | Test assertion via `spark.panic`. |
