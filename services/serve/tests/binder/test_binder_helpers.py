"""Pure helpers of the binder: no database needed."""

from __future__ import annotations

from datetime import date

import pytest

from cac_serve.domain import hours, templates
from cac_serve.domain.binder import bind, preset_surface, steer_shown, surface_text
from cac_serve.domain.graph import Graph, Node


@pytest.mark.parametrize(
    ("cents", "text"),
    [(995, "$9.95"), (800, "$8.00"), (5, "$0.05"), (120000, "$1,200.00"), (None, ""),
     ("995", ""), (True, ""), (-1, "")],
)
def test_price(cents, text):
    assert templates.price(cents) == text


@pytest.mark.parametrize(
    ("hhmm", "text"),
    [("11:00", "11:00 AM"), ("02:00", "2:00 AM"), ("00:30", "12:30 AM"), ("12:00", "12:00 PM"),
     ("23:59", "11:59 PM"), ("25:00", ""), ("soon", ""), (None, "")],
)
def test_time12(hhmm, text):
    assert hours.time12(hhmm) == text


def test_dates_are_spelled_without_locale():
    assert hours.long_date(date(2026, 10, 3)) == "Saturday 3 October 2026"
    assert hours.short_date(date(2026, 10, 4)) == "Sunday 4 October"


@pytest.mark.parametrize(
    ("days", "text"),
    [(["sun"], "Sunday"), (["mon", "tue", "wed"], "Monday to Wednesday"),
     (["thu", "fri", "sat"], "Thursday to Saturday"), (["mon", "tue"], "Monday and Tuesday"),
     (["mon", "wed", "fri"], "Monday, Wednesday and Friday"), ([], "")],
)
def test_days_phrase(days, text):
    assert hours.days_phrase(days) == text


def test_plain_words_and_plural_label():
    assert templates.plain_words("min_headcount") == "Min headcount"
    assert templates.plain_words("kind") == "Kind"
    assert templates.plural_label("GiftCard") == "Gift cards"
    assert templates.plural_label("Promotion") == "Promotions"


def test_fact_value_and_sentence():
    assert templates.fact_value(["$25", "$50"]) == "$25, $50"
    assert templates.fact_value(None) == ""
    assert templates.fact_value(True) == "Yes"
    assert templates.fact_value(15) == "15"
    assert templates.sentence("Draft") == "Draft."
    assert templates.sentence("Let us cater your next event!") == "Let us cater your next event!"


def test_title_rules():
    long_title = "Pale Ales & Lagers & Wheat & Pilsners & Fruited"
    assert templates.rail_title("Vegetarian", "Menu", "MenuList") == "Vegetarian"
    assert templates.rail_title(None, "Hours", "HoursCard") == "Hours"
    assert templates.rail_title(long_title, "Menu", "MenuList") == "Menu"
    assert templates.rail_title(long_title, "A rail label far longer than the limit", "X") == (
        long_title[:24]
    )
    assert templates.rail_title(None, None, "FactCard") == "FactCard"


def _hours_graph(*extra: Node) -> Graph:
    nodes = [
        Node("biz", "Business", "Cafe", {"phone": "+1 555 0100"}),
        Node("hrs_week", "HoursSpec", "Weekdays",
             {"days": ["mon", "tue", "wed", "thu", "fri"], "opens": "08:00", "closes": "17:00"}),
        Node("ui_hours_card", "UIComponent", "Hours",
             {"component": "HoursCard", "rail_label": "Hours", "say": None, "chips": ["Menu"]}),
    ]
    return Graph("biz", 3, [*nodes, *extra], [])


def test_hours_same_day_close_and_missing_row():
    graph = _hours_graph()
    monday = hours.hours_data(graph, date(2026, 10, 5))
    assert (monday["status"], monday["opens"], monday["closes"]) == ("open", "08:00", "17:00")
    assert hours.hours_say(monday) == "Open on Monday 5 October 2026, 8:00 AM to 5:00 PM."
    assert hours.hours_text(monday) == (
        "Open on Monday 5 October 2026 from 8:00 AM to 5:00 PM."
        " Regular hours: Monday to Friday 8:00 AM to 5:00 PM."
    )
    saturday = hours.hours_data(graph, date(2026, 10, 3))
    assert (saturday["status"], saturday["opens"], saturday["closes"]) == (None, None, None)
    assert hours.hours_say(saturday) == "We have no hours listed for Saturday 3 October 2026."


def test_special_hours_with_times_win_over_the_regular_row():
    special = Node("sh_1", "SpecialHours", "Short day",
                   {"date": "2026-10-05", "closed": False, "opens": "10:00", "closes": "14:00",
                    "note": "Short day"})
    data = hours.hours_data(_hours_graph(special), date(2026, 10, 5))
    assert (data["status"], data["opens"], data["closes"], data["note"]) == (
        "open", "10:00", "14:00", "Short day")


def test_slot_date_falls_back_to_today():
    today = date(2026, 10, 3)
    assert hours.slot_date({"date": "2027-07-04"}, today) == date(2027, 7, 4)
    assert hours.slot_date({"date": "next week"}, today) == today
    assert hours.slot_date({}, today) == today


def test_surface_without_goals_has_no_cta_and_reads_as_text():
    graph = _hours_graph()
    surface = bind(graph, {"kind": "answer", "views": [{"component": "HoursCard"}]}, {},
                   date(2026, 10, 5))
    assert [v["component"] for v in surface["views"]] == ["HoursCard"]
    assert not steer_shown(surface)
    assert surface_text(surface) == surface["views"][0]["text"]
    assert surface["meta"] == {"cache": "miss", "latency_ms": 0, "graph_version": 3,
                               "model": "local"}
    assert surface["chips"] == ["Menu"]


def test_unbindable_selection_becomes_the_gap_surface():
    graph = _hours_graph()
    today = date(2026, 10, 5)
    for selection in ({"kind": "answer", "views": [{"component": "BookingForm"}]},
                      {"kind": "answer", "views": []}, {"kind": "nonsense"}):
        surface = bind(graph, selection, {}, today)
        assert surface["kind"] == "gap"
        assert surface["views"][0]["data"]["facts"] == [{"name": "Phone", "value": "+1 555 0100"}]
        assert surface_text(surface).endswith("Phone: +1 555 0100.")
    off_topic = bind(graph, {"kind": "off_topic"}, {}, today)
    assert surface_text(off_topic) == off_topic["say"]
    assert preset_surface(graph, "reviews", today) is None
