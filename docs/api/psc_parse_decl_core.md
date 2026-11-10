# psc.parse.decl.core

> Source: `src/psc/parse/decl/core.pengu`

psc/parse/decl/core.pengu — declaraciones top-level.

Aquí viven `import`/`include`/`link`/`ldflag`/`insignia`, los tipos
nominales (`rune`, `echo`, `omen`, `alias`, `seal`), `concept`, `bind`,
`weave`, `enchanting`, `antiquus`, `declare`, `test` y `when` top-level.
Las declaraciones locales (`var`/`let`/`const`/`static`) se reutilizan de
`stmt/core.pengu`.

## Memoria
Construye nodos en el AST; no asigna strings salvo diagnósticos.

---

### `pdecl_parse_file`

> **pdecl_parse_file**(p: ref to PsParser) -> int

 Parsea un archivo completo y devuelve la raíz `start`.

 ## Memoria
 Crea `start -> file -> top_stmt*`.

### `pdecl_parse_file_body`

> **pdecl_parse_file_body**(p: ref to PsParser) -> int

 Parsea el nodo `file`.

 ## Memoria
 Crea `file` con los `top_stmt`.

### `pdecl_parse_top_stmt`

> **pdecl_parse_top_stmt**(p: ref to PsParser) -> int

 Parsea un `top_stmt` y lo envuelve.

 ## Memoria
 Crea un nodo `top_stmt`.

### `pdecl_parse_top_inner`

> **pdecl_parse_top_inner**(p: ref to PsParser, attrs: int) -> int

 Despacha una declaración top-level.

 ## Memoria
 Construye el nodo de la declaración.

### `pdecl_token_text`

> **pdecl_token_text**(p: ref to PsParser) -> string

 Texto del token actual para un diagnóstico.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `pdecl_parse_import`

> **pdecl_parse_import**(p: ref to PsParser) -> int

 Parsea `import dotted [as NAME]`.

 ## Memoria
 Crea un nodo `import_stmt`.

### `pdecl_parse_string_top`

> **pdecl_parse_string_top**(p: ref to PsParser, kind: NodeKind) -> int

 Parsea `include/link/ldflag "..."`.

 ## Memoria
 Crea un nodo con el token string.

### `pdecl_parse_insignia`

> **pdecl_parse_insignia**(p: ref to PsParser) -> int

 Parsea `insignia NAME`.

 ## Memoria
 Crea un nodo `insignia_stmt`.

### `pdecl_parse_attributes`

> **pdecl_parse_attributes**(p: ref to PsParser) -> int

 Parsea cero o más atributos `@...`.

 ## Memoria
 Crea un nodo `attributes` (posiblemente vacío).

### `pdecl_parse_attribute`

> **pdecl_parse_attribute**(p: ref to PsParser) -> int

 Parsea `@ NAME [ "(" args ")" ] [NEWLINE]`.

 ## Memoria
 Crea un nodo `attribute`.

### `pdecl_parse_attribute_args`

> **pdecl_parse_attribute_args**(p: ref to PsParser) -> int

 Parsea `(arg, arg...)` de un atributo.

 ## Memoria
 Crea un nodo `attribute_args`.

### `pdecl_parse_modifiers_into`

> **pdecl_parse_modifiers_into**(p: ref to PsParser) -> void

 Parsea `inline`/`ritual` (modificadores soft).

 ## Memoria
 Crea nodos `weave_modifier`.

### `pdecl_parse_record`

> **pdecl_parse_record**(p: ref to PsParser, kind: NodeKind, attrs: int) -> int

 Parsea `rune`/`echo`.

 ## Memoria
 Crea el nodo de registro con sus campos.

### `pdecl_parse_fundere`

> **pdecl_parse_fundere**(p: ref to PsParser) -> int

 Parsea `fundere type [as name] (,|and type [as name])*`.

 ## Memoria
 Crea un nodo `fundere_clause` con sus `embed`.

### `pdecl_parse_embed`

> **pdecl_parse_embed**(p: ref to PsParser) -> int

 Parsea `type [as name]` de una cláusula `fundere`.

 ## Memoria
 Crea un nodo `embed` con el tipo y el nombre opcional.

### `pdecl_parse_field`

> **pdecl_parse_field**(p: ref to PsParser) -> int

 Parsea un campo `@attrs NAME as type`.

 ## Memoria
 Crea un nodo `field_decl`.

### `pdecl_parse_omen`

> **pdecl_parse_omen**(p: ref to PsParser) -> int

 Parsea `omen NAME ...:`.

 ## Memoria
 Crea un nodo `omen_decl` con sus variantes.

### `pdecl_parse_omen_variant`

> **pdecl_parse_omen_variant**(p: ref to PsParser) -> int

 Parsea una variante de `omen`.

 ## Memoria
 Crea un nodo `omen_variant`.

### `pdecl_parse_omen_field`

> **pdecl_parse_omen_field**(p: ref to PsParser) -> int

 Parsea `NAME as type` de una variante.

 ## Memoria
 Crea un nodo `omen_field`.

### `pdecl_parse_alias`

> **pdecl_parse_alias**(p: ref to PsParser) -> int

 Parsea `alias NAME [shard...] as type`.

 ## Memoria
 Crea un nodo `alias_decl`.

### `pdecl_parse_seal`

> **pdecl_parse_seal**(p: ref to PsParser) -> int

 Parsea `seal NAME as type`.

 ## Memoria
 Crea un nodo `seal_decl`.

### `pdecl_parse_concept`

> **pdecl_parse_concept**(p: ref to PsParser) -> int

 Parsea `concept NAME [shard] : methods`.

 ## Memoria
 Crea un nodo `concept_decl`.

### `pdecl_parse_concept_method`

> **pdecl_parse_concept_method**(p: ref to PsParser) -> int

 Parsea un método de `concept` (sin cuerpo).

 ## Memoria
 Crea un nodo `concept_method`.

### `pdecl_parse_bind`

> **pdecl_parse_bind**(p: ref to PsParser) -> int

 Parsea `bind TYPE with CUSTOM [shard] : weaves`.

 ## Memoria
 Crea un nodo `bind_decl`.

### `pdecl_parse_weave`

> **pdecl_parse_weave**(p: ref to PsParser, attrs: int) -> int

 Parsea `weave ...: cuerpo`.

 ## Memoria
 Crea un nodo `weave_decl`.

### `pdecl_parse_enchanting`

> **pdecl_parse_enchanting**(p: ref to PsParser) -> int

 Parsea `enchanting RECEIVER [shard|where] : weaves`.

 ## Memoria
 Crea un nodo `enchanting_decl`.

### `pdecl_parse_declare`

> **pdecl_parse_declare**(p: ref to PsParser, attrs: int) -> int

 Parsea `declare ...` (sin cuerpo).

 ## Memoria
 Crea un nodo `declare_stmt`.

### `pdecl_parse_antiquus`

> **pdecl_parse_antiquus**(p: ref to PsParser, attrs: int) -> int

 Parsea `antiquus ...:` + cuerpo C.

 ## Memoria
 Crea un nodo `antiquus_decl` con el token del cuerpo.

### `pdecl_parse_test`

> **pdecl_parse_test**(p: ref to PsParser) -> int

 Parsea `test "nombre": ...`.

 ## Memoria
 Crea un nodo `test_decl` con los `stmt` hijos.

### `pdecl_parse_when_top`

> **pdecl_parse_when_top**(p: ref to PsParser) -> int

 Parsea `when cond:` con declaraciones top-level.

 ## Memoria
 Crea un nodo `when_top_decl`.

### `pdecl_parse_when_top_else`

> **pdecl_parse_when_top_else**(p: ref to PsParser) -> int

 Parsea el `else` de un `when` top-level.

 ## Memoria
 Crea `when_top_else_plain` o `when_top_else_when`.

### `pdecl_parse_param_list`

> **pdecl_parse_param_list**(p: ref to PsParser) -> int

 Parsea `with param (, param)*`.

 ## Memoria
 Crea un nodo `param_list`.

### `pdecl_parse_param`

> **pdecl_parse_param**(p: ref to PsParser) -> int

 Parsea `NAME as type [is default]`.

 ## Memoria
 Crea un nodo `param`.

### `pdecl_parse_declare_params`

> **pdecl_parse_declare_params**(p: ref to PsParser) -> int

 Parsea `with` + parámetros de `declare` y `...`.

 ## Memoria
 Crea un nodo `declare_params`.

### `pdecl_add_name_token`

> **pdecl_add_name_token**(p: ref to PsParser) -> void

 Añade el token del nombre actual o emite un error.

 ## Memoria
 O(1), no asigna.

### `pdecl_empty_node_here`

> **pdecl_empty_node_here**(p: ref to PsParser, kind: NodeKind) -> int

 Crea un nodo vacío en la posición actual sin consumir nada.

 ## Memoria
 Crea un nodo POD.

