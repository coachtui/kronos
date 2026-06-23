"""Render the generated content package to the Milestone 3 output files.

Writes, under output/<date>/:
    daily_brief_<date>.md                  long-form segmented script
    daily_brief_<date>_voiceover.txt       clean spoken narration only
    daily_brief_<date>_charts.md           chart callout manifest
    daily_brief_<date>_shorts.md           short-form clip ideas
    daily_brief_<date>_youtube_metadata.md titles / description / pinned / tags / chapters
    daily_brief_<date>_compliance.md       compliance report
"""
from __future__ import annotations

from pathlib import Path

import config


def identity(packet: dict) -> tuple[str, str]:
    """Return (filename_stem, title) for the packet's mode."""
    mode = packet.get("mode", "daily")
    date = packet.get("date")
    if mode == "stock":
        t = packet.get("focus", {}).get("ticker", "TICKER")
        return f"stock_review_{t}_{date}", f"Stock Review — {t} — {date}"
    if mode == "earnings":
        t = packet.get("focus", {}).get("ticker", "TICKER")
        return f"earnings_{t}_{date}", f"Earnings — {t} — {date}"
    if mode == "macro":
        slug = packet.get("event_slug", "event")
        return f"macro_event_{slug}_{date}", f"Macro Event — {packet.get('event', '')} — {date}"
    return f"daily_brief_{date}", f"Daily Market Brief — {date}"


def _script_md(title: str, pkg: dict) -> str:
    thesis = pkg.get("thesis", {})
    return (
        f"# {title}\n\n"
        f"_Thesis: **{thesis.get('stance', 'n/a')}** — {thesis.get('conditions', '')}_\n\n"
        f"{pkg['long_form_script'].strip()}\n"
    )


def _charts_md(date: str, pkg: dict) -> str:
    lines = [f"# Chart Callout Manifest — {date}\n",
             "Pull these manually from TradingView and place them per segment.\n"]
    for i, c in enumerate(pkg.get("charts", []), 1):
        lines.append(
            f"[CHART {i}]\n"
            f"Ticker: {c.get('ticker', '')}\n"
            f"Timeframe: {c.get('timeframe', '')}\n"
            f"Segment: {c.get('segment', '')}\n"
            f"Focus: {c.get('focus', '')}\n"
            f"Suggested overlays: {c.get('overlays', '')}\n"
            f"Why it matters: {c.get('why_it_matters', '')}\n"
        )
    return "\n".join(lines)


def _shorts_md(date: str, pkg: dict) -> str:
    lines = [f"# Short-Form Clip Ideas — {date}\n"]
    for i, s in enumerate(pkg.get("shorts", []), 1):
        lines.append(
            f"## Clip {i}: {s.get('title', '')}\n"
            f"- **Hook:** {s.get('hook', '')}\n"
            f"- **Window:** {s.get('start_timestamp', '')} – {s.get('end_timestamp', '')}\n"
            f"- **Spoken excerpt:** {s.get('spoken_excerpt', '')}\n"
            f"- **Caption:** {s.get('caption', '')}\n"
            f"- **Visual:** {s.get('visual', '')}\n"
            f"- **Platform note:** {s.get('platform_note', '')}\n"
        )
    return "\n".join(lines)


def _metadata_md(date: str, pkg: dict) -> str:
    m = pkg.get("youtube_metadata", {})
    titles = "\n".join(f"{i}. {t}" for i, t in enumerate(m.get("title_options", []), 1))
    hashtags = " ".join(m.get("hashtags", []))
    chapters = "\n".join(f"{c.get('timestamp', '')} {c.get('label', '')}"
                         for c in m.get("chapters", []))
    return (
        f"# YouTube Metadata — {date}\n\n"
        f"## Title options\n{titles}\n\n"
        f"## Recommended title\n{m.get('recommended_title', '')}\n\n"
        f"## Description\n{m.get('description', '')}\n\n"
        f"## Pinned comment\n{m.get('pinned_comment', '')}\n\n"
        f"## Hashtags\n{hashtags}\n\n"
        f"## Chapters\n{chapters}\n\n"
        f"## Disclaimer\n{config.FULL_DISCLAIMER}\n"  # full written disclaimer, verbatim
    )


def _voiceover_txt(pkg: dict) -> str:
    """Clean spoken narration with the short spoken disclaimer appended verbatim.

    Claude is told not to write a disclaimer in the voiceover field; if one slips
    through containing the canonical text, we don't double it.
    """
    body = pkg["voiceover"].strip()
    if config.SPOKEN_DISCLAIMER not in body:
        body = f"{body}\n\n{config.SPOKEN_DISCLAIMER}"
    return body + "\n"


def _compliance_md(date: str, report: dict) -> str:
    lines = [
        f"# Compliance Report — {date}\n",
        f"**Status:** {report.get('status', '').upper()}",
        f"**Final recommendation:** {report.get('final_recommendation', '').upper()}",
        f"**Sources:** {', '.join(report.get('sources', []))}",
        f"\n_{report.get('notes', '')}_\n",
        "## Flagged lines\n",
    ]
    flags = report.get("flagged_lines", [])
    if not flags:
        lines.append("None — no compliance issues detected.\n")
    for i, f in enumerate(flags, 1):
        lines.append(
            f"{i}. **{f.get('reason', '')}**\n"
            f"   - Line: `{f.get('line', '')}`\n"
            f"   - Suggested rewrite: {f.get('suggested_rewrite', '')}\n"
        )
    return "\n".join(lines)


def write_package(packet: dict, package: dict, compliance: dict) -> dict[str, Path]:
    """Write all content-package files for the packet's mode. Returns {label: path}."""
    date = packet.get("date")
    stem, title = identity(packet)
    out_dir = config.OUTPUT_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "script": (out_dir / f"{stem}.md", _script_md(title, package)),
        "voiceover": (out_dir / f"{stem}_voiceover.txt", _voiceover_txt(package)),
        "charts": (out_dir / f"{stem}_charts.md", _charts_md(date, package)),
        "shorts": (out_dir / f"{stem}_shorts.md", _shorts_md(date, package)),
        "metadata": (out_dir / f"{stem}_youtube_metadata.md", _metadata_md(date, package)),
        "compliance": (out_dir / f"{stem}_compliance.md", _compliance_md(date, compliance)),
    }
    written = {}
    for label, (path, content) in files.items():
        path.write_text(content)
        written[label] = path
    return written
