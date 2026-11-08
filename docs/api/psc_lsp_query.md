# psc.lsp.query

> Source: `src/psc/lsp/query.pengu`

psc/lsp/query.pengu — consultas semánticas para el servidor LSP.

El LSP no debe reimplementar el parser ni adivinar tipos desde el texto.
Este módulo expone las consultas mínimas sobre `SemaProgram`: símbolo bajo
una posición, tipo, documentación, exports, módulos y tamaño aproximado.

---

### `module_at`

> **module_at**(p: ref to SemaProgram, path: string) -> int

 Módulo cargado para un path (`-1` si no).

### `module_for_uri_path`

> **module_for_uri_path**(p: ref to SemaProgram, path: string) -> int

 Módulo cargado para el path absoluto de un documento.

### `symbol_count`

> **symbol_count**(p: ref to SemaProgram) -> int

 Número de símbolos del programa.

### `symbol_at`

> **symbol_at**(p: ref to SemaProgram, sid: int) -> SemaSymbol

 Símbolo por id (`-1` si no).

### `symbol_name_id`

> **symbol_name_id**(p: ref to SemaProgram, sid: int) -> int

 `NameId` de un símbolo.

### `symbol_name`

> **symbol_name**(p: ref to SemaProgram, sid: int) -> string

 Texto del nombre de un símbolo (prestado).

### `symbol_type`

> **symbol_type**(p: ref to SemaProgram, sid: int) -> int

 Tipo de un símbolo.

### `symbol_doc`

> **symbol_doc**(p: ref to SemaProgram, sid: int) -> string

 Doc de un símbolo (`""` si no).

### `type_text`

> **type_text**(p: ref to SemaProgram, type_id: int) -> string

 Texto canónico de un tipo.

### `signature_for`

> **signature_for**(p: ref to SemaProgram, sid: int) -> string

 Firma de un símbolo (`""` si no aplica).

### `node_type`

> **node_type**(p: ref to SemaProgram, mid: int, node: int) -> int

 Tipo de un nodo anotado (`-1` si no).

### `node_symbol`

> **node_symbol**(p: ref to SemaProgram, mid: int, node: int) -> int

 Símbolo de un nodo anotado (`-1` si no).

### `node_at`

> **node_at**(p: ref to SemaProgram, mid: int, offset: int) -> int

 Nodo AST más pequeño que contiene `offset` (`-1` si no).

### `is_word_char`

> **is_word_char**(c: int) -> bool

 `true` si `c` es carácter de identificador.

### `word_at`

> **word_at**(text: string, offset: int) -> string

 Palabra (identificador) bajo un offset.

### `is_public`

> **is_public**(p: ref to SemaProgram, sid: int) -> bool

 `true` si el símbolo es público/documentable.

### `symbol_by_name`

> **symbol_by_name**(p: ref to SemaProgram, mid: int, name: string, offset: int) -> int

 Símbolo que declara `name` en el módulo, el más cercano antes de `offset`.

### `symbol_at_offset`

> **symbol_at_offset**(p: ref to SemaProgram, mid: int, text: string, offset: int) -> int

 Símbolo bajo un offset (declaración o uso anotado).

### `type_at_offset`

> **type_at_offset**(p: ref to SemaProgram, mid: int, text: string, offset: int) -> int

 Tipo bajo un offset (`-1` si no).

### `module_symbols`

> **module_symbols**(p: ref to SemaProgram, mid: int) -> list of int

 Ids de símbolos declarados por un módulo.

### `module_for_scope`

> **module_for_scope**(p: ref to SemaProgram, scope_id: int) -> int

 Módulo cuyo scope global es `scope_id` (`-1` si no).

### `module_exports`

> **module_exports**(p: ref to SemaProgram, mid: int) -> list of int

 Exports de un módulo importado.

### `import_aliases`

> **import_aliases**(p: ref to SemaProgram, mid: int) -> list of string

 Alias de imports del módulo.

### `imported_module`

> **imported_module**(p: ref to SemaProgram, mid: int, alias: string) -> int

 Módulo importado por un alias (`-1` si no).

### `std_dirs`

> **std_dirs**(p: ref to SemaProgram) -> list of string

 Directorios de stdlib configurados.

### `type_size`

> **type_size**(p: ref to SemaProgram, type_id: int) -> int

 Tamaño en bytes de un tipo con el layout C del ABI v3 (64-bit, con padding).

 El cálculo vive en `layout.pengu`; aquí sólo se conserva la firma histórica
 que usa el resto del LSP.

### `type_size_at`

> **type_size_at**(p: ref to SemaProgram, type_id: int, depth: int) -> int

 Implementación recursiva de `type_size` (compatibilidad).

### `is_builtin_type_name`

> **is_builtin_type_name**(nm: string) -> bool

 `true` si `nm` es el nombre de un tipo incorporado.

### `receiver_type_at`

> **receiver_type_at**(p: ref to SemaProgram, mid: int, text: string, dot: int) -> int

 Tipo del receptor de `receptor.miembro` a partir del offset del punto.

 Usa el nodo AST que termina justo antes del punto; si no tiene anotación,
 cae al símbolo de la palabra. Devuelve `-1` si no se puede resolver.

### `nominal_base`

> **nominal_base**(p: ref to SemaProgram, ty: int) -> string

 Métodos de encantamiento aplicables a un tipo.

 Incluye los métodos exactos del receptor y los métodos genéricos (aquellos
 cuyo receptor es un `shard T`), que se resuelven en la llamada.
 Nombre base del nominal de un tipo (`""` si no es una runa/eco).

 Sigue `template_info` para que `Rc of Node` y `Rc of T` compartan base.

 ## Memoria
 O(1); devuelve un préstamo del pool de nombres.

### `methods_for_type`

> **methods_for_type**(p: ref to SemaProgram, type_id: int) -> list of int

_Undocumented._

### `field_type_at`

> **field_type_at**(p: ref to SemaProgram, type_id: int, name: string) -> int

 Tipo de un campo de `rune`/`echo` (`-1` si no existe).

### `variant_payload_type`

> **variant_payload_type**(p: ref to SemaProgram, type_id: int, name: string) -> int

 Tipo del payload de una variante de `omen` (`-1` si no existe o no lleva payload).

### `symbol_name_start`

> **symbol_name_start**(p: ref to SemaProgram, mid: int, sid: int) -> int

 Offset del nombre de un símbolo dentro de su declaración.

 `si.start` apunta al inicio de la declaración; para hover/rename se necesita
 el identificador. Devuelve `-1` si no se encuentra.

