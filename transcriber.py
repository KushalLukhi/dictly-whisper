"""
transcriber.py - Delegates speech recognition to the configured backend.
"""

import threading

import numpy as np

from transcription_backends import DEFAULT_BACKEND, create_backend, resolve_backend_choice


class Transcriber:
    def __init__(self):
        self.backend = None
        self._backend_name = None
        self._backend_notice = None
        self._settings = {}
        self._lock = threading.RLock()

    def load(self, settings: dict):
        with self._lock:
            self._settings = dict(settings)
            requested_backend = settings.get("backend", DEFAULT_BACKEND)
            backend_name, notice = resolve_backend_choice(requested_backend, settings)

            reuse_backend = self.backend is not None and self._backend_name == backend_name
            backend = self.backend if reuse_backend else create_backend(backend_name, settings)

            try:
                backend.load(settings)
            except Exception:
                backend.unload()
                if reuse_backend:
                    self.backend = None
                    self._backend_name = None
                raise

            self.backend = backend
            self._backend_name = backend_name

            backend_notice = getattr(self.backend, "notice", None)
            if notice and backend_notice and notice != backend_notice:
                self._backend_notice = f"{notice} {backend_notice}"
            else:
                self._backend_notice = backend_notice or notice

    def reload(self, settings: dict):
        """Reload with new settings (e.g. after model change in Settings)."""
        with self._lock:
            if self.backend is not None:
                self.backend.unload()
            self.backend = None
            self._backend_name = None
            self._backend_notice = None
            self.load(settings)

    def transcribe(self, audio: np.ndarray) -> tuple[str, str]:
        """Returns (transcribed_text, detected_language)."""
        with self._lock:
            if self.backend is None:
                raise RuntimeError("Model not loaded.")
            return self.backend.transcribe(audio)

    def get_notice(self) -> str | None:
        with self._lock:
            return self._backend_notice

    def get_active_backend(self) -> str | None:
        with self._lock:
            if self.backend is None:
                return None
            return getattr(self.backend, "active_name", getattr(self.backend, "name", None))
