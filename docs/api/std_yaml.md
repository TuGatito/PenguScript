# std.yaml

> Source: `std/yaml.pengu`

std.yaml.pengu — the YAML subset used by legacy `pengu.yaml` manifests.

TOML is the canonical manifest format, but `pengu.yaml`/`pengu.yml` remain
supported.  The Python fallback parser is a ~35-line indentation walker, not
a YAML implementation; this module ports exactly that subset:

- `key: value` scalars;
- `key:` sections nested by indentation;
- inline arrays `key: [a, b, "c"]`;
- `#` comments and blank lines;
- quoted or bare scalars.

Anchors, aliases, multi-document streams, block scalars and complex keys are
deliberately out of scope, matching the existing fallback (and documenting
that fact instead of silently accepting them).

## Example
```pengu
import std.yaml
import std.spark

weave main into int:
    let doc as result of list of yaml.YamlEntry to string is calling yaml.parse with "project:\n  name: demo\n"
    if doc.is_ok:
        calling spark.println with (calling yaml.get with doc.value, "project.name")
        calling yaml.free_entries with doc.value
    return 0
```

## Memoria
The returned list and every `YamlEntry` string are owned. Release them with
`free_entries`; getters return owned copies.

---

### `YAML_VERSION`

> **YAML_VERSION** : string

 std.yaml.pengu — the YAML subset used by legacy `pengu.yaml` manifests.

 TOML is the canonical manifest format, but `pengu.yaml`/`pengu.yml` remain
 supported.  The Python fallback parser is a ~35-line indentation walker, not
 a YAML implementation; this module ports exactly that subset:

 - `key: value` scalars;
 - `key:` sections nested by indentation;
 - inline arrays `key: [a, b, "c"]`;
 - `#` comments and blank lines;
 - quoted or bare scalars.

 Anchors, aliases, multi-document streams, block scalars and complex keys are
 deliberately out of scope, matching the existing fallback (and documenting
 that fact instead of silently accepting them).

 ## Example
 ```pengu
 import std.yaml
 import std.spark

 weave main into int:
     let doc as result of list of yaml.YamlEntry to string is calling yaml.parse with "project:\n  name: demo\n"
     if doc.is_ok:
         calling spark.println with (calling yaml.get with doc.value, "project.name")
         calling yaml.free_entries with doc.value
     return 0
 ```

 ## Memoria
 The returned list and every `YamlEntry` string are owned. Release them with
 `free_entries`; getters return owned copies.

### `YamlEntry`

> alias YamlEntry

 One flattened YAML key/value pair.  The shape intentionally matches
 `toml.TomlEntry` so manifest consumers can share one code path.

### `parse`

> **parse**(text: string) -> result of list of YamlEntry to string

 Parses the supported YAML subset.

### `parse_file`

> **parse_file**(path: string) -> result of list of YamlEntry to string

 Parses a YAML file.

### `free_entries`

> **free_entries**(entries: list of YamlEntry) -> void

 Releases every string in `entries` and then the list.

### `find`

> **find**(entries: list of YamlEntry, key: string) -> int

 Returns the index of `key`, or -1.

### `get`

> **get**(entries: list of YamlEntry, key: string) -> string

 Returns an owned copy of `key`'s value ("" when absent).

### `free_strings`

> **free_strings**(values: list of string) -> void

 Releases a list of strings returned by an array helper.

### `get_array`

> **get_array**(entries: list of YamlEntry, key: string) -> list of string

 Returns every element of `key[0]`, `key[1]`, ... as owned strings.

### `_yaml_copy`

> **_yaml_copy**(s: string) -> string

 ----------------------------------------------------------------------------
 Helpers
 ----------------------------------------------------------------------------

### `_yaml_strdup`

> **_yaml_strdup**(s: string) -> string

_Undocumented._

### `_yaml_free_stack`

> **_yaml_free_stack**(paths: list of string, indents: list of int) -> void

_Undocumented._

### `_yaml_indent`

> **_yaml_indent**(raw: string) -> int

_Undocumented._

### `_yaml_strip_comment`

> **_yaml_strip_comment**(raw: string) -> string

_Undocumented._

### `_yaml_find_colon`

> **_yaml_find_colon**(s: string) -> int

_Undocumented._

### `_yaml_join_path`

> **_yaml_join_path**(parent: string, key: string) -> string

_Undocumented._

### `_yaml_unquote`

> **_yaml_unquote**(s: string) -> string

_Undocumented._

### `_yaml_scalar_kind`

> **_yaml_scalar_kind**(value: string) -> int

_Undocumented._

