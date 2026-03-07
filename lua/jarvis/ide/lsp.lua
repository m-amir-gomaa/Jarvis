-- lua/jarvis/ide/lsp.lua
-- LSP client configuration for jarvis-lsp (TCP port 8002).
-- Handles server start/stop and capability negotiation.

local M = {}

local LSP_PORT = 8002
local server_started = false

function M.setup(opts)
  opts = opts or {}
  local token = opts.session_token or ""

  -- Register the Jarvis LSP client via nvim-lspconfig if available
  local ok, lspconfig = pcall(require, "lspconfig")
  if not ok then
    vim.notify("[Jarvis LSP] nvim-lspconfig not available — LSP features disabled", vim.log.levels.WARN)
    return
  end

  local configs = require("lspconfig.configs")
  if not configs.jarvis then
    configs.jarvis = {
      default_config = {
        cmd = vim.lsp.rpc.connect("127.0.0.1", LSP_PORT),
        filetypes = { "python", "lua", "rust", "nix", "javascript", "typescript" },
        root_dir = lspconfig.util.root_pattern(".git", "flake.nix", "pyproject.toml"),
        init_options = {
          jarvis_session_token = token,
        },
        settings = {},
      },
    }
  end

  lspconfig.jarvis.setup({
    on_attach = function(client, bufnr)
      M.on_attach(client, bufnr)
      -- P1-7: Fetch conn_id after LSP initialization and sync to security.lua
      vim.defer_fn(function()
        local result = vim.fn.system("curl -s http://localhost:8001/auth/conn_id")
        local ok, data = pcall(vim.fn.json_decode, result)
        if ok and data and data.conn_id then
          require("jarvis.ide.security").set_conn_id(data.conn_id)
        end
      end, 500)
    end,
  })
end

function M.on_attach(client, bufnr)
  vim.notify("[Jarvis LSP] Attached to buffer " .. bufnr, vim.log.levels.INFO)
end

function M.is_running()
  -- Check if jarvis-lsp HTTP sidecar is alive
  local result = vim.fn.system("curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/health")
  return result == "200"
end

return M
