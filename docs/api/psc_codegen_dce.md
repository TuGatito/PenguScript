# psc.codegen.dce

> Source: `src/psc/codegen/dce.pengu`

psc/codegen/dce.pengu — reachability conservadora para el bundle.

F4 empezó emitiendo todas las funciones del catálogo, incluidas las de std
que el programa no usa. Esto hacía que una función no soportada rompiera un
programa que ni la llamaba. La poda exacta por texto C llega en F4j; esta
primera versión recorre el AST y las anotaciones de símbolo de F3, que es
suficiente para no emitir código muerto evidente.

---

### `CgReach`

> rune CgReach

```pengu
    live as list of bool
    seen as map of int to int
    types as map of int to int
```

 Conjunto de funciones vivas.

 ## Memoria
 Dueño de `live`; liberar con `free`.

### `new_reach`

> **new_reach**(n: int) -> CgReach

 Crea el conjunto.

 ## Memoria
 Asigna lista/mapa.

### `reach_free`

> **reach_free**(r: ref to CgReach) -> void

 Libera el conjunto.

 ## Memoria
 Libera lista/mapa.

### `module_is_std`

> **module_is_std**(m: SemaModule) -> bool

 `true` si un módulo es std (con fallback por ruta).

 ## Memoria
 O(n) en el path.

### `mark_symbol`

> **mark_symbol**(c: ref to CgContext, r: ref to CgReach, sid: int) -> void

 Marca un símbolo y encola su cuerpo.

 ## Memoria
 O(1); no posee strings.

### `last_token`

> **last_token**(ast: ref to PsAst, node: int) -> int

 Último token de un target.

 ## Memoria
 O(nodos).

### `scan_interp_node`

> **scan_interp_node**(c: ref to CgContext, r: ref to CgReach, ast: ref to PsAst, anns: ref to SemaAnnotations, node: int) -> void

 Recorre el AST de una interpolación en busca de llamadas.

 ## Memoria
 Recursión sobre el AST; no asigna salvo el conjunto.

### `scan_node`

> **scan_node**(c: ref to CgContext, r: ref to CgReach, m: SemaModule, ast: ref to PsAst, node: int) -> void

 Recorre un nodo buscando llamadas.

 ## Memoria
 Recursión sobre el AST; no asigna salvo el conjunto.

### `mark_type`

> **mark_type**(c: ref to CgContext, r: ref to CgReach, ty: int) -> void

 Marca un tipo y sus dependencias.

 ## Memoria
 O(tipos).

### `mark_node_types`

> **mark_node_types**(c: ref to CgContext, r: ref to CgReach, m: SemaModule, ast: ref to PsAst, node: int) -> void

 Marca los tipos anotados en un subárbol.

 ## Memoria
 Recursión sobre el AST.

### `type_live`

> **type_live**(r: ref to CgReach, ty: int) -> bool

 `true` si un tipo debe emitirse con `--prune-types`.

 ## Memoria
 O(1).

### `parent_module`

> **parent_module**(c: ref to CgContext, m: SemaModule) -> int

 Módulo padre de un `.d.pengu` (o `-1`).

 ## Memoria
 O(módulos).

### `compute`

> **compute**(c: ref to CgContext) -> CgReach

 Calcula reachability.

 ## Memoria
 Devuelve `CgReach` owned; liberar con `reach_free`.

### `live`

> **live**(r: ref to CgReach, idx: int) -> bool

 Indica si una función del catálogo está viva.

 ## Memoria
 O(1).

