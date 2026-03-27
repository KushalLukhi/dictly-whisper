"""
dictation_overlay.py - Floating desktop waveform overlay.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import math
import tkinter as tk

import customtkinter as ctk
import numpy as np


class DictationOverlay(ctk.CTkToplevel):
    TRANSPARENT_BG = "#010203"
    PILL_BG = "#080808"
    WIDTH = 118
    HEIGHT = 34

    def __init__(self, parent, settings: dict):
        super().__init__(parent)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=self.TRANSPARENT_BG)

        try:
            self.attributes("-transparentcolor", self.TRANSPARENT_BG)
        except Exception:
            pass

        self._settings = dict(settings)
        self._state = "idle"
        self._audio_level = 0.0
        self._live_audio = False
        self._frame_index = 0
        self._after_id = None
        self._hide_after_id = None

        self._canvas = tk.Canvas(
            self,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg=self.TRANSPARENT_BG,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack()
        self._canvas.bind("<Button-1>", lambda _event: parent.show())
        self.bind("<Button-1>", lambda _event: parent.show())

        self._draw()

    def _exists(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    def destroy(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._hide_after_id:
            try:
                self.after_cancel(self._hide_after_id)
            except Exception:
                pass
            self._hide_after_id = None
        try:
            super().destroy()
        except tk.TclError:
            pass

    def _show_overlay(self):
        if not self._exists():
            return
        self.update_idletasks()
        left, top, right, bottom = self._get_work_area()
        x = max(left + 12, left + ((right - left - self.WIDTH) // 2))
        y = max(top + 12, bottom - self.HEIGHT - 2)
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")
        self.deiconify()

    def _hide_overlay(self):
        if not self._exists():
            return
        self.withdraw()

    def _get_work_area(self) -> tuple[int, int, int, int]:
        if hasattr(ctypes, "windll"):
            rect = wintypes.RECT()
            success = ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
            if success:
                return rect.left, rect.top, rect.right, rect.bottom
        return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

    def _schedule_draw(self):
        if not self._exists():
            return
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(40, self._tick)

    def _tick(self):
        if not self._exists():
            self._after_id = None
            return
        self._draw()
        self._audio_level *= 0.84
        if self._state in {"recording", "transcribing"}:
            self._frame_index += 1
            self._schedule_draw()
        else:
            self._after_id = None

    def _draw(self):
        if not self._exists():
            return
        canvas = self._canvas
        canvas.delete("all")
        self._draw_filled_outline(canvas, 2, 4, self.WIDTH - 2, self.HEIGHT - 4, 11, self.PILL_BG, "#f1f1f1")

        bars = self._build_bars()
        center_y = self.HEIGHT / 2
        start_x = 29
        gap = 7
        for index, value in enumerate(bars):
            x = start_x + index * gap
            extent = max(1.8, value * 6.6)
            canvas.create_line(
                x,
                center_y - extent,
                x,
                center_y + extent,
                fill="#f5f5f5",
                width=3,
                capstyle=tk.ROUND,
            )

    def _draw_filled_outline(self, canvas, x1, y1, x2, y2, radius, fill_color, outline_color):
        canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill_color, outline=fill_color)
        canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill_color, outline=fill_color)
        canvas.create_oval(x1, y1, x1 + radius * 2, y1 + radius * 2, fill=fill_color, outline=fill_color)
        canvas.create_oval(x2 - radius * 2, y1, x2, y1 + radius * 2, fill=fill_color, outline=fill_color)
        canvas.create_oval(x2 - radius * 2, y2 - radius * 2, x2, y2, fill=fill_color, outline=fill_color)
        canvas.create_oval(x1, y2 - radius * 2, x1 + radius * 2, y2, fill=fill_color, outline=fill_color)

        canvas.create_arc(x1, y1, x1 + radius * 2, y1 + radius * 2, start=90, extent=90, style=tk.ARC, outline=outline_color, width=1)
        canvas.create_arc(x2 - radius * 2, y1, x2, y1 + radius * 2, start=0, extent=90, style=tk.ARC, outline=outline_color, width=1)
        canvas.create_arc(x2 - radius * 2, y2 - radius * 2, x2, y2, start=270, extent=90, style=tk.ARC, outline=outline_color, width=1)
        canvas.create_arc(x1, y2 - radius * 2, x1 + radius * 2, y2, start=180, extent=90, style=tk.ARC, outline=outline_color, width=1)
        canvas.create_line(x1 + radius, y1, x2 - radius, y1, fill=outline_color, width=1)
        canvas.create_line(x2, y1 + radius, x2, y2 - radius, fill=outline_color, width=1)
        canvas.create_line(x1 + radius, y2, x2 - radius, y2, fill=outline_color, width=1)
        canvas.create_line(x1, y1 + radius, x1, y2 - radius, fill=outline_color, width=1)

    def _build_bars(self) -> list[float]:
        if self._state == "recording":
            base = max(self._audio_level, 0.18)
            bars = []
            phase = self._frame_index / 2.8
            for index in range(9):
                wave = (math.sin(phase + index * 0.62) + 1) / 2
                distance = abs(index - 4) / 4
                value = base * (0.65 + wave * 1.15) * (1.0 - distance * 0.18)
                bars.append(min(1.0, value))
            return bars

        pulse = 0.28 + ((math.sin(self._frame_index / 3.0) + 1) / 2) * 0.32
        return [pulse * scale for scale in (0.38, 0.52, 0.72, 0.9, 1.0, 0.9, 0.72, 0.52, 0.38)]

    def set_state(self, state: str):
        if not self._exists():
            return
        self._state = state

        if self._hide_after_id:
            self.after_cancel(self._hide_after_id)
            self._hide_after_id = None

        if state in {"recording", "transcribing"}:
            self._show_overlay()
            self._schedule_draw()
            return

        if state == "done":
            self._show_overlay()
            self._schedule_draw()
            self._hide_after_id = self.after(450, self._hide_overlay)
            return

        self._hide_overlay()

    def start_waveform(self):
        if not self._exists():
            return
        self._live_audio = True
        self._state = "recording"
        self._show_overlay()
        self._schedule_draw()

    def stop_waveform(self):
        if not self._exists():
            return
        self._live_audio = False
        self._audio_level = 0.0

    def push_audio(self, chunk):
        if not self._live_audio:
            return

        rms = float(np.sqrt(np.mean(chunk ** 2))) * 20
        self._audio_level = max(self._audio_level * 0.55, min(1.0, rms))

    def update_settings(self, settings: dict):
        if not self._exists():
            return
        self._settings = dict(settings)
        if self._state in {"recording", "transcribing"}:
            self._show_overlay()
