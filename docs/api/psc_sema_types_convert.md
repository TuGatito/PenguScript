# psc.sema.types.convert

> Source: `src/psc/sema/types/convert.pengu`

psc/sema/types/convert.pengu — AST de tipo → `TypeId`.

El AST de F2 replica la forma de Lark. Este módulo traduce cada nodo
`*_type` a la tabla plana. Los nombres se resuelven en `SemaSymbols`; un
nombre desconocido produce `E0004` y `TkError` para no encadenar errores.

## Memoria
`TypeCtx` presta todas sus referencias. Los `TypeId` viven en la tabla.

---

### `TypeCtx`

> rune TypeCtx

```pengu
    types as ref to SemaTypeTable
    symbols as ref to SemaSymbols
    names as ref to NamePool
    bag as ref to DiagnosticBag
    src as ref to SourceFile
    lex as ref to LexResult
    ast as ref to PsAst
```

 Contexto de conversión.

 ## Memoria
 Todas las referencias son prestadas.

### `convert`

> **convert**(ctx: ref to TypeCtx, node: int) -> int

 Convierte un nodo de tipo.

 ## Memoria
 Puede añadir tipos y diagnósticos.

### `convert_param`

> **convert_param**(ctx: ref to TypeCtx, node: int) -> int

 Convierte `shard T` en un `TypeParam`.

 ## Memoria
 Añade un tipo param y un tipo.

### `type_has_param`

> **type_has_param**(t: ref to SemaTypeTable, id: int) -> bool

 `true` si un tipo contiene un `TkTypeParam`.

 ## Memoria
 O(profundidad).

### `convert_custom`

> **convert_custom**(ctx: ref to TypeCtx, node: int) -> int

 Convierte un tipo custom (`mod.Name`/`Name` + args).

 ## Memoria
 Puede añadir diagnósticos; devuelve `TkError` si no existe.

### `convert_fn`

> **convert_fn**(ctx: ref to TypeCtx, node: int) -> int

 Convierte una firma `weave with ... into ...`.

 ## Memoria
 Añade params/tipo a la tabla.

### `path_text`

> **path_text**(ctx: ref to TypeCtx, node: int) -> string

 Texto de un `dotted_path`.

 ## Memoria
 Devuelve un string owned.

### `looks_like_type_param`

> **looks_like_type_param**(s: string) -> bool

 ¿El nombre parece un parámetro de tipo (`T`, `A`, `B`)?

 ## Memoria
 O(1).

### `last_component`

> **last_component**(s: string) -> string

 Último componente de un nombre dotted.

 ## Memoria
 Devuelve un string owned.

### `parse_int_aux`

> **parse_int_aux**(s: string) -> maybe int

 Parser de enteros auxiliar para tamaños de array.

 ## Memoria
 Devuelve un maybe; liberar si está presente.

