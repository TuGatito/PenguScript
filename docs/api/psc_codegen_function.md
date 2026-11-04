# psc.codegen.function

> Source: `src/psc/codegen/function.pengu`

psc/codegen/function.pengu — firmas y cuerpos de funciones.

Usa la firma resuelta por F3 (`SemaFnInfo`) y el AST sólo para nombres de
parámetros y statements.

---

### `is_type_node_fn`

> **is_type_node_fn**(ast: ref to PsAst, node: int) -> bool

 Firma C de una especialización genérica, construida desde el AST.

 ## Memoria
 Devuelve string owned.
 `true` si un nodo es un tipo (para funciones sin param_list).

 ## Memoria
 O(1).

### `signature_spec`

> **signature_spec**(c: ref to CgContext, f: CgFunction) -> string

_Undocumented._

### `fn_decl_with_name`

> **fn_decl_with_name**(c: ref to CgContext, m: SemaModule, type_node: int, name: string) -> string

 Declarador de un parámetro de tipo función, con su nombre.

 ## Memoria
 Strings owned.

### `name_fn_declarator`

> **name_fn_declarator**(raw: string, name: string) -> string

 Inserta un nombre en un declarador de puntero a función (`T (*)(...)`).

 ## Memoria
 Strings owned.

### `has_fn_slot`

> **has_fn_slot**(raw: string) -> bool

 ¿El declarador contiene `(*)`?

 ## Memoria
 O(n).

### `ast_fn_param_decl`

> **ast_fn_param_decl**(c: ref to CgContext, m: SemaModule, type_node: int, name: string) -> string

 Declarador C de un parámetro `fn_type` del AST.

 ## Memoria
 Strings owned.

### `signature`

> **signature**(c: ref to CgContext, f: CgFunction) -> string

 Firma C de una función (sin `;`).

 ## Memoria
 Devuelve string owned.

### `pname_for`

> **pname_for**(c: ref to CgContext, f: CgFunction, i: int) -> string

 Nombre de parámetro i de una función (AST o generado).

 ## Memoria
 Devuelve string owned.

### `emit_function`

> **emit_function**(c: ref to CgContext, f: CgFunction) -> void

 Emite la definición de una función.

 ## Memoria
 Abre/cierra contexto/local scope.

### `scan_local_names`

> **scan_local_names**(c: ref to CgContext, m: SemaModule, ast: ref to PsAst, node: int) -> void

 Registra nombres locales declarados en el cuerpo antes de emitirlo.

 F3 no siempre anota el `var_ref` de un local de tipo omen; pre-registrar el
 nombre evita que se confunda con una variante global.

 ## Memoria
 Añade locales al contexto.

### `body_start`

> **body_start**(ast: ref to PsAst, node: int) -> int

 Slot del primer statement del cuerpo.

 ## Memoria
 O(nodos).

