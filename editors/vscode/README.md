# PenguScript para VS Code

Resaltado de sintaxis, diagnósticos, autocompletado, definición, símbolos de
documento y formato para archivos `.pengu` y `.d.pengu`.

La extensión arranca `pengu lsp` y habla LSP por stdio. Antes de usarla:

```bash
bun run build          # genera dist/pengu
```

Si el ejecutable no está en el `PATH`, configura `pengu.executable` con la ruta
absoluta (por ejemplo `/ruta/al/repo/dist/pengu` o
`/ruta/al/repo/run-pengu.sh`).

## Desarrollo

```bash
cd editors/vscode
npm install
npx @vscode/vsce package    # genera penguscript-0.1.0.vsix
code --install-extension penguscript-0.1.0.vsix
```

Para probar sin empaquetar: abre esta carpeta en VS Code y pulsa `F5`
(«Run Extension»).
