import re
from pathlib import Path
from typing import Dict, Any
from .base import parse_frontmatter, normalize_description, extract_markdown_description

def parse_skill_md(filepath: str) -> Dict[str, Any]:
    data = {"name": "", "description": "", "raw_content": "", "body_content": "", "metadata": {}}
    try:
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
        print(f"Error parsing {filepath}: {e}")
    return data
