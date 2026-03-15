"""
Audio Capture Module
Cross-platform audio capture for Google Meet, Zoom, Teams.
Works by recording system audio (loopback) + microphone simultaneously.

Platform notes:
  Windows → VB-Cable virtual device (free) routes meeting audio to capture
  macOS   → BlackHole 2ch routes system audio (free from existential.audio)
  Linux   → PulseAudio null-sink for loopback
"""

import io
import time
import wave
import queue
import struct
import asyncio
import threading
import tempfile
from pathlib import Path
from typing import Optional, Callable


# ── Lightweight capture with sounddevice ──────────────────────────────────────
class AudioCapture:
    """
    Captures audio from the default input device (mic + loopback if configured).
    Sends chunks every `chunk_seconds` seconds via the `on_chunk` callback.
    """

    SAMPLE_RATE   = 16000   # Parakeet ASR expects 16 kHz
    CHANNELS      = 1       # Mono
    SAMPLE_WIDTH  = 2       # 16-bit PCM
    CHUNK_SECONDS = 5       # Emit a chunk every N seconds

    def __init__(
        self,
        chunk_seconds: int = 5,
        on_chunk: Optional[Callable[[bytes], None]] = None,
        device_index: Optional[int] = None,
    ):
        self.chunk_seconds = chunk_seconds
        self.on_chunk = on_chunk
        self.device_index = device_index
        self._recording = False
        self._frames: list[bytes] = []
        self._chunk_frames: list[bytes] = []
        self._thread: Optional[threading.Thread] = None
        self._chunk_queue: queue.Queue = queue.Queue()

    # ── Public interface ──────────────────────────────────────────────────────
    def start(self):
        """Start background recording thread."""
        self._recording = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self) -> bytes:
        """Stop recording and return the complete WAV bytes."""
        self._recording = False
        if self._thread:
            self._thread.join(timeout=5)
        return self._build_wav(self._frames)

    def get_next_chunk(self, timeout: float = 6.0) -> Optional[bytes]:
        """Block until the next chunk is ready, then return its WAV bytes."""
        try:
            return self._chunk_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices."""
        try:
            import sounddevice as sd
            devices = []
            for i, dev in enumerate(sd.query_devices()):
                if dev["max_input_channels"] > 0:
                    devices.append({"index": i, "name": dev["name"],
                                    "channels": dev["max_input_channels"]})
            return devices
        except Exception:
            return []

    # ── Recording loop (sounddevice) ──────────────────────────────────────────
    def _record_loop(self):
        try:
            import sounddevice as sd
            import numpy as np

            chunk_size = self.SAMPLE_RATE * self.chunk_seconds
            chunk_buf: list[bytes] = []
            chunk_frame_count = 0

            def callback(indata, frames, time_info, status):
                nonlocal chunk_frame_count
                # Convert float32 → int16 PCM
                audio_int16 = (indata[:, 0] * 32767).astype("int16")
                raw = audio_int16.tobytes()

                self._frames.append(raw)
                chunk_buf.append(raw)
                chunk_frame_count += frames

                if chunk_frame_count >= chunk_size:
                    wav_bytes = self._build_wav(chunk_buf[:])
                    self._chunk_queue.put(wav_bytes)
                    if self.on_chunk:
                        self.on_chunk(wav_bytes)
                    chunk_buf.clear()
                    chunk_frame_count = 0

            kw = dict(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype="float32",
                callback=callback,
            )
            if self.device_index is not None:
                kw["device"] = self.device_index

            with sd.InputStream(**kw):
                while self._recording:
                    time.sleep(0.1)

            # Flush remaining frames as final chunk
            if chunk_buf:
                wav_bytes = self._build_wav(chunk_buf)
                self._chunk_queue.put(wav_bytes)

        except ImportError:
            # sounddevice not installed — fall back to silence generator (testing only)
            self._silence_loop()

    def _silence_loop(self):
        """Fallback: generate silence for testing without a mic."""
        silence = b"\x00\x00" * self.SAMPLE_RATE  # 1 s of silence
        while self._recording:
            for _ in range(self.chunk_seconds):
                self._frames.append(silence)
            wav = self._build_wav([silence] * self.chunk_seconds)
            self._chunk_queue.put(wav)
            time.sleep(self.chunk_seconds)

    # ── WAV builder ───────────────────────────────────────────────────────────
    def _build_wav(self, frames: list[bytes]) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.SAMPLE_WIDTH)
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    @staticmethod
    def save_wav(wav_bytes: bytes, path: str):
        Path(path).write_bytes(wav_bytes)


# ── Async wrapper for FastAPI ─────────────────────────────────────────────────
class AsyncAudioCapture:
    """Wraps AudioCapture with an async API for use inside FastAPI endpoints."""

    def __init__(self, session_id: str, chunk_seconds: int = 5):
        self.session_id = session_id
        self._capture = AudioCapture(chunk_seconds=chunk_seconds)
        self._active = False

    async def start(self):
        self._capture.start()
        self._active = True

    async def stop(self) -> bytes:
        self._active = False
        return await asyncio.get_event_loop().run_in_executor(None, self._capture.stop)

    async def next_chunk(self) -> Optional[bytes]:
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._capture.get_next_chunk(timeout=7.0)
        )

    @property
    def is_active(self) -> bool:
        return self._active


# ── Platform setup guide (printed at import) ──────────────────────────────────
PLATFORM_SETUP = """
╔══════════════════════════════════════════════════════════════╗
║          Audio Loopback Setup (One-time, per platform)       ║
╠══════════════════════════════════════════════════════════════╣
║  Windows: Install VB-Cable (https://vb-audio.com/Cable/)     ║
║           Set "CABLE Output" as default playback device       ║
║           Set device_index to CABLE Output index             ║
╠══════════════════════════════════════════════════════════════╣
║  macOS:   Install BlackHole 2ch (existential.audio)          ║
║           Create Multi-Output Device in Audio MIDI Setup      ║
║           Route to BlackHole + your speakers                  ║
╠══════════════════════════════════════════════════════════════╣
║  Linux:   pactl load-module module-null-sink sink_name=meet  ║
║           pactl load-module module-loopback source=meet.mon  ║
╚══════════════════════════════════════════════════════════════╝
"""


if __name__ == "__main__":
    print(PLATFORM_SETUP)
    print("Available audio devices:")
    for d in AudioCapture.list_devices():
        print(f"  [{d['index']}] {d['name']} ({d['channels']} ch)")
