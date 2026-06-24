# kronos-brief — Daily Operating Instructions

How to run the pipeline correctly and produce a market-brief content package every
trading day. Read [`docs/CONTENT_ENGINE_CONTEXT.md`](docs/CONTENT_ENGINE_CONTEXT.md)
for the editorial strategy; this file is the **operations runbook**.

---

## TL;DR — the daily run (two steps, on purpose)

```bash
cd /Users/tui/kronos
.venv/bin/python main.py daily      # 1) build the TEXT package (no ElevenLabs charge)
#    → review compliance, edit the voiceover.txt if needed
.venv/bin/python main.py voice      # 2) voice it once → .mp3 + .srt (uses credits)
```

Generation is **text-only** so you never burn ElevenLabs credits on a draft you
haven't approved. The `voice` step is the *only* thing that uses credits — run it
once, after the script is final. Output lands in `output/YYYY-MM-DD/`.

> Tip: run `source .venv/bin/activate` once per terminal and you can drop the
> `.venv/bin/` prefix (just `python main.py daily --no-audio`).

---

## One-time setup (new machine / fresh clone)

```bash
cd /Users/tui/kronos
uv venv --python 3.13              # create the virtualenv
uv pip install -r requirements.txt # install deps (torch, yfinance, anthropic, …)
cp .env.example .env.local         # then edit .env.local (see below)
```

Put your keys in **`.env.local`** (never committed):

```env
ANTHROPIC_API_KEY=sk-ant-...     # required — Claude script generation
FINNHUB_API_KEY=...              # required — news / "why" behind moves (free at finnhub.io)
ELEVENLABS_API_KEY=...           # required for audio — voiceover (elevenlabs.io)
ELEVENLABS_VOICE_ID=...          # required for audio — the voice to use (see below)
CLAUDE_MODEL=claude-sonnet-4-6   # optional — default model
ELEVENLABS_MODEL=eleven_multilingual_v2   # optional — eleven_turbo_v2_5 is ~half the cost
```

First run downloads the Kronos model from Hugging Face (one time, cached).
Market data (yfinance) and earnings dates need no key.

**Picking a voice ID:** in ElevenLabs → Voices, choose (or clone) a voice → copy
its **Voice ID** → paste into `ELEVENLABS_VOICE_ID`.

**Cost / credits (measured):** ElevenLabs Creator = **121k credits/month**. A real
condensed daily (~3.3k chars on `turbo_v2_5`) measured **~915 credits ≈ $0.17**.
So 21 dailies/month ≈ **19k credits (~16% of the plan, ~$3.50)** — leaving ~100k
for stock/earnings/macro videos and Shorts. Two things keep it cheap: (1) **turbo**
(the default), and (2) the **two-step workflow** — editing/re-running the *script*
is free; you only spend credits on the final `voice` run.

---

## Daily workflow (the runbook)

1. **Generate the text package**
   ```bash
   .venv/bin/python main.py daily
   ```
   Text only — no ElevenLabs charge. Watch the summary line for the output folder
   and compliance verdict; it also prints the `voice` command to run next.

2. **Review compliance first** — open `daily_brief_DATE_compliance.md`.
   - `APPROVE` → good to use.
   - `REVISE` → read the flagged lines; either hand-edit the script or re-run.
   - `REJECT` → do not publish; fix the issue (usually fabricated data or advice)
     and re-run.

3. **Read the script** — `daily_brief_DATE.md`. Sanity-check it against the real
   market (does the read match what actually happened?).

4. **Voice it** — once the script is approved:
   ```bash
   .venv/bin/python main.py voice                 # today's daily brief
   .venv/bin/python main.py voice --date 2026-06-23
   .venv/bin/python main.py voice --file output/DATE/stock_review_NVDA_DATE_voiceover.txt
   ```
   This reads the (possibly hand-edited) `*_voiceover.txt`, generates
   `daily_brief_DATE.mp3` + `daily_brief_DATE.srt` (captions timed from ElevenLabs
   word alignment), and prints the estimated credit cost. It's the **only** step
   that uses credits — so editing/re-running the *script* is free.

5. **Pull the charts** — `daily_brief_DATE_charts.md` lists exactly which
   TradingView charts to capture, the timeframe, and which segment each pairs with.

6. **Assemble in CapCut** — drop in the voiceover audio + the charts, following the
   chart manifest's segment order.

7. **Title / description / clips** —
   - `daily_brief_DATE_youtube_metadata.md` → title options, description (full
     disclaimer included), pinned comment, hashtags, chapter timestamps.
   - `daily_brief_DATE_shorts.md` → 3–5 Shorts/Reels/TikTok clip ideas.

8. **Human review, then post.** Nothing auto-posts — you are the final check.

---

## Content modes

| Command | Produces |
|---|---|
| `python main.py daily` | Broad daily market brief — **text package** (default) |
| `python main.py stock NVDA` | Standalone single-stock review (text) |
| `python main.py earnings NVDA --event "earnings preview"` | Earnings preview/reaction (text) |
| `python main.py macro --event "FOMC decision"` | Macro-event video (text) |
| `python main.py voice [--date D] [--file PATH]` | **Audio step** — `.mp3` + `.srt` from an approved voiceover.txt (uses credits) |
| `python main.py validate` | Reconcile past forecasts vs. actuals (accuracy log) |

Offline test (no live data / no API spend on data, uses a saved packet):
```bash
.venv/bin/python main.py daily --from-fixture tests/fixtures/sample_market_packet.json --no-audio
```

Flags: `--event "..."` labels macro/earnings videos · `--from-fixture PATH` uses a
saved packet instead of fetching live · `--date` / `--file` target the `voice`
step. (Generation is always text-only; `--no-audio` is still accepted but is now
the default behaviour.)

---

## Output files (per run, in `output/YYYY-MM-DD/`)

```text
daily_brief_DATE.md                  # the full segmented script
daily_brief_DATE_voiceover.txt       # clean spoken narration (+ short disclaimer)
daily_brief_DATE_charts.md           # TradingView chart pull-list
daily_brief_DATE_shorts.md           # 3–5 short-form clip ideas
daily_brief_DATE_youtube_metadata.md # titles, description, pinned comment, tags, chapters
daily_brief_DATE_compliance.md       # approve / revise / reject report
daily_brief_DATE.mp3                  # voiceover audio (unless --no-audio)
daily_brief_DATE.srt                  # captions, timed (unless --no-audio)
packet_daily_DATE.json               # the raw data packet Claude was given (for auditing)
```

Stock/earnings/macro modes use the same six files with a different prefix
(`stock_review_TICKER_DATE.*`, `earnings_TICKER_DATE.*`, `macro_event_SLUG_DATE.*`).

---

## When to run

- **After the US close** (evening ET) is the natural slot: the brief recaps the
  completed session and projects the *next* session, and the overnight global
  lead-in (Asia/Europe) is captured via the quote-aware data layer.
- **Skip non-trading days** (weekends, US market holidays) — there's no new session
  to brief.
- The date stamp comes from the day you run it, so run it on the day you intend the
  brief to cover.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ANTHROPIC_API_KEY is not set` | Add it to `.env.local`. The packet still builds; only Claude generation is blocked. |
| News shows `unavailable` in the brief | Add `FINNHUB_API_KEY` to `.env.local` (free at finnhub.io). |
| A ticker is missing / failed | It's logged in `packet ... "errors"` and skipped — the run continues. yfinance occasionally hiccups; re-run. |
| Overnight foreign index looks wrong | The data layer reads the live quote when daily history lags, and flags anything still stale — spot-check `packet_daily_DATE.json` → `cross_market`. |
| Compliance `REVISE`/`REJECT` | Open the compliance file, address the flagged lines, re-run (it overwrites the same files). |
| Want to re-read the latest brief | `cat output/$(date +%F)/daily_brief_$(date +%F).md` |

---

## What's automated vs. manual (current state)

**Automated:** market data + overnight global lead-in + technicals + Kronos
projection + news/earnings correlation → structured packet → Claude script,
voiceover text, chart manifest, shorts, YouTube metadata, compliance review,
**ElevenLabs voiceover (.mp3), and timed captions (.srt).**

**Still manual (by design, until proven):** video assembly (CapCut), pulling
charts from TradingView, and posting. Human review before publishing is
intentional — see the roadmap in [`README.md`](README.md).

> Later: optional scheduling. Until then, keep a human in the loop on every post.
