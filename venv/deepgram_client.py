"""
Deepgram Real-Time Transcription Client
Captures audio from VB-Cable / microphone and transcribes live
Works with Google Meet, Zoom, Discord, Teams
"""

import os
import json
import asyncio
import threading
import websockets
import base64
from typing import Callable, Optional

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


class DeepgramClient:
    """Real-time streaming transcription via Deepgram WebSocket API"""

    def __init__(self):
        self.api_key = DEEPGRAM_API_KEY
        self._ws = None
        self._running = False
        self._transcript_callback: Optional[Callable] = None
        self._full_transcript = []

    # ── Start live transcription ──────────────────────────────────────────────
    async def start_streaming(
        self,
        on_transcript: Callable[[str, str, bool], None],
        language: str = "en",
        device_index: Optional[int] = None,
    ):
        """
        Start capturing audio and streaming to Deepgram.
        on_transcript(speaker, text, is_final) called for each result.
        language: en, hi, multi etc.
        """
        self._running = True
        self._transcript_callback = on_transcript
        self._full_transcript = []

        # Build Deepgram URL with params
        params = [
            "model=nova-2",
            f"language={language}",
            "smart_format=true",
            "diarize=true",
            "punctuate=true",
            "interim_results=true",
            "utterance_end_ms=1000",
            "encoding=linear16",
            "sample_rate=16000",
            "channels=1",
        ]
        url = f"{DEEPGRAM_WS_URL}?{'&'.join(params)}"

        headers = {"Authorization": f"Token {self.api_key}"}

        try:
            async with websockets.connect(url, extra_headers=headers) as ws:
                self._ws = ws

                # Start audio capture in separate thread
                audio_thread = threading.Thread(
                    target=self._capture_audio,
                    args=(ws, device_index),
                    daemon=True
                )
                audio_thread.start()

                # Listen for transcription results
                async for message in ws:
                    if not self._running:
                        break
                    try:
                        data = json.loads(message)
                        await self._handle_message(data)
                    except Exception:
                        pass

        except Exception as e:
            raise Exception(f"Deepgram connection failed: {e}")

    async def _handle_message(self, data: dict):
        """Process Deepgram response and call transcript callback"""
        msg_type = data.get("type", "")

        if msg_type == "Results":
            channel = data.get("channel", {})
            alternatives = channel.get("alternatives", [])
            if not alternatives:
                return

            transcript = alternatives[0].get("transcript", "").strip()
            if not transcript:
                return

            is_final = data.get("is_final", False)

            # Get speaker from diarization
            words = alternatives[0].get("words", [])
            speaker = "Unknown"
            if words:
                speaker_num = words[0].get("speaker", 0)
                speaker = f"Speaker {speaker_num + 1}"

            if self._transcript_callback:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._transcript_callback(speaker, transcript, is_final)
                )

            if is_final:
                self._full_transcript.append(f"{speaker}: {transcript}")

        elif msg_type == "Metadata":
            pass  # Connection established
        elif msg_type == "Error":
            error = data.get("message", "Unknown error")
            raise Exception(f"Deepgram error: {error}")

    def _capture_audio(self, ws, device_index: Optional[int]):
        """Capture audio from system/microphone and send to Deepgram"""
        try:
            import sounddevice as sd
            import numpy as np

            SAMPLE_RATE = 16000
            CHUNK_SIZE = 3200  # 0.2 seconds of audio

            def audio_callback(indata, frames, time_info, status):
                if not self._running:
                    return
                audio_int16 = (indata[:, 0] * 32767).astype("int16")
                raw_bytes = audio_int16.tobytes()
                # Send audio bytes to Deepgram via WebSocket
                try:
                    asyncio.run_coroutine_threadsafe(
                        ws.send(raw_bytes),
                        asyncio.get_event_loop()
                    )
                except Exception:
                    pass

            kw = dict(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=CHUNK_SIZE,
                callback=audio_callback,
            )
            if device_index is not None:
                kw["device"] = device_index

            with sd.InputStream(**kw):
                while self._running:
                    import time
                    time.sleep(0.1)

        except ImportError:
            # sounddevice not available — use silence for testing
            import time
            while self._running:
                time.sleep(1)
        except Exception as e:
            pass

    async def stop(self):
        """Stop transcription and return full transcript"""
        self._running = False
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await self._ws.close()
            except Exception:
                pass
        return "\n".join(self._full_transcript)

    def get_transcript(self) -> str:
        return "\n".join(self._full_transcript)

    @staticmethod
    def list_audio_devices() -> list[dict]:
        """List available audio input devices"""
        try:
            import sounddevice as sd
            devices = []
            for i, dev in enumerate(sd.query_devices()):
                if dev["max_input_channels"] > 0:
                    devices.append({
                        "index": i,
                        "name": dev["name"],
                        "channels": dev["max_input_channels"],
                    })
            return devices
        except Exception:
            return []

    @staticmethod
    def find_vbcable_device() -> Optional[int]:
        """Auto-detect VB-Cable device index"""
        try:
            import sounddevice as sd
            for i, dev in enumerate(sd.query_devices()):
                name = dev["name"].lower()
                if ("cable" in name or "vb-audio" in name or "vb audio" in name or
                        "blackhole" in name or "loopback" in name):
                    if dev["max_input_channels"] > 0:
                        return i
        except Exception:
            pass
        return None

    @staticmethod
    def get_language_code(language_name: str) -> str:
        """Convert display language to Deepgram language code"""
        mapping = {
            "English": "en",
            "Hindi": "hi",
            "Hindi + English (Hinglish)": "hi",
            "Hindi + English": "hi",
            "Auto-detect": "en",
            "Multiple / Auto-detect": "en",
            "Tamil + English": "ta",
            "Marathi + English": "mr",
        }
        return mapping.get(language_name, "en")