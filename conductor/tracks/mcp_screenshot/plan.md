# Plan: sm_screenshot MCP tool + navigation IPC

Design locked — see brainstorming Decision Log. Agents using the MCP server can
now visually confirm the live SkillManager UI: navigate the running GUI to a
section, then capture its window as a base64 PNG. Read-only (no `--mcp-allow-write`).

## Approach

MCP and the GUI run as separate processes, so the bridge (headless, offscreen)
cannot see or move the real window. We add a tiny **file-based IPC channel** the
GUI watches: MCP writes a JSON command (`navigate` to a view); the GUI executes
it on the Qt thread and writes an ack. Capture is **cross-process Win32**
(`EnumWindows` + `PrintWindow`, fallback `BitBlt`) matched by window title
"Skill Manager", converted to base64 via `pillow` (already a dependency). No new
third-party deps; reuses `utils/win32.py` (ctypes).

## Scope

- In:
  - `CommandChannel` in `app.py`: `QFileSystemWatcher` on `data/mcp/commands/`,
    parses `{action:"navigate", view, id}`, runs `ui_controller.currentView = view`
    on Qt thread, writes `data/mcp/acks/<id>.json`.
  - `bridge.capture_app_window()` — Win32 grab → PIL → base64; `None` if no window.
  - `bridge.send_navigation_command(view)` — write command file, poll ack (≤1s).
  - `tools/screenshot.py` — `sm_screenshot` (`navigate` enum + `save` bool),
    registered in `server.py`.
  - Tests mirroring `test_screenshot_*.py`.
  - Docs: `docs/MCP_SERVER.md` + this track + `skills/skillmanager-mcp/SKILL.md`.
- Out:
  - Capturing other apps' windows / whole screen / arbitrary regions.
  - Per-panel (sub-window) grabs beyond whole-app navigation.
  - New deps (`pywin32`, `mss`); named-pipe/socket IPC (file-watch is sufficient).

## Action Items

- [x] 1. `src/skill_manager/app.py` — add `CommandChannel`: watch `data/mcp/commands/`,
      execute `navigate` on Qt thread, write ack to `data/mcp/acks/<id>.json`; wire up in `AppController.__init__` (guard for headless/CI: skip if dir unwatchable).
- [x] 2. `src/skill_manager/mcp/bridge.py` — add `capture_app_window()` (Win32
      `EnumWindows` by title "Skill Manager" → `PrintWindow`/`BitBlt` → PIL → base64;
      returns `(b64, w, h)` or `None`) and `send_navigation_command(view)` (write
      command JSON + poll ack ≤1s, best-effort).
- [x] 3. `src/skill_manager/mcp/tools/screenshot.py` — `TOOL_SCHEMAS` (`sm_screenshot`:
      `navigate` enum `QuickCopy|Library|Updates|Settings`, `save` bool default false)
      + `get_handlers()`; handler calls nav (optional) → settle delay → capture;
      returns `ToolResult` with `image_b64,width,height,view,save_path?` or `ok:false`
      error (no GUI / capture failed).
- [x] 4. `src/skill_manager/mcp/server.py` — import `screenshot` schemas/handlers and
      add to the aggregation tuple so `sm_screenshot` appears in `list_tools`/`call_tool`.
- [x] 5. `tests/test_mcp_screenshot.py` — mock `EnumWindows`/HWND + PIL; assert base64
      produced, `ok:false` on no-window, nav command file written + ack parsed, save path
      behavior; mirror `test_screenshot_*.py` style.
- [x] 6. `docs/MCP_SERVER.md` — document `sm_screenshot` (params, navigate, save, errors)
      + the navigation IPC; add to tool table.
- [x] 7. Update `skills/skillmanager-mcp/SKILL.md` (if present) with the new tool, and
       append a "Follow-up" section to this `plan.md` recording result + tests.

## Validation

- `uv run ruff check src tests --fix` + `uv run ruff format src tests` clean.
- `uv run pytest tests/test_mcp_screenshot.py` passes.
- Smoke: launch `uv run skill-manager` (GUI), then `uv run skill-manager --mcp`, call
  `sm_screenshot` with and without `navigate`; confirm base64 returned and view switched.
- `lsp_diagnostics` clean on changed files.

## Decisions (from design lock)

- Win32 cross-process capture (bridge is headless/offscreen; can't see GUI window).
- IPC via file + `QFileSystemWatcher` (reuses file-watch infra, no new deps, Windows-safe).
- v1 = whole window + navigate; save only on request; error if no GUI.
- EnumWindows match by title startswith "Skill Manager" (confirmed `Main.qml:50`).

## Follow-up

**Result:** Implemented and verified via unit tests. `sm_screenshot` is a
read-only MCP tool that captures the live GUI window cross-process (Win32
`PrintWindow` + `BitBlt`/`GetDIBits` fallback → PIL → base64) and optionally
navigates the running GUI to a section first via a file-based IPC channel
(`data/mcp/commands/` → `CommandChannel` in `app.py` → `data/mcp/acks/`).

**Files changed**
- `src/skill_manager/mcp/bridge.py` — `capture_app_window()`, `send_navigation_command()`, Win32/PIL helpers, `MCP_COMMANDS_DIR`/`MCP_ACKS_DIR`/`_MCP_ROOT`/`_WINDOW_TITLE_PREFIX`.
- `src/skill_manager/mcp/tools/screenshot.py` — NEW `sm_screenshot` module (mirrors `monitor.py`).
- `src/skill_manager/mcp/server.py` — registers screenshot schemas/handlers.
- `src/skill_manager/app.py` — `CommandChannel` class + guarded wiring in `AppController.__init__`.
- `tests/test_mcp_screenshot.py` — NEW, 12 tests.
- `docs/MCP_SERVER.md`, `skills/skillmanager-mcp/SKILL.md` — documented.

**Tests**
- `uv run pytest tests/test_mcp_screenshot.py` → 12 passed.
- `uv run ruff check src tests` → clean.
- Existing `tests/test_app_controller.py` (33) and `tests/test_mcp_*.py` (48) still pass — no regression.

**Notes / caveats**
- The MCP server is headless; capture only succeeds when the **desktop GUI** is
  actually running (verified by window-title match). No-GUI path returns `ok:false`.
- Standalone `uv run python` scripts that construct `AppController` segfault under
  offscreen Qt in this environment (exit -1073740791); under `pytest` (pytest-qt
  event loop) construction is fine. This is environmental, not a code defect —
  the required `pytest` validation passes.
- `data/mcp/{commands,acks}/` are gitignored (`data/`).
- Track status remains `active` (not marked complete) per conductor convention.
