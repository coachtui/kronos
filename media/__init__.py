"""Media layer (Milestone 4): voiceover audio + captions."""
from __future__ import annotations

from pathlib import Path

from media import captions
from media import elevenlabs as tts
from media.elevenlabs import MissingVoiceConfigError, is_configured

__all__ = ["generate_voiceover", "MissingVoiceConfigError", "is_configured"]


def generate_voiceover(voiceover_text: str, out_dir: Path, stem: str) -> dict[str, Path]:
    """Synthesize the voiceover and write {stem}.mp3 + {stem}.srt.

    Returns {"mp3": path, "srt": path, "chars": n}. Raises MissingVoiceConfigError
    if not configured (caller handles the skip); request errors propagate.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    result = tts.synthesize(voiceover_text)

    mp3_path = out_dir / f"{stem}.mp3"
    mp3_path.write_bytes(result["audio"])

    srt_path = out_dir / f"{stem}.srt"
    srt_path.write_text(captions.alignment_to_srt(result["alignment"]))

    return {"mp3": mp3_path, "srt": srt_path, "chars": len(voiceover_text)}
