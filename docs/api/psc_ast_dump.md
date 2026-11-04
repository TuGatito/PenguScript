# psc.ast.dump

> Source: `src/psc/ast/dump.pengu`

psc/ast/dump.pengu — volcado canónico del AST.

El formato es estable y determinista; es la base de los golden tests y del
oráculo contra stage0.

```text
# psc-ast-dump v1
# file: <ruta>
# sha256: <hex>
# bytes: <n>
# nodes: <n>
start
  file
    top_stmt
      import_stmt
        dotted_path
          "std"
          "spark"
        _
```

- Nodo: su nombre de stage0 (`ps_node_kind_name`).
- Token: `"texto"` con escapes C.
- Ausente: `_`.
- Loop etiquetado: `for_in_stmt @label "outer"`.
- El cuerpo de un `antiquus` se imprime ya decodificado (dedent).
- CRLF se normaliza a LF solo en el texto del dump.
- No se imprimen posiciones: los spans se prueban aparte.

## Memoria
`dump`/`dump_body` devuelven un `string` owned; liberar con `banish`.

---

### `ps_ast_dump`

> **ps_ast_dump**(src: ref to SourceFile, lex: ref to LexResult, ast: ref to PsAst, root: int) -> string

 Volcado completo con cabecera.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `ps_ast_dump_body`

> **ps_ast_dump_body**(src: ref to SourceFile, lex: ref to LexResult, ast: ref to PsAst, root: int) -> string

 Volcado sin cabecera (oráculo y tests).

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `ps_ast_append_header`

> **ps_ast_append_header**(sb: ref to StringBuilder, src: ref to SourceFile, ast: ref to PsAst) -> void

 Cabecera del dump.

 ## Memoria
 Escribe en el builder; no asigna.

### `ps_ast_dump_node`

> **ps_ast_dump_node**(sb: ref to StringBuilder, src: ref to SourceFile, lex: ref to LexResult, ast: ref to PsAst, id: int, depth: int) -> void

 Escribe un nodo y sus hijos.

 ## Memoria
 Recursión acotada por el AST (máximo de parseo 512).

### `ps_ast_token_text`

> **ps_ast_token_text**(src: ref to SourceFile, lex: ref to LexResult, index: int) -> string

 Texto de un token del AST.

 Para `antiquus` devuelve el cuerpo decodificado; para el resto, el lexema
 crudo del fuente.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `ps_ast_indent`

> **ps_ast_indent**(sb: ref to StringBuilder, depth: int) -> void

 Añade `depth` niveles de indentación (dos espacios cada uno).

 ## Memoria
 O(depth), no asigna.

### `ps_ast_newline`

> **ps_ast_newline**(sb: ref to StringBuilder) -> void

 Añade un newline.

 ## Memoria
 O(1), no asigna.

### `ps_ast_append_quoted`

> **ps_ast_append_quoted**(sb: ref to StringBuilder, s: string) -> void

 Añade `s` entre comillas, con escapes C y CRLF normalizado.

 ## Memoria
 O(bytes), sin temporales owned.

### `ps_ast_append_hex_byte`

> **ps_ast_append_hex_byte**(sb: ref to StringBuilder, b: int) -> void

 Añade dos dígitos hex de un byte.

 ## Memoria
 O(1), no asigna.

### `ps_ast_hex_char`

> **ps_ast_hex_char**(n: int) -> int

 Valor ASCII de un nibble hex.

 ## Memoria
 O(1), no asigna.

