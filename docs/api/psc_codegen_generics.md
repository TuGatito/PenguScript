# psc.codegen.generics

> Source: `src/psc/codegen/generics.pengu`

psc/codegen/generics.pengu — especialización de funciones genéricas.

F3 reconoce los `shard` pero no materializa instancias. F4 crea una función
C por cada combinación de argumentos de tipo que aparece en una llamada
explícita (`f of T`). La sustitución se guarda en `CgNames.subst`.

---

### `find_spec`

> **find_spec**(c: ref to CgContext, sid: int, args: list of int) -> int

 Busca una especialización existente.

 ## Memoria
 O(funciones).

### `add_spec`

> **add_spec**(c: ref to CgContext, base_idx: int, args: list of int) -> int

 Añade una especialización de una función genérica.

 ## Memoria
 Añade al catálogo; no posee strings.

### `unify`

> **unify**(c: ref to CgContext, formal: int, actual: int, subst: ref to map of int to int) -> void

 Unifica un tipo formal con uno actual y anota los parámetros.

 ## Memoria
 No asigna; usa el mapa prestado.

### `infer_from_actual`

> **infer_from_actual**(c: ref to CgContext, base_idx: int, actuals: list of int) -> list of int

 Infiere los argumentos de tipo de una llamada genérica.

 ## Memoria
 Devuelve una lista owned; vacía si no se puede inferir.

### `scan`

> **scan**(c: ref to CgContext, m: SemaModule, node: int) -> void

 Recorre un nodo buscando llamadas genéricas explícitas.

 ## Memoria
 Recursión sobre el AST.

### `expr_last_token`

> **expr_last_token**(ast: ref to PsAst, node: int) -> int

 Último token de un target (sin depender de expr para evitar ciclos).

 ## Memoria
 O(nodos).

### `collect_type_instances`

> **collect_type_instances**(c: ref to CgContext) -> void

 Añade al catálogo las `CgType` de las instancias nominales.

 La plantilla ya está en `catalog.by_type` (se registró aunque sea genérica).
 Cada instancia usa el nodo/módulo de la plantilla, pero su `type_id` y sus
 campos son los de la `SemaNominalInfo` instanciada.

 ## Memoria
 Añade tipos al catálogo; no posee strings.

### `type_args_of`

> **type_args_of**(c: ref to CgContext, id: int) -> list of int

 Argumentos de tipo visibles en un receptor (`list of int`, `map of K to V`).

 ## Memoria
 Devuelve una lista owned.

### `container_kind`

> **container_kind**(c: ref to CgContext, id: int) -> int

 Kind estructural de un receptor de contenedor (para emparejar métodos genéricos).

### `spec_args_for`

> **spec_args_for**(c: ref to CgContext, base_idx: int, recv_id: int) -> list of int

 Busca la plantilla genérica de un método por nombre y forma del receptor.
 Deriva los argumentos de tipo de una especialización unificando el receptor
 plantilla con el receptor concreto. Devuelve vacío si algún parámetro queda
 sin ligar.

 ## Memoria
 Devuelve una lista owned.

### `call_arg_type`

> **call_arg_type**(c: ref to CgContext, node: int) -> int

 Tipo anotado de un nodo de la llamada (sin depender de `expr`).

### `spec_args_for_call`

> **spec_args_for_call**(c: ref to CgContext, base_idx: int, recv_id: int, node: int) -> list of int

 Argumentos de una especialización de método: parámetros del receptor más
 los `shard` propios del método, inferidos de los argumentos de la llamada.

### `find_generic_method`

> **find_generic_method**(c: ref to CgContext, name: int, recv_id: int) -> int

_Undocumented._

### `ensure_method_spec`

> **ensure_method_spec**(c: ref to CgContext, base_idx: int, recv_id: int, node: int) -> int

 Especializa un método genérico para un receptor concreto.

 ## Memoria
 Puede añadir una `CgFunction`; devuelve el índice.

### `add_method_spec`

> **add_method_spec**(c: ref to CgContext, base_idx: int, recv_type: int, args: list of int) -> int

 Añade la especialización de un método genérico para un receptor concreto.

 ## Memoria
 Añade una `CgFunction`; no posee strings.

### `receiver_type_of`

> **receiver_type_of**(c: ref to CgContext, f: CgFunction) -> int

 Tipo del receptor de una especialización de método.

 El catálogo puede guardar la plantilla nominal (`Box`) en lugar de
 `Box of int`; aquí se materializa con los primeros `spec_args`, que son los
 parámetros del receptor (los del método van después).

 ## Memoria
 Puede crear una instancia nominal; no posee strings.

### `all_concrete`

> **all_concrete**(c: ref to CgContext, args: list of int) -> bool

 `true` si todos los args de una lista son concretos.

 ## Memoria
 O(args).

### `collect_method_instances`

> **collect_method_instances**(c: ref to CgContext) -> void

 Especializa los métodos de todas las instancias nominales.

 ## Memoria
 Añade funciones al catálogo.

### `specialize_all`

> **specialize_all**(c: ref to CgContext) -> void

 Especializa todas las llamadas genéricas del catálogo.

 ## Memoria
 Añade funciones al catálogo.

### `subst_codegen`

> **subst_codegen**(c: ref to CgContext, id: int) -> int

 Sustituye los parámetros de tipo del contexto actual.

 ## Memoria
 O(tipo).

### `subst_spec_type_of`

> **subst_spec_type_of**(c: ref to CgContext, f: CgFunction, id: int) -> int

 Sustituye `id` con la tabla `tparams -> spec_args` de una especialización.

 Sirve para tipar los argumentos de una llamada a `f<T>` aunque el cuerpo que
 se está emitiendo no sea el de la especialización.

 ## Memoria
 Puede crear tipos internados; el mapa temporal se libera.

