-- lua/jarvis/pin.lua
-- Jarvis Neovim Plugin — Pinned Context Buffers
--
-- Users can pin lines/selections which are automatically injected into every
-- coding agent prompt as a "## Pinned Context" block.
--
-- Public API:
--   M.pin_selection()        — add current visual selection (or cursor line) to pins
--   M.unpin_all()            — clear all pins
--   M.show_pins()            — open float listing all pinned snippets
--   M.get_context_block()    — returns markdown string to prepend to prompts

local M = {}

--- Internal list of pinned snippets.
--- Each entry: { file = string, lstart = int, lend = int, text = string, ft = string }
local _pins = {}

--- Get current visual selection range and text.
--- Falls back to the cursor line when not in visual mode.
--- @return string, string, number, number  text, filename, lstart, lend
local function _get_selection_info()
  local bufnr = vim.api.nvim_get_current_buf()
  local file   = vim.api.nvim_buf_get_name(bufnr)
  local ft     = vim.bo[bufnr].filetype
  local mode   = vim.fn.mode()

  local lstart, lend

  if mode == "v" or mode == "V" or mode == "\22" then
    -- Leave visual first so getpos works correctly
    vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "x", false)
    lstart = vim.fn.getpos("'<")[2] - 1
    lend   = vim.fn.getpos("'>")[2]
  else
    local row = vim.api.nvim_win_get_cursor(0)[1]
    lstart = row - 1
    lend   = row
  end

  local lines = vim.api.nvim_buf_get_lines(bufnr, lstart, lend, false)
  local text  = table.concat(lines, "\n")
  return text, file, ft, lstart + 1, lend
end

--- Pin the current visual selection or cursor line.
function M.pin_selection()
  local text, file, ft, lstart, lend = _get_selection_info()

  if not text or vim.trim(text) == "" then
    vim.notify("Jarvis Pin: empty selection, nothing pinned", vim.log.levels.WARN)
    return
  end

  -- Avoid exact duplicates
  for _, p in ipairs(_pins) do
    if p.file == file and p.lstart == lstart and p.lend == lend then
      vim.notify("Jarvis Pin: already pinned (lines " .. lstart .. "–" .. lend .. ")", vim.log.levels.INFO)
      return
    end
  end

  local entry = {
    file   = file,
    ft     = ft or "",
    lstart = lstart,
    lend   = lend,
    text   = text,
  }
  table.insert(_pins, entry)

  local short = vim.fn.fnamemodify(file, ":t")
  vim.notify(
    string.format("Jarvis Pin: pinned %s:%d–%d (%d pins total)", short, lstart, lend, #_pins),
    vim.log.levels.INFO
  )
end

--- Clear all pinned snippets.
function M.unpin_all()
  local count = #_pins
  _pins = {}
  vim.notify(string.format("Jarvis Pin: cleared %d pin(s)", count), vim.log.levels.INFO)
end

--- Remove a single pin by index (1-based). Used internally by show_pins.
function M.unpin(idx)
  if idx < 1 or idx > #_pins then return end
  table.remove(_pins, idx)
  vim.notify(string.format("Jarvis Pin: removed pin #%d (%d remaining)", idx, #_pins), vim.log.levels.INFO)
end

--- Returns the number of active pins.
function M.count()
  return #_pins
end

--- Build a markdown string to prepend to any agent prompt.
--- Returns an empty string when no pins are active.
--- @return string
function M.get_context_block()
  if #_pins == 0 then return "" end

  local lines = { "## Pinned Context", "" }
  for i, p in ipairs(_pins) do
    local short = vim.fn.fnamemodify(p.file, ":~:.")  -- relative path
    table.insert(lines, string.format("### Pin %d — %s (lines %d–%d)", i, short, p.lstart, p.lend))
    table.insert(lines, "```" .. p.ft)
    table.insert(lines, p.text)
    table.insert(lines, "```")
    table.insert(lines, "")
  end

  return table.concat(lines, "\n")
end

--- Open a floating window listing all pinned snippets.
function M.show_pins()
  if #_pins == 0 then
    vim.notify("Jarvis Pin: no pins active", vim.log.levels.INFO)
    return
  end

  local content = M.get_context_block()
  local header  = string.format("# Pinned Context (%d pin(s))\n\nUse `:JarvisUnpin` to clear all.\n\n", #_pins)

  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_option(buf, "buftype", "nofile")
  vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, vim.split(header .. content, "\n", { plain = true }))

  local width  = math.floor(vim.o.columns * 0.7)
  local height = math.min(#_pins * 8 + 6, math.floor(vim.o.lines * 0.7))
  local row    = math.floor((vim.o.lines - height) / 2)
  local col    = math.floor((vim.o.columns - width) / 2)

  vim.api.nvim_open_win(buf, true, {
    relative   = "editor",
    width      = width,
    height     = height,
    row        = row,
    col        = col,
    style      = "minimal",
    border     = "rounded",
    title      = " 📌 Pinned Context ",
    title_pos  = "center",
  })
  vim.api.nvim_buf_set_keymap(buf, "n", "q",     ":close<CR>", { noremap = true, silent = true })
  vim.api.nvim_buf_set_keymap(buf, "n", "<Esc>", ":close<CR>", { noremap = true, silent = true })
end

return M
