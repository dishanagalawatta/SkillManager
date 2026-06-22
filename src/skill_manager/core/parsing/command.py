import re
from pathlib import Path
from typing import Any

from .base import extract_markdown_description, normalize_description, parse_frontmatter
from .categorizer import get_main_category


def parse_command_md(filepath: str) -> dict[str, Any] | None:
    data = {"name": "", "description": "", "raw_content": "", "body_content": "", "metadata": {}}
    try:
        stem = Path(filepath).stem

        # Skip common non-command files
        if stem.lower() in {
            "readme",
            "license",
            "changelog",
            "contributing",
            "todo",
            "package",
            "security",
            "skill",
        }:
            return None

        with open(filepath, encoding="utf-8-sig") as f:
            content = f.read()
            data["raw_content"] = content

        # Extract body content (without frontmatter)
        body = re.sub(
            r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", "", content, count=1, flags=re.DOTALL
        )
        data["body_content"] = body.strip()

        match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            metadata = parse_frontmatter(frontmatter)
            data["metadata"] = metadata
            data["name"] = str(metadata.get("name", "") or "").strip()
            data["client"] = metadata.get("client", "")
            data["category"] = metadata.get("category", "")
            data["description"] = normalize_description(metadata.get("description", ""))

        data["main_category"] = get_main_category(data.get("category", ""))

        # If no name in frontmatter, look for first H1 header
        if not data["name"]:
            h1_match = re.search(r"^#\s+(.*)$", content, re.MULTILINE)
            if h1_match:
                data["name"] = h1_match.group(1).strip()
            else:
                data["name"] = stem

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
        print(f"Error parsing command {filepath}: {e}")
        return None
    return data
