"""Data provider abstraction.

Every provider returns OHLCV in one normalized schema so the rest of the
pipeline never cares which vendor (yfinance, Polygon, Tiingo, ...) produced it.

Normalized schema (pandas DataFrame):
    index : DatetimeIndex, name="date", tz-naive, ascending
    columns: ["open", "high", "low", "close", "volume"]  (float)
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


class DataProvider(ABC):
    """Base class for all market-data providers."""

    name: str = "base"

    @abstractmethod
    def fetch_ohlcv(
        self, ticker: str, period: str = "2y", interval: str = "1d"
    ) -> pd.DataFrame:
        """Return normalized OHLCV for ``ticker`` (see module docstring)."""
        raise NotImplementedError

    # -- shared helpers -------------------------------------------------

    @staticmethod
    def normalize(df: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
        """Map vendor columns to the normalized schema and validate.

        column_map maps NORMALIZED name -> vendor column name, e.g.
        {"open": "Open", "high": "High", ...}.
        """
        out = pd.DataFrame(index=pd.to_datetime(df.index))
        out.index.name = "date"
        if out.index.tz is not None:
            out.index = out.index.tz_localize(None)

        for norm_col in OHLCV_COLUMNS:
            vendor_col = column_map.get(norm_col)
            if vendor_col is not None and vendor_col in df.columns:
                out[norm_col] = pd.to_numeric(df[vendor_col], errors="coerce")
            else:
                # volume legitimately missing for some indices -> 0.0
                out[norm_col] = 0.0 if norm_col == "volume" else pd.NA

        out = out.sort_index()
        out = out[~out.index.duplicated(keep="last")]
        # Drop rows with no price data; leave volume as-is.
        out = out.dropna(subset=["open", "high", "low", "close"])
        return out
