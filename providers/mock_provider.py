"""Deterministic offline provider for tests and no-network development.

Generates a smooth synthetic random-walk OHLCV series so the pipeline can be
exercised (and Kronos can run) without hitting any external API.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from .base import DataProvider, OHLCV_COLUMNS


class MockProvider(DataProvider):
    name = "mock"

    def __init__(self, cache_dir: Path | None = None, n_bars: int = 500):
        self.n_bars = n_bars

    def fetch_ohlcv(
        self, ticker: str, period: str = "2y", interval: str = "1d"
    ) -> pd.DataFrame:
        # Seed the walk off the ticker name so each symbol is stable but distinct.
        seed = sum(ord(c) for c in ticker)
        dates = pd.bdate_range(end=pd.Timestamp("2026-06-22"), periods=self.n_bars)
        rows = []
        price = 100.0 + (seed % 50)
        for i in range(self.n_bars):
            drift = math.sin((i + seed) / 15.0) * 0.6
            price = max(1.0, price + drift)
            high = price + abs(math.sin(i + seed)) * 0.8
            low = price - abs(math.cos(i + seed)) * 0.8
            open_ = (high + low) / 2
            vol = 1_000_000 + (i * 137 + seed) % 500_000
            rows.append([open_, high, low, price, float(vol)])
        df = pd.DataFrame(rows, columns=OHLCV_COLUMNS, index=dates)
        df.index.name = "date"
        return df
