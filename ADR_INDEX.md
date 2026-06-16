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
| [ADR-0006](#adr-0006-opt-in-release-tags) | Opt-in release tags `[patch]` / `[minor]` / `[major]` / `[dev]` | Accepted | 2025 |

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

**Status:** Accepted

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
