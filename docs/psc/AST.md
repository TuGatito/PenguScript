# AST de PSC (F2)

El AST de PSC es un árbol **plano por índices**. No hay un `alloc` por nodo ni
punteros recursivos: los nodos viven en `PsAst.nodes` y los hijos en una lista
paralela `PsAst.children`. El parser construye los nodos en **post-orden**
(hijos antes que el padre), de modo que los hijos de cada nodo son contiguos.

## 1. Tipos

```pengu
rune PsNode derive Par:
    kind as NodeKind
    start as int
    end as int
    first_child as int
    child_count as int
    aux as int

rune PsLoopLabel derive Par:
    node as int
    token as int

rune PsAst derive Nexus:
    nodes as list of PsNode
    children as list of int
    labels as list of PsLoopLabel
```

- `start`/`end` son offsets de byte half-open.
- `aux` es un payload por tipo de nodo. Hoy se usa para el token del operador
  en nodos binarios/comparaciones/unarios/rango; en el resto vale `0`.
- `banish ast` libera las tres listas. Los nodos y etiquetas son POD.

## 2. Codificación de hijos

| Valor de `children[i]` | Significado |
|---:|---|
| `0` | hijo ausente (`None` de Lark) |
| `> 0` | nodo `id = valor - 1` |
| `< 0` | token `id = -valor - 1` |

Los tokens son los de `LexResult.tokens`; no se copian. El AST **presta**
`SourceFile` y `LexResult`: el llamador debe mantenerlos vivos mientras use el
AST.

Helpers:

```pengu
calling ast.child_of with id, slot        # hijo codificado o 0
calling ast.child_node_of with id, slot   # id de nodo o -1
calling ast.child_token_of with id, slot  # índice de token o -1
calling ast.kind_of with id
calling ast.child_count_of with id
calling ast.label_of with id              # token de etiqueta o -1
```

## 3. Construcción (solo parser)

El parser usa una pila de trabajo en `PsParser`:

```pengu
calling ps_begin_children with p
calling ps_add_child with p, child_node
calling ps_add_token with p, token_index
calling ps_add_absent with p
var id as int is calling ps_finish_node with p, NodeKind.NdAdd, start, end, op_token
```

`ps_finish_node` copia los hijos acumulados desde la última marca a
`ast.children`, crea el `PsNode` y limpia la pila. No se debe crear un nodo y
añadirle hijos después.

## 4. Fidelidad a stage0

El árbol replica los nombres y la aridad de las reglas de
`pengu_parser/pengu_grammar.py`, incluidos los placeholders `None` de Lark.
Esto permite comparar 1:1 con stage0 y portar F3/F4 nodo a nodo.

Rarezas que **no** son accidentes y están cubiertas por tests:

- `when_variant` vacío representa `maybe none`.
- `arrow_access` tiene 1 hijo cuando es un `access_op` de un target
  (`calling x->f`) y 2 cuando es postfix (`x->f`).
- `to_expr` se usa tanto para `a to b` como para el cast `(a to T)`.
- `for_in_stmt` tiene 3 hijos con un nombre y 4 con dos; no hay placeholder
  para el segundo nombre.
- `declare_params` termina en `_` cuando hay parámetros pero no `...`.
- `when_stmt`, `if_stmt`, `while_stmt` y `for_*` usan un `block`; en cambio
  `when_else_plain`, `with_stmt`, `with_init_expr`, `do_expr` y `or_block`
  llevan sus `stmt` directamente (como stage0).
- `echo_decl` no lleva `attributes`; `rune_decl` sí.
- `type_or_param` envuelve los tipos en `list/slice/many/map/maybe/result` y en
  el receptor de `enchanting`; para `shard T` se usa `shard_param_ref` directo.
- Los loops etiquetados no usan el wrapper `labeled_loop`: la etiqueta vive en
  `PsAst.labels` y se consulta con `label_of`.
- `judge_expr`/`judge_over_expr` añaden `_` cuando no hay `else`.

## 5. Nodos especiales

- `NdError`: recuperación. Puede aparecer donde faltaba un constructo. Se
  imprime como `error`; F3 lo ignora/recupera y `ok=false`.
- No hay nodo `labeled_loop` ni `ANTIQUUS_BODY_PLACEHOLDER`.
- El cuerpo de `antiquus` es un token (`TokAntiquusBody`), no un string
  parseado.

## 6. Inventario de `NodeKind`

Los nombres de variante son `Nd` + PascalCase; `ps_node_kind_name` devuelve el
nombre de stage0 (el que usa el dump).

### Archivo, top-level y declaraciones

`start`, `file`, `top_stmt`, `import_stmt`, `dotted_path`, `include_stmt`,
`link_stmt`, `ldflag_stmt`, `insignia_stmt`, `attributes`, `attribute`,
`attribute_args`, `const_decl`, `var_decl`, `let_decl`, `var_name_list`,
`static_var_decl`, `rune_decl`, `echo_decl`, `field_decl`, `cyclus_kw`,
`shard_params`, `shard_param_ref`, `where_clause`, `where_bound`,
`derive_clause`, `omen_decl`, `omen_variant`, `omen_field`, `omen_string_kind`,
`alias_decl`, `seal_decl`, `concept_decl`, `concept_method`, `bind_decl`,
`weave_decl`, `weave_modifier`, `param_list`, `param`, `enchanting_decl`,
`antiquus_decl`, `declare_stmt`, `declare_params`, `test_decl`,
`when_top_decl`, `when_top_else_plain`, `when_top_else_when`.

### Statements

`stmt`, `block`, `set_stmt`, `compound_set_stmt`, `set_target`, `with_target`,
`normal_target`, `essence_target`, `if_stmt`, `if_cond`, `if_cond_binding`,
`unless_stmt`, `while_stmt`, `for_range_stmt`, `for_in_stmt`, `when_stmt`,
`when_else_plain`, `when_else_when`, `else_block`, `with_stmt`, `unsafe_stmt`,
`defer_stmt`, `errdefer_stmt`, `banish_stmt`, `return_stmt`, `break_stmt`,
`continue_stmt`, `expr_stmt`, `continue_simple`, `break_simple`,
`return_simple`, `set_simple`, `compound_set_simple`, `simple_stmt`.

### Expresiones

`or_else`, `or_return`, `or_block`, `try_expr`, `if_expr`, `when_expr`,
`judge_expr`, `judge_over_expr`, `for_comp`, `bool_or`, `bool_and`, `eq`,
`ne`, `lt`, `le`, `gt`, `ge`, `in_expr`, `not_in_expr`, `is_present`,
`is_not_present`, `is_true`, `is_false`, `range_dotdot`, `to_expr`,
`bitwise_or`, `bitwise_and`, `bitwise_xor`, `shl`, `shr`, `add`, `sub`, `mul`,
`div`, `mod`, `bit_not`, `log_not`, `neg`, `sigil_of`, `essence_of`,
`transmute`, `size_of`, `type_of`, `some_expr`, `banish_expr`, `ord_expr`,
`chr_expr`, `bytes_expr`.

### Llamadas, acceso, literales y contenedores

`calling_expr`, `generic_args`, `arg_list`, `pos_arg`, `named_arg`,
`field_access`, `arrow_access`, `at_expr`, `slice_at_expr`, `length_expr`,
`at_access`, `dot_access`, `slice_range`, `paren_expr`, `var_ref`, `self_ref`,
`int_lit`, `float_lit`, `string_lit`, `char_lit`, `true_lit`, `false_lit`,
`null_lit`, `maybe_none`, `error_lit`, `donum_expr`, `defined_expr`,
`struct_init`, `field_init`, `with_init_expr`, `do_expr`, `lambda_expr`,
`lambda_no_params`, `lambda_param`, `lambda_param_list`, `list_init_expr`,
`map_init_expr`, `array_init_expr`, `array_lit`, `map_lit`, `map_entry`,
`field_entry`, `indent_literal`, `indent_array`, `indent_row`,
`indent_entries`.

### Patrones

`when_clause`, `when_pattern`, `when_variant`, `when_payload`, `when_field`,
`field_pattern`, `field_tuple`, `when_guard`, `else_clause`.

### Tipos

`type_or_param`, `ref_type`, `frozen_type`, `fn_type`, `fn_param_list`,
`fn_param`, `array_type`, `slice_type`, `many_type`, `list_type`, `map_type`,
`maybe_type`, `result_type`, `opaque_type`, `base_type`, `custom_type`,
`tuple_type`.

## 7. AST dump canónico

```text
# psc-ast-dump v1
# file: <ruta>
# sha256: <hex>
# bytes: <n>
# nodes: <n>
start
  file
    top_stmt
      import_stmt
        dotted_path
          "std"
          "spark"
        _
```

- Nodo: nombre de stage0.
- Token: `"texto"` con escapes C; CRLF se normaliza a LF solo en el dump.
- Ausente: `_`.
- Loop etiquetado: `for_in_stmt @label "outer"`.
- `antiquus`: cuerpo decodificado.
- Sin posiciones (los spans se prueban con tokens/fixtures).

El oráculo `psc/tools/lark_ast_oracle.py` produce el mismo formato desde Lark y
compara los 205 archivos del corpus actual (204 exactos + 1 allowlist
documentado en `ast_allowlist.txt`).

## 8. Cómo añadir un nodo

1. Añadir la variante `Nd...` a `psc/src/psc/ast/kind.pengu` y su caso en
   `ps_node_kind_name`.
2. Documentar aquí su arreglo de hijos y placeholders.
3. Construirlo con `ps_begin_children`/`ps_finish_node`.
4. Añadir un test en `parser_unit.pengu` y, si aparece en corpus, ejecutar el
   oráculo.
5. Actualizar golden solo si el cambio es intencionado.
