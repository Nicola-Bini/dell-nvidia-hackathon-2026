"""wp6: the safety and steer rows of SCHEMA section 10, through the whole pipeline."""

from __future__ import annotations

from datetime import date

import pytest

from cac_serve.domain import binder
from cac_serve.domain.graph import Node
from cac_serve.domain.schema_builder import build_schema

pytestmark = pytest.mark.intents


def views(outcomes, text: str, component: str | None = None) -> list[dict]:
    found = outcomes[text].surface["views"]
    return [v for v in found if component is None or v["component"] == component]


def components(outcomes, text: str) -> list[str]:
    return [v["component"] for v in views(outcomes, text)]


def test_unverified_diet_is_never_a_badge(outcomes):
    items = [item for view in views(outcomes, "is the veg dog vegetarian?", "MenuList")
             for item in view["data"]["items"] if item["id"] == "mi_the_veg_dog"]
    assert items, "the veg dog is listed"
    for item in items:
        assert item["badges"] == [{"diet": "Vegetarian", "verified": False}]
    text = outcomes["is the veg dog vegetarian?"].surface["views"][0]["text"]
    assert "not verified, ask staff" in text.lower()


def test_gluten_free_beer_badges_are_all_unverified(outcomes):
    lists = views(outcomes, "is there a gluten free beer?", "MenuList")
    badges = [b for view in lists for item in view["data"]["items"] for b in item["badges"]]
    assert badges
    assert all(badge["verified"] is False for badge in badges)


@pytest.mark.parametrize("text", ["I'm allergic to peanuts", "nut-free dishes"])
def test_allergen_question_never_yields_a_dish_list(outcomes, text):
    shown = components(outcomes, text)
    assert "MenuList" not in shown
    assert "AllergenNotice" in shown
    notice = views(outcomes, text, "AllergenNotice")[0]
    assert notice["data"]["contains"] == []


def test_peanut_notice_uses_the_fixed_sentence(outcomes):
    notice = views(outcomes, "I'm allergic to peanuts", "AllergenNotice")[0]
    assert notice["text"] == ("We cannot guarantee any dish is free of peanuts. "
                              "Please tell your server about your allergy.")


@pytest.mark.parametrize(("text", "day"), [
    ("are you open on the 4th of July?", "2027-07-04"),
    ("are you open on Thanksgiving?", "2026-11-26"),
])
def test_date_resolver_and_closed_days(outcomes, text, day):
    card = views(outcomes, text, "HoursCard")[0]["data"]
    assert (card["date"], card["status"]) == (day, "closed")


def test_hours_question_gets_a_booking_cta(outcomes):
    cta = views(outcomes, "are you open tonight?", "GoalCTA")
    assert len(cta) == 1
    assert cta[0]["data"] == {"label": "Book a table"}
    assert cta[0]["actions"] == [{"name": "open_view:booking", "handler": "client"}]


def test_catering_question_gets_the_form_and_no_booking_cta(outcomes):
    shown = components(outcomes, "do you cater for 40?")
    assert shown == ["CateringQuoteForm"]
    form = views(outcomes, "do you cater for 40?")[0]["data"]
    assert form["prefill"] == {"headcount": 40}


def test_booking_form_is_prefilled_from_slots(outcomes):
    shown = components(outcomes, "table for 4 on Friday at 7pm")
    assert shown == ["BookingForm"]
    prefill = views(outcomes, "table for 4 on Friday at 7pm")[0]["data"]["prefill"]
    assert prefill == {"date": "2026-10-09", "time": "19:00", "party_size": 4}


def test_no_visitor_text_is_echoed(outcomes):
    gap = outcomes["is there parking nearby?"].surface
    assert gap["kind"] == "gap"
    assert "parking" not in str(gap).lower()


GIFT_CARDS = [
    Node("gc_25", "GiftCard", "$25 gift card",
         {"amounts": "$25", "terms": "Valid for 12 months. Redeemable in the bar."}),
    Node("gc_50", "GiftCard", "$50 gift card",
         {"amounts": "$50", "terms": "Valid for 12 months. Redeemable in the bar."}),
]
GIFT_FORM = Node("ui_form_gift_card", "UIComponent", "Request a gift card", {
    "component": "FormCard", "primitive": "FormCard", "version": 1, "selectable": True,
    "use_when": "Visitor wants to buy or request a gift card.",
    "binds": {"labels": ["Service"], "min": 0, "max": 1},
    "rail_label": "Request a gift card", "say": None, "chips": ["See the menu"],
    "channels": ["web", "mcp"], "submit_label": "Send request",
    "fields": [{"name": "name", "type": "text", "label": "Your name", "required": True}],
})


def test_agent_created_label_and_form_are_selectable_and_render(graph):
    """Generic components: a new label and a configured form need no new code."""
    evolved = graph.extended(nodes=[*GIFT_CARDS, GIFT_FORM])
    candidates = ["gc_25", "gc_50", "ui_form_gift_card"]
    schema = build_schema(evolved, candidates)
    offered = str(schema)
    assert "'GiftCard'" in offered and "'ui_form_gift_card'" in offered
    selection = {"kind": "answer", "views": [
        {"component": "ListCard", "label": "GiftCard"},
        {"component": "FormCard", "form": "ui_form_gift_card"}]}
    cleaned, errors = binder.clean_selection(evolved, candidates, selection)
    assert errors == []
    surface = binder.bind(evolved, cleaned, {}, date(2026, 10, 3))
    shown = [view["component"] for view in surface["views"]]
    assert shown[:2] == ["ListCard", "FormCard"]
    assert [item["id"] for item in surface["views"][0]["data"]["items"]] == ["gc_25", "gc_50"]
    assert surface["views"][1]["actions"] == [{"name": "submit_form", "handler": "server"}]
