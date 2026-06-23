"""Load and render prompt templates from editorial/prompts/.

Templates use ``{{TOKEN}}`` placeholders (double braces) so JSON braces in the
injected content never collide with Python str.format.
"""
from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load(name: str) -> str:
    """Load a prompt template by file stem (e.g. 'daily_brief')."""
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text()


def render(template: str, **tokens: str) -> str:
    """Replace ``{{TOKEN}}`` placeholders. Unprovided tokens become empty."""
    out = template
    for key, value in tokens.items():
        out = out.replace(f"{{{{{key}}}}}", value or "")
    return out
