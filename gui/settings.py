"""GUI Settings – load/save user preferences."""
import json, os, platform

def _user_data_dir() -> str:
    """Return %APPDATA%\\StudyTimer (Windows) or ~/.studytimer (Linux/macOS).
    Created on first access."""
    if platform.system() == 'Windows':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~')
        return os.path.join(base, '.studytimer')
    d = os.path.join(base, 'StudyTimer')
    os.makedirs(d, exist_ok=True)
    return d

_SETTINGS_FILE = os.path.join(_user_data_dir(), 'settings.json')


def _load_settings() -> dict:
    defaults = {
        'darkMode': True,
        'alwaysOnTop': False,
        'soundEnabled': True,
        'minimizeToTray': True,
        'language': 'vi',
        'autoStart': True,
        'autoAdvance': True,
        'smartBreakSkip': True,
    }
    if os.path.exists(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def _save_settings(s: dict):
    with open(_SETTINGS_FILE, 'w') as f:
        json.dump(s, f, indent=2)


