from skill_manager.core.categories import get_category_emoji


def test_get_category_emoji_exact():
    assert get_category_emoji("Testing") == "🧪"
    assert get_category_emoji("AI") == "🧠"
    assert get_category_emoji("DevOps") == "♾️"


def test_get_category_emoji_case_insensitive():
    assert get_category_emoji("testing") == "🧪"
    assert get_category_emoji("ai") == "🧠"
    assert get_category_emoji("DEVOPS") == "♾️"


def test_get_category_emoji_substring():
    assert get_category_emoji("Advanced Web Development") == "🌐"
    assert get_category_emoji("Mobile Dev") == "📱"
    assert get_category_emoji("Web Dev") == "🌐"


def test_get_category_emoji_special_characters():
    assert get_category_emoji("**Security**") == "🛡️"
    assert get_category_emoji("__Testing__") == "🧪"
    assert get_category_emoji("[Design]") == "🎨"


def test_get_category_emoji_fallback():
    assert get_category_emoji("") == "📁"
    assert get_category_emoji(None) == "📁"
    assert get_category_emoji("Unknown Area 123") == "📁"


def test_get_category_emoji_shorthands():
    assert get_category_emoji("Backend Dev") == "⚙️"
    assert get_category_emoji("Cloud Infra") == "☁️"
    assert get_category_emoji("Product Mgmt") == "📈"
