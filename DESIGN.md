# System Design

> SkillManager follows a layered architecture with clear separation
> between PySide6 UI, controller orchestration, and core business logic.

## Design System

### Theme (`Theme.qml`)

- **Singleton** `Theme.qml` provides all semantic tokens
- Two modes: `darkMode: true/false`
- Matte Graphite palette — no glass noise (`glassNoiseOpacity: 0.0`)
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

## Architectural Patterns

### 1. Controller Layer

All UI-to-business logic flows through **singleton controllers** registered via `qmlRegisterSingletonInstance`:

| Controller | Module | Purpose |
|------------|--------|---------|
| `AppController` | `app.py` | Root controller; sub-controllers exposed as properties |
| `ConfigController` | `controllers/config_controller.py` | Read/write `ConfigManager` state |
| `DiscoveryController` | `controllers/discovery_controller.py` | Find skills across sources |
| `OpsController` | `controllers/ops_controller.py` | Copy, delete, archive operations |
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
