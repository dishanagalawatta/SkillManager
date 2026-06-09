import re
from typing import Any

from .constants import CATEGORIES, MAIN_CATEGORIES_MAPPING

_CATEGORY_PATTERNS = None
_COMBINED_REGEX = None
_KW_TO_CAT = {}

_MAIN_CATEGORY_REVERSE_MAP = {
    sub.lower(): main for main, sub_cats in MAIN_CATEGORIES_MAPPING.items() for sub in sub_cats
}


def get_main_category(sub_category: str) -> str:
    if not sub_category:
        return "⚙️ System & Workflow"
    return _MAIN_CATEGORY_REVERSE_MAP.get(sub_category.lower(), "⚙️ System & Workflow")


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


def categorize_skill(name: str, description: str, metadata: dict | None = None) -> dict[str, str]:
    """Determines the best category for a skill using rapidfuzz."""
    try:
        from rapidfuzz import fuzz, process
    except ImportError:
        # Fallback if rapidfuzz isn't available somehow
        fuzz = None

    metadata = metadata or {}

    # 1. Exact metadata category match (highest priority)
    meta_cat = str(metadata.get("category", "")).strip()
    if meta_cat:
        for known_cat in CATEGORIES:
            if known_cat.lower() == meta_cat.lower():
                return {"main_category": get_main_category(known_cat), "sub_category": known_cat}

    name_text = name.lower().replace("-", " ").replace("_", " ")
    desc_text = description.lower().replace("-", " ").replace("_", " ")

    sub_category_scores = {}

    if fuzz is not None:
        for category, keywords in CATEGORIES.items():
            if not keywords:
                continue

            # Check name match
            name_match = process.extractOne(
                name_text, keywords, scorer=fuzz.token_set_ratio, score_cutoff=85
            )
            name_score = name_match[1] if name_match else 0
            cat_name_score = fuzz.token_set_ratio(category.lower(), name_text)
            if cat_name_score >= 85:
                name_score = max(name_score, cat_name_score + 5)

            # Check desc match
            desc_match = process.extractOne(
                desc_text, keywords, scorer=fuzz.token_set_ratio, score_cutoff=85
            )
            desc_score = desc_match[1] if desc_match else 0
            cat_desc_score = fuzz.token_set_ratio(category.lower(), desc_text)
            if cat_desc_score >= 85:
                desc_score = max(desc_score, cat_desc_score)

            # Weight name 10x
            score = (name_score * 10) + desc_score
            sub_category_scores[category] = score
    else:
        # Basic fallback using string containment
        for category, keywords in CATEGORIES.items():
            score = 0
            for kw in keywords:
                if kw.lower() in name_text:
                    score += 10
                if kw.lower() in desc_text:
                    score += 1
            if category.lower() in name_text:
                score += 10
            if category.lower() in desc_text:
                score += 1
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
            main_category_scores.items(), key=lambda x: (-x[1], main_cat_order.get(x[0], 999))
        )[0][0]

    # 4. Find winning Sub Category within the best Main Category
    best_sub_cat = "Uncategorized"
    valid_subs = {
        sub: score
        for sub, score in sub_category_scores.items()
        if get_main_category(sub) == best_main_cat and score > 0
    }

    if valid_subs:
        sub_cat_order = {k: i for i, k in enumerate(CATEGORIES.keys())}
        best_sub_cat = sorted(
            valid_subs.items(), key=lambda x: (-x[1], sub_cat_order.get(x[0], 999))
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
