-- lua/jarvis/init.lua
-- Jarvis Neovim Plugin — Entry Point
-- Requires: plenary.nvim for async HTTP
-- Install via home-manager: pkgs.vimPlugins.plenary-nvim

local M = {}
local agent = require("jarvis.agent")
local complete = require("jarvis.complete")
local dap_cfg = require("jarvis.dap")

M.config = {
  server_url = "http://localhost:7002",
  fim_debounce_ms = 800,  -- Raised from 300ms — CPU inference is slow
  enabled = true,
}

function M.setup(opts)
  M.config = vim.tbl_deep_extend("force", M.config, opts or {})

  -- Register user commands
  vim.api.nvim_create_user_command("JarvisFix",     function() agent.fix() end, {})
  vim.api.nvim_create_user_command("JarvisChat",    function() agent.chat() end, {})
  vim.api.nvim_create_user_command("JarvisExplain", function() agent.explain() end, {})
  vim.api.nvim_create_user_command("JarvisIndex",   function() agent.index() end, {})
  vim.api.nvim_create_user_command("JarvisToggleSuggestions", function()
    M.config.enabled = not M.config.enabled
    vim.notify("Jarvis FIM: " .. (M.config.enabled and "ON" or "OFF"), vim.log.levels.INFO)
  end, {})

  -- Setup DAP adapters
  dap_cfg.setup()

  -- Check server health on startup (async, non-blocking)
  require("plenary.curl").get(M.config.server_url .. "/health", {
    callback = function(res)
      if res and res.status == 200 then
        vim.schedule(function()
          vim.notify("Jarvis ready ✓", vim.log.levels.INFO)
        end)
      end
    end,
  })
end

return M
