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
