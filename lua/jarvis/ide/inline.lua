-- lua/jarvis/ide/inline.lua
-- Inline ghost-text completion support.
-- Uses the LSP Incomplete Results pattern — results arrive asynchronously
-- via jarvis/completionReady notification pushed from the server.

local M = {}
local api_base = "http://localhost:8001"
local server = "http://127.0.0.1:7002"
local curl = require("plenary.curl")
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

function M.clear(bufnr)
  local ns = vim.api.nvim_create_namespace("jarvis_inline_refactor")
  vim.api.nvim_buf_clear_namespace(bufnr, ns, 0, -1)
end

--- Stream a refactor edit inline replacing the current selection.
--- Uses plenary.curl and the SSE `/chat` endpoint.
--- @param bufnr number Buffer number
--- @param lstart number 0-indexed start line
--- @param lend number 0-indexed end line (inclusive)
--- @param prompt string User intent
function M.stream_refactor(bufnr, lstart, lend, prompt)
  if not bufnr or bufnr == 0 then bufnr = vim.api.nvim_get_current_buf() end
  
  -- 1. Grab original text
  local lines = vim.api.nvim_buf_get_lines(bufnr, lstart, lend + 1, false)
  local code = table.concat(lines, "\n")
  local ft = vim.bo[bufnr].filetype

  -- 2. Clear original text and inserted a placeholder
  local ns = vim.api.nvim_create_namespace("jarvis_inline_refactor")
  vim.api.nvim_buf_clear_namespace(bufnr, ns, 0, -1)
  
  -- We just delete the old text and insert an empty line, where we'll place the extmark
  vim.api.nvim_buf_set_lines(bufnr, lstart, lend + 1, false, { "" })
  
  -- Create extmark at the start of our new block
  local mark_id = vim.api.nvim_buf_set_extmark(bufnr, ns, lstart, 0, { right_gravity = false })

  -- 3. Prepare the query for the chat endpoint
  local query = string.format(
    "Refactor this code. Return ONLY the refactored code without markdown fencing.\nIntent: %s\nCode:\n```%s\n%s\n```",
    prompt, ft, code
  )

  vim.notify("Jarvis Inline: streaming refactor...", vim.log.levels.INFO)

  curl.post(server .. "/chat", {
    headers = {
      ["Content-Type"] = "application/json",
      ["Accept"] = "text/event-stream"
    },
    body = vim.fn.json_encode({ query = query, task_id = "inline_" .. os.time(), stream = true }),
    stream = vim.schedule_wrap(function(err, chunk, _)
      if err or not chunk then return end
      if not vim.api.nvim_buf_is_valid(bufnr) then return end
      
      for line in chunk:gmatch("[^\r\n]+") do
        if vim.startswith(line, "data: ") then
          local data_str = line:sub(7)
          if data_str ~= "[DONE]" then
            local ok, data = pcall(vim.fn.json_decode, data_str)
            if ok and data.token then
              -- Get current extmark position
              local mark = vim.api.nvim_buf_get_extmark_by_id(bufnr, ns, mark_id, {details = false})
              if mark and #mark > 0 then
                local r, c = mark[1], mark[2]
                -- Insert token at position
                local new_lines = vim.split(data.token, "\n", { plain = true })
                vim.api.nvim_buf_set_text(bufnr, r, c, r, c, new_lines)
              end
            end
          end
        end
      end
    end),
    callback = function(res)
      vim.schedule(function()
        vim.notify("Jarvis Inline: refactor complete", vim.log.levels.INFO)
      end)
    end,
  })
end

return M
