# Servidor de lenguaje (`pengu lsp`)

El servidor habla JSON-RPC 2.0 por stdio (`Content-Length`), sin dependencias.
Trabaja sobre un **proyecto**: el documento abierto, sus `invoke` (incluido
`std/`) y los buffers sin guardar que el editor todavía no escribió a disco.

## Capacidades

| Capacidad | Estado | Qué hace |
| --- | --- | --- |
| `textDocumentSync` | ✅ | Sincronización incremental por cambios completos; diagnósticos por archivo al abrir, cambiar y guardar. |
| `completion` | ✅ | Ámbito con sombreado, miembros de runes/omens/sellos/ecos, incorporados, métodos enhechizados y tipos tras `:`/`->`. |
| `hover` | ✅ | Firma, documentación (`--`), contenedor, tipo inferido, tamaño y desplazamiento de campos. |
| `signatureHelp` | ✅ | Parámetro activo, variádicas y funciones de módulos importados. |
| `definition` | ✅ | Locales, parámetros, campos, métodos, funciones, tipos y símbolos de `std/`. |
| `references` | ✅ | Ocurrencias por proyecto, ignorando cadenas y comentarios. |
| `rename` / `prepareRename` | ✅ | Renombrado por proyecto con sombreado; `std/` se rechaza con mensaje. |
| `documentSymbol` | ✅ | Jerárquico: rune→campos, omen→variantes, enchanting→métodos. |
| `workspace/symbol` | ✅ | Búsqueda por nombre en todos los archivos del proyecto. |
| `formatting` | ✅ | Documento completo con el mismo formateador del CLI. |
| `rangeFormatting` | ✅ | Solo cuando el rango cubre el documento; si no, no edita. |
| `inlayHint` | ✅ | Tipos inferidos; tamaño opcional (`pengu.inlayHints.sizes`). |
| `semanticTokens/full` | ✅ | Tokens con la leyenda del servidor (13 tipos). |
| `foldingRange` | ✅ | Pares INDENT/DEDENT del lexer. |
| `codeAction` | ✅ | Arreglos rápidos de diagnósticos y «añadir tipo explícito». |
| `documentLink` | ✅ | Cada `invoke "ruta"` enlaza con el archivo resuelto. |
| `codeLens` | ✅ | `▶ Ejecutar` sobre `main`. |
| `pengu/sizeAt` | ✅ | Petición propia: tipo y tamaño medido del símbolo bajo el cursor. |

No se anuncian `completionItem/resolve`, `codeAction/resolve`, `documentLink/resolve`
ni `codeLens/resolve`: los ítems ya viajan completos desde el servidor.

## Tamaños en bytes

Los tamaños son **medidos**, no estimados: el servidor genera un programa C++
con las declaraciones del proyecto y lo compila con el mismo toolchain que el
ejecutable, leyendo `sizeof`, `alignof` y `offsetof`. La tabla se cachea por
contenido en `.pengu-cache/layout/` y se descarta cuando cambian las
declaraciones. Sin compilador disponible, el servidor responde «no disponible»
y `pengu size` termina con código 1 y un mensaje claro.

Se miden: primitivos, `string` y variantes, runes, omens, sellos, ecos,
constantes y funciones (retorno + parámetros, y el tamaño de su
`std::function`). Los tipos genéricos se miden con su instanciación
representativa `int`; en un uso concreto se puede consultar `pengu/sizeAt`.

## Ajustes de la extensión

| Ajuste | Por defecto | Efecto |
| --- | --- | --- |
| `pengu.inlayHints.types` | `true` | Muestra `: T` en bindings sin anotación. |
| `pengu.inlayHints.sizes` | `false` | Añade `· N B` a los inlay hints. |
| `pengu.completion.docs` | `true` | Documentación en el autocompletado. |
| `pengu.statusBar.size` | `true` | Barra de estado con el tamaño bajo el cursor. |

Los ajustes que afectan al servidor se envían en `initializationOptions`; al
cambiarlos, la extensión reinicia el cliente.

## Rendimiento

El análisis de un proyecto pequeño (3–5 archivos con `std/`) tarda menos de
100 ms en un portátil moderno; la medición de tamaños añade ~1 s la primera vez
(compilación del sondeo) y es inmediata después desde la caché.
