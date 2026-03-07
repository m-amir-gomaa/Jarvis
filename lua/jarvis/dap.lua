-- lua/jarvis/dap.lua
-- Jarvis Neovim Plugin — Debug Adapter Protocol Configuration
-- Configured for: Rust (lldb), Python (debugpy)
-- Keys: F5=continue, F10=step-over, F11=step-into, b=breakpoint

local M = {}

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
end

return M
