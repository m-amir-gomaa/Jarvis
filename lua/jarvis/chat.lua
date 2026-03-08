-- lua/jarvis/chat.lua
local M = {}
local curl = require("plenary.curl")
local server = "http://127.0.0.1:7002"

local last_request_id = nil

--- RAG-augmented chat with SSE streaming
--- Opens a floating window and streams tokens from the server.
--- @param extra_context string|nil Optional markdown context to prepend to the query.
function M.chat(extra_context)
  vim.ui.input({ prompt = "Jarvis chat: " }, function(query)
    if not query or query == "" then return end

    if extra_context and vim.trim(extra_context) ~= "" then
      query = extra_context .. "\n" .. query
    end

    vim.notify("Jarvis: thinking (RAG chat)...", vim.log.levels.INFO)

    local task_id = "chat_" .. os.time()
    last_request_id = task_id

    local buf = vim.api.nvim_create_buf(false, true)
    vim.api.nvim_buf_set_name(buf, "Jarvis Chat " .. task_id)
    vim.api.nvim_buf_set_option(buf, "buftype", "nofile")
    vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
    vim.api.nvim_buf_set_lines(buf, 0, -1, false, { "# Jarvis Chat", "", "**You:** " .. query, "", "**Jarvis:**", "" })
    
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
      title = " Jarvis Chat ",
      title_pos = "center",
    })
    vim.api.nvim_buf_set_keymap(buf, "n", "q", ":close<CR>", { noremap = true, silent = true })
    vim.api.nvim_buf_set_keymap(buf, "n", "<Esc>", ":close<CR>", { noremap = true, silent = true })
    
    local ns = vim.api.nvim_create_namespace("jarvis_chat")
    local row = vim.api.nvim_buf_line_count(buf) - 1
    local mark_id = vim.api.nvim_buf_set_extmark(buf, ns, row, 0, { right_gravity = false })

    curl.post(server .. "/chat", {
      headers = {
        ["Content-Type"] = "application/json",
        ["Accept"] = "text/event-stream"
      },
      body = vim.fn.json_encode({ query = query, task_id = task_id, stream = true }),
      stream = vim.schedule_wrap(function(err, chunk, _)
        if err or not chunk then return end
        if not vim.api.nvim_buf_is_valid(buf) then return end
        
        for line in chunk:gmatch("[^\r\n]+") do
          if vim.startswith(line, "data: ") then
            local data_str = line:sub(7)
            if data_str ~= "[DONE]" then
              local ok, data = pcall(vim.fn.json_decode, data_str)
              if ok and data.token then
                local mark = vim.api.nvim_buf_get_extmark_by_id(buf, ns, mark_id, {details = false})
                if mark and #mark > 0 then
                  local r, c = mark[1], mark[2]
                  local lines = vim.split(data.token, "\n", { plain = true })
                  vim.api.nvim_buf_set_text(buf, r, c, r, c, lines)
                end
              end
            end
          end
        end
      end),
      callback = function(res)
        if last_request_id == task_id then last_request_id = nil end
      end,
    })
  end)
end

return M
