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

## Comandos

| Comando | Descripción |
| --- | --- |
| `pengu run <archivo>` | Compila y ejecuta; lo que sigue a `--` va al programa |
| `pengu build <archivo>` | Compila a nativo (`--out`, `--compiler`, `--link`) |
| `pengu check <archivo>` | Solo análisis: lexer, parser y checker |
| `pengu fmt [ruta]` | Formatea (`--check` para verificar sin escribir) |
| `pengu lsp` | Servidor LSP por stdin/stdout |
| `pengu bindgen <cabecera>` | Genera `*.d.pengu` desde una cabecera C/C++ |
| `pengu init [dir] [nombre]` | Crea un proyecto con `pengu.toml` |
| `pengu doctor` | Muestra versiones de Bun y de los compiladores |
| `pengu clean` | Borra las cachés `.pengu-cache` |

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
examples/      programas de ejemplo, de `01_hello` a `12_colecciones`
editors/vscode extensión de VS Code (gramática + cliente LSP)
scripts/       instalación del ejecutable y empaquetado del .vsix (sh + ps1)
tests/         lexer, parser, checker, formatter, lsp, bindgen y e2e
docs/          especificación del lenguaje (cheatsheet y stdlib)
```

La biblioteca estándar se escribe en `std/*.d.pengu` con firmas `declare`
(el runtime en C++ las implementa); `io`, `format` y `log` son intrínsecas
porque aún no hay funciones variádicas en el lenguaje.

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
- `examples/11_polimorfismo` — herencia, `parent`, operadores y despacho virtual.
- `examples/12_colecciones` — `std/string`, `vector`, `map`, `set`, `optional` e `int` enhechizados.

## Enlaces con C

```bash
pengu bindgen include/demo.h --realm demo --out demo.d.pengu
gcc -c -O1 -o demo.o demo.c
pengu build main.pengu --link demo.o
```

`bindgen` escribe un módulo con `extern "C"` y firmas traducidas; el checker
las valida y el generador emite los prototipos correspondientes.

## Documentación

- `docs/errors.md`: catálogo de códigos de diagnóstico.

- [`docs/cheatsheet.md`](docs/cheatsheet.md): referencia del lenguaje.
- [`docs/stdlib.md`](docs/stdlib.md): biblioteca estándar.
- [`scratch/plan_typescript.md`](scratch/plan_typescript.md): plan por fases.
