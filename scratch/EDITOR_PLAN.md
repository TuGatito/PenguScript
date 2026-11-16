# Plan — LSP y extensión de VS Code completos

Estado: cerrado; fases E0–E6 completadas.

## Objetivo

Que la extensión de VS Code y el servidor `pengu lsp` funcionen **juntos** y
cubran lo necesario para desarrollar en PenguScript: diagnósticos, hover con
tamaños, autocompletado (incluidos módulos de la std), inlay hints, resaltado
semántico, referencias/rename, snippets, resaltado de `#{…}` en cadenas, y
ejecutar/probar el programa desde el editor (lente sobre `grimoire`, comando y
atajo).

## Auditoría (estado real antes de este plan)

| # | Síntoma reportado | Causa encontrada | Arreglo |
|---|---|---|---|
| A | «no sé si el LSP funciona»; sin diagnósticos ni hover | La extensión solo manda `didOpen` en `onDidOpenTextDocument`, que **ya ocurrió** cuando la extensión se activa (la activación la dispara el propio archivo). El servidor nunca recibe el documento y responde vacío a todo. | Enviar `didOpen` de `vscode.workspace.textDocuments` tras `initialize`, además del evento. |
| B | Sin inlay hints, sin code lens | El cliente registra solo hover, completion, definition, documentSymbol y formatting; el servidor anuncia 14 capacidades más. | Registrar todos los providers del servidor. |
| C | Sin snippets | `completionItem.snippetSupport: false` y `package.json` sin `contributes.snippets`. | Activar snippets en el cliente + archivo de snippets del lenguaje. |
| D | `#{variable}` no se pinta dentro de la cadena | En la gramática, `#\{` es una región `meta.interpolation` **sin `contentName` ni `patterns`**; nada dentro se resalta. | Añadir `punctuation.definition.interpolation` y patrones embebidos (identificadores, números, operadores, llamadas). |
| E | No hay forma de ejecutar desde VS Code | El servidor manda code lens `pengu.runTest` pero el cliente ni registra el provider ni implementa el comando; no hay `pengu.run` ni atajos. | Comandos `pengu.run`/`pengu.test`, lentes sobre `grimoire` y `@@test`, atajos y tarea. |
| F | Sin autocompletado al importar la std | `features::completion` solo devuelve keywords + símbolos **del archivo**, y tras `.` devuelve **todas** las funciones del archivo. | Completion por contexto: módulos tras `summon`, miembros tras `mod::`, métodos según el tipo del receptor, snippets y orden. |
| G | Si `pengu` no está en el PATH, silencio | El fallo de `spawn` solo va a `console.log`. | Mensaje de error con acción («instala con scripts/install.sh o configura `pengu.serverPath`»), barra de estado y comando de reinicio. |
| H | — | `initialize` se envía sin esperar respuesta y `initialized` en un `.then`. | Cola de mensajes hasta `initialized`; versión y `didSave` consistentes. |

## Decisiones

- **D1** El cliente sigue sin dependencias (`node:vscode` + `node:child_process`),
  para que la extensión se pueda empaquetar sin `npm install`.
- **D2** El resaltado semántico usa la leyenda del servidor, replicada en el
  cliente como constante (el protocolo no permite pedirla después de `initialize`).
- **D3** Los snippets viven en `editors/vscode/snippets/pengu.json`
  (`contributes.snippets`); los snippets de completion del servidor se usan para
  imports de módulos y plantillas cortas.
- **D4** Ejecutar = `pengu run` en la raíz del proyecto (`Tome.toml`), en una
  terminal integrada reutilizada; probar = `pengu test`. Se guarda el documento
  antes de ejecutar.
- **D5** La lente de ejecución se pone sobre el bloque `grimoire` (programa) y
  sobre cada función `@@test`; la del servidor (`pengu.runTest`) se implementa en
  el cliente y se conserva como base para el futuro.
- **D6** Sin telemetría ni procesos residentes extra: un servidor por ventana.

## Fases

### E1 — Cliente que arranca de verdad
- `LspClient` con cola: los mensajes se envían cuando llega la respuesta de
  `initialize` y se manda `initialized`; promesa de arranque.
- `didOpen` de todos los documentos `pengu` ya abiertos; `didClose` correcto;
  versiones por URI sin resetear.
- Fallo de `spawn` (ENOENT) → `showErrorMessage` con botones «Instalar» (abre
  `docs/INSTALL.md`) y «Configurar ruta»; barra de estado con el estado del
  servidor; comando `pengu.restartServer`.
- Criterio: con VS Code abierto en un proyecto con `main.pengu`, aparecen
  diagnósticos sin tocar el archivo.

### E2 — Todos los providers
Hover, completion, definition, documentSymbol, formatting, **inlay hints**,
**code lens**, **semantic tokens** (full y range), references, document
highlight, prepare rename, rename, signature help, folding, selection ranges,
type definition, implementation, code actions, workspace symbols y call
hierarchy (prepare/incoming/outgoing).
Criterio: cada capacidad del servidor tiene su provider y responde; sin
excepciones en la consola.

### E3 — Autocompletado útil en el servidor
- Tras `summon ` → módulos (`std::libra`, `std::via`, …) y módulos del proyecto.
- Tras `summon std::` / `modulo::` → items del módulo con su firma.
- Tras `.` → métodos del tipo del receptor (resuelto con `check.types` en la
  posición; si no se puede, métodos del archivo como hasta ahora).
- Keywords y símbolos del archivo con `sortText` (locales primero) y `kind`.
- Snippets del servidor: `summon std::<mod>` con placeholders, `bind`, `match`,
  `for`, `grimoire`, `rune`, `ritual`, `@@test`.
- Criterio: tests de `features.rs` para módulo, miembro y método; y un cliente
  guionizado que reproduce la secuencia real de VS Code.

### E4 — Ejecutar y probar desde VS Code
- Comandos `pengu.run`, `pengu.test`, `pengu.check`, `pengu.restartServer`.
- Code lens: «▶ Ejecutar» sobre `grimoire`, «▶ Ejecutar prueba» sobre `@@test`.
- Atajos: `F5` (ejecutar), `Ctrl+F5` (probar), `Ctrl+Shift+B` (check).
- Terminal integrada reutilizada, `cwd` en la raíz del proyecto, guardado previo,
  y mensaje claro si no hay `Tome.toml`.
- Criterio: `F5` compila y muestra la salida del programa en la terminal.

### E5 — Snippets y gramática
- `snippets/pengu.json` con: programa completo, `rune`, `enchanting`, `pact`,
  `ritual`, `grimoire`, `summon`, `bind`, `morph`, `if/else`, `match`, `for`,
  `while`, `loop`, `@@test`, doc `---`, `--!`, interpolación, `curse`.
- Gramática: `#{…}` con `punctuation.definition.interpolation.pengu` y patrones
  internos (identificador, número, llamada, operador); tipos y keywords al día.
- `language-configuration.json`: comentarios de línea/bloque, corchetes,
  `indentationRules` reales y `onEnterRules` para bloques.
- Criterio: `#{total}` y `total` se pintan distinto dentro de la cadena.

### E6 — Verificación
- Tests de Rust para la completion nueva (módulo, miembro, método, snippets).
- `editors/e2e.mjs`: cliente que hace exactamente lo que la extensión
  (initialize → initialized → didOpen → inlayHint → completion `std::` →
  codeLens → hover) y falla si algo viene vacío.
- `node scripts/vsix.mjs --check`; `docs/EDITOR.md` con la tabla de lo que hace
  cada capacidad y cómo probarla a mano.
- Criterio: suite completa verde, `e2e.mjs` verde, `.vsix` válido.

## Seguimiento

| Fase | Estado |
|---|---|
| E0 auditoría | ✅ |
| E1 arranque del cliente | ✅ |
| E2 providers | ✅ |
| E3 completion del servidor | ✅ |
| E4 run/test | ✅ |
| E5 snippets y gramática | ✅ |
| E6 verificación | ✅ |

## E7 — el LSP no arrancaba en VS Code (2026-11-16)

Reporte del usuario: seguían sin aparecer hints, autocompletado ni tamaños, aun
con la gramática arreglada. Tres causas, las tres corregidas:

1. **La activación fallaba.** `editors/vscode/src/extension.js` hacía
   `require('node:vscode')`; `vscode` no es un builtin de Node, así que el
   módulo no se cargaba y `activate` nunca llegaba a ejecutarse. Sin activación
   no hay providers, ni barra de estado, ni servidor. Ahora es
   `require('vscode')` y `editors/check-extension.mjs` intercepta **solo**
   `vscode`, de modo que la prueba habría detectado el fallo.
2. **`pengu` no estaba en el PATH.** VS Code abierto desde el escritorio no
   hereda el `PATH` del shell. `resolveServer()` busca `pengu.serverPath`, el
   `PATH` del proceso, `~/.pengu/bin`, `~/pengu/bin`, `~/.local/bin`,
   `/usr/local/bin`, `target/{release,debug}` y `bin/` de la carpeta abierta, y
   como último recurso pregunta a una shell de login (`command -v pengu`). La
   ruta elegida se escribe en el canal de salida.
   Además `scripts/install.sh` ahora escribe el bloque del PATH en
   `~/.bash_profile`, `~/.profile`, `~/.bashrc`, `~/.zshrc` y `~/.zprofile`
   (antes solo en los que ya existieran, y `bash -lc` no veía nada).
3. **El autocompletado exigía que el archivo compilara.** Al escribir
   `summon ` o `summon std::` el documento tiene un error de sintaxis y no hay
   HIR, así que la lista salía vacía. `features::completion` cae ahora a
   `std_module_items()` (los 29 módulos de `std`, por nombre) cuando no hay
   `krate`, y también tras `std::`.

Pruebas añadidas: `completion_funciona_con_el_documento_a_medias`,
`completion_tras_std_dos_puntos_sin_hir` (Rust) y el caso de PATH mínimo en
`editors/check-extension.mjs` (`env -i PATH=/usr/bin:/bin … pengu`).
