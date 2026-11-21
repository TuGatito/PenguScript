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

Cobertura completa del lenguaje documentado en `docs/cheatsheet.md` (0.2.0):
las fases F1–F9 del plan `scratch/plan_compiler_completo.md`, sin deuda
técnica conocida en el compilador.

### Añadido en las fases F1–F9

- **Funciones variádicas** `(...xs: T)` con *spread* `f(...xs)`, tipo
  `function<(...T) -> R>` y `any` empaquetado en `::pengu::Value`; `stdio`,
  `format` y `log` pasan a escribirse en PenguScript sobre `declare`.
- **Tipos compuestos**: `array<T,N>`, literales con prefijo de tipo
  (`vector<int>[...]`, `set<T>{...}`, `map<K,V>{...}`), `pair`/`tuple`,
  `stack`, `queue`, `priority_queue`, `bitset`, `list`, `forward_list`,
  `multiset`, `unordered_*`, `span`, `variant`, `any`, `init_list`, `complex`,
  `atomic`, `mutex`, `shared_mutex`, `condition_variable` y `thread`.
- **Genéricos completos**: sigilos en funciones, runes, omens, `echo` y `seal`,
  instanciación explícita (`Caja<int>(7)`, `Resultado<int>::Ok(5)`) e
  inferencia, y restricciones `needs` comprobadas (E0513).
- **Runes**: herencia con `parent(...)`, `virtual` cuando hay herederos,
  *upcast* explícito `ref<Animal>(ref(d))`, operadores de usuario (`[]`, `+=`,
  unarios, `()`, `<=>`, libres por ADL) y `enchanting` sobre omens y sellos.
- **Memoria**: Ley de Exclusividad con préstamos por ámbito (E0602), contrato
  `mut` en la llamada (E0406), movimiento por campo e índice (E0601) y `unsafe`
  obligatorio para `raw`, `static mut`, `get_unchecked` y llamadas `unsafe`
  (E0603).
- **Módulos**: `const` evaluable en compilación (`constexpr`), `static mut` como
  variable de módulo (E0308 si no es evaluable), realms reabiertos con símbolos
  fusionados (E0304 al duplicar tipos) e importación por nombre de realm.
- **Diagnósticos**: conversiones numéricas portables y `T::try_from`/`T::from`,
  `Ordering` con `<=>`, mensajes con sugerencia de nombre y arreglo para la
  indentación, y `Display` obligatorio en interpolaciones y variádicas `any`.
- **Herramientas**: `pengu check --json`, `docs/errors.md` con el catálogo de
  códigos y banco de conformidad en `tests/conformance/`.

### Cambiado en las fases F1–F9

- `checker_expr.ts` y `cpp_expr.ts` se dividieron en módulos por
  responsabilidad (llamadas, control y operadores) para mantener los archivos
  legibles.
- El nombre con que se importa un módulo es el de su **realm** salvo que se
  escriba `as`.

### Corregido en las fases F1–F9

- BOM UTF-8 que rompía `invoke`, `static mut`, `mut ref<T>`, `array<T,N>`,
  `function<Sig>`, `if ... then` con bloque y la aridad con argumentos por
  defecto.

### Verificado

- `bun test`: 195 pruebas en 21 archivos (lexer, parser, checker, formateador,
  LSP de integración, bindgen, biblioteca estándar, conformidad y e2e de los
  ejemplos y de las fases F1–F8).
- `tsc --noEmit` sin errores y `pengu fmt --check` sin cambios pendientes.
- Los 13 ejemplos de `examples/` compilan y ejecutan con el compilador final.
