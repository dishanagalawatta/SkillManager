import logging
import os
from typing import Any

from .base import extract_markdown_description, normalize_description, split_frontmatter

logger = logging.getLogger(__name__)


def resolve_skill_file_path(path: str) -> str | None:
    """Resolve a local path (file or directory) to an actual readable markdown file path."""
    if not path:
        return None
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        for candidate_name in ("SKILL.md", "skill.md", "README.md"):
            cand = os.path.join(path, candidate_name)
            if os.path.isfile(cand):
                return cand
        try:
            for entry in os.listdir(path):
                if entry.endswith(".md"):
                    cand = os.path.join(path, entry)
                    if os.path.isfile(cand):
                        return cand
        except Exception:
            pass
    return None


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

        data["commands"] = []
    except Exception as e:
        logger.warning("Error parsing %s: %s", filepath, e)
    return data
