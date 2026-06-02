import logging
from pathlib import Path
from typing import Any

from .base import extract_markdown_description, normalize_description, split_frontmatter

logger = logging.getLogger(__name__)


def parse_skill_md(filepath: str) -> dict[str, Any]:
    data = {"name": "", "description": "", "raw_content": "", "body_content": "", "metadata": {}}
    try:
        with open(filepath, encoding="utf-8-sig") as f:
            content = f.read()
            data["raw_content"] = content

        metadata, body = split_frontmatter(content)
        data["body_content"] = body

        if metadata:
            data["metadata"] = metadata
            data["name"] = str(metadata.get("name", "") or "").strip()
            data["description"] = normalize_description(metadata.get("description", ""))
            data["is_bundle"] = metadata.get("type") == "bundle" or "bundle" in data["name"].lower()

        if not data["description"]:
            data["description"] = extract_markdown_description(content)

        # Look for commands (ONLY in commands/ subdir if SKILL.md exists)
        data["commands"] = []
        base_dir = Path(filepath).parent

        # Files in commands/ directory (trusted)
        commands_dir = base_dir / "commands"
        if commands_dir.is_dir():
            for md_file in commands_dir.glob("*.md"):
                if md_file.stem.lower() not in {"readme", "license", "changelog"}:
                    data["commands"].append(str(md_file.absolute()))
    except Exception as e:
        logger.warning("Error parsing %s: %s", filepath, e)
    return data
