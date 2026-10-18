# Plan: Skill Package Update Workflow Reliability

Anchor symptom: **"sometimes updates are not working"**.

Priority order: reliability → responsiveness → efficiency.

## Workstreams

### WS1 — Every remote probe is bounded and honest (`versioning.py`)

- [x] Add `VersionProbe` frozen dataclass, `DEFAULT_GIT_TIMEOUT = 10.0`.
- [x] Add `_git_probe_env()` (non-interactive: no prompts, ssh `BatchMode`).
- [x] Pass `env=` **and** `kill_after_timeout=` on both `g.execute()` calls
      (previously the env dict was built and never passed; the probe was unbounded).
- [x] `probe_git_remote_version()`: tags → HEAD, explicit failure reason.
- [x] `looks_like_git_remote()` + `_normalize_remote_url()` so any plausible git
      remote is probed, not only github.com / gitlab.com.
- [x] `RemoteProbeCache` dedupes probes per `(url, token)` and records
      `attempted` / `failure_reason`.
- [x] `check_skill_package_versions(..., remote_cache=None)` is host-agnostic and
      records `check_status` / `check_error` / `last_checked_at`.
- [x] `get_git_tag` delegates for remote URLs while keeping its `str` contract.

### WS2 — A scan can never strand the app (`update_controller.py`, `update_service.py`)

- [x] `update_service.last_scan_error`, one shared `RemoteProbeCache` per scan.
- [x] `SCAN_WATCHDOG_MS = 90_000` implemented as a real `QTimer` instance.
- [x] `_finish_scan()` is the single exit path and always clears `_is_loading`.
- [x] Distinct messages for failure vs timeout; "— could not check N package(s)".
- [x] Auto-update is skipped after a failed or timed-out scan.

### WS3 — No record, config write, or cleanup silently loses data

- [x] `ConfigManager.save()` writes atomically (`_atomic_write_json`).
- [x] `UpdatePackageRecord` declares `check_status`, `check_error`,
      `last_checked_at`, `update_error` (the model uses `extra="ignore"`).
- [x] `_resolvePackageStorageState()` keeps un-validatable records and appends
      instead of truncating (a short result used to shift the positional write-back).
- [x] `removeUpdatePackage()` aborts with no mutation when storage deletion
      returns errors.
- [x] `addSkillPackage()` seeds `last_updated = "Installing…"`, returns
      `{ok, error, name, installing, check_status, warning}` and surfaces an
      add-time probe warning in the status line.

### WS4 — A failed check is visible and recoverable

- [x] `CHECK_STATUS_OK / FAILED / NEVER_CHECKED` constants.
- [x] `get_unchecked_packages()` / `count_unchecked_packages()`.
- [x] `UpdateController.retryPackageCheck(package_id)`, resolving by `package_id`
      in `finalize_ui` so a row removed mid-probe cannot be written wrongly.
- [x] `AppController.statsUnchecked` (+ `.pyi`) computed in `recalculateStats`.
- [x] `Theme.warning` / `Theme.warningHover`; `"warning"` role in
      `IconButton.qml` and `ActionButton.qml`.
- [x] Updates view: header "· N unchecked", per-row "· could not check", and the
      primary button becomes an amber **Re-check** when no newer version is known.
- [x] `SourcesMixin.verifyGitPackage` is async (`gitVerificationFinished(url, tag, error)`),
      so the network probe never runs on the GUI thread.
- [x] `PackageEditDialog.qml` `Connections` handler renders the result inline and
      clears the in-flight guard (`verifyingField` / `verifyingUrl`).

### WS5 — Bounded work and coalesced rescans

- [x] One shared `RemoteProbeCache` across both phases of `updateUpdatePackage`.
- [x] `_register_package_watcher(pkg_path)` (watcher only, no scan).
- [x] Post-install refresh routed through the coalescing `_schedule_discovery_refresh()`.
- [x] The add path no longer triggers a full pre-install `loadInitialData()`.

## Tests

- [x] `tests/test_update_reliability.py` — WS1/WS2/WS3/WS4/WS5 regression suite.
- [x] `tests/test_config_controller.py` — async verify (fail / success / empty URL).
- [x] `tests/test_update_controller.py` — updated for deduped probes and deferred refresh.
- [x] `tests/test_qml_qol_contract.py` — QML contracts for the unchecked state and
      the async verify wiring.
- [x] `tests/qml/test_qml_update_button_flow.py` — short storage resolution no
      longer truncates the list.

## Verification

- [x] `uv run ruff format src tests` / `ruff check src tests` clean.
- [x] `uv run pytest -n auto --dist loadfile` green.
- [x] Real-app visual verification (`scripts/verify_updates_view_real.py`):
      Updates view dark + light, the git verify dialog, and the inline async
      verify failure message — all rendered un-clipped.

## Notes

- The add path deliberately does not rescan: the install it schedules ends with
  its own coalesced refresh.
- `last_updated` is display-only, so seeding `"Installing…"` is safe.
- `UpdatePackageRecord.extra="ignore"` means any new UI-visible field must be
  declared on the model — that is why `update_error` had to become a real field.
- Out of scope (left to the maintainer): rotating the signing key and purging the
  previously committed `.pfx` blob from git history; running `winget validate` on
  Windows.
