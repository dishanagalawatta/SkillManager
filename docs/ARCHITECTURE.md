# SkillManager Architecture

SkillManager is a cross-platform desktop application designed to manage, organize, and synchronize reusable agent skills across multiple project repositories. It is built using Python for the core logic and PySide6/QML for a modern, hardware-accelerated user interface.

## System Overview

The application is structured into three primary layers:
1.  **Core Domain (`src/skill_manager/core/`)**: Handles data modeling, file parsing, synchronization, and business logic.
2.  **GUI / Presentation (`src/skill_manager/gui/` & `src/skill_manager/SkillManagerComponents/`)**: The QML-based frontend, managing the visual representation and user interactions.
3.  **App Controller (`src/skill_manager/app.py`)**: The bridge connecting the QML frontend to the Python backend via Qt's Signal/Slot mechanism.

---

## Core Components

### 1. Data Models (`models.py`)
-   **`SkillModel`**: A `QAbstractListModel` subclass that exposes the list of skills to the QML frontend. It handles filtering (by category, project, client format, search text) and selection states.

### 2. File Parsing & IO (`parsing.py`, `skill_sources.py`)
-   Reads and parses Markdown files (`SKILL.md`, `*.md` commands) containing YAML frontmatter.
-   Extracts metadata such as `name`, `category`, `client`, and custom attributes.
-   Generates full-text search indexes for each skill based on its content and metadata.

### 3. Synchronization & Copying (`copier.py`, `quick_copy.py`, `updater.py`)
-   **Discovery**: Scans source directories (where skills are authored) and target directories (project repositories where skills are used).
-   **Copying**: Handles copying entire skill folders from the library into target projects.
-   **Updating**: Compares versions of skills in the library against those in target projects and performs surgical updates or global syncs.

### 4. Configuration Management (`config.py`)
-   Manages application settings, source/target directories, custom collections, and UI state (window size, position, active view).
-   Persists state to `.config` or `AppData` directories depending on the OS.

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
