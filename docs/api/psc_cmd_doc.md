# psc.cmd.doc

> Source: `src/psc/cmd/doc.pengu`

psc/cmd/doc.pengu — `psc doc` (Markdown básico F6).

---

### `print_help`

> **print_help**() -> void

 Ayuda.

 ## Memoria
 No asigna.

### `copy`

> **copy**(s: string) -> string

 Copia owned.

 ## Memoria
 Devuelve string owned.

### `find_root`

> **find_root**(start: string) -> string

 Busca el manifiesto.

 ## Memoria
 Devuelve string owned o `""`.

### `starts_with`

> **starts_with**(s: string, p: string) -> bool

 `true` si `s` empieza por `p`.

 ## Memoria
 O(p).

### `ends_with`

> **ends_with**(s: string, p: string) -> bool

 `true` si `s` termina en `p`.

 ## Memoria
 O(p).

### `is_decl`

> **is_decl**(line: string) -> bool

 `true` si `line` declara un símbolo documentable.

### `signature_of`

> **signature_of**(line: string) -> string

 Firma legible de una declaración.

 ## Memoria
 Devuelve string owned.

### `is_documentable`

> **is_documentable**(kind: SemaSymbolKind) -> bool

 `true` si el símbolo se documenta.

 ## Memoria
 No asigna.

### `append_type_details`

> **append_type_details**(sb: ref to StringBuilder, p: ref to SemaProgram, ty: SemaType) -> void

 Añade campos de una runa/echo o variantes de un omen.

 ## Memoria
 No retiene; los strings auxiliares se liberan.

### `trim_text`

> **trim_text**(s: string) -> string

 Recorta espacios y tabuladores en los extremos.

 ## Memoria
 Devuelve una vista de `s`.

### `module_doc`

> **module_doc**(path: string) -> string

 Docstring de módulo: bloque `##` inicial del archivo.

 Es el comentario `##` que abre el archivo, antes de imports y directivas.
 Si el archivo empieza por `#` (doc antigua) o por código, no hay docstring.

 ## Memoria
 Devuelve string owned o `""`.

### `render_file`

> **render_file**(path: string, rel: string, title: string, p: ref to SemaProgram) -> string

 Renderiza un archivo a Markdown desde los símbolos del checker.

 ## Memoria
 Devuelve string owned.

### `doc_name`

> **doc_name**(rel: string, sep: char) -> string

 Nombre documental a partir del path relativo.

 Sustituye los separadores de directorio por `sep` y quita `.pengu`.
 Se usa con `_` para el nombre de página y con `.` para el título.

 ## Memoria
 Devuelve string owned.

### `run_doc`

> **run_doc**(args: list of string) -> int

 Implementa `psc doc`.

 ## Memoria
 Libera ParseResult.

