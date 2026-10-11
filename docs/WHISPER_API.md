# `std.whisper` — frozen public API contract

> **Status: frozen.** This is the API that Chunk 7 (`filum`, `celeris`) and the
> remaining migration chunks are built against. Changing a signature here is a
> breaking change and must bump `WHISPER_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/whisper.pengu`](../std/whisper.pengu).
> Bugs fixed in this revision: [`BUGS_FIXED_CHUNK6.md`](BUGS_FIXED_CHUNK6.md).

`whisper` owns logging: six severities, ANSI colours, ISO timestamps, JSON
lines, file and stderr redirection, hierarchical child loggers and a per-name
singleton registry. It imports `std.spark` (I/O), `std.scrolls`, `std.chronicle`
(timestamps), `std.archivum` (file append) and `std.rites` (environment,
process exit).

The module declares `pengu_log_*` / `pengu_map_keys_string` and then sets
`insignia whisper_`. The insignia is load-bearing: without it the top-level weave
`log` would be emitted as a C symbol named `log` when `whisper` is the entry
module, and `<math.h>` already declares `double log(double)`. Three `antiquus`
blocks provide a portable process-wide mutex; `@export("whisper__mtx")` keeps the
accessor alive for the raw C callers.

**Call rituals unqualified.** After `import std.whisper`, write
`calling Logger.new with "app"` and `calling Logger.get_or_create with "app"`.
The dotted form `whisper.Logger.new` does not resolve in this compiler (see
finding C-2 in [`BUGS_FIXED_CHUNK6.md`](BUGS_FIXED_CHUNK6.md)); the type name in a
`var` annotation is still `whisper.Logger`.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every `string` parameter (`msg`, `s`, `path`, `fmt`, `name`, `key`, `value`) | borrowed, read-only | never `banish` |
| `map of string to string` parameters (`fields`) | borrowed, read-only | never `banish` |
| `Logger` returned by a constructor/method | owns `name`, `file_path`, `fmt` and the `context` map | never `banish` in practice (registry-owned values are shared); treat a logger as a value handle |
| `string` returns (`get_level_name`, `get_level_color`, `colorize`, `json_escape_public`, `Logger.get_name`, `Logger.get_timestamp`) | freshly allocated | `banish` |
| `list of string` returns (`log_levels`) | freshly allocated | `banish` |
| `maybe int` returns (`parse_level_string`) | value; owns nothing | never `banish` |

`_render_json` and `_apply_format` return freshly allocated `string`s used
internally; they are private.

## Constants

| Constant | Type | Value |
|---|---|---|
| `WHISPER_VERSION` | `string` | `"2.1.0"` |
| `LOG_TRACE` | `int` | `0` |
| `LOG_DEBUG` | `int` | `1` |
| `LOG_INFO` | `int` | `2` |
| `LOG_WARN` | `int` | `3` |
| `LOG_ERROR` | `int` | `4` |
| `LOG_FATAL` | `int` | `5` |
| `COLOR_RESET` | `string` | `"\033[0m"` |
| `COLOR_GRAY` | `string` | `"\033[90m"` |
| `COLOR_CYAN` | `string` | `"\033[36m"` |
| `COLOR_GREEN` | `string` | `"\033[32m"` |
| `COLOR_YELLOW` | `string` | `"\033[33m"` |
| `COLOR_RED` | `string` | `"\033[31m"` |
| `COLOR_BRIGHT_RED` | `string` | `"\033[91m"` |

## Native runtime declarations (internal C bridges)

| Declaration | Signature |
|---|---|
| `pengu_log_set_level` | `(int) -> void` |
| `pengu_log_get_level` | `() -> int` |
| `pengu_map_keys_string` | `(ref to map of string to string) -> list of string` |

## Global level configuration

| Symbol | Signature | Semantics |
|---|---|---|
| `set_level` | `(level: int) -> void` | Sets the process-global minimum level. |
| `get_level` | `() -> int` | Current global minimum. |
| `is_enabled` | `(level: int) -> bool` | `level >= get_level`. |
| `log_levels` | `() -> list of string` | `["trace", "debug", "info", "warn", "error", "fatal"]`. |
| `set_default_level` | `(level: int) -> void` | Fallback used when no env var names a level (initially `LOG_INFO`). |
| `get_default_level` | `() -> int` | The configured fallback. |
| `set_level_from_string` | `(s: string) -> bool` | Applies a level name; `false` when unknown. |
| `set_level_from_env` | `() -> void` | Scans the env vars below; falls back to `get_default_level`. |
| `parse_level_string` | `(s: string) -> maybe int` | Case-insensitive; accepts `warn` and `warning`. |

Environment variables, in order: `LOG_LEVEL`, `RUST_LOG`, `PENGU_LOG`,
`RITES_LOG_LEVEL`, `WHISPER_LOG`. A variable that is set but unparseable is
reported on stderr and skipped; an unset variable is skipped silently.

## Names, colours and JSON helpers

| Symbol | Signature | Semantics |
|---|---|---|
| `get_level_name` | `(level: int) -> string` | `"TRACE"`…`"FATAL"`; unknown ids map to `"FATAL"`. |
| `get_level_color` | `(level: int) -> string` | One `COLOR_*`; unknown ids map to `COLOR_BRIGHT_RED`. |
| `colorize` | `(level: int, msg: string) -> string` | `msg` wrapped in the level colour plus `COLOR_RESET`. |
| `json_escape_public` | `(s: string) -> string` | JSON-safe copy (public spelling of `_json_escape`). |
| `named_logger` | `(name: string) -> Logger` | Sugar for `Logger.get_or_create`. |
| `default_logger` | `() -> Logger` | The singleton logger named `"default"`. |

## Global logging functions

These filter against the **global** level and always write to stdout. They are
serialised by the internal lock.

| Symbol | Signature | Semantics |
|---|---|---|
| `log` | `(level: int, msg: string) -> void` | Emits `[LEVEL] msg`, colourised. |
| `trace` / `debug` / `info` / `warn` / `error` / `fatal` | `(msg: string) -> void` | `log` at the corresponding level. |
| `fatal_and_exit` | `(msg: string, code: int = 1) -> void` | Logs at FATAL, flushes both streams, exits. Never returns. |
| `log_json` | `(level: int, msg: string, fields: map of string to string) -> void` | JSON line with a `"time"` member and **sorted** field keys. |

## Rune `Logger`

`rune Logger` is a value rune with eight fields:

| Field | Type | Meaning |
|---|---|---|
| `name` | `string` | Hierarchical name; `""` omits it. |
| `min_level` | `int` | This logger's own minimum level. |
| `show_timestamp` | `bool` | Add an ISO timestamp to text lines. |
| `use_color` | `bool` | Colour stdout/stderr lines; files stay plain. |
| `file_path` | `string` | Append to this file when non-empty. |
| `stream` | `int` | `0` = stdout, `1` = stderr. |
| `fmt` | `string` | Template for `_apply_format`; `""` = default layout. |
| `context` | `map of string to string` | Structured members merged into `log_json`. |

The value returned by `Logger.new`, `Logger.named`, `Logger.from_env`,
`Logger.child`, `Logger.get_or_create`, `Logger.with_context` and
`Logger.with_field` owns its `name`, `file_path`, `fmt` and `context`; the
registry copies are process-lifetime singletons.

### Constructors (`ritual`)

| Ritual | Signature | Semantics |
|---|---|---|
| `Logger.new` | `(name: string) -> Logger` | `LOG_TRACE`, no timestamp, colour on, stdout. |
| `Logger.named` | `(name: string, min_level: int) -> Logger` | Same, explicit level. |
| `Logger.from_env` | `() -> Logger` | Named `"default"`, level from the environment. |
| `Logger.get_or_create` | `(name: string) -> Logger` | Singleton registry entry, created on first use. |

### Methods (`enchanting Logger`)

| Method | Signature | Semantics |
|---|---|---|
| `get_name` | `() -> string` | A fresh owned copy of the name. |
| `get_level` | `() -> int` | `self.min_level`. |
| `set_level` | `(level: int) -> void` | Sets the level and publishes it to the registry when the name is registered. |
| `is_enabled` | `(level: int) -> bool` | `level >= self.min_level`. |
| `enable_timestamp` / `disable_timestamp` | `() -> void` | Toggles `show_timestamp`. |
| `enable_color` / `disable_color` | `() -> void` | Toggles `use_color`. |
| `to_file` | `(path: string) -> void` | Redirects to a file (empty restores the stream). File lines are always plain; a failed append is reported on stderr. |
| `to_stderr` | `() -> void` | Redirects to stderr (file mode still wins). |
| `to_stdout` | `() -> void` | Redirects to stdout. |
| `is_file_mode` | `() -> bool` | `file_path` is non-empty. |
| `is_stderr_mode` | `() -> bool` | `stream == 1` and `file_path` is empty. |
| `set_format` | `(fmt: string) -> void` | Template with `{level}`, `{name}`, `{msg}`, `{time}`. Use a raw string (`r"…"`). |
| `with_context` | `(fields: map of string to string) -> Logger` | Copy with `fields` merged into `context`. |
| `with_field` | `(key: string, value: string) -> Logger` | Copy with one context member. |
| `flush` | `() -> void` | Flushes stdout and stderr. |
| `set_level_from_env` | `() -> void` | Applies the environment level to this logger. |
| `get_timestamp` | `() -> string` | ISO-8601 UTC timestamp. |
| `child` | `(sub: string) -> Logger` | Hierarchical child; inherits level, timestamp, colour, file, stream, format and context. Empty `sub` keeps the parent name; bytes outside `[A-Za-z0-9_.-]` become `_`. |
| `log` | `(level: int, msg: string) -> void` | Emits when `level >= self.min_level`. |
| `trace` / `debug` / `info` / `warn` / `error` / `fatal` | `(msg: string) -> void` | `log` at the corresponding level. |
| `log_json` | `(level: int, msg: string, fields: map of string to string) -> void` | JSON line; adds `"time"` exactly when `show_timestamp` is on. |
| `log_json_ex` | `(level: int, msg: string, fields: map of string to string, include_time: bool) -> void` | JSON line with explicit timestamp control. |

## JSON document shape

```
{"level":"INFO","time":"2026-09-25T14:30:00Z","logger":"app","msg":"ready","a":"1","z":"2"}
```

* `level` is always present.
* `time` is present in `log_json_ex(..., true)`, in the global `log_json`, and in
  `Logger.log_json` when `show_timestamp` is on.
* `logger` is present only when the name is non-empty.
* Extra members come from the logger's `context` first, then the call's `fields`
  (the call wins), emitted in ascending byte order.

## Destination precedence

1. `file_path` non-empty → append to the file, always plain.
2. otherwise `stream == 1` → stderr.
3. otherwise → stdout.

Colour applies only to stdout/stderr, never to a file.

## Thread-safety contract

Every emission — the whole line including the newline — runs inside the internal
`_lock` / `_unlock` critical section, so two threads cannot interleave two log
lines. The global helpers and every `Logger` method share that lock.

## Internal helpers (private, `_`-prefixed)

| Symbol | Signature | Purpose |
|---|---|---|
| `_json_escape` | `(s: string) -> string` | JSON escaping incl. `\b`, `\f`, `\u00XX`. |
| `_hex1` / `_hex2` | `(v: int) -> string` | Hex digits for the control escapes. |
| `_sorted_keys` | `(m: map of string to string) -> list of string` | Byte-sorted keys. |
| `_render_json` | `(level, logger_name, msg, fields, include_time) -> string` | Pure JSON renderer. |
| `_apply_format` | `(fmt, lvl, lname, msg, stamp) -> string` | Template substitution. |
| `_registry` | `() -> ref to map of string to Logger` | Singleton registry. |
| `_registry_store_level` | `(name: string, level: int) -> void` | Publishes a level. |
| `_copy_of` | 8 fields `-> Logger` | Field-wise rebuild. |
| `_level_from_env_or` | `(fallback: int) -> int` | Environment resolution. |
| `_env_names` | `() -> list of string` | Consulted env var names. |
| `_mtx` / `_lock` / `_unlock` | see source | Portable process-wide logging mutex. |
| `_default_cell` / `_default_set` / `_default_get` | see source | Shared default-level cell. |
