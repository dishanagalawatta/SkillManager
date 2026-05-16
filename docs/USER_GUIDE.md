# User Guide

Welcome to SkillManager, your professional tool for organizing, editing, and synchronizing AI agent skills across multiple project repositories.

## Overview of Views

The application is divided into four main views, accessible via the left sidebar:

1.  **Library**: Your central repository for all agent skills. Features multi-select deployment and deep inspection.
2.  **Quick Copy**: A project-focused view for rapid reference copying during active development.
3.  **Updates**: A centralized hub for synchronizing your library with Git sources and target projects.
4.  **Settings**: Comprehensive configuration for paths, branding, and deployment formats.

---

## 1. Library View

The Library is where you manage your source skills.

-   **Searching & Filtering**: Use the search bar at the top to instantly filter skills by name, content, or category. You can also use the category dropdown to view specific types of skills (e.g., `Architecture`, `Testing`).
-   **Skill Inspector**: Clicking on any skill opens the Inspector pane on the right. Here you can read the full documentation of the skill, view its raw Markdown, and manage its metadata.
-   **Creating Commands**: From the Inspector, you can create quick custom `.md` commands based on the skill for specific projects.
-   **Copying to Projects**: You can select one or multiple skills (using checkboxes) and hit the "Copy to Targets" button to deploy them into specific project folders.
-   **Automatic Categorization**: SkillManager intelligently categorizes your skills based on their content. By analyzing keywords in the title and description, the app assigns a visual identity (emoji) to each skill. For a full list of supported categories and their trigger keywords, see the **[Categorization Guide](CATEGORIES.md)**.

---

## 2. Quick Copy View

The Quick Copy view is designed for daily workflow efficiency when working within a specific project.

-   **Project Context**: Use the top dropdown to select the project you are currently working on. The view will update to show only the skills that are installed in that specific project.
-   **One-Click Copy**: Click the "Copy Reference" button next to any skill. This copies a formatted reference (e.g., `@.agents/skills/my-skill/SKILL.md`) directly to your clipboard, ready to be pasted into your AI chat or prompt.
-   **Custom Collections**: You can create custom groups of skills (e.g., "Frontend Setup") to quickly select and copy multiple references at once.

---

## 3. Updates View

When you modify a skill in your central library, you need to push those changes to the projects using it.

- **Git Updates**: Manage your skill sources (Git repos). Check for new versions and update your local library with one click.
- **Surgical Sync**: The system compares skill versions across your projects and identifies precisely which skills are outdated.
- **Syncing**: Update individual skills in specific projects, or use "Sync All" to bring all project targets up to date with your library.

---

## 4. Settings View

Configure how SkillManager integrates with your file system.

- **Skill Sources**: Manage the directories and Git repositories that feed your library.
- **Target Projects**: Configure project root directories. SkillManager manages the `.agents/skills/` folder in these locations.
- **Branding & Client Selector**: Choose your preferred AI agent (Antigravity, Gemini CLI, Codex). This updates the application's logo and the syntax used for copying references.
- **Appearance**: Toggle Dark/Light mode and Mica/Acrylic effects (Windows only).
