# Architecture Decision Records

> All ADRs for SkillManager. This index is the **single source of truth** —
> when an architectural decision changes, update the relevant entry here
> and link the new ADR.

| # | Title | Status | Date |
|---|-------|--------|------|
| [ADR-0001](#adr-0001-disable-qml-disk-cache) | Disable QML disk cache | Accepted | 2025 |
| [ADR-0002](#adr-0002-appcontroller-dual-registration) | `AppController` dual registration | Accepted | 2025 |
| [ADR-0003](#adr-0003-qt-6111-strict-data-list-property) | Qt 6.11.1 strict `data` list property | Accepted | 2025 |
| [ADR-0004](#adr-0004-qml-diagnostic-via-qqmlapplicationengine) | QML diagnostic uses `QQmlApplicationEngine` | Accepted | 2025 |
| [ADR-0005](#adr-0005-python-tests-use-qapplication) | Python tests use `QApplication` | Accepted | 2025 |
| [ADR-0006](#adr-0006-opt-in-release-tags) | Opt-in release tags | Superseded by ADR-0009 | 2025 |
| [ADR-0007](#adr-0007-release-please-conventional-commits) | Release-please with Conventional Commits | Superseded by ADR-0009 | 2026 |
| [ADR-0008](#adr-0008-windows-only-distribution) | Windows-only distribution | Accepted | 2026 |
| [ADR-0009](#adr-0009-python-semantic-release-with-opt-in-tokens) | python-semantic-release with opt-in tokens | Accepted | 2026 |
| [ADR-0010](#adr-0010-drop-tuf-use-github-releases-api) | Drop TUF, use GitHub Releases API | Accepted | 2026 |
| [ADR-0011](#adr-0011-selection-refresh-invariant) | Selection refresh invariant | Accepted | 2026 |
| [ADR-0012](#adr-0012-window-state-integrity) | Window state integrity | Accepted | 2026 |
| [ADR-0013](#adr-0013-package-add-snap-to-latest-policy) | Package add: snap-to-latest policy | Accepted | 2026 |
| [ADR-0014](#adr-0014-package-edit-snap-to-latest-policy) | Package edit: snap-to-latest policy | Accepted | 2026 |
| [ADR-0015](#adr-0015-conductor-root-plan-archival) | Conductor root plan archival | Accepted | 2026 |
| [ADR-0016](#adr-0016-opencode-gitignore-policy) | `.opencode` gitignore policy | Accepted | 2026 |

---

## ADR-0015 — Conductor root plan archival

**Status:** Accepted

**Context.** Root-level `*.md` plans accumulated at `conductor/` over
time. These are temporary proposals, not tracks. Without a lifecycle
rule, stale plans clutter the workspace and confuse navigation.

**Decision.** Root-level plans follow a two-path rule:

1. **Promote.** When a plan is selected for implementation, create
   `conductor/tracks/<slug>/` with `metadata.json`, `plan.md`, and
   optionally `spec.md`. Delete or deprecate the root-level stub.

2. **Archive.** Plans idle ≥ 30 days are moved into
   `conductor/_archive/<YYYY-MM-DD>/`. The root retains only six
   authoritative files: `workflow.md`, `tracks.md`, `product.md`,
   `tech-stack.md`, `plan.md`, `design_decisions.md`.

**Consequences.** Conductor root is predictable. Stale plans are
recoverable from `_archive/` but no longer clutter the working
directory. The archival rule is documented in `conductor/workflow.md`
§ 4a.

---

## ADR-0016 — `.opencode` gitignore policy

**Status:** Accepted

**Context.** The `.opencode/` directory contains local agent tooling
configuration (`package.json`, `node_modules/`, plans). It is
developer-local and must not be committed. The directory's internal
`.gitignore` excludes its own files, but the main `.gitignore` did
not list the top-level directory, causing it to appear as untracked
in `git status`.

**Decision.** Add `.opencode/` to the main `.gitignore` under the
"OS & editor" section. The directory's internal `.gitignore` is
retained for backward compatibility but is now redundant at the
repository level.

**Consequences.** `.opencode/` is fully excluded from version
control. Developers who use opencode retain their local config;
CI and fresh clones never see it.

---

## ADR-0013 — Package add: snap-to-latest policy

**Status:** Accepted

**Context.** Adding a new skill package via `addSkillPackage` left
`current_version` empty while `latest_version` was auto-detected from
the registry. QML's fallback `|| "1.0.0"` rendered `v1.0.0 → v1.9.0`
with an **Update** button — a newly-added package appeared outdated
before any install had run. The model conflated "registered" with
"installed".

**Decision.** Three-part fix:

1. **Snap on add.** When a package is added via `addSkillPackage`,
   detect `latest_version` (phase 1) and then snap
   `current_version = latest_version` (phase 2) using the new
   `sync_current_to_latest` flag in `check_skill_package_versions`.
   The package shows **Up to Date** immediately; the **Update** button
   only appears when the registry moves ahead.

2. **Block on undetectable latest.** If `latest_version` is empty
   after phase-1 detection (no repo URL, npm unreachable, no
   `latest_version_command`), the controller returns a structured
   JSON error `{"ok": false, "error": "..."}` and does **not** append
   to `_update_packages`. The QML dialog shows an inline error and
   keeps the user's input for correction.

3. **No migration.** Existing packages with `current_version=""` are
   not auto-healed. Users fix them by re-adding or clicking Update
   once. Release notes document this.

**Consequences.** `addSkillPackage` now returns `result=str` (JSON)
instead of void. `PackageEditDialog.qml` inspects the return value
and shows an inline error on failure. The `_sync_current_to_latest_if_applicable`
helper is reused by both `force_refresh=True` (post-update) and
`sync_current_to_latest=True` (add) paths — no code duplication.

---

## ADR-0014 — Package edit: snap-to-latest policy

**Status:** Accepted

**Context.** Editing an existing skill package via `updateUpdatePackage`
had the same broken behavior that `addSkillPackage` exhibited before
ADR-0013: the QML dialog only sends user-input fields (no
`current_version`), so the record's `current_version` defaulted to `""`.
QML's `|| "1.0.0"` fallback rendered `v1.0.0 → vX.Y.Z` with an
**Update** button — a just-edited package appeared outdated.

Additionally, `updateUpdatePackage` used a single-phase call to
`check_skill_package_versions` without `sync_current_to_latest`, so
`current_version` was never snapped even when detectable.

**Decision.** Mirror ADR-0013 for the edit path:

1. **Snap on edit.** `updateUpdatePackage` now calls
   `check_skill_package_versions` twice — phase 1 detect, phase 2 snap
   via `sync_current_to_latest=True`. The package shows **Up to Date**
   immediately after saving.

2. **Block on undetectable latest.** If `latest_version` is empty
   after phase-1 detection, the controller returns a structured
   JSON error and does **not** overwrite the record. The QML dialog
   shows an inline error and keeps the user's input.

3. **Preserve internal state.** `is_updating`, `just_finished`, and
   `last_updated` are read from the existing record before validation
   and re-applied after `model_validate` (which defaults them).

4. **JSON return.** The `@Slot` signature changes from
   `(int, dict)` to `(int, dict, result=str)`. `PackageEditDialog.qml`
   parses the return and shows inline errors on failure.

5. **Extend snap to git sources.** The `_sync_current_to_latest_if_applicable`
   helper now snaps for **all** source types (including git) when
   `current_version` is empty and `latest_version` is available. The
   previous `source_type != "git"` exclusion was too conservative —
   git sources whose local clone path was not detected (e.g. user
   entered the install path instead of the clone path) showed
   `unknown → vX.Y.Z` after edit. The condition is now:
   `latest AND !current AND !current_version_command`.

**Consequences.** Consistent behavior between add and edit across all
source types. The `_sync_current_to_latest_if_applicable` helper is
now used by three code paths (post-update, add, edit) with zero
duplication. Existing tests updated to handle the two-phase mock
pattern.

---

## ADR-0001 — Disable QML disk cache

**Status:** Accepted

**Context.** PySide6 6.11.1 serves stale bytecode from the QML disk
cache after source changes, producing "works on my machine" bugs.

**Decision.** Set `QML_DISABLE_DISK_CACHE=1` permanently. Application
guard in `src/skill_manager/__main__.py::_disable_qml_disk_cache` wipes
the stale directory when source mtimes advance.

**Consequences.** +200 ms recompile on first run after a QML edit. No
more stale-cache false positives.

---

## ADR-0002 — `AppController` dual registration

**Status:** Accepted

**Context.** QML uses `import App 1.0 { AppController }` *and* the
unqualified identifier `appController.*` in JS-embedded bindings.

**Decision.** Register the controller twice on every engine creation:

```python
qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
engine.rootContext().setContextProperty("appController", controller)
```

Order matters: singleton *before* engine.

**Consequences.** Diagnostics must use the same dual registration. A
private URI is required for any test-only mock.

---

## ADR-0003 — Qt 6.11.1 strict `data` list property

**Status:** Accepted

**Context.** `QQmlListProperty<QObject>` rejects any child whose type
is not declared in the parent's QML type info. Affected types include
`Timer`, `QtObject`, `NumberAnimation`, `MultiEffect`,
`RectangularGlow`, `InnerShadow`, `QGfxSourceProxy`.

**Decision.** No QObject-derived children of any `QQuickItem`. Use
`Behavior`/`Transition`/`PropertyAnimation` for animation. Consume
`Qt5Compat.GraphicalEffects` directly; never subclass.

**Consequences.** `tests/test_qml_comprehensive_diagnostic.py` guards
against regressions.

---

## ADR-0004 — QML diagnostic uses `QQmlApplicationEngine`

**Status:** Accepted

**Context.** `QQmlEngine` is stricter than `QQmlApplicationEngine` and
produces false-positive `data` errors. Registering a mock at the real
`App` URI collides with the conftest's session registration.

**Decision.** The diagnostic test uses `QQmlApplicationEngine` and
receives the conftest's real `AppController` via the
`app_controller` fixture. It does **not** call
`qmlRegisterSingletonInstance` against `App`.

**Consequences.** Tests run under the same QML engine semantics as
production. False positives eliminated.

---

## ADR-0005 — Python tests use `QApplication`

**Status:** Accepted

**Context.** `QQuickStyle` does not instantiate correctly under
`QGuiApplication` + `offscreen` platform.

**Decision.** The conftest `qapp_cls` fixture returns `QApplication`.
`setup_qml_style` calls `QQuickStyle.setStyle("Basic")` *before* the
QApplication is instantiated.

**Consequences.** +150 ms per session. All QML-loading tests inherit a
working style.

---

## ADR-0006 — Opt-in release tags

**Status:** Superseded by ADR-0009

**Decision.** Versions bump only on commits containing exactly one of
`[patch]`, `[minor]`, `[major]`, `[dev]`.

---

## ADR-0007 — Release-please with Conventional Commits

**Status:** Superseded by ADR-0009

**Decision.** Adopt release-please with Conventional Commits.

---

## ADR-0008 — Windows-only distribution

**Status:** Accepted

**Context.** Source uses Windows-only APIs (`ctypes.windll`,
`subprocess.CREATE_NO_WINDOW`, `os.startfile`). macOS / Linux CI cannot
verify the build.

**Decision.** Strip `sys.platform` / `os.name` guards. Ship only
Windows `.exe` installer and portable ZIP. CI runs on
`windows-latest` × Python 3.12 + 3.13.

**Consequences.** Source code has no cross-platform branches. macOS
and Linux portable ZIPs are not produced.

---

## ADR-0009 — python-semantic-release with opt-in tokens

**Status:** Accepted

**Context.** Release-please (ADR-0007) produced too many Release PRs.
The team prefers the opt-in approach of ADR-0006 but using a
maintained tool.

**Decision.** Use `python-semantic-release` v10.5.3 with a custom
opt-in commit parser (`src/skill_manager/commit_parser_optin.py`).
Tokens: `[patch]`, `[minor]`, `[major]`, `[dev]`. TUF publishing is
automated in CI.

**Consequences.** Clean `main` history. `CHANGELOG.md` is
auto-generated. TUF signing keys live in GitHub secrets.

---

## ADR-0010 — Drop TUF, use GitHub Releases API

**Status:** Accepted

**Context.** TUF produced a 320 MB tar.gz that exceeded GitHub Pages'
100 MB file limit. Git LFS returns pointer files; URL routing and
`tufup.Client` subclassing were rejected as over-engineered.

**Decision.** Drop TUF. Replace `AppUpdateController` with a single
`httpx` call to `GET /repos/.../releases/latest`. Show a banner when
the latest tag is greater than the running version.

**Consequences.** Users download updates manually. `gh-pages` branch
deleted. `TUF_KEY_*` secrets deleted. ADR-0008 unchanged.

---

## ADR-0011 — Selection refresh invariant

**Status:** Accepted

**Context.** `selectedSkill` is a passive dict snapshot set when the user
clicks a skill. When any mutation calls `addOrUpdateSkills` (command
create/update, screenshot capture, discovery scan), the model rows are
updated but the snapshot is not refreshed. QML only re-binds when
`selectedSkillChanged` fires, so the inspector shows stale data until
the app restarts. Three independent code sites missed this contract.

**Decision.** Every controller site that calls `addOrUpdateSkills` (or
`setSkills`) after a mutation MUST call
`OpsController._refresh_selected_skill(local_path)` and, for renames,
pass the new path via `rename_path`. The helper replaces
`_selected_skill` with a fresh dict from the model row and emits
`selectedSkillChanged` when the path matches the selected skill.

Affected call sites:
- `OpsController.createCustomCommand` (after `_merge_discovered_skills`)
- `OpsController.updateCustomCommandFull` (after `_merge_discovered_skills`)
- `ScreenshotController` (after post-capture `addOrUpdateSkills`)
- `DiscoveryController` (after incremental `addOrUpdateSkills`)

**Consequences.** Inspector always reflects the latest state. The
invariant is documented in `docs/API.md` § 5 and guarded by diagnostic
logging (`CATEGORY_SELECTION_REFRESHED`). Future mutation sites that
forget the helper are greppable and flagged in code review.

---

## ADR-0012 — Window state integrity

**Status:** Accepted

**Context.** The window's `x`, `y`, `width`, `height` are persisted via
QML `onXChanged`/`onYChanged` handlers in `Main.qml`. When
`hideWindowInstantly()` (screenshot auto-hide) sets `x = -32000`,
`y = -32000`, `opacity = 0`, those values are saved to disk if the app
is closed or crashes before `restoreWindowState()` runs. On next cold
boot, the window opens at (-32000, -32000) — off-screen — and appears
minimized/missing.

Additionally, `Main.qml:24` sets `visible: false` to prevent QML load
flicker, but `Component.onCompleted` did not explicitly re-show the
window, relying on `app.py:root.show()` called asynchronously.

**Decision.** Three-part fix:

1. **Guard flag.** Add `property bool _isHidingForScreenshot: false` to
   `Main.qml`. Set it `true` in `hideWindowInstantly()`, reset `false`
   in `restoreWindowState()`. The `onXChanged`/`onYChanged`/`onWidthChanged`/`onHeightChanged`
   handlers skip persistence when the guard is true.

2. **Explicit startup show.** `Component.onCompleted` now calls
   `window.visible = true`, `window.showNormal()`, `window.raise()`,
   `window.requestActivate()` to guarantee the window is visible and
   focused after QML loads.

3. **Diagnostic logging.** `onVisibilityChanged` handler emits
   `CATEGORY_WINDOW_STATE` to the diagnostic ring buffer, logging
   visibility state, position, and opacity on every change.

4. **Recovery script.** `scripts/recover_settings.py` detects and
   resets off-screen coordinates (x/y = -32000), zero opacity, and
   tiny dimensions (< 400) in the saved UI state.

5. **Screen geometry clamping.** After QML loads, `app.py` queries
   `QGuiApplication.primaryScreen().availableGeometry()` and clamps
   each root window's position so it is at least partially visible
   on the current primary monitor. This prevents windows saved on a
   disconnected multi-monitor setup from being permanently off-screen.

6. **Watchdog timer.** A 5-second `QTimer.singleShot` checks window
   visibility and forces `show()` + `raise_()` if the window is still
   not visible.

**Consequences.** Window always appears on the primary monitor, even
if saved coordinates were from a different monitor configuration.
Off-screen positions from cancelled screenshots are never persisted.
Diagnostic logging catches any future window state anomalies.
