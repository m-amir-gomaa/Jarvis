-- lua/jarvis/init.lua
-- Jarvis Neovim Plugin — Entry Point
-- Requires: plenary.nvim for async HTTP
-- Install via home-manager: pkgs.vimPlugins.plenary-nvim

local M = {}
local agent = require("jarvis.agent")
local complete = require("jarvis.complete")
local dap_cfg = require("jarvis.dap")
local pin = require("jarvis.pin")

M.config = {
  server_url = "http://127.0.0.1:7002",
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
  vim.api.nvim_create_user_command("JarvisCancel",  function() agent.cancel() end, {})
  vim.api.nvim_create_user_command("JarvisExplainError", function() agent.explain_error() end, {})
  vim.api.nvim_create_user_command("JarvisCommit",      function() agent.generate_commit() end, {})
  vim.api.nvim_create_user_command("JarvisSearch",      function(opts) agent.search(opts.args) end, { nargs = "?" })
  vim.api.nvim_create_user_command("JarvisPrefetch",    function() agent.prefetch_for_buffer() end, {})
  vim.api.nvim_create_user_command("JarvisModel",       function() agent.switch_model() end, {})
  vim.api.nvim_create_user_command("JarvisTimeline",    function() agent.diagnostic_timeline() end, {})

  -- Pin Commands
  vim.api.nvim_create_user_command("JarvisPin",   function() pin.pin_selection() end, { range = true })
  vim.api.nvim_create_user_command("JarvisPins",  function() pin.show_pins() end, {})
  vim.api.nvim_create_user_command("JarvisUnpin", function() pin.unpin_all() end, {})

  -- Inline Refactor
  vim.api.nvim_create_user_command("JarvisInlineRefactor", function(opts)
    local lstart = opts.line1 - 1
    local lend = opts.line2 - 1
    vim.ui.input({ prompt = "Jarvis Refactor Intent: " }, function(intent)
      if intent and intent ~= "" then
        require("jarvis.ide.inline").stream_refactor(0, lstart, lend, intent)
      end
    end)
  end, { range = true })

  -- Autocommands for Performance (Prefetching)
  local group = vim.api.nvim_create_augroup("JarvisPerformance", { clear = true })
  
  -- Prefetch for buffer on open/enter
  vim.api.nvim_create_autocmd({ "BufReadPost", "BufNewFile" }, {
    group = group,
    callback = function() agent.prefetch_for_buffer() end,
  })

  -- Prefetch completion model when entering insert mode
  vim.api.nvim_create_autocmd("InsertEnter", {
    group = group,
    callback = function() agent.prefetch("complete") end,
  })

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
