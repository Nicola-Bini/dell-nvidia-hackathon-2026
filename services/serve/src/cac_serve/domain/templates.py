"""Fixed visitor-facing sentences and formatting helpers for the binder (SCHEMA 8.3 rule 8).

Every word a visitor reads is either a graph fact or one of these templates. Nothing here
reads the database, the clock or a model.
"""

from __future__ import annotations

import re
from typing import Any

GAP_TITLE = "Call us"
GAP_SAY = "We haven't confirmed that yet. Please ask our staff."
OFF_TOPIC_TITLE = "Help"
OFF_TOPIC_SAY = "I can help with our menu, hours, bookings and catering."
MENU_SAY = "Here is our menu."
BUSY_SAY = "We're busy right now — here is our menu."
ALLERGEN_NOTICE = (
    "Before placing your order, please inform your server if a person in your party"
    " has a food allergy."
)
ALLERGEN_WARNING = (
    "We cannot guarantee any dish is free of {allergen}."
    " Please tell your server about your allergy."
)
ALLERGEN_CONTAINS = "Confirmed to contain {allergen}: {names}."
BOOKING_DISCLAIMER = (
    "This is a request, not a confirmed reservation; the restaurant will confirm."
)
MORE_LABEL = "Full menu"
MORE_PRESET = "menu"
FALLBACK_BUSINESS = "the restaurant"
TITLE_MAX = 24
LIST_CAP = 12

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def price(cents: Any) -> str:
    """850 -> "$8.50". Anything that is not a whole number of cents renders as ""."""
    if isinstance(cents, bool) or not isinstance(cents, int) or cents < 0:
        return ""
    return f"${cents // 100:,}.{cents % 100:02d}"


def plain_words(key: str) -> str:
    """A prop key in plain words: "min_headcount" -> "Min headcount"."""
    words = key.replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def plural_label(label: str) -> str:
    """A list title from a label: "GiftCard" -> "Gift cards"."""
    words = _CAMEL.sub(" ", label).split()
    if not words:
        return ""
    text = " ".join([words[0], *(w.lower() for w in words[1:])])
    return text if text.endswith("s") else text + "s"


def fact_value(value: Any) -> str:
    """A prop value as visitor text; "" means the fact is skipped."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list | tuple):
        return ", ".join(part for part in (fact_value(v) for v in value) if part)
    if isinstance(value, dict):
        return ""
    return str(value).strip()


def sentence(text: str) -> str:
    """The text with closing punctuation, so sentences can be joined with a space."""
    text = text.strip()
    if not text or text[-1] in ".!?":
        return text
    return text + "."


def rail_title(first_title: Any, rail_label: Any, component: str) -> str:
    """Surface title (SCHEMA 8.4): the view's title, else the rail label; 24 chars at most."""
    fallback = rail_label if isinstance(rail_label, str) and rail_label else component
    if isinstance(first_title, str) and first_title:
        if len(first_title) <= TITLE_MAX:
            return first_title
        if len(fallback) <= TITLE_MAX:
            return fallback
        return first_title[:TITLE_MAX]
    return fallback[:TITLE_MAX]
