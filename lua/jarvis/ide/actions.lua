-- lua/jarvis/ide/actions.lua
local M = {}
local security = require("jarvis.ide.security")

function M.fix_at_cursor()
  print("[Jarvis] Fixing at cursor...")
  security.request_capability("ide:edit", "Fix code at cursor", function(granted)
    if granted then print("[Jarvis] Capability granted!") else print("[Jarvis] Denied.") end
  end)
end

function M.explain_selection()
  print("[Jarvis] Explaining selection...")
end

function M.refactor(instr)
  print("[Jarvis] Refactoring: " .. (instr or ""))
end

return M
