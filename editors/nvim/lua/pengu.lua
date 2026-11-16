-- Configuración de PenguScript para Neovim (0.10+), LazyVim y Vim (con vim-lsp).
--
-- Uso rápido en Neovim / LazyVim:
--   1. Copia este archivo a ~/.config/nvim/lua/pengu.lua
--   2. Añade `require("pengu").setup()` en tu init.lua (o en un plugin spec de LazyVim)
--
-- El servidor se lanza con `pengu lsp` y se comunica por stdio.

local M = {}

local function root_dir(bufnr)
  local name = vim.api.nvim_buf_get_name(bufnr)
  local start = name ~= "" and vim.fs.dirname(name) or vim.fn.getcwd()
  return vim.fs.root(start, { "Tome.toml", "main.pengu", "lib.pengu" }) or start
end

-- Devuelve true si el ejecutable `pengu` está en el PATH.
local function has_server()
  return vim.fn.executable("pengu") == 1
end

function M.setup(options)
  options = options or {}
  local cmd = options.cmd or { "pengu", "lsp" }

  if not has_server() and not options.cmd then
    vim.notify("pengu: no se encontró `pengu` en el PATH", vim.log.levels.WARN)
    return
  end

  vim.filetype.add({
    extension = {
      pengu = "pengu",
    },
    pattern = {
      [".*%.d%.pengu"] = "pengu",
    },
  })

  vim.api.nvim_create_autocmd("FileType", {
    pattern = "pengu",
    callback = function(args)
      local root = root_dir(args.buf)
      vim.lsp.start({
        name = "pengu",
        cmd = cmd,
        root_dir = root,
        single_file_support = true,
        capabilities = vim.lsp.protocol.make_client_capabilities(),
        settings = {},
        on_attach = options.on_attach,
      }, { bufnr = args.buf })
    end,
  })
end

return M
