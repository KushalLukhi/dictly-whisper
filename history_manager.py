"""
history_manager.py — Saves and loads transcription history.
History lives in ~/.dictly/history.json (last 200 entries)
"""

import json
from datetime import datetime
from pathlib import Path
from config_manager import APP_DIR

HISTORY_FILE = APP_DIR / "history.json"
MAX_ENTRIES = 200


def _load_raw() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_raw(entries: list):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(entries[-MAX_ENTRIES:], f, indent=2, ensure_ascii=False)


def add(text: str, duration: float, language: str):
    entries = _load_raw()
    entries.append({
        "text": text,
        "timestamp": datetime.now().isoformat(),
        "duration": round(duration, 1),
        "language": language or "auto",
    })
    _save_raw(entries)


def get_all() -> list:
    return list(reversed(_load_raw()))


def clear():
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
