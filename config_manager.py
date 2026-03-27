"""
config_manager.py — Loads and saves all user settings to disk.
Settings live in ~/.dictly/settings.json
"""

import json
from pathlib import Path

APP_DIR = Path.home() / ".dictly"
SETTINGS_FILE = APP_DIR / "settings.json"

DEFAULTS = {
    "backend": "auto",
    "model": "small",
    "language": "en",
    "compute_type": "int8",
    "faster_whisper_device": "auto",
    "hotkey": ["ctrl", "shift"],
    "paste_method": "clipboard",
    "append_space": True,
    "prepend_space": False,
    "beam_size": 15,
    "vad_threshold": 0.3,
    "speech_pad_ms": 500,
    "launch_on_startup": False,
    "theme": "light",
}

LANGUAGE_OPTIONS = {
    "Auto-detect": None,
    "English": "en",
    "Hindi": "hi",
    "Gujarati": "gu",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Chinese": "zh",
    "Japanese": "ja",
    "Arabic": "ar",
    "Portuguese": "pt",
    "Russian": "ru",
}

MODEL_OPTIONS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]


def ensure_app_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    ensure_app_dir()
    if not SETTINGS_FILE.exists():
        save(DEFAULTS.copy())
        return DEFAULTS.copy()
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        for k, v in DEFAULTS.items():
            data.setdefault(k, v)
        if data.get("backend") == "whisper-cpp":
            data["backend"] = "auto"
        data.pop("whisper_cpp_binary", None)
        data.pop("whisper_cpp_model_dir", None)
        data.pop("whisper_cpp_no_gpu", None)
        return data
    except Exception:
        return DEFAULTS.copy()


def save(settings: dict):
    ensure_app_dir()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
