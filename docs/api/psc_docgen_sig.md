# psc.docgen.sig

> Source: `src/psc/docgen/sig.pengu`

psc/docgen/sig.pengu — firmas y docs desde símbolos F3.

Se usa como enriquecimiento del render textual: el nombre de la declaración
se busca en la tabla de símbolos y, si existe, la firma y el doc salen del
checker (tipos resueltos, defaults, genéricos).

---

### `nid_of`

> **nid_of**(p: ref to SemaProgram, name: string) -> int

 `NameId` de un texto.

### `symbol_of`

> **symbol_of**(p: ref to SemaProgram, name: string) -> int

 Símbolo por nombre (`-1` si no).

### `nt`

> **nt**(p: ref to SemaProgram, id: int) -> string

 Texto de un `NameId` (prestado).

### `type_into`

> **type_into**(tt: ref to SemaTypeTable, p: ref to SemaProgram, id: int, sb: ref to StringBuilder) -> void

 Renderiza un tipo.

### `type_text`

> **type_text**(p: ref to SemaProgram, type_id: int) -> string

 Texto canónico de un `TypeId` (`""` si no es válido).

 ## Memoria
 Devuelve string owned.

### `signature_for_symbol`

> **signature_for_symbol**(p: ref to SemaProgram, sid: int) -> string

 Firma de un símbolo por id (`""` si no es documentable).

 ## Memoria
 Devuelve string owned.

### `signature_for`

> **signature_for**(p: ref to SemaProgram, name: string) -> string

 Firma resuelta para un nombre; `""` si no es símbolo documentable.

### `doc_for_symbol`

> **doc_for_symbol**(p: ref to SemaProgram, sid: int) -> string

 Doc comment de un símbolo por id (`""` si no tiene).

 ## Memoria
 Devuelve string prestado del pool.

### `doc_for`

> **doc_for**(p: ref to SemaProgram, name: string) -> string

 Doc comment resuelto para un nombre (prestado; `""` si no).

