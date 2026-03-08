-- lua/jarvis/agent.lua
-- Jarvis Neovim Plugin — Agent Commands
-- CRITICAL: ALL HTTP calls MUST be async via plenary.curl
-- NEVER use vim.fn.system() or io.popen() — they BLOCK Neovim for 30-90s on CPU

local M = {}
local curl = require("plenary.curl")
local server = "http://127.0.0.1:7002"

-- Helper: show spinner while waiting, update buffer when done
local function with_spinner(label, fn)
  vim.notify("Jarvis: " .. label .. "...", vim.log.levels.INFO)
  fn()
end

-- Helper: write response to a new scratch buffer
local last_request_id = nil

local function open_response_buf(title, content)
  vim.schedule(function()
    -- Check if buffer already exists by name
    local buf_exists = vim.fn.bufexists(title) ~= 0
    local buf
    
    if buf_exists then
      buf = vim.fn.bufnr(title)
    else
      buf = vim.api.nvim_create_buf(false, true)
      vim.api.nvim_buf_set_name(buf, title)
    end
    
    vim.api.nvim_buf_set_option(buf, "buftype", "nofile")
    vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
    
    local lines = vim.split(content, "\n", { plain = true })
    vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
    
    -- Only open a new window if the buffer isn't already visible
    local win = vim.fn.bufwinid(buf)
    if win == -1 then
      local width = math.floor(vim.o.columns * 0.8)
      local height = math.floor(vim.o.lines * 0.8)
      local row = math.floor((vim.o.lines - height) / 2)
      local col = math.floor((vim.o.columns - width) / 2)
      
      vim.api.nvim_open_win(buf, true, {
        relative = "editor",
        width = width,
        height = height,
        row = row,
        col = col,
        style = "minimal",
        border = "rounded",
        title = " " .. title .. " ",
        title_pos = "center",
      })
      -- Easy close via q and Esc
      vim.api.nvim_buf_set_keymap(buf, "n", "q", ":close<CR>", { noremap = true, silent = true })
      vim.api.nvim_buf_set_keymap(buf, "n", "<Esc>", ":close<CR>", { noremap = true, silent = true })
    end
  end)
end

-- /cancel — cancel the latest long-running task
function M.cancel()
  if not last_request_id then
    vim.notify("Jarvis: no active task to cancel", vim.log.levels.WARN)
    return
  end
  
  curl.post(server .. "/cancel", {
    headers = { ["Content-Type"] = "application/json" },
    body = vim.fn.json_encode({ task_id = last_request_id }),
    callback = function(res)
      vim.schedule(function()
        if res and res.status == 200 then
          vim.notify("Jarvis: task cancelled ✓", vim.log.levels.INFO)
          last_request_id = nil
        else
          vim.notify("Jarvis: cancel failed (already done?)", vim.log.levels.WARN)
        end
      end)
    end,
  })
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
  require("jarvis.chat").chat()
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
    local task_id = "fix_" .. os.time()
    last_request_id = task_id
    curl.post(server .. "/fix", {
      headers = { ["Content-Type"] = "application/json" },
      body = vim.fn.json_encode({ task = "fix", prompt = prompt, max_retries = 3, task_id = task_id }),
      callback = function(res)
        if last_request_id == task_id then last_request_id = nil end
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
-- Explain the diagnostic error under the cursor
function M.explain_error()
  local line = vim.api.nvim_win_get_cursor(0)[1] - 1
  local diagnostics = vim.diagnostic.get(0, { lnum = line })
  
  if #diagnostics == 0 then
    vim.notify("Jarvis: no diagnostic at cursor", vim.log.levels.INFO)
    return
  end
  
  -- Get the first error/warning
  local diag = diagnostics[1]
  local error_msg = diag.message
  local context = table.concat(vim.api.nvim_buf_get_lines(0, line - 2, line + 3, false), "\n")
  
  with_spinner("analyzing error", function()
    curl.post(server .. "/analyze_error", {
      headers = { ["Content-Type"] = "application/json" },
      body = vim.fn.json_encode({
        error = error_msg,
        context = context,
        language = vim.bo.filetype
      }),
      callback = function(res)
        vim.schedule(function()
          if res and res.status == 200 then
            local data = vim.fn.json_decode(res.body)
            -- Show as virtual text on the current line
            local ns = vim.api.nvim_create_namespace("jarvis_lens")
            vim.api.nvim_buf_clear_namespace(0, ns, 0, -1)
            vim.api.nvim_buf_set_extmark(0, ns, line, 0, {
              virt_text = { { "󱐋 " .. data.analysis, "Comment" } },
              virt_text_pos = "eol",
            })
            -- Also show in a notification for clarity
            vim.notify("Jarvis Fix: " .. data.analysis, vim.log.levels.INFO)
          end
        end)
      end,
    })
  end)
end

-- Generate a semantic commit message for staged changes
function M.generate_commit()
  local diff = vim.fn.system("git diff --staged")
  if diff == "" then
    vim.notify("Jarvis: no staged changes", vim.log.levels.WARN)
    return
  end
  
  with_spinner("writing commit message", function()
    curl.post(server .. "/summarize_git", {
      headers = { ["Content-Type"] = "application/json" },
      body = vim.fn.json_encode({ diff = diff }),
      callback = function(res)
        vim.schedule(function()
          if res and res.status == 200 then
            local data = vim.fn.json_decode(res.body)
            open_response_buf("Jarvis Commit", data.summary)
          else
            vim.notify("Jarvis: git summarize failed", vim.log.levels.ERROR)
          end
        end)
      end,
    })
  end)
end

-- Global Web Research via SearXNG
function M.search(query)
  if not query or query == "" then
    vim.ui.input({ prompt = "Jarvis Search: " }, function(input)
      if input then M.search(input) end
    end)
    return
  end
  
  with_spinner("searching the web", function()
    curl.post(server .. "/research_manual", {
      headers = { ["Content-Type"] = "application/json" },
      body = vim.fn.json_encode({ query = query }),
      callback = function(res)
        vim.schedule(function()
          if res and res.status == 200 then
            local data = vim.fn.json_decode(res.body)
            if data.file then
              vim.cmd("edit " .. data.file)
              vim.notify("Jarvis Research complete: " .. query, vim.log.levels.INFO)
            else
              vim.notify("Jarvis: research failed (no file path)", vim.log.levels.ERROR)
            end
          else
            vim.notify("Jarvis: search service error", vim.log.levels.ERROR)
          end
        end)
      end,
    })
  end)
end

-- Prefetch models to RAM based on context
local prefetch_lock = {}
function M.prefetch(alias)
  if prefetch_lock[alias] then return end
  prefetch_lock[alias] = true
  
  curl.post(server .. "/prefetch", {
    headers = { ["Content-Type"] = "application/json" },
    body = vim.fn.json_encode({ model_alias = alias }),
    callback = function() 
      vim.defer_fn(function() prefetch_lock[alias] = false end, 60000) -- Unlock after 1 min
    end
  })
end

function M.prefetch_for_buffer()
  local ft = vim.bo.filetype
  -- Prime 'chat' (14B) for code-heavy files
  if ft == "python" or ft == "rust" or ft == "nix" or ft == "lua" or ft == "javascript" then
    M.prefetch("chat")
  end
  -- Prime 'complete' (1.7B) for all files when in insert mode
  -- (Triggered via autocommand)
end

function M.explain()
  local code = get_selection()
  with_spinner("explaining", function()
    local task_id = "explain_" .. os.time()
    last_request_id = task_id
    curl.post(server .. "/explain", {
      headers = { ["Content-Type"] = "application/json" },
      body = vim.fn.json_encode({ code = code, language = vim.bo.filetype, task_id = task_id }),
      callback = function(res)
        if last_request_id == task_id then last_request_id = nil end
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

-- Manage model aliases dynamically
function M.switch_model()
  curl.get(server .. "/models/list", {
    callback = function(res)
      if not res or res.status ~= 200 then
        vim.schedule(function() vim.notify("Jarvis: failed to fetch models", vim.log.levels.ERROR) end)
        return
      end
      
      local data = vim.fn.json_decode(res.body)
      local aliases = {}
      for k, _ in pairs(data.aliases) do table.insert(aliases, k) end
      table.sort(aliases)
      
      vim.schedule(function()
        vim.ui.select(aliases, { prompt = "Select alias to update:" }, function(alias)
          if not alias then return end
          
          local current = data.aliases[alias]
          local options = { "local/qwen3:14b-q4_K_M", "local/qwen3:8b", "local/qwen3:1.7b", "local/qwen2.5-coder:7b-instruct" }
          
          -- Add discovered ollama models
          for _, m in ipairs(data.available_ollama) do
            local spec = "local/" .. m
            local found = false
            for _, o in ipairs(options) do if o == spec then found = true break end end
            if not found then table.insert(options, spec) end
          end
          
          -- Add cloud options if providers exist
          for _, p in ipairs(data.available_providers) do
            if p ~= "ollama" then
              table.insert(options, "external/" .. p .. "/[enter-name]")
            end
          end
          
          vim.ui.select(options, { prompt = string.format("Update %s (current: %s):", alias, current) }, function(choice)
            if not choice then return end
            
            local final_spec = choice
            if choice:find("%[enter%-name%]") then
              vim.ui.input({ prompt = "Enter model name for " .. choice:match("external/([^/]+)") .. ":" }, function(input)
                if input and input ~= "" then
                  final_spec = choice:gsub("%[enter%-name%]", input)
                  M._update_alias_request(alias, final_spec)
                end
              end)
            else
              M._update_alias_request(alias, final_spec)
            end
          end)
        end)
      end)
    end
  })
end

function M._update_alias_request(alias, spec)
  curl.post(server .. "/models/set_alias", {
    headers = { ["Content-Type"] = "application/json" },
    body = vim.fn.json_encode({ alias = alias, spec = spec }),
    callback = function(res)
      vim.schedule(function()
        if res and res.status == 200 then
          vim.notify(string.format("Jarvis: %s updated to %s ✓", alias, spec), vim.log.levels.INFO)
        else
          vim.notify("Jarvis: failed to update alias", vim.log.levels.ERROR)
        end
      end)
    end
  })
end

return M
