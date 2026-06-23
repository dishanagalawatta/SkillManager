# Environment Variables

> Canonical reference. `.env.example` is the source for *defaults*; this
> file is the source for *contract*. Update both when a variable is added,
> renamed, or retired.

## Read order

All variables are read once at process start. Restart the app to apply
changes. `.env` overrides process environment.

## Qt / QML

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `QT_QUICK_CONTROLS_STYLE` | yes (test) | unset | Must be `Basic` in headless tests. |
| `QML_DISABLE_DISK_CACHE` | yes | `0` | Set to `1`. See ADR-0001. |
| `QT_QPA_PLATFORM` | test only | native | `offscreen` in CI. |

## Application

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SKILL_MANAGER_TESTING` | test only | unset | Skip analytics/network/state-restore. |
| `SKILL_MANAGER_SKIP_INITIAL_LOAD` | test only | unset | Skip initial skill load. |
| `SKILL_MANAGER_DATA_DIR` | optional | platformdirs | Override user data dir. |
| `SKILL_MANAGER_LOG_LEVEL` | optional | `INFO` | QML console bridge log level. |

## Telemetry

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `POSTHOG_PROJECT_TOKEN` | optional | empty | Empty disables. |
| `POSTHOG_HOST` | optional | empty | PostHog host URL. |
| `SENTRY_DSN` | optional | empty | Empty disables Sentry. |

## Conventions

- `.env` is git-ignored.
- All variables are read at process start.
- CI sets `QT_QPA_PLATFORM=offscreen` and `SKILL_MANAGER_TESTING=1` automatically.
- Test runs set `SKILL_MANAGER_DATA_DIR` to a per-run tempdir.
