# Crear una librería para PenguScript

Esta guía describe cómo escribir una librería que otros proyectos instalan con
`psc add` e importan como cualquier módulo. Refleja `psc` 0.40.0.

Una librería es un repositorio git (o un directorio local) con `pengu.toml`, un
árbol de fuentes importable y, opcionalmente, cabeceras C y archivos nativos.
No hay registro: la URL de origen *es* el paquete.

<!-- toc -->
- [1. Estructura](#1-estructura)
- [2. `pengu.toml`](#2-pengutoml)
- [3. La fachada](#3-la-fachada)
- [4. C y librerías nativas](#4-c-y-librerías-nativas)
  - [Opción A — C header-only](#opción-a--c-header-only)
  - [Opción B — librería nativa real](#opción-b--librería-nativa-real)
  - [`build.pengu`](#buildpengu)
- [5. Publicar e instalar](#5-publicar-e-instalar)
- [6. Probar una librería](#6-probar-una-librería)
- [7. Documentación y versiones](#7-documentación-y-versiones)
- [8. Licencia](#8-licencia)
- [9. Checklist](#9-checklist)
- [10. Errores frecuentes](#10-errores-frecuentes)
<!-- /toc -->

---

## 1. Estructura

```
mi_lib/
├── pengu.toml
├── pengu/                    # o src/; lo declara [build] src_dir
│   ├── mi_lib.pengu          # fachada: lo que da `import mi_lib`
│   └── mi_lib/
│       ├── app.pengu         # import mi_lib.app
│       ├── router.pengu      # import mi_lib.router
│       └── native.d.pengu    # declaraciones C (privado)
├── include/
│   └── mi_lib_native.h       # prototipos y C header-only
├── lib/                      # .a/.so/.dylib/.dll nativos, si hay
├── build.pengu               # opcional: prepara artefactos nativos
├── tests/                    # opcional: proyectos consumidores
├── examples/                 # opcional: ejemplos ejecutables
├── LICENSE
├── THIRD_PARTY.md            # si vendors código de terceros
└── README.md
```

Dos reglas separan "funciona en local" de "funciona tras `psc add`":

1. **`[build] src_dir` es la raíz de módulos.** El driver añade
   `<paquete>/<src_dir>` a la búsqueda de módulos del consumidor. Con
   `src_dir = "pengu"`, `pengu/foo.pengu` es `import foo` y
   `pengu/mi_lib/router.pengu` es `import mi_lib.router`. Los paquetes viejos
   con sólo `src/` siguen funcionando porque el valor por defecto es
   `src_dir = "src"`.
2. **El directorio y el nombre de import no son lo mismo.** El consumidor
   instala en `lib/<name>`, pero importa por ruta de módulo. Declara el
   namespace en el manifiesto; ver abajo.

`include/` se añade como `-I`, lo que resuelve `#include "mi_lib_native.h"`
desde el C generado. `lib/` se añade como `-L`, así `link "mi_lib"` encuentra
`lib/libmi_lib.a` sin una ruta hard-codeada.

---

## 2. `pengu.toml`

Una librería se compila como estática o compartida, nunca como ejecutable:

```toml
[project]
name = "mi-lib-repo"        # nombre del repo/paquete; puede llevar guiones
import = "mi_lib"           # opcional: import/directorio por defecto sin --name
version = "0.1.0"
entry = "pengu/mi_lib.pengu"
output = "static"

[build]
src_dir = "pengu"           # por defecto: "src"
include_dir = "include"     # por defecto: "include"
lib_dir = "lib"             # por defecto: "lib"
c_dir = "c"                 # sólo para el `psc build` de este repo
```

- `name` es la identidad del paquete en `pengu.lock` y en los diagnósticos.
  Admite letras, dígitos, `_` y `-`.
- `import` es el namespace que escriben los usuarios. Si existe y no se pasó
  `--name`, `psc add` instala en `lib/<import>` y escribe la dependencia con esa
  clave. Ejemplo: `psc add https://github.com/TuGatito/raylib-pengu` instala
  `lib/raylib`, así que se usa `import raylib`.
- `version` es semver. El consumidor la fija con `version = "^0.1"`, `tag` o
  `branch`. Etiqueta el repositorio (por ejemplo `v0.1.0`); un repo sin tags
  también se instala desde su rama por defecto si la constraint es `*`.
- `entry` sólo importa al compilar el paquete solo (CI, `psc build`);
  `psc add` instala fuentes y, con trust, ejecuta `build.pengu`.
- `lib_dir` es donde `build.pengu` deja los archivos nativos y lo que el driver
  añade al `-L` del consumidor.

No necesitas un `weave main` en una librería. Los demos van en `examples/`.

---

## 3. La fachada

El consumidor escribe `import mi_lib` y espera un módulo con la API pública.
Mantén ese módulo pequeño: imports, alias, constantes y wrappers finos.

```pengu-fragment
## mi_lib — una pequeña librería HTTP para PenguScript.
##
## Importa `mi_lib`; la implementación vive en `mi_lib.*`.
import mi_lib.app
import mi_lib.router

alias Application as mi_lib.app.Application
alias Router as mi_lib.router.Router

## Crea una aplicación con la configuración por defecto.
weave new_application into Application:
    return calling mi_lib.app.new_application
```

Reexportar un tipo con `alias` también reexporta sus métodos: un valor
`mi_lib.Application` puede llamar métodos declarados en `mi_lib.app`. Es la
forma soportada de construir una fachada, porque los imports no se reexportan.

Nombres: archivos `snake_case`, tipos `PascalCase`, funciones `snake_case`, sin
módulos `utils`/`helpers`/`common`.

---

## 4. C y librerías nativas

El consumidor **no** compila tu directorio `c/` ni lee `links` de tu
`pengu.toml`. Viajan tres cosas: tu árbol de fuentes (como módulos), tu
`include/` (como `-I`) y lo que tu `build.pengu` deje en `lib/` (como `-L`).
`link "..."` y `ldflag "..."` declarados en un módulo sí llegan a la línea de
enlace del consumidor.

### Opción A — C header-only

Pon la implementación en `include/mi_lib_native.h` como funciones `static` y
declárala desde `pengu/mi_lib/native.d.pengu`:

```c
/* include/mi_lib_native.h */
#ifndef MI_LIB_NATIVE_H
#define MI_LIB_NATIVE_H

#include <stdint.h>

static inline int32_t mi_lib_add(int32_t a, int32_t b) {
    return a + b;
}

#endif
```

```pengu-fragment
## Declaraciones C de mi_lib (privado).
include "mi_lib_native.h"

declare mi_lib_add with a as int, b as int into int
```

Es la distribución más simple: una sola unidad de traducción C, sin búsqueda en
link-time y con DCE. Mantén la cabecera autocontenida (`static inline`, sin
estado global salvo que lo documentes) y prefija todo con el nombre del paquete.

### Opción B — librería nativa real

Para un archivo precompilado o compilado:

1. Deja el archivo en `lib/libmi_lib.a` (o `.so`/`.dylib`/`.dll`/`.lib`).
2. Declara `link "mi_lib"` en el módulo que lo usa.
3. Haz que `build.pengu` produzca ese archivo cuando falte.

El driver añade `<paquete>/lib` (o el `lib_dir` declarado) a `-L`, así el
consumidor no necesita un `ldflag` con ruta. Un `ldflag` hard-codeado sigue
funcionando por compatibilidad, pero es frágil: mover o vendorear el paquete lo
rompe.

`psc add` copia los archivos nativos (sólo los archivos, no todo el árbol
`lib/`) y `psc vendor` los conserva, de modo que `--frozen` funciona offline.

### `build.pengu`

Programa PenguScript opcional en la raíz del paquete. `psc add`, `psc update` y
`psc upgrade` lo ejecutan **sólo con `--trust`** (o `PENGU_TRUST_ALL=1`); sin
trust se omite con un aviso. Se ejecuta con el directorio del paquete como cwd.
Devuelve un código distinto de cero si falla: `psc` aborta la instalación y
hace rollback si la dependencia era nueva.

Hazlo idempotente: si el archivo ya existe, devuelve 0. Un ejemplo típico:

```pengu
import std.archivum
import std.rites
import std.spark

weave main into int:
    if calling archivum.is_file with "lib/libmi_lib.a":
        return 0
    # Descarga verificada, o clona y compila el proyecto C.
    var rc as int is calling rites.run_shell with "make -C native"
    if rc != 0:
        return 1
    return 0
```

No publiques `build.py`, `build.sh` ni otro nombre: el instalador sólo busca
`build.pengu`. Si un paquete necesita Python hoy, porta la lógica a PenguScript
(`std.petitio` para HTTP, `std.digest` para checksums, `std.archivum` para
archivos) o escribe un `build.pengu` que invoque una herramienta externa de
forma explícita y falle si no está.

---

## 5. Publicar e instalar

1. Commit, tag y push:

   ```sh
   git tag v0.1.0
   git push origin main --tags
   ```

2. El usuario lo instala:

   ```sh
   psc add https://github.com/tu-usuario/mi_lib --trust
   psc add https://gitlab.com/tu-usuario/mi_lib --trust
   ```

   `--trust` es necesario para ejecutar `build.pengu`. Sin él se instalan las
   fuentes pero no se producen los artefactos nativos; `--no-build` es la forma
   explícita de omitir el script.

3. El `pengu.toml` del consumidor recibe:

   ```toml
   [dependencies.mi_lib]
   url = "https://github.com/tu-usuario/mi_lib"
   version = "^0.1"
   ```

   o, para una ruta local:

   ```toml
   [dependencies.mi_lib]
   path = "/home/tu-usuario/mi_lib"
   ```

   `pengu.lock` es schema 2: fija source, commit, versión, constraint, SHA-256
   del árbol instalado y el target. Commitea el lock; usa `--locked` en
   desarrollo y `--frozen` en CI.

Formas de URL que acepta `add`:

- `https://github.com/tu-usuario/mi_lib` (GitHub, rama por defecto)
- `https://gitlab.com/tu-usuario/mi_lib/-/tree/v0.2.0` (ref desde GitLab)
- `https://github.com/tu-usuario/mi_lib#v0.2.0` (ref explícita)
- `file:///ruta/absoluta` y `ssh://git@host/repo.git`
- una ruta local, absoluta o relativa al directorio actual

GitLab no necesita código especial: es git normal por HTTPS/SSH. Los repos
privados usan las credenciales git del usuario; evita poner tokens en la URL
porque el manifiesto y el lock los guardarían.

---

## 6. Probar una librería

`psc test` ejecuta los bloques `test "..."` de tu árbol de fuentes:

```pengu-fragment
test "suma dos números":
    let got as int is calling mi_lib_add with 2, 3
    assert got == 5
```

Para la API pública, añade un proyecto consumidor en `tests/consumer/` que
instale la librería por ruta y ejecute un programa. Es la única forma de probar
lo que vive el usuario (layout, resolución de módulos, `-I`, `-L`, archivo
nativo):

```sh
psc add ../.. --trust
psc run src/main.pengu
```

Pruébalo dos veces: con un checkout limpio (sin `lib/*.a`) y con `--frozen`
tras `psc vendor`. El primero detecta un `build.pengu` que falta; el segundo, un
vendor que perdió los archivos nativos.

---

## 7. Documentación y versiones

- Cada símbolo público lleva un docstring `##`. `psc doc` lo publica.
- Documenta la propiedad de todo lo que reserve memoria.
- Semver: patch para arreglos, minor para añadidos, major para cambios
  incompatibles. Etiqueta las releases; `psc add --version '^0.2'` elige el tag
  mayor que cumpla.
- Indica en el README contra qué versión de `psc` lo pruebas.

---

## 8. Licencia

- Pon un `LICENSE` en la raíz (MIT es lo habitual).
- Si vendors C, conserva su licencia, registra origen/versión en
  `THIRD_PARTY.md` y usa una licencia permisiva (MIT, BSD, Apache-2.0, ISC).
- Apache-2.0 exige conservar `NOTICE`.

---

## 9. Checklist

- [ ] `pengu.toml` con `output = "static"` (o `shared`), `name` válido y, si el
      import difiere, `import`.
- [ ] API pública en `<src_dir>/<import>.pengu`; implementación debajo.
- [ ] `[build] src_dir` / `include_dir` / `lib_dir` coinciden con el repo.
- [ ] C header-only en `include/`, o un archivo nativo en `lib/` producido por
      `build.pengu`.
- [ ] `build.pengu` idempotente, descargas verificadas, fallo distinto de cero.
- [ ] `psc build` y `psc test` pasan en la propia librería.
- [ ] Un consumidor limpio instala con `psc add --trust` y compila sin symlinks
      ni `-L` manual.
- [ ] `psc vendor` + `psc build --frozen` funciona.
- [ ] `LICENSE`, tags y el `pengu.lock` del consumidor commiteados.

---

## 10. Errores frecuentes

- **`import` es por ruta.** Si falla `import mi_lib.core`, comprueba
  `lib/mi_lib/<src_dir>/mi_lib/core.pengu`. El driver lee `src_dir`; ya no
  asume `src/`.
- **El nombre del paquete no es el import.** `raylib-pengu` se instala como
  `lib/raylib-pengu` salvo que el manifiesto declare `import = "raylib"` o el
  usuario pase `--name raylib`.
- **Sin trust no se construye nada.** `psc add` sin `--trust` omite
  `build.pengu`; un paquete nativo fallará al enlazar. Usa `--trust` en un
  entorno limpio o documenta los artefactos.
- **El consumidor nunca compila `c/`.** Pon el C reutilizable en `include/` o
  prepara un archivo real en `lib/`.
- **No hay closures.** Un callback es un weave con nombre más `ref to void`
  como user data.
- **`concept` no tiene dispatch dinámico.** Usa un `omen` etiquetado, un `rune`
  con punteros a función, o un enum más `judge`.
- **Los contenedores vacíos necesitan tipo**: `let xs as list of int is []`.
- **`at` es un operador**: `xs at 0`, no `calling xs.at with 0`.
- **Los strings son owned por defecto.** Un parámetro `string` es prestado; no
  lo liberes con `banish`. Devolver un string transfiere la propiedad.
- **El vendor sólo conserva archivos nativos de `lib/`**, no todo el árbol. No
  dependas de archivos arbitrarios bajo `lib/` en el build del consumidor.
