# MODE: EARNINGS PREVIEW / REACTION

An earnings-focused video for one ticker (`focus.ticker`). The `event` field says
whether this is a preview or a reaction. Use the ticker's price data plus SPY/QQQ
context.

Write `long_form_script` with these section markers, in order:

```
[INTRO]
[WHY THIS EARNINGS REPORT MATTERS]
[EXPECTATIONS]             (only if present in the packet; else omit — do NOT invent)
[RECENT PRICE ACTION]
[KEY METRICS TO WATCH]
[OPTIONS / IMPLIED MOVE]   (only if present in the packet; else omit — do NOT invent)
[BULL CASE]
[BEAR CASE]
[POST-EARNINGS LEVELS TO WATCH]
[OUTRO]
[DISCLAIMER]
```

Notes:
- `focus.earnings_context` carries the next earnings DATE (from the packet) — use
  it to ground "when" this report lands. Consensus estimates and `focus.implied_move`
  are still unavailable in this build: OMIT [EXPECTATIONS] and [OPTIONS / IMPLIED
  MOVE] or state in one honest line that estimates / the implied move aren't
  available — do NOT fabricate EPS/revenue numbers or an implied move. Use the
  packet's `news` for recent context, citing only what's there.
- [KEY METRICS TO WATCH] should be framed generically and educationally (e.g.
  "watch revenue growth, margins, and guidance") WITHOUT inventing specific
  numbers the packet doesn't contain.
- [POST-EARNINGS LEVELS TO WATCH] uses `focus.key_levels` — confirmation / risk /
  upside / invalidation levels and "levels I'm watching".
- Keep both [BULL CASE] and [BEAR CASE] balanced and conditional. No advice.
