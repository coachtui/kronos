"""Speech text normalization — fix patterns that TTS engines mis-read.

The main offender is currency: ElevenLabs reads "$733.84" as "733 dollars and
84 dollars". The voiceover prompt already prefers rounded, dollar-sign-free
numbers, but this is the deterministic backstop applied right before synthesis,
so a stray "$733.84" is always spoken as "733 dollars and 84 cents".
"""
from __future__ import annotations

import re

# $1,234.56  /  $733.84  (two-decimal cents)
_CURRENCY_CENTS = re.compile(r"\$(\d[\d,]*)\.(\d{2})\b")
# $1,500  /  $733  (whole dollars, no decimal)
_CURRENCY_WHOLE = re.compile(r"\$(\d[\d,]*)(?!\d)")


def _cents(m: re.Match) -> str:
    dollars = int(m.group(1).replace(",", ""))
    cents = int(m.group(2))
    if cents == 0:
        return f"{dollars} dollars"
    return f"{dollars} dollars and {cents} cents"


def _whole(m: re.Match) -> str:
    return f"{int(m.group(1).replace(',', ''))} dollars"


def normalize_for_speech(text: str) -> str:
    text = _CURRENCY_CENTS.sub(_cents, text)
    text = _CURRENCY_WHOLE.sub(_whole, text)
    return text
