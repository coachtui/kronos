"""kronos-brief CLI — mode-based content engine (Milestone 3, revised).

Modes:
    daily     broad daily market brief (default)
    stock     individual stock review
    earnings  earnings preview / reaction
    macro     macro-event video
    weekly    longer weekly review (future — not implemented yet)

Preferred CLI:
    python main.py daily --no-audio
    python main.py stock NVDA --no-audio
    python main.py earnings NVDA --event "earnings preview" --no-audio
    python main.py macro --event "FOMC decision" --no-audio
    python main.py validate

Backward-compatible flag form (no subcommand):
    python main.py --no-audio                 -> daily brief
    python main.py --stock NVDA --no-audio    -> separate stock review (NOT in daily)
    python main.py --macro --no-audio         -> daily brief with macro section
    python main.py --macro --event X          -> separate macro-event video

No audio, captions, or posting yet.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import config
from editorial import brief_generator, compliance, content_package
from providers import get_provider
from signals import packet as pb
from signals import validation

MODES = {"daily", "stock", "earnings", "macro", "weekly", "validate"}


def _parse(rest) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="main.py", description="kronos-brief content engine")
    p.add_argument("ticker", nargs="?", help="ticker for stock/earnings modes")
    p.add_argument("--event", help="event label (macro / earnings modes)")
    p.add_argument("--stock", metavar="TICKER", help="[flag form] generate a stock review")
    p.add_argument("--macro", action="store_true", help="[flag form] macro section / macro mode")
    p.add_argument("--no-audio", action="store_true", help="skip voiceover (M4; no effect yet)")
    p.add_argument("--from-fixture", metavar="PATH", help="load a saved packet instead of live fetch")
    p.add_argument("--validate", action="store_true", help="reconcile past forecasts with actuals")
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
    if args.no_audio:
        print("[audio] --no-audio set; skipping voiceover (M4).")
    _print_summary(written, report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
