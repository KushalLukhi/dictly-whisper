"""
transcription_backends.py - Backend registry for Dictly transcription engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import importlib
import platform

import numpy as np


DEFAULT_BACKEND = "auto"


@dataclass(frozen=True)
class BackendOption:
    key: str
    label: str


class TranscriptionBackend(ABC):
    @abstractmethod
    def load(self, settings: dict):
        """Prepare the backend using the provided settings."""

    @abstractmethod
    def unload(self):
        """Release any loaded model state."""

    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> tuple[str, str]:
        """Return (transcribed_text, detected_language)."""


class FasterWhisperBackend(TranscriptionBackend):
    name = "faster-whisper"

    def __init__(self):
        self.model = None
        self._settings = {}
        self._device = "cpu"
        self.notice = None
        self.active_name = self.name

    def load(self, settings: dict):
        from faster_whisper import WhisperModel

        self._settings = settings
        model_name = settings.get("model", "small")
        requested_device = _normalize_faster_whisper_device(settings.get("faster_whisper_device"))
        compute_type = settings.get("compute_type", "int8")
        self.notice = None

        if requested_device == "auto":
            device = "cuda" if _supports_faster_whisper_cuda() else "cpu"
        else:
            device = requested_device

        if device == "cuda" and not _supports_faster_whisper_cuda():
            self.notice = "CUDA faster-whisper unavailable. Using CPU faster-whisper instead."
            device = "cpu"

        effective_compute_type = "float16" if device == "cuda" else compute_type

        print(
            f"[Transcriber] Backend={self.name} model='{model_name}' device='{device}' compute='{effective_compute_type}'"
        )
        try:
            self.model = WhisperModel(model_name, device=device, compute_type=effective_compute_type)
        except Exception:
            if device != "cuda":
                raise
            self.notice = "CUDA faster-whisper failed to load. Using CPU faster-whisper instead."
            device = "cpu"
            effective_compute_type = compute_type
            print(f"[Transcriber] {self.notice}")
            self.model = WhisperModel(model_name, device=device, compute_type=effective_compute_type)

        self._device = device
        self.active_name = f"{self.name} ({device})"
        print("[Transcriber] Model ready [OK]")

    def unload(self):
        self.model = None
        self.notice = None
        self._device = "cpu"
        self.active_name = self.name

    def transcribe(self, audio: np.ndarray) -> tuple[str, str]:
        if self.model is None:
            raise RuntimeError("Backend not loaded.")
        if audio is None or len(audio) == 0:
            return "", ""

        language = self._settings.get("language") or None
        beam_size = self._settings.get("beam_size", 15)
        threshold = self._settings.get("vad_threshold", 0.3)
        pad_ms = self._settings.get("speech_pad_ms", 500)

        segments, info = self.model.transcribe(
            audio.astype(np.float32),
            language=language,
            beam_size=beam_size,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=pad_ms,
                threshold=threshold,
            ),
        )

        text = " ".join(segment.text.strip() for segment in segments).strip()
        detected = info.language or ""
        print(f"[Transcriber] [{detected}] \"{text}\"")
        return text, detected


class WhisperDirectMLBackend(TranscriptionBackend):
    name = "whisper-directml"

    def __init__(self):
        self.model = None
        self._settings = {}
        self._device = None

    def load(self, settings: dict):
        self._device = _ensure_directml_runtime()
        whisper = importlib.import_module("whisper")

        self._settings = settings
        model_name = settings.get("model", "small")
        print(f"[Transcriber] Backend={self.name} model='{model_name}' device='directml'")
        self.model = whisper.load_model(model_name, device="cpu")
        self.model = self.model.to(self._device)
        print("[Transcriber] Model ready [OK]")

    def unload(self):
        self.model = None
        self._device = None

    def transcribe(self, audio: np.ndarray) -> tuple[str, str]:
        if self.model is None:
            raise RuntimeError("Backend not loaded.")
        if audio is None or len(audio) == 0:
            return "", ""

        language = self._settings.get("language") or None
        beam_size = self._settings.get("beam_size", 15)
        result = self.model.transcribe(
            audio.astype(np.float32),
            language=language,
            beam_size=beam_size,
            fp16=False,
            verbose=False,
        )
        text = (result.get("text") or "").strip()
        detected = result.get("language") or ""
        print(f"[Transcriber] [{detected}] \"{text}\"")
        return text, detected


class AutoBackend(TranscriptionBackend):
    name = "auto"

    def __init__(self):
        self._selected_backend = None

    def load(self, settings: dict):
        candidates = []
        faster_whisper_device = _normalize_faster_whisper_device(settings.get("faster_whisper_device"))

        if faster_whisper_device == "auto":
            if _supports_faster_whisper_cuda():
                candidates.append(("faster-whisper", FasterWhisperBackend, {**settings, "faster_whisper_device": "cuda"}))
            if _supports_directml():
                candidates.append(("whisper-directml", WhisperDirectMLBackend, dict(settings)))
            candidates.append(("faster-whisper", FasterWhisperBackend, {**settings, "faster_whisper_device": "cpu"}))
        else:
            candidates.append(("faster-whisper", FasterWhisperBackend, dict(settings)))

        errors = []
        for backend_name, backend_type, backend_settings in candidates:
            backend = backend_type()
            try:
                backend.load(backend_settings)
                self._selected_backend = backend
                print(f"[Transcriber] Auto selected '{getattr(backend, 'active_name', backend_name)}'")
                return
            except Exception as exc:
                errors.append(f"{backend_name}: {exc}")
                backend.unload()

        raise RuntimeError("No usable transcription backend. " + " | ".join(errors))

    def unload(self):
        if self._selected_backend is not None:
            self._selected_backend.unload()
        self._selected_backend = None

    def transcribe(self, audio: np.ndarray) -> tuple[str, str]:
        if self._selected_backend is None:
            raise RuntimeError("Backend not loaded.")
        return self._selected_backend.transcribe(audio)

    @property
    def active_name(self) -> str:
        if self._selected_backend is None:
            return self.name
        return getattr(self._selected_backend, "name", self.name)


BACKEND_OPTIONS = [
    BackendOption(key=DEFAULT_BACKEND, label="Auto (prefer GPU, fallback to CPU)"),
    BackendOption(key="whisper-directml", label="Windows GPU (torch-directml, experimental)"),
    BackendOption(key="faster-whisper", label="faster-whisper (CPU / CUDA)"),
]

_BACKEND_FACTORIES = {
    "auto": AutoBackend,
    "whisper-directml": WhisperDirectMLBackend,
    "faster-whisper": FasterWhisperBackend,
}


def _ensure_directml_runtime():
    if platform.system() != "Windows":
        raise RuntimeError("DirectML backend is only available on Windows.")

    try:
        torch = importlib.import_module("torch")
        torch_directml = importlib.import_module("torch_directml")
        device = torch_directml.device()

        indices = torch.tensor([[0], [0]], dtype=torch.int64)
        values = torch.tensor([1.0], dtype=torch.float32)
        probe = torch.sparse_coo_tensor(indices, values, (1, 1))
        probe.to(device)
        return device
    except Exception as exc:
        raise RuntimeError(
            "torch-directml is installed, but Whisper cannot run on the current "
            "DirectML runtime."
        ) from exc


def _supports_directml() -> bool:
    if platform.system() != "Windows":
        return False
    try:
        importlib.import_module("whisper")
        _ensure_directml_runtime()
        return True
    except Exception:
        return False


def _supports_faster_whisper_cuda() -> bool:
    try:
        ctranslate2 = importlib.import_module("ctranslate2")
        return bool(ctranslate2.get_cuda_device_count() > 0)
    except Exception:
        return False


def _normalize_faster_whisper_device(value: str | None) -> str:
    device = (value or "auto").strip().lower()
    if device not in {"auto", "cpu", "cuda"}:
        return "auto"
    return device


def get_backend_options() -> list[BackendOption]:
    return list(BACKEND_OPTIONS)


def resolve_backend_choice(name: str | None, settings: dict | None = None) -> tuple[str, str | None]:
    del settings
    backend_name = (name or DEFAULT_BACKEND).strip().lower()
    if backend_name == "whisper-directml" and not _supports_directml():
        return "faster-whisper", "DirectML GPU backend unavailable. Using CPU backend instead."
    if backend_name == "whisper-cpp":
        return "faster-whisper", "whisper.cpp backend was removed. Using CPU backend instead."
    return backend_name, None


def normalize_backend_preference(name: str | None, settings: dict | None = None) -> str:
    requested = (name or DEFAULT_BACKEND).strip().lower()
    resolved, notice = resolve_backend_choice(requested, settings)
    if notice and requested != DEFAULT_BACKEND:
        return DEFAULT_BACKEND
    return resolved


def backend_preference_notice(name: str | None, settings: dict | None = None) -> str | None:
    requested = (name or DEFAULT_BACKEND).strip().lower()
    resolved, notice = resolve_backend_choice(requested, settings)
    if notice and requested != DEFAULT_BACKEND and resolved != requested:
        return f"{notice} Settings were switched back to Auto."
    return notice


def create_backend(name: str | None, settings: dict | None = None) -> TranscriptionBackend:
    backend_name, notice = resolve_backend_choice(name, settings)
    if notice:
        print(f"[Transcriber] {notice}")
    backend_factory = _BACKEND_FACTORIES.get(backend_name)
    if backend_factory is None:
        valid = ", ".join(option.key for option in BACKEND_OPTIONS)
        raise ValueError(f"Unknown backend '{backend_name}'. Valid options: {valid}")
    return backend_factory()
