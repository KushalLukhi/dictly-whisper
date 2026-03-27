"""
settings_window.py - Dictly settings dialog built with CustomTkinter.
"""

import customtkinter as ctk

from config_manager import LANGUAGE_OPTIONS, MODEL_OPTIONS
import startup_manager
from transcription_backends import DEFAULT_BACKEND, get_backend_options

THEMES = {
    "light": {
        "window_bg": "#f3f6fb",
        "card_bg": "#ffffff",
        "card_alt": "#f8fafc",
        "border": "#d7e0ea",
        "text": "#0f172a",
        "muted": "#64748b",
        "subtle": "#94a3b8",
        "button_bg": "#ffffff",
        "button_hover": "#edf2f8",
        "button_border": "#d7e0ea",
        "button_text": "#0f172a",
        "primary_bg": "#0f172a",
        "primary_hover": "#1e293b",
        "primary_text": "#ffffff",
    },
    "dark": {
        "window_bg": "#0d1117",
        "card_bg": "#121826",
        "card_alt": "#0f1722",
        "border": "#23304a",
        "text": "#f8fafc",
        "muted": "#94a3b8",
        "subtle": "#64748b",
        "button_bg": "#121826",
        "button_hover": "#182033",
        "button_border": "#23304a",
        "button_text": "#f8fafc",
        "primary_bg": "#f8fafc",
        "primary_hover": "#dce5f0",
        "primary_text": "#0f172a",
    },
}


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, settings: dict, on_save):
        super().__init__(parent)
        self.title("Dictly - Settings")
        self.geometry("560x560")
        self.minsize(560, 560)
        self.resizable(False, False)
        self._settings = dict(settings)
        self._on_save = on_save
        self._theme_name = self._settings.get("theme", "light")
        ctk.set_appearance_mode(self._theme_name)
        self._theme = THEMES.get(self._theme_name, THEMES["light"])
        self.configure(fg_color=self._theme["window_bg"])
        self.grab_set()
        self._build()

    def _build(self):
        theme = self._theme
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew", padx=22, pady=20)
        scroll.grid_columnconfigure(0, weight=1)

        backend_options = get_backend_options()
        backend_labels = [option.label for option in backend_options]
        self._backend_label_to_key = {option.label: option.key for option in backend_options}
        selected_backend = self._settings.get("backend", DEFAULT_BACKEND)
        backend_label = next((option.label for option in backend_options if option.key == selected_backend), backend_labels[0])
        self._backend_var = ctk.StringVar(value=backend_label)
        self._model_var = ctk.StringVar(value=self._settings.get("model", "small"))
        lang_code = self._settings.get("language")
        lang_display = next((key for key, value in LANGUAGE_OPTIONS.items() if value == lang_code), "English")
        self._lang_var = ctk.StringVar(value=lang_display)
        self._beam_var = ctk.IntVar(value=self._settings.get("beam_size", 15))
        self._theme_var = ctk.StringVar(value=self._theme_name.capitalize())
        hotkey = self._settings.get("hotkey", ["ctrl", "shift"])
        self._hotkey_var = ctk.StringVar(value=" + ".join(key.capitalize() for key in hotkey))
        self._append_var = ctk.BooleanVar(value=self._settings.get("append_space", True))
        self._prepend_var = ctk.BooleanVar(value=self._settings.get("prepend_space", False))
        self._paste_var = ctk.StringVar(value=self._settings.get("paste_method", "clipboard"))
        self._startup_var = ctk.BooleanVar(value=startup_manager.is_enabled())

        self._build_section(
            scroll,
            row=0,
            title="Transcription",
            description="Choose the runtime backend and how aggressively Dictly searches for transcripts.",
            fields=[
                ("Backend", lambda master: self._build_option_menu(master, self._backend_var, backend_labels)),
                ("Model", lambda master: self._build_option_menu(master, self._model_var, MODEL_OPTIONS)),
                ("Language", lambda master: self._build_option_menu(master, self._lang_var, list(LANGUAGE_OPTIONS.keys()))),
                ("Beam Size", self._build_beam_widget),
            ],
        )

        self._build_section(
            scroll,
            row=1,
            title="Appearance",
            description="Switch the app between light and dark without changing the overlay behavior.",
            fields=[
                ("Theme", lambda master: self._build_option_menu(master, self._theme_var, ["Light", "Dark"])),
            ],
        )

        self._build_section(
            scroll,
            row=2,
            title="Hotkey",
            description="The current push-to-talk combo is shown below.",
            fields=[
                ("Hold To Record", lambda master: self._build_disabled_entry(master, self._hotkey_var)),
            ],
            footer_text="Hotkey editing is still config-file based.",
        )

        self._build_section(
            scroll,
            row=3,
            title="Output",
            description="Control how Dictly inserts recognized text into the active application.",
            fields=[
                ("Append Space", lambda master: self._build_switch(master, self._append_var)),
                ("Prepend Space", lambda master: self._build_switch(master, self._prepend_var)),
                ("Paste Method", lambda master: self._build_option_menu(master, self._paste_var, ["clipboard", "type"])),
            ],
        )

        self._build_section(
            scroll,
            row=4,
            title="System",
            description="Choose whether Dictly launches automatically when you sign in.",
            fields=[
                ("Launch At Startup", lambda master: self._build_switch(master, self._startup_var)),
            ],
        )

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 20))
        button_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            fg_color=theme["button_bg"],
            hover_color=theme["button_hover"],
            border_width=1,
            border_color=theme["button_border"],
            text_color=theme["button_text"],
            command=self.destroy,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            button_frame,
            text="Save & Reload Model",
            fg_color=theme["primary_bg"],
            hover_color=theme["primary_hover"],
            text_color=theme["primary_text"],
            command=self._save,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_section(self, parent, row: int, title: str, description: str, fields: list, footer_text: str | None = None):
        theme = self._theme
        card = ctk.CTkFrame(
            parent,
            corner_radius=20,
            fg_color=theme["card_bg"],
            border_width=1,
            border_color=theme["border"],
        )
        card.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=title,
            text_color=theme["text"],
            font=ctk.CTkFont("Segoe UI", size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(
            card,
            text=description,
            text_color=theme["muted"],
            wraplength=470,
            justify="left",
            font=ctk.CTkFont("Segoe UI", size=12),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.grid(row=2, column=0, sticky="ew", padx=18)
        content.grid_columnconfigure(1, weight=1)

        for index, (label_text, widget_builder) in enumerate(fields):
            row_frame = ctk.CTkFrame(
                content,
                corner_radius=14,
                fg_color=self._theme["card_alt"],
                border_width=1,
                border_color=self._theme["border"],
            )
            row_frame.grid(row=index, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            row_frame.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                row_frame,
                text=label_text,
                text_color=self._theme["muted"],
                font=ctk.CTkFont("Segoe UI", size=11, weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=12, pady=12)
            widget = widget_builder(row_frame)
            sticky = "ew" if isinstance(widget, ctk.CTkFrame) else "e"
            widget.grid(in_=row_frame, row=0, column=1, sticky=sticky, padx=(0, 12), pady=10)

        if footer_text:
            ctk.CTkLabel(
                card,
                text=footer_text,
                text_color=theme["subtle"],
                font=ctk.CTkFont("Segoe UI", size=11),
            ).grid(row=3, column=0, sticky="w", padx=18, pady=(0, 16))
        else:
            ctk.CTkLabel(card, text="", height=6).grid(row=3, column=0)

    def _build_option_menu(self, master, variable, values):
        return ctk.CTkOptionMenu(master, width=110, variable=variable, values=values)

    def _build_disabled_entry(self, master, variable):
        return ctk.CTkEntry(master, width=220, textvariable=variable, state="disabled")

    def _build_switch(self, master, variable):
        return ctk.CTkSwitch(master, text="", variable=variable)

    def _build_beam_widget(self, master):
        frame = ctk.CTkFrame(master, fg_color="transparent")
        value_label = ctk.CTkLabel(frame, text=str(self._beam_var.get()), width=28, text_color=self._theme["text"])

        def update(value):
            value_label.configure(text=str(int(float(value))))
            self._beam_var.set(int(float(value)))

        slider = ctk.CTkSlider(
            frame,
            from_=1,
            to=15,
            number_of_steps=14,
            variable=self._beam_var,
            command=update,
            width=170,
        )
        slider.pack(side="left")
        value_label.pack(side="left", padx=(10, 0))
        return frame

    def _save(self):
        self._settings["backend"] = self._backend_label_to_key[self._backend_var.get()]
        self._settings["model"] = self._model_var.get()
        self._settings["language"] = LANGUAGE_OPTIONS.get(self._lang_var.get())
        self._settings["beam_size"] = self._beam_var.get()
        self._settings["theme"] = self._theme_var.get().lower()
        self._settings["append_space"] = self._append_var.get()
        self._settings["prepend_space"] = self._prepend_var.get()
        self._settings["paste_method"] = self._paste_var.get()

        startup_manager.set_enabled(self._startup_var.get())
        self._settings["launch_on_startup"] = self._startup_var.get()

        self._on_save(self._settings)
        self.destroy()
