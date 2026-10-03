"""Binder rule 1 (SCHEMA 8.3): clean_selection validates and cleans the model output."""

from __future__ import annotations

from binder_support import answer, gift_card_graph, menu, view

from cac_serve.domain.binder import clean_selection

CANDIDATES = ["diet_vegetarian", "sec_burgers", "mi_the_veg_dog", "mi_guinness",
              "faq_kitchen_hours", "alg_peanuts", "svc_private_events"]


def test_valid_selection_passes_unchanged(graph):
    selection = answer(menu(diet="diet_vegetarian", section="sec_burgers",
                            items=["mi_guinness"], order=True),
                       view("Answer", faq="faq_kitchen_hours"))
    assert clean_selection(graph, CANDIDATES, selection) == (selection, [])
    for fixed in (answer(view("HoursCard")), answer(view("BookingForm")),
                  answer(view("FormCard", form="ui_form_contact")),
                  answer(view("AllergenNotice", allergen="alg_peanuts")),
                  answer(view("AllergenNotice", allergen=None)),
                  answer(view("FactCard", node="svc_private_events")), {"kind": "off_topic"},
                  {"kind": "gap", "topic": "parking"}):
        assert clean_selection(graph, CANDIDATES, fixed) == (fixed, [])


def test_rejects_an_id_that_was_not_a_candidate(graph):
    for selection in (answer(menu(items=["mi_chicken_wings"])),
                      answer(menu(diet="diet_vegan")),
                      answer(view("Answer", faq="faq_brunch")),
                      answer(view("FactCard", node="svc_catering")),
                      answer(view("AllergenNotice", allergen="alg_milk"))):
        cleaned, errors = clean_selection(graph, CANDIDATES, selection)
        assert len(errors) == 1
        assert "was not a candidate" in errors[0]
        assert cleaned == {"kind": "answer", "views": []}


def test_rejects_an_unapproved_component(graph):
    for selection in (answer(view("GoalCTA")), answer(view("Cart")), answer(view("ItemCard")),
                      answer(view("FormCard", form="ui_form_gift_card")),
                      answer(view("FormCard", form="ui_menu_list")), answer("MenuList")):
        cleaned, errors = clean_selection(graph, CANDIDATES, selection)
        assert len(errors) == 1
        assert cleaned["views"] == []


def test_rejects_a_label_mismatch(graph):
    for selection in (answer(view("Answer", faq="mi_guinness")),
                      answer(menu(items=["faq_kitchen_hours"])),
                      answer(menu(diet="sec_burgers")),
                      answer(menu(section="diet_vegetarian")),
                      answer(view("AllergenNotice", allergen="mi_guinness"))):
        cleaned, errors = clean_selection(graph, CANDIDATES, selection)
        assert len(errors) == 1
        assert "has label" in errors[0]
        assert cleaned["views"] == []


def test_rejects_unknown_kind_and_no_views(graph):
    assert clean_selection(graph, CANDIDATES, {"kind": "joke"})[1]
    assert clean_selection(graph, CANDIDATES, {})[1]
    assert clean_selection(graph, CANDIDATES, answer())[1]
    assert clean_selection(graph, CANDIDATES, {"kind": "answer"})[1]


def test_deduplicates_and_caps(graph):
    selection = answer(
        menu(items=["mi_guinness", "mi_the_veg_dog", "mi_guinness"]),
        menu(section="sec_burgers"),
        view("HoursCard"),
        view("BookingForm"),
    )
    cleaned, errors = clean_selection(graph, CANDIDATES, selection)
    assert errors == []
    assert cleaned == answer(menu(items=["mi_guinness", "mi_the_veg_dog"]), view("HoursCard"))


def test_drops_unknown_keys_and_trims_the_gap_topic(graph):
    noisy = answer({"component": "HoursCard", "note": "ignore me"})
    assert clean_selection(graph, CANDIDATES, noisy) == (answer(view("HoursCard")), [])
    cleaned, errors = clean_selection(graph, [], {"kind": "gap", "topic": "x" * 80})
    assert errors == []
    assert cleaned == {"kind": "gap", "topic": "x" * 60}


def test_agent_created_label_and_form_are_selectable(graph):
    extended = gift_card_graph(graph)
    selection = answer(view("ListCard", label="GiftCard"),
                       view("FormCard", form="ui_form_gift_card"))
    assert clean_selection(extended, ["gc_25", "gc_50"], selection) == (selection, [])
    assert clean_selection(extended, ["gc_25"], answer(view("FactCard", node="gc_25")))[1] == []
    _, errors = clean_selection(extended, CANDIDATES, selection)
    assert len(errors) == 1
    assert "ListCard.label" in errors[0]
