"""
waveform_widget.py - Live animated waveform for CustomTkinter layouts.
"""

from collections import deque
import math
import tkinter as tk

import customtkinter as ctk
import numpy as np


class WaveformWidget(ctk.CTkFrame):
    DEFAULT_BG = "#1a1a2e"
    DEFAULT_IDLE = "#3a3a3a"
    DEFAULT_ACTIVE = "#a78bfa"
    DEFAULT_PEAK = "#f472b6"

    def __init__(
        self,
        parent,
        width=220,
        height=56,
        bar_count=40,
        bar_width=4,
        bar_gap=2,
        bg_color=None,
        idle_color=None,
        active_color=None,
        peak_color=None,
        corner_radius=8,
        **kwargs,
    ):
        self._bg_color = bg_color or self.DEFAULT_BG
        super().__init__(
            parent,
            width=width,
            height=height,
            fg_color=self._bg_color,
            corner_radius=corner_radius,
            **kwargs,
        )
        self._width = width
        self._height = height
        self._bar_count = bar_count
        self._bar_width = bar_width
        self._bar_gap = bar_gap
        self._idle_color = idle_color or self.DEFAULT_IDLE
        self._active_color = active_color or self.DEFAULT_ACTIVE
        self._peak_color = peak_color or self.DEFAULT_PEAK
        self._active = False
        self._frame_index = 0
        self._bars = deque([0.0] * self._bar_count, maxlen=self._bar_count)
        self._bars_smooth = [0.0] * self._bar_count
        self._after_id = None

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=self._bg_color,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.after(50, self._draw_idle)

    def start(self):
        self._active = True
        self._schedule_draw()

    def stop(self):
        self._active = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._frame_index = 0
        self._bars = deque([0.0] * self._bar_count, maxlen=self._bar_count)
        self._bars_smooth = [0.0] * self._bar_count
        self.after(0, self._draw_idle)

    def push_audio(self, chunk: np.ndarray):
        if not self._active:
            return
        rms = float(np.sqrt(np.mean(chunk ** 2))) * 8
        self._bars.append(min(rms, 1.0))

    def _schedule_draw(self):
        if self._active:
            self._draw_active()
            self._after_id = self.after(40, self._schedule_draw)

    def _smooth(self):
        alpha = 0.5
        for index, value in enumerate(self._bars):
            self._bars_smooth[index] = alpha * value + (1 - alpha) * self._bars_smooth[index]
        return self._bars_smooth

    def _draw_active(self):
        canvas = self._canvas
        canvas.delete("all")
        smooth = self._smooth()
        if max(smooth, default=0.0) < 0.05:
            smooth = self._ambient_bars()
        total = self._bar_count * (self._bar_width + self._bar_gap) - self._bar_gap
        x_start = max(0, (self._width - total) // 2)

        for index, value in enumerate(smooth):
            x = x_start + index * (self._bar_width + self._bar_gap)
            bar_height = max(3, int(value * (self._height - 8)))
            y1 = (self._height - bar_height) // 2
            y2 = y1 + bar_height
            color = self._peak_color if value > 0.7 else self._active_color
            canvas.create_rectangle(x, y1, x + self._bar_width, y2, fill=color, outline="")
        self._frame_index += 1

    def _ambient_bars(self):
        bars = []
        phase = self._frame_index / 3.5
        center = (self._bar_count - 1) / 2
        for index in range(self._bar_count):
            spread = 1 - min(1.0, abs(index - center) / max(center, 1))
            wave = (math.sin(phase + index * 0.6) + 1) / 2
            value = 0.08 + spread * 0.18 + wave * 0.12
            bars.append(min(value, 0.42))
        return bars

    def _draw_idle(self):
        canvas = self._canvas
        canvas.delete("all")
        total = self._bar_count * (self._bar_width + self._bar_gap) - self._bar_gap
        x_start = max(0, (self._width - total) // 2)
        mid = self._height // 2
        for index in range(self._bar_count):
            x = x_start + index * (self._bar_width + self._bar_gap)
            canvas.create_rectangle(
                x,
                mid - 1,
                x + self._bar_width,
                mid + 1,
                fill=self._idle_color,
                outline="",
            )
