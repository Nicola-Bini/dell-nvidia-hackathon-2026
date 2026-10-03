"""HoursCard data and sentences, computed in code (SCHEMA 8.3 rule 6).

SpecialHours for the date win over HoursSpec. A `closes` earlier than `opens` means the next
calendar day; `status` is for the service day in `date`.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from cac_serve.domain.graph import Graph, Node

WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")  # date.weekday() order
WEEK_ORDER = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")  # display order
DAY_NAMES = {
    "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
    "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
}
MONTHS = (
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
)
ALL_WRAP = "Closing times are after midnight, on the next day."
SOME_WRAP = "A closing time earlier than the opening time is on the next day."


def slot_date(slots: dict, today: date) -> date:
    """The date slot, or today when it is missing or not a valid ISO date."""
    raw = slots.get("date")
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        return today


def time12(hhmm: Any) -> str:
    """"02:00" -> "2:00 AM", "12:30" -> "12:30 PM". Unparseable input renders as ""."""
    try:
        hour, minute = (int(part) for part in str(hhmm).split(":")[:2])
    except ValueError:
        return ""
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return ""
    return f"{hour % 12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"


def short_date(day: date) -> str:
    return f"{DAY_NAMES[WEEKDAY_KEYS[day.weekday()]]} {day.day} {MONTHS[day.month - 1]}"


def long_date(day: date) -> str:
    return f"{short_date(day)} {day.year}"


def wraps(opens: Any, closes: Any) -> bool:
    """True when the closing time is on the next calendar day."""
    return bool(opens and closes) and str(closes) < str(opens)


def days_phrase(days: list[str]) -> str:
    """["mon","tue","wed"] -> "Monday to Wednesday"; one day -> its name."""
    known = [d for d in days if d in DAY_NAMES]
    names = [DAY_NAMES[d] for d in known]
    if len(names) <= 1:
        return "".join(names)
    index = [WEEK_ORDER.index(d) for d in known]
    if len(names) >= 3 and index == list(range(index[0], index[0] + len(index))):
        return f"{names[0]} to {names[-1]}"
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _days(node: Node) -> list[str]:
    days = node.props.get("days")
    return [str(d) for d in days] if isinstance(days, list) else []


def _first_day(node: Node) -> int:
    index = [WEEK_ORDER.index(d) for d in _days(node) if d in WEEK_ORDER]
    return min(index) if index else len(WEEK_ORDER)


def week_rows(graph: Graph) -> list[dict]:
    """Every HoursSpec row, Sunday first."""
    rows = sorted(graph.by_label("HoursSpec"), key=lambda n: (_first_day(n), n.id))
    return [
        {"days": _days(n), "opens": n.props.get("opens"), "closes": n.props.get("closes")}
        for n in rows
    ]


def _special(graph: Graph, day: date) -> Node | None:
    iso = day.isoformat()
    found = [n for n in graph.by_label("SpecialHours") if str(n.props.get("date")) == iso]
    return min(found, key=lambda n: n.id) if found else None


def _regular_props(graph: Graph, day: date) -> dict:
    key = WEEKDAY_KEYS[day.weekday()]
    found = [n for n in graph.by_label("HoursSpec") if key in _days(n)]
    return min(found, key=lambda n: n.id).props if found else {}


def _day_state(graph: Graph, day: date) -> dict:
    special = _special(graph, day)
    props = special.props if special is not None else {}
    note = props.get("note") or None
    if props.get("closed"):
        return {"status": "closed", "opens": None, "closes": None, "note": note}
    has_times = bool(props.get("opens") and props.get("closes"))
    source = props if has_times else _regular_props(graph, day)
    opens, closes = source.get("opens"), source.get("closes")
    if not (opens and closes):
        return {"status": None, "opens": None, "closes": None, "note": None}
    return {"status": "open", "opens": opens, "closes": closes, "note": note}


def hours_data(graph: Graph, day: date) -> dict:
    """HoursCard `data` for one date (SCHEMA 8.4)."""
    return {"date": day.isoformat(), **_day_state(graph, day), "week": week_rows(graph)}


def hours_say(data: dict) -> str:
    """The sentence shown above the card."""
    day = long_date(date.fromisoformat(data["date"]))
    if data["status"] == "closed":
        return f"Closed on {day}."
    if data["status"] == "open":
        return f"Open on {day}, {time12(data['opens'])} to {time12(data['closes'])}."
    return f"We have no hours listed for {day}."


def _day_text(data: dict) -> str:
    day = date.fromisoformat(data["date"])
    note = f" {data['note']}." if data["note"] else ""
    if data["status"] != "open":
        return hours_say(data) + note
    opens, closes = time12(data["opens"]), time12(data["closes"])
    if wraps(data["opens"], data["closes"]):
        next_day = short_date(day + timedelta(days=1))
        return f"Open on {long_date(day)} from {opens}; closes at {closes} on {next_day}.{note}"
    return f"Open on {long_date(day)} from {opens} to {closes}.{note}"


def _week_text(week: list[dict]) -> str:
    if not week:
        return ""
    parts = [
        f"{days_phrase(r['days'])} {time12(r['opens'])} to {time12(r['closes'])}" for r in week
    ]
    text = f"Regular hours: {'; '.join(parts)}."
    wrapping = [wraps(r["opens"], r["closes"]) for r in week]
    if all(wrapping):
        return f"{text} {ALL_WRAP}"
    return f"{text} {SOME_WRAP}" if any(wrapping) else text


def hours_text(data: dict) -> str:
    """The view's `text` for assistants: the day, then the regular week."""
    return " ".join(part for part in (_day_text(data), _week_text(data["week"])) if part)
