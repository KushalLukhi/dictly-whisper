"""
main.py — Dictly entry point.
Wires together keyboard listener, recorder, transcriber, UI and tray.
"""

import logging
import sys
import threading
import time
from pynput import keyboard

import config_manager
import history_manager
from app import DictlyApp
from recorder import AudioRecorder
from runtime_logging import configure_logging, get_log_file
from transcriber import Transcriber
from tray import TrayIcon
from typer import output_text
from transcription_backends import ModelUnavailableError

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self):
        self.settings = config_manager.load()
        self.recorder = AudioRecorder(waveform_callback=self._on_waveform)
        self.transcriber = Transcriber()
        self.app: DictlyApp = None
        self.tray: TrayIcon = None

        self._held_keys: set = set()
        self._recording = False
        self._transcribing = False
        self._lock = threading.Lock()

        # Build pynput key set from settings
        self._required_keys = self._parse_hotkey(self.settings.get("hotkey", ["ctrl", "shift"]))

    def _parse_hotkey(self, keys: list) -> set:
        mapping = {
            "ctrl":  keyboard.Key.ctrl_l,
            "shift": keyboard.Key.shift,
            "alt":   keyboard.Key.alt,
            "cmd":   keyboard.Key.cmd,
        }
        return {mapping[k] for k in keys if k in mapping}

    # ── Waveform callback (from recorder thread) ───────────────────────────

    def _on_waveform(self, chunk):
        if self.app:
            self.app.push_waveform(chunk)

    # ── Keyboard events ────────────────────────────────────────────────────

    def _on_press(self, key):
        self._held_keys.add(key)
        if self._required_keys.issubset(self._held_keys):
            with self._lock:
                if not self._recording and not self._transcribing:
                    self._recording = True
                    self.recorder.start()
                    if self.app:
                        self.app.set_status("recording")
                        self.app.start_waveform()
                    if self.tray:
                        self.tray.set_state("recording")

    def _on_release(self, key):
        self._held_keys.discard(key)
        if key in self._required_keys and self._recording:
            with self._lock:
                self._recording = False
                self._transcribing = True
            if self.app:
                self.app.set_status("transcribing")
                self.app.stop_waveform()
            if self.tray:
                self.tray.set_state("transcribing")
            threading.Thread(target=self._transcribe_and_paste, daemon=True).start()

    def _transcribe_and_paste(self):
        try:
            audio, duration = self.recorder.stop()
            if audio is not None and len(audio) > 0:
                text, lang = self.transcriber.transcribe(audio)
                if text:
                    time.sleep(0.15)
                    output_text(text, self.settings)
                    history_manager.add(text, duration, lang)
                    if self.app:
                        self.app.set_result(text)
                        self.app.set_status("done")
                else:
                    logger.warning("Transcription returned empty text.")
                    if self.app:
                        self.app.set_notice(f"No transcription result. See log: {get_log_file()}")
                        self.app.set_status("idle")
            else:
                logger.warning("Recorder returned empty audio.")
                if self.app:
                    self.app.set_notice(f"No audio captured. See log: {get_log_file()}")
                    self.app.set_status("idle")
        except Exception:
            message = "Transcription failed. See log: {log_file}".format(log_file=get_log_file())
            exc = sys.exc_info()[1]
            if isinstance(exc, RuntimeError) and str(exc) == "Model not loaded.":
                message = "Model is not loaded. Choose a Local Model Directory in Settings."
                logger.warning("Transcription requested before a local model was loaded.")
                if self.app:
                    self.app.set_notice(message)
                    self.app.set_status("idle")
            else:
                logger.exception("Transcription pipeline failed.")
                if self.app:
                    self.app.set_notice(message)
                    self.app.set_status("error")

        with self._lock:
            self._transcribing = False

        time.sleep(1.5)
        if self.app:
            self.app.set_status("idle")
        if self.tray:
            self.tray.set_state("idle")

    # ── Settings reload ────────────────────────────────────────────────────

    def reload_settings(self, new_settings: dict):
        self.settings = new_settings
        self._required_keys = self._parse_hotkey(new_settings.get("hotkey", ["ctrl", "shift"]))
        if self.app:
            self.app.set_status("loading")
        threading.Thread(target=self._reload_model, daemon=True).start()

    def _reload_model(self):
        try:
            self.transcriber.reload(self.settings)
            if self.app:
                self.app.set_runtime_info(
                    requested_backend=self.settings.get("backend"),
                    active_backend=self.transcriber.get_active_backend(),
                    settings=self.settings,
                )
                self.app.set_notice(self.transcriber.get_notice())
                self.app.set_status("idle")
        except ModelUnavailableError as exc:
            print(f"[Dictly] {exc}")
            if self.app:
                self.app.set_runtime_info(
                    requested_backend=self.settings.get("backend"),
                    active_backend="Not loaded",
                    settings=self.settings,
                )
                self.app.set_notice(str(exc))
                self.app.set_status("idle")
        except Exception as exc:
            logger.exception("Failed to reload backend.")
            print(f"[Dictly] Failed to reload backend: {exc}")
            if self.app:
                self.app.set_notice(f"Backend reload failed. See log: {get_log_file()}")
                self.app.set_status("error")

    # ── Startup ────────────────────────────────────────────────────────────

    def run(self):
        print("=" * 48)
        print("  Dictly - Local AI Dictation")
        print("=" * 48)

        # Load Whisper model in background so UI shows immediately
        def load_model():
            try:
                self.app.set_status("loading")
                self.transcriber.load(self.settings)
                self.app.set_runtime_info(
                    requested_backend=self.settings.get("backend"),
                    active_backend=self.transcriber.get_active_backend(),
                    settings=self.settings,
                )
                self.app.set_notice(self.transcriber.get_notice())
                self.app.set_status("idle")
                print("  [OK] Hold hotkey to dictate anywhere.")
            except ModelUnavailableError as exc:
                print(f"[Dictly] {exc}")
                self.app.set_runtime_info(
                    requested_backend=self.settings.get("backend"),
                    active_backend="Not loaded",
                    settings=self.settings,
                )
                self.app.set_notice(str(exc))
                self.app.set_status("idle")
            except Exception as exc:
                logger.exception("Failed to load backend.")
                print(f"[Dictly] Failed to load backend: {exc}")
                self.app.set_notice(f"Backend load failed. See log: {get_log_file()}")
                self.app.set_status("error")

        # Build tray
        self.tray = TrayIcon(
            on_show=lambda: self.app.show() if self.app else None,
            on_quit=self._quit,
        )
        self.tray.start()

        # Build CTk app (must run on main thread)
        self.app = DictlyApp(engine=self)

        # Start keyboard listener in background
        listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        listener.daemon = True
        listener.start()

        # Load model in background
        threading.Thread(target=load_model, daemon=True).start()

        # Run CTk main loop (blocking)
        self.app.mainloop()

    def _quit(self):
        print("[Dictly] Quitting...")
        if self.tray:
            self.tray.stop()
        sys.exit(0)


if __name__ == "__main__":
    configure_logging()
    Engine().run()
