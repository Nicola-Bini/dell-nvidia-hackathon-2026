"""The binder reproduces every golden Surface (fixtures/surfaces) from the seeded graph."""

from __future__ import annotations

import copy
import re

import pytest
from binder_support import (
    TODAY,
    answer,
    gift_card_graph,
    load_golden,
    menu,
    strip_volatile,
    view,
)

from cac_serve.domain.binder import bind, busy_surface, preset_surface

CASES = [
    ("menu_vegetarian", answer(menu(diet="diet_vegetarian")), {}),
    ("menu_vegetarian_order", answer(menu(diet="diet_vegetarian", order=True)), {}),
    ("menu_draft_beer", answer(menu(section="sec_draft_beer")), {}),
    ("allergen_peanuts", answer(view("AllergenNotice", allergen="alg_peanuts")), {}),
    ("hours_saturday", answer(view("HoursCard")), {}),
    ("hours_july4", answer(view("HoursCard")), {"date": "2027-07-04"}),
    ("answer_kitchen_hours", answer(view("Answer", faq="faq_kitchen_hours")), {}),
    ("booking_form", answer(view("BookingForm")),
     {"date": "2026-10-09", "time": "19:00", "party_size": 4}),
    ("catering_form_40", answer(view("CateringQuoteForm")), {"headcount": 40}),
    ("form_contact", answer(view("FormCard", form="ui_form_contact")), {}),
    ("fact_card", answer(view("FactCard", node="svc_private_events")), {}),
    ("gap", {"kind": "gap", "topic": "parking"}, {}),
    ("off_topic", {"kind": "off_topic"}, {}),
]


@pytest.mark.parametrize(("name", "selection", "slots"), CASES, ids=[c[0] for c in CASES])
def test_selection_binds_to_golden(graph, name, selection, slots):
    surface = bind(graph, selection, slots, TODAY)
    assert strip_volatile(surface) == strip_volatile(load_golden(name))


def test_bound_surface_meta_and_id(graph):
    surface = bind(graph, answer(view("HoursCard")), {}, TODAY)
    assert re.fullmatch(r"s_[0-9a-f]{12}", surface["surface_id"])
    assert surface["meta"] == {"cache": "miss", "latency_ms": 0,
                               "graph_version": graph.version, "model": "local"}
    assert list(surface) == ["surface_id", "kind", "title", "say", "views", "chips", "meta"]


def test_preset_menu_matches_golden(graph):
    surface = preset_surface(graph, "menu", TODAY)
    assert strip_volatile(surface) == strip_volatile(load_golden("preset_menu"))
    assert surface["meta"]["cache"] == "preset"
    assert surface["meta"]["graph_version"] == graph.version


def test_busy_fallback_matches_golden(graph):
    surface = busy_surface(graph, TODAY)
    assert strip_volatile(surface) == strip_volatile(load_golden("busy_fallback"))
    assert surface["meta"]["cache"] == "preset"


def test_other_presets(graph):
    booking = preset_surface(graph, "booking", TODAY)
    assert booking["kind"] == "preset"
    assert booking["meta"]["cache"] == "preset"
    assert [v["component"] for v in booking["views"]] == ["BookingForm"]
    assert booking["views"][0]["data"] == {"prefill": {}}
    assert booking["views"][0]["text"] == (
        "Request a table at The Kenmore. This is a request, not a confirmed reservation;"
        " the restaurant will confirm."
    )
    catering = preset_surface(graph, "catering", TODAY)
    assert [v["component"] for v in catering["views"]] == ["CateringQuoteForm"]
    assert catering["views"][0]["data"] == {"prefill": {}, "min_headcount": None}
    hours = preset_surface(graph, "hours", TODAY)
    golden = load_golden("hours_saturday")
    assert hours["views"] == golden["views"]
    assert (hours["kind"], hours["title"], hours["say"]) == ("preset", "Hours", golden["say"])
    assert preset_surface(graph, "nope", TODAY) is None


def _gift_cards(graph) -> dict:
    selection = answer(view("ListCard", label="GiftCard"),
                       view("FormCard", form="ui_form_gift_card"))
    return strip_volatile(bind(gift_card_graph(graph), selection, {}, TODAY))


def test_gift_cards_matches_golden_except_form_text(graph):
    """An agent-created label and form bind with no new code (SCHEMA section 7)."""
    surface = _gift_cards(graph)
    golden = strip_volatile(load_golden("gift_cards"))
    expected = copy.deepcopy(golden)
    expected["views"][1]["text"] = "Request a gift card: Your name, Email or phone, Amount."
    assert surface == expected


def test_gift_cards_form_text_matches_golden(graph):
    assert _gift_cards(graph) == strip_volatile(load_golden("gift_cards"))
