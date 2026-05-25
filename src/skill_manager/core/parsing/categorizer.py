import re
from typing import Any

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

_MAIN_CATEGORY_REVERSE_MAP = {
    sub.lower(): main
    for main, sub_cats in MAIN_CATEGORIES_MAPPING.items()
    for sub in sub_cats
}


def get_main_category(sub_category: str) -> str:
    if not sub_category:
        return "⚙️ System & Workflow"
    return _MAIN_CATEGORY_REVERSE_MAP.get(sub_category.lower(), "⚙️ System & Workflow")

def categorize_skill(name: str, description: str, metadata: dict | None = None) -> dict[str, str]:
    """Determines the best category for a skill using a weighted, hierarchical algorithm."""
    metadata = metadata or {}

    # 1. Exact metadata category match (highest priority)
    meta_cat = str(metadata.get("category", "")).strip()
    if meta_cat:
        for known_cat in CATEGORIES:
            if known_cat.lower() == meta_cat.lower():
                return {"main_category": get_main_category(known_cat), "sub_category": known_cat}

    name_text = name.lower()
    norm_name_text = " ".join(name_text.replace("-", " ").replace("_", " ").split())
    desc_text = description.lower()
    norm_desc_text = " ".join(desc_text.replace("-", " ").replace("_", " ").split())

    is_name_same = (name_text == norm_name_text)
    is_desc_same = (desc_text == norm_desc_text)

    patterns = _get_category_patterns()
    sub_category_scores = {}

    for category, cat_patterns in patterns.items():
        score = 0
        for p in cat_patterns:
            name_matches = sum(len(m) for m in p.findall(name_text))
            if not is_name_same:
                name_matches += sum(len(m) for m in p.findall(norm_name_text))
            score += name_matches * 10

            desc_matches = sum(len(m) for m in p.findall(desc_text))
            if not is_desc_same:
                desc_matches += sum(len(m) for m in p.findall(norm_desc_text))
            score += desc_matches

        sub_category_scores[category] = score

    # 2. Aggregate scores by Main Category
    main_category_scores = {}
    for sub, score in sub_category_scores.items():
        if score > 0:
            main_cat = get_main_category(sub)
            main_category_scores[main_cat] = main_category_scores.get(main_cat, 0) + score

    # 3. Find winning Main Category
    best_main_cat = "⚙️ System & Workflow"
    if main_category_scores:
        main_cat_order = {k: i for i, k in enumerate(MAIN_CATEGORIES_MAPPING.keys())}
        best_main_cat = sorted(
            main_category_scores.items(),
            key=lambda x: (-x[1], main_cat_order.get(x[0], 999))
        )[0][0]

    # 4. Find winning Sub Category within the best Main Category
    best_sub_cat = "Uncategorized"
    valid_subs = {sub: score for sub, score in sub_category_scores.items() if get_main_category(sub) == best_main_cat and score > 0}

    if valid_subs:
        sub_cat_order = {k: i for i, k in enumerate(CATEGORIES.keys())}
        best_sub_cat = sorted(
            valid_subs.items(),
            key=lambda x: (-x[1], sub_cat_order.get(x[0], 999))
        )[0][0]

    return {"main_category": best_main_cat, "sub_category": best_sub_cat}

def build_skill_search_text(skill_data: dict[str, Any]) -> str:
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
