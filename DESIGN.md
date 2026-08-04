# System Design

> SkillManager follows a layered architecture with clear separation
> between PySide6 UI, controller orchestration, and core business logic.

## Design System

### Theme (`Theme.qml`)

- **Singleton** `Theme.qml` provides all semantic tokens
- Two modes: `darkMode: true/false`
- Warm Stone palette (Light Mode) and Matte Graphite (Dark Mode) — reduced eye strain, no glass noise (`glassNoiseOpacity: 0.0`)
- All colors, sizes, and spacing referenced via `Theme.xxx`
- **No hardcoded values** in any QML component

### Key Token Groups

| Group | Examples |
|-------|----------|
| Surface | `appBackground`, `sidebarBackground`, `glassPill`, `glassHover` |
| Text | `textPrimary`, `textSecondary`, `textMuted`, `textOnAccent` |
| Border | `glassBorder`, `glassInnerBorder`, `separator` |
| Accent | `accentBlue`, `accentGreen`, `accentRed`, `accentYellow` |
| State | `selectedRow`, `selectedRowHover`, `disabledControl` |

### QML UI Conventions

- **Ribbons (`GlassPill`)**: Must use `Layout.preferredHeight: 48` and `radius: 24` to form a perfect pill. Do not apply external left/right margins directly to `GlassPill`.
- **Inner Controls**: Elements inside ribbons (e.g., `TabButton`, inner rectangles) should use `radius: 20` to perfectly contour the outer pill. `RowLayout` inside the pill should typically use `anchors.margins: 4`.
- **Buttons**: Prefer `IconButton` with `solar:` icons over text-heavy `ActionButton`s inside compact ribbons.
- **Roles**: Use `role: "primary-outline"` instead of solid filled `role: "primary"` for secondary or auxiliary actions to reduce visual weight.
- **Toggles**: Use `IconButton` with dynamic `iconSource` (e.g., swapping between `bold-duotone` and `broken`) instead of `GlassToggleButton`.
- **Layouts & Separators**: Flatten `RowLayout` groupings when elements have conditional visibility (`visible: condition`). Apply `visible` to individual elements instead of wrapper layouts to prevent orphaned separators when elements are hidden.
- **Icon naming**: All icons use the `solar:` URI scheme (e.g., `solar:copy-bold-duotone`, `solar:trash-bin-2-broken`). Use `bold-duotone` for primary actions, `broken` for secondary/inactive state.

**`IconButton` pattern:**

```qml
IconButton {
    iconSource: isActive ? "solar:bookmark-bold-duotone" : "solar:bookmark-broken"
    role: "primary-outline"
    onClicked: controller.toggleBookmark(skillId)
    ToolTip.text: isActive ? "Remove bookmark" : "Bookmark skill"
    ToolTip.visible: hovered
}
```

## Architectural Patterns

### 1. Controller Layer

All UI-to-business logic flows through **singleton controllers** registered via `qmlRegisterSingletonInstance`:

| Controller | Module | Purpose |
|------------|--------|---------|
| `AppController` | `app.py` | Root controller; sub-controllers exposed as properties |
| `ConfigController` | `controllers/config_controller.py` (facade over `config/` mixins) | Read/write `ConfigManager` state |
| `DiscoveryController` | `controllers/discovery_controller.py` | Find skills across sources |
| `OpsController` | `controllers/ops_controller.py` (facade over `ops/` mixins) | Copy, delete, archive operations |
| `UIController` | `controllers/ui_controller.py` | Sidebar, search, view state |
| `UpdateController` | `controllers/update_controller.py` | Skill source updates |
| `AppUpdateController` | `controllers/app_update_controller.py` | App-level update (TUF bundles) |
| `ScreenshotController` | `controllers/screenshot_controller.py` | Screen capture & annotation |
| `ImageInspectorController` | `controllers/image_inspector_controller.py` | Image analysis & color isolation |

Each controller inherits from `controllers/base.py` (`SingletonMixin`) and exposes `@Slot` / `@Property` to QML.

### 2. Threading Model

```
Main Thread (PySide6 event loop)
├── QML rendering
├── Signal/Slot dispatch
└── UI state updates

Background Threads
├── joblib.Parallel — skill parsing, filter passes
├── BackgroundTaskRunner — async operations with Future tracking
├── APScheduler (QtScheduler) — periodic polling
└── File Watcher (watchdog) — filesystem change detection
```

**Rule:** Never block the main thread. All heavy work (parsing, I/O, computation) runs on background threads.

### 3. Multiprocessing (ADR-0019)

- `joblib.Parallel(n_jobs=-1)` for CPU-bound skill parsing
- Replaced `ThreadPoolExecutor` to avoid GIL starvation
- Each parse job produces a `SkillEntity` → aggregated on main thread

### 4. Persistence Model

- `ConfigManager` — JSON-based config (`data/config.json`)
- `ScopedConfigManager` — per-project config isolation
- `SkillLibraryIndex` — `data/skill_library_index.json` (skill metadata cache)
- `DiskCache` — `diskcache.Cache` for expensive computation results

### 5. QML Lifecycle

**Incubation coordination** (ADR-0019 fix):

```
1. cacheBuffer = 0          ← QML stops incubating delegates
2. beginResetModel()        ← Python starts model reset
3. [background thread]      ← Heavy work (parse, filter, build)
4. endResetModel()          ← Python commits new data
5. cacheBuffer = 200        ← QML resumes incubation
```

`PreparedModelState` dataclass bundles a fully-computed model state for atomic commit.

### 6. Discovery Pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ File Scanner  │───▶│ Skill Parser │───▶│ Filter Pass  │
│ (watchdog)    │    │ (joblib)     │    │ (joblib)     │
└──────────────┘    └──────────────┘    └──────────────┘
                                              │
                   ┌──────────────┐    ┌───────▼────────┐
                   │ QML Commit   │◀───│ Row Prep       │
                   │ (main thread)│    │ (main thread)  │
                   └──────────────┘    └────────────────┘
```

- Fingerprint-based incremental scanning (hash of file tree)
- Background refresh with cooperative cancellation (generation counter)
- `isLoading` flag managed by `DiscoveryController`, not UI

### 7. Quick Copy System

- Drag skills to project targets
- Merge/overwrite conflict resolution
- Carry skill dependencies on copy (ADR-0017)
- Multi-project command selection

### 8. Screenshot System

- Native screen capture via PySide6 `QScreen`
- Annotation tools: rectangle, ellipse, text, freehand, highlight, redact
- Undo/redo stack
- Export to clipboard or file

### 9. Telemetry

- **PostHog** — anonymous product analytics (opt-in)
- **Sentry** — error tracking (opt-in)
- Both disabled in dev/test modes
- Device ID persisted in `data/device_id.json`

## Data Flow Diagrams

### App Startup

```
__main__.py
  └─▶ QGuiApplication
        └─▶ QQmlApplicationEngine
              ├─▶ Load qmldir (singleton Theme)
              ├─▶ Register AppController (root)
              ├─▶ Register sub-controllers
              ├─▶ Load Main.qml
              └─▶ Emit app_opened event (PostHog)
```

### Skill Copy

```
User clicks "Copy"
  └─▶ OpsController.copySkills(skills, target)
        ├─▶ DiscoveryController.getSkill(skillId)
        ├─▶ Copier.writeSkillFiles(skill, target)
        ├─▶ capture_event("skill_copied_to_project")
        └─▶ Emit skillsCopied signal
```

### 10. MCP Server Architecture

The `src/skill_manager/mcp/` subsystem exposes all core app capabilities to AI agents via the [MCP protocol](https://modelcontextprotocol.io/) (stdio, JSON-RPC 2.0).

```
src/skill_manager/mcp/
├── bridge/            ← IPC bridge package: routes MCP ↔ AppController
│   └── __init__.py      (facade; submodules: _controller, _capture, _ipc, _skills, ...)
├── models.py          ← pydantic request/response schemas
├── server.py          ← MCP server entry point (stdio)
└── tools/
    ├── skills.py        ← sm_list_skills, sm_get_skill, sm_search_skills, sm_sync_skills
    ├── analyze.py       ← sm_list_sources, sm_list_projects, sm_static_analyze
    ├── build.py         ← sm_build, sm_lint, sm_run_tests, sm_job_status
    ├── debug.py         ← sm_dump_state, sm_inspect_controller, sm_capture_errors, sm_toggle_debug_overlay
    ├── monitor.py       ← sm_get_health, sm_get_diagnostics, sm_tail_events, sm_profile
    ├── screenshot.py    ← sm_screenshot
    ├── gui.py           ← sm_navigate, sm_get_window_info, sm_mouse_move, sm_mouse_click, sm_type_text
    └── write.py         ← sm_create_skill, sm_update_skill, sm_deploy, sm_delete_skill
```

**Access modes:**

```bash
# Read-only (safe for untrusted agents)
uv run skill-manager --mcp

# Write-enabled (requires explicit opt-in)
uv run skill-manager --mcp --mcp-allow-write
```

See [`docs/MCP_SERVER.md`](docs/MCP_SERVER.md) for the full tool reference.

### 11. Error Handling Strategy

```
Error occurs
  ├── Sentry.capture_exception()     ← telemetry (if opt-in + prod)
  ├── logger.error(...)              ← structured log (always)
  ├── UI: toast / dialog             ← user-visible feedback
  └── Graceful degradation           ← app stays responsive
```

**Principles:**
- All exceptions in background threads are caught at the boundary and converted to signals
- `BackgroundTaskRunner` propagates failures via `taskFailed(str)` signal; QML binds to it for toasts
- Telemetry (`Sentry`) is always opt-in and disabled in `SKILL_MANAGER_TESTING=1` mode
- No exception propagates to the PySide6 event loop unhandled

## ADR Cross-references

| ADR | Decision | Impact |
|-----|----------|--------|
| ADR-0003 | Singleton controllers | `controllers/base.py` pattern |
| ADR-0004 | Token-based theme | `Theme.qml` semantic tokens |
| ADR-0008 | Atomic model reset | `PreparedModelState` |
| ADR-0010 | Drop TUF | Removed legacy update artifacts |
| ADR-0015 | Conductor archival | Track lifecycle rules |
| ADR-0016 | `.opencode` gitignore | Agent tooling excluded |
| ADR-0018 | Workspace standardization | File organization rules |
| ADR-0019 | Joblib multiprocessing | CPU-bound work offloaded |
| ADR-0020 | Command skill pills | Skill dependency UI |
| ADR-0021 | Frozen-build joblib override | `threading` backend in PyInstaller builds |
| ADR-0022 | Workspace cleanup standardization | Gitignore hardening + conductor archival batch |
