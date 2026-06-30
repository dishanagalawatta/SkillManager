<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into Skill Manager. A new analytics module was created and 10 events were instrumented across the app's core user flows, covering app startup, skill deployment, source management, and user engagement actions.

## Changes made

### New files
- **`src/skill_manager/core/analytics.py`** — PostHog client initialisation, persistent device ID helper, and `capture_event` / `capture_exception` / `shutdown` helpers. Reads credentials from environment variables and registers a graceful shutdown via `atexit`.
- **`.env`** — Stores `POSTHOG_PROJECT_TOKEN` and `POSTHOG_HOST` (covered by `.gitignore`).

### Modified files
- **`src/skill_manager/app.py`** — Imports the analytics module and adds event capture calls throughout `AppController`.
- **`pyproject.toml`** — `posthog` and `python-dotenv` added as dependencies.

## Instrumented events

| Event | Description | File |
|-------|-------------|------|
| `app_opened` | Fired when the app starts successfully | `src/skill_manager/app.py` |
| `skill_copied_to_project` | Fired when skills are copied to a target project, with `skills_copied`, `skills_merged`, `skills_failed`, and `skills_count` properties | `src/skill_manager/app.py` |
| `skills_deleted` | Fired when the user deletes one or more skills, with a `count` property | `src/skill_manager/app.py` |
| `skill_package_added` | Fired when a new skill source is added, with `source_type` property | `src/skill_manager/app.py` |
| `skill_package_removed` | Fired when a skill source is removed, with `source_type` property | `src/skill_manager/app.py` |
| `skill_package_updated` | Fired when a source update run completes, with `source_type` and `success` (bool) properties | `src/skill_manager/app.py` |
| `project_target_added` | Fired when a new project target directory is added, with `target_count` property | `src/skill_manager/app.py` |
| `skill_archived` | Fired when a skill is archived or restored, with an `action` property (`archived` / `restored`) | `src/skill_manager/app.py` |
| `skill_launched` | Fired when the user opens a skill folder in the OS file explorer | `src/skill_manager/app.py` |
| `skill_searched` | Fired when the user applies a category filter to the skill library | `src/skill_manager/app.py` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behaviour, based on the events we just instrumented:

- [Analytics basics dashboard](/dashboard/1588826)
- [Daily App Opens](/insights/mc5op95L) — App open frequency over the last 30 days
- [Skills Deployed to Projects](/insights/lSI3e06s) — Skill copy activity over time
- [Skill Source Update Outcomes](/insights/FkNvLuKm) — Update success vs failure, broken down by result
- [Key User Actions](/insights/KudZYTqi) — Skills launched, archived, deleted, and projects added in one view
- [Skill Source Lifecycle](/insights/U8R9vzzQ) — Sources added versus sources removed over time

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/integration-python/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
