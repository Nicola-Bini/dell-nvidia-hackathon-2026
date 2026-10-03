"""Slots (SCHEMA 8.2): date, time, party_size, headcount. Extracted by code, never the model."""

from __future__ import annotations

import re
from datetime import date

from cac_serve.domain.dates import MONTH_PATTERN, resolve_date

MAX_PARTY_SIZE = 20

_WORDS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
          "eleven", "twelve"]
_WORD_VALUES = {word: value for value, word in enumerate(_WORDS, start=1)}
_NUM = rf"(\d{{1,3}}|{'|'.join(_WORDS)})"
# A count is not the start of a time ("7pm", "7:30"), a date ("10/31", "4th", "4 July") or a
# longer number.
_NOT_DATE_OR_TIME = (
    rf"(?![\d:/])(?!-\d)(?!\s*(?:[ap]\.?m\b|st\b|nd\b|rd\b|th\b|(?:{MONTH_PATTERN})\b))"
)
_PEOPLE = r"(?:people|persons?|guests?|adults|of us|ppl|pax|heads|attendees|diners)"
_GROUP_OF = re.compile(
    r"\b(?:table|booking|reservation|party|group|seats?|dinner|lunch|brunch|room)"
    rf"\s+(?:for|of)\s+{_NUM}\b{_NOT_DATE_OR_TIME}"
)
_N_PEOPLE = re.compile(rf"(?<![\d:/-])\b{_NUM}\s+{_PEOPLE}\b")
_FOR_N = re.compile(rf"\bfor\s+(?:about\s+|around\s+)?{_NUM}\b{_NOT_DATE_OR_TIME}")
_CATERING = re.compile(
    r"\b(?:cater\w*|events?|wedding|banquet|headcount|buffet|reception|corporate|function)\b"
)
_TABLE = re.compile(r"\b(?:table|book\w*|reserv\w*|seat\w*)\b")

_AM_PM = re.compile(r"(?<![\d:/.-])(\d{1,2})(?::([0-5]\d))?\s*([ap])\.?m\b")
_CLOCK = re.compile(r"(?<![\d:/.-])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])")
_NAMED_TIMES = {"noon": "12:00", "midday": "12:00", "midnight": "00:00"}
_NAMED_TIME = re.compile(rf"\b({'|'.join(_NAMED_TIMES)})\b")


def _time(text: str) -> str | None:
    match = _AM_PM.search(text)
    if match and 1 <= int(match[1]) <= 12:
        hour = int(match[1]) % 12 + (12 if match[3] == "p" else 0)
        return f"{hour:02d}:{match[2] or '00'}"
    match = _CLOCK.search(text)
    if match:
        return f"{int(match[1]):02d}:{match[2]}"
    match = _NAMED_TIME.search(text)
    return _NAMED_TIMES[match[1]] if match else None


def _number(raw: str) -> int:
    return _WORD_VALUES[raw] if raw in _WORD_VALUES else int(raw)


def _count(text: str, catering: bool, table: bool) -> int | None:
    """How many people the text names. A bare "for N" counts only in a booking context."""
    match = _GROUP_OF.search(text) or _N_PEOPLE.search(text)
    if not match and (catering or table):
        match = _FOR_N.search(text)
    return _number(match[1]) if match else None


def _people(text: str) -> dict:
    catering = bool(_CATERING.search(text))
    table = bool(_TABLE.search(text))
    count = _count(text, catering, table)
    if not count:
        return {}
    if (catering and not table) or count > MAX_PARTY_SIZE:
        return {"headcount": count}
    return {"party_size": count}


def extract_slots(text: str, today: date) -> dict:
    """Only the slots found: date "YYYY-MM-DD", time "HH:MM", party_size, headcount."""
    lowered = text.lower()
    slots: dict = {}
    found_date = resolve_date(lowered, today)
    if found_date:
        slots["date"] = found_date.isoformat()
    found_time = _time(lowered)
    if found_time:
        slots["time"] = found_time
    slots.update(_people(lowered))
    return slots


def slots_key(slots: dict) -> str:
    """Canonical form for the cache key: "date=2026-10-09;party_size=4;time=19:00"."""
    return ";".join(f"{key}={slots[key]}" for key in sorted(slots))
