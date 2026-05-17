import re
from functools import lru_cache

CATEGORY_EMOJI_MAP = {
    "AI": "🧠",
    "Agents": "🤖",
    "Architecture": "🏛️",
    "Backend Development": "⚙️",
    "Backend Dev": "⚙️",
    "Cloud Infrastructure": "☁️",
    "Cloud Infra": "☁️",
    "DevOps": "♾️",
    "Developer Tools": "🧰",
    "Programming Languages": "⌨️",
    "Programming": "⌨️",
    "Web Development": "🌐",
    "Web Dev": "🌐",
    "Mobile Development": "📱",
    "Mobile Dev": "📱",
    "Desktop Development": "🖥️",
    "Desktop Dev": "🖥️",
    "Embedded Systems": "📟",
    "Embedded": "📟",
    "Web3": "⛓️",
    "Game Development": "🎮",
    "Game Dev": "🎮",
    "Shell Scripting": "🐚",
    "Build Systems": "🏗️",
    "Background Jobs": "⏱️",
    "Business Strategy": "♟️",
    "Marketing": "📢",
    "Product Management": "📈",
    "Product Mgmt": "📈",
    "Finance": "💰",
    "Legal": "⚖️",
    "Compliance": "📜",
    "Logistics": "📦",
    "Procurement": "🛒",
    "Billing": "💳",
    "Payments": "💸",
    "ERP": "🏢",
    "Human Resources": "👥",
    "Inventory": "🏬",
    "Manufacturing": "🏭",
    "Careers": "💼",
    "Security": "🛡️",
    "Testing": "🧪",
    "Debugging": "🐞",
    "Performance": "🏎️",
    "Observability": "🔭",
    "Code Quality": "🧹",
    "Linting": "✨",
    "Quality Control": "💎",
    "Migration": "🛫",
    "Analytics": "📊",
    "Data": "🧊",
    "Databases": "🗄️",
    "Content": "📝",
    "Documentation": "📚",
    "Knowledge Management": "💡",
    "Knowledge Mgmt": "💡",
    "Diagrams": "🗺️",
    "Design": "🎨",
    "Communications": "📧",
    "Social Media": "💬",
    "Localization": "🌍",
    "Psychology": "🧩",
    "Health": "🩺",
    "Mental Health": "🧘",
    "Fitness": "🏋️",
    "Sleep": "🌙",
    "Rehabilitation": "🩹",
    "Traditional Medicine": "🌿",
    "Occupational Health": "👷",
    "Oral Health": "🦷",
    "Sexual Health": "🏥",
    "Travel Health": "✈️",
    "Core Workflow": "🔄",
    "Uncategorized": "📁",
    "Essentials": "⭐",
    "Collections": "📦",
    "Custom Commands": "⚡",
}

# Pre-compute a lowercase version of the map to avoid dynamic lowercasing during iterations
_MAP_LOWER = {k.lower(): v for k, v in CATEGORY_EMOJI_MAP.items()}

# Cache the resulting emoji lookup for a category name up to maxsize (e.g. 1024 unique category names).
# This prevents repeated expensive string cleaning and matching.
@lru_cache(maxsize=1024)
def get_category_emoji(category_name: str) -> str:
    if not category_name:
        return "📁"

    clean_name = re.sub(r"[*_]", "", category_name).strip()
    if clean_name in CATEGORY_EMOJI_MAP:
        return CATEGORY_EMOJI_MAP[clean_name]

    cat_lower = clean_name.lower()
    if cat_lower in _MAP_LOWER:
        return _MAP_LOWER[cat_lower]

    for name_lower, emoji in _MAP_LOWER.items():
        if name_lower in cat_lower or cat_lower in name_lower:
            return emoji

    return "📁"
