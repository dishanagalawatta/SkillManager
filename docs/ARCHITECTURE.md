# SkillManager Architecture

> Status: **Accepted** | Last reviewed: 2026-08-17
> Related ADRs: [ADR-0010](adr/ADR-0010-drop-tuf.md), [ADR-0019](adr/ADR-0019-multiprocessing-joblib.md), [ADR-0024](adr/ADR-0024-dual-write-clipboard-verification.md), [ADR-0025](adr/ADR-0025-selection-persistence-shutdown-sync.md), [ADR-0027](adr/ADR-0027-path-self-healing-and-two-phase-incubation.md)

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
| `SelectedSkillController` | `selected_skill_controller.py` | Live-bound QObject managing currently and last selected skill properties |
| `ConfigController` | `config_controller.py` (facade over `config/` mixins) | `ConfigManager` instance, skill sources, projects, shortcuts |
| `OpsController` | `ops_controller.py` (facade over `ops/` mixins) | Copy, delete, archive, restore, starred state, custom commands |
| `UpdateController` | `update_controller.py` | Background sync, Git source updates, progress reporting |
| `DiscoveryController` | `discovery_controller.py` | Filesystem scanning, project discovery, prepared-state pipeline |
| `ScreenshotController` | `screenshot_controller.py` | Screen capture, region selection, PII redaction |
| `ImageInspectorController` | `image_inspector_controller.py` | Color isolation, pixel inspection |
| `AppUpdateController` | `app_update_controller.py` | App self-update via GitHub Releases API |

### Registration & Meta-Object Signal Inheritance

```python
qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
engine.rootContext().setContextProperty("appController", controller)
```

QML consumers reach it via `import App 1.0` or the `appController` context property.

**Mixin Signal Inheritance Pattern**: Facade controllers (such as `ConfigController`) inherit from specialized domain mixins (`SettingsMixin`, `ShortcutsMixin`, `ProjectsMixin`, `CollectionsMixin`). Class-level `Signal` instances associated with `@Property(..., notify=...)` decorators are declared on the respective mixins. The composing facade inherits these class attributes without re-declaring them as class-level attributes, guaranteeing PySide6's Qt Meta-Object registration accurately routes property change notifications to QML bindings.

---

## 2. Data Models (`core/models/`)

| File | Class | Purpose |
|------|-------|---------|
| `entities.py` | `SkillEntity`, `CommandEntity`, etc. | Core data classes (Pydantic models) |
| `filter_engine.py` | `FilterEngine` | Category, text, client, starred/archived filtering |
| `qt_model.py` | `SkillModel` | `QAbstractListModel` subclass for QML binding (facade over `roles`, `selection`, `pipeline`, `incubation`, `collapse`, `ingest` mixins) |

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
| `UpdateService` | `update_service.py` | Version comparison, surgical file updates, exact-match project-skill ownership linking |
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
| `clipboard_service.py` | Cross-platform verified dual-write clipboard service (ADR-0024) |
| `linux.py` | Linux shell, active Wayland/X11 clipboard (`wl-copy`/`xclip`/`xsel`), and input automation |
| `win32.py` | Windows shell, clipboard, and UI automation utilities |
| `input_guard.py` | Injection safety guard enforcing test/offscreen isolation |

### Verified Dual-Write Clipboard Architecture

On Linux (Wayland and X11), Qt's `QClipboard` selection data source can be destroyed or disconnected when the application window minimizes (such as during QuickCopy auto-minimize). To ensure clipboard persistence across window minimization and reliable cross-app paste operations:

1. **Subprocess Environment Sanitization (`get_clean_env()`)**: When running in frozen binary bundles (PyInstaller onedir/onefile) or AppImages, `LD_LIBRARY_PATH` points to bundled runtime libraries (`_internal`). System binaries (`wl-copy`, `wl-paste`, `xclip`, `ydotool`) dynamically link against the host system's libraries. `get_clean_env()` restores `LD_LIBRARY_PATH` to `LD_LIBRARY_PATH_ORIG` or removes it to prevent shared library version mismatch crashes.
2. **Multi-Directory Binary Discovery (`find_system_binary()`)**: Probes standard system installation paths (`/usr/bin`, `/usr/local/bin`, `/snap/bin`, `~/.local/bin`) in addition to `PATH` to guarantee discovery in minimal desktop environments.
3. **Session Probing**: `is_wayland_active()` inspects `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY`, and runtime directory sockets (`/run/user/<uid>/wayland-*`).
4. **System-Truth Verification**: Verifies written content by reading directly from the native compositor/X11 selection buffer before reporting operation success.

```mermaid
sequenceDiagram
    autonumber
    participant UI as QML View (QuickCopy / Library)
    participant Ops as OpsController / ClipboardMixin
    participant Svc as ClipboardService
    participant Linux as Linux Native Helper (linux.py)
    participant Sys as System Compositor (wl-copy / xclip)
    participant Qt as Qt QClipboard

    UI->>Ops: copySelectedSkillsToClipboard()
    Ops->>Svc: copy_text(content)
    
    alt prefer_native = True (Linux)
        Svc->>Linux: set_clipboard(content)
        Linux->>Linux: get_clean_env() & find_system_binary()
        Linux->>Sys: Run wl-copy / xclip (DEVNULL pipes, clean env)
        Sys-->>Linux: Return code 0 (Success)
        Linux-->>Svc: True
        
        Note over Svc,Sys: System-Truth Verification
        Svc->>Linux: get_clipboard()
        Linux->>Sys: Run wl-paste / xclip -o
        Sys-->>Linux: Current clipboard text
        Linux-->>Svc: Verify content match (stripped)
        
        alt Verification Passed
            Svc->>Qt: Set in-memory cache / QClipboard
            Svc-->>Ops: Return True (Verified)
        else Native Failed / Unverified
            Svc->>Qt: Fallback to QClipboard.setText()
            Svc-->>Ops: Return Status
        end
    else Windows / macOS
        Svc->>Qt: QClipboard.setText(content)
        Svc-->>Ops: Return Status
    end

    Ops-->>UI: Status Notification ("Copied N skills")
    opt Auto-Minimize Enabled
        Ops->>UI: _maybeMinimizeOnCopy() (Window minimizes safely)
    end
```

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

## 9. Prepared-State Pipeline, Self-Healing Storage, & Silent Background Refresh

All cache-refresh paths and storage configurations share a unified self-healing lifecycle:

### Boot & Storage Normalization Sequence (ADR-0027)

```mermaid
flowchart TD
    Boot["AppController Boot"] --> Norm["_normalize_paths_on_startup()"]
    Norm --> FixProj["repair_malformed_path(projects)"]
    Norm --> FixSrc["repair_malformed_path(sources)"]
    Norm --> FixPkg["resolve_package_storage(_update_packages)"]
    FixPkg --> StripDup["Strip nested roots & prepend leading /"]
    FixProj --> SaveConfig["config.json self-healed & saved"]
    FixSrc --> SaveConfig
    StripDup --> SaveConfig
    SaveConfig --> Watchers["Initialize SkillFolderWatcher"]
    Watchers --> Pipeline["Start Background Prepared-State Pipeline"]
```

### Pipeline Execution

1. **Main thread** — caller invokes `DiscoveryController.refreshSkills()`
2. **Background thread** — `_run_pipeline()` executes: scan → parse → filter → search → row prep → visibility
3. **Cross-thread commit** — result emitted as `PreparedModelState` via `_discoveryPrepared` signal
4. **Main thread commit** — `SkillModel.replacePreparedState()` executes two-phase deferred reset

### Key Features

- **Silent UI**: No `isLoading` flag; diagnostic events only
- **Cancellation**: Generation counter (`_refresh_generation`) for cooperative cancellation
- **Debounce**: 400 ms `QTimer` trailing-edge debounce for filesystem events
- **Self-Healing Storage**: Automatically cleans missing leading slashes (`home/...` -> `/home/...`) and nested duplicated roots before watcher registration.

### Add-Time Hooks

Adding a folder through `ConfigController.addSource` / `addProject` wires it into
the refresh pipeline without a restart:

1. **Watcher registration** — the folder (plus the project's `.agents/skills` and
   commands dirs) is registered with `SkillFolderWatcher` so later file changes
   trigger incremental rescans.
2. **Silent refresh** — `loadInitialData()` runs the same prepared-state pipeline
   above, so new skills appear in the Library immediately.
3. **Exact-match linking** (projects only) — a `BackgroundTaskRunner` task calls
   `UpdateService.link_exact_match_project_skills()`, which records package
   ownership for pre-existing project skills whose folder name **and** file
   contents match a package skill exactly. The result is persisted to
   `project_skill_ownership.json`, so update cycles treat those skills as
   package-owned without a full sync first.

---

## 10. QML Incubation Coordination & Two-Phase Reset (ADR-0027)

To prevent `Object or context destroyed during incubation` warnings when the QML engine is actively creating delegates during model resets or row mutations:

```mermaid
sequenceDiagram
    autonumber
    participant DC as DiscoveryController
    participant Model as SkillModel
    participant QML as QuickCopy / Library QML View
    participant QtEngine as Qt Quick Delegate Incubator

    DC->>Model: replacePreparedState(prepared)
    Model->>QML: emit aboutToMutateStructure
    QML->>QML: set cacheBuffer = 0 (abort/pause new incubations)
    
    Note over Model,QtEngine: 1-Tick Deferred Reset (QTimer.singleShot(0))
    Model->>Model: QTimer.singleShot(0, _do_reset)
    QtEngine-->>QML: In-flight incubators finish or abort cleanly
    
    Model->>Model: beginResetModel()
    Model->>Model: Swap _skills and active filter state
    Model->>Model: endResetModel()
    
    Model->>QML: emit structureMutated
    QML->>QML: Restore cacheBuffer (Theme.viewCacheBuffer)
```

### Three-Part Protocol

1. **`cacheBuffer` lifecycle**: Set to 0 before reset and during granular row removals/insertions (`onRowsAboutToBeRemoved` / `onRowsAboutToBeInserted`), restored after mutation completes.
2. **Deferred model reset**: `QTimer.singleShot(0, _do_reset)` allows in-flight incubators to complete or abort across event-loop ticks before `beginResetModel()` is executed.
3. **Incubation Guard**: `cacheBuffer` initialization in QML components is guarded against `incubating` state to prevent race conditions during tab navigation.

---

## 11. Development Patterns

| Pattern | Description |
|---------|-------------|
| **Hub & Spoke** | `AppController` stays thin; logic in sub-controllers |
| **Optimistic UI** | Filesystem ops update model immediately, then run in background |
| **Signal Best Practices** | Formal parameter arrow functions in QML handlers |
| **Smooth Scrolling** | `WheelHandler` pointer integration with dynamic `scrollSpeedMultiplier` scaling for both wheel notches (`angleDelta`) and trackpads (`pixelDelta`) |
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

## 12. Distribution & Release Architecture

SkillManager uses a dual-track delivery pipeline: a zero-dependency, 1-command installer/updater for end users on Linux and Windows, and an automated SemVer release pipeline for maintainers:

```mermaid
flowchart TD
    subgraph "End-User 1-Command Workflow (Zero Repo Cloning)"
        A["curl -fsSL .../install.sh | bash"] --> B{Detect Linux Distro}
        B -->|Ubuntu / Debian| C[Query GitHub API for latest .deb]
        B -->|Other Linux / --appimage| D[Query GitHub API for latest AppImage]
        C --> E[Download .deb to /tmp]
        E --> F[sudo apt install -y /tmp/skill-manager_*.deb]
        D --> G[Download to ~/.local/bin/skill-manager]
        G --> H[Install desktop file & icons to ~/.local/share]
        F --> I[Update desktop database & verify install]
        H --> I
    end

    subgraph "Maintainer Release Flow"
        M["uv run python scripts/release.py [bump]"] --> N[Pre-flight: Lint & Test]
        N --> O[Sync versions across pyproject, __init__, iss, metainfo, README]
        O --> P[Update CHANGELOG.md]
        P --> Q["Git Commit & Tag vX.Y.Z"]
        Q --> R["Git Push origin main --tags"]
        R --> S["GitHub Actions: release-build.yml"]
        S --> T["Publish GitHub Release (.deb, .AppImage, .exe, SHA256SUMS)"]
        T --> A
    end
```

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

