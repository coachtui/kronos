"""Finnhub news feed — the 'why' behind market moves.

Free-tier endpoints: general market news and per-company news. Degrades to
`unavailable` (never raises) when no key is set or the request fails, so the
packet build can't be broken by the news layer.

The script must only cite headlines actually present in the packet — Claude is
instructed never to invent news.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import config

_BASE = "https://finnhub.io/api/v1"


def _unavailable(reason: str | None = None) -> dict:
    return {"status": "unavailable", "source": "finnhub", "headlines": [], "reason": reason}


def _clean(items: list[dict], limit: int) -> list[dict]:
    out = []
    for x in items[:limit]:
        ts = x.get("datetime")
        when = None
        if ts:
            try:
                when = dt.datetime.fromtimestamp(ts).isoformat(timespec="minutes")
            except (ValueError, OSError, TypeError):
                when = None
        out.append({
            "headline": (x.get("headline") or "").strip(),
            "summary": (x.get("summary") or "").strip()[:400],
            "source": x.get("source"),
            "datetime": when,
            "url": x.get("url"),
            "related": x.get("related") or None,
        })
    return [h for h in out if h["headline"]]


def get_market_news(limit: int | None = None) -> dict:
    """Top general market headlines (for daily / macro modes)."""
    limit = limit or config.NEWS_HEADLINE_LIMIT
    if not config.FINNHUB_API_KEY:
        return _unavailable("no FINNHUB_API_KEY set")
    try:
        import requests

        r = requests.get(f"{_BASE}/news",
                         params={"category": "general", "token": config.FINNHUB_API_KEY},
                         timeout=15)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return _unavailable("unexpected response")
        return {"status": "ok", "source": "finnhub", "headlines": _clean(data, limit)}
    except Exception as exc:  # noqa: BLE001 - never break the run on news
        return _unavailable(f"{type(exc).__name__}: {exc}")


def get_company_news(ticker: str, days: int = 7, limit: int | None = None) -> dict:
    """Recent company-specific headlines (for stock / earnings modes)."""
    limit = limit or config.NEWS_HEADLINE_LIMIT
    if not config.FINNHUB_API_KEY:
        return _unavailable("no FINNHUB_API_KEY set")
    try:
        import requests

        today = dt.date.today()
        params = {
            "symbol": ticker.upper(),
            "from": (today - dt.timedelta(days=days)).isoformat(),
            "to": today.isoformat(),
            "token": config.FINNHUB_API_KEY,
        }
        r = requests.get(f"{_BASE}/company-news", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return _unavailable("unexpected response")
        # newest first
        data.sort(key=lambda x: x.get("datetime", 0), reverse=True)
        out = {"status": "ok", "source": "finnhub", "headlines": _clean(data, limit)}
        out["ticker"] = ticker.upper()
        return out
    except Exception as exc:  # noqa: BLE001
        return _unavailable(f"{type(exc).__name__}: {exc}")
