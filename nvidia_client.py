"""
NVIDIA NIM API Client
Handles all communication with NVIDIA's AI inference endpoints.
"""

import os
import base64
import httpx
import asyncio
from typing import Optional

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "your-nvidia-api-key-here")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
ASR_BASE_URL    = "https://ai.api.nvidia.com/v1/asr/nvidia/parakeet-ctc-1.1b"
RIVA_BASE_URL   = "https://ai.api.nvidia.com/v1/nvidia"


class NVIDIAClient:
    """Unified client for NVIDIA NIM speech and language APIs."""

    def __init__(self):
        self.api_key = NVIDIA_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ── Speech-to-text (Parakeet ASR NIM) ────────────────────────────────────
    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav") -> dict:
        """
        Transcribe audio using NVIDIA Parakeet ASR NIM.
        Falls back to Whisper-compatible endpoint if Parakeet unavailable.
        """
        try:
            return await self._transcribe_parakeet(audio_bytes, filename)
        except Exception:
            return await self._transcribe_whisper_compat(audio_bytes, filename)

    async def _transcribe_parakeet(self, audio_bytes: bytes, filename: str) -> dict:
        """Use NVIDIA Parakeet CTC 1.1B for ASR."""
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {
            "audio": audio_b64,
            "language_code": "en-US",
            "encoding": "LINEAR_PCM",
            "sample_rate_hertz": 16000,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{RIVA_BASE_URL}/parakeet-ctc-1.1b/asr",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "text": data.get("transcript", ""),
                "confidence": data.get("confidence", 1.0),
                "words": data.get("words", []),
                "speaker": data.get("speaker_tag", "Unknown"),
            }

    async def _transcribe_whisper_compat(self, audio_bytes: bytes, filename: str) -> dict:
        """
        Whisper-compatible transcription via NVIDIA NIM.
        (Used as fallback or when running locally with NIM containers.)
        """
        import io
        async with httpx.AsyncClient(timeout=120) as client:
            files = {"file": (filename, io.BytesIO(audio_bytes), "audio/wav")}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await client.post(
                f"{NVIDIA_BASE_URL}/audio/transcriptions",
                headers=headers,
                files=files,
                data={"model": "whisper-large-v3", "language": "en"},
            )
            response.raise_for_status()
            data = response.json()
            return {
                "text": data.get("text", ""),
                "confidence": 1.0,
                "words": [],
                "speaker": "Unknown",
            }

    # ── LLM (Llama 3.1 70B / Mistral via NVIDIA NIM) ─────────────────────────
    async def chat_complete(
        self,
        messages: list[dict],
        model: str = "meta/llama-3.1-70b-instruct",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str:
        """
        Call NVIDIA-hosted LLM via the OpenAI-compatible /chat/completions endpoint.
        Available models on build.nvidia.com:
          - meta/llama-3.1-70b-instruct  (best quality)
          - meta/llama-3.1-8b-instruct   (faster, free tier)
          - mistralai/mixtral-8x7b-instruct-v0.1
          - mistralai/mistral-7b-instruct-v0.3
          - microsoft/phi-3-medium-128k-instruct
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{NVIDIA_BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def embed(self, texts: list[str], model: str = "nvidia/nv-embedqa-e5-v5") -> list[list[float]]:
        """Get embeddings via NVIDIA NIM embedding model."""
        payload = {"input": texts, "model": model, "input_type": "query"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{NVIDIA_BASE_URL}/embeddings",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    # ── Riva speaker diarization ──────────────────────────────────────────────
    async def diarize(self, audio_bytes: bytes, num_speakers: Optional[int] = None) -> dict:
        """
        Speaker diarization: who spoke when.
        Uses NVIDIA Riva diarization if available, else returns mock data.
        """
        try:
            audio_b64 = base64.b64encode(audio_bytes).decode()
            payload = {
                "audio": audio_b64,
                "num_speakers": num_speakers,
                "encoding": "LINEAR_PCM",
                "sample_rate_hertz": 16000,
            }
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    f"{RIVA_BASE_URL}/diarization",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except Exception:
            # Graceful fallback — diarization is optional
            return {"segments": [], "speakers": []}
