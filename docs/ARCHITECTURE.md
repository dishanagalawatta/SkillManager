# SkillManager Architecture

SkillManager is a Windows desktop application designed to manage, organize, and synchronize reusable agent skills across multiple project repositories. It is built using Python for the core logic and PySide6/QML for a modern, hardware-accelerated user interface.

## System Overview

The application is structured into four primary layers:
1. **Core Domain (`src/skill_manager/core/`)**: Pure Python business logic, handling file parsing, data modeling, synchronization algorithms, and background services.
2. **Sub-Controllers (`src/skill_manager/controllers/`)**: Specialized controllers that encapsulate specific logical domains (UI, Config, Ops, Updates, Screenshot, Discovery, AppUpdates).
3. **App Hub (`src/skill_manager/app.py`)**: The central `AppController` that coordinates sub-controllers and provides a stable Signal/Slot bridge to the frontend.
4. **Declarative UI (`src/skill_manager/SkillManagerComponents/`)**: The QML-based frontend components.

---

### 1. The Hub & Spoke Controllers (`controllers/`)

To prevent the `AppController` from becoming a "God Object," responsibilities are distributed into sub-controllers:

- **`UIController`**: Manages application-wide UI state (Current View, Dark Mode), window geometry (X, Y, Width, Height), and asset URI resolution for QML.
- **`ConfigController`**: Manages the `ConfigManager` instance, handling the addition/removal of skill sources, project targets, client formats, custom collections, shortcuts, and update settings.
- **`OpsController`**: Handles high-frequency skill operations such as copying to projects, deleting skills (with optimistic UI updates), managing starred/archive states, and custom commands.
- **`UpdateController`**: Orchestrates background synchronization processes, Git source updates, skill package scanning, and provides real-time progress reporting to the UI.
- **`DiscoveryController`**: Handles filesystem scanning for skills, project discovery, and initial data loading.
- **`ScreenshotController`**: Manages screenshot capture workflow with region selection, PII redaction, and saving.
- **`ImageInspectorController`**: Handles color isolation and pixel inspection within captured screenshots.
- **`AppUpdateController`**: Manages application self-update checks via GitHub Releases API.

### 2. Data Models (`core/models/`)

- **`entities.py`**: Defines core data classes (`SkillData`, `SkillCollection`, etc.) used throughout the application.
- **`filter_engine.py`**: Implements filtering and search logic for skills (category, text, client format, starred, archived).
- **`qt_model.py`**: `SkillModel` - A `QAbstractListModel` subclass that exposes skills to QML. It implements highly optimized filtering and selection logic, supporting thousands of skills without UI lag.

### 3. Core Services (`core/`)

- **`discovery.py`**: `DiscoveryService` - Scans the filesystem to populate the models.
- **`parsing/`**: Modular parsing engine:
  - `base.py` - Common parsing utilities (markdown extraction, normalization).
  - `categorizer.py` - Auto-classification engine using weighted keyword frequency.
  - `command.py` - Custom command markdown parsing.
  - `constants.py` - Category definitions and keyword mappings.
  - `skill.py` - Skill markdown frontmatter extraction.
- **`update_service.py`**: Handles low-level logic for comparing versions and performing surgical file updates.
- **`updater.py`**: Git-based skill source updater.
- **`config.py`**: `ConfigManager` - Low-level persistence for `config.json`.
- **`analytics.py`**: PostHog analytics event capture and shutdown.
- **`categories.py`**: Emoji resolution and category display utilities.
- **`copier.py`**: File copy operations for deploying skills to projects, including command–skill carry.
- **`skill_references.py`**: Detects which skills a command body depends on (extract + resolve).
- **`commands.py`**: Custom command integration.
- **`file_watch.py`**: `SkillFolderWatcher` - Watchdog-based filesystem monitoring for live refresh.
- **`image_provider.py`**: `ScreenshotImageProvider` - QML image provider for screenshot previews.
- **`persistence.py`**: Archive and starred state persistence.
- **`quick_copy.py`**: Quick Copy workflow state management.
- **`resources.py`**: Resource path resolution for development and PyInstaller builds.
- **`schemas.py`**: Pydantic schemas for config and metadata validation.
- **`search.py`**: Search index for fast skill lookup.
- **`skill_packages/`**: Subsystem for managing downloadable skill packages:
  - `config.py`, `process.py`, `relocator.py`, `storage.py`, `updater.py`, `versioning.py`.

### 4. Utilities (`utils/`)

- **`qt_threading.py`**: Qt-compatible thread management utilities.
- **`task_runner.py`**: `BackgroundTaskRunner` - Concurrent background task execution.
- **`win32.py`**: Windows-specific shell and UI utilities.

### 5. Categorization Engine (`core/parsing/categorizer.py`)

The application implements an intelligent auto-classification system for skills without explicit frontmatter categories:
- **Weighted Frequency**: Matches keywords against skill content, with the `name` field weighted 2x more than the `description`.
- **Two-Stage Resolution**: Maps keywords to a Sub Category, which resolves its parent Main Category automatically.
- **Visual Resolution**: Emoji mapping via `get_category_emoji()` in `core/categories.py`.
- **Definitive Guide**: Full mapping logic and keywords are documented in `docs/CATEGORIES.md`.

---

## UI Design & The "Solid Matte" Aesthetic

SkillManager follows a **Solid Matte & Liquid Glass** design guide (previously defined in `DESIGN.md`).

### Design Principles
- **Solid Matte Foundation**: The main window utilizes a solid, deeply-tinted material (`#0E1210` in Dark Mode).
- **Glass-Pill Components**: Functional areas (sidebars, list items, headers) are encapsulated in "frosted glass" pills (`#1A201E`).
- **Synchronized Rounding**: 12px corner radii across all primary containers, matching native Windows 11 DWM preferences.
- **Native Shell Integration**: Uses `pywinstyles` to apply native Mica/Acrylic effects and immersive dark mode. Sets `AppUserModelID` via `ctypes` for proper taskbar grouping.

### QML Component Structure
- **`Main.qml`**: The root application window and layout orchestrator.
- **`Sidebar.qml`**: Navigation between Library, Quick Copy, Updates, and Settings.
- **`TopBar.qml` & `CustomTitleBar.qml`**: Window chrome and toolbar.
- **`views/`**: Main application screens (`LibraryView.qml`, `QuickCopyView.qml`, `SettingsView.qml`, `UpdatesView.qml`, `ShortcutsSettings.qml`).
- **`SkillItem.qml` & `SkillInspector.qml`**: Skill row representation and preview pane.
- **`Theme.qml`**: Singleton defining colors, fonts, and layout metrics.
- **`GlassMenu.qml` & `GlassMenuItem.qml`**: Ultra-glass context menus.
- **`ScreenshotOverlay.qml` & `ImageInspector.qml`**: Screenshot capture and redaction.
- **`FrostOverlay.qml`**: Glass blur effect for popups.
- **`dialogs/`**: Modal dialogs (`ArchiveConfirmDialog`, `DeleteConfirmDialog`, `PackageEditDialog`, `CommandCreateDialog`, `ProjectRenameDialog`, `FolderPickerNative`).

---

## Distribution & Packaging Architecture

SkillManager is distributed as a native standalone executable for Windows. The packaging pipeline is fully automated via GitHub Actions.

### 1. Freezing & Compilation (`scripts/build_app.py` / `packaging/skill_manager.spec`)
- Compilation is orchestrated by `scripts/build_app.py` which:
  - Automatically prepares a Windows high-fidelity multi-size icon `logo.ico` from `logo.png` (16x16 through 256x256).
  - Checks the Spec file syntax and invokes PyInstaller securely with `--noconfirm`.
- The spec file `packaging/skill_manager.spec` resolves paths dynamically relative to `SPECPATH`, avoiding CWD-dependence.
- Path resolution at runtime uses `resource_path` in `core/resources.py` to handle both development and PyInstaller's `_internal` extraction folders.

### 2. Native OS Wrappers
- **Windows**: PyInstaller output wrapped into `SkillManager_Setup.exe` via Inno Setup (`packaging/windows/installer.iss`). Portable ZIP also generated.

### 3. CI/CD Pipeline
The project uses [python-semantic-release](https://python-semantic-release.readthedocs.io/) with opt-in tokens (see ADR-0009):
1. **Opt-In Version Bumps**: Commits must include `[patch]`, `[minor]`, `[major]`, or `[dev]` to trigger a release.
2. **Build**: `windows-latest` × Python 3.12 + 3.13.
3. **Artifact Publishing**: Native installer and portable ZIP attached to GitHub Release.

### 4. Application Updates
- `AppUpdateController` checks the GitHub Releases API for new versions.
- Users download updates manually from the GitHub Releases page.

---

## Environment Tiers

SkillManager supports three environment tiers via `environments/`:

| Tier | Use Case | Key Settings |
|------|----------|--------------|
| **Dev** | Local development, headless tests | `QT_QPA_PLATFORM=offscreen`, `DEBUG` logging |
| **Staging** | CI builds, staging deployments | `WARNING` logging, telemetry slots |
| **Prod** | Production builds | `ERROR` logging, telemetry required |

See [`environments/README.md`](../environments/README.md) for full
details and [`docs/ENVIRONMENT.md`](ENVIRONMENT.md) for the variable
contract.

---

## Diagnostic Ring Buffer

The application uses a ring-buffer diagnostic logger
(`core/diagnostics.py`) instead of the standard `logging` module.
Events are categorized via `CATEGORY_*` constants and emitted to the
QML console bridge. Key categories:

- `CATEGORY_SELECTION_REFRESHED` — selection invariant guard (ADR-0011)
- `CATEGORY_WINDOW_STATE` — window visibility/position tracking (ADR-0012)
- `CATEGORY_COMMAND_CARRY_PROMPTED` / `_COPIED` / `_SKIPPED` — command-skill carry decisions (ADR-0017)

---

## Development Patterns

### Dependency Boundary Guidelines

Dependencies are kept behind narrow internal boundaries:

- `platformdirs` for data directory resolution.
- `pydantic`/`pydantic-settings` for tolerant internal schemas.
- `python-frontmatter` and `markdown-it-py` for parsing skill/command Markdown.
- `pathspec` for `.gitignore`-style discovery filtering.
- `httpx` and `tenacity` for update-check HTTP calls with retry.
- `watchdog` for filesystem change monitoring.
- `sentry-sdk` for error reporting.
- `posthog` for product analytics.
- `apscheduler` for background task scheduling.
- `PySide6.QtAsyncio` for future Qt-owned coroutine work.
- `diskcache` for local caching.
- `orjson` for fast JSON serialization.

### 1. Signal Handler Best Practices (QML)
All QML signal handlers use formal parameter arrow functions:
```qml
onClicked: (mouse) => {
    console.log(mouse.x);
}
```

### 2. Hub and Spoke Delegation
The `AppController` remains thin. New logic goes in specialized controllers and exposed via properties.

### 3. Optimistic UI Updates
Filesystem operations (deletion, archive) immediately update `SkillModel` for instant feedback, then execute in a background thread.

### 4. Subprocess Patching (`__main__.py`)
`subprocess.Popen` is patched with `CREATE_NO_WINDOW` to prevent console windows from appearing during background operations.

### 5. Lifecycle Management
- `on_quit()` ensures clean shutdown: watcher stop, scheduler shutdown, state save, Sentry flush, PostHog shutdown with timeout.
- `os._exit()` is called at the end of `main()` to force-clean background threads.
