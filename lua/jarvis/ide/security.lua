-- lua/jarvis/ide/security.lua
local M = {}
local api_base = "http://localhost:8001"

function M.setup(opts)
  M.opts = opts
end

function M.request_capability(cap, reason, callback)
  local body = vim.fn.json_encode({
    capability = cap,
    reason = reason,
    scope = "task"
  })
  
  -- Use curl for simple OOB request from Lua
  vim.fn.jobstart({
    "curl", "-s", "-X", "POST",
    "-H", "Content-Type: application/json",
    "-d", body,
    api_base .. "/security/request"
  }, {
    on_stdout = function(_, data)
      local result_str = table.concat(data)
      if result_str == "" then return end
      local ok, result = pcall(vim.fn.json_decode, result_str)
      if ok and result.granted then
        callback(true)
      else
        callback(false)
      end
    end,
    on_exit = function(_, code)
      if code ~= 0 then callback(false) end
    end
  })
end

return M
