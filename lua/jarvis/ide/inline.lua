-- lua/jarvis/ide/inline.lua
-- Inline ghost-text completion support.
-- Uses the LSP Incomplete Results pattern — results arrive asynchronously
-- via jarvis/completionReady notification pushed from the server.

local M = {}
local api_base = "http://localhost:8001"
local _pending = false

function M.setup(opts)
  M.opts = vim.tbl_deep_extend("force", {
    debounce_ms = 800,
    max_tokens  = 64,
  }, opts or {})
end

function M.trigger(bufnr, row, col)
  if _pending then return end
  _pending = true

  local lines = vim.api.nvim_buf_get_lines(bufnr, math.max(0, row - 5), row, false)
  local prefix = table.concat(lines, "\n")
  local file   = vim.api.nvim_buf_get_name(bufnr)
  local ft     = vim.bo[bufnr].filetype

  local body = vim.fn.json_encode({
    prefix     = prefix,
    file       = file,
    filetype   = ft,
    max_tokens = M.opts.max_tokens,
  })

  vim.fn.jobstart({
    "curl", "-s", "-X", "POST",
    "-H", "Content-Type: application/json",
    "-d", body,
    api_base .. "/ide/complete"
  }, {
    on_stdout = function(_, data)
      local s = table.concat(data)
      if s == "" then _pending = false; return end
      local ok, result = pcall(vim.fn.json_decode, s)
      if ok and result.completion and result.completion ~= "" then
        -- Show as virtual text (ghost text)
        local ns = vim.api.nvim_create_namespace("jarvis_inline")
        vim.api.nvim_buf_clear_namespace(bufnr, ns, 0, -1)
        vim.api.nvim_buf_set_extmark(bufnr, ns, row - 1, col, {
          virt_text      = { { result.completion, "Comment" } },
          virt_text_pos  = "eol",
          hl_mode        = "combine",
        })
      end
      _pending = false
    end,
    on_exit = function(_, _)
      _pending = false
    end
  })
end

function M.accept(bufnr)
  -- Clear ghost text (user has pressed Tab/accept key)
  local ns = vim.api.nvim_create_namespace("jarvis_inline")
  vim.api.nvim_buf_clear_namespace(bufnr, ns, 0, -1)
end

return M
