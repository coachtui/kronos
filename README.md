# kronos-brief

Local-first Python pipeline for a faceless finance channel. It turns market
data + technical signals + an optional [Kronos](https://github.com/shiyu-coder/Kronos)
ML forecast into a Claude-generated market brief and ElevenLabs voiceover.

**Design principle:** Kronos is *one signal*, not the source of truth. The brief
reads like disciplined market analysis, never a guaranteed prediction.

> 📌 **Future agents:** read [`docs/CONTENT_ENGINE_CONTEXT.md`](docs/CONTENT_ENGINE_CONTEXT.md)
> before modifying this project. It is the working memory for content strategy,
> editorial framework, tone rules, compliance guardrails, and what must NOT be
> reused from the old weekly-article prompt.

## Status — Milestone 3 ✅ (mode-based content engine)

Builds a market packet, then generates a full **text content package** with
Claude (`claude-sonnet-4-6`, configurable): long-form segmented script, clean
voiceover text, chart manifest, 3–5 shorts ideas, YouTube metadata, and a
compliance report. Four content **modes**, each with its own structure and
output naming. No audio, captions, video, or posting yet.

```bash
python main.py daily --no-audio                              # broad daily market brief (default)
python main.py stock NVDA --no-audio                         # individual stock review
python main.py earnings NVDA --event "earnings preview" --no-audio
python main.py macro --event "FOMC decision" --no-audio
python main.py validate                                      # reconcile forecasts (M6 stub)

# offline (no live fetch):
python main.py daily --from-fixture tests/fixtures/sample_market_packet.json --no-audio
```

Backward-compatible flag form: `python main.py --no-audio` → daily;
`python main.py --stock NVDA` → a **separate** stock review (not inside the
daily brief); `python main.py --macro` → daily with a macro section, or
`--macro --event X` → a separate macro-event video.

**Editorial direction:** the forecasting model is invisible — the word "Kronos"
never appears in any script (it lives only as an internal `projection` signal in
the packet). The daily brief is a **whole-market view** (no auto stock spotlight)
that synthesizes price structure, volatility, the dollar, sector rotation, and
any available macro/rates/sentiment into a conditional base case.

Requires `ANTHROPIC_API_KEY` in `.env.local` (and optional `CLAUDE_MODEL`). If
missing, the packet is still produced and the run exits with a clear message.

**Output naming** (under `output/YYYY-MM-DD/`), 6 files per package:

```text
daily_brief_DATE.{md,_voiceover.txt,_charts.md,_shorts.md,_youtube_metadata.md,_compliance.md}
stock_review_TICKER_DATE.*
earnings_TICKER_DATE.*
macro_event_SLUG_DATE.*
```

Compliance is **hybrid**: a deterministic offline lexical scan (banned advice/
hype, any "Kronos" mention, technicals-only claims, a spotlight inside a daily
brief, missing disclaimer) merged with Claude's nuanced review (fabricated data,
unsupported claims). Claude uses only packet data; missing fields are stated as
unavailable, never invented.

### Mode structures

| Mode | Segments (high level) |
|---|---|
| `daily` | INTRO · MARKET SNAPSHOT · SPY/QQQ STRUCTURE · VIX · DXY · SECTOR ROTATION · MACRO/SENTIMENT (if avail) · RISK MATRIX · **DAILY PROJECTION** · BULL/NEUTRAL/BEAR · WHAT WOULD CHANGE THE VIEW · OUTRO · DISCLAIMER |
| `stock` | SNAPSHOT · PRICE STRUCTURE · RELATIVE STRENGTH vs SPY/QQQ · KEY LEVELS · CATALYSTS/EARNINGS (if avail) · RISK · SETUP PROJECTION · scenarios · OUTRO · DISCLAIMER |
| `earnings` | WHY IT MATTERS · EXPECTATIONS (if avail) · RECENT PRICE ACTION · KEY METRICS · IMPLIED MOVE (if avail) · BULL/BEAR CASE · POST-EARNINGS LEVELS · OUTRO · DISCLAIMER |
| `macro` | WHAT THE EVENT IS · WHY IT MATTERS · SETUP BEFORE · SPY/QQQ REACTION LEVELS · VIX/DXY/RATES · BULLISH/BEARISH REACTION · WHAT TO WATCH AFTER · OUTRO · DISCLAIMER |

**Output:** `output/YYYY-MM-DD/daily_brief_YYYY-MM-DD.json`
**Offline fixture:** `tests/fixtures/sample_market_packet.json` (mock data, for prompt testing without live calls)

### Packet fields

**Implemented (real, computed data):**

- Per ticker (SPY, QQQ, ^VIX, DXY[`DX-Y.NYB`→`DX=F` fallback], XLK/XLF/XLE/XLI/XLY/XLP/XLU/XLV):
  latest & previous close, daily % change, 20/50/200-day MAs, RSI(14), ATR(14),
  support/resistance levels, trend & volatility classification, price-vs-MAs.
- Kronos block per ticker: forecast for SPY/QQQ (+`--stock`); others marked `skipped`.
- `market_regime`: risk tone, volatility tone, sector leadership/laggards,
  SPY/QQQ trend summaries, VIX summary, DXY summary.

**Placeholders (marked `"status": "unavailable"` until a provider is added):**

- `fear_greed` (CNN Fear & Greed) · `macro_calendar` · `rates_summary` (Fed/rates)
  · `wall_street_consensus`.

Each ticker and each major section carries a `status` field, and per-ticker fetch
failures are collected in `packet.errors` without crashing the run.

## Setup

Requires Python 3.10+ (built/tested on 3.13). Uses [`uv`](https://docs.astral.sh/uv/).

```bash
uv venv --python 3.13
uv pip install -r requirements.txt
cp .env.example .env        # fill in keys as later milestones need them
.venv/bin/python main.py --stock SPY --no-audio
```

The first run downloads the Kronos-mini weights from Hugging Face (small,
~tens of MB; cached under `HF_HOME` / `~/.cache/huggingface`). Kronos runs on
CPU by default (`KRONOS_DEVICE=cpu`; `mps`/`cuda:0` also supported).

## Layout

| Path | Role |
|------|------|
| `config.py` | tickers, model + path settings, env loading |
| `providers/` | data provider abstraction (`yfinance`, `mock`) + normalized OHLCV schema + caching |
| `signals/technicals.py` | MAs, RSI, ATR, trend & volatility classification |
| `signals/levels.py` | support/resistance from recent swing points |
| `signals/regime.py` | market regime (risk/vol tone, sector rotation, summaries) |
| `signals/packet.py` | assembles the structured market source packet JSON |
| `editorial/brief_generator.py` | Claude call → content package (structured output) |
| `editorial/compliance.py` | hybrid compliance review (local scan + Claude) |
| `editorial/content_package.py` | renders the content-package output files |
| `media/elevenlabs.py` | ElevenLabs TTS (with-timestamps) |
| `media/captions.py` | builds `.srt` from word-level alignment |
| `editorial/prompt_loader.py` + `prompts/` | shared house rules + per-mode templates (daily, stock, earnings, macro, shorts, compliance) |
| `signals/kronos_predictor.py` | Kronos wrapper, graceful failure |
| `signals/validation.py` | `logs/forecast_history.csv` — forecast accuracy log |
| `vendor/kronos/` | vendored Kronos `model/` package (MIT, from upstream) |
| `main.py` | CLI orchestration |

## Roadmap

- **M1** ✅ SPY fetch + cache + Kronos forecast + log + graceful failure
- **M2** ✅ Full ticker universe, technical signals, structured brief JSON packet
- **M3** ✅ Claude content package — script + voiceover text + charts + shorts + metadata + compliance
- **M4** ✅ ElevenLabs voiceover (.mp3) + timed captions (.srt)
- **M5** `--stock` spotlight + `--macro` segment
- **M6** `--validate` outcome matching + Kronos accuracy report
- **M7** human-review workflow before any posting

## Disclaimer

Educational / informational only. Not financial advice. Model forecasts are
probabilistic and may be wrong.
