# Editor: la extensión de VS Code

La extensión de VS Code (`editors/vscode`) es un cliente LSP sin dependencias y
con snippets propios. Este documento cuenta qué trae, cómo probarla y qué hacer
si el servidor no arranca. El protocolo y sus capacidades están en
[`LSP.md`](LSP.md).

## Instalación

```sh
./scripts/install.sh                 # instala el CLI y lo pone en el PATH
./scripts/install-extension.sh       # empaqueta e instala la extensión
```

`install-extension.sh` llama a `scripts/vsix.mjs --install`, que comprueba que la
versión de la extensión coincide con `pengu version --json` antes de empaquetar.

## Qué aporta

| Capacidad | Dónde se nota |
| --- | --- |
| Diagnósticos | Al guardar o escribir: subrayado con código `PGS-…` y ayuda. |
| Hover | Sobre cualquier símbolo: firma, documentación y tamaño en bytes. |
| Autocompletado | Tras `summon`, tras `modulo::`, tras `.`, y símbolos del archivo. |
| Inlay hints | `: Tipo · N B` en `bind`, `morph` y parámetros sin anotación. |
| Semantic tokens | Coloreado de tipos, funciones, variables, números y operadores. |
| Lentes | «▶ Ejecutar programa» sobre `grimoire`; «ejecutar test» sobre `@@test`. |
| Navegación | Definición, tipo de la expresión, implementaciones, referencias, resaltado, renombrar y jerarquía de llamadas. |
| Formato | `Format Document` (`Shift+Alt+F`) con el mismo formateador que `pengu fmt`. |
| Snippets | 24 plantillas: `prog`, `fn`, `fnpriv`, `test`, `rune`, `enchanting`, `pact`, `ritual`, `ritualp`, `scroll`, `summon`, `bind`, `morph`, `if`, `elseif`, `match`, `for`, `while`, `loop`, `curse`, `foreign`, `doc`, `moddoc`, `interp`. |

## Ejecutar desde el editor

| Comando | Atajo | Efecto |
| --- | --- | --- |
| `PenguScript: Ejecutar programa` | `F5` | `pengu run` en la raíz del proyecto |
| `PenguScript: Ejecutar pruebas` | `Ctrl+F5` | `pengu test` |
| `PenguScript: Comprobar` | `Ctrl+Shift+B` | `pengu check` |
| `PenguScript: Reiniciar servidor` | — | Reinicia el LSP |

El terminal se llama `PenguScript` y se reutiliza; el documento se guarda antes
de lanzar el comando. Hace falta un `Tome.toml` en el proyecto (o en un
directorio padre): es lo que define la raíz desde la que se ejecuta.

## Sintaxis e interpolación

La gramática resalta comentarios `--` y `--[[ ]]`, cadenas, números, atributos
`@@`, palabras clave, declaraciones y **la interpolación `#{…}`** dentro de
cadenas, incluida la expresión que va dentro.

## Comprobaciones automáticas

```sh
node editors/check-extension.mjs target/debug/pengu   # activación y providers
node editors/smoke.mjs target/debug/pengu             # protocolo contra el servidor
```

`check-extension.mjs` carga la extensión con un `vscode` simulado, comprueba que
registra los 19 providers y los comandos, y que lanza `pengu lsp`. `smoke.mjs`
habla el protocolo real: diagnósticos, hover, autocompletado de `summon std::`,
inlay hints, lente de ejecución y tokens semánticos.

## Depurar

1. `pengu doctor` dice si el binario está en el PATH y si la extensión está
   instalada.
2. `pengu.serverPath` permite apuntar a un binario concreto; `pengu.logFile`
   escribe el registro del servidor en un archivo.
3. La barra de estado muestra el estado del servidor: girando mientras arranca,
   `check` cuando está listo y `error`/`warning` cuando no.
4. `PenguScript: Reiniciar servidor` reinicia el proceso sin recargar VS Code.

### Si VS Code no encuentra `pengu`

VS Code abierto desde el escritorio no siempre hereda el `PATH` del shell. La
extensión lo busca, en este orden, en: `pengu.serverPath` (si tiene ruta),
el `PATH` del proceso, `~/.pengu/bin`, `~/pengu/bin`, `~/.local/bin`,
`/usr/local/bin`, `target/release`, `target/debug` y `bin/` de la carpeta
abierta, y por último pregunta a una shell de login (`command -v pengu`).
La ruta elegida se escribe en el canal de salida «PenguScript».

### Autocompletado mientras escribes

El autocompletado no depende de que el archivo compile: si estás a medias
(`summon `, `summon std::`), la extensión lista igualmente los 29 módulos de la
biblioteca estándar. Cuando el programa es válido, además ofrece los símbolos
del archivo, los métodos tras `.` y los items de cada módulo.

Si el servidor no arranca, VS Code ofrece tres acciones: instalar el CLI (abre
las instrucciones), configurar la ruta del binario o abrir el registro.
