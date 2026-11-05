# psc.codegen.context

> Source: `src/psc/codegen/context.pengu`

psc/codegen/context.pengu — estado de una emisión C.

El contexto presta el `SemaProgram`; es dueño del nombre table, catálogo,
emisor y scopes C. No muta F3.

---

### `CgLocal`

> rune CgLocal

```pengu
    name as int
    type as int
    c_name as int
```

 Binding local C.

### `CgLambda`

> rune CgLambda

```pengu
    module as int
    node as int
```

 Lambda descubierta en el AST.

### `CgContext`

> rune CgContext

```pengu
    program as ref to SemaProgram
    options as CgOptions
    names as CgNames
    catalog as CgCatalog
    emitter as CgEmitter
    locals as list of CgLocal
    defers as list of int
    errdefers as list of int
    scope_marks as list of int
    err_marks as list of int
    scope_loops as list of bool
    with_targets as list of string
    with_types as list of int
    unsafe_depth as int
    return_type as int
    current_module as int
    current_fn as string
    self_type as int
    self_value as bool
    lambdas as list of CgLambda
    errors as int
    tmp_seq as int
    block_value as weave with c: ref to CgContext, node: int, expected: int into string
```

 Contexto de emisión.

 ## Memoria
 Dueño de names/catalog/emitter/locales; liberar con `free`.

### `block_value_unset`

> **block_value_unset**(c: ref to CgContext, node: int, expected: int) -> string

 Hook por defecto: un bloque en posición de valor sin instalador.

 ## Memoria
 Devuelve un literal owned.

### `new_context`

> **new_context**(p: ref to SemaProgram, o: CgOptions) -> CgContext

 Crea un contexto para un programa.

 ## Memoria
 Asigna tablas/emisor; liberar con `free`.

### `context_free`

> **context_free**(c: ref to CgContext) -> void

 Libera el contexto.

 ## Memoria
 Libera nombres, catálogo, emisor y locals.

### `set_subst`

> **set_subst**(c: ref to CgContext, f: CgFunction) -> void

 Fija la sustitución de type params de una función.

 ## Memoria
 Vacía el mapa anterior.

### `cg_scope_push`

> **cg_scope_push**(c: ref to CgContext, is_loop: bool) -> void

 Abre un scope C para `defer`/`break`/`continue`.

 ## Memoria
 Añade dos marcas POD.

### `cg_scope_pop`

> **cg_scope_pop**(c: ref to CgContext) -> void

 Cierra el scope C actual (el llamador ya emitió sus defers).

 ## Memoria
 Quita dos marcas POD.

### `current_scope_mark`

> **current_scope_mark**(c: ref to CgContext) -> int

 Índice de `defers` donde empieza el scope actual (0 si no hay).

 ## Memoria
 O(1).

### `add_defer`

> **add_defer**(c: ref to CgContext, node: int) -> void

 Registra un `defer` en el scope actual.

 ## Memoria
 Añade un nodo AST (POD).

### `add_errdefer`

> **add_errdefer**(c: ref to CgContext, node: int) -> void

 Registra un `errdefer` en el scope actual.

 ## Memoria
 Añade un nodo AST (POD).

### `push_with`

> **push_with**(c: ref to CgContext, text: string, type_id: int) -> void

 Abre un `with target:` con su expresión C y su tipo.

 ## Memoria
 `text` se transfiere a la pila; se libera al hacer `pop_with`.

### `pop_with`

> **pop_with**(c: ref to CgContext) -> void

 Cierra el `with target:` más interno y libera su texto.

 ## Memoria
 Libera la expresión C transferida por `push_with`.

### `clear_scopes`

> **clear_scopes**(c: ref to CgContext) -> void

 Limpia todos los defers y scopes (nueva función/cuerpo).

 ## Memoria
 Vacía listas; los nodos son del AST.

### `add_local`

> **add_local**(c: ref to CgContext, name: int, type_id: int, c_name: int) -> void

 Añade un local al scope C actual.

 ## Memoria
 Añade a `locals`; el nombre C es un `NameId`.

### `local_type`

> **local_type**(c: ref to CgContext, name: int) -> int

 Busca el tipo de un local.

 ## Memoria
 O(n); scopes pequeños.

### `local_c_name`

> **local_c_name**(c: ref to CgContext, name: int) -> int

 Busca el nombre C de un local.

 ## Memoria
 O(n).

### `clear_locals`

> **clear_locals**(c: ref to CgContext) -> void

 Vacía los locales (fin de función).

 ## Memoria
 O(1).

### `is_c_keyword`

> **is_c_keyword**(s: string) -> bool

 `true` para identificadores que son palabras reservadas de C.

 PenguScript permite parámetros como `default` o `case`; emitirlos tal cual
 produce C inválido. La capa C les añade un sufijo `_` de forma consistente.

 ## Memoria
 No asigna.

### `safe_c_name`

> **safe_c_name**(s: string) -> string

 Nombre C seguro para un identificador de PenguScript.

 Sustituye cualquier byte que no sea `[A-Za-z0-9_]` por `_` (los módulos
 `.d.pengu` producen prefijos como `raylib.d_`) y añade `_` a las palabras
 reservadas de C.

 ## Memoria
 Devuelve string owned.

