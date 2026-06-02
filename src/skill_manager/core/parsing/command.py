import logging
from pathlib import Path
from typing import Any

from .base import (
    extract_markdown_description,
    first_heading,
    normalize_description,
    split_frontmatter,
)
from .categorizer import get_main_category

logger = logging.getLogger(__name__)


def parse_command_md(filepath: str) -> dict[str, Any] | None:
    data = {"name": "", "description": "", "raw_content": "", "body_content": "", "metadata": {}}
    try:
        stem = Path(filepath).stem

        # Skip common non-command files
        if stem.lower() in {
            "readme", "license", "changelog", "contributing",
            "todo", "package", "security", "skill",
        }:
            return None

        with open(filepath, encoding="utf-8-sig") as f:
            content = f.read()
            data["raw_content"] = content

        metadata, body = split_frontmatter(content)
        data["body_content"] = body

        if metadata:
            data["metadata"] = metadata
            data["name"] = str(metadata.get("name", "") or "").strip()
            data["client"] = metadata.get("client", "")
            data["category"] = metadata.get("category", "")
            data["description"] = normalize_description(metadata.get("description", ""))

        data["main_category"] = get_main_category(data.get("category", ""))

        # If no name in frontmatter, look for first H1 header
        if not data["name"]:
            data["name"] = first_heading(content) or stem

        if not data["description"]:
            data["description"] = extract_markdown_description(content)

        # If name or filename contains client info, extract it
        if not data.get("client"):
            if "." in stem:
                parts = stem.split(".")
                data["client"] = parts[-1]
            else:
                try:
                    from skill_manager.core.quick_copy import CLIENT_FORMATS
                    if stem in CLIENT_FORMATS:
                        data["client"] = stem
                except ImportError:
                    pass

    except Exception as e:
        logger.warning("Error parsing command %s: %s", filepath, e)
        return None
    return data
