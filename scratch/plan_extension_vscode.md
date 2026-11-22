# Plan: extensión de VS Code completa para PenguScript

Estado: **implementado** (2026-11-21, fases E1–E7). Aprobado en m07112.
Versión objetivo: `0.1.0` (la misma que el compilador; no se sube).

---

## 0. Resumen

La extensión de VS Code funciona hoy como un cliente LSP mínimo: arranca
`pengu lsp`, colorea con una gramática incompleta y aporta diagnósticos, hover,
autocompletado, definición, símbolos y formato. Le falta la mitad de la
experiencia: **la gramática no cubre el lenguaje**, **no hay snippets**, **no
se puede compilar ni ejecutar desde el editor**, **no hay tareas ni botones**,
**no hay manejo de errores si `pengu` no está**, **no hay pruebas** y la
documentación no describe nada de eso.

La auditoría de §1 lo cuantifica: **1 keyword ausente, 47 nombres de tipo
ausentes, 5 operadores ausentes, 0 comandos, 0 snippets, 0 tareas, 0
keybindings, 0 pruebas**, más un directorio vacío y sin `launch.json` para el
`F5` que promete el README.

El plan se divide en siete fases (E1–E7). Cada fase deja la extensión
instalable y verificable; al final, `bun test` cubre también la extensión y el
`.vsix` se genera e instala con los scripts existentes.

---

## 1. Auditoría con evidencia

### 1.1 Gramática (`editors/vscode/syntaxes/pengu.tmLanguage.json`, 62 líneas)

Comparada contra las tablas del compilador (`src/frontend/token.ts` y
`src/frontend/ast_type.ts`), que son la fuente de verdad del lenguaje:

| Elemento | En el compilador | En la gramática | Falta |
|---|---|---|---|
| Keywords | 45 | 44 | `declare` |
| Operadores | 35 | 30 | `...`, `<<`, `>>`, `<<=`, `>>=` |
| Primitivos | 21 | 15 | multi-palabra (`signed char`, `unsigned char`, `unsigned short`, `unsigned int`, `unsigned long`, `unsigned long long`, `long long`, `long double`), `wchar_t`, `char8_t`, `char16_t`, `char32_t`, `nullptr_t` |
| Cadenas | 10 | 1 (`string`) | `wstring`, `u8string`, `u16string`, `u32string`, `string_view`, `wstring_view`, `u8string_view`, `u16string_view`, `u32string_view` |
| Ancho fijo | 13 | 9 | `ptrdiff_t`, `intptr_t`, `uintptr_t`, `byte` |
| Contenedores | 31 | 18 | `forward_list`, `multiset`, `unordered_set`, `multimap`, `unordered_map`, `unordered_multimap`, `stack`, `queue`, `priority_queue`, `bitset`, `variant`, `any`, `init_list`, `complex`, `atomic`, `mutex`, `shared_mutex`, `condition_variable`, `thread` |
| `Ordering` | tipo del runtime | no | `Ordering` |
| Números | `0x`, `0b`, `0o`, decimal, float | `0x`, `0b`, decimal, float | `0o` |
| Scopes | — | 7 patrones | `constant.language` (`true/false/none/nullptr`), `entity.name.function`, `entity.name.namespace` (tras `realm`), `variable.other.member` (campos), `variable.parameter`, `variable.language.self` (`@`), `keyword.operator.size-of` (`#`), `punctuation.*` |

Además:

- El lookbehind de `entity.name.type` (`syntaxes/pengu.tmLanguage.json:22`) solo
  cubre `rune|omen|echo|seal|enchanting`: `rune Perro heir Animal` deja
  `Animal` sin resaltar, y las declaraciones genéricas (`rune Caja<T>`) pierden
  el `<T>`.
- No hay reglas para el bloque `declare` (`std/*.pengu`), que hoy se ve como
  texto plano.
- El grupo `keyword.other` mezcla modificadores (`mut`, `const`, `static`,
  `unsafe`, `needs`, `operator`) con constantes (`true`, `false`, `none`,
  `nullptr`), que deben llevar scopes distintos.

### 1.2 Configuración del lenguaje (`language-configuration.json`, 16 líneas)

| Falta | Consecuencia real |
|---|---|
| `wordPattern` | doble clic/selección de palabra rota en `@campo`, `#xs`, `realm::x`, `campo.nombre` |
| `indentationRules` completas | `switch`/`match` y sus `when` no siempre indentan; `declare` no indentan; líneas que terminan en `then` inline pueden indentar de más |
| `onEnterRules` | al pulsar Intro tras `--` no continúa el comentario; dentro de `#{...}` no se cierra la interpolación |
| `autoCloseBefore` | autocierre de `"`/`'` agresivo delante de `)` o `,` |

Hoy solo hay `comments.lineComment`, `brackets`, pares de autocierre, y dos
regex de indentación (`language-configuration.json:12-15`).

### 1.3 Extensión (`src/extension.js`, 32 líneas)

| Capacidad | Estado |
|---|---|
| Cliente LSP por stdio | ✅ |
| Selección de documentos y watcher `**/*.pengu` | ✅ |
| Comandos (`run`, `build`, `check`, `fmt`, `bindgen`, `init`, `doctor`, reinicio) | ❌ 0 |
| Terminal integrada / botón ▶ Ejecutar / menús / keybindings | ❌ 0 |
| `TaskProvider` + `problemMatcher` (`Ctrl+Shift+B`, `tasks.json`) | ❌ 0 |
| Snippets | ❌ 0 |
| `outputChannel` y `trace.server` | ❌ |
| Detección de `pengu` ausente y mensaje accionable | ❌ (`client.start()` sin `catch`) |
| Reinicio al cambiar `pengu.executable` | ❌ |
| `check --json` al guardar | ❌ |
| Barra de estado | ❌ |
| `untrustedWorkspaces` / `extensionKind` | ❌ |

Detalle de la única propiedad configurable (`package.json:28-38`):
`pengu.executable` (default `"pengu"`). No hay `pengu.build.args`,
`pengu.run.args`, `pengu.check.onSave` ni `pengu.lsp.trace.server`.

### 1.4 Empaquetado y metadatos

- `package.json` no declara `commands`, `menus`, `keybindings`, `snippets`,
  `taskDefinitions`, `problemMatchers`, `configurationDefaults`, `repository`,
  `icon`, `extensionKind` ni `capabilities.untrustedWorkspaces`.
- No existe `LICENSE` (aunque `license: "MIT"` está declarado) ni
  `editors/vscode/.vscode/launch.json`, así que el «pulsa `F5`» del README no
  funciona sin crearlo a mano.
- `editors/vscode-penguscript/` es un **directorio vacío** heredado de pruebas
  de empaquetado.
- `.vscodeignore` no excluye `test/**` ni `**/*.ts`; con las pruebas nuevas
  habrá que ajustarlo para no engordar el `.vsix`.
- `README.md` de la extensión (26 líneas) no documenta comandos, ajustes,
  snippets ni tareas — porque no existían.

### 1.5 Pruebas

No hay ninguna prueba de la extensión. Por eso el desfase de §1.1 pasó
inadvertido (`declare` existe en el compilador desde F3 y en la gramática
nunca apareció). Tampoco hay validación de que `package.json` y
`extension.js` declaren los mismos comandos.

### 1.6 Lo que el LSP sí ofrece (y la extensión puede aprovechar)

`src/lsp/server.ts:322-334` declara `textDocumentSync`, `hoverProvider`,
`completionProvider` (`"." ":" "@" "#"`), `definitionProvider`,
`documentSymbolProvider` y `documentFormattingProvider`. **No** hay
`codeAction`, `semanticTokens`, `inlayHint`, `rename`, `references`,
`signatureHelp` ni `foldingRange`; este plan no los añade en el compilador
(sería otra fase del LSP), pero la extensión debe funcionar sin ellos.

---

## 2. Diagnóstico

1. **No hay fuente única para la gramática.** El compilador ganó keywords y
   tipos (`declare`, variádicas, `std/memory`, …) y la gramática se quedó en
   F0. La solución no es generarla (los scopes son decisión humana y de
   mantenimiento), sino **probarla contra** `KEYWORDS`, `OPERATORS` y las
   tablas de tipos: si el compilador crece, la prueba falla.
2. **La extensión se quedó en «cliente LSP».** El resto de la experiencia
   (`run`, `build`, tareas, snippets) nunca se escribió.
3. **No hay red de seguridad.** Sin pruebas de JSON ni de snippets, cualquier
   regresión rompe el resaltado en silencio.

---

## 3. Decisiones de diseño (D1–D8)

- **D1 — Comandos sobre terminal, no sobre `child_process`.** `run`/`build`/
  `check`/`fmt`/`bindgen`/`init`/`doctor` se ejecutan con
  `terminal.sendText("pengu …")` en una terminal dedicada `PenguScript`, con
  el `cwd` del proyecto (`pengu.toml` más cercano) o de la carpeta del
  archivo. Así el usuario ve la salida, puede cancelar con `Ctrl+C` y no hay
  procesos huérfanos. `child_process.execFile` se reserva para cosas
  silenciosas: `pengu --version` (detección) y `pengu check --json` (guardado).
- **D2 — Tareas de verdad.** `TaskProvider` + `contributes.taskDefinitions` +
  `problemMatchers` (`$pengu`) para que `Ctrl+Shift+B`, «Run Task» y un
  `tasks.json` escrito a mano funcionen, con los errores del compilador
  enlazados al archivo y la línea.
- **D3 — Snippets en `.code-snippets`.** Un archivo
  `snippets/penguscript.code-snippets` con los moldes del lenguaje; las
  pruebas quitan los placeholders (`$1`, `${1:x}`) y compilan el texto
  resultante con el parser real, así un snippet no puede quedar obsoleto.
- **D4 — La gramática se prueba, no se genera.** Prueba de cobertura contra
  `src/frontend/token.ts` y `src/frontend/ast_type.ts`; los scopes siguen
  siendo manuales. Si mañana se añade un tipo al compilador, la prueba falla
  con el nombre exacto que falta.
- **D5 — Ajustes mínimos y explícitos.** `pengu.executable`,
  `pengu.build.args`, `pengu.run.args`, `pengu.check.onSave`,
  `pengu.lsp.trace.server`. `configurationDefaults` solo con lo que la spec
  ya impone: `[pengu]` → `editor.insertSpaces: true`, `editor.tabSize: 2`,
  `editor.detectIndentation: false`. **No** se fuerza `formatOnSave` (el
  usuario decide).
- **D6 — `pengu` ausente es un caso de primera clase.** Al activar se ejecuta
  `pengu --version`; si falla, un aviso con «Configurar ruta» y «Ver README»,
  y una barra de estado en gris. Los comandos se registran igual (fallan con
  un mensaje claro) y `pengu lsp` no se arranca.
- **D7 — Pruebas sin Electron ni dependencias nuevas.** `tests/extension/`
  con `bun test`: validación de JSON, cobertura de gramática, snippets
  parseables, coherencia de comandos y de documentación. Nada de
  `@vscode/test-electron` (pesado y con descargas de VS Code).
- **D8 — Limpieza y metadatos.** Se borra `editors/vscode-penguscript/`, se
  añade `.vscode/launch.json` (Extension Host, F5 real), `LICENSE` MIT y los
  campos `keywords`/`categories` que falten. Versión `0.1.0`.

---

## 4. Fases

### E1 — Gramática completa y con scopes

Objetivo: que **todo** token del lenguaje tenga un scope razonable.

- Keywords: añadir `declare`; separar `storage.modifier` (`mut`, `const`,
  `static`, `unsafe`, `needs`, `operator`, `flags`, `heir`, `constructor`,
  `destructor`, `parent`, `declare`, `extern`) de `keyword.operator.word`
  (`and`, `or`, `not`) y `constant.language` (`true`, `false`, `none`,
  `nullptr`).
- Tipos: primitivos multi-palabra como patrones propios (el más largo
  primero: `unsigned long long` antes que `unsigned long`), cadenas (las 10),
  ancho fijo (13), contenedores (31) y `Ordering`.
- Números: `0o[0-7_]+`.
- Operadores: `...`, `<<`, `>>`, `<<=`, `>>=`.
- Scopes nuevos: `entity.name.function` en `nombre = (` y
  `nombre = <T>(`, `entity.name.namespace` tras `realm`,
  `variable.other.member` en `campo: Tipo` dentro de `rune`/`omen`,
  `variable.parameter` en firmas, `variable.language.self` (`@`),
  `keyword.operator.size-of` (`#`), `entity.name.type` también tras `heir` y
  dentro de `enchanting`.
- Puntuación: `,` `:` `;`(no existe) `::` `.` `?` `..` `..<` `->`.

Criterios de aceptación:

1. La prueba de cobertura de E7 pasa con **0 faltantes** de keywords,
   operadores, números y tipos.
2. Un archivo de muestra (`examples/13_enchanting/main.pengu` más un archivo
   `std/*.pengu`) se ve correctamente en «Developer: Inspect Editor Tokens and
   Scopes» (lista de comprobación manual en E7).
3. El JSON sigue siendo válido y el `.vsix` no crece de forma desmedida.

### E2 — `language-configuration.json` completa

- `wordPattern: "(-?\\d*\\.?\\d+)|([A-Za-z_][A-Za-z0-9_]*)"` (los números y
  los identificadores se seleccionan enteros; `@`/`#`/`::` quedan fuera de la
  palabra, como en la mayoría de lenguajes).
- `indentationRules.increaseIndentPattern`:
  `(->|then|else|do|match|switch|enchanting|rune|omen|seal|echo|extern|declare|flags)\s*$`
  o `^\s*(if|unless|while|until|for|repeat)\b`, o
  `^\s*when\b.*\bthen\s*$` (armas con bloque).
- `decreaseIndentPattern`: `^\s*(else|when|until)\b`.
- `onEnterRules`:
  - después de `^(\s*)--\s?` → insertar `-- ` (continuar comentario);
  - dentro de `#{` sin cerrar → no autoindentar (action `none`).
- `autoCloseBefore: ";:.,=}])> \n\t"` y pares que respeten `'`/`"`.

Criterios: JSON válido; comprobación manual de indentación en `rune`, `omen`
con variantes, `switch`/`match`, `declare`, `if/then` inline y en bloque, y
`enchanting` con genéricos.

### E3 — Snippets y valores por defecto

- `snippets/penguscript.code-snippets` con, como mínimo:
  `main`, `invoke`, `invoke-selectivo`, `realm`, `rune`, `rune-heir`,
  `constructor`, `destructor`, `enchanting-rune`, `enchanting-incorporado`,
  `omen-unitario`, `omen-algebraico`, `flags`, `echo`, `seal`, `declare`,
  `funcion`, `funcion-generica`, `variadica`, `if`, `if-else`, `unless`,
  `switch`, `match`, `for-numerico`, `for-iterable`, `while`, `repeat`, `do`,
  `comprehension`, `literal-tipado`, `map-literal`, `set-literal`,
  `interpolacion`, `unsafe`, `static-mut`, `operator`, `operator-libre`,
  `try-from`, `opcional`.
- `contributes.snippets` y `categories` con `Snippets`.
- `configurationDefaults` de D5.

Criterios: JSON válido; cada snippet, sin placeholders, parsea sin
diagnósticos con `parse_text`; los nombres no se repiten; los `prefix` no
chocan con keywords.

### E4 — Comandos, menús, teclas y terminal

Comandos (`contributes.commands` + `registerCommand`):

| id | Título | Qué hace |
|---|---|---|
| `pengu.runFile` | PenguScript: Ejecutar archivo | `pengu run <archivo>` en terminal |
| `pengu.runProject` | PenguScript: Ejecutar proyecto | `pengu run` (usa `pengu.toml`) |
| `pengu.buildFile` | PenguScript: Compilar archivo | `pengu build <archivo>` |
| `pengu.checkFile` | PenguScript: Verificar archivo | `pengu check <archivo>` |
| `pengu.fmtFile` | PenguScript: Formatear archivo | comando LSP `editor.action.formatDocument`; si no, `pengu fmt <archivo>` |
| `pengu.bindgen` | PenguScript: Generar enlaces (bindgen) | prompt del `.h`, `pengu bindgen <h> --realm <r> --out <d.pengu>` |
| `pengu.init` | PenguScript: Inicializar proyecto | `pengu init` en la carpeta |
| `pengu.doctor` | PenguScript: Diagnóstico del toolchain | `pengu doctor` |
| `pengu.restartServer` | PenguScript: Reiniciar servidor | reinicia el cliente LSP |
| `pengu.showOutput` | PenguScript: Ver registro | muestra el `outputChannel` |

- Terminal `PenguScript`: reutilizada, `cwd` = raíz del proyecto (o carpeta
  del archivo), con quoting correcto de rutas con espacios.
- Menús: `editor/title` (▶ junto a «Ejecutar archivo»), `editor/context`,
  `explorer/context` para `.pengu`/`.d.pengu`, `commandPalette` con `when`.
- Keybindings: `ctrl+alt+r` ejecutar archivo, `ctrl+alt+b` compilar,
  `ctrl+alt+k` verificar (documentados en el README).
- Barra de estado: `PenguScript 0.1.0` (o «pengu no encontrado»), click →
  registro.
- Guardado: si `pengu.check.onSave`, ejecutar `check --json` y publicar en una
  `DiagnosticCollection` propia (independiente del LSP, para cuando el LSP
  esté desactivado).

Criterios: los 10 comandos aparecen en la paleta; ejecutar/compilar abre la
terminal y muestra la salida; el botón ▶ solo aparece en `.pengu`; un archivo
con error de sintaxis se ve también con el LSP parado (vía `check --json`).

### E5 — Tareas y `problemMatcher`

- `contributes.taskDefinitions`: tipo `pengu` con `command`
  (`build`|`run`), `file` (opcional) y `args`.
- `TaskProvider` devuelve `ShellExecution` con el comando ya citado y el
  `cwd` correcto.
- `contributes.problemMatchers`: `$pengu` con
  `^(.+?):(\d+):(\d+): (error|warning)\[([A-Z]\d{4})\]: (.+)$`,
  `fileLocation: absolute`, `severity` mapeado y `code` capturado.
- `group: { kind: "build", isDefault: true }` para `Ctrl+Shift+B`.

Criterios: «Tasks: Run Task» lista `pengu: compilar` y `pengu: ejecutar`;
`Ctrl+Shift+B` compila el archivo activo; los errores salen en «Problems» con
archivo/línea; un `tasks.json` con `"type": "pengu"` funciona.

### E6 — Robustez del cliente LSP

- `outputChannel` (`PenguScript`) y `trace` desde
  `pengu.lsp.trace.server` (`off|messages|verbose`).
- `client.start()` con `catch` → aviso accionable (D6) y barra de estado.
- Reinicio al cambiar `pengu.executable` o `pengu.lsp.trace.server`
  (`onDidChangeConfiguration`).
- `capabilities.untrustedWorkspaces: { supported: "limited", description }` y
  `extensionKind: ["workspace"]`.
- `deactivate()` seguro si nunca se arrancó el cliente.

Criterios: con `pengu.executable` apuntando a algo inexistente aparece un
aviso con acciones y **no** un error rojo sin contexto; al corregir la ruta y
guardar, el servidor se reinicia solo; el registro muestra los mensajes del
servidor cuando `trace = verbose`.

### E7 — Pruebas, documentación y empaquetado

- `tests/extension/extension.test.ts` (varios `describe`):
  1. `package.json` válido: ids de comandos únicos, todos los `commands`
     aparecen en `src/extension.js`, `activationEvents` coherente.
  2. Gramática: cobertura 100 % de `KEYWORDS`, `OPERATORS`, `0o`, y de
     `PRIMITIVE_TYPES` ∪ `FIXED_WIDTH_TYPES` ∪ `STRING_TYPES` ∪
     `BUILTIN_TYPE_NAMES` ∪ `{"Ordering"}`; los patrones compilan.
  3. Snippets: JSON válido, prefijos únicos, y cada cuerpo (sin placeholders)
     parsea con `parse_text` y `make_source`.
  4. `language-configuration.json`: válido, `wordPattern` presente, brackets
     equilibrados, regex de indentación compilan.
  5. Coherencia de documentación: cada comando de `package.json` aparece en
     `editors/vscode/README.md` y en la tabla del README raíz.
  6. Limpieza: no existe `editors/vscode-penguscript/`; existe
     `editors/vscode/.vscode/launch.json`; `.vscodeignore` excluye `test/**`.
- Documentación: `editors/vscode/README.md` reescrito (features, tabla de
  comandos, tabla de ajustes, snippets, tareas, problemas y soluciones,
  desarrollo con F5); README raíz con la lista de lo que aporta la extensión;
  `CHANGELOG.md` con «Añadido en las fases E1–E7»; bitácora de este plan.
- Empaquetado: `bash scripts/vsix.sh --package-only` genera el `.vsix`,
  `code --install-extension` lo instala y `code --list-extensions` lo muestra;
  el `.vsix` no incluye `test/`, `.vscode/` ni `node_modules/.bin`.

Criterios: `bun test` verde con las pruebas nuevas; `bunx tsc --noEmit`
limpio; `pengu fmt --check` sigue limpio; el `.vsix` se instala y la extensión
funciona en una ventana nueva (lista de comprobación manual: resaltado,
snippets, ▶, tarea, hover, error, formato).

---

## 5. Matriz de cobertura

| Capacidad | Dónde | Prueba |
|---|---|---|
| Keywords/tipos/operadores/números | `syntaxes/pengu.tmLanguage.json` | E7.2 (cobertura) |
| Scopes semánticos (funciones, campos, `@`, `#`) | idem | E7.2 + inspección manual |
| Indentación, comentarios, wordPattern | `language-configuration.json` | E7.4 + manual |
| Snippets | `snippets/penguscript.code-snippets` | E7.3 (parseo) |
| Ejecutar/compilar/verificar/formatear | `src/extension.js` + `package.json` | E7.1 + manual |
| Botón ▶, menús, teclas | `package.json` | E7.1 + manual |
| Tareas y problemas | `package.json` + `src/extension.js` | manual + E7.1 |
| Ajustes y defaults | `package.json` | E7.1 + E7.4 |
| Robustez del LSP | `src/extension.js` | manual + E7.6 |
| Ajustes documentados | `editors/vscode/README.md` | E7.5 |
| Empaquetado limpio | `.vscodeignore` | E7.6 + `scripts/vsix.sh` |

---

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| Los regex TextMate se escapan mal (`<`, `>`, `[`, `#`) | Prueba que compila cada patrón y comparación contra las tablas del compilador |
| Multi-palabra (`unsigned long long`) resaltado parcial | Patrones ordenados de más largo a más corto y prueba de cobertura por nombre completo |
| Las pruebas acoplan la extensión al compilador | Es intencional (D4): el compilador es la spec; el test da el nombre exacto que falta |
| `code` CLI ausente en la máquina del usuario | `scripts/vsix.sh` ya imprime instrucciones manuales; la prueba no depende de `code` |
| Snippets con indentación de tabs que el parser rechaza | La prueba normaliza tabs→espacios antes de parsear |
| Tareas con rutas con espacios | Comillas simples en `ShellExecution` y prueba manual con una ruta con espacios |
| El `.vsix` crece por `node_modules` | `.vscodeignore` excluye `test/`, `.vscode/`, `**/*.map`, `node_modules/.bin`; el resto es necesario para el cliente LSP |

---

## 7. Criterio de terminado

- [ ] `bun test` verde con `tests/extension/` (0 fallos).
- [ ] `bunx tsc --noEmit` limpio y `pengu fmt --check` sin cambios.
- [ ] 0 keywords, 0 operadores, 0 tipos y 0 números del compilador sin
      cubrir en la gramática.
- [ ] 10 comandos, 2 tareas, 1 `problemMatcher`, ≥25 snippets, 5 ajustes.
- [ ] `pengu` ausente → aviso accionable, sin excepción sin capturar.
- [ ] `.vsix` generado e instalado; extensión usable en una ventana nueva.
- [ ] README de la extensión y CHANGELOG actualizados; versión `0.1.0`.
- [ ] `editors/vscode-penguscript/` eliminado; `launch.json` y `LICENSE`
      presentes.

---

## 8. Bitácora

| Fase | Estado | Verificación |
|---|---|---|
| E1 gramática | ✅ | `tests/extension/grammar.test.ts` (6): 0 keywords, 0 tipos y 0 operadores sin scope; todas las regex compilan |
| E2 language-configuration | ✅ | `tests/extension/language.test.ts` (5): `wordPattern`, sangría que abre/cierra y `onEnterRules` |
| E3 snippets | ✅ | 49 snippets; `tests/extension/snippets.test.ts` (4) los parsea tras quitar marcadores |
| E4 comandos y terminal | ✅ | 11 comandos en `package.json` == 11 registrados; `tests/extension/sources.test.ts` (6) |
| E5 tareas y problemas | ✅ | `tests/extension/tasks.test.ts` (3): el problem matcher `$pengu` reconoce un diagnóstico real |
| E6 robustez LSP | ✅ | `start_client`/`stop_client`/`restart_client`, barra de estado, aviso accionable, reinicio al cambiar ajustes |
| E7 pruebas, docs y empaquetado | ✅ | `bun test` 314 pass / 38 archivos; `.vsix` empaquetado e instalado; README y CHANGELOG |

Notas de cierre:

- El cambio de `match` con `else` (`src/frontend/parser_control.ts`,
  `src/semantic/checker_control.ts`, `src/codegen/cpp_expr_control.ts`) se
  encontró validando los snippets y quedó cubierto por el banco de pruebas.
- La regla de indentación no cubría `rune Punto` ni `switch forma`; se corrigió
  `language-configuration.json` y el caso quedó fijado en las pruebas.
- `editors/vscode-penguscript/` (vacío) se eliminó; se añadieron
  `.vscode/launch.json` y `LICENSE`.
- La prueba de humo (`tests/extension/runtime.test.ts`, 6 pruebas) activa la
  extensión con un `vscode` simulado; descubrió que el binario instalado en el
  `PATH` era antiguo (sin `check --json`), así que se recompiló y reinstaló con
  `scripts/install.sh`.
