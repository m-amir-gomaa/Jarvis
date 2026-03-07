-- lua/jarvis/ide/actions.lua
-- IDE action handlers. Each action requests a capability via the security bridge,
-- then calls the Jarvis HTTP API to perform the action.

local M = {}
local security = require("jarvis.ide.security")
local api_base = "http://localhost:8001"

local function notify(msg, level)
  vim.schedule(function()
    vim.notify("[Jarvis IDE] " .. msg, level or vim.log.levels.INFO)
  end)
end

local function get_visual_selection()
  local s = vim.fn.getpos("'<")
  local e = vim.fn.getpos("'>")
  local lines = vim.api.nvim_buf_get_lines(0, s[2] - 1, e[2], false)
  if #lines == 0 then return "" end
  lines[#lines] = string.sub(lines[#lines], 1, e[3])
  lines[1] = string.sub(lines[1], s[3])
  return table.concat(lines, "\n")
end

local function get_current_line_context(n)
  n = n or 10
  local row = vim.api.nvim_win_get_cursor(0)[1]
  local start = math.max(0, row - n - 1)
  local lines = vim.api.nvim_buf_get_lines(0, start, row + n, false)
  return table.concat(lines, "\n")
end

local function call_jarvis_action(action, payload, callback)
  local body = vim.fn.json_encode(payload)
  vim.fn.jobstart({
    "curl", "-s", "-X", "POST",
    "-H", "Content-Type: application/json",
    "-d", body,
    api_base .. "/ide/" .. action
  }, {
    on_stdout = function(_, data)
      local s = table.concat(data)
      if s == "" then return end
      local ok, result = pcall(vim.fn.json_decode, s)
      if ok and callback then callback(result) end
    end,
    on_exit = function(_, code)
      if code ~= 0 then
        notify("Action '" .. action .. "' failed (curl exit " .. code .. ")", vim.log.levels.WARN)
      end
    end
  })
end

function M.fix()
  security.request_capability("ide:edit", "Fix code at cursor", function(granted)
    if not granted then
      notify("ide:edit capability denied", vim.log.levels.WARN)
      return
    end
    local ctx = get_current_line_context(15)
    local file = vim.api.nvim_buf_get_name(0)
    notify("Requesting fix…")
    call_jarvis_action("fix", { context = ctx, file = file }, function(result)
      if result and result.fixed_code then
        notify("Fix ready — see quickfix list")
        -- In a full implementation: apply the diff via vim.lsp.util
      else
        notify(result and result.error or "No fix returned", vim.log.levels.WARN)
      end
    end)
  end)
end

function M.explain()
  security.request_capability("ide:read", "Explain code selection", function(granted)
    if not granted then notify("ide:read capability denied", vim.log.levels.WARN); return end
    local text = get_visual_selection()
    if text == "" then text = get_current_line_context(5) end
    notify("Explaining selection…")
    call_jarvis_action("explain", { text = text }, function(result)
      if result and result.explanation then
        -- Open a scratch buffer with the explanation
        local buf = vim.api.nvim_create_buf(false, true)
        vim.api.nvim_buf_set_lines(buf, 0, -1, false, vim.split(result.explanation, "\n"))
        vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
        vim.cmd("vsplit")
        vim.api.nvim_win_set_buf(0, buf)
      else
        notify(result and result.error or "No explanation returned", vim.log.levels.WARN)
      end
    end)
  end)
end

function M.refactor()
  security.request_capability("ide:edit", "Refactor selection", function(granted)
    if not granted then notify("ide:edit capability denied", vim.log.levels.WARN); return end
    local text = get_visual_selection()
    notify("Requesting refactor…")
    call_jarvis_action("refactor", { code = text }, function(result)
      if result and result.refactored then
        notify("Refactor ready (check scratch buffer)")
        local buf = vim.api.nvim_create_buf(false, true)
        vim.api.nvim_buf_set_lines(buf, 0, -1, false, vim.split(result.refactored, "\n"))
        vim.cmd("vsplit"); vim.api.nvim_win_set_buf(0, buf)
      else
        notify(result and result.error or "No refactor returned", vim.log.levels.WARN)
      end
    end)
  end)
end

function M.test_gen()
  security.request_capability("ide:edit", "Generate tests", function(granted)
    if not granted then notify("ide:edit capability denied", vim.log.levels.WARN); return end
    local ctx = get_current_line_context(30)
    notify("Generating tests…")
    call_jarvis_action("test_gen", { code = ctx }, function(result)
      if result and result.tests then
        local buf = vim.api.nvim_create_buf(false, true)
        vim.api.nvim_buf_set_lines(buf, 0, -1, false, vim.split(result.tests, "\n"))
        vim.api.nvim_buf_set_option(buf, "filetype", "python")
        vim.cmd("vsplit"); vim.api.nvim_win_set_buf(0, buf)
      else
        notify(result and result.error or "No tests generated", vim.log.levels.WARN)
      end
    end)
  end)
end

function M.doc_gen()
  security.request_capability("ide:edit", "Generate docstring", function(granted)
    if not granted then notify("ide:edit capability denied", vim.log.levels.WARN); return end
    local ctx = get_current_line_context(20)
    notify("Generating docstring…")
    call_jarvis_action("doc_gen", { code = ctx }, function(result)
      if result and result.docstring then
        notify("Docstring ready (check scratch buffer)")
        local buf = vim.api.nvim_create_buf(false, true)
        vim.api.nvim_buf_set_lines(buf, 0, -1, false, vim.split(result.docstring, "\n"))
        vim.cmd("vsplit"); vim.api.nvim_win_set_buf(0, buf)
      else
        notify(result and result.error or "No docstring generated", vim.log.levels.WARN)
      end
    end)
  end)
end

function M.commit()
  security.request_capability("vcs:write", "Generate commit message", function(granted)
    if not granted then notify("vcs:write capability denied", vim.log.levels.WARN); return end
    notify("Generating commit message…")
    call_jarvis_action("commit", {}, function(result)
      if result and result.message then
        vim.fn.setreg('"', result.message)
        notify("Commit message copied to register: " .. result.message)
      else
        notify(result and result.error or "No commit message generated", vim.log.levels.WARN)
      end
    end)
  end)
end

function M.review()
  security.request_capability("ide:read", "Review code selection", function(granted)
    if not granted then notify("ide:read capability denied", vim.log.levels.WARN); return end
    local text = get_visual_selection()
    if text == "" then text = get_current_line_context(40) end
    notify("Requesting code review…")
    call_jarvis_action("review", { code = text }, function(result)
      if result and result.review then
        local buf = vim.api.nvim_create_buf(false, true)
        vim.api.nvim_buf_set_lines(buf, 0, -1, false, vim.split(result.review, "\n"))
        vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
        vim.cmd("vsplit"); vim.api.nvim_win_set_buf(0, buf)
      else
        notify(result and result.error or "No review returned", vim.log.levels.WARN)
      end
    end)
  end)
end

function M.search(query)
  if not query or query == "" then
    query = vim.fn.input("Jarvis Search: ")
  end
  if query == "" then return end
  notify("Searching: " .. query)
  call_jarvis_action("search", { query = query }, function(result)
    if result and result.results then
      local buf = vim.api.nvim_create_buf(false, true)
      local lines = {}
      for _, r in ipairs(result.results) do
        table.insert(lines, "## " .. (r.title or r.source or "Result"))
        table.insert(lines, r.content or "")
        table.insert(lines, "")
      end
      vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
      vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
      vim.cmd("vsplit"); vim.api.nvim_win_set_buf(0, buf)
    else
      notify(result and result.error or "No results", vim.log.levels.WARN)
    end
  end)
end

return M
