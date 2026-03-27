"""
transcriber.py - Delegates speech recognition to the configured backend.
"""

import numpy as np

from transcription_backends import DEFAULT_BACKEND, create_backend, resolve_backend_choice


class Transcriber:
    def __init__(self):
        self.backend = None
        self._backend_name = None
        self._backend_notice = None
        self._settings = {}

    def load(self, settings: dict):
        self._settings = settings
        requested_backend = settings.get("backend", DEFAULT_BACKEND)
        backend_name, notice = resolve_backend_choice(requested_backend, settings)
        self._backend_notice = notice
        if self.backend is None or self._backend_name != backend_name:
            self.backend = create_backend(backend_name, settings)
            self._backend_name = backend_name
        self.backend.load(settings)

    def reload(self, settings: dict):
        """Reload with new settings (e.g. after model change in Settings)."""
        if self.backend is not None:
            self.backend.unload()
        self.backend = None
        self._backend_name = None
        self.load(settings)

    def transcribe(self, audio: np.ndarray) -> tuple[str, str]:
        """Returns (transcribed_text, detected_language)."""
        if self.backend is None:
            raise RuntimeError("Model not loaded.")
        return self.backend.transcribe(audio)

    def get_notice(self) -> str | None:
        return self._backend_notice

    def get_active_backend(self) -> str | None:
        if self.backend is None:
            return None
        return getattr(self.backend, "active_name", getattr(self.backend, "name", None))
