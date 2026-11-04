# psc.sema.names

> Source: `src/psc/sema/names.pengu`

psc/sema/names.pengu — internado de nombres y textos semánticos.

Todo nombre que sobrevive al análisis (`SemaType.name`, `SemaSymbol.name`,
nombres C, docs, textos de `type of`) se guarda una sola vez aquí y se
referencia con un `NameId` (`int`). Esto evita duplicar strings en cada
símbolo/tipo y hace que el dump semántico sea determinista.

## Memoria
`NamePool` es dueño de cada string de `strings` y del mapa `ids`.
`free_pool` libera ambos; `text` presta el string (no lo liberes).

## Ejemplo
```pengu
var pool as NamePool is calling new_pool
var id as int is calling intern with (sigil of pool), "Point"
calling spark.println with calling text with (sigil of pool), id
calling free_pool with (sigil of pool)
```

---

### `_copy_string`

> **_copy_string**(s: string) -> string

 Copia owned de un string.

 ## Motivo
 `intern` debe ser el único dueño del texto: el llamador conserva su string
 temporal y lo libera. Un `push` normal copiaría solo la cabecera y dejaría
 el pool apuntando a memoria liberada.

 ## Memoria
 Devuelve un buffer owned; liberar con `banish`.

### `copy_string`

> **copy_string**(s: string) -> string

 Copia owned de un string para quien necesite una clave estable.

 ## Memoria
 Devuelve un buffer owned; liberar con `banish`.

### `NamePool`

> rune NamePool

```pengu
    strings as list of string
    ids as map of string to int
```

 Pool de nombres internados.

 ## Memoria
 Sin `derive Nexus`: los strings de `strings` necesitan `banish` individual
 antes de liberar la lista. Usar `free_pool`.

### `new_pool`

> **new_pool**() -> NamePool

 Crea un pool vacío.

 ## Memoria
 Asigna la lista y el mapa; liberar con `free_pool`.

### `free_pool`

> **free_pool**(pool: ref to NamePool) -> void

 Libera todos los nombres y el índice.

 ## Memoria
 Libera cada string, luego la lista y el mapa. El pool no debe usarse después.

### `pool_len`

> **pool_len**(pool: ref to NamePool) -> int

 Número de nombres internados.

 ## Memoria
 O(1), no asigna.

### `intern`

> **intern**(pool: ref to NamePool, s: string) -> int

 Interna `s` y devuelve su `NameId`.

 ## Memoria
 Si es nuevo, copia `s` a la lista; el llamador conserva su string.

### `intern_if_missing`

> **intern_if_missing**(pool: ref to NamePool, s: string) -> int

 Interna `s` solo si no existe y devuelve el id existente.

 ## Memoria
 Igual que `intern`; se ofrece como nombre explícito para el collector.

### `_borrow_string`

> **_borrow_string**(s: string) -> string

 Préstamo no propietario de los bytes de `s`.

 ## Motivo
 `(pool->strings at id)` copia la cabecera `PenguString` con `is_owned = 1`:
 un `banish` sobre el resultado liberaría el buffer del pool y dejaría el
 nombre colgando. El préstamo marca `is_owned = 0` para que `banish` sea un
 no-op y el pool siga siendo el único dueño.

 ## Memoria
 No asigna; el resultado vive mientras viva el pool.

### `text`

> **text**(pool: ref to NamePool, id: int) -> string

 Texto de un `NameId`.

 ## Retorno
 Un préstamo (no propietario) del string del pool; no lo liberes.

 ## Memoria
 Devuelve un préstamo al string del pool; no lo liberes (`banish` es no-op).

### `has_id`

> **has_id**(pool: ref to NamePool, id: int) -> bool

 `true` si el id está dentro del pool.

 ## Memoria
 O(1), no asigna.

### `find`

> **find**(pool: ref to NamePool, s: string) -> int

 `NameId` existente o `-1`.

 ## Memoria
 O(1) promedio; no asigna.

### `dump_pool`

> **dump_pool**(pool: ref to NamePool) -> void

 Depuración: imprime los nombres en orden.

 ## Memoria
 No asigna salvo la salida de `spark`.

