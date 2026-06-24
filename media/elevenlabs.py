"""ElevenLabs text-to-speech (Milestone 4).

Uses the with-timestamps endpoint so a single call returns both the audio and
per-character timing — the timing feeds the .srt caption builder. Raw HTTP (no
SDK) for stability and control. Degrades gracefully: a missing key/voice raises
a clear error the caller turns into a skip, never a crash.
"""
from __future__ import annotations

import base64

import config

_BASE = "https://api.elevenlabs.io/v1"


class MissingVoiceConfigError(RuntimeError):
    """ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID is not set."""


def is_configured() -> bool:
    return bool(config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE_ID)


def synthesize(text: str, voice_id: str | None = None, api_key: str | None = None) -> dict:
    """Return {"audio": bytes, "alignment": {...}} for the given text.

    Raises MissingVoiceConfigError if not configured; lets request errors
    propagate for the caller to handle.
    """
    api_key = api_key or config.ELEVENLABS_API_KEY
    voice_id = voice_id or config.ELEVENLABS_VOICE_ID
    if not api_key:
        raise MissingVoiceConfigError(
            "ELEVENLABS_API_KEY is not set. Add it to .env.local to enable voiceover."
        )
    if not voice_id:
        raise MissingVoiceConfigError(
            "ELEVENLABS_VOICE_ID is not set. Pick a voice in ElevenLabs and add its "
            "ID to .env.local."
        )

    import requests

    url = f"{_BASE}/text-to-speech/{voice_id}/with-timestamps"
    payload = {
        "text": text,
        "model_id": config.ELEVENLABS_MODEL,
        "output_format": config.ELEVENLABS_OUTPUT_FORMAT,
    }
    resp = requests.post(
        url,
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    audio = base64.b64decode(data["audio_base64"])
    alignment = data.get("alignment") or data.get("normalized_alignment") or {}
    return {"audio": audio, "alignment": alignment}
