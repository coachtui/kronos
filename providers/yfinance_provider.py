"""yfinance-backed data provider with local parquet caching.

Cache policy: one parquet per (ticker, interval) under data/cache/yfinance/.
If the cache file was written today, reuse it; otherwise refetch. This stops
reruns from hammering Yahoo while still picking up a new daily bar each day.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from .base import DataProvider

# Tickers Yahoo serves under awkward symbols, with fallbacks tried in order.
SYMBOL_FALLBACKS = {
    "DXY": ["DX-Y.NYB", "DX=F"],
    "DX-Y.NYB": ["DX-Y.NYB", "DX=F"],
}


class YFinanceProvider(DataProvider):
    name = "yfinance"

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir) / "yfinance"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, ticker: str, interval: str) -> Path:
        safe = ticker.replace("^", "_").replace("=", "_").replace(".", "_")
        return self.cache_dir / f"{safe}_{interval}.parquet"

    def _cache_is_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        mtime = dt.date.fromtimestamp(path.stat().st_mtime)
        return mtime >= dt.date.today()

    def fetch_ohlcv(
        self, ticker: str, period: str = "2y", interval: str = "1d"
    ) -> pd.DataFrame:
        path = self._cache_path(ticker, interval)
        if self._cache_is_fresh(path):
            return pd.read_parquet(path)

        df = self._download(ticker, period, interval)
        if df.empty:
            # Fall back to a stale cache rather than failing the run.
            if path.exists():
                return pd.read_parquet(path)
            raise RuntimeError(f"No data returned for {ticker!r} and no cache available.")

        df.to_parquet(path)
        return df

    def _download(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        import yfinance as yf

        for symbol in SYMBOL_FALLBACKS.get(ticker, [ticker]):
            raw = yf.download(
                symbol,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if raw is not None and not raw.empty:
                # yfinance may return a MultiIndex column frame for single tickers.
                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = raw.columns.get_level_values(0)
                column_map = {
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
                return self.normalize(raw, column_map)
        return pd.DataFrame()
