"""Central configuration for kronos-brief.

Loads .env, defines ticker universe, model settings, and paths.
No secrets live here — keys come from the environment only.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env first, then .env.local (local overrides — put real secrets here).
# Resolve relative to this file so it works regardless of the launch directory.
_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE / ".env")
load_dotenv(_HERE / ".env.local", override=True)

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
VENDOR_KRONOS_DIR = BASE_DIR / "vendor" / "kronos"
FORECAST_LOG = LOGS_DIR / "forecast_history.csv"
RUN_LOG = LOGS_DIR / "run_log.jsonl"

for _d in (CACHE_DIR, OUTPUT_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Ticker universe ---
# DXY is unreliable on Yahoo; yfinance_provider tries DX-Y.NYB then DX=F.
INDEX_TICKERS = ["^VIX", "DX-Y.NYB"]
CORE_TICKERS = ["SPY", "QQQ"]
SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLI", "XLY", "XLP", "XLU", "XLV"]
DEFAULT_TICKERS = CORE_TICKERS + INDEX_TICKERS + SECTOR_ETFS

# Which tickers get a Kronos forecast vs. context-only.
# Indices (VIX/DXY) are out-of-distribution for Kronos -> context only.
FORECAST_TICKERS = set(CORE_TICKERS)  # extended by --stock at runtime

# --- Data provider ---
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "yfinance")
HISTORY_PERIOD = "2y"   # enough for 200D MA + Kronos lookback
BAR_INTERVAL = "1d"

# --- Kronos model ---
KRONOS_MODEL_NAME = os.getenv("KRONOS_MODEL_NAME", "NeoQuasar/Kronos-mini")
KRONOS_TOKENIZER_NAME = os.getenv("KRONOS_TOKENIZER_NAME", "NeoQuasar/Kronos-Tokenizer-2k")
KRONOS_DEVICE = os.getenv("KRONOS_DEVICE", "cpu")  # cpu | mps | cuda:0
KRONOS_MAX_CONTEXT = 512   # mini supports 2048; 512 is fast and plenty for daily bars
KRONOS_LOOKBACK = 400      # daily bars fed as context
KRONOS_PRED_LEN = 1        # next-session forecast
KRONOS_TEMPERATURE = 1.0
KRONOS_TOP_P = 0.9
KRONOS_SAMPLE_COUNT = 1

# --- News + catalysts feeds (the "why") ---
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
NEWS_HEADLINE_LIMIT = int(os.getenv("NEWS_HEADLINE_LIMIT", "8"))
# Market-moving names checked for upcoming earnings in daily/macro briefs.
EARNINGS_WATCHLIST = [
    "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META",
    "AVGO", "MU", "AMD", "TSLA", "NFLX", "JPM",
]
EARNINGS_HORIZON_DAYS = int(os.getenv("EARNINGS_HORIZON_DAYS", "7"))

# --- Overnight / cross-market lead-in (broad & general, NOT industry-specific) ---
# The global equity sessions + cross-asset moves that PRECEDE the US open. Their
# latest daily bar is the overnight backdrop the US often reacts to. Claude traces
# the day's actual correlation from this data dynamically — we don't hardcode a
# theme. (ticker, name, region)
# Backbone = US-listed regional ETFs: they reprice the overnight foreign move at
# the US open and are RELIABLY fresh (native indices like ^KS11 lag a day in
# yfinance). Native indices kept for the recognizable headline number but
# staleness-flagged. Plus cross-asset (oil/gold/rates/credit).
CROSS_MARKET = [
    ("EWY", "South Korea (US ETF)", "Asia"),
    ("EWJ", "Japan (US ETF)", "Asia"),
    ("MCHI", "China (US ETF)", "Asia"),
    ("VGK", "Europe (US ETF)", "Europe"),
    ("^KS11", "KOSPI (native index)", "Asia"),
    ("^N225", "Nikkei 225 (native)", "Asia"),
    ("CL=F", "Crude Oil", "Commodity"),
    ("GC=F", "Gold", "Commodity"),
    ("^TNX", "US 10Y Yield", "Rates"),
    ("HYG", "US High-Yield Credit", "Credit"),
]

# --- Claude script generation (Milestone 3) ---
# User-selected model; claude-sonnet-4-6 is the configured default.
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "16000"))

# --- Disclaimers (injected deterministically so they are always verbatim) ---
# Spoken: short, read aloud in the voiceover + the script's [DISCLAIMER] segment.
SPOKEN_DISCLAIMER = (
    "This is educational content, not financial advice. The brief is AI-assisted "
    "and based on market data, news context, and quantitative signals. Projections "
    "can be wrong, so always verify the data and make your own decisions."
)
# Full: written-only, used in the YouTube metadata / description.
FULL_DISCLAIMER = (
    "This video is for educational and informational purposes only. Nothing here is "
    "financial advice or a recommendation to buy, sell, or hold any security. This "
    "brief is AI-assisted and may use quantitative signals as part of the research "
    "process. Projections are probabilistic and may be wrong. Always do your own "
    "research and consult a qualified financial professional before making "
    "investment decisions."
)

# --- API keys (read lazily by the layers that need them) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
