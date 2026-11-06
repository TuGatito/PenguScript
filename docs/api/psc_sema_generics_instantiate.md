# psc.sema.generics.instantiate

> Source: `src/psc/sema/generics/instantiate.pengu`

psc/sema/generics/instantiate.pengu — materialización de tipos genéricos.

Convierte una plantilla nominal (`Box`, `Node`, `Option`, ...) y sus
argumentos de tipo en una `SemaNominalInfo` concreta.  La instancia se
cachea por `(plantilla, args)` y se registra antes de sustituir sus campos
para que los tipos recursivos (`Node of T` dentro de `Node of T`) terminen.

El compilador sigue siendo explícito: no hay sustitución perezosa en F4.

---

### `instance_key`

> **instance_key**(template: int, args: list of int) -> string

 Clave textual de una instancia (plantilla + args).

 ## Memoria
 Devuelve string owned.

### `instance_c_name`

> **instance_c_name**(t: ref to SemaTypeTable, template: int, args: list of int) -> string

 Nombre C estable de una instancia.

 ## Memoria
 Devuelve string owned.

### `subst_type`

> **subst_type**(t: ref to SemaTypeTable, id: int, subst: ref to map of int to int) -> int

 Sustituye un tipo formal por sus argumentos reales.

 ## Memoria
 Puede crear nuevos `TypeId` internados; no posee strings.

### `has_param`

> **has_param**(t: ref to SemaTypeTable, id: int) -> bool

 `true` si el tipo contiene un `TkTypeParam` (versión local para no importar
 `convert`, que ya importa este módulo).

 ## Memoria
 O(profundidad).

### `subst_deep`

> **subst_deep**(s: ref to SemaSymbols, id: int, subst: map of int to int) -> int

 Sustituye en profundidad y re-instancia nominales cuyos argumentos cambian.

 A diferencia de `subst_type`, `Box of T` pasa a `Box of int` cuando `T` está
 en `subst`; el resultado es el `TypeId` de la instancia concreta.

 ## Memoria
 Puede crear tipos/instancias internados; no posee strings.

### `type_mentions_param`

> **type_mentions_param**(s: ref to SemaSymbols, id: int, name: int) -> bool

 Whether `id` mentions the type parameter `name` anywhere inside it.

 This guards inference against self-referential bindings such as `A := Job of A`,
 which happens when a generic worker value is unified before its argument.

### `unify_param`

> **unify_param**(s: ref to SemaSymbols, formal: int, actual: int, subst: ref to map of int to int) -> void

 Unifica un tipo formal con uno actual y anota los type params por nombre.

 Es la mitad "inferencia" de la instanciación: dado `list of T` y `list of
 int`, deja `T -> int` en `subst`. Los tipos sintéticos (any/void/error) y
 los nominales ya instanciados no se unifican.

 ## Memoria
 Escribe en `subst` (prestado); no posee strings.

### `instantiate_return`

> **instantiate_return**(s: ref to SemaSymbols, info: SemaFnInfo, recv_template: int, recv_actual: int, arg_types: list of int) -> int

 Resuelve el retorno de una firma genérica con los tipos reales.

 ## Memoria
 Puede crear tipos internados; devuelve el retorno sustituido.

### `instance_symbol_kind`

> **instance_symbol_kind**(k: SemaNominalKind) -> SemaSymbolKind

 Mapea una clase nominal al `SemaSymbolKind` de su plantilla.

 ## Memoria
 No asigna.

### `instantiate_nominal`

> **instantiate_nominal**(s: ref to SemaSymbols, template: int, args: list of int) -> int

 Materializa una instancia nominal.

 `template` es el `TypeId` de la plantilla; `args` son sus argumentos ya
 convertidos. Devuelve el `TypeId` de la instancia o `-1` si la aridad no
 coincide.

 ## Memoria
 Añade `SemaNominalInfo`, campos, variantes, `SemaInstance` y args.

