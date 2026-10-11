# `std.compass` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `COMPASS_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/compass.pengu`](../std/compass.pengu).

`compass` owns path manipulation: joining, splitting, normalizing and querying
filesystem paths. Almost everything is pure PenguScript; the only non-Pengu
pieces are one `antiquus` glob matcher and the five native `declare`s at the top
of the file. `compass` imports `std.spark`, `std.oracle` and `std.scrolls`, but
delegates none of its path logic to them.

The public surface is **72 declarations over 57 distinct weave names**: 37
module functions, the `Path` rune with 2 ritual constructors and 29 methods, and
4 module-level `Path` constructors (`path`, `new_path`, `current_dir`,
`path_join`). Fifteen names deliberately exist both as a module function and as
a `Path` method (`components`, `cwd`, `drive`, `expand_user`, `has_suffix`,
`is_absolute`, `is_hidden`, `is_relative`, `is_root`, `matches`, `normalize`,
`parent`, `relative_to`, `stem`, `suffixes`). Every building block is a
module-private helper named `cp_<thing>` (31 weaves plus the `antiquus`
`cp_glob_match`); the public functions are thin delegations to them, which keeps
the helpers apart from the `enchanting Path` methods and from the code
generator's function registry.

`Path` is a single-field rune (`raw as string`) whose methods are pure
transformations returning new runes, so no aliasing rules are needed. The
platform model is one compile-time flag: `cp_win` folds `when os == "windows"`,
so `separator`, `drive`, `is_absolute` and `normalize` branch on the target OS
without a runtime check. Note that `cp_is_sep` recognises both `/` and `\` on
every platform, while `is_absolute`/`is_root` follow the platform flag.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every `string`-returning function/method | new owned heap copy | `banish` / `defer banish` |
| every `list of string`-returning function/method | owned element buffer; elements are owned too | `banish` the list, `banish (xs at i)` per element |
| every `maybe string`-returning function/method | `some` owns its payload; `none` has none | `banish` |
| `Path` rune and every `Path`-returning function/method | the rune owns its `raw` buffer | the caller releases the rune's `raw` |
| `separator`, empty-string results, and `add_ext` / `expand_user` / `Path.to_string` when unchanged | borrowed view (literal or the input) | `banish` is a safe no-op |
| every parameter and every receiver | borrowed | caller keeps its own release |

## Constants

| Symbol | Type | Value | Notes |
|---|---|---|---|
| `COMPASS_VERSION` | `string` | `"2.1.0"` | Revision of the **compass API**. Bumps only when a public signature or observable result changes. |

## Native runtime declarations

These five bridges are the module's only filesystem access. They **stay in
`pengu_runtime.h`**, where they are shared with `std.archivum` and `std.rites`;
this chunk does **not** move runtime code, and `compass` declares them exactly
as before.

| Declaration | Signature | Notes |
|---|---|---|
| `pengu_c_getcwd` | `() -> maybe string` | Backs `cwd` / `cp_cwd`; `none` on failure. |
| `pengu_c_getenv` | `(string) -> maybe string` | Backs `cp_expand_user` (`HOME`, `USERPROFILE`). |
| `pengu_c_archivum_exists` | `(string) -> bool` | Backs `Path.exists`. |
| `pengu_c_archivum_is_file` | `(string) -> bool` | Backs `Path.is_file`. |
| `pengu_c_archivum_is_dir` | `(string) -> bool` | Backs `Path.is_dir`. |

## String functions

### Join and split

| Symbol | Signature | Semantics |
|---|---|---|
| `join` | `(list of string) -> string` | Joins parts with the platform separator, skipping empty parts, then normalizes; an absolute part restarts the buffer. Empty list yields a borrowed `""`. |
| `join_all` | `(list of string) -> string` | Exact twin of `join` (a second name for the same `cp_join`). |
| `split` | `(string) -> list of string` | Splits into the Windows drive prefix, the root separator and the segments; empty path yields an empty list. |
| `components` | `(string) -> list of string` | `split` applied after `normalize`, so `.`/`..` and repeated separators are gone. |

### Name parts

| Symbol | Signature | Semantics |
|---|---|---|
| `basename` | `(string) -> string` | Final component; trailing separators are skipped; `""` for an empty path or separators only. |
| `filename` | `(string) -> string` | Alias of `basename`. |
| `dirname` | `(string) -> string` | Directory portion without a trailing separator; `""` when there is none; the root stays the root. |
| `stem` | `(string) -> string` | Basename without its final extension. |
| `file_stem` | `(string) -> string` | Alias of `stem`. |
| `with_filename` | `(string, string) -> string` | Replaces the final component with `new_name`; returns `new_name` when there is no directory. |

### Extensions and suffixes

| Symbol | Signature | Semantics |
|---|---|---|
| `ext` | `(string) -> string` | Extension of the basename including its dot; `""` when none. A leading dot is not an extension and only the last dot counts. |
| `has_ext` | `(string) -> bool` | `ext(path) != ""`. |
| `change_ext` | `(string, string) -> string` | Replaces the extension with `new_ext` (a dot is added when missing; empty `new_ext` removes it). |
| `with_extension` | `(string, string) -> string` | Alias of `change_ext`. |
| `without_extension` | `(string) -> string` | `change_ext(path, "")`: drops the final extension. |
| `add_ext` | `(string, string) -> string` | Appends `ext` only when the path has no extension and `ext` is non-empty; otherwise returns the borrowed path unchanged. |
| `suffixes` | `(string) -> list of string` | Dotted suffixes of the basename, e.g. `"a.tar.gz"` → `["tar", "gz"]`. |

### Normalization

| Symbol | Signature | Semantics |
|---|---|---|
| `normalize` | `(string) -> string` | Collapses redundant separators and resolves `.`/`..`; `""` becomes `"."`; an absolute root is kept and leading `..` on a relative path is kept. |
| `absolute` | `(string) -> string` | The normalized absolute path; relative inputs are resolved against `cwd`. |

### Relationship

| Symbol | Signature | Semantics |
|---|---|---|
| `parent` | `(string) -> maybe string` | `some dir` with the parent directory, or `none` for a root / a path with no directory. |
| `relative_to` | `(target: string, base: string) -> maybe string` | Relative path from `base` to `target`, using `..`; `none` when `target` is absolute and shares no leading component with `base`. |
| `has_component` | `(string, string) -> bool` | True when any normalized component equals `name`. |

### Predicates

| Symbol | Signature | Semantics |
|---|---|---|
| `is_absolute` | `(string) -> bool` | True for a leading separator, or a `X:` drive prefix on Windows. |
| `is_relative` | `(string) -> bool` | Negation of `is_absolute`. |
| `is_root` | `(string) -> bool` | True for `"/"`, and for `"C:"` / `"C:\"` on Windows. |
| `has_suffix` | `(path: string, suffix: string) -> bool` | True when the tail of `path` equals `suffix`; the empty suffix always matches. |
| `is_hidden` | `(string) -> bool` | True when the basename starts with `.` and is not `"."` or `".."`. |
| `is_unc` | `(string) -> bool` | True for a UNC path: two separators followed by a non-separator. |

### Glob matching

| Symbol | Signature | Semantics |
|---|---|---|
| `has_wildcard` | `(string) -> bool` | True when a `*` or `?` byte occurs anywhere. |
| `matches` | `(path: string, pattern: string) -> bool` | Anchored, case-sensitive wildcard match (`*` any run, `?` one byte). When `pattern` contains a separator the whole normalized `path` is matched; otherwise only its basename. |

### Platform and environment

| Symbol | Signature | Semantics |
|---|---|---|
| `separator` | `() -> string` | `"\\"` on Windows, `"/"` elsewhere; a borrowed literal. |
| `alt_separator` | `() -> maybe string` | `some "/"` on Windows, `maybe none` elsewhere. |
| `drive` | `(string) -> string` | Windows drive prefix (`"C:"`) when present, else `""`; always `""` on POSIX. |
| `cwd` | `() -> string` | Current working directory as an owned string; falls back to `"."` when the native call fails. |
| `expand_user` | `(string) -> string` | Expands a leading `~` or `~/...` from `HOME` (`USERPROFILE` first on Windows); `~user` is unsupported and returned borrowed unchanged. |
| `is_windows` | `() -> bool` | True when this build targets Windows (reads `cp_win`). |
| `is_unix` | `() -> bool` | Negation of `is_windows`. |

## `Path`

The rune deliberately stays a plain single-field wrapper, unchanged from 2.0.0:

```pengu
rune Path:
    raw as string
```

### Constructors

| Symbol | Signature | Semantics |
|---|---|---|
| `path` | `(raw: string) -> Path` | Wraps `raw` without copying; the rune takes ownership. |
| `new_path` | `(s: string) -> Path` | Delegates to `Path.from_str`. |
| `current_dir` | `() -> Path` | Delegates to `Path.cwd`. |
| `path_join` | `(list of string) -> Path` | Joins and normalizes `parts`, then wraps the result. |
| `Path.from_str` *(ritual)* | `(s: string) -> Path` | `with raw is s`: moves `s` into the rune. |
| `Path.cwd` *(ritual)* | `() -> Path` | `with raw is cp_cwd()`: the rune owns a fresh copy of the working directory. |

### Methods

All 31 members of `enchanting Path` are listed; the receiver is implicit and
borrowed. A `string`/`list of string`/`maybe string` result is owned and released
with `banish`; a `Path` result is a new rune that owns its `raw`.

| Method | Signature | Semantics |
|---|---|---|
| `to_string` | `() -> string` | The `raw` field, borrowed: do not `banish` it. |
| `name` | `() -> string` | Basename (`cp_basename`). |
| `parent` | `() -> maybe string` | `some dir` or `none` for a root / no parent. |
| `stem` | `() -> string` | Basename without its final extension. |
| `suffix` | `() -> string` | Dotted extension, `""` when none. |
| `suffixes` | `() -> list of string` | Dotted suffixes of the basename. |
| `drive` | `() -> string` | Windows drive prefix, `""` when none. |
| `parts` | `() -> list of string` | Raw split: drive, root separator and segments. |
| `components` | `() -> list of string` | Normalized components. |
| `is_absolute` | `() -> bool` | True when `raw` is absolute. |
| `is_relative` | `() -> bool` | Negation of `is_absolute`. |
| `is_root` | `() -> bool` | True when `raw` is exactly a root. |
| `has_suffix` | `() -> bool` | True when the basename has an **extension** (this is `cp_has_ext`, not a tail test). |
| `has_suffix_with` | `(suffix: string) -> bool` | True when `raw` ends with `suffix`; the empty suffix always matches. |
| `is_empty` | `() -> bool` | True when `raw` is the empty string. |
| `is_hidden` | `() -> bool` | True for a dotfile other than `.`/`..`. |
| `matches` | `(pattern: string) -> bool` | Wildcard match with the same basename/whole-path rule as `compass.matches`. |
| `exists` | `() -> bool` | Native `pengu_c_archivum_exists` probe. |
| `is_file` | `() -> bool` | Native `pengu_c_archivum_is_file` probe. |
| `is_dir` | `() -> bool` | Native `pengu_c_archivum_is_dir` probe. |
| `to_absolute` | `() -> Path` | New rune holding `cp_absolute(raw)`. |
| `expand_user` | `() -> Path` | New rune holding `cp_expand_user(raw)`. |
| `to_uri` | `() -> string` | `file://` URI: `\` becomes `/` and spaces become `%20`; an absolute path gives `file:///…`. |
| `normalize` | `() -> Path` | New rune holding `cp_normalize(raw)`. |
| `relative_to` | `(base: string) -> maybe string` | Relative path from `base` to `raw`, or `none`. |
| `with_suffix` | `(new_ext: string) -> Path` | New rune with the extension replaced. |
| `with_name` | `(new_name: string) -> Path` | New rune with the final component replaced. |
| `add_suffix` | `(ext: string) -> Path` | New rune with `ext` appended only when there is no extension. |
| `without_suffix` | `() -> Path` | New rune with the final extension removed. |
| `Path.from_str` | `(s: string) -> Path` | Ritual constructor (see above). |
| `Path.cwd` | `() -> Path` | Ritual constructor (see above). |

## The `cp_glob_match` C block

`cp_glob_match` is now an **`antiquus` C block** — a pointer wildcard matcher
covering `*` (any run) and `?` (one byte) — replacing the previous byte-indexed
Pengu loop. Its declared form is
`antiquus cp_glob_match with s as string, p as string into bool`: private, and
producing identical results to the old implementation (including the documented
`matches("**", "*") == false` quirk).

Its `## ## Motivo` records why: a pointer scan walks both buffers in place, so
the matcher indexes no substrings and allocates nothing per step; the
backtracking state is three raw pointers, whereas the Pengu loop rebuilt
one-byte slices for every comparison. Its `## ## Memoria` records the cost:
allocates nothing; both strings are borrowed and never freed.

The five native `declare`s and `Path`'s shape are **unchanged** by this chunk.

## Compatibility

* Every 2.0.0 public symbol keeps its name, bounds and signature; all 72 public
  declarations are preserved.
* The five native `declare`s are untouched and remain in `pengu_runtime.h`.
* `rune Path` remains a single `raw as string` field.
* 2.1.0 is a documentation/style migration plus the `cp_glob_match` C block:
  comments and docstrings are English, every public weave and `Path` method
  carries `## ## Parámetros` / `## ## Retorno` / `## ## Ejemplo` sections, and
  the internal `# --- Tests ---` suite was added.
* Behavior is unchanged; the only new name is the private `cp_glob_match` block
  (the private helper set grew, the public set did not). Nothing is deprecated.

## Private helpers (internal)

Not part of the frozen surface. The public functions delegate here.

* **Platform and shape:** `cp_win () -> bool`, `cp_is_sep (string) -> bool`, `cp_is_letter (string) -> bool`, `cp_sep () -> string`, `cp_is_abs (string) -> bool`, `cp_is_root (string) -> bool`, `cp_drive (string) -> string`.
* **Name parts:** `cp_basename`, `cp_dirname`, `cp_ext`, `cp_stem` (all `(string) -> string`), `cp_has_ext (string) -> bool`, `cp_has_suffix (string, string) -> bool`, `cp_suffixes (string) -> list of string`, `cp_with_filename (string, string) -> string`.
* **Structure:** `cp_normalize (string) -> string`, `cp_parent (string) -> maybe string`, `cp_split (string) -> list of string`, `cp_join (list of string) -> string`, `cp_components (string) -> list of string`, `cp_has_component (string, string) -> bool`, `cp_change_ext (string, string) -> string`, `cp_add_ext (string, string) -> string`, `cp_relative_to (string, string) -> maybe string`.
* **Predicates and glob:** `cp_is_hidden`, `cp_is_unc`, `cp_has_wildcard` (all `(string) -> bool`), `cp_matches (string, string) -> bool`, `cp_glob_match (string, string) -> bool` (the `antiquus` block).
* **Environment:** `cp_cwd () -> string`, `cp_expand_user (string) -> string`, `cp_absolute (string) -> string`.
* **Test-only (private `# --- Tests ---` harness):** `_cp_test_join`, `_cp_expect_int`, `_cp_expect_str`, `_cp_expect_true`.
