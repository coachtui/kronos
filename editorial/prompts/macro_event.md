# MODE: MACRO EVENT

A video built around a named macro event (`event`, e.g. "FOMC decision",
"CPI release"). Use SPY/QQQ/VIX/DXY context from the packet.

Write `long_form_script` with these section markers, in order:

```
[INTRO]
[WHAT THE EVENT IS]
[WHY IT MATTERS]
[MARKET SETUP BEFORE THE EVENT]
[SPY / QQQ REACTION LEVELS]
[VIX / DXY / RATES CONTEXT]
[BULLISH MARKET REACTION]
[BEARISH MARKET REACTION]
[WHAT TO WATCH AFTER THE EVENT]
[OUTRO]
[DISCLAIMER]
```

Notes:
- [WHAT THE EVENT IS] / [WHY IT MATTERS]: describe the event TYPE in general,
  educational terms. Do NOT invent a specific date, time, consensus number,
  prior reading, or outcome unless the packet provides it.
- [MARKET SETUP BEFORE THE EVENT] and [SPY / QQQ REACTION LEVELS] use the packet's
  price structure, support, and resistance — frame as "levels I'm watching".
- [VIX / DXY / RATES CONTEXT]: use the VIX and DXY summaries from the packet.
  `rates_summary` is likely `"unavailable"` — if so, say rates data isn't wired
  in yet rather than fabricating yields or Fed funds.
- [BULLISH] / [BEARISH MARKET REACTION]: lay out conditional scenarios tied to
  the reaction levels. No advice, no predicted outcome stated as fact.
