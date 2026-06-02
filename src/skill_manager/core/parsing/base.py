import re
from typing import Any

import frontmatter
import yaml
from markdown_it import MarkdownIt

_MARKDOWN = MarkdownIt("commonmark")


def normalize_description(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    elif not isinstance(value, str):
        value = str(value)
    return " ".join(value.split()).strip(" \"'")

def extract_markdown_description(content: str) -> str:
    body = split_frontmatter(content)[1]
    
    try:
        tokens = _MARKDOWN.parse(body)
    except Exception:
        return ""

    for index, token in enumerate(tokens):
        if token.type == "paragraph_open" and token.level == 0:
            inline = tokens[index + 1]
            if inline.type == "inline":
                text = inline.content.replace("*", "").replace("_", "").replace("`", "")
                return normalize_description(text)
    return ""


def split_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Return parsed metadata and body content using python-frontmatter."""
    if not content:
        return {}, ""

    try:
        post = frontmatter.loads(content)
        return dict(post.metadata) if post.metadata else {}, post.content.strip()
    except Exception:
        return {}, content.strip()


def first_heading(content: str) -> str:
    """Extract the first H1 text using markdown-it-py tokenization."""
    try:
        tokens = _MARKDOWN.parse(content or "")
    except Exception:
        return ""

    for index, token in enumerate(tokens[:-1]):
        if token.type == "heading_open" and token.tag == "h1":
            inline = tokens[index + 1]
            if inline.type == "inline":
                return normalize_description(inline.content)
    return ""
