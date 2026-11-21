# PenguScript 0.1.0 — Plan maestro (TypeScript + Bun)

> Reemplaza a `scratch/plan.md` (C++20) como plan de implementación activo.
> La especificación del lenguaje sigue siendo `docs/cheatsheet.md` (3835 líneas).
> `scratch/plan.md` se conserva como checklist de features del lenguaje (Bloques A–E).

---

## 0. Objetivo, reglas y economía de tokens

### 0.1 Objetivo

Un toolchain completo de PenguScript escrito en TypeScript y ejecutado con Bun:

| Herramienta | Comando | Entrega |
|---|---|---|
| Compilador | `pengu build` | binario nativo vía C++20 (g++/clang++) |
| Runner | `pengu run` | compila en caché y ejecuta |
| Checker | `pengu check` | diagnósticos sin emitir C++ |
| Formateador | `pengu fmt` | estilo canónico, idempotente |
| LSP | `pengu lsp` | JSON-RPC por stdio |
| Bindgen | `pengu bindgen` | cabeceras C/C++ → `.d.pengu` con clang |
| Extensión | `editors/vscode` | resaltado + cliente LSP |

Versión única **0.1.0** en `package.json`, `--version`, `capabilities.serverInfo`,
extensión y plantillas `pengu init`, hasta que TODO (incluido stdlib y bindgen)
sea funcional. No habrá 0.2.0 en esta etapa.

### 0.2 Reglas de estilo del código TypeScript (estilo PenguScript)

1. **Sin `class`.** Datos = `type`/`interface` + funciones fábrica `make_*`.
   Estado compartido = objeto plano pasado explícitamente o closures.
2. **snake_case** para variables, funciones, campos de módulo y nombres de archivo.
   `PascalCase` para tipos. `SCREAMING_SNAKE_CASE` para constantes de módulo.
3. **Named exports only.** Sin `export default`. Un barrel `index.ts` por subsistema.
4. **Uniones discriminadas** con `kind: "..."` para AST, tokens, diagnósticos y tipos.
   Nunca `any`; `unknown` + narrowing. `readonly` por defecto en estructuras de datos.
5. **`Result<T, E>`** para errores esperados entre capas:
   `{ ok: true; value: T } | { ok: false; error: E }`.
   `throw` solo para invariantes internas imposibles (nunca para errores de usuario).
6. **Funciones puras primero.** Efectos (fs, red, proceso, stdio) aislados en
   `cli/`, `project/`, `lsp/` y `bindgen/`.
7. **Archivos de 80–250 líneas.** Un concepto por archivo. Si un archivo crece,
   se parte por fase del pipeline (lex/parse/check/emit), nunca por "utilidades".
8. **Sin dependencias externas** en el compilador, LSP, formatter y bindgen.
   Solo `bun` + módulos nativos de Node (`node:fs`, `node:path`, `node:child_process`).
9. Comentarios solo cuando explican **por qué**, no **qué**.
10. Todo texto de diagnóstico y help de CLI en español; identificadores en inglés.

### 0.3 Economía de tokens (sin perder calidad)

- **No releer** `docs/cheatsheet.md` entero: consultar por rangos de línea cuando
  haga falta una sintaxis exacta (usar `grep`/`read offset`).
- **Fixture-first**: cada feature se fija con un `.pengu` + `.expect` en `tests/`.
  Los fixtures son la documentación ejecutable; no se duplican en prosa.
- **Salida de herramientas acotada**: los tests imprimen solo el primer fallo;
  `pengu check` limita a 20 diagnósticos por archivo.
- **Golden snapshots** de C++ solo para módulos pequeños (≤60 líneas de .pengu).
- **No generar código muerto**: cada archivo nuevo debe ser importado por el
  pipeline o por un test en la misma fase.
- **Commits/estados**: este plan es el único documento de estado; la sección 7
  se actualiza al cerrar cada fase (una línea por fase).

---

## 1. Arquitectura

### 1.1 Pipeline

```
                    ┌────────────┐
  .pengu ──source──▶│   lexer    │──tokens──▶ parser ──AST──▶ resolver
                    └────────────┘                              │
                                                    módulos + símbolos
                                                                ▼
                                                             checker
                                                        (tipos, ownership,
                                                         exhaustividad)
                                                                │ AST tipado
                                                                ▼
                                                          codegen C++20
                                                                │ .hpp/.cpp
                                                                ▼
                                                     g++/clang++ -std=c++20
                                                                │
                                                                ▼
                                                            binario
```

Reglas de contrato entre capas:

- **Lexer** no conoce el parser; produce tokens con `span` y comentarios incluidos.
- **Parser** no conoce nombres de módulos ni tipos; produce AST con spans.
- **Resolver** construye el grafo de módulos y las tablas de símbolos por realm.
- **Checker** no emite; devuelve `CheckResult` con diagnósticos y AST anotado.
- **Codegen** no diagnostica; asume AST válido (si hay errores, no se ejecuta).
- **CLI** orquesta; es la única capa que toca `process`, `fs` y `child_process`.

### 1.2 Árbol de directorios

```
PenguScript/
├── package.json            # nombre, versión 0.1.0, bin, scripts
├── tsconfig.json           # strict, noEmit, bundler resolution
├── bunfig.toml             # test runner config
├── pengu.toml              # manifiesto del proyecto de ejemplo
├── .gitignore
├── docs/                   # spec (no se toca)
├── scratch/
│   ├── plan.md             # plan C++ anterior (checklist de lenguaje)
│   └── plan_typescript.md  # ESTE plan
├── runtime/
│   └── pengu_rt.hpp        # runtime C++20 (io, panic, helpers de contenedores)
├── src/
│   ├── main.ts             # entrypoint: despacho de comandos
│   ├── version.ts          # VERSION = "0.1.0"
│   ├── util/
│   │   ├── result.ts       # ok/err/is_ok/is_err/map_result
│   │   ├── span.ts         # Span, Source, line/col, merge_spans
│   │   ├── text.ts         # indentación, escape, snake/pascal helpers
│   │   └── path.ts         # resolución de rutas y extensiones
│   ├── diagnostics/
│   │   ├── diagnostic.ts   # Diagnostic, Severity, notes, fixes
│   │   ├── codes.ts        # catálogo estable E####/W####
│   │   ├── render.ts       # salida humana con caret y colores
│   │   └── sink.ts         # colección + dedupe + límite
│   ├── frontend/
│   │   ├── token.ts        # TokenKind, Token, keywords, operadores
│   │   ├── lexer.ts        # scanner con INDENT/DEDENT
│   │   ├── lexer_string.ts # strings, interpolación, chars, escapes
│   │   ├── lexer_number.ts # enteros/float/hex/bin
│   │   ├── ast.ts          # barrel de nodos
│   │   ├── ast_expr.ts     # expresiones
│   │   ├── ast_stmt.ts     # sentencias
│   │   ├── ast_decl.ts     # declaraciones top-level
│   │   ├── ast_type.ts     # tipos
│   │   ├── parser.ts       # entrada + bloques + utilidades
│   │   ├── parser_decl.ts  # rune/omen/enchanting/echo/seal/invoke/realm
│   │   ├── parser_stmt.ts  # control de flujo y asignaciones
│   │   ├── parser_expr.ts  # Pratt + postfijos + literales compuestos
│   │   └── parser_type.ts  # tipos, sigilos, function<...>
│   ├── project/
│   │   ├── manifest.ts     # pengu.toml (parser mínimo, sin deps)
│   │   ├── module.ts       # ModuleInfo, realm, imports
│   │   ├── resolve.ts      # grafo de imports, ciclos, orden topológico
│   │   └── build.ts        # orquesta frontend+checker+codegen por módulo
│   ├── semantic/
│   │   ├── types.ts        # Type, display_type, assignability
│   │   ├── symbols.ts      # SymbolKind, SymbolTable, realms
│   │   ├── collect.ts      # pase 1: declaraciones y firmas
│   │   ├── check.ts        # pase 2: cuerpos + inferencia
│   │   ├── check_expr.ts   # expresiones
│   │   ├── check_stmt.ts   # sentencias y control de flujo
│   │   ├── check_decl.ts   # runes, omens, enchanting, operadores
│   │   ├── builtins.ts     # métodos intrínsecos de contenedores/opcionales
│   │   ├── ownership.ts    # ref/mut/unique/shared, unsafe, exclusividad
│   │   └── exhaustiveness.ts # match/switch sobre omens
│   ├── codegen/
│   │   ├── cpp.ts          # emitter (Writer con indent)
│   │   ├── cpp_types.ts    # Type → string C++
│   │   ├── cpp_expr.ts     # expresiones → C++
│   │   ├── cpp_stmt.ts     # sentencias → C++
│   │   ├── cpp_decl.ts     # runes/omens/funciones/realms
│   │   └── module_emit.ts  # .hpp + .cpp por módulo
│   ├── driver/
│   │   ├── toolchain.ts    # detecta g++/clang++, flags, versión
│   │   ├── compile.ts      # invoca el compilador C++ y enlaza
│   │   └── cache.ts        # .pengu-cache por hash de contenido
│   ├── formatter/
│   │   ├── format.ts       # entrada: tokens → texto canónico
│   │   ├── spacing.ts      # tabla de espacios por par de tokens
│   │   └── comments.ts    # reubicación de comentarios
│   ├── lsp/
│   │   ├── server.ts       # loop JSON-RPC por stdio
│   │   ├── protocol.ts     # tipos LSP mínimos
│   │   ├── document.ts     # store de documentos + versiones
│   │   ├── analysis.ts     # cache de AST/checker por documento
│   │   └── features/
│   │       ├── diagnostics.ts
│   │       ├── hover.ts
│   │       ├── completion.ts
│   │       ├── definition.ts
│   │       ├── symbols.ts
│   │       └── semantic_tokens.ts
│   ├── bindgen/
│   │   ├── clang.ts        # clang++ -Xclang -ast-dump=json
│   │   ├── model.ts        # nodos C++ filtrados
│   │   ├── map_types.ts    # C/C++ → PenguScript
│   │   └── emit.ts         # .d.pengu determinista
│   └── cli/
│       ├── args.ts         # parser de flags sin deps
│       ├── help.ts
│       ├── build.ts
│       ├── run.ts
│       ├── check.ts
│       ├── fmt.ts
│       ├── lsp.ts
│       ├── bindgen.ts
│       ├── init.ts
│       └── doctor.ts
├── std/                    # stdlib escrita en PenguScript
│   ├── core.pengu
│   ├── io.pengu
│   ├── string.pengu
│   ├── vector.pengu ...
├── tests/
│   ├── lexer/*.test.ts
│   ├── parser/*.test.ts
│   ├── checker/*.test.ts
│   ├── codegen/*.test.ts
│   ├── e2e/*.test.ts
│   └── fixtures/
│       ├── ok/<name>.pengu
│       ├── err/<name>.pengu (+ <name>.expect con códigos)
│       └── run/<name>.pengu (+ <name>.out)
├── examples/
│   ├── 01_hello/hello.pengu
│   ├── 02_control/...
│   ├── 03_runes/...
│   ├── 04_omens/...
│   ├── 05_containers/...
│   ├── 06_closures/...
│   └── 07_modules/...
└── editors/
    └── vscode/
        ├── package.json
        ├── syntaxes/penguscript.tmLanguage.json
        └── src/extension.ts
```

### 1.3 Diagnósticos

```ts
type Diagnostic = {
  code: string;          // "E0102"
  severity: "error" | "warning" | "info";
  message: string;
  span: Span;
  notes: readonly string[];
  fix?: { title: string; replacement: string; span: Span };
};
```

Catálogo por rango:

| Rango | Área |
|---|---|
| E00xx | CLI / proyecto / manifiesto |
| E01xx | léxico (indentación, literales, escapes) |
| E02xx | sintaxis |
| E03xx | módulos, realms, imports, ciclos |
| E04xx | nombres y símbolos |
| E05xx | tipos e inferencia |
| E06xx | mutabilidad, ownership, unsafe |
| E07xx | runes/omens/enchanting |
| E08xx | codegen / toolchain |
| E09xx | LSP / bindgen |
| W0xxx | warnings |

Formato humano: `archivo:línea:col: error[E0201]: mensaje` + línea fuente + caret +
notas. Formato `--json` para LSP y CI.

### 1.4 Caché

`.pengu-cache/<hash-contenido>/`:

- clave = hash de (versión del compilador + flags + contenido del módulo + hashes
  de sus dependencias).
- artefactos: `<module>.hpp`, `<module>.cpp`, `<module>.o`.
- `pengu run` reutiliza el binario si el hash del proyecto no cambió.
- limpieza: `pengu clean`.

---

## 2. Fases

Cada fase termina con: `bun test` verde, `bunx tsc --noEmit` limpio (cuando haya
`node_modules`) y una línea en la sección 7.

### P0 — Andamiaje (0.5 kLOC)

- `package.json` 0.1.0, `tsconfig.json` estricto, `bunfig.toml`, `.gitignore`.
- `src/version.ts`, `src/main.ts` con `--version` y `--help`.
- `src/util/{result,span,text,path}.ts`.
- `src/diagnostics/{diagnostic,codes,render,sink}.ts`.
- `tests/util/*.test.ts`.
- **Aceptación:** `bun run src/main.ts --version` imprime `pengu 0.1.0`.

### P1 — Lexer (1.2 kLOC)

- `token.ts` con keywords (incluye primitivos multi-palabra como identificadores
  que el parser de tipos combina), operadores, signos.
- `lexer.ts`: INDENT/DEDENT por línea lógica, supresión de NEWLINE dentro de
  `() [] {}`, líneas en blanco y de solo comentario, `--` hasta EOL, EOF.
- `lexer_number.ts`: decimal, `0x`, `0b`, `0o`, floats con exponente.
- `lexer_string.ts`: strings multilínea, `#{expr}` (guarda sub-fuente),
  chars y escapes (`\n \t \r \\ \" \' \0 \xNN \u{...}`).
- Tests de tabla: entrada → `[kind,text]`, más errores de indentación.
- **Aceptación:** tokeniza los 7 ejemplos de `examples/` sin errores.

### P2 — AST + Parser (3.5 kLOC)

- Nodos con `span`, uniones discriminadas, `readonly`.
- Declaraciones: `realm`, `invoke` (simple/selectivo/alias), `const`,
  `static mut`, funciones nombradas con sigilos, `rune` (+`heir`, `constructor`,
  `destructor`), `enchanting` (+métodos y operadores), `omen`/`flags omen`,
  `echo`, `seal`, `extern "c"` + `declare` (extensión para bindgen).
- Sentencias: bindings (`x = e`, `mut a,b = ...`, `x: T = e`), asignaciones,
  `return`, `break [e]`, `continue`, `pass`, `unsafe` (bloque y función).
- Expresiones: literales, identificadores, `realm::sym`, member, index, call,
  `f!`, instanciación `<T>`, unarios (`- not ~ &`), binarios con precedencia,
  rangos `..`/`..<`, `as`, `ref(x)`, `mut x` en args, `@`, `parent(...)`,
  `if/unless` (bloque e inline `then/else`), `switch`, `match` con guards,
  `do`, `while/until`, `repeat`, `for` numérico e iterable con `else`,
  lambdas con/sin params, vectores, mapas, sets, tuplas, comprehensions.
- Recuperación de errores: sincronizar en NEWLINE/DEDENT/`when`; máx. 20 por archivo.
- Tests: golden de AST resumido (`kind` + spans clave) para 20 fixtures.
- **Aceptación:** parsea todos los fixtures `tests/fixtures/ok/` y reporta
  códigos correctos en `tests/fixtures/err/`.

### P3 — Proyecto y módulos (0.8 kLOC)

- `pengu.toml`: `[package] name, version, entry`; `[build] cxx, std, opt`.
- Resolución: `invoke "a/b"` → `a/b.pengu` o `a/b/index.pengu`; relativos;
  alias; selectivos; realms por archivo (`realm` o nombre de archivo).
- Detección de ciclos con camino completo en el diagnóstico; orden topológico.
- **Aceptación:** `pengu check examples/07_modules` resuelve 3 módulos y detecta
  un ciclo en un fixture dedicado.

### P4 — Checker v1 (3 kLOC)

- `types.ts`: `void bool char int… float double string vector<T> map<K,V> set<T>
  optional<T> ref<T> mut_ref<T> unique<T> shared<T> raw<T> function<...> tuple<...>
  named<realm::Name> generic<T> unknown`.
- `collect.ts`: tabla por realm (funciones, runes, omens, echo/seal, consts),
  firmas, duplicados, realms reabiertos.
- `check.ts` + `check_expr/stmt/decl.ts`: inferencia bottom-up, promoción numérica,
  `bool` obligatorio en condiciones (sin truthiness), retorno implícito/explícito,
  `mut` para reasignar, `const` inmutable, `unsafe` para `raw`/`static mut`,
  métodos de contenedores/opcionales de `builtins.ts`, `#`, `in`, casts seguros.
- `exhaustiveness.ts`: `match` sobre omen completo o con `else`.
- `ownership.ts` v1: uso tras move de `unique`, doble `mut` con `ref` activo,
  mutación estructural durante `for`, `weak.lock()` → `shared<T>?`.
- **Aceptación:** 15 fixtures erróneos producen el código esperado; 10 correctos
  pasan sin diagnósticos.

### P5 — Codegen C++20 + runtime + driver (3 kLOC)

- `cpp_types.ts`: tabla completa de mapeo; `string`→`std::string`, `T?`→
  `std::optional<T>`, `#`→`.size()`, `vector`→`std::vector`, etc.
- `cpp_expr/stmt/decl.ts`: emisión con `Writer` (indent 4); expresiones de control
  como lambdas `[&]() -> T { ... }()`; `switch`→`if/else` encadenado;
  `match`→`std::visit`/`get_if`; omen unitario→`enum class`; algebraico→`variant`.
- `runtime/pengu_rt.hpp`: `io::print/println/eprint`, `panic`, `format` helpers,
  `get_at`, `get_or`, `extract`, `push`, `pop_opt`, `contains`, `as_int`
  (try_from/from), `Display` conceptual vía `to_string`.
- `module_emit.ts`: un `.hpp` (declaraciones + tipos) y un `.cpp` (definiciones)
  por módulo, `#pragma once`, includes por import.
- `driver/`: detecta compilador, flags `-std=c++20 -O2 -Wall -Wextra`,
  enlaza, reporta stderr mapeando a diagnósticos E08xx.
- **Aceptación:** `pengu run examples/01_hello` imprime `Hello, PenguScript!`;
  `tests/fixtures/run/*.pengu` producen su `.out`.

### P6 — CLI completa (0.7 kLOC)

- `pengu build [path] [-o bin] [--emit-cpp] [--release]`
- `pengu run <file> [-- args...]`
- `pengu check [path] [--json] [--strict]`
- `pengu fmt [path] [--check] [--stdout]`
- `pengu lsp`
- `pengu bindgen <header> [-o out.d.pengu] [--clang path]`
- `pengu init [dir]` (crea `pengu.toml`, `src/main.pengu`, `.gitignore`)
- `pengu doctor` (versiones de bun, g++, clang++, rutas)
- `pengu clean`
- Códigos de salida: 0 ok, 1 diagnósticos, 2 uso incorrecto, 3 toolchain.
- **Aceptación:** cada comando tiene `--help` y un test e2e.

### P7 — Formatter (0.8 kLOC)

- Basado en tokens (preserva comentarios) + nivel de indentación.
- Reglas: 2 espacios, `=` y binarios con espacios, `,` sin espacio antes,
  `:` de tipo sin espacio antes, `->` con espacios, una sentencia por línea,
  máximo una línea en blanco entre bloques, `then` inline se conserva.
- `--check` sale 1 si hay diferencias; idempotencia testeada (fmt(fmt(x))==fmt(x)).
- **Aceptación:** los 7 ejemplos quedan estables tras dos pasadas.

### P8 — LSP (1.5 kLOC)

- Framing `Content-Length`, JSON-RPC 2.0, full sync, cancelación básica.
- Capacidades: `textDocumentSync=1`, hover, completion (`:`/`::`/`.`),
  definition, documentSymbol, semanticTokens/full, formatting, publishDiagnostics.
- Análisis incremental por documento con cache por versión y debounce 150 ms.
- **Aceptación:** `bun test tests/lsp` inicia el server, abre un doc con error,
  recibe `publishDiagnostics`, pide hover y formatting.

### P9 — Extensión de editor (0.4 kLOC)

- VS Code: `package.json` con `engines.vscode`, lenguaje `penguscript`,
  gramática TextMate (keywords, tipos, runes, strings con `#{}`, comentarios),
  cliente LSP que lanza `pengu lsp`.
- Configuración Neovim/Zed documentada en `editors/README.md` (sin código extra).
- **Aceptación:** `pnpm -C editors/vscode package` produce `.vsix` (o `vsce ls`).

### P10 — Bindgen con clang (0.9 kLOC)

- `clang++ -Xclang -ast-dump=json -fsyntax-only <header>` (+ `-I` flags).
- Filtra `FunctionDecl`, `RecordDecl`, `EnumDecl`, `TypedefDecl`, `CXXMethodDecl`.
- Mapea tipos C/C++ → PenguScript (`int`→`int`, `size_t`→`size_t`, punteros→
  `raw<T>`, `const char*`→`string_view`, structs→`rune` con campos).
- Emite `.d.pengu` determinista (ordenado por nombre) con `extern "c"` +
  `declare`, listo para `invoke`.
- **Aceptación:** bindgen de una cabecera C propia (`tests/fixtures/bindgen/demo.h`)
  genera un `.d.pengu` que el checker acepta.

### P11 — stdlib (2 kLOC)

- Orden: `core`, `io`, `string`, `vector`, `map`, `set`, `optional`, `math`,
  `fs`, `path`, `time`, `random`, `error`, `assert`, `iter`, `format`.
- Cada módulo: `.d.pengu` (firmas) + `.pengu` (implementación) cuando aplique.
- Implementación inicial en C++ en `runtime/` para lo que no se puede expresar
  aún (io, fs, math); el resto en PenguScript.
- **Aceptación:** ejemplos usan solo APIs de stdlib y compilan.

### P12 — Ejemplos y documentación (0.6 kLOC)

- `examples/01_hello` … `07_modules`, cada uno con `README.md` de 3 líneas.
- `README.md` raíz: instalación con Bun, `pengu run examples/01_hello`.
- **Aceptación:** `bun run scripts/verify_examples.ts` compila y ejecuta todos.

### P13 — Self-hosting y release (continuo)

- Reescribir en `.pengu` partes del toolchain que el lenguaje ya soporte
  (formatter primero, luego parser), manteniendo el checker en TS.
- Checklist final 0.1.0 (sección 6) completo; `pengu doctor` verde en Linux.

---

## 3. Estrategia de pruebas

| Nivel | Ubicación | Qué valida |
|---|---|---|
| Unidad | `tests/{lexer,parser,checker,codegen}` | tablas entrada→salida, sin proceso |
| Golden AST | `tests/fixtures/ast/*.json` | forma del AST y spans |
| Diagnósticos | `tests/fixtures/err/*.expect` | códigos exactos y líneas |
| Ejecución | `tests/fixtures/run/*.out` | stdout del binario compilado |
| E2E CLI | `tests/e2e/*.test.ts` | comandos, códigos de salida, `--json` |
| LSP | `tests/lsp/*.test.ts` | framing, diagnósticos, hover |
| Bindgen | `tests/fixtures/bindgen/` | `.d.pengu` determinista |

`bun test` corre todo. Los tests de codegen/ejecución se saltan con
`PENGU_SKIP_NATIVE=1` (CI sin g++).

Regla: un bug = un fixture nuevo antes del fix.

---

## 4. Cobertura del lenguaje (mapa a cheatsheet)

`scratch/plan.md` ya enumera las features por bloque (A–E). Este plan las ordena
por dependencia de implementación:

| Bloque cheatsheet | Fase |
|---|---|
| Lexer, comentarios, literales, strings/interpolación | P1 |
| Declaraciones, control de flujo, funciones, lambdas | P2 |
| Módulos, realms, invoke, alias, ciclos | P3 |
| Tipos, inferencia, mutabilidad, casts, contenedores | P4 |
| Runes, enchanting, herencia, operadores, echo/seal | P2/P4/P5 |
| Omens (unitarios, flags, algebraicos, genéricos) | P2/P4/P5 |
| Ownership (ref/mut/unique/shared/raw), unsafe, exclusividad | P4 |
| Genéricos/sigilos y constraints | P4/P5 (templates C++) |
| Thread safety (`Send`/`Sync` estático) | P11 (tras stdlib thread) |
| Codegen, runtime, toolchain | P5 |
| Formatter, LSP, editor, bindgen | P7–P10 |

---

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Indentación ambigua (tabs/espacios mezclados) | error E0101 con columna exacta; el lexer nunca "adivina" |
| Interpolación anidada compleja | sub-fuente con offset base; tests de `"a#{f("#{x}")}b"` |
| Checker incompleto bloquea codegen | codegen solo corre si `checker.ok`; fixtures por feature |
| C++ generado ilegible | `Writer` + plantillas por nodo; snapshot de módulos ≤60 líneas |
| `std::format` no disponible | runtime usa `ostringstream` propio; sin dependencia de `<format>` |
| LSP sin deps → bugs de framing | parser incremental de bytes con buffer; tests con pipe |
| Bindgen clang cambia JSON entre versiones | filtrar por `kind` y tolerar campos faltantes; test con clang 23 |
| Scope creep (stdlib completa) | stdlib mínima por fase; el resto en P11 con `.d.pengu` |
| Tokens/contexto | fixtures como documentación; no reescribir archivos completos |

---

## 6. Definición de Hecho — 0.1.0

- [ ] `pengu build/run/check/fmt/lsp/bindgen/init/doctor/clean` funcionales.
- [ ] Lexer/parser cubren el 100% de la sintaxis de `docs/cheatsheet.md`.
- [ ] Checker: tipos, mutabilidad, unsafe, ownership v1, exhaustividad.
- [ ] Codegen C++20 compila con g++ 16 y clang++ 23 sin warnings.
- [ ] LSP: diagnósticos, hover, completion, definition, symbols, tokens, format.
- [ ] Extensión VS Code publicable; gramática TextMate completa.
- [ ] Bindgen produce `.d.pengu` válidos para cabeceras C.
- [ ] 7 ejemplos ejecutables + `tests/fixtures` verdes.
- [ ] `README.md` actualizado (Bun, no Python/uv).
- [ ] Versión 0.1.0 en todos los artefactos.

---

## 7. Bitácora

- P0 ✅ esqueleto Bun + CLI (`--version`, `--help`, `doctor`, `init`, `clean`), utilidades (span, result), diagnósticos con código estable y render con caret.
- P1 ✅ lexer completo: indentación INDENT/DEDENT, comentarios, números (hex/bin/oct, `_`), strings multilínea con interpolación `#{...}`, chars y escapes. 10 tests.
- P2 ✅ parser completo sobre AST inmutable (`kind`): declaraciones (`realm`, `invoke` selectivo/alias, `const`, `static mut`, `rune`+ctor/dtor, `enchanting`+operadores, `omen` unit/flags/algebraico, `echo`, `seal`, `extern`), expresiones (todos los operadores, `as`, rangos, comprensiones, lambdas), control (`if/unless/switch/match/do/while/until/repeat/for`), patrones. 23 tests.
- P3 ✅ checker: tipos `PenguType`, scopes, `TypeEnv`, módulos, inferencia de expresiones y sentencias, mutabilidad (`E0406`), `unsafe` (`E0603`), exhaustividad de `match` (`E0701`), aridad (`E0504`), condicionales (`E0503`). 17 tests.
- P4 ✅ codegen C++20 (`cpp_types`, `cpp_expr`, `cpp_stmt`, `cpp_decl`, `cpp_module`, runtime `pengu_rt.hpp`) + driver `compile_file` con caché `.pengu-cache/<hash>/`.
- P5 ✅ CLI `build`/`run` con `g++`/`clang++`, `--out`, `--link`, `--compiler`; `explain_failure` reutiliza diagnósticos.
- P6 ✅ formateador (`format_tokens` token-based, 2 espacios, comentarios y líneas en blanco, `<T>` pegados, idempotente) + `pengu fmt --check`.
- P7 ✅ LSP sobre stdio sin dependencias: initialize/shutdown, didOpen/didChange/didSave/didClose, publishDiagnostics, hover (tipos inferidos), completion (keywords + símbolos), definition (símbolos del módulo), documentSymbol y formatting. 2 tests de integración.
- P8 ✅ bindgen con clang: `clang++ -Xclang -ast-dump=json`, mapa de tipos C→PenguScript, salida `.d.pengu` con `extern "C"`; `pengu bindgen <cabecera> [--realm] [--out]`. Conversión `string` ↔ `const char*` en la frontera mediante envolturas inline. `tests/e2e/bindgen_native.test.ts` compila `demo.c` con gcc, genera enlaces, compila y ejecuta el binario enlazado.
- P9 ✅ módulos multi-archivo: `invoke` con alias y selectivo, realm por archivo, ciclos `E0302`, símbolos externos en checker y codegen (`realm::simbolo`); resolución de `path.pengu`, `path.d.pengu` y `path/index.pengu`.
- P10 ✅ extensión VS Code (`editors/vscode`): gramática TextMate, configuración de lenguaje, cliente LSP (`pengu lsp`); README con empaquetado (`vsce package`) y `.vscodeignore`.
- P11 ✅ (base) stdlib intrínseca con firmas reales en `src/semantic/builtin_modules.ts` (`io`, `math`, `fs`, `format`, `time`, `os`, `random`, `log`, `assert`), variádicas y aridad comprobadas; `try_from`/`from`, acceso seguro (`get_at`, `map_get*`, `map_extract`, `pop_opt`, `map_insert`, `set_insert`) en el runtime C++. Además `std/{math,fs,time,random,os,assert}.d.pengu` declaran las firmas con el bloque `declare` (el runtime C++ las implementa); `tests/std/std.test.ts` comprueba que no falte ninguna implementación y que el cargador resuelva `std/...`.
- P12 ✅ (v1) `break value` (bucle → `T?`), `else` de bucle, variantes de omen sin prefijo (`Circle(1.0)`), `weak(shared)` + `.lock()` opcional, `in` sobre `string`, verificados con `tests/e2e/features.test.ts` (5 pruebas de extremo a extremo). ownership v1: `unique<T>(...)`/`shared<T>(...)`/`weak(x)` construidos con `make_unique`/`make_shared`, movimiento por paso de parámetro y asignación (`use after move` → E0601), auto-desreferencia de punteros en miembros. Caché de `pengu build`/`run` por contenido del C++ generado + runtime + flags: reutiliza el binario y se invalida si cambia cualquier módulo importado. Publicación de la extensión pendiente.

Estado actual: 85 tests / 11 archivos en verde (`bun test`), `tsc --noEmit` limpio, 10 ejemplos ejecutables (`examples/01_hello` … `10_ownership`), FFI verificado de extremo a extremo (cabecera → bindgen → objeto C → binario).
