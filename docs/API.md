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
| `confirmCommandSkillsCarry(projectPath, cmdJson, skillsJson)` | `None` | Carry confirmed skills alongside commands to a project. |
| `copyCommandsToProjectWithCarry(projectPath, cmdJson)` | `None` | Copy commands; prompt if skills are missing. |
| `createCustomCommand(n: str, b: str, project_labels: QStringList, cat: str)` | `str` | Create a custom command deployed to all listed projects. |
| `updateCustomCommandFull(lp: str, n: str, b: str, cat: str, project_labels: QStringList, on_conflict: str)` | `str` | Update a custom command; rewrites every project copy. |
| `commandProjectsForPath(local_path: str) → QStringList` | `QStringList` | Returns project labels that hold a copy of the command. |
| `deleteCustomCommand(command_name: str, project_labels: QStringList)` | `None` | Removes command from all listed projects. |

**Side effect.** `updateCustomCommandFull` and `createCustomCommand` may
emit `selectedSkillChanged` as a side effect of refreshing the
`selectedSkill` snapshot after model mutation.

**Package add/edit returns.** `addSkillPackage` and
`updateUpdatePackage` now return `result=str` (JSON) instead of
`void`. QML callers MUST parse the return value; on failure the
controller returns `{"ok": false, "error": "..."}` and does not
append/overwrite the record. See
[`ADR-0013`](../ADR_INDEX.md#adr-0013-package-add-snap-to-latest-policy)
and
[`ADR-0014`](../ADR_INDEX.md#adr-0014-package-edit-snap-to-latest-policy).

## 5. Signals (selected)

| Signal | Payload | Emitted when |
|--------|---------|--------------|
| `skillModelChanged()` | — | `skillModel` was rebuilt (rare; usually only initial load). |
| `selectedSkillChanged()` | — | `selectedSkill` property changed. |
| `statusMessageChanged()` | — | `statusMessage` property changed. |
| `isLoadingChanged()` | — | `isLoading` property changed. |
| `projectSynced(projectId, ok)` | `str, bool` | A background sync completed. |
| `commandSkillsCarryPrompt(cmdJson, projPath, skillsJson)` | `str, str, str` | Commands copied; skills missing in target. Show carry dialog. |

**Invariant.** Any mutation that calls `addOrUpdateSkills` (or
`setSkills`) after changing a skill's data MUST call
`OpsController._refresh_selected_skill(local_path)` if the mutation may
affect the currently selected skill. See
[`ADR-0011`](../ADR_INDEX.md#adr-0011-selection-refresh-invariant).

## 6. Python Public Modules

### `core/config.py`

```python
class ConfigManager:
    """JSON-based configuration manager."""
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def save(self) -> None: ...

class ScopedConfigManager(ConfigManager):
    """Per-project config isolation."""
    def __init__(self, project_path: str): ...
```

### `core/discovery.py`

```python
class SkillDiscovery:
    """Find and parse skills across configured sources."""
    def scan(self) -> list[SkillEntity]: ...
    def scan_incremental(self) -> list[SkillEntity]: ...
```

### `core/copier.py`

```python
def copy_skill_files(skill: SkillEntity, target: str) -> CopyResult: ...
def merge_skill(skill: SkillEntity, target: str) -> MergeResult: ...
```

### `core/analytics.py`

```python
def capture_event(event_name: str, properties: dict = None) -> None: ...
def capture_exception(error: Exception) -> None: ...
def shutdown() -> None: ...
```

### `core/schemas.py`

```python
class SkillEntity(BaseModel):
    """Pydantic model for a parsed skill."""
    name: str
    path: str
    description: str
    category: str
    commands: list[CommandEntity]
    ...
```

## 7. CLI Entry Point

```bash
# Development
uv run skill-manager
uv run python -m skill_manager.__main__

# Production (via installer)
skill-manager.exe
```

The `__main__.py` module:
1. Loads `.env` via `python-dotenv`
2. Initializes `QGuiApplication`
3. Registers `AppController` and sub-controllers
4. Loads `Main.qml`
5. Enters the Qt event loop

## 8. Environment Contract

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTHOG_PROJECT_TOKEN` | No | (empty) | PostHog analytics token |
| `POSTHOG_HOST` | No | `https://us.i.posthog.com` | PostHog instance URL |
| `SENTRY_DSN` | No | (empty) | Sentry error tracking DSN |
| `SKILL_MANAGER_LOG_LEVEL` | No | `INFO` | Logging level |
| `SKILL_MANAGER_TESTING` | No | (unset) | Enable test mode |
| `SKILL_MANAGER_DATA_DIR` | No | (default) | Override data directory |

See [`environments/README.md`](../environments/README.md) for tier-specific values.

## 9. Telemetry Surface

### PostHog Events

| Event | Properties | When |
|-------|------------|------|
| `app_opened` | — | App starts successfully |
| `skill_copied_to_project` | `skills_copied`, `skills_merged`, `skills_failed`, `skills_count` | Skills copied to target |
| `skills_deleted` | `count` | User deletes skills |
| `skill_package_added` | `source_type` | New skill source added |
| `skill_package_removed` | `source_type` | Skill source removed |
| `skill_package_updated` | `source_type`, `success` | Source update completes |
| `project_target_added` | `target_count` | New project target added |
| `skill_archived` | `action` (`archived`/`restored`) | Skill archived or restored |
| `skill_launched` | — | User opens skill folder in explorer |
| `skill_searched` | — | User applies category filter |

See [`docs/PRODUCT_TELEMETRY.md`](PRODUCT_TELEMETRY.md) for full details.

## 10. Error Model

| Error Type | Handler | User Visibility |
|------------|---------|-----------------|
| `ConfigError` | Log + fallback defaults | Silent |
| `DiscoveryError` | Log + diagnostic event | Status bar message |
| `CopyError` | Log + emit signal | Dialog (retry/skip) |
| `UpdateError` | Log + diagnostic event | Status bar message |
| `QML Error` | `console.error` in QML | Developer tools only |

All Python exceptions are caught at the controller level and converted to diagnostic events (see `core/diagnostics.py`).

## 11. Lifecycles

- `AppController.__init__(skip_initial_load=False, config=None)` is
  called once in `__main__.py`. `skip_initial_load=True` is used by
  the conftest's session-scoped `app_controller` fixture.
- `AppController.on_quit()` is called from the `aboutToQuit` Qt
  signal — it flushes pending writes, cancels background tasks, and
  saves user preferences.

## 12. Versioning

Public surface is **unstable within a minor version**. Breaking
changes require a `feat!:` commit (see [`ADR_INDEX.md`](../ADR_INDEX.md)).
Internal controllers may change without notice.

## 13. Cross-references

- ADRs: [`ADR_INDEX.md`](../ADR_INDEX.md)
- Architecture: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- Design: [`DESIGN.md`](../DESIGN.md)
- Environment: [`ENVIRONMENT.md`](ENVIRONMENT.md)
- Environments tiers: [`environments/README.md`](../environments/README.md)
