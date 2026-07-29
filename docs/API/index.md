# Core API Documentation

> This is the landing page for SkillManager's internal API surface.
> For the full QML/Python controller reference, see [`docs/API.md`](../API.md).
> For the MCP tool reference (agent-facing), see [`docs/MCP_SERVER.md`](../MCP_SERVER.md).

---

## Quick Reference

### Controller APIs (QML/Python boundary)

| Controller | Exposed As | Primary Purpose |
|-----------|-----------|-----------------|
| `AppController` | `AppController` / `appController` | Root proxy; sub-controllers as properties |
| `ConfigController` | `AppController.config` | Read/write app and project configuration |
| `DiscoveryController` | `AppController.discovery` | Skill discovery, filtering, model reset |
| `OpsController` | `AppController.ops` | Copy, delete, archive skill operations |
| `UIController` | `AppController.ui` | View state, search, sidebar, modal management |
| `UpdateController` | `AppController.updates` | Skill source update scheduling |
| `AppUpdateController` | `AppController.app_update` | Self-update pipeline |
| `ScreenshotController` | `AppController.screenshot` | Screen capture and annotation |
| `ImageInspectorController` | `AppController.image_inspector` | Image analysis and color isolation |

### MCP Tool APIs (agent-facing)

| Tool | Mode | Description |
|------|------|-------------|
| `sm_list_skills` | read | List all skills with optional filters |
| `sm_get_skill` | read | Get full skill details by ID or path |
| `sm_search_skills` | read | Fuzzy-search skills by name/description |
| `sm_sync_skills` | read | Force a discovery rescan |
| `sm_analyze_skill` | read | Analyze skill quality and dependencies |
| `sm_monitor_discovery` | read | Stream discovery progress events |
| `sm_build_app` | read | Trigger a PyInstaller build |
| `sm_debug_skill` | read | Run diagnostic checks on a skill |
| `sm_get_diagnostics` | read | Retrieve structured app diagnostics |
| `sm_screenshot` | read | Capture the current app window |
| `sm_navigate` | read | Navigate to a view/skill in the UI |
| `sm_create_skill` | **write** | Create a new skill from template |
| `sm_update_skill` | **write** | Update an existing skill's content |
| `sm_deploy` | **write** | Deploy a skill to a target project |
| `sm_delete_skill` | **write** | Delete a skill by ID |

> Write tools require `--mcp-allow-write` flag.

---

## Common API Patterns

### Reading a skill from QML

```qml
import App 1.0

Connections {
    target: AppController
    function onSelectedSkillChanged() {
        const skill = AppController.selectedSkill
        console.log(skill.name, skill.description)
    }
}
```

### Triggering discovery from Python

```python
# Via controller (preferred — thread-safe)
app_controller.discovery.requestFullRescan()

# Listen for completion
app_controller.discovery.discoveryComplete.connect(on_complete)
```

### Calling MCP tools from an agent

```bash
# Read-only session
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"sm_list_skills","arguments":{"category":"debugging"}}}' \
  | uv run skill-manager --mcp
```

---

## Full References

- [**docs/API.md**](../API.md) — Complete `@Q_PROPERTY`, `@Slot`, `@Signal` surface with examples
- [**docs/MCP_SERVER.md**](../MCP_SERVER.md) — MCP server setup, client configs, all tool schemas
- [**DESIGN.md**](../../DESIGN.md) — Architectural patterns and controller design
- [**src/skill_manager/app.py**](../../src/skill_manager/app.py) — `AppController` source of truth
- [**src/skill_manager/controllers/**](../../src/skill_manager/controllers/) — Sub-controller implementations
- [**src/skill_manager/mcp/tools/**](../../src/skill_manager/mcp/tools/) — MCP tool implementations
