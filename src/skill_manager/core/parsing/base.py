import re
from typing import Any

import yaml


def parse_frontmatter(frontmatter: str) -> dict[str, Any]:
    if not frontmatter:
        return {}

    try:
        parsed = yaml.safe_load(frontmatter)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # Fallback to manual parsing if YAML fails
    parsed = {}
    current_key = None
    current_lines = []

    def flush_multiline():
        nonlocal current_key, current_lines
        if current_key:
            parsed[current_key] = " ".join(line.strip() for line in current_lines).strip()
            current_key = None
            current_lines = []

    for line in frontmatter.splitlines():
        if re.match(r"^\s", line) and current_key:
            current_lines.append(line)
            continue

        flush_multiline()
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not key_match:
            continue

        key, value = key_match.groups()
        value = value.strip()
        if value in {">", "|", ">-", "|-"}:
            current_key = key
            current_lines = []
        else:
            parsed[key] = value.strip(" \"'")

    flush_multiline()
    return parsed

def normalize_description(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    elif not isinstance(value, str):
        value = str(value)
    return " ".join(value.split()).strip(" \"'")

def extract_markdown_description(content: str) -> str:
    body = re.sub(
        r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", "", content, count=1, flags=re.DOTALL
    )
    paragraphs = []
    current = []

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if line.startswith("#") or line.startswith("```") or line.startswith("---"):
            continue
        current.append(re.sub(r"[*_`]+", "", line))

    if current:
        paragraphs.append(" ".join(current))

    return normalize_description(paragraphs[0] if paragraphs else "")
