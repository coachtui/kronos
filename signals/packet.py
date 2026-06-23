"""Market source packet builder (mode-aware).

Builds the structured JSON that feeds Claude. Modes:
    daily     broad market brief (SPY/QQQ/VIX/DXY/sectors) — NO stock spotlight
    stock     single-ticker review (+ SPY/QQQ for relative strength)
    earnings  single-ticker earnings preview/reaction
    macro     macro-event view (SPY/QQQ/VIX/DXY) around a named event

Hard rules (see docs/CONTENT_ENGINE_CONTEXT.md):
- never invent data; mark missing fields unavailable
- one failed ticker must not crash the run
- the internal forecast signal is ONE input, not the source of truth, and is
  named neutrally (`projection`) — "Kronos" never appears in the packet.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import config
from providers import DataProvider, earnings as earnings_feed, news as news_feed
from signals import kronos_predictor, levels, regime, technicals, validation

SCHEMA_VERSION = "3.0"
PROJECTION_NOTE = (
    "The projection is one probabilistic input among many (price structure, "
    "volatility, the dollar, sector rotation, macro). It is not the source of "
    "truth and requires price confirmation. Do not name the underlying model."
)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "event"


def _unavailable(**extra: Any) -> dict:
    base = {"status": "unavailable", "source": None}
    base.update(extra)
    return base


def _placeholders() -> dict:
    return {
        "fear_greed": _unavailable(score=None, classification=None, sub_indexes=[]),
        "macro_calendar": _unavailable(events=[]),
        "rates_summary": _unavailable(
            ten_year_yield=None, two_year_yield=None, fed_funds=None, summary=None
        ),
        "wall_street_consensus": _unavailable(summary=None, targets=[]),
    }


def _projection_skipped() -> dict:
    return {"status": "skipped", "direction": None, "projected_close": None, "magnitude": None}


def _build_ticker(
    symbol: str, provider: DataProvider, do_forecast: bool, log_forecasts: bool
) -> tuple[dict, str | None]:
    """Return (ticker_object, error_message_or_None). Internal forecast -> `projection`."""
    try:
        df = provider.fetch_ohlcv(
            symbol, period=config.HISTORY_PERIOD, interval=config.BAR_INTERVAL
        )
        if df.empty:
            return ({"ticker": symbol, "status": "unavailable", "reason": "no data returned"},
                    f"{symbol}: no data")

        tech = technicals.compute(df)
        support, resistance = levels.support_resistance(df)
        obj: dict = {"ticker": symbol, "status": "ok", **tech,
                     "support_levels": support, "resistance_levels": resistance}

        if do_forecast:
            fc = kronos_predictor.forecast(symbol, df)  # internal signal
            obj["projection"] = {
                "status": fc["status"],
                "direction": fc["predicted_direction"],
                "projected_close": fc["predicted_close"],
                "magnitude": fc["predicted_magnitude"],
            }
            if log_forecasts:
                validation.log_forecast(fc)
        else:
            obj["projection"] = _projection_skipped()

        return obj, None
    except Exception as exc:  # noqa: BLE001 - one bad ticker must not stop the run
        return ({"ticker": symbol, "status": "unavailable", "reason": f"{type(exc).__name__}: {exc}"},
                f"{symbol}: {exc}")


def _quote_price(ticker: str) -> float | None:
    """Current quote (fast_info) — fresh even when daily history lags a session."""
    try:
        import yfinance as yf

        fi = yf.Ticker(ticker).fast_info
        last = fi.get("lastPrice") if hasattr(fi, "get") else getattr(fi, "last_price", None)
        return float(last) if last else None
    except Exception:  # noqa: BLE001
        return None


def _build_cross_market(provider: DataProvider) -> dict:
    """Overnight global sessions + cross-asset — the lead-in to the US open.

    yfinance's daily *history* for native foreign indices (e.g. ^KS11) lags a
    session, so when an instrument's last bar is behind the freshest session we
    pull its live *quote* and compute the move vs the prior close. This yields the
    same number Yahoo's website shows (e.g. KOSPI -9.99%), not a stale +0.69%.
    """
    raw = []
    for ticker, name, region in config.CROSS_MARKET:
        try:
            df = provider.fetch_ohlcv(ticker, period="1mo", interval=config.BAR_INTERVAL)
            if df is None or len(df) < 2:
                continue
            raw.append({"ticker": ticker, "name": name, "region": region,
                        "hist_date": df.index[-1].date().isoformat(),
                        "hist_last": float(df["close"].iloc[-1]),
                        "hist_prev": float(df["close"].iloc[-2])})
        except Exception:  # noqa: BLE001 - never break the run on a foreign ticker
            continue
    if not raw:
        return {"status": "unavailable", "source": provider.name, "as_of": None, "markets": []}

    ref = max(r["hist_date"] for r in raw)  # the current session, set by fresh instruments
    markets = []
    for r in raw:
        if r["hist_date"] == ref:  # history is current
            close, prev, date, stale = r["hist_last"], r["hist_prev"], r["hist_date"], False
        else:  # history lags — use the live quote vs the last (prior) close
            q = _quote_price(r["ticker"])
            if q is not None:
                close, prev, date, stale = q, r["hist_last"], ref, False
            else:
                close, prev, date, stale = r["hist_last"], r["hist_prev"], r["hist_date"], True
        chg = round((close - prev) / prev * 100, 2) if prev else None
        markets.append({"ticker": r["ticker"], "name": r["name"], "region": r["region"],
                        "close": round(close, 2), "change_pct": chg, "date": date, "stale": stale})
    return {"status": "ok", "source": provider.name, "as_of": ref, "markets": markets}


def _relative_strength(tickers: dict, focus: str) -> dict:
    f = tickers.get(focus, {})
    out = {"status": "unavailable", "vs_SPY_pct": None, "vs_QQQ_pct": None}
    if f.get("status") != "ok" or f.get("daily_change_pct") is None:
        return out
    fc = f["daily_change_pct"]
    for key, sym in (("vs_SPY_pct", "SPY"), ("vs_QQQ_pct", "QQQ")):
        t = tickers.get(sym, {})
        if t.get("status") == "ok" and t.get("daily_change_pct") is not None:
            out[key] = round(fc - t["daily_change_pct"], 4)
    if out["vs_SPY_pct"] is not None or out["vs_QQQ_pct"] is not None:
        out["status"] = "ok"
    return out


def _assemble(
    provider: DataProvider,
    *,
    mode: str,
    universe: list[str],
    forecast_set: set[str],
    macro_enabled: bool = False,
    event: str | None = None,
    focus_ticker: str | None = None,
    run_date: str | None = None,
    write: bool = True,
    log_forecasts: bool | None = None,
    include_feeds: bool | None = None,
) -> tuple[dict, Path | None]:
    if log_forecasts is None:
        log_forecasts = write
    # Feeds are live network calls — on by default for yfinance, off for mock/tests.
    if include_feeds is None:
        include_feeds = getattr(provider, "name", "") == "yfinance"
    run_date = run_date or dt.date.today().isoformat()

    ticker_objs: dict[str, dict] = {}
    errors: list[str] = []
    for symbol in universe:
        obj, err = _build_ticker(symbol, provider, symbol in forecast_set, log_forecasts)
        ticker_objs[symbol] = obj
        if err:
            errors.append(err)

    # --- news + earnings + cross-market feeds (degrade to unavailable, never crash) ---
    cross_market = {"status": "unavailable", "source": None, "markets": []}
    if include_feeds:
        if mode in ("stock", "earnings") and focus_ticker:
            news = news_feed.get_company_news(focus_ticker)
            earnings_cal = earnings_feed.get_earnings_calendar([focus_ticker], config.EARNINGS_HORIZON_DAYS)
        else:
            news = news_feed.get_market_news()
            earnings_cal = earnings_feed.get_earnings_calendar(config.EARNINGS_WATCHLIST, config.EARNINGS_HORIZON_DAYS)
            cross_market = _build_cross_market(provider)
    else:
        news = {"status": "unavailable", "source": None, "headlines": []}
        earnings_cal = {"status": "unavailable", "source": None, "upcoming": []}

    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "milestone": 3,
        "mode": mode,
        "date": run_date,
        "event": event,
        "data_provider": provider.name,
        "projection_note": PROJECTION_NOTE,
        "tickers": ticker_objs,
        "market_regime": regime.build(ticker_objs),
        "news": news,
        "earnings_calendar": earnings_cal,
        "cross_market": cross_market,
        **_placeholders(),
        "macro": {"enabled": bool(macro_enabled)},
        "errors": errors,
    }
    if event:
        packet["event_slug"] = slugify(event)
    if focus_ticker:
        f = ticker_objs.get(focus_ticker, {})
        packet["focus"] = {
            "enabled": True,
            "ticker": focus_ticker,
            "key_levels": {
                "support": f.get("support_levels", []),
                "resistance": f.get("resistance_levels", []),
            },
            "relative_strength": _relative_strength(ticker_objs, focus_ticker),
            "earnings_context": (
                earnings_feed.get_ticker_earnings(focus_ticker) if include_feeds
                else _unavailable(next_date=None)
            ),
            "implied_move": _unavailable(value=None),  # options-implied move: not wired yet
        }

    written = None
    if write:
        out_dir = config.OUTPUT_DIR / run_date
        out_dir.mkdir(parents=True, exist_ok=True)
        written = out_dir / f"packet_{mode}_{run_date}.json"
        written.write_text(json.dumps(packet, indent=2, default=str))
    return packet, written


# --- Public mode builders -------------------------------------------------

def build_daily(provider, *, macro_enabled=False, run_date=None, write=True, log_forecasts=None):
    return _assemble(
        provider, mode="daily", universe=list(config.DEFAULT_TICKERS),
        forecast_set=set(config.CORE_TICKERS), macro_enabled=macro_enabled,
        run_date=run_date, write=write, log_forecasts=log_forecasts,
    )


def build_stock(provider, ticker, *, mode="stock", event=None, run_date=None, write=True, log_forecasts=None):
    ticker = ticker.upper()
    universe = [ticker, "SPY", "QQQ", "^VIX"]
    return _assemble(
        provider, mode=mode, universe=universe, forecast_set={ticker},
        event=event, focus_ticker=ticker, run_date=run_date, write=write,
        log_forecasts=log_forecasts,
    )


def build_earnings(provider, ticker, *, event="earnings preview", run_date=None, write=True, log_forecasts=None):
    return build_stock(provider, ticker, mode="earnings", event=event,
                       run_date=run_date, write=write, log_forecasts=log_forecasts)


def build_macro(provider, event, *, run_date=None, write=True, log_forecasts=None):
    universe = ["SPY", "QQQ", "^VIX", "DX-Y.NYB"]
    return _assemble(
        provider, mode="macro", universe=universe,
        forecast_set=set(config.CORE_TICKERS), macro_enabled=True, event=event,
        run_date=run_date, write=write, log_forecasts=log_forecasts,
    )
