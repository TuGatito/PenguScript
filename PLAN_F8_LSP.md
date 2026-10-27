# PLAN F8 — LSP nativo de PenguScript

> **Estado:** propuesta para aprobación. No implementado todavía.
> **Base:** F7 cerrada (fmt/doc/assets/watch/benchmark, `std.jsonrpc`,
> `std.io`, `std.filum`, F3/F4 estables y bootstrap en punto fijo).
> **Objetivo:** `psc lsp --stdio` nativo, sin Python, compatible con la extensión
> de VS Code y con paridad funcional con `pengu_lsp` (stage0).

---

## 1. Resumen ejecutivo

Hoy el LSP vive en Python (`pengu_lsp/`, pygls) y `psc lsp` es un stub que
responde “F8”. F8 reemplaza ese servidor por uno escrito en PSC sobre el core
del compilador:

```text
stdin bytes ──▶ framing Content-Length ──▶ JSON-RPC
                                             │
                                             ├── lifecycle
                                             ├── documentos (URI/texto/versión)
                                             ├── parse + sema + diagnósticos
                                             ├── índices de símbolos
                                             └── features LSP
                                             │
stdout bytes ◀── framing Content-Length ◀────┘
```

El servidor debe funcionar **sin Python instalado** y sin `pengu_lsp` en el
camino de producción. El LSP Python queda congelado como **oráculo dev-only**
hasta F11.

**Fuera de F8:** dependencias/package manager (F9), `bind` (F10), cross/WASM y
switchover final (F11). No se toca el runtime ni el ABI.

---

## 2. Estado actual (F7) y piezas disponibles

| Pieza | Estado |
|---|---|
| `psc lsp` | stub explícito F8 (`cmd_stubs.run_lsp`) |
| `pengu_lsp/` | servidor pygls completo: diagnósticos, completion, hover, definition, implementation, references, highlight, symbols, folding, semantic tokens, inlay hints, code lens, actions, rename, formatting, on-type, signature help |
| `std.jsonrpc` | JSON-RPC 2.0, framing `Content-Length`, `encode_framed`, `decode_framed_bytes`, errores, batches |
| `std.io` | lectura exacta/línea de stdin, escritura/flush de stdout |
| `std.filum` | canales, mutex, cond, atómicos, sleep; no hay `spawn` de goroutine en std (ver D5) |
| F3 | `SemaProgram`, `SemaSymbols`, tipos, diagnósticos, scopes, módulos |
| F4/F5 | bundle/codegen/driver estables |
| F7 | `fmt` paritario reutilizable para formatting/on-type |
| VS Code | extensión `vscode-extension/` y `.vsix`; hoy habla con el LSP Python |

### Deuda/bloqueo detectado en F3 para F8

Los símbolos tienen `line`, `col`, `doc` y `module`, pero en la práctica el
campo `module` no quedó poblado de forma fiable durante la recolección
(observado al intentar agrupar símbolos por módulo en F7). F8.0 debe:

1. Asignar `module` al declarar (o resolver el módulo por scope/URI).
2. Verificar `line`/`col` 1-indexed y `doc` en declaraciones top-level.
3. Añadir tests que fallen si un símbolo de proyecto queda sin dueño/posición.

Sin esto, `documentSymbol`, `workspaceSymbol`, `definition`, `references` y
`rename` no pueden ser correctos en proyectos multi-módulo.

---

## 3. Decisiones

### D1 — Servidor nativo PSC

- ✅ **Recomendado:** implementar el servidor en `psc/src/psc/lsp/**` y
  conectar `psc lsp`. Sin Python en producción.
- ⚠️ Alternativa: empaquetar pygls. Rompe el objetivo de auto-hospedaje.

### D2 — Transporte

- ✅ **Recomendado:** `--stdio` primero, con `Content-Length` y UTF-8, usando
  `std.jsonrpc` + `std.io`. `--tcp` queda documentado como opción posterior.
- ⚠️ Alternativa: TCP en F8. Añade seguridad/ciclo de vida y no lo pide VS Code.

### D3 — Sincronización de documentos

- ✅ **Recomendado:** `TextDocumentSyncKind.Full` en F8.0–F8.3; incremental
  (`Incremental`) sólo si las mediciones lo exigen y hay tests de rangos.
- ⚠️ Alternativa: incremental desde el inicio. Más riesgo de corrupción.

### D4 — Codificación de posiciones

- ✅ **Recomendado:** **UTF-16** (default LSP), conversion centralizada
  `byte offset ↔ (line, character UTF-16)`. Aceptar `positionEncoding` UTF-8
  sólo si el cliente lo pide y se implementa explícitamente.
- ⚠️ Alternativa: UTF-8 interno. Rompe clientes que cuentan UTF-16.

### D5 — Concurrencia

- ✅ **Recomendado:** bucle de lectura síncrono + **debounce** de validación
  (350 ms) y caches por hash. Si un proyecto de 100 módulos bloquea >50 ms, se
  añade un worker con `std.filum` y cola, sin cambiar el protocolo.
- ⚠️ Alternativa: worker desde el día 1. Más complejo y sin datos de latencia.

### D6 — Alcance de features

- ✅ **Recomendado:** paridad funcional con `pengu_lsp` en:
  lifecycle, diagnósticos, completion, hover, signature help, definition,
  implementation, references, document highlight, document/workspace symbols,
  folding, semantic tokens, inlay hints, code lens, code actions, rename,
  formatting, on-type formatting.
- ⚠️ Alternativa: sólo diagnósticos/completion/hover en F8.0 y resto F8.1.
  Es el mismo plan por fases; no se recorta el objetivo final.

### D7 — Diagnósticos

- ✅ **Recomendado:** parse+check con `SemaProgram`, publicar
  `textDocument/publishDiagnostics` con `version`, severidad, código, fuente
  `psc`, `relatedInformation`; recuperación ante errores; UTF-16; debounce;
  no publicar si el contenido no cambió (hash).
- ⚠️ Alternativa: publicar en cada keystroke. Ruido y CPU.

### D8 — Índices y caches

- ✅ **Recomendado:** cache por URI (texto, versión, hash, diagnósticos,
  símbolos) + grafo de imports + invalidación de dependientes. Índice de
  workspace por módulo.
- ⚠️ Alternativa: reparsear todo en cada request. No escala a 100 módulos.

### D9 — URI y paths

- ✅ **Recomendado:** módulo `lsp/uri.pengu`:
  - `file://` con percent-decoding;
  - Windows `C:\...` ↔ `file:///C:/...`;
  - espacios/Unicode;
  - normalización de `.`/`..` y separadores;
  - `uriToPath`/`pathToUri` probados en Linux y Windows.
- ⚠️ Alternativa: asumir paths POSIX. Rompe Windows.

### D10 — Errores y ciclo de vida

- ✅ **Recomendado:** `initialize` → `initialized` → requests/notifications →
  `shutdown` → `exit` (0 si hubo shutdown, 1 si no). Errores JSON-RPC estándar;
  métodos desconocidos `-32601`; params inválidos `-32602`; sin logs en stdout.
- ⚠️ Alternativa: cerrar ante cualquier error. Mala UX.

### D11 — Reutilizar F7 para formatting

- ✅ **Recomendado:** el formatter/on-type llama al módulo de F7
  (`psc/src/psc/cmd/fmt.pengu` o su lógica extraída), no al proceso `psc fmt`.
- ⚠️ Alternativa: subprocess `psc fmt`. Latencia y dependencia circular.

### D12 — Python LSP como oráculo

- ✅ **Recomendado:** `pengu_lsp` se mantiene congelado como **stage0/oráculo
  dev-only** para tests de paridad; no se elimina hasta F11.
- ⚠️ Alternativa: borrarlo ahora. Perdemos referencia y tests.

### D13 — Windows/macOS

- ✅ **Recomendado:** transporte/paths/UTF-16 portables; CI Linux obligatorio y
  job Windows/macOS no bloqueante en F8.0, bloqueante antes de F11.
- ⚠️ Alternativa: sólo Linux. La extensión es multiplataforma.

### D14 — Sin cambios de runtime/ABI

- ✅ **Recomendado:** F8 usa `std.io`, `std.jsonrpc`, `std.filum`, F3/F4/F7.
  Si falta una primitiva, se añade en `std` sin tocar `pengu_runtime.h`.
- ⚠️ Alternativa: tocar el runtime para threads. No hace falta para F8.0.

---

## 4. Arquitectura

```text
psc/src/psc/lsp/
  main.pengu          # bucle, lifecycle, shutdown/exit
  transport.pengu     # read frame, write frame, flush, EOF
  rpc.pengu           # dispatch, ids, cancel, errores (std.jsonrpc)
  session.pengu       # initialize/capabilities, workspaceFolders
  documents.pengu     # URI -> texto/versión/hash; didOpen|Change|Save|Close
  uri.pengu           # file:// <-> path, percent-encoding
  positions.pengu     # byte <-> line/UTF-16
  diagnostics.pengu   # parse+check, publish, debounce
  index.pengu         # símbolos por módulo/workspace, imports, invalidación
  features/
    completion.pengu
    hover.pengu
    signature.pengu
    definition.pengu
    implementation.pengu
    references.pengu
    highlight.pengu
    symbols.pengu
    folding.pengu
    semantic.pengu
    inlay.pengu
    lens.pengu
    actions.pengu
    rename.pengu
    formatting.pengu
    on_type.pengu
psc/src/psc/cmd/lsp.pengu   # CLI fino
psc/src/main.pengu          # dispatch "lsp" -> cmd_lsp
psc/tests/lsp_client.py     # cliente de cable dev-only
tests/psc/test_f8_*.py
tests/golden/f8/**
```

`psc lsp [--stdio] [--log=stderr|file]`; `--tcp` reservado.

---

## 5. Transporte y protocolo

### 5.1 Framing

- Leer headers hasta `\r\n\r\n` con `std.io.read_stdin_line` /
  `read_stdin_exact`.
- Parsear `Content-Length` (bytes, no caracteres).
- Leer exactamente el body; decodificar UTF-8.
- `std.jsonrpc.decode_framed_bytes` para validar; `encode_framed` para
  responder.
- Escribir `Content-Length: N\r\n\r\n<body>` + `flush_stdout` después de cada
  mensaje.
- Nunca escribir logs en stdout; stderr o archivo `--log`.

### 5.2 Mensajes

- Requests: `initialize`, `shutdown`, `textDocument/*`, `workspace/*`.
- Notifications: `initialized`, `exit`, `didOpen/Change/Save/Close`,
  `didChangeConfiguration`, `didChangeWatchedFiles`, `$/cancelRequest`.
- Responses: result/error; batches opcionales.
- Ids number/string; map de requests en vuelo; `$/cancelRequest` responde
  `RequestCancelled` (-32800) si aún no empezó.

### 5.3 Capacidades mínimas (`initialize.result.capabilities`)

```text
textDocumentSync: Full
completionProvider: { triggerCharacters: [".", ":", "@"] }
hoverProvider: true
signatureHelpProvider: { triggerCharacters: ["(", ","] }
definitionProvider: true
implementationProvider: true
referencesProvider: true
documentHighlightProvider: true
documentSymbolProvider: true
workspaceSymbolProvider: true
codeActionProvider: true
renameProvider: { prepareProvider: true }
documentFormattingProvider: true
documentOnTypeFormattingProvider: { firstTriggerCharacter: ":" }
foldingRangeProvider: true
semanticTokensProvider: { legend, full: true }
inlayHintProvider: true
codeLensProvider: { resolveProvider: false }
```

`serverInfo: { name: "psc", version: "0.8.0 (F8)" }`;
`positionEncoding: "utf-16"`.

---

## 6. Lifecycle y documentos

- `initialize`: guardar `rootUri`, `workspaceFolders`, `capabilities`,
  `positionEncoding`; responder.
- `initialized`: construir índice inicial (lazy si es grande).
- `textDocument/didOpen`: guardar texto/versión; validar y publicar.
- `didChange`: full sync; reemplazar texto; invalidar cache; debounce.
- `didSave`: revalidar; opcional `includeText`.
- `didClose`: borrar documento y diagnósticos (`[]`).
- `didChangeConfiguration`: settings `pengus.*` (runtime/std, lint).
- `didChangeWatchedFiles`: invalidar URIs del grafo.
- `shutdown`: responder null, marcar shutdown.
- `exit`: salir 0 si shutdown previo; 1 si no.

---

## 7. Diagnósticos

- Parse+check con `SemaProgram` sobre el entry del documento/proyecto.
- Convertir `Diagnostic` (línea/col byte) a UTF-16.
- Campos: `range`, `severity` (Error/Warning/Info/Hint), `code`, `source:
  "psc"`, `message`, `relatedInformation`, `tags` (unnecessary/deprecated).
- Publicar `publishDiagnostics` con `version` y `uri`.
- Debounce 350 ms por URI; generación monotónica para descartar validaciones
  viejas.
- Cancelar/ignorar si el documento cambió.
- Recuperación: publicar errores de parseo y seguir sirviendo features.
- No publicar si hash + configuración no cambió.

---

## 8. Índice de símbolos

- Por módulo: `path`, `uri`, `hash`, `version`, `SemaProgram`, símbolos
  (nombre, tipo, kind, línea/col, doc), imports.
- Workspace: `module -> symbols`; `name -> [symbols]` para workspaceSymbol.
- Invalidación: cambio de archivo -> revalidar ese módulo + dependientes
  (grafo inverso).
- Resolución:
  - local (scope del nodo);
  - global del módulo;
  - import alias/`import std.x`;
  - campos/métodos por tipo.
- **F8.0:** corregir `SemaSymbol.module`/`line`/`col` o construir el índice por
  scopes; tests de multi-módulo.

---

## 9. Features

### 9.1 Completion

- Keywords, tipos builtin, símbolos locales/globales, imports, campos, métodos,
  valores de `omen`, snippets (`weave`, `rune`, `match`).
- Contexto: tras `.` sólo miembros; tras `import` módulos; en tipo, tipos.
- `CompletionItem`: label, kind, detail (firma), documentation, insertText,
  sortText, filterText, textEdit.
- Trigger characters; no bloquear.

### 9.2 Hover

- Tipo inferido, firma, doc, deprecación, valor de constante.
- Rango del identificador; Markdown; UTF-16.
- Fallback: palabra bajo cursor sin símbolo -> nada.

### 9.3 Signature help

- Detectar llamada `calling f with` y argumento activo; parámetros, tipos,
  defaults, variádicos; activeParameter; overloads (si hay).

### 9.4 Definition / implementation

- Local, global, import, campo, método, tipo nominal.
- `Location` con URI/range; múltiples para overloads.
- Implementation: métodos de concepto/seal y variantes de omen.

### 9.5 References / highlight

- Todas las ocurrencias del símbolo en workspace; excluir declaración según
  `includeDeclaration`.
- Highlight: read/write en documento actual; mismo rango.

### 9.6 Document / workspace symbols

- Jerarquía: módulo -> runas/echo/omen/alias/seal/concept -> métodos/campos;
  funciones/constantes/tests.
- `DocumentSymbol` con range/selectionRange/kind/children.
- Workspace: consulta por prefijo/fuzzy; límite configurable.

### 9.7 Folding

- Bloques por indentación, triples, comentarios `##`, `antiquus`, imports.
- `FoldingRange` con kind comment/region/imports.

### 9.8 Semantic tokens

- Legend: namespace, type, class, enum, interface, struct, typeParameter,
  parameter, variable, property, function, method, macro, keyword, string,
  number, comment, operator.
- Lexer + sema; delta/full; UTF-16; multi-line tokens.

### 9.9 Inlay hints

- Tipos inferidos en `var`/`let` sin anotación; nombres de parámetros en
  llamadas; rangos UTF-16; configurable.

### 9.10 Code lens

- `test` -> “Run test”; `main` -> “Run”; comandos `pengus.runTest` /
  `pengus.run`; resolver opcional.

### 9.11 Code actions

- Quick fixes de diagnósticos (import faltante, typo, mutabilidad).
- “Format document” (delegado a F7).
- Refactors básicos (extraer? fuera de F8 si no hay AST rewrite seguro).

### 9.12 Rename / prepareRename

- Validar identificador; no renombrar keywords/builtins sin confirmación.
- WorkspaceEdit con cambios por URI; preservar UTF-16.
- `prepareRename` devuelve range+placeholder.

### 9.13 Formatting / on-type

- Llamar al formatter F7; devolver un `TextEdit` de documento completo (o
  mínimo si es estable).
- On-type: `:` + newline -> indentar; `}`/`end` -> dedent; respetar
  `.pengufmt.toml`.
- `fmt` ya es paritario; no duplicar lógica.

---

## 10. UTF-16 y URIs

- `positions.pengu`: línea 0-indexed, character en **code units UTF-16**;
  manejar pares surrogados (emoji), `ñ`, CJK.
- `uri.pengu`: `file://`, percent-encoding, Windows drive, UNC, espacios.
- Tests dedicados con:
  - `ñ` (1 unit), `漢` (1), `😀` (2), combinaciones;
  - `C:\Users\...`, `file:///C:/...`, `%20`.
- Toda conversión pasa por estos módulos; prohibido indexar strings por bytes
  para posiciones LSP.

---

## 11. Rendimiento y concurrencia

- Medir:
  - initialize + índice de 100 módulos;
  - didChange -> diagnósticos (p50/p95);
  - completion/hover (p95);
  - 1 000 didChange sin leaks.
- Objetivo: didChange p95 < 150 ms en 100 módulos; completion < 50 ms.
- Si no se cumple: worker `std.filum` con cola, cancelación por generación.
- Caches: texto, hash, programa sema, diagnósticos, símbolos por URI,
  índice workspace, formatter.
- Sin allocations por mensaje innecesarias; liberar cada `JsonRpcMessage`.

---

## 12. Tests

### 12.1 Cliente de cable dev-only

`psc/tests/lsp_client.py` (Python, sólo tests):

- lanza `psc lsp --stdio`;
- escribe/lee frames `Content-Length`;
- helpers `initialize`, `didOpen`, `request`, `notify`, `shutdown`;
- timeouts y stderr.

### 12.2 Suites

- `test_f8_lifecycle.py`: initialize/initialized/shutdown/exit, métodos
  desconocidos, params inválidos, exit codes.
- `test_f8_transport.py`: frames parciales, headers extra, UTF-8, EOF, batches.
- `test_f8_diagnostics.py`: errores/warnings, códigos, versiones, debounce,
  didChange/didClose.
- `test_f8_completion.py`: keywords, locales, imports, `.` miembros, snippets.
- `test_f8_hover.py`: tipos, firmas, docs, deprecación.
- `test_f8_navigation.py`: definition, implementation, references, highlight.
- `test_f8_symbols.py`: document/workspace symbols, folding.
- `test_f8_semantic.py`: tokens, inlay hints, code lens.
- `test_f8_actions.py`: code actions, prepareRename/rename, formatting/on-type.
- `test_f8_utf16.py`: ñ/CJK/emoji, rangos.
- `test_f8_uri.py`: POSIX/Windows/percent encoding.
- `test_f8_stress.py`: 1 000 didChange, ASan/UBSan; 100 módulos.

### 12.3 VS Code

- Configurar `pengus.executablePath` a `psc`.
- Smoke manual: abrir proyecto, diagnósticos, completion, hover, definition,
  rename, format.
- CI: job no bloqueante con `@vscode/test-electron` si el runner lo permite;
  si no, documento de smoke y tests de protocolo.

### 12.4 Paridad con Python

- `pengu_lsp` como oráculo dev-only para un corpus de fixtures:
  comparar diagnósticos (código/línea/columna), hover, definition,
  completion (subset), symbols.
- Normalizar orden/IDs; goldens en `tests/golden/f8/`.
- No se ejecuta Python en producción.

---

## 13. Fases y estimación

| Fase | Contenido | Semanas |
|---|---|---:|
| F8.0 | Símbolos F3 (module/line/col), transporte, lifecycle, URI/UTF-16, cliente de cable | 2 |
| F8.1 | Documentos, diagnósticos, debounce, caches | 1.5 |
| F8.2 | Definition, references, highlight, document/workspace symbols, folding | 2 |
| F8.3 | Completion, hover, signature help, implementation | 2 |
| F8.4 | Semantic tokens, inlay hints, code lens | 1.5 |
| F8.5 | Code actions, rename/prepareRename, formatting/on-type | 2 |
| F8.6 | VS Code, paridad Python, stress/ASan, rendimiento | 1.5 |
| F8.7 | Docs, CI, cierre | 1 |
| **Total** | | **13–14** |

Timebox: 12–14 semanas. Si la concurrencia/rendimiento no llega, F8.5 añade
worker thread; no se recorta el conjunto de features.

---

## 14. Criterios de aceptación

1. `psc lsp --stdio` funciona sin Python.
2. VS Code abre un proyecto, recibe diagnósticos y usa completion/hover/
   definition/references/symbols/rename/format.
3. `initialize` anuncia las capacidades de §5.3; `shutdown`/`exit` correctos.
4. Diagnósticos con severidad/código/versión y debounce.
5. Posiciones UTF-16 correctas con `ñ`, CJK y emoji.
6. URIs `file://` POSIX/Windows/percent-encoding correctas.
7. 1 000 didChange sin fugas y sin bloquear el bucle.
8. Proyecto de 100 módulos: didChange p95 < 150 ms.
9. `documentSymbol`/`workspaceSymbol` correctos en multi-módulo.
10. Paridad funcional con `pengu_lsp` en el corpus F8.
11. Tests de cable/CI/ASan verdes; F1–F7 y bootstrap siguen verdes.
12. Sin cambios de runtime/ABI; sin Python en producción.
13. Docs, CHANGELOG y `psc lsp --help`.
14. Commit final en `main`, sin push.

---

## 15. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Símbolos F3 sin módulo/posición | Alta | Alto | F8.0 los corrige y testea |
| UTF-16 mal convertido | Alta | Alto | módulo único + tests emoji/CJK |
| Bloqueo por sema | Media | Alto | debounce, caches, worker si p95 falla |
| Windows paths/URIs | Media | Medio | tests dedicados, CI Windows |
| Paridad pygls incompleta | Media | Medio | oráculo + matriz de features |
| stdout contaminado | Media | Alto | logs sólo stderr; tests de framing |
| Memoria en didChange | Media | Alto | ASan 1 000 ciclos, ownership |
| Scope creep a F9/F10 | Alta | Alto | stubs y fuera de alcance |
| VS Code CI inestable | Media | Bajo | protocolo como gate; smoke manual |

---

## 16. Fuera de alcance

- Dependencias/package manager (F9).
- `bind` (F10).
- Cross/WASM/MSVC/switchover (F11).
- Refactors que reescriban AST (extraer función, mover símbolo) más allá de
  quick fixes seguros.
- Debug Adapter Protocol (DAP).
- Notebooks, inlay hints experimentales, LSP 3.18.

---

## 17. Preguntas para aprobar

1. ¿Aprobado el servidor nativo PSC sin Python (D1)?
2. ¿Aprobado `--stdio` primero y full-sync inicial (D2/D3)?
3. ¿Aprobado UTF-16 y módulos URI/positions dedicados (D4/D9)?
4. ¿Aprobado el conjunto completo de features de §9 (D6)?
5. ¿Aprobado el plan de diagnósticos/debounce/caches (D7/D8)?
6. ¿Aprobado corregir primero `SemaSymbol.module/line/col` (F8.0)?
7. ¿Aprobado mantener `pengu_lsp` como oráculo dev-only (D12)?
8. ¿Aprobado el presupuesto 10–14 semanas y el worker sólo si la latencia lo
   exige (D5)?

Si se aprueba, empiezo por **F8.0**: símbolos F3, transporte, lifecycle,
URI/UTF-16 y cliente de cable; después diagnósticos y navegación.
