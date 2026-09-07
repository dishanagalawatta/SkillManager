# ADR-0032: Local-Only Prefilled GitHub Issue URL with Manual Diagnostic Bundle Attach

> Status: **Accepted**
> Date: 2026-09-07
> Owner: @DIKKA

## Context

Settings had no report flow, so users hitting a bug had to hand-write an issue
with no version, OS, or log context attached. Diagnostic file writes sit off by
default (`set_enabled` opt-in), which keeps most production reports empty even
when the in-memory ring holds the last 1000 events. App logging had two more
gaps: `skill_manager.log` grows without bound, and the QML log truncates early,
so neither is a sound base for bug reports. Commit fbc2d22 closes the loop with
a report path that works in that reality.

## Decision

1. **`build_report_issue_url` in `core/diagnostics.py` builds the issue URL locally.**
   It templates app version, OS and Python/Qt versions, health status
   (`get_health_status`), level counts (`get_diagnostic_counts`), and the log
   path into the `issues/new` title and body. It performs no network I/O.
2. **Bundle export stays manual.** `export_bundle` zips the current log, rotated
   logs, and a manifest (`diagnostic_bundle.json` with versions, OS, log level,
   recent events) via `exportDiagnosticBundle` / `getReportBundlePath`, and the
   user attaches the zip to the issue by hand.
3. **Controller slots wire it to QML.** `getReportIssueUrl(summary, body)`,
   `getReportBundlePath(output_dir)`, and `openReportIssue(url)` (opened via
   `QDesktopServices`) expose the flow to `DiagnosticsPane.qml`.
4. **Bound the app log.** `skill_manager.log` moves to a `RotatingFileHandler`
   at 5 MB x 5 files.
5. **Split capture from persistence.** The ring buffer stays always-on so
   `get_recent_events` works in production, while JSON-line file writes remain
   opt-in. `SKILL_MANAGER_LOG_LEVEL` is honored for both loggers.

## Consequences

### Positive

- Every report arrives with version, OS, health, counts, and log path already filled in.
- No token, account, or network permission needed to file a report.
- Bounded log size caps disk use while the always-on ring keeps recent events available.

### Negative

- Manual attach adds friction, and some users will file without the bundle.
- Prefilled URLs can hit browser URL length limits on long bodies.
- Report quality still depends on file-write opt-in; default-off installs yield thin logs.

### Neutral

- The bundle carries no PII beyond local paths and log content the user can inspect before attaching.

## Alternatives Considered

### Auto-submit via GitHub API

Rejected: needs a personal token stored in the app, adds auth and network failure
modes, and posts user log content without an explicit review step.

### Sentry-only reporting

Rejected: Sentry is opt-in and empty by default, so it can't cover reporters who
never enabled it. It stays a complement, not the report path.

### Leaving diagnostics fully off

Rejected: keeps production reports empty by design and wastes the ring buffer
that already captures the events support needs.

## References

- Commit fbc2d22 (implements report flow)
- `src/skill_manager/core/diagnostics.py` (`build_report_issue_url`, `export_bundle`)
- `src/skill_manager/controllers/config/diagnostics.py` (report slots)
- `DiagnosticsPane.qml`
- `release_check_service.GITHUB_REPO` (`dishanagalawatta/SkillManager`)
