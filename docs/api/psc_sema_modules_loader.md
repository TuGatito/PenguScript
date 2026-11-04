# psc.sema.modules.loader

> Source: `src/psc/sema/modules/loader.pengu`

psc/sema/modules/loader.pengu — carga de un módulo con F1 + F2.

`SemaModule` es el bundle que posee todo lo que necesita el checker de un
archivo: `SourceFile`, `LexResult` y `PsParseResult` (que a su vez posee el
AST). El `DiagnosticBag` es compartido por el programa para conservar el
orden de diagnósticos entre módulos.

## Memoria
`load_module` devuelve un `SemaModule` owned. `free_module` libera parse,
lex, fuente y path en ese orden. El bag es prestado y no se libera aquí.

---

### `SemaInterp`

> rune SemaInterp

```pengu
    node as int
    part_start as int
    part_end as int
    parse as InterpParseResult
    annotations as SemaAnnotations
```

 Interpolación `{expr}` de un literal string, ya parseada e inferida.

 Se conserva para que el codegen no tenga que re-parsear ni re-inferir la
 expresión: usa el AST y las anotaciones que produjo el sema.

### `SemaModule`

> rune SemaModule

```pengu
    path as string
    canonical_path as string
    source as SourceFile
    source_text as string
    lex as LexResult
    parse as PsParseResult
    ok as bool
    id as int
    is_entry as bool
    is_std as bool
    insignia as int
    insignia_pos as int
    depth as int
    annotations as SemaAnnotations
    scope as int
    type_ids as map of int to int
    companion_for as int
    interps as list of SemaInterp
```

 Un módulo cargado.

 ## Memoria
 Sin `derive Nexus`: `free_module` libera cada campo.

### `free_module`

> **free_module**(m: ref to SemaModule) -> void

 Libera un módulo.

 ## Memoria
 Libera el AST, los tokens, la fuente y el path.

### `load_module`

> **load_module**(path: string, display: string, bag: ref to DiagnosticBag, is_entry: bool, is_std: bool, depth: int) -> SemaModule

 Carga un archivo desde disco.

 `path` es la ruta de sistema (canónica, la que se lee). `display` es la ruta
 que se guarda en el módulo y se usa en `#line`/diagnósticos; puede ser
 relativa al proyecto.

 Si la lectura falla, emite `E0004` y devuelve un módulo vacío con `ok=false`.

 ## Memoria
 Devuelve un módulo owned; liberar con `free_module`.

### `load_text`

> **load_text**(path: string, display: string, text: string, bag: ref to DiagnosticBag, readable: bool, is_entry: bool, is_std: bool, depth: int) -> SemaModule

 Carga un módulo desde texto (para tests/LSP).

 `path` es la ruta de sistema; `display` la ruta lógica (diagnósticos/`#line`).

 ## Memoria
 Devuelve un módulo owned; liberar con `free_module`.

### `empty_module`

> **empty_module**(path: string, display: string, bag: ref to DiagnosticBag, readable: bool, is_entry: bool, is_std: bool, depth: int) -> SemaModule

 Módulo vacío para una lectura fallida.

 ## Memoria
 Igual que `load_text` pero sin texto; emite E0004.

### `empty_source`

> **empty_source**(path: string) -> SourceFile

 Fuente vacía auxiliar para emitir un diagnóstico de lectura.

 ## Memoria
 Devuelve una fuente owned; el llamador la libera con `banish`.

### `has_ast`

> **has_ast**(m: ref to SemaModule) -> bool

 ¿El módulo tiene AST?

 ## Memoria
 O(1).

