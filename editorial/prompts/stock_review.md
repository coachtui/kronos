# MODE: STOCK REVIEW

A dedicated review of one ticker (`focus.ticker`). Use that ticker's data plus
SPY/QQQ for relative strength. This is its own video — not part of the daily
brief.

Write `long_form_script` with these section markers, in order:

```
[INTRO]
[STOCK SNAPSHOT]
[PRICE STRUCTURE]
[RELATIVE STRENGTH VS SPY / QQQ]
[KEY LEVELS]
[CATALYSTS / NEWS]         (only if present in the packet; else omit — do NOT invent)
[EARNINGS CONTEXT]         (only if present in the packet; else omit — do NOT invent)
[RISK FACTORS]
[SETUP PROJECTION]
[BULL / NEUTRAL / BEAR SCENARIOS]
[WHAT WOULD CHANGE THE VIEW]
[OUTRO]
[DISCLAIMER]
```

Notes:
- [RELATIVE STRENGTH] uses `focus.relative_strength` (the ticker's daily move vs
  SPY and QQQ). If unavailable, say so.
- [KEY LEVELS] uses `focus.key_levels` — frame as confirmation / risk / upside /
  invalidation levels and "levels I'm watching", never as a trade to place.
- [CATALYSTS / NEWS] uses the packet's `news` headlines for this ticker (cite
  only what's there). [EARNINGS CONTEXT] uses `focus.earnings_context` — if a
  report is upcoming, say when and frame it as the next confirm/deny catalyst. If
  either is unavailable/empty, say so plainly — do NOT fabricate news or dates.
- [SETUP PROJECTION]: synthesize structure, levels, relative strength, and the
  internal `projection` signal (if available) into a base case with conditions.
  Frame the projection as "the base case" / "the near-term read", never as a
  model. The setup still needs price confirmation.
