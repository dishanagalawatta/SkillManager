# `AppController` — Public API Reference

> Auto-generated reference. The source of truth is the `@Q_PROPERTY`,
> `@Slot`, and `@Signal` decorators in `src/skill_manager/app.py` and
> `src/skill_manager/controllers/*.py`. This file summarises the
> surface for QML and Python consumers.

## Registration

`AppController` is registered as a QML singleton at module URI
`App 1.0` *and* bound as a context property `appController` (see
ADR-0002). QML reaches it either way:

```qml
import App 1.0
Item {
    Connections {
        target: AppController
        function onSelectedSkillChanged() { ... }
    }
}
```

```qml
// or, equivalently:
Item {
    Connections {
        target: appController
        function onSelectedSkillChanged() { ... }
    }
}
```

## Sub-Controllers

The full `AppController` surface is split into sub-controllers
(`src/skill_manager/controllers/`). Each sub-controller is exposed as
a property on `AppController` and is independently testable.

| Property | Type | File | Purpose |
|----------|------|------|---------|
| `config` | `ConfigController` | `controllers/config_controller.py` | Read/write `ConfigManager` state. |
| `discovery` | `DiscoveryController` | `controllers/discovery_controller.py` | Find skills across configured sources. |
| `updates` | `UpdateController` | `controllers/update_controller.py` | Schedule + run update operations. |
| `ops` | `OpsController` | `controllers/ops_controller.py` | Delete, archive, restore skills. |
| `ui` | `UiController` | `controllers/ui_controller.py` | View selection, modal state, status bar. |
| `screenshot` | `ScreenshotController` | `controllers/screenshot_controller.py` | Capture + annotate screenshots. |
| `image_inspector` | `ImageInspectorController` | `controllers/image_inspector_controller.py` | Skill image inspection. |
| `app_update` | `AppUpdateController` | `controllers/app_update_controller.py` | Self-update pipeline (TUF). |

## Q_PROPERTY Surface (selected)

| Property | Type | Read-only | Notes |
|----------|------|-----------|-------|
| `skillModel` | `QAbstractListModel` | yes | Source-of-truth skill list. Drives Library + QuickCopy views. |
| `quickCopyModel` | `QAbstractListModel` | yes | Filtered + sorted view for the QuickCopy screen. |
| `updateSources` | `QAbstractListModel` | yes | Configured update sources. |
| `projects` | `QAbstractListModel` | yes | Project aliases. |
| `isLoading` | `bool` | yes | True during initial load or background sync. |
| `statusMessage` | `str` | yes | Human-readable status text. |
| `selectedSkill` | `QVariant` | yes | Currently selected skill entity, or `None`. |
| `selectedSource` | `QVariant` | yes | Currently selected source. |

## Q_INVOKABLE / Slot Surface (selected)

| Method | Returns | Purpose |
|--------|---------|---------|
| `refreshSkills()` | `None` | Force a re-scan of all sources. |
| `loadInitialData()` | `None` | Idempotent. Called once at startup. |
| `selectSkill(skillId)` | `None` | Set `selectedSkill` and emit `selectedSkillChanged`. |
| `setStatus(message)` | `None` | Update `statusMessage` from Python. |
| `getProjectLabel(path)` | `str` | Resolve a project path to its human label. |
| `archiveSkill(skillId)` | `None` | Move a skill to the archive. |
| `deleteSkill(skillId)` | `None` | Permanent delete. Asks for confirmation via the UI. |
| `syncProject(projectId)` | `None` | Pull latest from the project's update source. |

## Signals (selected)

| Signal | Payload | Emitted when |
|--------|---------|--------------|
| `skillModelChanged()` | — | `skillModel` was rebuilt (rare; usually only initial load). |
| `selectedSkillChanged()` | — | `selectedSkill` property changed. |
| `statusMessageChanged()` | — | `statusMessage` property changed. |
| `isLoadingChanged()` | — | `isLoading` property changed. |
| `projectSynced(projectId, ok)` | `str, bool` | A background sync completed. |

## Lifecycles

- `AppController.__init__(skip_initial_load=False, config=None)` is
  called once in `__main__.py`. `skip_initial_load=True` is used by
  the conftest's session-scoped `app_controller` fixture.
- `AppController.on_quit()` is called from the `aboutToQuit` Qt
  signal — it flushes pending writes, cancels background tasks, and
  saves user preferences.
