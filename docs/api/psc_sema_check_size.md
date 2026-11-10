# psc.sema.check.size

> Source: `src/psc/sema/check/size.pengu`

psc/sema/check/size.pengu — tipos de tamaño finito (E0050).

Un rune (o echo) no puede contenerse a sí mismo por valor: el `struct` de C
saldría con tamaño infinito. El chequeo recorre el grafo de "contiene por
valor" y, cuando encuentra un ciclo, lo reporta con la cadena completa
(`A -> B -> A`).

Cubre las dos formas de crear un ciclo:

- `fundere`: `rune A fundere A:` o `rune A fundere B:` + `rune B fundere A:`.
- `cyclus` con un campo del propio tipo: `rune Node cyclus: next as Node`.

La indirección rompe el ciclo: `ref to T`, `frozen ref to T`, `list of T`,
`map of K to V`, `slice of T`, `many T` y los handles de `std.consortium`
(`Rc`/`Arc`/`Weak`, que guardan un `ref` por dentro) no cuentan como
contención por valor.

## Memoria
Presta el programa; crea `SemaState` por módulo al diagnosticar.

---

### `SIZE_UNVISITED`

> **SIZE_UNVISITED** : int

 Color de un tipo en el DFS de tamaños.

### `SIZE_ACTIVE`

> **SIZE_ACTIVE** : int

_Undocumented._

### `SIZE_DONE`

> **SIZE_DONE** : int

_Undocumented._

### `SIZE_MAX_DEPTH`

> **SIZE_MAX_DEPTH** : int

 Tope de profundidad; un ciclo real se detecta mucho antes.

### `check_all_sizes`

> **check_all_sizes**(p: ref to SemaProgram) -> void

 Comprueba que ningún tipo nominal tenga tamaño infinito.

 ## Memoria
 Presta el programa; libera las listas temporales al terminar.

### `contains_by_value`

> **contains_by_value**(t: SemaType) -> bool

 ¿Este tipo contiene sus hijos por valor?

 ## Memoria
 Compara variantes; no asigna.

### `size_walk`

> **size_walk**(p: ref to SemaProgram, color: ref to list of int, chain: ref to list of int, ty: int, depth: int) -> bool

 Recorre un tipo y devuelve `true` si encuentra un ciclo.

 `chain` lleva la pila de nominales abiertos, en orden.

 ## Memoria
 Presta `color`/`chain`; no asigna.

### `size_walk_children`

> **size_walk_children**(p: ref to SemaProgram, color: ref to list of int, chain: ref to list of int, t: SemaType, depth: int) -> bool

 Recorre los campos (o el payload de cada variante) de un nominal.

 ## Memoria
 Presta `color`/`chain`; no asigna.

### `report_size_cycle`

> **report_size_cycle**(p: ref to SemaProgram, chain: ref to list of int, back: int) -> void

 Reporta el ciclo `A -> B -> A` en la declaración del tipo que lo cierra.

 ## Memoria
 Crea un `SemaState` por módulo y strings owned; los libera.

