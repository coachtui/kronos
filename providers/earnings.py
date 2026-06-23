"""Earnings-date awareness via yfinance (free, no key).

Surfaces upcoming earnings for a watchlist (daily/macro) or a single focus
ticker (stock/earnings) so the brief can connect catalysts to today's action —
e.g. a memory-led selloff with Micron reporting tomorrow. Degrades to
`unavailable` (never raises).
"""
from __future__ import annotations

import datetime as dt
from typing import Any


def _when(days: int) -> str:
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    return f"in {days} days"


def _next_earnings_date(ticker: str, today: dt.date) -> dt.date | None:
    import yfinance as yf

    try:
        df = yf.Ticker(ticker).get_earnings_dates(limit=16)
    except Exception:  # noqa: BLE001
        df = None
    future = []
    if df is not None and not df.empty:
        for ts in df.index:
            try:
                d = ts.date()
            except AttributeError:
                continue
            if d >= today:
                future.append(d)
    if future:
        return min(future)
    # Fallback: the .calendar dict (some tickers only populate this)
    try:
        cal = yf.Ticker(ticker).calendar
        ed = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if isinstance(ed, list) and ed:
            ed = ed[0]
        if isinstance(ed, dt.date) and ed >= today:
            return ed
    except Exception:  # noqa: BLE001
        pass
    return None


def get_earnings_calendar(tickers: list[str], horizon_days: int = 7) -> dict:
    """Upcoming earnings within ``horizon_days`` for the given tickers."""
    today = dt.date.today()
    upcoming: list[dict[str, Any]] = []
    for t in tickers:
        d = _next_earnings_date(t, today)
        if d is None:
            continue
        days = (d - today).days
        if 0 <= days <= horizon_days:
            upcoming.append({"ticker": t.upper(), "date": d.isoformat(),
                             "days_until": days, "when": _when(days)})
    upcoming.sort(key=lambda x: x["days_until"])
    return {"status": "ok" if upcoming else "none_upcoming", "source": "yfinance",
            "horizon_days": horizon_days, "upcoming": upcoming}


def get_ticker_earnings(ticker: str) -> dict:
    """Next earnings date for a single ticker (stock/earnings modes)."""
    today = dt.date.today()
    d = _next_earnings_date(ticker, today)
    if d is None:
        return {"status": "unavailable", "source": "yfinance", "next_date": None}
    days = (d - today).days
    return {"status": "ok", "source": "yfinance", "next_date": d.isoformat(),
            "days_until": days, "when": _when(days)}
