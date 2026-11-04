# psc.sema.ast

> Source: `src/psc/sema/ast.pengu`

psc/sema/ast.pengu — acceso de solo lectura al AST de F2.

El checker no conoce la codificación de hijos: estas funciones devuelven IDs
de nodo (`-1` si el hijo es token/ausente) o índices de token (`-1` si es
nodo/ausente). El texto de un token se copia porque `SourceFile.slice`
devuelve un string owned; el llamador lo libera.

## Memoria
`token_text` devuelve un string owned; el resto es POD o un préstamo.

---

### `kind_of`

> **kind_of**(ast: ref to PsAst, id: int) -> NodeKind

 Tipo de un nodo.

 ## Memoria
 O(1).

### `start_of`

> **start_of**(ast: ref to PsAst, id: int) -> int

 Inicio de byte.

 ## Memoria
 O(1).

### `end_of`

> **end_of**(ast: ref to PsAst, id: int) -> int

 Fin de byte.

 ## Memoria
 O(1).

### `child_count`

> **child_count**(ast: ref to PsAst, id: int) -> int

 Número de hijos.

 ## Memoria
 O(1).

### `ast_child_at`

> **ast_child_at**(ast: ref to PsAst, id: int, slot: int) -> int

 Hijo codificado.

 ## Memoria
 O(1).

### `node_child`

> **node_child**(ast: ref to PsAst, id: int, slot: int) -> int

 ID de nodo hijo, o `-1`.

 ## Memoria
 O(1).

### `token_child`

> **token_child**(ast: ref to PsAst, id: int, slot: int) -> int

 Índice de token hijo, o `-1`.

 ## Memoria
 O(1).

### `is_absent`

> **is_absent**(ast: ref to PsAst, id: int, slot: int) -> bool

 `true` si el hijo está ausente (`0`).

 ## Memoria
 O(1).

### `token_text`

> **token_text**(src: ref to SourceFile, lex: ref to LexResult, idx: int) -> string

 Texto de un token por índice.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `child_token_text`

> **child_token_text**(src: ref to SourceFile, lex: ref to LexResult, ast: ref to PsAst, id: int, slot: int) -> string

 Texto del token hijo `slot`.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `first_token_text`

> **first_token_text**(src: ref to SourceFile, lex: ref to LexResult, ast: ref to PsAst, id: int) -> string

 Texto del primer token hijo.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `has_child`

> **has_child**(ast: ref to PsAst, id: int, slot: int) -> bool

 `true` si el nodo tiene un hijo en `slot`.

 ## Memoria
 O(1).

### `child_token_kind`

> **child_token_kind**(lex: ref to LexResult, ast: ref to PsAst, id: int, slot: int) -> TokenKind

 Tipo de token de un hijo.

 ## Memoria
 O(1).

### `token_at`

> **token_at**(lex: ref to LexResult, idx: int) -> Token

 Token completo de un índice.

 ## Memoria
 Copia POD.

### `loop_label_token`

> **loop_label_token**(ast: ref to PsAst, id: int) -> int

 Token del label de loop del nodo, o `-1`.

 ## Memoria
 O(labels); no asigna.

### `label_text_exists`

> **label_text_exists**(src: ref to SourceFile, lex: ref to LexResult, ast: ref to PsAst, name: string) -> bool

 ¿Hay algún loop con el label `name` en el AST?

 ## Memoria
 O(labels); copia el texto para comparar.

### `label_text_in_range`

> **label_text_in_range**(src: ref to SourceFile, lex: ref to LexResult, ast: ref to PsAst, name: string, start: int, end: int) -> bool

 ¿Hay un loop con label `name` cuyo token cae en `[start,end)`?

 ## Memoria
 O(labels); copia el texto para comparar.

