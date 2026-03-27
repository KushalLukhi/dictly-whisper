"""
tray.py — System tray icon with colored status indicator.
"""

import threading
from PIL import Image, ImageDraw
import pystray

COLORS = {
    "idle":         (80,  80,  80),
    "recording":    (220, 50,  50),
    "transcribing": (100, 130, 240),
}


class TrayIcon:
    def __init__(self, on_show, on_quit):
        self._on_show = on_show
        self._on_quit = on_quit
        self._icon = None

    def start(self):
        menu = pystray.Menu(
            pystray.MenuItem("Show Dictly", self._show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )
        self._icon = pystray.Icon("Dictly", self._make_img("idle"), "Dictly — Idle", menu)
        threading.Thread(target=self._icon.run, daemon=True).start()

    def set_state(self, state: str):
        if self._icon:
            self._icon.icon = self._make_img(state)
            labels = {"idle": "Dictly — Idle", "recording": "Dictly — Recording…",
                      "transcribing": "Dictly — Transcribing…"}
            self._icon.title = labels.get(state, "Dictly")

    def stop(self):
        if self._icon:
            self._icon.stop()

    def _make_img(self, state: str) -> Image.Image:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = COLORS.get(state, COLORS["idle"]) + (255,)
        draw.ellipse([4, 4, 60, 60], fill=color)
        return img

    def _show(self, icon, item):
        self._on_show()

    def _quit(self, icon, item):
        self._on_quit()
