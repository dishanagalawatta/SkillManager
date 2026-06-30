# User Guide

Welcome to SkillManager, your professional tool for organizing, editing, and synchronizing AI agent skills across multiple project repositories.

## Overview of Views

The application is divided into four main views, accessible via the left sidebar:

1. **Library**: Your central repository for all agent skills. Features multi-select deployment and deep inspection.
2. **Quick Copy**: A project-focused view for rapid reference copying during active development.
3. **Updates**: A centralized hub for synchronizing your library with Git sources and project projects.
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
- **Copying to Projects**: Select one or multiple skills and use the "Copy to Projects" button to deploy them into specific project folders.
- **Archive/Unarchive**: Archive skills you don't need while keeping them available for restoration.
- **Star/Favorite**: Star important skills to pin them to the top of the list.
- **Automatic Categorization**: Skills are intelligently categorized based on content analysis. For a full list of supported categories and their trigger keywords, see the **[Categorization Guide](CATEGORIES.md)**.
- **Custom Collections**: Group skills into named collections for quick filtering and batch operations.

---

## 2. Quick Copy View

The Quick Copy view is designed for daily workflow efficiency when working within a specific project.

- **Project Context**: Use the top dropdown to select the project you are currently working on. The view updates to show only skills installed in that project.
- **One-Click Copy**: Click the "Copy Reference" button next to any skill. This copies a formatted reference (e.g., `@.agents/skills/my-skill/SKILL.md`) directly to your clipboard.
- **Client Format**: Choose your preferred AI agent format (Antigravity, Gemini CLI, Codex, Plain Text). This changes the syntax used for copying references.
- **Custom Collections**: Create custom groups of skills for quick batch reference copying.
- **Manual Input**: Add raw text references or notes alongside your skill references.
- **Starred Items**: Starred skills and commands are shown as first-class items in the Quick Copy workflow.
- **Command Skill Carry**: When you copy a command to another project, SkillManager automatically detects which skills the command references (e.g., `/git-pr`, `@cavecrew`). If any of those skills are missing in the target project, a carry dialog appears listing them. You can toggle individual skills, carry all, or skip and copy commands only. This ensures commands work in every project without manual dependency tracking.

---

## 3. Updates View

When you modify a skill in your central library, you need to push those changes to projects using it.

- **Git Updates**: Manage your skill sources (Git repos). Check for new versions and update your local library.
- **Surgical Sync**: The system compares skill versions across projects and identifies precisely which skills are outdated.
- **Syncing**: Update individual skills in specific projects, or use sync to bring all projects up to date.
- **Skill Package Management**: Add, edit, and remove update sources (Git repos or local paths).
- **Source Updating**: Run batch updates on all or selected skill packages.

---

## 4. Settings View

Configure how SkillManager integrates with your system.

- **Skill Sources**: Manage the directories and Git repositories that feed your library.
- **Project Projects**: Configure project root directories. SkillManager manages the `.agents/skills/` folder in these locations.
- **Branding & Client Selector**: Choose your preferred AI agent (Antigravity, Gemini CLI, Codex, Plain Text). This updates the application's logo and reference syntax.
- **Appearance**: Toggle Dark/Light mode, enable Mica/Acrylic effects (Windows only), reduced motion, compact list rows.
- **Shortcuts**: Customize keyboard shortcuts for all major operations (search, copy, archive, delete, refresh, navigation, theme toggle) and per-collection shortcuts for one-keystroke copy+paste.
- **Updates**: Control auto-update checking, auto-download, and update check interval.
- **Skill Packages**: Toggle automatic skill package updates and choose update mode.

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
| `Alt+1` | Quick Copy view |
| `Alt+2` | Library view |
| `Alt+3` | Updates view |
| `Alt+4` | Settings view |
| **Tools** | |
| `Ctrl+T` | Toggle theme |
| `Ctrl+Shift+S` | Take screenshot |
| *Customizable* | All shortcuts can be remapped in Settings |
| *Per-collection* | Each collection can have its own shortcut; pressing it copies the collection's skill references and pastes them into the focused field |

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

## Tips & Tricks

- **Drag & Drop**: Drag source and project directories directly into the Updates view to add them.
- **Project Aliases**: Give friendly names to project paths for easier identification in dropdowns.
- **Temporary Copies**: Use "Copy to Project (Temporary)" for one-off testing without permanent deployment.
