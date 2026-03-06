-- lua/jarvis/agent.lua
-- Jarvis Neovim Plugin — Agent Commands
-- CRITICAL: ALL HTTP calls MUST be async via plenary.curl
-- NEVER use vim.fn.system() or io.popen() — they BLOCK Neovim for 30-90s on CPU

local M = {}
local curl = require("plenary.curl")
local server = "http://localhost:7002"

-- Helper: show spinner while waiting, update buffer when done
local function with_spinner(label, fn)
  vim.notify("Jarvis: " .. label .. "...", vim.log.levels.INFO)
  fn()
end

-- Helper: write response to a new scratch buffer
local function open_response_buf(title, content)
  vim.schedule(function()
    local buf = vim.api.nvim_create_buf(false, true)
    vim.api.nvim_buf_set_option(buf, "buftype", "nofile")
    vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
    vim.api.nvim_buf_set_name(buf, title)
    local lines = vim.split(content, "\n", { plain = true })
    vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
    vim.cmd("botright split")
    vim.api.nvim_win_set_buf(0, buf)
    vim.api.nvim_win_set_height(0, 15)
  end)
end

-- Get current visual selection or whole buffer
local function get_selection()
  local mode = vim.fn.mode()
  if mode == "v" or mode == "V" then
    local start = vim.fn.getpos("'<")
    local finish = vim.fn.getpos("'>")
    local lines = vim.api.nvim_buf_get_lines(0, start[2] - 1, finish[2], false)
    return table.concat(lines, "\n")
  end
  -- Fallback: whole buffer content (capped to 3000 chars)
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  local text = table.concat(lines, "\n")
  return text:sub(1, 3000)
end

-- /chat — RAG-augmented question answering
function M.chat()
  -- Prompt user for query
  vim.ui.input({ prompt = "Jarvis chat: " }, function(query)
    if not query or query == "" then return end

    with_spinner("thinking (RAG chat)", function()
      curl.post(server .. "/chat", {
        headers = { ["Content-Type"] = "application/json" },
        body = vim.fn.json_encode({ query = query }),
        callback = function(res)
          if res and res.status == 200 then
            local data = vim.fn.json_decode(res.body)
            open_response_buf("Jarvis Chat", data.response or "(no response)")
          else
            vim.schedule(function()
              vim.notify("Jarvis: server error or offline", vim.log.levels.ERROR)
            end)
          end
        end,
      })
    end)
  end)
end

-- /fix — run agent_loop for current buffer error
function M.fix()
  local diagnostics = vim.diagnostic.get(0, { severity = vim.diagnostic.severity.ERROR })
  if #diagnostics == 0 then
    vim.notify("Jarvis: no errors in current buffer", vim.log.levels.WARN)
    return
  end

  local code = get_selection()
  local errors = {}
  for _, d in ipairs(diagnostics) do
    table.insert(errors, string.format("Line %d: %s", d.lnum + 1, d.message))
  end

  local prompt = string.format(
    "Fix these errors in the following code:\n\nErrors:\n%s\n\nCode:\n```%s\n%s\n```",
    table.concat(errors, "\n"),
    vim.bo.filetype,
    code
  )

  with_spinner("thinking (fix loop 3-90s)", function()
    curl.post(server .. "/fix", {
      headers = { ["Content-Type"] = "application/json" },
      body = vim.fn.json_encode({ task = "fix", prompt = prompt, max_retries = 3 }),
      callback = function(res)
        if res and res.status == 200 then
          local data = vim.fn.json_decode(res.body)
          open_response_buf("Jarvis Fix", data.output or data.stderr or "(no output)")
        else
          vim.schedule(function()
            vim.notify("Jarvis /fix: error " .. (res and res.status or "offline"), vim.log.levels.ERROR)
          end)
        end
      end,
    })
  end)
end

-- /explain — explain current selection or buffer
function M.explain()
  local code = get_selection()
  with_spinner("explaining", function()
    curl.post(server .. "/explain", {
      headers = { ["Content-Type"] = "application/json" },
      body = vim.fn.json_encode({ code = code, language = vim.bo.filetype }),
      callback = function(res)
        if res and res.status == 200 then
          local data = vim.fn.json_decode(res.body)
          open_response_buf("Jarvis Explain", data.explanation or "(no response)")
        else
          vim.schedule(function()
            vim.notify("Jarvis /explain: offline?", vim.log.levels.WARN)
          end)
        end
      end,
    })
  end)
end

-- /index — index the current project
function M.index()
  local root = vim.fn.getcwd()
  vim.notify("Jarvis: indexing " .. root .. " (async)...", vim.log.levels.INFO)
  curl.post(server .. "/index", {
    headers = { ["Content-Type"] = "application/json" },
    body = vim.fn.json_encode({ root = root }),
    callback = function(res)
      if res and res.status == 200 then
        local data = vim.fn.json_decode(res.body)
        vim.schedule(function()
          vim.notify(
            string.format("Jarvis: indexed %d chunks ✓", data.chunks_indexed or 0),
            vim.log.levels.INFO
          )
        end)
      else
        vim.schedule(function()
          vim.notify("Jarvis /index: failed", vim.log.levels.ERROR)
        end)
      end
    end,
  })
end

return M
