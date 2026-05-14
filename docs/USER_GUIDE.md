# User Guide

Welcome to SkillManager, your professional tool for organizing, editing, and synchronizing AI agent skills across multiple project repositories.

## Overview of Views

The application is divided into four main views, accessible via the left sidebar:

1.  **Library**: Your central repository of all agent skills.
2.  **Quick Copy**: A fast way to browse skills currently active in your specific projects.
3.  **Updates**: The hub for syncing changes between your library and your target projects.
4.  **Settings**: Application configuration, including sources and targets.

---

## 1. Library View

The Library is where you manage your source skills.

-   **Searching & Filtering**: Use the search bar at the top to instantly filter skills by name, content, or category. You can also use the category dropdown to view specific types of skills (e.g., `Architecture`, `Testing`).
-   **Skill Inspector**: Clicking on any skill opens the Inspector pane on the right. Here you can read the full documentation of the skill, view its raw Markdown, and manage its metadata.
-   **Creating Commands**: From the Inspector, you can create quick custom `.md` commands based on the skill for specific projects.
-   **Copying to Projects**: You can select one or multiple skills (using checkboxes) and hit the "Copy to Targets" button to deploy them into specific project folders.

---

## 2. Quick Copy View

The Quick Copy view is designed for daily workflow efficiency when working within a specific project.

-   **Project Context**: Use the top dropdown to select the project you are currently working on. The view will update to show only the skills that are installed in that specific project.
-   **One-Click Copy**: Click the "Copy Reference" button next to any skill. This copies a formatted reference (e.g., `@.agents/skills/my-skill/SKILL.md`) directly to your clipboard, ready to be pasted into your AI chat or prompt.
-   **Custom Collections**: You can create custom groups of skills (e.g., "Frontend Setup") to quickly select and copy multiple references at once.

---

## 3. Updates View

When you modify a skill in your central library, you need to push those changes to the projects using it.

-   **Scan for Updates**: Click "Scan for Updates" to compare your library against all configured target projects. The system will identify which projects have outdated or missing skills.
-   **Syncing**: You can update individual skills in specific projects, or click "Update All Outdated" to synchronize everything at once.

---

## 4. Settings View

Configure how SkillManager integrates with your file system.

-   **Skill Sources**: Add the directories where your central library of skills is stored.
-   **Target Projects**: Add the root directories of the projects where you want to deploy skills. SkillManager will automatically manage the `.agents/skills/` directory within these targets.
-   **Client Format**: Choose how SkillManager formats references when copying to the clipboard (e.g., Antigravity, standard Markdown, raw paths) to match your specific AI agent's required syntax.
-   **Appearance**: Toggle Dark/Light mode and other UI preferences.
