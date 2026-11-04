# std.archivum

> Source: `std/archivum.pengu`

std/archivum.pengu — file-system operations: reading, writing, copying,
moving, deleting, listing, metadata and searching.

Every operation delegates to a `declare`d C runtime primitive; the module
itself adds the ergonomics (`maybe`/`bool` answers plus `result` variants that
report *why* an operation failed) and the recursive helpers (`copy_tree`,
`walk`, `list_files_recursive`, `dir_size`, `find_*`).

## Example
```pengu
import std.archivum
import std.spark

weave main into int:
    let path as string is "/tmp/archivum_demo.txt"
    if calling archivum.write_file with path, "hello\nworld\n":
        let text as maybe string is calling archivum.read_file with path
        if text.is_present:
            calling spark.println with text.value
    calling archivum.delete_file with path
    return 0
```

## Memory
A `string` is a value: inputs are borrowed and never banished by this module.
Every returned `string`, `list`, `map` and `result` payload is freshly
allocated and owned by the caller, so release it with `banish` (and the
elements of a returned `list of string` individually) when it is no longer
needed. The `result` variants rebuild their container instead of returning a
parameter: `calling ok_of with v` / `calling err_of with e`.

## Design notes
- **Two answers per question.** The `maybe`/`bool` weaves answer "is it
  there?" and stay the right tool for that. The `*_result` weaves answer "it
  failed, and why", with `IoError` as the error type; they are built with
  `calling ok_of` / `calling err_of`.
- **No `+` on strings** (E0005): every composition uses `"{expr}"`
  interpolation, including the byte-count loops.
- **Directory entry names only.** `read_dir` mirrors the runtime primitive and
  returns bare names; `read_dir_full` is the convenience weave that joins each
  entry with the directory with `std.compass.join`.
- **Recursion is explicit.** `copy_tree`, `walk`, `find_dirs`,
  `list_files_recursive` and `dir_size` keep their own stack/list instead of
  calling themselves, which keeps the generated C flat.
- **Permissions are checked through `metadata`.** `is_readable`/`is_writable`
  require `exists and is_file` and then inspect the POSIX mode bits reported by
  `permissions` (read: `0400 | 0040 | 0004`, write: `0200 | 0020 | 0002`).
- **External `enchanting`.** The optional `enchanting compass.Path` block adds
  filesystem methods to `compass.Path`; it delegates through `self->raw` and
  never touches `std/compass.pengu`.
- **Internal tests without `std.ward`** (`ward` would create an import cycle):
  the `# --- Tests ---` section uses a private harness on top of `spark.panic`.

## Migration

`2.0.0` → `2.1.0` is additive: no symbol was removed, renamed or given new
bounds/behaviour.

| Added | Purpose |
|---|---|
| `read_text` / `write_text` | explicit aliases of `read_file` / `write_file` |
| `read_last_n_lines` | tail of a file, complementing `read_first_n_lines` |
| `read_dir_full` | `read_dir` entries already joined with the directory |
| `is_readable` / `is_writable` | existence + regular file + mode check |
| `read_lines_result`, `write_lines_result`, `read_dir_result`, `create_dir_result`, `remove_dir_result`, `copy_file_result`, `copy_tree_result`, `append_lines_result`, `touch_result`, `symlink_result`, `metadata_result` | `result of T to IoError` variants of the weaves above |
| `enchanting compass.Path` | `read_text`, `write_text`, `read_lines`, `append_text`, `delete`, `mkdir`, `rmdir`, `iter_dir`, `stat` |

---

### `ARCHIVUM_VERSION`

> **ARCHIVUM_VERSION** : string

 Module version identifier for std.archivum.

### `pengu_c_archivum_read_file`

> **pengu_c_archivum_read_file**(path: string) -> maybe string

 Runtime primitive: reads the whole file at `path` as UTF-8 text.

### `pengu_c_archivum_write_file`

> **pengu_c_archivum_write_file**(path: string, content: string) -> bool

 Runtime primitive: writes `content` to `path`, truncating any existing file.

### `pengu_c_archivum_append_file`

> **pengu_c_archivum_append_file**(path: string, content: string) -> bool

 Runtime primitive: appends `content` to `path`, creating it when missing.

### `pengu_c_archivum_delete_file`

> **pengu_c_archivum_delete_file**(path: string) -> bool

 Runtime primitive: deletes the entry at `path`.

### `pengu_c_archivum_exists`

> **pengu_c_archivum_exists**(path: string) -> bool

 Runtime primitive: true when an entry exists at `path`.

### `pengu_c_archivum_is_file`

> **pengu_c_archivum_is_file**(path: string) -> bool

 Runtime primitive: true when `path` is a regular file.

### `pengu_c_archivum_is_dir`

> **pengu_c_archivum_is_dir**(path: string) -> bool

 Runtime primitive: true when `path` is a directory.

### `pengu_c_archivum_is_symlink`

> **pengu_c_archivum_is_symlink**(path: string) -> bool

 Runtime primitive: true when `path` is a symbolic link.

### `pengu_c_archivum_create_dir`

> **pengu_c_archivum_create_dir**(path: string, parents: bool) -> bool

 Runtime primitive: creates the directory at `path`.

### `pengu_c_archivum_remove_dir`

> **pengu_c_archivum_remove_dir**(path: string, recursive: bool) -> bool

 Runtime primitive: removes the directory at `path`.

### `pengu_c_archivum_read_dir`

> **pengu_c_archivum_read_dir**(path: string) -> maybe list of string

 Runtime primitive: lists the direct entry names of `path`.

### `pengu_c_archivum_copy_file`

> **pengu_c_archivum_copy_file**(src: string, dst: string, overwrite: bool) -> bool

 Runtime primitive: copies file `src` to `dst`.

### `pengu_c_archivum_move_file`

> **pengu_c_archivum_move_file**(src: string, dst: string, overwrite: bool) -> bool

 Runtime primitive: moves file `src` to `dst`.

### `pengu_c_archivum_rename`

> **pengu_c_archivum_rename**(old: string, new: string) -> bool

 Runtime primitive: renames entry `old` to `new`.

### `pengu_c_archivum_metadata`

> **pengu_c_archivum_metadata**(path: string) -> maybe map of string to string

 Runtime primitive: stat()es `path` into an owned map of string to string.

### `pengu_c_archivum_glob`

> **pengu_c_archivum_glob**(pattern: string) -> list of string

 Runtime primitive: globs `pattern` from the working directory.

### `pengu_c_archivum_walk`

> **pengu_c_archivum_walk**(root: string) -> list of list of string

 Runtime primitive: walks `root` depth-first into an owned nested list.

### `pengu_c_archivum_touch`

> **pengu_c_archivum_touch**(path: string) -> bool

 Runtime primitive: updates modification time of `path`.

### `pengu_c_archivum_symlink`

> **pengu_c_archivum_symlink**(target: string, link: string) -> bool

 Runtime primitive: creates symbolic link `link` pointing at `target`.

### `pengu_c_archivum_read_symlink`

> **pengu_c_archivum_read_symlink**(path: string) -> maybe string

 Runtime primitive: resolves the target of the symlink at `path`.

### `pengu_c_archivum_realpath`

> **pengu_c_archivum_realpath**(path: string) -> maybe string

 Runtime primitive: canonicalizes `path` to an absolute path.

### `_copy_string`

> **_copy_string**(s: string) -> string

 Returns a fresh owned copy of `s` (`pengu_string_copy` without a public symbol).

 ## Motivo
 `pengu_string_split` returns a list whose elements are *views* into the source
 buffer, so a split result cannot outlive the string it came from. The line
 readers need owned elements in order to release the file text they read; this
 bridge deep-copies one view without adding a public `declare` for the runtime
 primitive (which `std/filum.pengu` already owns).

 ## Memoria
 Allocates one owned buffer and returns it; the caller releases it with
 `banish`. The input `s` is borrowed and never freed.

### `_join_lines`

> **_join_lines**(lines: list of string) -> string

 Joins `lines` with "\n" and appends one trailing "\n".

 ## Motivo
 The PenguScript spelling of a linear join (`for x in lines: out = "{out}{x}"`)
 is quadratic and leaks the accumulator on every step. This block sums the
 lengths, allocates the result once and `memcpy`s each piece, so the cost is
 linear and the copy is binary-exact (embedded NULs survive, matching
 `pengu_string_format_ex`).

 ## Memoria
 Allocates one owned buffer of exactly the joined length (plus the NUL) and
 returns it; the caller releases it with `banish`. The input list and its
 strings are only read, never retained.

### `read_file`

> **read_file**(path: string) -> maybe string

 Reads the whole file at `path` as UTF-8 text.

 ## Parámetros
 - `path`: the file to read. It is borrowed, not consumed.

 ## Retorno
 `some` with the owned file text, or `maybe none` when the file is missing or
 cannot be read. Release the text with `banish` when it is an owned copy.

 ## Ejemplo
 ```pengu
 let text as maybe string is calling archivum.read_file with "notes.txt"
 ```

### `read_text`

> **read_text**(path: string) -> maybe string

 Reads the whole file at `path` as UTF-8 text (alias of `read_file`).

 ## Parámetros
 - `path`: the file to read. It is borrowed, not consumed.

 ## Retorno
 `some` with the owned text, or `maybe none` on failure.

 ## Ejemplo
 ```pengu
 let text as maybe string is calling archivum.read_text with "notes.txt"
 ```

### `read_bytes`

> **read_bytes**(path: string) -> maybe string

 Reads file bytes as an owned string buffer. Alias of read_file.

 ## Parámetros
 - `path`: the file to read. It is borrowed, not consumed.

 ## Retorno
 `some` with the owned byte buffer, or `maybe none` on failure. No UTF-8
 decoding is performed; the buffer is the raw bytes.

 ## Ejemplo
 ```pengu
 let data as maybe string is calling archivum.read_bytes with "logo.png"
 ```

### `write_file`

> **write_file**(path: string, content: string) -> bool

 Writes `content` verbatim to `path`, creating or truncating the file. Returns true on success.

 ## Parámetros
 - `path`: destination file. Missing parent directories are not created.
 - `content`: the exact text to store. It is borrowed.

 ## Retorno
 `true` when the runtime wrote the file, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling archivum.write_file with "notes.txt", "hello"
 ```

### `write_text`

> **write_text**(path: string, content: string) -> bool

 Writes `content` verbatim to `path` (alias of `write_file`).

 ## Parámetros
 - `path`: destination file.
 - `content`: the exact text to store. It is borrowed.

 ## Retorno
 `true` on success, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling archivum.write_text with "notes.txt", "hello"
 ```

### `write_bytes`

> **write_bytes**(path: string, data: string) -> bool

 Writes binary data buffer to `path`. Alias of write_file.

 ## Parámetros
 - `path`: destination file.
 - `data`: the raw bytes to store. It is borrowed.

 ## Retorno
 `true` on success, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling archivum.write_bytes with "blob.bin", payload
 ```

### `IoError`

> omen IoError

```pengu
    NotFound
    IsADirectory
    NotAFile
    Permission
    Unknown
```

 Cause of an I/O failure, used as the error type of the `*_result` weaves.

### `read_file_result`

> **read_file_result**(path: string) -> result of string to IoError

 Reads the whole file at `path` as UTF-8, reporting the failure cause.

 ## Parámetros
 - `path`: the file to read. It is borrowed, not consumed.

 ## Retorno
 `ok` with the owned text, or `err` with the `IoError` cause. The result owns
 its payload; release it with `banish` when it is a `string`.

 ## Efectos
 Returns `err(IoError.IsADirectory)` for a directory, `err(IoError.NotFound)`
 when the entry does not exist and `err(IoError.Unknown)` for any other
 failure.

 ## Ejemplo
 ```pengu
 let r as result of string to archivum.IoError is calling archivum.read_file_result with "notes.txt"
 ```

### `write_file_result`

> **write_file_result**(path: string, content: string) -> result of int to IoError

 Writes `content` to `path`, reporting the failure cause. `result of int to
 IoError` succeeds with 0 (bytes written is not exposed by the runtime).

 ## Parámetros
 - `path`: destination file. It is borrowed, not consumed.
 - `content`: the exact text to store. It is borrowed.

 ## Retorno
 `ok(0)` on success, or `err` with the `IoError` cause.

 ## Efectos
 Returns `err(IoError.IsADirectory)` when `path` names a directory and
 `err(IoError.Unknown)` for any other write failure.

 ## Ejemplo
 ```pengu
 let r as result of int to archivum.IoError is calling archivum.write_file_result with "notes.txt", "hi"
 ```

### `delete_file_result`

> **delete_file_result**(path: string) -> result of int to IoError

 Deletes the entry at `path`, reporting the failure cause.

 ## Parámetros
 - `path`: the entry to delete. It is borrowed, not consumed.

 ## Retorno
 `ok(0)` on success, or `err` with the `IoError` cause.

 ## Efectos
 Returns `err(IoError.NotFound)` when the entry does not exist,
 `err(IoError.IsADirectory)` for a directory and `err(IoError.Unknown)`
 otherwise.

 ## Ejemplo
 ```pengu
 let r as result of int to archivum.IoError is calling archivum.delete_file_result with "notes.txt"
 ```

### `describe_error`

> **describe_error**(e: IoError) -> string

 Returns the human-readable message of an `IoError`.

 ## Parámetros
 - `e`: the error value to describe. It is a value type, copied in.

 ## Retorno
 An owned `string` with a short English message; release it with `banish`. The
 text is the same for every platform.

 ## Ejemplo
 ```pengu
 calling archivum.describe_error with archivum.IoError.NotFound     # "no such file or directory"
 ```

### `append_file`

> **append_file**(path: string, content: string) -> bool

 Appends `content` to the end of `path`, creating it when missing. Returns true on success.

 ## Parámetros
 - `path`: destination file.
 - `content`: the exact text to append. It is borrowed.

 ## Retorno
 `true` when the runtime appended the text, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling archivum.append_file with "notes.txt", "more\n"
 ```

### `append_bytes`

> **append_bytes**(path: string, data: string) -> bool

 Appends binary data buffer to `path`. Alias of append_file.

 ## Parámetros
 - `path`: destination file.
 - `data`: the raw bytes to append. It is borrowed.

 ## Retorno
 `true` on success, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling archivum.append_bytes with "blob.bin", extra
 ```

### `delete_file`

> **delete_file**(path: string) -> bool

 Deletes the entry (file, empty dir or symlink) at `path`. Returns true on success.

 ## Parámetros
 - `path`: the entry to delete. It is borrowed, not consumed.

 ## Retorno
 `true` when the runtime removed the entry, `false` otherwise. Use `remove_dir`
 for a non-empty directory.

 ## Ejemplo
 ```pengu
 calling archivum.delete_file with "notes.txt"
 ```

### `exists`

> **exists**(path: string) -> bool

 Returns true when any file system entry exists at `path`.

 ## Parámetros
 - `path`: the path to probe. It is borrowed, not consumed.

 ## Retorno
 `true` for a file, directory or symlink; `false` when nothing is there.

 ## Ejemplo
 ```pengu
 calling archivum.exists with "notes.txt"     # true
 ```

### `is_file`

> **is_file**(path: string) -> bool

 Returns true when the entry at `path` is a regular file.

 ## Parámetros
 - `path`: the path to probe. It is borrowed, not consumed.

 ## Retorno
 `true` only for a regular file; `false` for a directory, a symlink to a
 directory or a missing path.

 ## Ejemplo
 ```pengu
 calling archivum.is_file with "notes.txt"     # true
 ```

### `is_dir`

> **is_dir**(path: string) -> bool

 Returns true when the entry at `path` is a directory.

 ## Parámetros
 - `path`: the path to probe. It is borrowed, not consumed.

 ## Retorno
 `true` only for a directory; `false` otherwise.

 ## Ejemplo
 ```pengu
 calling archivum.is_dir with "/tmp"     # true
 ```

### `is_symlink`

> **is_symlink**(path: string) -> bool

 Returns true when the entry at `path` is a symbolic link.

 ## Parámetros
 - `path`: the path to probe. It is borrowed, not consumed.

 ## Retorno
 `true` when the entry itself is a symlink (the link is not followed).

 ## Ejemplo
 ```pengu
 calling archivum.is_symlink with "latest"     # true
 ```

### `is_readable`

> **is_readable**(path: string) -> bool

 Returns true when `path` exists, is a regular file and carries read permission.

 ## Parámetros
 - `path`: the file to probe. It is borrowed, not consumed.

 ## Retorno
 `true` when the entry exists, is a regular file and its POSIX mode has at
 least one read bit (`0400`, `0040` or `0004`); `false` otherwise.

 ## Efectos
 The check is advisory: it reads the mode bits reported by `metadata`, so an
 access-control list or a read-only mount can still deny the actual read.

 ## Ejemplo
 ```pengu
 calling archivum.is_readable with "notes.txt"     # true
 ```

### `is_writable`

> **is_writable**(path: string) -> bool

 Returns true when `path` exists, is a regular file and carries write permission.

 ## Parámetros
 - `path`: the file to probe. It is borrowed, not consumed.

 ## Retorno
 `true` when the entry exists, is a regular file and its POSIX mode has at
 least one write bit (`0200`, `0020` or `0002`); `false` otherwise.

 ## Efectos
 The check is advisory, like `is_readable`: a read-only mount can still deny
 the actual write.

 ## Ejemplo
 ```pengu
 calling archivum.is_writable with "notes.txt"     # true
 ```

### `create_dir`

> **create_dir**(path: string, parents: bool) -> bool

 Creates the directory at `path`. When `parents` is true, creates missing ancestors.

 ## Parámetros
 - `path`: the directory to create. It is borrowed, not consumed.
 - `parents`: when `true`, missing ancestors are created as well (default
   `false`).

 ## Retorno
 `true` when the directory exists after the call, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling archivum.create_dir with "/tmp/a/b", true
 ```

### `remove_dir`

> **remove_dir**(path: string, recursive: bool) -> bool

 Removes directory at `path`. When `recursive` is true, deletes directory and its contents.

 ## Parámetros
 - `path`: the directory to remove. It is borrowed, not consumed.
 - `recursive`: when `true`, the directory is deleted with all of its contents
   (default `false`).

 ## Retorno
 `true` when the runtime removed the directory, `false` otherwise.

 ## Efectos
 With `recursive` the deletion is immediate and irreversible; there is no
 trash can.

 ## Ejemplo
 ```pengu
 calling archivum.remove_dir with "/tmp/a", true
 ```

### `read_dir`

> **read_dir**(path: string) -> maybe list of string

 Lists the direct entry names inside `path` (excluding "." and "..").

 ## Parámetros
 - `path`: the directory to list. It is borrowed, not consumed.

 ## Retorno
 `some` with an owned `list of string` of bare entry names, or `maybe none`
 when `path` is not a readable directory. Release the list and its elements
 with `banish`.

 ## Ejemplo
 ```pengu
 let names as maybe list of string is calling archivum.read_dir with "/tmp"
 ```

### `read_dir_full`

> **read_dir_full**(path: string) -> list of string

 Lists the direct entries inside `path` with `path` joined to each name.

 ## Parámetros
 - `path`: the directory to list. It is borrowed, not consumed.

 ## Retorno
 A new owned `list of string`; it is empty when `path` is not a readable
 directory. Each element is `calling compass.join` of `path` and the entry
 name, so it can be passed straight back to `is_file`, `metadata`, etc.
 Release the list and its elements with `banish`.

 ## Memoria
 The list owns both its element buffer and the freshly joined strings.

 ## Ejemplo
 ```pengu
 let paths as list of string is calling archivum.read_dir_full with "/tmp"
 ```

### `copy_file`

> **copy_file**(src: string, dst: string, overwrite: bool) -> bool

 Copies file `src` to `dst`. When `overwrite` is false, an existing `dst` makes copy fail.

 ## Parámetros
 - `src`: the source file. It is borrowed, not consumed.
 - `dst`: the destination file. It is borrowed, not consumed.
 - `overwrite`: when `true`, an existing `dst` is replaced (default `false`).

 ## Retorno
 `true` when the runtime copied the file, `false` otherwise. The directory tree
 is never created: the parent of `dst` must exist.

 ## Ejemplo
 ```pengu
 calling archivum.copy_file with "a.txt", "b.txt", true
 ```

### `move_file`

> **move_file**(src: string, dst: string, overwrite: bool) -> bool

 Moves file `src` to `dst`. When `overwrite` is false, an existing `dst` makes move fail.

 ## Parámetros
 - `src`: the source file. It is borrowed, not consumed.
 - `dst`: the destination file. It is borrowed, not consumed.
 - `overwrite`: when `true`, an existing `dst` is replaced (default `false`).

 ## Retorno
 `true` when the runtime moved the file, `false` otherwise. A cross-device move
 is reported as a plain failure.

 ## Ejemplo
 ```pengu
 calling archivum.move_file with "a.txt", "b.txt", false
 ```

### `rename`

> **rename**(old: string, new: string) -> bool

 Renames entry `old` to `new` (an existing `new` is overwritten).

 ## Parámetros
 - `old`: the current path. It is borrowed, not consumed.
 - `new`: the new path. It is borrowed, not consumed.

 ## Retorno
 `true` when the runtime renamed the entry, `false` otherwise. Unlike
 `move_file`, an existing `new` is overwritten unconditionally.

 ## Ejemplo
 ```pengu
 calling archivum.rename with "a.txt", "b.txt"
 ```

### `metadata`

> **metadata**(path: string) -> maybe map of string to string

 Reads metadata of entry `path` into an owned map of string to string.

 ## Parámetros
 - `path`: the entry to stat. It is borrowed, not consumed.

 ## Retorno
 `some` with an owned map of `string` to `string`, or `maybe none` when the
 entry does not exist or `stat` fails. Contract of the returned map keys:
 - "size": decimal string of file size in bytes (e.g. "1024").
 - "is_file": boolean string ("true" or "false").
 - "is_dir": boolean string ("true" or "false").
 - "is_symlink": boolean string ("true" or "false").
 - "modified": decimal string of Unix epoch timestamp in seconds (e.g. "1790346624").
 - "created": decimal string of Unix epoch timestamp in seconds.
 - "accessed": decimal string of Unix epoch timestamp in seconds.
 - "permissions": decimal string of POSIX permission mode bits (st_mode & 0777).

 ## Memoria
 The map and its key/value strings are owned by the caller. `banish` on the
 `maybe` frees the entry table only, so walk the map (`for k in md`), `banish`
 each key and its `md.get` value, and then `banish` the wrapper.

 ## Ejemplo
 ```pengu
 let md as maybe map of string to string is calling archivum.metadata with "notes.txt"
 ```

### `read_lines`

> **read_lines**(path: string) -> maybe list of string

 Reads file and splits text on newline into an owned list of lines.

 ## Parámetros
 - `path`: the file to read. It is borrowed, not consumed.

 ## Retorno
 `some` with an owned `list of string`, or `maybe none` when the file cannot be
 read. The split is on "\n" only, so a trailing newline yields a final empty
 element and "\r\n" keeps the "\r". Release the list and its elements with
 `banish`.

 ## Ejemplo
 ```pengu
 let lines as maybe list of string is calling archivum.read_lines with "notes.txt"
 ```

### `read_first_n_lines`

> **read_first_n_lines**(path: string, n: int) -> maybe list of string

 Reads at most `n` lines from `path`.

 ## Parámetros
 - `path`: the file to read. It is borrowed, not consumed.
 - `n`: maximum number of lines to take. A non-positive `n` gives an empty
   list.

 ## Retorno
 `some` with an owned `list of string` of up to `n` leading lines, or
 `maybe none` when the file cannot be read.

 ## Ejemplo
 ```pengu
 let head as maybe list of string is calling archivum.read_first_n_lines with "notes.txt", 3
 ```

### `read_last_n_lines`

> **read_last_n_lines**(path: string, n: int) -> maybe list of string

 Reads the last `n` lines of `path`.

 ## Parámetros
 - `path`: the file to read. It is borrowed, not consumed.
 - `n`: maximum number of trailing lines to take. A non-positive `n` gives an
   empty list; when the file has fewer than `n` lines, every line is returned.

 ## Retorno
 `some` with an owned `list of string` of at most `n` trailing elements, or
 `maybe none` when the file cannot be read. The semantics mirror `read_lines`:
 the split is on "\n" and a trailing newline counts as one more (empty) line.

 ## Ejemplo
 ```pengu
 let tail as maybe list of string is calling archivum.read_last_n_lines with "notes.txt", 2
 ```

### `count_lines`

> **count_lines**(path: string) -> maybe int

 Returns the total number of lines in file `path`.

 ## Parámetros
 - `path`: the file to measure. It is borrowed, not consumed.

 ## Retorno
 `some` with the number of "\n"-separated elements, or `maybe none` when the
 file cannot be read. A file ending in a newline therefore counts one extra
 empty line, matching `read_lines`.

 ## Ejemplo
 ```pengu
 let total as maybe int is calling archivum.count_lines with "notes.txt"
 ```

### `write_lines`

> **write_lines**(path: string, lines: list of string) -> bool

 Joins `lines` with "\n", appends a trailing "\n", and writes to `path`.

 ## Parámetros
 - `path`: destination file.
 - `lines`: the lines to store. The list is borrowed, not consumed.

 ## Retorno
 `true` on success, `false` otherwise. An empty list writes a single "\n".

 ## Ejemplo
 ```pengu
 calling archivum.write_lines with "notes.txt", ["a", "b"]
 ```

### `append_lines`

> **append_lines**(path: string, lines: list of string) -> bool

 Joins `lines` with "\n", appends a trailing "\n", and appends to `path`.

 ## Parámetros
 - `path`: destination file; it is created when missing.
 - `lines`: the lines to append. The list is borrowed, not consumed.

 ## Retorno
 `true` on success, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling archivum.append_lines with "notes.txt", ["c"]
 ```

### `read_lines_result`

> **read_lines_result**(path: string) -> result of list of string to IoError

 Reads file and splits text on newline, reporting the failure cause.

 ## Parámetros
 - `path`: the file to read. It is borrowed, not consumed.

 ## Retorno
 `ok` with the owned `list of string`, or `err` with the `IoError` cause.

 ## Efectos
 Returns `err(IoError.IsADirectory)` for a directory and
 `err(IoError.Unknown)` for any other read failure.

 ## Ejemplo
 ```pengu
 let r as result of list of string to archivum.IoError is calling archivum.read_lines_result with "notes.txt"
 ```

### `write_lines_result`

> **write_lines_result**(path: string, lines: list of string) -> result of int to IoError

 Writes `lines` joined by "\n" with a trailing "\n", reporting the failure cause.

 ## Parámetros
 - `path`: destination file. It is borrowed, not consumed.
 - `lines`: the lines to store. The list is borrowed, not consumed.

 ## Retorno
 `ok(0)` on success, or `err` with the `IoError` cause.

 ## Efectos
 Inherits the cause reported by `write_file_result`
 (`err(IoError.IsADirectory)` for a directory, `err(IoError.Unknown)`
 otherwise).

 ## Ejemplo
 ```pengu
 let r as result of int to archivum.IoError is calling archivum.write_lines_result with "notes.txt", ["a"]
 ```

### `append_lines_result`

> **append_lines_result**(path: string, lines: list of string) -> result of int to IoError

 Appends `lines` joined by "\n" with a trailing "\n", reporting the failure cause.

 ## Parámetros
 - `path`: destination file. It is borrowed, not consumed.
 - `lines`: the lines to append. The list is borrowed, not consumed.

 ## Retorno
 `ok(0)` on success, or `err` with the `IoError` cause.

 ## Efectos
 Returns `err(IoError.IsADirectory)` when `path` is a directory and
 `err(IoError.Unknown)` for any other append failure.

 ## Ejemplo
 ```pengu
 let r as result of int to archivum.IoError is calling archivum.append_lines_result with "notes.txt", ["b"]
 ```

### `read_dir_result`

> **read_dir_result**(path: string) -> result of list of string to IoError

 Lists the direct entry names inside `path`, reporting the failure cause.

 ## Parámetros
 - `path`: the directory to list. It is borrowed, not consumed.

 ## Retorno
 `ok` with the owned `list of string` of bare entry names, or `err` with the
 `IoError` cause.

 ## Efectos
 Returns `err(IoError.NotFound)` when `path` does not exist and
 `err(IoError.NotAFile)` when it exists but is not a directory.

 ## Ejemplo
 ```pengu
 let r as result of list of string to archivum.IoError is calling archivum.read_dir_result with "/tmp"
 ```

### `create_dir_result`

> **create_dir_result**(path: string, parents: bool) -> result of bool to IoError

 Creates the directory at `path`, reporting the failure cause.

 ## Parámetros
 - `path`: the directory to create. It is borrowed, not consumed.
 - `parents`: when `true`, missing ancestors are created as well (default
   `false`).

 ## Retorno
 `ok(true)` when the directory exists after the call, or `err` with the
 `IoError` cause.

 ## Efectos
 Returns `err(IoError.IsADirectory)` when a regular file already occupies
 `path` and `err(IoError.Unknown)` for any other failure.

 ## Ejemplo
 ```pengu
 let r as result of bool to archivum.IoError is calling archivum.create_dir_result with "/tmp/a", true
 ```

### `remove_dir_result`

> **remove_dir_result**(path: string, recursive: bool) -> result of bool to IoError

 Removes the directory at `path`, reporting the failure cause.

 ## Parámetros
 - `path`: the directory to remove. It is borrowed, not consumed.
 - `recursive`: when `true`, the contents are removed as well (default
   `false`).

 ## Retorno
 `ok(true)` on success, or `err` with the `IoError` cause.

 ## Efectos
 Returns `err(IoError.NotFound)` when `path` does not exist,
 `err(IoError.NotAFile)` when it exists but is not a directory and
 `err(IoError.Unknown)` for any other failure (for example a non-empty
 directory with `recursive` false).

 ## Ejemplo
 ```pengu
 let r as result of bool to archivum.IoError is calling archivum.remove_dir_result with "/tmp/a", true
 ```

### `copy_file_result`

> **copy_file_result**(src: string, dst: string, overwrite: bool) -> result of bool to IoError

 Copies file `src` to `dst`, reporting the failure cause.

 ## Parámetros
 - `src`: the source file. It is borrowed, not consumed.
 - `dst`: the destination file. It is borrowed, not consumed.
 - `overwrite`: when `false`, an existing `dst` makes the copy fail (default
   `false`).

 ## Retorno
 `ok(true)` on success, or `err` with the `IoError` cause.

 ## Efectos
 Returns `err(IoError.NotFound)` when `src` does not exist,
 `err(IoError.IsADirectory)` when `src` is a directory and
 `err(IoError.Unknown)` otherwise.

 ## Ejemplo
 ```pengu
 let r as result of bool to archivum.IoError is calling archivum.copy_file_result with "a.txt", "b.txt"
 ```

### `copy_tree_result`

> **copy_tree_result**(src: string, dst: string) -> result of bool to IoError

 Recursively copies a directory tree from `src` to `dst`, reporting the failure
 cause.

 ## Parámetros
 - `src`: the source directory. It is borrowed, not consumed.
 - `dst`: the destination directory. It is borrowed, not consumed.

 ## Retorno
 `ok(true)` on success, or `err` with the `IoError` cause.

 ## Efectos
 Returns `err(IoError.NotFound)` when `src` does not exist,
 `err(IoError.IsADirectory)` when `src` exists but is a regular file and
 `err(IoError.Unknown)` otherwise. The copy is non-transactional, exactly like
 `copy_tree`.

 ## Ejemplo
 ```pengu
 let r as result of bool to archivum.IoError is calling archivum.copy_tree_result with "src_dir", "dst_dir"
 ```

### `touch_result`

> **touch_result**(path: string) -> result of bool to IoError

 Updates the modification time of `path` to now, reporting the failure cause.

 ## Parámetros
 - `path`: the entry to touch. It is borrowed, not consumed.

 ## Retorno
 `ok(true)` on success, or `err` with the `IoError` cause.

 ## Efectos
 Returns `err(IoError.IsADirectory)` when `path` is a directory and
 `err(IoError.Unknown)` for any other failure.

 ## Ejemplo
 ```pengu
 let r as result of bool to archivum.IoError is calling archivum.touch_result with "notes.txt"
 ```

### `symlink_result`

> **symlink_result**(target: string, link: string) -> result of bool to IoError

 Creates symbolic link `link` pointing at `target`, reporting the failure cause.

 ## Parámetros
 - `target`: the link target. It is borrowed, not consumed and need not exist.
 - `link`: the link path to create. It is borrowed, not consumed.

 ## Retorno
 `ok(true)` on success, or `err` with the `IoError` cause.

 ## Efectos
 Returns `err(IoError.Unknown)` when the runtime cannot create the link (for
 example an existing `link`).

 ## Ejemplo
 ```pengu
 let r as result of bool to archivum.IoError is calling archivum.symlink_result with "a.txt", "latest"
 ```

### `metadata_result`

> **metadata_result**(path: string) -> result of map of string to string to IoError

 Reads metadata of entry `path`, reporting the failure cause.

 ## Parámetros
 - `path`: the entry to stat. It is borrowed, not consumed.

 ## Retorno
 `ok` with the owned map (same keys as `metadata`), or `err` with the
 `IoError` cause. The map and its strings are owned by the caller.

 ## Efectos
 Returns `err(IoError.NotFound)` when `path` does not exist and
 `err(IoError.Unknown)` for any other `stat` failure.

 ## Ejemplo
 ```pengu
 let r as result of map of string to string to archivum.IoError is calling archivum.metadata_result with "notes.txt"
 ```

### `glob`

> **glob**(pattern: string) -> list of string

 Globs `pattern` starting from the working directory.

 Paths are collected from the working directory downwards and reported as
 `./<relative path>`, so an absolute `pattern` (one starting with `/`) never
 matches.

 ## Parámetros
 - `pattern`: the pattern to match. `*` or `**` alone matches every entry,
   `*.ext` matches by extension, and any other text matches as a substring of
   the `./<relative path>` or exactly the entry name. `?` is **not** a
   wildcard.

 ## Retorno
 A new owned `list of string` of matching paths, empty when nothing matches.
 Release the list and its elements with `banish`.

 ## Ejemplo
 ```pengu
 let found as list of string is calling archivum.glob with "*.txt"
 ```

### `walk`

> **walk**(root: string) -> list of list of string

 Walks `root` depth-first and returns an owned nested list.

 ## Parámetros
 - `root`: the directory to walk. It is borrowed, not consumed.

 ## Retorno
 A new owned `list of list of string`; each inner list starts with the
 directory it describes followed by that directory's direct entry names (no
 paths, only basenames). The first inner list describes `root`, and each
 subdirectory then contributes its own inner list in depth-first order, so
 `walk` is not a level-by-level traversal. The outer list is empty when `root`
 is not a directory. Release the nested buffers with `banish`.

 ## Ejemplo
 ```pengu
 let levels as list of list of string is calling archivum.walk with "/tmp"
 ```

### `touch`

> **touch**(path: string) -> bool

 Updates modification time of `path` to now, creating an empty file when missing.

 ## Parámetros
 - `path`: the entry to touch. It is borrowed, not consumed.

 ## Retorno
 `true` when the timestamp was updated, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling archivum.touch with "notes.txt"
 ```

### `symlink`

> **symlink**(target: string, link: string) -> bool

 Creates symbolic link `link` pointing at `target`.

 ## Parámetros
 - `target`: the link target. It is borrowed and need not exist.
 - `link`: the link path to create. It is borrowed.

 ## Retorno
 `true` when the link was created, `false` otherwise (for example an existing
 `link`).

 ## Ejemplo
 ```pengu
 calling archivum.symlink with "a.txt", "latest"
 ```

### `read_symlink`

> **read_symlink**(path: string) -> maybe string

 Reads target of symbolic link at `path`.

 ## Parámetros
 - `path`: the symlink to read. It is borrowed, not consumed.

 ## Retorno
 `some` with the owned link target (relative targets stay relative), or
 `maybe none` when `path` is not a symlink.

 ## Ejemplo
 ```pengu
 let target as maybe string is calling archivum.read_symlink with "latest"
 ```

### `realpath`

> **realpath**(path: string) -> maybe string

 Resolves `path` to a canonical absolute path.

 ## Parámetros
 - `path`: the path to resolve. It is borrowed, not consumed.

 ## Retorno
 `some` with the owned absolute path (symlinks and "." / ".." resolved), or
 `maybe none` when the entry does not exist.

 ## Ejemplo
 ```pengu
 let abs_path as maybe string is calling archivum.realpath with "notes.txt"
 ```

### `_release_metadata`

> **_release_metadata**(m: maybe map of string to string) -> void

 Releases every key/value string of a metadata map, then the map and its
 `maybe` wrapper.

 `pengu_c_archivum_metadata` builds 8 owned keys and 8 owned values with
 `pengu_string_new` and stores them in a map that keeps only the *bytes* of the
 `PenguString` header.  `banish m` on the wrapper frees the entry cells but not
 the 16 payload buffers, so a consumer that only reads one key must walk the
 map and release every key and value explicitly.

### `_metadata_int`

> **_metadata_int**(path: string, key: string) -> maybe int

 Returns the `int` stored under `key` in metadata `md`, or `maybe none`.

### `_has_mode_bit`

> **_has_mode_bit**(path: string, mask: int) -> bool

 True when `path` is a regular file whose mode has any bit of `mask` set.

### `_missing_dir_error`

> **_missing_dir_error**(path: string) -> IoError

 IoError for a path that should be a directory but is missing or not one.

### `file_size`

> **file_size**(path: string) -> maybe int

 Returns the size of file `path` in bytes, or none if file does not exist.

 ## Parámetros
 - `path`: the file to measure. It is borrowed, not consumed.

 ## Retorno
 `some` with the size from the "size" metadata key, or `maybe none` when the
 entry does not exist or the key is not a parseable integer.

 ## Ejemplo
 ```pengu
 let bytes as maybe int is calling archivum.file_size with "notes.txt"
 ```

### `dir_size`

> **dir_size**(path: string, recursive: bool) -> maybe int

 Returns the total size in bytes of files in directory `path`.

 ## Parámetros
 - `path`: the directory to measure. It is borrowed, not consumed.
 - `recursive`: when `true`, subdirectories are summed too (default `false`).

 ## Retorno
 `some` with the summed byte size of the regular files, or `maybe none` when
 `path` is not a directory. Empty files contribute 0; unreadable entries are
 skipped.

 ## Ejemplo
 ```pengu
 let total as maybe int is calling archivum.dir_size with "/tmp/a", true
 ```

### `modified_time`

> **modified_time**(path: string) -> maybe float

 Returns the last modification time of `path` as a Unix timestamp float.

 ## Parámetros
 - `path`: the entry to inspect. It is borrowed, not consumed.

 ## Retorno
 `some` with the "modified" epoch seconds converted to `float`, or
 `maybe none` when unavailable.

 ## Ejemplo
 ```pengu
 let t as maybe float is calling archivum.modified_time with "notes.txt"
 ```

### `created_time`

> **created_time**(path: string) -> maybe float

 Returns the creation time of `path` as a Unix timestamp float.

 ## Parámetros
 - `path`: the entry to inspect. It is borrowed, not consumed.

 ## Retorno
 `some` with the "created" epoch seconds converted to `float`, or
 `maybe none` when unavailable (some file systems do not record it).

 ## Ejemplo
 ```pengu
 let t as maybe float is calling archivum.created_time with "notes.txt"
 ```

### `accessed_time`

> **accessed_time**(path: string) -> maybe float

 Returns the last access time of `path` as a Unix timestamp float.

 ## Parámetros
 - `path`: the entry to inspect. It is borrowed, not consumed.

 ## Retorno
 `some` with the "accessed" epoch seconds converted to `float`, or
 `maybe none` when unavailable.

 ## Ejemplo
 ```pengu
 let t as maybe float is calling archivum.accessed_time with "notes.txt"
 ```

### `permissions`

> **permissions**(path: string) -> maybe int

 Returns the file mode/permissions of `path` as an octal integer mode.

 ## Parámetros
 - `path`: the entry to inspect. It is borrowed, not consumed.

 ## Retorno
 `some` with the decimal value of the POSIX mode bits (`st_mode & 0777`, so
 0644 is reported as 420), or `maybe none` when unavailable.

 ## Ejemplo
 ```pengu
 let mode as maybe int is calling archivum.permissions with "notes.txt"
 ```

### `is_empty_file`

> **is_empty_file**(path: string) -> bool

 True when `path` exists, is a regular file, and has a size of 0 bytes.

 ## Parámetros
 - `path`: the entry to probe. It is borrowed, not consumed.

 ## Retorno
 `true` only for an existing regular file of size 0; `false` for a directory,
 a missing path or a non-empty file.

 ## Ejemplo
 ```pengu
 calling archivum.is_empty_file with "empty.txt"     # true
 ```

### `is_empty_dir`

> **is_empty_dir**(path: string) -> bool

 True when `path` is an existing directory containing zero entries.

 ## Parámetros
 - `path`: the directory to probe. It is borrowed, not consumed.

 ## Retorno
 `true` only for an existing directory with no entries; `false` for a file, a
 missing path or a directory with at least one entry.

 ## Ejemplo
 ```pengu
 calling archivum.is_empty_dir with "/tmp/a"     # true
 ```

### `find_files`

> **find_files**(root: string, recursive: bool) -> list of string

 Returns list of all regular files in directory `root`.

 ## Parámetros
 - `root`: the directory to search. It is borrowed, not consumed.
 - `recursive`: when `true`, subdirectories are searched too (default `true`).

 ## Retorno
 A new owned `list of string` of file paths; empty when `root` is not a
 directory. Release the list and its elements with `banish`.

 ## Ejemplo
 ```pengu
 let files as list of string is calling archivum.find_files with "/tmp/a", true
 ```

### `find_dirs`

> **find_dirs**(root: string, recursive: bool) -> list of string

 Returns list of all subdirectories in directory `root`.

 ## Parámetros
 - `root`: the directory to search. It is borrowed, not consumed.
 - `recursive`: when `true`, subdirectories of subdirectories are included
   (default `true`). `root` itself is never included.

 ## Retorno
 A new owned `list of string` of directory paths; empty when there is none.

 ## Ejemplo
 ```pengu
 let dirs as list of string is calling archivum.find_dirs with "/tmp/a", true
 ```

### `find_by_name`

> **find_by_name**(root: string, target_name: string, recursive: bool) -> list of string

 Finds files under `root` whose basename exactly matches `target_name`.

 ## Parámetros
 - `root`: the directory to search. It is borrowed, not consumed.
 - `target_name`: the exact basename to match (case-sensitive).
 - `recursive`: when `true`, subdirectories are searched too (default `true`).

 ## Retorno
 A new owned `list of string` of matching file paths; empty when nothing
 matches. Release the list and its elements with `banish`.

 ## Ejemplo
 ```pengu
 let hits as list of string is calling archivum.find_by_name with "/tmp/a", "notes.txt"
 ```

### `find_by_ext`

> **find_by_ext**(root: string, extension: string, recursive: bool) -> list of string

 Finds files under `root` whose extension matches `extension` (e.g. ".log" or "log").

 ## Parámetros
 - `root`: the directory to search. It is borrowed, not consumed.
 - `extension`: the extension to match, with or without the leading dot
   (case-sensitive).
 - `recursive`: when `true`, subdirectories are searched too (default `true`).

 ## Retorno
 A new owned `list of string` of matching file paths; empty when nothing
 matches. Release the list and its elements with `banish`.

 ## Ejemplo
 ```pengu
 let logs as list of string is calling archivum.find_by_ext with "/tmp/a", ".log"
 ```

### `temp_dir`

> **temp_dir**() -> string

 Returns the system temporary directory path as a string.

 ## Retorno
 An owned `string` with the directory path: `$TEMP`/`$TMP` (or "C:\\Temp") on
 Windows, `$TMPDIR` (or "/tmp") elsewhere. The directory is not created here.

 ## Ejemplo
 ```pengu
 let tmp as string is calling archivum.temp_dir
 ```

### `temp_file`

> **temp_file**(prefix: string) -> string

 Generates a unique temporary file path within the system temporary directory.

 ## Parámetros
 - `prefix`: the filename prefix (default `"pengu"`).

 ## Retorno
 An owned `string` with the path of a not-yet-existing file. The file is *not*
 created; the caller decides what to write.

 ## Efectos
 The candidate name embeds the process id and a counter; after 10000 occupied
 candidates it falls back to `"{temp_dir}/{prefix}.tmp"` without checking.

 ## Ejemplo
 ```pengu
 let tmp_path as string is calling archivum.temp_file with "notes"
 ```

### `FsCopyTask`

> rune FsCopyTask

```pengu
    s as string
    d as string
```

 Internal record used by copy_tree to queue directory pairs.

### `copy_tree`

> **copy_tree**(src: string, dst: string) -> bool

 Recursively copies a directory tree from `src` to `dst`. Returns true on success.

 ## Parámetros
 - `src`: the source directory. It is borrowed, not consumed.
 - `dst`: the destination directory; it is created when missing.

 ## Retorno
 `true` when every entry was copied, `false` as soon as one step fails. An
 existing `dst` is merged into, and existing files are overwritten.

 ## Efectos
 Note: This operation is non-transactional; any partially created files or
 subdirectories remain on disk if a subsequent step encounters an error.
 Symlinks and special files are skipped.

 ## Ejemplo
 ```pengu
 calling archivum.copy_tree with "src_dir", "dst_dir"
 ```

### `list_files_recursive`

> **list_files_recursive**(root: string) -> list of string

 Recursively lists every file below root.

 ## Parámetros
 - `root`: the directory to scan. It is borrowed, not consumed.

 ## Retorno
 A new owned `list of string` with every regular file below `root` (in
 depth-first order, unlike `walk`); empty when there is none. Release the list
 and its elements with `banish`.

 ## Ejemplo
 ```pengu
 let files as list of string is calling archivum.list_files_recursive with "/tmp/a"
 ```

### `append_text`

> **append_text**(content: string) -> bool

 Appends `content` to this file, creating it when missing.

 ## Parámetros
 - `content`: the exact text to append. It is borrowed.

 ## Retorno
 `true` on success, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling p.append_text with "more\n"
 ```

### `delete`

> **delete**() -> bool

 Deletes the file, empty directory or symlink at this path.

 ## Retorno
 `true` on success, `false` otherwise. Use `rmdir` for a directory.

 ## Ejemplo
 ```pengu
 calling p.delete
 ```

### `mkdir`

> **mkdir**(parents: bool) -> bool

 Creates this directory.

 ## Parámetros
 - `parents`: when `true`, missing ancestors are created too (default
   `false`).

 ## Retorno
 `true` when the directory exists after the call, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling p.mkdir with true
 ```

### `rmdir`

> **rmdir**(recursive: bool) -> bool

 Removes this directory.

 ## Parámetros
 - `recursive`: when `true`, the contents are removed too (default `false`).

 ## Retorno
 `true` on success, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling p.rmdir with true
 ```

### `iter_dir`

> **iter_dir**() -> list of string

 Lists this directory's direct entries joined with the directory.

 ## Retorno
 A new owned `list of string`; empty when the directory cannot be read.

 ## Ejemplo
 ```pengu
 let entries as list of string is calling p.iter_dir
 ```

### `stat`

> **stat**() -> maybe map of string to string

 Reads the metadata map of this path.

 ## Retorno
 `some` with the owned map (same keys as `archivum.metadata`), or
 `maybe none` when `stat` fails.

 ## Ejemplo
 ```pengu
 let md as maybe map of string to string is calling p.stat
 ```

### `_arch_expect_int`

> **_arch_expect_int**(got: int, want: int, label: string) -> void

 Aborts the current test with `label` when `got != want`.

### `_arch_expect_str`

> **_arch_expect_str**(got: string, want: string, label: string) -> void

 Aborts the current test with `label` when `got != want`.

### `_arch_expect_true`

> **_arch_expect_true**(cond: bool, label: string) -> void

 Aborts the current test with `label` when `cond` is false.

### `_arch_path`

> **_arch_path**(base: string, name: string) -> string

 Joins `base` and `name` into a test path with the module separator.

### `_arch_fresh_dir`

> **_arch_fresh_dir**(base: string) -> string

 Removes any leftover `base` and recreates it empty; returns `base`.

### `_arch_cleanup`

> **_arch_cleanup**(base: string) -> void

 Removes the test directory `base` and everything below it.

### `_arch_base`

> **_arch_base**(name: string) -> string

 Builds the unique test directory `/tmp/pengu_arch_test_<pid>_<name>`.

### `"ARCHIVUM_VERSION is 2.14.0"`

> test "ARCHIVUM_VERSION is 2.14.0"

_Undocumented._

### `"write_file then read_file round-trips the content"`

> test "write_file then read_file round-trips the content"

_Undocumented._

### `"read_text and write_text alias read_file and write_file"`

> test "read_text and write_text alias read_file and write_file"

_Undocumented._

### `"append_file adds to the existing content"`

> test "append_file adds to the existing content"

_Undocumented._

### `"read_lines splits the file on newline"`

> test "read_lines splits the file on newline"

_Undocumented._

### `"read_first_n_lines takes the head"`

> test "read_first_n_lines takes the head"

_Undocumented._

### `"read_last_n_lines takes the tail"`

> test "read_last_n_lines takes the tail"

_Undocumented._

### `"count_lines counts the split elements"`

> test "count_lines counts the split elements"

_Undocumented._

### `"write_lines and append_lines add a trailing newline"`

> test "write_lines and append_lines add a trailing newline"

_Undocumented._

### `"exists and is_file and is_dir classify the entries"`

> test "exists and is_file and is_dir classify the entries"

_Undocumented._

### `"create_dir with parents builds nested directories"`

> test "create_dir with parents builds nested directories"

_Undocumented._

### `"remove_dir removes a tree recursively"`

> test "remove_dir removes a tree recursively"

_Undocumented._

### `"copy_file duplicates a file and copy_tree duplicates a tree"`

> test "copy_file duplicates a file and copy_tree duplicates a tree"

_Undocumented._

### `"move_file and rename relocate an entry"`

> test "move_file and rename relocate an entry"

_Undocumented._

### `"metadata reports the file size"`

> test "metadata reports the file size"

_Undocumented._

### `"is_empty_file distinguishes empty from non-empty"`

> test "is_empty_file distinguishes empty from non-empty"

_Undocumented._

### `"permissions are readable and writable for a fresh file"`

> test "permissions are readable and writable for a fresh file"

_Undocumented._

### `"is_readable and is_writable answer for files and missing paths"`

> test "is_readable and is_writable answer for files and missing paths"

_Undocumented._

### `"read_bytes and write_bytes round-trip a byte buffer"`

> test "read_bytes and write_bytes round-trip a byte buffer"

_Undocumented._

### `"touch creates a file and delete_file removes it"`

> test "touch creates a file and delete_file removes it"

_Undocumented._

### `"read_file_result is err for a missing file and ok for a present one"`

> test "read_file_result is err for a missing file and ok for a present one"

_Undocumented._

### `"the result variants report the ok path"`

> test "the result variants report the ok path"

_Undocumented._

### `"the result variants report the error path"`

> test "the result variants report the error path"

_Undocumented._

### `"describe_error names every IoError variant"`

> test "describe_error names every IoError variant"

_Undocumented._

### `"read_dir lists entries and read_dir_full joins them"`

> test "read_dir lists entries and read_dir_full joins them"

_Undocumented._

### `"find_files and find_dirs and find_by_name and find_by_ext"`

> test "find_files and find_dirs and find_by_name and find_by_ext"

_Undocumented._

### `"list_files_recursive and walk visit the tree"`

> test "list_files_recursive and walk visit the tree"

_Undocumented._

### `"glob finds the fixture inside its own directory"`

> test "glob finds the fixture inside its own directory"

_Undocumented._

### `"dir_size sums the top-level files"`

> test "dir_size sums the top-level files"

_Undocumented._

### `"time helpers read the metadata timestamps"`

> test "time helpers read the metadata timestamps"

_Undocumented._

### `"symlink and read_symlink work and realpath resolves"`

> test "symlink and read_symlink work and realpath resolves"

_Undocumented._

### `"temp_dir and temp_file name a usable location"`

> test "temp_dir and temp_file name a usable location"

_Undocumented._

### `"Path enchanting exposes the filesystem methods"`

> test "Path enchanting exposes the filesystem methods"

_Undocumented._

