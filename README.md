# PenguScript

PenguScript es un lenguaje con bloques por indentación, tipado estático y
compilación a C++20. Este repositorio contiene el compilador, el checker, el
formateador, el servidor LSP y las herramientas de enlace con código nativo,
escritos en TypeScript y ejecutados con [Bun](https://bun.sh).

Versión actual: **0.1.0** (todo el *toolchain* en desarrollo activo).

## Requisitos

- [Bun](https://bun.sh) ≥ 1.4
- Un compilador de C++20: `g++` o `clang++`
- Opcional, para `pengu bindgen`: `clang`

```bash
bun install
```

## Uso rápido

```bash
bun run src/main.ts --version      # pengu 0.1.0
bun run src/main.ts run examples/01_hello/main.pengu
bun run src/main.ts check examples/03_control/main.pengu
bun run src/main.ts fmt examples
bun run src/main.ts lsp            # servidor LSP por stdio
bun run src/main.ts size examples/11_polimorfismo/main.pengu   # tamaños medidos
```

Para tener el comando en el `PATH` y la extensión de VS Code instalada:

```bash
./scripts/install.sh        # compila y deja «pengu» en un directorio del PATH
pengu run examples/01_hello/main.pengu

./scripts/vsix.sh           # empaqueta la extensión .vsix y la instala en VS Code
```

Los scripts no editan perfiles de shell: funcionan igual desde bash, zsh o fish.
En Windows hay equivalentes `scripts\install.ps1` y `scripts\vsix.ps1`.
Detalles en [scripts/README.md](scripts/README.md).

## Extensión de VS Code

`editors/vscode/` incluye la extensión completa: resaltado de todo el lenguaje,
diagnósticos del LSP (y opcionalmente `pengu check` al guardar), snippets,
autocompletado de valores, tipos, miembros y `std/`, ayuda de firma, ir a la
definición, referencias y renombrado por proyecto, inlay hints de tipos
inferidos, tokens semánticos, plegado, enlaces y lentes, formato y comandos
para **ejecutar**, **compilar**, **verificar**, **formatear** y **ver el tamaño
del símbolo** bajo el cursor, además de tareas con el *problem matcher*
`$pengu`.

El servidor está pensado para escribir rápido: agrupa los cambios (120 ms),
publica solo los archivos cuyos diagnósticos cambiaron y mide los tamaños en
segundo plano, así que el hover responde en milisegundos aunque el proyecto
cambie.

```bash
./scripts/vsix.sh           # empaqueta e instala la extensión
```

Atajos en archivos `.pengu`: `Ctrl+Alt+R` ejecutar, `Ctrl+Alt+B` compilar,
`Ctrl+Alt+K` verificar. Los detalles (comandos, ajustes, tareas y snippets)
están en [editors/vscode/README.md](editors/vscode/README.md).

## Comandos

| Comando | Descripción |
| --- | --- |
| `pengu run <archivo>` | Compila y ejecuta; lo que sigue a `--` va al programa |
| `pengu build <archivo>` | Compila a nativo (`--out`, `--compiler`, `--link`) |
| `pengu check <archivo>` | Solo análisis: lexer, parser y checker |
| `pengu fmt [ruta]` | Formatea (`--check` para verificar sin escribir) |
| `pengu lsp` | Servidor LSP por stdin/stdout |
| `pengu size [archivo]` | Bytes y alineación medidos (`--json`, `--type`, `--fields`) |
| `pengu bindgen <cabecera>` | Genera `*.d.pengu` desde una cabecera C/C++ |
| `pengu init [dir] [nombre]` | Crea un proyecto con `pengu.toml` |
| `pengu doctor` | Toolchain y huella de la stdlib; avisa si el proyecto tiene otra (`--json`) |
| `pengu clean` | Borra las cachés `.pengu-cache` |

## Si el LSP marca errores que `pengu check` no ve

Casi siempre hay dos copias distintas de `std/` en juego (el binario instalado
trae una empotrada y el proyecto puede tener la suya). Ejecuta `pengu doctor`:

```
std 44 archivo(s) · 732383169c004163
proyecto /home/tu/proyecto
  std/ del proyecto 44 archivo(s) · 732383169c004163 (coincide con el binario)
```

Si dice **NO coincide**, reinstala el compilador (`bash scripts/install.sh`) y
recarga el editor. Si el proyecto tiene su propio `std/` y no hay `pengu.toml`
en la raíz, el LSP no puede saber que es del proyecto: crea el manifiesto con
`pengu init`. Los detalles están en `docs/errors.md`.

## Estructura

```
src/
  frontend/    lexer, parser y AST
  semantic/    checker de tipos, scopes, entornos
  codegen/     emisión de C++20 y runtime (`pengu_rt.hpp`)
  driver/      compilación, toolchain y caché
  project/     resolución de módulos e `invoke`
  formatter/   formateador de código
  lsp/         protocolo, transporte y servidor
  bindgen/     lectura del AST de clang y generación de enlaces
  cli/         comandos de la línea de órdenes
  diagnostics/ códigos, diagnósticos y render con caret
std/           biblioteca estándar: firmas `*.d.pengu` que declara el bloque `declare`
examples/      programas de ejemplo, de `01_hello` a `16_herramienta`
editors/vscode extensión de VS Code (gramática, snippets, comandos y LSP)
scripts/       instalación del ejecutable y empaquetado del .vsix (sh + ps1)
tests/         lexer, parser, checker, formatter, lsp, bindgen, extensión y e2e
docs/          especificación del lenguaje (cheatsheet y stdlib)
```

El `pengu.toml` de la raíz marca el repositorio como proyecto: así `std/` es
la biblioteca del repositorio (y no la copia empotrada en el binario `pengu`).
Sin manifiesto, la raíz es el directorio del archivo y una importación desde
`src/` no resolvería.

La biblioteca estándar se escribe en `std/*.pengu` (con un bloque `declare`
para lo intrínseco); las firmas generadas se documentan en
`docs/stdlib_api.md`.
(el runtime en C++ las implementa). `io`, `format` y `log` son módulos
`.pengu` que envuelven intrínsecos sobre `vector<any>`: las funciones
variádicas aceptan cualquier valor que implemente `Display`.

El estilo del propio compilador sigue las convenciones de PenguScript:
`snake_case` para valores y archivos, `PascalCase` para tipos, sin clases,
funciones puras y módulos pequeños de una sola responsabilidad.

## Ejemplos

- `examples/01_hello` — hola mundo e `invoke`.
- `examples/02_variables` — `mut`, `const`, interpolación.
- `examples/03_control` — `if`, `switch`, bucles, comprensiones.
- `examples/04_functions` — funciones, valores por defecto, recursión.
- `examples/05_runes` — runes, `enchanting` y operadores.
- `examples/06_omens` — omens unitarios, flags y algebraicos con `match`.
- `examples/07_seal` — `echo`, `seal` y métodos.
- `examples/08_modules` — varios archivos, `realm`, `invoke` selectivo.
- `examples/09_stdlib` — vectores, mapas, conjuntos, opcionales, `math` y `format`.
- `examples/10_ownership` — `unique<T>`, movimiento y `use after move`.
- `examples/11_polimorfismo` — herencia, `parent`, operadores y despacho estático.
- `examples/12_colecciones` — `std/string`, `vector`, `map`, `set`, `optional` e `int` enhechizados.
- `examples/13_enchanting` — `enchanting`: métodos que añaden los módulos de `std/` a tipos incorporados.
- `examples/14_geometria` — `std/geometry`: vectores, rectángulos, intersecciones y transformaciones.
- `examples/15_juego` — física, easing y color en un bucle de juego.
- `examples/16_herramienta` — `std/cli`, `std/hash` y `std/json` en una herramienta de línea de comandos.

## Recetas

Tres programas de una pantalla que muestran lo que ya se puede escribir hoy.
Todos se compilan y ejecutan con `pengu run` y usan solo la biblioteca estándar.

**Física de un cuerpo** (`std/physics`, `std/easing` y `std/color`):

```coffee
invoke "std/color"
invoke "std/easing"
invoke "std/geometry"
invoke "std/io"
invoke "std/physics"

main = -> void
  mut cuerpo = physics::body_moving(geometry::vec2(0.0, 0.0), geometry::vec2(12.0, 0.0))
  gravedad = geometry::vec2(0.0, 9.81)
  for paso in 1..240
    cuerpo = physics::step(cuerpo, gravedad, 0.0, 0.05)
    if cuerpo.position.y >= 20.0
      break
  t = easing::bounce_out(0.5)
  io::println("impacto: #{cuerpo.position} velocidad: #{cuerpo.speed()}")
  io::println("color de impacto: #{(color::rgb(1.0, t, 0.5)).to_hex()}")
```

**Una CLI con flags y JSON** (`std/cli`, `std/json` y `std/hash`):

```coffee
invoke "std/cli"
invoke "std/hash"
invoke "std/io"
invoke "std/json"
invoke "std/os"
invoke "std/vector"

main = -> void
  banderas = vector<cli::Flag>[cli::short_option("nombre", "n", "a quién saludar"), cli::short_flag("seco", "s", "sin mayúsculas")]
  argv = os::args()
  opciones = cli::parse(ref(banderas), ref(argv))
  if !opciones.is_ok()
    io::println(cli::usage("saluda", ref(banderas)))
    os::exit(1)
  nombre = opciones.value_or("nombre", "mundo")
  saludo = if opciones.has("seco") then "hola, #{nombre}" else "Hola, #{nombre}"
  claves = vector<string>["saludo", "huella"]
  valores = vector<json::Value>[json::text_value(saludo), json::text_value(hash::fnv1a32_hex(saludo))]
  datos = json::object_value(claves, valores)
  io::println(json::stringify(datos))
```

**Tiro parabólico** (`std/geometry` y `std/math`):

```coffee
invoke "std/geometry"
invoke "std/io"
invoke "std/math"

main = -> void
  mut velocidad = geometry::vec2(8.0, 12.0)
  mut posicion = geometry::zero_vec2()
  mut altura_maxima = 0.0
  for paso in 1..60
    velocidad = velocidad + geometry::vec2(0.0, -9.81 * 0.05)
    posicion = posicion + velocidad * 0.05
    if posicion.y > altura_maxima
      altura_maxima = posicion.y
  io::println("caída en: #{posicion.x} m, altura máxima: #{altura_maxima} m")
```

## Enlaces con C

```bash
pengu bindgen include/demo.h --realm demo --out demo.d.pengu
gcc -c -O1 -o demo.o demo.c
pengu build main.pengu --link demo.o
```

`bindgen` traduce también los **tipos** de la cabecera: `omen` para los enums,
`rune` para los structs, `meld` para las uniones, `bits` para los bitfields,
`echo` para los typedefs y `opaque` para los records incompletos. El orden
respeta las dependencias y un record con un campo no traducible se omite con
motivo. Las firmas las valida el checker y el layout coincide con C:
`pengu size --fields` muestra los mismos bytes, alineación y desplazamientos.

Con `raylib` instalada, `pengu bindgen /usr/include/raylib.h --realm raylib
--out raylib.d.pengu --link raylib` genera enlaces completos y verificados.

## Documentación

- [`docs/cheatsheet.md`](docs/cheatsheet.md): referencia del lenguaje.
- [`docs/stdlib.md`](docs/stdlib.md): biblioteca estándar por capas.
- [`docs/stdlib_api.md`](docs/stdlib_api.md): referencia generada desde el código (firmas exactas).
- `docs/lsp.md`: capacidades del servidor LSP y ajustes de la extensión.
- `docs/errors.md`: catálogo de códigos de diagnóstico.
- [`scratch/plan_typescript.md`](scratch/plan_typescript.md): plan por fases.
- [`scratch/plan_extension_vscode.md`](scratch/plan_extension_vscode.md): auditoría y fases de la extensión.
- [`scratch/plan_lsp_intellisense.md`](scratch/plan_lsp_intellisense.md): plan de IntelliSense, tamaños e inlay hints.
