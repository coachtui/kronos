"""Forecast validation log — built from day one.

Every forecast run appends a row to logs/forecast_history.csv. Later, the
``--validate`` command fills in ``actual_next_close`` once the next session has
closed, so directional accuracy and average error can be computed.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import Any

import config

FIELDNAMES = [
    "run_date",
    "ticker",
    "last_close",
    "predicted_close",
    "predicted_direction",
    "predicted_magnitude",
    "actual_next_close",
    "hit_or_miss",
    "error_pct",
    "kronos_status",
]


def log_forecast(forecast: dict[str, Any], run_date: str | None = None) -> Path:
    """Append one forecast record. Creates the file + header if needed."""
    path = config.FORECAST_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()

    row = {
        "run_date": run_date or dt.date.today().isoformat(),
        "ticker": forecast.get("ticker"),
        "last_close": forecast.get("last_close"),
        "predicted_close": forecast.get("predicted_close"),
        "predicted_direction": forecast.get("predicted_direction"),
        "predicted_magnitude": forecast.get("predicted_magnitude"),
        "actual_next_close": "",   # filled later by --validate
        "hit_or_miss": "",         # filled later by --validate
        "error_pct": "",           # filled later by --validate
        "kronos_status": forecast.get("status"),
    }

    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    return path


def update_validations(provider) -> int:
    """Fill in actual outcomes for past forecasts. (Full impl: Milestone 6.)

    Returns the number of rows updated. For now this is a stub that reports
    how many rows are awaiting validation so --validate is wired end-to-end.
    """
    path = config.FORECAST_LOG
    if not path.exists():
        print("No forecast history yet — nothing to validate.")
        return 0

    pending = 0
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            if not row.get("actual_next_close"):
                pending += 1
    print(
        f"--validate: {pending} forecast row(s) awaiting actual outcomes.\n"
        "Outcome-matching lands in Milestone 6."
    )
    return 0
