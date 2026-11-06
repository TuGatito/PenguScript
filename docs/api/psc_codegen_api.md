# psc.codegen.api

> Source: `src/psc/codegen/api.pengu`

psc/codegen/api.pengu — API pública de codegen F4.

Recibe un `SemaProgram` ya comprobado por F3 y devuelve un `bundle.c` owned.
No invoca el compilador C ni toca el sistema de archivos.

---

### `CgResult`

> rune CgResult

```pengu
    ok as bool
    bundle as string
    error as string
    stats as CgStats
    live_modules as list of int
```

 Resultado de una emisión.

 ## Memoria
 `bundle` es owned; liberar con `free_result`.

### `default_options`

> **default_options**(base_dir: string) -> CgOptions

 Opciones por defecto (reexportadas para la CLI).

 ## Memoria
 Strings prestados.

### `generate_c`

> **generate_c**(p: ref to SemaProgram, o: CgOptions) -> CgResult

 Genera C para un programa.

 ## Memoria
 Devuelve un resultado owned; el programa sigue siendo del llamador.

### `free_result`

> **free_result**(r: ref to CgResult) -> void

 Libera un resultado.

 ## Memoria
 Libera el bundle y el error.

### `CgUnitsResult`

> rune CgUnitsResult

```pengu
    ok as bool
    header as string
    core as string
    units as list of CgUnit
    error as string
    live_modules as list of int
```

 Resultado de una emisión multiunidad (F7).

 ## Memoria
 Textos owned; liberar con `free_units`.

### `generate_units`

> **generate_units**(p: ref to SemaProgram, o: CgOptions) -> CgUnitsResult

 Genera cabecera, core y una unidad C por módulo.

 ## Memoria
 Devuelve textos owned; el programa sigue siendo del llamador.

### `free_units`

> **free_units**(r: ref to CgUnitsResult) -> void

 Libera un resultado multiunidad.

 ## Memoria
 Libera cabecera, core, unidades y error.

