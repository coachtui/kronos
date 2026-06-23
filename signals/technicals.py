"""Technical signals computed from a normalized OHLCV DataFrame.

Every value is derived from real cached/fetched data — nothing is invented.
Functions return ``None`` when there is insufficient history rather than
guessing, so the packet can mark fields honestly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _round(x, n=4):
    return round(float(x), n) if x is not None and pd.notna(x) else None


def sma(close: pd.Series, window: int) -> float | None:
    if len(close) < window:
        return None
    return _round(close.rolling(window).mean().iloc[-1])


def rsi(close: pd.Series, period: int = 14) -> float | None:
    """Wilder's RSI."""
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    return _round(rsi_series.iloc[-1], 2)


def atr(df: pd.DataFrame, period: int = 14) -> float | None:
    """Wilder's Average True Range."""
    if len(df) < period + 1:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr_series = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return _round(atr_series.iloc[-1])


def _vs(price: float | None, ma: float | None) -> str | None:
    if price is None or ma is None:
        return None
    return "above" if price >= ma else "below"


def classify_trend(price, ma20, ma50, ma200) -> str:
    if any(v is None for v in (price, ma50, ma200)):
        return "insufficient_data"
    if price > ma50 > ma200:
        return "uptrend"
    if price < ma50 < ma200:
        return "downtrend"
    if price > ma200:
        return "neutral_bullish"
    return "neutral_bearish"


def classify_volatility(atr_val, price) -> str:
    """Generic ATR-as-percent-of-price banding. (VIX gets its own read in regime.)"""
    if atr_val is None or not price:
        return "unavailable"
    atr_pct = atr_val / price * 100
    if atr_pct < 1.0:
        return "low"
    if atr_pct < 2.0:
        return "normal"
    if atr_pct < 3.5:
        return "elevated"
    return "high"


def compute(df: pd.DataFrame) -> dict:
    """Return the full technical-signal dict for one ticker."""
    close = df["close"]
    latest = _round(close.iloc[-1]) if len(close) else None
    previous = _round(close.iloc[-2]) if len(close) >= 2 else None
    change_pct = (
        _round((latest - previous) / previous * 100)
        if latest is not None and previous not in (None, 0)
        else None
    )
    ma20, ma50, ma200 = sma(close, 20), sma(close, 50), sma(close, 200)
    atr14 = atr(df)

    return {
        "latest_close": latest,
        "previous_close": previous,
        "daily_change_pct": change_pct,
        "ma_20": ma20,
        "ma_50": ma50,
        "ma_200": ma200,
        "rsi_14": rsi(close),
        "atr_14": atr14,
        "trend": classify_trend(latest, ma20, ma50, ma200),
        "volatility": classify_volatility(atr14, latest),
        "price_vs_moving_averages": {
            "vs_20d": _vs(latest, ma20),
            "vs_50d": _vs(latest, ma50),
            "vs_200d": _vs(latest, ma200),
        },
    }
