# `std.archivum` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `ARCHIVUM_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/archivum.pengu`](../std/archivum.pengu).

`archivum` owns the file system: reading and writing text and bytes, appending,
copying, moving, renaming, deleting, listing directories, metadata, search and
temporary paths. Every operation bottoms out in a `declare`d C runtime primitive
(`pengu_c_archivum_*`); the module adds the ergonomics on top — `maybe`/`bool`
answers, `result of T to IoError` variants that report *why* a call failed, and
the recursive helpers (`copy_tree`, `walk`, `list_files_recursive`, `dir_size`,
`find_*`).

Its import list is `std.spark`, `std.oracle`, `std.compass`, `std.scrolls`,
`std.tally` and `std.rites`; only `spark` (`panic`/`parse_int`/`println`),
`compass` (`join`/`basename`/`ext`) and `rites` (`getpid`/`getenv`/`getcwd`/
`chdir`) are actually called. It deliberately does **not** import `std.ward`,
which would close the cycle `ward -> rites -> archivum`.

The module carries `insignia archivum_`, so every top-level C symbol it
generates is prefixed and the weaves `rename`, `symlink` and `realpath` cannot
collide with the libc functions of the same name when `std/archivum.pengu` is the
bundle entry. The `pengu_c_archivum_*` declarations sit before the directive and
keep their exact runtime names.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every parameter (`path`, `src`, `dst`, `content`, `data`, `lines`, `pattern`, `root`, `target`, `link`, `prefix`) | borrowed, read-only | never `banish` |
| scalar returns (`bool`, `int`, `float`) | plain value | never `banish` |
| `maybe string` / `maybe int` / `maybe float` / `maybe list of string` / `maybe map of string to string` | `some` owns its payload; `none` owns nothing | `banish` |
| `result of T to IoError` | `ok`/`err` owns its payload; `IoError` is a value | `banish` the result (and a `string`/`list`/`map` payload) |
| `string`, `list of string`, `list of list of string`, `map of string to string` | freshly allocated; list elements are owned too | `banish` each element, then the container |
| the `compass.Path` receiver | borrowed through `self->raw` | the caller releases its own `Path` |
| `IoError`, `FsCopyTask` | value omen/rune, no heap | never `banish` |

## Constants

`ARCHIVUM_VERSION as string is "2.1.0"` — the revision of the **archivum API**,
not of the toolchain. It bumps only when a signature on this page changes.

## Error model — `omen IoError`

| Member | `describe_error` text | Raised by |
|---|---|---|
| `NotFound` | `no such file or directory` | read/delete/`*_result` on a missing entry. |
| `IsADirectory` | `is a directory` | read/write/delete when `path` names a directory. |
| `NotAFile` | `not a regular file` | reserved for the non-regular-file case. |
| `Permission` | `permission denied` | reserved for the mode-check failure. |
| `Unknown` | `unknown I/O error` | any other runtime failure. |

| Symbol | Signature | Semantics |
|---|---|---|
| `describe_error` | `(e: IoError) -> string` | Owned English message for an `IoError`; the same on every platform. |

## Native runtime declarations (internal C bridges)

These 21 `declare`s are the module's only file-system access. They are the
runtime contract, not the PenguScript API; call the weaves above them. The
`insignia archivum_` directive does not rename them.

| Declaration | Signature |
|---|---|
| `pengu_c_archivum_read_file` | `(string) -> maybe string` |
| `pengu_c_archivum_write_file` | `(string, string) -> bool` |
| `pengu_c_archivum_append_file` | `(string, string) -> bool` |
| `pengu_c_archivum_delete_file` | `(string) -> bool` |
| `pengu_c_archivum_exists` | `(string) -> bool` |
| `pengu_c_archivum_is_file` | `(string) -> bool` |
| `pengu_c_archivum_is_dir` | `(string) -> bool` |
| `pengu_c_archivum_is_symlink` | `(string) -> bool` |
| `pengu_c_archivum_create_dir` | `(string, bool) -> bool` |
| `pengu_c_archivum_remove_dir` | `(string, bool) -> bool` |
| `pengu_c_archivum_read_dir` | `(string) -> maybe list of string` |
| `pengu_c_archivum_copy_file` | `(string, string, bool) -> bool` |
| `pengu_c_archivum_move_file` | `(string, string, bool) -> bool` |
| `pengu_c_archivum_rename` | `(string, string) -> bool` |
| `pengu_c_archivum_metadata` | `(string) -> maybe map of string to string` |
| `pengu_c_archivum_glob` | `(string) -> list of string` |
| `pengu_c_archivum_walk` | `(string) -> list of list of string` |
| `pengu_c_archivum_touch` | `(string) -> bool` |
| `pengu_c_archivum_symlink` | `(string, string) -> bool` |
| `pengu_c_archivum_read_symlink` | `(string) -> maybe string` |
| `pengu_c_archivum_realpath` | `(string) -> maybe string` |

## Core file operations

| Symbol | Signature | Semantics |
|---|---|---|
| `read_file` | `(path: string) -> maybe string` | Whole file as UTF-8 text; `none` when it cannot be read. |
| `read_text` | `(path: string) -> maybe string` | Alias of `read_file`. |
| `read_bytes` | `(path: string) -> maybe string` | Raw byte buffer, no UTF-8 decoding; alias of `read_file`. |
| `write_file` | `(path: string, content: string) -> bool` | Writes verbatim, creating or truncating; missing parents are not created. |
| `write_text` | `(path: string, content: string) -> bool` | Alias of `write_file`. |
| `write_bytes` | `(path: string, data: string) -> bool` | Writes a raw byte buffer; alias of `write_file`. |
| `append_file` | `(path: string, content: string) -> bool` | Appends, creating the file when missing. |
| `append_bytes` | `(path: string, data: string) -> bool` | Appends a raw byte buffer; alias of `append_file`. |
| `delete_file` | `(path: string) -> bool` | Deletes a file, an empty directory or a symlink. |

## Existence, type and permission predicates

| Symbol | Signature | Semantics |
|---|---|---|
| `exists` | `(path: string) -> bool` | True when any entry exists at `path`. |
| `is_file` | `(path: string) -> bool` | True for a regular file. |
| `is_dir` | `(path: string) -> bool` | True for a directory. |
| `is_symlink` | `(path: string) -> bool` | True for a symbolic link (not followed). |
| `is_readable` | `(path: string) -> bool` | `exists and is_file` plus a read bit in the POSIX mode (`0400\|0040\|0004`). |
| `is_writable` | `(path: string) -> bool` | `exists and is_file` plus a write bit (`0200\|0020\|0002`). |
| `is_empty_file` | `(path: string) -> bool` | True only for an existing regular file of size 0. |
| `is_empty_dir` | `(path: string) -> bool` | True only for an existing directory with zero entries. |

## Directories — create, remove, list

| Symbol | Signature | Semantics |
|---|---|---|
| `create_dir` | `(path: string, parents: bool is false) -> bool` | Creates the directory; `parents` also creates missing ancestors. |
| `remove_dir` | `(path: string, recursive: bool is false) -> bool` | Removes the directory; `recursive` removes its contents too. |
| `read_dir` | `(path: string) -> maybe list of string` | Bare direct entry names; `none` when not a readable directory. |
| `read_dir_full` | `(path: string) -> list of string` | Same entries already joined with `path` via `compass.join`; empty on failure. |

## Copy, move, rename and recursive copy

| Symbol | Signature | Semantics |
|---|---|---|
| `copy_file` | `(src: string, dst: string, overwrite: bool is false) -> bool` | Copies a file; the parent of `dst` must exist. |
| `move_file` | `(src: string, dst: string, overwrite: bool is false) -> bool` | Moves a file; a cross-device move is a plain failure. |
| `rename` | `(old: string, new: string) -> bool` | Renames an entry, overwriting an existing `new` unconditionally. |
| `copy_tree` | `(src: string, dst: string) -> bool` | Recursive copy; merges into `dst`, skips symlinks/special files, non-transactional. |
| `list_files_recursive` | `(root: string) -> list of string` | Every regular file below `root`, depth-first; empty when none. |

## Metadata, size, time and permissions

| Symbol | Signature | Semantics |
|---|---|---|
| `metadata` | `(path: string) -> maybe map of string to string` | Owned map with keys `size`, `is_file`, `is_dir`, `is_symlink`, `modified`, `created`, `accessed`, `permissions`. |
| `file_size` | `(path: string) -> maybe int` | Size in bytes from the `size` key; `none` when absent/unparseable. |
| `dir_size` | `(path: string, recursive: bool is false) -> maybe int` | Summed size of the regular files; `none` when `path` is not a directory. |
| `modified_time` | `(path: string) -> maybe float` | `modified` epoch seconds as `float`. |
| `created_time` | `(path: string) -> maybe float` | `created` epoch seconds; `none` where the file system does not record it. |
| `accessed_time` | `(path: string) -> maybe float` | `accessed` epoch seconds as `float`. |
| `permissions` | `(path: string) -> maybe int` | Decimal value of `st_mode & 0777` (0644 → 420). |

## Lines and text helpers

| Symbol | Signature | Semantics |
|---|---|---|
| `read_lines` | `(path: string) -> maybe list of string` | Splits on `"\n"` only; a trailing newline yields a final empty element and `"\r\n"` keeps the `\r`. |
| `read_first_n_lines` | `(path: string, n: int) -> maybe list of string` | Up to `n` leading lines; `n <= 0` gives an empty list. |
| `read_last_n_lines` | `(path: string, n: int) -> maybe list of string` | Up to `n` trailing elements with `read_lines` semantics. |
| `count_lines` | `(path: string) -> maybe int` | Number of `"\n"`-separated elements (a trailing newline counts one extra). |
| `write_lines` | `(path: string, lines: list of string) -> bool` | Joins with `"\n"` plus a trailing `"\n"`; an empty list writes a single `"\n"`. |
| `append_lines` | `(path: string, lines: list of string) -> bool` | Same encoding, appended to `path`. |

## Result-based I/O (`result of T to IoError`)

The `maybe`/`bool` API above stays unchanged: `maybe` answers "is it there?",
these variants answer "it failed, and why". Payloads are built with the
`ok_of`/`err_of` intrinsics and are owned by the caller.

| Symbol | Signature | Semantics |
|---|---|---|
| `read_file_result` | `(path: string) -> result of string to IoError` | `IsADirectory`, `NotFound` or `Unknown`. |
| `write_file_result` | `(path: string, content: string) -> result of int to IoError` | `ok(0)` on success; `IsADirectory`/`Unknown` otherwise. |
| `delete_file_result` | `(path: string) -> result of int to IoError` | `ok(0)`; `NotFound`/`IsADirectory`/`Unknown`. |
| `read_lines_result` | `(path: string) -> result of list of string to IoError` | `read_lines` with a cause. |
| `write_lines_result` | `(path: string, lines: list of string) -> result of int to IoError` | `write_lines` with a cause; `ok(0)`. |
| `append_lines_result` | `(path: string, lines: list of string) -> result of int to IoError` | `append_lines` with a cause; `ok(0)`. |
| `read_dir_result` | `(path: string) -> result of list of string to IoError` | `read_dir` with a cause. |
| `create_dir_result` | `(path: string, parents: bool is false) -> result of bool to IoError` | `create_dir` with a cause. |
| `remove_dir_result` | `(path: string, recursive: bool is false) -> result of bool to IoError` | `remove_dir` with a cause. |
| `copy_file_result` | `(src: string, dst: string, overwrite: bool is false) -> result of bool to IoError` | `copy_file` with a cause. |
| `copy_tree_result` | `(src: string, dst: string) -> result of bool to IoError` | `copy_tree` with a cause. |
| `touch_result` | `(path: string) -> result of bool to IoError` | `touch` with a cause. |
| `symlink_result` | `(target: string, link: string) -> result of bool to IoError` | `symlink` with a cause. |
| `metadata_result` | `(path: string) -> result of map of string to string to IoError` | `metadata` with a cause. |

## Search, glob and traversal

| Symbol | Signature | Semantics |
|---|---|---|
| `glob` | `(pattern: string) -> list of string` | Globs from the working directory (`*`, `?`, `**`); empty when nothing matches. |
| `walk` | `(root: string) -> list of list of string` | Owned nested list; each inner list is a directory followed by its bare entry names, depth-first from `root`. |
| `find_files` | `(root: string, recursive: bool is true) -> list of string` | Every regular file under `root`. |
| `find_dirs` | `(root: string, recursive: bool is true) -> list of string` | Every subdirectory under `root`. |
| `find_by_name` | `(root: string, target_name: string, recursive: bool is true) -> list of string` | Files whose basename equals `target_name` (case-sensitive). |
| `find_by_ext` | `(root: string, extension: string, recursive: bool is true) -> list of string` | Files whose extension matches, with or without the leading dot. |

## Links, paths and touch

| Symbol | Signature | Semantics |
|---|---|---|
| `touch` | `(path: string) -> bool` | Updates the modification time, creating an empty file when missing. |
| `symlink` | `(target: string, link: string) -> bool` | Creates a symlink; `target` need not exist. |
| `read_symlink` | `(path: string) -> maybe string` | Link target (relative stays relative); `none` when `path` is not a symlink. |
| `realpath` | `(path: string) -> maybe string` | Canonical absolute path with symlinks and `.`/`..` resolved; `none` when missing. |

## Temporary paths

| Symbol | Signature | Semantics |
|---|---|---|
| `temp_dir` | `() -> string` | `$TEMP`/`$TMP` (or `C:\Temp`) on Windows, `$TMPDIR` (or `/tmp`) elsewhere; not created. |
| `temp_file` | `(prefix: string is "pengu") -> string` | Path of a not-yet-existing file under `temp_dir`; embeds pid and a counter; not created. |

## Methods on `compass.Path` (external `enchanting` block)

`enchanting compass.Path` adds file-system methods to the owned path rune of
`std.compass` without touching `std/compass.pengu`; each method delegates through
`self->raw` to the module weaves above. The receiver is borrowed; `std.compass`
must be imported for the receiver type to exist.

| Method | Signature | Semantics |
|---|---|---|
| `read_text` | `() -> maybe string` | `read_file` on `self->raw`. |
| `write_text` | `(content: string) -> bool` | `write_file` on `self->raw`. |
| `read_lines` | `() -> maybe list of string` | `read_lines` on `self->raw`. |
| `append_text` | `(content: string) -> bool` | `append_file` on `self->raw`. |
| `delete` | `() -> bool` | `delete_file` on `self->raw`; use `rmdir` for a directory. |
| `mkdir` | `(parents: bool is false) -> bool` | `create_dir` on `self->raw`. |
| `rmdir` | `(recursive: bool is false) -> bool` | `remove_dir` on `self->raw`. |
| `iter_dir` | `() -> list of string` | `read_dir_full` on `self->raw`: the entries **of this path itself**, so it must be called on a directory; empty when it cannot be read. |
| `stat` | `() -> maybe map of string to string` | `metadata` on `self->raw` (same map keys). |

## Internal rune

`rune FsCopyTask: s as string, d as string` is the queue record used by
`copy_tree`. It is an implementation detail, not part of the callable surface,
and is listed here only so the inventory is complete.

## Migración (2.0.0 → 2.1.0)

2.1.0 is additive: no 2.0.0 symbol was removed, renamed or given new
bounds/behaviour, and every 2.0.0 signature is preserved exactly.

| Added in 2.1.0 | Purpose |
|---|---|
| `read_text` / `write_text` | explicit aliases of `read_file` / `write_file`. |
| `read_last_n_lines` | tail of a file, complementing `read_first_n_lines`. |
| `read_dir_full` | `read_dir` entries already joined with the directory. |
| `is_readable` / `is_writable` | existence + regular file + POSIX mode-bit check. |
| `read_lines_result`, `write_lines_result`, `append_lines_result`, `read_dir_result`, `create_dir_result`, `remove_dir_result`, `copy_file_result`, `copy_tree_result`, `touch_result`, `symlink_result`, `metadata_result` | `result of T to IoError` variants of the corresponding weaves. |
| `enchanting compass.Path` | the nine methods documented above. |
| `insignia archivum_` | prefixes the module's own C symbols so `rename`/`symlink`/`realpath` cannot collide with libc in a bundle. |

The 21 `pengu_c_archivum_*` declarations, the `rune FsCopyTask` record and all
`IoError` members are byte-identical to 2.0.0. The only other changes are
documentation/style and the private `# --- Tests ---` harness. Nothing is
deprecated in this revision.

## Internal tests

The internal `# --- Tests ---` suite holds **33 `test` blocks** on top of the
private `_arch_expect_*` harness (`spark.panic`; `std.ward` cannot be imported
from a library module). Every test builds `/tmp/pengu_arch_test_<pid>_<name>`
and removes it again.

## Private helpers (internal)

Not public API; do not call them.

| Symbol | Signature | Role |
|---|---|---|
| `_metadata_int` | `(path: string, key: string) -> maybe int` | Parses one integer metadata key. |
| `_has_mode_bit` | `(path: string, mask: int) -> bool` | Mode-bit test behind `is_readable`/`is_writable`. |
| `_missing_dir_error` | `(path: string) -> IoError` | Shared `NotFound`/`IsADirectory`/`Unknown` classification. |
| `_arch_expect_int` | `(got: int, want: int, label: string) -> void` | Test assertion. |
| `_arch_expect_str` | `(got: string, want: string, label: string) -> void` | Test assertion. |
| `_arch_expect_true` | `(cond: bool, label: string) -> void` | Test assertion. |
| `_arch_path` | `(base: string, name: string) -> string` | Test path join. |
| `_arch_fresh_dir` | `(base: string) -> string` | Recreates the test directory. |
| `_arch_cleanup` | `(base: string) -> void` | Removes the test directory. |
| `_arch_base` | `(name: string) -> string` | Unique `/tmp/pengu_arch_test_<pid>_<name>` root. |
