"""Kronos forecast layer.

Wraps the vendored KronosPredictor. Kronos is treated as ONE signal, not the
source of truth: every failure mode degrades gracefully to a status string so
the brief can continue on market data + technical signals alone.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

import config

# Make the vendored `model` package importable: `from model import ...`
_VENDOR = str(config.VENDOR_KRONOS_DIR)
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

# Forecast status values
STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"

_PREDICTOR = None  # lazily loaded singleton


def _load_predictor():
    """Load model + tokenizer once. Raises on failure (caller handles it)."""
    global _PREDICTOR
    if _PREDICTOR is not None:
        return _PREDICTOR
    from model import Kronos, KronosTokenizer, KronosPredictor

    tokenizer = KronosTokenizer.from_pretrained(config.KRONOS_TOKENIZER_NAME)
    model = Kronos.from_pretrained(config.KRONOS_MODEL_NAME)
    _PREDICTOR = KronosPredictor(
        model,
        tokenizer,
        device=config.KRONOS_DEVICE,
        max_context=config.KRONOS_MAX_CONTEXT,
    )
    return _PREDICTOR


def _next_session_timestamp(last_ts: pd.Timestamp, pred_len: int) -> pd.Series:
    """Next ``pred_len`` business days after ``last_ts`` (weekends skipped).

    Note: does not skip market holidays yet — acceptable for the M1 forecast.
    """
    future = pd.bdate_range(
        start=last_ts + pd.tseries.offsets.BDay(1), periods=pred_len
    )
    return pd.Series(future)


def forecast(ticker: str, ohlcv: pd.DataFrame) -> dict[str, Any]:
    """Generate a next-session forecast for ``ticker``.

    Returns a dict that is always safe to consume, even on failure:
        status, last_close, predicted_close, predicted_direction,
        predicted_magnitude (pct), pred_len, error
    """
    result: dict[str, Any] = {
        "ticker": ticker,
        "status": STATUS_UNAVAILABLE,
        "last_close": None,
        "predicted_close": None,
        "predicted_direction": None,
        "predicted_magnitude": None,
        "pred_len": config.KRONOS_PRED_LEN,
        "error": None,
    }

    try:
        last_close = float(ohlcv["close"].iloc[-1])
        result["last_close"] = round(last_close, 4)
    except (KeyError, IndexError, ValueError) as exc:
        result["error"] = f"bad input data: {exc}"
        return result

    try:
        predictor = _load_predictor()

        lookback = min(config.KRONOS_LOOKBACK, len(ohlcv))
        window = ohlcv.iloc[-lookback:]
        x_df = window[["open", "high", "low", "close", "volume"]].reset_index(drop=True)
        x_timestamp = pd.Series(window.index)
        y_timestamp = _next_session_timestamp(window.index[-1], config.KRONOS_PRED_LEN)

        pred_df = predictor.predict(
            df=x_df,
            x_timestamp=x_timestamp,
            y_timestamp=y_timestamp,
            pred_len=config.KRONOS_PRED_LEN,
            T=config.KRONOS_TEMPERATURE,
            top_p=config.KRONOS_TOP_P,
            sample_count=config.KRONOS_SAMPLE_COUNT,
            verbose=False,
        )

        predicted_close = float(pred_df["close"].iloc[-1])
        magnitude_pct = (predicted_close - last_close) / last_close * 100.0
        if magnitude_pct > 0.05:
            direction = "up"
        elif magnitude_pct < -0.05:
            direction = "down"
        else:
            direction = "flat"

        result.update(
            status=STATUS_OK,
            predicted_close=round(predicted_close, 4),
            predicted_direction=direction,
            predicted_magnitude=round(magnitude_pct, 4),
        )
    except Exception as exc:  # noqa: BLE001 - degrade gracefully on ANY failure
        result["status"] = STATUS_UNAVAILABLE
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result
