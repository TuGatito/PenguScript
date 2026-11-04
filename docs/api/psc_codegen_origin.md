# psc.codegen.origin

> Source: `src/psc/codegen/origin.pengu`

psc/codegen/origin.pengu — line markers y mapa de origen.

F4 emite `#line` para que gcc/clang/MSVC señalen el `.pengu`. El origin map
completo se añadirá en F4l; este módulo centraliza el cálculo de línea.

---

### `line_of`

> **line_of**(m: SemaModule, node: int) -> int

 Línea 1-indexed de un nodo.

 ## Memoria
 O(nodos).

### `marker`

> **marker**(c: ref to CgContext, m: SemaModule, node: int) -> void

 Emite `#line` para un nodo si está activado.

 ## Memoria
 Strings temporales liberados.

