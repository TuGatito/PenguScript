# psc.parse.expr.atoms

> Source: `src/psc/parse/expr/atoms.pengu`

psc/parse/expr/atoms.pengu — átomos de expresión.

Cubre `primary` de la gramática: nombres, literales, paréntesis,
contenedores, `with` struct-init, `with:`, `do:`, `lambda`, `donum` y
`defined`. Las expresiones anidadas se piden a los hooks de
`PsHooks`, que apuntan a `expr/ops.pengu`; así este archivo no importa
`ops` y no hay ciclo.

## Memoria
Construye nodos en el AST. Los strings solo se crean para diagnósticos.

---

### `patom_nested_expr`

> **patom_nested_expr**(p: ref to PsParser) -> int

 Pide una expresión completa al hook.

 ## Memoria
 Llama a `PsHooks.expr`; no asigna.

### `patom_nested_list_expr`

> **patom_nested_list_expr**(p: ref to PsParser) -> int

 Pide una expresión de lista al hook.

 ## Memoria
 Llama a `PsHooks.list_expr`; no asigna.

### `patom_nested_list_value`

> **patom_nested_list_value**(p: ref to PsParser) -> int

 Pide una expresión de lista de valor al hook.

 ## Memoria
 Llama a `PsHooks.list_value_expr`; no asigna.

### `patom_leaf`

> **patom_leaf**(p: ref to PsParser, kind: NodeKind) -> int

 Crea un nodo hoja con el token actual y avanza.

 ## Memoria
 Crea un nodo y avanza un token.

### `patom_empty`

> **patom_empty**(p: ref to PsParser, kind: NodeKind) -> int

 Crea un nodo sin hijos y avanza.

 ## Memoria
 Crea un nodo y avanza un token.

### `patom_parse_primary`

> **patom_parse_primary**(p: ref to PsParser) -> int

 Parsea `primary`.

 ## Memoria
 Construye el nodo correspondiente en el AST.

### `patom_parse_keyword_atom`

> **patom_parse_keyword_atom**(p: ref to PsParser) -> int

 Átomos que empiezan por keyword.

 ## Memoria
 Construye el nodo correspondiente.

### `patom_parse_paren`

> **patom_parse_paren**(p: ref to PsParser) -> int

 Parsea `( expr )`.

 ## Memoria
 Crea un nodo `paren_expr`.

### `patom_parse_array_lit`

> **patom_parse_array_lit**(p: ref to PsParser) -> int

 Parsea un array literal `[a, b, ...]`.

 ## Memoria
 Crea un nodo `array_lit`.

### `patom_parse_map_lit`

> **patom_parse_map_lit**(p: ref to PsParser) -> int

 Parsea un map literal `{clave: valor, ...}`.

 ## Memoria
 Crea un nodo `map_lit` con `map_entry`.

### `patom_parse_map_entry`

> **patom_parse_map_entry**(p: ref to PsParser) -> int

 Parsea una entrada de mapa/clave.

 ## Memoria
 Crea un nodo `map_entry`.

### `patom_parse_struct_init`

> **patom_parse_struct_init**(p: ref to PsParser) -> int

 Parsea `with campo is valor, ...`.

 ## Memoria
 Crea un nodo `struct_init` con `field_init`.

### `patom_parse_field_init`

> **patom_parse_field_init**(p: ref to PsParser) -> int

 Parsea un campo de `with`.

 Si el slot es un único nombre, se expande a `nombre is nombre`, igual que
 hace stage0 antes de parsear.

 ## Memoria
 Crea un nodo `field_init`.

### `patom_parse_list_init`

> **patom_parse_list_init**(p: ref to PsParser) -> int

 Parsea `list of T [with capacity expr]`.

 ## Memoria
 Crea un nodo `list_init_expr`.

### `patom_parse_map_init`

> **patom_parse_map_init**(p: ref to PsParser) -> int

 Parsea `map of K to V`.

 ## Memoria
 Crea un nodo `map_init_expr`.

### `patom_parse_array_init`

> **patom_parse_array_init**(p: ref to PsParser) -> int

 Parsea `array of T with size N`.

 ## Memoria
 Crea un nodo `array_init_expr`.

### `patom_parse_lambda`

> **patom_parse_lambda**(p: ref to PsParser) -> int

 Parsea `lambda [params] into expr`.

 ## Memoria
 Crea `lambda_expr` o `lambda_no_params`.

### `patom_parse_lambda_params`

> **patom_parse_lambda_params**(p: ref to PsParser) -> int

 Parsea la lista de parámetros de una lambda.

 ## Memoria
 Crea un nodo `lambda_param_list`.

### `patom_parse_lambda_param`

> **patom_parse_lambda_param**(p: ref to PsParser) -> int

 Parsea `NAME as type`.

 ## Memoria
 Crea un nodo `lambda_param`.

### `patom_parse_donum`

> **patom_parse_donum**(p: ref to PsParser) -> int

 Parsea `donum T`.

 ## Memoria
 Crea un nodo `donum_expr`.

### `patom_parse_defined`

> **patom_parse_defined**(p: ref to PsParser) -> int

 Parsea `defined(NAME)`.

 ## Memoria
 Crea un nodo `defined_expr`.

### `patom_parse_indent_literal`

> **patom_parse_indent_literal**(p: ref to PsParser) -> int

 Parsea un literal indentado (valor de `var`/`const`).

 ## Memoria
 Crea `indent_literal` y sus filas/entradas.

### `patom_is_entry_start`

> **patom_is_entry_start**(p: ref to PsParser) -> bool

 `true` si la primera línea del literal indentado es una entrada.

 ## Memoria
 O(1), no asigna.

### `patom_parse_indent_rows`

> **patom_parse_indent_rows**(p: ref to PsParser) -> int

 Parsea filas de un literal indentado.

 ## Memoria
 Crea un nodo `indent_array` con `indent_row`.

### `patom_parse_indent_row`

> **patom_parse_indent_row**(p: ref to PsParser) -> int

 Parsea una fila de un literal indentado.

 ## Memoria
 Crea un nodo `indent_row`.

### `patom_parse_indent_entries`

> **patom_parse_indent_entries**(p: ref to PsParser) -> int

 Parsea entradas de un literal indentado.

 ## Memoria
 Crea un nodo `indent_entries`.

### `patom_parse_indent_entry`

> **patom_parse_indent_entry**(p: ref to PsParser) -> int

 Parsea una entrada `clave: valor` o `campo is valor`.

 ## Memoria
 Crea `map_entry` o `field_entry`.

