# Soporte de Capacitor

`std.web.capacitor` es un adaptador tipado sobre una fachada `window.PenguNpm`.
No incrusta un puente nativo: el JS de Capacitor corre en el WebView y el
adaptador solo serializa JSON y Promises.

<!-- toc -->
- [Contrato de la fachada](#contrato-de-la-fachada)
- [API](#api)
- [Degradación por plataforma](#degradación-por-plataforma)
- [Permisos](#permisos)
- [Versiones](#versiones)
<!-- /toc -->

## Contrato de la fachada

```ts
import { Capacitor } from "@capacitor/core";
import { Camera, Device, Network, Preferences, Share, Haptics } from "@capacitor/*";
import { LocalNotifications } from "@capacitor/local-notifications";

globalThis.PenguNpm = {
  capacitor: {
    platform: () => Capacitor.getPlatform(),
    native: () => Capacitor.isNativePlatform(),
    available: (name: string) => Capacitor.isPluginAvailable(name),
  },
  plugins: { Camera, Device, Network, Preferences, Share, Haptics, LocalNotifications },
};
```

El bundle debe ser IIFE (`esbuild --format=iife`) e inyectarse con `[web]` antes
del loader de PenguScript.

## API

| Función | Contrato |
|---|---|
| `platform` | `"web"`, `"ios"` o `"android"` |
| `is_native` | true solo dentro de un shell nativo Capacitor |
| `is_available(name)` | plugin registrado en esta plataforma |
| `plugin(name)` | handle owned al objeto del plugin |
| `call_json(name, method, args)` | llamada síncrona, devuelve texto JSON |
| `call_async(name, method, args, ok, err)` | conecta una Promise |
| `device_info` / `network_status` | JSON de `Device.getInfo` / `Network.getStatus` |
| `camera_check_permissions` / `request_permissions` / `take_photo` | adaptador Camera |
| `preferences_get/set/remove`, `share`, `haptics_impact` | Preferences/Share/Haptics |
| `notifications_check_permissions` / `request_permissions` / `schedule` | LocalNotifications |

Los callbacks de `call_async` son one-shot y reciben handles prestados. Los
errores son `js.JsError` con nombre `CapacitorError`.

## Degradación por plataforma

Un navegador no es una app nativa. `is_native` es false, `Camera.takePhoto`
puede usar la implementación web o fallar, las notificaciones locales son
limitadas y push no existe igual. Ramifica siempre:

```pengu-fragment
if calling cap.is_native:
    calling cap.camera_take_photo with on_photo, on_error
else:
    # fallback <input type="file" accept="image/*">
    return
```

## Permisos

Android: añade permisos de cámara/notificaciones en
`android/app/src/main/AndroidManifest.xml`. iOS: añade
`NSCameraUsageDescription` y uso de notificaciones en `Info.plist`, y pide en
runtime con los adaptadores. Un permiso denegado llega por `on_err`.

## Versiones

El adaptador apunta a Capacitor 8. Mantén `@capacitor/core`, el CLI y todos los
plugins en el mismo major. `npx cap sync` tras cada cambio de `dist/`.
