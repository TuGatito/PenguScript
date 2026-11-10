# std.web.capacitor

> Source: `std/web/capacitor.pengu`

std/web/capacitor.pengu — puente tipado sobre Capacitor.

Requiere que el bundle NPM exponga:

```js
globalThis.PenguNpm = {
  capacitor: {
    platform: () => Capacitor.getPlatform(),
    native: () => Capacitor.isNativePlatform(),
    available: (name) => Capacitor.isPluginAvailable(name),
  },
  plugins: { Camera, LocalNotifications, Device, Network, Preferences, Share, Haptics },
};
```

## Ejemplo
```pengu
import std.web.capacitor as cap

weave main into int:
    var p as result of string to js.JsError is calling cap.platform
    if p.is_ok:
        calling spark.println with p.value
    return 0
```

## Memoria
Los handles devueltos por `plugin` y los strings son owned. Los callbacks
reciben handles borrowed y son one-shot.

---

### `empty`

> **empty**(s: string) -> bool

 `true` si `s` está vacío.

 ## Memoria
 O(1).

### `wrap_error`

> **wrap_error**(e: JsError) -> JsError

 Convierte un error JS en error de Capacitor, consumiendo el original.

 ## Memoria
 Libera `e`.

### `core`

> **core**() -> result of JsValue to JsError

 Obtiene el objeto `capacitor` de la fachada NPM.

 ## Retorno
 Handle owned.

 ## Errores
 El bundle no expuso `capacitor`.

 ## Memoria
 El handle devuelto es owned.

### `platform`

> **platform**() -> result of string to JsError

 Plataforma actual: `"web"`, `"ios"` o `"android"`.

 ## Errores
 Bundle ausente, método ausente o valor no string.

 ## Memoria
 El string devuelto es owned.

### `is_native`

> **is_native**() -> bool

 `true` si corre dentro de una app nativa de Capacitor.

 ## Memoria
 No retiene handles.

### `is_available`

> **is_available**(name: string) -> bool

 `true` si el plugin `name` está disponible en la plataforma actual.

 ## Parámetros
 - `name`: nombre del plugin (`"Camera"`, `"LocalNotifications"`, ...).

 ## Memoria
 No retiene handles.

### `plugin`

> **plugin**(name: string) -> result of JsValue to JsError

 Obtiene un plugin por nombre (`PenguNpm.plugins.<name>`).

 ## Retorno
 Handle owned.

 ## Errores
 Plugin no expuesto por el bundle.

 ## Memoria
 El handle devuelto es owned.

### `call_json`

> **call_json**(plugin_name: string, method: string, args_json: string) -> result of string to JsError

 Llama `plugin.method(...)` con argumentos JSON y devuelve JSON.

 `args_json` debe ser un array JSON. Para un método de un solo objeto usa
 `"[{...}]"`.

 ## Retorno
 String JSON owned.

 ## Errores
 Plugin/método ausente, JSON inválido o excepción JS.

 ## Memoria
 El string devuelto es owned.

### `call_async`

> **call_async**(plugin_name: string, method: string, args_json: string, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 Llama `plugin.method(...)` y conecta la promesa.

 ## Retorno
 `true` si la promesa se conectó.

 ## Memoria
 Los callbacks reciben handles borrowed; son one-shot.

### `camera_check_permissions`

> **camera_check_permissions**(on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `Camera.checkPermissions()`.

 ## Memoria
 El callback recibe el objeto de permisos; no lo retiene.

### `camera_request_permissions`

> **camera_request_permissions**(permissions_json: string, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `Camera.requestPermissions({ permissions: [...] })`.

 ## Memoria
 El callback recibe el objeto de permisos; no lo retiene.

### `camera_take_photo`

> **camera_take_photo**(options_json: string, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `Camera.takePhoto(options)`.

 ## Memoria
 El callback recibe `{ webPath, ... }`; no lo retiene.

### `device_info`

> **device_info**(on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `Device.getInfo()`.

 ## Memoria
 El callback recibe el objeto de información; no lo retiene.

### `network_status`

> **network_status**(on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `Network.getStatus()`.

 ## Memoria
 El callback recibe el estado; no lo retiene.

### `preferences_get`

> **preferences_get**(key: string, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `Preferences.get({ key })`.

 ## Memoria
 El callback recibe `{ value }`; no lo retiene.

### `preferences_set`

> **preferences_set**(key: string, value: string, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `Preferences.set({ key, value })`.

 ## Memoria
 El callback no recibe valor útil; no lo retiene.

### `preferences_remove`

> **preferences_remove**(key: string, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `Preferences.remove({ key })`.

 ## Memoria
 El callback no recibe valor útil; no lo retiene.

### `share`

> **share**(options_json: string, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `Share.share({ title, text, url, dialogTitle })`.

 ## Memoria
 El callback no recibe valor útil; no lo retiene.

### `haptics_impact`

> **haptics_impact**(style: string, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `Haptics.impact({ style })`.

 ## Memoria
 El callback no recibe valor útil; no lo retiene.

### `notifications_check_permissions`

> **notifications_check_permissions**(on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `LocalNotifications.checkPermissions()`.

 ## Memoria
 El callback recibe el objeto de permisos; no lo retiene.

### `notifications_request_permissions`

> **notifications_request_permissions**(on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `LocalNotifications.requestPermissions()`.

 ## Memoria
 El callback recibe el objeto de permisos; no lo retiene.

### `notifications_schedule`

> **notifications_schedule**(notifications_json: string, on_ok: weave with v: JsValue into void, on_err: weave with e: JsValue into void) -> result of bool to JsError

 `LocalNotifications.schedule({ notifications: [...] })`.

 ## Memoria
 El callback no recibe valor útil; no lo retiene.

