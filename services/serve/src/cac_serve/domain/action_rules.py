"""Validation of untrusted action payloads (SCHEMA 8.4 form payloads, 8.5 rules).

Pure functions: each returns (clean payload, errors). The clean payload holds only known
fields, so nothing unexpected is stored. Errors are [{ "field", "message" }].
"""

from __future__ import annotations

import re
from datetime import date

from cac_serve.domain.graph import Node

MAX_SHORT = 200
MAX_LONG = 1000
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_DIGIT_RUN = re.compile(r"(?:\d[ -]?){13,19}")

Errors = list[dict[str, str]]


def _error(field: str, message: str) -> dict[str, str]:
    return {"field": field, "message": message}


def _luhn(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value = value * 2 - 9 if value > 4 else value * 2
        total += value
    return total % 10 == 0


def looks_sensitive(value: str) -> bool:
    """Card numbers and SSNs are never stored anywhere in CAC (PRD section 10, invariant 7)."""
    if _SSN.search(value):
        return True
    for match in _DIGIT_RUN.finditer(value):
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn(digits):
            return True
    return False


def _text(payload: dict, field: str, errors: Errors, required: bool, limit: int) -> str | None:
    value = payload.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            errors.append(_error(field, "This field is required."))
        return None
    if not isinstance(value, str) or len(value) > limit:
        errors.append(_error(field, f"Must be text of at most {limit} characters."))
        return None
    if looks_sensitive(value):
        errors.append(_error(field, "Please do not send card or ID numbers."))
        return None
    return value.strip()


def _date(payload: dict, field: str, errors: Errors, today: date) -> str | None:
    value = payload.get(field)
    try:
        parsed = date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        parsed = None
    if parsed is None:
        errors.append(_error(field, "Enter a date as YYYY-MM-DD."))
        return None
    if parsed < today:
        errors.append(_error(field, "The date is in the past."))
        return None
    return parsed.isoformat()


def _integer(payload: dict, field: str, errors: Errors, bounds: tuple[int, int]) -> int | None:
    value = payload.get(field)
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value)
    low, high = bounds
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        errors.append(_error(field, f"Enter a whole number from {low} to {high}."))
        return None
    return value


def _contact_fields(payload: dict, errors: Errors) -> dict:
    clean = {
        "name": _text(payload, "name", errors, True, MAX_SHORT),
        "contact": _text(payload, "contact", errors, True, MAX_SHORT),
    }
    notes = _text(payload, "notes", errors, False, MAX_LONG)
    if notes is not None:
        clean["notes"] = notes
    return clean


def validate_booking(payload: dict, today: date) -> tuple[dict, Errors]:
    errors: Errors = []
    clean: dict = {"date": _date(payload, "date", errors, today)}
    time_value = payload.get("time")
    if isinstance(time_value, str) and _TIME.match(time_value):
        clean["time"] = time_value
    else:
        errors.append(_error("time", "Enter a time as HH:MM."))
    clean["party_size"] = _integer(payload, "party_size", errors, (1, 20))
    clean.update(_contact_fields(payload, errors))
    return clean, errors


def validate_catering(payload: dict, today: date, min_headcount: int | None) -> tuple[dict, Errors]:
    errors: Errors = []
    clean: dict = {"date": _date(payload, "date", errors, today)}
    headcount = _integer(payload, "headcount", errors, (1, 5000))
    if headcount is not None and min_headcount and headcount < min_headcount:
        errors.append(_error("headcount", f"Catering starts at {min_headcount} guests."))
    clean["headcount"] = headcount
    clean.update(_contact_fields(payload, errors))
    return clean, errors


def _form_value(spec: dict, raw: object, errors: Errors, today: date) -> object:
    name, kind = spec.get("name", ""), spec.get("type", "text")
    holder = {name: raw}
    if kind == "number":
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            errors.append(_error(name, "Enter a number."))
            return None
        return raw
    if kind == "date":
        return _date(holder, name, errors, today)
    if kind == "select":
        if raw not in (spec.get("options") or []):
            errors.append(_error(name, "Choose one of the listed options."))
            return None
        return raw
    return _text(holder, name, errors, True, MAX_LONG)


def validate_form(form: Node, payload: dict, today: date) -> tuple[dict, Errors]:
    """Check `values` against the form's configured `fields`; unknown keys are dropped."""
    errors: Errors = []
    values = payload.get("values")
    if not isinstance(values, dict):
        return {}, [_error("values", "Expected an object of field values.")]
    clean: dict = {}
    for spec in form.props.get("fields") or []:
        name = spec.get("name", "")
        raw = values.get(name)
        if raw is None or raw == "":
            if spec.get("required"):
                errors.append(_error(name, "This field is required."))
            continue
        value = _form_value(spec, raw, errors, today)
        if value is not None:
            clean[name] = value
    return {"form": form.id, "values": clean}, errors
