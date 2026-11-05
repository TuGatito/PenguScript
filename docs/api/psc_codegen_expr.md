# psc.codegen.expr

> Source: `src/psc/codegen/expr.pengu`

psc/codegen/expr.pengu — expresiones C (núcleo inicial).

La primera entrega cubre literales, variables locales, aritmética, unarios,
comparaciones y llamadas directas. Las subfases posteriores añaden el resto
sin cambiar la interfaz `emit_expr`.

---

### `node_type`

> **node_type**(c: ref to CgContext, node: int) -> int

 Tipo anotado de un nodo.

 ## Memoria
 O(1).

### `emit_expr`

> **emit_expr**(c: ref to CgContext, node: int) -> string

 Emite una expresión como string C owned.

 ## Memoria
 Devuelve un string owned; el llamador lo libera con `banish`.

### `guess_type`

> **guess_type**(c: ref to CgContext, node: int, ast: ref to PsAst) -> int

 Tipo aproximado de una expresión cuando F3 no lo anotó.

 Para acceso a campo/local resuelve por la tabla nominal; `-1` si no sabe.

 ## Memoria
 O(profundidad); sin asignaciones.

### `unwrap_expr`

> **unwrap_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, is_or_return: bool) -> string

 Emite una expresión con un tipo esperado (para struct init sin anotación).

 ## Memoria
 Devuelve string owned.
 Emite `or return` y `try` sobre `maybe`/`result`.

 ## Memoria
 Devuelve un string owned.

### `zero_value_expr`

> **zero_value_expr**(c: ref to CgContext, ty: int) -> string

 Emite el valor cero de un tipo (`donum T`).

 ## Memoria
 Devuelve un string owned.

### `in_expr`

> **in_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, negated: bool) -> string

 Emite `valor in coleccion` / `valor not in coleccion`.

 ## Memoria
 Devuelve un string owned.

### `for_comp_expr`

> **for_comp_expr**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

 Emite una lista por comprensión (`for x in xs [when cond] then expr`).

 ## Memoria
 Strings owned; el resultado es una statement-expression con un `PenguList`
 recién reservado.

### `list_literal_expr`

> **list_literal_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, ty: int) -> string

 Emite un literal de lista `[a, b, ...]` como `PenguList`.

 ## Memoria
 Strings owned.

### `emit_expr_as`

> **emit_expr_as**(c: ref to CgContext, node: int, expected: int) -> string

_Undocumented._

### `binary_expr`

> **binary_expr**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

 Emite una operación binaria.

 ## Memoria
 Strings owned.

### `last_token_deep`

> **last_token_deep**(ast: ref to PsAst, node: int) -> int

 Último token de un subárbol (el nombre del método en un target).

 ## Memoria
 O(nodos).

### `some_expr_c`

> **some_expr_c**(c: ref to CgContext, node: int, ast: ref to PsAst, wanted: int) -> string

 Emite `some expr` con boxing en heap.

 ## Memoria
 Strings owned.

### `result_ctor`

> **result_ctor**(c: ref to CgContext, node: int, ast: ref to PsAst, is_ok: bool, is_maybe: bool, wanted: int) -> string

 Constructores intrínsecos `ok_of`, `err_of` y `some`.

 ## Memoria
 Devuelve una statement-expression owned.

### `maybe_result_method`

> **maybe_result_method**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

 Baja métodos builtin de `maybe`/`result` (`unwrap`, `is_some`, ...).

 Devuelve `""` si la llamada no es uno de esos métodos. El receptor se
 resuelve sin el último acceso (el nombre del método).

 ## Memoria
 Devuelve string owned cuando hay coincidencia.

### `generic_ref`

> **generic_ref**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

 Emite una llamada.

 Usa la anotación de símbolo de F3 (resuelve `mod.fn` y métodos); si falta,
 cae al último token del target y al catálogo por nombre.

 ## Memoria
 Strings owned; no posee args.
 Emite un valor de función genérico (`f of T`).

 ## Memoria
 Puede crear especializaciones y tipos.

### `call_expr`

> **call_expr**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

_Undocumented._

### `omen_payload_field_type`

> **omen_payload_field_type**(c: ref to CgContext, oty: int, vname: int, fname: int) -> int

 Tipo de un campo de payload de una variante de omen.

 ## Memoria
 O(variantes/campos).

### `if_expr_expected`

> **if_expr_expected**(c: ref to CgContext, node: int, ast: ref to PsAst, expected: int) -> string

 Emite un `judge` sobre un omen.

 ## Memoria
 Strings owned; los payloads se añaden al scope C.
 Emite un `if` usado como expresión con un tipo esperado.

 ## Memoria
 Devuelve string owned.

### `if_stmt_value`

> **if_stmt_value**(c: ref to CgContext, node: int, ast: ref to PsAst, expected: int) -> string

 Emite un `if` de sentencia usado como valor.

 ## Memoria
 Devuelve string owned.

### `judge_expr_c`

> **judge_expr_c**(c: ref to CgContext, node: int, ast: ref to PsAst, wanted: int) -> string

_Undocumented._

### `infer_at_type`

> **infer_at_type**(c: ref to CgContext, node: int, ast: ref to PsAst) -> int

 Infiere el tipo de un `base at index` sin anotación F3.

 ## Memoria
 O(1).

### `checked_index`

> **checked_index**(c: ref to CgContext, idx: string, base: string, base_type: int, node: int, is_ref: bool) -> string

 Envuelve un índice con `pengu_assert_bounds` si los checks están activos.

 ## Parámetros
 - `idx`: expresión C del índice.
 - `base`: expresión C del contenedor.
 - `base_type`: `TypeId` del contenedor (puede ser `ref to`).
 - `node`: nodo del acceso, para la ubicación del diagnóstico.
 - `is_ref`: `true` si `base` ya es un puntero al contenedor.

 ## Retorno
 La expresión del índice, envuelta o no. String owned.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `sigil_at_expr`

> **sigil_at_expr**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

 Emite una indexación `base at index`.

 ## Memoria
 Strings owned.
 Dirección de un elemento de lista/slice (`sigil of (xs at i)`).

 Devuelve "" cuando el nodo no es un `at` sobre lista/slice; en ese caso el
 llamador usa `&(expr)` para arrays y punteros.

 ## Memoria
 Devuelve string owned.

### `at_expr`

> **at_expr**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

_Undocumented._

### `CgTarget`

> rune CgTarget

```pengu
    text as string
    type_id as int
```

 Target resuelto de una llamada: texto C y tipo.

### `cg_field_type`

> **cg_field_type**(c: ref to CgContext, ty: int, fname: int) -> int

 Tipo de un campo nominal.

 ## Memoria
 O(campos).

### `at_access_target`

> **at_access_target**(c: ref to CgContext, ch: int, base: string, ty: int, ast: ref to PsAst) -> CgTarget

 Resuelve un target de llamada y devuelve el receptor (sin el método).

 ## Memoria
 Devuelve un `CgTarget` owned; liberar `text` con `banish`.
 Aplica un acceso `at` a un target ya resuelto.

 ## Memoria
 Devuelve un `CgTarget` owned; liberar `text`.

### `resolve_with_target`

> **resolve_with_target**(c: ref to CgContext, target: int, ast: ref to PsAst, skip_method: bool) -> CgTarget

 Resuelve un target relativo al `with target:` más interno.

 El AST de un `with_target` empieza con el nombre del primer campo (o del
 método, si `skip_method`) y sigue con accesos `.campo` / `->campo` / `at`.

 ## Memoria
 Devuelve un `CgTarget` owned; liberar `text`.

### `resolve_target`

> **resolve_target**(c: ref to CgContext, target: int, ast: ref to PsAst, skip_method: bool) -> CgTarget

 Resuelve el target de un `set` (nombre, campo, índice o `with`).

 ## Memoria
 Devuelve un `CgTarget` owned; liberar `text`.

### `method_receiver`

> **method_receiver**(c: ref to CgContext, target: int, ast: ref to PsAst, self_value: bool, recv_type: int) -> string

 Texto C del receptor de una llamada a método.

 El target de una llamada es un `normal_target` con un token base y una
 secuencia de accesos (`arrow_access`, `dot_access`). El último acceso es el
 nombre del método; el resto forma el receptor (`self->_blocks`).

 ## Memoria
 Devuelve string owned.

### `get_alias_call`

> **get_alias_call**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

 Expande la forma pura `get_<metodo>` de un método `@mutates`.

 El alias semántico lleva `SYM_GET_ALIAS` + `alias_of`; no existe en el
 catálogo como función C. Se emite una copia del receptor, la llamada mutante
 sobre la copia y el valor copiado.

 ## Memoria
 Devuelve string owned o `""` si no es un alias.

### `dotted_path_text`

> **dotted_path_text**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

 Texto de una ruta cualificada (`mod.Type`) en un target de acceso.

 ## Memoria
 Devuelve string owned.

### `chain_method_fn`

> **chain_method_fn**(c: ref to CgContext, recv: int, name: int) -> int

 Busca la función de catálogo de un método para un receptor y nombre.

 ## Memoria
 O(n) sobre el catálogo; no asigna salvo strings temporales.

### `chain_pipe_fn`

> **chain_pipe_fn**(c: ref to CgContext, name: int) -> int

 Busca la función de catálogo de un pipe por nombre.

 ## Memoria
 O(n) sobre el catálogo.

### `chain_method_recv`

> **chain_method_recv**(c: ref to CgContext, nm: int) -> int

 Emite una cadena de métodos o pipes con temporales.

 ## Memoria
 Devuelve string owned; libera temporales de strings.
 Emite una cadena de métodos de un `calling` con target multi-acceso.

 El target conserva la forma `base.a.b`; los accesos intermedios ya están
 anotados por sema. Cada uno se evalúa en un temporal para no devolver
 punteros a temporales de statement-expressions anidadas.

 ## Memoria
 Devuelve string owned o `""` si no se puede bajar.
 Tipo de receptor declarado por el primer método con nombre `nm`.

 ## Memoria
 O(funciones), no asigna.

### `chain_call_expr`

> **chain_call_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, cname: string) -> string

_Undocumented._

### `chain_fn_void`

> **chain_fn_void**(c: ref to CgContext, fidx: int) -> bool

_Undocumented._

### `chain_fn_by_symbol`

> **chain_fn_by_symbol**(c: ref to CgContext, sid: int) -> int

_Undocumented._

### `chain_expr`

> **chain_expr**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

_Undocumented._

### `omen_variant_c_name`

> **omen_variant_c_name**(c: ref to CgContext, oty: int, vname: int) -> string

 Nombre C de una variante de omen.

 Los omens propios emiten `Type_Variant`; los declarados en un `.d.pengu`
 usan el nombre crudo del enum de la cabecera (`BLEND_ALPHA`, no
 `BlendMode_BLEND_ALPHA`), porque su `typedef` no se regenera.

 ## Memoria
 Devuelve string owned.

### `find_module_variant`

> **find_module_variant**(c: ref to CgContext, module_id: int, name: int) -> int

 Busca una variante de omen exportada por `module_id` (global scope).

 Las variantes se registran en el scope 0, no en el scope del módulo, así que
 `lookup_in_scope(module_scope, ...)` no las encuentra para `mod.Variant`.

 ## Memoria
 O(símbolos); no asigna.

### `field_access_expr`

> **field_access_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, arrow: bool) -> string

 Emite un acceso a campo o una variante de omen.

 ## Memoria
 Strings owned.

### `array_lit_expr`

> **array_lit_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, wanted: int) -> string

 Emite un literal de array `(Tipo[N]){...}`.

 ## Memoria
 Strings owned.

### `list_init_expr`

> **list_init_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, wanted: int) -> string

 Emite una lista vacía o con elementos.

 ## Memoria
 Strings owned.

### `omen_has_layout`

> **omen_has_layout**(c: ref to CgContext, ty: int) -> bool

 `true` si el omen usa representación tag+union.

 ## Memoria
 O(variantes).

### `omen_variant_has_payload`

> **omen_variant_has_payload**(c: ref to CgContext, ty: int, vname: int) -> bool

 `true` si una variante de omen tiene payload.

 ## Memoria
 O(variantes).

### `omen_variant_literal`

> **omen_variant_literal**(c: ref to CgContext, ty: int, vname: int) -> string

 Inicializador C de una variante de omen usada como valor.

 `E.Empty` no es un identificador C válido: se emite `(E){.tag = E_Empty}`.

 ## Memoria
 Devuelve string owned.

### `omen_first_payload`

> **omen_first_payload**(c: ref to CgContext, ty: int, vname: int) -> int

 Primer campo de payload de una variante.

 ## Memoria
 O(variantes).

### `omen_first_payload_type`

> **omen_first_payload_type**(c: ref to CgContext, ty: int, vname: int) -> int

 Tipo del primer campo de payload de una variante.

 ## Memoria
 O(variantes).

### `payload_struct`

> **payload_struct**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

 Inicializador de un payload de omen con varios campos.

 ## Memoria
 Strings owned.

### `payload_fields`

> **payload_fields**(c: ref to CgContext, node: int, ast: ref to PsAst, skip: string) -> string

 Emite los campos de un payload anidado, ignorando el nombre de la variante.

 ## Memoria
 Devuelve string owned.

### `omen_init_expr`

> **omen_init_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, ty: int) -> string

 Emite una variante de omen con payload.

 ## Memoria
 Strings owned.

### `with_init_expr`

> **with_init_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, ty: int) -> string

 Emite `Tipo with: set .campo is valor ...`.

 ## Memoria
 Strings owned.

### `indent_init_expr`

> **indent_init_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, ty: int) -> string

 Emite `Tipo is:` con `campo is valor` (bloque indentado).

 ## Memoria
 Strings owned.

### `struct_init_expr`

> **struct_init_expr**(c: ref to CgContext, node: int, ast: ref to PsAst, wanted: int) -> string

 Emite una inicialización de rune/echo.

 ## Memoria
 Strings owned.

### `escape_c_lit`

> **escape_c_lit**(s: string) -> string

 Escapa un literal preservando los escapes que C ya entiende.

 ## Memoria
 Devuelve string owned.

### `c_string_expr`

> **c_string_expr**(c: ref to CgContext, node: int, raw: string, as_cstr: bool) -> string

 Convierte un literal PenguScript completo (con comillas) en C.

 Con `as_cstr = true` emite un literal `const char*` puro (`"..."`) para
 contextos `ref to char`/`ref to frozen char`; si no, un `PenguString`.
 Los literales con `{expr}` simples (identificadores locales) se emiten con
 `pengu_string_format_ex`; el resto se conserva como texto. La subfase de
 interpolación completa añadirá expresiones arbitrarias y `(chr N)`.

 ## Memoria
 Devuelve string owned.

### `has_interp`

> **has_interp**(s: string) -> bool

 `true` si el contenido tiene una interpolación simple.

 ## Memoria
 O(n).

### `append_interp_value`

> **append_interp_value**(c: ref to CgContext, fmt: ref to StringBuilder, args: ref to StringBuilder, expr: string, ty: int) -> void

 Emite una interpolación simple.

 ## Memoria
 Strings owned; args se construyen en un builder.
 Añade un valor a `fmt`/`args` de interpolación según su tipo.

 ## Memoria
 O(1) strings owned.

### `nominal_field_type`

> **nominal_field_type**(c: ref to CgContext, ty: int, fname: int) -> int

 Campo nominal de un tipo por nombre.

 ## Memoria
 O(campos).

### `find_string_info`

> **find_string_info**(c: ref to CgContext, node: int) -> int

 Devuelve el índice del `StringInfo` del literal `node`, o `-1`.

 ## Memoria
 O(literales).

### `find_interp`

> **find_interp**(m: ref to SemaModule, node: int, pstart: int, pend: int) -> int

 Devuelve el índice del `SemaInterp` de un segmento, o `-1`.

 ## Memoria
 O(interpolaciones del módulo).

### `append_format_text`

> **append_format_text**(fmt: ref to StringBuilder, text: string) -> void

 Añade un texto literal al formato, escapando C y `%`.

 ## Memoria
 Strings owned.

### `interp_path_c`

> **interp_path_c**(c: ref to CgContext, txt: string) -> CgTarget

 Resuelve un camino simple `a.b.c` / `self->x` para una interpolación cuyo
 AST no quedó asociado al literal. Devuelve texto/type o text vacío.

 ## Memoria
 Devuelve `text` owned; liberar con `banish`.

### `interp_expr`

> **interp_expr**(c: ref to CgContext, node: int, content: string) -> string

 Emite una interpolación usando los AST/anotaciones que guardó el sema.

 ## Memoria
 Strings owned.

