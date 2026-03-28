"""
app.py - Dictly main window built with CustomTkinter.
"""

import customtkinter as ctk
import logging

import config_manager
from dictation_overlay import DictationOverlay
import history_manager
from runtime_logging import get_log_file
from settings_window import SettingsWindow
from transcription_backends import backend_preference_notice, normalize_backend_preference

ctk.set_default_color_theme("blue")
logger = logging.getLogger(__name__)

THEMES = {
    "light": {
        "window_bg": "#f3f6fb",
        "panel_bg": "#ffffff",
        "panel_alt": "#f8fafc",
        "border": "#d7e0ea",
        "text": "#0f172a",
        "muted": "#64748b",
        "subtle": "#5b6b80",
        "button_bg": "#ffffff",
        "button_hover": "#edf2f8",
        "button_text": "#0f172a",
        "primary_bg": "#0f172a",
        "primary_hover": "#1e293b",
        "primary_text": "#ffffff",
        "notice_bg": "#fff7e8",
        "notice_border": "#f2c66d",
        "notice_text": "#9a6700",
    },
    "dark": {
        "window_bg": "#0d1117",
        "panel_bg": "#121826",
        "panel_alt": "#0f1722",
        "border": "#23304a",
        "text": "#f8fafc",
        "muted": "#94a3b8",
        "subtle": "#9fb0ca",
        "button_bg": "#121826",
        "button_hover": "#182033",
        "button_text": "#f8fafc",
        "primary_bg": "#f8fafc",
        "primary_hover": "#dce5f0",
        "primary_text": "#0f172a",
        "notice_bg": "#2a1f10",
        "notice_border": "#6f4c16",
        "notice_text": "#fbbf24",
    },
}


class DictlyApp(ctk.CTk):
    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        self.title("Dictly")
        self.geometry("460x700")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._settings = config_manager.load()
        self._active_backend = self._settings.get("backend", "auto")
        self._requested_backend = self._settings.get("backend", "auto")
        self._current_notice = None
        self._apply_theme_mode()
        self._overlay = DictationOverlay(self, self._settings)
        self._build_ui()
        self._refresh_history()
        self.set_runtime_info(
            requested_backend=self._requested_backend,
            active_backend=self._active_backend,
            settings=self._settings,
        )

    def _apply_theme_mode(self):
        theme = self._settings.get("theme", "light")
        ctk.set_appearance_mode(theme)
        self._theme = THEMES.get(theme, THEMES["light"])

    def _rebuild_ui(self):
        for child in self.winfo_children():
            if child is self._overlay:
                continue
            child.destroy()
        self._apply_theme_mode()
        self._build_ui()
        self._refresh_history()
        self.set_runtime_info(
            requested_backend=self._requested_backend,
            active_backend=self._active_backend,
            settings=self._settings,
        )
        self.set_notice(self._current_notice)
        if self._overlay_exists():
            self._overlay.update_settings(self._settings)

    def _overlay_exists(self) -> bool:
        return hasattr(self, "_overlay") and self._overlay is not None and bool(self._overlay.winfo_exists())

    def _widget_exists(self, widget) -> bool:
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except Exception:
            return False

    def _build_ui(self):
        theme = self._theme
        self.configure(fg_color=theme["window_bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        topbar = ctk.CTkFrame(self, fg_color="transparent")
        topbar.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 0))
        topbar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            topbar,
            text="Dictly",
            font=ctk.CTkFont("Segoe UI", size=28, weight="bold"),
            text_color=theme["text"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            topbar,
            text="Offline dictation with a live desktop overlay",
            text_color=theme["muted"],
            font=ctk.CTkFont("Segoe UI", size=12),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ctk.CTkButton(
            topbar,
            text="Settings",
            width=86,
            height=36,
            fg_color=theme["button_bg"],
            hover_color=theme["button_hover"],
            border_width=1,
            border_color=theme["border"],
            text_color=theme["button_text"],
            command=self._open_settings,
        ).grid(row=0, column=2, rowspan=2)

        hero = ctk.CTkFrame(
            self,
            corner_radius=22,
            fg_color=theme["panel_bg"],
            border_width=1,
            border_color=theme["border"],
        )
        hero.grid(row=1, column=0, sticky="ew", padx=22, pady=(18, 0))
        hero.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            hero,
            text="Desktop overlay ready",
            font=ctk.CTkFont("Segoe UI", size=18, weight="bold"),
            text_color=theme["text"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            hero,
            text="Hold the hotkey to speak. The waveform overlay appears near the taskbar while Dictly keeps history and runtime details here.",
            text_color=theme["subtle"],
            wraplength=390,
            justify="left",
            font=ctk.CTkFont("Segoe UI", size=12),
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 14))

        self._notice_frame = ctk.CTkFrame(
            hero,
            corner_radius=14,
            fg_color=theme["notice_bg"],
            border_width=1,
            border_color=theme["notice_border"],
        )
        self._notice_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 14))
        self._notice_frame.grid_columnconfigure(0, weight=1)
        self._notice_label = ctk.CTkLabel(
            self._notice_frame,
            text="",
            text_color=theme["notice_text"],
            wraplength=370,
            justify="left",
            font=ctk.CTkFont("Segoe UI", size=12, weight="bold"),
        )
        self._notice_label.grid(row=0, column=0, sticky="w", padx=12, pady=10)
        self._notice_frame.grid_remove()

        self._requested_chip = self._make_metric_card(hero, row=3, column=0, title="Requested Backend")
        self._active_chip = self._make_metric_card(hero, row=3, column=1, title="Active Engine")
        self._model_chip = self._make_metric_card(hero, row=4, column=0, title="Model")
        self._speech_chip = self._make_metric_card(hero, row=4, column=1, title="Beam / Language")

        history_card = ctk.CTkFrame(self, fg_color="transparent")
        history_card.grid(row=2, column=0, sticky="nsew", padx=22, pady=(14, 0))
        history_card.grid_columnconfigure(0, weight=1)
        history_card.grid_rowconfigure(1, weight=1)

        history_top = ctk.CTkFrame(history_card, fg_color="transparent")
        history_top.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            history_top,
            text="History",
            font=ctk.CTkFont("Segoe UI", size=13, weight="bold"),
            text_color=theme["text"],
        ).pack(side="left")
        ctk.CTkButton(
            history_top,
            text="Clear",
            width=58,
            height=26,
            fg_color=theme["button_bg"],
            border_width=1,
            border_color=theme["border"],
            hover_color=theme["button_hover"],
            text_color=theme["button_text"],
            font=ctk.CTkFont("Segoe UI", size=11),
            command=self._clear_history,
        ).pack(side="right")

        self._history_frame = ctk.CTkScrollableFrame(
            history_card,
            corner_radius=16,
            fg_color=theme["panel_bg"],
            border_width=1,
            border_color=theme["border"],
        )
        self._history_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self._history_frame.grid_columnconfigure(0, weight=1)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", padx=22, pady=(10, 14))
        self._footer_label = ctk.CTkLabel(
            bottom,
            text="",
            text_color=theme["muted"],
            font=ctk.CTkFont("Segoe UI", size=11),
        )
        self._footer_label.pack(side="left")

    def _make_metric_card(self, parent, row: int, column: int, title: str):
        theme = self._theme
        card = ctk.CTkFrame(
            parent,
            corner_radius=16,
            fg_color=theme["panel_alt"],
            border_width=1,
            border_color=theme["border"],
        )
        card.grid(row=row, column=column, sticky="ew", padx=18 if column == 0 else (8, 18), pady=(0, 10))
        ctk.CTkLabel(
            card,
            text=title,
            text_color=theme["muted"],
            font=ctk.CTkFont("Segoe UI", size=10),
        ).pack(anchor="w", padx=12, pady=(10, 2))
        value = ctk.CTkLabel(
            card,
            text="-",
            text_color=theme["text"],
            font=ctk.CTkFont("Segoe UI", size=14, weight="bold"),
        )
        value.pack(anchor="w", padx=12, pady=(0, 10))
        return value

    def _model_summary(self, settings: dict) -> str:
        model = settings.get("model", "small")
        if (settings.get("model_path") or "").strip():
            return f"{model} (local)"
        return str(model)

    def _status_summary(self, requested_backend: str, active_backend: str, settings: dict) -> str:
        model = self._model_summary(settings)
        beam = settings.get("beam_size", 15)
        lang = settings.get("language") or "auto"
        return f"Requested: {requested_backend}  |  Active: {active_backend}  |  Model: {model}  |  Beam: {beam}  |  Language: {lang}"

    def set_runtime_info(
        self,
        requested_backend: str | None = None,
        active_backend: str | None = None,
        settings: dict | None = None,
    ):
        runtime_settings = dict(settings or self._settings)
        self._requested_backend = requested_backend or runtime_settings.get("backend", "auto")
        self._active_backend = active_backend or self._requested_backend

        beam = runtime_settings.get("beam_size", 15)
        lang = runtime_settings.get("language") or "auto"

        def update():
            if not all(
                self._widget_exists(widget)
                for widget in (
                    getattr(self, "_requested_chip", None),
                    getattr(self, "_active_chip", None),
                    getattr(self, "_model_chip", None),
                    getattr(self, "_speech_chip", None),
                    getattr(self, "_footer_label", None),
                )
            ):
                return
            self._requested_chip.configure(text=str(self._requested_backend))
            self._active_chip.configure(text=str(self._active_backend))
            self._model_chip.configure(text=self._model_summary(runtime_settings))
            self._speech_chip.configure(text=f"{beam} / {lang}")
            self._footer_label.configure(
                text=self._status_summary(
                    requested_backend=str(self._requested_backend),
                    active_backend=str(self._active_backend),
                    settings=runtime_settings,
                )
            )

        self.after(0, update)

    def set_status(self, state: str):
        self.after(0, lambda: self._overlay_exists() and self._overlay.set_state(state))

    def set_notice(self, text: str | None):
        self._current_notice = text

        def update():
            if not all(
                self._widget_exists(widget)
                for widget in (
                    getattr(self, "_notice_label", None),
                    getattr(self, "_notice_frame", None),
                )
            ):
                return
            if text:
                self._notice_label.configure(text=text)
                self._notice_frame.grid()
            else:
                self._notice_label.configure(text="")
                self._notice_frame.grid_remove()

        self.after(0, update)

    def start_waveform(self):
        self.after(0, lambda: self._overlay_exists() and self._overlay.start_waveform())

    def stop_waveform(self):
        self.after(0, lambda: self._overlay_exists() and self._overlay.stop_waveform())

    def push_waveform(self, chunk):
        if self._overlay_exists():
            self._overlay.push_audio(chunk)

    def set_result(self, text: str):
        self.after(0, self._refresh_history)

    def _refresh_history(self):
        theme = self._theme
        for widget in self._history_frame.winfo_children():
            widget.destroy()

        entries = history_manager.get_all()
        if not entries:
            ctk.CTkLabel(
                self._history_frame,
                text="No history yet.",
                text_color=theme["muted"],
                font=ctk.CTkFont("Segoe UI", size=12),
            ).grid(row=0, column=0, pady=22)
            return

        for index, entry in enumerate(entries[:50]):
            self._add_history_row(index, entry)

    def _add_history_row(self, index: int, entry: dict):
        theme = self._theme
        row_frame = ctk.CTkFrame(
            self._history_frame,
            corner_radius=12,
            fg_color=theme["panel_alt"],
            border_width=1,
            border_color=theme["border"],
        )
        row_frame.grid(row=index, column=0, sticky="ew", pady=4, padx=2)
        row_frame.grid_columnconfigure(0, weight=1)

        timestamp = entry.get("timestamp", "")[:16].replace("T", "  ")
        meta = f"{timestamp}  |  {entry.get('duration', 0):.1f}s  |  {entry.get('language', '')}"
        ctk.CTkLabel(
            row_frame,
            text=meta,
            text_color=theme["muted"],
            font=ctk.CTkFont("Segoe UI", size=10),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))

        text = entry.get("text", "")
        preview = text[:120] + ("..." if len(text) > 120 else "")
        ctk.CTkLabel(
            row_frame,
            text=preview,
            wraplength=360,
            justify="left",
            text_color=theme["text"],
            font=ctk.CTkFont("Segoe UI", size=12),
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

    def _clear_history(self):
        history_manager.clear()
        self._refresh_history()

    def _open_settings(self):
        SettingsWindow(self, self._settings, on_save=self._on_settings_saved)

    def _on_settings_saved(self, new_settings: dict):
        preference_notice = backend_preference_notice(new_settings.get("backend"), new_settings)
        new_settings["backend"] = normalize_backend_preference(new_settings.get("backend"), new_settings)
        config_manager.save(new_settings)
        theme_changed = new_settings.get("theme", "light") != self._settings.get("theme", "light")
        self._settings = new_settings
        if self._overlay_exists():
            self._overlay.update_settings(new_settings)
        self.set_runtime_info(
            requested_backend=new_settings.get("backend"),
            active_backend=self._active_backend,
            settings=new_settings,
        )
        self._engine.reload_settings(new_settings)
        if theme_changed:
            self._rebuild_ui()
        if preference_notice:
            self.set_notice(preference_notice)

    def _on_close(self):
        self.withdraw()

    def show(self):
        self.deiconify()
        self.lift()

    def report_callback_exception(self, exc, val, tb):
        logger.exception("Tkinter callback error", exc_info=(exc, val, tb))
        try:
            self.set_notice(f"Internal error. See log: {get_log_file()}")
        except Exception:
            pass
