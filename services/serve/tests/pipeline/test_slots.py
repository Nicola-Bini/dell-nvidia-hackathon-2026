"""SCHEMA 8.2: slots are extracted by code. Every date is pinned to Saturday 2026-10-03."""

from __future__ import annotations

from datetime import date

import pytest

from cac_serve.domain.slots import extract_slots, slots_key

TODAY = date(2026, 10, 3)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("are you open on the 4th of July?", "2027-07-04"),
        ("are you open on Thanksgiving?", "2026-11-26"),
        ("are you open tonight?", "2026-10-03"),
        ("open today?", "2026-10-03"),
        ("can I come tomorrow", "2026-10-04"),
        ("what time do you close on Saturday", "2026-10-03"),
        ("table on Friday", "2026-10-09"),
        ("open Sunday?", "2026-10-04"),
        ("are you open July 4", "2027-07-04"),
        ("are you open 4 July", "2027-07-04"),
        ("open Dec 25th?", "2026-12-25"),
        ("open on 10/31?", "2026-10-31"),
        ("open on 10/3?", "2026-10-03"),
        ("open on 10/2?", "2027-10-02"),
        ("booking for 2026-12-24", "2026-12-24"),
        ("open on Christmas Eve?", "2026-12-24"),
        ("open on Christmas?", "2026-12-25"),
        ("open Christmas Day?", "2026-12-25"),
        ("open on New Year's Eve?", "2026-12-31"),
        ("open on New Year's Day?", "2027-01-01"),
        ("open on Independence Day?", "2027-07-04"),
        ("open on the Fourth of July?", "2027-07-04"),
        ("open on Halloween?", "2026-10-31"),
        ("open on Labor Day?", "2027-09-06"),
        ("open on Memorial Day?", "2027-05-31"),
        ("open on Valentine's Day?", "2027-02-14"),
        ("open on October 3rd?", "2026-10-03"),
        ("open on October 2nd?", "2027-10-02"),
    ],
)
def test_date_resolves_to_next_occurrence_on_or_after_today(text, expected):
    assert extract_slots(text, TODAY).get("date") == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("table at 7pm", "19:00"),
        ("table at 7:30 pm", "19:30"),
        ("table at 7 p.m.", "19:00"),
        ("come at 19:00", "19:00"),
        ("are you open at noon", "12:00"),
        ("are you open at midnight", "00:00"),
        ("open at 12am?", "00:00"),
        ("open at 12pm?", "12:00"),
        ("open at 11:15am?", "11:15"),
    ],
)
def test_time(text, expected):
    assert extract_slots(text, TODAY).get("time") == expected


@pytest.mark.parametrize(
    "text",
    ["table for 4", "are you open on the 4th of July?", "do you cater for 40?",
     "open on 10/31?", "booking for 2026-12-24", "vegetarian options"],
)
def test_counts_and_dates_are_not_times(text):
    assert "time" not in extract_slots(text, TODAY)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("table for 4", 4),
        ("party of 6", 6),
        ("for 2 people", 2),
        ("there are 4 of us, can we book?", 4),
        ("can I reserve for 3 at 7pm", 3),
        ("table for two tonight", 2),
    ],
)
def test_party_size(text, expected):
    slots = extract_slots(text, TODAY)
    assert slots.get("party_size") == expected
    assert "headcount" not in slots


def test_headcount_in_a_catering_context():
    assert extract_slots("do you cater for 40?", TODAY) == {"headcount": 40}
    assert extract_slots("catering for 15 people", TODAY) == {"headcount": 15}
    assert extract_slots("an event with 60 guests", TODAY) == {"headcount": 60}


def test_a_group_too_large_for_a_table_is_a_headcount():
    assert extract_slots("table for 30", TODAY) == {"headcount": 30}


def test_booking_sentence_fills_three_slots():
    assert extract_slots("table for 4 on Friday at 7pm", TODAY) == {
        "date": "2026-10-09", "time": "19:00", "party_size": 4,
    }


def test_no_slots_gives_an_empty_dict():
    assert extract_slots("vegetarian options", TODAY) == {}
    assert extract_slots("tell me a joke", TODAY) == {}
    assert extract_slots("how much are the chicken wings", TODAY) == {}
    assert extract_slots("food for the 4th", TODAY) == {}


def test_slots_key_is_canonical():
    slots = {"time": "19:00", "party_size": 4, "date": "2026-10-09"}
    assert slots_key(slots) == "date=2026-10-09;party_size=4;time=19:00"
    assert slots_key({}) == ""
    assert slots_key({"headcount": 40}) == "headcount=40"
