# psc.sema.check.lint

> Source: `src/psc/sema/check/lint.pengu`

psc/sema/check/lint.pengu — lints opcionales del checker.

De momento hay uno solo: `W0008`, detrás de `--lint=cow`.

La heurística marca copiar un contenedor y mutar la copia dentro de un
bucle. El programa sigue siendo correcto (COW lo hace seguro), pero paga
una clonación del búfer por vuelta: mover la copia fuera del bucle, o
limpiar y rellenar el mismo contenedor, evita el coste.

El lint es **opt-in** a propósito: sin el flag, ningún proyecto ve avisos
nuevos.

---

### `is_mutating_method`

> **is_mutating_method**(name: string) -> bool

 `true` si el nombre de método muta el contenedor.

 `push`/`append` y `put`/`insert` añaden, `remove`/`clear` quitan; en los
 cuatro casos el receptor necesita un búfer exclusivo.

 ## Memoria
 Compara literales; no asigna.

### `lint_cow_loops`

> **lint_cow_loops**(s: ref to SemaState, body: int) -> void

 Recorre el cuerpo buscando bucles y aplica la heurística a cada uno.

 ## Memoria
 O(profundidad del AST); no retiene nodos.

### `walk_loops`

> **walk_loops**(s: ref to SemaState, node: int) -> void

 Desciende el AST y llama a `lint_loop` en cada bucle.

 ## Memoria
 Recursión acotada por la profundidad del AST.

### `child_text`

> **child_text**(s: ref to SemaState, node: int, slot: int) -> string

 Texto del token `slot` de un nodo, o `""`.

 ## Memoria
 Devuelve owned; el llamador lo libera.

### `type_node_is_cow`

> **type_node_is_cow**(s: ref to SemaState, tnode: int) -> bool

 `true` si el nodo de tipo nombra `list`, `map` o `string`.

 Se mira la forma sintáctica (no el tipo resuelto) para que el lint funcione
 también en tipos genéricos aún sin instanciar.

 ## Memoria
 Libera el texto que pide; no retiene nada.

### `scan_loop`

> **scan_loop**(s: ref to SemaState, node: int, decls: ref to list of int, muts: ref to list of string) -> void

 Acumula copias (`var x is y`) y receptores mutados del subárbol.

 ## Memoria
 Empuja en las listas del llamador; no libera nada.

### `lint_loop`

> **lint_loop**(s: ref to SemaState, loop: int) -> void

 Aplica la heurística a un bucle concreto.

 ## Memoria
 Listas locales liberadas con `banish`.

