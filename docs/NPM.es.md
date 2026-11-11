# Paquetes NPM en PenguScript

PenguScript no descarga ni evalúa paquetes NPM durante el build. Conservas tu
toolchain JavaScript, empaquetas con esbuild/Vite/Rollup, expones una fachada
explícita y la llamas desde PenguScript con `std.web.npm`.

<!-- toc -->
- [1. Empaqueta la fachada](#1-empaqueta-la-fachada)
- [2. Declara los assets web](#2-declara-los-assets-web)
- [3. Llama a la fachada](#3-llama-a-la-fachada)
- [4. Bundle y PWA con `psc web`](#4-bundle-y-pwa-con-psc-web)
- [5. Reglas de seguridad](#5-reglas-de-seguridad)
<!-- /toc -->

## 1. Empaqueta la fachada

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

El bundle debe asignar un único objeto global. PenguScript no importa ESM
directamente: WASM no resuelve módulos NPM y una fachada explícita mantiene el
límite tipado y auditable.

## 2. Declara los assets web

```toml
[web]
dir = "web"
scripts = ["npm.js"]
base = ""
# Opcional: deja que `psc web bundle` ejecute esbuild por ti.
# bundle = "web/npm.ts"
# assets = ["logo.png", "fonts"]
```

`scripts` se copian junto al HTML generado y se inyectan antes de `</head>` en
orden. `assets` copia archivos o directorios. `base` se antepone al `src` de los
scripts, por ejemplo `"/static/"`.

## 3. Llama a la fachada

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

- `call` / `call_json` son síncronos.
- `call_async` conecta una Promise; los callbacks reciben handles `JsValue`
  prestados.
- `call_json_text` devuelve texto JSON y convierte errores del puente en un
  diagnóstico.
- Todo handle devuelto es owned y debe liberarse exactamente una vez.

## 4. Bundle y PWA con `psc web`

`psc web bundle` es una comodidad opcional: lee `[web] bundle`, ejecuta el
`node_modules/.bin/esbuild` local (o `npx esbuild`) y escribe el IIFE en la
primera entrada de `[web] scripts`.

```toml
[web]
dir = "web"
bundle = "web/npm.ts"
scripts = ["npm.js"]
```

```sh
psc web bundle .
psc web bundle . --pwa   # además escribe manifest.webmanifest y sw.js
```

`--pwa` escribe un manifest mínimo y un service worker cache-first en el
directorio `[web]`. El worker cachea `./`, `app.html`, `app.js` y `app.wasm`;
añade iconos y ajusta la lista para producción. El comando nunca instala
paquetes NPM: ejecuta `npm install` antes.

## 5. Reglas de seguridad

- Sin `eval` ni `import()` dinámico desde PenguScript; la fachada es el único
  límite.
- No expongas objetos NPM crudos a HTML no confiable. Valida argumentos y
  resultados.
- Una página web no es una app nativa: las APIs PWA degradan (cámara,
  notificaciones, push). Ver `docs/CAPACITOR.md`.
