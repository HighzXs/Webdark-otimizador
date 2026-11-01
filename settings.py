"""Configurações do usuário (guardadas em %APPDATA%\\FaxinaVarzea\\settings.json)."""
import json
import os

DEFAULTS = {"background": False, "scan_minutes": 60, "last_notice": 0.0, "tray_tip_shown": False}


def _path():
    base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "FaxinaVarzea")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "preferences.json")   # settings.json é do vigia de temperatura (thermal.py)


def load():
    data = dict(DEFAULTS)
    try:
        with open(_path(), encoding="utf-8") as f:
            data.update(json.load(f))
    except (OSError, ValueError):
        pass
    return data


def save(data):
    try:
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass
