"""
startup_manager.py — Register/unregister Dictly to run at OS startup.
Supports Windows (Registry), macOS (LaunchAgent), Linux (autostart .desktop)
"""

import os
import sys
import platform
from pathlib import Path

APP_NAME = "Dictly"
_OS = platform.system()


def _get_executable() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'


# ── Windows ────────────────────────────────────────────────────────────────

def _win_enable():
    import winreg
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE,
    )
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_executable())
    winreg.CloseKey(key)


def _win_disable():
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass


def _win_is_enabled() -> bool:
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False


# ── macOS ──────────────────────────────────────────────────────────────────

def _mac_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / "com.dictly.app.plist"


def _mac_enable():
    exe = _get_executable()
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.dictly.app</string>
  <key>ProgramArguments</key>
  <array><string>{exe}</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
</dict>
</plist>"""
    p = _mac_plist_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(plist)


def _mac_disable():
    p = _mac_plist_path()
    if p.exists():
        p.unlink()


def _mac_is_enabled() -> bool:
    return _mac_plist_path().exists()


# ── Linux ──────────────────────────────────────────────────────────────────

def _linux_desktop_path() -> Path:
    return Path.home() / ".config" / "autostart" / "dictly.desktop"


def _linux_enable():
    exe = _get_executable()
    desktop = f"""[Desktop Entry]
Type=Application
Name=Dictly
Exec={exe}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Dictly — Local AI Dictation
"""
    p = _linux_desktop_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(desktop)


def _linux_disable():
    p = _linux_desktop_path()
    if p.exists():
        p.unlink()


def _linux_is_enabled() -> bool:
    return _linux_desktop_path().exists()


# ── Public API ─────────────────────────────────────────────────────────────

def enable():
    if _OS == "Windows":
        _win_enable()
    elif _OS == "Darwin":
        _mac_enable()
    else:
        _linux_enable()


def disable():
    if _OS == "Windows":
        _win_disable()
    elif _OS == "Darwin":
        _mac_disable()
    else:
        _linux_disable()


def is_enabled() -> bool:
    if _OS == "Windows":
        return _win_is_enabled()
    elif _OS == "Darwin":
        return _mac_is_enabled()
    else:
        return _linux_is_enabled()


def set_enabled(enabled: bool):
    if enabled:
        enable()
    else:
        disable()
