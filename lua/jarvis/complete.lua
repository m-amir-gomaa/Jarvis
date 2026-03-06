-- lua/jarvis/complete.lua
-- Jarvis Neovim Plugin — FIM Autocomplete Source for blink.cmp
-- Debounce: 800ms (raised from 300ms — CPU inference at 3-5 tok/s)

local M = {}
local curl = require("plenary.curl")
local debounce_timer = nil
local server = "http://localhost:7002"

-- FIM completion source compatible with blink.cmp
M.source = {}
M.source.name = "jarvis"

function M.source:get_completions(ctx, resolve)
  local config = require("jarvis").config
  if not config.enabled then
    resolve({ items = {}, isIncomplete = false })
    return
  end

  -- Cancel pending debounce
  if debounce_timer then
    debounce_timer:stop()
    debounce_timer = nil
  end

  -- Debounce 800ms before firing request
  debounce_timer = vim.loop.new_timer()
  debounce_timer:start(800, 0, vim.schedule_wrap(function()
    debounce_timer = nil

    local row, col = unpack(vim.api.nvim_win_get_cursor(0))
    local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
    local prefix_lines = vim.list_slice(lines, 1, row)
    prefix_lines[row] = string.sub(lines[row], 1, col)
    local suffix_lines = vim.list_slice(lines, row + 1)

    local prefix = table.concat(prefix_lines, "\n")
    local suffix = table.concat(suffix_lines, "\n")

    -- CRITICAL: suffix parameter required for proper FIM tokens
    curl.post(server .. "/complete", {
      headers = { ["Content-Type"] = "application/json" },
      body = vim.fn.json_encode({ prefix = prefix, suffix = suffix }),
      callback = function(res)
        vim.schedule(function()
          if not res or res.status ~= 200 then
            resolve({ items = {}, isIncomplete = false })
            return
          end
          local ok, data = pcall(vim.fn.json_decode, res.body)
          if not ok or not data.completion or data.completion == "" then
            resolve({ items = {}, isIncomplete = false })
            return
          end
          resolve({
            items = {
              {
                label = data.completion:sub(1, 60) .. "...",
                insertText = data.completion,
                kind = 15, -- Snippet
                detail = "Jarvis FIM (Qwen3-1.7B)",
                documentation = { kind = "markdown", value = "```\n" .. data.completion .. "\n```" },
              }
            },
            isIncomplete = false,
          })
        end)
      end,
    })
  end))
end

-- Register source with blink.cmp if available
function M.setup()
  local ok, blink = pcall(require, "blink.cmp")
  if ok then
    blink.add_source("jarvis", M.source)
  end
end

return M
