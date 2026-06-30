# SkillManager Architecture

> Status: **Accepted** | Last reviewed: 2026-06-30
> Related ADRs: [ADR-0010](adr/ADR-0010-drop-tuf.md), [ADR-0019](adr/ADR-0019-multiprocessing-joblib.md)

SkillManager is a Windows desktop application designed to manage, organize, and synchronize reusable agent skills across multiple project repositories. It is built using Python for the core logic and PySide6/QML for a modern, hardware-accelerated user interface.

## System Overview

The application is structured into four primary layers:

```
┌─────────────────────────────────────────────────────────┐
│  QML UI Layer (SkillManagerComponents/)                 │
│  Theme.qml · Main.qml · views/ · dialogs/ · components │
├─────────────────────────────────────────────────────────┤
│  Controller Layer (app.py + controllers/)               │
│  AppController → Config · Discovery · Ops · UI · ...   │
├─────────────────────────────────────────────────────────┤
│  Core Logic (core/)                                     │
│  Parsing · Models · Config · Copier · Discovery · ...   │
├─────────────────────────────────────────────────────────┤
│  Utils (utils/)                                         │
│  Threading · Task Runner · Win32                        │
└─────────────────────────────────────────────────────────┘
```

---

## 1. Hub & Spoke Controllers (`controllers/`)

To prevent `AppController` from becoming a "God Object," responsibilities are distributed into sub-controllers:

| Controller | Module | Purpose |
|------------|--------|---------|
| `UIController` | `ui_controller.py` | Application-wide UI state, window geometry, asset URI resolution |
| `ConfigController` | `config_controller.py` | `ConfigManager` instance, skill sources, projects, shortcuts |
| `OpsController` | `ops_controller.py` | Copy, delete, archive, restore, starred state, custom commands |
| `UpdateController` | `update_controller.py` | Background sync, Git source updates, progress reporting |
| `DiscoveryController` | `discovery_controller.py` | Filesystem scanning, project discovery, prepared-state pipeline |
| `ScreenshotController` | `screenshot_controller.py` | Screen capture, region selection, PII redaction |
| `ImageInspectorController` | `image_inspector_controller.py` | Color isolation, pixel inspection |
| `AppUpdateController` | `app_update_controller.py` | App self-update via GitHub Releases API |

### Registration

```python
qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
engine.rootContext().setContextProperty("appController", controller)
```

QML consumers reach it via `import App 1.0` or the `appController` context property.

---

## 2. Data Models (`core/models/`)

| File | Class | Purpose |
|------|-------|---------|
| `entities.py` | `SkillEntity`, `CommandEntity`, etc. | Core data classes (Pydantic models) |
| `filter_engine.py` | `FilterEngine` | Category, text, client, starred/archived filtering |
| `qt_model.py` | `SkillModel` | `QAbstractListModel` subclass for QML binding |

`SkillModel` implements optimized filtering and selection, supporting thousands of skills without UI lag.

---

## 3. Core Services (`core/`)

### Parsing Engine (`core/parsing/`)

| File | Purpose |
|------|---------|
| `base.py` | Common parsing utilities (markdown extraction, normalization) |
| `categorizer.py` | Auto-classification via weighted keyword frequency |
| `command.py` | Custom command markdown parsing |
| `constants.py` | Category definitions and keyword mappings |
| `skill.py` | Skill markdown frontmatter extraction |

### Key Services

| Service | Module | Purpose |
|---------|--------|---------|
| `DiscoveryService` | `discovery.py` | Filesystem scanning → model population |
| `UpdateService` | `update_service.py` | Version comparison, surgical file updates |
| `ConfigManager` | `config.py` | JSON-based `config.json` persistence |
| `SkillFolderWatcher` | `file_watch.py` | Watchdog-based filesystem monitoring |
| `BackgroundTaskRunner` | `utils/task_runner.py` | Concurrent background task execution |
| `Copier` | `copier.py` | File copy operations, command-skill carry |
| `SkillReferences` | `skill_references.py` | Skill dependency detection |
| `SearchEngine` | `search.py` | Fast skill lookup index |
| `DiskCache` | (via `diskcache`) | Expensive computation caching |

### Skill Packages (`core/skill_packages/`)

| File | Purpose |
|------|---------|
| `config.py` | Package configuration |
| `process.py` | Package processing pipeline |
| `relocator.py` | Skill relocation logic |
| `storage.py` | Package storage management |
| `updater.py` | Package update logic |
| `versioning.py` | Version comparison |

---

## 4. Utilities (`utils/`)

| File | Purpose |
|------|---------|
| `qt_threading.py` | Qt-compatible thread management |
| `task_runner.py` | `BackgroundTaskRunner` — async operations with Future tracking |
| `win32.py` | Windows shell and UI utilities |

---

## 5. UI Design & "Solid Matte" Aesthetic

### Design Principles

- **Solid Matte Foundation**: Main window uses solid, deeply-tinted material (`#121214` Dark Mode)
- **Glass-Pill Components**: Functional areas encapsulated in frosted glass pills
- **Synchronized Rounding**: 12px corner radii across all primary containers
- **Native Shell Integration**: `pywinstyles` for Mica/Acrylic effects and immersive dark mode

### QML Component Structure

```
SkillManagerComponents/
├── Main.qml              # Root window and layout orchestrator
├── Theme.qml             # Singleton: colors, fonts, layout tokens
├── Sidebar.qml           # Navigation (Library, QuickCopy, Updates, Settings)
├── TopBar.qml            # Window chrome and toolbar
├── CustomTitleBar.qml    # Custom title bar
├── SkillItem.qml         # Skill row representation
├── SkillInspector.qml    # Skill preview pane
├── CommandInspector.qml  # Command details with skill pills
├── GlassMenu.qml         # Ultra-glass context menus
├── FrostOverlay.qml      # Glass blur for popups
├── ScreenshotOverlay.qml # Screen capture
├── ImageInspector.qml    # Color isolation
├── views/                # Main screens
│   ├── LibraryView.qml
│   ├── QuickCopyView.qml
│   ├── SettingsView.qml
│   └── UpdatesView.qml
└── dialogs/              # Modal dialogs
    ├── ArchiveConfirmDialog.qml
    ├── DeleteConfirmDialog.qml
    ├── PackageEditDialog.qml
    ├── CommandCreateDialog.qml
    └── ProjectRenameDialog.qml
```

---

## 6. Distribution & Packaging

### Build Pipeline

1. `scripts/build_app.py` — orchestrates PyInstaller build
2. `packaging/skill_manager.spec` — PyInstaller spec (path-relative)
3. `packaging/windows/installer.iss` — Inno Setup installer
4. `packaging/windows/build.ps1` — Build automation script

### CI/CD Pipeline

Uses `python-semantic-release` with opt-in tokens:

1. **Opt-In Version Bumps**: Commits must include `[patch]`, `[minor]`, `[major]`, or `[dev]`
2. **Build**: `windows-latest` × Python 3.12 + 3.13
3. **Artifact Publishing**: Native installer + portable ZIP attached to GitHub Release

### Application Updates

- `AppUpdateController` checks GitHub Releases API
- Users download updates manually from the Releases page

---

## 7. Environment Tiers

| Tier | Use Case | Key Settings |
|------|----------|--------------|
| **Dev** | Local development, headless tests | `QT_QPA_PLATFORM=offscreen`, `DEBUG` logging |
| **Staging** | CI builds, staging deployments | `WARNING` logging, telemetry slots |
| **Prod** | Production builds | `ERROR` logging, telemetry required |

See [`environments/README.md`](../environments/README.md) and [`docs/ENVIRONMENT.md`](ENVIRONMENT.md).

---

## 8. Diagnostic Ring Buffer

Uses `core/diagnostics.py` instead of standard `logging`. Events are categorized via `CATEGORY_*` constants:

| Category | Purpose |
|----------|---------|
| `CATEGORY_SELECTION_REFRESHED` | Selection invariant guard (ADR-0011) |
| `CATEGORY_WINDOW_STATE` | Window visibility/position tracking |
| `CATEGORY_COMMAND_CARRY_*` | Command-skill carry decisions (ADR-0017) |
| `CATEGORY_REFRESH_*` | Background refresh lifecycle |

---

## 9. Prepared-State Pipeline & Silent Background Refresh

All cache-refresh paths share a single architecture:

### Pipeline

1. **Main thread** — caller invokes `DiscoveryController.refreshSkills()`
2. **Background thread** — `_run_pipeline()` executes: scan → parse → filter → search → row prep → visibility
3. **Cross-thread commit** — result emitted as `PreparedModelState` via `_discoveryPrepared` signal
4. **Main thread commit** — `SkillModel.replacePreparedState()` + deferred `beginResetModel`/`endResetModel`

### Key Features

- **Silent UI**: No `isLoading` flag; diagnostic events only
- **Cancellation**: Generation counter (`_refresh_generation`) for cooperative cancellation
- **Debounce**: 400 ms `QTimer` trailing-edge debounce for filesystem events

---

## 10. QML Incubation Coordination

Three-part protocol to prevent "Object destroyed during incubation":

1. **`cacheBuffer` lifecycle**: Set to 0 before reset, restored after
2. **Deferred model reset**: `QTimer.singleShot(0, _do_reset)` — one event-loop tick
3. **`incubating` flag**: Safety timer; incoming states queued and replayed

---

## 11. Development Patterns

| Pattern | Description |
|---------|-------------|
| **Hub & Spoke** | `AppController` stays thin; logic in sub-controllers |
| **Optimistic UI** | Filesystem ops update model immediately, then run in background |
| **Signal Best Practices** | Formal parameter arrow functions in QML handlers |
| **Subprocess Patching** | `CREATE_NO_WINDOW` flag prevents console windows |
| **Lifecycle Management** | `on_quit()` ensures clean shutdown |

### Dependency Boundaries

| Dependency | Purpose |
|------------|---------|
| `platformdirs` | Data directory resolution |
| `pydantic` | Internal schemas |
| `python-frontmatter` | Markdown frontmatter parsing |
| `pathspec` | `.gitignore`-style filtering |
| `httpx` + `tenacity` | HTTP with retry |
| `watchdog` | Filesystem monitoring |
| `sentry-sdk` | Error reporting |
| `posthog` | Product analytics |
| `apscheduler` | Background scheduling |
| `diskcache` | Local caching |
| `orjson` | Fast JSON |
| `joblib` | CPU-bound parallelism (ADR-0019) |

---

## Cross-references

| Document | Description |
|----------|-------------|
| [`DESIGN.md`](../DESIGN.md) | Design patterns and token system |
| [`API.md`](API.md) | QML/Python API reference |
| [`docs/ENVIRONMENT.md`](ENVIRONMENT.md) | Environment variable contract |
| [`docs/CI_CD.md`](CI_CD.md) | CI/CD pipeline reference |
| [`docs/RELEASING.md`](RELEASING.md) | Release workflow |
| [`docs/HOUSEKEEPING.md`](HOUSEKEEPING.md) | Cleanup rules |
| [`ADR_INDEX.md`](../ADR_INDEX.md) | Architecture decisions |
