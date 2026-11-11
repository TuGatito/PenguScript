# NPM packages in PenguScript

PenguScript does not download or evaluate NPM packages at build time. You keep
your JavaScript toolchain, bundle the packages with esbuild/Vite/Rollup, expose a
small explicit facade, and call it from PenguScript through `std.web.npm`.

<!-- toc -->
- [1. Bundle the facade](#1-bundle-the-facade)
- [2. Declare the web assets](#2-declare-the-web-assets)
- [3. Call the facade](#3-call-the-facade)
- [4. Bundle and PWA with `psc web`](#4-bundle-and-pwa-with-psc-web)
- [5. Safety rules](#5-safety-rules)
<!-- /toc -->

## 1. Bundle the facade

```ts
// web/npm.ts
import { Capacitor } from "@capacitor/core";
import { Device } from "@capacitor/device";

globalThis.PenguNpm = {
  capacitor: {
    platform: () => Capacitor.getPlatform(),
    native: () => Capacitor.isNativePlatform(),
    available: (name: string) => Capacitor.isPluginAvailable(name),
  },
  plugins: { Device },
};
```

```sh
npx esbuild web/npm.ts --bundle --format=iife --platform=browser --outfile=web/npm.js
```

The bundle must assign a single global object. PenguScript never imports ESM
directly: WASM cannot resolve NPM modules, and an explicit facade keeps the
boundary typed and auditable.

## 2. Declare the web assets

```toml
[web]
dir = "web"
scripts = ["npm.js"]
base = ""
# Optional: let `psc web bundle` run esbuild for you.
# bundle = "web/npm.ts"
# assets = ["logo.png", "fonts"]
```

`scripts` are copied next to the generated HTML and injected before `</head>`
in order. `assets` copy files or directories. `base` is prepended to script
`src` values, for example `"/static/"`.

## 3. Call the facade

```pengu
import std.web.npm as npm
import std.web.js as js

weave main into int:
    var r as result of js.JsValue to js.JsError is calling npm.root
    if not r.is_ok:
        return 1
    var out as result of string to js.JsError is calling npm.call_json_text with r.value, "add", "[2,3]"
    if out.is_ok:
        calling spark.println with out.value
    return 0
```

- `call` / `call_json` are synchronous.
- `call_async` connects a Promise; callbacks receive borrowed `JsValue` handles.
- `call_json_text` returns JSON text and turns bridge errors into a diagnostic.
- All returned handles are owned and must be released exactly once.

## 4. Bundle and PWA with `psc web`

`psc web bundle` is an optional convenience: it reads `[web] bundle`, runs the
project's local `node_modules/.bin/esbuild` (or `npx esbuild`), and writes the
IIFE into the first `[web] scripts` entry.

```toml
[web]
dir = "web"
bundle = "web/npm.ts"
scripts = ["npm.js"]
```

```sh
psc web bundle .
psc web bundle . --pwa   # also writes manifest.webmanifest and sw.js
```

`--pwa` writes a minimal manifest and a cache-first service worker into the
`[web]` directory. The worker caches `./`, `app.html`, `app.js` and `app.wasm`;
add icons and adjust the cache list for production. The command never installs
NPM packages: run `npm install` first.

## 5. Safety rules

- No `eval`, no dynamic `import()` from PenguScript; the facade is the only
  boundary.
- Never expose raw NPM objects to untrusted HTML. Validate arguments and results.
- A browser page is not a native app: PWA APIs degrade (camera, notifications,
  push). See `docs/CAPACITOR.md`.
