# std.rites

> Source: `std/rites.pengu`

std/rites.pengu — operating-system rites: environment variables, program
arguments, process identity, standard directories, platform detection,
executable search, and shell execution with output capture.

The module is the thin, portable PenguScript face of the C runtime's "Rites"
section (`pengu_runtime.h`, section 14) plus a few `antiquus` bridges for the
capabilities the runtime does not expose (stdout/stderr capture and the POSIX
user/group identifiers).

## Example
```pengu
import std.spark
import std.rites

weave main into int:
    let home as maybe string is calling rites.home_dir
    if home is present:
        calling spark.println with "home={home.value}"
    let out as maybe string is calling rites.run_capture with "sh", ["-c", "echo hi"]
    if out is present:
        calling spark.println with out.value
    return 0
```

## Memory
Every returned `string` (and every string inside a returned `list of string`)
is a fresh, owned allocation made by the C runtime or by the standard library,
so it follows normal PenguScript value lifetimes and never aliases an OS-owned
buffer (`getenv`, `getcwd`, `uname`, `hostname`, ...). Release those results
with `banish`; a `banish` on a string literal or an empty view is a no-op.
`get_args` owns both the element buffer and each element, so release the
elements (or use the list-wide release helper) before the list. A
`maybe string` owns its payload only when it is `present`. Arguments are
borrowed for the duration of the call and are never retained, and this module
never frees a caller-owned buffer.

## Design notes
- **C bridges keep their original names.** The `pengu_c_*` declarations name
  `static inline` helpers of `pengu_runtime.h`; they are declared, never
  redefined, so the runtime stays the single implementation. The `declare`
  block sits *before* the module's `insignia rites_` directive, so the
  `pengu_c_*` symbols keep their exact runtime names while the module's own
  weaves are C-prefixed.
- **New `antiquus` bridges are narrow.** `run_capture*` needs a pipe
  (`popen`/`pclose`) that the runtime does not wrap, and `get_uid`/`get_gid`
  need the POSIX credential calls. Both are embedded C bodies that call libc
  directly; each one justifies itself in `## ## Motivo`.
- **The command line is built in Pengu, not in C.** Every element of a
  `cmd`/`args` pair is quoted with `shell_escape` before it is handed to the
  C bridge, so the quoting policy lives in exactly one place and is covered by
  unit tests. On POSIX that is single-quote escaping; on Windows it is
  double-quote escaping.
- **`popen` runs the platform shell.** The module's query helpers treat the
  shell status like a process status: only `0` is success, and the extracted
  exit code is reported as `128 + signal` when the shell reports termination
  by signal.
- **Test-only names are `_rites_*`.** The internal tests never import
  `std.ward` (`ward` imports `std.rites`, so that would be a cycle); they use a
  private harness over `spark.panic` and call unambiguous `_rites_*` helpers so
  they stay safe in the shared namespace used when several bundled modules are
  type-checked together.

## Migration
2.1.0 is a documentation/style migration with new capability and no
removals:

- **Every 2.0.0 symbol is preserved** with its exact name, bounds and
  signature, including the `pengu_c_*` declarations, `clear_env`,
  `getenv_or`, `arg_at_or`, `parse_flags` and the aliases (`env_substitute`,
  `os_family`, `spawn`).
- **New capture API.** `run_capture`, `run_capture_result`,
  `run_capture_lines`, `run_capture_stderr` and `run_shell_capture` close the
  old `run_capture()` TODO; they are built on two private `antiquus` bridges
  (`_rites_capture`, `_rites_run_status`).
- **New POSIX credentials API.** `get_uid`, `get_gid`, `get_euid` and `get_egid`
  close the old `get_uid()`/`get_gid()` TODO through one private `antiquus`
  bridge (`_rites_id`); they return `maybe none` on Windows.
- **Still unsupported:** `set_uid`/`set_gid`, `fork`/`waitpid` and raw `pipe`
  objects remain out of scope; they need runtime-level work, not a doc pass.
- **Documentation.** All prose is English, every public weave carries the
  canonical `## ## Parámetros`/`## ## Retorno`/`## ## Ejemplo` sections and the
  internal `# --- Tests ---` suite was added (there were none in 2.0.0).

---

### `pengu_c_getenv`

> **pengu_c_getenv**(name: string) -> maybe string

 C bridge that looks up the value of environment variable `name`; returns a
 maybe string that is none when the variable is unset.

### `pengu_c_setenv`

> **pengu_c_setenv**(name: string, value: string, overwrite: bool) -> bool

 C bridge that sets environment variable `name` to `value`; `overwrite`
 controls whether an existing variable may be replaced. Returns true on
 success, false on failure (e.g. an empty `name`).

### `pengu_c_unsetenv`

> **pengu_c_unsetenv**(name: string) -> bool

 C bridge that removes environment variable `name`. Returns true on success,
 false on failure (e.g. an empty `name`).

### `pengu_c_get_argc`

> **pengu_c_get_argc**() -> int

 C bridge returning the program's argument count (argc, including the program
 name at index 0).

### `pengu_c_get_argv`

> **pengu_c_get_argv**(idx: int) -> string

 C bridge returning a copy of the program argument at index `idx` (0 = the
 program name); an out-of-range index yields an empty string.

### `pengu_c_get_args`

> **pengu_c_get_args**() -> list of string

 C bridge returning a new list of string with one copy per program argument,
 from index 0 (program name) upward.

### `pengu_c_getpid`

> **pengu_c_getpid**() -> int

 C bridge returning the current process id (int).

### `pengu_c_getppid`

> **pengu_c_getppid**() -> int

 C bridge returning the parent process id (int); always 0 on Windows.

### `pengu_c_getcwd`

> **pengu_c_getcwd**() -> maybe string

 C bridge returning the current working directory as a maybe string (none
 when it cannot be determined).

### `pengu_c_chdir`

> **pengu_c_chdir**(path: string) -> bool

 C bridge that changes the current working directory to `path`; returns true
 on success, false on failure.

### `pengu_c_exit`

> **pengu_c_exit**(code: int) -> void

 C bridge that terminates the process immediately with exit code `code`.

### `pengu_c_exec`

> **pengu_c_exec**(cmd: string, args: list of string) -> int

 C bridge that runs `cmd` plus each `args` entry (space-joined) through the
 platform shell (system()) and returns the raw status it reports.

### `pengu_c_spawn`

> **pengu_c_spawn**(cmd: string, args: list of string) -> int

 C bridge that launches `cmd` with `args`; currently shares the same
 implementation as exec (a blocking system() call).

### `pengu_c_uname`

> **pengu_c_uname**() -> string

 C bridge returning the OS family name ("Windows", "Darwin", "Linux" or
 "Unknown") as a string.

### `pengu_c_arch`

> **pengu_c_arch**() -> string

 C bridge returning the host architecture ("x64", "arm64", "x86" or "arm").

### `pengu_c_hostname`

> **pengu_c_hostname**() -> string

 C bridge returning the machine's host name as a string.

### `pengu_c_get_env_keys`

> **pengu_c_get_env_keys**() -> list of string

 C bridge returning a new list of string holding the names of all currently
 set environment variables.

### `pengu_c_archivum_is_file`

> **pengu_c_archivum_is_file**(path: string) -> bool

 External file check declaration to avoid circular import with std.archivum.

### `RITES_VERSION`

> **RITES_VERSION** : string

 Version constant for the std.rites module.

### `_rites_capture`

> **_rites_capture**(cmdline: string, stream: string, err: ref to string) -> string

 Runs `cmdline` through the shell and captures one of its output streams.

 ## Motivo
 `popen`/`pclose` are the portable pipe pair for "run and read", but they are
 not wrapped by `pengu_runtime.h`; expressing a pipe in PenguScript would need
 `fork`/`dup2`/`waitpid` bridges instead. The stream selector (`"r"` for
 stdout, `"e"` for stderr) and the error message are the two values the Pengu
 wrappers need, and one C call gives both so a command never runs twice.

 ## Memoria
 Returns a freshly allocated owned `PenguString`; the caller releases it with
 `banish`. On Windows or on a failure it returns an empty view. `cmdline` is
 borrowed and never freed, and `err` is a borrowed output slot that receives
 an empty view on success or a freshly allocated message on failure.

### `_rites_run_status`

> **_rites_run_status**(cmdline: string) -> int

 Returns the shell exit status of `cmdline` without capturing its output.

 ## Motivo
 `run_capture_result` needs the numeric exit code even when the capture call
 already reported the failure text; `pclose` is the only portable way to get
 it and the Pengu side cannot reach the wait macros. The command is therefore
 run a second time only on the error path, where its output is known to be
 empty.

 ## Memoria
 Allocates nothing. `cmdline` is borrowed and never freed.

### `ProcessResult`

> rune ProcessResult

```pengu
    out as string
    err as string
    code as int
    timed_out as bool
```

 A completed child process with both output streams and its exit code.

 ## Campos
 - `stdout`: everything the child wrote to standard output.
 - `stderr`: everything the child wrote to standard error.
 - `code`: exit status (128 + signal on POSIX when it was killed).
 - `timed_out`: reserved for callers that implement a timeout; the built-in
   bridge is blocking and always reports `false`.

 ## Memoria
 Both strings are owned by the rune; release each one with `banish` after the
 last use.  The rune itself is a plain value (no hidden allocation).

### `_rites_capture_all`

> **_rites_capture_all**(cmdline: string, out: ref to string, errtext: ref to string) -> int

 Runs `cmd` with `args` and captures stdout, stderr and the exit code.

 ## Motivo
 `popen` can only capture one stream, and both `run_capture` and
 `run_capture_stderr` discard the buffer when the child fails.  A compiler
 driver needs gcc's diagnostics *and* its exit status from the same run
 (B3), so this bridge connects two temporary files to stdout/stderr, waits
 for the child and reads both back.  It never loses output on a non-zero exit.

 ## Memoria
 Both out parameters receive freshly allocated owned strings; the caller
 releases them.  `cmdline` is borrowed.

 ## Efectos
 Blocks until the child exits.  POSIX uses `fork`/`execl("/bin/sh")`;
 Windows uses `system()` with temporary files.

### `run_capture_all`

> **run_capture_all**(cmd: string, args: list of string) -> ProcessResult

 Runs `cmd` with `args`, returning both streams and the exit code.

 ## Parámetros
 - `cmd`: executable or shell command line. Borrowed.
 - `args`: arguments, each escaped with `shell_escape`. Borrowed.

 ## Retorno
 A `ProcessResult` whose `out`/`err` are owned strings and whose `code`
 is the child's exit status.  Unlike `run_capture`, a non-zero exit does not
 hide the output; this is the API a compiler driver uses for `gcc`.

 ## Memoria
 The caller owns both strings inside the result and must `banish` each one.

 ## Ejemplo
 ```pengu
 let r as rites.ProcessResult is calling rites.run_capture_all with "gcc", ["-v"]
 calling spark.println_int with r.code
 banish r.out
 banish r.err
 ```

### `_rites_id`

> **_rites_id**(which: int) -> int

 Returns POSIX credential `which` for the current process.

 ## Motivo
 The four credential calls (`getuid`, `getgid`, `geteuid`, `getegid`) are one
 line of C each; a Pengu body cannot reach them at all. `which` selects the
 call, and `-1f` means "not available on this target", which the Pengu wrapper
 turns into `maybe none`.

 ## Memoria
 Allocates nothing. The parameter is a borrowed `int`.

### `getenv`

> **getenv**(name: string) -> maybe string

 Looks up environment variable `name`.

 ## Parámetros
 - `name`: the variable name to look up. Borrowed.

 ## Retorno
 A fresh owned `maybe string`: `some value` when the variable is set (an empty
 string is still `present`) and `maybe none` when it is unset or `name` is
 empty.

 ## Memoria
 The payload is a fresh copy of the environment value, released with `banish`.

 ## Ejemplo
 ```pengu
 let home as maybe string is calling rites.getenv with "HOME"
 ```

### `setenv`

> **setenv**(name: string, value: string, overwrite: bool) -> bool

 Sets environment variable `name` to `value`.

 ## Parámetros
 - `name`: the variable name. Borrowed; an empty name fails.
 - `value`: the value to store, possibly empty. Borrowed.
 - `overwrite`: when false and `name` already exists, leave it untouched.

 ## Retorno
 `true` on success, `false` when `name` is empty or the runtime cannot store
 the pair.

 ## Memoria
 The runtime copies both strings; the caller keeps whatever it owned. Nothing
 is retained after the call.

 ## Ejemplo
 ```pengu
 calling rites.setenv with "APP_MODE", "debug", true
 ```

### `unsetenv`

> **unsetenv**(name: string) -> bool

 Removes environment variable `name` from the process environment.

 ## Parámetros
 - `name`: the variable name to remove. Borrowed.

 ## Retorno
 `true` on success or when the variable was already unset; `false` for an
 empty name.

 ## Memoria
 Arguments are not retained.

 ## Ejemplo
 ```pengu
 calling rites.unsetenv with "APP_MODE"
 ```

### `get_env_keys`

> **get_env_keys**() -> list of string

 Returns the names of all currently set environment variables.

 ## Parámetros
 - None.

 ## Retorno
 A new owned `list of string`; empty when no variables are defined.

 ## Memoria
 The list owns its element buffer and every element is an owned string, so
 release the elements before the list.

 ## Ejemplo
 ```pengu
 let keys as list of string is calling rites.get_env_keys
 ```

### `getenv_or`

> **getenv_or**(name: string, default: string) -> string

 Looks up environment variable `name`, returning `default` if unset.

 ## Parámetros
 - `name`: the variable name. Borrowed.
 - `default`: the value returned when `name` is unset. Borrowed.

 ## Retorno
 The variable value, or `default` when the variable is unset or `name` is
 empty.

 ## Memoria
 A fresh owned string when the variable is set; otherwise `default` itself.

 ## Ejemplo
 ```pengu
 calling rites.getenv_or with "NO_SUCH_VAR", "fallback"    # "fallback"
 ```

### `has_env`

> **has_env**(name: string) -> bool

 Checks whether environment variable `name` is currently set.

 ## Parámetros
 - `name`: the variable name. Borrowed.

 ## Retorno
 `true` when the variable exists, even if its value is the empty string.

 ## Memoria
 No persistent allocations; the temporary lookup result is not returned.

 ## Ejemplo
 ```pengu
 calling rites.has_env with "PATH"    # true
 ```

### `getenv_int`

> **getenv_int**(name: string) -> maybe int

 Looks up environment variable `name` and parses it as an integer.

 ## Parámetros
 - `name`: the variable name. Borrowed.

 ## Retorno
 `some value` when the variable is set and `spark.parse_int` accepts it;
 `maybe none` otherwise. Never panics.

 ## Memoria
 No persistent allocations beyond the discarded lookup copy.

 ## Ejemplo
 ```pengu
 let port as maybe int is calling rites.getenv_int with "PORT"
 ```

### `getenv_float`

> **getenv_float**(name: string) -> maybe float

 Looks up environment variable `name` and parses it as a float.

 ## Parámetros
 - `name`: the variable name. Borrowed.

 ## Retorno
 `some value` when the variable is set and `spark.parse_float` accepts it;
 `maybe none` otherwise. Never panics.

 ## Memoria
 No persistent allocations beyond the discarded lookup copy.

 ## Ejemplo
 ```pengu
 let ratio as maybe float is calling rites.getenv_float with "RATIO"
 ```

### `getenv_bool`

> **getenv_bool**(name: string) -> maybe bool

 Looks up environment variable `name` and parses it as a boolean.

 ## Parámetros
 - `name`: the variable name. Borrowed.

 ## Retorno
 `some true` for `"1"`, `"true"`, `"TRUE"`, `"True"`, `"yes"`, `"YES"` or
 `"Yes"`; `some false` for the `0`/`false`/`no` spellings; `maybe none` when
 the variable is unset or the value is not recognized.

 ## Memoria
 No persistent allocations beyond the discarded lookup copy.

 ## Ejemplo
 ```pengu
 let debug as maybe bool is calling rites.getenv_bool with "DEBUG"
 ```

### `get_env_map`

> **get_env_map**() -> map of string to string

 Returns a snapshot map of all environment variables and their values.

 ## Parámetros
 - None.

 ## Retorno
 A new owned `map of string to string`; empty when no variables are defined.

 ## Memoria
 Keys and values are copied with `memcpy`, so release any heap buffers they
 reference yourself once the map is no longer needed.

 ## Ejemplo
 ```pengu
 let env as map of string to string is calling rites.get_env_map
 ```

### `set_env_map`

> **set_env_map**(m: map of string to string) -> int

 Sets multiple environment variables from a key-value map.

 ## Parámetros
 - `m`: the entries to apply. Borrowed; the map is not consumed.

 ## Retorno
 The number of variables successfully set.

 ## Memoria
 No allocations; each value is copied by the runtime.

 ## Ejemplo
 ```pengu
 var m as map of string to string is map of string to string
 calling m.put with "APP_MODE", "debug"
 calling rites.set_env_map with m
 ```

### `clear_env`

> **clear_env**() -> int

 Clears all environment variables in the current process.

 ## Parámetros
 - None.

 ## Retorno
 The count of variables successfully removed.

 ## Memoria
 Mutates the process environment; no allocation is returned.

 ## Efectos
 Only the current process environment is affected: the OS, the parent process
 and the initial environment of future children are untouched.

 ## Ejemplo
 ```pengu
 let removed as int is calling rites.clear_env
 ```

### `expand_env`

> **expand_env**(s: string) -> string

 Expands environment variable placeholders in string `s`.

 ## Parámetros
 - `s`: the template to expand. Borrowed.

 ## Retorno
 A new owned string with `$VAR`, `${VAR}` and `%VAR%` replaced.

 ## Memoria
 The result is freshly allocated; release it with `banish`.

 ## Efectos
 Single-pass and non-recursive: a variable whose value contains `$` is not
 expanded again. Unset variables expand to the empty string, `$$`/`%%` become
 a literal `$`/`%`, and an unterminated `${...}`/`%...%` is preserved verbatim.

 ## Ejemplo
 ```pengu
 calling rites.expand_env with "home is $HOME"    # "home is /home/<user>"
 ```

### `env_substitute`

> **env_substitute**(s: string) -> string

 Alias of `expand_env`.

 ## Parámetros
 - `s`: the template to expand. Borrowed.

 ## Retorno
 A new owned string with the environment variables substituted.

 ## Memoria
 The result is freshly allocated; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling rites.env_substitute with "%HOME%"    # the home directory
 ```

### `get_argc`

> **get_argc**() -> int

 Returns the program's argument count, including the program name at index 0.

 ## Parámetros
 - None.

 ## Retorno
 The `argc` value as an `int`; at least 1 for a normal program.

 ## Memoria
 No allocations.

 ## Ejemplo
 ```pengu
 calling rites.get_argc    # e.g. 1
 ```

### `get_argv`

> **get_argv**(idx: int) -> string

 Returns a copy of the program argument at index `idx` (0 = program name).

 ## Parámetros
 - `idx`: the argument position. Borrowed.

 ## Retorno
 A fresh owned string; an out-of-range `idx` yields the empty string.

 ## Memoria
 The result is freshly allocated; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling rites.get_argv with 0    # the program path
 ```

### `get_args`

> **get_args**() -> list of string

 Returns a new list of string holding one copy per program argument.

 ## Parámetros
 - None.

 ## Retorno
 A new owned `list of string` with `argc` entries, index 0 being the program
 name.

 ## Memoria
 The returned list owns its element buffer and each string element owns its
 own bytes: free them with `pengu_banish_string_list` (or banish each element)
 before the list.

 ## Ejemplo
 ```pengu
 let argv as list of string is calling rites.get_args
 ```

### `arg_at_or`

> **arg_at_or**(idx: int, default: string) -> string

 Returns the argument at index `idx`, or `default` if `idx` is out of range.

 ## Parámetros
 - `idx`: the argument position. Borrowed.
 - `default`: the value returned when `idx` is out of range. Borrowed.

 ## Retorno
 A fresh owned string when `0 <= idx < get_argc()`; otherwise `default`.

 ## Memoria
 A fresh owned string when the argument exists; `default` itself otherwise.

 ## Ejemplo
 ```pengu
 calling rites.arg_at_or with 99, "none"    # "none"
 ```

### `parse_flags`

> **parse_flags**() -> map of string to string

 Parses command-line flags from `get_args()` (skipping argv[0]).

 ## Parámetros
 - None.

 ## Retorno
 A new owned `map of string to string`: `--key=value` becomes
 `["key"] = "value"` and a bare `--flag` becomes `["flag"] = "true"`.

 ## Memoria
 The map is freshly allocated; keys and values are owned strings.

 ## Efectos
 Positional arguments (anything not starting with `--`) are ignored.

 ## Ejemplo
 ```pengu
 let flags as map of string to string is calling rites.parse_flags
 ```

### `has_flag`

> **has_flag**(name: string) -> bool

 Checks if flag `--name` was passed on the command line.

 ## Parámetros
 - `name`: the flag name without the leading `--`. Borrowed.

 ## Retorno
 `true` when the parsed flag map contains `name`.

 ## Memoria
 No persistent allocations; the parsed map is discarded.

 ## Ejemplo
 ```pengu
 if calling rites.has_flag with "verbose":
     calling spark.println with "verbose mode"
 ```

### `get_flag_value`

> **get_flag_value**(name: string) -> maybe string

 Returns the value of flag `--name` if passed, or maybe none.

 ## Parámetros
 - `name`: the flag name without the leading `--`. Borrowed.

 ## Retorno
 `some value` when the flag was passed (`"true"` for a bare flag), otherwise
 `maybe none`.

 ## Memoria
 The payload is owned by the returned `maybe`; release it with `banish`.

 ## Ejemplo
 ```pengu
 let out as maybe string is calling rites.get_flag_value with "output"
 ```

### `getpid`

> **getpid**() -> int

 Returns the current process id (int).

 ## Parámetros
 - None.

 ## Retorno
 The process id as an `int`.

 ## Memoria
 No allocations.

 ## Ejemplo
 ```pengu
 calling spark.println with "{calling rites.getpid}"
 ```

### `getppid`

> **getppid**() -> int

 Returns the parent process id (int). Always 0 on Windows.

 ## Parámetros
 - None.

 ## Retorno
 The parent process id as an `int`; `0` on Windows.

 ## Memoria
 No allocations.

 ## Ejemplo
 ```pengu
 let ppid as int is calling rites.getppid
 ```

### `get_uid`

> **get_uid**() -> maybe int

 Returns the real user id of the current process.

 ## Parámetros
 - None.

 ## Retorno
 `some uid` on POSIX; `maybe none` on Windows or when the value is not
 available.

 ## Memoria
 No allocations; the `int` payload is a value.

 ## Ejemplo
 ```pengu
 let uid as maybe int is calling rites.get_uid
 ```

### `get_gid`

> **get_gid**() -> maybe int

 Returns the real group id of the current process.

 ## Parámetros
 - None.

 ## Retorno
 `some gid` on POSIX; `maybe none` on Windows or when the value is not
 available.

 ## Memoria
 No allocations; the `int` payload is a value.

 ## Ejemplo
 ```pengu
 let gid as maybe int is calling rites.get_gid
 ```

### `get_euid`

> **get_euid**() -> maybe int

 Returns the effective user id of the current process.

 ## Parámetros
 - None.

 ## Retorno
 `some euid` on POSIX; `maybe none` on Windows or when the value is not
 available.

 ## Memoria
 No allocations; the `int` payload is a value.

 ## Ejemplo
 ```pengu
 let euid as maybe int is calling rites.get_euid
 ```

### `get_egid`

> **get_egid**() -> maybe int

 Returns the effective group id of the current process.

 ## Parámetros
 - None.

 ## Retorno
 `some egid` on POSIX; `maybe none` on Windows or when the value is not
 available.

 ## Memoria
 No allocations; the `int` payload is a value.

 ## Ejemplo
 ```pengu
 let egid as maybe int is calling rites.get_egid
 ```

### `getcwd`

> **getcwd**() -> maybe string

 Returns the current working directory as a maybe string.

 ## Parámetros
 - None.

 ## Retorno
 `some path` or `maybe none` when the current directory cannot be determined.

 ## Memoria
 The payload is a fresh owned string; release it with `banish`.

 ## Ejemplo
 ```pengu
 let cwd as maybe string is calling rites.getcwd
 ```

### `chdir`

> **chdir**(path: string) -> bool

 Changes the current working directory to `path`.

 ## Parámetros
 - `path`: the target directory. Borrowed.

 ## Retorno
 `true` on success; `false` when the path does not exist or access is denied.

 ## Memoria
 Arguments are not retained.

 ## Ejemplo
 ```pengu
 calling rites.chdir with "/tmp"
 ```

### `home_dir`

> **home_dir**() -> maybe string

 Returns the current user's home directory.

 ## Parámetros
 - None.

 ## Retorno
 `some path`, or `maybe none` when no source variable is set.

 ## Memoria
 The payload is a fresh owned string; release it with `banish`.

 ## Efectos
 On Windows it inspects `USERPROFILE` and then `HOMEDRIVE` + `HOMEPATH`; on
 POSIX it inspects `HOME`.

 ## Ejemplo
 ```pengu
 let home as maybe string is calling rites.home_dir
 ```

### `temp_dir`

> **temp_dir**() -> maybe string

 Returns the system temporary directory path.

 ## Parámetros
 - None.

 ## Retorno
 `some path`; never `none` because each platform has a fallback.

 ## Memoria
 The payload is a fresh owned string; release it with `banish`.

 ## Efectos
 On Windows it inspects `TEMP`/`TMP` with fallback `C:\Temp`; on POSIX it
 inspects `TMPDIR`/`TEMP`/`TMP` with fallback `/tmp`.

 ## Ejemplo
 ```pengu
 let tmp as maybe string is calling rites.temp_dir
 ```

### `config_dir`

> **config_dir**() -> maybe string

 Returns the user configuration directory path.

 ## Parámetros
 - None.

 ## Retorno
 `some path`, or `maybe none` when neither the XDG variable nor the home
 directory is available.

 ## Memoria
 The payload is a fresh owned string; release it with `banish`.

 ## Efectos
 On Windows it returns `%APPDATA%`; on POSIX `$XDG_CONFIG_HOME` or
 `~/.config`.

 ## Ejemplo
 ```pengu
 let cfg as maybe string is calling rites.config_dir
 ```

### `cache_dir`

> **cache_dir**() -> maybe string

 Returns the user cache directory path.

 ## Parámetros
 - None.

 ## Retorno
 `some path`, or `maybe none` when neither the XDG variable nor the home
 directory is available.

 ## Memoria
 The payload is a fresh owned string; release it with `banish`.

 ## Efectos
 On Windows it returns `%LOCALAPPDATA%`; on POSIX `$XDG_CACHE_HOME` or
 `~/.cache`.

 ## Ejemplo
 ```pengu
 let cache as maybe string is calling rites.cache_dir
 ```

### `data_dir`

> **data_dir**() -> maybe string

 Returns the user local data directory path.

 ## Parámetros
 - None.

 ## Retorno
 `some path`, or `maybe none` when neither the XDG variable nor the home
 directory is available.

 ## Memoria
 The payload is a fresh owned string; release it with `banish`.

 ## Efectos
 On Windows it returns `%APPDATA%`; on POSIX `$XDG_DATA_HOME` or
 `~/.local/share`.

 ## Ejemplo
 ```pengu
 let data as maybe string is calling rites.data_dir
 ```

### `uname`

> **uname**() -> string

 Returns the operating-system family name: "Windows", "Darwin", "Linux" or
 "Unknown".

 ## Parámetros
 - None.

 ## Retorno
 The OS name as a fresh owned string.

 ## Memoria
 The result is freshly allocated; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling spark.println with calling rites.uname    # e.g. "Linux"
 ```

### `hostname`

> **hostname**() -> string

 Returns the machine's host name.

 ## Parámetros
 - None.

 ## Retorno
 The host name as a fresh owned string; it may be empty when the OS cannot
 provide one.

 ## Memoria
 The result is freshly allocated; release it with `banish`.

 ## Ejemplo
 ```pengu
 let host as string is calling rites.hostname
 ```

### `os_arch`

> **os_arch**() -> string

 Returns the host CPU architecture string ("x64", "arm64", "x86", "arm", or
 "unknown").

 ## Parámetros
 - None.

 ## Retorno
 The architecture name as a string literal chosen at compile time.

 ## Memoria
 No allocations; the result is a non-owning literal view.

 ## Ejemplo
 ```pengu
 calling rites.os_arch    # e.g. "x64"
 ```

### `host_arch`

> **host_arch**() -> string

 The host architecture, detected at runtime.

 Unlike `os_arch`, this reflects the machine that is running the binary, not
 the `arch` value baked into the current build.

 ## Memoria
 The result is freshly allocated; release it with `banish`.

### `os_family`

> **os_family**() -> string

 Returns the operating-system family name. Alias of `uname()`.

 ## Parámetros
 - None.

 ## Retorno
 The OS name as a fresh owned string.

 ## Memoria
 The result is freshly allocated; release it with `banish`.

 ## Ejemplo
 ```pengu
 let family as string is calling rites.os_family
 ```

### `is_windows`

> **is_windows**() -> bool

 Checks if the current target operating system is Windows.

 ## Parámetros
 - None.

 ## Retorno
 A compile-time constant `bool`.

 ## Memoria
 No allocations.

 ## Ejemplo
 ```pengu
 if calling rites.is_windows:
     calling spark.println with "windows build"
 ```

### `is_unix`

> **is_unix**() -> bool

 Checks if the current target operating system is Unix-like (Linux, macOS,
 BSD).

 ## Parámetros
 - None.

 ## Retorno
 A compile-time constant `bool`: `true` for every non-Windows target.

 ## Memoria
 No allocations.

 ## Ejemplo
 ```pengu
 calling rites.is_unix    # true on Linux
 ```

### `is_macos`

> **is_macos**() -> bool

 Checks if the current target operating system is macOS (Darwin).

 ## Parámetros
 - None.

 ## Retorno
 A compile-time constant `bool`.

 ## Memoria
 No allocations.

 ## Ejemplo
 ```pengu
 calling rites.is_macos    # false on Linux
 ```

### `is_linux`

> **is_linux**() -> bool

 Checks if the current target operating system is Linux.

 ## Parámetros
 - None.

 ## Retorno
 A compile-time constant `bool`.

 ## Memoria
 No allocations.

 ## Ejemplo
 ```pengu
 calling rites.is_linux    # true on Linux
 ```

### `which_all`

> **which_all**(cmd: string) -> list of string

 Searches the system PATH for all executable candidates matching `cmd`.

 ## Parámetros
 - `cmd`: the executable name to search for. Borrowed.

 ## Retorno
 A new owned `list of string` with one entry per matching PATH directory, in
 PATH order; empty when `PATH` is unset, empty, or has no match.

 ## Memoria
 The list and each element are owned by the caller. The elements are built by
 joining a PATH directory with `cmd`, so release each element before the list.

 ## Efectos
 On Windows the delimiter is `;` and `.exe`, `.bat`, `.cmd` (and the bare
 name) are tested; on POSIX the delimiter is `:`.

 ## Notes
 On POSIX, `which_all` checks for regular file existence in PATH directories
 (`pengu_c_archivum_is_file`). It does not currently inspect POSIX executable
 permission bits (e.g. `access(X_OK)`), which requires a dedicated runtime
 permission bridge.

 ## Ejemplo
 ```pengu
 let hits as list of string is calling rites.which_all with "sh"
 ```

### `which`

> **which**(cmd: string) -> maybe string

 Locates the first executable matching `cmd` on the system PATH.

 ## Parámetros
 - `cmd`: the executable name to search for. Borrowed.

 ## Retorno
 `some path` for the first PATH match, or `maybe none` when `cmd` is not on
 the PATH.

 ## Memoria
 The payload is an owned path string; release it with `banish`.

 ## Ejemplo
 ```pengu
 let sh as maybe string is calling rites.which with "sh"
 ```

### `exit`

> **exit**(code: int) -> void

 Terminates the process immediately with exit code `code` (never returns).

 ## Parámetros
 - `code`: the process exit status (0–255 on POSIX).

 ## Retorno
 Nothing; the helper returns `void`. The process ends before it can return.

 ## Memoria
 No allocations.

 ## Ejemplo
 ```pengu
 calling rites.exit with 0
 ```

### `exec`

> **exec**(cmd: string, args: list of string) -> int

 Runs `cmd` plus `args` through the platform shell and blocks until
 completion. Returns the raw status code reported by the shell (-1 on error).

 ## Parámetros
 - `cmd`: the program or shell line to run. Borrowed.
 - `args`: the arguments appended to `cmd`. Borrowed.

 ## Retorno
 The raw status reported by `system()`; `-1` on failure.

 ## Memoria
 Arguments are not retained.

 ## Efectos
 Uses `system()` internally; the arguments are joined with spaces and are not
 escaped, so do NOT pass untrusted user input without sanitization.

 ## Ejemplo
 ```pengu
 calling rites.exec with "echo", ["hello"]
 ```

### `spawn`

> **spawn**(cmd: string, args: list of string) -> int

 Launches `cmd` with `args` and blocks until it finishes. Shares exec's
 implementation.

 ## Parámetros
 - `cmd`: the program or shell line to run. Borrowed.
 - `args`: the arguments appended to `cmd`. Borrowed.

 ## Retorno
 The raw status reported by `system()`; `-1` on failure.

 ## Memoria
 Arguments are not retained.

 ## Efectos
 Currently identical to `exec` (a blocking `system()` call).

 ## Ejemplo
 ```pengu
 calling rites.spawn with "echo", ["hello"]
 ```

### `exec_ok`

> **exec_ok**(cmd: string, args: list of string) -> bool

 Runs `cmd` with `args` and returns true if the command succeeded.

 ## Parámetros
 - `cmd`: the program or shell line to run. Borrowed.
 - `args`: the arguments appended to `cmd`. Borrowed.

 ## Retorno
 `true` when the shell status is exactly `0`, `false` otherwise.

 ## Memoria
 Arguments are not retained.

 ## Ejemplo
 ```pengu
 if calling rites.exec_ok with "true", []:
     calling spark.println with "ok"
 ```

### `exec_or_panic`

> **exec_or_panic**(cmd: string, args: list of string) -> void

 Runs `cmd` with `args` and panics if the command fails.

 ## Parámetros
 - `cmd`: the program or shell line to run. Borrowed.
 - `args`: the arguments appended to `cmd`. Borrowed.

 ## Retorno
 Nothing; the helper returns `void`.

 ## Efectos
 Aborts the program via `spark.panic` when the status is not `0`; the message
 is exactly `Command execution failed with status: <status>`.

 ## Memoria
 Arguments are not retained.

 ## Ejemplo
 ```pengu
 calling rites.exec_or_panic with "make", ["all"]
 ```

### `run_shell`

> **run_shell**(cmdline: string) -> int

 Executes a raw command line string directly through the platform shell.

 ## Parámetros
 - `cmdline`: the complete shell command line. Borrowed.

 ## Retorno
 The raw status reported by the platform shell; `-1` on failure.

 ## Memoria
 Arguments are not retained.

 ## Efectos
 Uses `system()` internally; do NOT pass untrusted user input without
 sanitization.

 ## Ejemplo
 ```pengu
 calling rites.run_shell with "echo hello"
 ```

### `shell_escape`

> **shell_escape**(s: string) -> string

 Escapes string `s` for safe inclusion as a command line argument.

 ## Parámetros
 - `s`: the raw argument text. Borrowed.

 ## Retorno
 A new owned escaped string, always wrapped in quotes (`""`/`''` for an empty
 input).

 ## Memoria
 The result is freshly allocated; release it with `banish`.

 ## Efectos
 POSIX: wraps in single quotes and rewrites each `'` as `'\''`. Windows:
 wraps in double quotes and prefixes each embedded `"` with a backslash.

 ## Ejemplo
 ```pengu
 calling rites.shell_escape with "it's"    # 'it'\''s'
 ```

### `run_capture`

> **run_capture**(cmd: string, args: list of string) -> maybe string

 Runs `cmd` with `args`, capturing its standard output.

 ## Parámetros
 - `cmd`: the executable name or shell line. Borrowed.
 - `args`: the arguments, each escaped with `shell_escape`. Borrowed.

 ## Retorno
 `some stdout` when the command exits with status `0`; `maybe none` on a
 non-zero exit, a closed pipe, or an empty command.

 ## Memoria
 The payload is a fresh owned string; release it with `banish`.

 ## Efectos
 Runs the command through the platform shell (`popen`) and blocks until it
 finishes; stderr is not captured and follows the process's own stream.

 ## Ejemplo
 ```pengu
 let out as maybe string is calling rites.run_capture with "sh", ["-c", "echo hi"]
 ```

### `run_capture_result`

> **run_capture_result**(cmd: string, args: list of string) -> result of string to string

 Runs `cmd` with `args`, capturing its standard output and exit code.

 ## Parámetros
 - `cmd`: the executable name or shell line. Borrowed.
 - `args`: the arguments, each escaped with `shell_escape`. Borrowed.

 ## Retorno
 A native `result of string to string`, owned by the caller: `ok(stdout)` on a
 zero exit, `err("command exited with code <code>")` otherwise.

 ## Memoria
 The result owns its payload; release it with `banish`.

 ## Efectos
 Runs the command through the platform shell (`popen`) and blocks until it
 finishes; stderr is not captured.

 ## Ejemplo
 ```pengu
 let r as result of string to string is calling rites.run_capture_result with "sh", ["-c", "exit 3"]
 ```

### `run_capture_lines`

> **run_capture_lines**(cmd: string, args: list of string) -> maybe list of string

 Runs `cmd` with `args`, capturing its standard output split into lines.

 ## Parámetros
 - `cmd`: the executable name or shell line. Borrowed.
 - `args`: the arguments, each escaped with `shell_escape`. Borrowed.

 ## Retorno
 `some lines` on a zero exit, where each line has no trailing newline and a
 trailing newline does not produce a final empty entry; `maybe none` on a
 non-zero exit. Empty output yields `some []`.

 ## Memoria
 The list and each element are owned; release the elements before the list.

 ## Efectos
 Runs the command through the platform shell (`popen`) and blocks until it
 finishes; stderr is not captured.

 ## Ejemplo
 ```pengu
 let lines as maybe list of string is calling rites.run_capture_lines with "printf", ["a\nb\n"]
 ```

### `run_capture_stderr`

> **run_capture_stderr**(cmd: string, args: list of string) -> maybe string

 Runs `cmd` with `args`, capturing its standard error output.

 ## Parámetros
 - `cmd`: the executable name or shell line. Borrowed.
 - `args`: the arguments, each escaped with `shell_escape`. Borrowed.

 ## Retorno
 `some stderr` when the command exits with status `0`; `maybe none` on a
 non-zero exit, a closed pipe, or an empty command.

 ## Memoria
 The payload is a fresh owned string; release it with `banish`.

 ## Efectos
 POSIX only: the command line is run inside a subshell that duplicates stderr
 onto stdout and then discards stdout. On Windows the redirect is not applied
 and the result follows `run_capture`.

 ## Ejemplo
 ```pengu
 let err as maybe string is calling rites.run_capture_stderr with "sh", ["-c", "echo oops >&2"]
 ```

### `run_shell_capture`

> **run_shell_capture**(cmdline: string) -> maybe string

 Runs a raw shell command line, capturing its standard output.

 ## Parámetros
 - `cmdline`: the complete shell command line. Borrowed.

 ## Retorno
 `some stdout` when the shell exits with status `0`; `maybe none` otherwise.

 ## Memoria
 The payload is a fresh owned string; release it with `banish`.

 ## Efectos
 Runs the line through the platform shell (`popen`) and blocks until it
 finishes; the caller owns the quoting, so do NOT pass untrusted input
 unescaped.

 ## Ejemplo
 ```pengu
 let out as maybe string is calling rites.run_shell_capture with "echo hi | tr a-z A-Z"
 ```

### `current_user`

> **current_user**() -> maybe string

 Returns the username of the current logged-in user.

 ## Parámetros
 - None.

 ## Retorno
 `some name`, or `maybe none` when the environment does not carry one.

 ## Memoria
 The payload is a fresh owned string; release it with `banish`.

 ## Efectos
 On Windows it inspects `USERNAME`; on POSIX `USER` with fallback to `LOGNAME`.

 ## Ejemplo
 ```pengu
 let user as maybe string is calling rites.current_user
 ```

### `_rites_build_cmdline`

> **_rites_build_cmdline**(cmd: string, args: list of string) -> string

 Builds the shell command line `cmd arg1 arg2 ...` with every element escaped.

### `_rites_shell_capture`

> **_rites_shell_capture**(cmdline: string, err: ref to string) -> maybe string

 Runs `cmdline` and returns the captured output, or none on failure.

 On failure the `err` slot receives the C bridge's message (empty when the
 command was never started); on success the slot stays empty.

### `_rites_split_lines`

> **_rites_split_lines**(s: string) -> list of string

 Splits `s` on newlines, dropping a single trailing empty entry.

### `_rites_expect_int`

> **_rites_expect_int**(got: int, want: int, label: string) -> void

 Aborts the current test with `label` when `got != want`.

### `_rites_expect_str`

> **_rites_expect_str**(got: string, want: string, label: string) -> void

 Aborts the current test with `label` when `got != want`.

### `_rites_expect_true`

> **_rites_expect_true**(cond: bool, label: string) -> void

 Aborts the current test with `label` when `cond` is false.

### `_rites_contains`

> **_rites_contains**(s: string, needle: string) -> bool

 True when `s` contains `needle` (byte scan; `needle` empty matches anywhere).

### `_rites_has_env`

> **_rites_has_env**(name: string) -> bool

 Test wrapper: `has_env` under a unique name for the shared test namespace.

### `_rites_getenv`

> **_rites_getenv**(name: string) -> maybe string

 Test wrapper: `getenv` under a unique name for the shared test namespace.

### `_rites_setenv`

> **_rites_setenv**(name: string, value: string, overwrite: bool) -> bool

 Test wrapper: `setenv` under a unique name for the shared test namespace.

### `_rites_unsetenv`

> **_rites_unsetenv**(name: string) -> bool

 Test wrapper: `unsetenv` under a unique name for the shared test namespace.

### `"RITES_VERSION is 2.14.0"`

> test "RITES_VERSION is 2.14.0"

_Undocumented._

### `"setenv, getenv and has_env round-trip"`

> test "setenv, getenv and has_env round-trip"

_Undocumented._

### `"an empty environment value is present"`

> test "an empty environment value is present"

_Undocumented._

### `"has_env is false for an unused name"`

> test "has_env is false for an unused name"

_Undocumented._

### `"setenv without overwrite keeps the first value"`

> test "setenv without overwrite keeps the first value"

_Undocumented._

### `"unsetenv on a missing name does not panic"`

> test "unsetenv on a missing name does not panic"

_Undocumented._

### `"getenv_or returns the fallback for an unset name"`

> test "getenv_or returns the fallback for an unset name"

_Undocumented._

### `"getenv_int parses a set variable"`

> test "getenv_int parses a set variable"

_Undocumented._

### `"getenv_int rejects a non-numeric value"`

> test "getenv_int rejects a non-numeric value"

_Undocumented._

### `"getenv_bool accepts the documented spellings"`

> test "getenv_bool accepts the documented spellings"

_Undocumented._

### `"getenv_bool rejects an unrecognized value"`

> test "getenv_bool rejects an unrecognized value"

_Undocumented._

### `"expand_env replaces a braced variable"`

> test "expand_env replaces a braced variable"

_Undocumented._

### `"expand_env keeps an unknown variable empty"`

> test "expand_env keeps an unknown variable empty"

_Undocumented._

### `"expand_env treats a doubled dollar as a literal"`

> test "expand_env treats a doubled dollar as a literal"

_Undocumented._

### `"env_substitute matches expand_env"`

> test "env_substitute matches expand_env"

_Undocumented._

### `"get_args and get_argc agree"`

> test "get_args and get_argc agree"

_Undocumented._

### `"get_argv of index 0 is not empty"`

> test "get_argv of index 0 is not empty"

_Undocumented._

### `"arg_at_or falls back for an out-of-range index"`

> test "arg_at_or falls back for an out-of-range index"

_Undocumented._

### `"shell_escape wraps a plain argument in single quotes"`

> test "shell_escape wraps a plain argument in single quotes"

_Undocumented._

### `"shell_escape doubles an embedded single quote"`

> test "shell_escape doubles an embedded single quote"

_Undocumented._

### `"shell_escape of the empty string is two single quotes"`

> test "shell_escape of the empty string is two single quotes"

_Undocumented._

### `"which finds sh or skips"`

> test "which finds sh or skips"

_Undocumented._

### `"which_all returns sh when which does"`

> test "which_all returns sh when which does"

_Undocumented._

### `"which returns none for a name that cannot exist"`

> test "which returns none for a name that cannot exist"

_Undocumented._

### `"run_capture of sh -c echo returns stdout"`

> test "run_capture of sh -c echo returns stdout"

_Undocumented._

### `"run_capture_lines splits stdout into lines"`

> test "run_capture_lines splits stdout into lines"

_Undocumented._

### `"run_capture_lines of empty stdout is an empty list"`

> test "run_capture_lines of empty stdout is an empty list"

_Undocumented._

### `"run_capture returns none on a non-zero exit"`

> test "run_capture returns none on a non-zero exit"

_Undocumented._

### `"run_capture_result reports the exit code"`

> test "run_capture_result reports the exit code"

_Undocumented._

### `"run_capture_result is ok on success"`

> test "run_capture_result is ok on success"

_Undocumented._

### `"run_capture_stderr captures only stderr"`

> test "run_capture_stderr captures only stderr"

_Undocumented._

### `"run_shell_capture returns the pipeline output"`

> test "run_shell_capture returns the pipeline output"

_Undocumented._

### `"run_shell_capture returns none on a failing line"`

> test "run_shell_capture returns none on a failing line"

_Undocumented._

### `"get_uid and get_gid have the maybe shape of the target"`

> test "get_uid and get_gid have the maybe shape of the target"

_Undocumented._

### `"effective ids have the maybe shape of the target"`

> test "effective ids have the maybe shape of the target"

_Undocumented._

### `"is_windows and is_unix are consistent"`

> test "is_windows and is_unix are consistent"

_Undocumented._

### `"platform predicates are compile-time constants"`

> test "platform predicates are compile-time constants"

_Undocumented._

### `"os_arch returns a known name or unknown"`

> test "os_arch returns a known name or unknown"

_Undocumented._

### `"getpid and getppid are non-negative"`

> test "getpid and getppid are non-negative"

_Undocumented._

### `"getcwd returns the current directory"`

> test "getcwd returns the current directory"

_Undocumented._

### `"temp_dir always has a fallback"`

> test "temp_dir always has a fallback"

_Undocumented._

### `"home_dir is either present or absent"`

> test "home_dir is either present or absent"

_Undocumented._

### `"parse_flags ignores positional arguments"`

> test "parse_flags ignores positional arguments"

_Undocumented._

### `"has_flag is false for an unused flag"`

> test "has_flag is false for an unused flag"

_Undocumented._

### `"uname and os_family agree"`

> test "uname and os_family agree"

_Undocumented._

### `"hostname returns a string"`

> test "hostname returns a string"

_Undocumented._

### `"current_user shape matches the platform"`

> test "current_user shape matches the platform"

_Undocumented._

### `"get_env_keys and get_env_map describe the same environment"`

> test "get_env_keys and get_env_map describe the same environment"

_Undocumented._

### `"set_env_map reports zero for an empty map"`

> test "set_env_map reports zero for an empty map"

_Undocumented._

