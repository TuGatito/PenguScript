# Clientes de editor

Clientes del servidor LSP de `pengu`. Todos hablan el mismo protocolo por
`stdio`, así que la configuración solo cambia en cómo se arranca el binario.

| Editor | Ruta | Notas |
|--------|------|-------|
| VS Code | `vscode/` | Extensión sin dependencias (`node:child_process`); `F5` para probarla. |
| Neovim | `nvim/lua/pengu.lua` | API nativa `vim.lsp.start` de Neovim 0.10+. |
| LazyVim | `nvim/lua/pengu.lua` | Igual; ver el comentario de uso dentro del archivo. |
| Vim | — | Con `vim-lsp` o `coc.nvim`; instrucciones en `docs/LSP.md`. |

## Requisitos

- `pengu` en el `PATH` (`cargo install --path crates/pengu-cli`) o la ruta
  configurada en el cliente.
- Para VS Code: `pengu.serverPath` si el binario no está en el `PATH`.

## Pruebas rápidas

```bash
# Servidor + protocolo real, sin editor
node editors/smoke.mjs

# Rendimiento con archivos grandes
node editors/bench.mjs target/release/pengu 7000
```

`smoke.mjs` arranca `target/debug/pengu lsp`, abre un documento con un error de
tipos, comprueba los diagnósticos publicados y un `hover`. `bench.mjs` mide
`didOpen` y `didChange` + `documentSymbol` sobre un programa generado.
