-- lua/jarvis/ide/chat.lua
-- Floating chat window for inline Jarvis conversations.

local M = {}
local api_base = "http://localhost:8001"
local _chat_buf  = nil
local _chat_win  = nil
local _history   = {}

local function create_float()
  local width  = math.floor(vim.o.columns * 0.6)
  local height = math.floor(vim.o.lines * 0.7)
  local row    = math.floor((vim.o.lines - height) / 2)
  local col    = math.floor((vim.o.columns - width) / 2)

  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
  vim.api.nvim_buf_set_option(buf, "bufhidden", "wipe")

  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor",
    width    = width,
    height   = height,
    row      = row,
    col      = col,
    style    = "minimal",
    border   = "rounded",
    title    = " Jarvis Chat ",
    title_pos = "center",
  })

  return buf, win
end

local function render_history(buf)
  local lines = { "# Jarvis Chat", "" }
  for _, turn in ipairs(_history) do
    if turn.role == "user" then
      table.insert(lines, "**You:** " .. turn.content)
    else
      table.insert(lines, "**Jarvis:** " .. turn.content)
    end
    table.insert(lines, "")
  end
  table.insert(lines, "---")
  table.insert(lines, "_Type your message and press <CR> to send. <Esc> or q to close._")
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
end

function M.open()
  if _chat_win and vim.api.nvim_win_is_valid(_chat_win) then
    vim.api.nvim_set_current_win(_chat_win)
    return
  end

  _chat_buf, _chat_win = create_float()
  render_history(_chat_buf)

  -- Keymaps
  vim.api.nvim_buf_set_keymap(_chat_buf, "n", "q",    ":close<CR>", { noremap = true, silent = true })
  vim.api.nvim_buf_set_keymap(_chat_buf, "n", "<Esc>",":close<CR>", { noremap = true, silent = true })
  vim.api.nvim_buf_set_keymap(_chat_buf, "n", "<CR>", "", {
    noremap = true, silent = true,
    callback = function()
      local row = vim.api.nvim_win_get_cursor(_chat_win)[1]
      local line = vim.api.nvim_buf_get_lines(_chat_buf, row - 1, row, false)[1] or ""
      if line and line ~= "" then M.send(line) end
    end
  })
end

function M.send(text)
  if not text or text == "" then return end
  table.insert(_history, { role = "user", content = text })
  render_history(_chat_buf)

  local body = vim.fn.json_encode({ message = text, history = _history })
  vim.fn.jobstart({
    "curl", "-s", "-X", "POST",
    "-H", "Content-Type: application/json",
    "-d", body,
    api_base .. "/ide/chat"
  }, {
    on_stdout = function(_, data)
      local s = table.concat(data)
      if s == "" then return end
      local ok, result = pcall(vim.fn.json_decode, s)
      if ok and result.response then
        table.insert(_history, { role = "assistant", content = result.response })
        if _chat_buf and vim.api.nvim_buf_is_valid(_chat_buf) then
          vim.schedule(function() render_history(_chat_buf) end)
        end
      end
    end
  })
end

return M
