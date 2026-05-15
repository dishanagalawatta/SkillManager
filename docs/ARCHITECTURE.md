# SkillManager Architecture

SkillManager is a cross-platform desktop application designed to manage, organize, and synchronize reusable agent skills across multiple project repositories. It is built using Python for the core logic and PySide6/QML for a modern, hardware-accelerated user interface.

## System Overview

The application is structured into four primary layers:
1.  **Core Domain (`src/skill_manager/core/`)**: Pure Python business logic, handling file parsing, data modeling, synchronization algorithms, and background services.
2.  **Sub-Controllers (`src/skill_manager/controllers/`)**: Specialized controllers that encapsulate specific logical domains (UI, Config, Ops, Updates).
3.  **App Hub (`src/skill_manager/app.py`)**: The central `AppController` that coordinates sub-controllers and provides a stable Signal/Slot bridge to the frontend.
4.  **Declarative UI (`src/skill_manager/SkillManagerComponents/`)**: The QML-based frontend components.

---

### 1. The Hub & Spoke Controllers (`controllers/`)

To prevent the `AppController` from becoming a "God Object," responsibilities are distributed into sub-controllers:

- **`UIController`**: Manages application-wide UI state (Current View, Dark Mode), window geometry (X, Y, Width, Height), and asset URI resolution for QML.
- **`ConfigController`**: Manages the `ConfigManager` instance, handling the addition/removal of skill sources and project targets.
- **`OpsController`**: Handles high-frequency skill operations such as copying to projects, deleting skills (with optimistic UI updates), and managing essential/archive states.
- **`UpdateController`**: Orchestrates background synchronization processes, Git source updates, and provides real-time progress reporting to the UI.

### 2. Data Models (`core/models.py`)

- **`SkillModel`**: A `QAbstractListModel` subclass that exposes skills to QML. It implements highly optimized filtering and selection logic, supporting thousands of skills without UI lag.

### 3. Core Services (`core/`)

- **`DiscoveryService`**: Scans the filesystem to populate the models.
- **`Parsing`**: Extracts YAML frontmatter and Markdown content.
- **`UpdateService`**: Handles the low-level logic for comparing versions and performing surgical file updates.
- **`ConfigManager`**: Low-level persistence for `config.json`.

---

## UI Design & The "Solid Matte" Aesthetic

SkillManager follows a **Solid Matte & Liquid Glass** design guide (previously defined in `DESIGN.md`).

### Design Principles
-   **Solid Matte Foundation**: The main window utilizes a solid, deeply-tinted material (`#0E1210` in Dark Mode) providing a robust feel without desktop wallpaper bleed-through.
-   **Glass-Pill Components**: Functional areas (sidebars, list items, headers) are encapsulated in "frosted glass" pills (`#1A201E`).
-   **Synchronized Rounding**: 12px corner radii across all primary containers, matching native Windows 11 DWM preferences.
-   **Native Shell Integration**: Uses `pywinstyles` (where available) to apply native Mica/Acrylic effects and immersive dark mode to the window chrome.

### QML Component Structure
-   **`Main.qml`**: The root application window and layout orchestrator.
-   **`Sidebar.qml`**: Navigation between Library, Quick Copy, Updates, and Settings.
-   **`views/`**: Contains the main application screens (`LibraryView.qml`, `QuickCopyView.qml`, `UpdatesView.qml`, etc.).
-   **`SkillItem.qml` & `SkillInspector.qml`**: The visual representation of a skill row and its detailed preview pane.
-   **`Theme.qml`**: A singleton defining colors, fonts, and layout metrics for the application.

---

## Distribution & Packaging Architecture

SkillManager is distributed as native standalone executables for Windows, macOS, and Linux. The packaging pipeline is fully automated via GitHub Actions.

### 1. Freezing (PyInstaller)
-   The Python code, dependencies (PySide6, pyyaml), and static assets (`assets/`, QML components) are bundled into a standalone binary using PyInstaller (`packaging/skill_manager.spec`).
-   Path resolution uses a custom `resource_path` utility in `app.py` to seamlessly handle both local development paths and PyInstaller's `_internal` temporary extraction folders.

### 2. Native OS Wrappers
-   **Windows**: The PyInstaller output is wrapped into `SkillManager_Setup.exe` using Inno Setup (`packaging/windows/installer.iss`). This creates Start Menu shortcuts and a standard uninstaller.
-   **macOS**: The generated `.app` bundle is converted into a standard `.dmg` image using `create-dmg`.
-   **Linux**: The output directory is packaged as a `.tar.gz` (with potential future expansion to AppImage).

### 3. CI/CD Pipeline (`.github/workflows/release.yml`)
1.  Triggered automatically upon pushing a `v*` version tag.
2.  Runs parallel jobs on `windows-latest`, `macos-latest`, and `ubuntu-latest`.
3.  Uses `uv` for fast dependency installation and virtual environment management.
4.  Builds the OS-specific installers and uploads them as workflow artifacts.
5.  Creates a new GitHub Release and attaches all generated installers.

---

## Development Patterns

### 1. Signal Handler Best Practices (QML)
To avoid deprecation warnings in Qt 6.x and ensure scope safety, all QML signal handlers should use formal parameter arrow functions:

**Bad (Deprecated):**
```qml
onClicked: {
    console.log(mouse.x); // 'mouse' is injected
}
```

**Good (Standard):**
```qml
onClicked: (mouse) => {
    console.log(mouse.x);
}
```

### 2. Hub and Spoke Delegation
The `AppController` should remain as thin as possible. New logic should be added to specialized controllers in `src/skill_manager/controllers/` and exposed via the `AppController` properties.

### 3. Optimistic UI Updates
When performing filesystem operations (like deletion), the application should immediately remove the item from the `SkillModel` to provide instant feedback, then handle the actual deletion in a background thread.
