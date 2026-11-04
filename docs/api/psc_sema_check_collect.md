# psc.sema.check.collect

> Source: `src/psc/sema/check/collect.pengu`

psc/sema/check/collect.pengu — recolección de declaraciones top-level.

Pass 1 de F3: registra imports/insignia/includes, tipos, firmas, consts y
tests. Los cuerpos se validan en `body.pengu`. El collector no infiere
expresiones salvo los valores de `const` y los tipos declarados.

## Memoria
Presta `SemaState`; los símbolos/tipos viven en las tablas del programa.

---

### `ParamRange`

> rune ParamRange

```pengu
    first as int
    count as int
```

 Rango de parámetros recién añadidos.

 ## Memoria
 POD.

### `collect_module`

> **collect_module**(s: ref to SemaState) -> void

 Recorre el archivo y recolecta las declaraciones.

 ## Memoria
 Puede emitir diagnósticos; no posee listas.

### `predeclare_types`

> **predeclare_types**(s: ref to SemaState) -> void

 Predeclara nombres de tipos para permitir referencias hacia delante.

 ## Memoria
 Añade tipos al registro y `module->type_ids`.

### `collect_top`

> **collect_top**(s: ref to SemaState, node: int) -> void

 Recolecta un `top_stmt` (o un `stmt`/declaración directa).

 ## Memoria
 Puede emitir diagnósticos.

### `collect_import`

> **collect_import**(s: ref to SemaState, node: int) -> void

 Registra un `import` en el módulo actual.

 ## Memoria
 Puede emitir diagnósticos; no posee el módulo destino.

### `import_alias`

> **import_alias**(s: ref to SemaState, node: int, dot: string) -> int

 Alias de un import (explícito o último componente).

 ## Memoria
 Devuelve un `NameId`.

### `collect_dotted_text`

> **collect_dotted_text**(s: ref to SemaState, node: int) -> string

 Texto de un `dotted_path`.

 ## Memoria
 Devuelve un string owned.

### `collect_substring`

> **collect_substring**(s: string, start: int, end: int) -> string

 Substring con copia owned.

 ## Memoria
 Devuelve un string owned.

### `when_value`

> **when_value**(s: ref to SemaState, node: int) -> string

 Valor textual de un operando de `when` (`os`, `arch`, `compiler`,
 `wasm_target`, booleanos comptime o un literal).

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `when_known`

> **when_known**(s: ref to SemaState, node: int) -> bool

 `true` si el operando de un `when` es una constante comptime conocida.

 Un identificador desconocido no es "falso": es E0039. Sólo `-D NAME` lo
 convierte en definido.

 ## Memoria
 O(1); no asigna.

### `when_error`

> **when_error**(s: ref to SemaState, node: int) -> void

 Error E0039 para una condición `when` no resoluble.

 ## Memoria
 Emite el diagnóstico; no retiene strings.

### `when_truth`

> **when_truth**(s: ref to SemaState, node: int) -> bool

 Evalúa una condición `when` top-level sencilla.

 ## Memoria
 O(1); no asigna.

### `define_has`

> **define_has**(s: ref to SemaState, name: string) -> bool

 ¿`-D name` está definido?

 ## Memoria
 O(defines).

### `collect_when_top`

> **collect_when_top**(s: ref to SemaState, node: int) -> void

 Recolecta la rama activa de un `when` top-level.

 ## Memoria
 Recorre top_stmts; no asigna.

### `collect_link`

> **collect_link**(s: ref to SemaState, node: int, kind: NodeKind) -> void

 `include`, `link`, `ldflag`.

 ## Memoria
 Copia el string del token a la lista del programa.

### `unquote`

> **unquote**(s: string) -> string

 Quita comillas dobles de un string.

 ## Memoria
 Devuelve un string owned.

### `collect_insignia`

> **collect_insignia**(s: ref to SemaState, node: int) -> void

 `insignia NAME`.

 ## Memoria
 Interna el nombre y lo guarda.

### `collect_name_slot`

> **collect_name_slot**(s: ref to SemaState, node: int) -> int

 Busca el primer token hijo (el nombre de la declaración).

 ## Memoria
 O(n hijos), no asigna.

### `decl_name`

> **decl_name**(s: ref to SemaState, node: int) -> int

 Nombre de la declaración como `NameId` (`-1` si falta).

 ## Memoria
 Interna el texto.

### `decl_name_text`

> **decl_name_text**(s: ref to SemaState, node: int) -> string

 Nombre de la declaración como string.

 ## Memoria
 Devuelve un string owned.

### `collect_type_ctx`

> **collect_type_ctx**(s: ref to SemaState) -> TypeCtx

 Contexto de conversión de tipos.

 ## Memoria
 Valor puro de referencias.

### `new_nominal`

> **new_nominal**(s: ref to SemaState, kind: SemaNominalKind, name: int, cname: int, public: bool) -> int

 Crea una info nominal y su `TypeId`.

 ## Memoria
 Añade a la tabla y al registro.

### `parse_uint_text`

> **parse_uint_text**(t: string) -> int

 Convierte un texto numérico simple en entero (atributos `@align(N)`).

### `field_align_override`

> **field_align_override**(s: ref to SemaState, field: int) -> int

 `@align(N)` de un campo (`0` si no tiene).

 ## Memoria
 O(1).

### `apply_nominal_attrs`

> **apply_nominal_attrs**(s: ref to SemaState, ty: int, node: int) -> void

 Aplica `@packed` / `@align(N)` del nodo de declaración a su info nominal.

### `trim_text`

> **trim_text**(s: string) -> string

 Recorta espacios de una línea.

### `tag_decl`

> **tag_decl**(s: ref to SemaState, id: int, node: int) -> void

 Asigna módulo, línea, columna, span y doc a un símbolo top-level.

### `register_type`

> **register_type**(s: ref to SemaState, kind: SemaSymbolKind, name: int, type_id: int, node: int) -> void

 Registra un tipo en los mapas y el scope.

 ## Memoria
 Añade símbolo.

### `collect_record`

> **collect_record**(s: ref to SemaState, node: int, sk: SemaSymbolKind) -> void

 `rune`/`echo`.

 ## Memoria
 Añade tipo, campos y símbolo.

### `first_token_slot_after_attrs`

> **first_token_slot_after_attrs**(s: ref to SemaState, node: int) -> int

 Primer token tras los atributos de un `field_decl`.

 ## Memoria
 O(n).

### `collect_omen`

> **collect_omen**(s: ref to SemaState, node: int) -> void

 `omen`.

 ## Memoria
 Añade tipo/variantes.

### `collect_alias`

> **collect_alias**(s: ref to SemaState, node: int, is_seal: bool) -> void

 `alias`/`seal`.

 ## Memoria
 Añade tipo/símbolo.

### `collect_concept`

> **collect_concept**(s: ref to SemaState, node: int) -> void

 `concept`.

 ## Memoria
 Añade tipo/símbolo y métodos.

### `const_literal`

> **const_literal**(s: ref to SemaState, node: int) -> SemaConst

 `const NAME [as T] is value`.

 ## Memoria
 Evalúa un literal constante simple.

 F3 sólo necesita valores para `const` de módulo; las expresiones complejas
 se dejan en `CkNone` y las resolverá el codegen/inferencia cuando exista el
 plegado completo. Aquí se cubren enteros (decimal/hex), bool, string y char,
 que son la mayoría de constantes de std.

 ## Memoria
 El string se interna en el pool; no asigna listas.

### `collect_const`

> **collect_const**(s: ref to SemaState, node: int) -> void

 Añade un símbolo y un valor constante POD.

### `starts_with_text`

> **starts_with_text**(s: string, prefix: string) -> bool

 `true` si `s` empieza por `prefix`.

 ## Memoria
 O(prefix); no asigna.

### `has_attribute`

> **has_attribute**(s: ref to SemaState, attrs: int, name: string) -> bool

 ¿Un nodo `attributes` contiene `name`?

 ## Memoria
 O(n); strings temporales liberados.

### `collect_weave`

> **collect_weave**(s: ref to SemaState, node: int, no_body: bool) -> void

 `weave`/`declare`/`antiquus`.

 ## Memoria
 Añade FnType/símbolo; `check` valida el cuerpo.

### `collect_params`

> **collect_params**(s: ref to SemaState, pnode: int, out: ref to ParamRange) -> void

 Recolecta params de una lista.

 ## Memoria
 Añade `SemaFnParam` y actualiza `first/count` por referencia.

### `find_attribute`

> **find_attribute**(s: ref to SemaState, attrs: int, name: string) -> int

 Nodo `attribute` llamado `name`, o `-1`.

 ## Memoria
 O(attrs).

### `check_mutates_method`

> **check_mutates_method**(s: ref to SemaState, m: int, recv: int, ft: int) -> void

 Valida `@mutates` en un método.

 Reglas stage0: sin argumentos; retorno `void` o el tipo receptor.

 ## Memoria
 Puede emitir diagnósticos; no posee recursos.

### `reject_free_mutates`

> **reject_free_mutates**(s: ref to SemaState, m: int) -> void

 Rechaza `@mutates` en una función libre/declare.

 ## Memoria
 O(attrs).

### `collect_method_sig`

> **collect_method_sig**(s: ref to SemaState, m: int) -> int

 Firma de un método de `enchanting`/`bind` (params y retorno).

 ## Memoria
 Añade fn_params y fn_info; devuelve el `TypeId`.

### `collect_bounds`

> **collect_bounds**(s: ref to SemaState, where_node: int) -> ParamRange

 Recoge los bounds de un `where_clause` en `types.bounds`.

 ## Memoria
 Añade TypeIds de concepto; devuelve `first/count`.

### `apply_bounds`

> **apply_bounds**(s: ref to SemaState, sid: int, br: ParamRange) -> void

 Aplica bounds a un símbolo ya definido.

 ## Memoria
 O(1).

### `reject_duplicate_primitive`

> **reject_duplicate_primitive**(s: ref to SemaState, recv: int, mname: int, m: int) -> void

 Rechaza métodos duplicados sobre un primitivo (coherencia).

 ## Memoria
 O(1); puede emitir diagnósticos.

### `mark_mutating`

> **mark_mutating**(s: ref to SemaState, m: int, sid: int) -> void

 Marca un método como `@mutates` en el símbolo.

 ## Memoria
 O(1).

### `tree_has_self`

> **tree_has_self**(s: ref to SemaState, node: int) -> bool

 ¿El subárbol contiene `self`?

 ## Memoria
 O(nodos).

### `tree_has_set`

> **tree_has_set**(s: ref to SemaState, node: int) -> bool

 ¿Hay un `set` sobre `self`/sus campos en el subárbol?

 Los `set` de locales no cuentan para `@mutates`.

 ## Memoria
 O(nodos).

### `concept_method_exists`

> **concept_method_exists**(s: ref to SemaState, name: int) -> bool

 ¿Existe un método de concepto con ese nombre?

 ## Memoria
 O(métodos de concepto).

### `define_get_alias`

> **define_get_alias**(s: ref to SemaState, recv: int, mname: int, ft: int, br: ParamRange, base_sid: int) -> void

 Registra el alias puro `get_<metodo>` si no existe.

 ## Memoria
 O(1); no asigna el nombre si ya existe.

### `collect_enchanting`

> **collect_enchanting**(s: ref to SemaState, node: int) -> void

 `enchanting`.

 ## Memoria
 Añade métodos al registro.

### `collect_bind`

> **collect_bind**(s: ref to SemaState, node: int) -> void

 `bind Tipo with Concepto:`: registra las implementaciones de método.

 ## Memoria
 Añade métodos al registro del tipo receptor.

### `collect_test`

> **collect_test**(s: ref to SemaState, node: int) -> void

 `test "nombre":`.

 ## Memoria
 Añade un símbolo de test.

