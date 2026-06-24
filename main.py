"""kronos-brief CLI — mode-based content engine (Milestone 3, revised).

Two steps, so audio is never charged by accident:
    1. generate the TEXT package (free of ElevenLabs), review/approve it
    2. `voice` it once to produce the .mp3 + .srt

Modes:
    daily     broad daily market brief (default)
    stock     individual stock review
    earnings  earnings preview / reaction
    macro     macro-event video
    voice     generate audio (.mp3 + .srt) from an already-approved voiceover.txt
    weekly    longer weekly review (future — not implemented yet)

Preferred CLI:
    python main.py daily                       # 1) build the text package
    python main.py voice                       # 2) voice today's daily brief
    python main.py stock NVDA
    python main.py voice --file output/DATE/stock_review_NVDA_DATE_voiceover.txt
    python main.py earnings NVDA --event "earnings preview"
    python main.py macro --event "FOMC decision"
    python main.py validate

Backward-compatible flag form (no subcommand):
    python main.py --no-audio                 -> daily brief
    python main.py --stock NVDA --no-audio    -> separate stock review (NOT in daily)
    python main.py --macro --no-audio         -> daily brief with macro section
    python main.py --macro --event X          -> separate macro-event video

Audio (.mp3) + captions (.srt) come from the separate `voice` step. No posting yet.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import config
from editorial import brief_generator, compliance, content_package
from providers import get_provider
from signals import packet as pb
from signals import validation

MODES = {"daily", "stock", "earnings", "macro", "weekly", "validate", "voice"}


def _parse(rest) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="main.py", description="kronos-brief content engine")
    p.add_argument("ticker", nargs="?", help="ticker for stock/earnings modes")
    p.add_argument("--event", help="event label (macro / earnings modes)")
    p.add_argument("--stock", metavar="TICKER", help="[flag form] generate a stock review")
    p.add_argument("--macro", action="store_true", help="[flag form] macro section / macro mode")
    p.add_argument("--no-audio", action="store_true", help="(generation is text-only by default; kept for compatibility)")
    p.add_argument("--from-fixture", metavar="PATH", help="load a saved packet instead of live fetch")
    p.add_argument("--validate", action="store_true", help="reconcile past forecasts with actuals")
    p.add_argument("--date", help="date (YYYY-MM-DD) for the `voice` command (default: today)")
    p.add_argument("--file", metavar="PATH", help="explicit voiceover .txt for the `voice` command")
    return p.parse_args(rest)


def _resolve(argv):
    """Return (mode, ticker, event, args). Supports subcommands and flag form."""
    if argv and argv[0] in MODES:
        mode, rest = argv[0], argv[1:]
    else:
        mode, rest = None, argv
    args = _parse(rest)

    if mode == "validate" or args.validate:
        return "validate", None, None, args

    if mode is None:  # flag form / default
        if args.stock:
            return "stock", args.stock.upper(), args.event, args
        if args.macro and args.event:
            return "macro", None, args.event, args
        return "daily", None, None, args

    ticker = (args.ticker or "").upper() or None
    return mode, ticker, args.event, args


def _build_packet(mode, ticker, event, args, provider):
    if args.from_fixture:
        print(f"[packet] loading fixture {args.from_fixture} ...")
        return json.loads(Path(args.from_fixture).read_text())

    print(f"[packet] building {mode} packet via {provider.name} ...")
    if mode == "daily":
        pkt, path = pb.build_daily(provider, macro_enabled=args.macro)
    elif mode == "stock":
        pkt, path = pb.build_stock(provider, ticker)
    elif mode == "earnings":
        pkt, path = pb.build_earnings(provider, ticker, event=event or "earnings preview")
    elif mode == "macro":
        pkt, path = pb.build_macro(provider, event)
    else:
        raise ValueError(mode)
    print(f"[packet] saved -> {path}")
    return pkt


def _print_summary(written, report) -> None:
    print("\n" + "=" * 60)
    print("  CONTENT PACKAGE")
    print("=" * 60)
    for label, path in written.items():
        print(f"  {label:<10}: {path.name}")
    print("-" * 60)
    print(f"  Compliance : {report.get('status', '').upper()} "
          f"/ {report.get('final_recommendation', '').upper()} "
          f"({len(report.get('flagged_lines', []))} flag(s))")
    print(f"  Dir        : {next(iter(written.values())).parent}")
    print("=" * 60 + "\n")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    mode, ticker, event, args = _resolve(argv)

    if mode == "voice":  # audio-only step on an already-approved script (no Claude, no data)
        return _voice_command(args)

    provider = get_provider(config.DATA_PROVIDER, config.CACHE_DIR)

    if mode == "validate":
        validation.update_validations(provider)
        return 0
    if mode == "weekly":
        print("[weekly] Weekly review is a planned future mode — not implemented yet.")
        return 0
    if mode in ("stock", "earnings") and not ticker and not args.from_fixture:
        print(f"[error] {mode} mode needs a ticker, e.g. `python main.py {mode} NVDA`.")
        return 2
    if mode == "macro" and not event and not args.from_fixture:
        print('[error] macro mode needs --event, e.g. `python main.py macro --event "FOMC decision"`.')
        return 2

    packet = _build_packet(mode, ticker, event, args, provider)
    mode = packet.get("mode", mode)  # fixture carries its own mode

    print(f"[claude] generating {mode} content package ({config.CLAUDE_MODEL}) ...")
    try:
        package = brief_generator.generate_content_package(packet, mode=mode)
    except brief_generator.MissingAPIKeyError as exc:
        print(f"\n[error] {exc}")
        print("[error] The packet was produced, but script generation needs an "
              "Anthropic key. Set ANTHROPIC_API_KEY in .env.local and rerun.")
        return 1

    print("[compliance] reviewing generated script ...")
    report = compliance.run_compliance_check(package["long_form_script"], packet, mode=mode)

    written = content_package.write_package(packet, package, report)
    _print_summary(written, report)
    # Generation is text-only and never charges ElevenLabs. Approve the script,
    # then voice it separately:
    print(f"[next] review the script, then run:  python main.py voice "
          f"{'' if mode == 'daily' else '--file ' + str(written['voiceover'])}".rstrip())
    return 0


def _voice_command(args) -> int:
    """Generate .mp3 + .srt from an already-approved voiceover.txt (no Claude)."""
    import media

    if args.file:
        path = Path(args.file)
    else:
        date = args.date or dt.date.today().isoformat()
        path = config.OUTPUT_DIR / date / f"daily_brief_{date}_voiceover.txt"

    if not path.exists():
        print(f"[voice] no voiceover file at {path}")
        print("[voice] generate the script first (e.g. `python main.py daily`), "
              "or pass --file PATH / --date YYYY-MM-DD.")
        return 2

    text = path.read_text()
    out_dir = path.parent
    suffix = "_voiceover.txt"
    stem = path.name[: -len(suffix)] if path.name.endswith(suffix) else path.stem

    per_char = 0.5 if any(m in config.ELEVENLABS_MODEL for m in ("turbo", "flash")) else 1.0
    print(f"[voice] {len(text):,} chars via ElevenLabs ({config.ELEVENLABS_MODEL}) "
          f"≈ {int(len(text) * per_char):,} credits ...")
    try:
        paths = media.generate_voiceover(text, out_dir, stem)
    except media.MissingVoiceConfigError as exc:
        print(f"[voice] {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[voice] ElevenLabs error: {type(exc).__name__}: {exc}")
        return 1
    print(f"[voice] saved -> {paths['mp3']}")
    print(f"[voice] saved -> {paths['srt']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
