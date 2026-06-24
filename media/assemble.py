"""Auto-assemble a draft video from the brief's outputs (Milestone 5).

Inputs (already produced by the pipeline + the charts you pull):
  - {stem}.mp3        voiceover audio (sets the runtime)
  - {stem}.srt        captions (timing + the words to burn in)
  - an images folder  chart screenshots named by ticker (SPY.png, QQQ.png,
                      VIX.png, DXY.png, EWY.png, XLK.png, MU.png, ...).
                      TradingView's "TICKER_date_time.png" names work too.

The "active ticker" drives which chart is on screen: whenever a ticker we have a
chart for is named in the captions, that chart comes up and stays until another
is named. Captions are rendered with Pillow and composited in (no libass/ffmpeg
subtitle filter needed). Output is a DRAFT .mp4 — polish in CapCut.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

W, H, FPS = 1920, 1080, 30
CAP_H = 230  # caption strip height (bottom of frame)

# Tickers we can recognise in a filename, mapped to the words the script uses.
# Keep keywords specific so general words ("tech") don't hijack the active chart.
TICKER_KEYWORDS: dict[str, list[str]] = {
    "SPY": ["spy"],
    "QQQ": ["qqq", "nasdaq"],
    "VIX": ["vix"],
    "DXY": ["dxy", "dollar", "dx-y"],
    "EWY": ["ewy", "korea", "kospi"],
    "XLK": ["xlk", "technology"],
    "MU": ["micron"],
    "SMH": ["smh", "semiconductor"],
    "TNX": ["10-year", "ten-year", "yield"],
}


class AssembleError(RuntimeError):
    pass


def _ts(t: str) -> float:
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    cues = []
    for block in re.split(r"\n\s*\n", path.read_text().strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        m = re.search(r"(\d\d:\d\d:\d\d,\d+)\s*-->\s*(\d\d:\d\d:\d\d,\d+)", lines[1])
        if m:
            cues.append((_ts(m.group(1)), _ts(m.group(2)), " ".join(lines[2:])))
    return cues


def _ticker_for_image(name: str) -> str | None:
    up = re.sub(r"[^A-Z]", "", name.upper())
    for ticker in TICKER_KEYWORDS:
        if ticker in up:
            return ticker
    return None


def _collect_shots(images_dir: Path, cues, duration: float):
    images: dict[str, Path] = {}
    unmatched: list[str] = []
    for img in sorted(images_dir.iterdir()):
        if img.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        ticker = _ticker_for_image(img.stem)
        if ticker and ticker not in images:
            images[ticker] = img
        elif not ticker:
            unmatched.append(img.name)

    if not images:
        raise AssembleError(
            f"No chart images matched a ticker in {images_dir}. Name them by ticker "
            "(e.g. SPY.png, QQQ.png, VIX.png, DXY.png, EWY.png, XLK.png)."
        )

    # active-ticker segmentation: a new shot whenever a different ticker is named
    segs: list[tuple[float, str]] = []
    active = None
    for start, _end, text in cues:
        low = text.lower()
        mentioned = None
        for ticker in images:
            if any(k in low for k in TICKER_KEYWORDS.get(ticker, [ticker.lower()])):
                mentioned = ticker  # last mention in the cue wins
        if mentioned and mentioned != active:
            active = mentioned
            segs.append((start, mentioned))

    if not segs:  # nothing matched in the captions — even split as a fallback
        items = list(images.values())
        seg = duration / len(items)
        shots = [(i * seg, (i + 1) * seg, p) for i, p in enumerate(items)]
        return shots, unmatched

    shots = []
    for i, (st, tk) in enumerate(segs):
        en = segs[i + 1][0] if i + 1 < len(segs) else duration
        if en - st >= 0.5:  # drop blink-length shots
            shots.append((st, en, images[tk]))
    if shots and shots[0][0] > 0:  # no black gap at the open
        shots[0] = (0.0, shots[0][1], shots[0][2])
    return shots, unmatched


# --- captions (Pillow, no external subtitle dependency) ---

def _font(size: int):
    from PIL import ImageFont
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/Library/Fonts/Arial.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def _caption_png(text: str, fontsize: int = 46) -> np.ndarray:
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (W, CAP_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = _font(fontsize)
    max_w = int(W * 0.86)
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    lines = lines[:3]
    line_h = fontsize + 12
    y = CAP_H - len(lines) * line_h - 10
    for ln in lines:
        x = (W - d.textlength(ln, font=font)) // 2
        d.text((x, y), ln, font=font, fill=(255, 255, 255, 255),
               stroke_width=3, stroke_fill=(0, 0, 0, 255))
        y += line_h
    return np.array(img)


def build_video(audio: Path, srt: Path, images_dir: Path, out_path: Path) -> dict:
    from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, ImageClip

    if not audio.exists():
        raise AssembleError(f"missing audio: {audio}")
    if not images_dir.exists():
        raise AssembleError(f"images folder not found: {images_dir}")

    cues = parse_srt(srt) if srt.exists() else []
    audio_clip = AudioFileClip(str(audio))
    duration = audio_clip.duration

    shots, unmatched = _collect_shots(images_dir, cues, duration)

    layers = [ColorClip((W, H), color=(0, 0, 0), duration=duration)]
    for start, end, img in shots:  # charts, letterboxed (never cropped)
        clip = ImageClip(str(img))
        scale = min(W / clip.w, H / clip.h)
        layers.append(clip.resized(scale).with_start(start)
                      .with_duration(max(0.1, end - start)).with_position("center"))

    burned = 0
    for start, end, text in cues:  # captions
        layers.append(ImageClip(_caption_png(text), transparent=True)
                      .with_start(start).with_duration(max(0.1, end - start))
                      .with_position(("center", "bottom")))
        burned += 1

    video = CompositeVideoClip(layers, size=(W, H)).with_audio(audio_clip)
    video.write_videofile(str(out_path), fps=FPS, codec="libx264",
                          audio_codec="aac", logger=None)

    return {
        "out": out_path,
        "shots": [(round(s, 1), round(e, 1), i.name) for s, e, i in shots],
        "unmatched": unmatched,
        "captions": burned,
        "duration": round(duration, 1),
    }
