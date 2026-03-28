"""
transcription_backends.py - Backend registry for Dictly transcription engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import importlib
import os
import platform
from pathlib import Path
import sys

import numpy as np


DEFAULT_BACKEND = "auto"


class ModelUnavailableError(RuntimeError):
    """Raised when the selected model cannot be loaded from a local source."""


def _bootstrap_ca_bundle() -> Path | None:
    """Prefer the Windows trust store, then fall back to certifi."""
    if platform.system() == "Windows":
        try:
            truststore = importlib.import_module("truststore")
            truststore.inject_into_ssl()
            print("[Transcriber] TLS trust source='windows trust store'")
            return None
        except Exception:
            pass

        try:
            importlib.import_module("certifi_win32")
            print("[Transcriber] TLS trust source='windows certifi bridge'")
        except Exception:
            pass

    try:
        certifi = importlib.import_module("certifi")
    except Exception:
        return None

    bundle_path = Path(certifi.where())
    if not bundle_path.exists():
        return None

    bundle_str = str(bundle_path)
    os.environ.setdefault("SSL_CERT_FILE", bundle_str)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", bundle_str)
    os.environ.setdefault("CURL_CA_BUNDLE", bundle_str)
    print(f"[Transcriber] TLS trust source='certifi' bundle='{bundle_path}'")
    return bundle_path


def _ssl_error_text(exc: Exception) -> str:
    return (str(exc).strip() or exc.__class__.__name__).lower()


def _looks_like_ssl_error(exc: Exception) -> bool:
    lowered = _ssl_error_text(exc)
    markers = (
        "certificate verify failed",
        "cert_verify_failed",
        "unable to get local issuer certificate",
        "ssl:",
    )
    return any(marker in lowered for marker in markers)


def _configure_hf_insecure_client() -> bool:
    try:
        huggingface_hub = importlib.import_module("huggingface_hub")
        httpx = importlib.import_module("httpx")
    except Exception:
        return False

    def _client_factory():
        return httpx.Client(verify=False, follow_redirects=True, trust_env=True)

    try:
        huggingface_hub.set_client_factory(_client_factory)
        if hasattr(huggingface_hub, "close_session"):
            huggingface_hub.close_session()
        print("[Transcriber] Hugging Face client configured with TLS verification disabled")
        return True
    except Exception:
        return False


def _describe_model_load_error(exc: Exception, model_name: str) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()

    snapshot_markers = (
        "snapshot folder",
        "locate the files on the hub",
        "cannot find the appropriate snapshot folder",
    )

    if _looks_like_ssl_error(exc) or any(marker in lowered for marker in snapshot_markers):
        return (
            f"Unable to load model '{model_name}' from Hugging Face or local cache."
        )

    return message


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _candidate_bundled_model_paths(model_name: str) -> list[Path]:
    root = _runtime_root()
    candidates = [
        root / "models" / model_name,
        root / "_internal" / "models" / model_name,
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "models" / model_name)
    return candidates


def _resolve_faster_whisper_model_source(settings: dict, model_name: str) -> tuple[str, str | None]:
    configured_path = (settings.get("model_path") or "").strip()
    if configured_path:
        local_path = Path(configured_path).expanduser()
        if not local_path.exists():
            raise RuntimeError(f"Configured local model path does not exist: {local_path}")
        return str(local_path), f"Using local model files from: {local_path}"

    for candidate in _candidate_bundled_model_paths(model_name):
        if candidate.exists():
            return str(candidate), f"Using bundled local model files from: {candidate}"

    return model_name, None


def _transformers_whisper_model_id(model_name: str) -> str:
    normalized = (model_name or "small").strip()
    if not normalized:
        normalized = "small"
    return f"openai/whisper-{normalized}"


def _resolve_transformers_whisper_model_source(settings: dict, model_name: str) -> tuple[str, str | None]:
    configured_path = (settings.get("model_path") or "").strip()
    if configured_path:
        local_path = Path(configured_path).expanduser()
        if not local_path.exists():
            raise RuntimeError(f"Configured local model path does not exist: {local_path}")
        return str(local_path), f"Using local transformers model files from: {local_path}"

    return _transformers_whisper_model_id(model_name), None


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

    def _append_notice(self, text: str):
        if not text:
            return
        if not self.notice:
            self.notice = text
            return
        if text not in self.notice:
            self.notice = f"{self.notice} {text}"

    def _create_model(self, model_source: str, model_name: str, device: str, compute_type: str):
        from faster_whisper import WhisperModel

        try:
            return WhisperModel(model_source, device=device, compute_type=compute_type)
        except Exception as exc:
            if model_source == model_name and _looks_like_ssl_error(exc) and _configure_hf_insecure_client():
                self._append_notice("Using Hugging Face download fallback with TLS verification disabled.")
                return WhisperModel(model_source, device=device, compute_type=compute_type)
            raise

    def load(self, settings: dict):
        _bootstrap_ca_bundle()

        self._settings = settings
        model_name = settings.get("model", "small")
        model_source, model_notice = _resolve_faster_whisper_model_source(settings, model_name)
        requested_device = _normalize_faster_whisper_device(settings.get("faster_whisper_device"))
        compute_type = settings.get("compute_type", "int8")
        self.notice = None
        self._append_notice(model_notice)

        if requested_device == "auto":
            device = "cuda" if _supports_faster_whisper_cuda() else "cpu"
        else:
            device = requested_device

        if device == "cuda" and not _supports_faster_whisper_cuda():
            self._append_notice("CUDA faster-whisper unavailable. Using CPU faster-whisper instead.")
            device = "cpu"

        effective_compute_type = "float16" if device == "cuda" else compute_type

        print(
            f"[Transcriber] Backend={self.name} model='{model_name}' source='{model_source}' device='{device}' compute='{effective_compute_type}'"
        )
        try:
            self.model = self._create_model(model_source, model_name, device, effective_compute_type)
        except Exception as exc:
            if device != "cuda":
                raise ModelUnavailableError(_describe_model_load_error(exc, model_name)) from exc
            self._append_notice("CUDA faster-whisper failed to load. Using CPU faster-whisper instead.")
            device = "cpu"
            effective_compute_type = compute_type
            print(f"[Transcriber] {self.notice}")
            try:
                self.model = self._create_model(model_source, model_name, device, effective_compute_type)
            except Exception as fallback_exc:
                raise ModelUnavailableError(_describe_model_load_error(fallback_exc, model_name)) from fallback_exc

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


class WhisperXBackend(TranscriptionBackend):
    name = "whisperx"

    def __init__(self):
        self.model = None
        self._settings = {}
        self._device = "cpu"
        self.notice = None
        self.active_name = self.name

    def _append_notice(self, text: str):
        if not text:
            return
        if not self.notice:
            self.notice = text
            return
        if text not in self.notice:
            self.notice = f"{self.notice} {text}"

    def _load_model(
        self,
        whisperx_module,
        model_source: str,
        model_name: str,
        device: str,
        compute_type: str,
        language: str | None,
        beam_size: int,
    ):
        kwargs = {
            "compute_type": compute_type,
            "language": language,
            "asr_options": {
                "beam_size": beam_size,
                "condition_on_prev_text": False,
            },
        }
        try:
            return whisperx_module.load_model(model_source, device, **kwargs)
        except Exception as exc:
            if model_source == model_name and _looks_like_ssl_error(exc) and _configure_hf_insecure_client():
                self._append_notice("Using Hugging Face download fallback with TLS verification disabled.")
                return whisperx_module.load_model(model_source, device, **kwargs)
            raise

    def load(self, settings: dict):
        _bootstrap_ca_bundle()
        try:
            whisperx = importlib.import_module("whisperx")
        except Exception as exc:
            raise RuntimeError("WhisperX backend is not installed.") from exc

        self._settings = settings
        model_name = settings.get("model", "small")
        model_source, model_notice = _resolve_faster_whisper_model_source(settings, model_name)
        requested_device = _normalize_faster_whisper_device(settings.get("faster_whisper_device"))
        compute_type = settings.get("compute_type", "int8")
        language = settings.get("language") or None
        beam_size = settings.get("beam_size", 5)
        batch_size = int(settings.get("whisperx_batch_size", 4) or 4)
        self.notice = None
        self._append_notice(model_notice)

        if requested_device == "auto":
            device = "cuda" if _supports_faster_whisper_cuda() else "cpu"
        else:
            device = requested_device

        if device == "cuda" and not _supports_faster_whisper_cuda():
            self._append_notice("CUDA WhisperX unavailable. Using CPU WhisperX instead.")
            device = "cpu"

        effective_compute_type = "float16" if device == "cuda" else compute_type

        print(
            f"[Transcriber] Backend={self.name} model='{model_name}' source='{model_source}' device='{device}' compute='{effective_compute_type}' batch='{batch_size}'"
        )
        try:
            self.model = self._load_model(
                whisperx_module=whisperx,
                model_source=model_source,
                model_name=model_name,
                device=device,
                compute_type=effective_compute_type,
                language=language,
                beam_size=beam_size,
            )
        except Exception as exc:
            if device != "cuda":
                raise ModelUnavailableError(_describe_model_load_error(exc, model_name)) from exc
            self._append_notice("CUDA WhisperX failed to load. Using CPU WhisperX instead.")
            device = "cpu"
            effective_compute_type = compute_type
            print(f"[Transcriber] {self.notice}")
            try:
                self.model = self._load_model(
                    whisperx_module=whisperx,
                    model_source=model_source,
                    model_name=model_name,
                    device=device,
                    compute_type=effective_compute_type,
                    language=language,
                    beam_size=beam_size,
                )
            except Exception as fallback_exc:
                raise ModelUnavailableError(_describe_model_load_error(fallback_exc, model_name)) from fallback_exc

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
        batch_size = int(self._settings.get("whisperx_batch_size", 4) or 4)
        result = self.model.transcribe(audio.astype(np.float32), batch_size=batch_size, language=language)

        segments = result.get("segments") or []
        text = " ".join((segment.get("text") or "").strip() for segment in segments).strip()
        detected = result.get("language") or language or ""
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


class InsanelyFastWhisperBackend(TranscriptionBackend):
    name = "insanely-fast-whisper"

    def __init__(self):
        self.pipeline = None
        self._settings = {}
        self._device = "cpu"
        self.notice = None
        self.active_name = self.name

    def _append_notice(self, text: str):
        if not text:
            return
        if not self.notice:
            self.notice = text
            return
        if text not in self.notice:
            self.notice = f"{self.notice} {text}"

    def load(self, settings: dict):
        _bootstrap_ca_bundle()
        try:
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
        except Exception as exc:
            raise RuntimeError("insanely-fast-whisper dependencies are not installed.") from exc

        self._settings = settings
        model_name = settings.get("model", "small")
        model_source, model_notice = _resolve_transformers_whisper_model_source(settings, model_name)
        batch_size = int(settings.get("insanely_fast_batch_size", 24) or 24)
        chunk_length = int(settings.get("insanely_fast_chunk_length_s", 30) or 30)
        language = settings.get("language") or None
        beam_size = int(settings.get("beam_size", 5) or 5)
        self.notice = None
        self._append_notice(model_notice)

        if not torch.cuda.is_available():
            raise RuntimeError("insanely-fast-whisper requires CUDA. Select faster-whisper for CPU mode.")

        try:
            importlib.import_module("flash_attn")
            attn_implementation = "flash_attention_2"
            self._append_notice("Using Flash Attention 2.")
        except Exception:
            attn_implementation = "sdpa"
            self._append_notice("Flash Attention 2 is unavailable. Using SDPA attention instead.")

        print(
            f"[Transcriber] Backend={self.name} model='{model_name}' source='{model_source}' device='cuda' batch='{batch_size}' chunk='{chunk_length}' attn='{attn_implementation}'"
        )
        try:
            self.pipeline = transformers.pipeline(
                "automatic-speech-recognition",
                model=model_source,
                torch_dtype=torch.float16,
                device="cuda:0",
                model_kwargs={"attn_implementation": attn_implementation},
            )
        except Exception as exc:
            raise ModelUnavailableError(_describe_model_load_error(exc, model_name)) from exc

        self._device = "cuda"
        self.active_name = f"{self.name} ({self._device})"
        self._pipeline_batch_size = batch_size
        self._chunk_length = chunk_length
        self._generate_kwargs = {"task": "transcribe", "language": language, "num_beams": beam_size}
        if language is None:
            self._generate_kwargs.pop("language")
        print("[Transcriber] Model ready [OK]")

    def unload(self):
        self.pipeline = None
        self.notice = None
        self._device = "cpu"
        self.active_name = self.name

    def transcribe(self, audio: np.ndarray) -> tuple[str, str]:
        if self.pipeline is None:
            raise RuntimeError("Backend not loaded.")
        if audio is None or len(audio) == 0:
            return "", ""

        payload = {"array": audio.astype(np.float32), "sampling_rate": 16000}
        result = self.pipeline(
            payload,
            chunk_length_s=self._chunk_length,
            batch_size=self._pipeline_batch_size,
            generate_kwargs=dict(self._generate_kwargs),
            return_timestamps=False,
        )
        text = (result.get("text") or "").strip()
        detected = self._settings.get("language") or ""
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
            requested_backend = (settings.get("backend") or "").strip().lower()
            if requested_backend == "whisperx":
                candidates.append(("whisperx", WhisperXBackend, dict(settings)))
            elif requested_backend == "insanely-fast-whisper":
                candidates.append(("insanely-fast-whisper", InsanelyFastWhisperBackend, dict(settings)))
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
    BackendOption(key="insanely-fast-whisper", label="Insanely Fast Whisper (CUDA transformers)"),
    BackendOption(key="whisperx", label="WhisperX (experimental live mode)"),
    BackendOption(key="whisper-directml", label="Windows GPU (torch-directml, experimental)"),
    BackendOption(key="faster-whisper", label="faster-whisper (CPU / CUDA)"),
]

_BACKEND_FACTORIES = {
    "auto": AutoBackend,
    "insanely-fast-whisper": InsanelyFastWhisperBackend,
    "whisperx": WhisperXBackend,
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


def _supports_whisperx() -> bool:
    try:
        importlib.import_module("whisperx")
        return True
    except Exception:
        return False


def _supports_insanely_fast_whisper() -> bool:
    try:
        torch = importlib.import_module("torch")
        importlib.import_module("transformers")
        return bool(torch.cuda.is_available())
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
    if backend_name == "insanely-fast-whisper" and not _supports_insanely_fast_whisper():
        return "faster-whisper", "Insanely Fast Whisper requires CUDA, torch, and transformers. Using faster-whisper instead."
    if backend_name == "whisperx" and not _supports_whisperx():
        return "faster-whisper", "WhisperX backend is not installed. Using faster-whisper instead."
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
