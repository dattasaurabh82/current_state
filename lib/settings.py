import json
from pathlib import Path

_settings = None

def load_settings():
    """Load settings from settings.json. Caches result."""
    global _settings
    if _settings is None:
        settings_path = Path(__file__).parent.parent / "settings.json"
        with open(settings_path) as f:
            _settings = json.load(f)
    return _settings
