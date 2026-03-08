local pickers = require("telescope.pickers")
local finders = require("telescope.finders")
local conf = require("telescope.config").values
local actions = require("telescope.actions")
local action_state = require("telescope.actions.state")

local M = {}

M.select_mcp_tool = function(opts)
  opts = opts or {}
  
  -- In a full implementation, this would dynamically fetch from the Jarvis MCP Server
  -- via jobstart or LSP.
  local mcp_tools = {
      { name = "search_rag", description = "Search Jarvis internal RAG knowledge base" },
      { name = "web_search", description = "Search the web for information" },
  }

  pickers.new(opts, {
    prompt_title = "Jarvis MCP Tools",
    finder = finders.new_table({
      results = mcp_tools,
      entry_maker = function(entry)
        return {
          value = entry,
          display = string.format("%-15s │ %s", entry.name, entry.description),
          ordinal = entry.name .. " " .. entry.description,
        }
      end
    }),
    sorter = conf.generic_sorter(opts),
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local selection = action_state.get_selected_entry()
        if selection then
            -- Execute the tool via Jarvis CLI or notify the user
            vim.notify("Executed Jarvis MCP Tool: " .. selection.value.name, vim.log.levels.INFO)
            -- Example execution:
            -- vim.fn.jobstart({"jarvis", "mcp", "call", selection.value.name})
        end
      end)
      return true
    end,
  }):find()
end

return M
