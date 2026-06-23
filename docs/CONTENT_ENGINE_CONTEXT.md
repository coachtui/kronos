# kronos-brief — Content Engine Context

> **Working memory for this repo.** Future Claude Code / Codex sessions should
> read this file *before* modifying the project. It captures the content
> strategy, editorial framework, technical pipeline, and explicit do-not-reuse
> rules carried over from an older weekly-article prompt.

---

## 1. What this project is

A **local-first Python content engine** for a **faceless finance YouTube
channel**. Each trading day it produces a reviewable content package — not a
single video — from market data, technical signals, an optional Kronos ML
forecast, and Claude-generated copy.

Outputs (eventual full package): daily market brief script, chart manifest,
Shorts/Reels/TikTok clip ideas, YouTube metadata, and optional ElevenLabs
voiceover + captions.

**Guiding principle:** the brief reads like disciplined market analysis, never a
guaranteed prediction engine. Quality is proven by human review before any
publishing is automated.

---

## 2. Status

**Milestone 1 — COMPLETE & verified:**

- SPY OHLCV fetch via yfinance
- local parquet caching (reruns don't refetch same-day)
- Kronos-mini loads locally from Hugging Face
- next-session forecast generation
- terminal forecast output (last close, predicted close, direction, magnitude, status)
- graceful failure handling (Kronos failure → `unavailable`, run continues)
- forecast logging to `/logs/forecast_history.csv`

Roadmap M2–M7 is in `README.md`. Next up: M2 (full ticker universe + technical
signals + structured brief JSON packet).

---

## 3. Editorial framework (carried from the old weekly SPY prompt)

The old weekly **SPY article** prompt is **editorial context only**. Preserve the
*thinking*, not the *plumbing*.

### ✅ Preserve these ideas

- SPY technical analysis
- VIX volatility read
- CNN Fear & Greed sentiment read
- macro snapshot
- risk matrix
- directional thesis
- bull / neutral / bear scenarios
- source discipline (only state data that is actually in the source packet)
- a clear market bias **with conditions**
- "what changes the setup" framing

### ❌ Do NOT preserve or reuse these parts

- HTML article template
- GitHub publishing instructions
- GitHub token (see Security below)
- website index update logic
- article filename logic
- automatic publishing behavior

### 🔐 Security note

If any API token or secret appears in the old prompt, the repo, or git history:
**do not reuse it.** Treat it as compromised — flag it as a secret that must be
**rotated** and moved to `.env`. Never hardcode keys; everything secret is read
from the environment.

---

## 4. Daily YouTube brief structure

The long-form daily brief script uses these clearly-marked segments:

```text
[INTRO]
[MARKET SNAPSHOT]
[SPY / QQQ TECHNICAL STRUCTURE]
[VIX / VOLATILITY READ]
[FEAR & GREED / SENTIMENT READ]
[SECTOR ROTATION]
[MACRO CONTEXT]        optional (--macro)
[STOCK SPOTLIGHT]      optional (--stock TICKER)
[RISK MATRIX]
[DIRECTIONAL THESIS]
[BULL / NEUTRAL / BEAR SCENARIOS]
[WHAT WOULD CHANGE THE SETUP]
[OUTRO]
[DISCLAIMER]
```

---

## 5. Tone

direct · serious · analytical · calm · not promotional · not hype-driven · not
robotic · not meme-stock style.

### Preferred language

- "levels I'm watching"
- "the setup improves if"
- "risk increases below"
- "confirmation would come from"
- "this remains conditional"
- "the model leans"
- "price still needs to confirm"
- "risk/reward improves if"

### Avoid

- "buy" / "sell" / "you should buy"
- "guaranteed" / "easy money" / "load up" / "can't miss"
- "this stock will explode"
- direct position sizing
- personal allocation advice

Replace trade-call language (`entry / target / invalidation`) with:
**confirmation level · risk level · upside level · invalidation level · levels I'm
watching.**

---

## 6. Kronos guidance

Kronos is **one signal, not the source of truth.** Never present a Kronos
forecast as a guaranteed prediction. Describe it as a **probabilistic model
signal that requires price confirmation** — e.g. "the model leans lower, but
price still needs to confirm below X."

---

## 7. Content package outputs

The system should eventually generate, per run, under `output/YYYY-MM-DD/`:

```text
daily_brief_YYYY-MM-DD.md                 long-form script
daily_brief_YYYY-MM-DD.json               structured source packet
daily_brief_YYYY-MM-DD_voiceover.txt      clean spoken text (no chart/production notes)
daily_brief_YYYY-MM-DD_charts.md          chart callout manifest
daily_brief_YYYY-MM-DD_shorts.md          Shorts/Reels/TikTok clip ideas
daily_brief_YYYY-MM-DD_youtube_metadata.md  titles, description, tags, pinned comment
daily_brief_YYYY-MM-DD.mp3                voiceover (optional; --no-audio skips)
daily_brief_YYYY-MM-DD.srt                captions (optional)
```

If audio or captions are skipped, still generate the other files.

---

## 8. Human review rule

**Do not implement auto-posting yet.** The system generates a *reviewable
content package* first. YouTube, TikTok, Instagram, and website publishing stay
**manual** until content quality is proven. Auto-publishing is the last
milestone (M7), gated behind a human-review workflow.

---

## 9. Compliance guardrails (always)

Every generated script must include: educational-content disclaimer,
not-financial-advice disclaimer, AI-assisted-content disclosure (if applicable),
and a statement that model forecasts are probabilistic and may be wrong. No
personalized investment advice, no position sizing, and **no fabricated
catalysts, earnings dates, Fed events, or news** — Claude only uses data present
in the source packet.
