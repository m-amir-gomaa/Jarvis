-- lua/jarvis/ide/init.lua
local M = {}

function M.setup(opts)
  opts = opts or {}
  -- Core IDE components
  require("jarvis.ide.security").setup(opts.security or {})
  -- Register commands
  M._register_commands()
end

function M._register_commands()
  local actions = require("jarvis.ide.actions")
  local cmds = {
    JarvisIDEFix      = function() actions.fix_at_cursor() end,
    JarvisIDEExplain  = function() actions.explain_selection() end,
    JarvisIDERefactor = function(args) actions.refactor(args.args) end,
    JarvisIDEChat     = function() require("jarvis.ide.chat").open() end,
  }
  for name, fn in pairs(cmds) do
    if vim.fn.exists(":" .. name) == 0 then
      vim.api.nvim_create_user_command(name, fn, { nargs = "?" })
    end
  end
end

return M
