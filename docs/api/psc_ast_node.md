# psc.ast.node

> Source: `src/psc/ast/node.pengu`

psc/ast/node.pengu — arena plana del AST.

El AST guarda nodos POD en `nodes` y una lista plana de hijos en `children`.
Cada hijo se codifica en un entero para no necesitar un `PsNode` por token:

| Valor | Significado |
|---:|---|
| `0` | hijo ausente (`None` de stage0) |
| `> 0` | nodo `id = valor - 1` |
| `< 0` | token `id = -valor - 1` |

Los nodos se crean en **post-orden** (hijos antes que el padre). Así los
hijos de un nodo son siempre contiguos en `children`, sin obligar a
reservar un `list` por nodo. El parser usa una pila de trabajo
(`Parser.child_stack`/`Parser.marks`) para agruparlos.

## Memoria
`banish ast` libera `nodes`, `children` y `labels`. Los `PsNode` y
`PsLoopLabel` son valores puros.

---

### `PsNode`

> rune PsNode

```pengu
    kind as NodeKind
    start as int
    end as int
    first_child as int
    child_count as int
    aux as int
```

 Un nodo del AST.

 `start`/`end` son offsets de byte half-open. `first_child`/`child_count`
 indexan `PsAst.children`. `aux` es un payload por tipo de nodo (por ejemplo,
 el token del operador en un nodo binario); `0` cuando no aplica.

 ## Memoria
 Valor puro: no tiene heap.

### `PsLoopLabel`

> rune PsLoopLabel

```pengu
    node as int
    token as int
```

 Etiqueta de un loop (`outer: for ...`).

 ## Memoria
 Valor puro.

### `PsAst`

> rune PsAst

```pengu
    nodes as list of PsNode
    children as list of int
    labels as list of PsLoopLabel
```

 Arena del AST.

 ## Memoria
 `banish ast` libera las tres listas.

### `ps_ast_new`

> **ps_ast_new**() -> PsAst

 Construye un AST vacío.

 ## Memoria
 Asigna las tres listas; liberar con `banish`.

### `ps_enc_node`

> **ps_enc_node**(id: int) -> int

 Codifica un id de nodo como hijo.

 ## Memoria
 O(1), no asigna.

### `ps_enc_token`

> **ps_enc_token**(id: int) -> int

 Codifica un índice de token como hijo.

 ## Memoria
 O(1), no asigna.

### `ps_child_is_node`

> **ps_child_is_node**(c: int) -> bool

 `true` si el hijo codificado referencia un nodo.

 ## Memoria
 O(1), no asigna.

### `ps_child_is_token`

> **ps_child_is_token**(c: int) -> bool

 `true` si el hijo codificado referencia un token.

 ## Memoria
 O(1), no asigna.

### `ps_child_node_id`

> **ps_child_node_id**(c: int) -> int

 Id de nodo de un hijo codificado, o `-1` si no es nodo.

 ## Memoria
 O(1), no asigna.

### `ps_child_token_id`

> **ps_child_token_id**(c: int) -> int

 Índice de token de un hijo codificado, o `-1` si no es token.

 ## Memoria
 O(1), no asigna.

### `node_count`

> **node_count**() -> int

 Número de nodos.

### `child_total`

> **child_total**() -> int

 Número de hijos almacenados.

### `node_new`

> **node_new**(kind: NodeKind, start: int, end: int, first_child: int, child_count: int, aux: int) -> int

 Crea un nodo con un rango de hijos ya copiado en `children`.

 El parser no llama a esto directamente: usa
 `Parser.finish_node`, que copia la pila de trabajo.

 ## Memoria
 Hace `push` en `nodes`; no asigna por nodo.

### `add_encoded_child`

> **add_encoded_child**(c: int) -> void

 Añade un hijo ya codificado al final de `children`.

 ## Memoria
 Hace `push`; no asigna por hijo.

### `node_at`

> **node_at**(id: int) -> PsNode

 Devuelve el nodo `id`.

 ## Memoria
 Devuelve una copia POD; no asigna.

### `kind_of`

> **kind_of**(id: int) -> NodeKind

 Tipo de un nodo.

 ## Memoria
 O(1), no asigna.

### `span_of`

> **span_of**(id: int) -> ByteSpan

 Span de un nodo.

 ## Memoria
 Devuelve una copia POD; no asigna.

### `child_count_of`

> **child_count_of**(id: int) -> int

 Número de hijos de un nodo.

 ## Memoria
 O(1), no asigna.

### `child_of`

> **child_of**(id: int, slot: int) -> int

 Hijo codificado en una posición, o `0` si está fuera de rango.

 ## Memoria
 O(1), no asigna.

### `child_node_of`

> **child_node_of**(id: int, slot: int) -> int

 Id de nodo de un hijo, o `-1` si es token/ausente.

 ## Memoria
 O(1), no asigna.

### `child_token_of`

> **child_token_of**(id: int, slot: int) -> int

 Índice de token de un hijo, o `-1` si es nodo/ausente.

 ## Memoria
 O(1), no asigna.

### `add_label`

> **add_label**(node: int, token: int) -> void

 Añade una etiqueta de loop.

 ## Memoria
 Hace `push` en `labels`.

### `label_of`

> **label_of**(node: int) -> int

 Token de la etiqueta de un nodo, o `-1` si no tiene.

 ## Memoria
 Búsqueda lineal; los labels son raros.

