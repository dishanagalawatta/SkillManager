# Environment Variables

Reference for every environment variable SkillManager reads.

## Test / CI

| Variable | Purpose | Default |
|----------|---------|---------|
| `QT_QUICK_CONTROLS_STYLE` | Qt Quick Controls style. Must be `Basic` for headless test runs. | unset (uses platform default) |
| `QT_QPA_PLATFORM` | Qt platform plugin. `offscreen` for headless CI. | unset (native) |
| `QML_DISABLE_DISK_CACHE` | Disable QML disk cache. Set user-scope permanently. PySide6 6.11.1 serves stale cached bytecode after QML edits; this prevents that class of bug. | unset |
| `SKILL_MANAGER_TESTING` | When set, `AppController` skips non-essential startup (analytics, real network, state restore). | unset |
| `SKILL_MANAGER_SKIP_INITIAL_LOAD` | When set, `AppController.__init__` does not auto-load skills on startup. | unset |
| `SKILL_MANAGER_DATA_DIR` | Override per-user data dir (`%APPDATA%/SkillManager` on Windows, `~/.local/share/SkillManager` on Linux). Tests should point to a per-run tempdir. | platform default |
| `SKILL_MANAGER_LOG_LEVEL` | Log level for the QML console bridge. `DEBUG` / `INFO` / `WARNING` / `ERROR`. | `INFO` |

## Analytics (PostHog)

| Variable | Purpose | Default |
|----------|---------|---------|
| `POSTHOG_PROJECT_TOKEN` | Project token for self-hosted or cloud PostHog. Empty disables telemetry. | empty |
| `POSTHOG_HOST` | PostHog host URL. | empty |

## Conventions

- `.env` is git-ignored; copy from `.env.example` for local overrides.
- All variables are read at process start. Restart the app to apply changes.
- CI sets `QT_QPA_PLATFORM=offscreen` and `SKILL_MANAGER_TESTING=1` automatically (see `run_tests.py`).
