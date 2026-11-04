# psc.lsp.layout

> Source: `src/psc/lsp/layout.pengu`

psc/lsp/layout.pengu — layout C (size/align) de los tipos de PenguScript.

El ABI v3 es de 64 bits: `pengu_runtime.h` documenta los descriptores del
runtime y el codegen emite `struct`/`union` de C. Este módulo calcula el
mismo layout que el compilador C (padding incluido) para el hover y los
Inlay Hints. No sustituye a `size of`: es una consulta del LSP.

## Memoria
No asigna: sólo recorre la tabla de tipos del programa.

---

### `align_up`

> **align_up**(n: int, a: int) -> int

 Redondea `n` al siguiente múltiplo de `a`.

### `base_align`

> **base_align**(nm: string) -> int

 Alineación de un primitivo por nombre canónico.

### `base_size`

> **base_size**(nm: string) -> int

 Tamaño de un primitivo por nombre canónico.

### `align_of`

> **align_of**(p: ref to SemaProgram, type_id: int, depth: int) -> int

 Alineación de un tipo (`1` si no se puede calcular).

### `size_of`

> **size_of**(p: ref to SemaProgram, type_id: int, depth: int) -> int

 Tamaño en bytes de un tipo, con padding y alineación del ABI v3 (64-bit).

### `type_align`

> **type_align**(p: ref to SemaProgram, type_id: int) -> int

 Alineación pública de un tipo.

### `type_size`

> **type_size**(p: ref to SemaProgram, type_id: int) -> int

 Tamaño público de un tipo.

