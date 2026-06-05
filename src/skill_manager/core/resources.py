import os
import sys
from pathlib import Path


def resource_path(relative_path: str, *, base_path: str | None = None) -> str:
    if base_path is None:
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
        else:
            # First try relative to the project root (where it lives in the repo)
            # src/skill_manager/core/resources.py -> Project Root is 3 levels up from core
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            if (project_root / relative_path).exists():
                base_path = str(project_root)
            else:
                base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def qml_components_dir(
    *,
    frozen: bool | None = None,
    meipass: str | None = None,
    package_file: str | None = None,
) -> Path:
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if meipass is None:
        meipass = getattr(sys, "_MEIPASS", "")
    if package_file is None:
        package_file = __file__

    if frozen:
        base = Path(meipass)
        internal = base / "_internal"
        if internal.exists():
            return internal / "skill_manager" / "SkillManagerComponents"
        return base / "skill_manager" / "SkillManagerComponents"

    return Path(package_file).resolve().parent / "SkillManagerComponents"


def logo_asset_for_client(fmt: str) -> str:
    fmt_lower = str(fmt or "").lower()
    if "antigravity" in fmt_lower:
        return "clients/antigravity.svg"
    if "gemini" in fmt_lower:
        return "clients/gemini-cli.svg"
    if "codex" in fmt_lower:
        return "clients/codex.svg"
    if "plain" in fmt_lower:
        return "clients/plaintext.svg"
    return "brand/logo.png"
