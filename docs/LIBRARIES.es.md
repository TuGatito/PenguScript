# Cómo crear una librería de PenguScript

Esta guía describe cómo escribir una librería que otros proyectos puedan
instalar con `psc add` e importar como cualquier otro módulo. Todo lo que sigue
está probado con `psc` 0.31.0 en Linux y macOS; las notas indican lo que solo
funciona en versiones nuevas del compilador.

Una librería en PenguScript es **un repositorio git** (o un directorio local)
con un `pengu.toml`, un árbol `src/` cuyos módulos son importables y,
opcionalmente, un directorio `include/` con declaraciones C. No hay registro:
la URL del fuente *es* el paquete.

<!-- toc -->
- [1. Estructura del repositorio](#1-estructura-del-repositorio)
- [2. `pengu.toml`](#2-pengutoml)
- [3. La fachada](#3-la-fachada)
- [4. Código C: dos opciones](#4-código-c-dos-opciones)
  - [Opción A — C header-only (recomendada)](#opción-a-c-header-only-recomendada)
  - [Opción B — una librería real (`-l`)](#opción-b-una-librería-real--l)
  - [Llamar de vuelta a Pengu](#llamar-de-vuelta-a-pengu)
- [5. Publicar e instalar](#5-publicar-e-instalar)
  - [`build.pengu`](#buildpengu)
- [6. Probar una librería](#6-probar-una-librería)
- [7. Documentación y versionado](#7-documentación-y-versionado)
- [8. Licencias](#8-licencias)
- [9. Lista de comprobación](#9-lista-de-comprobación)
- [10. Trampas conocidas](#10-trampas-conocidas)
<!-- /toc -->

---

## 1. Estructura del repositorio

```
mi_lib/
├── pengu.toml
├── src/
│   ├── mi_lib.pengu          # fachada: lo que `import mi_lib` da al usuario
│   └── mi_lib/
│       ├── app.pengu         # import mi_lib.app
│       ├── router.pengu      # import mi_lib.router
│       └── native.d.pengu    # declaraciones C (privado)
├── include/
│   └── mi_lib_native.h       # prototipos C y código C header-only
├── tests/                    # opcional: proyectos consumidores y scripts
├── examples/                 # opcional: ejemplos ejecutables
├── LICENSE
├── THIRD_PARTY.md            # si incorporas código de terceros
└── README.md
```

Dos reglas marcan la diferencia entre "funciona en mi máquina" y "funciona tras
`psc add`":

1. **El `src/` del paquete se convierte en raíz de módulos.** `psc add` copia el
   repositorio a `lib/<nombre>/` y añade `lib/<nombre>/src` a la búsqueda de
   módulos. Un fichero en `src/foo.pengu` se importa como `import foo`, y uno en
   `src/mi_lib/router.pengu` como `import mi_lib.router`. No hay otro prefijo de
   paquete que la ruta del fichero.
2. **No pongas tu único punto de entrada en `src/<nombre>.d.pengu`.** Un
   fichero `src/native.d.pengu` es importable como `import native` desde el
   consumidor; un `.d.pengu` dentro de `src/<nombre>/` queda en el espacio de
   nombres (`import mi_lib.native`) y es privado en la práctica. La fachada va
   en `src/<nombre>.pengu`.

`include/` se añade como `-I` para el consumidor; así resuelve el `#include
"mi_lib_native.h"` del C generado.

---

## 2. `pengu.toml`

Una librería se construye como biblioteca estática (o compartida), nunca como
ejecutable:

```toml
[project]
name = "mi_lib"
version = "0.1.0"
entry = "src/mi_lib.pengu"
output = "static"

[build]
src_dir = "src"
include_dir = "include"
strict_c99 = true
```

- `name` debe ser un identificador válido de PenguScript (minúsculas, sin
  guiones); se convierte en el directorio bajo `lib/` y en el nombre dentro del
  `pengu.toml` de los consumidores.
- `version` es semver. El consumidor puede fijarla con `version = "^0.1"`,
  `tag` o `branch`.
- `entry` solo importa cuando el paquete se construye solo (CI, `psc build`);
  `psc add` instala los fuentes, no un artefacto.

**No** necesitas un `weave main` en una librería. Un `weave main into int`
haría ambiguo `psc run`; las demos van en `examples/`.

---

## 3. La fachada

El consumidor escribe `import mi_lib` y espera un módulo con la API pública.
Mantén ese módulo pequeño: imports, alias, constantes y envoltorios finos.

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

Reexportar un tipo con `alias` reexporta también sus métodos: un valor de tipo
`mi_lib.Application` puede llamar a métodos declarados en `mi_lib.app`. Es la
forma soportada de construir una fachada, porque los imports no se reexportan.

Qué dejar privado: los módulos que la documentación no menciona. Un consumidor
puede seguir haciendo `import mi_lib.native`, pero los campos `_` y el contrato
de los `##` le dicen que no lo haga. Si necesitas privacidad real, mantén la
implementación en un módulo que la fachada no exponga y no lo documentes.

Los nombres siguen la guía del lenguaje: ficheros `snake_case`, tipos
`PascalCase`, funciones `snake_case`, nada de módulos `utils`/`helpers`/`common`.
Una librería es un buen sitio para ser estricto con esto: sus nombres pasan a
ser el vocabulario de otras personas.

---

## 4. Código C: dos opciones

La compilación del consumidor **no** compila tu directorio `c/` y **no** lee
`links` de tu `pengu.toml`. Solo viajan dos cosas: tu `src/` (como módulos) y tu
`include/` (como `-I`). El `ldflag "..."` declarado en un módulo **sí** se emite
en la línea de enlace del consumidor.

### Opción A — C header-only (recomendada)

Pon la implementación C en `include/mi_lib_native.h` como funciones `static` y
declárala desde `src/mi_lib/native.d.pengu`:

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

Esto es lo que hace que `psc add` "funcione sin más": el proyecto entero es una
sola unidad de traducción C, así que el código header-only se compila dentro,
el compilador C elimina lo que no se usa y no hay que encontrar nada en el
enlace. Mantén la cabecera autocontenida (`static inline`, sin estado global
salvo que lo documentes) y prefija todo con el nombre del paquete (`mi_lib_`)
para evitar choques.

Para dependencias C grandes, **amalgama** en una sola cabecera en la release
(como se distribuyen `stb` o `sqlite3`) en vez de pedir al usuario que instale
una librería del sistema. Un `include/mi_lib_llhttp.h` generado con funciones
`static` sigue siendo header-only, y guardas el fuente en `vendor/` con su
licencia.

### Opción B — una librería real (`-l`)

Si de verdad necesitas enlazar una librería del sistema, declárala en un módulo:

```pengu-fragment
link "milibreria"
```

El flag de enlace solo se emite si algún símbolo vivo lo necesita (actúa el DCE),
pero el usuario debe tener la librería instalada y el compilador debe
encontrarla. Eso rompe la promesa de "un solo comando", así que resérvalo para
librerías ya omnipresentes (libc, pthreads) o para funciones opcionales
documentadas como tales.

También puedes enviar una biblioteca estática precompilada dentro del paquete y
apuntarla con un `ldflag` absoluto o relativo. Funciona, pero la ruta queda
grabada en la línea de enlace: mover el proyecto o vendorizar el paquete lo
rompe. Prefiere la opción A.

### Llamar de vuelta a Pengu

Una función C puede llamar a un weave de Pengu pasado como puntero a función. El
handle portable es `ref to void`:

```pengu-fragment
declare mi_lib_run with cb as weave with userdata as ref to void into void, userdata as ref to void into int
```

Pasa `sigil of estado` como dato de usuario y haz `transmute` de vuelta dentro
del callback. Así es como un event loop (o un servidor) entrega eventos a la
librería.

---

## 5. Publicar e instalar

1. Haz commit, etiqueta y sube:

   ```sh
   git tag v0.1.0
   git push origin main --tags
   ```

2. El usuario la instala:

   ```sh
   psc add https://github.com/tu/mi_lib --trust
   ```

   `--trust` es obligatorio porque `psc add` ejecuta el `build.pengu` del
   paquete si existe (es código que se ejecuta). Sin `--trust`, los fuentes se
   instalan igual pero el script de build se omite (`--no-build` hace lo mismo).

3. El `pengu.toml` del consumidor recibe:

   ```toml
   [dependencies.mi_lib]
   url = "https://github.com/tu/mi_lib"
   version = "^0.1"
   ```

   y `pengu.lock` fija el commit exacto. Commitea el lock; usa `--locked` en
   desarrollo y `--frozen` en CI.

En compiladores **0.28.0 y anteriores**, `psc add` sin `--name` corrompe el
manifiesto (arreglado en 0.31.0). Pasa `--name mi_lib` explícitamente si sigues
anclado a 0.28.0.

### `build.pengu`

Programa opcional en la raíz del paquete, que se ejecuta con `psc run
build.pengu --` en el directorio del paquete cuando el usuario confía en él.
Úsalo para generar código, comprobar el entorno o construir artefactos nativos.
Debe ser idempotente y rápido; se ejecuta en cada `psc add` salvo que el usuario
pase `--no-build`. Un script típico imprime una línea por paso y sale con código
distinto de cero al fallar, para que la instalación se detenga.

---

## 6. Probar una librería

`psc test` ejecuta los bloques `test "..."` de tu `src/`:

```pengu-fragment
test "suma dos números":
    let got as int is calling mi_lib_add with 2, 3
    assert got == 5
```

Para la API pública, añade un proyecto consumidor en `tests/consumer/` que
instale la librería por ruta y ejecute un programa. Es la única forma de probar
lo que el usuario vive de verdad (resolución de módulos, `include/`, ldflags):

```sh
psc add ../.. --name mi_lib --trust
psc run src/main.pengu
```

Automatízalo en CI con un script que copie el repositorio a un directorio
temporal, lo añada a un proyecto limpio y compruebe la salida. Mantén el test de
"compila en un proyecto limpio" separado de los tests unitarios; detecta los
bugs de empaquetado que los unitarios no ven.

---

## 7. Documentación y versionado

- Todo símbolo público lleva docstring `##`. `psc doc` lo publica; un símbolo
  público sin documentación está a medias.
- Documenta la propiedad de lo que asigna memoria: ¿la cadena/lista devuelta es
  del llamador? ¿Los parámetros son prestados? PenguScript no lo comprueba por
  ti.
- Semver: parche para fixes, menor para añadidos (módulos o funciones nuevas),
  mayor para cambios incompatibles. Depreca con `@deprecated("usa X")` y
  mantén el símbolo antiguo al menos una versión menor.
- Anota en el README la versión del compilador con la que pruebas y fíjala en
  CI.

---

## 8. Licencias

- Pon un `LICENSE` en la raíz (MIT es lo habitual para código PenguScript).
- Si incorporas código C, conserva su texto de licencia, registra origen y
  versión en `THIRD_PARTY.md` y asegúrate de que la licencia es permisiva (MIT,
  BSD-2/3, Apache-2.0, ISC, dominio público). El código GPL no se puede enlazar
  en la mayoría de proyectos; no lo vendorices.
- Apache-2.0 exige conservar el fichero `NOTICE` y la atribución.

---

## 9. Lista de comprobación

- [ ] `pengu.toml` con `output = "static"` y un `name` válido.
- [ ] API pública en `src/<nombre>.pengu`; implementación en `src/<nombre>/*.pengu`.
- [ ] Tipos de la fachada reexportados con `alias`, no redeclarados.
- [ ] C header-only en `include/`, prefijado y documentado; o un `link`
      documentado para una librería del sistema.
- [ ] `psc build` y `psc test` pasan en la propia librería.
- [ ] Un proyecto consumidor la instala con `psc add` y ejecuta.
- [ ] `psc doc` limpio; el docstring del módulo dice lo que la librería **no**
      hace.
- [ ] `LICENSE` y, si hace falta, `THIRD_PARTY.md`.
- [ ] Versión etiquetada, `pengu.lock` del consumidor commiteado.

---

## 10. Trampas conocidas

- **`import` va por ruta, no por paquete.** Si `import mi_lib.core` falla tras
  `psc add`, comprueba que el fichero está en
  `lib/mi_lib/src/mi_lib/core.pengu`, no en `lib/mi_lib/src/core.pengu`.
- **No hay closures.** Un callback es un weave con nombre más datos de usuario
  `ref to void` (o `std.functor`); una lambda no puede capturar. Diseña las APIs
  alrededor de un contexto/handle.
- **`concept` no tiene dispatch dinámico.** Una lista de valores de un `concept`
  no es posible; usa un `omen` etiquetado, un `rune` con punteros a función o un
  enum con `judge`.
- **Los `let` quedan congelados en algunas posiciones** (`ref to frozen T`); usa
  `var` cuando necesites llamar a un método mutador sobre el local.
- **Toda sentencia necesita forma:** `calling f with x`, `let y is ...`,
  `return ...`. Una llamada suelta es error de sintaxis.
- **`with` exige `campo is valor`**: `Widget with name is "x"`, nunca
  `Widget with "x"`.
- **Los contenedores vacíos necesitan tipo**: `let xs as list of int is []`.
- **`at` es un operador**: escribe `xs at 0`, no `calling xs.at with 0`.
- **Las cadenas son propias por defecto.** Una función que recibe un parámetro
  `string` lo presta; devolver una transfiere la propiedad al llamador. No
  hagas `banish` de un parámetro.
- **El consumidor no compila tu C.** Si `psc add` funciona pero el enlace del
  consumidor falla con un símbolo indefinido, enviaste C en `c/` en vez de en
  `include/`.
