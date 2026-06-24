"""Compliance review (Milestone 3).

Hybrid review of a generated script:
1. A deterministic local lexical scan (always runs, offline) — catches banned
   advice/hype phrasing and missing disclaimers.
2. Claude's nuanced review (when a key/client is available) — catches fabricated
   data, unsupported claims, and AI-sounding repetition the lexical scan can't.

The two are merged into one report. Local findings alone can already fail a
script, so the gate works even without the API.
"""
from __future__ import annotations

import json
import re
from typing import Any

import config
from editorial import brief_generator, prompt_loader

# High-precision backstop: only UNAMBIGUOUS advice/hype phrasing. Nuanced advice
# detection is Claude's job — bare "buy"/"sell" appear legitimately in narration
# ("not a buy signal") and in disclaimers ("do not buy, sell, or hold"), so they
# are intentionally NOT matched here.
BANNED_PATTERNS = [
    (r"\byou should buy\b", "direct financial advice"),
    (r"\byou should sell\b", "direct financial advice"),
    (r"\b(buy|sell)\s+(now|today|the dip)\b", "advice / timing instruction"),
    (r"\bload up\b", "advice / hype"),
    (r"\bcan'?t miss\b", "hype / guarantee"),
    (r"\beasy money\b", "hype / guarantee"),
    (r"\bguaranteed\b", "overconfident / guarantee"),
    (r"\bwill explode\b", "overconfident / hype"),
    (r"\bto the moon\b", "meme-stock hype"),
]

# Editorial-direction violations (reject-level): the model must stay invisible
# and the analysis must read as a whole-market view, never one-model/technicals.
FORBIDDEN_PATTERNS = [
    (r"\bkronos\b", "public mention of 'Kronos' (internal model name)"),
    (r"\bthe model (says|forecasts|predicts|expects|leans)\b", "names a single forecasting model"),
    (r"\bthe algorithm\b", "names a single algorithm/model"),
    (r"\bthe ai (says|predicts|thinks)\b", "attributes the call to 'the AI'"),
    (r"\bbased (only|solely) on technicals\b", "claims the analysis is technicals-only"),
    (r"\b(purely|just) a technical (call|analysis)\b", "claims the analysis is technicals-only"),
]

COMPLIANCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["pass", "fail"]},
        "flagged_lines": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "line": {"type": "string"},
                    "reason": {"type": "string"},
                    "suggested_rewrite": {"type": "string"},
                },
                "required": ["line", "reason", "suggested_rewrite"],
            },
        },
        "final_recommendation": {"type": "string", "enum": ["approve", "revise", "reject"]},
        "notes": {"type": "string"},
    },
    "required": ["status", "flagged_lines", "final_recommendation", "notes"],
}

_SEVERITY = {"approve": 0, "revise": 1, "reject": 2}


def _local_scan(script: str, mode: str = "daily") -> dict:
    flags: list[dict] = []
    severe = False  # reject-level hit

    for pattern, reason in BANNED_PATTERNS:
        for m in re.finditer(pattern, script, flags=re.IGNORECASE):
            flags.append({"line": _line_of(script, m.start()), "reason": f"banned phrase — {reason}",
                          "suggested_rewrite": "remove / rephrase as a conditional 'levels I'm watching'"})
            if "advice" in reason:
                severe = True

    for pattern, reason in FORBIDDEN_PATTERNS:
        for m in re.finditer(pattern, script, flags=re.IGNORECASE):
            flags.append({"line": _line_of(script, m.start()), "reason": f"editorial violation — {reason}",
                          "suggested_rewrite": "rephrase using projection vocabulary (e.g. 'the base case', 'the near-term read')"})
            severe = True

    if mode == "daily" and re.search(r"\[\s*stock spotlight\s*\]", script, flags=re.IGNORECASE):
        flags.append({"line": "[STOCK SPOTLIGHT]", "reason": "editorial violation — stock spotlight inside a daily brief",
                      "suggested_rewrite": "remove the spotlight; stock features belong in stock-review mode"})
        severe = True

    low = script.lower()
    # A compliant disclaimer disclaims advice — accept common phrasings, e.g.
    # "not financial advice" or "nothing ... constitutes financial advice".
    has_not_advice = bool(
        re.search(r"\b(not|nothing|no|never|don'?t|do not)\b[^.]*\b(financial|investment)\s+advice\b", low)
        or re.search(r"\b(financial|investment)\s+advice\b[^.]*\b(only|educational|informational)\b", low)
    )
    if not has_not_advice:
        flags.append({"line": "[DISCLAIMER]", "reason": "missing not-financial-advice disclaimer",
                      "suggested_rewrite": "add an explicit 'this is not financial advice' line"})
    if "ai-assisted" not in low and "ai assisted" not in low and "ai-generated" not in low:
        flags.append({"line": "[DISCLAIMER]", "reason": "missing AI-assisted-content disclosure",
                      "suggested_rewrite": "disclose that the content is AI-assisted"})

    if severe:
        rec = "reject"
    elif flags:
        rec = "revise"
    else:
        rec = "approve"
    return {"status": "fail" if flags else "pass", "flagged_lines": flags,
            "final_recommendation": rec, "notes": "local lexical scan"}


def _line_of(text: str, idx: int) -> str:
    start = text.rfind("\n", 0, idx) + 1
    end = text.find("\n", idx)
    return text[start: end if end != -1 else len(text)].strip()[:200]


def _claude_review(script: str, packet: dict, mode: str, client, model: str) -> dict | None:
    try:
        client = client or brief_generator._make_client()
    except brief_generator.MissingAPIKeyError:
        return None
    system = prompt_loader.load("compliance_check")
    user = (
        f"CONTENT MODE: {mode}\n\nSCRIPT TO REVIEW:\n\n" + script + "\n\n---\nSOURCE "
        "PACKET (the only data the script is allowed to use):\n\n```json\n"
        + json.dumps(packet, indent=2) + "\n```"
    )
    response = client.messages.create(
        model=model or config.CLAUDE_MODEL,
        max_tokens=config.CLAUDE_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": COMPLIANCE_SCHEMA}},
    )
    text = next((b.text for b in response.content if b.type == "text"), None)
    return json.loads(text) if text else None


_WITHDRAWN_MARKERS = (
    "withdraw", "no change needed", "no genuine violation", "no violation here",
    "not a genuine violation", "no actual violation",
)


def _is_withdrawn(flag: dict) -> bool:
    blob = ((flag.get("reason") or "") + " " + (flag.get("suggested_rewrite") or "")).lower()
    return any(m in blob for m in _WITHDRAWN_MARKERS)


def run_compliance_check(
    script: str, packet: dict, mode: str | None = None, client=None, model: str | None = None
) -> dict:
    """Return a merged compliance report (local scan + optional Claude review)."""
    mode = mode or packet.get("mode", "daily")
    local = _local_scan(script, mode)
    claude = _claude_review(script, packet, mode, client, model)

    if claude is None:
        merged = dict(local)
        merged["notes"] = local["notes"] + " (Claude review skipped — no API key)"
        merged["sources"] = ["local"]
        return merged

    # Drop self-withdrawn / no-issue items the reviewer sometimes still emits.
    claude_flags = [f for f in claude.get("flagged_lines", []) if not _is_withdrawn(f)]
    claude_rec = claude.get("final_recommendation", "approve") if claude_flags else "approve"
    claude_status = claude.get("status", "pass") if claude_flags else "pass"

    flags = local["flagged_lines"] + claude_flags
    rec = max(local["final_recommendation"], claude_rec, key=lambda r: _SEVERITY.get(r, 0))
    status = "fail" if (local["status"] == "fail" or claude_status == "fail") else "pass"
    if not flags:  # nothing real survived → clean
        rec, status = "approve", "pass"
    return {
        "status": status,
        "flagged_lines": flags,
        "final_recommendation": rec,
        "notes": f"local: {local['notes']} | claude: {claude.get('notes', '')}",
        "sources": ["local", "claude"],
    }
