# Servidor LSP de PenguScript

`pengu lsp` es un servidor **LSP 3.17 sobre stdio**, sin dependencias externas,
pensado para usarse desde VS Code, Neovim, LazyVim y Vim. Esta página describe
qué ofrece, cómo conectarlo y qué límites tiene.

## Arranque

```sh
pengu lsp                 # habla JSON-RPC por stdin/stdout
pengu lsp --log=/tmp/lsp.log   # opcional: log a archivo (PENGU_LSP_LOG)
```

El binario se compila con el resto del proyecto (`cargo build -p pengu-cli`).

## Capacidades

| Método | Estado | Notas |
| --- | --- | --- |
| `initialize` / `initialized` / `shutdown` / `exit` | ✅ | Negocia `positionEncoding` (`utf-8` si el cliente lo ofrece; si no `utf-16`). |
| `textDocument/publishDiagnostics` | ✅ | Léxicos, sintácticos, de tipos y de ownership, con `source = "pengu"`. |
| `textDocument/didOpen` / `didChange` / `didSave` / `didClose` | ✅ | Sincronización **incremental** (`change: 2`); también acepta reemplazos completos. |
| `textDocument/hover` | ✅ | Firma de la definición o tipo de la expresión; markdown con bloque `pengu`. |
| `textDocument/definition` | ✅ | Incluye navegación a la stdlib (documentos virtuales `pengu-std:`). |
| `textDocument/completion` | ✅ | Keywords, símbolos del archivo y métodos tras `.`. |
| `textDocument/documentSymbol` | ✅ | Funciones, tipos, constantes, módulos y variantes. |
| `textDocument/formatting` | ✅ | Formato conservador (ver abajo). |
| `$/cancelRequest` | ✅ | Cancela peticiones aún no procesadas (`-32800`). |
| `textDocument/references` | ✅ | Apariciones por nombre en el archivo (declaración opcional). |
| `textDocument/documentHighlight` | ✅ | Resaltado de todas las apariciones. |
| `textDocument/prepareRename` / `rename` | ✅ | `WorkspaceEdit`; la stdlib es de solo lectura. |
| `textDocument/semanticTokens/full` y `/range` | ✅ | Leyenda de 9 tipos y 2 modificadores. |
| `textDocument/inlayHint` | ✅ | `: Tipo · N B` en locales sin anotación. |
| `textDocument/signatureHelp` | ✅ | Firma de la llamada y parámetro activo. |
| `textDocument/codeLens` | ✅ | `@@test` → `pengu.runTest`. |
| `textDocument/foldingRange` | ✅ | Bloques por indentación y comentarios. |
| `textDocument/selectionRange` | ✅ | Línea y bloque contenedor. |
| `textDocument/typeDefinition` | ✅ | Expresión → definición de su ADT. |
| `textDocument/implementation` | ✅ | Pacto → sus `ritual … for`. |
| `textDocument/codeAction` | ✅ | Quickfix: campo privado → `unveil`. |
| `workspace/symbol` | ✅ | Símbolos de los documentos abiertos. |
| `callHierarchy/*` | ✅ | `prepare`, `incomingCalls` y `outgoingCalls` por nombre en el archivo. |
| `textDocument/documentLink` | ❌ | Descartado: los módulos no son archivos (ver `scratch/PHASE7_PLAN.md` A2). |

## Modelo de proyecto

- La raíz se descubre subiendo desde el documento hasta encontrar `Tome.toml`;
  si no hay manifiesto, se usa el primer directorio con `main.pengu` o
  `lib.pengu`.
- El **programa es un archivo** (`main.pengu` o `lib.pengu`), igual que en el
  compilador: los módulos son `scroll` internos y la stdlib se fusiona siempre.
- Los archivos de `std/*.pengu` se abren como documentos de solo lectura con
  URIs `pengu-std:/<módulo>.pengu`, de modo que "ir a la definición" funciona
  también dentro de la biblioteca estándar.

## Rendimiento

- Análisis perezoso por documento con caché por **hash de contenido**: un
  `didChange` solo reanaliza si el texto cambió.
- Los diagnósticos se agrupan con un *debounce* de 120 ms, así que ráfagas de
  cambios producen una sola publicación.
- La construcción del CST es lineal (una sola pasada de tokens), el parser JSON
  valida en una pasada y el índice se arma con las definiciones ya resueltas del
  HIR.
- Presupuesto medido con `editors/bench.mjs` en `--release` (un `didOpen` incluye
  análisis completo y publicación de diagnósticos):

  | Líneas | `didOpen` | `didChange` + `documentSymbol` |
  |--------|-----------|-------------------------------|
  | 2 004 | 219 ms | 73 ms |
  | 6 004 | 507 ms | 347 ms |
  | 14 004 | 514 ms | 442 ms |
  | 40 004 | 1 807 ms | 2 129 ms |

  El análisis (`pengu-lsp::analysis::analyze`) de 14 004 líneas tarda ~380 ms en
  release; el resto es serialización. En `debug` los mismos casos tardan ~2 s.
- Los archivos por encima de 10 MiB o 200 000 líneas se rechazan con
  `PGS-E1901` y no se analizan (el servidor sigue funcionando para el resto).

## Tamaños

`hover`, los inlay hints y `pengu size` muestran el tamaño real en bytes, medido
con `pengu-layout` (el mismo motor que valida `crates/pengu-codegen/tests/layout.rs`
contra `std::mem::size_of` de `rustc`):

- tipos: `tamaño 8 B, alineación 4 B` y, en `rune`, el recordatorio de que los
  campos van en orden de declaración porque el backend emite `#[repr(C)]`;
- funciones: `huella`, la suma de parámetros y retorno;
- `sigil`: tamaño de su tipo;
- expresión bajo el cursor: `tamaño N B` cuando es medible (un slice no lo es).

`pengu size` imprime la tabla completa del programa:

```console
$ pengu size
fn suma · huella 12 B
tipo Caja · genérico (el tamaño depende de sus argumentos)
tipo Forma · 16 B, alineación 8 B
tipo Punto · 8 B, alineación 4 B
```

## Formato

El formateo de esta fase es **conservador** y no reordena código: normaliza
`\r\n` a `\n`, convierte tabulaciones iniciales en 4 espacios, quita espacios
finales, colapsa líneas en blanco consecutivas al final y garantiza un salto de
línea final. Si el resultado es idéntico al texto actual no se devuelve ninguna
edición. El formateador completo (alineación, expresiones, comentarios) llega
en la Fase 8.

## VS Code

La extensión vive en `editors/vscode` y **no necesita `npm install`**: el
cliente LSP está escrito en JavaScript puro sobre `node:child_process`.

```sh
# empaqueta e instala la extensión en VS Code
./scripts/install-extension.sh
# o solo el paquete
node scripts/vsix.mjs
```

La extensión aporta:

| Pieza | Qué hace |
| --- | --- |
| Diagnósticos | Subraya errores y avisos del compilador con código y ayuda. |
| Hover | Firma, documentación y **tamaño en bytes** con alineación. |
| Autocompletado | Contexto real: módulos tras `summon`, miembros tras `modulo::`, métodos tras `.`, símbolos y palabras clave. |
| Inlay hints | `: Tipo · N B` en `bind`/`morph`/parámetros sin anotación. |
| Semantic tokens | Coloreado preciso de tipos, funciones, variables, números y operadores. |
| Lentes de código | «▶ Ejecutar programa» sobre `grimoire` y «ejecutar test» sobre cada `@@test`. |
| Navegación | Definición, tipo, implementaciones, referencias, resaltado, renombrar, jerarquía de llamadas. |
| Formato | `Format Document` con el mismo formateador que `pengu fmt`. |
| Snippets | 24 plantillas (`prog`, `fn`, `rune`, `pact`, `match`, `test`, `doc`…). |

Comandos y atajos (solo con el editor en un archivo `.pengu`):

| Comando | Atajo | Qué ejecuta |
| --- | --- | --- |
| `PenguScript: Ejecutar programa` | `F5` | `pengu run` en la raíz del proyecto |
| `PenguScript: Ejecutar pruebas` | `Ctrl+F5` | `pengu test` |
| `PenguScript: Comprobar` | `Ctrl+Shift+B` | `pengu check` |
| `PenguScript: Reiniciar servidor` | — | Reinicia el LSP |

Ejecutar exige un `Tome.toml` en algún directorio padre; el documento se guarda
antes y el terminal se reutiliza (`PenguScript`).

Configuración: `pengu.serverPath` (por defecto `pengu`) y `pengu.logFile`
(archivo de registro del servidor). Si el servidor no arranca, la extensión
ofrece instalar el CLI, configurar la ruta y abrir el registro.

## Neovim y LazyVim

Copia `editors/nvim/lua/pengu.lua` a tu configuración y llama a `setup()`:

```lua
require("pengu").setup()
```

En LazyVim, añade un plugin spec:

```lua
return {
  {
    "pengu-lsp",
    dir = "~/ruta/a/PenguScript-Rust/editors/nvim",
    config = function()
      require("pengu").setup()
    end,
  },
}
```

El módulo usa `vim.lsp.start()` (Neovim 0.10+), así que no hace falta
`nvim-lspconfig`.

## Vim

Con [vim-lsp](https://github.com/prabirshrestha/vim-lsp):

```vim
augroup pengu
  autocmd!
  autocmd User lsp_setup call lsp#register_server({
    \ 'name': 'pengu',
    \ 'cmd': {server_info -> ['pengu', 'lsp']},
    \ 'allowlist': ['pengu'],
    \ 'root_uri': {server_info -> lsp#utils#path_to_uri(
    \   lsp#utils#find_nearest_parent_file_directory(
    \     lsp#utils#get_buffer_path(), 'Tome.toml'))},
    \ })
augroup END
```

Con `coc.nvim`, define el servidor en `coc-settings.json`:

```json
{
  "languageserver": {
    "pengu": {
      "command": "pengu",
      "args": ["lsp"],
      "filetypes": ["pengu"],
      "rootPatterns": ["Tome.toml", "main.pengu", "lib.pengu"]
    }
  }
}
```

## Prueba de humo

`editors/smoke.mjs` habla el mismo protocolo que la extensión, sin
dependencias:

```sh
cargo build -p pengu-cli
node editors/smoke.mjs
```

Comprueba contra el binario real: `initialize` (y que anuncie hover, inlay
hints, code lens y semantic tokens), `didOpen`, `publishDiagnostics`, `hover`,
autocompletado de `summon std::`, inlay hints, la lente «▶ Ejecutar programa»
sobre `grimoire`, los tokens semánticos y `shutdown`.

## Límites conocidos

- **Un archivo raíz por proyecto**: no se analizan a la vez los `.pengu` que no
  son el programa (el compilador tampoco los carga).
- La cancelación es cooperativa: no interrumpe un análisis en curso, solo
  descarta peticiones que aún no habían empezado.
- `CStr` y otras vistas prestadas siguen las mismas reglas que el compilador
  (ver `scratch/LIMITATIONS_AUDIT.md`).
- `documentLink` no se implementa: los módulos del lenguaje no son archivos.
- `workspace/didChangeWatchedFiles` tampoco: el estado del editor (overlay) es
  la fuente de verdad y el servidor no vigila el disco.
