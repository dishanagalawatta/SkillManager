# Agent Instructions

> This file defines constraints, conventions, and workflows for AI agents
> and human contributors working on SkillManager. Keep it concise.

## Core Constraints

### Exclusions (never modify)

| Path | Reason |
|------|--------|
| `TODO.md` | User-managed task list |
| `.agents/commands/**` | User-managed agent commands |
| `.agents/skills/**` | Installed agent skills |
| `image/TODO/**` | Packaging reference screenshots |

### Mandatory Rules

1. **Entry point**: Always use `uv run python -m skill_manager.__main__` for development.
2. **QML lifecycle**: Clear `cacheBuffer` before setting `model = null` to prevent incubation destruction exceptions.
3. **Threading**: Never block the PySide6 event loop. Heavy work runs on `joblib.Parallel` or `BackgroundTaskRunner`.
4. **Telemetry**: Never log or commit API tokens. `.env` is gitignored.
5. **Git revert**: Any `git checkout --`, `git revert`, `git reset` (hard/mixed), or any other command that discards or reverts changes must be approved by the user first. Tag the user for confirmation before executing.
6. **UI Validation (REAL APP ONLY — ZERO TOLERANCE)**: After EVERY change involving layout, positioning, visibility, or text rendering in QML (including debugging/fixing text clipping), you MUST visually verify using `look_at` on a screenshot of the REAL running app (`uv run skill-manager`).

   **EXPLICITLY FORBIDDEN (automatic violation)**
   - ❌ Writing inline QML (`qml = '''...'''`) in Python test scripts
   - ❌ Creating temporary `.qml` files under `/tmp/` or anywhere outside `src/skill_manager/SkillManagerComponents/`
   - ❌ Instantiating `QQmlApplicationEngine` in test scripts with ad-hoc QML content
   - ❌ Using `grabWindow()` or any capture method on anything other than the real `Main.qml` loaded through the real `AppController`
   - ❌ Running UI/rendering tests through pytest (these are for logic/contract testing only)
   - ❌ Referencing old/stale screenshot captures from previous verification runs

   The ONLY valid verification procedure is:
   (a) Start the real app via `uv run skill-manager`
   (b) Identify ALL views/panels affected by the change (Library, QuickCopy, etc.) — verify EACH ONE, not just the first one you think of
   (c) For each affected view:
       - Navigate to that view
       - Select a skill that exercises the changed code path
       - Wait for QML to settle (at least 3s after selectSkill)
       - Verify QML debug logs (INSPECTOR_DEBUG, LAYOUT_CHAIN) confirm the expected state
   (d) Capture a screenshot using `PySide6.QtGui.QWindow.grabWindow()` from a helper script that shares the same process as the real AppController — do NOT use IPC `CommandChannel` capture (grabs wrong region in headless/multiscreen environments)
   (e) Clean all captures from `data/mcp/captures/` BEFORE each run so no stale screenshot is accidentally re-analyzed
   (f) Pass the NEW screenshot to `look_at` for analysis
   (g) CONFIRM the active view in the screenshot matches the expected view (Library vs QuickCopy vs Settings) — if the view is wrong, fix the verification script and retake
   
   **CRITICAL: Visual Evidence Overrides Properties**: A `look_at` analysis showing clipped/truncated/overflowing text takes ABSOLUTE PRIORITY over any QML property values (`contentHeight`, `contentWidth`, `implicitHeight`, etc.) or debug logging. If the screenshot shows clipping, the fix is INCOMPLETE — do not rationalize away visual evidence with property values. Investigate ALL visual issues `look_at` reports, not just the one you were checking.

   **Enforcement**: Any violation of this rule triggers IMMEDIATE REVERSION of all unverified QML changes and restart from last known-good state. Do NOT mark any UI/rendering work complete without real-app visual validation evidence.

7. **Input Injection Safety (ZERO TOLERANCE)**: Real mouse/keyboard injection (`ydotool` uinput, `pyautogui`, Win32 `keybd_event`/`SendInput`) sends input to the user's live desktop. It MUST NEVER run from tests, CI, or headless processes, and MCP input tools MUST NEVER inject into a window that is not the live SkillManager GUI.
   - **Single source of truth**: ALL injection safety decisions MUST route through `src/skill_manager/utils/input_guard.py` — `injection_allowed()` (env guard: pytest/offscreen) and `injection_refused_reason()` (adds GUI-window presence check). Never add a new injection path or guard check anywhere else.
   - **Patch target**: Tests that exercise injection code MUST patch `skill_manager.utils.input_guard.*` (or the module-level name imported by the caller, e.g. `utils.linux.injection_allowed`). NEVER patch a platform module by guesswork — the original incident happened because a test patched `win32.send_paste_to_focused_window` while the code dispatched to `utils.linux` on non-Windows, so the real `ydotool key 29+47` (Ctrl+V) executed against the live desktop.
   - **No bypass**: Never delete/override `PYTEST_CURRENT_TEST` or `QT_QPA_PLATFORM=offscreen` to force real injection in a test, and never assert a real `subprocess`/`keybd_event` call fired during a pytest run (regression guard: `tests/test_linux_utils.py::test_send_ctrl_v_blocked_under_pytest`).

## Conventions

### Code Style

- **Lint**: `uv run ruff check src tests` — must pass before commit
- **Format**: `uv run ruff format src tests` — must pass before commit
- **Type hints**: Use `pyright` with `.pyrightconfig.json` settings
- **QML**: Follow `Theme.qml` semantic tokens; no hardcoded colors/sizes

### QML UI Conventions
- **Ribbons (`GlassPill`)**: Must use `Layout.preferredHeight: 48` and `radius: 24` to form a perfect pill. Do not apply external left/right margins directly to `GlassPill`.
- **Inner Controls**: Elements inside ribbons (e.g., `TabButton`, inner rectangles) should use `radius: 20` to perfectly contour the outer pill. `RowLayout` inside the pill should typically use `anchors.margins: 4`.
- **Buttons**: Prefer `IconButton` with `solar:` icons over text-heavy `ActionButton`s inside compact ribbons.
- **Roles**: Use `role: "primary-outline"` instead of solid filled `role: "primary"` for secondary or auxiliary actions to reduce visual weight.
- **Toggles**: Use `IconButton` with dynamic `iconSource` (e.g., swapping between `bold-duotone` and `broken`) instead of `GlassToggleButton`.
- **Layouts & Separators**: Flatten `RowLayout` groupings when elements have conditional visibility (`visible: condition`). Apply `visible` to individual elements instead of wrapper layouts to prevent orphaned separators when elements are hidden.

### Testing

- **Framework**: pytest + pytest-qt + pytest-cov
- **Parallel**: `uv run pytest -n auto --dist loadfile`
- **Coverage**: Target 80% (`fail_under = 80` in `pyproject.toml`)
- **Run all checks**: `python scripts/dev_test.py`

### Git & Commits

- Use [Conventional Commits](https://www.conventionalcommits.org/) format
- Prefix: `feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`
- Keep subject line ≤ 50 characters
- Body only when "why" isn't obvious from subject
- **Release tokens**: Commits on `main` may carry opt-in tokens `[patch]`, `[minor]`, `[major]`, `[dev]` matched as substrings in the subject **or** body. `[dev]` publishes a prerelease (`x.y.z-dev.n`); a `[patch]` while a dev line is active promotes it to stable. Never write a bracketed token word in body prose — e.g. "promotion via `[patch]`" in a `[dev]` commit body overrides the subject token and releases stable instead.

### Documentation & Architecture Diagrams

- **Visual Diagrams Required**: Any major feature, architecture change, distribution/installer lifecycle, or user workflow MUST include clear Mermaid diagrams (`flowchart`, `sequenceDiagram`, etc.) in relevant docs (`docs/ARCHITECTURE.md`, `docs/INSTALL.md`, `docs/RELEASING.md`) to ensure immediate visual clarity for end users and maintainers.

## Workflow

### Before Any Edit

1. Run `uv run ruff check src tests` to verify baseline
2. Check `docs/HOUSEKEEPING.md` for cleanup rules
3. Review related ADRs in `docs/adr/` if changing architecture

### After Any Edit

1. Run `uv run ruff check src tests --fix`
2. Run `uv run ruff format src tests`
3. Run `uv run pytest tests/test_<relevant>.py` (smoke subset)
4. Verify `git status` shows no unexpected untracked files

### Conductor Tracks

- Active tracks live in `conductor/tracks/<name>/`
- Each track has `metadata.json`, `plan.md`, and optionally `spec.md`
- When a track is fully merged, archive it to `conductor/_archive/<date>/`
- See [`conductor/workflow.md`](conductor/workflow.md) for full lifecycle

### ADR Process

- New architectural decisions → create `docs/adr/ADR-XXXX-<slug>.md`
- Update `ADR_INDEX.md` with entry
- See [`docs/adr/0000-template.md`](docs/adr/0000-template.md) for format

## Forbidden Actions

- Never commit `.env`, `data/*.json`, or `src/data/*.json`
- Never modify `TODO.md`, `.agents/commands/`, `.agents/skills/`
- Never hardcode colors, sizes, or fonts in QML (use `Theme.qml` tokens)
- Never use `ThreadPoolExecutor` for heavy work (use `joblib.Parallel`)
- Never block the main thread with I/O or computation

## Quick Reference

| Task | Command |
|------|---------|
| Run app | `uv run skill-manager` |
| Lint | `uv run ruff check src tests` |
| Lint (single file) | `uv run ruff check <path>` |
| Format | `uv run ruff format src tests` |
| Format (single file) | `uv run ruff format <path>` |
| Type check | `uv run pyright src/` |
| Test (parallel) | `uv run pytest -n auto` |
| Test (single file) | `uv run pytest tests/test_config.py` |
| All checks | `python scripts/dev_test.py` |
| Build | `uv run skill-manager-build` |
| MCP server (read) | `uv run skill-manager --mcp` |
| MCP server (write) | `uv run skill-manager --mcp --mcp-allow-write` |

## Cross-references

- [`docs/HOUSEKEEPING.md`](docs/HOUSEKEEPING.md) — cleanup rules
- [`conductor/workflow.md`](conductor/workflow.md) — track lifecycle
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — contribution guidelines
- [`ADR_INDEX.md`](ADR_INDEX.md) — architecture decisions

- **UI Validation**: See Mandatory Rule #6 — applies to every QML layout/positioning/rendering change.
