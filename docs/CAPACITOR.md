# Capacitor support

`std.web.capacitor` is a typed adapter over a `window.PenguNpm` facade. It does
not embed a native bridge: Capacitor's own JS runs in the WebView and the
adapter only marshals JSON and Promises.

<!-- toc -->
- [Facade contract](#facade-contract)
- [API](#api)
- [Platform degradation](#platform-degradation)
- [Permissions](#permissions)
- [Versions](#versions)
<!-- /toc -->

## Facade contract

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

The bundle must be an IIFE (`esbuild --format=iife`) injected by `[web]`
before the PenguScript loader.

## API

| Function | Contract |
|---|---|
| `platform` | `"web"`, `"ios"` or `"android"` |
| `is_native` | true only inside a Capacitor native shell |
| `is_available(name)` | plugin registered on this platform |
| `plugin(name)` | owned handle to the facade plugin object |
| `call_json(name, method, args)` | synchronous call, returns JSON text |
| `call_async(name, method, args, ok, err)` | connects a Promise |
| `device_info` / `network_status` | JSON of `Device.getInfo` / `Network.getStatus` |
| `camera_check_permissions` / `request_permissions` / `take_photo` | Camera adapter |
| `preferences_get/set/remove`, `share`, `haptics_impact` | Preferences/Share/Haptics |
| `notifications_check_permissions` / `request_permissions` / `schedule` | LocalNotifications |

All `call_async` callbacks are one-shot and receive borrowed handles. Errors are
`js.JsError` named `CapacitorError`.

## Platform degradation

A browser is not a native app. `is_native` is false, `Camera.takePhoto` may use
the web implementation or fail, local notifications are limited, and push does
not exist in the same form. Always branch:

```pengu-fragment
if calling cap.is_native:
    calling cap.camera_take_photo with on_photo, on_error
else:
    # <input type="file" accept="image/*"> fallback
    return
```

## Permissions

Android: add camera/notification permissions to
`android/app/src/main/AndroidManifest.xml`. iOS: add `NSCameraUsageDescription`
and notification usage to `Info.plist`, then request at runtime with the typed
adapters. A denied permission arrives through `on_err`.

## Versions

The adapter targets Capacitor 8. Keep `@capacitor/core`, the CLI and every
plugin on the same major. `npx cap sync` after every change to `dist/`.
