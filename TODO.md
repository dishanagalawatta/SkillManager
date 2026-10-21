# 1. Project Metadata

* **Project Name:** CourseBar
* **Important Links:**
  * [Code Repository](https://github.com/dishanagalawatta/SkillManager)
  * [README](README.md)
  * [DESIGN](DESIGN.md)
  * [Environment](docs/ENVIRONMENT.md)
  * [Development](docs/DEVELOPMENT.md)
  * [ARCHITECTURE](docs/ARCHITECTURE.md)
  * [API](docs/API.md)
  * [VERSIONING](docs/VERSIONING.md)

---

## 2. High-Level Milestones

* **Goal A:**
* **Goal B:**

---

## 3. Active Task Tracker

### To Do (Ready for Pickup)

>
>
> We are standardizing the application's list row layout: **Make Compact List Rows the single, permanent default across the app, remove the "Normal" (non-compact) row mode and setting toggle, and thoroughly clean up all related dead code.**
>
> Before making changes, search the entire codebase (`src/` and `tests/`) for `compactListRows`, `compact_list_rows`, and any compact-row theme tokens or conditionals in:
>
> - `src/skill_manager/SkillManagerComponents/SkillItem.qml`
> - `src/skill_manager/SkillManagerComponents/Theme.qml`
> - `src/skill_manager/SkillManagerComponents/views/SettingsView.qml`, `LibraryView.qml`, `QuickCopyView.qml`
> - `src/skill_manager/controllers/ui_controller.py`, `app.py`, `app_proxies.py`, `config/settings.py`
> - `src/skill_manager/core/schemas.py` & `src/skill_manager/core/config.py`
> - `DESIGN.md` and `AGENTS.md` (strictly obey all 7 mandatory rules, especially Rule #6 for real-app visual verification).
>
> ### 1. Refactoring & Cleanup Requirements
>
> #### A. QML UI & Theme Cleanup (`SkillManagerComponents/`)
>
> 1. **Bake Compact Geometry into `SkillItem.qml` (and any other list delegates):**
>    - Inspect every ternary / conditional branch driven by `compactListRows` (or `AppController.compactListRows` / `ui_controller.compactListRows`).
>    - Replace all `compactListRows ? <compact_value> : <normal_value>` expressions with the `<compact_value>` directly (heights, paddings, margins, font sizes, tag/description visibility, icon sizes, spacing).
>    - Remove any dead QML child components or layout elements that were only ever visible when `compactListRows` was `false`.
> 2. **`Theme.qml` Token Consolidation:**
>    - If `Theme.qml` defines separate tokens for compact vs. normal list rows, promote the compact values to be the canonical row tokens (or remove the unused non-compact tokens after updating all QML call sites). Ensure zero hardcoded magic numbers are introduced.
> 3. **Remove Setting Toggle from `SettingsView.qml`:**
>    - Remove the "Compact List Rows" switch/toggle row and its labels/descriptions from `SettingsView.qml`.
>    - Ensure the remaining settings section layout and spacing adjust cleanly with no visual gaps or orphaned bindings.
>
> #### B. Controller & Schema Cleanup (`controllers/` & `core/`)
>
> 1. **`UIController` & `AppController` (`ui_controller.py`, `app.py`, `app_proxies.py`):**
>    - Remove the `compactListRows` `Q_PROPERTY`, `compactListRowsChanged` signal, getter/setter methods, and any proxy forwarders on `AppController` / `AppControllerProxyMixin`.
>    - Verify no QML files or MCP bridge tools (`mcp/bridge/_state.py`, `_ui_inspection.py`, etc.) still reference `compactListRows` (or if an MCP state dump inspects `UIStateRecord`, update it cleanly).
> 2. **Schema & Config Backward Compatibility (`core/schemas.py` & `core/config.py`):**
>    - Remove `compact_list_rows` from `UIStateRecord` (and `AppConfig` / default config dicts in `core/config.py`).
>    - **Backward Compatibility Guard:** Ensure existing user `config.json` files on disk that still contain `"compact_list_rows": true/false` under `ui_state` or top-level keys do **not** raise a Pydantic `ValidationError` on boot (verify `extra="ignore"` or strip the legacy key during config normalization/load).
>
> #### C. Tests & Documentation Cleanup (`tests/` & `docs/`)
>
> 1. **Update Test Suite:**
>    - Search `tests/` for `compact_list_rows` and `compactListRows`.
>    - Remove obsolete tests that specifically test toggling between normal and compact row modes, and update any UI state / config serialization fixture tests to reflect the removed field (optionally keep 1 test verifying that loading a legacy `config.json` containing `compact_list_rows` succeeds silently).
>    - If `DESIGN.md` documents the `compactListRows` toggle, update it to state that compact row metrics are now the standard list row design.
>
> ### 2. Verification & Quality Gates
>
> 1. **Static Analysis & Tests:**
>    - Run `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run pyright src/`, and `uv run pytest` — all must pass with zero errors or unused variable warnings.
> 2. **Mandatory Real-App Visual Verification (AGENTS.md Rule #6):**
>    - Launch the real app (`uv run skill-manager`) and capture screenshots via the in-process `QWindow.grabWindow()` helper for:
>      - `LibraryView.qml` (showing the standard compact skill rows)
>      - `QuickCopyView.qml` (showing the standard compact skill/command rows)
>      - `SettingsView.qml` (confirming the Compact List Rows toggle is cleanly removed)
>    - Inspect all screenshots and check `qml_console.log` to ensure zero QML `ReferenceError` / `TypeError` / `Unable to assign [undefined]` warnings from any leftover `compactListRows` binding.

>
>
> We are refactoring the **Custom Slash Command Creation, Editing, and Project Deployment Workflow** so that deploying/updating commands in projects works identically to copying skills from the Library.
>
> ### Current vs. Desired Behavior
>
> - **Current Behavior:** Creating or editing a command inside `CommandCreateDialog.qml` (and `CommandInspector.qml` / `commands.py::update_custom_command_file_multi`) includes a multi-project selector inside the edit popup to sync/push the command to projects during save. Meanwhile, `copier.py::copy_command_files_to_projects` currently skips existing command files when copying.
> - **Desired Behavior:**
>   1. **Simplify Command Create/Edit Popup (`CommandCreateDialog.qml`):** Remove the project selector from the Create/Edit Command dialog. Creating or updating a command in the Library should only save/update the canonical command file in the Library.
>   2. **Unified Library Deployment (Single & Batch):** Users select one or more commands (or a mix of commands and skills) in `LibraryView.qml`, choose target project(s) using the Library's project selector/copy mechanism, and click Copy.
>   3. **Conflict / Update Prompt for Existing Commands:** When copying selected commands to target project(s), check if any of the selected commands already exist in the target project(s) (`<project>/.agents/commands/<name>.md`).
>      - If one or more commands already exist in the target project(s), prompt the user with a clean confirmation dialog asking if they want to **Update / Overwrite** the existing command(s) in those project(s) (with options like *Update All*, *Skip Existing*, or *Cancel*).
>   4. **Automatic Skill Carry on Add & Update (ADR-0036):** Whenever commands are added OR updated in a project via this flow, automatically inspect the commands for referenced skills (`find_referenced_skills_in_command`) and trigger the skill carry flow (`copy_commands_with_skill_carry` / `CommandCarrySkillsDialog.qml`) so any referenced skills are carried over/updated alongside the commands.
>
> Before writing code, inspect the following files to understand the current implementation:
>
> - `src/skill_manager/core/commands.py` & `src/skill_manager/core/copier.py`
> - `src/skill_manager/controllers/ops/commands.py` & `src/skill_manager/controllers/ops/copy.py`
> - `src/skill_manager/controllers/app_proxies.py`
> - `src/skill_manager/SkillManagerComponents/dialogs/CommandCreateDialog.qml`
> - `src/skill_manager/SkillManagerComponents/dialogs/CommandCarrySkillsDialog.qml`
> - `src/skill_manager/SkillManagerComponents/CommandInspector.qml` & `CommandInspectorPanel.qml`
> - `src/skill_manager/SkillManagerComponents/views/LibraryView.qml`
> - `DESIGN.md` and `AGENTS.md` (strictly obey all 7 mandatory rules, especially Rule #6 for real-app visual verification and `Theme.qml` semantic token usage).
>
> ### 1. Architectural & Implementation Requirements
>
> #### A. Decouple Project Sync from Command Create/Edit (`CommandCreateDialog.qml`, `core/commands.py`, `controllers/ops/commands.py`)
>
> 1. **UI Cleanup (`CommandCreateDialog.qml` & `CommandInspector.qml`):**
>    - Remove the target project selection UI / checkboxes from `CommandCreateDialog.qml` (and any project-push controls in `CommandInspector.qml` if present).
>    - Resize/reflow `CommandCreateDialog.qml` cleanly using `Theme.qml` tokens so the dialog focuses purely on Command Name, Description/Frontmatter, Markdown Body, and Referenced Skills preview/syntax highlighting.
> 2. **Backend Save Simplification (`controllers/ops/commands.py` & `core/commands.py`):**
>    - Creating or editing a command from the dialog should write/update the canonical `.md` command file in the Library source directory and refresh discovery/cache (`patch_cache_add` / discovery update) without automatically fanning out or prompting for project removals.
>
> #### B. Unified Batch Copy & Update Detection (`core/copier.py` & `controllers/ops/copy.py`)
>
> 1. **Detect Existing Commands Before Copy:**
>    - In `core/copier.py` / `controllers/ops/copy.py`, when the user initiates a copy from `LibraryView` to target project(s) and the selection includes command items (`is_command == True` / `.md` commands):
>    - Check each target project's commands directory (`get_commands_dir(project_path)`) to see which selected commands already exist on disk.
> 2. **Update Confirmation Dialog / Flow:**
>    - If **no** selected commands exist in the target project(s), proceed directly to copying them + triggering the Skill Carry check.
>    - If **one or more** selected commands already exist in the target project(s):
>      - Emit a signal to QML to open a confirmation dialog (either a new reusable `CommandUpdateConfirmDialog.qml` or an enhanced mode of an existing conflict dialog styled with `Theme.qml` tokens).
>      - Display which command(s) already exist in which target project(s).
>      - Provide clear actions:
>        - **"Update Existing & Copy New"** (`overwrite_commands=True`): Overwrites existing `.md` command files in the target project(s) with the updated Library version and copies any new ones.
>        - **"Copy Only New (Skip Existing)"** (`overwrite_commands=False`): Keeps existing project commands untouched and only copies commands that don't exist yet.
>        - **"Cancel"**: Aborts the operation.
> 3. **Update `copy_command_files_to_projects` in `core/copier.py`:**
>    - Add an `overwrite: bool = False` parameter to `copy_command_files_to_projects(...)`.
>    - When `overwrite=True`, overwrite existing destination `.md` command files atomically/cleanly and record them in the copied/updated result list.
>
> #### C. Carry Respective Skills on Both Add and Update (ADR-0036)
>
> 1. **Skill Carry Integration (`controllers/ops/copy.py` & `CommandCarrySkillsDialog.qml`):**
>    - Ensure that whether commands are being **newly added** OR **updated/overwritten** in the target project(s) (both single-command copy and multi-command batch copy), the controller scans all commands being deployed via `find_referenced_skills_in_command`.
>    - If referenced skills are found:
>      - Trigger the existing Skill Carry workflow (`CommandCarrySkillsDialog.qml` / `copy_commands_with_skill_carry`) so the user can confirm/carry the respective skills into the target project(s) and rewrite/normalize skill reference paths if applicable.
>      - If the user simultaneously selected both a Command and its referenced Skill in the Library batch selection, deduplicate cleanly so the skill isn't copied twice or flagged erroneously as missing.
> 2. **Quick Copy Handoff Compatibility:**
>    - Ensure newly copied/updated commands and their carried skills also register with the one-shot Quick Copy handoff (if active) and update `_quick_copy_model` / `_library_model` caches immediately.
>
> #### D. Enable Command Selection & Copy in `LibraryView.qml`
>
> 1. Verify that when `showCommands` is enabled (or when viewing commands in `LibraryView.qml`), users can multi-select commands via checkboxes/batch selection and click the main Copy to Project button in `LibraryView.qml` just like skills.
>
> ### 2. Guardrails, Testing & Verification
>
> 1. **Code Quality & Tests:**
>    - Update existing unit tests in `tests/` that tested the old `CommandCreateDialog` multi-project sync behavior, and add new tests covering:
>      - Creating/updating a command in the Library without project arguments.
>      - Copying multiple commands to a project when some already exist (`overwrite=True` vs `overwrite=False`).
>      - Verifying that updating an existing command in a project still triggers `find_referenced_skills_in_command` and carries its respective skills.
>    - Run `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run pyright src/`, and `uv run pytest`.
> 2. **Mandatory Real-App Visual Verification (AGENTS.md Rule #6):**
>    - Launch the real app (`uv run skill-manager`) and capture screenshots via the in-process `QWindow.grabWindow()` helper for:
>      1. The simplified `CommandCreateDialog.qml` (confirming the project selector is gone and layout is clean).
>      2. Selecting multiple commands in `LibraryView.qml` and triggering Copy to a project where at least one command already exists, showing the **Update Command Confirmation Dialog**.
>      3. The resulting `CommandCarrySkillsDialog.qml` prompt carrying the respective skills for the added/updated commands.
>    - Inspect all screenshots and check `qml_console.log` to ensure zero QML errors or layout issues.

>
>
> We are refactoring the **Custom Slash Command Creation, Editing, and Project Deployment Workflow** so that deploying/updating commands in projects works identically to copying skills from the Library.
>
> ### Current vs. Desired Behavior
>
> - **Current Behavior:** Creating or editing a command inside `CommandCreateDialog.qml` (and `CommandInspector.qml` / `commands.py::update_custom_command_file_multi`) includes a multi-project selector inside the edit popup to sync/push the command to projects during save. Meanwhile, `copier.py::copy_command_files_to_projects` currently skips existing command files when copying.
> - **Desired Behavior:**
>   1. **Simplify Command Create/Edit Popup (`CommandCreateDialog.qml`):** Remove the project selector from the Create/Edit Command dialog. Creating or updating a command in the Library should only save/update the canonical command file in the Library.
>   2. **Unified Library Deployment (Single & Batch):** Users select one or more commands (or a mix of commands and skills) in `LibraryView.qml`, choose target project(s) using the Library's project selector/copy mechanism, and click Copy.
>   3. **Conflict / Update Prompt for Existing Commands:** When copying selected commands to target project(s), check if any of the selected commands already exist in the target project(s) (`<project>/.agents/commands/<name>.md`).
>      - If one or more commands already exist in the target project(s), prompt the user with a clean confirmation dialog asking if they want to **Update / Overwrite** the existing command(s) in those project(s) (with options like *Update All*, *Skip Existing*, or *Cancel*).
>   4. **Automatic Skill Carry on Add & Update (ADR-0036):** Whenever commands are added OR updated in a project via this flow, automatically inspect the commands for referenced skills (`find_referenced_skills_in_command`) and trigger the skill carry flow (`copy_commands_with_skill_carry` / `CommandCarrySkillsDialog.qml`) so any referenced skills are carried over/updated alongside the commands.
>
> Before writing code, inspect the following files to understand the current implementation:
>
> - `src/skill_manager/core/commands.py` & `src/skill_manager/core/copier.py`
> - `src/skill_manager/controllers/ops/commands.py` & `src/skill_manager/controllers/ops/copy.py`
> - `src/skill_manager/controllers/app_proxies.py`
> - `src/skill_manager/SkillManagerComponents/dialogs/CommandCreateDialog.qml`
> - `src/skill_manager/SkillManagerComponents/dialogs/CommandCarrySkillsDialog.qml`
> - `src/skill_manager/SkillManagerComponents/CommandInspector.qml` & `CommandInspectorPanel.qml`
> - `src/skill_manager/SkillManagerComponents/views/LibraryView.qml`
> - `DESIGN.md` and `AGENTS.md` (strictly obey all 7 mandatory rules, especially Rule #6 for real-app visual verification and `Theme.qml` semantic token usage).
>
> ### 1. Architectural & Implementation Requirements
>
> #### A. Decouple Project Sync from Command Create/Edit (`CommandCreateDialog.qml`, `core/commands.py`, `controllers/ops/commands.py`)
>
> 1. **UI Cleanup (`CommandCreateDialog.qml` & `CommandInspector.qml`):**
>    - Remove the target project selection UI / checkboxes from `CommandCreateDialog.qml` (and any project-push controls in `CommandInspector.qml` if present).
>    - Resize/reflow `CommandCreateDialog.qml` cleanly using `Theme.qml` tokens so the dialog focuses purely on Command Name, Description/Frontmatter, Markdown Body, and Referenced Skills preview/syntax highlighting.
> 2. **Backend Save Simplification (`controllers/ops/commands.py` & `core/commands.py`):**
>    - Creating or editing a command from the dialog should write/update the canonical `.md` command file in the Library source directory and refresh discovery/cache (`patch_cache_add` / discovery update) without automatically fanning out or prompting for project removals.
>
> #### B. Unified Batch Copy & Update Detection (`core/copier.py` & `controllers/ops/copy.py`)
>
> 1. **Detect Existing Commands Before Copy:**
>    - In `core/copier.py` / `controllers/ops/copy.py`, when the user initiates a copy from `LibraryView` to target project(s) and the selection includes command items (`is_command == True` / `.md` commands):
>    - Check each target project's commands directory (`get_commands_dir(project_path)`) to see which selected commands already exist on disk.
> 2. **Update Confirmation Dialog / Flow:**
>    - If **no** selected commands exist in the target project(s), proceed directly to copying them + triggering the Skill Carry check.
>    - If **one or more** selected commands already exist in the target project(s):
>      - Emit a signal to QML to open a confirmation dialog (either a new reusable `CommandUpdateConfirmDialog.qml` or an enhanced mode of an existing conflict dialog styled with `Theme.qml` tokens).
>      - Display which command(s) already exist in which target project(s).
>      - Provide clear actions:
>        - **"Update Existing & Copy New"** (`overwrite_commands=True`): Overwrites existing `.md` command files in the target project(s) with the updated Library version and copies any new ones.
>        - **"Copy Only New (Skip Existing)"** (`overwrite_commands=False`): Keeps existing project commands untouched and only copies commands that don't exist yet.
>        - **"Cancel"**: Aborts the operation.
> 3. **Update `copy_command_files_to_projects` in `core/copier.py`:**
>    - Add an `overwrite: bool = False` parameter to `copy_command_files_to_projects(...)`.
>    - When `overwrite=True`, overwrite existing destination `.md` command files atomically/cleanly and record them in the copied/updated result list.
>
> #### C. Carry Respective Skills on Both Add and Update (ADR-0036)
>
> 1. **Skill Carry Integration (`controllers/ops/copy.py` & `CommandCarrySkillsDialog.qml`):**
>    - Ensure that whether commands are being **newly added** OR **updated/overwritten** in the target project(s) (both single-command copy and multi-command batch copy), the controller scans all commands being deployed via `find_referenced_skills_in_command`.
>    - If referenced skills are found:
>      - Trigger the existing Skill Carry workflow (`CommandCarrySkillsDialog.qml` / `copy_commands_with_skill_carry`) so the user can confirm/carry the respective skills into the target project(s) and rewrite/normalize skill reference paths if applicable.
>      - If the user simultaneously selected both a Command and its referenced Skill in the Library batch selection, deduplicate cleanly so the skill isn't copied twice or flagged erroneously as missing.
> 2. **Quick Copy Handoff Compatibility:**
>    - Ensure newly copied/updated commands and their carried skills also register with the one-shot Quick Copy handoff (if active) and update `_quick_copy_model` / `_library_model` caches immediately.
>
> #### D. Enable Command Selection & Copy in `LibraryView.qml`
>
> 1. Verify that when `showCommands` is enabled (or when viewing commands in `LibraryView.qml`), users can multi-select commands via checkboxes/batch selection and click the main Copy to Project button in `LibraryView.qml` just like skills.
>
> ### 2. Guardrails, Testing & Verification
>
> 1. **Code Quality & Tests:**
>    - Update existing unit tests in `tests/` that tested the old `CommandCreateDialog` multi-project sync behavior, and add new tests covering:
>      - Creating/updating a command in the Library without project arguments.
>      - Copying multiple commands to a project when some already exist (`overwrite=True` vs `overwrite=False`).
>      - Verifying that updating an existing command in a project still triggers `find_referenced_skills_in_command` and carries its respective skills.
>    - Run `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run pyright src/`, and `uv run pytest`.
> 2. **Mandatory Real-App Visual Verification (AGENTS.md Rule #6):**
>    - Launch the real app (`uv run skill-manager`) and capture screenshots via the in-process `QWindow.grabWindow()` helper for:
>      1. The simplified `CommandCreateDialog.qml` (confirming the project selector is gone and layout is clean).
>      2. Selecting multiple commands in `LibraryView.qml` and triggering Copy to a project where at least one command already exists, showing the **Update Command Confirmation Dialog**.
>      3. The resulting `CommandCarrySkillsDialog.qml` prompt carrying the respective skills for the added/updated commands.
>    - Inspect all screenshots and check `qml_console.log` to ensure zero QML errors or layout issues.

>
>
> We are adding a **Per-Project Task List** feature to SkillManager and redesigning `QuickCopyView.qml` (the Home / Quick Copy workspace) so users can manage separate task lists for each registered project right alongside their skills and slash commands.
>
> Before writing code, inspect the following files to ground your implementation in the existing architecture:
>
> - `src/skill_manager/core/schemas.py` & `src/skill_manager/core/persistence.py`
> - `src/skill_manager/core/config.py`
> - `src/skill_manager/controllers/app.py`, `src/skill_manager/controllers/app_proxies.py`, & `src/skill_manager/controllers/ops/`
> - `src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml`
> - `src/skill_manager/SkillManagerComponents/Theme.qml`
> - `DESIGN.md` and `AGENTS.md` (strictly follow all 7 mandatory rules, especially Rule #6 for real-app visual verification and Rule #7 for `input_guard.py`).
>
> ### 1. Feature Requirements & Architecture
>
> #### A. Data Model & Atomic Persistence (`core/schemas.py` & `core/tasks.py`)
>
> 1. **Pydantic Schemas (`core/schemas.py`):**
>    - Create `ProjectTaskRecord` (Pydantic v2 model):
>      - `id: str` (UUID or stable short hash)
>      - `title: str` (min_length=1)
>      - `description: str = ""` (optional context/notes or attached skill references)
>      - `completed: bool = False`
>      - `priority: Literal["low", "medium", "high"] = "medium"`
>      - `linked_skills: list[str] = []` (optional skill names/paths associated with this task)
>      - `created_at: float` / `updated_at: float`
>      - `order: int = 0`
>    - Create `ProjectTasksState` mapping canonical `project_path: str` -> `list[ProjectTaskRecord]`.
> 2. **Persistence (`core/tasks.py` & `core/persistence.py`):**
>    - Persist tasks in `DATA_DIR / "project_tasks.json"` using `persistence._atomic_write_json` and `FileLock` (matching `project_skill_ownership.json` patterns).
>    - Normalize project keys using the same path canonicalization used across `ConfigManager` so Windows/Linux path differences never orphan a project's task list.
>    - Support CRUD operations: `get_tasks(project_path)`, `add_task(...)`, `update_task(...)`, `toggle_task(...)`, `delete_task(...)`, `clear_completed_tasks(project_path)`, and `reorder_tasks(project_path, ordered_ids)`.
>
> #### B. Controller & Clipboard Integration (`controllers/`)
>
> 1. **Task Management Controller (`controllers/task_controller.py` or mixin in `OpsController`):**
>    - Wire into `AppController` and expose necessary properties/slots (and proxy slots on `AppControllerProxyMixin` if needed by QML conventions).
>    - React automatically when the active project filter/selection changes in `QuickCopyView` so the task list always reflects the currently selected project (and handle the "No Project Selected / All Projects" state gracefully with a prompt to select a project or a grouped overview).
>    - Expose signals and properties to QML:
>      - `currentProjectTasks` (`QVariantList` of task dicts for the active project)
>      - `activeTaskCount` / `completedTaskCount` (for status badges on project pills)
>    - Expose `@Slot` methods for QML:
>      - `addProjectTask(project_path: str, title: str, priority: str, description: str)`
>      - `toggleProjectTask(project_path: str, task_id: str)`
>      - `updateProjectTask(project_path: str, task_id: str, title: str, description: str, priority: str)`
>      - `deleteProjectTask(project_path: str, task_id: str)`
>      - `clearCompletedProjectTasks(project_path: str)`
>      - `copyTaskAsPrompt(project_path: str, task_id: str)`: Formats the task title, description, and any linked skill references (formatted according to the currently selected Client Format in QuickCopy: Codex, Gemini CLI, Antigravity, OpenCode, Plain Text) and copies it to the clipboard via `ClipboardService` for instant pasting into an agent!
>
> #### C. Redesign `QuickCopyView.qml` Layout (Home / Quick Copy Workspace)
>
> Redesign `QuickCopyView.qml` so the Per-Project Task List is a first-class citizen of the daily workflow without crowding the skill list or inspector. Strictly use semantic tokens from `Theme.qml` (no hardcoded colors/metrics) and provide full keyboard accessibility (`Accessible.role`, `Accessible.name` per ADR-0031):
>
> 1. **Project Bar Enhancement:**
>    - On the project selector pills/dropdown in `QuickCopyView.qml`, display a subtle badge showing the number of open tasks (e.g., `3`) for each project so users have immediate visibility when switching projects.
> 2. **Cohesive Workspace Layout Integration:**
>    - Integrate the **Project Tasks Panel** into `QuickCopyView.qml` using a clean, collapsible split-pane, dedicated drawer, or segmented workspace toggle alongside the Skills/Commands list and Inspector:
>      - **Header:** Shows `"Tasks — <Active Project Alias/Name>"`, an open/completed counter pill (e.g., `2 Open · 5 Done`), a filter toggle (`All` / `Active` / `Done`), and a `"Clear Done"` action.
>      - **Quick-Add Input Bar:** A sleek top input bar (`"Add a task for <Project>... (Enter to add)"`) with a quick priority selector pill (`Low` / `Med` / `High`) for frictionless keyboard-driven task entry.
>      - **Task List View:**
>        - Custom checkbox with smooth check state, task title (strikethrough + muted token when completed), priority indicator dot/pill, and optional expandable description/notes.
>        - Hover/focus quick actions on each task row:
>          - **Copy for Agent (`IconButton`):** Calls `copyTaskAsPrompt` to copy the task + client-formatted skill references directly to the clipboard with a toast confirmation.
>          - **Edit inline / modal** and **Delete (`IconButton`)**.
>      - **Empty States:**
>        - If no specific project is selected: Show a clean empty state prompting the user to select a project pill above to view/manage its tasks.
>        - If a project has 0 tasks: Show a lightweight empty state encouraging them to add their first task above.
> 3. **Responsive & Resizable Behavior:**
>    - Ensure the tasks panel can be collapsed/expanded (persisting its open/closed state in `UIStateRecord` / `config.json`) so users on smaller screens or compact layouts can toggle it effortlessly via a top-bar button or keyboard shortcut.
>
> ### 2. Guardrails, Testing & Verification
>
> 1. **Safety & Standards:**
>    - Never bypass `src/skill_manager/utils/input_guard.py` for any clipboard/paste automation.
>    - Maintain 100% compatibility with existing `QuickCopyView` skill copying, command carry dialogs, and MCP tools.
> 2. **Automated Tests:**
>    - Add unit tests in `tests/` covering `ProjectTaskRecord` validation, per-project isolation (Project A tasks never leak into Project B), atomic persistence across reloads, and `copyTaskAsPrompt` formatting with client syntax.
>    - Run `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run pyright src/`, and `uv run pytest`.
> 3. **Mandatory Real-App Visual Verification (AGENTS.md Rule #6):**
>    - Launch the real app (`uv run skill-manager`), navigate to `QuickCopyView`, select a project, create multiple tasks (with different priorities and completion states), and capture screenshots using the mandated in-process `QWindow.grabWindow()` workflow.
>    - Verify both Dark and Light themes, check `qml_console.log` for zero QML warnings/binding loops, and inspect the screenshots to confirm visual polish and layout balance.

>
>
> We are evolving the "Updates" section into a comprehensive **Skill Package Manager & Curated Catalog** ("Packages"). Users need to manage their installed skill packages, sync project skills, AND browse/install pre-configured community/curated skill packages via 1-click or custom configuration.
>
> Before writing code, inspect the following files to ground your implementation in the current architecture:
>
> - `src/skill_manager/core/schemas.py`
> - `src/skill_manager/core/skill_packages/config.py` & `storage.py`
> - `src/skill_manager/controllers/update_controller.py` & `app_proxies.py`
> - `src/skill_manager/SkillManagerComponents/Sidebar.qml` & `Main.qml`
> - `src/skill_manager/SkillManagerComponents/views/UpdatesView.qml`
> - `src/skill_manager/SkillManagerComponents/dialogs/PackageEditDialog.qml`
> - `DESIGN.md` and `AGENTS.md` (strictly obey all 7 mandatory rules, especially Rule #6 for real-app visual verification and `Theme.qml` token usage).
>
> ### 1. Feature Requirements & Architecture
>
> #### A. Curated Skill Package Catalog (Data & Domain Layer)
>
> 1. **Schema (`core/schemas.py`):**
>    - Create a Pydantic model `CatalogPackageTemplate` with fields:
>      - `id: str` (unique slug, e.g., `"vercel-skills"`, `"anthropic-skills"`)
>      - `display_name: str`
>      - `description: str`
>      - `author: str`
>      - `category: str` / `tags: list[str]`
>      - `source_type: str` (`"git"`, `"npx"`, `"script"`)
>      - `install_command: str` (the raw command or repo URL passed to `infer_package_metadata`, e.g., `npx skills add vercel-labs/skills` or `https://github.com/...`)
>      - `repository_url: str`
>      - `default_args: str = ""`
>      - `featured: bool = False`
> 2. **Curated Registry (`core/skill_packages/catalog.py` or JSON asset):**
>    - Create a built-in curated catalog of popular pre-existing skill libraries (also check if `data/skill_library_essentials.json` or existing fixtures have entries we should incorporate/migrate).
>    - Provide helper functions to query the catalog and cross-reference against currently installed packages (`UpdatePackageRecord` in `config.json`) by matching `repository_url`, `package_name`, or canonicalized repo aliases (`KNOWN_SKILL_REPO_ALIASES`) so the UI knows whether a catalog item is already `Installed`.
>
> #### B. Controller & Installation Flows (`controllers/update_controller.py` & `app_proxies.py`)
>
> Expose the catalog and two distinct installation flows to QML:
>
> 1. **`catalogPackages` Property:**
>    - Expose a `QVariantList` (or model) on `UpdateController` (and proxy on `AppController` if required by existing QML patterns) returning the catalog items enriched with an `is_installed: bool` and `installed_package_id: str` status. Update this automatically whenever packages are added, removed, or loaded.
> 2. **Flow 1 — One-Click Default Install (`installCatalogPackageDefault(catalog_id: str)`):**
>    - Resolves the catalog entry by `catalog_id`.
>    - Uses `infer_package_metadata()` and `resolve_package_storage()` to configure the package at the **default skill packages storage path** automatically.
>    - Saves the new `UpdatePackageRecord` and immediately triggers the background install/sync pipeline (staging/cloning + relocation + `DiscoveryController` refresh) with non-blocking progress feedback in the UI.
> 3. **Flow 2 — Configure & Install (`openCatalogPackageConfigure(catalog_id: str)` / Prefilled Dialog):**
>    - Opens `PackageEditDialog.qml` in a `"create_from_template"` / pre-filled mode.
>    - Pre-populates the dialog fields with the catalog item's `display_name`, `install_command` / `repository_url`, `source_type`, default target path, and optional arguments.
>    - Allows the user to customize the target installation directory, arguments, alias/name, or update command before clicking "Install / Save".
>
> #### C. Section Rename ("Updates" -> "Packages")
>
> 1. **UI Naming:**
>    - Rename the sidebar navigation item in `Sidebar.qml` from `"Updates"` to `"Packages"` (keep internal view key `"updates"` or alias it cleanly so `ui_state.startup_view`, shortcuts, and MCP navigation tools `sm_navigate` do not break!).
>    - Update the page header title, subtitle, and tooltips in `UpdatesView.qml` and `SettingsView.qml` (e.g., startup view dropdown labels) to reflect **"Packages"** (Skill Packages, Catalog & Project Sync).
>
> #### D. Redesign `UpdatesView.qml` Layout & `PackageEditDialog.qml`
>
> Redesign `UpdatesView.qml` strictly using semantic tokens from `Theme.qml` (no hardcoded colors/spacings) and full keyboard/Accessibility roles (`DESIGN.md` / ADR-0031):
>
> 1. **Top Header & Action Bar:**
>    - Clean title **"Packages"** with status summary pills (e.g., Installed count, Outdated count, Project Sync status).
>    - Primary actions: **"+ Add Custom Package"** button (opens blank `PackageEditDialog`), **"Check for Updates"** / **"Sync All"** button.
> 2. **Segmented View Switcher / Tabs (or Cohesive Split Layout):**
>    - Organize the page cleanly into three logical tabs or collapsible sections so the view isn't cluttered:
>      1. **Installed Packages:** Cards/rows for currently installed packages showing version probe status, last checked time, update/reinstall/edit/delete actions.
>      2. **Discover Library (Curated Catalog):** A responsive grid or rich list of curated skill packages with search/tag filtering. Each card displays:
>         - Title, Author badge, Source type badge (`git` / `npx`), Description, and Tags.
>         - If not installed: Primary **"Install"** button (1-click default path install with spinner state while installing) + Secondary **"Configure…"** icon/button (opens `PackageEditDialog` pre-filled with the package's config).
>         - If already installed: **"Installed ✓"** badge + quick action to **"Reconfigure"** or **"Update"**.
>      3. **Project Sync:** The per-project surgical git sync status (`up_to_date` / `outdated` / `missing`) and 1-click project sync controls.
> 3. **`PackageEditDialog.qml` Enhancement:**
>    - Add a `openWithTemplate(templateData)` (or equivalent property/function) to `PackageEditDialog.qml` so when triggered from a Catalog card's "Configure…" button, all fields (`installCommand`, `displayName`, custom install path, etc.) are pre-populated and ready for user adjustment prior to installation.
>
> ### 2. Guardrails, Testing & Verification
>
> 1. **Backward Compatibility:** Do not break existing `config.json` keys, `UpdatePackageRecord` validation, or MCP tool contracts (`sm_navigate`, `sm_get_current_view`).
> 2. **Unit & Controller Tests:**
>    - Add pytest tests covering catalog lookup, `is_installed` state detection, `installCatalogPackageDefault`, and template pre-fill logic.
>    - Run `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run pyright src/`, and `uv run pytest` to ensure zero regressions.
> 3. **Mandatory Real-App Visual Verification (AGENTS.md Rule #6):**
>    - Launch the real app, navigate to the redesigned **Packages** view, and capture screenshots of:
>      - The Installed Packages tab/section
>      - The Discover Library (Catalog) tab/section
>      - The `PackageEditDialog` opened via "Configure…" with pre-filled values
>    - Inspect all screenshots to verify alignment, theme token contrast, and zero QML console errors (`qml_console.log`).

### In Progress

---

## 4. Bug Tracker


---

## 5. Icebox / Backlog

### Windows code signing — free OSS route (SignPath Foundation)

* [ ] Submit application at [https://signpath.org/apply](https://signpath.org/apply) — repo URL, Releases page, short description. Prerequisites are already in place: EXE `ProductName`/`ProductVersion` metadata and the README code signing policy.
* [ ] After approval: create the organization / project / signing-policy / artifact-configuration on signpath.io, add the `SIGNPATH_API_TOKEN` secret, then apply the workflow diff in [`docs/RELEASING.md`](docs/RELEASING.md).
* [ ] On Windows: align `installer.iss` `MyAppPublisher` so Add/Remove Programs matches the Authenticode publisher (SignPath Foundation). Needs a Windows machine — Inno Setup cannot be compiled on Linux.

### Leaked code-signing key (`packaging/windows/certs/code-signing.pfx`)

* [X] Removed on 2026-10-19 by deleting and recreating the repository. A rewrite alone could not: 138 `refs/pull/*` refs served the blob and cannot be rewritten by pushing. See `docs/SECURITY.md` for the measurement and the cost paid.
* [ ] Rotate/revoke the superseded certificate once a replacement is in use — revocation is what actually retires the key.
