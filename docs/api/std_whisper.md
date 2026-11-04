# std.whisper

> Source: `std/whisper.pengu`

std/whisper.pengu — the whisper: leveled, structured logging.

Six severities (`LOG_TRACE` through `LOG_FATAL`), ANSI colours, ISO
timestamps, JSON lines, file redirection, stderr redirection, hierarchical
child loggers and a per-name singleton registry.

## Example
```pengu
import std.whisper

weave main into int:
    calling whisper.info with "starting"                  # global logger
    var log as whisper.Logger is calling whisper.Logger.get_or_create with "app"
    calling log.enable_timestamp
    calling log.with_field with "pid", "1234"
    calling log.info with "ready"
    calling whisper.set_level with whisper.LOG_WARN
    calling whisper.debug with "not printed"
    calling whisper.warn with "printed"
    return 0
```

## Memory
Level names, colours, rendered lines and JSON documents are fresh owned
`string`s. `Logger` owns its `name`, `file_path`, `fmt` and `context`
strings; a `Logger` returned by `new`, `named`, `from_env`, `child`,
`get_or_create`, `with_context` or `with_field` therefore owns what it
carries. `log_levels` returns a fresh owned `list of string`. Parameters are
borrowed and never retained.

## Design notes
- **Global functions versus `Logger` runes.** The module-level helpers
  (`log`, `trace`, … `fatal`, `log_json`) filter against the process-global
  level configured by `set_level` / `set_level_from_env` and always write to
  stdout. A `Logger` value has its own `min_level`, destination and
  formatting, and never reads or writes the global level.
- **Levels.** `LOG_TRACE = 0` … `LOG_FATAL = 5`. A message is emitted when
  its level is `>=` the active minimum.
- **Colours.** `get_level_color` maps a level to an ANSI escape. File
  output is always plain so a log file stays greppable; use `set_format` if
  you want a different *text* layout. Per the contract, colouring a file is
  deliberately not offered.
- **JSON.** `_render_json` sorts the field keys before emitting them, so two
  runs with the same fields produce byte-identical documents (2.1.0 fix:
  2.0.0 iterated the hash map and produced a different order every run).
  `Logger.log_json` adds a `"time"` member when `show_timestamp` is on;
  the module-level `log_json` always adds it.
- **Thread safety.** Emission runs inside the private `_lock` / `_unlock`
  critical section, so two threads cannot interleave two log lines. The lock
  is a portable mutex taken from the runtime's thread layer.
- **Default level.** `set_level_from_env` falls back to `get_default_level`
  (initially `LOG_INFO`) when no environment variable names a level, so a
  program that calls it never silently keeps the very verbose global
  `LOG_TRACE` (2.1.0 fix for B18). `set_default_level` changes that fallback.
- **Singleton loggers.** `Logger.get_or_create` (and `named_logger`) keep one
  entry per name in a module-level registry; `set_level` publishes the new
  level back to the registry, so a later `get_or_create` for the same name
  sees it.

## Migration
2.1.0 fixes B12–B24 and adds the Python `logging` parity surface. Every
2.0.0 symbol keeps its signature.

| New in 2.1.0 | Purpose |
|---|---|
| `set_default_level` / `get_default_level` | configurable env fallback |
| `colorize` | wrap a message with a level colour |
| `json_escape_public` | public JSON string escaping |
| `named_logger` | sugar for `Logger.get_or_create` |
| `Logger.to_stderr` / `to_stdout` | stream redirection |
| `Logger.set_format` | `{level}` `{name}` `{msg}` `{time}` template |
| `Logger.with_context` / `with_field` | structured JSON context |
| `Logger.get_name` / `get_or_create` | identity and singleton registry |
| `Logger.is_file_mode` / `is_stderr_mode` | destination queries |
| `Logger.flush` / `get_timestamp` / `set_level_from_env` | runtime helpers |
| `Logger.log_json_ex` | JSON with explicit timestamp control |

---

### `WHISPER_VERSION`

> **WHISPER_VERSION** : string

 Version constant for the std.whisper module.

### `LOG_TRACE`

> **LOG_TRACE** : int

 Severity 0: most verbose level, used for fine-grained tracing.

### `LOG_DEBUG`

> **LOG_DEBUG** : int

 Severity 1: diagnostic detail useful while debugging.

### `LOG_INFO`

> **LOG_INFO** : int

 Severity 2: default operating level for notable, normal events.

### `LOG_WARN`

> **LOG_WARN** : int

 Severity 3: suspicious but non-fatal conditions.

### `LOG_ERROR`

> **LOG_ERROR** : int

 Severity 4: errors that the program recovers from.

### `LOG_FATAL`

> **LOG_FATAL** : int

 Severity 5: unrecoverable failures; also the fallback name for unknown ids.

### `COLOR_RESET`

> **COLOR_RESET** : string

 ANSI escape that resets terminal colours back to the default.

### `COLOR_GRAY`

> **COLOR_GRAY** : string

 ANSI bright-black (grey) foreground, used for trace lines.

### `COLOR_CYAN`

> **COLOR_CYAN** : string

 ANSI cyan foreground, used for debug lines.

### `COLOR_GREEN`

> **COLOR_GREEN** : string

 ANSI green foreground, used for info lines.

### `COLOR_YELLOW`

> **COLOR_YELLOW** : string

 ANSI yellow foreground, used for warn lines.

### `COLOR_RED`

> **COLOR_RED** : string

 ANSI red foreground, used for error lines.

### `COLOR_BRIGHT_RED`

> **COLOR_BRIGHT_RED** : string

 ANSI bright-red foreground, used for fatal lines.

### `pengu_log_set_level`

> **pengu_log_set_level**(level: int) -> void

 C bridge that stores the global minimum log level.

### `pengu_log_get_level`

> **pengu_log_get_level**() -> int

 C bridge that returns the global minimum log level.

### `pengu_map_keys_string`

> **pengu_map_keys_string**(m: ref to map of string to string) -> list of string

 C bridge that copies the keys of a `map of string to string` into a list.

### `_mtx`

> **_mtx**() -> opaque

 Returns the process-wide logging lock handle.

 ## Motivo
 Reuses the runtime's portable mutex factory; `@export` pins the C symbol and
 keeps the accessor alive because `_lock` / `_unlock` call it from raw C.

 ## Memoria
 Allocates the mutex once and keeps it for the process lifetime.

### `_lock`

> **_lock**() -> void

 Acquires the process-wide logging lock.

 ## Motivo
 Serialises whole log lines so two threads cannot interleave their bytes.

 ## Memoria
 No allocations.

### `_unlock`

> **_unlock**() -> void

 Releases the process-wide logging lock acquired by `_lock`.

 ## Motivo
 Pairs one-to-one with `_lock`.

 ## Memoria
 No allocations.

### `_default_cell`

> **_default_cell**() -> opaque

 Returns a pointer to the module's default-level cell.

 ## Motivo
 A module-level `static var` can only live inside one weave, so the default
 level is kept in one C cell that `_default_set` and `_default_get` share.

 ## Memoria
 Static storage; no allocation.

### `_default_set`

> **_default_set**(level: int) -> void

 Stores the default fallback level in the shared cell.

 ## Parámetros
 - `level`: the level to remember.

 ## Retorno
 Nothing.

 ## Memoria
 No allocations.

### `_default_get`

> **_default_get**() -> int

 Reads the default fallback level from the shared cell.

 ## Retorno
 The stored level.

 ## Memoria
 No allocations.

### `_cmp_string`

> **_cmp_string**(a: string, b: string) -> int

 Compares two strings bytewise (`memcmp` with length as tie-breaker).

 ## Motivo
 The JSON renderer has to sort map keys, and PenguScript has no ordering
 operator for `string`. This comparator is exact for NUL-containing strings.

 ## Memoria
 Reads the two borrowed strings; allocates nothing.

### `set_level`

> **set_level**(level: int) -> void

 Sets the global minimum log level.

 ## Parámetros
 - `level`: one of the `LOG_*` constants; messages below it are suppressed by
   the module-level helpers.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling whisper.set_level with whisper.LOG_WARN
 ```

### `get_level`

> **get_level**() -> int

 Returns the current global minimum log level.

 ## Retorno
 One of the `LOG_*` constants.

 ## Ejemplo
 ```pengu
 var level as int is calling whisper.get_level
 ```

### `is_enabled`

> **is_enabled**(level: int) -> bool

 Checks whether `level` meets the current global minimum.

 ## Parámetros
 - `level`: the level to test.

 ## Retorno
 `true` when a message at `level` would be emitted.

 ## Ejemplo
 ```pengu
 if calling whisper.is_enabled with whisper.LOG_DEBUG:
 ```

### `log_levels`

> **log_levels**() -> list of string

 Returns every standard level name in order of increasing severity.

 ## Retorno
 A new owned `list of string`: `trace`, `debug`, `info`, `warn`, `error`,
 `fatal`. Release it with `banish`.

 ## Ejemplo
 ```pengu
 var names as list of string is calling whisper.log_levels
 ```

### `set_default_level`

> **set_default_level**(level: int) -> void

 Stores the default fallback level used when no environment variable names one.

 ## Parámetros
 - `level`: the level to use as the fallback.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling whisper.set_default_level with whisper.LOG_WARN
 ```

### `get_default_level`

> **get_default_level**() -> int

 Returns the default fallback level used by `set_level_from_env`.

 ## Retorno
 The configured fallback (initially `LOG_INFO`).

 ## Ejemplo
 ```pengu
 var fallback as int is calling whisper.get_default_level
 ```

### `get_level_name`

> **get_level_name**(level: int) -> string

 Maps a level int to its uppercase name.

 ## Parámetros
 - `level`: the level id.

 ## Retorno
 `"TRACE"`, `"DEBUG"`, `"INFO"`, `"WARN"`, `"ERROR"` or `"FATAL"`; any other
 id falls through to `"FATAL"`.

 ## Ejemplo
 ```pengu
 calling whisper.get_level_name with 2    # "INFO"
 ```

### `get_level_color`

> **get_level_color**(level: int) -> string

 Maps a level int to its ANSI colour escape.

 ## Parámetros
 - `level`: the level id.

 ## Retorno
 One of the `COLOR_*` constants; unknown ids map to `COLOR_BRIGHT_RED`.

 ## Ejemplo
 ```pengu
 calling whisper.get_level_color with 2    # COLOR_GREEN
 ```

### `colorize`

> **colorize**(level: int, msg: string) -> string

 Wraps `msg` in the colour of `level`, terminated by `COLOR_RESET`.

 ## Parámetros
 - `level`: the level whose colour to use.
 - `msg`: the text to wrap. Borrowed.

 ## Retorno
 A new owned `string`. Release it with `banish`.

 ## Ejemplo
 ```pengu
 var line as string is calling whisper.colorize with whisper.LOG_WARN, "careful"
 ```

### `parse_level_string`

> **parse_level_string**(s: string) -> maybe int

 Parses a level name (case-insensitive) into its integer constant.

 ## Parámetros
 - `s`: `trace`, `debug`, `info`, `warn`/`warning`, `error` or `fatal`.

 ## Retorno
 `some level` on success, `maybe none` for an unknown name.

 ## Ejemplo
 ```pengu
 var opt as maybe int is calling whisper.parse_level_string with "info"
 ```

### `set_level_from_string`

> **set_level_from_string**(s: string) -> bool

 Sets the global minimum level from a level name.

 ## Parámetros
 - `s`: the level name, case-insensitive.

 ## Retorno
 `true` when the level was recognised and applied, `false` otherwise.

 ## Ejemplo
 ```pengu
 if calling whisper.set_level_from_string with "warn":
 ```

### `_env_names`

> **_env_names**() -> list of string

 Returns the environment variable names consulted for the log level, in order.

 ## Retorno
 A new owned `list of string`.

### `_level_from_env_or`

> **_level_from_env_or**(fallback: int) -> int

 Resolves a log level from the environment, or `fallback`.

 ## Parámetros
 - `fallback`: the level to return when no variable names a valid level.

 ## Retorno
 The first successfully parsed level, otherwise `fallback`.

 ## Nota
 A variable that *is* set but holds an unknown name is reported on stderr
 and skipped; a variable that is not set at all is skipped silently. That is
 the 2.1.0 fix for B17, which used to treat both cases identically.

### `set_level_from_env`

> **set_level_from_env**() -> void

 Configures the global minimum level from environment variables.

 ## Retorno
 Nothing. Checks `LOG_LEVEL`, `RUST_LOG`, `PENGU_LOG`, `RITES_LOG_LEVEL` and
 `WHISPER_LOG`, in that order, and falls back to `get_default_level` when none
 of them names a valid level (2.1.0 fix for B18: 2.0.0 left the level at the
 very verbose `LOG_TRACE`).

 ## Ejemplo
 ```pengu
 calling whisper.set_level_from_env
 ```

### `_hex1`

> **_hex1**(v: int) -> string

 Returns one lowercase hex digit for a nibble in `[0, 15]`.

 ## Parámetros
 - `v`: the nibble.

 ## Retorno
 A one-character `string`.

### `_hex2`

> **_hex2**(code: int) -> string

 Formats a byte as two lowercase hex digits.

 ## Parámetros
 - `code`: a value in `[0, 255]`.

 ## Retorno
 A two-character `string`.

### `_json_escape`

> **_json_escape**(s: string) -> string

 Escapes `s` so it can be embedded between JSON double quotes.

 ## Parámetros
 - `s`: the raw text. Read only.

 ## Retorno
 A new owned `string` in which `"`, `\`, `\b`, `\f`, `\n`, `\r`, `\t` and
 every other byte below `0x20` (as `\u00XX`) are escaped. Bytes `>= 0x20`,
 including UTF-8 continuation bytes, pass through unchanged.

 ## Nota
 2.1.0 added `\b`, `\f` and the general `\u00XX` control escape (fix for
 B14); 2.0.0 only handled `"`, `\`, `\n`, `\r` and `\t`.

 ## Ejemplo
 ```pengu
 var safe as string is calling whisper._json_escape with "a\"b"
 ```

### `json_escape_public`

> **json_escape_public**(s: string) -> string

 Public wrapper around `_json_escape`.

 ## Parámetros
 - `s`: the raw text. Read only.

 ## Retorno
 A new owned JSON-safe `string`.

 ## Ejemplo
 ```pengu
 var safe as string is calling whisper.json_escape_public with "a\nb"
 ```

### `_sorted_keys`

> **_sorted_keys**(m: map of string to string) -> list of string

 Returns the keys of `m` sorted bytewise.

 ## Parámetros
 - `m`: the map to read. Read only.

 ## Retorno
 A new owned `list of string` in ascending byte order, which is what makes
 the JSON output deterministic (2.1.0 fix for B16).

### `_render_json`

> **_render_json**(level: int, logger_name: string, msg: string, fields: map of string to string, include_time: bool) -> string

 Renders one JSON log document.

 ## Parámetros
 - `level`: the severity id.
 - `logger_name`: the logger name, or `""` to omit the member.
 - `msg`: the message text. Read only.
 - `fields`: extra members. Read only.
 - `include_time`: whether to add an ISO-8601 `"time"` member.

 ## Retorno
 A new owned `string` shaped
 `{"level":...,"time":...,"logger":...,"msg":...,<sorted fields>}` with the
 members in that fixed order. Release it with `banish`.

 ## Nota
 Rendering is pure: it never touches the environment and never writes, which
 is what lets the internal tests assert on the exact bytes.

### `_apply_format`

> **_apply_format**(fmt: string, lvl: string, lname: string, msg: string, stamp: string) -> string

 Applies a `{level}` `{name}` `{msg}` `{time}` template.

 ## Parámetros
 - `fmt`: the template. Read only.
 - `lvl`: the rendered level name. Read only.
 - `lname`: the logger name. Read only.
 - `msg`: the message text. Read only.
 - `stamp`: the timestamp text. Read only.

 ## Retorno
 A new owned `string`. Unknown `{placeholders}` are kept verbatim and a lone
 `{` or `}` is copied through.

 ## Nota
 2.1.0 added templates (fix for B24: 2.0.0 hard-coded `[LEVEL] [name] msg`).

### `log`

> **log**(level: int, msg: string) -> void

 Emits `msg` at severity `level` when `level` meets the global minimum.

 ## Parámetros
 - `level`: the severity id.
 - `msg`: the message text. Borrowed.

 ## Retorno
 Nothing. The line is written to stdout, colourised by level.

 ## Ejemplo
 ```pengu
 calling whisper.log with whisper.LOG_INFO, "hello"
 ```

### `trace`

> **trace**(msg: string) -> void

 Logs `msg` at TRACE level.

 ## Parámetros
 - `msg`: the message text. Borrowed.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling whisper.trace with "enter"
 ```

### `debug`

> **debug**(msg: string) -> void

 Logs `msg` at DEBUG level.

 ## Parámetros
 - `msg`: the message text. Borrowed.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling whisper.debug with "value"
 ```

### `info`

> **info**(msg: string) -> void

 Logs `msg` at INFO level.

 ## Parámetros
 - `msg`: the message text. Borrowed.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling whisper.info with "hello"
 ```

### `warn`

> **warn**(msg: string) -> void

 Logs `msg` at WARN level.

 ## Parámetros
 - `msg`: the message text. Borrowed.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling whisper.warn with "careful"
 ```

### `error`

> **error**(msg: string) -> void

 Logs `msg` at ERROR level.

 ## Parámetros
 - `msg`: the message text. Borrowed.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling whisper.error with "failed"
 ```

### `fatal`

> **fatal**(msg: string) -> void

 Logs `msg` at FATAL level.

 ## Parámetros
 - `msg`: the message text. Borrowed.

 ## Retorno
 Nothing. It does **not** terminate the process; use `fatal_and_exit` for that.

 ## Ejemplo
 ```pengu
 calling whisper.fatal with "unrecoverable"
 ```

### `fatal_and_exit`

> **fatal_and_exit**(msg: string, code: int) -> void

 Logs `msg` at FATAL level and immediately terminates the process.

 ## Parámetros
 - `msg`: the message text. Borrowed.
 - `code`: the exit status, default `1`.

 ## Retorno
 Never returns.

 ## Ejemplo
 ```pengu
 calling whisper.fatal_and_exit with "cannot continue", 2
 ```

### `log_json`

> **log_json**(level: int, msg: string, fields: map of string to string) -> void

 Emits a JSON log line to stdout when `level` meets the global minimum.

 ## Parámetros
 - `level`: the severity id.
 - `msg`: the message text. Borrowed.
 - `fields`: extra JSON members. Read only.

 ## Retorno
 Nothing. The document always carries a `"time"` member (2.1.0 fix for B15)
 and its field keys are sorted (2.1.0 fix for B16).

 ## Ejemplo
 ```pengu
 var f as map of string to string is map of string to string
 with f:
     calling .put with "pid", "42"
 calling whisper.log_json with whisper.LOG_INFO, "started", f
 ```

### `Logger`

> rune Logger

```pengu
    name as string
    min_level as int
    show_timestamp as bool
    use_color as bool
    file_path as string
    stream as int
    fmt as string
    context as map of string to string
```

 Instance-based logger with an independent level, destination, timestamp,
 colour, format template and structured JSON context.

 | Field | Meaning |
 |---|---|
 | `name` | hierarchical name, `""` to omit it |
 | `min_level` | this logger's own minimum level |
 | `show_timestamp` | add an ISO timestamp to text lines |
 | `use_color` | colour stdout/stderr lines (files stay plain) |
 | `file_path` | append to this file when non-empty |
 | `stream` | `0` = stdout, `1` = stderr |
 | `fmt` | template for `_apply_format`, `""` for the default layout |
 | `context` | structured members merged into `log_json` |

### `_registry`

> **_registry**() -> ref to map of string to Logger

 Returns the module-level singleton registry of named loggers.

 ## Retorno
 A reference to the registry map. The `static var` lives here and only here,
 which is what makes every caller see the same map.

### `_copy_of`

> **_copy_of**(new_name: string, new_level: int, new_ts: bool, new_color: bool, new_file: string, new_stream: int, new_fmt: string, new_ctx: map of string to string) -> Logger

 Builds a `Logger` from already-prepared field values.

 ## Parámetros
 - `new_name`, `new_level`, `new_ts`, `new_color`, `new_file`, `new_stream`,
   `new_fmt`, `new_ctx`: the fields of the result.

 ## Retorno
 A new `Logger` value.

### `_no_fields`

> **_no_fields**() -> map of string to string

 Returns an empty structured-field map.

 ## Retorno
 A new empty `map of string to string`.

### `_registry_store_level`

> **_registry_store_level**(name: string, level: int) -> void

 Publishes a new level for `name` into the singleton registry.

 ## Parámetros
 - `name`: the registered logger name; an empty name is ignored.
 - `level`: the new minimum level.

 ## Retorno
 Nothing. Does nothing when the name is not registered.

### `default_logger`

> **default_logger**() -> Logger

 Returns a default logger named `"default"`.

 ## Retorno
 The singleton `Logger` called `"default"`.

 ## Ejemplo
 ```pengu
 var log as whisper.Logger is calling whisper.default_logger
 ```

### `named_logger`

> **named_logger**(name: string) -> Logger

 Returns the singleton logger called `name`.

 ## Parámetros
 - `name`: the logger name.

 ## Retorno
 The value registered under `name`, creating and registering it on first use
 (2.1.0 fix for B20: `Logger.new("app")` twice used to build two independent
 loggers).

 ## Ejemplo
 ```pengu
 var log as whisper.Logger is calling whisper.named_logger with "app"
 ```

### `new`

> **new**(name: string) -> Logger

 Creates a logger named `name` with `LOG_TRACE` as its minimum level.

 ## Parámetros
 - `name`: the logger name. Borrowed.

 ## Retorno
 A new `Logger` writing to stdout with colour and without timestamps.

 ## Ejemplo
 ```pengu
 var log as whisper.Logger is calling whisper.Logger.new with "app"
 ```

### `named`

> **named**(name: string, min_level: int) -> Logger

 Creates a logger with `name` and an explicit `min_level`.

 ## Parámetros
 - `name`: the logger name. Borrowed.
 - `min_level`: this logger's minimum level.

 ## Retorno
 A new `Logger` writing to stdout with colour and without timestamps.

 ## Ejemplo
 ```pengu
 var log as whisper.Logger is calling whisper.Logger.named with "app", whisper.LOG_WARN
 ```

### `from_env`

> **from_env**() -> Logger

 Creates a logger configured from the environment.

 ## Retorno
 A logger named `"default"` whose level is the first valid environment
 level, or `get_default_level` when none is set. An environment variable
 that is set but invalid is reported on stderr (2.1.0 fix for B17).

 ## Ejemplo
 ```pengu
 var log as whisper.Logger is calling whisper.Logger.from_env
 ```

### `get_or_create`

> **get_or_create**(name: string) -> Logger

 Returns the singleton logger called `name`.

 ## Parámetros
 - `name`: the logger name. Borrowed.

 ## Retorno
 The registered value, creating it on first use. Repeated calls with the
 same name observe the level published by `set_level` (2.1.0 fix for B20).

 ## Ejemplo
 ```pengu
 var log as whisper.Logger is calling whisper.Logger.get_or_create with "app"
 ```

### `get_name`

> **get_name**() -> string

 Returns this logger's name.

 ## Retorno
 A new owned copy of the name. Release it with `banish`.

 ## Ejemplo
 ```pengu
 var who as string is calling log.get_name
 ```

### `enable_timestamp`

> **enable_timestamp**() -> void

 Turns ISO timestamps on for text lines.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling log.enable_timestamp
 ```

### `disable_timestamp`

> **disable_timestamp**() -> void

 Turns ISO timestamps off for text lines.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling log.disable_timestamp
 ```

### `enable_color`

> **enable_color**() -> void

 Enables ANSI colour on stdout/stderr lines (files stay plain).

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling log.enable_color
 ```

### `disable_color`

> **disable_color**() -> void

 Disables ANSI colour.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling log.disable_color
 ```

### `to_file`

> **to_file**(path: string) -> void

 Redirects output to a file (empty string restores the current stream).

 ## Parámetros
 - `path`: the destination file. Borrowed.

 ## Retorno
 Nothing. The file is opened lazily on each emission. File lines are
 always plain: colours are never written to a file. A write failure is
 reported on stderr and does not interrupt the program (2.1.0 fix for
 B21: 2.0.0 discarded the failure silently).

 ## Ejemplo
 ```pengu
 calling log.to_file with "app.log"
 ```

### `to_stderr`

> **to_stderr**() -> void

 Redirects output to stderr.

 ## Retorno
 Nothing. A later `to_file` still wins, because file mode is checked
 first (2.1.0 fix for B19).

 ## Ejemplo
 ```pengu
 calling log.to_stderr
 ```

### `to_stdout`

> **to_stdout**() -> void

 Redirects output back to stdout.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling log.to_stdout
 ```

### `set_format`

> **set_format**(fmt: string) -> void

 Sets a custom text template.

 ## Parámetros
 - `fmt`: the template. `{level}`, `{name}`, `{msg}` and `{time}` are
   substituted; an empty string restores the default layout. Borrowed.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling log.set_format with r"{time} {level} {name}: {msg}"
 ```

### `with_context`

> **with_context**(fields: map of string to string) -> Logger

 Returns a copy with `fields` merged into the structured context.

 ## Parámetros
 - `fields`: members to add or overwrite. Read only.

 ## Retorno
 A new `Logger`; the receiver is unchanged.

 ## Ejemplo
 ```pengu
 var child as whisper.Logger is calling log.with_context with fields
 ```

### `with_field`

> **with_field**(key: string, value: string) -> Logger

 Returns a copy with one structured member added or overwritten.

 ## Parámetros
 - `key`: the member name. Borrowed.
 - `value`: the member value. Borrowed.

 ## Retorno
 A new `Logger`; the receiver is unchanged.

 ## Ejemplo
 ```pengu
 var child as whisper.Logger is calling log.with_field with "pid", "42"
 ```

### `_one_field`

> **_one_field**(key: string, value: string) -> map of string to string

 Builds a one-entry field map (helper for `with_field`).

 ## Parámetros
 - `key`: the member name. Borrowed.
 - `value`: the member value. Borrowed.

 ## Retorno
 A new `map of string to string` with a single entry.

### `is_file_mode`

> **is_file_mode**() -> bool

 Returns true when this logger appends to a file.

 ## Retorno
 `true` when `file_path` is non-empty.

 ## Ejemplo
 ```pengu
 if calling log.is_file_mode:
 ```

### `is_stderr_mode`

> **is_stderr_mode**() -> bool

 Returns true when this logger writes to stderr and not to a file.

 ## Retorno
 `true` when `stream == 1` and `file_path` is empty.

 ## Ejemplo
 ```pengu
 if calling log.is_stderr_mode:
 ```

### `flush`

> **flush**() -> void

 Flushes stdout and stderr.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling log.flush
 ```

### `get_timestamp`

> **get_timestamp**() -> string

 Returns the current time as an ISO-8601 UTC string.

 ## Retorno
 A new owned `string` such as `2026-09-25T14:30:00Z`. Release it with
 `banish`.

 ## Ejemplo
 ```pengu
 var now as string is calling log.get_timestamp
 ```

### `_child_name`

> **_child_name**(sub: string) -> string

 Joins a hierarchical child name onto this logger's name.

 ## Parámetros
 - `sub`: the child segment. Empty returns the parent unchanged; bytes
   outside `[A-Za-z0-9_.-]` become `_` (2.1.0 fix for B23).

 ## Retorno
 A new owned, sanitised name. Release it with `banish`.

### `child`

> **child**(sub: string) -> Logger

 Creates a child logger with hierarchical name `"parent.sub"`.

 ## Parámetros
 - `sub`: the child segment. Borrowed; sanitised as `_child_name` documents.

 ## Retorno
 A new `Logger` that inherits the parent's level, timestamp, colour,
 file path, stream, format and context (2.1.0 fix for B12: 2.0.0 dropped
 the parent's `file_path`, so a child silently stopped writing to the
 parent's file).

 ## Ejemplo
 ```pengu
 var child as whisper.Logger is calling log.child with "db"
 ```

### `_format_line`

> **_format_line**(level: int, msg: string) -> string

 Renders this logger's text layout for `msg` (without colour).

 ## Parámetros
 - `level`: the severity id.
 - `msg`: the message text. Borrowed.

 ## Retorno
 A new owned `string`.

### `_emit`

> **_emit**(line: string) -> void

 Writes one already-rendered line to the configured destination.

 ## Parámetros
 - `line`: the exact text, without a trailing newline. Borrowed.

 ## Retorno
 Nothing. File failures are reported on stderr.

### `log_json_ex`

> **log_json_ex**(level: int, msg: string, fields: map of string to string, include_time: bool) -> void

 Emits a JSON line with explicit control over the timestamp member.

 ## Parámetros
 - `level`: the severity id.
 - `msg`: the message text. Borrowed.
 - `fields`: extra JSON members, merged after the context. Read only.
 - `include_time`: whether to add `"time"`.

 ## Retorno
 Nothing.

 ## Ejemplo
 ```pengu
 calling log.log_json_ex with whisper.LOG_INFO, "ready", f, true
 ```

### `_wsp_expect`

> **_wsp_expect**(cond: bool, label: string) -> void

 Aborts unless `cond` holds.

### `_wsp_expect_eq_int`

> **_wsp_expect_eq_int**(got: int, want: int, label: string) -> void

 Aborts unless the two ints are equal.

### `_wsp_expect_eq_string`

> **_wsp_expect_eq_string**(got: string, want: string, label: string) -> void

 Aborts unless the two strings are byte-equal.

### `_wsp_contains`

> **_wsp_contains**(s: string, sub: string) -> bool

 Returns true when `s` contains `sub` as a substring.

### `"WHISPER_VERSION is the frozen 2.1.0 contract"`

> test "WHISPER_VERSION is the frozen 2.1.0 contract"

_Undocumented._

### `"level ids are ordered from trace to fatal"`

> test "level ids are ordered from trace to fatal"

_Undocumented._

### `"get_level_name maps every level and defaults to FATAL"`

> test "get_level_name maps every level and defaults to FATAL"

_Undocumented._

### `"get_level_color maps every level and defaults to bright red"`

> test "get_level_color maps every level and defaults to bright red"

_Undocumented._

### `"parse_level_string accepts names and rejects junk"`

> test "parse_level_string accepts names and rejects junk"

_Undocumented._

### `"set_level, get_level and is_enabled agree on the global level"`

> test "set_level, get_level and is_enabled agree on the global level"

_Undocumented._

### `"log_levels publishes the six names in severity order"`

> test "log_levels publishes the six names in severity order"

_Undocumented._

### `"colorize wraps a message and terminates with the reset escape"`

> test "colorize wraps a message and terminates with the reset escape"

_Undocumented._

### `"BUG-14: _json_escape handles quotes and backslashes"`

> test "BUG-14: _json_escape handles quotes and backslashes"

_Undocumented._

### `"BUG-14: _json_escape handles backspace, form feed and control bytes"`

> test "BUG-14: _json_escape handles backspace, form feed and control bytes"

_Undocumented._

### `"json_escape_public is the public spelling of _json_escape"`

> test "json_escape_public is the public spelling of _json_escape"

_Undocumented._

### `"BUG-16: _sorted_keys returns byte-sorted keys"`

> test "BUG-16: _sorted_keys returns byte-sorted keys"

_Undocumented._

### `"BUG-16: _render_json emits fields in a deterministic order"`

> test "BUG-16: _render_json emits fields in a deterministic order"

_Undocumented._

### `"BUG-15: _render_json includes a timestamp only when asked"`

> test "BUG-15: _render_json includes a timestamp only when asked"

_Undocumented._

### `"_apply_format substitutes the four placeholders"`

> test "_apply_format substitutes the four placeholders"

_Undocumented._

### `"Logger.new and Logger.named set their documented defaults"`

> test "Logger.new and Logger.named set their documented defaults"

_Undocumented._

### `"BUG-12: Logger.child preserves the parent file path and settings"`

> test "BUG-12: Logger.child preserves the parent file path and settings"

_Undocumented._

### `"BUG-23: Logger.child sanitises empty and whitespace segments"`

> test "BUG-23: Logger.child sanitises empty and whitespace segments"

_Undocumented._

### `"Logger stream helpers report their destination"`

> test "Logger stream helpers report their destination"

_Undocumented._

### `"Logger.set_format changes the rendered text layout"`

> test "Logger.set_format changes the rendered text layout"

_Undocumented._

### `"Logger.with_field and with_context extend the structured context"`

> test "Logger.with_field and with_context extend the structured context"

_Undocumented._

### `"Logger.get_timestamp returns a non-empty ISO string"`

> test "Logger.get_timestamp returns a non-empty ISO string"

_Undocumented._

### `"BUG-20: Logger.get_or_create returns one registered logger per name"`

> test "BUG-20: Logger.get_or_create returns one registered logger per name"

_Undocumented._

### `"BUG-20: a level set on a named logger is visible to a later get_or_create"`

> test "BUG-20: a level set on a named logger is visible to a later get_or_create"

_Undocumented._

### `"BUG-18: set_level_from_env falls back to the configured default"`

> test "BUG-18: set_level_from_env falls back to the configured default"

_Undocumented._

### `"BUG-17: a set-but-invalid environment level is ignored, not silently equal to unset"`

> test "BUG-17: a set-but-invalid environment level is ignored, not silently equal to unset"

_Undocumented._

### `"BUG-21: a logger pointed at an unwritable file does not crash"`

> test "BUG-21: a logger pointed at an unwritable file does not crash"

_Undocumented._

### `"log_json_ex renders through the logger and respects the level"`

> test "log_json_ex renders through the logger and respects the level"

_Undocumented._

### `"the global helpers emit and suppress according to the global level"`

> test "the global helpers emit and suppress according to the global level"

_Undocumented._

### `log_json_global_helper`

> **log_json_global_helper**() -> void

 Emits one global JSON line (helper kept out of the test body for readability).

### `_wsp_fields`

> **_wsp_fields**() -> map of string to string

 Returns a one-entry context map for the `with_context` test.

