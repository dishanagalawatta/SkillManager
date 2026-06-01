import re
from typing import Any

from .constants import CATEGORIES, MAIN_CATEGORIES_MAPPING

_CATEGORY_PATTERNS = None
_FAST_SUBSTRINGS = None

def _get_category_patterns():
    global _CATEGORY_PATTERNS, _FAST_SUBSTRINGS
    if _CATEGORY_PATTERNS is not None:
        return _CATEGORY_PATTERNS

    _CATEGORY_PATTERNS = {}
    _FAST_SUBSTRINGS = {}

    for cat, keywords in CATEGORIES.items():
        plain = []
        special = []
        all_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            all_keywords.append(kw_lower)
            if re.search(r"[+#./\s-]", kw_lower):
                special.append(kw_lower)
            else:
                plain.append(kw_lower)

        patterns = []
        if plain:
            patterns.append(
                re.compile(r"\b(?:" + "|".join(re.escape(k) for k in plain) + r")\b")
            )
        if special:
            patterns.extend([re.compile(re.escape(k)) for k in special])

        if patterns:
            _CATEGORY_PATTERNS[cat] = patterns
            _FAST_SUBSTRINGS[cat] = all_keywords

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

# Pre-compute static mappings for fast lookup
_CATEGORY_KEYS_LOWER = {known_cat.lower(): known_cat for known_cat in CATEGORIES}
_MAIN_CAT_ORDER = {k: i for i, k in enumerate(MAIN_CATEGORIES_MAPPING.keys())}
_SUB_CAT_ORDER = {k: i for i, k in enumerate(CATEGORIES.keys())}

def categorize_skill(name: str, description: str, metadata: dict | None = None) -> dict[str, str]:
    """Determines the best category for a skill using a weighted, hierarchical algorithm."""
    metadata = metadata or {}

    # 1. Exact metadata category match (highest priority)
    meta_cat = str(metadata.get("category", "")).strip()
    if meta_cat:
        meta_cat_lower = meta_cat.lower()
        if meta_cat_lower in _CATEGORY_KEYS_LOWER:
            known_cat = _CATEGORY_KEYS_LOWER[meta_cat_lower]
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
        # Fast path substring check before executing expensive regex
        substrings = _FAST_SUBSTRINGS[category]
        has_potential_match = False
        for kw in substrings:
            if kw in name_text or (not is_name_same and kw in norm_name_text) or kw in desc_text or (not is_desc_same and kw in norm_desc_text):
                has_potential_match = True
                break

        if not has_potential_match:
            continue

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

        if score > 0:
            sub_category_scores[category] = score

    # 2. Aggregate scores by Main Category
    main_category_scores = {}
    for sub, score in sub_category_scores.items():
        main_cat = get_main_category(sub)
        main_category_scores[main_cat] = main_category_scores.get(main_cat, 0) + score

    # 3. Find winning Main Category
    best_main_cat = "⚙️ System & Workflow"
    if main_category_scores:
        best_main_cat = sorted(
            main_category_scores.items(),
            key=lambda x: (-x[1], _MAIN_CAT_ORDER.get(x[0], 999))
        )[0][0]

    # 4. Find winning Sub Category within the best Main Category
    best_sub_cat = "Uncategorized"
    valid_subs = {sub: score for sub, score in sub_category_scores.items() if get_main_category(sub) == best_main_cat}

    if valid_subs:
        best_sub_cat = sorted(
            valid_subs.items(),
            key=lambda x: (-x[1], _SUB_CAT_ORDER.get(x[0], 999))
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
