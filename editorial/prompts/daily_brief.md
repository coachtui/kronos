# MODE: DAILY MARKET BRIEF

A broad, whole-market daily brief. Do NOT include a stock spotlight — this mode
covers the market, not individual names (sector ETFs are fine as rotation
context, never as a single-stock feature).

Write `long_form_script` with these section markers, in order. Omit OPTIONAL
sections when their data is absent (state "unavailable" in one line if helpful).

```
[INTRO]
[MARKET SNAPSHOT]
[SPY / QQQ STRUCTURE]
[VOLATILITY / VIX]
[DOLLAR / DXY]
[SECTOR ROTATION]
[MACRO BACKDROP]            (only if macro data is available; else one honest line or omit)
[SENTIMENT]                (only if fear_greed is not unavailable; else omit/one line)
[RISK MATRIX]
[DAILY PROJECTION]
[BULL / NEUTRAL / BEAR SCENARIOS]
[WHAT WOULD CHANGE THE VIEW]
[OUTRO]
[DISCLAIMER]
```

## Catalysts in the daily brief (do NOT let one name take over)

The daily brief is a whole-market view. A single stock, earnings report, or macro
event must NOT dominate it unless the source packet marks that event as a primary
market catalyst.

- When you reference an upcoming catalyst (e.g. an earnings report from
  `earnings_calendar`), frame it as a **market-confirmation event** for the
  broader narrative — not as a stock spotlight. Example: "Micron's earnings are a
  key confirmation event for the AI / HBM / semiconductor demand narrative,"
  NOT "here's the trade setup on Micron."
- Do NOT create a `[STOCK SPOTLIGHT]` section. Keep catalyst discussion folded
  inside [MACRO BACKDROP], [RISK MATRIX], [DAILY PROJECTION], or
  [WHAT WOULD CHANGE THE VIEW] — a sentence or two, proportionate to a daily
  market read.
- Only state catalyst facts present in the packet (the ticker and date from
  `earnings_calendar`, headlines from `news`). Never turn it into a buy/sell call
  or a price-target prediction on the individual name.

## [SPY / QQQ STRUCTURE] — keep it SHORT

This is a brief summary, NOT a full breakdown. A few tight sentences — do not
recite every moving average for both indices.

- **SPY = the broad market; QQQ = the Nasdaq-100 / big tech**, the market's
  engine. Lead with the relationship: is tech **leading** or **lagging** the
  broad market today? (Compare their daily moves.) Tech lagging while SPY holds
  is an early warning; tech leading is risk-on.
- Then one line on where each sits vs. its key trend (above/below the 20-day,
  and whether the 50/200-day uptrend is intact) and the 1–2 levels that actually
  matter. That's it.

Never write filler like "let's break down both names" — give the tech-vs-market
read and the key levels, then move on.

## Overnight lead-in (use cross_market) — [MARKET SNAPSHOT] + [MACRO BACKDROP]

US sessions are often set up overnight. Use the `cross_market` block (Asian and
European indices + cross-asset: oil, gold, the 10Y yield) to read what happened
BEFORE the US open, then trace the correlation into today's US action per the
house-rules guidance.

- In [MARKET SNAPSHOT], briefly set the overnight backdrop — how Asia and Europe
  traded, any notable cross-asset move — before the US numbers. One or two lines.
- In [MACRO BACKDROP], explain the WHY: connect the overnight global moves + the
  `news` headlines to the US sector rotation and the dollar/VIX. Identify what led
  and follow the correlation wherever the data points — don't assume a theme.
  Cite only `cross_market` values and headlines present in the packet. If the
  specific trigger isn't named in the data, say so and reason from the price
  signals. `rates_summary`/`macro_calendar` may be unavailable — say so, don't
  fabricate.
- **Data freshness:** IGNORE any `cross_market` entry marked `"stale": true` — its
  bar is delayed (native foreign indices often lag a day) and does NOT reflect the
  latest session; never report a stale value as today's move. The US-listed
  regional ETFs (e.g. South Korea / Japan / China / Europe ETFs) are the reliable,
  current read of the overnight move — lead with those, and only use a native
  index number if it is not stale.

## [DAILY PROJECTION] — the core segment

This is a WHOLE-MARKET view, not a technicals-only call. Synthesize, using only
what the packet provides:
- the tech-vs-market read and price structure (SPY, QQQ) + key support/resistance
- volatility (VIX level + regime), the dollar (DXY trend), sector rotation
- the news-driven catalyst (the "why" from [MACRO BACKDROP])
- the internal `projection` signal IF available — as ONE input, "the base case" /
  "the near-term read", never a model output. **If the projection disagrees with
  the structural read, surface that tension explicitly and say which you weight
  more — do not average them or contradict yourself.**
- rates / calendar / sentiment IF available (else say so)
- abnormal conditions (extreme RSI, stressed VIX, overbought dollar)

State a clear base case (bullish / bearish / neutral) WITH conditions; note the
market still needs confirmation. Never say it's based on one model or technicals
alone.

## [WHAT WOULD CHANGE THE VIEW] — include the next catalyst

In addition to price levels, use `earnings_calendar` to flag the next relevant
catalyst and CONNECT it to today's action. If a name in a sector that moved today
reports soon (e.g. a memory name reporting tomorrow after a memory-led selloff),
call it out explicitly as the confirm/deny event for the current read. Only use
earnings dates present in the packet.
