"""Market regime synthesis from per-ticker signal dicts.

Consumes the already-computed ticker objects (see packet.py) and derives a
top-level read: risk tone, volatility tone, sector leadership/laggards, and
short summaries for SPY, QQQ, VIX, and DXY. Everything degrades to
"unavailable" when its inputs are missing — no invented tone.
"""
from __future__ import annotations

import config

DXY_KEYS = ("DX-Y.NYB", "DX=F", "DXY")


def _get(tickers: dict, symbol: str) -> dict | None:
    t = tickers.get(symbol)
    return t if t and t.get("status") == "ok" else None


def _dxy(tickers: dict) -> tuple[str | None, dict | None]:
    for key in DXY_KEYS:
        t = _get(tickers, key)
        if t:
            return key, t
    return None, None


def _trend_summary(t: dict | None, name: str) -> str | None:
    if not t:
        return f"{name} data unavailable"
    chg = t.get("daily_change_pct")
    trend = t.get("trend")
    pos = t.get("price_vs_moving_averages", {})
    chg_str = f"{chg:+.2f}%" if chg is not None else "n/a"
    return (
        f"{name} {chg_str} on the day, {trend}; "
        f"{pos.get('vs_50d', 'n/a')} 50D, {pos.get('vs_200d', 'n/a')} 200D."
    )


def _vix_summary(tickers: dict) -> dict:
    t = _get(tickers, "^VIX")
    if not t:
        return {"status": "unavailable", "level": None, "daily_change_pct": None, "read": None}
    level = t.get("latest_close")
    if level is None:
        read = None
    elif level < 15:
        read = "calm"
    elif level < 20:
        read = "normal"
    elif level < 30:
        read = "elevated"
    else:
        read = "high / stressed"
    return {
        "status": "ok",
        "level": level,
        "daily_change_pct": t.get("daily_change_pct"),
        "read": read,
    }


def _dxy_summary(tickers: dict) -> dict:
    key, t = _dxy(tickers)
    if not t:
        return {"status": "unavailable", "symbol": None, "level": None,
                "daily_change_pct": None, "trend": None}
    return {
        "status": "ok",
        "symbol": key,
        "level": t.get("latest_close"),
        "daily_change_pct": t.get("daily_change_pct"),
        "trend": t.get("trend"),
    }


def _sector_ranking(tickers: dict) -> tuple[list, list]:
    ranked = []
    for sym in config.SECTOR_ETFS:
        t = _get(tickers, sym)
        if t and t.get("daily_change_pct") is not None:
            ranked.append({"ticker": sym, "daily_change_pct": t["daily_change_pct"]})
    ranked.sort(key=lambda r: r["daily_change_pct"], reverse=True)
    leaders = ranked[:3]
    laggards = list(reversed(ranked[-3:])) if len(ranked) >= 3 else ranked
    return leaders, laggards


def _risk_tone(spy: dict | None, vix: dict, leaders: list, laggards: list) -> str:
    if spy is None or vix.get("status") != "ok":
        return "unavailable"
    spy_up = (spy.get("daily_change_pct") or 0) > 0
    spy_trend_bull = spy.get("trend") in ("uptrend", "neutral_bullish")
    vix_read = vix.get("read")
    if spy_up and spy_trend_bull and vix_read in ("calm", "normal"):
        return "risk-on"
    if (not spy_up) and vix_read in ("elevated", "high / stressed"):
        return "risk-off"
    return "neutral / mixed"


def build(tickers: dict) -> dict:
    spy = _get(tickers, "SPY")
    qqq = _get(tickers, "QQQ")
    vix = _vix_summary(tickers)
    dxy = _dxy_summary(tickers)
    leaders, laggards = _sector_ranking(tickers)

    return {
        "risk_tone": _risk_tone(spy, vix, leaders, laggards),
        "volatility_tone": vix.get("read") or "unavailable",
        "sector_leadership": leaders,
        "sector_laggards": laggards,
        "spy_trend_summary": _trend_summary(spy, "SPY"),
        "qqq_trend_summary": _trend_summary(qqq, "QQQ"),
        "vix_summary": vix,
        "dxy_summary": dxy,
    }
