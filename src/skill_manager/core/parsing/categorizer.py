import re
from functools import lru_cache
from typing import Dict, List, Any
from .constants import CATEGORIES, MAIN_CATEGORIES_MAPPING

_CATEGORY_PATTERNS = None

def _get_category_patterns():
    global _CATEGORY_PATTERNS
    if _CATEGORY_PATTERNS is not None:
        return _CATEGORY_PATTERNS

    _CATEGORY_PATTERNS = {}
    for cat, keywords in CATEGORIES.items():
        plain = []
        special = []
        for kw in keywords:
            if re.search(r"[+#./\s-]", kw):
                special.append(kw)
            else:
                plain.append(kw)

        patterns = []
        if plain:
            patterns.append(
                re.compile(r"\b(?:" + "|".join(re.escape(kw.lower()) for kw in plain) + r")\b")
            )
        if special:
            patterns.extend([re.compile(re.escape(kw.lower())) for kw in special])

        if patterns:
            _CATEGORY_PATTERNS[cat] = patterns
    return _CATEGORY_PATTERNS

@lru_cache(maxsize=1024)
def get_main_category(sub_category: str) -> str:
    if not sub_category:
        return "⚙️ System & Workflow"
    for main_cat, sub_cats in MAIN_CATEGORIES_MAPPING.items():
        if sub_category in sub_cats:
            return main_cat
        if sub_category.lower() in [s.lower() for s in sub_cats]:
            return main_cat
    return "⚙️ System & Workflow"

def categorize_skill(name: str, description: str) -> Dict[str, str]:
    """Determines the best category for a skill based on its name and description."""
    text = f"{name} {name} {description}".lower()
    norm_text = " ".join(text.replace("-", " ").replace("_", " ").split())

    best_category = "Uncategorized"
    max_matches = 0

    patterns = _get_category_patterns()
    is_same = (text == norm_text)

    for category, cat_patterns in patterns.items():
        matches = 0
        for p in cat_patterns:
            matches += len(p.findall(text))
            if not is_same:
                matches += len(p.findall(norm_text))

        if matches > max_matches:
            max_matches = matches
            best_category = category

    return {"main_category": get_main_category(best_category), "sub_category": best_category}

def build_skill_search_text(skill_data: Dict[str, Any]) -> str:
    parts = [
        skill_data.get("name", ""),
        skill_data.get("description", ""),
        skill_data.get("folder_name", ""),
        skill_data.get("category", ""),
        skill_data.get("main_category", ""),
    ]
    metadata = skill_data.get("metadata") or {}
    for key in ("source", "risk", "category", "version", "date_added"):
        value = metadata.get(key)
        if value not in (None, ""):
            parts.append(str(value))
    return " ".join(" ".join(parts).split()).lower()
