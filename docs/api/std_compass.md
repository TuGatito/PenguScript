# std.compass

> Source: `std/compass.pengu`

std/compass.pengu — path manipulation: joining, splitting, normalizing and
querying filesystem paths.

The module owns the pure PenguScript half of path handling: separator and drive
detection, `basename`/`dirname`/`ext`/`stem`, normalization, joining, relative
paths, glob matching and the `Path` rune. The filesystem itself is reached only
through the five native `declare`s at the top of the file (`pengu_c_getcwd`,
`pengu_c_getenv`, `pengu_c_archivum_exists`, `pengu_c_archivum_is_file`,
`pengu_c_archivum_is_dir`); they are frozen and are provided by
`std.archivum`/`std.rites` in a later chunk. This file never touches
`pengu_runtime.h`.

## Example
```pengu
import std.spark

---

### `COMPASS_VERSION`

> **COMPASS_VERSION** : string

 Module version identifier for std.compass.

### `pengu_c_getcwd`

> **pengu_c_getcwd**() -> maybe string

 ----------------------------------------------------------------------------
 External C Runtime Declarations
 ----------------------------------------------------------------------------

### `pengu_c_getenv`

> **pengu_c_getenv**(name: string) -> maybe string

_Undocumented._

### `pengu_c_archivum_exists`

> **pengu_c_archivum_exists**(path: string) -> bool

_Undocumented._

### `pengu_c_archivum_is_file`

> **pengu_c_archivum_is_file**(path: string) -> bool

_Undocumented._

### `pengu_c_archivum_is_dir`

> **pengu_c_archivum_is_dir**(path: string) -> bool

_Undocumented._

### `cp_win`

> **cp_win**() -> bool

 Compile-time platform flag: true when `os` is "windows".

### `cp_is_sep`

> **cp_is_sep**(b: int) -> bool

 True when the byte `b` is a path separator: "/" (47) or a backslash (92).

 ## Memoria
 Allocates nothing. The byte is a plain integer, so a separator test no longer
 materialises a one-byte `path at i` string that nobody released.

### `cp_is_letter`

> **cp_is_letter**(b: int) -> bool

 True when the byte `b` is an ASCII letter (A-Z or a-z); detects Windows drive
 letters.

 ## Memoria
 Allocates nothing. The byte is a plain integer.

### `cp_sep`

> **cp_sep**() -> string

 Preferred separator for this platform: "\\" on Windows, "/" elsewhere.

### `cp_is_abs`

> **cp_is_abs**(path: string) -> bool

 True when `path` is absolute.

 ## Memoria
 Allocates nothing: the bytes are read through `bytes of`, never through
 `path at i` (which would heap-allocate a one-byte string per probe).

### `cp_is_root`

> **cp_is_root**(path: string) -> bool

 True when `path` is exactly a filesystem root.

 ## Memoria
 Allocates nothing; the probes read bytes through `bytes of`.

### `cp_drive`

> **cp_drive**(path: string) -> string

 Windows drive prefix of `path` (e.g. "C:"), or "" when there is none.

 ## Memoria
 Returns a fresh owned two-byte copy when a drive is present (release it with
 `banish`), or a borrowed empty view otherwise. Allocates at most once and
 never materialises the individual drive characters.

### `cp_basename`

> **cp_basename**(path: string) -> string

 Final component of `path`; "" when `path` is empty or only separators.

 ## Memoria
 Returns a fresh owned substring (release it with `banish`) or a borrowed empty
 view. Separator probes are allocation-free byte reads.

### `cp_dirname`

> **cp_dirname**(path: string) -> string

 Directory portion of `path` without a trailing separator; "" when there is none.

 ## Memoria
 Returns a fresh owned substring (release it with `banish`) or a borrowed empty
 view. All separator probes are allocation-free byte reads.

### `cp_ext`

> **cp_ext**(path: string) -> string

 Extension of the basename, dot included (e.g. ".txt"); "" when there is none.

 ## Memoria
 Returns a fresh owned substring (release it with `banish`) or a borrowed empty
 view; the dot scan is an allocation-free byte read.

### `cp_stem`

> **cp_stem**(path: string) -> string

 Basename without its final extension.

 ## Memoria
 Returns a fresh owned substring (release it with `banish`) or the owned
 basename itself when there is no extension. The intermediate basename is
 always released here; the dot scan allocates nothing.

### `cp_has_ext`

> **cp_has_ext**(path: string) -> bool

 True when the basename has an extension.

### `cp_has_suffix`

> **cp_has_suffix**(path: string, suffix: string) -> bool

 True when the tail of `path` equals `suffix`.

### `cp_suffixes`

> **cp_suffixes**(path: string) -> list of string

 Suffixes of the basename split at dots, e.g. "a.tar.gz" gives ["tar", "gz"].

 ## Memoria
 The returned list owns its element buffer and every pushed suffix (each a
 fresh substring). The basename itself is released here; the dot scan is an
 allocation-free byte read.

### `cp_normalize`

> **cp_normalize**(path: string) -> string

 Collapses redundant separators and resolves "." and ".." segments.

 ## Memoria
 Returns a fresh owned string (release it with `banish`) or the borrowed "."
 literal for an empty path. Every substring pushed as a segment is released
 here: "." is dropped, ".." that cancels a segment is dropped after the popped
 segment is freed, and the surviving stack entries are freed one by one before
 the result is returned. The accumulator always releases its previous buffer
 before being reassigned.

### `cp_parent`

> **cp_parent**(path: string) -> maybe string

 Parent directory of `path` as maybe string.

### `cp_split`

> **cp_split**(path: string) -> list of string

 Splits `path` into components: optional drive prefix, root separator and segments.

 ## Memoria
 The returned list owns its element buffer and every component it pushes (the
 drive prefix and the segments are fresh substrings; the root separator is a
 borrowed literal). The scan itself allocates nothing.

### `cp_join`

> **cp_join**(parts: list of string) -> string

 Joins `parts` with the platform separator and normalizes the result.

 ## Memoria
 Returns a fresh owned string (release it with `banish`) or a borrowed empty
 view for an empty list. `parts` and its elements are borrowed and never
 released. The accumulator copies each part instead of aliasing it, releases
 its previous buffer before every reassignment, and is released before the
 normalized result is returned.

### `cp_change_ext`

> **cp_change_ext**(path: string, new_ext: string) -> string

 Replaces the extension of `path` with `new_ext`.

 ## Memoria
 Returns a fresh owned string (release it with `banish`). The intermediate
 dirname/stem buffers are released here, and each accumulator reassignment
 releases the previous buffer before storing the replacement.

### `cp_add_ext`

> **cp_add_ext**(path: string, ext: string) -> string

 Appends `ext` to `path` only when `path` has no extension yet.

 ## Memoria
 Returns a fresh owned string when an extension was appended, or the borrowed
 `path` view otherwise; `banish` is safe either way. The leading-dot test is
 an allocation-free byte read.

### `cp_release_strings`

> **cp_release_strings**(xs: list of string) -> void

 Releases every owned element of `xs`; the element buffer itself stays with the
 caller, who still owns it and must `banish` it separately.

 ## Memoria
 Frees the element payloads exactly once; `banish` is a no-op on borrowed
 elements (the root separators pushed by `cp_split`, for instance).

### `cp_relative_to`

> **cp_relative_to**(target: string, base: string) -> maybe string

 Relative path from `base` to `target`.

 ## Memoria
 Returns `some` with a fresh owned string (release it with `banish`) or
 `maybe none`. Both component lists built here are released in full: their
 buffers by `defer`, their owned elements by `cp_release_strings`, on every
 return path.

### `cp_glob_match`

> **cp_glob_match**(s: string, p: string) -> bool

 Glob pattern matcher (`*` matches any sequence, `?` matches one byte).

 ## Motivo
 A pointer scan walks both buffers in place, so the matcher indexes no
 substrings and allocates nothing per step; the backtracking state is three raw
 pointers. The Pengu loop rebuilt one-byte slices for every comparison.

 ## Memoria
 Allocates nothing. Both strings are borrowed and never freed.

### `cp_components`

> **cp_components**(path: string) -> list of string

 Splits normalized `path` into components.

### `cp_has_component`

> **cp_has_component**(path: string, name: string) -> bool

 True when any component of `path` matches `name`.

 ## Memoria
 Allocates only through `cp_components`, whose owned components are released
 here before every return; the list buffer is released by `defer`.

### `cp_is_hidden`

> **cp_is_hidden**(path: string) -> bool

 True when `path` starts with a dot and is not "." or "..".

 ## Memoria
 Allocates nothing beyond the basename that is released here; the first-byte
 test is an allocation-free byte read.

### `cp_is_unc`

> **cp_is_unc**(path: string) -> bool

 True when `path` is a Universal Naming Convention (UNC) path.

 ## Memoria
 Allocates nothing; the three leading bytes are read through `bytes of`.

### `cp_has_wildcard`

> **cp_has_wildcard**(path: string) -> bool

 True when `path` contains glob wildcards (`*` or `?`).

 ## Memoria
 Allocates nothing; each byte is compared in place instead of through a
 freshly allocated one-byte `path at i` string.

### `cp_matches`

> **cp_matches**(path: string, pattern: string) -> bool

 Tests if `path` matches a wildcard `pattern`.

 ## Memoria
 Allocates only the normalized-or-basename subject, released here; the
 separator scan is allocation-free and the matcher itself allocates nothing.

### `cp_cwd`

> **cp_cwd**() -> string

 Returns the current working directory as an owned string.

 ## Memoria
 The maybe box and its string payload are released here; the returned string
 is a fresh owned copy (release it with `banish`), or the borrowed "." literal
 when `getcwd` fails.

### `cp_expand_user`

> **cp_expand_user**(path: string) -> string

 Expands a leading `~` or `~/...` to the user home directory.

 ## Memoria
 Every `pengu_c_getenv` maybe box (with its string payload) is released here,
 and `home` is a fresh owned copy of the environment value, so it is released
 on each path that does not hand it to the caller. The result is owned when an
 expansion happened and the borrowed input otherwise.

### `cp_absolute`

> **cp_absolute**(path: string) -> string

 Returns the normalized absolute path.

### `cp_with_filename`

> **cp_with_filename**(path: string, new_name: string) -> string

 Replaces the final component (basename) of `path` with `new_name`.

### `join`

> **join**(parts: list of string) -> string

 Joins path parts with the platform separator and normalizes the result.

 ## Parámetros
 - `parts`: the segments to join, in order. Empty segments are skipped.

 ## Retorno
 The normalized joined path, as a new owned `string`; release it with
 `banish`. An empty `parts` list yields a borrowed empty string.

 ## Memoria
 The result is a fresh heap copy; the `parts` list and its elements are
 borrowed and never freed.

 ## Ejemplo
 ```pengu
 calling compass.join with ["a", "b"]     # "a/b"
 ```

### `join_all`

> **join_all**(parts: list of string) -> string

 Joins path parts with the platform separator and normalizes the result; twin of
 `join`.

 ## Parámetros
 - `parts`: the segments to join, in order. Empty segments are skipped.

 ## Retorno
 The normalized joined path, as a new owned `string`; release it with
 `banish`.

 ## Memoria
 The result is a fresh heap copy; the `parts` list and its elements are
 borrowed and never freed.

 ## Ejemplo
 ```pengu
 calling compass.join_all with ["a", "b"]     # "a/b"
 ```

### `basename`

> **basename**(path: string) -> string

 Final component of `path` (filename), or "" when there is none.

 ## Parámetros
 - `path`: the path to inspect. May be empty or end in separators.

 ## Retorno
 A new owned `string` with the last segment, or a borrowed empty string when
 `path` is empty or consists only of separators. Trailing separators after a
 name are skipped, so `"a/"` still yields `"a"`. Release an owned result with
 `banish`.

 ## Ejemplo
 ```pengu
 calling compass.basename with "/tmp/a.txt"     # "a.txt"
 ```

### `filename`

> **filename**(path: string) -> string

 Alias of `basename`: returns the final component of `path`.

 ## Parámetros
 - `path`: the path to inspect.

 ## Retorno
 A new owned `string` with the last segment; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.filename with "/tmp/a.txt"     # "a.txt"
 ```

### `dirname`

> **dirname**(path: string) -> string

 Directory portion of `path` without a trailing separator, or "" when there is
 none.

 ## Parámetros
 - `path`: the path to inspect.

 ## Retorno
 A new owned `string` with the directory part, or a borrowed empty string when
 `path` has no parent. Release an owned result with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.dirname with "/tmp/a.txt"     # "/tmp"
 ```

### `ext`

> **ext**(path: string) -> string

 Extension of the basename including the dot (e.g. ".txt"), or "" when there is
 none.

 ## Parámetros
 - `path`: the path to inspect.

 ## Retorno
 A new owned `string` with the extension and its dot, or a borrowed empty string
 when the basename has no extension. A leading dot is not an extension. Release
 an owned result with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.ext with "a.tar.gz"     # ".gz"
 ```

### `stem`

> **stem**(path: string) -> string

 Basename without its final extension.

 ## Parámetros
 - `path`: the path to inspect.

 ## Retorno
 A new owned `string` with the basename minus its last extension; release it
 with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.stem with "/tmp/a.tar.gz"     # "a.tar"
 ```

### `file_stem`

> **file_stem**(path: string) -> string

 Alias of `stem`: returns the basename without its final extension.

 ## Parámetros
 - `path`: the path to inspect.

 ## Retorno
 A new owned `string`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.file_stem with "/tmp/a.txt"     # "a"
 ```

### `is_absolute`

> **is_absolute**(path: string) -> bool

 True when `path` is absolute (a drive prefix on Windows, or a leading separator).

 ## Parámetros
 - `path`: the path to test.

 ## Retorno
 `true` when the path is absolute, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling compass.is_absolute with "/tmp"     # true
 ```

### `is_relative`

> **is_relative**(path: string) -> bool

 True when `path` is not absolute.

 ## Parámetros
 - `path`: the path to test.

 ## Retorno
 `true` when the path is relative, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling compass.is_relative with "a/b"     # true
 ```

### `normalize`

> **normalize**(path: string) -> string

 Collapses redundant separators and resolves "." and ".." segments.

 ## Parámetros
 - `path`: the path to normalize. An empty string normalizes to `"."`.

 ## Retorno
 The normalized path as a new owned `string`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.normalize with "a//b/./c/../d"     # "a/b/d"
 ```

### `parent`

> **parent**(path: string) -> maybe string

 Parent directory as `maybe string`; `none` when `path` is a root or has no
 parent directory.

 ## Parámetros
 - `path`: the path to inspect.

 ## Retorno
 `some dir` with an owned `string` when there is a parent, `maybe none`
 otherwise. Release the result with `banish`.

 ## Memoria
 The payload is a fresh heap copy; the input is borrowed.

 ## Ejemplo
 ```pengu
 calling compass.parent with "/tmp/a.txt"     # some "/tmp"
 ```

### `split`

> **split**(path: string) -> list of string

 Splits `path` into its drive, root separator and segment components.

 ## Parámetros
 - `path`: the path to split. An empty path yields an empty list.

 ## Retorno
 A new owned `list of string` holding the drive prefix (Windows only), the root
 separator and the segments. Release the buffer with `banish` and each component
 with `banish (xs at i)` when you need to reclaim it.

 ## Memoria
 The list owns its element buffer and its freshly built component strings.

 ## Ejemplo
 ```pengu
 calling compass.split with "/a/b"     # ["/", "a", "b"]
 ```

### `components`

> **components**(path: string) -> list of string

 Splits `path` into components after normalizing it.

 ## Parámetros
 - `path`: the path to split.

 ## Retorno
 A new owned `list of string` with the normalized components; release the buffer
 with `banish` and each component with `banish (xs at i)` when you need to
 reclaim it.

 ## Memoria
 The list owns its element buffer and its freshly built component strings.

 ## Ejemplo
 ```pengu
 calling compass.components with "a//b"     # ["a", "b"]
 ```

### `has_component`

> **has_component**(path: string, name: string) -> bool

 True when any component of `path` matches `name`.

 ## Parámetros
 - `path`: the path to search.
 - `name`: the exact component to look for.

 ## Retorno
 `true` when some normalized component equals `name`, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling compass.has_component with "/a/b/c", "b"     # true
 ```

### `has_ext`

> **has_ext**(path: string) -> bool

 True when the basename has an extension.

 ## Parámetros
 - `path`: the path to inspect.

 ## Retorno
 `true` when `ext` would return a non-empty string, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling compass.has_ext with "a.txt"     # true
 ```

### `separator`

> **separator**() -> string

 Preferred path separator for this platform ("\\" on Windows, "/" elsewhere).

 ## Retorno
 A borrowed one-character literal; do not `banish` it.

 ## Ejemplo
 ```pengu
 calling compass.separator     # "/" on Unix, "\\" on Windows
 ```

### `alt_separator`

> **alt_separator**() -> maybe string

 Alternate path separator: `some "/"` on Windows, `none` on other platforms.

 ## Retorno
 `some "/"` on Windows or `maybe none` elsewhere; release `some` with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.alt_separator     # none on Unix
 ```

### `is_root`

> **is_root**(path: string) -> bool

 True when `path` is exactly a filesystem root.

 ## Parámetros
 - `path`: the path to test.

 ## Retorno
 `true` for `"/"`, `"C:"` or `"C:\\"` (the last two on Windows), `false`
 otherwise.

 ## Ejemplo
 ```pengu
 calling compass.is_root with "/"     # true
 ```

### `drive`

> **drive**(path: string) -> string

 Windows drive prefix of `path` (e.g. "C:"), or "" when there is none.

 ## Parámetros
 - `path`: the path to inspect.

 ## Retorno
 A new owned `string` with the drive prefix, or a borrowed empty string when
 there is none. Release an owned result with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.drive with "C:/a"     # "C:" on Windows, "" on Unix
 ```

### `change_ext`

> **change_ext**(path: string, new_ext: string) -> string

 Replaces the extension of `path` with `new_ext` (the dot is added when missing;
 an empty `new_ext` removes the extension).

 ## Parámetros
 - `path`: the path to rewrite.
 - `new_ext`: the new extension, with or without its leading dot.

 ## Retorno
 A new owned `string`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.change_ext with "a.txt", ".md"     # "a.md"
 ```

### `with_extension`

> **with_extension**(path: string, new_ext: string) -> string

 Replaces the extension of `path` with `new_ext`.

 ## Parámetros
 - `path`: the path to rewrite.
 - `new_ext`: the new extension, with or without its leading dot.

 ## Retorno
 A new owned `string`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.with_extension with "a.txt", "md"     # "a.md"
 ```

### `without_extension`

> **without_extension**(path: string) -> string

 Returns `path` without its final extension.

 ## Parámetros
 - `path`: the path to rewrite.

 ## Retorno
 A new owned `string`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.without_extension with "/tmp/a.txt"     # "/tmp/a"
 ```

### `with_filename`

> **with_filename**(path: string, new_name: string) -> string

 Replaces the final component (basename) of `path` with `new_name`.

 ## Parámetros
 - `path`: the path to rewrite.
 - `new_name`: the replacement basename.

 ## Retorno
 A new owned `string`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling compass.with_filename with "/tmp/a.txt", "b.md"     # "/tmp/b.md"
 ```

### `add_ext`

> **add_ext**(path: string, ext: string) -> string

 Appends `ext` only when `path` has no extension yet.

 ## Parámetros
 - `path`: the path to extend.
 - `ext`: the extension to append, with or without its leading dot.

 ## Retorno
 The unchanged borrowed `path` when it already has an extension or `ext` is
 empty, otherwise a new owned `string`. `banish` is safe either way.

 ## Ejemplo
 ```pengu
 calling compass.add_ext with "a", ".txt"     # "a.txt"
 ```

### `relative_to`

> **relative_to**(target: string, base: string) -> maybe string

 Relative path from `base` to `target`, using ".." segments when needed.

 ## Parámetros
 - `target`: the destination path.
 - `base`: the directory the result is relative to.

 ## Retorno
 `some rel` with an owned `string` when a relative path exists, or `maybe none`
 when `target` is absolute and shares no leading component with `base`. Release
 the result with `banish`.

 ## Memoria
 The payload is a fresh heap copy; both arguments are borrowed.

 ## Ejemplo
 ```pengu
 calling compass.relative_to with "/a/b/c", "/a/b"     # some "c"
 ```

### `has_suffix`

> **has_suffix**(path: string, suffix: string) -> bool

 True when the tail of `path` equals `suffix`.

 ## Parámetros
 - `path`: the path to test.
 - `suffix`: the suffix to compare; the empty suffix always matches.

 ## Retorno
 `true` when `path` ends with `suffix`, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling compass.has_suffix with "a.tar.gz", ".gz"     # true
 ```

### `suffixes`

> **suffixes**(path: string) -> list of string

 The dotted suffixes of the basename, e.g. "a.tar.gz" gives ["tar", "gz"].

 ## Parámetros
 - `path`: the path to inspect.

 ## Retorno
 A new owned `list of string` with the non-empty suffixes between dots. Release
 the buffer with `banish` and each element with `banish (xs at i)` when you need
 to reclaim it.

 ## Memoria
 The list owns its element buffer and its freshly built component strings.

 ## Ejemplo
 ```pengu
 calling compass.suffixes with "a.tar.gz"     # ["tar", "gz"]
 ```

### `is_hidden`

> **is_hidden**(path: string) -> bool

 True when `path` starts with a dot and is not "." or "..".

 ## Parámetros
 - `path`: the path to test.

 ## Retorno
 `true` for a dotfile such as ".bashrc", `false` for ".", ".." and regular
 names.

 ## Ejemplo
 ```pengu
 calling compass.is_hidden with ".bashrc"     # true
 ```

### `is_unc`

> **is_unc**(path: string) -> bool

 True when `path` is a Universal Naming Convention (UNC) path (e.g.
 "\\\\server\\share").

 ## Parámetros
 - `path`: the path to test.

 ## Retorno
 `true` when `path` starts with two separators followed by a non-separator,
 `false` otherwise.

 ## Ejemplo
 ```pengu
 calling compass.is_unc with "//server/share"     # true
 ```

### `has_wildcard`

> **has_wildcard**(path: string) -> bool

 True when `path` contains glob wildcards (`*` or `?`).

 ## Parámetros
 - `path`: the string to scan.

 ## Retorno
 `true` when a `*` or `?` byte occurs anywhere in `path`, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling compass.has_wildcard with "*.pengu"     # true
 ```

### `matches`

> **matches**(path: string, pattern: string) -> bool

 Tests if filename or path matches a wildcard pattern.

 ## Parámetros
 - `path`: the path to test.
 - `pattern`: the glob pattern; `*` matches any sequence and `?` one byte.

 ## Retorno
 `true` when the pattern matches. When `pattern` contains a separator the whole
 normalized `path` is matched, otherwise only its basename is.

 ## Ejemplo
 ```pengu
 calling compass.matches with "dir/a.txt", "*.txt"     # true
 ```

### `cwd`

> **cwd**() -> string

 Returns the current working directory as an owned string.

 ## Retorno
 A new owned `string`; release it with `banish`. Falls back to `"."` when the
 native `getcwd` fails.

 ## Ejemplo
 ```pengu
 let here as string is calling compass.cwd
 defer banish here
 ```

### `expand_user`

> **expand_user**(path: string) -> string

 Expands a leading `~` or `~/...` to the user home directory.

 ## Parámetros
 - `path`: the path to expand. A path that does not start with `~` is returned
   unchanged.

 ## Retorno
 A new owned `string` when the expansion happened, or the borrowed input
 unchanged. Named-user expansions (`~username`) are not supported and are
 returned unchanged. `banish` is safe either way.

 ## Ejemplo
 ```pengu
 calling compass.expand_user with "~/notes"     # "/home/user/notes"
 ```

### `absolute`

> **absolute**(path: string) -> string

 Returns the normalized absolute path.

 ## Parámetros
 - `path`: the path to make absolute. An already absolute path is only
   normalized.

 ## Retorno
 A new owned `string`; release it with `banish`. Relative inputs are resolved
 against `cwd`.

 ## Ejemplo
 ```pengu
 calling compass.absolute with "notes.txt"     # "/current/dir/notes.txt"
 ```

### `is_windows`

> **is_windows**() -> bool

 True when this build targets Windows.

 ## Retorno
 `true` on a Windows target, `false` everywhere else.

 ## Ejemplo
 ```pengu
 calling compass.is_windows     # false on Unix
 ```

### `is_unix`

> **is_unix**() -> bool

 True when this build targets a Unix-like platform (not Windows).

 ## Retorno
 `true` on a non-Windows target, `false` on Windows.

 ## Ejemplo
 ```pengu
 calling compass.is_unix     # true on Unix
 ```

### `Path`

> rune Path

```pengu
    raw as string
```

 An owned wrapper around a raw path string exposing chainable query and
 transform methods.

 ## Memoria
 The rune stores the `string` in its `raw` field without copying it; the rune
 owns that buffer and releasing it is the caller's responsibility.

### `from_str`

> **from_str**(s: string) -> Path

 Ritual constructor creating a `Path` from a raw string.

 ## Parámetros
 - `s`: the path text to wrap. Moved into the rune.

 ## Retorno
 A new `Path` whose `raw` field holds `s`.

 ## Memoria
 The rune takes ownership of `s` as-is; do not `banish` the argument
 separately.

 ## Ejemplo
 ```pengu
 let p as compass.Path is calling compass.Path.from_str with "a/b.txt"
 ```

### `to_string`

> **to_string**() -> string

 The underlying raw path as a plain string.

 ## Retorno
 The rune's `raw` string, borrowed: do not `banish` it.

 ## Ejemplo
 ```pengu
 calling p.to_string     # "a/b.txt"
 ```

### `name`

> **name**() -> string

 Final component of the path (basename), "" when there is none.

 ## Retorno
 A new owned `string`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling p.name     # "b.txt"
 ```

### `suffix`

> **suffix**() -> string

 Extension including the dot, "" when there is none.

 ## Retorno
 A new owned `string`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling p.suffix     # ".txt"
 ```

### `parts`

> **parts**() -> list of string

 Path split into drive, root separator and segment components.

 ## Retorno
 A new owned `list of string`; release the buffer with `banish` and each
 element with `banish (xs at i)` when you need to reclaim it.

 ## Memoria
 The list owns its element buffer and its freshly built component strings.

 ## Ejemplo
 ```pengu
 calling p.parts     # ["/", "a", "b.txt"]
 ```

### `has_suffix_with`

> **has_suffix_with**(suffix: string) -> bool

 True when the tail of the path equals the given suffix.

 ## Parámetros
 - `suffix`: the suffix to compare; the empty suffix always matches.

 ## Retorno
 `true` when `raw` ends with `suffix`, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling p.has_suffix_with with ".txt"     # true
 ```

### `is_empty`

> **is_empty**() -> bool

 True when the wrapped path is the empty string.

 ## Retorno
 `true` when `raw` has zero bytes, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling p.is_empty     # false
 ```

### `exists`

> **exists**() -> bool

 True when the entry exists on the filesystem.

 ## Retorno
 `true` when the native `archivum` probe finds the entry, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling p.exists     # true when the file is there
 ```

### `is_file`

> **is_file**() -> bool

 True when the entry is a regular file.

 ## Retorno
 `true` when the native `archivum` probe reports a regular file, `false`
 otherwise.

 ## Ejemplo
 ```pengu
 calling p.is_file     # true for a regular file
 ```

### `is_dir`

> **is_dir**() -> bool

 True when the entry is a directory.

 ## Retorno
 `true` when the native `archivum` probe reports a directory, `false`
 otherwise.

 ## Ejemplo
 ```pengu
 calling p.is_dir     # true for a directory
 ```

### `to_absolute`

> **to_absolute**() -> Path

 Returns a new `Path` with the normalized absolute path.

 ## Retorno
 A new `Path`; the rune owns its `raw` string.

 ## Memoria
 The returned rune owns the freshly built path; the receiver is borrowed.

 ## Ejemplo
 ```pengu
 let abs_p as compass.Path is calling p.to_absolute
 ```

### `to_uri`

> **to_uri**() -> string

 Converts the path to a `file://` URI (backslashes become `/`, spaces become
 `%20`).

 ## Retorno
 A new owned `string`; release it with `banish`.

 ## Memoria
 The intermediate normalized path and the byte buffer are owned temporaries,
 released before the function returns.

 ## Ejemplo
 ```pengu
 calling p.to_uri     # "file:///a/b.txt"
 ```

### `with_suffix`

> **with_suffix**(new_ext: string) -> Path

 A new `Path` whose extension is replaced by `new_ext`.

 ## Parámetros
 - `new_ext`: the new extension, with or without its leading dot.

 ## Retorno
 A new `Path`; the rune owns its `raw` string.

 ## Memoria
 The returned rune owns the freshly built path; the receiver is borrowed.

 ## Ejemplo
 ```pengu
 let md as compass.Path is calling p.with_suffix with ".md"
 ```

### `with_name`

> **with_name**(new_name: string) -> Path

 A new `Path` with its final component replaced by `new_name`.

 ## Parámetros
 - `new_name`: the replacement basename.

 ## Retorno
 A new `Path`; the rune owns its `raw` string.

 ## Memoria
 The returned rune owns the freshly built path; the receiver is borrowed.

 ## Ejemplo
 ```pengu
 let renamed as compass.Path is calling p.with_name with "c.md"
 ```

### `add_suffix`

> **add_suffix**(ext: string) -> Path

 A new `Path` with `ext` appended when it has no extension yet, unchanged
 otherwise.

 ## Parámetros
 - `ext`: the extension to append, with or without its leading dot.

 ## Retorno
 A new `Path`; the rune owns its `raw` string, which may alias the receiver's
 when nothing changed.

 ## Memoria
 The returned rune owns the resulting path.

 ## Ejemplo
 ```pengu
 let full as compass.Path is calling p.add_suffix with ".txt"
 ```

### `without_suffix`

> **without_suffix**() -> Path

 A new `Path` without its final extension.

 ## Retorno
 A new `Path`; the rune owns its `raw` string.

 ## Memoria
 The returned rune owns the freshly built path; the receiver is borrowed.

 ## Ejemplo
 ```pengu
 let bare as compass.Path is calling p.without_suffix
 ```

### `path`

> **path**(raw: string) -> Path

 Builds an owned `Path` value from a raw path string.

 ## Parámetros
 - `raw`: the path text to wrap. Moved into the rune.

 ## Retorno
 A new `Path` whose `raw` field holds the same string.

 ## Memoria
 The rune takes ownership of `raw` as-is (no copy); do not `banish` the argument
 separately.

 ## Ejemplo
 ```pengu
 let p as compass.Path is calling compass.path with "a/b.txt"
 ```

### `new_path`

> **new_path**(s: string) -> Path

 Builds an owned `Path` value from a raw path string (alias of
 `Path.from_str`).

 ## Parámetros
 - `s`: the path text to wrap. Moved into the rune.

 ## Retorno
 A new `Path` whose `raw` field holds `s`.

 ## Memoria
 The rune takes ownership of `s` as-is (no copy).

 ## Ejemplo
 ```pengu
 let p as compass.Path is calling compass.new_path with "/tmp/notes.txt"
 ```

### `current_dir`

> **current_dir**() -> Path

 Returns the current working directory as an owned `Path`.

 ## Retorno
 A new `Path` whose `raw` is an owned copy of the working directory.

 ## Memoria
 The rune owns the freshly built path.

 ## Ejemplo
 ```pengu
 let here as compass.Path is calling compass.current_dir
 ```

### `path_join`

> **path_join**(parts: list of string) -> Path

 Builds an owned `Path` by joining `parts` with the platform separator and
 normalizing.

 ## Parámetros
 - `parts`: the segments to join, in order. Empty segments are skipped.

 ## Retorno
 A new `Path` whose `raw` is the joined, normalized path.

 ## Memoria
 The rune owns the freshly built path; the `parts` list is borrowed.

 ## Ejemplo
 ```pengu
 let p as compass.Path is calling compass.path_join with ["a", "b.txt"]
 ```

### `_cp_test_join`

> **_cp_test_join**(parts: list of string) -> string

 Test-only compass join; avoids the `scrolls.join` name in the test namespace.

### `_cp_expect_int`

> **_cp_expect_int**(got: int, want: int, label: string) -> void

 Aborts the current test with `label` when `got != want`.

### `_cp_expect_str`

> **_cp_expect_str**(got: string, want: string, label: string) -> void

 Aborts the current test with `label` when `got != want`.

### `_cp_expect_true`

> **_cp_expect_true**(cond: bool, label: string) -> void

 Aborts the current test with `label` when `cond` is false.

### `"COMPASS_VERSION is 2.14.0"`

> test "COMPASS_VERSION is 2.14.0"

_Undocumented._

### `"separator is a single character"`

> test "separator is a single character"

_Undocumented._

### `"join combines two segments"`

> test "join combines two segments"

_Undocumented._

### `"join skips empty segments"`

> test "join skips empty segments"

_Undocumented._

### `"join_all behaves like join"`

> test "join_all behaves like join"

_Undocumented._

### `"join of an empty list is the empty string"`

> test "join of an empty list is the empty string"

_Undocumented._

### `"join keeps an absolute first part"`

> test "join keeps an absolute first part"

_Undocumented._

### `"basename returns the last segment"`

> test "basename returns the last segment"

_Undocumented._

### `"basename skips a trailing separator"`

> test "basename skips a trailing separator"

_Undocumented._

### `"basename of separators only is empty"`

> test "basename of separators only is empty"

_Undocumented._

### `"basename of the root is empty"`

> test "basename of the root is empty"

_Undocumented._

### `"filename is an alias of basename"`

> test "filename is an alias of basename"

_Undocumented._

### `"dirname drops the final segment"`

> test "dirname drops the final segment"

_Undocumented._

### `"dirname of a bare name is empty"`

> test "dirname of a bare name is empty"

_Undocumented._

### `"dirname of the root keeps the root"`

> test "dirname of the root keeps the root"

_Undocumented._

### `"ext returns the dotted extension"`

> test "ext returns the dotted extension"

_Undocumented._

### `"ext ignores a leading dot"`

> test "ext ignores a leading dot"

_Undocumented._

### `"ext keeps only the last dot"`

> test "ext keeps only the last dot"

_Undocumented._

### `"stem drops the final extension"`

> test "stem drops the final extension"

_Undocumented._

### `"file_stem is an alias of stem"`

> test "file_stem is an alias of stem"

_Undocumented._

### `"has_ext detects an extension"`

> test "has_ext detects an extension"

_Undocumented._

### `"normalize collapses redundant separators"`

> test "normalize collapses redundant separators"

_Undocumented._

### `"normalize resolves dot segments"`

> test "normalize resolves dot segments"

_Undocumented._

### `"normalize resolves parent segments"`

> test "normalize resolves parent segments"

_Undocumented._

### `"normalize keeps unresolvable parent segments"`

> test "normalize keeps unresolvable parent segments"

_Undocumented._

### `"normalize of an empty path is a dot"`

> test "normalize of an empty path is a dot"

_Undocumented._

### `"normalize keeps an absolute root"`

> test "normalize keeps an absolute root"

_Undocumented._

### `"is_absolute accepts a leading separator"`

> test "is_absolute accepts a leading separator"

_Undocumented._

### `"is_absolute rejects a bare name"`

> test "is_absolute rejects a bare name"

_Undocumented._

### `"is_relative negates is_absolute"`

> test "is_relative negates is_absolute"

_Undocumented._

### `"absolute of a relative path is absolute"`

> test "absolute of a relative path is absolute"

_Undocumented._

### `"relative_to computes a child path"`

> test "relative_to computes a child path"

_Undocumented._

### `"relative_to walks up with parent segments"`

> test "relative_to walks up with parent segments"

_Undocumented._

### `"relative_to of an absolute target under a relative base is none"`

> test "relative_to of an absolute target under a relative base is none"

_Undocumented._

### `"components includes the root separator"`

> test "components includes the root separator"

_Undocumented._

### `"components splits a relative path"`

> test "components splits a relative path"

_Undocumented._

### `"has_component finds a segment"`

> test "has_component finds a segment"

_Undocumented._

### `"has_suffix compares the tail"`

> test "has_suffix compares the tail"

_Undocumented._

### `"suffixes lists the dotted suffixes"`

> test "suffixes lists the dotted suffixes"

_Undocumented._

### `"suffixes of a dotfile is empty"`

> test "suffixes of a dotfile is empty"

_Undocumented._

### `"drive has no prefix on a posix-style path"`

> test "drive has no prefix on a posix-style path"

_Undocumented._

### `"is_root accepts the separator"`

> test "is_root accepts the separator"

_Undocumented._

### `"is_hidden accepts a dotfile"`

> test "is_hidden accepts a dotfile"

_Undocumented._

### `"is_unc accepts a double-separator prefix"`

> test "is_unc accepts a double-separator prefix"

_Undocumented._

### `"has_wildcard detects star and question"`

> test "has_wildcard detects star and question"

_Undocumented._

### `"matches accepts an exact pattern"`

> test "matches accepts an exact pattern"

_Undocumented._

### `"matches honours the star wildcard"`

> test "matches honours the star wildcard"

_Undocumented._

### `"matches honours the question wildcard"`

> test "matches honours the question wildcard"

_Undocumented._

### `"matches is case sensitive"`

> test "matches is case sensitive"

_Undocumented._

### `"matches anchors the pattern"`

> test "matches anchors the pattern"

_Undocumented._

### `"matches an empty pattern only against an empty string"`

> test "matches an empty pattern only against an empty string"

_Undocumented._

### `"matches a literal star against a literal star"`

> test "matches a literal star against a literal star"

_Undocumented._

### `"matches uses the basename when the pattern has no separator"`

> test "matches uses the basename when the pattern has no separator"

_Undocumented._

### `"matches uses the whole path when the pattern has a separator"`

> test "matches uses the whole path when the pattern has a separator"

_Undocumented._

### `"Path from_str round-trips"`

> test "Path from_str round-trips"

_Undocumented._

### `"Path new_path and path agree"`

> test "Path new_path and path agree"

_Undocumented._

### `"Path name stem and suffix"`

> test "Path name stem and suffix"

_Undocumented._

### `"Path parent of a nested file"`

> test "Path parent of a nested file"

_Undocumented._

### `"Path parent of a root is none"`

> test "Path parent of a root is none"

_Undocumented._

### `"Path is_empty detects the empty path"`

> test "Path is_empty detects the empty path"

_Undocumented._

### `"Path normalize resolves segments"`

> test "Path normalize resolves segments"

_Undocumented._

### `"Path components splits the raw path"`

> test "Path components splits the raw path"

_Undocumented._

### `"Path matches a glob"`

> test "Path matches a glob"

_Undocumented._

### `"Path with_suffix replaces the extension"`

> test "Path with_suffix replaces the extension"

_Undocumented._

### `"Path without_suffix removes the extension"`

> test "Path without_suffix removes the extension"

_Undocumented._

### `"Path add_suffix only fills a missing extension"`

> test "Path add_suffix only fills a missing extension"

_Undocumented._

### `"Path with_name replaces the basename"`

> test "Path with_name replaces the basename"

_Undocumented._

### `"Path has_suffix_with compares the tail"`

> test "Path has_suffix_with compares the tail"

_Undocumented._

### `"Path relative_to finds a child"`

> test "Path relative_to finds a child"

_Undocumented._

### `"Path to_uri renders an absolute path"`

> test "Path to_uri renders an absolute path"

_Undocumented._

### `"Path to_uri encodes spaces"`

> test "Path to_uri encodes spaces"

_Undocumented._

### `"Path to_absolute produces an absolute path"`

> test "Path to_absolute produces an absolute path"

_Undocumented._

### `"Path expand_user keeps a usable path"`

> test "Path expand_user keeps a usable path"

_Undocumented._

### `"the filesystem root exists"`

> test "the filesystem root exists"

_Undocumented._

### `"cwd is a non-empty string"`

> test "cwd is a non-empty string"

_Undocumented._

### `"expand_user of a tilde path is non-empty"`

> test "expand_user of a tilde path is non-empty"

_Undocumented._

### `"alt_separator is a forward slash or absent"`

> test "alt_separator is a forward slash or absent"

_Undocumented._

