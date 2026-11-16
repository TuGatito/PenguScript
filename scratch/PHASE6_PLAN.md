# Fase 6 — LSP base: plan de ejecución

> Estado: **en ejecución**. Al cerrar, la fase se marca ✅ en `scratch/TOOLING_PLAN.md`
> y el resumen queda en `scratch/STATUS.md`.

## 1. Objetivo y criterio de cierre

Servidor LSP por stdio, sin dependencias externas, que funcione en **Neovim,
LazyVim, Vim y VS Code** con:

- ciclo de vida completo (`initialize`/`initialized`/`shutdown`/`exit`);
- `textDocument/publishDiagnostics` con versión del documento;
- `textDocument/hover`, `completion`, `definition`, `documentSymbol`;
- `textDocument/formatting`;
- `pengu lsp`, logging y configuración;
- cliente de prueba y snapshots de protocolo.

Criterio de cierre: un proyecto real creado con `pengu new` muestra diagnósticos,
autocompletado, hover y navegación en VS Code **y** en Neovim/Vim, con un cliente
de prueba en CI que reproduce el flujo completo sin editores.

Requisitos transversales del usuario:

1. **Cero deuda técnica**: sin `TODO`s, sin caminos a medias, clippy `-D warnings`,
   todo cubierto por tests.
2. **Rápido**: protocolo LSP 3.17, sincronización **incremental**, negociación de
   codificación de posición, debounce, cancelación y caché.
3. **Archivos gigantes**: presupuestos medidos y tests de rendimiento.
4. **Base para la Fase 7**: índice de símbolos y arquitectura de análisis pensados
   para referencias, rename, tokens semánticos, jerarquía y cancelación.

## 2. Estado de partida

- Compilador **de un solo archivo**: `pengu-build` compila `main.pengu`/`lib.pengu`
  fusionando la stdlib. El "programa" del LSP es ese archivo raíz.
- No hay crate LSP ni dependencias externas: JSON y framing se escriben a mano.
- `pengu-vfs` ya aporta overlays, índice de líneas y hash de contenido, pero **no**
  aplica ediciones incrementales ni conoce la codificación UTF-16.
- `pengu-syntax::parse_program`, `pengu-hir::lower_program`,
  `pengu-types::check_crate`, `pengu-check::check_ownership` son las etapas usables.
- La stdlib se parsea hoy como **un único** `FileId`: no se puede navegar a ella
  con una URI real.

## 3. Arquitectura

### 3.1 Crates

| crate | papel |
|---|---|
| `pengu-lsp` (nuevo) | protocolo, documentos, análisis, features y formateo |
| `pengu-cli` | subcomando `pengu lsp` |
| `pengu-std` | fuentes de `std` con `FileId` propio y consultables |
| `pengu-vfs` | ediciones incrementales y conversión de posiciones |

### 3.2 Módulos de `pengu-lsp`

```
src/
  lib.rs          API pública (run, Server)
  json.rs         Value + parser + serializer (streaming sobre &str)
  framing.rs      Content-Length sobre Read/Write (binario, límite de tamaño)
  rpc.rs          envelopes, ids, errores JSON-RPC, $/cancelRequest
  uri.rs          file:// y pengu-std:// (parse/render sin dependencias)
  position.rs     UTF-8 ↔ UTF-16 ↔ (línea, columna), rangos
  docs.rs         DocumentStore: overlays, versión, ediciones, std virtual
  project.rs      descubrimiento de raíz, manifiesto, archivo raíz del programa
  analysis.rs     pipeline cacheado por (versión, hash) + índice de símbolos
  index.rs        símbolos, definiciones, tipos por span (base de Fase 7)
  features.rs     diagnostics, hover, completion, definition, documentSymbol
  format.rs       formateo conservador determinista
  server.rs       bucle de eventos, capacidades, despacho, cancelación
  log.rs          logging a stderr y a archivo
tests/
  protocol.rs     cliente in-process sobre UnixStream::pair
  snapshots/      respuestas normalizadas
```

### 3.3 Concurrencia y latencia

- **Un hilo lector** vuelca mensajes del framing a un canal.
- **Hilo principal**: despacho y análisis. `recv_timeout` implementa el debounce
  (120 ms) cuando hay documentos sucios; sin documentos sucios bloquea.
- Hover/completion/definition calculan el análisis bajo demanda si la versión del
  documento cambió; los diagnósticos siempre pasan por el debounce.
- Cancelación: `$/cancelRequest` para peticiones en vuelo y **versión** para
  diagnósticos (un resultado de una versión vieja se descarta).
- Sin locks compartidos ni `unsafe`: el estado vive en el hilo principal.

### 3.4 Posiciones y archivos gigantes

- Capacidad `positionEncoding`: se anuncia `["utf-8","utf-16"]`; si el cliente
  ofrece `utf-8` se usa (sin conversión), si no `utf-16` (por defecto del
  protocolo). La conversión UTF-16 maneja pares sustitutos.
- Sincronización **incremental** (`TextDocumentSyncKind::Incremental`) con
  `contentChanges[].range`; `range` ausente = reemplazo total (fallback).
- `DocumentStore` mantiene `Arc<str>` + índice de líneas y aplica rangos en O(n)
  sobre el texto resultante una vez por edición (sin rebuild por carácter).
- Índice de líneas diferencial: se reconstruye solo cuando cambia el número de
  líneas; si no, se ajusta.
- Caché de análisis por `(FileId, hash)`; la stdlib se parsea **una vez**.
- Límite de diagnósticos publicados (200) y de tamaño de mensaje (64 MiB).

### 3.5 Modelo de proyecto

1. `textDocument/didOpen` registra la URI y el texto (overlay).
2. La raíz se busca subiendo por `Tome.toml` desde el archivo.
3. Archivo raíz del programa: `[[bin]].path`/`main.pengu`, si no `[lib].path`/`lib.pengu`.
4. Si el documento abierto **es** el raíz, el análisis es el programa completo
   (con la stdlib fusionada); si no, se analiza como unidad independiente y se
   informa de que no pertenece al programa del proyecto (sin diagnósticos falsos).
5. Las fuentes de `std` se exponen como documentos de solo lectura con URI
   `pengu-std:///std/<módulo>.pengu`, mapeadas a sus `FileId`.

## 4. Decisiones (D1–D16)

- **D1** Crate `pengu-lsp` de librería + `pengu lsp` en la CLI; sin dependencias.
- **D2** JSON propio, sin `serde`: parser iterativo con profundidad limitada y
  serializer compacto; `Value` con número `i64`/`f64` y `id` acepta número o cadena.
- **D3** Framing `Content-Length` en bytes, cabeceras case-insensitive, límite de
  64 MiB y error de protocolo accionable.
- **D4** Modelo de hilos de §3.3 (lector + principal).
- **D5** Sincronización incremental; se anuncia `save: { includeText: false }` y
  `change: 2`.
- **D6** Codificación de posición negociada (§3.4).
- **D7** `pengu-std` expone `files()`, `file_id(i)` y parsea cada archivo con su
  propio `FileId`, envolviéndolos en un `scroll std` sintético. Esto da spans
  reales por archivo y habilita hover/definition hacia la stdlib.
- **D8** Un programa = archivo raíz del proyecto; documentos sueltos se analizan
  aislados (el compilador es de un archivo, no se finge un workspace multi-archivo).
- **D9** Diagnósticos desde parse + HIR + tipos + ownership, con `code`,
  `severity`, `relatedInformation` de labels y `source: "pengu"`.
- **D10** Hover: firma + tipo inferido + origen (módulo de std o archivo), en
  Markdown; si no hay tipo, se omite el bloque en vez de inventarlo.
- **D11** Completion: palabras clave, items del ámbito (funciones, tipos, runes,
  pacts, rituales, constantes) y nombres de la stdlib; `sortText` por cercanía.
- **D12** Definition: `Res::Def` de las resoluciones HIR → `Location`; soporta
  URIs `pengu-std://` y devuelve `null` si el span es sintético.
- **D13** DocumentSymbol jerárquico desde el AST (`scroll`, `rune`, `pact`,
  `ritual`, funciones, constantes), con `range` y `selectionRange`.
- **D14** Formateo **conservador** en Fase 6: tabs→4 espacios, espacios finales,
  líneas en blanco consecutivas (máx. 2) y newline final. El formateador completo
  es de la Fase 8 (`pengu fmt`); se documenta para no prometer de más.
- **D15** Robustez: método desconocido → `MethodNotFound`; notificación antes de
  `initialize` → se ignora; `shutdown` idempotente; `exit` con 0 solo si hubo
  `shutdown`; errores internos → `InternalError` sin tumbar el servidor.
- **D16** Presupuestos: didOpen→diagnósticos ≤ 400 ms para 5 000 líneas y ≤ 2 s
  para 20 000; hover con análisis cacheado ≤ 100 ms; memoria O(texto abierto).

## 5. Fases de ejecución

### L0 — Núcleo de protocolo
`json.rs`, `framing.rs`, `rpc.rs`, `uri.rs`, `position.rs`, esqueleto de
`server.rs` y `pengu lsp`. Tests unitarios de JSON (escapes, unicode, anidamiento,
números), framing (partido en trozos, mayúsculas, límite) y ciclo de vida.

**Aceptación:** un cliente puede hacer `initialize` → `initialized` →
`shutdown` → `exit` y recibe capacidades correctas.

### L1 — Documentos, sincronización y std virtual
`pengu-vfs`: `apply_change(range, text)`, `offset_at(line, col, encoding)`,
`position_at(offset, encoding)`. Refactor de `pengu-std` (D7). `docs.rs` con
overlays, versiones y URIs de std.

**Aceptación:** `didOpen`/`didChange` incrementales producen el texto esperado,
incluido un cambio en mitad de un carácter multibyte; `pengu-std://` resuelve.

### L2 — Análisis, diagnósticos e índice
`analysis.rs` (pipeline y caché), `index.rs` (símbolos y tipos), publicación de
diagnósticos con debounce/cancelación y `source`/`code`/`relatedInformation`.

**Aceptación:** un error de sintaxis y otro de tipos se publican con rango exacto
y `version`; al corregir, la lista queda vacía; un archivo de 20 000 líneas entra
en presupuesto.

### L3 — Hover, completion, definition, documentSymbol
`features.rs` + `index.rs`. Tests de protocolo con snapshots.

**Aceptación:** hover sobre una llamada muestra firma y tipo; completion incluye
items locales y de `std`; definition salta a la función, al campo y a `std`;
documentSymbol devuelve el árbol.

### L4 — Formateo
`format.rs` (D14) con idempotencia y respeto de comentarios/cadenas.

**Aceptación:** formatear dos veces da lo mismo; no toca el interior de cadenas
ni comentarios; devuelve un único `TextEdit` que cubre el documento.

### L5 — Editores
`editors/vscode/` (extensión mínima con `package.json` + `extension.js` + gramática
TextMate básica), `editors/nvim/` (`lua/pengu.lua` con `vim.lsp.start` y variante
LazyVim), `editors/vim/` (vim-lsp y `:h lsp` no existe: instrucciones claras) y
`editors/README.md` con los cuatro flujos y diagnóstico de problemas.

**Aceptación:** instrucciones reproducibles y `pengu lsp` responde a `initialize`
desde una configuración copiada tal cual.

### L6 — Protocolo, snapshots y rendimiento
`tests/protocol.rs` con `UnixStream::pair` y un cliente que habla el protocolo
real; snapshots en `tests/snapshots/`; test de archivo gigante con presupuestos;
test de cancelación y de versión obsoleta.

**Aceptación:** suite de protocolo verde, sin `#[ignore]`.

### L7 — Cierre
Documentación: `docs/LSP.md` (uso, capacidades, límites, integración),
`scratch/STATUS.md`, `scratch/TOOLING_PLAN.md` (Fase 6 ✅), este plan (tabla de
estado). `cargo fmt`, `clippy -D warnings`, suite completa y commit.

## 6. Matriz de paridad con otros servidores

| capacidad | rust-analyzer | clangd | pyright | pengu (Fase 6) |
|---|---|---|---|---|
| diagnósticos push | ✅ | ✅ | ✅ | ✅ |
| hover | ✅ | ✅ | ✅ | ✅ |
| completion | ✅ | ✅ | ✅ | ✅ (sin resolver import) |
| definition | ✅ | ✅ | ✅ | ✅ (archivo + std) |
| documentSymbol | ✅ | ✅ | ✅ | ✅ |
| formatting | ✅ | ✅ | ✅ | ✅ conservador |
| incremental sync | ✅ | ✅ | ✅ | ✅ |
| cancelación | ✅ | ✅ | ✅ | ✅ |
| std navegable | ✅ | ✅ | ✅ | ✅ vía `pengu-std://` |
| references/rename/tokens | ✅ | ✅ | ✅ | Fase 7 |

## 7. Riesgos y mitigación

| riesgo | mitigación |
|---|---|
| JSON a mano con bugs sutiles | parser con pruebas de casos raros y límite de profundidad |
| posiciones UTF-16 mal convertidas | tabla de pruebas con emoji y acentos; negociación a utf-8 |
| análisis lento en archivos grandes | caché por hash, std parseada una vez, debounce y presupuestos en CI |
| spans de std inexistentes | D7: un `FileId` por archivo de `std` |
| competir con el compilador de un solo archivo | D8: se documenta el modelo, no se simula un workspace |
| deuda por formateo parcial | D14 explícito + Fase 8 dueña del formateador completo |

## 8. Tabla de seguimiento

| fase | estado | evidencia |
|---|---|---|
| L0 | ✅ | JSON, framing, RPC, URI, posiciones y ciclo de vida (`5b1b6b1`). |
| L1 | ✅ | `docs.rs`, `project.rs`, `analysis.rs`, `diag.rs`; std con `FileId` por archivo (`5b1b6b1`). |
| L2 | ✅ | `publishDiagnostics` con debounce, versiones y cambios incrementales (`5b1b6b1`). |
| L3 | ✅ | hover, definition, completion y documentSymbol con índice del HIR (`5b1b6b1`). |
| L4 | ✅ | formato conservador e idempotente (`5b1b6b1`). |
| L5 | ✅ | VS Code (cliente JS sin dependencias), Neovim/LazyVim, Vim y gramática TextMate. |
| L6 | ✅ | protocolo real, cancelación (`$/cancelRequest`), CST y parser JSON lineales, límite de 200 000 líneas y `editors/bench.mjs`. |
| L7 | ✅ | `docs/LSP.md`, `editors/README.md`, tabla cerrada y suite completa en verde. |
