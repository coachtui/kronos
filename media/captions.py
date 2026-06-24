"""Build an .srt caption file from ElevenLabs character-level alignment.

The alignment gives parallel arrays of characters and their start/end times.
We group characters into caption cues at sentence boundaries (and at a max
length, breaking on spaces so we never split a word), using the first char's
start and the last char's end as the cue timing.
"""
from __future__ import annotations


def _fmt(t: float | None) -> str:
    ms = max(0, int(round((t or 0.0) * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def alignment_to_srt(alignment: dict, max_chars: int = 80) -> str:
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    n = min(len(chars), len(starts), len(ends))

    cues: list[tuple[float, float, str]] = []
    buf = ""
    cue_start: float | None = None
    cue_end: float | None = None
    prev_nonspace = ""

    def flush():
        nonlocal buf, cue_start, cue_end
        text = buf.strip()
        if text and cue_start is not None:
            cues.append((cue_start, cue_end if cue_end is not None else cue_start, text))
        buf, cue_start, cue_end = "", None, None

    for i in range(n):
        ch = chars[i]
        if cue_start is None and ch.strip() == "":
            continue  # skip leading whitespace of a cue
        if cue_start is None:
            cue_start = starts[i]
        buf += ch
        cue_end = ends[i]
        is_space = ch == " "
        boundary = is_space and (prev_nonspace in ".!?" or len(buf) >= max_chars)
        if ch.strip():
            prev_nonspace = ch
        if boundary:
            flush()
    flush()

    blocks = []
    for idx, (st, en, text) in enumerate(cues, 1):
        blocks.append(f"{idx}\n{_fmt(st)} --> {_fmt(en)}\n{text}\n")
    return "\n".join(blocks)
