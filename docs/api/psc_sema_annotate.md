# psc.sema.annotate

> Source: `src/psc/sema/annotate.pengu`

psc/sema/annotate.pengu — anotaciones semánticas por nodo del AST.

`SemaAnnotations.items[node_id]` guarda el tipo inferido, el símbolo
resuelto y un payload auxiliar. F4 consume esta tabla en vez de volver a
inferir. Las anotaciones se inicializan a `-1` y se rellenan on demand.

## Memoria
`SemaAnnotations` es dueño de la lista; `free_annotations` la libera.

---

### `ANN_HAS_TYPE`

> **ANN_HAS_TYPE** : int

 Hay tipo válido en `type_id`.

### `ANN_HAS_SYMBOL`

> **ANN_HAS_SYMBOL** : int

 Hay símbolo resuelto en `symbol_id`.

### `ANN_MUTATING_CALL`

> **ANN_MUTATING_CALL** : int

 Llamada a método `@mutates` reescrita a statement.

### `ANN_TUPLE`

> **ANN_TUPLE** : int

 `type_id`/`aux` describen una tupla.

### `ANN_FN_VALUE`

> **ANN_FN_VALUE** : int

 Es un valor de función/lambda.

### `ANN_BANISH`

> **ANN_BANISH** : int

 El nodo es el target de un `banish`.

### `ANN_JUDGE_CHECKED`

> **ANN_JUDGE_CHECKED** : int

 El nodo ya pasó el chequeo de `judge`.

### `ANN_C_NAME`

> **ANN_C_NAME** : int

 `aux` es el `NameId` del C name resuelto.

### `ANN_BIND_MAYBE`

> **ANN_BIND_MAYBE** : int

 `aux` es el `TypeId` del binding `maybe`.

### `ANN_BIND_ELEM`

> **ANN_BIND_ELEM** : int

 `aux` es el `TypeId` del elemento del binding.

### `SemaAnnotation`

> rune SemaAnnotation

```pengu
    type_id as int
    symbol_id as int
    aux as int
    flags as int
```

 Anotación POD.

### `SemaAnnotations`

> rune SemaAnnotations

```pengu
    items as list of SemaAnnotation
```

 Tabla de anotaciones.

 ## Memoria
 Dueña de `items`.

### `new_annotations`

> **new_annotations**(ast: ref to PsAst) -> SemaAnnotations

 Crea una tabla con una entrada por nodo.

 ## Memoria
 Asigna la lista; liberar con `free_annotations`.

### `free_annotations`

> **free_annotations**(a: ref to SemaAnnotations) -> void

 Libera la tabla.

 ## Memoria
 Libera la lista.

### `get`

> **get**(a: ref to SemaAnnotations, node: int) -> SemaAnnotation

 Obtiene la anotación de un nodo.

 ## Memoria
 Copia POD.

### `set`

> **set**(a: ref to SemaAnnotations, node: int, v: SemaAnnotation) -> void

 Guarda una anotación.

 ## Memoria
 O(1).

### `set_type`

> **set_type**(a: ref to SemaAnnotations, node: int, type_id: int) -> void

 Marca el tipo de un nodo.

 ## Memoria
 O(1).

### `type_of`

> **type_of**(a: ref to SemaAnnotations, node: int) -> int

 Tipo de un nodo (`-1` si no).

 ## Memoria
 O(1).

### `ann_set_symbol`

> **ann_set_symbol**(a: ref to SemaAnnotations, node: int, symbol: int) -> void

 Marca el símbolo resuelto de un nodo.

 ## Memoria
 O(1).

### `symbol_of`

> **symbol_of**(a: ref to SemaAnnotations, node: int) -> int

 Símbolo de un nodo (`-1` si no).

 ## Memoria
 O(1).

### `add_flag`

> **add_flag**(a: ref to SemaAnnotations, node: int, flag: int) -> void

 Marca un flag.

 ## Memoria
 O(1).

### `set_aux`

> **set_aux**(a: ref to SemaAnnotations, node: int, aux: int) -> void

 Guarda el auxiliar.

 ## Memoria
 O(1).

