# psc.parse.patterns.core

> Source: `src/psc/parse/patterns/core.pengu`

psc/parse/patterns/core.pengu — patrones de `judge`/`when`.

Un `when_clause` es `when <patrón> [with <payload>] [if <guarda>] -> <body>`.
Los patrones se representan como en stage0: los literales simples quedan
como tokens, los nombres cualificados como `when_variant`, y `maybe none`
como un `when_variant` vacío (la forma que produce Lark).

## Memoria
Construye nodos en el AST; no asigna strings salvo diagnósticos.

---

### `ppat_parse_when_clause`

> **ppat_parse_when_clause**(p: ref to PsParser) -> int

 Parsea una cláusula `when ...`.

 ## Memoria
 Crea un nodo `when_clause`.

### `ppat_parse_pattern`

> **ppat_parse_pattern**(p: ref to PsParser) -> int

 Parsea un patrón completo, con alternativas `|`.

 ## Memoria
 Crea un nodo `when_pattern`.

### `ppat_add_variant`

> **ppat_add_variant**(p: ref to PsParser) -> void

 Añade una variante al patrón en construcción.

 ## Memoria
 Añade un token o un nodo `when_variant`.

### `ppat_finish_empty`

> **ppat_finish_empty**(p: ref to PsParser, kind: NodeKind, start: int) -> int

 Cierra un nodo vacío en `start`.

 ## Memoria
 Crea un nodo sin hijos.

### `ppat_parse_payload`

> **ppat_parse_payload**(p: ref to PsParser) -> int

 Parsea `with field, field...`.

 ## Memoria
 Crea un nodo `when_payload`.

### `ppat_parse_when_field`

> **ppat_parse_when_field**(p: ref to PsParser) -> int

 Parsea `NAME [as pattern]`.

 ## Memoria
 Crea un nodo `when_field`.

### `ppat_parse_field_pattern`

> **ppat_parse_field_pattern**(p: ref to PsParser) -> int

 Parsea un patrón de campo: tupla o estado cualificado.

 ## Memoria
 Crea `field_tuple` o `field_pattern`.

### `ppat_parse_guard`

> **ppat_parse_guard**(p: ref to PsParser) -> int

 Parsea una guarda `if expr` / `when expr`.

 ## Memoria
 Crea un nodo `when_guard`.

