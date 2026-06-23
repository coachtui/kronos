"""Support / resistance detection from recent swing points.

Swing highs/lows are local extrema within a +/-``window`` bar neighborhood over
the last ``lookback`` bars. Levels are deduplicated by proximity so we return a
few clean, distinct prices rather than a noisy cluster.
"""
from __future__ import annotations

import pandas as pd


def _dedup(levels: list[float], price: float, tol_pct: float = 0.5) -> list[float]:
    """Merge levels within ``tol_pct`` of each other (keep the first seen)."""
    out: list[float] = []
    for lvl in levels:
        if all(abs(lvl - kept) / price * 100 > tol_pct for kept in out):
            out.append(lvl)
    return out


def support_resistance(
    df: pd.DataFrame, lookback: int = 120, window: int = 3, max_levels: int = 3
) -> tuple[list[float], list[float]]:
    """Return (supports, resistances) nearest to the current price.

    supports: distinct swing lows below price, nearest first.
    resistances: distinct swing highs above price, nearest first.
    """
    if len(df) < window * 2 + 1:
        return [], []

    data = df.iloc[-lookback:]
    highs = data["high"].to_numpy()
    lows = data["low"].to_numpy()
    n = len(data)
    price = float(df["close"].iloc[-1])

    swing_highs, swing_lows = [], []
    for i in range(window, n - window):
        if highs[i] == highs[i - window : i + window + 1].max():
            swing_highs.append(round(float(highs[i]), 2))
        if lows[i] == lows[i - window : i + window + 1].min():
            swing_lows.append(round(float(lows[i]), 2))

    # supports: below price, nearest (highest) first
    supports = sorted({l for l in swing_lows if l < price}, reverse=True)
    # resistances: above price, nearest (lowest) first
    resistances = sorted({h for h in swing_highs if h > price})

    supports = _dedup(supports, price)[:max_levels]
    resistances = _dedup(resistances, price)[:max_levels]
    return supports, resistances
