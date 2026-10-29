# User Guide

Welcome to SkillManager, your professional tool for organizing, editing, and synchronizing AI agent skills across multiple project repositories.

## Overview of Views

The application is divided into four main views, accessible from the top ribbon:

1. **Library**: Your central repository for all agent skills. Features multi-select deployment and deep inspection.
2. **Workbench**: A project-focused workspace for rapid reference copying and per-project tasks during active development.
3. **Hub**: A centralized hub for managing skill packages — install curated packages, track updates, and sync your library with Git sources and projects.
4. **Settings**: Comprehensive configuration for paths, branding, deployment formats, shortcuts, and appearance.

---

## 1. Library View

The Library is where you manage your source skills.

- **Searching & Filtering**: Use the search bar at the top to instantly filter skills by name, content, or category. You can also use the category dropdown to view specific types of skills.
- **Multi-Select**: Use checkboxes or selection shortcuts to select multiple skills for batch operations.
- **Skill Inspector**: Clicking on any skill opens the Inspector pane on the right. Here you can read the full documentation, view raw Markdown, and manage metadata.
- **Creating Commands**: From the Inspector, create custom `.md` commands based on the skill for specific projects.

> **Multi-project deployment.** You can now deploy a custom command to
> multiple projects at once. The Create/Edit dialog shows a multi-select
> dropdown - click individual projects or use "All Projects" to select
> every repository. Edits update every copy; the delete confirmation
> lets you choose which projects to remove the command from.
> **Smart no-op.** If the destination file already contains the same content,
> SkillManager skips the write and does not show the conflict dialog — even
> when the target project is different from the source.
- **Customize a command's emoji**: Each custom command shows a default 📜 icon in the list. You can replace it with any emoji you like. Open the **Create Command** dialog (the emoji picker is available there), or edit an existing command and click the emoji button to open the picker. Choose an emoji and it saves immediately, overriding the default. To go back to the default, pick 📜 from the picker or use the reset button. Recently used emojis appear at the top of the picker for quick reuse. Your custom emoji is stored in the app settings (not in the command's `.md` file), so it survives edits, renames, and redeploys. Note: this applies to commands only, not to skills.
- **Copying to Projects**: Select one or multiple skills and use the "Copy to Projects" button to deploy them into specific project folders.
- **Archive/Unarchive**: Archive skills you don't need while keeping them available for restoration.
- **Star/Favorite**: Star important skills to pin them to the top of the list.
- **Automatic Categorization**: Skills are intelligently categorized based on content analysis. For a full list of supported categories and their trigger keywords, see the **[Categorization Guide](CATEGORIES.md)**.
- **Custom Collections**: Group skills into named collections for quick filtering and batch operations.

---

## 2. Workbench View

The Workbench is designed for daily workflow efficiency when working within a specific project.

- **Project Context**: Use the top dropdown to select the project you are currently working on. The view updates to show only skills installed in that project.
- **Quick-Switch Button**: The swap icon in the top bar instantly toggles between the currently selected project and the previously selected one. Its tooltip shows the target project. This is handy when you bounce between two projects — click it repeatedly to cycle back and forth. The last project is remembered across app restarts.
- **One-Click Copy**: Click the "Copy Reference" button next to any skill. This copies a formatted reference (e.g., `@.agents/skills/my-skill/SKILL.md`) directly to your clipboard.
- **Client Format**: The toolbars carry one button per enabled AI agent format. Clicking a button makes it the active format and changes the syntax used for copied references: Antigravity, Gemini CLI, Codex, OpenCode, or Plain Text. The format menu next to those buttons lists every format, so you can switch to one you have not pinned to the bar — see *Settings → Enabled Client Formats* below.
- **Custom Collections**: Create custom groups of skills for quick batch reference copying.
- **Manual Input**: Add raw text references or notes alongside your skill references.
- **Starred Items**: Starred skills and commands are shown as first-class items in the Workbench workflow.
- **Command Skill Carry**: When you copy a command to another project, SkillManager automatically detects which skills the command references (e.g., `/git-pr`, `@cavecrew`). If any of those skills are missing in the target project, a carry dialog appears listing them. You can toggle individual skills, carry all, or skip and copy commands only. This ensures commands work in every project without manual dependency tracking. When a command edit spans multiple projects, the missing skills are merged into a single prompt (one union list for all projects, copied per project on confirm). Re-editing after a full carry stays silent — if nothing is missing, no dialog appears.
- **Per-Project Task List**: A collapsible panel next to the skill list holds a task list for the *active* project. Toggle it with the checklist button in the top bar or with `Ctrl+Shift+L`. The panel shows an open/done counter and an All/Active/Done filter, and each row offers copy, inline edit, and delete. The project dropdown carries a badge with the number of open tasks, so you can see at a glance which project still has work waiting. "Copy for Agent" puts the task title, its notes, and any linked skill references on the clipboard, formatted for the client format you selected.
- **Inline Composer**: Tasks are written at the bottom of the task list — no dialog. Type a title on the first line and keep typing for notes: the first non-empty line becomes the title and everything after it becomes the task notes. `- `, `* `, and `- [ ] ` bullets continue on `Enter`, so a checklist can be typed straight into the composer. `Ctrl+Enter` (or the **Add** button) saves, `Esc` discards the draft. The priority pill sits inside the composer, and the draft is kept per project so switching away does not lose what you were typing.
- **Images in Tasks**: Paste an image with `Ctrl+V` while the composer has focus (text pasting behaves normally), drop one onto the composer, or click the paperclip to pick a file. Attachments show as thumbnails on the task row and are stored inside the app data directory, keyed per project; deleting or clearing a task removes its files.

---

## 3. Hub View

When you modify a skill in your central library, you need to push those changes to projects using it.

- **Git Updates**: Manage your skill sources (Git repos). Check for new versions and update your local library.
- **Three Tabs**: *Installed* lists the packages you have, *Discover* is a curated catalog of ready-to-install skill collections, and *Project Sync* shows the per-project skill status.
- **Curated Catalog**: The *Discover* tab lists popular skill packages (Vercel Skills, Anthropic Skills, Agentic Awesome Skills, …). **Install** sets one up with its default configuration; **Configure…** opens the package dialog pre-filled so you can change the target directory, the arguments or the alias first. Packages you already have are badged **Installed ✓**. The catalog is extensible — drop a `package_catalog.json` into the app data directory to add your own entries.
- **Status Summary**: The header shows how many packages are installed, how many are outdated, and how many could not be checked.
- **Surgical Sync**: The system compares skill versions across projects and identifies precisely which skills are outdated.
- **Syncing**: Update individual skills in specific projects, or use sync to bring all projects up to date.
- **Skill Package Management**: Add, edit, and manage update sources across multiple protocols with an ultra-sleek, streamlined dialog:
  - **Smart Real-Time Auto-Detection**: As you type or paste a package identifier into the primary input, SkillManager instantly infers both the **Protocol** (NPX, GitHub, or Custom Script) and a humanized **Display Name** (e.g. `npx skills add vercel-labs/find-skills` $\rightarrow$ `Find Skills`, `https://github.com/sickn33/agentic-awesome-skills.git` $\rightarrow$ `Agentic Awesome Skills`, `@modelcontextprotocol/server-filesystem` $\rightarrow$ `Server Filesystem`, `./sync.sh` $\rightarrow$ `Sync`). Both the Display Name and Protocol remain fully editable at any time.
  - **Live Input Validation**: Package name fields feature dynamic inline validation (such as a green `✓` indicator) confirming valid package structures as you type.
  - **NPX Packages & Skills CLI**: Direct support for NPM-published skill packages (e.g. `@org/skills`), GitHub shorthand repositories (`owner/repo`), and `skills` CLI commands (`npx skills add <repo>`). SkillManager provides **Auto-Detected Versioning** via the NPM registry and upstream Git tags (<100ms non-blocking lookups), automatic non-interactive flags (`-y`), and self-healing canonical repository resolution. An optional *Advanced Overrides* section is available if custom repository URLs or CLI flags are needed.
  - **Git Repositories**: Track upstream GitHub/GitLab repositories with **Auto-Detected Versioning** (semantic release tags, git tags, and HEAD commits from remote repositories and local workspaces). Supports full URLs (`https://github.com/owner/repo.git`) and GitHub shorthand (`owner/repo`), connection verification, optional authentication tokens, and collapsible *Advanced Overrides* for custom version query commands.
  - **Custom Scripts**: Configure arbitrary shell commands to pull, generate, and check versions for local or custom skills pipelines.



- **Source Updating**: Run batch updates on all or selected skill packages with real-time status reporting.
- **Header count & Update All**: The "N updates" badge counts outdated packages 1:1 with the per-package Update buttons. **Update All** installs every pending package update, then flips to **Up to Date** (disabled) as soon as the new versions land.
- **Update notifications**: With Auto Update on (Settings), a bottom-right popup confirms each background update. With it off, a bottom-right popup with an **Update** button appears whenever updates are found — clicking it opens this view and starts Update All.
- **Clean Package Removal**: Removing a package via the delete button in the Hub automatically cleans up its local storage directory (e.g. `~/.agent/skills/<pkg-slug>`), git clone cache under `package_clones/`, lockfiles, and persisted inventory, while simultaneously purging all package skills from the Library and Workbench models with zero orphaned disk files.
- **Instant Discovery on Add**: Adding a project or package folder registers it with the file watcher and triggers a silent background refresh — its skills appear in the Library immediately, with no restart or manual refresh needed.
- **Automatic Skill Linking**: When you add a project folder, any skill already present there that matches a package skill by name **and** identical file contents is automatically linked to that package. Linked skills are tracked as package-owned, so future updates and syncs manage them correctly without a full update cycle.


---

## 4. Settings View

Configure how SkillManager integrates with your system.

- **Skill Sources**: Manage the directories and Git repositories that feed your library.
- **Project Projects**: Configure project root directories. SkillManager manages the `.agents/skills/` folder in these locations.
- **Branding & Client Selector**: Choose your preferred AI agent (Antigravity, Gemini CLI, Codex, OpenCode, Plain Text). This updates the application's logo and reference syntax.
- **Enabled Client Formats**: The Workbench toolbar shows one button per enabled client format — **Plain Text** and **Gemini CLI** by default. Add a format (up to four) or remove any beyond the first two; the format menu on the toolbar still lists every available format, so a format you hide stays one click away.
- **Appearance**: Toggle Dark/Light mode, enable Mica/Acrylic effects (Windows only), reduced motion, and adjust the Scroll Speed Multiplier (0.5x to 5.0x) with real-time UI feedback for customized trackpad and mouse wheel scroll speed across all views. List rows always use the compact layout — there is no separate row-density setting.
- **Shortcuts**: Customize keyboard shortcuts for all major operations (search, copy, archive, delete, refresh, navigation, theme toggle) and per-collection shortcuts for one-keystroke copy+paste.
- **Updates**: SkillManager checks GitHub Releases automatically shortly after launch and once a day, showing a bottom-right "App update available" popup. **Update Now** downloads, checksum-verifies and installs the release for your install type (AppImage, `.deb` or Windows installer) and restarts; **View Release** opens the download page. The same actions live in **Settings → About** and the **Updates** hub, with live download progress and a cancel button. Source checkouts are not self-updatable — the card points at `scripts/update-local.sh` instead. See [INSTALL.md](INSTALL.md#update-skillmanager).
- **Skill Packages**: Toggle **Auto Update** on or off. Update checks always run at startup and every 6h. When on, updates install in the background and a bottom-right popup confirms completion. When off, a bottom-right popup with an **Update** button appears whenever updates are available — clicking it opens the Hub and starts the update.

---

## 5. Screenshot & Redaction

SkillManager includes a powerful screenshots and redaction feature.

- **Capture**: Take screenshots of any area of your screen while the app is open.
- **Redaction**: Use the Image Inspector to perform color-based PII redaction by isolating and removing specific pixel colors.
- **Saving**: Save annotated or redacted screenshots for inclusion in AI prompts.
- **Cancel**: Press `Escape` to cancel a screenshot capture at any time.

---

## Keyboard Shortcuts

| Shortcut (Default) | Action |
|---|---|
| **Find & Select** | |
| `Ctrl+F` | Search current view |
| `Ctrl+A` | Select all visible skills |
| `Esc` | Clear selection |
| **Clipboard** | |
| `Ctrl+C` | Copy selected skill reference |
| **Skill Ops** | |
| `F5` | Refresh current view |
| `Ctrl+Shift+X` | Archive selected skills |
| `Delete` | Delete selected skills |
| **Tree View** | |
| `Ctrl+E` | Expand all categories |
| `Ctrl+Shift+E` | Collapse all categories |
| `Home` | Scroll to top |
| **Navigate** | |
| `Alt+1` | Workbench view |
| `Alt+2` | Library view |
| `Alt+3` | Hub view |
| `Alt+4` | Settings view |
| **Tools** | |
| `Ctrl+T` | Toggle theme |
| `Ctrl+Shift+S` | Take screenshot |
| `Ctrl+Shift+L` | Toggle the Workbench task panel |
| *Customizable* | All shortcuts can be remapped in Settings |
| *Per-collection* | Each collection can have its own shortcut; pressing it copies the collection's skill references and pastes them into the focused field |

---

## Screen Reader & Keyboard Operation

SkillManager is fully operable without a mouse, and screen readers announce control state:

- **Toggles announce state**: select checkboxes, star/unstar, Show Archived, category expanders,
  and Settings switches all report checked/expanded on/off — not just "button".
- **Full keyboard flow**: `Tab` moves through lists, headers, checkboxes, and toolbar controls;
  `Space`/`Enter` activates the focused control; revealed-on-focus delete buttons and
  tooltip previews work from the keyboard, not just hover.
- **Tabs & formats**: Workbench/Library/Hub/Settings nav and the Settings
  General/Shortcuts/About tabs expose the selected tab; the Workbench client-format
  buttons expose the active format.
- **Annotation canvas**: the screenshot canvas, color/size/eraser presets, and resize handles
  are keyboard reachable (arrows nudge, `Delete` removes, `Space` cycles selection).

---

---

## Environment Variables

SkillManager reads environment variables from `.env` at startup.
Override defaults by setting variables in your shell or in `.env`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `QML_DISABLE_DISK_CACHE` | `0` | Set to `1` to disable QML bytecode cache. |
| `SKILL_MANAGER_LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `SKILL_MANAGER_DATA_DIR` | (platformdirs) | Override the user data directory. |
| `POSTHOG_PROJECT_TOKEN` | (empty) | PostHog analytics token. Empty disables. |
| `SENTRY_DSN` | (empty) | Sentry error reporting DSN. Empty disables. |

For tiered environment configurations (dev, staging, prod), see
[`environments/README.md`](../environments/README.md) and
[`docs/ENVIRONMENT.md`](ENVIRONMENT.md).

---

## Troubleshooting & Report Issue

If something breaks, export diagnostics and file an issue with the bundle attached:

1. Open **Settings > About > Diagnostics** and click **Expand**.
2. Fill in **Summary** and **Description** (steps to reproduce).
3. Click **Export Bundle** — saves `diagnostic_bundle_*.zip` (manifest + logs + 50 recent events).
4. Click **Copy Issue URL** (prefilled title, version, OS, health, event counts), open it in your browser, and attach the bundle manually.

Notes: the last 1000 events are always kept in memory; file logging stays opt-in via Settings. `skill_manager.log` rotates at 5 MB x 5; `qml_console.log` appends and truncates only over the 5 MB cap. Telemetry is off unless analytics credentials are configured, and you can switch it off at any time under **Settings > Diagnostics > Share Anonymous Usage Data**.

---

## Command-Line Options

When launching from the terminal or scripts:

| Option | Description |
|---|---|
| `-v`, `--version` | Print application version and exit |
| `--mcp` | Start headless Model Context Protocol (MCP) server |
| `--mcp-allow-write` | Enable write/mutation tools in MCP server |

---

## Tips & Tricks

- **Drag & Drop**: Drag source and project directories directly into the Hub to add them.
- **Project Aliases**: Give friendly names to project paths for easier identification in dropdowns.
- **Temporary Copies**: Use "Copy to Project (Temporary)" for one-off testing without permanent deployment.
