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

### La medición nunca bloquea una petición

Compilar el sondeo tarda ~1,8 s, así que ninguna consulta del editor la
espera. Mientras la tabla es válida se responde con ella; cuando cambian las
declaraciones queda marcada como vieja y la medición se agenda **400 ms
después** del último cambio. Hasta que llega, el hover no muestra tamaño, los
inlay hints no llevan `· N B` y la barra de estado oculta el valor; al
terminar, el servidor pide al editor que refresque los inlay hints.

El sondeo incluye solo declaraciones (tipos, runes y omens), no los cuerpos de
las funciones: editar un cuerpo no invalida la caché. La tabla se guarda en
`.pengu-cache/layout/` con el hash del sondeo como clave.

`pengu/refreshSizes` fuerza la medición (lo usa el comando «PenguScript:
medir tamaños») y `pengu/perf` devuelve los tiempos del último análisis,
publicación y medición, útil para comprobar presupuestos.

## Ajustes de la extensión

| Ajuste | Por defecto | Efecto |
| --- | --- | --- |
| `pengu.inlayHints.types` | `true` | Muestra `: T` en bindings sin anotación. |
| `pengu.inlayHints.sizes` | `false` | Añade `· N B` a los inlay hints. |
| `pengu.completion.docs` | `true` | Documentación en el autocompletado. |
| `pengu.statusBar.size` | `true` | Barra de estado con el tamaño bajo el cursor. |
| `pengu.hover.sizes` | `true` | Muestra el tamaño medido en el hover. |

Los ajustes que afectan al servidor se envían en `initializationOptions`; al
cambiarlos, la extensión reinicia el cliente.

## Rendimiento

Cifras medidas sobre `examples/13_enchanting` (5 archivos, con `std/`) en el
mismo equipo:

| Operación | Antes | Ahora |
| --- | --- | --- |
| Reanálisis tras una pulsación | 8–30 ms por pulsación | 6 ms, una sola vez tras 120 ms de reposo |
| Hover después de editar | 1975 ms (compilaba en línea) | 10 ms |
| Publicación de diagnósticos | todos los archivos en cada cambio | solo los archivos cuya lista cambió |
| Medición de tamaños | bloqueaba la petición 1889 ms | 1,8 s en segundo plano; las peticiones responden ya |

Cómo funciona:

1. **Sincronización incremental**: los cambios del editor se aplican sobre el
   texto actual (antes se reemplazaba el documento entero por el fragmento).
2. **Debounce** de 120 ms: una ráfaga de teclas produce un único análisis y
   una única publicación. Guardar analiza de inmediato.
3. **Diff de diagnósticos**: cada archivo tiene una huella; si no cambió, no se
   reenvía.
4. **Filtro de la zona caliente**: mientras se escribe no se publican
   `E0403`/`E0506` sobre el tramo recién editado; 800 ms después del reposo se
   publica la lista definitiva.
5. **Tamaños en segundo plano** y **caché de parseo** por contenido (hash
   FNV-1a), que evita volver a parsear los archivos que no cambiaron.

La extensión también agrupa los cambios de selección (250 ms) antes de pedir
`pengu/sizeAt`.
