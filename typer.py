"""
typer.py — Pastes transcribed text into the active window.
"""

import time
import platform
import pyperclip
from pynput.keyboard import Key, Controller as KeyboardController

_keyboard = KeyboardController()
_OS = platform.system()


def output_text(text: str, settings: dict):
    if not text:
        return

    final = ""
    if settings.get("prepend_space"):
        final += " "
    final += text
    if settings.get("append_space", True):
        final += " "

    method = settings.get("paste_method", "clipboard")
    if method == "clipboard":
        _paste_via_clipboard(final)
    else:
        _type_characters(final)


def _paste_via_clipboard(text: str):
    try:
        old = pyperclip.paste()
    except Exception:
        old = ""

    pyperclip.copy(text)
    time.sleep(0.05)

    paste_key = Key.cmd if _OS == "Darwin" else Key.ctrl
    with _keyboard.pressed(paste_key):
        _keyboard.press("v")
        _keyboard.release("v")

    time.sleep(0.1)

    try:
        pyperclip.copy(old)
    except Exception:
        pass


def _type_characters(text: str):
    for char in text:
        _keyboard.type(char)
        time.sleep(0.01)
