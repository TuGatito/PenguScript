# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí. El formato
sigue [Keep a Changelog](https://keepachangelog.com/es/1.0.0/) y el proyecto usa
[versionado semántico](https://semver.org/lang/es/).

## [0.1.0] - 2026-11-20

Primera versión funcional del *toolchain* completo, escrita en TypeScript y
ejecutada con Bun. La versión del lenguaje que documenta `docs/cheatsheet.md`
es la 0.2.0; la del compilador y sus herramientas es la 0.1.0.

### Añadido

- **Compilador a C++20**: lexer con bloques por indentación, parser con AST
  inmutable, checker de tipos, resolución de módulos, análisis de posesión v1
  (`unique`/`shared`/`weak`, `ref`, `mut` y uso tras movimiento) y generación de
  C++20 por *realm* con runtime propio (`pengu_rt.hpp`).
- **CLI `pengu`** con los comandos `run`, `build`, `check`, `fmt`, `lsp`,
  `bindgen`, `init`, `clean` y `doctor`; caché de compilación por contenido y
  enlace de objetos nativos (`--link`).
- **Servidor LSP** por stdio sin dependencias: diagnósticos, *hover* con tipos
  inferidos, autocompletado, ir a la definición, símbolos de documento y
  formateo.
- **Formateador** idempotente: indentación de 2 espacios, espaciado de
  operadores, comentarios y líneas en blanco, genéricos y `operator`.
- **`pengu bindgen`**: lee el AST JSON de `clang++` y genera módulos
  `*.d.pengu` con `extern "C"`, incluidas conversiones `string` ↔ `const char*`.
- **Biblioteca estándar inicial** en `std/` con el nuevo bloque `declare`:
  `math`, `fs`, `time`, `random`, `os` y `assert`; `io`, `format` y `log` son
  intrínsecas hasta que el lenguaje soporte variádicas.
- **Soportes del lenguaje** incorporados en esta versión: `switch`/`match` con
  exhaustividad, `break` con valor, bucles con `else`, comprensiones de vector,
  mapa y conjunto, omens unitarios, flags y algebraicos, `echo`/`seal`,
  `enchanting` con operadores, cierres, genéricos con `needs` y módulos con
  `invoke` selectivo y alias.
- **Extensión de VS Code** en `editors/vscode`: gramática TextMate,
  configuración del lenguaje y cliente LSP.
- **Ejemplos** de `examples/01_hello` a `examples/10_ownership`, todos
  compilables y ejecutables, más fixtures de bindgen nativo.
- **Scripts de instalación** en `scripts/`: `install.sh`/`install.ps1` compilan
  con Bun y dejan `pengu` en el PATH sin editar perfiles de shell;
  `vsix.sh`/`vsix.ps1` empaquetan e instalan la extensión.
- **Documentación**: `README.md` reescrito, `docs/stdlib.md` con el estado de la
  implementación y plan escalable en `scratch/plan_typescript.md`.

### Cambiado

- El proyecto pasa de la implementación anterior en Python a TypeScript + Bun,
  con estilo `snake_case`, sin clases y módulos pequeños.
- `docs/cheatsheet.md` actualizado a la versión 0.2.0 del lenguaje.

### Eliminado

- La implementación anterior en Python (`src/penguscript/`, `pyproject.toml`,
  `uv.lock` y sus pruebas).

### Verificado

- `bun test`: 85 pruebas en 11 archivos (lexer, parser, checker, formateador,
  LSP de integración, bindgen, biblioteca estándar y e2e de los ejemplos).
- `tsc --noEmit` sin errores y `pengu fmt --check` sin cambios pendientes.
