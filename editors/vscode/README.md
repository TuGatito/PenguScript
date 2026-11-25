# PenguScript para VS Code

Extensión completa del lenguaje PenguScript: resaltado, diagnósticos,
autocompletado, snippets, formato, ejecución de archivos y tareas.

La extensión arranca `pengu lsp` (servidor LSP por stdio) y delega en el mismo
ejecutable del compilador para ejecutar, compilar, verificar y formatear. Antes
de usarla:

```bash
bun run build                  # genera dist/pengu
./scripts/install.sh           # o ponlo en el PATH
```

Si `pengu` no está en el `PATH`, configura `pengu.executable` con la ruta
absoluta (`Ctrl+,` → busca «pengu.executable»).

## Qué incluye

- **Resaltado** (`syntaxes/pengu.tmLanguage.json`) para todo el lenguaje:
  palabras clave, tipos primitivos y contenedores, declaraciones de `rune`,
  `omen`, `echo`, `seal`, `enchanting`, funciones, parámetros, `@campo`, `#xs`,
  `realm::simbolo`, interpolación `#{…}`, números hex/bin/octal/float y todos
  los operadores.
- **Diagnósticos en tiempo real** del servidor LSP y, opcionalmente,
  `pengu check --json` al guardar (`pengu.check.onSave`).
- **IntelliSense completo** (ver más abajo), incluidos los métodos de
  `enchanting`, los tipos del proyecto y `std/`.
- **Tamaños medidos** del símbolo bajo el cursor en la barra de estado y
  comando «Mostrar tamaño del símbolo».
- **Snippets** (`snippets/penguscript.code-snippets`): 49 plantillas para
  `main`, `invoke`, `rune`, `omen`, `match`, `for`, `unsafe`, operadores, etc.
- **Comandos** (paleta con `Ctrl+Shift+P`, menú contextual del editor y del
  explorador):

  | Comando | Atajo | Qué hace |
  | --- | --- | --- |
  | PenguScript: ejecutar archivo | `Ctrl+Alt+R` | `pengu run <archivo>` en una terminal |
  | PenguScript: compilar archivo | `Ctrl+Alt+B` | `pengu build <archivo>` |
  | PenguScript: verificar archivo | `Ctrl+Alt+K` | `pengu check <archivo>` |
  | PenguScript: ejecutar proyecto | — | `pengu run` con el `pengu.toml` del proyecto |
  | PenguScript: formatear archivo | — | formato del LSP |
  | PenguScript: generar enlaces de C | — | `pengu bindgen` (pide encabezado y realm) |
  | PenguScript: inicializar proyecto | — | `pengu init` |
  | PenguScript: diagnóstico del entorno | — | `pengu doctor` |
  | PenguScript: reiniciar servidor | — | reinicia `pengu lsp` |
  | PenguScript: mostrar salida | — | canal «PenguScript» |
  | PenguScript: configurar ejecutable | — | abre el ajuste `pengu.executable` |

- **Tareas** para `Ctrl+Shift+B` y `tasks.json` con `"type": "pengu"`; el
  *problem matcher* `$pengu` reconoce los diagnósticos del compilador.

Ejemplo de `tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    { "type": "pengu", "command": "build", "group": { "kind": "build", "isDefault": true } },
    { "type": "pengu", "command": "run", "file": "src/main.pengu" }
  ]
}
```

- **Barra de estado** con la versión del ejecutable o un aviso si no se
  encuentra.


## IntelliSense

El cliente LSP analiza el **proyecto completo** (el archivo, sus `invoke` y
`std/`), incluyendo los buffers sin guardar:

- autocompletado con ámbito y sombreado, miembros de runes/omens/sellos/ecos,
  miembros incorporados y métodos enhechizados (primero), `::` con variantes y
  exportaciones, y tipos tras `:` o `->`;
- *hover* con firma, documentación de los comentarios `--`, contenedor, tamaño
  y desplazamiento de campos;
- ayuda de firma con el parámetro activo;
- ir a la definición (incluidos locales y `std/`), referencias y renombrado por
  proyecto (renombrar `std/` se rechaza);
- inlay hints de tipos inferidos, tokens semánticos, plegado, acciones de código,
  enlaces en los `invoke` y lente «▶ Ejecutar» sobre `main`.

## Ajustes

| Ajuste | Por defecto | Descripción |
| --- | --- | --- |
| `pengu.executable` | `pengu` | Ruta o nombre del ejecutable. |
| `pengu.build.args` | `[]` | Argumentos extra para `pengu build`. |
| `pengu.run.args` | `[]` | Argumentos extra para `pengu run`. |
| `pengu.check.onSave` | `false` | Verifica al guardar con `pengu check --json`. |
| `pengu.lsp.trace.server` | `off` | Traza de la comunicación LSP (`messages`/`verbose`). |
| `pengu.inlayHints.types` | `true` | Muestra `: T` en los bindings sin anotación. |
| `pengu.inlayHints.sizes` | `false` | Añade `· N B` a los inlay hints. |
| `pengu.completion.docs` | `true` | Muestra la documentación en el autocompletado. |
| `pengu.statusBar.size` | `true` | Barra de estado con el tamaño del símbolo. |
| `pengu.hover.sizes` | `true` | Muestra el tamaño medido en el hover. |

Los tamaños se miden compilando un sondeo C++ con el mismo compilador que usa
`pengu build`. La primera medición tarda ~1,8 s y ocurre en segundo plano: el
hover y la barra de estado responden al instante con el último valor válido.

Además, los archivos `.pengu` usan por defecto 2 espacios, sin detección
automática de sangría (el lenguaje es sensible a la indentación).

## Si no encuentra `pengu`

VS Code lanzado desde el escritorio no siempre hereda el `PATH` del shell. La
extensión busca el ejecutable en el `PATH` del proceso **y** en
`~/.local/bin`, `~/.bun/bin`, `~/bin`, `/usr/local/bin`, `/opt/homebrew/bin` y
`/usr/bin`. Si aun así no aparece, el aviso permite abrir `pengu.executable`
para escribir la ruta absoluta y muestra en la salida los directorios
consultados. Con `scripts/install.sh` el binario queda en `~/.local/bin/pengu`,
que ya se busca automáticamente.

## Si el LSP marca errores que `pengu check` no ve

Casi siempre es el mismo problema: el editor y la terminal están usando
stdlibs distintas. Ejecuta `pengu doctor` en la terminal del proyecto.

- Si dice que el `std/` del proyecto **no coincide** con el del binario,
  reinstala: `bash scripts/install.sh` y luego «Developer: Reload Window».
- Si el proyecto tiene su propio `std/` y no hay `pengu.toml` en la raíz, el
  LSP no puede saber que ese `std/` es del proyecto: crea el manifiesto con
  `pengu init` o copia el del repositorio.
- La salida «PenguScript» del editor registra la huella que está usando el
  servidor al arrancar.

## Desarrollo

```bash
cd editors/vscode
npm install
npx @vscode/vsce package    # genera penguscript-0.1.0.vsix
code --install-extension penguscript-0.1.0.vsix
```

Para probar sin empaquetar: abre esta carpeta en VS Code y pulsa `F5`
(«Ejecutar extensión»).

Las pruebas de la extensión viven en `tests/extension/` y comprueban, entre
otras cosas, que la gramática cubre todas las palabras clave, tipos y
operadores del compilador y que cada snippet es código válido:

```bash
bun test tests/extension
```
