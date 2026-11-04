# psc.driver.runner

> Source: `src/psc/driver/runner.pengu`

psc/driver/runner.pengu — ejecutar el artefacto de un build.

Nativo: exec directo. Wasm: `node <artifact>.js` (Emscripten escribe
`app.html`, `app.js` y `app.wasm`; el HTML no es ejecutable).

## Memoria
Construye argv owned y libera todo antes de volver.

---

### `copy`

> **copy**(s: string) -> string

 Copia owned.

 ## Memoria
 Devuelve string owned.

### `ends_with`

> **ends_with**(s: string, suffix: string) -> bool

 `true` si `s` termina en `suffix`.

 ## Memoria
 O(suffix); no asigna.

### `normalize`

> **normalize**(raw: int) -> int

 Normaliza el código de retorno de un proceso.

 `proc.run_argv` devuelve el estado crudo de `wait` en algunas plataformas.

 ## Memoria
 O(1).

### `js_path`

> **js_path**(artifact: string) -> string

 Ruta del loader JS de un artefacto wasm.

 ## Memoria
 Devuelve string owned.

### `chromium_path`

> **chromium_path**() -> maybe string

 Busca un navegador Chromium/Chrome para wasm headless.

 ## Memoria
 Devuelve un string owned o `maybe none`.

### `run_browser`

> **run_browser**(artifact: string) -> int

 Ejecuta un HTML wasm en Chromium headless con un servidor HTTP local.

 ## Memoria
 Libera temporales; el servidor se termina al acabar.

### `run`

> **run**(t: Target, artifact: string, argv: list of string, browser: bool) -> int

 Ejecuta `artifact` con los argumentos del programa.

 ## Memoria
 Libera argv y temporales.

