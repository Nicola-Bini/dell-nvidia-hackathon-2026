"""Date resolution for slots (SCHEMA 8.2).

A date with no year resolves to its next occurrence on or after `today`. Pure functions: the
caller supplies `today` in the business time zone.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, timedelta

_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4,
    "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}
MONTH_PATTERN = "|".join(sorted(_MONTHS, key=len, reverse=True))
_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "tues": 1, "wednesday": 2, "thursday": 3, "thurs": 3,
    "thur": 3, "friday": 4, "fri": 4, "saturday": 5, "sunday": 6,
}

_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_NUMERIC = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?(?![\d/])")
_DAY_MONTH = re.compile(
    rf"(?<![\d:])(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTH_PATTERN})\b(?:,?\s+(\d{{4}}))?"
)
_MONTH_DAY = re.compile(
    rf"\b({MONTH_PATTERN})\.?\s+(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?(?![\d:])(?:,?\s+(\d{{4}}))?"
)
_WEEKDAY = re.compile(rf"\b({'|'.join(sorted(_WEEKDAYS, key=len, reverse=True))})\b")
_TODAY = re.compile(r"\b(today|tonight|this (?:evening|afternoon|morning))\b")
_TOMORROW = re.compile(r"\btomorrow\b")


def nth_weekday(year: int, month: int, weekday: int, nth: int) -> date:
    """The nth (1-based) given weekday of a month; Monday is 0."""
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (nth - 1))


def last_weekday(year: int, month: int, weekday: int) -> date:
    following = date(year + month // 12, month % 12 + 1, 1)
    last = following - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _fixed(month: int, day: int) -> Callable[[int], date]:
    return lambda year: date(year, month, day)


# Checked in order, so "christmas eve" wins over "christmas".
_HOLIDAYS: list[tuple[re.Pattern[str], Callable[[int], date]]] = [
    (re.compile(r"\bthanksgiving\b"), lambda y: nth_weekday(y, 11, 3, 4)),
    (re.compile(r"\b(christmas|xmas) eve\b"), _fixed(12, 24)),
    (re.compile(r"\b(christmas|xmas)\b"), _fixed(12, 25)),
    (re.compile(r"\b(new years? eve|nye)\b"), _fixed(12, 31)),
    (re.compile(r"\bnew years?\b"), _fixed(1, 1)),
    (re.compile(r"\b(independence day|fourth of july|july fourth)\b"), _fixed(7, 4)),
    (re.compile(r"\bhalloween\b"), _fixed(10, 31)),
    (re.compile(r"\blabou?r day\b"), lambda y: nth_weekday(y, 9, 0, 1)),
    (re.compile(r"\bmemorial day\b"), lambda y: last_weekday(y, 5, 0)),
    (re.compile(r"\bvalentines?\b"), _fixed(2, 14)),
]


def _valid(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def next_month_day(month: int, day: int, today: date) -> date | None:
    """The next occurrence of a month and day on or after today (29 February may be years off)."""
    for year in range(today.year, today.year + 9):
        found = _valid(year, month, day)
        if found and found >= today:
            return found
    return None


def next_weekday(weekday: int, today: date) -> date:
    return today + timedelta(days=(weekday - today.weekday()) % 7)


def _with_year(month: int, day: int, year: str | None, today: date) -> date | None:
    if year is None:
        return next_month_day(month, day, today)
    return _valid(int(year) + (2000 if len(year) == 2 else 0), month, day)


def _iso(text: str, today: date) -> date | None:
    match = _ISO.search(text)
    return _valid(*(int(g) for g in match.groups())) if match else None


def _numeric(text: str, today: date) -> date | None:
    match = _NUMERIC.search(text)
    if not match:
        return None
    return _with_year(int(match[1]), int(match[2]), match[3], today)


def _named_month(text: str, today: date) -> date | None:
    match = _DAY_MONTH.search(text)
    if match:
        return _with_year(_MONTHS[match[2]], int(match[1]), match[3], today)
    match = _MONTH_DAY.search(text)
    if match:
        return _with_year(_MONTHS[match[1]], int(match[2]), match[3], today)
    return None


def _holiday(text: str, today: date) -> date | None:
    for pattern, on_year in _HOLIDAYS:
        if pattern.search(text):
            this_year = on_year(today.year)
            return this_year if this_year >= today else on_year(today.year + 1)
    return None


def _relative(text: str, today: date) -> date | None:
    if _TOMORROW.search(text):
        return today + timedelta(days=1)
    if _TODAY.search(text):
        return today
    match = _WEEKDAY.search(text)
    return next_weekday(_WEEKDAYS[match[1]], today) if match else None


_RESOLVERS = (_iso, _numeric, _named_month, _holiday, _relative)


def resolve_date(text: str, today: date) -> date | None:
    """The first date the text names, most explicit form first; None when it names none."""
    cleaned = re.sub(r"['‘’]", "", text.lower())
    for resolver in _RESOLVERS:
        found = resolver(cleaned, today)
        if found:
            return found
    return None
