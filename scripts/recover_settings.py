"""Recover user settings from legacy config and fix corrupted app-data config.

Merges valid settings from both configs, replacing test temp paths
with the user's real project path.
"""

import json
import shutil
from pathlib import Path

APP_DATA_CONFIG = Path.home() / "AppData" / "Local" / "SkillManager" / "config.json"
LEGACY_CONFIG = Path.cwd() / "data" / "config.json"
BACKUP_SUFFIX = ".backupBeforeRecovery"


def recover():
    print("=" * 60)
    print("SkillManager Settings Recovery")
    print("=" * 60)

    # Read both configs
    app_data = {}
    if APP_DATA_CONFIG.exists():
        app_data = json.loads(APP_DATA_CONFIG.read_text(encoding="utf-8"))
        print(f"\n[APP-DATA] Read from: {APP_DATA_CONFIG}")
        print(f"  sources: {app_data.get('sources', [])}")
        print(f"  projects: {app_data.get('projects', [])}")

    legacy = {}
    if LEGACY_CONFIG.exists():
        legacy = json.loads(LEGACY_CONFIG.read_text(encoding="utf-8"))
        print(f"\n[LEGACY] Read from: {LEGACY_CONFIG}")
        print(f"  targets: {legacy.get('targets', [])}")
        print(f"  skills count: {len(legacy.get('skills', []))}")

    # Find the real project path from legacy targets
    real_targets = legacy.get("targets", [])
    real_project = None
    for t in real_targets:
        if Path(t).exists():
            real_project = t
            break

    if not real_project:
        print("\n[ERROR] No valid project path found in legacy config!")
        return False

    print(f"\n[RECOVERY] Real project path: {real_project}")

    # Build recovered config
    recovered = dict(app_data) if app_data else {}

    # Fix sources and projects — use real project path
    recovered["sources"] = [real_project]
    recovered["projects"] = [real_project]

    # Migrate legacy 'targets' to 'projects' if not already done
    if "targets" in recovered and "projects" not in recovered:
        recovered["projects"] = recovered.pop("targets")

    # Preserve legacy skills (package management data)
    if legacy.get("skills"):
        recovered["skills"] = legacy["skills"]
        print(f"  Migrated {len(legacy['skills'])} package configs")

    # Preserve valid settings from legacy that might be more recent
    for key in ["client_format", "default_client", "show_archived",
                "category_filter", "collection_filter", "show_commands",
                "show_starred", "is_package_only", "is_source_only"]:
        if key in legacy and key not in recovered:
            recovered[key] = legacy[key]

    # Preserve UI state from legacy if it has better values
    if "ui_state" in legacy:
        legacy_ui = legacy["ui_state"]
        recovered_ui = recovered.get("ui_state", {})
        # Use legacy UI state if it has window positions (user's actual layout)
        if legacy_ui.get("window_x") and legacy_ui["window_x"] != recovered_ui.get("window_x"):
            recovered["ui_state"] = legacy_ui
            print("  Restored UI state from legacy config")

    # Fix corrupted UI state: off-screen coordinates from hideWindowInstantly
    ui_state = recovered.get("ui_state", {})
    fixed_corrupted = False
    offscreen_sentinel = -32000

    if ui_state.get("window_x") == offscreen_sentinel:
        print(f"  [FIX] Detected off-screen window_x={offscreen_sentinel}, resetting to 100")
        ui_state["window_x"] = 100
        fixed_corrupted = True
    if ui_state.get("window_y") == offscreen_sentinel:
        print(f"  [FIX] Detected off-screen window_y={offscreen_sentinel}, resetting to 100")
        ui_state["window_y"] = 100
        fixed_corrupted = True
    # Clamp coordinates beyond a reasonable single-monitor width (2560px)
    max_x = 2560
    max_y = 1440
    if ui_state.get("window_x", 0) > max_x:
        print(f"  [FIX] Detected off-screen window_x={ui_state['window_x']}, resetting to 100")
        ui_state["window_x"] = 100
        fixed_corrupted = True
    if ui_state.get("window_y", 0) > max_y:
        print(f"  [FIX] Detected off-screen window_y={ui_state['window_y']}, resetting to 100")
        ui_state["window_y"] = 100
        fixed_corrupted = True
    if ui_state.get("window_opacity", 1.0) == 0.0:
        print("  [FIX] Detected zero window_opacity, resetting to 1.0")
        ui_state["window_opacity"] = 1.0
        fixed_corrupted = True
    if ui_state.get("window_width", 1200) < 400:
        print(f"  [FIX] Detected tiny window_width={ui_state.get('window_width')}, resetting to 1200")
        ui_state["window_width"] = 1200
        fixed_corrupted = True
    if ui_state.get("window_height", 800) < 400:
        print(f"  [FIX] Detected tiny window_height={ui_state.get('window_height')}, resetting to 800")
        ui_state["window_height"] = 800
        fixed_corrupted = True

    if fixed_corrupted:
        recovered["ui_state"] = ui_state
        print("  [FIX] Corrected corrupted window geometry in UI state")

    # Ensure required fields exist
    if "shortcuts" not in recovered:
        recovered["shortcuts"] = app_data.get("shortcuts", {})
    if "project_aliases" not in recovered:
        recovered["project_aliases"] = {}
    if "disabled_shortcuts" not in recovered:
        recovered["disabled_shortcuts"] = []

    # Backup current app-data config
    if APP_DATA_CONFIG.exists():
        backup_path = APP_DATA_CONFIG.with_suffix(BACKUP_SUFFIX)
        shutil.copy2(APP_DATA_CONFIG, backup_path)
        print(f"\n[BACKUP] Saved backup to: {backup_path}")

    # Write recovered config
    APP_DATA_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    APP_DATA_CONFIG.write_text(
        json.dumps(recovered, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n[WRITE] Recovered config to: {APP_DATA_CONFIG}")
    print(f"  sources: {recovered.get('sources', [])}")
    print(f"  projects: {recovered.get('projects', [])}")
    print(f"  skills: {len(recovered.get('skills', []))} packages")

    print("\n" + "=" * 60)
    print("RECOVERY COMPLETE")
    print("Restart SkillManager to apply changes.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    recover()
