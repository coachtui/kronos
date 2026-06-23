"""Claude script generation (Milestone 3).

Takes the structured market source packet and produces a full text content
package via the Anthropic API, using structured outputs (output_config.format)
so the response is guaranteed-parseable JSON.

Model is configurable (config.CLAUDE_MODEL; default claude-sonnet-4-6). The
Anthropic client is read from the environment (ANTHROPIC_API_KEY) and can be
injected for testing.
"""
from __future__ import annotations

import json
from typing import Any

import config
from editorial import prompt_loader


class MissingAPIKeyError(RuntimeError):
    """Raised when ANTHROPIC_API_KEY is absent and no client was injected."""


# --- Structured output schema (output_config.format) ---
# Note: structured outputs don't support min/maxLength etc.; keep types simple.
CONTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "long_form_script": {"type": "string"},
        "voiceover": {"type": "string"},
        "thesis": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "stance": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
                "conditions": {"type": "string"},
            },
            "required": ["stance", "conditions"],
        },
        "charts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "ticker": {"type": "string"},
                    "timeframe": {"type": "string"},
                    "segment": {"type": "string"},
                    "focus": {"type": "string"},
                    "overlays": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                },
                "required": ["ticker", "timeframe", "segment", "focus", "overlays", "why_it_matters"],
            },
        },
        "shorts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "hook": {"type": "string"},
                    "start_timestamp": {"type": "string"},
                    "end_timestamp": {"type": "string"},
                    "spoken_excerpt": {"type": "string"},
                    "caption": {"type": "string"},
                    "visual": {"type": "string"},
                    "platform_note": {"type": "string"},
                },
                "required": ["title", "hook", "start_timestamp", "end_timestamp",
                             "spoken_excerpt", "caption", "visual", "platform_note"],
            },
        },
        "youtube_metadata": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title_options": {"type": "array", "items": {"type": "string"}},
                "recommended_title": {"type": "string"},
                "description": {"type": "string"},
                "pinned_comment": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
                "chapters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "timestamp": {"type": "string"},
                            "label": {"type": "string"},
                        },
                        "required": ["timestamp", "label"],
                    },
                },
                "disclaimer": {"type": "string"},
            },
            "required": ["title_options", "recommended_title", "description",
                         "pinned_comment", "hashtags", "chapters", "disclaimer"],
        },
    },
    "required": ["long_form_script", "voiceover", "thesis", "charts", "shorts", "youtube_metadata"],
}


def _make_client():
    if not config.ANTHROPIC_API_KEY:
        raise MissingAPIKeyError(
            "ANTHROPIC_API_KEY is not set. Add it to .env (see .env.example) "
            "to enable Claude script generation."
        )
    import anthropic

    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


MODE_TEMPLATE = {
    "daily": "daily_brief",
    "stock": "stock_review",
    "earnings": "earnings_review",
    "macro": "macro_event",
}


def _build_system_prompt(mode: str) -> str:
    """Assemble the system prompt: shared house rules + mode structure + shorts."""
    template = MODE_TEMPLATE.get(mode)
    if template is None:
        raise ValueError(f"Unknown content mode: {mode!r}")
    return "\n\n".join([
        prompt_loader.load("_house_rules"),
        prompt_loader.load(template),
        prompt_loader.load("shorts"),
    ])


def _extract_json(response) -> dict:
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise RuntimeError("Claude returned no text block.")
    return json.loads(text)


def generate_content_package(
    packet: dict, mode: str | None = None, client=None, model: str | None = None
) -> dict:
    """Generate the full content package for the packet's mode.

    Raises MissingAPIKeyError if no key/client is available.
    """
    client = client or _make_client()
    model = model or config.CLAUDE_MODEL
    mode = mode or packet.get("mode", "daily")

    system = _build_system_prompt(mode)
    user = (
        "Here is today's market source packet (JSON). Generate the complete "
        "content package. Use ONLY data present in this packet — do not invent "
        "anything.\n\n```json\n" + json.dumps(packet, indent=2) + "\n```"
    )

    response = client.messages.create(
        model=model,
        max_tokens=config.CLAUDE_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": CONTENT_SCHEMA}},
    )
    return _extract_json(response)
