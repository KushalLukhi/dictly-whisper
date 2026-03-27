"""
dictation_tooltip_widget.py - Tooltip-inspired dictation status widget.
"""

import customtkinter as ctk

from waveform_widget import WaveformWidget


STATE_CONTENT = {
    "idle": {
        "prefix": "Click or hold ",
        "accent": "{hotkey}",
        "suffix": " to start dictating",
        "accent_color": "#d8a5ff",
        "dot_color": "#7c7c7c",
    },
    "loading": {
        "prefix": "Preparing ",
        "accent": "{backend}",
        "suffix": " for dictation",
        "accent_color": "#f5c26b",
        "dot_color": "#f59e0b",
    },
    "recording": {
        "prefix": "Listening on ",
        "accent": "{hotkey}",
        "suffix": " release when done",
        "accent_color": "#f09fff",
        "dot_color": "#ff7ad9",
    },
    "transcribing": {
        "prefix": "Transcribing with ",
        "accent": "{model}",
        "suffix": " locally",
        "accent_color": "#77b7ff",
        "dot_color": "#60a5fa",
    },
    "done": {
        "prefix": "Last dictation ",
        "accent": "captured",
        "suffix": "",
        "accent_color": "#60d7a0",
        "dot_color": "#34d399",
    },
    "error": {
        "prefix": "Dictation failed, check ",
        "accent": "console",
        "suffix": "",
        "accent_color": "#ff8c8c",
        "dot_color": "#f87171",
    },
}


class DictationTooltipWidget(ctk.CTkFrame):
    def __init__(self, parent, settings: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._settings = dict(settings)

        self.grid_columnconfigure(0, weight=1)

        self._bubble = ctk.CTkFrame(
            self,
            corner_radius=22,
            fg_color="#080808",
            border_color="#262626",
            border_width=1,
        )
        self._bubble.grid(row=0, column=0, padx=8, sticky="")

        text_row = ctk.CTkFrame(self._bubble, fg_color="transparent")
        text_row.pack(padx=18, pady=12)

        self._prefix_label = ctk.CTkLabel(
            text_row,
            text="",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#f7f7f7",
        )
        self._prefix_label.pack(side="left")

        self._accent_label = ctk.CTkLabel(
            text_row,
            text="",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#d8a5ff",
        )
        self._accent_label.pack(side="left")

        self._suffix_label = ctk.CTkLabel(
            text_row,
            text="",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#f7f7f7",
        )
        self._suffix_label.pack(side="left")

        dock = ctk.CTkFrame(self, fg_color="transparent")
        dock.grid(row=1, column=0, pady=(8, 0))

        self._indicator = ctk.CTkFrame(
            dock,
            width=42,
            height=36,
            corner_radius=18,
            fg_color="#080808",
            border_color="#262626",
            border_width=1,
        )
        self._indicator.pack(side="left", padx=(0, 8))
        self._indicator.pack_propagate(False)

        self._indicator_dot = ctk.CTkLabel(
            self._indicator,
            text="o",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#7c7c7c",
        )
        self._indicator_dot.place(relx=0.5, rely=0.5, anchor="center")

        self._wave_pod = ctk.CTkFrame(
            dock,
            width=96,
            height=36,
            corner_radius=18,
            fg_color="#080808",
            border_color="#262626",
            border_width=1,
        )
        self._wave_pod.pack(side="left")
        self._wave_pod.pack_propagate(False)

        self._waveform = WaveformWidget(
            self._wave_pod,
            width=78,
            height=14,
            bar_count=14,
            bar_width=3,
            bar_gap=2,
            bg_color="#080808",
            idle_color="#525252",
            active_color="#d8a5ff",
            peak_color="#ff8fd6",
            corner_radius=0,
        )
        self._waveform.place(relx=0.5, rely=0.5, anchor="center")

        self.set_state("idle")

    def update_settings(self, settings: dict):
        self._settings = dict(settings)
        self.set_state("idle")

    def set_state(self, state: str):
        content = STATE_CONTENT.get(state, STATE_CONTENT["idle"])
        hotkey = " + ".join(key.capitalize() for key in self._settings.get("hotkey", ["ctrl", "shift"]))
        model = self._settings.get("model", "small")
        backend = self._settings.get("backend", "faster-whisper")

        self._prefix_label.configure(text=content["prefix"])
        self._accent_label.configure(
            text=content["accent"].format(hotkey=hotkey, model=model, backend=backend),
            text_color=content["accent_color"],
        )
        self._suffix_label.configure(text=content["suffix"])
        self._indicator_dot.configure(text_color=content["dot_color"])

    def start_waveform(self):
        self._waveform.start()

    def stop_waveform(self):
        self._waveform.stop()

    def push_audio(self, chunk):
        self._waveform.push_audio(chunk)
