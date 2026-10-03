"""POST /v1/intent: validate the text, then run the pipeline (SCHEMA 8.5)."""

from __future__ import annotations

from typing import Any

from cac_serve.services import pipeline


class InvalidText(ValueError):
    """The visitor's text is empty or too long (HTTP 422). Never carries the text itself."""


def clean_text(text: str, max_chars: int) -> str:
    """Trim the text and check it is 1..max_chars characters (SCHEMA 8.5 step 1)."""
    trimmed = text.strip()
    if not 1 <= len(trimmed) <= max_chars:
        raise InvalidText(f"text must be 1 to {max_chars} characters")
    return trimmed


def handle_intent(
    text: str, session_id: str, channel: str, context: dict[str, Any] | None = None
) -> dict:
    """Return the Surface for one visitor intent. `context` (refinement) is P1 and ignored."""
    return pipeline.run_intent(text, session_id, channel).surface
