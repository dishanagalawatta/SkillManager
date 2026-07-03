from pathlib import Path
from skill_manager.core.discovery import get_discovery_cache

def test_cache():
    cache = get_discovery_cache()
    print("cache valid")
