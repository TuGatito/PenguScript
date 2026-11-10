# std.web.npm

> Source: `std/web/npm.pengu`

std/web/npm.pengu — puente controlado hacia paquetes NPM.

Un bundle JavaScript (esbuild/Vite/Rollup) importa los paquetes NPM y expone
una fachada explícita en `globalThis.PenguNpm`. Este módulo la consume sin
`eval`, sin resolución de bare specifiers y sin exponer `window`.

## Ejemplo
```pengu
import std.web.npm as npm

weave main into int:
    var r as result of js.JsValue to js.JsError is calling npm.root
    if r.is_ok:
        var args as list of js.JsValue is list of js.JsValue
        var out as result of js.JsValue to js.JsError is calling npm.call with r.value, "ping", args
    return 0
```

## Memoria
`root`, `get_path`, `call` y `call_json` devuelven handles owned. Liberar con
`js.release` cuando ya no se usen. Los argumentos son borrowed.

---

### `DEFAULT_ROOT`

> **DEFAULT_ROOT** : string

 Nombre global por defecto de la fachada.

 El bundle debe asignar `globalThis.PenguNpm = { ... }`.

### `empty`

> **empty**(s: string) -> bool

 `true` si `s` está vacío.

 ## Memoria
 O(1).

### `root`

> **root**() -> result of JsValue to JsError

 Obtiene la fachada global `PenguNpm`.

 ## Retorno
 Handle owned del objeto fachada.

 ## Errores
 `result.error` describe que la fachada no existe o no es un objeto utilizable.

 ## Memoria
 El handle devuelto es owned.

### `has_root`

> **has_root**() -> bool

 `true` si la fachada global existe.

 ## Memoria
 No retiene handles.

### `get_path`

> **get_path**(path: string) -> result of JsValue to JsError

 Obtiene una propiedad por path con puntos (`"camera.takePhoto"`).

 ## Parámetros
 - `path`: path no vacío; cada segmento es una propiedad del objeto anterior.

 ## Retorno
 Handle owned del valor final.

 ## Errores
 Path vacío, propiedad inexistente o valor no accesible.

 ## Memoria
 El handle devuelto es owned.

### `has_path`

> **has_path**(path: string) -> bool

 `true` si el path existe.

 ## Memoria
 No retiene handles.

### `call`

> **call**(target: JsValue, method: string, args: list of JsValue) -> result of JsValue to JsError

 Llama `target.method(args...)`.

 ## Parámetros
 - `target`: objeto owned o borrowed; el llamador conserva su ownership.
 - `method`: nombre del método; no se evalúa.
 - `args`: argumentos JS; se pasan tal cual.

 ## Retorno
 Handle owned del valor devuelto.

 ## Errores
 Método inexistente, excepción JS o handle inválido.

 ## Memoria
 El handle devuelto es owned. `args` no se libera.

### `call_json`

> **call_json**(target: JsValue, method: string, args_json: string) -> result of JsValue to JsError

 Llama un método con un array JSON de argumentos.

 `args_json` debe ser un array JSON (`"[\\"a\\",1]"`). Un objeto se rechaza
 para evitar ambigüedad: usa un array de un elemento.

 ## Errores
 JSON inválido, resultado no array, método inexistente o excepción JS.

 ## Memoria
 El handle devuelto es owned.

### `call_json_text`

> **call_json_text**(target: JsValue, method: string, args_json: string) -> result of string to JsError

 Llama un método con argumentos JSON y devuelve el resultado como JSON.

 ## Retorno
 String JSON owned.

 ## Memoria
 El string devuelto es owned.

### `call_async`

> **call_async**(target: JsValue, method: string, args: list of JsValue, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 Llama `target.method(args...)` y conecta la promesa resultante.

 `on_ok` recibe el valor resuelto (borrowed); `on_err` recibe el error
 (borrowed). Ambos son punteros C sin capturas y se ejecutan una sola vez.

 ## Retorno
 `true` si la promesa se conectó.

 ## Memoria
 El handle de la promesa se libera aquí; los callbacks son del bridge.

### `has_method`

> **has_method**(target: JsValue, method: string) -> bool

 `true` si el método existe en `target`.

 ## Memoria
 No retiene handles.

### `error_message`

> **error_message**(e: JsError) -> string

 Mensaje legible de un `JsError`, consumiéndolo.

 ## Memoria
 Libera `e`; devuelve string owned.

