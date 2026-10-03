"""SCHEMA section 10 rows the binder owns: diet badges, allergens, goal steer, dates."""

from __future__ import annotations

from binder_support import TODAY, answer, components, first, menu, view

from cac_serve.domain.binder import bind, preset_surface, steer_shown, surface_text
from cac_serve.domain.graph import Edge

VEG_DOG = "mi_the_veg_dog"
VEG_BURGER = "mi_the_beyond_meat_burger_vegetarian"
PEANUTS = view("AllergenNotice", allergen="alg_peanuts")


def _badges(surface: dict, item_id: str) -> list[dict]:
    items = first(surface, "MenuList")["data"]["items"]
    return next(i for i in items if i["id"] == item_id)["badges"]


def test_unverified_diet_edge_is_never_a_verified_badge(graph):
    by_diet = bind(graph, answer(menu(diet="diet_vegetarian")), {}, TODAY)
    by_name = bind(graph, answer(menu(items=[VEG_DOG])), {}, TODAY)
    by_section = bind(graph, answer(menu(section="sec_hot_dogs")), {}, TODAY)
    for surface in (by_diet, by_name, by_section):
        assert _badges(surface, VEG_DOG) == [{"diet": "Vegetarian", "verified": False}]
    assert "Not verified, ask staff: The Veg \"Dog\"" in first(by_diet, "MenuList")["text"]
    assert "Vegetarian: not verified, ask staff" in first(by_name, "MenuList")["text"]
    assert "confirmed" not in first(by_name, "MenuList")["text"]
    assert by_name["title"] == "Menu"


def test_only_owner_verified_edges_are_verified(graph):
    surface = preset_surface(graph, "menu", TODAY)
    verified = [
        item["id"]
        for v in surface["views"] if v["component"] == "MenuList"
        for item in v["data"]["items"] if any(b["verified"] for b in item["badges"])
    ]
    assert verified == [VEG_BURGER]


def test_gluten_free_list_is_all_unverified(graph):
    surface = bind(graph, answer(menu(diet="diet_gluten_free")), {}, TODAY)
    listing = first(surface, "MenuList")
    assert [i["id"] for i in listing["data"]["items"]] == [
        "mi_xul_tiny_umbrella", "mi_happy_dad_grape", "mi_happy_dad_fruit_punch"]
    assert all(b == {"diet": "Gluten-free", "verified": False}
               for i in listing["data"]["items"] for b in i["badges"])
    assert listing["text"].startswith("Gluten-free (not verified, ask staff): ")
    assert "confirmed" not in listing["text"]


def test_diet_filter_never_lists_an_item_without_the_tag(graph):
    named = menu(diet="diet_vegetarian", items=["mi_chicken_wings", VEG_BURGER])
    surface = bind(graph, answer(named), {}, TODAY)
    assert [i["id"] for i in first(surface, "MenuList")["data"]["items"]] == [VEG_BURGER]
    nothing = bind(graph, answer(menu(diet="diet_vegan")), {}, TODAY)
    assert nothing["kind"] == "gap"
    unknown = bind(graph, answer(menu(diet="diet_keto")), {}, TODAY)
    assert unknown["kind"] == "gap"


def test_badges_list_every_diet_in_seed_order(graph):
    tagged = graph.extended(edges=[
        Edge(VEG_DOG, "diet_gluten_free", "SUITABLE_FOR"),
        Edge(VEG_DOG, "diet_vegan", "SUITABLE_FOR", verified=True),
    ])
    surface = bind(tagged, answer(menu(items=[VEG_DOG])), {}, TODAY)
    assert _badges(surface, VEG_DOG) == [
        {"diet": "Vegetarian", "verified": False},
        {"diet": "Vegan", "verified": True},
        {"diet": "Gluten-free", "verified": False},
    ]


def test_allergen_selection_never_shows_a_menu_list(graph):
    """ "I'm allergic to peanuts", "nut-free dishes": AllergenNotice only."""
    selections = [
        answer(PEANUTS),
        answer(menu(section="sec_burgers"), PEANUTS),
        answer(PEANUTS, menu(diet="diet_vegetarian")),
        answer(menu(items=["mi_chicken_wings"]), view("AllergenNotice", allergen="alg_tree_nuts")),
        answer(menu(section="sec_burgers"), view("AllergenNotice", allergen=None)),
    ]
    for selection in selections:
        surface = bind(graph, selection, {}, TODAY)
        assert "MenuList" not in components(surface)
        assert components(surface).count("AllergenNotice") == 1
        assert first(surface, "AllergenNotice")["data"]["contains"] == []
        assert "mi_" not in surface_text(surface)


def test_allergen_contains_lists_only_owner_verified_edges(graph):
    tagged = graph.extended(edges=[
        Edge("mi_chicken_wings", "alg_peanuts", "CONTAINS_ALLERGEN", verified=True),
        Edge("mi_pretzel_bites", "alg_peanuts", "CONTAINS_ALLERGEN", verified=False),
    ])
    notice = first(bind(tagged, answer(PEANUTS), {}, TODAY), "AllergenNotice")
    assert notice["data"] == {
        "allergen": "peanuts", "contains": [{"id": "mi_chicken_wings", "name": "Chicken Wings"}]}
    assert notice["text"] == (
        "We cannot guarantee any dish is free of peanuts. Please tell your server about your"
        " allergy. Confirmed to contain peanuts: Chicken Wings."
    )


def test_menu_list_always_gets_the_allergen_notice(graph):
    surface = bind(graph, answer(menu(section="sec_burgers"),
                                 view("Answer", faq="faq_kitchen_hours")), {}, TODAY)
    assert components(surface) == ["MenuList", "AllergenNotice", "Answer", "GoalCTA"]
    assert [v["id"] for v in surface["views"]] == ["v1", "v2", "v3", "v4"]
    assert first(surface, "AllergenNotice")["data"] == {"allergen": None, "contains": []}


def test_goal_steer(graph):
    hours = bind(graph, answer(view("HoursCard")), {}, TODAY)
    assert steer_shown(hours)
    assert hours["views"][-1]["data"] == {"label": "Book a table"}
    assert hours["views"][-1]["actions"] == [{"name": "open_view:booking", "handler": "client"}]
    catering = bind(graph, answer(view("CateringQuoteForm")), {"headcount": 40}, TODAY)
    booking = bind(graph, answer(view("BookingForm")), {}, TODAY)
    both = bind(graph, answer(view("HoursCard"), view("BookingForm")), {}, TODAY)
    for surface in (catering, booking, both):
        assert not steer_shown(surface)
    assert components(catering) == ["CateringQuoteForm"]
    for fixed in ({"kind": "gap", "topic": "parking"}, {"kind": "off_topic"}):
        assert not steer_shown(bind(graph, fixed, {}, TODAY))


def test_thanksgiving_is_closed(graph):
    surface = bind(graph, answer(view("HoursCard")), {"date": "2026-11-26"}, TODAY)
    data = surface["views"][0]["data"]
    assert (data["date"], data["status"], data["opens"], data["closes"], data["note"]) == (
        "2026-11-26", "closed", None, None, "Thanksgiving")
    assert surface["say"] == "Closed on Thursday 26 November 2026."
    assert surface["views"][0]["text"].startswith(
        "Closed on Thursday 26 November 2026. Thanksgiving. Regular hours: ")


def test_section_and_named_items_combine(graph):
    surface = bind(graph, answer(menu(section="sec_draft_beer", items=["mi_guinness"])), {},
                   TODAY)
    listing = first(surface, "MenuList")
    assert listing["data"]["title"] == "Draft Beer"
    assert [i["id"] for i in listing["data"]["items"]] == ["mi_guinness"]
    assert listing["data"]["more"] is None
    assert listing["text"].startswith("Draft Beer: Guinness, $9.00. Rich and creamy.")


def test_booking_form_degrades_without_slots(graph):
    surface = bind(graph, answer(view("BookingForm")), {"party_size": 2}, TODAY)
    form = surface["views"][0]
    assert form["data"] == {"prefill": {"party_size": 2}}
    assert form["text"].startswith("Request a table at The Kenmore for 2. This is a request")
