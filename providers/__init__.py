"""Provider factory — selects a data provider by name."""
from __future__ import annotations

from pathlib import Path

from .base import DataProvider, OHLCV_COLUMNS
from .mock_provider import MockProvider
from .yfinance_provider import YFinanceProvider

__all__ = ["DataProvider", "OHLCV_COLUMNS", "get_provider"]


def get_provider(name: str, cache_dir: Path) -> DataProvider:
    name = (name or "yfinance").lower()
    if name == "yfinance":
        return YFinanceProvider(cache_dir=cache_dir)
    if name == "mock":
        return MockProvider(cache_dir=cache_dir)
    raise ValueError(
        f"Unknown DATA_PROVIDER {name!r}. Supported now: yfinance, mock."
    )
