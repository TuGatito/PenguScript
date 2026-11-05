# psc.sema.infer.core

> Source: `src/psc/sema/infer/core.pengu`

psc/sema/infer/core.pengu — inferencia de expresiones (núcleo).

Cubre literales, referencias, operadores, accesos, llamadas simples y
constructores de contenedores. Las construcciones que necesitan el checker
(`if`/`do`/`with`/`judge`/lambda) se delegan a `SemaHooks`; así el módulo no
importa `check` y no hay ciclos.

## Memoria
Todo es de solo lectura sobre la tabla de tipos/símbolos. Los strings
temporales se liberan en la misma función.

---

### `infer`

> **infer**(s: ref to SemaState, node: int, expected: int) -> int

 Infiere una expresión y la anota.

 `expected` es `-1` si no hay contexto. Devuelve `0` (`TkError`) en error.

 ## Memoria
 Puede emitir diagnósticos; no posee recursos.

### `string_literal_has_interp`

> **string_literal_has_interp**(s: ref to SemaState, node: int) -> bool

 ¿El literal string de `node` contiene interpolación `{...}`?

 Los literales que se emiten como `const char*` no pueden interpolar: el
 resultado sería un `PenguString`, no un puntero C.

 ## Memoria
 O(n); no asigna.

### `check_string_literal`

> **check_string_literal**(s: ref to SemaState, node: int) -> void

 Comprueba las interpolaciones de un literal string en el scope actual.

 ## Memoria
 Parsea/infiere AST temporal; libera bundle, bag y anotaciones.

### `infer_int`

> **infer_int**(s: ref to SemaState, node: int) -> int

 `int` o `i64` según el literal.

 ## Memoria
 Puede liberar el texto temporal.

### `infer_none`

> **infer_none**(s: ref to SemaState, node: int, expected: int) -> int

 `none` necesita un `maybe` esperado.

 ## Memoria
 Puede emitir un error.

### `infer_generic_ref`

> **infer_generic_ref**(s: ref to SemaState, node: int) -> int

 Resuelve un valor de función genérico (`f of T`).

 ## Memoria
 Puede crear tipos y mapas temporales.

### `infer_var`

> **infer_var**(s: ref to SemaState, node: int) -> int

 Referencia a un nombre.

 ## Memoria
 O(1) promedio; puede emitir E0004.

### `infer_name`

> **infer_name**(s: ref to SemaState, node: int, name: string, at_node: int) -> int

 Resuelve un nombre y anota el símbolo.

 ## Memoria
 O(1) promedio.

### `infer_donum`

> **infer_donum**(s: ref to SemaState, node: int, expected: int) -> int

 `donum T` o `donum (T)`.

 ## Memoria
 Puede emitir error.

### `starts_with_fn`

> **starts_with_fn**(s: string) -> bool

 ¿El nombre parece un tipo de función (`Fn1`, `Fn2`, ...)?

 ## Memoria
 O(1).

### `scope_has_donum`

> **scope_has_donum**(s: ref to SemaState) -> bool

 ¿El scope actual tiene un bound `Donum`?

 ## Memoria
 O(profundidad * bounds).

### `module_dotted_name`

> **module_dotted_name**(s: ref to SemaState, mid: int) -> string

 Nombre lógico (`a.b.c`) de un módulo, derivado de su ruta.

 Permite reconocer `calling modulo.hijo.fn` cuando `modulo` es el propio
 módulo actual (bug 8), sin depender de un símbolo de import del consumidor.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `module_by_dotted`

> **module_by_dotted**(s: ref to SemaState, dotted: string) -> int

 Busca un módulo por su nombre lógico.

 ## Memoria
 Devuelve un índice; no asigna.

### `type_is_owning`

> **type_is_owning**(s: ref to SemaState, id: int) -> bool

 ¿El tipo posee campos que se mueven con el valor?

### `check_spawn_ref`

> **check_spawn_ref**(s: ref to SemaState, node: int, ty: int) -> void

 Comprueba que un `ref to T` apunte a un tipo `@shared`.

### `type_has_unshared_ref`

> **type_has_unshared_ref**(s: ref to SemaState, id: int, depth: int) -> bool

 ¿El tipo contiene algún `ref to T` cuyo destino no sea `@shared`?

 Los `ref` anidados dentro de runas/colecciones no los ve `check_spawn_ref`;
 sin este chequeo un rune con un campo `ref to T` cruza un hilo y produce una
 carrera de datos. Un `slice`/`opaque`/`many` también se considera préstamo.

### `check_arg_ownership`

> **check_arg_ownership**(s: ref to SemaState, anode: int, aty: int, move_flag: int) -> void

 Valida la propiedad de un argumento transferido (hilo o corrutina).

 Un valor con dueño debe venir de un binding local (`var`/`let`), no de un
 parámetro prestado ni de una expresión compuesta. Los literales de string
 son frescos (`is_owned = 0`) y se pueden pasar directamente.

### `check_spawn_arg`

> **check_spawn_arg**(s: ref to SemaState, anode: int, aty: int) -> void

 Valida los argumentos de `filum.start`.
 Valida un argumento transferido a un hilo.

### `infer_spawn`

> **infer_spawn**(s: ref to SemaState, node: int, args: int, arg_types: list of int) -> void

_Undocumented._

### `check_coro_arg`

> **check_coro_arg**(s: ref to SemaState, anode: int, aty: int) -> void

 Valida los argumentos de `std.coro.start`.

 Una corrutina vive en el mismo hilo que su creador, así que `ref to T`,
 slices, opaque y punteros a función son legales. Los valores con dueño se
 mueven igual que en un hilo, pero con un flag distinto para que el
 diagnóstico diga "coroutine".

### `infer_coro`

> **infer_coro**(s: ref to SemaState, node: int, args: int, arg_types: list of int) -> void

 Comprueba `std.coro.start` / `start0`.

 Replica las reglas de worker de `infer_spawn`, pero no exige `@shared`:
 la corrutina nunca cambia de hilo.

### `infer_call`

> **infer_call**(s: ref to SemaState, node: int, expected: int) -> int

 Llamada.

 ## Memoria
 Infiere target/args; no posee listas.

### `infer_chain_method`

> **infer_chain_method**(s: ref to SemaState, recv: int, step: int, is_last: bool) -> int

 Resuelve un paso de método de `NdChainExpr`.

 ## Memoria
 Infiere argumentos; no posee listas.

### `infer_chain_pipe`

> **infer_chain_pipe**(s: ref to SemaState, recv: int, step: int, is_last: bool) -> int

 Resuelve un paso `pipe` de `NdChainExpr`.

 ## Memoria
 Infiere argumentos; no posee listas.

### `infer_chain`

> **infer_chain**(s: ref to SemaState, node: int) -> int

 Infiere una cadena de métodos (`aux == 0`) o de pipes (`aux == 1`).

 ## Memoria
 Infiere la base y cada paso; no posee listas.

### `builtin_method`

> **builtin_method**(s: ref to SemaState, recv: int, name: string, expected: int) -> int

 Tipo de un método nativo de una colección/string.

 Devuelve `-1` si no es un método conocido. Se usa para no rechazar
 `list.push`, `map.put`, etc. antes de que el registro de métodos builtin
 esté completo.

 ## Memoria
 O(1).

### `active_with_type`

> **active_with_type**(s: ref to SemaState) -> int

 Tipo activo de `with` desde el scope actual.

 ## Memoria
 O(profundidad).

### `infer_with_call`

> **infer_with_call**(s: ref to SemaState, node: int, target: int, expected: int) -> int

 Llamada con target `.method` dentro de `with`.

 ## Memoria
 Infiere args; no asigna.

### `concept_grants`

> **concept_grants**(c: string, op: string) -> bool

 ¿El concepto `c` concede `op`?

 ## Memoria
 O(1).

### `bound_operator_ok`

> **bound_operator_ok**(s: ref to SemaState, op: string) -> bool

 ¿El scope actual concede `op` a un `TypeParam`?

 Devuelve `true` si no hay bounds (no se puede decidir aquí).

 ## Memoria
 O(profundidad * bounds).

### `operator_bound_error`

> **operator_bound_error**(s: ref to SemaState, node: int, op: string) -> void

 Reporta un operador no concedido por el bound actual.

 ## Memoria
 O(1).

### `underlying_type`

> **underlying_type**(s: ref to SemaState, id: int) -> int

 Aplica un acceso intermedio a un tipo.

 ## Memoria
 O(1)/campos.
 Desenvuelve alias/seal hasta el tipo real.

 ## Memoria
 O(profundidad); no asigna.

### `access_op_type`

> **access_op_type**(s: ref to SemaState, base: int, op: int) -> int

 Aplica un acceso intermedio a un tipo.

### `infer_args_only`

> **infer_args_only**(s: ref to SemaState, args: int) -> void

 Infiere argumentos sin comprobar contra una firma.

 ## Memoria
 O(n).

### `infer_result_ctor`

> **infer_result_ctor**(s: ref to SemaState, node: int, which: string, expected: int) -> int

 Constructores `ok_of`/`err_of`.

 ## Memoria
 O(1).

### `undefined_call`

> **undefined_call**(s: ref to SemaState, node: int, name: string) -> void

 Emite el error de una llamada inexistente.

 ## Memoria
 Construye un mensaje temporal.

### `param_index`

> **param_index**(s: ref to SemaState, info: SemaFnInfo, name: string) -> int

 Índice de un parámetro por nombre.

 ## Memoria
 O(n).

### `infer_field`

> **infer_field**(s: ref to SemaState, node: int) -> int

 Acceso `.field`.

 ## Memoria
 O(campos).

### `infer_arrow`

> **infer_arrow**(s: ref to SemaState, node: int) -> int

 Acceso `->field`.

 ## Memoria
 O(campos).

### `field_type`

> **field_type**(s: ref to SemaState, type_id: int, name: string) -> int

 Tipo de un campo de una runa/echo; error si no existe.

 ## Memoria
 O(campos).

### `infer_at`

> **infer_at**(s: ref to SemaState, node: int) -> int

 Acceso `at`.

 ## Memoria
 O(1).

### `infer_to`

> **infer_to**(s: ref to SemaState, node: int) -> int

 Cast `(expr to T)`.

 ## Memoria
 Convierte el nodo tipo.

### `infer_list_lit`

> **infer_list_lit**(s: ref to SemaState, node: int, expected: int) -> int

 Lista vacía o de tipo homogéneo.

 ## Memoria
 O(n).

### `infer_list_init`

> **infer_list_init**(s: ref to SemaState, node: int, expected: int) -> int

 Constructor `list of T`.

 ## Memoria
 Convierte el tipo y devuelve `list of T`.

### `infer_map_init`

> **infer_map_init**(s: ref to SemaState, node: int, expected: int) -> int

 Constructor `map of K to V`.

 ## Memoria
 Convierte ambos tipos.

### `infer_array_init`

> **infer_array_init**(s: ref to SemaState, node: int, expected: int) -> int

 Constructor `array of T with size N`.

 ## Memoria
 Convierte el tipo y el tamaño constante.

### `infer_map_lit`

> **infer_map_lit**(s: ref to SemaState, node: int, expected: int) -> int

 Literal de mapa.

 ## Memoria
 Infiere claves/valores; vacío usa el expected.

### `infer_struct_init`

> **infer_struct_init**(s: ref to SemaState, node: int) -> int

 Inicialización de runa `Point with x is 1`.

 ## Memoria
 O(campos).

### `nominal_field_index`

> **nominal_field_index**(s: ref to SemaState, ty: int, nid: int) -> int

 Índice del campo `nid` en un rune/echo (0-based), o `-1`.

 ## Memoria
 No asigna.

### `has_nominal_fields`

> **has_nominal_fields**(s: ref to SemaState, ty: int) -> bool

 `true` si `ty` es un rune/echo con campos declarados (no omen, genérico,
 alias, seal ni primitivo).

 ## Memoria
 No asigna.

### `infer_field_inits`

> **infer_field_inits**(s: ref to SemaState, node: int, ty: int) -> void

 Infiere los valores de `with campo is expr, ...`.

 `infer_struct_init` solo resuelve el tipo nominal; sin esto el valor de cada
 campo queda sin anotar y una lambda dentro de un `with` no recibe firma. El
 tipo del campo se pasa como tipo esperado para conservar el contexto de
 `maybe`/`result` (`with data is maybe none`).

 ## Memoria
 O(campos); reutiliza el estado de inferencia.

### `infer_do`

> **infer_do**(s: ref to SemaState, node: int, expected: int) -> int

 `do:` como expresión de bloque.

 ## Memoria
 Recorre statements; devuelve el tipo del último valor.

### `infer_error_lit`

> **infer_error_lit**(s: ref to SemaState, node: int) -> int

 Literal `error` dentro de un bloque `or:`.

 El símbolo lo define `infer_or` al entrar en el bloque; fuera de él no
 existe y se diagnostica. Para `maybe T` el payload es `string`; para
 `result of T to E` es `E`.

 ## Memoria
 O(profundidad de scopes); puede emitir E0015.

### `infer_or`

> **infer_or**(s: ref to SemaState, node: int, expected: int) -> int

 `or else`/`or return`/`or:`.

 ## Memoria
 Infiere el lado izquierdo y, si es maybe/result, devuelve su valor. Los
 cuerpos de `or:` se comprueban statement a statement con `error` en scope.

### `infer_for_comp`

> **infer_for_comp**(s: ref to SemaState, node: int) -> int

 `for x in col then expr` como expresión de lista.

 ## Memoria
 Entra/sale de un scope; devuelve `list of T`.

### `infer_if_expr`

> **infer_if_expr**(s: ref to SemaState, node: int, expected: int) -> int

 `if`/`when` como expresión.

 ## Memoria
 Infiere condición y ramas; no asigna.

### `infer_bool`

> **infer_bool**(s: ref to SemaState, node: int) -> int

 Operadores booleanos.

 ## Memoria
 O(1).

### `infer_compare`

> **infer_compare**(s: ref to SemaState, node: int) -> int

 Comparaciones.

 ## Memoria
 O(1).

### `is_self_value`

> **is_self_value**(s: ref to SemaState, node: int) -> bool

 `true` si el nodo es `self` en un método con receptor por valor.

 ## Memoria
 O(1).

### `sigil_status`

> **sigil_status**(s: ref to SemaState, node: int) -> int

 Clasifica la addressability de una expresión para `sigil of`.

 Devuelve 0 si no es lvalue, 1 si es mutable, 2 si es de solo lectura
 (`let`) y 3 si es una constante (error E0008).

 ## Memoria
 O(profundidad del acceso).

### `sigil_lvalue_error`

> **sigil_lvalue_error**(s: ref to SemaState, node: int) -> void

 Error E0008: `sigil of` sobre algo que no es un lvalue.

 ## Memoria
 O(1).

### `sigil_const_error`

> **sigil_const_error**(s: ref to SemaState, node: int) -> void

 Error E0008: `sigil of` sobre una constante.

 ## Memoria
 O(1).

### `essence_error`

> **essence_error**(s: ref to SemaState, node: int, got: int) -> void

 Error E0005: `essence of` sobre un valor que no es `ref to T`.

 ## Memoria
 O(1).

### `void_pointee`

> **void_pointee**(s: ref to SemaState, tid: int) -> bool

 ¿El pointee es `void` (no permite aritmética escalada)?

 ## Memoria
 O(1).

### `infer_arith`

> **infer_arith**(s: ref to SemaState, node: int) -> int

 Aritmética.

 ## Memoria
 O(1).

### `infer_bit`

> **infer_bit**(s: ref to SemaState, node: int) -> int

 Bitwise/shifts.

 ## Memoria
 O(1).

### `infer_unary`

> **infer_unary**(s: ref to SemaState, node: int) -> int

 Unarios.

 ## Memoria
 O(1).

### `infer_range`

> **infer_range**(s: ref to SemaState, node: int) -> int

 Rangos.

 ## Memoria
 O(1).

### `infer_pointer`

> **infer_pointer**(s: ref to SemaState, node: int) -> int

 `sigil of`/`essence of`.

 ## Memoria
 O(1).

### `type_mismatch`

> **type_mismatch**(s: ref to SemaState, node: int, expected: int, got: int) -> void

 Emite un mismatch con tipos canónicos.

 ## Memoria
 Construye dos strings temporales y los libera.

### `resolve_callable`

> **resolve_callable**(t: ref to SemaTypeTable, id: int) -> int

 Resuelve una referencia o un alias hasta el tipo subyacente (máx. 32
 saltos). Se usa para llamar funciones guardadas en un alias, p. ej.
 `alias Handler as weave with context as ref to Context into result of void to HttpError`.

 ## Memoria
 O(1); no asigna.

### `call_fn_field`

> **call_fn_field**(s: ref to SemaState, recv_ty: int, name: string, args: int) -> int

 Llama al puntero a función guardado en el campo `name` del receptor.

 Devuelve el tipo de retorno, o `-1` si el campo no existe o no es una
 función (`calling route.handler with context`).

 ## Memoria
 O(1); no asigna.

