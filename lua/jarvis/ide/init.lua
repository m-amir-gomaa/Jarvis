-- lua/jarvis/ide/init.lua
local M = {}

function M.setup(opts)
  opts = opts or {}
  -- Core IDE components
  require("jarvis.ide.security").setup(opts.security or {})
  require("jarvis.ide.lsp").setup(opts.lsp or {})
  require("jarvis.ide.inline").setup(opts.inline or {})
  
  -- Register commands
  M._register_commands()
end

function M._register_commands()
  local actions = require("jarvis.ide.actions")
  local cmds = {
    JarvisFix      = function() actions.fix() end,
    JarvisExplain  = function() actions.explain() end,
    JarvisRefactor = function() actions.refactor() end,
    JarvisTestGen  = function() actions.test_gen() end,
    JarvisDocGen   = function() actions.doc_gen() end,
    JarvisChat     = function() require("jarvis.ide.chat").open() end,
    JarvisReview   = function() actions.review() end,
    JarvisCommit   = function() actions.commit() end,
    JarvisSearch   = function(args) actions.search(args.args) end,
  }
  for name, fn in pairs(cmds) do
    vim.api.nvim_create_user_command(name, fn, { nargs = "*" })
  end
end

return M
