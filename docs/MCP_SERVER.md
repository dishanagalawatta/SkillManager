# MCP Server for SkillManager — Design & Tool Reference

> Status: DESIGN LOCKED (2026-07-20)
> Owner: Dishan Agalawatta
> Related: AGENTS.md, docs/ARCHITECTURE.md, docs/DEVELOPMENT.md

## 1. Purpose

Coding agents (opencode, Claude Code, Codex, etc.) currently can only shell out
to dev tooling. They cannot introspect the **live** PySide6 app — its skill/source/
project state, controller health, or diagnostics. This MCP server closes that gap
by exposing build / analyze / monitor / debug tools that bridge directly to the
in-process `AppController` and its sub-controllers.

## 2. Why not the 4 referenced projects?

| Repo | Lang | Result |
|------|------|--------|
| signal-slot/qtmcp | C++20/Qt6 | No Python bindings, tri-GPL — cannot embed in PySide6 |
| Palm1r/llmqore | C++20/Qt6 | No Python bindings (MIT, has `mcp-bridge` binary) |
| logos-co/logos-qt-mcp | C++ plugin + Node | C++ plugin must be compiled in; MIT/Apache |
| TheQtCompanyRnD/agent-skills | Hosted HTTP | Docs-only, no app introspection |

**Conclusion:** All are C++ or hosted-doc. The only embeddable path for a PySide6
app is a **native Python MCP server** using the official `mcp` SDK. logos-qt-mcp's
architecture (in-process inspector + separate MCP process) is the pattern we mirror,
but implemented in Python against `AppController` instead of a C++ plugin.

## 3. Architecture

- New launch mode `--mcp` added to `main()` in `app.py`. Boots Qt app +
  `AppController` (QML engine loads so controllers work; window-show watchdog
  skipped). Starts an `mcp.server.stdio` server.
- MCP runs on an asyncio loop bridged to the Qt event loop (Qt owns `app.exec()`;
  MCP pumps via `QEventLoop` / `QTimer`). Tools call `AppController` **in-memory**
  — zero IPC.
- Heavy tools (build, tests) delegate to the existing `BackgroundTaskRunner` and
  return a job id + `sm_job_status` poll, so stdio never blocks.

### Module layout (`src/skill_manager/mcp/`)
```
mcp/
  __init__.py          # registers server with main()
  server.py            # MCPServer factory, stdio transport, tool registry
  bridge.py            # thin wrappers over AppController + sub-controllers
  models.py            # pydantic request/response schemas
  tools/
    build.py           # sm_lint, sm_run_tests, sm_build
    analyze.py         # sm_list_skills, sm_list_sources, sm_list_projects, sm_static_analyze
    monitor.py         # sm_get_diagnostics, sm_get_health, sm_tail_events, sm_profile
    debug.py           # sm_dump_state, sm_inspect_controller, sm_capture_errors
    screenshot.py      # sm_screenshot  (read-only; cross-process GUI capture + nav IPC)
    write.py           # sm_delete_skill, sm_deploy  (gated: --mcp-allow-write)
```

### Lifecycle guard
- `--mcp` uses its own mutex `SkillManagerMcpMutex` (never fights the GUI instance).
- Write tools refuse paths under `TODO.md`, `.agents/commands/`, `.agents/skills/`
  (AGENTS.md exclusions).
- `--mcp-allow-write` absent → write tools return `{ok:false, error:"write mode disabled"}`.

## 4. Tool Surface

All tools return structured JSON, names prefixed `sm_`.

**Build** (always on)
- `sm_lint` — `ruff check src tests`, structured error list.
- `sm_run_tests` — `pytest` (subset/full), pass/fail/coverage. Async.
- `sm_build` — `skill-manager-build` (PyInstaller), artifact path. Async.

**Analyze** (always on)
- `sm_list_skills` — from `AppController._library_model`.
- `sm_list_sources` / `sm_list_projects` — configured sources & deploy targets.
- `sm_static_analyze` — safe in-repo symbol/pattern search (respects `.gitignore`).

**Monitor** (always on)
- `sm_get_diagnostics` — from `get_diagnostic_logger()` buffer.
- `sm_get_health` — Qt loop alive? controller loaded? model counts; recent exceptions.
- `sm_tail_events` — last N telemetry / `capture_event` entries.
- `sm_profile` — run the discovery pipeline with per-stage timing and report the
  identified bottleneck. Read-only; supports `force_full_scan` to also measure the
  cold (full filesystem scan) path. Useful for perf investigations without a profiler.

**Debug** (always on)
- `sm_dump_state` — serialize `AppController` key state to JSON.
- `sm_inspect_controller` — list a controller's public methods/signals.
- `sm_capture_errors` — in-memory / Sentry error buffer.

**Visual** (always on, read-only)
- `sm_screenshot` — capture the live GUI window (title "Skill Manager") as a
  base64 PNG, cross-process via Win32 `PrintWindow`. Optional `navigate`
  (`QuickCopy` | `Library` | `Updates` | `Settings`) switches the running GUI to
  that section first through a file-based IPC channel; `save=true` also writes the
  PNG to `.agents/screenshots/`. GUI not running → `ok=false`.

**GUI Interaction** (always on, Windows-only)
- `sm_mouse_move` — move the system cursor to absolute screen pixel coordinates.
- `sm_mouse_click` — click a mouse button at optional (x, y); supports
  left/right/middle and double-click.
- `sm_type_text` — type text (alphanumeric, symbols, Enter, Tab) into the
  currently focused window.
- `sm_get_window_info` — return the live SkillManager window geometry (left, top,
  right, bottom, width, height) for calculating click targets.

**Write** (gated `--mcp-allow-write`)
- `sm_delete_skill`, `sm_deploy` — delegate to `OpsController`/`AppController`.
  Audit-log each call. Refuse AGENTS.md-excluded paths.

## 5. Error Handling & Observability

- `safe_tool()` decorator: catches exceptions → `{ok:false, error, tool}`.
- Job timeouts: build 300s, tests 600s → `timeout` status.
- Every tool call → `capture_event("mcp_tool_call", {tool, args})` (reuse existing
  diagnostics — you can monitor the *agent's* MCP usage).

## 6. Testing

- `tests/test_mcp_*.py`: unit each bridge fn with mocked `AppController`
  (reuse `tests/conftest.py` fixtures); integration launching server in-process
  over an in-memory stdio pipe. No GUI required (controllers build headless,
  see `test_app_controller.py`). Coverage target 80%.

## 7. Docs / Handoff

- New `docs/MCP_SERVER.md` (this file) — transport, launch, tool reference,
  `.mcp.json` snippet.
- Update `README.md` dev section + `AGENTS.md` quick-reference table.
- Provide `.mcp.json` example for opencode / Claude Code.
- Follow-up: optionally add the hosted **Qt Documentation MCP**
  (`https://qt-docs-mcp.qt.io/mcp`) as a 2nd server for docs-aware coding
  (zero build cost, official, version-pinned Qt 6.8.4 / 6.11.0).

## 8. Decision Log

| Decision | Alternatives | Why |
|---|---|---|
| Native Python `mcp` SDK, stdio | C++ refs, hosted docs MCP | Only embeddable path in PySide6 |
| In-process (`--mcp`) | Out-of-process IPC, build-only | Direct `AppController` access, no IPC bugs |
| Full lifecycle tools | Analyze/monitor-only | Matches explicit user ask |
| Write tools gated `--mcp-allow-write` | Always-open, read-only | Respects AGENTS.md exclusions by default |

## Client Setup (.mcp.json)

Drop a `.mcp.json` at the project root so opencode / Claude Code can launch the
server. The agent **must run from the project root** so `uv` resolves the
workspace and the `skill-manager` command is on PATH.

```json
{
  "mcpServers": {
    "skillmanager": {
      "command": "uv",
      "args": ["run", "skill-manager", "--mcp"]
    },
    "skillmanager-write": {
      "command": "uv",
      "args": ["run", "skill-manager", "--mcp", "--mcp-allow-write"]
    }
  }
}
```

- `skillmanager` — all read-only tools (build / analyze / monitor / debug / screenshot / gui).
- `skillmanager-write` — same plus mutating tools `sm_delete_skill`, `sm_deploy`.
  Only add this entry when the agent is trusted to modify skills/deployments.

For **opencode**, the server can be configured in `opencode.jsonc` instead:

```jsonc
{
  "mcp": {
    "skillmanager": {
      "type": "local",
      "command": ["uv", "run", "skill-manager", "--mcp"],
      "enabled": true,
      "description": "SkillManager MCP server"
    }
  }
}
```

### Tool reference

| Tool | What it does | Gated? |
|------|--------------|--------|
| `sm_lint` | Run `ruff check src tests`, return structured error list | No |
| `sm_run_tests` | Run `pytest` (subset/full), return pass/fail/coverage | No |
| `sm_build` | Run `skill-manager-build` (PyInstaller), return artifact path | No |
| `sm_job_status` | Poll status of an async build/test job by id | No |
| `sm_list_skills` | List skills from `AppController._library_model` | No |
| `sm_list_sources` | List configured skill sources | No |
| `sm_list_projects` | List configured deploy target projects | No |
| `sm_static_analyze` | Safe in-repo symbol/pattern search (respects `.gitignore`) | No |
| `sm_get_diagnostics` | Return diagnostic logger buffer | No |
| `sm_get_health` | Report Qt loop / controller / model health | No |
| `sm_tail_events` | Return last N telemetry / `capture_event` entries | No |
| `sm_profile` | Run discovery pipeline with per-stage timing; report bottleneck | No |
| `sm_dump_state` | Serialize `AppController` key state to JSON | No |
| `sm_inspect_controller` | List a controller's public methods/signals | No |
| `sm_capture_errors` | Return in-memory / Sentry error buffer | No |
| `sm_screenshot` | Capture the live GUI window as base64 PNG; optional `navigate`/`save` | No |
| `sm_mouse_move` | Move the system cursor to (x, y) screen coordinates | No |
| `sm_mouse_click` | Click left/right/middle mouse button, optional (x, y), double-click | No |
| `sm_type_text` | Type text into the currently focused window | No |
| `sm_get_window_info` | Return live GUI window geometry + HWND | No |
| `sm_delete_skill` | Delete a skill (delegates to `OpsController`) | Yes (`--mcp-allow-write`) |
| `sm_deploy` | Deploy a skill to a target project | Yes (`--mcp-allow-write`) |

### `sm_screenshot` — GUI capture & navigation

Captures the **running** SkillManager desktop window and (optionally) drives it to
a different section before capturing. Read-only; never opens or owns a GUI.

**Parameters**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `navigate` | string (enum) | — | One of `QuickCopy`, `Library`, `Updates`, `Settings`. Switches the live GUI to that section before capture. Omit to capture the current view. |
| `save` | boolean | `false` | When `true`, also writes the PNG to `.agents/screenshots/Screenshot_<timestamp>.png` and returns `save_path`. |

**Response envelope**

```json
{ "ok": true, "tool": "sm_screenshot",
  "data": { "image_base64": "<PNG, base64>", "width": 1280, "height": 800,
            "view": "Library", "saved": false } }
```

- `view` is the requested `navigate` value, or the current view when omitted.
- `saved` / `save_path` reflect the `save` flag.

**Errors**

- GUI not running (no window whose title starts with "Skill Manager") →
  `{"ok": false, "error": "SkillManager GUI window not found"}`.
- Invalid `navigate` value → `{"ok": false, "error": "invalid navigate value: <v>"}`.
- Navigation command not acknowledged within 1s →
  `{"ok": false, "error": "navigation to <view> not acknowledged by GUI"}`.

**Navigation IPC (file-based, cross-process)**

The MCP server and the GUI run in separate processes, so navigation uses a
drop-dir contract under `data/mcp/` (gitignored):

1. Server writes `data/mcp/commands/<uuid>.json`:
   `{"action": "navigate", "view": "<view>", "id": "<uuid>"}`.
2. The GUI's `CommandChannel` (`app.py`, a `QFileSystemWatcher` on
   `data/mcp/commands/`) receives `directoryChanged`, parses the command, validates
   the view, sets `self.app.ui.currentView` on the Qt thread, then writes
   `data/mcp/acks/<uuid>.json`: `{"ok": true, "view": "<view>"}` (or
   `{"ok": false, "error": "..."}`).
3. Server polls for the ack up to 1s, then deletes both files.

This keeps the MCP server headless and never touches `ScreenshotController`
(the in-app annotation tool, which is blank when headless). Capture uses Win32
`PrintWindow` with a `PW_RENDERFULLCONTENT` fallback to `BitBlt` + `GetDIBits`
(via `ctypes` + `PIL`), so it works even if the window is partially obscured.

### `sm_mouse_click` / `sm_mouse_move` — GUI interaction

These tools operate on the **running** SkillManager desktop window by sending
Win32 mouse events cross-process. They do not require the MCP server to own
the window — they work with any visible desktop window.

**`sm_mouse_move` parameters**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `x` | integer | Yes | Absolute screen X coordinate |
| `y` | integer | Yes | Absolute screen Y coordinate |

**`sm_mouse_click` parameters**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `x` | integer | — | Optional: move cursor here first; omit to click at current position |
| `y` | integer | — | Optional: paired with `x` |
| `button` | string | `"left"` | One of `"left"`, `"right"`, `"middle"` |
| `double` | boolean | `false` | Double-click when `true` |

**`sm_type_text` parameters**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `text` | string | Yes | Text to type. Supports A-Z, 0-9, common symbols, Space, Enter, Tab. Shift-key modulation handled automatically. |

**`sm_get_window_info` response**

Returns the SkillManager window's current geometry. Use the coordinates to
calculate click targets relative to the window:

```json
{ "ok": true, "tool": "sm_get_window_info",
  "data": { "ok": true, "hwnd": 123456, "left": 100, "top": 200,
            "right": 1152, "bottom": 950, "width": 1052, "height": 750 } }
```

**Typical workflow**

1. `sm_get_window_info` → get window position
2. `sm_screenshot` → capture current view
3. Calculate click target: `screen_x = window.left + offset_x`, `screen_y = window.top + offset_y`
4. `sm_mouse_click(x=screen_x, y=screen_y)` → click the target
5. `sm_screenshot` → verify result
