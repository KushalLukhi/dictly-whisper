"""
recorder.py — Mic capture using sounddevice.
Exposes waveform_callback for live visualization.
"""

import threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
MAX_RECORD_SECONDS = 60


class AudioRecorder:
    def __init__(self, waveform_callback=None):
        self.recording = False
        self.frames = []
        self._lock = threading.Lock()
        self._stream = None
        self.waveform_callback = waveform_callback  # called with each chunk (np array)

    def start(self):
        with self._lock:
            if self.recording:
                return
            self.frames = []
            self.recording = True

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=self._callback,
            blocksize=1024,
        )
        self._stream.start()
        print("[Recorder] Recording started")

    def stop(self) -> tuple[np.ndarray | None, float]:
        """Returns (audio_array, duration_seconds)."""
        with self._lock:
            if not self.recording:
                return None, 0.0
            self.recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self.frames:
            return None, 0.0

        audio = np.concatenate(self.frames, axis=0).flatten()
        duration = len(audio) / SAMPLE_RATE
        print(f"[Recorder] Stopped - {duration:.1f}s captured")
        return audio, duration

    def _callback(self, indata, frames, time, status):
        if status:
            print(f"[Recorder] Stream status: {status}")
        if self.recording:
            chunk = indata.copy()
            self.frames.append(chunk)
            if self.waveform_callback:
                self.waveform_callback(chunk.flatten())
            total = sum(len(f) for f in self.frames)
            if total >= SAMPLE_RATE * MAX_RECORD_SECONDS:
                self.recording = False
