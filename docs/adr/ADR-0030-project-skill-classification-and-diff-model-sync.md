# ADR-0030: Project Skill Classification & Differential Model Synchronization

## Status
**Accepted** | Date: 2026-08-20 | Owner: @DIKKA

## Context
When skills were copied from the Master Library into a project workspace via `copySelectedSkillsToProject()`, the newly copied skills occasionally appeared duplicated in the Library view. This issue exhibited specific characteristics:
1. The duplicate skill showed in the Library view immediately after copying.
2. Upon triggering a manual refresh or full discovery pass (`discover_all`), the duplicate disappeared.
3. The root cause lay in the fallback `is_package` heuristic inside `DiscoveryService._discover_single_skill_folder()`: when single-skill discovery was invoked without an explicit `is_package` parameter, it tested `resolved_proj.is_relative_to(s)` for all configured `sources`. If a project root (or a parent directory) was registered in `sources`, the skill located at `<project_root>/.agents/skills/<skill_name>` was erroneously classified as `is_package = True` with `project_label = "Master Library"`.
4. Furthermore, `addOrUpdateSkills` in `IngestMixin` used `_apply_filter(reset=False)` which only emitted `layoutChanged` without row mutation diffing, and unconditionally recomputed `project_label` for all skills (even package skills).

## Decision
1. **Strict `.agents/skills` Project Boundary Rule**:
   - Skills residing under `.agents/skills/` or `.agents/commands/` are by definition project-level artifacts (`is_package = False`).
   - `DiscoveryService._discover_single_skill_folder` explicitly enforces `is_package = False` whenever `.agents` appears in the skill or project path parts.
   - `discover_project` and `copySelectedSkillsToProject` explicitly pass `is_package = False` during targeted discovery.
2. **Package Label Invariance**:
   - In `addOrUpdateSkills`, `project_label` recomputation is strictly scoped to project skills (`not skill.is_package`). Package skills permanently retain `project_label = "Master Library"`.
3. **Differential Model Synchronization**:
   - Switched `addOrUpdateSkills` to use `_apply_filter_with_diff()` on non-empty models. This computes exact list differences using `difflib.SequenceMatcher` and emits proper Qt row mutation signals (`beginInsertRows`/`endInsertRows`, `beginRemoveRows`/`endRemoveRows`, `dataChanged`), preventing QML `ListView` delegate duplication and index drift.
4. **Discovery Service Configuration Alignment**:
   - `_build_discovery_service` incorporates `_update_packages` into `sources`, ensuring targeted single-scans utilize the identical package source list as background full discovery pipelines.

## Consequences

### Positive
- **No Duplicate Records**: Copying skills to projects will never cause them to appear in the Master Library view, even if the project path is also present in source package paths.
- **Accurate Project Labels**: Project skills always retain their canonical project label, while package skills are reliably labeled "Master Library".
- **Visual Stability**: Delegate creation and destruction in `ListView` are cleanly synchronized with Qt row signals, eliminating UI ghost items and delegate cache corruption.

### Negative / Trade-offs
- Targeted discovery strictly identifies `.agents` paths as project skills; any external tool structuring package skills inside a directory named `.agents` must explicitly supply `is_package = True`.
