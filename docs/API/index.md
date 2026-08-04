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
| `sm_list_skills` | read | List skills in the library model |
| `sm_get_skill` | read | Full skill details (metadata, SKILL.md body, files) |
| `sm_search_skills` | read | Search skills by name/category/tags/content |
| `sm_sync_skills` | read | Re-scan skill source directories |
| `sm_list_sources` | read | List configured skill source directories |
| `sm_list_projects` | read | List configured target project directories |
| `sm_static_analyze` | read | Safe regex grep over the repo (respects `.gitignore`) |
| `sm_build` | read | Run `skill-manager-build` as a background job |
| `sm_lint` | read | Run `ruff check src tests`, return structured errors |
| `sm_run_tests` | read | Run the pytest suite as a background job |
| `sm_job_status` | read | Poll background test/build job status |
| `sm_get_health` | read | App & bridge health snapshot |
| `sm_get_diagnostics` | read | Diagnostic logger ring-buffer events |
| `sm_tail_events` | read | Tail recent telemetry / `capture_event` entries |
| `sm_profile` | read | Run discovery pipeline profiling |
| `sm_dump_state` | read | Export safe subset of controller state |
| `sm_inspect_controller` | read | Introspect sub-controller methods/signals |
| `sm_capture_errors` | read | Return error diagnostic buffer |
| `sm_screenshot` | read | Capture live GUI window as base64 PNG |
| `sm_navigate` | read | Navigate the GUI to a view/skill |
| `sm_get_window_info` | read | Return live GUI window geometry |
| `sm_mouse_move` | read* | Move system cursor (Windows; input-guarded) |
| `sm_mouse_click` | read* | Send mouse click (Windows; input-guarded) |
| `sm_type_text` | read* | Type text into focused window (Windows; input-guarded) |
| `sm_toggle_debug_overlay` | read | Toggle the QML debug overlay |
| `sm_create_skill` | **write** | Create a new skill from template |
| `sm_update_skill` | **write** | Update an existing skill's SKILL.md |
| `sm_deploy` | **write** | Deploy a skill to `<target>/.agents/skills/` |
| `sm_delete_skill` | **write** | Delete a skill (refuses AGENTS.md-excluded paths) |

> Write tools require `--mcp-allow-write` flag.
>
> `sm_mouse_*` and `sm_type_text` inject real input and are gated by
> `src/skill_manager/utils/input_guard.py` — they never run under
> pytest/CI (see AGENTS.md rule 7).

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
