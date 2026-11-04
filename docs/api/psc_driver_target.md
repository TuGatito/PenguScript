# psc.driver.target

> Source: `src/psc/driver/target.pengu`

psc/driver/target.pengu — modelo de target de compilación.

Un `Target` describe para qué plataforma se compila. En este MVP se aceptan
el host nativo y `wasm32-unknown-emscripten` (alias `wasm`, `wasm32`,
`emscripten`). `wasm32-wasi` se reconoce para poder rechazarlo con un mensaje
claro, y cualquier otro triple de cross-compilación se rechaza hasta que el
driver tenga soporte real.

## Memoria
Todos los strings son owned; liberar con `free`.

---

### `Target`

> rune Target

```pengu
    ok as bool
    error as string
    raw as string
    triple as string
    os as string
    arch as string
    env as string
    is_wasm as bool
    wasm_target as string
    is_host as bool
```

 Plataforma de compilación.

 ## Memoria
 Strings owned; liberar con `free`.

### `copy`

> **copy**(s: string) -> string

 Copia owned de un string.

 ## Memoria
 Devuelve string owned.

### `arch_name`

> **arch_name**(s: string) -> string

 Normaliza un nombre de arquitectura a la ortografía del compilador.

 ## Memoria
 Devuelve string owned.

### `host_os`

> **host_os**() -> string

 SO del host en el vocabulario de `Target`.

 ## Memoria
 Devuelve string owned.

### `clone`

> **clone**(t: Target) -> Target

 Copia owned de un target.

 ## Memoria
 Devuelve strings owned; liberar con `free`.

### `host`

> **host**() -> Target

 Target del host.

 ## Memoria
 Devuelve strings owned; liberar con `free`.

### `wasm_target`

> **wasm_target**(which: string, raw_text: string) -> Target

 Target wasm canónico.

 ## Memoria
 Devuelve strings owned; liberar con `free`.

### `failed`

> **failed**(msg: string) -> Target

 Target de error.

 ## Memoria
 Devuelve strings owned; liberar con `free`.

### `parse`

> **parse**(text: string) -> Target

 Interpreta `--target` / `[build] target`.

 Acepta `""` (host), `wasm`, `wasm32`, `emscripten`,
 `wasm32-unknown-emscripten`, `wasm32-wasi`/`wasi`, y triples del host.
 Cualquier otro triple se rechaza: el driver todavía no hace cross-compilation
 nativa real.

 ## Memoria
 Devuelve strings owned; liberar con `free`.

### `free`

> **free**(t: ref to Target) -> void

 Libera un target.

 ## Memoria
 Libera todos los strings.

### `apply_sema`

> **apply_sema**(t: Target, o: ref to SemaOptions) -> void

 Aplica un target a las opciones semánticas (copia owned de los strings).

 ## Memoria
 Reemplaza los strings owned de `o`; el llamador conserva el target.

### `apply_cg`

> **apply_cg**(t: Target, o: ref to CgOptions) -> void

 Aplica un target a las opciones de codegen (strings prestados).

 El target debe sobrevivir al codegen; el llamador lo garantiza.

 ## Memoria
 No asigna; asigna vistas.

