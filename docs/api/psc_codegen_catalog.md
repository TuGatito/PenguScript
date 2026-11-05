# psc.codegen.catalog

> Source: `src/psc/codegen/catalog.pengu`

psc/codegen/catalog.pengu — declaraciones C que el codegen debe emitir.

Recorre los módulos de F3 en orden topológico y registra funciones y firmas.
No interpreta cuerpos: eso es trabajo de `emit`/`stmt`/`expr`.

---

### `CgFunction`

> rune CgFunction

```pengu
    name as int
    symbol as int
    node as int
    module as int
    is_declare as bool
    is_antiquus as bool
    is_method as bool
    recv_type as int
    self_value as bool
    is_ritual as bool
    is_generated as bool
    tparams as list of int
    spec_args as list of int
    is_generic as bool
    is_spec as bool
    is_main as bool
    c_name as int
```

 Función declarada en un módulo.

### `CgType`

> rune CgType

```pengu
    type_id as int
    node as int
    module as int
    is_struct as bool
    is_omen as bool
```

 Tipo declarado en un módulo.

### `CgInclude`

> rune CgInclude

```pengu
    text as string
    module as int
```

 Include declarado en un módulo.

### `CgConst`

> rune CgConst

```pengu
    name as int
    type_id as int
    c_name as int
    module as int
    node as int
    value as SemaConst
```

 Constante de módulo.

### `CgCatalog`

> rune CgCatalog

```pengu
    functions as list of CgFunction
    by_symbol as map of int to int
    by_name as map of int to int
    types as list of CgType
    consts as list of CgConst
    includes as list of CgInclude
    by_type as map of int to int
    errors as int
    ambiguous as map of int to int
```

 Catálogo de funciones.

 ## Memoria
 Dueña de listas/mapas; `free` los libera.

### `new_catalog`

> **new_catalog**() -> CgCatalog

 Crea un catálogo vacío.

 ## Memoria
 Asigna listas/mapas.

### `catalog_free`

> **catalog_free**(c: ref to CgCatalog) -> void

 Libera el catálogo.

 ## Memoria
 Libera listas/mapas.

### `module_scope`

> **module_scope**(p: ref to SemaProgram, m: SemaModule) -> int

 Scope que contiene los símbolos de un módulo (compañero `.d.pengu` incluido).

 ## Memoria
 O(1).

### `decl_name_slot`

> **decl_name_slot**(ast: ref to PsAst, node: int) -> int

 Primer token de nombre de una declaración.

 ## Memoria
 O(nodos).

### `decl_name`

> **decl_name**(p: ref to SemaProgram, ast: ref to PsAst, src: ref to SourceFile, lex: ref to LexResult, node: int) -> int

 Nombre `NameId` de una declaración.

 ## Memoria
 Interna el texto.

### `module_fn_prefix`

> **module_fn_prefix**(p: ref to SemaProgram, m: SemaModule, node: int) -> string

 Prefijo C de funciones/consts de un módulo.

 Usa `insignia` si existe; si no, deriva del path (`lexer_`, `sema_api_`,
 `spark_`, `main_`) para evitar colisiones con locales y entre módulos.

 ## Memoria
 Devuelve string owned; liberar con `banish`.

### `add_function`

> **add_function**(p: ref to SemaProgram, c: ref to CgCatalog, m: SemaModule, node: int, is_declare: bool, is_antiquus: bool) -> void

 Registra una función si su símbolo F3 existe.

 ## Memoria
 Añade a listas/mapas; no posee strings.

### `deep_token_text`

> **deep_token_text**(m: SemaModule, ast: ref to PsAst, node: int) -> string

 Primer texto de token descendiendo por el primer hijo nodo.

 `first_token_text` sólo mira hijos directos; `type_or_param` envuelve un
 `custom_type` y luego un `dotted_path`, así que hay que bajar.

 ## Memoria
 Devuelve string owned.

### `catalog_type_from_ast`

> **catalog_type_from_ast**(p: ref to SemaProgram, m: SemaModule, node: int) -> int

 Convierte un nodo de tipo a `TypeId` durante la construcción del catálogo.

 El catálogo se construye antes de que exista un `CgContext`, así que no se
 puede usar `tast.from_ast`; se usa el mismo `convert.TypeCtx` de F3.

 ## Memoria
 Puede añadir diagnósticos; no posee strings.

### `has_type_param`

> **has_type_param**(p: ref to SemaProgram, id: int) -> bool

 `true` si el tipo contiene un parámetro `shard T`.

 El catálogo actual no especializa métodos genéricos: registrarlos como si
 fueran concretos emitía C con `void *` y rompía la compilación del propio
 compilador.  Se omiten hasta que exista especialización real; las funciones
 genéricas de módulo conservan su camino propio.

 ## Memoria
 O(profundidad del tipo).

### `underlying_type_id`

> **underlying_type_id**(p: ref to SemaProgram, id: int) -> int

 Resuelve alias/seal hasta el tipo subyacente.

 Los métodos de `enchanting Quaternion` (alias de `Vector4`) se registran en
 sema bajo `Vector4`; el catálogo debe buscar con el mismo id.

 ## Memoria
 O(profundidad); no asigna.

### `collect_enchanting`

> **collect_enchanting**(p: ref to SemaProgram, c: ref to CgCatalog, m: SemaModule, node: int) -> void

 Recorre un bloque `enchanting` y registra sus métodos.

 ## Memoria
 Añade al catálogo.

### `collect_type_params`

> **collect_type_params**(p: ref to SemaProgram, id: int, out: ref to list of int) -> void

 Registra un método de `enchanting`.

 ## Memoria
 Añade a listas/mapas; no posee strings.
 Añade los `NameId` de los type params presentes en un tipo.

 ## Memoria
 Añade a la lista prestada.

### `add_method`

> **add_method**(p: ref to SemaProgram, c: ref to CgCatalog, m: SemaModule, recv: int, node: int) -> void

_Undocumented._

### `collect_bind`

> **collect_bind**(p: ref to SemaProgram, c: ref to CgCatalog, m: SemaModule, node: int) -> void

 Recorre un bloque `bind <Type> with <Concept>` y registra sus métodos.

 `bind` bodies were previously invisible to the code generator: the symbol
 table knew about `int.cmp`, but the catalog (and therefore the emitted C) did
 not, so `calling x.cmp` lowered to a bare `cmp(...)`.  Registering the bind
 methods here makes bound concept methods ordinary catalog entries.

 ## Memoria
 Añade al catálogo.

### `safe_ident`

> **safe_ident**(s: string) -> string

 Registra una constante de módulo.

 ## Memoria
 Identificador C válido a partir de un nombre de módulo.

 Los módulos `.d.pengu` producen prefijos con punto (`raylib.d_`); un
 `#define` no puede contenerlo.

 ## Memoria
 Devuelve string owned.

### `c_ident_safe`

> **c_ident_safe**(s: string) -> string

 Sanea un identificador C: allowlist `[A-Za-z0-9_]` y guion bajo inicial si
 empieza por dígito.

 ## Memoria
 Devuelve string owned; liberar con `banish`.

### `add_const`

> **add_const**(p: ref to SemaProgram, c: ref to CgCatalog, m: SemaModule, node: int) -> void

 Añade a listas; no posee strings.

### `parse_int_text`

> **parse_int_text**(t: string) -> i64

 Entero de un token decimal/hex.

 ## Memoria
 No asigna.

### `const_fallback`

> **const_fallback**(p: ref to SemaProgram, m: SemaModule, node: int) -> SemaConst

 Evalúa constantes si F3 no guardó el valor (bootstrap stage2).

 ## Memoria
 Devuelve POD; strings se internan.

### `is_decl_path`

> **is_decl_path**(path: string) -> bool

 `true` si el módulo es un archivo de declaración `.d.pengu`.

 Su C ya viene de los `include` de cabecera; volver a emitir `struct`/`enum`
 duplicaría las definiciones del header.

 ## Memoria
 O(sufijo); no asigna.

### `add_type`

> **add_type**(p: ref to SemaProgram, c: ref to CgCatalog, m: SemaModule, node: int, is_struct: bool, is_omen: bool) -> void

 Registra un tipo de un módulo.

 ## Memoria
 Añade a listas/mapas; no posee strings.

### `collect_top_node`

> **collect_top_node**(p: ref to SemaProgram, c: ref to CgCatalog, m: SemaModule, o: CgOptions, node0: int) -> void

 Registra un nodo top-level (o una rama viva de `when`).

 ## Memoria
 Añade al catálogo; los strings de include son owned por el AST.

### `collect_module`

> **collect_module**(p: ref to SemaProgram, c: ref to CgCatalog, m: SemaModule, o: CgOptions) -> void

 Recorre un módulo y registra sus funciones top-level.

 `o` son las opciones de codegen para resolver `when` comptime.

 ## Memoria
 Añade al catálogo.

### `catalog_collect`

> **catalog_collect**(p: ref to SemaProgram, o: CgOptions) -> CgCatalog

 Construye el catálogo completo en orden topológico.

 ## Memoria
 Recorre todos los módulos; no libera el programa.

