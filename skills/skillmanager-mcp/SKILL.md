---
name: skillmanager-mcp
description: Use this skill when an agent needs to connect to or drive the SkillManager desktop app via its MCP server (uv run skill-manager --mcp). Covers client setup (.mcp.json), full tool catalogue (skills, build, analyze, monitor, debug, write), write-mode gating, and response envelopes for any coding agent.
risk: medium
source: project
---

# SkillManager MCP Server

SkillManager ships a native Python MCP server (stdio, `mcp` SDK) that lets AI coding agents search, read, create, update, deploy, delete, and analyze agent skills — without shelling out or opening a GUI.

## When to Use

- An agent needs to search, read, inspect, or manage skills across projects and source directories.
- An agent needs to build, lint, test, or analyze the SkillManager codebase.
- An agent needs to inspect running app state (health, diagnostics, loaded skills/projects).
- An agent needs to create, update, deploy, or delete skills safely (with write mode enabled).

## Launch / Connect

The server runs headless (own mutex, never collides with a running GUI instance). An agent connects by launching the server executable. Point the client at the repo launcher script (it invokes the project venv directly, so `uv` does not need to be on the client's PATH):

```json
{
  "mcpServers": {
    "skillmanager": {
      "command": "/path/to/skill-manager/scripts/mcp_launcher.sh",
      "args": ["--mcp"]
    },
    "skillmanager-write": {
      "command": "/path/to/skill-manager/scripts/mcp_launcher.sh",
      "args": ["--mcp", "--mcp-allow-write"]
    }
  }
}
```

- `skillmanager` — Read-only tools (`sm_list_skills`, `sm_get_skill`, `sm_search_skills`, `sm_sync_skills`, build/analyze/monitor/debug).
- `skillmanager-write` — Same plus mutating tools (`sm_create_skill`, `sm_update_skill`, `sm_delete_skill`, `sm_deploy`).

## Tools Reference

All tools use the prefix `sm_`. Every response is wrapped in a uniform JSON envelope:
`{"ok": bool, "tool": str, "data"?: ..., "error"?: str}`.

### Skill Management (Read-Only)
| Tool | Args | Description |
|------|------|-------------|
| `sm_list_skills` | `{include_commands?, project_label?}` | Enumerate all discovered skills in library model. |
| `sm_get_skill` | `{skill_id}` | Retrieve full skill details (metadata, SKILL.md body, file listing). |
| `sm_search_skills` | `{query, category?, project_label?, include_commands?, limit?}` | Search skills by keyword in name, category, description, tags, or content. |
| `sm_sync_skills` | `{force_full_scan?}` | Re-scan skill source directories and target projects into library model. |
| `sm_list_sources` | `{}` | List configured skill source directories. |
| `sm_list_projects` | `{}` | List configured target project directories. |

### Skill Management (Mutating — `--mcp-allow-write` required)
| Tool | Args | Description |
|------|------|-------------|
| `sm_create_skill` | `{name, content, source_path?, description?, category?}` | Create a new skill directory with SKILL.md. |
| `sm_update_skill` | `{skill_id, content?, description?, category?}` | Update an existing skill's SKILL.md file or metadata. |
| `sm_deploy` | `{skill_id, target}` | Deploy a skill to a target project directory (`<target>/.agents/skills/`). |
| `sm_delete_skill` | `{skill_id}` | Delete a skill folder/file (refuses protected AGENTS.md paths). |

### Build & Dev Tools
| Tool | Args | Description |
|------|------|-------------|
| `sm_lint` | `{path?, fix?}` | Run `uv run ruff check [--fix] <path>`. Returns lint pass status, stdout, stderr. |
| `sm_run_tests` | `{target?, parallel?}` | Run pytest suite. Returns `job_id` for async polling. |
| `sm_build` | `{target?}` | Run application builder (`uv run skill-manager-build`). Returns `job_id`. |
| `sm_job_status` | `{job_id}` | Poll background job status/results (`running`, `done`, `error`). |

### Analysis & Debugging
| Tool | Args | Description |
|------|------|-------------|
| `sm_static_analyze` | `{pattern, path?}` | Regex grep over codebase (gitignore-aware). |
| `sm_get_health` | `{}` | Application & bridge health status snapshot. |
| `sm_get_diagnostics` | `{limit?}` | Read recent diagnostic ring-buffer entries. |
| `sm_dump_state` | `{}` | Export safe subset of controller & model configuration state. |
| `sm_screenshot` | `{navigate?, save?}` | Capture live GUI app window screenshot as base64 PNG. |

## Safety & Exclusion Rules

1. **Write tools require `--mcp-allow-write`.** Without this flag, mutating tools return `{"ok": false, "error": "write mode disabled..."}`.
2. **AGENTS.md Exclusions.** Mutating tools strictly refuse paths containing `TODO.md`, `.agents/skills`, or `.agents/commands`.
3. **No Unsafe Fallbacks.** Unresolvable skill IDs return `ok=false` with descriptive error messages instead of corrupting paths.

## Quick Reference

- Read-only: `uv run skill-manager --mcp`
- Write mode: `uv run skill-manager --mcp --mcp-allow-write`
- Full documentation & setup guides: `docs/MCP_SERVER.md`
