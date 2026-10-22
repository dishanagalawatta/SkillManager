# SkillManager Architecture

> Status: **Accepted** | Last reviewed: 2026-08-20
> Related ADRs: [ADR-0010](adr/ADR-0010-drop-tuf.md), [ADR-0019](adr/ADR-0019-multiprocessing-joblib.md), [ADR-0024](adr/ADR-0024-dual-write-clipboard-verification.md), [ADR-0025](adr/ADR-0025-selection-persistence-shutdown-sync.md), [ADR-0027](adr/ADR-0027-path-self-healing-and-two-phase-incubation.md), [ADR-0028](adr/ADR-0028-non-blocking-package-versioning-and-npx-resolution.md), [ADR-0029](adr/ADR-0029-package-deletion-storage-cleanup.md), [ADR-0030](adr/ADR-0030-project-skill-classification-and-diff-model-sync.md), [ADR-0036](adr/ADR-0036-batched-command-skill-carry.md)


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
| `AppUpdateController` | `app_update_controller.py` | App release checks (automatic launch/daily + manual) via GitHub Releases API |

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
| `config.py` | Package configuration, defaults, command normalization |
| `process.py` | Subprocess execution pipeline with token sanitization |
| `relocator.py` | Skill relocation logic from staging to target paths |
| `storage.py` | Package storage management and path conflict detection |
| `updater.py` | Staging area execution and update pipelines |
| `versioning.py` | Non-blocking multi-protocol version detection (ADR-0028) |

#### Real-Time Protocol and Display Name Auto-Detection
The package creation dialog (`PackageEditDialog.qml`) integrates directly with `infer_package_metadata()` and `humanize_slug()` in `config.py` via `AppController.detectPackageMetadata()`. When a user types or pastes into the primary package/URL/command input:
1. **Protocol Inference**: URLs (`https://`, `git@`, `.git`) dispatch to `git`, shell prefixes (`bash `, `./`, `python `) dispatch to `custom`, and npm scopes or slugs dispatch to `npx`.
2. **Display Name Humanization**: Slugs are stripped of leading scopes, split along delimiters (`-`, `_`, `/`), and capitalized into human-readable titles (e.g. `vercel-labs/find-skills` $\rightarrow$ `Find Skills`, `agentic-awesome-skills` $\rightarrow$ `Agentic Awesome Skills`).
3. **Canonical Repository Mapping & Self-Healing**: Shorthand aliases and meta-skill names (e.g., `vercel-labs/find-skills`) are canonicalized via `KNOWN_SKILL_REPO_ALIASES` to their upstream source repository (`vercel-labs/skills`) for backend execution while preserving the user's specific display title (`Find Skills`).
4. **Headless Non-Interactive Flags**: `skills add` commands are automatically augmented with `-y` (or `--all`) to prevent subprocess terminal blocking.
5. **User-Edit Preservation**: Manual edits in the Display Name or Protocol fields set explicit override flags (`userEditedName`, `userEditedProtocol`), guaranteeing the user's manual choices are preserved unless explicitly cleared.

#### Non-Blocking Multi-Protocol Package Addition (ADR-0028)

Skill package registration uses a non-blocking multi-protocol probe pipeline designed to eliminate Qt event loop freezes and prevent OS "Not Responding" modals:

1. **Direct HTTP NPM Registry Lookup**: Uses `fetch_npm_registry_version()` to query `registry.npmjs.org` with a 3-second timeout for scoped (`@scope/pkg`) and standard npm packages in <100ms without shell overhead.
2. **GitHub Shorthand Resolution**: Automatically detects `owner/repo` formats (e.g. `vercel-labs/skills`) and probes remote repository tags or HEAD commits via HTTPS.
3. **Graceful Fallback & Snap**: Unresolvable or offline packages default to `"latest"` and snap `current_version`, enabling immediate registration with "Up to Date" status while actual downloads execute on `BackgroundTaskRunner`.

```mermaid
sequenceDiagram

    autonumber
    participant UI as PackageEditDialog (QML)
    participant Ctrl as UpdateController
    participant Ver as versioning.py
    participant HTTP as NPM Registry API
    participant Git as Git Remote (HTTPS)
    participant Watch as SkillFolderWatcher
    participant Runner as BackgroundTaskRunner
    participant Disc as DiscoveryController
    participant Disk as Local Storage

    UI->>Ctrl: addSkillPackage(data)
    Ctrl->>Ver: check_skill_package_versions(config)
    
    alt Standard / Scoped NPM Package
        Ver->>HTTP: GET registry.npmjs.org/{pkg}/latest (Timeout 3s)
        HTTP-->>Ver: Latest Version ("1.5.0")
    else GitHub Shorthand (owner/repo)
        Ver->>Git: git ls-remote --tags https://github.com/owner/repo
        Git-->>Ver: Latest Tag ("v2.0.0")
    else Offline / Undetectable
        Ver-->>Ver: Fallback to "latest" (No blocking error)
    end
    
    Ver-->>Ctrl: Normalized Record with latest_version & current_version snapped
    Ctrl->>Ctrl: Commit to app._update_packages & save config (last_updated = "Installing…")
    Ctrl->>Watch: _register_package_watcher (add_path to watcher)
    Ctrl-->>UI: {"ok": true, "installing": true, "check_status": …, "warning": …}
    
    Ctrl->>Runner: runPackageUpdate(new_index) [Async Worker]
    Runner->>Disk: Run npx/git/script update into staging & relocate skills
    Runner->>Watch: Register resolved_package_path with file watcher
    Runner->>Disc: discover_single(..., is_package=True)
    Runner->>Disc: _schedule_discovery_refresh() [coalesced loadInitialData]
    Runner-->>UI: Update finished notification & automatic library refresh
```

The add path deliberately does **not** call `loadInitialData()` itself: the install it schedules ends with its own (coalesced) refresh, and the immediate one walked every source and project before a single file of the package existed on disk.

#### Version Check State, Bounded Probes, and Scan Recovery

Every package record carries the outcome of its last remote check, so the UI can tell
"up to date" apart from "we never found out":

| `check_status` | Meaning | UI |
|----------------|---------|----|
| `ok` | Remote answered; `latest_version` is trustworthy | `Update` or `Up to Date` |
| `failed` | Probe failed (network/auth/timeout); `latest_version` is stale | amber `· could not check` + `Re-check` |
| `never_checked` | No remote and no version command to ask | `Update` or `Up to Date` |

```mermaid
stateDiagram-v2
    [*] --> never_checked: package added without a remote
    [*] --> failed: add-time probe could not reach the remote
    never_checked --> ok: remote answers
    failed --> ok: Re-check succeeds
    ok --> failed: later probe fails (latest_version kept, now stale)
    ok --> ok: probe confirms latest_version
    failed --> failed: Re-check fails again
    note right of failed
        Primary action becomes "Re-check".
        A *known* newer version still wins,
        so the button stays "Update".
    end note
```

Guarantees that make this state reachable instead of silently stuck:

- **Bounded, non-interactive probes** (`versioning.DEFAULT_GIT_TIMEOUT`, `_git_probe_env()`): every
  `git ls-remote` passes `env=` (no terminal prompts, `BatchMode` ssh) and
  `kill_after_timeout=`, and any plausible git remote is probed — not just
  `github.com`/`gitlab.com`. Previously the env dict was built and never passed, and
  there was no timeout, so a credential-gated remote blocked the scan thread forever.
- **Scan watchdog** (`UpdateController.SCAN_WATCHDOG_MS`): a real `QTimer` finalises the scan
  with partial results if the worker never returns, so `_is_loading` can never be stranded
  and "Update scan complete: 0" is never reported for a scan that failed. A failed or
  timed-out scan also suppresses auto-update for that run.
- **Recovery** (`retryPackageCheck(package_id)`): re-probes one package on the task runner and
  writes the result back by `package_id`, so a row added or removed mid-probe cannot be
  written to the wrong position.
- **Visibility**: `statsUnchecked` (a `count_unchecked_packages()` count) drives the header's
  "· N unchecked" text; per-row state drives the caption and the button label.
- **One probe per remote per scan, one rescan per change burst**: `RemoteProbeCache` is shared
  across a scan and across both phases of an add/edit, and
  `_schedule_discovery_refresh()` coalesces rapid `loadInitialData()` requests into a single
  filesystem scan.

#### Reactive Package File Watching & Instant Library Refresh
When a skill package is added (`addSkillPackage`, `addUpdatePackage`) or updated (`runPackageUpdate`):
1. **Dynamic Watcher Registration**: The package's resolved storage directory (`resolved_package_path`) is registered with `SkillFolderWatcher.add_path()`. This attaches inotify/ReadDirectoryChanges watchers immediately to detect subsequent on-disk modifications.
2. **Typed Single-Skill Discovery**: During incremental folder extraction, `DiscoveryService.discover_single(path, is_package=True)` enforces `is_package=True` and `project_label="Master Library"`, ensuring skills are immediately visible in the Library model (`isPackageOnly = True`).
3. **Automated Discovery Refresh**: Upon completion, `DiscoveryController.loadInitialData()` runs the full background discovery pipeline asynchronously, atomically syncing category headers, search engine indices, and filter models via `PreparedModelState`.

#### Lockfile Lifecycle & `skills` CLI Interoperability
When packages run tools such as `npx skills add <package>` or `npx skills update`, the staging engine manages `.skill-lock.json` and `.skills-lock.json` lockfiles:
- **Lockfile Relocation & Merge (`merge_and_move_lockfile`)**: Moves the lockfile from the temporary staging root into the target project root, merging JSON skill definitions and versions across multiple updates without clobbering existing tracked skills.
- **Outdated Folder Cleanup**: Detects outdated or removed skills between package versions and cleans up disk structures while refreshing the in-memory library model.
- **Subprocess Environment & Error Filtering**: Propagates `GITHUB_TOKEN` and `GH_TOKEN` for authenticated rate limits, strips ANSI escape sequences and decorative box borders, and extracts the exact failure summary line into the status bar.

#### Package Deletion & Storage Cleanup Lifecycle

When a package is removed from the Updates view, `UpdateController.removeUpdatePackage(index)` coordinates with `delete_package_storage()` to execute a multi-tier cleanup with strict safety guards:

```mermaid
flowchart TD
    A[User clicks Remove Package] --> B[UpdateController.removeUpdatePackage]
    B --> C[is_safe_deletion_target Guards]
    C -->|Guards Valid| D[delete_package_storage]
    C -->|Unsafe Path| E[Skip FS deletion & Log Error]
    
    D --> D1[Delete Grouped/Dedicated Storage Folder]
    D --> D2[Delete Git Clones in package_clones/]
    D --> D3[Delete Target Root Manifests & Lockfiles]
    
    B --> F[Persistence Cleanup]
    F --> F1[Prune package_skill_inventory.json]
    F --> F2[Prune project_skill_ownership.json]
    F --> F3[patch_cache_remove on cache.json]
    
    B --> G[UI & System Sync]
    G --> G1[removeSkillsByPath on Library & QuickCopy Models]
    G --> G2[Reset Selected Skill if deleted]
    G --> G3[Unregister Path from SkillFolderWatcher]
    G --> G4[Recalculate Update Stats]
```

1. **Safety Boundary Enforcement**: Prevents accidental deletion of filesystem roots (`/`, `C:\`), user home (`~`), current working directory (`CWD`), `DATA_DIR` root, active project directories (`_projects`), and user source roots (`_sources`).
2. **Dedicated vs. Shared Storage**:
   - For **Grouped mode** or isolated subdirectories (e.g. `~/.agent/skills/find-skills-2b87d3d3`), the package's folder and all contained skill subfolders are completely removed.
   - For **Direct mode** or shared storage roots, only the specific package's `managed_folders` are removed.
3. **Repository Clone Staging**: Safely prunes repository clone folders under `DATA_DIR / "package_clones"` (with Windows read-only file handling).
4. **State Pruning & Model Synchronization**:
    - Removes entries from `package_skill_inventory.json` and `project_skill_ownership.json`.
    - Surgically purges deleted skill paths from `cache.json` using `patch_cache_remove()`.
    - Removes skill instances from in-memory models (`_library_model`, `_quick_copy_model`) and unregisters the directory from the live file watcher (`_watcher`).
5. **All-or-Nothing Removal**: `delete_package_storage()` returns an `errors` list. If it is non-empty the
   removal **aborts before any state mutation** — no list entry removed, no config written — and the
   status reports which package could not be removed, so the user can retry instead of being left with
   orphaned files, a vanished row, and no explanation.

#### Config Write Durability & Storage Resolution Integrity

- **Atomic config writes**: `ConfigManager.save()` goes through `_atomic_write_json()` (serialise, write
  a `.tmp`, `os.replace`). A crash, a full disk, or a serialisation failure leaves the previous
  `config.json` intact instead of a truncated one.
- **No record is ever dropped**: `_resolvePackageStorageState()` writes resolved records back
  *positionally*, so a package whose record fails `model_validate` is kept as-is rather than dropped.
  Dropping it used to shift the write-back and give every later package the previous package's storage
  path. If `resolve_package_storage()` returns fewer records than it was given, the remainder is
  appended instead of truncating the list.
- **Every displayed field is declared**: `UpdatePackageRecord` is validated with `extra="ignore"`, so a
  field the UI reads but the model does not declare (this bit `update_error`) is silently discarded on
  every round-trip. New UI-visible record fields must be declared on the model.

#### Skill Copying, Project Classification & Differential Ingest (ADR-0030)

When skills are copied from the Master Library into project workspaces (`copySelectedSkillsToProject`), the operational pipeline ensures clean separation between master package skills and project-installed copies:

```mermaid
sequenceDiagram
    autonumber
    participant UI as Library / QuickCopy View
    participant Ops as OpsController (CopyMixin)
    participant Copier as copier.py
    participant Disc as DiscoveryService
    participant Cache as cache.json
    participant LibModel as _library_model (isPackageOnly=True)
    participant QCModel as _quick_copy_model (isPackageOnly=False)

    UI->>Ops: copySelectedSkillsToProject(project_path)
    Ops->>Copier: copy_skill_folders_to_projects(source_skills, [project_path])
    Copier-->>Ops: Result {"details": [{"status": "copied", "message": dest_path, "project": project_path}]}
    
    loop For each copied skill
        Ops->>Disc: discover_single(dest_path, project_path, is_package=False)
        Disc->>Disc: Enforce .agents/skills boundary rule (is_package=False)
        Disc->>Disc: Compute canonical project_label (e.g. "my-project")
        Disc-->>Ops: Normalized skill dict
    end
    
    Ops->>Cache: patch_cache_add(discovered_skills)
    Ops->>LibModel: addOrUpdateSkills(discovered_skills)
    Note over LibModel: Evaluates is_package=False -> filtered out by isPackageOnly -> no duplicates!
    Ops->>QCModel: addOrUpdateSkills(discovered_skills)
    Note over QCModel: Evaluates is_package=False -> diffs state & emits beginInsertRows
    Ops-->>UI: Status updated & selection cleared
```

1. **Strict Project Boundary Enforcement**: Any skill residing inside an `.agents/skills` or `.agents/commands` folder is explicitly identified as `is_package = False`. Even if the workspace root or parent folder is registered in `sources`, the project boundary prevents misclassifying project copies as Master Library packages.
2. **Package Label Invariance**: In `addOrUpdateSkills`, `project_label` recomputation is scoped exclusively to project skills (`not skill.is_package`), permanently preserving `"Master Library"` for package records.
3. **Differential Model Synchronization**: Non-empty model updates use `_apply_filter_with_diff()` via `difflib.SequenceMatcher` to emit surgical Qt row mutation signals (`beginInsertRows`/`endInsertRows`, `beginRemoveRows`/`endRemoveRows`, `dataChanged`), preventing QML `ListView` delegate cache corruption and index desynchronization. `equal` blocks are synced via `PipelineMixin._sync_equal_block()`, which reassigns only rows whose objects actually mutated (`!=`, preserving identity for identical items) and batches contiguous changed rows into single `dataChanged(topLeft, bottomRight)` emissions to prevent signal storms.

#### Unified Command Workflow

The **Library is the single source of truth** for a custom command.

- **Create / Edit** (`CommandCreateDialog.qml`) edits the canonical command
  file where it lives — the Library's active project. There is no project
  selector in the dialog and no fan-out: one file, one write.
- **Deploy** to other projects happens through the Library's own copy flow
  (`Copy to Project`). When a selected command already exists in the target
  project, the copy **pauses** and the user decides:

  | Action | Result |
  |---|---|
  | *Update Existing & Copy New* (`overwrite_commands=True`) | The project file is replaced by the Library version; new commands are copied. |
  | *Copy Only New* (`overwrite_commands=False`) | The project's file is kept; only commands it does not have are copied. |
  | *Cancel* | Nothing is written. |

- **Skill carry** (ADR-0036) runs on **add and update** alike: after a
  command is created, edited, or deployed, the controller scans it for
  referenced skills (`find_referenced_skills_in_command`) and, when the
  target project lacks one, emits a single carry prompt with the union of
  the missing skills.

```mermaid
sequenceDiagram
    autonumber
    participant UI as Command Dialog (QML)
    participant Lib as LibraryView (QML)
    participant Ops as OpsController
    participant Core as commands.py / copier.py
    participant Disc as DiscoveryService
    participant QML as CommandCarrySkillsDialog

    UI->>Ops: createCustomCommand(name, body, category)
    Ops->>Core: create_custom_command_file(...)  (canonical project)
    Core-->>Ops: path
    Ops->>Disc: discover_single + patch_cache_add
    Ops->>Ops: _collect_missing_skills_batch(pairs, body, CREATE)
    Ops-->>QML: commandSkillsCarryPrompt(...)  (when a skill is missing)

    Lib->>Ops: copySelectedSkillsToProject(project)
    Ops->>Core: find_existing_commands_in_projects(...)
    alt Command already exists in the target
        Ops-->>Lib: commandCopyExistingDetected(project, cmdPaths, existing)
        Lib->>QML: CommandUpdateConfirmDialog.openForCopy(...)
        QML->>Ops: confirmCommandCopyWithOverwrite(project, paths, overwrite)
    else No conflict
        Ops->>Core: copy_command_files_to_projects(...)
    end
    Ops->>Disc: discover_project(target)
    Ops->>Ops: _prompt_missing_skills_for_commands(...)
    Ops-->>QML: commandSkillsCarryPrompt(...)
```

```mermaid
flowchart TD
    A["equal block i1..i2"] --> B["idx in range?"]
    B -- no --> G["changed_start set?"]
    B -- yes --> C["row != new item?"]
    C -- yes --> D["reassign row, open/extend batch"]
    D --> B
    C -- no --> E["batch open?"]
    E -- yes --> F["emit dataChanged batch, close batch"]
    F --> B
    E -- no --> B
    G -- yes --> H["emit trailing dataChanged"]
    G -- no --> I["emit nothing"]
```

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

### Active View Model Routing & Selection Resolution
The application manages two distinct skill models:
- `_library_model` (`skillModel`): Master repository containing global package skills (`isPackageOnly = True`).
- `_quick_copy_model` (`quickCopyModel`): Project-scoped repository containing skills and custom commands installed within individual workspaces.

To ensure consistent behavior regardless of which view is active:
- `OpsController` mixins (`ClipboardMixin`, `DeleteMixin`, `TogglesMixin`, `CopyMixin`) route selection queries via `_get_active_model()`.
- When `ui_controller.currentView == "QuickCopy"`, operations query `quickCopyModel` first, falling back to `skillModel`.
- When in `Library` view, operations query `skillModel` first, falling back to `quickCopyModel`.
- Multi-model state updates (e.g. archiving, deletion) synchronize property changes across both models and clear selection state cleanly.

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

Versions are bumped manually; GitHub Actions only builds tagged releases:

1. **Release PR**: `uv run python scripts/release.py <patch|minor|major|dev|X.Y.Z>` syncs all metadata on `release/vX.Y.Z` and opens a PR (see [RELEASING.md](RELEASING.md))
2. **Build**: `windows-latest` × Python 3.12 + 3.13
3. **Artifact Publishing**: Native installer + portable ZIP attached to GitHub Release

### Application Updates

- `AppUpdateController` checks the GitHub Releases API automatically ~4s after launch and then daily (`startAutoCheck`), plus on demand from Settings.
- A newer version emits `appUpdateAvailable`, rendered by `UpdateToast` with a **View Release** action (see [ADR-0044](adr/ADR-0044-automatic-app-release-checks.md)).
- Users download and install updates manually from the Releases page — the app never self-installs ([ADR-0010](adr/ADR-0010-drop-tuf.md)).
- Only packaged builds (`sys.frozen`) check on startup; a source checkout skips it without marking the check as done, so Settings cannot report "Up to Date" for a check that never ran.

```mermaid
flowchart LR
    Boot[App start] -->|4s, packaged only| Check[GET /releases/latest]
    Boot -->|daily timer| Check
    Settings[Settings: Check for Updates] --> Check
    Check -->|tag newer than __version__| Toast[toast: App update available<br/>View Release]
    Check -->|same or older| UpToDate[status: Up to date<br/>button stays enabled]
    Check -->|dev build skipped| Skipped[no result recorded]
    Toast -->|click| Releases[GitHub Releases page<br/>manual download and install]
```

### Skill Package Auto-Update

- Setting is a single **Auto Update** toggle (`skill_package_auto_update`, default off). Legacy tri-state configs migrate automatically (`silent` → on, `prompt`/`off` → off).
- Update checks always run: startup scan (~2s after launch) + 6h periodic re-scan via `QtScheduler` (`skill-package-auto-scan` job).
- Each scan force-refreshes `latest_version` (npm/git/commands), then `recalculateStats()` sets the header count to the number of outdated **packages** (`current_version != latest_version`) — a 1:1 match with the per-package Update buttons. Skill content drift stays in `_update_results` as inspector detail and never arms the header.
- **On**: outdated packages install in the background via `updateNow()`; completion fires an `autoUpdateFinished` toast popup (bottom-right).
- **Off**: an `updatesAvailable` toast popup (bottom-right) with an **Update** button appears whenever updates are found — clicking it opens the Updates view and starts Update All.
- Both `updateNow` and `runPackageUpdate` recalculate stats in their finalize step, so the header count drops to 0 (and Update All disables) the moment promoted versions land — no follow-up scan required.

```mermaid
flowchart LR
    Boot --> Scan[scanForUpdates<br/>force_refresh]
    Scan --> Stats[recalculateStats<br/>outdated packages]
    Stats -->|0 outdated| Idle
    Stats -->|> 0, auto on| Auto[updateNow<br/>background]
    Auto --> DoneToast[toast: finished]
    Stats -->|> 0, auto off| ActionToast[toast + Update button]
    ActionToast -->|click| Updates[Updates view<br/>+ updateAllOutdated]
    Timer[6h scheduler] --> Scan
```

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

Three log outputs share `DATA_DIR` (resolved via `platformdirs`, overridable with `SKILL_MANAGER_DATA_DIR`):

- `skill_manager.log`: stdlib logging via `RotatingFileHandler` in `__main__.setup_logging()` (5 MB x 5).
- `qml_console.log`: QML `console.log` via stderr redirect in `__main__._redirect_qml_log()` (append mode, truncated once past the 5 MB cap).
- `diagnostic.log`: structured JSON-line events from `core/diagnostics.py` (5 MB x 5, `diagnostic.log.1` onward). File write is opt-in through Settings General `diagnostic_logging`, always on in dev mode.

`DiagnosticLogger` keeps an in-memory ring (`deque`, `maxlen=1000`) that always captures `log_event()` calls, even when file logging is off. `set_enabled()` only gates JSON-line file I/O. `SKILL_MANAGER_LOG_LEVEL` controls both sides (`_resolve_log_level()` for stdlib, `_resolve_diag_log_level()` for diag, `DEBUG` in dev mode else `INFO`).

Events are categorized via `CATEGORY_*` constants:

| Category | Purpose |
|----------|---------|
| `CATEGORY_SELECTION_REFRESHED` | Selection invariant guard (ADR-0011) |
| `CATEGORY_WINDOW_STATE` | Window visibility/position tracking |
| `CATEGORY_COMMAND_CARRY_*` | Command-skill carry decisions (ADR-0017) |
| `CATEGORY_REFRESH_*` | Background refresh lifecycle |

### Logging Outputs

```mermaid
flowchart TD
    Callers["log_event() callers\nPython controllers / QML bridge / MCP"] --> Ring["Ring buffer\ndeque maxlen 1000, always on"]
    Ring --> Gate{"File-write gate\nset_enabled opt-in?"}
    Gate -- "Yes" --> DiagFile["diagnostic.log\nJSON lines, 5 MB x 5"]
    Gate -- "No" --> RingOnly["No file write\nring only"]
    DiagFile --> Rot["Rotated files\ndiagnostic.log.1 and up"]
    Stdlib["stdlib logger\nskill_manager.*"] --> RotHandler["RotatingFileHandler\nskill_manager.log, 5 MB x 5"]
    QmlErr["QML console.log\nstderr"] --> QmlFile["qml_console.log\nappend, 5 MB cap"]
```

### Report Issue Flow

`export_bundle()` zips a manifest (`app_version`, `qt_version`, OS, Python, `log_level`, 50 recent events, `exported_at`) plus the current and rotated `diagnostic.log` files. `DiagnosticsMixin` exposes `exportDiagnosticBundle` / `getReportBundlePath`, `getReportIssueUrl` (local only, builds a prefilled `issues/new` URL with version, health status from `get_health_status()`, level counts from `get_diagnostic_counts()`, and log path), and `openReportIssue` (opens the URL via `QDesktopServices`). The user attaches the bundle manually.

```mermaid
sequenceDiagram
    autonumber
    participant User as User
    participant Pane as DiagnosticsPane
    participant Cfg as ConfigController DiagnosticsMixin
    participant Diag as DiagnosticLogger
    participant Browser as Browser
    User->>Pane: Fill summary and description
    Pane->>Cfg: exportDiagnosticBundle()
    Cfg->>Diag: export_bundle() zip
    Diag-->>Pane: Bundle path with manifest plus logs
    Pane->>Cfg: getReportIssueUrl(summary, body)
    Cfg->>Diag: build_report_issue_url() with version, health, counts
    Diag-->>Pane: issues/new URL
    Pane->>Cfg: openReportIssue(url)
    Cfg->>Browser: QDesktopServices.openUrl(url)
    User->>Browser: Attach bundle manually and submit
```

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
- **Canonical Filesystem Walk** (ADR-0037): every recursive tree listing in `src/` goes through `iter_relative_files()` (`core/skill_packages/storage.py`) — iterative `os.scandir`, `/`-separated sorted output, symlinked files listed, symlinked directories never recursed, non-regular files excluded. Consumers (`skill_fingerprint`, `_relative_file_map`, MCP `static_analyze`) adapt it; no second inline walk may be added. Shallow single-level skill-directory listings (`quick_copy` discovery, `DiscoveryService` scans) use inline `os.scandir` with `entry.is_dir()` + `name.lower()` sorting instead, since they need per-entry type info rather than relative-path trees; `is_ignored()` there avoids `Path.relative_to()` via string slicing on the hot path.

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

SkillManager uses a dual-track delivery pipeline: a zero-dependency, 1-command installer/updater for end users on Linux and Windows, and a tag-driven release pipeline for maintainers:

```mermaid
flowchart TD
    subgraph "End-User 1-Command Workflow (Zero Repo Cloning)"
        A["curl -fsSL .../install.sh | bash"] --> B{Detect Linux Distro}
        B -->|Ubuntu / Debian| C[Query GitHub API for latest .deb]
        B -->|Other Linux / --appimage| D[Query GitHub API for latest AppImage]
        C --> E[Download .deb + SHA256SUMS to /tmp]
        E --> E2[Verify sha256 checksum]
        E2 --> F[sudo apt install -y /tmp/skill-manager_*.deb]
        D --> G[Download AppImage + SHA256SUMS to /tmp]
        G --> G2[Verify sha256 checksum]
        G2 --> H[Install to ~/.local/bin + desktop file & icons]
        F --> I[Update desktop database & verify install]
        H --> I
    end

    subgraph "Maintainer Release Flow"
        M["uv run python scripts/release.py [bump]"] --> N[Pre-flight: Lint & Test]
        N --> O[Sync versions across pyproject, __init__, iss, metainfo, README]
        O --> P[Update CHANGELOG.md]
        P --> Q["Commit on release/vX.Y.Z & open PR"]
        Q --> R["Merge after CI Gate"]
        R --> S["scripts/release.py tag & push vX.Y.Z"]
        S --> T["GitHub Actions: release-build.yml"]
        T --> U["Publish GitHub Release (.deb, .AppImage, .exe, SHA256SUMS)"]
        U --> A
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

