# Public API Reference

> Authoritative surface for QML and Python consumers. The
> `@Q_PROPERTY`, `@Slot`, and `@Signal` decorators in
> `src/skill_manager/app.py` and `src/skill_manager/controllers/*.py`
> are the source of truth; this document is a derived view.

## 1. Registration

`AppController` is registered twice (see [`ADR_INDEX.md`](../ADR_INDEX.md)):

```python
qmlRegisterSingletonInstance(AppController, "App", 1, 0, "AppController", controller)
engine.rootContext().setContextProperty("appController", controller)
```

QML consumers reach it via `import App 1.0` *or* via the context
property `appController`:

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

## 2. Sub-Controllers

The full `AppController` surface is split into sub-controllers
(`src/skill_manager/controllers/`). Each sub-controller is exposed as
a property on `AppController` and is independently testable.

| Property | Type | Module | Purpose |
|----------|------|--------|---------|
| `config` | `ConfigController` | `controllers/config_controller.py` | Read / write `ConfigManager` state. |
| `discovery` | `DiscoveryController` | `controllers/discovery_controller.py` | Find skills across configured sources. |
| `updates` | `UpdateController` | `controllers/update_controller.py` | Schedule and run updates. |
| `ops` | `OpsController` | `controllers/ops_controller.py` | Delete, archive, restore. |
| `ui` | `UiController` | `controllers/ui_controller.py` | View selection, modal state. |
| `screenshot` | `ScreenshotController` | `controllers/screenshot_controller.py` | Capture + annotate. |
| `image_inspector` | `ImageInspectorController` | `controllers/image_inspector_controller.py` | Image inspection. |
| `app_update` | `AppUpdateController` | `controllers/app_update_controller.py` | Self-update pipeline. |

## 3. Q_PROPERTY Surface (selected)

| Property | Type | Read-only | Notes |
|----------|------|-----------|-------|
| `skillModel` | `QAbstractListModel` | yes | Source-of-truth skill list. Drives Library + QuickCopy views. |
| `quickCopyModel` | `QAbstractListModel` | yes | Filtered / sorted for Quick Copy. |
| `updateSources` | `QAbstractListModel` | yes | Configured update sources. |
| `projects` | `QAbstractListModel` | yes | Project aliases. |
| `isLoading` | `bool` | yes | True during initial load or sync. |
| `statusMessage` | `str` | yes | Human-readable status text. |
| `selectedSkill` | `QVariant` | yes | Currently selected skill entity, or `None`. |
| `selectedSource` | `QVariant` | yes | Currently selected source. |

## 4. Q_INVOKABLE / Slot Surface (selected)

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

**Side effect.** `updateCustomCommandFull` and `createCustomCommand` may
emit `selectedSkillChanged` as a side effect of refreshing the
`selectedSkill` snapshot after model mutation.

## 5. Signals (selected)

| Signal | Payload | Emitted when |
|--------|---------|--------------|
| `skillModelChanged()` | — | `skillModel` was rebuilt (rare; usually only initial load). |
| `selectedSkillChanged()` | — | `selectedSkill` property changed. |
| `statusMessageChanged()` | — | `statusMessage` property changed. |
| `isLoadingChanged()` | — | `isLoading` property changed. |
| `projectSynced(projectId, ok)` | `str, bool` | A background sync completed. |

**Invariant.** Any mutation that calls `addOrUpdateSkills` (or
`setSkills`) after changing a skill's data MUST call
`OpsController._refresh_selected_skill(local_path)` if the mutation may
affect the currently selected skill. See
[`ADR-0011`](../ADR_INDEX.md#adr-0011-selection-refresh-invariant).

## 6. Lifecycles

- `AppController.__init__(skip_initial_load=False, config=None)` is
  called once in `__main__.py`. `skip_initial_load=True` is used by
  the conftest's session-scoped `app_controller` fixture.
- `AppController.on_quit()` is called from the `aboutToQuit` Qt
  signal — it flushes pending writes, cancels background tasks, and
  saves user preferences.

## 7. Versioning

Public surface is **unstable within a minor version**. Breaking
changes require a `feat!:` commit (see [`ADR_INDEX.md`](../ADR_INDEX.md)).
Internal controllers may change without notice.

## 8. Cross-references

- ADRs: [`ADR_INDEX.md`](../ADR_INDEX.md)
- Environment: [`docs/ENVIRONMENT.md`](ENVIRONMENT.md)
- Design: [`DESIGN.md`](../DESIGN.md)
