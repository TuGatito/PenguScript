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
- **Autocompletado, hover, ir a la definición, símbolos del documento y
  formato** (heredados del LSP, incluidos los métodos de `enchanting`).
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

## Ajustes

| Ajuste | Por defecto | Descripción |
| --- | --- | --- |
| `pengu.executable` | `pengu` | Ruta o nombre del ejecutable. |
| `pengu.build.args` | `[]` | Argumentos extra para `pengu build`. |
| `pengu.run.args` | `[]` | Argumentos extra para `pengu run`. |
| `pengu.check.onSave` | `false` | Verifica al guardar con `pengu check --json`. |
| `pengu.lsp.trace.server` | `off` | Traza de la comunicación LSP (`messages`/`verbose`). |

Además, los archivos `.pengu` usan por defecto 2 espacios, sin detección
automática de sangría (el lenguaje es sensible a la indentación).

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
