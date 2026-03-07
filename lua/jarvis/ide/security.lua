-- lua/jarvis/ide/security.lua
-- Security bridge — async HTTP to Jarvis LSP HTTP sidecar (port 8001).
-- Handles immediate grants AND long-polls for OOB (out-of-band) approval.

local M = {}
local api_base     = "http://localhost:8001"
local _active_poll = false  -- Guard: only one outstanding long-poll curl at a time
local _conn_id     = nil    -- Set during setup(), passed to long-poll endpoint

function M.setup(opts)
  M.opts   = opts or {}
  _conn_id = M.opts.conn_id or nil
end

-- ── Public: request a capability ──────────────────────────────────────────────

function M.request_capability(cap, reason, callback)
  local body = vim.fn.json_encode({
    capability = cap,
    reason     = reason,
    scope      = "task"
  })

  vim.fn.jobstart({
    "curl", "-s", "-X", "POST",
    "-H", "Content-Type: application/json",
    "-d", body,
    api_base .. "/security/request"
  }, {
    on_stdout = function(_, data)
      local s = table.concat(data)
      if s == "" then return end
      local ok, result = pcall(vim.fn.json_decode, s)
      if not ok then callback(false); return end

      if result.granted then
        callback(true)
      elseif result.error == "pending" and result.pending_id then
        M._poll_pending(result.pending_id, callback, 0)
      else
        callback(false)
      end
    end,
    on_exit = function(_, code)
      if code ~= 0 then callback(false) end
    end
  })
end

-- ── Internal: long-poll for OOB grant resolution ──────────────────────────────

function M._poll_pending(pending_id, callback, attempts)
  local MAX_ATTEMPTS = 6  -- 6 × ~10s = ~60s max wait, matching spec
  if attempts >= MAX_ATTEMPTS then
    vim.schedule(function()
      vim.notify(
        "[Jarvis] Capability approval timed out. "
        .. "Run: jarvis approve " .. pending_id,
        vim.log.levels.WARN
      )
    end)
    callback(false)
    return
  end

  if _active_poll then
    -- Another poll in flight — back off and retry
    vim.defer_fn(function()
      M._poll_pending(pending_id, callback, attempts)
    end, 2000)
    return
  end

  _active_poll = true

  -- Include conn_id for per-connection queue isolation if available
  local url = api_base .. "/security/pending?timeout=10"
  if _conn_id and _conn_id ~= "" then
    url = url .. "&conn_id=" .. _conn_id
  end

  vim.fn.jobstart({ "curl", "-s", url }, {
    on_stdout = function(_, data)
      _active_poll = false
      local s = table.concat(data)

      -- Timeout response or empty body — retry
      if s == "" or s == '{"status":"timeout"}' then
        M._poll_pending(pending_id, callback, attempts + 1)
        return
      end

      local ok, result = pcall(vim.fn.json_decode, s)
      if not ok then
        M._poll_pending(pending_id, callback, attempts + 1)
        return
      end

      -- Check if this event belongs to our pending_id
      local pid = result.pending_id or ""
      if pid == pending_id then
        -- Our request was resolved
        local approved = result.granted == true
        callback(approved)
      else
        -- Unrelated notification — keep polling
        M._poll_pending(pending_id, callback, attempts + 1)
      end
    end,
    on_exit = function(_, code)
      _active_poll = false
      if code ~= 0 then
        M._poll_pending(pending_id, callback, attempts + 1)
      end
    end
  })
end

return M
