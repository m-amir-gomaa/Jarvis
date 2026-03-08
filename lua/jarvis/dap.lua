-- lua/jarvis/dap.lua
-- Jarvis Neovim Plugin — Debug Adapter Protocol Configuration
-- Configured for: Rust (lldb), Python (debugpy)
-- Keys: F5=continue, F10=step-over, F11=step-into, b=breakpoint

local M = {}

--- Setup DAP (Debug Adapter Protocol) configurations
--- Configures adapters and configurations for Rust and Python.
--- Sets up key mappings (F5, F10, F11, b) and UI listeners.
function M.setup()
  local ok_dap, dap = pcall(require, "dap")
  if not ok_dap then
    return  -- nvim-dap not installed, graceful degradation
  end

  -- ── Rust / C / C++ via lldb ──────────────────────────────────────────────
  dap.adapters.lldb = {
    type = "executable",
    command = "lldb-dap",  -- installed via home-manager: pkgs.lldb
    name = "lldb",
  }

  dap.configurations.rust = {
    {
      name = "Launch executable",
      type = "lldb",
      request = "launch",
      program = function()
        return vim.fn.input("Path to executable: ", vim.fn.getcwd() .. "/target/debug/", "file")
      end,
      cwd = "${workspaceFolder}",
      stopOnEntry = false,
      args = {},
    },
  }
  dap.configurations.c = dap.configurations.rust
  dap.configurations.cpp = dap.configurations.rust

  -- ── Python via debugpy ────────────────────────────────────────────────────
  local jarvis_root = os.getenv("JARVIS_ROOT") or (os.getenv("HOME") .. "/NixOSenv/Jarvis")
  dap.adapters.python = {
    type = "executable",
    command = jarvis_root .. "/.venv/bin/python",
    args = { "-m", "debugpy.adapter" },
  }

  dap.configurations.python = {
    {
      type = "python",
      request = "launch",
      name = "Launch file",
      program = "${file}",
      pythonPath = jarvis_root .. "/.venv/bin/python",
    },
  }

  -- ── Key mappings ──────────────────────────────────────────────────────────
  local map = vim.keymap.set
  local opts = { noremap = true, silent = true }

  map("n", "<F5>",  function() dap.continue() end,           vim.tbl_extend("force", opts, { desc = "DAP: Continue" }))
  map("n", "<F10>", function() dap.step_over() end,          vim.tbl_extend("force", opts, { desc = "DAP: Step Over" }))
  map("n", "<F11>", function() dap.step_into() end,          vim.tbl_extend("force", opts, { desc = "DAP: Step Into" }))
  map("n", "b",     function() dap.toggle_breakpoint() end,  vim.tbl_extend("force", opts, { desc = "DAP: Toggle Breakpoint" }))

  local ok_ui, dapui = pcall(require, "dap-ui")
  if ok_ui then
    dap.listeners.after.event_initialized["dapui_config"] = function() dapui.open() end
    dap.listeners.before.event_terminated["dapui_config"] = function() dapui.close() end
  end

  vim.api.nvim_create_user_command("JarvisDebugAnalyze", M.analyze_exception, {})
end

--- Analyze the current exception or stack trace using Jarvis
--- Fetches the stack trace from the DAP session and sends it to the `/explain` endpoint.
function M.analyze_exception()
  local dap = require("dap")
  local session = dap.session()
  if not session then
    vim.notify("Jarvis DAP: No active debug session", vim.log.levels.WARN)
    return
  end

  session:request("stackTrace", { threadId = session.stopped_thread_id }, function(err, result)
    if err or not result or not result.stackFrames then
      vim.schedule(function() vim.notify("Jarvis DAP: Could not fetch stack trace", vim.log.levels.ERROR) end)
      return
    end

    local trace = {}
    for i, frame in ipairs(result.stackFrames) do
      table.insert(trace, string.format("Frame %d: %s at %s:%d", i, frame.name, frame.source and frame.source.path or "?", frame.line or 0))
      if i > 5 then break end
    end

    local prompt = "Analyze this exception stack trace during debugging:\n\n" .. table.concat(trace, "\n")
    vim.schedule(function() vim.notify("Jarvis DAP: Analyzing exception...", vim.log.levels.INFO) end)
    
    local curl = require("plenary.curl")
    curl.post("http://127.0.0.1:7002/explain", {
      headers = { ["Content-Type"] = "application/json" },
      body = vim.fn.json_encode({ code = prompt, language = "plaintext" }),
      callback = function(res)
        vim.schedule(function()
          if res and res.status == 200 then
            local data = vim.fn.json_decode(res.body)
            local buf = vim.api.nvim_create_buf(false, true)
            vim.api.nvim_buf_set_option(buf, "buftype", "nofile")
            vim.api.nvim_buf_set_option(buf, "filetype", "markdown")
            local lines = vim.split(data.explanation or "(no explanation)", "\n", { plain = true })
            vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
            
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
              title = " Jarvis DAP Analysis ",
              title_pos = "center",
            })
            vim.api.nvim_buf_set_keymap(buf, "n", "q", ":close<CR>", { noremap = true, silent = true })
            vim.api.nvim_buf_set_keymap(buf, "n", "<Esc>", ":close<CR>", { noremap = true, silent = true })
          else
            vim.notify("Jarvis DAP: Analysis failed", vim.log.levels.ERROR)
          end
        end)
      end
    })
  end)
end

return M
