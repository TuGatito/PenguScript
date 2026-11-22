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
- **Ejemplos** de `examples/01_hello` a `examples/12_colecciones`, todos
  compilables y ejecutables, más fixtures de bindgen nativo.
- **Scripts de instalación** en `scripts/`: `install.sh`/`install.ps1` compilan
  con Bun y dejan `pengu` en el PATH sin editar perfiles de shell;
  `vsix.sh`/`vsix.ps1` empaquetan e instalan la extensión.
- **Documentación**: `README.md` reescrito, `docs/stdlib.md` con el estado de la
  implementación y plan escalable en `scratch/plan_typescript.md`.

### Añadido en las fases G1–G6

- **`enchanting` sobre tipos incorporados**: un bloque `enchanting string`,
  `enchanting vector<T>`, `enchanting map<K, V>` o `enchanting tuple<A, B>`
  añade métodos a un tipo de la biblioteca sin tocar el compilador. Los
  métodos se registran por tipo base y aridad, admiten sobrecargas, respetan
  `mut` solo en tipos por referencia y se resuelven en este orden: propios,
  importados y, por último, la tabla nativa. Se añadieron los códigos E0707
  (firma duplicada), E0708 (ambigüedad entre módulos), E0709 (destino
  desconocido), E0710 (`mut` sobre un tipo por valor) y E0711 (aridad del
  patrón).
- **Biblioteca de colecciones en `std/`**: `std/string`, `std/vector`,
  `std/array`, `std/map`, `std/set`, `std/optional`, `std/pair`, `std/tuple`
  (pares y ternas), `std/int`, `std/double` y `std/ordering`. Cada módulo se
  importa explícitamente; sin el `invoke` los métodos no existen.
- **Codegen de métodos enhechizados**: funciones libres cualificadas por
  realm, `realm::metodo(receptor, ...)`, `std::get<N>` para tuplas y
  parámetros genéricos no deducidos con `std::type_identity_t` para permitir
  conversiones como `or_else(size_t?, 0)`.
- **LSP**: *hover* con la firma del método enhechizado y su realm,
  autocompletado de miembros tras `.` sobre receptores incorporados y
  `documentSymbol` para los bloques `enchanting`.
- **Documentación**: sección «Enchanting built-in types» en
  `docs/cheatsheet.md`, tabla de módulos enhechizados en `docs/stdlib.md` y
  `docs/errors.md` con E0707–E0711.
- **Pruebas**: `tests/regression/g2.test.ts` (resolución, sobrecargas, `mut`,
  ambigüedad), `tests/regression/g4.test.ts` (los once módulos de colecciones)
  y seis casos de conformidad nuevos (`g1_string` … `g6_ambiguedad`).

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
- **CLI**: `pengu run`, `build` y `check` sin argumentos usan el `entry` del
  `pengu.toml` del proyecto; `check --json` escribe siempre en stdout y un
  archivo ausente aparece como E0005 en el propio JSON.
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

### Añadido en la fase E (extensión de VS Code)

- Extensión completa en `editors/vscode/`: gramática para todo el lenguaje
  (palabras clave, tipos primitivos, contenedores, cadenas, ancho fijo,
  `declare`, `Ordering`, operadores y `...`), configuración de lenguaje con
  `wordPattern` y reglas de sangría, y 49 snippets validados por el parser.
- Comandos para ejecutar, compilar, verificar y formatear el archivo actual,
  ejecutar el proyecto, `bindgen`, `init`, `doctor`, reiniciar el servidor y
  configurar el ejecutable; menús del editor y del explorador, atajos
  `Ctrl+Alt+R/B/K`, terminal dedicada, barra de estado y canal de salida.
- Tareas `"type": "pengu"` con el *problem matcher* `$pengu`, verificación
  opcional al guardar (`pengu.check.onSave`) y reinicio automático del LSP al
  cambiar `pengu.executable` o la traza.
- Pruebas de la extensión en `tests/extension/` (36 pruebas) que comparan la
  gramática con las tablas del compilador, parsean los snippets y validan el
  manifiesto, las tareas y los módulos, y una prueba de humo que activa la
  extensión con un `vscode` simulado.
- `match` admite `else` al final, como documenta el *cheatsheet*.

### Añadido en las fases H1–H7

- **Rangos como valores**: `range<T>` se anota, se pasa, se devuelve, se mide
  con `#`, se prueba con `in` y se recorre con `for`.
- **`std/memory.pengu`**: `unique<T>` y `shared<T>` ganan `get` y `mut set`;
  `weak<T>` gana `is_alive`.
- **`std/string`**: `get(i) -> char?` y `mut pop() -> char?`.
- **`std/set`**: `intersection`, `difference`, `symmetric_difference` e
  `is_subset`.
- **Hash sintetizado** para runes y sellos, de modo que pueden usarse como
  claves de `unordered_map`/`unordered_set`.
- **Banco de conformidad H1–H6** en `tests/conformance/` (21 casos).

### Cambiado en las fases H1–H7

- La herencia usa **despacho estático**: ya no se emite `virtual`. Así lo
  documenta el lenguaje y así lo muestran `examples/11_polimorfismo` y las
  pruebas de F6.
- A partir de `operator <=>` se derivan `<`, `>`, `<=` y `>=`.
- `pengu bindgen` ya enlaza funciones C variádicas.

### Corregido en las fases H1–H7

- `any` no se puede convertir con `as` (E0514) ni `mut`/`unsafe` son valores de
  primera clase (E0515).
- Un índice fuera de rango imprime `panic: índice 5 fuera de rango (tamaño 2)`
  y termina con código 1 en lugar de abortar sin mensaje.
- `@ = valor` funciona en métodos `mut`; un método `mut` sobre un temporal da
  E0406.
- Un `return` dentro de un `for`/`while` usado como sentencia sale de la
  función (antes salía de una lambda).
- La interpolación evalúa sus partes de izquierda a derecha.
- `for k, v in mapa` liga la clave y el valor (antes ligaba un índice entero).
- El formateador escribe `ref<set<T>>` pegado y `#@ then` con espacio.
- `map{}` sin argumentos de tipo funciona cuando el contexto lo anota.

### Añadido en las fases I1–I8 (IntelliSense y tamaños)

- **Análisis de proyecto en el LSP**: el servidor reconstruye el grafo completo
  (documento abierto, sus `invoke` y `std/`) con *overlays* de los buffers sin
  guardar, publica diagnósticos por archivo y comparte un índice de símbolos.
- **Autocompletado completo**: ámbitos con sombreado, miembros de runes
  (heredados), omens, sellos, ecos, tipos incorporados y métodos enhechizados
  de `std/` y de módulos propios; `::` ofrece variantes y exportaciones; tras
  `:` y `->` se ofrecen tipos del proyecto, `vector<T>`, `map<K, V>` y `T?`.
- **Hover y ayuda de firma**: firma, documentación extraída de los comentarios
  `--`, contenedor, tamaño y desplazamiento de campos; `signatureHelp` marca el
  parámetro activo, también en variádicas.
- **Navegación y refactor**: definición de locales, parámetros, campos, métodos
  y símbolos de `std/`; referencias y renombrado por proyecto con sombreado;
  `prepareRename`; `std/` protegido contra renombrado; símbolos jerárquicos del
  documento y símbolos del workspace.
- **`pengu size`**: mide bytes y alineación reales compilando un programa de
  sondeo con el mismo toolchain (`--json`, `--type`, `--fields`). Cubre tipos
  primitivos, runes, omens, sellos, ecos, constantes y funciones (retorno +
  parámetros, y tamaño de `std::function`). La tabla se cachea por contenido y
  nunca inventa cifras: sin compilador informa y falla.
- **Inlay hints** de tipos inferidos (`x = 1` → `: int`) con opción de añadir el
  tamaño; **tokens semánticos**, **plegado** y **acciones de código**
  (arreglos rápidos y «añadir tipo explícito»).
- **Extensión**: ajustes `pengu.inlayHints.types`, `pengu.inlayHints.sizes`,
  `pengu.completion.docs` y `pengu.statusBar.size`, barra de estado con el
  tamaño del símbolo bajo el cursor y comando «Mostrar tamaño del símbolo».

### Corregido en las fases I1–I8

- La extensión encuentra `pengu` aunque VS Code no herede el `PATH` del shell:
  busca en el `PATH` del proceso y en `~/.local/bin`, `~/.bun/bin`, `~/bin`,
  `/usr/local/bin`, `/opt/homebrew/bin` y `/usr/bin`, y usa la ruta absoluta
  para la terminal, las tareas, los diagnósticos y el LSP. El aviso de
  ejecutable ausente explica el problema, abre los ajustes y muestra los
  directorios consultados en la salida.

- El autocompletado de miembros ya no pierde los métodos enhechizados del
  módulo propio y calcula bien el receptor con un prefijo a medio escribir.
- La finalización de `string` incluye `compare`, `trim`, `split`… y los
  métodos enhechizados aparecen primero.
- Los símbolos de función llevan su tipo `function<…>`, lo que habilita la
  ayuda de firma y el hover con firma.
- Los tokens semánticos usan el formato de cinco enteros por token exigido por
  el protocolo.
- La biblioteca estándar viaja **dentro** del ejecutable (`src/project/std_bundle.ts`,
  generado por `scripts/embed_std.ts`): antes, un binario instalado fuera del
  repositorio calculaba mal `std/` y, con ello, el LSP no veía `trim`, `join`,
  `sort`… aunque `bun run` sí. `bun run build` regenera el paquete y una prueba
  verifica que no quede desactualizado.
- El cliente LSP 11 de la extensión usa `LogOutputChannel` y toma `Trace` de
  `vscode-jsonrpc`; sin eso, el arranque del servidor fallaba con un mensaje
  engañoso («no respondió a `--version`»).
- La medición de tamaños cualifica los tipos de cada realm y omite `void`.

### Rendimiento del LSP (fases L1–L6)

- **Sincronización incremental de verdad**: `src/lsp/sync.ts` aplica cada
  `contentChanges[].range` sobre el texto actual. Antes el servidor anunciaba
  cambios incrementales pero reemplazaba el documento por el último fragmento.
- **Análisis agrupado**: una ráfaga de teclas espera 120 ms y produce un solo
  análisis y una sola publicación; `didSave` analiza de inmediato.
- **Diagnósticos por diferencia**: cada archivo tiene una huella; si su lista
  no cambió, no se reenvía (`src/lsp/publish.ts`). Los módulos empotrados
  (`std:…`) no se publican.
- **Sin errores fantasma al escribir**: `E0403`/`E0506` que tocan el tramo
  recién editado se filtran hasta 800 ms después del reposo, cuando se publica
  la lista definitiva.
- **Tamaños que no bloquean**: `src/lsp/sizes_state.ts` mantiene la última
  tabla válida y agenda la medición 400 ms después del último cambio. Hover,
  inlay hints y `pengu/sizeAt` responden al instante; al terminar se pide
  `workspace/inlayHint/refresh`. Nueva petición `pengu/refreshSizes` y
  `pengu/perf` con los tiempos del último análisis/publicación/medición.
- **Sondeo estable**: `generate_program` admite `declarations_only`; el sondeo
  de tamaños ya no incluye cuerpos, así que editar una función no recompila.
- **Caché de parseo** por contenido (hash FNV-1a) en `ParseCache`, compartida
  por el servidor entre pulsaciones.
- **Extensión**: debounce de 250 ms para `pengu/sizeAt` desde la barra de
  estado (`editors/vscode/src/debounce.js`) y ajuste `pengu.hover.sizes`.
- Cifras medidas en `examples/13_enchanting`: hover tras editar 1975 → 10 ms;
  reanálisis 6 ms; la medición de tamaños (1,8 s) pasa a segundo plano.

### Corregido en las fases L1–L6

- El servidor LSP corrompía el documento al recibir cambios incrementales
  (reemplazaba todo el texto por el fragmento insertado).
- El hover compilaba el sondeo C++ dentro de la propia petición (hasta 1975 ms).
- Cada pulsación publicaba los diagnósticos de todos los archivos del proyecto.
- El sondeo de tamaños cambiaba de hash al editar cualquier cuerpo, lo que
  invalidaba la caché y forzaba una compilación de ~1,9 s.

### Verificado

- `bun test`: 361 pruebas en 45 archivos (lexer, parser, checker, formateador,
  LSP de integración, de consultas, de sincronización y de rendimiento,
  medición de tamaños, bindgen, biblioteca estándar, conformidad y e2e de los
  ejemplos, de las fases F1–F9, G1–G6, H1–H7, I1–I8 y L1–L6, y de la extensión
  de VS Code).
- `tsc --noEmit` sin errores y `pengu fmt --check` sin cambios pendientes.
- Los 13 ejemplos de `examples/` compilan y ejecutan con el compilador final.
