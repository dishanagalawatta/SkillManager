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

## Tier Matrix

Each tier selects only the variables relevant to its use case.
See [`environments/README.md`](../environments/README.md) for full
details and file paths.

| Variable | Dev | Staging | Prod |
|----------|-----|---------|------|
| `QT_QUICK_CONTROLS_STYLE` | `Basic` | `Basic` | `Basic` |
| `QML_DISABLE_DISK_CACHE` | `1` | `1` | `1` |
| `QT_QPA_PLATFORM` | `offscreen` | `offscreen` | (unset) |
| `SKILL_MANAGER_TESTING` | `1` | `1` | (unset) |
| `SKILL_MANAGER_SKIP_INITIAL_LOAD` | `1` | `1` | (unset) |
| `SKILL_MANAGER_DATA_DIR` | (unset) | (unset) | (unset) |
| `SKILL_MANAGER_LOG_LEVEL` | `DEBUG` | `WARNING` | `ERROR` |
| `POSTHOG_PROJECT_TOKEN` | (empty) | (empty) | (required) |
| `POSTHOG_HOST` | (empty) | (empty) | (required) |
| `SENTRY_DSN` | (empty) | (empty) | (required) |

## Conventions

- `.env` is git-ignored.
- All variables are read at process start.
- CI sets `QT_QPA_PLATFORM=offscreen` and `SKILL_MANAGER_TESTING=1` automatically.
- Test runs set `SKILL_MANAGER_DATA_DIR` to a per-run tempdir.
- Tier-specific overrides live in [`environments/`](../environments/README.md).

## Deprecated

The following variables were removed in ADR-0010 (Drop TUF):
`TUF_KEY_*`, `TUF_REPO_*`. They are no longer read by the application.
