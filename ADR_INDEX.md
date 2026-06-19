# Architecture Decision Records

> All ADRs for SkillManager. This index is the **single source of truth** —
> when an architectural decision changes, update the relevant entry here
> and link the new ADR. Do not scatter ADR files across `docs/`; they
> live inline in this document.

| # | Title | Status | Date |
|---|-------|--------|------|
| [ADR-0001](#adr-0001-disable-qml-disk-cache) | Disable QML disk cache | Accepted | 2025 |
| [ADR-0002](#adr-0002-appcontroller-dual-registration) | `AppController` dual-registration (singleton + context property) | Accepted | 2025 |
| [ADR-0003](#adr-0003-qt-6111-strict-data-list-property) | Qt 6.11.1 strict `data` list-property — child QObject constraints | Accepted | 2025 |
| [ADR-0004](#adr-0004-qml-diagnostic-via-qqmlapplicationengine) | QML diagnostic test uses `QQmlApplicationEngine` + real `AppController` | Accepted | 2025 |
| [ADR-0005](#adr-0005-python-tests-use-qapplication) | Python tests use `QApplication`, not `QGuiApplication` | Accepted | 2025 |
| [ADR-0006](#adr-0006-opt-in-release-tags) | Opt-in release tags `[patch]` / `[minor]` / `[major]` / `[dev]` | Superseded | 2025 |
| [ADR-0007](#adr-0007-release-please-conventional-commits) | Release-please with Conventional Commits | Superseded | 2026 |
| [ADR-0008](#adr-0008-windows-only-distribution) | Windows-Only Distribution | Accepted | 2026 |
| [ADR-0009](#adr-0009-python-semantic-release-with-opt-in-tokens) | python-semantic-release with opt-in tokens | Accepted | 2026 |

---

## ADR-0001: Disable QML disk cache

**Status:** Accepted

**Context:** PySide6 6.11.1 serves stale bytecode from the QML disk cache
(`%APPDATA%/QtProject/qmlcache` on Windows, `~/.cache/QtProject/qmlcache` on
Linux) after source files change. Symptoms: QML edits have no visible
effect, "works on my machine" bugs, flaky CI runs.

**Decision:** Set `QML_DISABLE_DISK_CACHE=1` in the user environment
permanently. Implement an application-level guard
(`src/skill_manager/__main__.py::_disable_qml_disk_cache`) that sets the
matching `QML_DISABLE_DISK_CACHE` Qt environment variable and additionally
wipes the stale cache directory when source mtimes advance.

**Consequences:**
- Slight startup cost on first run after a QML edit (~200 ms recompile).
- No more stale-cache false-positives in CI or in the field.
- The cache directory is the only place we touch on disk to invalidate.

---

## ADR-0002: `AppController` dual-registration

**Status:** Accepted

**Context:** QML files in this project use `import App 1.0 { AppController }`
at the top, which requires the controller to be registered as a QML
singleton. However, several JavaScript-embedded bindings in QML reach
properties directly via the unqualified identifier `appController.*`. That
identifier is only available when a context property is set on the
engine's root context.

**Decision:** Register the controller twice on every engine creation:

```python
qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
engine.rootContext().setContextProperty("appController", controller)
```

The order matters: register the singleton *before* creating the engine,
otherwise PySide6 6.11.1 falls back to strict-validating every child
type of every type that subclasses a Qt5Compat effect (cascading into
hundreds of false-positive "Cannot assign object of type QGfxSourceProxy
to list property 'data'" errors).

**Consequences:**
- Diagnostics must use the same dual-registration or they will see
  different errors than production.
- A private URI (e.g. `DiagnosticMock`) must be used for any test-only
  registration, otherwise the process-wide registration collides and
  invalidates every subsequent QML load.

---

## ADR-0003: Qt 6.11.1 strict `data` list-property — child QObject constraints

**Status:** Accepted

**Context:** Qt 6.11.1's `QQmlListProperty<QObject>` rejects any child
QObject added to a visual item's `data` list whose type is not declared
in the parent's QML type information. Affected types include `Timer`,
`QtObject`, `WheelHandler`, `NumberAnimation`, `MultiEffect`,
`RectangularGlow`, `InnerShadow`, `QGfxSourceProxy`. The error reads
`Cannot assign object of type "X" to list property "data"; expected
"QObject"`.

`QQmlApplicationEngine` swallows the error and the affected control
silently renders empty. `QQmlComponent` (used in diagnostics and most
testing harnesses) surfaces the error.

**Decision:**
- Do not place QObject-derived children of any `QQuickItem` in this
  project. Where a Timer, animation, or handler is required, embed it
  inline in the visual item *or* use a QML-native equivalent (e.g.
  `Behavior on opacity` instead of a polling `Timer`).
- Where a Qt5Compat effect (`ColorOverlay`, `DropShadow`) is needed,
  consume it directly via `import Qt5Compat.GraphicalEffects` — do not
  subclass it. Subclassing forces a re-validation that fails.
- The custom `ColorOverlay.qml`, `DropShadow.qml` etc. in
  `SkillManagerComponents/` are thin property aliases or MultiEffect
  adapters, never subclasses of the Qt5Compat effect.

**Consequences:**
- The QML components in this project must not use QObject children.
- Custom `Timer`-based behaviours must be replaced with declarative
  `Behavior`/`Transition`/`PropertyAnimation` declarations.
- The `tests/test_qml_comprehensive_diagnostic.py` test (ADR-0004)
  guards against regressions by loading every QML file and asserting no
  `data` errors.

---

## ADR-0004: QML diagnostic test uses `QQmlApplicationEngine` + real `AppController`

**Status:** Accepted

**Context:** A previous version of the diagnostic test used
`QQmlEngine` + `qmlRegisterSingletonInstance(_Mock, "App", 1, 0, ...)`.
This differed from the real app in two ways and produced false-positive
errors:
1. `QQmlEngine` is stricter about child QObject types than
   `QQmlApplicationEngine` — the strict `data` check (ADR-0003) fires.
2. Registering a mock at the real `App` URI collides with the conftest's
   session-scoped registration of the real `AppController`, which causes
   every subsequent QML load in the process to fail.

**Decision:** The diagnostic test in
`tests/test_qml_comprehensive_diagnostic.py`:
- Uses `QQmlApplicationEngine`, matching production.
- Receives the conftest's session-scoped real `AppController` via the
  `app_controller` fixture and binds it via `setContextProperty`.
- Does **not** call `qmlRegisterSingletonInstance` against `App` — that
  URI is already taken by the conftest.

**Consequences:**
- Tests run under the same QML engine semantics as production.
- False-positive `data` errors are eliminated.
- A regression in production is guaranteed to also fail the diagnostic.

---

## ADR-0005: Python tests use `QApplication`, not `QGuiApplication`

**Status:** Accepted

**Context:** Several test paths load `QQuickStyle`-aware QML controls
(dialogs, native folder pickers). `QGuiApplication` does not instantiate
`QQuickStyle` correctly under headless `offscreen` platform, and
`QQuickStyle::setStyle()` returns silently — leading to "no controls
rendered" failures in CI.

**Decision:** The conftest `qapp_cls` fixture returns `QApplication`.
The `setup_qml_style` session fixture calls `QQuickStyle.setStyle("Basic")`
*before* the QApplication is instantiated, as Qt requires.

**Consequences:**
- A real `QApplication` is instantiated once per test session.
- All tests that load QML inherit a working style.
- Test runtime increases by ~150 ms per session (acceptable).

---

## ADR-0006: Opt-in release tags

**Status:** Superseded by ADR-0009

**Context:** A conventional commit-based release strategy produces too
many unintended version bumps on `main` and clutters the changelog.

**Decision:** Versions are only bumped when a commit message on
`develop` / `main` contains exactly one of the trigger tokens
`[patch]`, `[minor]`, `[major]`, or `[dev]`. See `docs/VERSIONING.md`
for the full ruleset and `conductor/` for the track lifecycle.

**Consequences:**
- A clean `main` history is preserved.
- Tracks under `conductor/tracks/` are the canonical way to group
  related commits for a single release.
- `CHANGELOG.md` is generated, never hand-edited.

---

## ADR-0007: Release-please with Conventional Commits

**Status:** Superseded by ADR-0009

**Context:** `python-semantic-release` is unmaintained (last release 2024).
The opt-in tag system (ADR-0006) required manual `[patch]`/`[minor]`/`[major]`
tokens in commit messages, which was error-prone and inconsistent with
industry standards.

**Decision:** Migrate to [release-please](https://github.com/googleapis/release-please-action)
with [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` → minor bump
- `fix:` / `perf:` → patch bump
- `feat!:` / `BREAKING CHANGE:` → major bump
- `docs:`, `test:`, `chore:`, `ci:` → no bump

Release-please automatically opens/updates a Release PR. Merging it
creates a git tag + GitHub Release. CI builds Windows artifacts and attaches
them. TUF publishing remains manual per-project policy.

**Consequences:**
- No more manual release trigger tokens in commit messages.
- `CHANGELOG.md` is auto-generated by release-please.
- Version is tracked in both `pyproject.toml` and `.release-please-manifest.json`.
- `__init__.py` is updated via `extra-files` in release-please config.
- Branch protection: `ci-gate` is the required status check.

---

## ADR-0008: Windows-Only Distribution

**Status:** Accepted
**Date:** 2026

**Context:** CI tests failed on macOS/Linux because source code contains Windows-specific APIs (`ctypes.windll`, `subprocess.CREATE_NO_WINDOW`, `os.startfile`, Win32 shell integration) with `sys.platform`/`os.name` guards that return no-ops on non-Windows. The app cannot be verified on macOS/Linux — only Windows is available for testing.

**Decision:** Remove all `sys.platform`/`os.name` conditional branches from source code. Strip macOS/Linux from CI workflows (`_test-python.yml`, `_build-pyinstaller.yml`). Ship only Windows `.exe` installer and portable ZIP.

**Consequences:**
- CI runs on `windows-latest` × Python 3.12 + 3.13 only.
- Source code has no cross-platform branches — Windows APIs are called directly.
- Two non-Windows tests deleted from `test_win32_utils.py`.
- macOS/Linux portable ZIP no longer attached to GitHub Releases.
- `docs/CI_CD.md`, `docs/RELEASING.md`, `docs/DEVELOPMENT.md`, `docs/ARCHITECTURE.md`, `docs/ENVIRONMENT.md`, `DESIGN.md`, `README.md` updated to reflect Windows-only scope.

---

## ADR-0009: python-semantic-release with opt-in tokens

**Status:** Accepted
**Date:** 2026

**Context:** Release-please (ADR-0007) opened Release PRs for every conventional commit, creating noise and requiring manual PR merges. The team preferred the original opt-in approach (ADR-0006) where only commits with explicit `[patch]`/`[minor]`/`[major]`/`[dev]` tokens trigger releases, but the original implementation used a custom version calculator that was unmaintained.

**Decision:** Migrate back to [python-semantic-release](https://python-semantic-release.readthedocs.io/) v10.5.3 with a custom opt-in commit parser (`src/skill_manager/commit_parser_optin.py`):

- `[patch]` → patch bump (`x.y.z` → `x.y.(z+1)`)
- `[minor]` → minor bump (`x.y.z` → `x.(y+1).0`)
- `[major]` → major bump (`x.y.z` → `(x+1).0.0`)
- `[dev]` → pre-release (`x.y.z-dev.N`)

Commits without a token are ignored by the release system. The `[dev]` token is handled by CI detecting it in the latest commit and passing `--as-prerelease` to semantic-release. TUF publishing is fully automated in the release workflow.

**Consequences:**
- Clean `main` history — no accidental version bumps.
- `CHANGELOG.md` is auto-generated by python-semantic-release.
- Version is tracked in `pyproject.toml:project.version` and `src/skill_manager/__init__.py:__version__`.
- Branch protection: `ci-gate` is the required status check.
- Release-please config files (`.github/release-please-config.json`, `.github/.release-please-manifest.json`) deleted.
- TUF signing keys are stored as GitHub secrets and written to files during CI.
