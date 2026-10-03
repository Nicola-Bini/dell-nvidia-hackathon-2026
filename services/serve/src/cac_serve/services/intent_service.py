"""POST /v1/intent. STUB (wp2): golden surfaces by exact text; the pipeline replaces the body."""

from __future__ import annotations

from typing import Any

from cac_serve.services.golden import load_golden, load_index


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
    """Return the Surface for one visitor intent.

    STUB: a text listed in fixtures/surfaces/index.json gets its golden surface verbatim;
    everything else gets the off-topic surface. No model call, no log row yet.
    """
    filename = load_index().get(text)
    if filename is None:
        return load_golden("off_topic")
    return load_golden(filename.removesuffix(".json"))
